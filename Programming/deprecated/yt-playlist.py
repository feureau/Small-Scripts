from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

def extract_playlist_urls(playlist_url):
    """
    Extracts video URLs from a YouTube playlist URL (including "Uploads" feeds).
    Saves them to the user's Downloads folder as 'video_urls.txt'.
    """

    # ----- Configure Firefox -----
    options = webdriver.FirefoxOptions()
    # Uncomment below to run headless (invisible browser)
    # options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)

    try:
        # ----- 1. Open the YouTube Playlist URL -----
        driver.get(playlist_url)
        
        # OPTIONAL: Dismiss any cookie banner (depends on region)
        dismiss_cookie_banner(driver)

        # ----- 2. Wait until some video elements appear or timeout -----
        # We use a combined CSS selector that often catches both standard playlist
        # items and "Uploads" feed items:
        combined_selector = (
            "a.yt-simple-endpoint.style-scope.ytd-playlist-video-renderer,"
            "a.yt-simple-endpoint.style-scope.ytd-grid-video-renderer"
        )
        wait = WebDriverWait(driver, 20)
        
        # Wait for at least one video link to appear
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, combined_selector)))

        # ----- 3. Attempt to auto-scroll / load all videos -----
        scroll_to_load_all(driver, combined_selector)

        # ----- 4. Try a final click on "Load more" if it exists -----
        # (Not always present, but we'll try once.)
        try_click_load_more(driver)

        # Just in case there's more to load:
        scroll_to_load_all(driver, combined_selector)

        # ----- 5. Find all video links -----
        video_elements = driver.find_elements(By.CSS_SELECTOR, combined_selector)
        print(f"Found {len(video_elements)} video elements.")

        # Extract hrefs (filter out None or empty)
        video_urls = [elem.get_attribute("href") for elem in video_elements if elem.get_attribute("href")]
        video_urls = list(dict.fromkeys(video_urls))  # Remove duplicates, preserve order
        print(f"Extracted {len(video_urls)} unique video URLs.")

        # ----- 6. Save to file in Downloads -----
        output_folder = os.path.join(os.path.expanduser("~"), "Downloads")
        output_file = os.path.join(output_folder, "video_urls.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            for url in video_urls:
                f.write(url + "\n")

        print(f"Video URLs saved to '{output_file}'.")

    finally:
        driver.quit()

def scroll_to_load_all(driver, video_selector, max_tries=10):
    """
    Scrolls down on the page multiple times to ensure all items are loaded.
    If the scroll height no longer changes, we stop early.
    """
    last_height = driver.execute_script("return document.documentElement.scrollHeight")
    tries = 0

    while tries < max_tries:
        driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
        time.sleep(2)  # Short pause to allow new content to load

        new_height = driver.execute_script("return document.documentElement.scrollHeight")
        if new_height == last_height:
            # No change in scroll height, might be done
            break
        last_height = new_height
        tries += 1

    # Give a moment for final load
    time.sleep(1)

def try_click_load_more(driver):
    """
    Some YouTube layouts include a "Load more" or "Show more" button in playlists.
    Attempt to click it if present.
    """
    # Example possible selector for "Load more" button:
    load_more_selectors = [
        "#button[aria-label='Load more']",
        "tp-yt-paper-button#button[aria-label='Load more']",
        "yt-next-continuation #button",  # fallback
    ]
    for sel in load_more_selectors:
        try:
            button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
            )
            button.click()
            time.sleep(2)
            print("Clicked 'Load more' button.")
            return
        except:
            pass

def dismiss_cookie_banner(driver):
    """
    Attempt to dismiss or accept cookie banners if present.
    This is heavily region/language dependent, so you may need to adjust it.
    """
    try:
        # Example: look for a button that says "I agree" or "Accept all"
        # (The actual text/selector can vary by region.)
        cookies_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='I agree' or normalize-space()='Accept all']",
                )
            )
        )
        cookies_button.click()
        time.sleep(1)
        print("Cookie banner dismissed.")
    except:
        # If not found, ignore
        pass


# ----- Main script entry -----
if __name__ == "__main__":
    playlist_url = input("Enter the YouTube playlist URL: ").strip()
    if playlist_url:
        extract_playlist_urls(playlist_url)
    else:
        print("Please enter a valid YouTube playlist URL.")
