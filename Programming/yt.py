"""
# Ultimate YouTube Batch Uploader & Manager

Desktop (Tkinter) tool for two workflows:
1. **Update mode**: bulk-edit existing YouTube videos (schedule, visibility, metadata).
2. **Upload mode**: upload local video files with optional metadata/subtitle matching.

---

## What This Script Does

- Authenticates with the YouTube Data API (OAuth installed app flow).
- Loads existing channel videos or videos from a specific playlist.
- Matches local JSON metadata and subtitle files to videos.
- Bulk updates titles/descriptions/tags/category/language/scheduling/privacy.
- Uploads local files with title, description, tags, and category as private videos.
- Previews upload requests without authentication or file movement in Dry Run.
- Optionally moves files after a successful upload.
- Provides guardrails (blank metadata-file skip, dry-run mode, log persistence).
- Preserves unspecified metadata during updates and rejects invalid or ambiguous sources.

---

## High-Level Architecture

### 1) Configuration and constants
- API scopes, file/folder names, upload patterns, limits, and language/category maps.

### 2) Logging
- Standard logger outputs to console and in-memory list.
- Optional "save log on exit" writes buffered logs to `yt_manager.log`.

### 3) Utility helpers
- Text normalization for matching; validation for approved metadata payloads.
- Strict JSON metadata reading with field-presence and source-shape checks.
- File moving helpers for uploaded/failed organization.

### 4) Data models
- `VideoData`: existing YouTube video + API metadata cache.
- `VideoEntry`: local file queued for upload + inferred metadata/subtitle.
- `UploadJobOptions`: immutable selection/options snapshot passed to the upload worker.

### 5) GUI controller (`MainApp`)
- Builds the interface, handles mode switching, filtering, selection, and actions.
- Spawns background threads for API-heavy operations.
- Keeps UI responsive while updating status bar text.

### 6) Processing engines
- `update_videos_on_youtube(...)`: applies updates in batch order.
- `upload_new_videos(...)`: uploads selected local files.

---

## End-to-End Flows

## Update Mode Flow
1. Authenticate.
2. Load existing videos (uploads playlist or custom playlist ID).
3. (Optional) Filter/select subset in tree view.
4. Set schedule/visibility/metadata options.
5. Click `PROCESS` to update selected videos.

Notes:
- Scheduling uses `First Publish + interval` sequence.
- Auto-set buttons:
  - `Auto-Regular`: anchor to latest scheduled regular video.
  - `Auto-Shorts`: anchor to latest scheduled short video.
- Shorts heuristic in this script:
  - vertical aspect ratio (`height > width`) and
  - duration `<= 180` seconds.

## Upload Mode Flow
1. Load local files matching video patterns.
2. Explicit main.json mappings take priority, then exact `<video-stem>-youtube.json`,
   then a unique legacy metadata match. Invalid exact files and tied matches block the item.
3. Select desired rows and execution options, then click `PROCESS`.
4. Dry Run previews the file, metadata source, sanitized tags, and request settings;
   no authentication, media upload, API insertion, or file movement occurs.
5. Actual uploads require authentication and insert the prepared title, description,
   tags, and category as private (optionally with `publishAt` if set).
6. Optional file moves into organized `uploaded/...` folders follow upload success.

---

## API Usage Summary

- `channels().list(...)`: channel info and uploads playlist ID.
- `playlistItems().list(...)`: enumerate video IDs in a playlist.
- `videos().list(...)`: fetch `snippet,status,fileDetails,contentDetails`.
- `videos().update(...)`: apply metadata/status changes.
- `videos().insert(...)`: resumable upload with `snippet.tags` in the initial request.

Key fields used:
- `status.publishAt`: schedule timestamp.
- `status.privacyStatus`: private/unlisted/public.
- `contentDetails.duration`: ISO-8601 duration (for short detection).
- `fileDetails.videoStreams`: width/height and source file hints.

---

## Section-by-Section Reference

### Logger and auth helpers
- `ListHandler`: stores formatted log lines in memory.
- `revoke_token`, `setup_revocation_on_exit`: cleanup token on exit/signals.
- `get_authenticated_service`: OAuth bootstrap + credential refresh + service build.

### Text and metadata sanitizers
- `normalize_for_matching`: normalize text for loose matching.
- `sanitize_for_youtube`: legacy filename/matching cleanup.
- `validate_title`: validates approved titles without truncating them.
- `sanitize_description`: validates the 5000 UTF-8 byte limit; rejects forbidden
  characters or oversized copy instead of truncating it.
- `assemble_description`: appends hashtags once, then validates the assembled bytes.
- `prepare_tags`: validates at most 15 unique tags, each 1-30 ASCII letters/numbers/spaces,
  and the platform budget including separators and space-related quoting overhead.
  The count, per-tag, and ASCII limits are local compatibility choices.
- `sanitize_tags`: explicit legacy cleanup with diagnostics for changed/dropped tags.
- `read_metadata_file`: strict JSON and sidecar-shape validation.
- `sanitize_and_parse_json`: retained tolerant parser for legacy GUI/import helpers.

### File movement and logs
- `generate_batch_id`: unique batch key.
- `safe_move_file`: collision-safe move helper.
- `move_uploaded_files`: move video/description/subtitles after upload.
- `save_upload_log`: save structured upload result JSON.

### Data model classes
- `VideoData`:
  - stores raw API payload fragments + current effective values.
  - parses ISO-8601 duration to seconds.
  - `is_likely_short()` for scheduling heuristics.
- `VideoEntry`:
  - represents local upload candidate.
  - resolves adjacent JSON metadata and subtitles; retains metadata errors for safe rejection.

### GUI class (`MainApp`)
- `build_gui`: constructs all widgets and binds callbacks.
- Scheduling helpers:
  - `_read_interval_delta`
  - `_get_latest_scheduled_dt`
  - `_auto_set_start_time`
  - `auto_set_start_time_regular`
  - `auto_set_start_time_shorts`
  - `auto_set_start_time` (backward-compatible fallback)
- Mode/UI handlers:
  - `_update_gui_for_mode`, `_update_ui_states`
  - `_populate_treeview`, `on_video_select_display_info`
  - filter + sorting helpers (`apply_filters`, `_sort_column`, etc.)
- Load/auth handlers:
  - `select_credentials_and_auth`, `load_channel_categories`
  - `gui_load_existing_videos`, `run_video_load`, `finish_video_load`
  - `gui_load_files_for_upload`
- Data fetch:
  - `fetch_all_videos_from_api` (playlist traversal + local file matching).
- Execution:
  - `start_processing_thread`, `run_update_processing`, `run_upload_processing`
  - `on_exit`

### Processing functions
- `update_videos_on_youtube(service, processing_data)`:
  - overlays explicitly supplied metadata on cached remote mutable snippet values.
  - absent fields preserve remote values; `tags: []` explicitly clears tags.
  - missing required preservation data or invalid metadata rejects that item.
  - applies scheduling/visibility/metadata options.
  - supports dry run and blank-file safety skip.
- `upload_new_videos(service, video_entries, skip_subtitles, move_files=True, *, dry_run=False, legacy_tag_cleanup=False)`:
  - validates supplied tags through the same helper used by metadata updates.
  - prepares one request body for both execution and preview.
  - Dry Run counts planned uploads separately from successful uploads; no video URL
    is reported for a preview. The full prepared body is available at DEBUG log level.
  - retains the resumable upload loop and optional post-success file movement.

---

## Safety Guards and Behaviors

- Blank metadata files (`.txt`/`.json`) are skipped.
- Invalid date input for scheduling aborts update run with log error.
- Network/API exceptions are logged; app continues where possible.
- Dry Run logs intended updates without calling `videos().update(...)` and previews
  uploads before `MediaFileUpload`, `videos().insert(...)`, or `next_chunk()`.
- Upload selections, skip-subtitle, move-files, and Dry Run options are captured on
  the GUI thread; the worker does not read Tk variables for these options.
- Sidecars contain only title, description, hashtags, and tags. Partial metadata is
  allowed; null, invalid field types, malformed JSON, and timing-export fields are rejected.
- Empty or unchanged GUI description/tag fields mean no override. Use an explicit
  empty array in source metadata to clear tags on an existing video.
- Untouched remote tags, including Unicode tags, retain their original values.
- Python callers can opt into lossy legacy tag cleanup with `legacy_tag_cleanup=True`
  for uploads or `processing_data['legacy_tag_cleanup'] = True` for updates. The GUI
  uses strict validation. Cleanup reports every changed or dropped value.

## Focused Regression Tests

Run `python -m unittest discover -s Programming/tests -p "test_yt*.py"`
from the repository root with the application dependencies installed. Tests capture
requests through a fake API client; they do not open the GUI or upload media.
Coverage includes uploads/Dry Run, partial-update preservation, deterministic matching,
invalid inputs, explicit legacy cleanup, and platform byte/character boundaries.

---

## Local Files and Folders Used

- `token.json`: OAuth credentials.
- `yt_manager.log`: optional saved runtime logs.
- `uploaded/`: successful upload archive.
- `failed_updates/`: failed update artifacts.

---

## Entry Point

- Script starts with:
  - `if __name__ == '__main__': MainApp()`
"""

import os
import sys
import json
import signal
import atexit
import re
import logging
import shutil
import glob
import math
import random
import threading
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timedelta, time, timezone
from dataclasses import dataclass

import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- Constants ---
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]
TOKEN_FILE = "token.json"
FAILED_UPDATES_FOLDER = "failed_updates"
UPLOADED_FOLDER = "uploaded"
UPLOADED_VIDEOS_SUBFOLDER = "videos"
UPLOADED_DESCRIPTIONS_SUBFOLDER = "descriptions"
UPLOADED_SUBTITLES_SUBFOLDER = "subtitles"
UPLOADED_THUMBNAILS_SUBFOLDER = "thumbnails"
UPLOADED_LOGS_SUBFOLDER = "logs"
LOG_FILE = "yt_manager.log"
OAUTH_PORT = 0
API_TIMEOUT_SECONDS = 60
VIDEO_PATTERNS = ["*.mp4", "*.mkv", "*.avi", "*.mov", "*.wmv"]
SUBTITLE_PATTERNS = ["*.srt", "*.sbv", "*.vtt", "*.scc", "*.ttml"]
METADATA_EXTENSIONS = {".json"}
THUMBNAIL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
YOUTUBE_THUMBNAIL_MAX_BYTES = 2 * 1024 * 1024
YOUTUBE_TAGS_MAX_LENGTH = 500
YOUTUBE_TAGS_MAX_COUNT = 15
YOUTUBE_TITLE_MAX_LENGTH = 100
YOUTUBE_DESCRIPTION_MAX_BYTES = 5000
LANGUAGES_MAP = {"Don't Change": None, "English": "en", "Spanish": "es", "French": "fr", "German": "de", "Japanese": "ja", "Chinese": "zh"}
STATIC_CATEGORY_MAP = {"Film & Animation": "1", "Autos & Vehicles": "2", "Music": "10", "Pets & Animals": "15", "Sports": "17", "Travel & Events": "19", "Gaming": "20", "People & Blogs": "22", "Comedy": "23", "Entertainment": "24", "News & Politics": "25", "Howto & Style": "26", "Education": "27", "Science & Technology": "28", "Nonprofits & Activism": "29"}

# --- Logger Setup ---
log_records = []
class ListHandler(logging.Handler):
    def emit(self, record): log_records.append(self.format(record))
logger = logging.getLogger("yt_manager"); logger.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout); console_handler.setFormatter(formatter)
    list_handler = ListHandler(); list_handler.setFormatter(formatter)
    logger.addHandler(console_handler); logger.addHandler(list_handler)

# --- Helper, Auth & Data Models ---
def extract_core_name(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r'^\d+[_\-]?', '', stem)
    stem = re.sub(r'[_\-]?[a-f0-9]{6,12}$', '', stem, flags=re.IGNORECASE)
    return normalize_for_matching(stem)

def revoke_token():
    if not os.path.exists(TOKEN_FILE): return
    logger.info("Revoking token on exit...")
    try:
        with open(TOKEN_FILE, 'r') as f: token_data = json.load(f)
        if token_data.get('refresh_token'):
            requests.post('https://oauth2.googleapis.com/revoke', params={'token': token_data['refresh_token']}, timeout=10)
    except Exception as e: logger.error(f"Token revocation failed: {e}")
    finally:
        try: os.remove(TOKEN_FILE)
        except OSError: pass

def setup_revocation_on_exit():
    atexit.register(revoke_token)
    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(1))
    signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))

def get_authenticated_service(secrets_path):
    creds = None
    if Path(TOKEN_FILE).exists():
        try: creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception: creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request(timeout=API_TIMEOUT_SECONDS))
            except Exception as e: logger.error(f"Token refresh failed: {e}"); creds = None
        if not creds:
            if not secrets_path or not Path(secrets_path).exists(): logger.error("Client secrets file missing."); return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=OAUTH_PORT, open_browser=True, timeout=900)
            except Exception as e:
                logger.error(f"OAuth local server flow failed: {e}. Falling back to console.")
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES); creds = flow.run_console()
        with open(TOKEN_FILE, 'w') as f: f.write(creds.to_json())
    return build('youtube', 'v3', credentials=creds, cache_discovery=False)

def normalize_for_matching(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', '_', text)
    return text.strip(' _')

def nuclear_clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\.[a-z0-9]{3,4}$', '', text, flags=re.IGNORECASE)
    return re.sub(r'[^a-z0-9]', '', text.lower())

def extract_marker_number(text: str):
    if not text:
        return None
    lowered = text.lower()
    m = re.search(r'\bmarker[\s_\-\(\)]*(\d{1,4})(?!\d)', lowered)
    if m:
        return int(m.group(1))
    m2 = re.search(r'\bmarker(\d{1,4})(?!\d)', lowered)
    if m2:
        return int(m2.group(1))
    return None

def has_eng_token(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r'\beng\b', text.lower()))

def extract_trailing_hash8(text: str):
    if not text:
        return None
    stem = re.sub(r'\.[a-z0-9]{2,4}$', '', str(text), flags=re.IGNORECASE)
    m = re.search(r'[_\-]([a-f0-9]{8})$', stem, flags=re.IGNORECASE)
    return m.group(1).lower() if m else None

def extract_title_from_metadata_file(path: Path) -> str | None:
    """Best-effort metadata title extraction for robust local/YouTube matching."""
    try:
        if path.suffix.lower() != ".json" or path.stat().st_size <= 0:
            return None
        content = path.read_text(encoding="utf-8", errors="replace")
        data = sanitize_and_parse_json(content)
        if isinstance(data, dict):
            title = data.get("title")
            if title:
                return str(title)
    except Exception:
        return None
    return None

def sanitize_for_youtube(text: str, max_len=None) -> str:
    sanitized = text.replace('<', '').replace('>', '')
    return sanitized[:max_len] if max_len else sanitized

def sanitize_description(desc: str) -> str:
    """Validate approved copy without truncating or rewriting it."""
    if not isinstance(desc, str):
        raise ValueError("Description must be a string.")
    if '<' in desc or '>' in desc or re.search(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', desc):
        raise ValueError("Description contains forbidden <, >, or control characters.")
    size = len(desc.encode('utf-8'))
    if size > YOUTUBE_DESCRIPTION_MAX_BYTES:
        raise ValueError(f"Description exceeds {YOUTUBE_DESCRIPTION_MAX_BYTES} UTF-8 bytes ({size}); correct the source instead of truncating it.")
    return desc


def validate_title(title):
    if not isinstance(title, str) or not title.strip() or len(title) > YOUTUBE_TITLE_MAX_LENGTH:
        raise ValueError(f"Title must be a nonempty string of at most {YOUTUBE_TITLE_MAX_LENGTH} characters.")
    if '<' in title or '>' in title or re.search(r'[\x00-\x1F\x7F]', title):
        raise ValueError("Title contains forbidden <, >, or control characters.")
    return title


def require_string_list(values, field):
    if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
        raise ValueError(f"{field} must be an array of strings; null is invalid.")
    return values


def effective_tag_length(tags):
    require_string_list(tags, 'Tags')
    return sum(len(tag) for tag in tags) + max(0, len(tags) - 1) + 2 * sum(' ' in tag for tag in tags)


def validate_tag_budget(tags):
    if effective_tag_length(tags) > YOUTUBE_TAGS_MAX_LENGTH:
        raise ValueError(f"Tags exceed the {YOUTUBE_TAGS_MAX_LENGTH}-character effective platform budget.")


def sanitize_tags(raw_tags, *, diagnostics=None):
    """Explicit legacy cleanup. Each discarded or changed value produces a diagnostic."""
    require_string_list(raw_tags, 'Tags')
    losses = []
    clean = []
    for index, raw in enumerate(raw_tags, 1):
        tag = re.sub(r'[\x00-\x1F\x7F]', '', raw.strip())
        tag = re.sub(r'[^A-Za-z0-9 ]+', '', tag)[:30].strip()
        if tag != raw:
            losses.append(f"Tag {index} changed by ASCII/whitespace cleanup or the 30-character limit: {raw!r} -> {tag!r}")
        if not tag:
            losses.append(f"Tag {index} dropped because it is empty after cleanup.")
        elif tag in clean:
            losses.append(f"Tag {index} dropped as a duplicate: {tag!r}")
        elif len(clean) >= YOUTUBE_TAGS_MAX_COUNT or effective_tag_length(clean + [tag]) > YOUTUBE_TAGS_MAX_LENGTH:
            losses.append(f"Tag {index} dropped because the tag count or platform budget is exhausted: {tag!r}")
        else:
            clean.append(tag)
    if diagnostics is not None:
        diagnostics.extend(losses)
    elif losses:
        logger.warning("Legacy tag cleanup: %s", '; '.join(losses))
    return clean


def prepare_tags(tags, *, legacy_cleanup=False):
    require_string_list(tags, 'Tags')
    if legacy_cleanup:
        return sanitize_tags(tags)
    if len(tags) > YOUTUBE_TAGS_MAX_COUNT:
        raise ValueError(f"Local policy allows at most {YOUTUBE_TAGS_MAX_COUNT} tags; no keywords were dropped.")
    for index, tag in enumerate(tags, 1):
        if not tag or tag != tag.strip() or len(tag) > 30 or not re.fullmatch(r'[A-Za-z0-9 ]+', tag):
            raise ValueError(f"Tag {index} violates local policy: use 1-30 ASCII letters/numbers/spaces with no outer whitespace; correct the source or explicitly enable legacy_tag_cleanup.")
    if len(set(tags)) != len(tags):
        raise ValueError("Duplicate tags are invalid; correct the source or explicitly enable legacy_tag_cleanup.")
    validate_tag_budget(tags)
    return list(tags)


def assemble_description(description, hashtags):
    require_string_list(hashtags, 'Hashtags')
    if any(not re.fullmatch(r'#[^\s#<>]+', tag) for tag in hashtags) or len(set(hashtags)) != len(hashtags):
        raise ValueError("Hashtags must be unique, nonempty #tokens without spaces or angle brackets.")
    if not isinstance(description, str):
        raise ValueError("Description must be a string.")
    body = description.strip()
    if hashtags:
        terminal = body.splitlines()[-1].split() if body else []
        if terminal != hashtags:
            if terminal and all(token.startswith('#') for token in terminal) and set(terminal) & set(hashtags):
                raise ValueError("Description has a conflicting terminal hashtag line; correct the source.")
            body = f"{body}\n\n{' '.join(hashtags)}".strip()
    return sanitize_description(body)

def sanitize_and_parse_json(content: str) -> dict | None:
    # Clean control characters first
    content_cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)
    try:
        # 1. Try direct loading (most reliable for valid, clean JSON files)
        return json.loads(content_cleaned, strict=False)
    except Exception:
        pass
    
    # 2. Fallback to bracket extractor if there is extra text before/after the JSON
    try:
        start_index = content_cleaned.find('{')
        if start_index == -1: return None
        brace_level, in_string, end_index = 1, False, -1
        for i in range(start_index + 1, len(content_cleaned)):
            char = content_cleaned[i]
            if char == '"' and content_cleaned[i-1] != '\\': in_string = not in_string
            if in_string: continue
            if char == '{': brace_level += 1
            elif char == '}': brace_level -= 1
            if brace_level == 0: end_index = i + 1; break
        if end_index == -1: return None
        json_str = content_cleaned[start_index:end_index]
        def escape_quotes(match): return match.group(1) + match.group(2).replace('"', '\\"') + match.group(3)
        json_str = re.sub(r'(".*?":\s*")(.*?)(")', escape_quotes, json_str, flags=re.DOTALL)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
        return json.loads(json_str, strict=False)
    except Exception:
        return None

ALLOWED_METADATA_FIELDS = {'title', 'description', 'hashtags', 'tags', 'filename', 'id', 'video_id'}

def validate_metadata_object(data):
    """Validate supplied fields without losing the distinction between absent and empty."""
    if not isinstance(data, dict) or not ({'title', 'description', 'hashtags', 'tags'} & data.keys()):
        raise ValueError("Metadata must be an object containing title, description, hashtags, or tags.")
    if 'filename' in data and not isinstance(data['filename'], str):
        raise ValueError("Metadata filename must be a string.")
    for field in ('title', 'description'):
        if field in data and not isinstance(data[field], str):
            raise ValueError(f"Metadata {field} must be a string.")
    for field in ('hashtags', 'tags'):
        if field in data and (not isinstance(data[field], list) or any(not isinstance(value, str) for value in data[field])):
            raise ValueError(f"Metadata {field} must be an array of strings; null is invalid.")
    return data


def read_metadata_file(path, *, allow_unrelated=False):
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if allow_unrelated and (not isinstance(data, dict) or not ({'title', 'description', 'hashtags', 'tags'} & data.keys())):
            return None
        if isinstance(data, dict):
            unexpected = data.keys() - ALLOWED_METADATA_FIELDS
            if unexpected:
                raise ValueError(f"Unexpected sidecar fields: {', '.join(sorted(unexpected))}; use only title, description, hashtags, and tags.")
        return validate_metadata_object(data)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{path}: {error}") from error


def unique_metadata_match(matches, label):
    if not matches:
        return None
    best_rank = min(rank for rank, value in matches)
    best = [value for rank, value in matches if rank == best_rank]
    if len(best) > 1:
        names = sorted(str(value.get('video_id') or value.get('id') or value.get('filename') or value.get('title') or '<unnamed entry>') if isinstance(value, dict) else str(value) for value in best)
        raise ValueError(f"Ambiguous {label}: {'; '.join(names)}")
    return best[0]


def match_main_json(items, *, filename=None, video_id=None, title=None):
    """Explicit IDs/filenames outrank normalized matches, regardless of list order."""
    matches = []
    filename = str(filename or '')
    names = {name for name in (filename, Path(filename).stem if filename else '', title) if name}
    normalized = {normalize_for_matching(name) for name in names} - {''}
    nuclear = {nuclear_clean(name) for name in names} - {''}
    for item in items or []:
        if not isinstance(item, dict):
            raise ValueError("Each main.json entry must be a metadata object.")
        item_id = item.get('video_id') or item.get('id')
        if video_id and item_id:
            if str(item_id) == str(video_id):
                matches.append((0, item))
            continue
        item_filename = item.get('filename', '')
        if not isinstance(item_filename, str):
            raise ValueError("main.json filename must be a string.")
        if item_filename and (item_filename in names or Path(item_filename).stem in names):
            matches.append((1, item))
        elif item_filename and normalize_for_matching(Path(item_filename).stem) in normalized:
            matches.append((2, item))
        elif item_filename and nuclear_clean(item_filename) in nuclear:
            matches.append((3, item))
        elif title and isinstance(item.get('title'), str) and normalize_for_matching(item['title']) in normalized:
            matches.append((4, item))
    match = unique_metadata_match(matches, f"main.json mapping for {video_id or filename}")
    return validate_metadata_object(match) if match is not None else None


def compatible_render_variant(source_stem, candidate_stem):
    pattern = r'(?:^|[\s_-])(top|bottom)(?=[\s_-]|$)'
    source = set(re.findall(pattern, source_stem.lower()))
    candidate = set(re.findall(pattern, candidate_stem.lower()))
    if source and candidate and source != candidate:
        return False
    orient_pattern = r'(?:^|[\s_-])(horz|horizontal|vert|vertical)(?=[\s_-]|$)'
    norm_orient = lambda s: {'horz' if t.startswith('hor') else 'vert' for t in re.findall(orient_pattern, s.lower())}
    src_orient = norm_orient(source_stem)
    cand_orient = norm_orient(candidate_stem)
    return not (src_orient and cand_orient and src_orient != cand_orient)


def find_upload_metadata(video_path):
    video_path = Path(video_path)
    exact = video_path.with_name(f"{video_path.stem}-youtube.json")
    if exact.is_file():
        if exact.stat().st_size:
            read_metadata_file(exact)  # An invalid exact sidecar blocks fallback matching.
        return exact
    matches = []
    nuclear = nuclear_clean(video_path.stem)
    marker = extract_marker_number(video_path.stem)
    for candidate in sorted(video_path.parent.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() not in METADATA_EXTENSIONS or candidate.name.lower() == 'main.json' or not candidate.stat().st_size:
            continue
        if not compatible_render_variant(video_path.stem, candidate.stem):
            continue
        candidate_nuclear = nuclear_clean(candidate.stem)
        score = None
        if nuclear and candidate_nuclear == nuclear:
            score = 0
        elif nuclear and candidate_nuclear and (nuclear in candidate_nuclear or candidate_nuclear in nuclear):
            score = 1
        elif marker is not None and extract_marker_number(candidate.stem) == marker:
            score = 1.5 if has_eng_token(video_path.stem) and has_eng_token(candidate.stem) else 2
        if score is not None:
            try:
                if read_metadata_file(candidate, allow_unrelated=True) is None:
                    continue
            except (ValueError, OSError):
                pass  # A malformed matching source must block the item, not become filename defaults.
            matches.append((score, candidate))
    match = unique_metadata_match(matches, f"metadata for {video_path.name}")
    if match is not None:
        read_metadata_file(match)
    return match


def prepare_update_snippet(video, options):
    """Overlay intentionally supplied fields on the last fetched mutable snippet."""
    if getattr(video, 'metadata_error', None):
        raise ValueError(video.metadata_error)
    fields = ('title', 'description', 'tags', 'categoryId', 'defaultLanguage', 'defaultAudioLanguage')
    snippet = {key: deepcopy(value) for key, value in video.video_snippet.items() if key in fields}
    data = {}
    if video.main_json_dict is not None:
        data = validate_metadata_object(video.main_json_dict)
    elif video.description_file_path:
        path = Path(video.description_file_path)
        data = {'description': path.read_text(encoding='utf-8')} if path.suffix.lower() == '.txt' else read_metadata_file(path)
    if 'title' in data:
        snippet['title'] = data['title']
    if 'description' in data:
        snippet['description'] = assemble_description(data['description'], data.get('hashtags', []))
    elif 'hashtags' in data:
        raise ValueError("Supply description together with hashtags so existing copy can be preserved.")
    if 'tags' in data:
        snippet['tags'] = prepare_tags(data['tags'], legacy_cleanup=options.get('legacy_tag_cleanup', False))
    description_override = options.get('description_override', '')
    if description_override.strip():
        snippet['description'] = description_override
    tags_override = options.get('tags_override', '')
    if tags_override.strip():
        tags = [value.strip() for value in tags_override.split(',') if value.strip()]
        if not tags:
            raise ValueError("Tags override must contain at least one tag; an empty field means no override.")
        snippet['tags'] = prepare_tags(tags, legacy_cleanup=options.get('legacy_tag_cleanup', False))
    if options.get('category_id'):
        snippet['categoryId'] = options['category_id']
    for required in ('title', 'categoryId'):
        if not snippet.get(required):
            raise ValueError(f"Cannot preserve {required}: required remote value is unavailable; reload the video or supply it explicitly.")
    validate_title(snippet['title'])
    if not isinstance(snippet['categoryId'], str):
        raise ValueError("Category ID must be a string.")
    if 'description' in snippet:
        sanitize_description(snippet['description'])
    if 'tags' in snippet:
        validate_tag_budget(snippet['tags'])
    return snippet


# File Management Functions
def generate_batch_id():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
    return f"batch_{timestamp}_{random_str}"

def safe_move_file(source_path, destination_path):
    source = Path(source_path)
    destination = Path(destination_path)
    if not source.exists(): return False
    counter = 1
    original_dest = destination
    while destination.exists():
        stem = original_dest.stem
        suffix = original_dest.suffix
        destination = original_dest.parent / f"{stem}_{counter}{suffix}"
        counter += 1
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        logger.info(f"Moved: {source.name} -> {destination.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to move {source.name}: {e}")
        return False

def move_uploaded_files(video_entry, batch_id, upload_success=True):
    moved_files = {}
    if upload_success:
        base_folder = UPLOADED_FOLDER
        batch_folder = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_{batch_id}"
        target_dir = Path(base_folder) / batch_folder
    else:
        target_dir = Path(FAILED_UPDATES_FOLDER) / batch_id
    
    (target_dir / UPLOADED_VIDEOS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    (target_dir / UPLOADED_DESCRIPTIONS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    (target_dir / UPLOADED_SUBTITLES_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    (target_dir / UPLOADED_THUMBNAILS_SUBFOLDER).mkdir(parents=True, exist_ok=True)
    
    video_src = Path(video_entry.filepath)
    video_dst = target_dir / UPLOADED_VIDEOS_SUBFOLDER / video_src.name
    if safe_move_file(video_src, video_dst):
        moved_files['video'] = (str(video_src), str(video_dst))
    
    if hasattr(video_entry, 'description_file_path') and video_entry.description_file_path:
        desc_src = Path(video_entry.description_file_path)
        desc_dst = target_dir / UPLOADED_DESCRIPTIONS_SUBFOLDER / desc_src.name
        if safe_move_file(desc_src, desc_dst): moved_files['description'] = (str(desc_src), str(desc_dst))
    
    if hasattr(video_entry, 'subtitle_path') and video_entry.subtitle_path:
        sub_src = Path(video_entry.subtitle_path)
        sub_dst = target_dir / UPLOADED_SUBTITLES_SUBFOLDER / sub_src.name
        if safe_move_file(sub_src, sub_dst): moved_files['subtitle'] = (str(sub_src), str(sub_dst))

    if hasattr(video_entry, 'thumbnail_path') and video_entry.thumbnail_path:
        thumb_src = Path(video_entry.thumbnail_path)
        thumb_dst = target_dir / UPLOADED_THUMBNAILS_SUBFOLDER / thumb_src.name
        if safe_move_file(thumb_src, thumb_dst): moved_files['thumbnail'] = (str(thumb_src), str(thumb_dst))
    
    return moved_files


def find_matching_thumbnail_for_stem(parent_dir: Path, stems: list[str]) -> Path | None:
    """Find a non-empty thumbnail file in parent_dir matching any candidate stem."""
    if not parent_dir.is_dir():
        return None
    ext_priority = {".jpg": 0, ".jpeg": 1, ".png": 2, ".webp": 3}
    candidates = [
        f for f in parent_dir.iterdir()
        if f.is_file() and f.suffix.lower() in THUMBNAIL_EXTENSIONS and f.stat().st_size > 0
    ]
    for stem in stems:
        if not stem:
            continue
        stem_lower = stem.lower()
        matching = [f for f in candidates if f.stem.lower() == stem_lower]
        if matching:
            matching.sort(key=lambda f: (ext_priority.get(f.suffix.lower(), 99), f.name.lower()))
            return matching[0]
    return None


def upload_video_thumbnail(service, video_id: str, thumb_path: str | Path, *, is_dry_run: bool = False) -> bool:
    """Validate size and upload a custom thumbnail image to YouTube via thumbnails.set."""
    p = Path(thumb_path)
    if not p.is_file() or p.stat().st_size == 0:
        logger.warning(f"Skipping thumbnail upload for {video_id}: '{p}' missing or empty.")
        return False
    file_size = p.stat().st_size
    if file_size > YOUTUBE_THUMBNAIL_MAX_BYTES:
        logger.error(f"Thumbnail '{p.name}' exceeds 2 MB limit ({file_size} bytes); skipping thumbnail upload.")
        return False
    if is_dry_run:
        logger.info(f"DRY RUN Thumbnail: video_id={video_id} <- '{p.name}'")
        return True
    media = MediaFileUpload(str(p), resumable=False)
    try:
        service.thumbnails().set(
            videoId=video_id,
            media_body=media,
        ).execute()
    finally:
        stream = media.stream() if hasattr(media, 'stream') else None
        if stream is not None and hasattr(stream, 'close'):
            stream.close()
    logger.info(f"Uploaded thumbnail '{p.name}' for video {video_id}.")
    return True

def save_upload_log(batch_id, upload_data):
    log_file = Path(UPLOADED_FOLDER) / UPLOADED_LOGS_SUBFOLDER / f"{batch_id}.json"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_data = {'batch_id': batch_id, 'upload_time': datetime.now().isoformat(), 'total_videos': len(upload_data), 'uploads': upload_data}
    try:
        with open(log_file, 'w', encoding='utf-8') as f: json.dump(log_data, f, indent=2)
    except Exception as e: logger.error(f"Failed to save upload log: {e}")

class VideoData:
    def __init__(self, video_id, video_title, video_snippet, video_status, video_file_details=None, video_content_details=None, video_statistics=None):
        self.video_id = video_id
        self.original_title = video_title 
        self.video_snippet = video_snippet or {}
        self.video_status = video_status or {}
        self.video_content_details = video_content_details or {}
        self.video_statistics = video_statistics or {}
        self.view_count = self.video_statistics.get('viewCount', '0')
        self.like_count = self.video_statistics.get('likeCount', '0')
        self.comment_count = self.video_statistics.get('commentCount', '0')
        self.upload_date = self.video_snippet.get('publishedAt', '')
        self.description_file_path, self.description_filename = None, "N/A"
        self.subtitle_file_path, self.subtitle_filename = None, "N/A"
        self.thumbnail_file_path, self.thumbnail_filename = None, "N/A"
        self.width, self.height = 0, 0
        self.original_upload_filename = None
        self.main_json_dict = None
        self.metadata_error = None
        if video_file_details:
            self.original_upload_filename = video_file_details.get('fileName')
            if 'videoStreams' in video_file_details and video_file_details['videoStreams']:
                stream = video_file_details['videoStreams'][0]
                self.width, self.height = stream.get('widthPixels', 0), stream.get('heightPixels', 0)
        self.current_title = self.video_snippet.get('title', self.original_title)
        self.current_description = self.video_snippet.get('description', '')
        self.current_tags = self.video_snippet.get('tags', [])
        self.current_category_id = self.video_snippet.get('categoryId', '24')
        self.current_video_language = self.video_snippet.get('defaultAudioLanguage', 'en')
        self.current_default_language = self.video_snippet.get('defaultLanguage', 'en')
        self.current_recording_date = (self.video_snippet.get('recordingDetails') or {}).get('recordingDate', '')
        self.current_made_for_kids = self.video_status.get('selfDeclaredMadeForKids')
        self.current_embeddable = self.video_status.get('embeddable', True)
        self.current_public_stats_viewable = self.video_status.get('publicStatsViewable', False)
        self.duration_seconds = self._parse_iso8601_duration_seconds(self.video_content_details.get('duration'))

    @staticmethod
    def _parse_iso8601_duration_seconds(duration_str):
        if not duration_str:
            return None
        # Supports common YouTube API formats like PT59S, PT1M2S, PT2H5M.
        match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return None
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def is_likely_short(self):
        is_vertical = self.height > self.width if self.width and self.height else False
        if self.duration_seconds is None:
            return is_vertical
        # Shorts eligibility now supports up to 3 minutes.
        return self.duration_seconds <= 180 and is_vertical

class VideoEntry:
    def __init__(self, filepath, main_json_data=None):
        p = Path(filepath); self.filepath = str(p); self.title = sanitize_for_youtube(p.stem, YOUTUBE_TITLE_MAX_LENGTH); self.description, self.description_source = "", "None"; self.subtitle_path, self.subtitle_source = None, "None"; self.thumbnail_path, self.thumbnail_source = None, "None"; self.tags = []; self.description_file_path = None
        self.metadata_error = None
        try:
            data = match_main_json(main_json_data, filename=p.name)
            if data is not None:
                self.description_source = "main.json"
            else:
                metadata_file = find_upload_metadata(p)
                if metadata_file:
                    self.description_source = metadata_file.name
                    self.description_file_path = str(metadata_file)
                    if metadata_file.stat().st_size:
                        data = read_metadata_file(metadata_file)
            if data is not None:
                self.title = data.get('title', self.title)
                self.description = assemble_description(data.get('description', ''), data.get('hashtags', []))
                self.tags = list(data.get('tags', []))
                logger.info("Loaded metadata from %s for '%s'.", self.description_source, p.name)
        except (ValueError, OSError) as error:
            self.metadata_error = str(error)
            logger.error("Metadata error for '%s': %s", p.name, error)
        try:
            for pattern in SUBTITLE_PATTERNS:
                found_subs = list(p.parent.glob(f"{p.stem}*.srt"))
                if found_subs: sub_file = found_subs[0]; logger.info(f"Found matching subtitle file '{sub_file.name}' for video '{p.name}'."); self.subtitle_path = str(sub_file); self.subtitle_source = sub_file.name; break
        except Exception as e: logger.error(f"Error searching for subtitle file for '{p.name}': {e}")
        try:
            candidate_stems = [p.stem]
            if self.description_file_path:
                candidate_stems.append(Path(self.description_file_path).stem)
            thumb_file = find_matching_thumbnail_for_stem(p.parent, candidate_stems)
            if thumb_file:
                logger.info(f"Found matching thumbnail file '{thumb_file.name}' for video '{p.name}'.")
                self.thumbnail_path = str(thumb_file)
                self.thumbnail_source = thumb_file.name
        except Exception as e:
            logger.error(f"Error searching for thumbnail file for '{p.name}': {e}")
        self.categoryId = '24'; self.videoLanguage = 'en'; self.defaultLanguage = 'en'; self.recordingDate = None; self.notifySubscribers = False; self.madeForKids = False; self.embeddable = True; self.publicStatsViewable = False; self.playlistId = ''; self.publishAt = None


@dataclass(frozen=True)
class UploadJobOptions:
    """Selection and execution options captured on the GUI thread."""

    video_entries: tuple[VideoEntry, ...]
    skip_subtitles: bool
    move_files: bool = True
    dry_run: bool = False
    upload_thumbnails: bool = False


def calculate_default_start_time():
    now = datetime.now(); minimum_time = now + timedelta(hours=1); midnight_today = datetime.combine(now.date(), time()); minutes_from_midnight_to_minimum = (minimum_time - midnight_today).total_seconds() / 60; interval_minutes = 144; num_intervals = math.ceil(minutes_from_midnight_to_minimum / interval_minutes); scheduled_time = midnight_today + timedelta(minutes=num_intervals * interval_minutes)
    return scheduled_time.strftime('%Y-%m-%d %H:%M')

class MainApp:
    def __init__(self):
        self.service = None; self.videos_to_process = []; self.dynamic_category_map = {}; self.app_mode = "update"; self.main_json_data = None
        self.root = tk.Tk(); setup_revocation_on_exit(); self.root.title('Ultimate YouTube Batch Uploader & Manager 1.7')
        self.build_gui(); self.root.protocol("WM_DELETE_WINDOW", self.on_exit); self._update_gui_for_mode(); self.root.mainloop()
    
    def build_gui(self):
        frm = ttk.Frame(self.root, padding=10); frm.pack(fill=tk.BOTH, expand=True)
        top_frame = ttk.Frame(frm); top_frame.pack(fill=tk.X, pady=5)
        self.select_cred_button = ttk.Button(top_frame, text='1. Select client_secrets.json & Authenticate', command=self.select_credentials_and_auth)
        self.select_cred_button.pack(side=tk.TOP, fill=tk.X, expand=True, padx=(0, 5), pady=(0, 2))
        self.load_main_json_button = ttk.Button(top_frame, text='Load Main JSON Data (Optional)', command=self.gui_load_main_json)
        self.load_main_json_button.pack(side=tk.TOP, fill=tk.X, expand=True, padx=(0, 5))

        load_frame = ttk.Frame(frm); load_frame.pack(fill=tk.X, pady=5)
        self.load_existing_button = ttk.Button(load_frame, text='2. Load Existing Videos', command=self.gui_load_existing_videos, state=tk.DISABLED)
        self.load_existing_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Label(load_frame, text='From Playlist ID:').pack(side=tk.LEFT, padx=(10, 2))
        self.playlist_id_entry_var = tk.StringVar()
        playlist_id_entry = ttk.Entry(load_frame, textvariable=self.playlist_id_entry_var, width=25)
        playlist_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Label(load_frame, text='Mode:').pack(side=tk.LEFT, padx=(10, 2))
        self.playlist_load_mode_var = tk.StringVar(value='Playlist Only')
        playlist_load_mode_cb = ttk.Combobox(load_frame, textvariable=self.playlist_load_mode_var, values=['Playlist Only', 'Uploads + Playlist'], state="readonly", width=16)
        playlist_load_mode_cb.pack(side=tk.LEFT, padx=(0, 5))
        
        self.load_for_upload_button = ttk.Button(load_frame, text='OR: Load Files for Upload', command=self.gui_load_files_for_upload, state=tk.NORMAL)
        self.load_for_upload_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Label(load_frame, text='Max to Load:').pack(side=tk.LEFT, padx=(10, 2))
        self.max_videos_var = tk.StringVar(value='100')
        ttk.Spinbox(load_frame, from_=0, to=10000, width=5, textvariable=self.max_videos_var).pack(side=tk.LEFT, padx=(0, 5))

        list_lf = ttk.LabelFrame(frm, text="Video List", padding=5); list_lf.pack(fill=tk.BOTH, expand=True, pady=5)
        tree_frame = ttk.Frame(list_lf); tree_frame.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=('id_or_path', 'title', 'views', 'likes', 'comments', 'desc_file', 'sub_file', 'thumb_file', 'status', 'publish_at', 'upload_date'), show='headings', selectmode="extended")
        for col in self.tree['columns']: self.tree.heading(col, command=lambda c=col: self._sort_column(c, False))
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=vsb.set); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); vsb.pack(side=tk.RIGHT, fill=tk.Y); self.tree.bind('<<TreeviewSelect>>', self.on_video_select_display_info)

        list_controls = ttk.Frame(list_lf); list_controls.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(list_controls, text="Search:").pack(side=tk.LEFT, padx=(0, 2))
        self.search_var = tk.StringVar(); self.search_var.trace_add("write", lambda *args: self.apply_filters())
        self.search_entry = ttk.Entry(list_controls, textvariable=self.search_var, width=20); self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.filter_menubutton = ttk.Menubutton(list_controls, text="Filter by...", state=tk.DISABLED); self.filter_menubutton.pack(side=tk.LEFT, padx=(0, 10)); self.filter_menu = tk.Menu(self.filter_menubutton, tearoff=0); self.filter_menubutton["menu"] = self.filter_menu; self.filter_vars = {k: tk.BooleanVar() for k in ["public", "not_public", "private", "not_private", "unlisted", "not_unlisted", "has_schedule", "no_schedule", "has_main_json", "no_main_json", "has_desc_file", "no_desc_file", "has_sub_file", "no_sub_file", "has_thumb_file", "no_thumb_file", "is_horizontal", "is_vertical"]}; self.filter_menu.add_checkbutton(label="Public", variable=self.filter_vars["public"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Public", variable=self.filter_vars["not_public"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Private", variable=self.filter_vars["private"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Private", variable=self.filter_vars["not_private"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Unlisted", variable=self.filter_vars["unlisted"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Unlisted", variable=self.filter_vars["not_unlisted"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Schedule", variable=self.filter_vars["has_schedule"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Not Scheduled", variable=self.filter_vars["no_schedule"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Main JSON Match", variable=self.filter_vars["has_main_json"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Main JSON Match", variable=self.filter_vars["no_main_json"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Description File", variable=self.filter_vars["has_desc_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Description File", variable=self.filter_vars["no_desc_file"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Subtitle File", variable=self.filter_vars["has_sub_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Subtitle File", variable=self.filter_vars["no_sub_file"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Has Thumbnail File", variable=self.filter_vars["has_thumb_file"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="No Thumbnail File", variable=self.filter_vars["no_thumb_file"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_checkbutton(label="Horizontal Video", variable=self.filter_vars["is_horizontal"], command=self.apply_filters); self.filter_menu.add_checkbutton(label="Vertical Video", variable=self.filter_vars["is_vertical"], command=self.apply_filters); self.filter_menu.add_separator(); self.filter_menu.add_command(label="Clear All Filters", command=self.clear_filters)
        ttk.Button(list_controls, text='Select All Visible', command=lambda: self.tree.selection_set(self.tree.get_children())).pack(side=tk.LEFT, padx=2); ttk.Button(list_controls, text='Select Main JSON', command=self.select_main_json_matches).pack(side=tk.LEFT, padx=2); ttk.Button(list_controls, text='Deselect All', command=lambda: self.tree.selection_remove(self.tree.selection())).pack(side=tk.LEFT, padx=2); ttk.Button(list_controls, text='Export Data', command=self.export_data).pack(side=tk.RIGHT, padx=2)

        bottom_frame = ttk.Frame(frm); bottom_frame.pack(fill=tk.X, pady=5)
        sched = ttk.LabelFrame(bottom_frame, text='Scheduling & Visibility', padding=10); sched.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        meta = ttk.LabelFrame(bottom_frame, text='Metadata', padding=10); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(sched, text='First Publish:').grid(row=0, column=0, sticky='w')
        self.start_ent = ttk.Entry(sched, width=20)
        self.start_ent.insert(0, calculate_default_start_time())
        self.start_ent.grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Button(sched, text="Auto-Regular", width=12, command=self.auto_set_start_time_regular).grid(row=0, column=2, sticky='w', padx=2)
        ttk.Button(sched, text="Auto-Shorts", width=12, command=self.auto_set_start_time_shorts).grid(row=0, column=3, sticky='w', padx=2)

        ttk.Label(sched, text='Interval Hours:').grid(row=1, column=0, sticky='w')
        self.interval_hour_var = tk.StringVar(value='2')
        ttk.Spinbox(sched, from_=0, to=1000, width=5, textvariable=self.interval_hour_var).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        ttk.Label(sched, text='Interval Mins:').grid(row=2, column=0, sticky='w')
        self.interval_minute_var = tk.StringVar(value='24')
        ttk.Spinbox(sched, from_=0, to=59, width=5, textvariable=self.interval_minute_var).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        
        ttk.Separator(sched, orient='horizontal').grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
        def _on_update_toggle():
            if getattr(self, 'update_schedule_var', None) and self.update_schedule_var.get(): self.remove_schedule_var.set(False)
            self._update_ui_states()
        def _on_remove_toggle():
            if getattr(self, 'remove_schedule_var', None) and self.remove_schedule_var.get(): self.update_schedule_var.set(False)
            self._update_ui_states()
        def _on_vis_toggle():
            if getattr(self, 'update_visibility_var', None) and self.update_visibility_var.get() and getattr(self, 'update_schedule_var', None) and self.update_schedule_var.get():
                self.update_schedule_var.set(False)
            self._update_ui_states()
        def _on_vis_radio_select():
            if getattr(self, 'update_schedule_var', None) and self.update_schedule_var.get():
                self.update_schedule_var.set(False)
            self.update_visibility_var.set(True)
            self._update_ui_states()
        self.update_schedule_var = tk.BooleanVar(value=True); ttk.Checkbutton(sched, text="Update Schedule", variable=self.update_schedule_var, command=_on_update_toggle).grid(row=4, column=0, sticky='w')
        self.remove_schedule_var = tk.BooleanVar(value=False); ttk.Checkbutton(sched, text="Remove Schedule", variable=self.remove_schedule_var, command=_on_remove_toggle).grid(row=4, column=1, sticky='w')
        self.update_visibility_var = tk.BooleanVar(value=False); self.vis_cb = ttk.Checkbutton(sched, text="Update Visibility Status", variable=self.update_visibility_var, command=_on_vis_toggle); self.vis_cb.grid(row=5, column=0, columnspan=2, sticky='w')
        self.visibility_choice_var = tk.StringVar(value='private'); self.rad_private = ttk.Radiobutton(sched, text="Private", variable=self.visibility_choice_var, value='private', command=_on_vis_radio_select); self.rad_private.grid(row=6, column=0, columnspan=2, sticky='w', padx=10); self.rad_unlisted = ttk.Radiobutton(sched, text="Unlisted", variable=self.visibility_choice_var, value='unlisted', command=_on_vis_radio_select); self.rad_unlisted.grid(row=7, column=0, columnspan=2, sticky='w', padx=10); self.rad_public = ttk.Radiobutton(sched, text="Public", variable=self.visibility_choice_var, value='public', command=_on_vis_radio_select); self.rad_public.grid(row=8, column=0, columnspan=2, sticky='w', padx=10)
        ttk.Label(sched, text='Schedule Order:').grid(row=9, column=0, sticky='w', pady=(5,0))
        self.schedule_order_var = tk.StringVar(value='Random')
        self.schedule_order_cb = ttk.Combobox(sched, textvariable=self.schedule_order_var, values=['As is', 'File Name (Asc)', 'File Name (Desc)', 'Random'], state="readonly", width=15)
        self.schedule_order_cb.grid(row=9, column=1, sticky='w', padx=5, pady=(5,0), columnspan=3)

        self.update_metadata_var = tk.BooleanVar(value=True)
        self.update_metadata_cb = ttk.Checkbutton(meta, text="Update Metadata (Title / Desc / Tags / Settings) — uncheck for Visibility/Schedule only", variable=self.update_metadata_var, command=self._on_update_metadata_toggle)
        self.update_metadata_cb.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 6))

        ttk.Label(meta, text='Description:').grid(row=1, column=0, sticky='nw'); self.desc_txt = tk.Text(meta, height=3, width=40, wrap=tk.WORD); self.desc_txt.grid(row=1, column=1, sticky='ew', columnspan=3)
        ttk.Label(meta, text='Tags (comma-sep):').grid(row=2, column=0, sticky='w', pady=(5,0)); self.tags_ent = ttk.Entry(meta); self.tags_ent.grid(row=2, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Video Category:').grid(row=3, column=0, sticky='w', pady=(5,0)); self.category_var = tk.StringVar(); self.category_cb = ttk.Combobox(meta, textvariable=self.category_var, values=["Don't Change"], state="readonly"); self.category_cb.set("Don't Change"); self.category_cb.grid(row=3, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Metadata Lang:').grid(row=4, column=0, sticky='w', pady=(5,0)); self.metadata_lang_var = tk.StringVar(); self.metadata_lang_cb = ttk.Combobox(meta, textvariable=self.metadata_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.metadata_lang_cb.set('English'); self.metadata_lang_cb.grid(row=4, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Audio Language:').grid(row=5, column=0, sticky='w', pady=(5,0)); self.audio_lang_var = tk.StringVar(); self.audio_lang_cb = ttk.Combobox(meta, textvariable=self.audio_lang_var, values=list(LANGUAGES_MAP.keys()), state="readonly"); self.audio_lang_cb.set('English'); self.audio_lang_cb.grid(row=5, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Recording Date (YYYY-MM-DD):').grid(row=6, column=0, sticky='w', pady=(5,0)); self.recording_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d')); self.recording_date_ent = ttk.Entry(meta, textvariable=self.recording_date_var); self.recording_date_ent.grid(row=6, column=1, sticky='ew', pady=(5,0), columnspan=3)
        ttk.Label(meta, text='Playlist ID:').grid(row=7, column=0, sticky='w', pady=(5,0)); self.playlist_id_var = tk.StringVar(); self.playlist_id_ent = ttk.Entry(meta, textvariable=self.playlist_id_var); self.playlist_id_ent.grid(row=7, column=1, sticky='ew', pady=(5,0), columnspan=3)
        option_frame = ttk.Frame(meta); option_frame.grid(row=8, column=0, columnspan=4, sticky='w', pady=(5,0)); self.allow_embedding_var = tk.BooleanVar(value=True); self.allow_embedding_cb = ttk.Checkbutton(option_frame, text="Allow Embedding", variable=self.allow_embedding_var); self.allow_embedding_cb.pack(side=tk.LEFT, padx=(0,10)); self.notify_subscribers_var = tk.BooleanVar(value=False); self.notify_subscribers_cb = ttk.Checkbutton(option_frame, text="Notify Subscribers (on public)", variable=self.notify_subscribers_var); self.notify_subscribers_cb.pack(side=tk.LEFT, padx=(0,10)); self.public_stats_var = tk.BooleanVar(value=False); self.public_stats_cb = ttk.Checkbutton(option_frame, text="Public Stats Visible", variable=self.public_stats_var); self.public_stats_cb.pack(side=tk.LEFT)
        ttk.Label(meta, text='Made for Kids:').grid(row=9, column=0, sticky='w', pady=(5,0)); self.made_for_kids_var = tk.StringVar(value='no'); mfk_frame = ttk.Frame(meta); mfk_frame.grid(row=9, column=1, sticky='ew', pady=(5,0), columnspan=3); self.mfk_no_rb = ttk.Radiobutton(mfk_frame, text="No", variable=self.made_for_kids_var, value='no'); self.mfk_no_rb.pack(side=tk.LEFT, padx=(0, 10)); self.mfk_yes_rb = ttk.Radiobutton(mfk_frame, text="Yes", variable=self.made_for_kids_var, value='yes'); self.mfk_yes_rb.pack(side=tk.LEFT, padx=(0, 10)); self.mfk_dc_rb = ttk.Radiobutton(mfk_frame, text="Don't Change", variable=self.made_for_kids_var, value='dont_change'); self.mfk_dc_rb.pack(side=tk.LEFT); meta.grid_columnconfigure(1, weight=1)

        action_frame = ttk.LabelFrame(frm, text="Execution", padding=10)
        action_frame.pack(fill=tk.X, pady=5)
        self.dry_run_var = tk.BooleanVar(value=False)
        dry_run_cb = ttk.Checkbutton(action_frame, text="Dry Run (Test Mode)", variable=self.dry_run_var)
        dry_run_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.skip_subs_var = tk.BooleanVar(value=True)
        skip_subs_cb = ttk.Checkbutton(action_frame, text="Skip Subtitle Uploads", variable=self.skip_subs_var)
        skip_subs_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.upload_thumbnails_var = tk.BooleanVar(value=False)
        upload_thumbs_cb = ttk.Checkbutton(action_frame, text="Upload Matched Thumbnails", variable=self.upload_thumbnails_var)
        upload_thumbs_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.move_files_var = tk.BooleanVar(value=True)
        move_files_cb = ttk.Checkbutton(action_frame, text="Move files to 'uploaded' folder after success", variable=self.move_files_var)
        move_files_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.save_log_var = tk.BooleanVar(value=False)
        save_log_cb = ttk.Checkbutton(action_frame, text="Save log on exit", variable=self.save_log_var)
        save_log_cb.pack(side=tk.LEFT)
        
        self.process_button = ttk.Button(frm, text='PROCESS', command=self.start_processing_thread, state=tk.DISABLED); self.process_button.pack(fill=tk.X, ipady=8, pady=(5, 0)); self.status_bar = ttk.Label(frm, text="Welcome! Authenticate to load existing videos.", relief=tk.SUNKEN, anchor='w'); self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def export_data(self):
        if not self.tree.get_children():
            messagebox.showinfo("No Data", "There is no data to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Data"
        )
        if not file_path:
            return
            
        import csv
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
                writer.writerow(headers)
                for item_id in self.tree.get_children():
                    row_data = self.tree.item(item_id)['values']
                    writer.writerow(row_data)
            messagebox.showinfo("Export Successful", f"Data successfully exported to:\n{file_path}")
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            messagebox.showerror("Export Failed", f"An error occurred while exporting data:\n{e}")

    def _read_interval_delta(self):
        try: hours = int(self.interval_hour_var.get()); mins = int(self.interval_minute_var.get())
        except ValueError: hours, mins = 2, 24
        return timedelta(hours=hours, minutes=mins)

    def _get_latest_scheduled_dt(self, filter_type="all"):
        latest_scheduled_dt = None
        if self.app_mode != "update":
            return None

        for vd in self.videos_to_process:
            if not isinstance(vd, VideoData):
                continue

            if filter_type == "regular" and vd.is_likely_short():
                continue
            if filter_type == "shorts" and not vd.is_likely_short():
                continue

            raw_time = vd.video_status.get('publishAt')
            if not raw_time:
                continue
            try:
                dt = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                if latest_scheduled_dt is None or dt > latest_scheduled_dt:
                    latest_scheduled_dt = dt
            except ValueError:
                pass
        return latest_scheduled_dt

    def _auto_set_start_time(self, filter_type="all", label="selected videos"):
        interval_delta = self._read_interval_delta()
        latest_scheduled_dt = self._get_latest_scheduled_dt(filter_type=filter_type)

        if latest_scheduled_dt:
            new_start_time = latest_scheduled_dt.astimezone() + interval_delta
            self.update_status(f"Found latest schedule for {label}. Setting start to {new_start_time.strftime('%Y-%m-%d %H:%M')}")
        else:
            new_start_time = datetime.now() + interval_delta
            self.update_status(f"No previous schedule found for {label}. Setting start to Now + Interval.")

        self.start_ent.delete(0, tk.END)
        self.start_ent.insert(0, new_start_time.strftime('%Y-%m-%d %H:%M'))

    def auto_set_start_time_regular(self):
        self._auto_set_start_time(filter_type="regular", label="regular videos")

    def auto_set_start_time_shorts(self):
        self._auto_set_start_time(filter_type="shorts", label="short videos")

    def auto_set_start_time(self):
        # Backward-compatible fallback if any older code path still calls this.
        interval_delta = self._read_interval_delta(); latest_scheduled_dt = None
        if self.app_mode == "update":
            for vd in self.videos_to_process:
                if isinstance(vd, VideoData):
                    raw_time = vd.video_status.get('publishAt')
                    if raw_time:
                        try:
                            dt = datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                            if latest_scheduled_dt is None or dt > latest_scheduled_dt: latest_scheduled_dt = dt
                        except ValueError: pass
        if latest_scheduled_dt: new_start_time = latest_scheduled_dt.astimezone() + interval_delta; self.update_status(f"Found schedule. Setting start to {new_start_time.strftime('%Y-%m-%d %H:%M')}")
        else: new_start_time = datetime.now() + interval_delta; self.update_status(f"No previous schedule found. Setting start to Now + Interval.")
        self.start_ent.delete(0, tk.END); self.start_ent.insert(0, new_start_time.strftime('%Y-%m-%d %H:%M'))

    def _update_gui_for_mode(self):
        self.tree.delete(*self.tree.get_children())
        if self.app_mode == "update":
            self.filter_menubutton.config(state=tk.NORMAL); self.process_button.config(text="PROCESS SELECTED VIDEOS"); self.tree.heading('id_or_path', text='Video ID'); self.tree.heading('title', text='Title'); self.tree.heading('views', text='Views'); self.tree.column('views', width=60); self.tree.heading('likes', text='Likes'); self.tree.column('likes', width=60); self.tree.heading('comments', text='Comments'); self.tree.column('comments', width=70); self.tree.heading('desc_file', text='Description File'); self.tree.heading('sub_file', text='Subtitle File'); self.tree.heading('thumb_file', text='Thumbnail File'); self.tree.heading('status', text='Privacy'); self.tree.heading('publish_at', text='Publish At (UTC)'); self.tree.heading('upload_date', text='Upload Date (UTC)'); self.tree.column('upload_date', width=150); self.vis_cb.config(state=tk.NORMAL); self.rad_private.config(state=tk.NORMAL); self.rad_unlisted.config(state=tk.NORMAL); self.rad_public.config(state=tk.NORMAL)
            self.update_status("UPDATE MODE: Load existing videos or select from list.")
        elif self.app_mode == "upload":
            self.clear_filters(); self.filter_menubutton.config(state=tk.DISABLED); self.process_button.config(text="UPLOAD SELECTED FILES"); self.tree.heading('id_or_path', text='File Path'); self.tree.heading('title', text='Title'); self.tree.heading('views', text=''); self.tree.heading('likes', text=''); self.tree.heading('comments', text=''); self.tree.heading('desc_file', text='Description Source'); self.tree.heading('sub_file', text=''); self.tree.heading('thumb_file', text='Thumbnail Source'); self.tree.heading('status', text=''); self.tree.heading('publish_at', text=''); self.tree.heading('upload_date', text='Subtitle Source'); self.tree.column('upload_date', width=120)
            self.vis_cb.config(state=tk.DISABLED); self.rad_private.config(state=tk.DISABLED); self.rad_unlisted.config(state=tk.DISABLED); self.rad_public.config(state=tk.DISABLED)
            self.update_status("UPLOAD MODE: Load local files or select from list to upload.")
        self._update_ui_states()
    
    def _on_update_metadata_toggle(self):
        self._update_ui_states()
        if self.app_mode == "update" and self.videos_to_process:
            update_meta = getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get()
            for vd in self.videos_to_process:
                if isinstance(vd, VideoData) and getattr(vd, 'main_json_dict', None):
                    if update_meta:
                        if "title" in vd.main_json_dict:
                            vd.current_title = vd.main_json_dict["title"]
                        hashtags = " ".join(vd.main_json_dict.get("hashtags", []))
                        if "description" in vd.main_json_dict:
                            vd.current_description = f"{vd.main_json_dict['description']}\n\n{hashtags}".strip()
                        if "tags" in vd.main_json_dict:
                            vd.current_tags = vd.main_json_dict["tags"]
                    else:
                        vd.current_title = vd.video_snippet.get('title', vd.original_title)
                        vd.current_description = vd.video_snippet.get('description', '')
                        vd.current_tags = vd.video_snippet.get('tags', [])
            selected = self.tree.selection()
            self.apply_filters()
            if selected:
                valid_iids = [iid for iid in selected if self.tree.exists(iid)]
                if valid_iids:
                    self.tree.selection_set(valid_iids)

    def _update_ui_states(self):
        is_scheduling = self.update_schedule_var.get()
        is_removing = getattr(self, 'remove_schedule_var', tk.BooleanVar(value=False)).get()
        if self.app_mode == "update":
            if is_scheduling:
                self.update_visibility_var.set(True)
                self.visibility_choice_var.set('private')
            if is_removing:
                self.update_visibility_var.set(True)
            self.vis_cb.config(state=tk.NORMAL)
            self.rad_private.config(state=tk.NORMAL)
            self.rad_unlisted.config(state=tk.NORMAL)
            self.rad_public.config(state=tk.NORMAL)
        update_meta = getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get()
        meta_state = tk.NORMAL if update_meta else tk.DISABLED
        combo_state = "readonly" if update_meta else tk.DISABLED
        if hasattr(self, 'desc_txt'):
            self.desc_txt.config(state=meta_state)
        for attr in ('tags_ent', 'recording_date_ent', 'playlist_id_ent', 'allow_embedding_cb', 'notify_subscribers_cb', 'public_stats_cb', 'mfk_no_rb', 'mfk_yes_rb', 'mfk_dc_rb'):
            if hasattr(self, attr):
                getattr(self, attr).config(state=meta_state)
        for attr in ('category_cb', 'metadata_lang_cb', 'audio_lang_cb'):
            if hasattr(self, attr):
                getattr(self, attr).config(state=combo_state)
    
    def _sort_column(self, col, reverse):
        def get_sort_key(item_id):
            value = self.tree.set(item_id, col)

            if col in ['publish_at', 'upload_date'] and self.app_mode == 'update':
                if value == "Not Scheduled" or not value:
                    return datetime.min
                try:
                    return datetime.strptime(value.replace(' UTC', ''), '%Y-%m-%d %H:%M')
                except ValueError:
                    return datetime.min

            if col in ['views', 'likes', 'comments']:
                try:
                    return int(value)
                except ValueError:
                    return -1

            str_val = str(value).lower().strip()
            if str_val in ["", "n/a", "none"]:
                return "zzzzzz"
            return str_val

        data = [(get_sort_key(k), k) for k in self.tree.get_children('')]; data.sort(reverse=reverse)
        for i, item in enumerate(data): self.tree.move(item[1], '', i)
        self.tree.heading(col, command=lambda c=col: self._sort_column(c, not reverse))
    
    def update_status(self, message): self.root.after(0, lambda: self._set_status_text(message))
    def _set_status_text(self, message): self.status_bar.config(text=message)

    def apply_filters(self):
        search_text = getattr(self, 'search_var', tk.StringVar()).get().lower()
        active_filters = {key for key, var in getattr(self, 'filter_vars', {}).items() if var.get()}
        if not active_filters and not search_text: return self._populate_treeview(self.videos_to_process)
        filtered_list = []
        for vd in self.videos_to_process:
            if isinstance(vd, VideoData):
                if search_text and search_text not in vd.current_title.lower() and search_text not in vd.original_title.lower():
                    continue
                status = vd.video_status.get('privacyStatus'); has_schedule = bool(vd.video_status.get('publishAt'))
                has_main = bool(getattr(vd, 'main_json_dict', None))
                has_desc = bool(vd.description_file_path or has_main)
                conditions = {"public": status == 'public', "not_public": status != 'public', "private": status == 'private', "not_private": status != 'private', "unlisted": status == 'unlisted', "not_unlisted": status != 'unlisted', "has_schedule": has_schedule, "no_schedule": not has_schedule, "has_main_json": has_main, "no_main_json": not has_main, "has_desc_file": has_desc, "no_desc_file": not has_desc, "has_sub_file": bool(vd.subtitle_file_path), "no_sub_file": not vd.subtitle_file_path, "has_thumb_file": bool(vd.thumbnail_file_path), "no_thumb_file": not vd.thumbnail_file_path}
                if vd.width > 0 and vd.height > 0: conditions.update({"is_horizontal": vd.width > vd.height, "is_vertical": vd.height >= vd.width})
                if active_filters and not all(conditions.get(key, True) for key in active_filters): continue
                filtered_list.append(vd)
            elif isinstance(vd, VideoEntry):
                if search_text and search_text not in vd.title.lower() and search_text not in Path(vd.filepath).name.lower():
                    continue
                filtered_list.append(vd)
        self._populate_treeview(filtered_list)
    
    def clear_filters(self):
        for var in getattr(self, 'filter_vars', {}).values(): var.set(False)
        if hasattr(self, 'search_var'): self.search_var.set("")
        self.apply_filters()
    
    def _populate_treeview(self, videos_to_display):
        self.tree.delete(*self.tree.get_children())
        if not videos_to_display: return
        if self.app_mode == "update":
            for vd in videos_to_display:
                publish_at, upload_date = vd.video_status.get('publishAt'), vd.upload_date
                if publish_at:
                    try: publish_at = datetime.fromisoformat(publish_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
                    except (ValueError, TypeError): pass
                else: publish_at = "Not Scheduled"
                if upload_date:
                    try: upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M UTC')
                    except (ValueError, TypeError): pass
                self.tree.insert('', tk.END, values=(vd.video_id, vd.current_title, vd.view_count, vd.like_count, vd.comment_count, vd.description_filename, vd.subtitle_filename, vd.thumbnail_filename, vd.video_status.get('privacyStatus', 'N/A'), publish_at, upload_date), iid=vd.video_id)
        elif self.app_mode == "upload":
            for ve in videos_to_display: self.tree.insert('', tk.END, values=(ve.filepath, ve.title, '', '', '', ve.description_source, '', ve.thumbnail_source, '', '', ve.subtitle_source), iid=ve.filepath)
        self.update_status(f"Displaying {len(videos_to_display)} videos in {self.app_mode.upper()} mode.")
    
    def on_video_select_display_info(self, event):
        selected_items = self.tree.selection()
        if len(selected_items) == 1:
            item_iid = selected_items[0]
            if self.app_mode == "update":
                vd_obj = next((vd for vd in self.videos_to_process if isinstance(vd, VideoData) and vd.video_id == item_iid), None)
                if vd_obj:
                    self.desc_txt.delete('1.0', tk.END); self.desc_txt.insert('1.0', vd_obj.current_description); self.tags_ent.delete(0, tk.END); self.tags_ent.insert(0, ", ".join(vd_obj.current_tags)); cat_name = next((k for k, v in self.dynamic_category_map.items() if v == vd_obj.current_category_id), "Don't Change"); self.category_cb.set(cat_name); meta_lang_name = next((k for k, v in LANGUAGES_MAP.items() if v == vd_obj.current_default_language), "Don't Change"); self.metadata_lang_cb.set(meta_lang_name); audio_lang_name = next((k for k, v in LANGUAGES_MAP.items() if v == vd_obj.current_video_language), "Don't Change"); self.audio_lang_cb.set(audio_lang_name); self.recording_date_var.set(vd_obj.current_recording_date.split('T')[0] if vd_obj.current_recording_date else ''); self.allow_embedding_var.set(vd_obj.current_embeddable); self.public_stats_var.set(vd_obj.current_public_stats_viewable)
                    if vd_obj.current_made_for_kids is True: self.made_for_kids_var.set('yes')
                    elif vd_obj.current_made_for_kids is False: self.made_for_kids_var.set('no')
                    else: self.made_for_kids_var.set('dont_change')
            elif self.app_mode == "upload":
                ve_obj = next((ve for ve in self.videos_to_process if isinstance(ve, VideoEntry) and ve.filepath == item_iid), None)
                if ve_obj: self.desc_txt.delete('1.0', tk.END); self.desc_txt.insert('1.0', ve_obj.description); self.tags_ent.delete(0, tk.END); self.tags_ent.insert(0, ", ".join(ve_obj.tags))
        elif len(selected_items) != 1: self.desc_txt.delete('1.0', tk.END); self.tags_ent.delete(0, tk.END); self.category_cb.set("Don't Change"); self.metadata_lang_cb.set("English"); self.audio_lang_cb.set("English"); self.recording_date_var.set(datetime.now().strftime('%Y-%m-%d')); self.allow_embedding_var.set(True); self.public_stats_var.set(False); self.made_for_kids_var.set('no')
        self._displayed_metadata_values = {
            'description': self.desc_txt.get('1.0', 'end-1c'),
            'tags': self.tags_ent.get(),
        }
    
    def select_credentials_and_auth(self):
        path = filedialog.askopenfilename(title='Select client_secrets.json', filetypes=[('JSON files', '*.json')])
        if path: self.update_status("Authenticating..."); self.service = get_authenticated_service(path)
        if self.service: self.load_channel_categories(); self.load_existing_button.config(state=tk.NORMAL)
        else: self.update_status("Authentication failed.")
    
    def load_channel_categories(self):
        self.update_status("Loading channel categories...");
        try:
            channels_resp = self.service.channels().list(part="snippet", mine=True).execute(); categories_resp = self.service.videoCategories().list(part="snippet", regionCode=channels_resp["items"][0]["snippet"].get("country", "US")).execute(); self.dynamic_category_map = {item['snippet']['title']: item['id'] for item in categories_resp.get("items", []) if item.get('snippet', {}).get('assignable', False)}; sorted_categories = sorted(self.dynamic_category_map.keys()); self.category_cb['values'] = ["Don't Change"] + sorted_categories; self.update_status("Authentication successful. Categories loaded.")
        except Exception as e: logger.error(f"Failed to load video categories: {e}"); self.update_status("Error: Could not load categories.")
    
    def _match_video_to_main_json(self, vd_obj: VideoData) -> dict | None:
        try:
            return match_main_json(
                getattr(self, 'main_json_data', None), video_id=vd_obj.video_id,
                filename=vd_obj.original_upload_filename, title=vd_obj.original_title,
            )
        except ValueError as error:
            vd_obj.metadata_error = str(error)
            logger.error("Metadata error for '%s': %s", vd_obj.original_title, error)
            return None

    def _apply_main_json_to_video(self, vd_obj: VideoData, main_json_item: dict, apply_metadata: bool | None = None):
        vd_obj.main_json_dict = main_json_item
        vd_obj.description_filename = "main.json"
        if apply_metadata is None:
            apply_metadata = getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get()
        if apply_metadata:
            if "title" in main_json_item:
                vd_obj.current_title = main_json_item["title"]
            hashtags = " ".join(main_json_item.get("hashtags", []))
            if "description" in main_json_item:
                vd_obj.current_description = f"{main_json_item['description']}\n\n{hashtags}".strip()
            if "tags" in main_json_item:
                vd_obj.current_tags = main_json_item["tags"]

    def _apply_main_json_matches_to_loaded_videos(self) -> int:
        if self.app_mode != "update" or not self.videos_to_process:
            return 0
        apply_metadata = getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get()
        if self.service and getattr(self, 'main_json_data', None):
            existing_ids = {vd.video_id for vd in self.videos_to_process if isinstance(vd, VideoData)}
            missing_ids = []
            for item in self.main_json_data:
                if isinstance(item, dict):
                    vid = item.get("video_id") or item.get("id")
                    if vid and str(vid) not in existing_ids and str(vid) not in missing_ids:
                        missing_ids.append(str(vid))
            if missing_ids:
                logger.info(f"Fetching {len(missing_ids)} Main JSON video IDs missing from playlist load...")
                try:
                    for i in range(0, len(missing_ids), 50):
                        resp = self.service.videos().list(
                            id=",".join(missing_ids[i:i + 50]),
                            part="snippet,status,fileDetails,contentDetails,statistics"
                        ).execute()
                        for item in resp.get("items", []):
                            vd_obj = VideoData(
                                item["id"],
                                item["snippet"]["title"],
                                item["snippet"],
                                item["status"],
                                item.get("fileDetails"),
                                item.get("contentDetails"),
                                item.get("statistics")
                            )
                            self.videos_to_process.append(vd_obj)
                            existing_ids.add(item["id"])
                except Exception as e:
                    logger.error(f"Failed fetching missing Main JSON IDs: {e}")

        matched_count = 0
        for vd_obj in self.videos_to_process:
            if not isinstance(vd_obj, VideoData):
                continue
            match = self._match_video_to_main_json(vd_obj)
            if match:
                self._apply_main_json_to_video(vd_obj, match, apply_metadata=apply_metadata)
                matched_count += 1
        self.apply_filters()
        self.select_main_json_matches(silent=True)
        return matched_count

    def select_main_json_matches(self, silent=False):
        if self.app_mode != "update":
            return
        matched_iids = [
            vd.video_id
            for vd in self.videos_to_process
            if isinstance(vd, VideoData) and getattr(vd, 'main_json_dict', None) and self.tree.exists(vd.video_id)
        ]
        self.tree.selection_set(matched_iids)
        if matched_iids:
            self.tree.see(matched_iids[0])
        if not silent:
            self.update_status(f"Selected {len(matched_iids)} videos matching Main JSON.")

    def gui_load_main_json(self):
        path = filedialog.askopenfilename(title='Select main.json', filetypes=[('JSON files', '*.json')])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    raw = f.read()
                try:
                    data = json.loads(raw)
                except Exception:
                    data = sanitize_and_parse_json(raw)
                if isinstance(data, dict):
                    data = data.get("videos") or data.get("items") or [data]
                if not isinstance(data, list):
                    raise ValueError("Main JSON must be a JSON list of video objects (or an object containing 'videos'/'items').")
                self.main_json_data = data
                if self.app_mode == "update" and self.videos_to_process:
                    matched = self._apply_main_json_matches_to_loaded_videos()
                    self.update_status(f"Loaded Main JSON ({len(self.main_json_data)} entries). Matched & selected {matched} loaded videos.")
                    logger.info(f"Loaded Main JSON ({len(self.main_json_data)} entries). Matched {matched} loaded videos.")
                else:
                    self.update_status(f"Loaded Main JSON with {len(self.main_json_data)} entries.")
                    logger.info(f"Loaded Main JSON with {len(self.main_json_data)} entries.")
            except Exception as e:
                logger.error(f"Failed to load Main JSON: {e}")
                self.update_status("Error loading Main JSON.")
    
    def gui_load_existing_videos(self):
        self.app_mode = "update"; self._update_gui_for_mode()
        try: max_to_load = int(self.max_videos_var.get())
        except ValueError: max_to_load = 50
        playlist_id = self.playlist_id_entry_var.get().strip()
        load_mode = self.playlist_load_mode_var.get()
        apply_metadata = getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get()
        self.update_status(f"Loading up to {max_to_load or 'ALL'} videos..."); self.load_existing_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_video_load, args=(max_to_load, playlist_id, load_mode, apply_metadata), daemon=True).start()
    
    def run_video_load(self, max_to_load, playlist_id=None, load_mode="Playlist Only", apply_metadata=True):
        self.videos_to_process = self.fetch_all_videos_from_api(max_videos_to_fetch=max_to_load, playlist_id=playlist_id, load_mode=load_mode, apply_metadata=apply_metadata)
        self.root.after(100, self.finish_video_load)

    def finish_video_load(self):
        self.apply_filters()
        self.process_button.config(state=tk.NORMAL)
        self.filter_menubutton.config(state=tk.NORMAL)
        self.load_existing_button.config(state=tk.NORMAL)
        if getattr(self, 'main_json_data', None):
            self.select_main_json_matches(silent=True)
            matched_count = len(self.tree.selection())
            self.update_status(f"Loaded {len(self.videos_to_process)} videos ({matched_count} matched & selected from Main JSON).")
        else:
            self.update_status(f"Loaded {len(self.videos_to_process)} videos.")
    
    def gui_load_files_for_upload(self):
        self.app_mode = "upload"; self._update_gui_for_mode(); self.videos_to_process = []; logger.info("Scanning for video files to upload...")
        for pat in VIDEO_PATTERNS:
            for f in glob.glob(pat):
                if f not in [v.filepath for v in self.videos_to_process]: self.videos_to_process.append(VideoEntry(f, self.main_json_data if hasattr(self, 'main_json_data') else None))
        logger.info(f"Found {len(self.videos_to_process)} videos to upload."); self._populate_treeview(self.videos_to_process); self.process_button.config(state=tk.NORMAL if self.videos_to_process else tk.DISABLED)
    
    def fetch_all_videos_from_api(self, max_videos_to_fetch=0, playlist_id=None, load_mode="Playlist Only", apply_metadata=True):
        all_video_data_map, video_ids = {}, []
        
        try:
            target_playlist_ids = []
            
            uploads_playlist_id = None
            if not playlist_id or load_mode == "Uploads + Playlist":
                logger.info("Fetching default 'Uploads' playlist ID.")
                uploads_id_req = self.service.channels().list(part="contentDetails", mine=True).execute()
                if uploads_id_req.get("items"):
                    uploads_playlist_id = uploads_id_req["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            if not playlist_id:
                if uploads_playlist_id:
                    target_playlist_ids.append(uploads_playlist_id)
            else:
                if load_mode == "Uploads + Playlist":
                    if uploads_playlist_id:
                        target_playlist_ids.append(uploads_playlist_id)
                    target_playlist_ids.append(playlist_id)
                else:
                    target_playlist_ids.append(playlist_id)
            
            if not target_playlist_ids:
                return []
            
            for pid in target_playlist_ids:
                next_page_token = None
                logger.info(f"Fetching from Playlist ID: {pid}")
                while True:
                    pl_resp = self.service.playlistItems().list(
                        playlistId=pid, part="contentDetails", maxResults=50, pageToken=next_page_token
                    ).execute()
                    
                    for item in pl_resp.get("items", []):
                        vid = item["contentDetails"]["videoId"]
                        if vid not in video_ids:
                            video_ids.append(vid)
                            
                    if max_videos_to_fetch and len(video_ids) >= max_videos_to_fetch: break
                    next_page_token = pl_resp.get("nextPageToken")
                    if not next_page_token: break
                if max_videos_to_fetch and len(video_ids) >= max_videos_to_fetch: break
    
            if max_videos_to_fetch: video_ids = video_ids[:max_videos_to_fetch]
            if getattr(self, 'main_json_data', None):
                existing_set = set(video_ids)
                for item in self.main_json_data:
                    if isinstance(item, dict):
                        vid = item.get("video_id") or item.get("id")
                        if vid and str(vid) not in existing_set:
                            video_ids.append(str(vid))
                            existing_set.add(str(vid))
            if not video_ids: return []
    
            local_files = [f for f in Path.cwd().rglob('*') if f.is_file()]
            logger.info(f"--- DEBUG: FOUND {len(local_files)} LOCAL FILES ---")
            metadata_title_cache = {}
            valid_metadata_files = set()
            metadata_file_errors = {}
            for f in local_files:
                if f.suffix.lower() in METADATA_EXTENSIONS and f.name.lower() != 'main.json':
                    try:
                        data = read_metadata_file(f, allow_unrelated=True)
                        if data is None:
                            continue
                        valid_metadata_files.add(f)
                        metadata_title_cache[f] = normalize_for_matching(data.get('title', ''))
                    except (ValueError, OSError) as error:
                        metadata_file_errors[f] = str(error)
            
            # High-Precision TIMESTAMP_PATTERN (Captures Seconds)
            TIMESTAMP_PATTERN = re.compile(r'(202\d)[\.\-\s_]?([01]\d)[\.\-\s_]?([0-3]\d).*?([0-2]\d)[\.\-\s_]?([0-5]\d)[\.\-\s_]?([0-5]\d)?')
            
            used_metadata_files = set()
            used_subtitle_files = set()
            used_thumbnail_files = set()

            for i in range(0, len(video_ids), 50):
                self.update_status(f"Fetching details... ({min(i + 50, len(video_ids))}/{len(video_ids)})")
                videos_resp = self.service.videos().list(id=",".join(video_ids[i:i + 50]), part="snippet,status,fileDetails,contentDetails,statistics").execute()
                
                for item in videos_resp.get("items", []):
                    video_id = item["id"]
                    if video_id in all_video_data_map: continue

                    vd_obj = VideoData(
                        video_id,
                        item["snippet"]["title"],
                        item["snippet"],
                        item["status"],
                        item.get("fileDetails"),
                        item.get("contentDetails"),
                        item.get("statistics")
                    )
                    logger.info(f"\n[Processing Video]: {vd_obj.current_title[:60]}... (Original: {vd_obj.original_upload_filename or 'Unknown'})")
                    
                    yt_timestamps = set()
                    def get_ts(s):
                        if not s: return None
                        m = TIMESTAMP_PATTERN.search(s)
                        if m:
                            secs = m.group(6) if m.group(6) else "00"
                            return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}-{m.group(5)}-{secs}"
                        return None
                    
                    ts_title = get_ts(vd_obj.current_title)
                    if ts_title: yt_timestamps.add(ts_title)
                    if vd_obj.original_upload_filename:
                        ts_orig = get_ts(vd_obj.original_upload_filename)
                        if ts_orig: yt_timestamps.add(ts_orig)

                    yt_norm_title = normalize_for_matching(vd_obj.current_title)
                    orig_upload_stem = re.sub(r'\.[a-z0-9]{2,4}$', '', vd_obj.original_upload_filename, flags=re.IGNORECASE) if vd_obj.original_upload_filename else None
                    orig_norm_stem = normalize_for_matching(orig_upload_stem) if orig_upload_stem else ""
                    nuclear_title = nuclear_clean(vd_obj.current_title)
                    marker_num_title = extract_marker_number(vd_obj.current_title)
                    
                    main_json_item = self._match_video_to_main_json(vd_obj)

                    if main_json_item:
                        self._apply_main_json_to_video(vd_obj, main_json_item, apply_metadata=apply_metadata)
                        best_meta_match_name = "main.json"
                        logger.info(f"  > MAIN JSON MATCH FOUND for '{vd_obj.original_title}'")

                    yt_hash_tokens = set()
                    for src in (vd_obj.current_title, vd_obj.original_upload_filename):
                        h = extract_trailing_hash8(src)
                        if h:
                            yt_hash_tokens.add(h)
                    best_txt_match = None; best_sub_match = None; best_thumb_match = None
                    best_txt_score = float('inf')
                    best_sub_score = float('inf')
                    best_thumb_score = float('inf')
                    if not main_json_item:
                        best_meta_match_name = None
                    best_sub_match_name = None
                    best_thumb_match_name = None
                    best_txt_hash_tiebreak = -1
                    best_sub_hash_tiebreak = -1
                    best_thumb_hash_tiebreak = -1
                    best_metadata_candidates = []
                    exact_metadata = None
                    if not main_json_item and not vd_obj.metadata_error:
                        try:
                            stems = [orig_upload_stem] if orig_upload_stem else [vd_obj.current_title]
                            exact_yt_names = {f'{stem}-youtube.json'.lower() for stem in stems if stem}
                            exact_json_names = {f'{stem}.json'.lower() for stem in stems if stem}
                            exact_candidates = [
                                (0, path) for path in local_files
                                if path not in used_metadata_files and path.name.lower() in exact_yt_names
                            ] + [
                                (1, path) for path in local_files
                                if path not in used_metadata_files and path.name.lower() in exact_json_names and (path in valid_metadata_files or path in metadata_file_errors)
                            ]
                            exact_metadata = unique_metadata_match(exact_candidates, f"metadata for {vd_obj.original_title}")
                            if exact_metadata in metadata_file_errors:
                                raise ValueError(metadata_file_errors[exact_metadata])
                            if exact_metadata is not None and exact_metadata not in valid_metadata_files:
                                raise ValueError(f"{exact_metadata}: exact sidecar must contain a metadata object, not a timing export or another JSON type.")
                        except ValueError as error:
                            vd_obj.metadata_error = str(error)
                            logger.error("Metadata error for '%s': %s", vd_obj.original_title, error)

                    for file_path in local_files:
                        ext_lower = file_path.suffix.lower()
                        if ext_lower in METADATA_EXTENSIONS and (file_path not in valid_metadata_files and file_path not in metadata_file_errors or vd_obj.metadata_error): continue
                        if (ext_lower in METADATA_EXTENSIONS or ext_lower in THUMBNAIL_EXTENSIONS) and orig_upload_stem and not compatible_render_variant(orig_upload_stem, file_path.stem): continue
                        # Guard: Skip blank files
                        if (ext_lower in METADATA_EXTENSIONS or ext_lower in THUMBNAIL_EXTENSIONS) and file_path.stat().st_size == 0: continue
                        if ext_lower in METADATA_EXTENSIONS and file_path in used_metadata_files: continue
                        if any(ext_lower == p.replace('*', '') for p in SUBTITLE_PATTERNS) and file_path in used_subtitle_files: continue
                        if ext_lower in THUMBNAIL_EXTENSIONS and file_path in used_thumbnail_files: continue
                        
                        current_score = float('inf')
                        file_ts = get_ts(file_path.name)
                        file_norm_stem = normalize_for_matching(file_path.stem)
                        nuclear_file = nuclear_clean(file_path.name)
                        file_hash = extract_trailing_hash8(file_path.stem)
                        hash_tiebreak = 1 if (file_hash and file_hash in yt_hash_tokens) else 0

                        # A. EXACT NORMALIZED TITLE/ORIGINAL-FILENAME <-> STEM MATCH (strongest non-timestamp signal)
                        if file_norm_stem and (file_norm_stem == yt_norm_title or (orig_norm_stem and file_norm_stem == orig_norm_stem)):
                            current_score = 0.1

                        # B. TIMESTAMP MATCH (Score 0 or 5 based on Replay status)
                        if file_ts and file_ts in yt_timestamps:
                            current_score = 0
                            yt_has_replay = "replay" in vd_obj.current_title.lower()
                            file_has_replay = "replay" in file_path.name.lower()
                            if yt_has_replay != file_has_replay:
                                current_score = 5 # Penalty for Rec/Replay mismatch
                                
                            marker_num_file = extract_marker_number(file_path.stem)
                            if marker_num_title is not None:
                                if marker_num_file == marker_num_title:
                                    current_score -= 0.05
                                elif marker_num_file is not None:
                                    current_score += 0.5
                                else:
                                    current_score += 0.1

                        # C. NUCLEAR TEXT MATCH (Score 1)
                        if current_score > 1 and len(nuclear_file) > 8 and len(nuclear_title) > 0:
                            if nuclear_file in nuclear_title or nuclear_title in nuclear_file:
                                current_score = 1
                        # D. Marker token match (handles "Marker X ..."-style names)
                        if current_score > 1:
                            marker_num_file = extract_marker_number(file_path.stem)
                            if marker_num_title is not None and marker_num_file == marker_num_title:
                                current_score = 2
                                if has_eng_token(vd_obj.current_title) and has_eng_token(file_path.stem):
                                    current_score = 1.5
                        # E. Metadata JSON title match (handles custom YT titles vs timestamp filenames)
                        if current_score > 0.5 and file_path.suffix.lower() in METADATA_EXTENSIONS:
                            metadata_norm_title = metadata_title_cache.get(file_path, "")
                            if metadata_norm_title and yt_norm_title:
                                if metadata_norm_title == yt_norm_title:
                                    current_score = 0.5
                                elif (len(metadata_norm_title) > 4 and metadata_norm_title in yt_norm_title) or (len(yt_norm_title) > 4 and yt_norm_title in metadata_norm_title):
                                    current_score = min(current_score, 0.75)

                        # F. Hash Priority Override
                        if hash_tiebreak == 1:
                            current_score = -1
                        if file_path == exact_metadata:
                            current_score = -2

                        if current_score < float('inf'):
                            ext = file_path.suffix.lower()
                            if ext in METADATA_EXTENSIONS:
                                if main_json_item: continue # Skip if main json matched
                                if (current_score < best_txt_score) or (current_score == best_txt_score and hash_tiebreak > best_txt_hash_tiebreak):
                                    best_txt_score = current_score
                                    best_txt_match = file_path
                                    best_meta_match_name = file_path.name
                                    best_txt_hash_tiebreak = hash_tiebreak
                                    best_metadata_candidates = [file_path]
                                elif current_score == best_txt_score and hash_tiebreak == best_txt_hash_tiebreak:
                                    best_metadata_candidates.append(file_path)
                            elif any(ext == p.replace('*', '') for p in SUBTITLE_PATTERNS):
                                if (current_score < best_sub_score) or (current_score == best_sub_score and hash_tiebreak > best_sub_hash_tiebreak):
                                    best_sub_score = current_score
                                    best_sub_match = file_path
                                    best_sub_match_name = file_path.name
                                    best_sub_hash_tiebreak = hash_tiebreak
                            elif ext in THUMBNAIL_EXTENSIONS:
                                if (current_score < best_thumb_score) or (current_score == best_thumb_score and hash_tiebreak > best_thumb_hash_tiebreak):
                                    best_thumb_score = current_score
                                    best_thumb_match = file_path
                                    best_thumb_match_name = file_path.name
                                    best_thumb_hash_tiebreak = hash_tiebreak

                    if len(best_metadata_candidates) > 1:
                        vd_obj.metadata_error = f"Ambiguous metadata for {vd_obj.original_title}: {'; '.join(str(path) for path in sorted(best_metadata_candidates))}"
                        logger.error(vd_obj.metadata_error)
                        best_txt_match = None
                        best_meta_match_name = None
                    elif best_txt_match in metadata_file_errors:
                        vd_obj.metadata_error = metadata_file_errors[best_txt_match]
                        logger.error("Metadata error for '%s': %s", vd_obj.original_title, vd_obj.metadata_error)
                        best_txt_match = None
                        best_meta_match_name = None
                    if best_txt_match and (best_thumb_match is None or best_thumb_score > best_txt_score):
                        sibling_thumb = find_matching_thumbnail_for_stem(best_txt_match.parent, [best_txt_match.stem])
                        if sibling_thumb and sibling_thumb not in used_thumbnail_files:
                            best_thumb_match = sibling_thumb
                            best_thumb_match_name = sibling_thumb.name
                    if best_txt_match or best_sub_match or best_thumb_match:
                         if best_txt_match:
                             vd_obj.description_file_path = str(best_txt_match)
                             vd_obj.description_filename = best_txt_match.name
                             used_metadata_files.add(best_txt_match)
                         if best_sub_match:
                             vd_obj.subtitle_file_path = str(best_sub_match)
                             vd_obj.subtitle_filename = best_sub_match.name
                             used_subtitle_files.add(best_sub_match)
                         if best_thumb_match:
                             vd_obj.thumbnail_file_path = str(best_thumb_match)
                             vd_obj.thumbnail_filename = best_thumb_match.name
                             used_thumbnail_files.add(best_thumb_match)
                         logger.info(f"  > MATCH FOUND -> metadata={best_meta_match_name or 'None'}, subtitle={best_sub_match_name or 'None'}, thumbnail={best_thumb_match_name or 'None'}")
                    elif not main_json_item:
                         logger.info("  > NO LOCAL MATCH FOUND")

                    all_video_data_map[video_id] = vd_obj

        except Exception as e:
            logger.error(f"Error fetching videos: {e}", exc_info=True)
        return list(all_video_data_map.values())

    def start_processing_thread(self):
        selected_iids = self.tree.selection()
        if not selected_iids: return self.update_status("Error: No items selected.")
        self.process_button.config(state=tk.DISABLED)
        order = self.schedule_order_var.get()
        if self.app_mode == "update":
            selected_videos = []
            for iid in selected_iids:
                match = next((vd for vd in self.videos_to_process if isinstance(vd, VideoData) and vd.video_id == iid), None)
                if match: selected_videos.append(match)
            if order == 'File Name (Asc)':
                selected_videos.sort(key=lambda x: str(x.original_upload_filename or x.current_title).lower())
            elif order == 'File Name (Desc)':
                selected_videos.sort(key=lambda x: str(x.original_upload_filename or x.current_title).lower(), reverse=True)
            elif order == 'Random':
                random.shuffle(selected_videos)
            description_override = self.desc_txt.get('1.0', 'end-1c')
            tags_override = self.tags_ent.get()
            displayed = getattr(self, '_displayed_metadata_values', {})
            if description_override == displayed.get('description'): description_override = ''
            if tags_override == displayed.get('tags'): tags_override = ''
            processing_data = {"videos": selected_videos, "start_time_str": self.start_ent.get(), "interval_hours": int(self.interval_hour_var.get()), "interval_mins": int(self.interval_minute_var.get()), "playlist_id": self.playlist_id_var.get().strip(), "is_dry_run": self.dry_run_var.get(), "update_metadata": getattr(self, 'update_metadata_var', tk.BooleanVar(value=True)).get(), "upload_thumbnails": getattr(self, 'upload_thumbnails_var', tk.BooleanVar(value=False)).get(), "update_schedule": self.update_schedule_var.get(), "remove_schedule": getattr(self, 'remove_schedule_var', tk.BooleanVar(value=False)).get(), "update_visibility": self.update_visibility_var.get(), "visibility_to_set": self.visibility_choice_var.get(), "notify_subscribers": self.notify_subscribers_var.get(), "category_id": self.dynamic_category_map.get(self.category_var.get()) if self.category_var.get() != "Don't Change" else None, "description_override": description_override, "tags_override": tags_override, "metadata_lang_name": self.metadata_lang_var.get(), "audio_lang_name": self.audio_lang_var.get(), "recording_date": self.recording_date_var.get().strip(), "allow_embedding": self.allow_embedding_var.get(), "public_stats_viewable": self.public_stats_var.get(), "made_for_kids": self.made_for_kids_var.get()}
            self.update_status("Updating... Check console."); threading.Thread(target=self.run_update_processing, args=(processing_data,), daemon=True).start()
        elif self.app_mode == "upload":
            selected_videos = []
            for iid in selected_iids:
                match = next((ve for ve in self.videos_to_process if isinstance(ve, VideoEntry) and ve.filepath == iid), None)
                if match: selected_videos.append(match)
            if order == 'File Name (Asc)':
                selected_videos.sort(key=lambda x: Path(x.filepath).name.lower())
            elif order == 'File Name (Desc)':
                selected_videos.sort(key=lambda x: Path(x.filepath).name.lower(), reverse=True)
            elif order == 'Random':
                random.shuffle(selected_videos)
            job_options = UploadJobOptions(
                video_entries=tuple(selected_videos),
                skip_subtitles=self.skip_subs_var.get(),
                move_files=self.move_files_var.get(),
                dry_run=self.dry_run_var.get(),
                upload_thumbnails=getattr(self, 'upload_thumbnails_var', tk.BooleanVar(value=False)).get(),
            )
            self.update_status("Previewing uploads... Check console." if job_options.dry_run else "Uploading... Check console.")
            threading.Thread(target=self.run_upload_processing, args=(job_options,), daemon=True).start()

    def _finish_update_ui(self):
        selected = self.tree.selection()
        self.apply_filters()
        if selected:
            valid_iids = [iid for iid in selected if self.tree.exists(iid)]
            if valid_iids:
                self.tree.selection_set(valid_iids)
        self.process_button.config(state=tk.NORMAL)
        self.update_status("Update process complete.")

    def run_update_processing(self, processing_data):
        try:
            if self.service: update_videos_on_youtube(self.service, processing_data)
            else: self.update_status("Error: Not authenticated.")
        except Exception as e: logger.error(f"Overall update process failed: {e}"); self.update_status("Update process failed.")
        finally: self.root.after(100, self._finish_update_ui)

    def run_upload_processing(self, job_options):
        completion_status = "Upload preview complete." if job_options.dry_run else "Upload process complete."
        try:
            if self.service is None and not job_options.dry_run:
                completion_status = "Error: Not authenticated."
                return
            upload_new_videos(
                self.service, job_options.video_entries, job_options.skip_subtitles,
                job_options.move_files, dry_run=job_options.dry_run,
                upload_thumbnails=job_options.upload_thumbnails,
            )
        except Exception as e:
            logger.error(f"Overall upload process failed: {e}")
            completion_status = "Upload process failed."
        finally:
            self.root.after(100, lambda: self.process_button.config(state=tk.NORMAL))
            self.root.after(100, lambda: self.update_status(completion_status))

    def on_exit(self):
        if self.save_log_var.get():
            with open(LOG_FILE, 'w', encoding='utf-8') as f: f.write("\n".join(log_records))
        self.root.destroy()

def update_videos_on_youtube(service, processing_data):
    videos = processing_data["videos"]; is_dry_run = processing_data["is_dry_run"]
    update_metadata = processing_data.get("update_metadata", True)
    upload_thumbnails = processing_data.get("upload_thumbnails", False)
    start_dt, delta = None, None
    if processing_data.get("update_schedule"):
        try:
            start_dt = datetime.strptime(processing_data["start_time_str"], '%Y-%m-%d %H:%M').astimezone(timezone.utc)
            delta = timedelta(hours=processing_data["interval_hours"], minutes=processing_data["interval_mins"])
        except ValueError:
            logger.error("Invalid date format.")
            return
    
    success_count = 0; failed_videos = []; skipped_videos = []
    
    for i, vd in enumerate(videos):
        # Blank File Safety Guard (only when updating metadata from a local file)
        if update_metadata and vd.description_file_path and not getattr(vd, 'main_json_dict', None):
            if Path(vd.description_file_path).stat().st_size == 0:
                logger.warning(f"SKIPPING '{vd.original_title}': Matched file is blank (0 KB).")
                skipped_videos.append(vd.original_title)
                continue

        parts, body = [], {'id': vd.video_id}
        display_title = vd.current_title
        if update_metadata:
            try:
                snippet = prepare_update_snippet(vd, processing_data)
            except (ValueError, OSError) as error:
                logger.error("Skipping metadata update for '%s': %s", vd.original_title, error)
                failed_videos.append(vd.original_title)
                continue
            body['snippet'] = snippet; parts.append('snippet')
            display_title = snippet['title']
        
        if update_metadata:
            status = {'publicStatsViewable': processing_data["public_stats_viewable"], 'embeddable': processing_data["allow_embedding"]}
            if processing_data["made_for_kids"] != 'dont_change':
                status['selfDeclaredMadeForKids'] = (processing_data["made_for_kids"] == 'yes')
        else:
            status = {}
            for k in ('embeddable', 'publicStatsViewable', 'selfDeclaredMadeForKids'):
                if k in vd.video_status:
                    status[k] = vd.video_status[k]

        for key in ('license', 'containsSyntheticMedia'):
            if key in vd.video_status:
                status[key] = vd.video_status[key]

        status['privacyStatus'] = vd.video_status.get('privacyStatus', 'private')
        if processing_data["update_schedule"]:
            # YouTube API rejects scheduling for videos that are already public or if the time is in the past.
            target_time = start_dt + i * delta
            current_privacy = vd.video_status.get('privacyStatus', '')
            if current_privacy == 'public':
                logger.warning(f"Skipping schedule update for '{vd.original_title}' (already {current_privacy}).")
            elif target_time < datetime.now(timezone.utc):
                logger.warning(f"Skipping schedule update for '{vd.original_title}' (calculated time {target_time.strftime('%Y-%m-%d %H:%M')} is in the past).")
            else:
                status['publishAt'] = target_time.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                status['privacyStatus'] = 'private'
        elif processing_data.get("remove_schedule"):
            status['privacyStatus'] = processing_data["visibility_to_set"] if processing_data["update_visibility"] else vd.video_status.get('privacyStatus', 'private')
        elif processing_data["update_visibility"]: 
            status['privacyStatus'] = processing_data["visibility_to_set"]
        elif vd.video_status.get('publishAt'):
            status['publishAt'] = vd.video_status['publishAt']
            
        body['status'] = status; parts.append('status')
        
        if is_dry_run:
            logger.info(f"DRY RUN ({i+1}/{len(videos)}): '{vd.original_title}' -> parts={','.join(parts)}, privacyStatus={status.get('privacyStatus')}, publishAt={status.get('publishAt')}")
            if upload_thumbnails and getattr(vd, 'thumbnail_file_path', None):
                upload_video_thumbnail(service, vd.video_id, vd.thumbnail_file_path, is_dry_run=True)
            success_count += 1
            continue
        try:
            service.videos().update(part=",".join(parts), body=body).execute()
            vd.video_status['privacyStatus'] = status['privacyStatus']
            if 'publishAt' in status:
                vd.video_status['publishAt'] = status['publishAt']
            else:
                vd.video_status.pop('publishAt', None)
            if 'snippet' in body:
                vd.video_snippet.update(deepcopy(body['snippet']))
                vd.current_title = body['snippet']['title']
                vd.current_description = body['snippet'].get('description', '')
                vd.current_tags = body['snippet'].get('tags', [])
                vd.current_category_id = body['snippet']['categoryId']
            logger.info(f"({i+1}/{len(videos)}) Updated '{display_title}' (parts={','.join(parts)}, privacy={status.get('privacyStatus')}).")
            if upload_thumbnails and getattr(vd, 'thumbnail_file_path', None):
                upload_video_thumbnail(service, vd.video_id, vd.thumbnail_file_path, is_dry_run=False)
            success_count += 1
        except HttpError as e:
            logger.error(f"FAILED update: {e.reason}")
            failed_videos.append(vd.original_title)
            if 'quota' in str(e).lower() or 'quota' in getattr(e, 'reason', '').lower():
                logger.error("Quota exceeded. Stopping update process.")
                break
    
    logger.info("\n--- Update Process Summary ---")
    logger.info(f"Total processed: {len(videos)}")
    logger.info(f"Successfully updated: {success_count}")
    if skipped_videos: logger.info(f"Skipped (blank metadata): {len(skipped_videos)}")
    if failed_videos:
        logger.error(f"Failed updates: {len(failed_videos)}")
        for fv in failed_videos: logger.error(f"  - {fv}")
    logger.info("------------------------------")

def upload_new_videos(service, video_entries, skip_subtitles, move_files=True, *, dry_run=False, legacy_tag_cleanup=False, upload_thumbnails=False):
    if service is None and not dry_run:
        raise ValueError("Not authenticated.")
    batch_id = generate_batch_id()
    success_count = 0; planned_count = 0; failed_videos = []; skipped_videos = []
    
    for e in video_entries:
        # Blank File Safety Guard
        if e.description_file_path and Path(e.description_file_path).stat().st_size == 0:
            logger.warning(f"SKIPPING upload of {e.filepath}: Metadata file is blank.")
            skipped_videos.append(e.title)
            continue

        try:
            if getattr(e, 'metadata_error', None):
                raise ValueError(e.metadata_error)
            snippet = {
                'title': validate_title(e.title),
                'description': sanitize_description(e.description),
                'categoryId': e.categoryId,
                'tags': prepare_tags(e.tags, legacy_cleanup=legacy_tag_cleanup),
            }
            body = {'snippet': snippet, 'status': {'privacyStatus': 'private', 'publishAt': e.publishAt, 'selfDeclaredMadeForKids': e.madeForKids}}
            logger.debug("Prepared upload body for %s: %s", e.filepath, body)
            if dry_run:
                logger.info(
                    "DRY RUN: file=%s | metadata=%s | thumbnail=%s | tags=%s | part=snippet,status | categoryId=%s | status=%s | skip_subtitles=%s | upload_thumbnails=%s | move_files=%s (disabled for preview)",
                    e.filepath, e.description_file_path or e.description_source,
                    getattr(e, 'thumbnail_path', None) or getattr(e, 'thumbnail_source', 'None'),
                    snippet['tags'], snippet['categoryId'], body['status'], skip_subtitles, upload_thumbnails, move_files,
                )
                planned_count += 1
                continue
            media = MediaFileUpload(e.filepath, chunksize=-1, resumable=True)
            try:
                req = service.videos().insert(part='snippet,status', body=body, media_body=media); resp = None
                while resp is None: progress, resp = req.next_chunk()
            finally:
                stream = media.stream() if hasattr(media, 'stream') else None
                if stream is not None and hasattr(stream, 'close'):
                    stream.close()
            vid = resp['id']; logger.info(f"Uploaded: https://youtu.be/{vid}")
            if upload_thumbnails and getattr(e, 'thumbnail_path', None):
                upload_video_thumbnail(service, vid, e.thumbnail_path, is_dry_run=False)
            success_count += 1
            if move_files: move_uploaded_files(e, batch_id, True)
        except Exception as ex: 
            logger.error(f"Upload failed: {ex}")
            failed_videos.append(e.title)
            if isinstance(ex, HttpError) and ('quota' in str(ex).lower() or 'quota' in getattr(ex, 'reason', '').lower()):
                logger.error("Quota exceeded. Stopping upload process.")
                break
            
    logger.info("\n--- Upload Process Summary ---")
    logger.info(f"Total processed: {len(video_entries)}")
    if dry_run: logger.info(f"Planned uploads (Dry Run): {planned_count}")
    logger.info(f"Successfully uploaded: {success_count}")
    if skipped_videos: logger.info(f"Skipped (blank metadata): {len(skipped_videos)}")
    if failed_videos:
        logger.error(f"Failed uploads: {len(failed_videos)}")
        for fv in failed_videos: logger.error(f"  - {fv}")
    logger.info("------------------------------")

if __name__ == '__main__':
    MainApp()

