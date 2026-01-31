import sys
import re
import requests
import os
import time
import json
from urllib.parse import urljoin

# Set Windows console to UTF-8
if sys.platform.startswith('win'):
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)

# Import Selenium
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

def get_source_via_browser(url):
    print(f"[*] Opening Firefox (headless) to load: {url}")
    options = Options()
    options.add_argument("-headless")
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    try:
        driver.get(url)
        print("[*] Waiting for Scribd to initialize assets (15 seconds)...")
        time.sleep(15) 
        return driver.page_source
    finally:
        driver.quit()

def download_scribd():
    if len(sys.argv) < 2:
        print("Usage: python scribdl.py <URL>")
        return

    input_val = sys.argv[1]
    source_text = get_source_via_browser(input_val) if input_val.startswith("http") else open(input_val, "r", encoding="utf-8").read()

    # 1. Setup Metadata & Folders
    title_match = re.search(r'<title>(.*?)</title>', source_text)
    title = title_match.group(1).split("|")[0].strip() if title_match else "Document"
    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
    
    asset_folder = f"{safe_title}_assets"
    if not os.path.exists(asset_folder): os.makedirs(asset_folder)

    # 2. Extract Asset Prefix and Font Info
    asset_prefix_match = re.search(r'docManager\.assetPrefix\s*=\s*["\']([^"\']+)["\']', source_text)
    asset_prefix = asset_prefix_match.group(1) if asset_prefix_match else ""

    # 3. Find Page JSONP links
    print("[*] Searching for pages...")
    urls = re.findall(r'(https://html\.scribdassets\.com/[a-z0-9]+/pages/\d+-[a-z0-9]+\.jsonp)', source_text)
    urls = sorted(list(set(urls)), key=lambda x: int(re.search(r'pages/(\d+)-', x).group(1)))

    if not urls:
        print("[!] No assets found. Check if the document is public.")
        return

    # 4. Download Fonts (The key to perfect layout)
    print("[*] Downloading custom fonts...")
    font_matches = re.findall(r'docManager\.addFont\(\s*(\d+)\s*,', source_text)
    font_css = ""
    for font_id in set(font_matches):
        font_name = f"ff{font_id}"
        # Construct .woff2 URL (Scribd's standard format)
        font_url = f"https://html.scribdassets.com/{asset_prefix}/fonts/{font_id.zfill(4)}.woff2"
        local_font_path = os.path.join(asset_folder, f"{font_name}.woff2")
        
        try:
            f_res = requests.get(font_url, timeout=10)
            if f_res.status_code == 200:
                with open(local_font_path, "wb") as f: f.write(f_res.content)
                font_css += f"""
                @font-face {{
                    font-family: '{font_name}';
                    src: url('{asset_folder}/{font_name}.woff2') format('woff2');
                }}
                div.{font_name} span {{ font-family: '{font_name}', Arial !important; }}
                """
        except: pass

    # 5. Process Pages
    combined_body = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in urls:
        p_num = re.search(r'pages/(\d+)-', url).group(1)
        print(f"    [>] Downloading Page {p_num}...", end="\r")
        try:
            res = requests.get(url, headers=headers)
            start = res.text.find('["') + 2
            end = res.text.rfind('"]')
            page_html = res.text[start:end].replace('\\"', '"').replace('\\/', '/').replace('\\n', '')

            # Scan for ALL image sources (img tags and CSS urls)
            img_links = re.findall(r'(?:orig="|url\()([^"\)]+\.(?:png|jpg|jpeg|webp|svg))', page_html)
            for img_url in set(img_links):
                full_img_url = img_url.replace("http://html.scribd.com", "https://html.scribdassets.com")
                img_name = full_img_url.split("/")[-1].split("?")[0]
                local_path = os.path.join(asset_folder, img_name)
                
                if not os.path.exists(local_path):
                    try:
                        img_data = requests.get(full_img_url, headers=headers).content
                        with open(local_path, "wb") as f_img: f_img.write(img_data)
                    except: pass
                
                # Replace paths in HTML
                page_html = page_html.replace(img_url, f"{asset_folder}/{img_name}")

            # Force all hidden elements to be visible
            page_html = page_html.replace('display:none', 'display:block').replace('opacity:0', 'opacity:1')
            page_html = page_html.replace('orig=', 'src=')

            combined_body.append(f'<div class="outer_page">{page_html}</div>')
        except: continue

    # 6. Final HTML with Fonts and Core Positioning
    html_template = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{title}</title>
    <style>
        {font_css}
        body {{ background: #525659; display: flex; flex-direction: column; align-items: center; padding: 20px; }}
        .outer_page {{ 
            position: relative; background: white; margin-bottom: 20px; 
            box-shadow: 0 0 15px rgba(0,0,0,0.3); width: 901px; height: 1279px; overflow: hidden; 
        }}
        .text_layer {{ 
            position: absolute; top: 0; left: 0; transform: scale(0.2); 
            transform-origin: top left; z-index: 5; width: 500%; height: 500%; 
        }}
        .text_layer div, .text_layer span {{ 
            white-space: nowrap; position: absolute; line-height: 1; color: transparent; 
        }}
        .image_layer {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }}
        .image_layer img {{ width: 100%; height: 100%; display: block; border: none; }}
        .absimg {{ position: absolute; }}
        ::selection {{ background: rgba(0, 150, 255, 0.3); }}
    </style></head><body>{"".join(combined_body)}</body></html>"""

    with open(f"{safe_title}.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"\n\n[+] SUCCESS! Document reconstructed with fonts and images.")

if __name__ == "__main__":
    download_scribd()