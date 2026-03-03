import fitz  # PyMuPDF
import argparse
import pathlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


def _safe_folder_name(name: str) -> str:
    """Return a filesystem-safe folder component for auto-generated output folders."""
    # Windows-disallowed characters in file/folder names.
    invalid_chars = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid_chars else ch for ch in name)
    # Trim control chars and trailing dots/spaces (invalid on Windows).
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32).rstrip(" .")
    return cleaned or "output"


def get_output_path(pdf_path, output_dir=None, multiple_pdfs=False):
    """Resolve output directory for a given PDF."""
    safe_stem = _safe_folder_name(pdf_path.stem)
    if output_dir:
        if multiple_pdfs:
            return output_dir / safe_stem
        return output_dir
    return pdf_path.parent / safe_stem


def process_single_pdf(pdf_path, output_dir=None, multiple_pdfs=False, index=None, total=None):
    """Extract images from a single PDF and return count of extracted images."""
    images_in_pdf = 0
    progress = f" ({index}/{total})" if index and total else ""
    print(f"\n--- Processing PDF{progress}: {pdf_path.name} ---")

    output_path = get_output_path(pdf_path, output_dir=output_dir, multiple_pdfs=multiple_pdfs)
    output_path.mkdir(parents=True, exist_ok=True)

    # Cache extracted image payloads by xref; many PDFs reuse the same xref.
    xref_cache = {}

    try:
        pdf_document = fitz.open(pdf_path)
        for page_index in range(len(pdf_document)):
            page = pdf_document.load_page(page_index)
            image_list = page.get_images(full=True)

            if not image_list:
                continue

            print(f"  Page {page_index + 1}: Found {len(image_list)} image reference(s).")

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    if xref not in xref_cache:
                        base_image = pdf_document.extract_image(xref)
                        if not base_image:
                            print(f"    - Could not extract image data for xref {xref} on page {page_index + 1}.")
                            continue
                        xref_cache[xref] = (base_image["image"], base_image["ext"])

                    image_bytes, image_ext = xref_cache[xref]
                    image_filename = f"page{page_index + 1:03d}_img{img_index + 1:03d}.{image_ext}"
                    save_path = output_path / image_filename

                    with open(save_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    images_in_pdf += 1

                except Exception as img_err:
                    print(f"    - ERROR processing image {img_index + 1} (xref {xref}) on page {page_index + 1}: {img_err}")

        pdf_document.close()
        print(f"  -> Extracted {images_in_pdf} image(s) to folder '{output_path}'")
        return images_in_pdf

    except Exception as pdf_err:
        print(f"  ERROR: Could not process PDF file {pdf_path.name}. Reason: {pdf_err}")
        return 0

def extract_images_from_pdfs(pdf_files, output_dir=None):
    """
    Extracts embedded images from each PDF in the provided list
    and saves them into dedicated subfolders.

    Args:
        pdf_files (list of pathlib.Path): List of PDF files to process.
        output_dir (pathlib.Path, optional): Optional output directory override.
    """
def extract_images_from_pdfs(pdf_files, output_dir=None, jobs=1):
    pdf_count = len(pdf_files)
    total_images_extracted = 0

    if not pdf_files:
        print("No PDF files to process.")
        return

    print(f"Found {pdf_count} PDF file(s) to process.")

    multiple_pdfs = len(pdf_files) > 1
    worker_count = max(1, min(jobs, len(pdf_files)))

    if worker_count > 1 and multiple_pdfs:
        print(f"Using {worker_count} parallel worker(s).")
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(
                    process_single_pdf,
                    pdf_path,
                    output_dir,
                    multiple_pdfs,
                    i + 1,
                    len(pdf_files),
                ): pdf_path
                for i, pdf_path in enumerate(pdf_files)
            }
            for future in as_completed(futures):
                total_images_extracted += future.result()
    else:
        for i, pdf_path in enumerate(pdf_files):
            total_images_extracted += process_single_pdf(
                pdf_path,
                output_dir=output_dir,
                multiple_pdfs=multiple_pdfs,
                index=i + 1,
                total=len(pdf_files),
            )

    print(f"\n--- Finished ---")
    print(f"Processed {pdf_count} PDF file(s).")
    print(f"Total images extracted: {total_images_extracted}")


def determine_worker_count(jobs_arg, pdf_count):
    """
    Determine worker count from CLI flag:
    - No -j passed: 1
    - -j passed without value: auto
    - -j N: explicit N
    """
    if pdf_count <= 1:
        return 1

    if jobs_arg is None:
        return 1

    if jobs_arg == "auto":
        cpu_count = os.cpu_count() or 4
        # Keep one core free when possible and cap by number of PDFs.
        return max(1, min(pdf_count, max(2, cpu_count - 1)))

    try:
        jobs = int(jobs_arg)
    except ValueError:
        raise ValueError(f"Invalid jobs value: {jobs_arg}. Use -j, -j auto, or -j <positive-int>.")

    if jobs < 1:
        raise ValueError(f"Invalid jobs value: {jobs}. It must be >= 1.")

    return max(1, min(jobs, pdf_count))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from PDF files.")
    parser.add_argument("files", nargs="*", help="PDF files to process. If empty, scans current directory.")
    parser.add_argument("-o", "--output", help="Output directory. For single files, this is the destination folder. For multiple files, this is the root folder.")
    parser.add_argument(
        "-j",
        "--jobs",
        nargs="?",
        const="auto",
        default=None,
        help="Parallel workers for multiple PDFs. Omit flag: single-thread. Use -j for auto. Use -j N for explicit workers.",
    )

    args = parser.parse_args()

    pdf_to_process = []
    
    # Resolve output directory if provided
    output_dir = pathlib.Path(args.output) if args.output else None

    if not args.files:
        # Default behavior: scan current working directory
        cwd = pathlib.Path.cwd()
        print(f"No arguments provided. Scanning for PDF files in: {cwd}")
        pdf_to_process.extend(cwd.glob('*.pdf'))
    else:
        for arg in args.files:
            path = pathlib.Path(arg)
            # Glob expansion support for shells that don't do it automatically (like Windows CMD)
            # However, argparse usually receives expanded lists if the shell handles it (bash/zsh/powershell).
            # For robustness, we check if it contains wildcards or just treat as file/dir.
            if '*' in arg or '?' in arg:
                 # Manually globbing if passed as string literal or from non-expanding shell
                 # This is a bit of an edge case but good for robustness
                 parent = pathlib.Path(arg).parent
                 if parent.name == '': parent = pathlib.Path('.')
                 pattern = pathlib.Path(arg).name
                 pdf_to_process.extend(parent.glob(pattern))
            elif path.is_file():
                if path.suffix.lower() == '.pdf':
                    pdf_to_process.append(path)
                else:
                    print(f"Skipping non-PDF file: {path}")
            elif path.is_dir():
                print(f"Scanning directory: {path}")
                pdf_to_process.extend(path.glob('*.pdf'))
            elif not path.exists():
                 # Attempt to treat as glob pattern if path doesn't exist
                 # e.g. user typed *.pdf in a shell that didn't expand it
                 parent = path.parent
                 if str(parent) == '.': parent = pathlib.Path.cwd()
                 pattern = path.name
                 found = list(parent.glob(pattern))
                 if found:
                     pdf_to_process.extend([p for p in found if p.suffix.lower() == '.pdf'])
                 else:
                     print(f"Argument not found (skipping): {arg}")

    if pdf_to_process:
        # Sort to ensure consistent processing order
        pdf_to_process.sort()
        # Filter duplicates just in case
        pdf_to_process = list(dict.fromkeys(pdf_to_process))
        try:
            jobs = determine_worker_count(args.jobs, len(pdf_to_process))
        except ValueError as err:
            print(err)
            raise SystemExit(2)

        if args.jobs == "auto":
            print(f"Auto-selected parallel workers: {jobs}")

        extract_images_from_pdfs(pdf_to_process, output_dir, jobs=jobs)
    else:
        print("No valid PDF files found to process.")
