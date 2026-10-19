#!/usr/bin/env python3
import argparse, csv, errno, shutil
from pathlib import Path

SIGS = {
    '.jpg':  ('JPEG', lambda h: h.startswith(b'\xff\xd8')),
    '.jpeg': ('JPEG', lambda h: h.startswith(b'\xff\xd8')),
    '.jpe':  ('JPEG', lambda h: h.startswith(b'\xff\xd8')),
    '.jfif': ('JPEG', lambda h: h.startswith(b'\xff\xd8')),
    '.png':  ('PNG',  lambda h: h.startswith(b'\x89PNG\r\n\x1a\n')),
    '.gif':  ('GIF',  lambda h: h.startswith(b'GIF87a') or h.startswith(b'GIF89a')),
    '.bmp':  ('BMP',  lambda h: h.startswith(b'BM')),
    '.webp': ('WEBP', lambda h: len(h) >= 12 and h.startswith(b'RIFF') and h[8:12] == b'WEBP'),
    '.heic': ('HEIC', lambda h: len(h) >= 12 and h[4:8] == b'ftyp' and h[8:12] in (b'heic', b'heix', b'mif1', b'hevc')),
    '.tif':  ('TIFF', lambda h: h.startswith(b'II*\x00') or h.startswith(b'MM\x00*')),
    '.tiff': ('TIFF', lambda h: h.startswith(b'II*\x00') or h.startswith(b'MM\x00*')),
    '.arw':  ('ARW',  lambda h: h.startswith(b'II*\x00') or h.startswith(b'MM\x00*')),
    '.nef':  ('NEF',  lambda h: h.startswith(b'II*\x00') or h.startswith(b'MM\x00*')),
    '.dng':  ('DNG',  lambda h: h.startswith(b'II*\x00') or h.startswith(b'MM\x00*')),
    '.cr2':  ('CR2',  lambda h: len(h) >= 16 and (h.startswith(b'II*\x00\x10\x00\x00\x00CR\x02\x00') or h.startswith(b'MM\x00*\x00\x00\x00\x10CR\x02\x00'))),
    '.cr3':  ('CR3',  lambda h: len(h) >= 12 and h[4:12] == b'ftypcrx '),
}

HEADER_LENS = {
    '.jpg': 2, '.jpeg': 2, '.jpe': 2, '.jfif': 2,
    '.png': 8,
    '.gif': 6,
    '.bmp': 2,
    '.webp': 12,
    '.heic': 12,
    '.tif': 8, '.tiff': 8, '.arw': 8, '.nef': 8, '.dng': 8,
    '.cr2': 16,
    '.cr3': 12,
}

REPAIRABLE = {
    '.jpg', '.jpeg', '.jpe', '.jfif', '.png', '.gif', '.bmp',
    '.cr2', '.cr3', '.tif', '.tiff', '.webp', '.heic', '.arw', '.nef', '.dng'
}

# Folders this script creates. We skip them so re-runs don't reprocess outputs.
SKIP_DIRS = {'_good', '_fixed', '_repaired', '_unfixable', '_empty'}


def read_head(path, n=16):
    try:
        with open(path, 'rb') as f:
            return f.read(n)
    except Exception:
        return b''


def unique_target(folder, filename):
    """Return a non-existing path inside `folder` for `filename`,
    appending _1, _2, ... before the extension if it already exists."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    counter = 1
    while True:
        candidate = folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def detect_corruption_mode(ext, head, header_len):
    """
    Heuristics to guess if the header was deleted (truncated) or overwritten by garbage bytes.
    Returns 'prepend' or 'replace'.
    """
    if ext in ('.jpg', '.jpeg', '.jpe', '.jfif'):
        if len(head) >= 4:
            if head[0] == 0xff and head[1] not in (0xd8, 0x00):
                return 'prepend'
            if head[2] == 0xff and head[3] not in (0xd8, 0x00):
                return 'replace'

    elif ext == '.png':
        if len(head) >= 16:
            if b'IHDR' in head[0:8]:
                return 'prepend'
            if b'IHDR' in head[8:16]:
                return 'replace'

    elif ext in ('.heic', '.cr3'):
        if len(head) >= 16:
            if b'ftyp' in head[0:8]:
                return 'prepend'
            if b'ftyp' in head[8:16]:
                return 'replace'

    elif ext == '.webp':
        if len(head) >= 20:
            if b'VP8' in head[0:12]:
                return 'prepend'
            if b'VP8' in head[12:20]:
                return 'replace'

    if len(head) >= header_len and all(b == 0 for b in head[:header_len]):
        return 'replace'

    return 'prepend'


def verify_image(path, ext=None, header_len=None):
    """
    Validates if a file has both a valid magic header and a readable image payload.
    Returns (is_valid, status_code, reason)
    status_code can be: 'OK', 'BAD_HEADER', or 'CORRUPT_BODY'
    """
    if ext is None:
        ext = path.suffix.lower()

    if ext not in SIGS:
        return False, 'UNSUPPORTED', 'Unsupported file extension'

    h = read_head(path)
    name, checker = SIGS[ext]
    if not checker(h):
        return False, 'BAD_HEADER', 'Invalid magic header'

    try:
        size = path.stat().st_size
        if size < 128:
            return False, 'CORRUPT_BODY', 'File is too small to contain valid image data'

        if header_len is None:
            header_len = HEADER_LENS.get(ext, 8)

        with open(path, 'rb') as f:
            f.seek(header_len)
            sample = f.read(1024)
            if len(sample) > 0 and len(set(sample)) <= 1:
                return False, 'CORRUPT_BODY', 'Image payload is completely empty or corrupted'

            if ext in ('.jpg', '.jpeg', '.jpe', '.jfif'):
                f.seek(max(0, size - 4096))
                if b'\xff\xd9' not in f.read():
                    return False, 'CORRUPT_BODY', 'Missing JPEG End-Of-Image marker (truncated payload)'
            elif ext == '.png':
                f.seek(max(0, size - 256))
                if b'IEND' not in f.read():
                    return False, 'CORRUPT_BODY', 'Missing PNG IEND marker (truncated payload)'
            elif ext == '.gif':
                f.seek(size - 1)
                if f.read(1) != b'\x3b':
                    return False, 'CORRUPT_BODY', 'Missing GIF EOF marker'

        if ext in ('.jpg', '.jpeg', '.jpe', '.jfif', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff'):
            try:
                from PIL import Image, ImageFile
                Image.MAX_IMAGE_PIXELS = None
                ImageFile.LOAD_TRUNCATED_IMAGES = False
                # We put a timeout or limit here in our minds, but Image.open and verify are usually very fast
                # verify() does not decode the whole image, it just reads the headers.
                with Image.open(path) as img:
                    img.verify()

                # Also do a quick check to see if the image is entirely one solid color
                # (which indicates a completely empty/dead payload that was just padded out by a decoder)
                with Image.open(path) as img:
                    img.load() # Actually decode the pixels
                    extrema = img.getextrema()
                    # extrema is ((rmin, rmax), (gmin, gmax), ...) for RGB, or (min, max) for L
                    if extrema:
                        if isinstance(extrema[0], tuple):
                            is_solid = all(cmin == cmax for cmin, cmax in extrema)
                        else:
                            is_solid = extrema[0] == extrema[1]

                        if is_solid:
                            return False, 'CORRUPT_BODY', 'Image payload is completely empty (solid color)'

            except ImportError:
                pass
            except Exception as e:
                return False, 'CORRUPT_BODY', f'Image stream corrupted ({e})'

        # Additional deep verification for RAW and TIFF files using ExifTool if available
        if ext in ('.tif', '.tiff', '.dng', '.arw', '.nef', '.cr2', '.cr3', '.heic'):
            try:
                import subprocess
                # Ask exiftool to print Warning, Error tags, AND ImageSize to ensure it actually sees an image
                proc = subprocess.run(
                    ['exiftool', '-a', '-Warning', '-Error', '-ImageSize', str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=5
                )
                output = proc.stdout.lower()

                has_image_size = False
                for line in output.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if any(x in line for x in ('bad format', 'bad ifd', 'bad directory', 'corrupt', 'unexpected end of file', 'format error', 'truncated')):
                        msg = line.split(":", 1)[-1].strip() if ":" in line else line
                        return False, 'CORRUPT_BODY', f'ExifTool detected corruption: {msg}'
                    if 'image size' in line:
                        has_image_size = True

                if not has_image_size:
                    return False, 'CORRUPT_BODY', 'ExifTool could not find any image data (no Image Size tag found)'

            except subprocess.TimeoutExpired:
                # Exiftool took too long, assume corrupt or skip
                return False, 'CORRUPT_BODY', 'ExifTool verification timed out'
            except Exception:
                # Ignore if exiftool is not installed or errors out
                pass

        return True, 'OK', 'Valid'
    except Exception as e:
        return False, 'CORRUPT_BODY', f'Verification error: {e}'


def repair_file(path, salvage_mode=True, force_salvage=False):
    ext = path.suffix.lower()

    if ext in ('.jpg', '.jpeg', '.jpe', '.jfif'):
        header = b'\xff\xd8'
    elif ext == '.png':
        header = b'\x89PNG\r\n\x1a\n'
    elif ext == '.gif':
        header = b'GIF89a'
    elif ext == '.bmp':
        header = b'BM'
    elif ext in ('.tif', '.tiff', '.arw', '.nef', '.dng'):
        header = b'II*\x00\x08\x00\x00\x00'
    elif ext == '.cr2':
        header = b'II*\x00\x10\x00\x00\x00CR\x02\x00'
    elif ext == '.cr3':
        header = b'\x00\x00\x00\x18ftypcrx \x00\x00\x00\x01crx isom'
    elif ext == '.heic':
        header = b'\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic'
    elif ext == '.webp':
        header = b'RIFF\x00\x00\x00\x00WEBP'
    else:
        return False, 'unsupported for auto-repair'

    header_len = len(header)

    try:
        with open(path, 'rb') as f:
            head = f.read(32)
            has_valid_header = head.startswith(header)
            mode = detect_corruption_mode(ext, head, header_len) if not has_valid_header else 'salvage'
    except Exception as e:
        return False, f"read error: {e}"

    local_outdir = path.parent / '_fixed'
    local_outdir.mkdir(parents=True, exist_ok=True)

    outpath = unique_target(local_outdir, path.name)
    tmp_path = unique_target(local_outdir, f"{outpath.name}.tmp")

    try:
        if has_valid_header:
            shutil.copy2(str(path), str(tmp_path))
        else:
            with open(path, 'rb') as fin, open(tmp_path, 'wb') as fout:
                if ext == '.webp':
                    riff_size = path.stat().st_size - 8 if mode == 'replace' else path.stat().st_size + header_len - 8
                    header = b'RIFF' + riff_size.to_bytes(4, byteorder='little', signed=False) + b'WEBP'

                fout.write(header)

                if mode == 'replace':
                    fin.seek(header_len)

                while chunk := fin.read(1024 * 1024):
                    fout.write(chunk)

        # Optional Pillow salvage / deep-clean
        # Do not use Pillow salvage for large TIFF files if it's too slow, but since we are doing
        # salvage it might just take a bit of time.
        if salvage_mode and ext in ('.jpg', '.jpeg', '.jpe', '.jfif', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp'):
            try:
                from PIL import Image, ImageFile
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                # Increase the max image pixels limit to prevent DecompressionBombError on large panoramas/RAWs
                Image.MAX_IMAGE_PIXELS = None

                with Image.open(tmp_path) as img:
                    img.load() # Force it to decode the salvageable parts

                    extrema = img.getextrema()
                    is_solid = False
                    if extrema:
                        if isinstance(extrema[0], tuple):
                            is_solid = all(cmin == cmax for cmin, cmax in extrema)
                        else:
                            is_solid = extrema[0] == extrema[1]

                    if is_solid:
                        raise ValueError("Image payload is completely empty (solid color)")

                    if img.mode not in ('RGB', 'RGBA', 'L'):
                        img = img.convert('RGB')

                    save_kwargs = {}
                    if ext in ('.jpg', '.jpeg', '.jpe', '.jfif'):
                        save_kwargs['quality'] = 95

                    img.save(outpath, **save_kwargs)

                tmp_path.unlink()
                return True, f"{outpath} (mode: salvage)"
            except ImportError:
                pass
            except Exception:
                pass

        is_valid, status, reason = verify_image(tmp_path, ext, header_len)

        # Robust bypass check: If verification failed but force_salvage is requested,
        # we strictly check if the file has any decodable, non-solid visual data left.
        # If it's completely un-renderable or just a blank square, we throw it out.
        can_bypass = False
        if force_salvage and not is_valid:
            try:
                from PIL import Image, ImageFile
                ImageFile.LOAD_TRUNCATED_IMAGES = True
                Image.MAX_IMAGE_PIXELS = None
                with Image.open(tmp_path) as img:
                    img.load()
                    extrema = img.getextrema()
                    is_solid = False
                    if extrema:
                        if isinstance(extrema[0], tuple):
                            is_solid = all(cmin == cmax for cmin, cmax in extrema)
                        else:
                            is_solid = extrema[0] == extrema[1]
                    if not is_solid:
                        can_bypass = True
            except Exception:
                pass

        if is_valid or can_bypass:
            tmp_path.rename(outpath)
            mode_str = mode if is_valid else f"{mode} - forced bypass"
            return True, f"{outpath} (mode: {mode_str})"
        else:
            tmp_path.unlink()
            return False, f"repair failed verification: {reason}"

    except OSError as e:
        if tmp_path.exists():
            tmp_path.unlink()
        if e.errno == errno.ENOSPC:
            raise e
        return False, f"write error: {e}"
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        return False, f"write error: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?', default='.', help='Folder to scan (defaults to current directory)')

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--repair', action='store_true',
                      help='Write repaired copies and organize originals into _good, _repaired, and _unfixable subfolders')
    mode.add_argument('--good-only', action='store_true',
                      help='Move only files with valid image headers and payloads into _good subfolders; leave all other files untouched')

    ap.add_argument('--strict', action='store_true', help='Discard salvaged files if they still fail strict structural verification')
    ap.add_argument('--no-salvage', action='store_true', help='Disable Pillow deep-cleaning and rescue of heavily corrupted/truncated images')
    ap.add_argument('--no-organize', action='store_true', help='Disable automatic organization of original files when repairing')
    ap.add_argument('-v', '--verbose', action='store_true', help='Print every file on a new line')
    ap.add_argument('-q', '--quiet', action='store_true', help='Disable dynamic progress reporting')
    args = ap.parse_args()

    root = Path(args.folder)

    rows = []
    counts = {}
    repaired_count = 0
    failed_count = 0
    empty_payload_count = 0
    moved_good_count = 0

    try:
        for p in root.rglob('*'):
            if not p.is_file():
                continue

            # Skip files inside folders this script itself creates.
            try:
                rel_parts = p.relative_to(root).parts
            except ValueError:
                rel_parts = p.parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue

            ext = p.suffix.lower()
            if ext not in SIGS:
                continue

            h = read_head(p)
            name, _ = SIGS[ext]
            is_valid, status, reason = verify_image(p, ext)

            row = {
                'path': str(p),
                'ext': ext,
                'size': p.stat().st_size,
                'first16_hex': h.hex(),
                'status': status,
                'type': name,
                'repair': ''
            }

            # --- --good-only: move valid files to _good, leave everything else ---
            if args.good_only:
                if is_valid:
                    try:
                        target = unique_target(p.parent / '_good', p.name)
                        shutil.move(str(p), str(target))
                        moved_good_count += 1
                        row['repair'] = f'moved to {target}'
                    except OSError as e:
                        row['repair'] = f'FAILED to move: {e}'

                counts[status] = counts.get(status, 0) + 1
                rows.append(row)

                if not args.quiet:
                    if args.verbose or not is_valid:
                        info = f" -> {row['repair']}" if row['repair'] else f" ({reason})" if not is_valid else ""
                        print(f"\r\033[K[{status}] {p}{info}")
                    if not args.verbose:
                        bad = counts.get('BAD_HEADER', 0) + counts.get('CORRUPT_BODY', 0)
                        print(f"\r\033[KScanning... {len(rows)} files processed | Bad/corrupted files: {bad}", end="", flush=True)
                continue

            organize_files = args.repair and not args.no_organize
            salvage = args.repair and not args.no_salvage
            force_salvage = args.repair and not args.strict

            if args.repair and not is_valid and ext in REPAIRABLE:
                try:
                    ok2, msg = repair_file(p, salvage_mode=salvage, force_salvage=force_salvage)

                    row['repair'] = msg if ok2 else f'FAILED: {msg}'
                    if ok2:
                        repaired_count += 1
                        if organize_files:
                            target = unique_target(p.parent / '_repaired', p.name)
                            shutil.move(str(p), str(target))
                    else:
                        failed_count += 1
                        is_empty_payload = "Image payload is completely empty" in msg
                        if is_empty_payload:
                            empty_payload_count += 1
                        if organize_files:
                            target_dir_name = '_empty' if is_empty_payload else '_unfixable'
                            target = unique_target(p.parent / target_dir_name, p.name)
                            shutil.move(str(p), str(target))
                except OSError as e:
                    if e.errno == errno.ENOSPC:
                        print("\n[FATAL] Disk out of space! Stopping process immediately.")
                        break
                    else:
                        row['repair'] = f'FAILED: write error: {e}'
                        failed_count += 1

            elif not is_valid:
                failed_count += 1
                if organize_files:
                    target = unique_target(p.parent / '_unfixable', p.name)
                    shutil.move(str(p), str(target))

            elif is_valid and organize_files:
                target = unique_target(p.parent / '_good', p.name)
                shutil.move(str(p), str(target))

            counts[status] = counts.get(status, 0) + 1
            rows.append(row)

            if not args.quiet:
                if args.repair:
                    repair_info = f" -> Fixed: {row['repair']}" if row['repair'] else ""
                else:
                    repair_info = f" -> ({reason})" if not is_valid else ""

                if args.verbose or not is_valid:
                    print(f"\r\033[K[{status}] {p}{repair_info}")

                if not args.verbose:
                    bad = counts.get('BAD_HEADER', 0) + counts.get('CORRUPT_BODY', 0)
                    print(f"\r\033[KScanning... {len(rows)} files processed | Bad/corrupted files: {bad}", end="", flush=True)

    except KeyboardInterrupt:
        print("\n\n[INFO] Process interrupted by user (Ctrl-C). Stopping early...")

    if not args.quiet and not args.verbose:
        print("\r\033[K", end="", flush=True)

    report = root / 'image_header_report.csv'
    with open(report, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['path', 'ext', 'size', 'first16_hex', 'status', 'type', 'repair'])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    print("\n--- Summary ---")
    print(f"Total files scanned : {len(rows)}")
    print(f"Good files (OK)     : {counts.get('OK', 0)}")
    print(f"Bad headers found   : {counts.get('BAD_HEADER', 0)}")
    if counts.get('CORRUPT_BODY', 0) > 0:
        print(f"Corrupt bodies found: {counts.get('CORRUPT_BODY', 0)}")
    if args.good_only:
        print(f"Moved good files    : {moved_good_count}")
        print("Bad files were left untouched.")
    if args.repair:
        print(f"Successfully fixed  : {repaired_count}")
        print(f"Failed to fix       : {failed_count}")
        if empty_payload_count > 0:
            print(f"  -> ({empty_payload_count} failed because the file was totally empty/garbage)")
        if repaired_count > 0:
            print("Repaired copies were saved to '_fixed' subfolders.")
        if not args.no_organize:
            print("Original files were categorized into '_good', '_repaired', '_unfixable', and '_empty' subfolders.")
    print(f"Report saved to     : {report}")


if __name__ == '__main__':
    main()
