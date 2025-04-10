import requests
from bs4 import BeautifulSoup
import re # Regular expressions for matching URLs
import sys # To get command line arguments
import time # To add a small delay
import os # Import the os module to get the current working directory

# --- Configuration ---
# Base filename for the output
OUTPUT_FILENAME_BASE = "twitch_clips.txt"
# Use a realistic User-Agent header to mimic a browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}
TWITCH_BASE_URL = "https://www.twitch.tv"
# -------------------

def find_clip_links(soup):
    """
    Finds all links that appear to be Twitch clip links within the parsed HTML.
    Twitch structure changes, so this might need adjustments.
    """
    clip_links = set()
    links = soup.find_all('a', href=re.compile(r'^(/[^/]+/clip/|/clip/)[\w-]+$'))

    for link in links:
        href = link.get('href')
        if href:
            if re.match(r'^(/[^/]+/clip/|/clip/)[\w-]+$', href):
                 if href.startswith('/'):
                    absolute_url = TWITCH_BASE_URL + href
                    clip_links.add(absolute_url)

    return list(clip_links)

def scrape_twitch_clips(channel_clips_url, output_file_path): # Renamed parameter for clarity
    """
    Fetches the Twitch clips page and extracts clip URLs, saving to the specified full path.
    """
    print(f"Attempting to fetch: {channel_clips_url}")
    try:
        response = requests.get(channel_clips_url, headers=HEADERS, timeout=20)
        response.raise_for_status()

        print("Page fetched successfully. Parsing HTML...")
        soup = BeautifulSoup(response.text, 'lxml')

        clip_urls = find_clip_links(soup)

        if not clip_urls:
            print("\n--- WARNING ---")
            print("No clip links found using the standard method.")
            print("This might be because:")
            print(" 1. The page structure has changed on Twitch.")
            print(" 2. Clips are loaded dynamically with JavaScript (requests can't run JS).")
            print(" 3. There are simply no clips in the selected range on that channel.")
            print("Consider inspecting the page source manually or trying Selenium.")
            print("---------------\n")
            return False

        print(f"Found {len(clip_urls)} unique clip links.")

        # --- Save to file using the full path provided ---
        try:
            # output_file_path now contains the full path including the working directory
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for url in clip_urls:
                    f.write(url + '\n')
            # Use the full path in the success message
            print(f"Successfully saved clip URLs to '{output_file_path}'")
            return True
        except IOError as e:
            print(f"Error writing to file '{output_file_path}': {e}")
            return False

    except requests.exceptions.Timeout:
        print(f"Error: Request timed out while trying to fetch {channel_clips_url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {channel_clips_url}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        print(f"Using URL from command line: {target_url}")
    else:
        target_url = "https://www.twitch.tv/hasanabi/videos?featured=true&filter=clips&range=24hr"
        print(f"Using default URL: {target_url}")

    if not target_url.startswith("https://www.twitch.tv/") or "filter=clips" not in target_url:
        print("Warning: The URL might not be a valid Twitch clips page.")

    # --- Determine the output path ---
    # Get the current working directory (where the script was called FROM)
    working_directory = os.getcwd()
    # Combine the working directory with the base filename to get the full path
    full_output_path = os.path.join(working_directory, OUTPUT_FILENAME_BASE)
    print(f"Output file will be saved to: {full_output_path}")
    # --------------------------------

    # Pass the full output path to the scraping function
    scrape_twitch_clips(target_url, full_output_path)

    # time.sleep(1) # Optional delay