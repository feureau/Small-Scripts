import argparse
import os
import sys
import time
import requests
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from bs4 import BeautifulSoup

def execute_download_sequence(target_url: str, cookie: str = None) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://ctext.org/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    parsed_url = urlparse(target_url)
    query_parameters = parse_qs(parsed_url.query)
    
    if 'file' not in query_parameters:
        sys.stderr.write("Error: The provided URL lacks the requisite 'file' parameter.\n")
        sys.exit(1)
        
    file_identifier = query_parameters['file'][0]
    output_directory = f"ctext_document_{file_identifier}"
    os.makedirs(output_directory, exist_ok=True)
    
    sys.stdout.write(f"Initializing extraction sequence. Output directory established: {output_directory}\n")

    current_page_index = int(query_parameters.get('page', [1])[0])
    http_session = requests.Session()
    http_session.headers.update(headers)
    if cookie:
        http_session.headers.update({"Cookie": cookie})

    while True:
        query_parameters['page'] = [str(current_page_index)]
        encoded_query = urlencode(query_parameters, doseq=True)
        iterative_url = urlunparse(parsed_url._replace(query=encoded_query))
        
        sys.stdout.write(f"Transmitting request for page index {current_page_index}: {iterative_url}\n")
        
        response = http_session.get(iterative_url)
        if response.status_code != 200:
            sys.stdout.write(f"Extraction terminated: Server returned HTTP status code {response.status_code}.\n")
            break
            
        if "Please confirm that you are human" in response.text:
            sys.stderr.write("Error: ctext.org is requesting a CAPTCHA confirmation (access patterns assigned low trust).\n")
            sys.stderr.write("Solution: Solve the CAPTCHA in your browser and provide your browser's cookie via the --cookie argument.\n")
            break

        document_tree = BeautifulSoup(response.text, 'html.parser')
        
        primary_image_element = document_tree.find('img', id='previmg')
        
        if not primary_image_element:
            for img_tag in document_tree.find_all('img'):
                src_attribute = img_tag.get('src', '')
                if any(k in src_attribute for k in ['library.ctext.org', 'library.pl', 'res=', 'file=']):
                    primary_image_element = img_tag
                    break
                
        if not primary_image_element:
            sys.stdout.write("Extraction terminated: Primary document image unidentifiable or boundary of document reached.\n")
            break
            
        image_source_url = primary_image_element['src']
        if not image_source_url.startswith('http'):
            base_url_prefix = f"{parsed_url.scheme}://{parsed_url.netloc}"
            image_source_url = base_url_prefix + ('/' if not image_source_url.startswith('/') else '') + image_source_url
                
        image_response = http_session.get(image_source_url, stream=True)
        if image_response.status_code == 200:
            content_type_header = image_response.headers.get('Content-Type', '')
            file_extension = 'jpg'
            if 'png' in content_type_header:
                file_extension = 'png'
            elif 'gif' in content_type_header:
                file_extension = 'gif'
                
            output_filename = os.path.join(output_directory, f"page_{current_page_index:04d}.{file_extension}")
            with open(output_filename, 'wb') as output_file:
                for data_chunk in image_response.iter_content(1024):
                    output_file.write(data_chunk)
            sys.stdout.write(f"Data successfully committed to disk: {output_filename}\n")
        else:
            sys.stderr.write(f"Extraction error: Failed to retrieve image data. HTTP status code: {image_response.status_code}\n")
            break

        current_page_index += 1
        time.sleep(2) 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download library images from ctext.org")
    parser.add_argument("url", help="The ctext.org library URL to extract from")
    parser.add_argument("--cookie", help="Optional session cookie string to authenticate requests")
    
    args = parser.parse_args()
    execute_download_sequence(args.url, args.cookie)