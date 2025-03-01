from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import sys
import os
import re
import urllib.parse  # Import urllib.parse for URL parsing

def sanitize_filename(title):
    """Sanitizes a string to be used as a filename."""
    sanitized_title = re.sub(r'[^\w\s-]', '', title).strip()
    sanitized_title = re.sub(r'\s+', '_', sanitized_title)
    sanitized_title = sanitized_title[:150]
    return sanitized_title

def load_full_comments_section(driver, scroll_pause_time=2, initial_page_down_count=3):
    """
    Performs initial scroll, then continuously scrolls to load full comment section.
    (Same scrolling logic as before)
    """
    try:
        # 0. Wait for the page to be fully loaded and interactive
        WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "ytd-page-manager"))
        )
        print("Page manager loaded, page considered interactive.")
        time.sleep(2)

        # 1. Initial "Page Down" scroll
        body_element = driver.find_element(By.TAG_NAME, 'body')
        for _ in range(initial_page_down_count):
            body_element.send_keys(Keys.PAGE_DOWN)
            time.sleep(0.5)
        time.sleep(3)

        # 2. Wait for *at least one comment*
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-comment-thread-renderer #comment"))
        )
        print("Initial comments loaded after page down scrolls.")

        # 3. Continuous scrolling
        last_height = driver.execute_script("return document.documentElement.scrollHeight")
        comment_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.documentElement.scrollHeight")
            current_comments = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer #comment")
            new_comment_count = len(current_comments)
            if new_comment_count == comment_count and new_height == last_height:
                print("Reached end of comments.")
                break
            else:
                comment_count = new_comment_count
                last_height = new_height
                print(f"Comments loaded: {comment_count}")

    except Exception as e:
        print(f"Error during comment section loading/scrolling: {e}")

def scrape_youtube_comments(video_url):
    """
    Scrapes comments and video metadata from a YouTube video.

    Args:
        video_url (str): The URL of the YouTube video.

    Returns:
        tuple: A tuple containing:
            - list: A list of comment dictionaries (or empty list on error).
            - dict: A dictionary of video metadata (or empty dict on error).
    """
    driver = webdriver.Firefox()

    try:
        driver.get(video_url)

        # Extract Video Metadata
        video_metadata = {}
        try:
            title_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "#title > h1#title > yt-formatted-string#video-title"))
            )
            video_metadata['title'] = title_element.text.strip()
        except:
            video_metadata['title'] = "Title not found"

        try:
            description_element = driver.find_element(By.CSS_SELECTOR, "#description yt-formatted-string")
            video_metadata['description'] = description_element.text.strip()
        except:
            video_metadata['description'] = "Description not found"

        # You can add more metadata extraction here, e.g., view count, upload date, etc.
        # ... (Inspect page source to find selectors for other metadata)

        load_full_comments_section(driver)
        comment_elements = driver.find_elements(By.CSS_SELECTOR, "ytd-comment-thread-renderer #comment")
        comments_data = []

        for comment_element in comment_elements:
            try:
                author_element = comment_element.find_element(By.CSS_SELECTOR, "#author-text span")
                comment_text_element = comment_element.find_element(By.CSS_SELECTOR, "#content-text")
                author = author_element.text.strip()
                comment_text = comment_text_element.text.strip()
                comments_data.append({'author': author, 'comment_text': comment_text})
            except Exception as e:
                print(f"Error extracting comment: {e}")
                continue

        return comments_data, video_metadata

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return [], {}

    finally:
        driver.quit()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ytcomment.py <youtube_video_url> or <youtube_video_id>")
        sys.exit(1)

    user_input = sys.argv[1]
    video_id = ""  # Initialize video_id

    if user_input.startswith(('http://', 'https://', 'www.')):
        video_url = user_input
        # Extract video ID from URL
        parsed_url = urllib.parse.urlparse(video_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        video_id = query_params.get('v', [''])[0] # Get 'v' parameter, default to empty list, take first element
    else:
        video_id = user_input
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Constructed YouTube URL from ID: {video_url}")

    print(f"Scraping comments and metadata from: {video_url}")

    comments, video_metadata = scrape_youtube_comments(video_url)

    if comments:
        video_title_sanitized = sanitize_filename(video_metadata.get('title', 'youtube_comments'))
        # Construct filename with video ID prefix
        output_filename = f"{video_id}_{video_title_sanitized}_comments.txt"
        output_filepath = os.path.join(os.getcwd(), output_filename)

        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                # Write Video Metadata at the beginning
                f.write("--- VIDEO METADATA ---\n")
                f.write(f"Title: {video_metadata.get('title', 'N/A')}\n")
                f.write(f"Description:\n{video_metadata.get('description', 'N/A')}\n")
                f.write("-" * 40 + "\n")
                f.write("\n--- COMMENTS ---\n")
                f.write(f"Video URL: {video_url}\n")
                f.write("-" * 40 + "\n")
                for comment in comments:
                    f.write(f"Author: {comment['author']}\n")
                    f.write(f"Comment: {comment['comment_text']}\n")
                    f.write("-" * 20 + "\n")
            print(f"Comments and metadata saved to: {output_filepath}")
        except Exception as e:
            print(f"Error saving comments to file: {e}")

    else:
        print("No comments found or an error occurred during scraping.")