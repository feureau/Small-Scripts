import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager


def download_hathi_max_quality():
    if len(sys.argv) < 2:
        print("Usage: python dlhathi.py <URL>")
        return

    input_url = sys.argv[1]
    base_id_match = re.search(r"id=([a-z0-9\.]+)", input_url)
    if not base_id_match:
        print("[!] Could not parse base ID from URL")
        return
    base_id = base_id_match.group(1)

    start_seq = 1
    seq_match = re.search(r"seq=(\d+)", input_url)
    if seq_match:
        start_seq = int(seq_match.group(1))

    # Setup Download Directory
    download_dir = os.path.join(os.getcwd(), f"{base_id}_600dpi_TIF")
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    print(f"[*] Target Directory: {download_dir}")

    options = Options()
    # Configure Firefox to auto-save TIFFs
    options.set_preference("browser.download.dir", download_dir)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "image/tiff,image/x-tiff,application/octet-stream",
    )
    options.set_preference("pdfjs.disabled", True)

    driver = webdriver.Firefox(
        service=Service(GeckoDriverManager().install()), options=options
    )

    try:
        # Initial load to get total pages
        driver.get(f"https://babel.hathitrust.org/cgi/pt?id={base_id}&view=1up&seq=1")
        time.sleep(5)
        total_pages = int(driver.execute_script("return HT.params.totalSeq"))

        print(f"[*] Starting sequence for {total_pages} pages at 600 DPI...")

        for seq in range(start_seq, total_pages + 1):
            driver.get(
                f"https://babel.hathitrust.org/cgi/pt?id={base_id}&view=1up&seq={seq}"
            )
            print(f"[>] Page {seq}/{total_pages}...", end="\r")

            try:
                wait = WebDriverWait(driver, 20)

                # 1. Expand Sidebar if closed
                download_sect = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".download-options")
                    )
                )
                if "active" not in download_sect.get_attribute("class"):
                    header = wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, "#download-options-header, .download-options h2")
                        )
                    )
                    driver.execute_script("arguments[0].click();", header)
                    time.sleep(1)

                # 2. Select TIFF Radio
                tif_radio = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='tif']"))
                )
                driver.execute_script("arguments[0].click();", tif_radio)
                time.sleep(1)  # Wait for resolution dropdown to update

                # 3. Select 600 DPI / Full
                res_dropdown_el = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='size']"))
                )
                res_dropdown = Select(res_dropdown_el)

                # Look for "600" or "Full" in the text
                found_res = False
                for option in res_dropdown.options:
                    if "600" in option.text or "Full" in option.text:
                        res_dropdown.select_by_visible_text(option.text)
                        found_res = True
                        break

                if not found_res:
                    # Fallback to the highest available if 600 isn't listed
                    res_dropdown.select_by_index(len(res_dropdown.options) - 1)

                # 4. Click Download Button
                download_btn = wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button.download-button, a[data-tracking-action='Download Image'], .download-options button.btn-primary")
                    )
                )
                driver.execute_script("arguments[0].click();", download_btn)

                # 5. Cool-down to prevent rate-limiting and allow file generation
                # 600dpi TIFFs are large and take time to generate
                time.sleep(7)

                # Handle Robot Check
                if (
                    "robot" in driver.page_source.lower()
                    or "recaptcha" in driver.page_source.lower()
                ):
                    print(
                        "\n[!] CAPTCHA detected. Solve it in Firefox and the script will continue."
                    )
                    while "robot" in driver.page_source.lower():
                        time.sleep(2)
                    print("[*] Resuming...")

            except Exception as e:
                print(f"\n[!] Skip/Error on Page {seq}: {e}")
                continue

        print("\n[+] Extraction Complete.")

    finally:
        driver.quit()


if __name__ == "__main__":
    download_hathi_max_quality()
