"""
SCRIPT: iametadata.py
PURPOSE: Internet Archive (archive.org) Smart Metadata Editor & Syncer
AUTHOR: Assistant (AI)
DATE: 2026-08-30
VERSION: 1.03 (Multi-Paragraph & External Editor Support)

================================================================================
DOCUMENTATION & UPDATE POLICY
================================================================================
1. STRICT UPDATE RULE:
   Any future modifications to this script MUST be documented in the "CHANGE LOG".

2. RECURSIVE NOTICE REQUIREMENT:
   This documentation block must be included in every version of the script.

================================================================================
CHANGE LOG
================================================================================
[2026-08-30] VERSION 1.03 UPDATE
   - ADDED: Multi-line description support with 'p' (terminal paste mode until EOF/Ctrl+Z)
           and 'e' (external Notepad / text editor integration).
   - ADDED: --description-file / --desc-file CLI argument to load descriptions from file.
   - FIXED: Multi-paragraph paste waterfall across subsequent interactive prompts.

[2026-08-30] VERSION 1.02 UPDATE
   - FIXED: Corrected missing colon syntax error on tag condition check.
   - AUDITED: Verified all function definitions and conditional statements.

[2026-08-30] VERSION 1.01 UPDATE
   - FIXED: Replaced io.TextIOWrapper assignment with sys.stdout.reconfigure() to
           prevent Windows garbage collection from closing standard stream handles.
   - ADDED: Top-level diagnostic wrapper to catch and display any startup/import errors.

[2026-08-30] VERSION 1.00 UPDATE
   - Initial Release.
================================================================================
"""

import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

# --- CONSOLE ENCODING FIX (Windows UTF-8 Safe Reconfigure) ---
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- DEPENDENCY CHECK ---
try:
    from internetarchive import get_item, get_session
except ImportError:
    print("[ERROR] The 'internetarchive' Python library is not installed.")
    print("Please install it by running: pip install internetarchive")
    sys.exit(1)

# --- CONSTANTS & CONFIGURATION ---
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 300
REMOVE_TAG = "REMOVE_TAG"

LICENSE_OPTIONS = {
    "1": ("GPLv3", "https://www.gnu.org/licenses/gpl-3.0.html"),
    "2": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/"),
    "3": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/"),
    "4": ("CC BY-ND 4.0", "https://creativecommons.org/licenses/by-nd/4.0/"),
    "5": ("CC BY-NC 4.0", "https://creativecommons.org/licenses/by-nc/4.0/"),
    "6": ("CC BY-NC-SA 4.0", "https://creativecommons.org/licenses/by-nc-sa/4.0/"),
    "7": ("CC BY-NC-ND 4.0", "https://creativecommons.org/licenses/by-nc-nd/4.0/"),
    "8": (
        "CC0 1.0 (Public Domain)",
        "https://creativecommons.org/publicdomain/zero/1.0/",
    ),
    "9": (
        "PDM 1.0 (Public Domain Mark)",
        "https://creativecommons.org/publicdomain/mark/1.0/",
    ),
    "0": ("Custom URL / None", None),
}

SYSTEM_IMMUTABLE_FIELDS = {
    "identifier",
    "mediatype",
    "addeddate",
    "publicdate",
    "uploader",
    "curation",
    "backup_location",
    "filesxml",
}

_skip_to_defaults = False


# --- HELPER FUNCTIONS ---


def sanitize_identifier(raw_identifier):
    """Normalize identifier and remove illegal characters."""
    import unicodedata

    norm = unicodedata.normalize("NFKD", raw_identifier)
    ascii_only = norm.encode("ascii", "ignore").decode("ascii")
    cleaned = ascii_only.replace(" ", "_")
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch in "._-")
    cleaned = cleaned.strip("._-")
    return cleaned[:100]


def format_val_for_display(val, max_len=60):
    """Format single string or list for table and prompt display."""
    if val is None:
        return "[None]"
    if val == REMOVE_TAG:
        return "[REMOVE / CLEAR]"
    if isinstance(val, list):
        display_str = "; ".join(str(x) for x in val)
    else:
        display_str = str(val).strip()

    display_str = display_str.replace("\n", " ").replace("\r", "")
    if len(display_str) > max_len:
        return display_str[: max_len - 3] + "..."
    return display_str


def get_account_collections(session):
    """Best-effort fetch of collections writable/available to the current account."""
    if not session:
        return []

    endpoints = [
        "https://archive.org/services/xauthn/?op=userinfo",
        "https://archive.org/services/xauthn/?op=account",
    ]

    for url in endpoints:
        try:
            resp = session.get(url, timeout=(10, 30))
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            continue

        collections = []
        if isinstance(data, dict):
            if isinstance(data.get("collections"), list):
                collections = data["collections"]
            elif isinstance(data.get("user"), dict) and isinstance(
                data["user"].get("collections"), list
            ):
                collections = data["user"]["collections"]

        out = []
        for c in collections:
            if isinstance(c, str) and c.strip():
                out.append(c.strip())
            elif isinstance(c, dict):
                val = c.get("identifier") or c.get("name")
                if isinstance(val, str) and val.strip():
                    out.append(val.strip())

        if out:
            return sorted(set(out))

    return []


# --- MULTI-LINE / EXTERNAL EDITOR HELPERS ---


def open_external_editor(initial_text=""):
    """Opens system text editor (Notepad on Windows, $EDITOR or nano on POSIX)."""
    suffix = ".txt"
    with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=suffix, delete=False) as tf:
        if initial_text and initial_text != REMOVE_TAG:
            tf.write(initial_text)
        temp_path = tf.name

    try:
        if sys.platform == "win32":
            subprocess.run(["notepad.exe", temp_path])
        else:
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, temp_path])

        with open(temp_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return content if content else None
    except Exception as e:
        print(f"  [!] Failed to launch external editor: {e}")
        return None
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def read_terminal_multiline():
    """Reads multiple lines until sentinel 'EOF', 'END', or Ctrl+Z / Ctrl+D."""
    print("\n  --- MULTI-LINE PASTE MODE ---")
    print("  Paste your text below.")
    print("  When finished, type 'EOF' on a new line and press Enter (or press Ctrl+Z then Enter):")
    print("  " + "-" * 60)

    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n  [!] Paste mode cancelled.")
            return None

        if line.strip().upper() in ["EOF", "END", "!EOF", "!END"]:
            break
        lines.append(line)

    result = "\n".join(lines).strip()
    print("  " + "-" * 60)
    print(f"  [+] Captured {len(lines)} line(s) / {len(result)} character(s).")
    return result if result else None


def get_multiline_input(prompt_text, default=None, allow_clear=True):
    """Special prompt for long/multi-paragraph fields like Description."""
    global _skip_to_defaults
    disp_default = format_val_for_display(default, max_len=55)

    if _skip_to_defaults:
        print(f"  {prompt_text} [{disp_default}]: (Kept default)")
        return default

    print(f"\n  {prompt_text}:")
    if default:
        print(f"    Current: \"{disp_default}\"")
    print("    Commands: [Enter] Keep current | [p] Paste mode | [e] Open in Notepad | [-] Clear")

    while True:
        try:
            choice = input("    Enter command or single-line text [Enter=keep]: ").strip()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if choice == "!!":
            _skip_to_defaults = True
            print("  >> Skipping to defaults. All remaining fields will keep their current values.")
            return default

        if allow_clear and choice in ["!clear", "!del", "-"]:
            print(f"  >> Marked '{prompt_text}' for REMOVAL.")
            return REMOVE_TAG

        if not choice:
            return default

        if choice.lower() in ["p", "!paste", "!p", "!m", "paste"]:
            pasted = read_terminal_multiline()
            return pasted if pasted is not None else default

        if choice.lower() in ["e", "!edit", "!e", "!notepad", "edit", "notepad"]:
            edited = open_external_editor(default or "")
            if edited is not None:
                print(f"  [+] Received {len(edited)} characters from Notepad.")
                return edited
            return default

        # User typed a single line directly
        return choice


# --- METADATA IMPORT & EXPORT PARSERS ---


def _xml_text(node):
    if node is None:
        return None
    text = (node.text or "").strip()
    return text if text else None


def load_metadata_xml(file_or_dir_path):
    """Load metadata from an XML file or directory containing metadata.xml / _meta.xml."""
    p = Path(file_or_dir_path)
    if p.is_dir():
        xml_path = p / "metadata.xml"
        if not xml_path.exists():
            xml_path = p / "_meta.xml"
    else:
        xml_path = p

    if not xml_path.exists():
        return None

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  [!] Error parsing XML '{xml_path}': {e}")
        return None

    data = {}
    subjects = []
    relations = []
    formats = []

    for child in root:
        tag = child.tag
        if tag.startswith("{"):
            continue
        val = _xml_text(child)
        if not val:
            continue

        tag_lower = tag.lower()
        if tag_lower in ["subject", "tag"]:
            subjects.append(val)
        elif tag_lower == "relation":
            relations.append(val)
        elif tag_lower == "format":
            formats.append(val)
        else:
            data[tag] = val

    if subjects:
        data["subject"] = subjects
    if relations:
        data["relation"] = relations
    if formats:
        data["format"] = formats

    return data or None


def load_metadata_json(file_or_dir_path):
    """Load metadata from a JSON file or directory containing metadata.json."""
    p = Path(file_or_dir_path)
    if p.is_dir():
        json_path = p / "metadata.json"
    else:
        json_path = p

    if not json_path.exists():
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [!] Error parsing JSON '{json_path}': {e}")
        return None

    if not isinstance(data, dict):
        return None
    if isinstance(data.get("metadata"), dict):
        data = data["metadata"]

    return data or None


def load_metadata_file(source_path):
    """Unified loader checking XML first, then JSON."""
    p = Path(source_path)
    if p.is_file():
        if p.suffix.lower() == ".xml":
            return load_metadata_xml(p)
        if p.suffix.lower() == ".json":
            return load_metadata_json(p)

    xml_res = load_metadata_xml(p)
    if xml_res:
        return xml_res
    return load_metadata_json(p)


def export_metadata(metadata, out_format="json", out_path=None, identifier=None):
    """Export metadata dictionary to JSON or XML file."""
    cleaned = {k: v for k, v in metadata.items() if not k.startswith("_")}

    if not out_path:
        stem = identifier or "metadata_export"
        out_path = f"{stem}.{out_format.lower()}"

    out_file = Path(out_path)

    if out_format.lower() == "xml":
        root = ET.Element("metadata")
        for k, v in cleaned.items():
            if isinstance(v, list):
                for item in v:
                    el = ET.SubElement(root, k)
                    el.text = str(item)
            else:
                el = ET.SubElement(root, k)
                el.text = str(v)

        xml_str = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(
            indent="  "
        )
        out_file.write_text(xml_str, encoding="utf-8")
    else:
        out_file.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"  [+] Metadata exported successfully to: {out_file.resolve()}")


# --- INTERACTIVE QUESTIONNAIRE ENGINE ---


def get_input(
    prompt_text,
    default=None,
    required=False,
    valid_options=None,
    allow_clear=True,
):
    global _skip_to_defaults
    disp_default = format_val_for_display(default)

    if _skip_to_defaults:
        print(f"  {prompt_text} [{disp_default}]: (Kept default)")
        return default

    while True:
        display = f"  {prompt_text} [{disp_default}]: " if default is not None else f"  {prompt_text}: "
        try:
            val = input(display).strip()
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            sys.exit(0)

        if val == "!!":
            _skip_to_defaults = True
            print("  >> Skipping to defaults. All remaining fields will keep their current values.")
            return default

        if allow_clear and val in ["!clear", "!del", "-"]:
            print(f"  >> Marked '{prompt_text}' for REMOVAL.")
            return REMOVE_TAG

        if not val and default is not None:
            return default

        if required and not val:
            print("    Error: This field is required.")
            continue

        if valid_options and val and val not in valid_options:
            print(f"    Error: Choose from {valid_options}")
            continue

        return val if val else None


def prompt_license(current_url=None):
    print("\n  --- LICENSE SELECTION ---")
    default_key = "0"
    if current_url:
        for k, (name, url) in LICENSE_OPTIONS.items():
            if url == current_url:
                default_key = k
                break

    for key, (name, url) in LICENSE_OPTIONS.items():
        curr_marker = " (current)" if key == default_key and current_url else ""
        print(f"    [{key}] {name}{curr_marker}")

    choice = get_input("Choose license option [0-9 or custom URL]", default=default_key)

    if choice == REMOVE_TAG:
        return REMOVE_TAG, REMOVE_TAG

    if choice in LICENSE_OPTIONS:
        selected_name, selected_url = LICENSE_OPTIONS[choice]
        if choice == "0":
            custom_url = get_input("Custom License URL", default=current_url)
            return custom_url, None
        return selected_url, selected_name

    return choice, None


def prompt_subjects(current_subjects):
    curr_str = ""
    if isinstance(current_subjects, list):
        curr_str = ", ".join(str(s) for s in current_subjects)
    elif isinstance(current_subjects, str):
        curr_str = current_subjects

    print(
        "  (Tip: Enter comma-separated tags, prefix with '+' to append (e.g. '+tag3'), or '-' to clear)"
    )
    val = get_input("Tags / Subjects", default=curr_str if curr_str else None)

    if val == REMOVE_TAG or val is None:
        return val

    if val.startswith("+"):
        raw_to_add = [t.strip().lstrip("+").strip() for t in val.split(",") if t.strip()]
        base_list = (
            list(current_subjects)
            if isinstance(current_subjects, list)
            else ([current_subjects] if current_subjects else [])
        )
        for item in raw_to_add:
            if item not in base_list:
                base_list.append(item)
        return base_list

    tags = [t.strip() for t in val.split(",") if t.strip()]
    return tags if tags else REMOVE_TAG


def collect_interactive_metadata(remote_meta, account_collections=None):
    global _skip_to_defaults
    _skip_to_defaults = False

    print("\n" + "=" * 60)
    print("INTERACTIVE METADATA EDITOR")
    print("=" * 60)
    print("Commands: [Enter] = Keep current value | '!!' = Keep all remaining defaults")
    print("          '!clear' or '-' = Delete field from remote item")
    print("-" * 60)

    staged = {}

    title = get_input("Title", default=remote_meta.get("title"), required=True)
    if title != remote_meta.get("title"):
        staged["title"] = title

    # Multi-line Description Prompt
    desc = get_multiline_input("Description", default=remote_meta.get("description"))
    if desc != remote_meta.get("description"):
        staged["description"] = desc

    creator = get_input("Creator", default=remote_meta.get("creator"))
    if creator != remote_meta.get("creator"):
        staged["creator"] = creator

    curr_sub = remote_meta.get("subject")
    new_sub = prompt_subjects(curr_sub)
    if new_sub != curr_sub:
        staged["subject"] = new_sub

    date = get_input("Date (YYYY, YYYY-MM, or YYYY-MM-DD)", default=remote_meta.get("date"))
    if date != remote_meta.get("date"):
        staged["date"] = date

    curr_license = remote_meta.get("licenseurl")
    new_license, matched_rights = prompt_license(curr_license)
    if new_license != curr_license:
        staged["licenseurl"] = new_license
        if matched_rights and not remote_meta.get("rights"):
            staged["rights"] = matched_rights

    rights = get_input(
        "Rights statement",
        default=staged.get("rights") or remote_meta.get("rights"),
    )
    if rights != remote_meta.get("rights"):
        staged["rights"] = rights

    if account_collections:
        print("\n  Available account collections:")
        print("    " + ", ".join(account_collections))
    collection = get_input("Collection", default=remote_meta.get("collection"))
    if collection != remote_meta.get("collection"):
        staged["collection"] = collection

    print("\n  --- EXTENDED METADATA (Optional) ---")
    extended_fields = [
        ("language", "Language (e.g. eng, en, zxx)"),
        ("publisher", "Publisher"),
        ("contributor", "Contributor"),
        ("source", "Source"),
        ("coverage", "Coverage"),
        ("temporal", "Temporal (Period/Range)"),
        ("spatial", "Spatial (Location/Country)"),
        ("citation", "Citation"),
        ("relation", "Relation (URLs / Related links)"),
        ("type", "Type"),
    ]

    for key, label in extended_fields:
        curr_val = remote_meta.get(key)
        new_val = get_input(label, default=curr_val)
        if new_val != curr_val:
            staged[key] = new_val

    print("\n  --- CUSTOM FIELDS ---")
    known_keys = {
        "title",
        "description",
        "creator",
        "subject",
        "date",
        "licenseurl",
        "rights",
        "collection",
        "language",
        "publisher",
        "contributor",
        "source",
        "coverage",
        "temporal",
        "spatial",
        "citation",
        "relation",
        "type",
    } | SYSTEM_IMMUTABLE_FIELDS

    remote_custom = {k: v for k, v in remote_meta.items() if k not in known_keys}
    if remote_custom:
        print("  Existing Custom Keys:")
        for k, v in remote_custom.items():
            new_custom_val = get_input(f"Custom: {k}", default=v)
            if new_custom_val != v:
                staged[k] = new_custom_val

    add_more = get_input("Add a new custom field? (y/n)", default="n")
    while add_more and add_more.lower() in ["y", "yes"]:
        c_key = get_input("  Field Name (key)")
        if c_key and c_key not in SYSTEM_IMMUTABLE_FIELDS:
            c_val = get_input(f"  Value for '{c_key}'")
            if c_val:
                staged[c_key] = c_val
        add_more = get_input("Add another custom field? (y/n)", default="n")

    return staged


# --- DIFF & AUDIT ENGINE ---


def build_diff(remote_meta, proposed_changes):
    diff_entries = []

    for key, new_val in proposed_changes.items():
        if key in SYSTEM_IMMUTABLE_FIELDS:
            continue

        old_val = remote_meta.get(key)

        if new_val == REMOVE_TAG:
            if old_val is not None:
                diff_entries.append({
                    "field": key,
                    "action": "REMOVE",
                    "old": old_val,
                    "new": "[REMOVED]",
                })
            continue

        if old_val is None:
            if new_val is not None and new_val != "":
                diff_entries.append({
                    "field": key,
                    "action": "ADD",
                    "old": "[None]",
                    "new": new_val,
                })
            continue

        if old_val != new_val:
            diff_entries.append({
                "field": key,
                "action": "UPDATE",
                "old": old_val,
                "new": new_val,
            })

    return diff_entries


def display_diff_table(diff_entries, identifier):
    print("\n" + "=" * 80)
    print(f"METADATA AUDIT / DIFF PLAN for item: '{identifier}'")
    print("=" * 80)

    if not diff_entries:
        print("  [i] No metadata changes detected. Remote metadata is already up to date.")
        print("=" * 80)
        return False

    header = f"{'ACTION':<10} | {'FIELD':<18} | {'OLD VALUE':<22} | {'NEW VALUE':<22}"
    print(header)
    print("-" * 80)

    for entry in diff_entries:
        action = f"[{entry['action']}]"
        field = entry["field"]
        old_display = format_val_for_display(entry["old"], max_len=22)
        new_display = format_val_for_display(entry["new"], max_len=22)

        print(f"{action:<10} | {field:<18} | {old_display:<22} | {new_display:<22}")

    print("=" * 80)
    return True


# --- APPLICATION LOGIC ---


def apply_metadata_changes(item, proposed_changes, dry_run=False):
    if dry_run:
        print("\n[DRY RUN] No changes were written to archive.org.")
        return True

    payload = {}
    for k, v in proposed_changes.items():
        if k in SYSTEM_IMMUTABLE_FIELDS:
            continue
        payload[k] = v

    if not payload:
        print("Nothing to apply.")
        return True

    print(f"\nSubmitting metadata changes to '{item.identifier}'...")
    try:
        r = item.modify_metadata(
            payload,
            request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
        )
        print(f"[SUCCESS] Metadata successfully updated on Internet Archive!")
        print(f"Item URL: https://archive.org/details/{item.identifier}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to modify metadata for '{item.identifier}': {e}")
        return False


def process_single_item(identifier, args, session, account_collections):
    clean_id = sanitize_identifier(identifier)
    print(f"\nFetching live metadata for item: '{clean_id}'...")

    try:
        item = get_item(
            clean_id,
            archive_session=session,
            request_kwargs={"timeout": (CONNECT_TIMEOUT, READ_TIMEOUT)},
        )
    except Exception as e:
        print(f"[ERROR] Network error while fetching item '{clean_id}': {e}")
        return False

    if not item.exists:
        print(f"[ERROR] Item '{clean_id}' does not exist on archive.org.")
        return False

    remote_meta = dict(item.metadata)

    if args.export:
        export_metadata(remote_meta, out_format=args.export, out_path=args.export_out, identifier=clean_id)
        if not (
            args.from_file
            or args.title
            or args.description
            or args.description_file
            or args.set
            or args.unset
            or args.interactive
        ):
            return True

    proposed_changes = {}

    if args.from_file:
        print(f"Loading metadata from file/folder: '{args.from_file}'...")
        imported = load_metadata_file(args.from_file)
        if not imported:
            print(f"[ERROR] Could not read valid metadata from: '{args.from_file}'")
            return False
        proposed_changes.update(imported)

    if args.title:
        proposed_changes["title"] = args.title

    # Description from direct CLI text or external file
    if args.description_file:
        desc_path = Path(args.description_file)
        if desc_path.exists():
            proposed_changes["description"] = desc_path.read_text(encoding="utf-8").strip()
            print(f"  [+] Loaded description from file: '{args.description_file}'")
        else:
            print(f"  [!] Description file not found: '{args.description_file}'")
    elif args.description:
        proposed_changes["description"] = args.description

    if args.creator:
        proposed_changes["creator"] = args.creator
    if args.date:
        proposed_changes["date"] = args.date
    if args.collection:
        proposed_changes["collection"] = args.collection
    if args.licenseurl:
        proposed_changes["licenseurl"] = args.licenseurl
    if args.rights:
        proposed_changes["rights"] = args.rights
    if args.language:
        proposed_changes["language"] = args.language

    if args.tags:
        proposed_changes["subject"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.add_tag:
        curr_tags = remote_meta.get("subject", [])
        if isinstance(curr_tags, str):
            curr_tags = [curr_tags]
        elif not isinstance(curr_tags, list):
            curr_tags = []
        new_tag_list = list(curr_tags)
        for t in args.add_tag:
            if t not in new_tag_list:
                new_tag_list.append(t)
        proposed_changes["subject"] = new_tag_list
    if args.del_tag:
        curr_tags = remote_meta.get("subject", [])
        if isinstance(curr_tags, str):
            curr_tags = [curr_tags]
        elif isinstance(curr_tags, list):
            new_tag_list = [t for t in curr_tags if t not in args.del_tag]
            proposed_changes["subject"] = new_tag_list if new_tag_list else REMOVE_TAG

    if args.set:
        for item_kv in args.set:
            if "=" in item_kv:
                k, v = item_kv.split("=", 1)
                proposed_changes[k.strip()] = v.strip()

    if args.unset:
        for k in args.unset:
            proposed_changes[k.strip()] = REMOVE_TAG

    is_direct_mode = bool(
        args.from_file
        or args.title
        or args.description
        or args.description_file
        or args.creator
        or args.date
        or args.collection
        or args.licenseurl
        or args.rights
        or args.language
        or args.tags
        or args.add_tag
        or args.del_tag
        or args.set
        or args.unset
    )

    if not is_direct_mode or args.interactive:
        interactive_staged = collect_interactive_metadata(remote_meta, account_collections)
        proposed_changes.update(interactive_staged)

    diff_entries = build_diff(remote_meta, proposed_changes)
    has_changes = display_diff_table(diff_entries, clean_id)

    if not has_changes:
        return True

    if not args.yes and not args.dry_run:
        try:
            confirm = input("\nApply these changes to archive.org? (y/n) [y]: ").strip().lower()
            if confirm and confirm not in ["y", "yes"]:
                print("Aborted by user. No changes were made.")
                return False
        except KeyboardInterrupt:
            print("\nAborted by user.")
            return False

    return apply_metadata_changes(item, proposed_changes, dry_run=args.dry_run)


# --- MAIN ENTRYPOINT ---


def main():
    parser = argparse.ArgumentParser(
        description="Internet Archive Smart Metadata Editor & Syncer (iametadata.py)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("identifier", nargs="?", help="Archive.org item identifier")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Force interactive questionnaire mode"
    )
    parser.add_argument(
        "-f", "--from-file", help="Import metadata from XML / JSON file or folder"
    )
    parser.add_argument(
        "--batch", help="Path to text file containing list of identifiers (one per line)"
    )
    parser.add_argument(
        "--export",
        choices=["json", "xml"],
        help="Export remote metadata to a local file (json or xml)",
    )
    parser.add_argument("--export-out", help="Custom output path for exported metadata file")
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="Preview diff without applying changes to IA"
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Auto-confirm all changes without prompting"
    )

    parser.add_argument("--title", help="Set item title")
    parser.add_argument("--description", help="Set item description string")
    parser.add_argument(
        "--description-file",
        "--desc-file",
        help="Load item description from a text or HTML file",
    )
    parser.add_argument("--creator", help="Set creator / author")
    parser.add_argument("--date", help="Set date (YYYY, YYYY-MM, or YYYY-MM-DD)")
    parser.add_argument("--collection", help="Set collection identifier")
    parser.add_argument("--licenseurl", help="Set license URL")
    parser.add_argument("--rights", help="Set rights statement")
    parser.add_argument("--language", help="Set language code (e.g. en, eng, zxx)")

    parser.add_argument("--tags", help="Replace all tags with comma-separated list")
    parser.add_argument(
        "--add-tag", action="append", help="Append a tag/subject (can be used multiple times)"
    )
    parser.add_argument(
        "--del-tag", action="append", help="Remove a tag/subject (can be used multiple times)"
    )

    parser.add_argument(
        "--set", action="append", help="Set custom key=value pair (can be used multiple times)"
    )
    parser.add_argument(
        "--unset", action="append", help="Delete a metadata key (can be used multiple times)"
    )

    args = parser.parse_args()

    print("--- Archive.org Smart Metadata Editor (iametadata v1.03) ---")

    # 0. Auth Check
    try:
        session = get_session()
        if not session.access_key:
            print("Error: Not authenticated. Please run 'ia configure' first.")
            sys.exit(1)
    except Exception as e:
        print(f"Error accessing session: {e}")
        sys.exit(1)

    account_collections = get_account_collections(session)

    # 1. Resolve Targets
    identifiers = []
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: Batch file '{args.batch}' not found.")
            sys.exit(1)
        with open(batch_path, "r", encoding="utf-8") as f:
            identifiers = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"Loaded {len(identifiers)} identifier(s) from batch file.")
    elif args.identifier:
        identifiers = [args.identifier]
    else:
        try:
            raw_id = input("\nEnter Archive.org Item Identifier: ").strip()
            if not raw_id:
                print("Error: Identifier is required.")
                sys.exit(1)
            identifiers = [raw_id]
        except KeyboardInterrupt:
            print("\nExiting.")
            sys.exit(0)

    # 2. Process Items
    success_count = 0
    fail_count = 0

    for idx, ident in enumerate(identifiers, start=1):
        if len(identifiers) > 1:
            print(f"\n>>> Processing Item {idx}/{len(identifiers)}: '{ident}'")

        ok = process_single_item(ident, args, session, account_collections)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    # 3. Summary
    if len(identifiers) > 1:
        print("\n" + "=" * 40)
        print("BATCH PROCESSING COMPLETE")
        print("=" * 40)
        print(f"Total Processed: {len(identifiers)}")
        print(f"Successful:      {success_count}")
        print(f"Failed / Skipped:{fail_count}")
        print("=" * 40)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[CRITICAL ERROR] {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)