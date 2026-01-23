#!/usr/bin/env python3
"""
iadeleteitems.py

Delete Internet Archive items from a list of URLs or item IDs.

Usage:
  python iadeleteitems.py <input_file> [--threads N]

Arguments:
  input_file    Path to a text file containing IA URLs or item identifiers.
  --threads     Number of concurrent delete threads (default: 5).

The input file can contain:
  - Full URLs: https://archive.org/compress/686220
  - Details URLs: https://archive.org/details/myitem
  - Download URLs: https://archive.org/download/myitem/file.zip
  - Just item IDs: 686220

Requirements:
  pip install internetarchive tqdm
"""

import sys
import os
import re
import argparse
import queue
from concurrent.futures import ThreadPoolExecutor, wait

try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' module not found. Please install it:\n  pip install tqdm")
    sys.exit(1)

import internetarchive as ia

# Global queue for managing tqdm positions for threads
position_queue = queue.Queue()


def extract_item_id(line):
    """
    Extract the Internet Archive item identifier from a URL or raw ID.
    
    Handles formats like:
      - https://archive.org/compress/itemid
      - https://archive.org/details/itemid
      - https://archive.org/download/itemid/filename
      - itemid (raw)
    """
    line = line.strip()
    if not line:
        return None
    
    # Pattern to match common IA URL formats
    # Matches: /compress/, /details/, /download/, /metadata/, /serve/
    url_pattern = r'archive\.org/(?:compress|details|download|metadata|serve)/([^/\s?#]+)'
    match = re.search(url_pattern, line)
    
    if match:
        return match.group(1)
    
    # If no URL pattern matched, assume it's a raw item ID
    # Basic validation: no spaces, not a URL without archive.org
    if ' ' not in line and '://' not in line:
        return line
    
    return None


def delete_item_worker(item_id, position, cascade=True):
    """
    Worker function to delete a single IA item.
    Uses ia.delete() to remove all files from an item.
    """
    try:
        item = ia.get_item(item_id)
        
        # Check if item exists
        if not item.exists:
            tqdm.write(f"[SKIP] Item does not exist: {item_id}")
            return False, item_id, "not found"
        
        # Delete all files in the item using ia.delete()
        # cascade=True ensures all derived files are also deleted
        responses = ia.delete(item_id, cascade=cascade)
        
        # Check responses for success
        # responses is a list of Response objects
        if responses:
            success = all(r.status_code == 200 for r in responses if hasattr(r, 'status_code'))
        else:
            # No files to delete or empty response
            success = True
        
        if success:
            tqdm.write(f"[DELETED] {item_id}")
            return True, item_id, "deleted"
        else:
            # Get error details if available
            for r in responses:
                if hasattr(r, 'status_code') and r.status_code != 200:
                    tqdm.write(f"[FAILED] {item_id} - Status {r.status_code}")
                    break
            else:
                tqdm.write(f"[FAILED] {item_id} - Check permissions or item status")
            return False, item_id, "failed"
            
    except Exception as e:
        tqdm.write(f"[ERROR] {item_id}: {e}")
        return False, item_id, str(e)


def process_delete_list(input_file, num_threads):
    """
    Reads item IDs/URLs from a file and deletes them concurrently.
    """
    print(f"Reading items from '{input_file}'...")
    
    with open(input_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Extract item IDs from each line
    items = []
    for line in lines:
        item_id = extract_item_id(line)
        if item_id:
            items.append(item_id)
        else:
            print(f"[WARN] Could not parse: {line}")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_items = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    items = unique_items
    
    if not items:
        print("No valid items found.")
        return
    
    print(f"Found {len(items)} unique items to delete with {num_threads} threads.")
    print("-" * 50)
    
    # Confirmation prompt
    confirm = input(f"\n⚠️  WARNING: This will DELETE {len(items)} items permanently!\nType 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return
    
    print()
    
    # Initialize position queue for thread progress bars
    for i in range(num_threads):
        position_queue.put(i + 1)
    
    # Statistics
    results = {'deleted': 0, 'failed': 0, 'skipped': 0}
    
    # Main progress bar (Total Items)
    with tqdm(total=len(items), unit='item', desc="Total Progress", position=0) as main_bar:
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            
            def submit_job(item_id):
                pos = position_queue.get()
                try:
                    success, _, status = delete_item_worker(item_id, pos)
                    if success:
                        results['deleted'] += 1
                    elif status == "not found":
                        results['skipped'] += 1
                    else:
                        results['failed'] += 1
                finally:
                    position_queue.put(pos)
                    main_bar.update(1)
            
            futures = [executor.submit(submit_job, item_id) for item_id in items]
            wait(futures)
    
    # Final summary
    print("\n" + "=" * 50)
    print("DELETION SUMMARY")
    print("=" * 50)
    print(f"  Deleted:  {results['deleted']}")
    print(f"  Skipped:  {results['skipped']} (not found)")
    print(f"  Failed:   {results['failed']}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Delete Internet Archive items from a list of URLs or IDs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python iadeleteitems.py links.txt
  python iadeleteitems.py items.txt --threads 10

Input file format (one per line):
  https://archive.org/compress/686220
  https://archive.org/details/myitem
  myitem123
        """
    )
    parser.add_argument("input", help="Text file containing IA URLs or item identifiers (one per line)")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent delete threads (default: 5)")
    
    args = parser.parse_args()
    
    if not os.path.isfile(args.input):
        print(f"Error: File not found: {args.input}")
        sys.exit(1)
    
    process_delete_list(args.input, args.threads)


if __name__ == "__main__":
    main()
