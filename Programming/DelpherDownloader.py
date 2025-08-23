#!/usr/bin/env python3
import requests
import sys
import os
import re
import json

def get_page_count(base_identifier, session):
    """
    Finds the page count by loading the actual viewer page and extracting the
    embedded viewer configuration data from the HTML source.
    """
    try:
        # Construct the URL to the main viewer page for the first page of the item.
        # This page contains the configuration data for the entire item.
        full_identifier = f"{base_identifier}:mpeg21"
        view_url = f"https://www.delpher.nl/nl/kranten/view?identifier={full_identifier}"
        
        print(f"Fetching main page to find configuration: {view_url}")
        response = session.get(view_url)
        response.raise_for_status()

        # The configuration data is stored in a JavaScript variable within a <script> tag.
        # We will find this variable and parse it as JSON.
        # The pattern looks for 'window.viewerState = {' followed by the JSON object.
        match = re.search(r'window\.viewerState\s*=\s*(\{.*?\});', response.text)
        
        if not match:
            print("Fatal Error: Could not find the viewer configuration data in the page source.")
            print("The website structure may have changed.")
            return None

        # Extract the JSON string and parse it
        json_string = match.group(1)
        data = json.loads(json_string)
        
        # Navigate the JSON object to find the pageCount
        page_count = data.get('viewer', {}).get('pageCount')

        if page_count:
            print(f"Successfully found {page_count} pages in the publication.")
            return int(page_count)
        else:
            print("Error: Found configuration data, but it did not contain a page count.")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"HTTP Error fetching the main viewer page: {e}")
        return None
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error parsing the configuration data from the page: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while getting page count: {e}")
        return None


def download_delpher_item(resolver_url, save_directory="."):
    """
    Downloads all high-resolution images for a given Delpher resolver URL.
    """
    try:
        if "urn=" not in resolver_url:
            print("Error: The URL must be a resolver URL containing 'urn='.")
            return
            
        base_identifier = resolver_url.split("urn=")[1].split("&")[0]
        safe_identifier = base_identifier.replace(':', '-')
        
        print(f"Starting process for identifier: {base_identifier}")
        session = requests.Session()

        page_count = get_page_count(base_identifier, session)
        if not page_count:
            print("Could not determine page count. Aborting.")
            return

        for page_num in range(1, page_count + 1):
            page_str = f"{page_num:03}"
            page_identifier = f"{base_identifier}:mpeg21:p{page_str}"
            image_url = f"https://www.delpher.nl/nl/api/downloadimage?id={page_identifier}"

            try:
                print(f"Downloading page {page_num}/{page_count}...")
                response = session.get(image_url, stream=True)
                response.raise_for_status()

                filename = f"{safe_identifier}_p{page_str}.jpeg"
                save_path = os.path.join(save_directory, filename) 

                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
            except requests.exceptions.RequestException as e:
                print(f"Could not download page {page_num}. Error: {e}")
                continue

        print(f"\nDownload complete! Images are saved in: {os.path.abspath(save_directory)}")

    except IndexError:
        print("Error: Could not parse the identifier from the URL.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python DelpherDownloader.py <url> [optional_save_directory]")
        print("Example: python DelpherDownloader.py https://resolver.kb.nl/resolve?urn=MMKB32:164595010")
        sys.exit(1)
        
    url_to_download = sys.argv[1]
    output_dir = "."
    if len(sys.argv) == 3:
        output_dir = sys.argv[2]
        os.makedirs(output_dir, exist_ok=True)

    download_delpher_item(url_to_download, output_dir)