import os
import requests
from bs4 import BeautifulSoup

DOH_URL = "https://cloudflare-dns.com/dns-query"
HEADERS = {
    'Accept': 'application/dns-json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0',
    'Referer': 'https://www.google.com'
}

def resolve_domain_doh(domain):
    """
    Resolves the IP address of a domain using DNS over HTTPS (DoH).
    """
    response = requests.get(f"{DOH_URL}?name={domain}&type=A", headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    ip_address = data['Answer'][0]['data']
    return ip_address

def get_urls_from_files(folder_path):
    """
    Reads .url files from the specified folder and extracts URLs.
    """
    urls = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.url'):
            with open(os.path.join(folder_path, file_name), 'r') as file:
                for line in file:
                    if line.startswith("URL="):
                        url = line.strip().split('=')[1]
                        urls.append(url)
                        break
    return urls

def scrape_pages(urls):
    """
    Scrapes the entire text content of pages from the given URLs.
    Displays the output on the console and saves it to a text file.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    
    with open("scraped_pages.txt", "w", encoding="utf-8") as file:
        for url in urls:
            try:
                # Make the request and get the page content
                response = session.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract the visible text from the page
                page_text = soup.get_text(separator="\n").strip()
                
                # Display the scraped data on the console
                print(f"URL: {url}")
                print(f"Page Content:\n{page_text[:500]}...")  # Display the first 500 characters for brevity
                print("\n" + "="*80 + "\n")
                
                # Write the URL and page content to the file
                file.write(f"URL: {url}\n")
                file.write(f"Page Content:\n{page_text}\n")
                file.write("\n" + "="*80 + "\n")
            
            except requests.exceptions.HTTPError as e:
                print(f"Failed to scrape {url}: {e}")
                file.write(f"Failed to scrape {url}: {e}\n")
                file.write("\n" + "="*80 + "\n")
    
    print("Scraping complete! Data saved to 'scraped_pages.txt'.")

if __name__ == "__main__":
    folder_path = input("Enter the folder path containing .url files: ")
    urls = get_urls_from_files(folder_path)
    
    if urls:
        print(f"Found {len(urls)} URLs. Starting to scrape...")
        scrape_pages(urls)
    else:
        print("No .url files found or no URLs extracted.")
