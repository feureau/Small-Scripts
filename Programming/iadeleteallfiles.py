#!/usr/bin/env python3
"""
iadeleteallfiles.py

A utility script to delete ALL files within a specified Internet Archive item.
Includes a retry mechanism with exponential backoff to handle server-side
rate limiting (503 errors).

*** EXTREME CAUTION IS ADVISED ***
This action is irreversible. Once the files are deleted, they cannot be recovered
through the API. Always double-check the identifier before proceeding.

Functionality:
 1. Fetches a list of all files in the specified Internet Archive item.
 2. Displays the item identifier and the total number of files to be deleted.
 3. Requires the user to re-enter the item identifier as a confirmation safety check.
 4. If confirmed, it proceeds to delete each file one by one.
 5. If a deletion fails due to a server-side 503 error, it will automatically
    retry with an increasing (exponential) delay.

Usage:
    python iadeleteallfiles.py <identifier>

Arguments:
    identifier   (required) The Archive.org item identifier whose files will be deleted.

Example:
    python iadeleteallfiles.py my-test-item-for-deletion

Requirements:
  - Python 3.x
  - internetarchive module (pip install internetarchive)
  - Internet connectivity and valid IA credentials with delete privileges (ia.configure)

Behavior:
  - Aborts immediately if the confirmation does not match the identifier.
  - Prints the status of each deletion attempt and any retry attempts.
"""
import sys
import time
import internetarchive as ia

# --- Constants for the retry mechanism ---
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 5

def main():
    if len(sys.argv) != 2:
        print("Usage: python iadeleteallfiles.py <identifier>")
        sys.exit(1)

    IDENT = sys.argv[1]

    # --- Step 1: Get the item and list all files ---
    print(f"Fetching file list for item: '{IDENT}'...")
    try:
        item = ia.get_item(IDENT)
        # We only care about the 'name' which is the key for deletion
        files_to_delete = [f['name'] for f in item.files]
    except Exception as e:
        print(f"Error: Could not retrieve item '{IDENT}'. Please check the identifier and your connection.")
        print(f"Details: {e}")
        sys.exit(1)

    if not files_to_delete:
        print("No files found in this item. Nothing to do.")
        sys.exit(0)

    # --- Step 2: Implement a strong confirmation safety check ---
    print("\n" + "="*60)
    print("!! WARNING: IRREVERSIBLE ACTION !!")
    print("="*60)
    print(f"You are about to delete {len(files_to_delete)} files from the item: '{IDENT}'")
    print("This action CANNOT be undone.")
    print("\nTo confirm this action, please type the identifier again.")

    confirmation = input(f"Confirm by typing '{IDENT}': ")

    if confirmation.strip() != IDENT:
        print("\nConfirmation did not match. Deletion aborted.")
        sys.exit(0)

    # --- Step 3: Proceed with deletion if confirmed ---
    print("\nConfirmation accepted. Proceeding with deletion...")

    success_count = 0
    failure_count = 0

    # Delete files one by one to get individual status updates
    for filename in files_to_delete:
        print(f"Deleting: {filename} ... ", end='', flush=True)

        retries = 0
        backoff_seconds = INITIAL_BACKOFF_SECONDS
        deleted_successfully = False

        while retries < MAX_RETRIES:
            try:
                # The delete function can take a list, but one-by-one gives better feedback.
                ia.delete(IDENT, files=[filename])
                print("SUCCESS")
                success_count += 1
                deleted_successfully = True
                break  # Exit the retry loop on success

            except Exception as e:
                # Check if the error is the specific 503 rate-limiting error
                if '503' in str(e) and 'MaxRetryError' in str(e):
                    retries += 1
                    if retries < MAX_RETRIES:
                        print(f"FAILED (503 Server Error). Retrying in {backoff_seconds}s... ", end='', flush=True)
                        time.sleep(backoff_seconds)
                        backoff_seconds *= 2  # Exponentially increase backoff time
                    else:
                        # All retries have failed
                        print(f"\nFAILED. All {MAX_RETRIES} retries failed for this file.")
                        break # Exit retry loop, this file has failed
                else:
                    # It's a different, unexpected error, so don't retry.
                    print(f"FAILED. Reason: {e}")
                    break # Exit retry loop, this file has failed

        if not deleted_successfully:
            failure_count += 1


    print("\n" + "="*60)
    print("Deletion process complete.")
    print(f"Successfully deleted: {success_count} files")
    print(f"Failed to delete:    {failure_count} files")
    print("="*60)


if __name__ == '__main__':
    main()