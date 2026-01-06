import sys
import os
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def extract_links(file_path):
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found.")
        sys.exit(1)

    try:
        # Open and parse the HTML file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
            soup = BeautifulSoup(html_content, 'html.parser')

        # Set to store unique identifiers to avoid duplicate links
        unique_identifiers = set()

        # Find all <a> tags with an href attribute
        links = soup.find_all('a', href=True)

        for link in links:
            href = link['href']
            
            # We look for links containing '/details/' which is the standard Archive structure
            if '/details/' in href:
                # Logic to extract the identifier
                # Example href: https://archive.org/details/647350_Han_Po_1933_07-03
                # Split by '/details/' and take the part after it
                try:
                    # Get the part after /details/
                    path_after_details = href.split('/details/')[1]
                    
                    # Clean up: remove query strings (?), fragments (#), or trailing slashes
                    # This ensures we get just "647350_Han_Po_1933_07-03" even if the link is complex
                    identifier = path_after_details.split('/')[0].split('?')[0].split('#')[0]

                    # Verify identifier isn't empty and hasn't been added yet
                    if identifier and identifier not in unique_identifiers:
                        unique_identifiers.add(identifier)
                        
                        # Generate the required output format
                        download_link = f"https://archive.org/compress/{identifier}"
                        print(download_link)

                except IndexError:
                    # In case the parsing fails on a specific link, skip it
                    continue

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Ensure a filename was passed
    if len(sys.argv) < 2:
        print("Usage: python archiveorglinkextractor.py <path_to_html_file>")
    else:
        input_file = sys.argv[1]
        extract_links(input_file)