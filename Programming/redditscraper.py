import sys
import os
import configparser
import logging
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def is_valid_reddit_url(url):
    """
    Validates if the URL is a proper Reddit post URL.
    Adjust the regex if you want to handle www.reddit.com, etc.
    """
    regex = r'^https?://(www\.)?old\.reddit\.com/r/\w+/comments/\w+/?'
    return re.match(regex, url) is not None

def read_urls_from_url_file(file_path):
    """
    Reads a single .url file and returns the Reddit URL if valid, or None.
    """
    if not os.path.isfile(file_path):
        print(f"File does not exist: {file_path}")
        return None
    
    if not file_path.lower().endswith('.url'):
        return None
    
    config = configparser.ConfigParser()
    try:
        config.read(file_path, encoding='utf-8')
        url = config.get('InternetShortcut', 'URL')
        if is_valid_reddit_url(url):
            print(f"URL extracted from {file_path}: {url}")
            return url
        else:
            print(f"Invalid Reddit URL in {file_path}: {url}")
            return None
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Failed to parse {file_path}: {e}")
        return None

def read_urls_from_directory(directory_path):
    """
    Reads URLs from all .url files in the specified directory.
    Returns a list of valid Reddit URLs found.
    """
    urls = []
    if not os.path.isdir(directory_path):
        print(f"Not a directory: {directory_path}")
        return urls
    
    for filename in os.listdir(directory_path):
        full_path = os.path.join(directory_path, filename)
        if filename.lower().endswith('.url'):
            url = read_urls_from_url_file(full_path)
            if url:
                urls.append(url)
    return urls

def sanitize_filename(filename):
    """
    Removes or replaces invalid filename characters to ensure the file can be saved.
    """
    # Replace invalid characters with an underscore
    sanitized = re.sub(r'[\\/*?:"<>|]+', '_', filename)
    # Optionally, trim the filename to a reasonable length
    return sanitized[:80] if len(sanitized) > 80 else sanitized

def scrape_reddit_posts(urls, output_directory, log_filename):
    """
    Scrapes each Reddit URL using Selenium, and for each post:
      - Extract the title, upvotes, and all comments
      - Create an output file named "<sanitized_title>_<datetime>.txt"
    Logs all actions to a single log file.
    """
    # Configure logging
    logging.basicConfig(
        filename=log_filename,
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Set up Firefox options
    firefox_options = Options()
    # Uncomment the next line to run in headless mode
    # firefox_options.add_argument("--headless")  # Run in headless mode (no GUI)

    # Update if necessary: path to your Firefox installation
    firefox_binary = "C:/Program Files/Mozilla Firefox/firefox.exe"
    if os.path.exists(firefox_binary):
        firefox_options.binary_location = firefox_binary
    else:
        print(f"Firefox binary not found at {firefox_binary}. Please check the path.")
        logging.error(f"Firefox binary not found at {firefox_binary}.")
        return

    # GeckoDriver path - update if needed
    geckodriver_path = "C:/Users/Feureau/AppData/Roaming/SeleniumDrivers/geckodriver.exe"
    if not os.path.exists(geckodriver_path):
        print(f"GeckoDriver not found at {geckodriver_path}. Please check the path.")
        logging.error(f"GeckoDriver not found at {geckodriver_path}.")
        return

    service = Service(geckodriver_path)
    try:
        driver = webdriver.Firefox(service=service, options=firefox_options)
    except Exception as e:
        print(f"Failed to initialize WebDriver: {e}")
        logging.error(f"Failed to initialize WebDriver: {e}")
        return

    for url in urls:
        try:
            logging.info(f"Scraping URL: {url}")
            print(f"\nScraping URL: {url}...")
            driver.get(url)

            # Wait for the post title to appear
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.title"))
            )

            # Extract the post title
            title_element = driver.find_element(By.CSS_SELECTOR, "a.title")
            title = title_element.text.strip()
            print(f"Title: {title}")
            logging.info(f"Title: {title}")

            # Extract the post upvotes
            upvotes_element = driver.find_element(By.CSS_SELECTOR, "div.score.unvoted")
            post_upvotes = upvotes_element.text.strip()
            print(f"Post Upvotes: {post_upvotes}")
            logging.info(f"Post Upvotes: {post_upvotes}")

            # Scroll down and wait for comments to load
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.entry.unvoted"))
            )

            # Extract comments
            comment_elements = driver.find_elements(By.CSS_SELECTOR, "div.entry.unvoted")
            comment_tree = []

            for comment_element in comment_elements:
                try:
                    comment_text_element = comment_element.find_element(By.CSS_SELECTOR, "div.md")
                    comment_text = comment_text_element.text.strip()

                    upvotes_span = comment_element.find_element(By.CSS_SELECTOR, "span.score.unvoted")
                    comment_upvotes = upvotes_span.text.strip()

                    comment_tree.append((comment_text, comment_upvotes, 0))  # Assuming depth 0
                    print(f"- {comment_text} (Upvotes: {comment_upvotes})")
                    logging.info(f"Comment: {comment_text} (Upvotes: {comment_upvotes})")
                except NoSuchElementException as nse:
                    logging.warning(f"Failed to extract a comment in {url}: {nse}")
                    print(f"Failed to extract a comment: {nse}")

            # Generate unique filename based on title and timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            safe_title = sanitize_filename(title)
            output_filename = os.path.join(output_directory, f"{safe_title}_{timestamp}.txt")

            print(f"\nSaving post data to: {output_filename}")
            logging.info(f"Output file created: {output_filename}")

            with open(output_filename, "w", encoding="utf-8") as file:
                file.write(f"URL: {url}\n")
                file.write(f"Title: {title}\n")
                file.write(f"Post Upvotes: {post_upvotes}\n")
                file.write("Comments Tree:\n")
                for c_text, c_upvotes, depth in comment_tree:
                    indent = "  " * depth
                    file.write(f"{indent}- {c_text} (Upvotes: {c_upvotes})\n")

        except TimeoutException as te:
            logging.error(f"Timeout while scraping {url}: {te}")
            print(f"Failed to scrape {url} due to timeout: {te}")
            error_filename = os.path.join(output_directory, f"error_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
            with open(error_filename, "w", encoding="utf-8") as error_file:
                error_file.write(f"Failed to scrape {url} due to timeout: {te}\n")
        except NoSuchElementException as nse:
            logging.error(f"Element not found while scraping {url}: {nse}")
            print(f"Failed to scrape {url} due to missing elements: {nse}")
            error_filename = os.path.join(output_directory, f"error_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
            with open(error_filename, "w", encoding="utf-8") as error_file:
                error_file.write(f"Failed to scrape {url} due to missing elements: {nse}\n")
        except Exception as e:
            logging.error(f"An unexpected error occurred while scraping {url}: {e}")
            print(f"Failed to scrape {url} due to an unexpected error: {e}")
            error_filename = os.path.join(output_directory, f"error_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")
            with open(error_filename, "w", encoding="utf-8") as error_file:
                error_file.write(f"Failed to scrape {url} due to an unexpected error: {e}\n")

    driver.quit()
    logging.info("Scraping complete!")
    print("\nScraping complete! Each post has its own output file.")

def main():
    """
    Main function to handle inputs automatically:
    - If an argument is a directory, read .url files from it.
    - If an argument is a .url file, parse the contained URL.
    - If an argument is a valid Reddit URL string, add it directly.
    - Output files and log are saved in the current working directory.
    """
    input_args = sys.argv[1:]
    current_working_directory = os.getcwd()
    log_filename = os.path.join(current_working_directory, "scraping.log")
    discovered_urls = []
    directories_used = set()

    if not input_args:
        # Prompt the user to input a path or URL
        user_input = input(
            "Enter a directory path, a .url file path, or a direct Reddit URL.\n"
            "Or press Enter to cancel: "
        ).strip()

        if not user_input:
            print("No input provided. Exiting.")
            return

        input_args = [user_input]

    for arg in input_args:
        arg = arg.strip('"')  # Remove surrounding quotes if any (e.g., dragged from Windows)
        if os.path.isdir(arg):
            # Process directory of .url files
            print(f"Detected directory: {arg}")
            urls = read_urls_from_directory(arg)
            discovered_urls.extend(urls)
            directories_used.add(os.path.abspath(arg))
        elif os.path.isfile(arg):
            if arg.lower().endswith('.url'):
                # Process a single .url file
                print(f"Detected .url file: {arg}")
                url = read_urls_from_url_file(arg)
                if url:
                    discovered_urls.append(url)
            else:
                # Could be a direct Reddit URL in text form or an invalid file
                # Attempt to treat the file path as a direct URL
                if is_valid_reddit_url(arg):
                    print(f"Detected direct Reddit URL in file path: {arg}")
                    discovered_urls.append(arg)
                else:
                    print(f"Skipped unknown file: {arg}")
        else:
            # Not a file or directory, maybe it's a direct URL?
            if is_valid_reddit_url(arg):
                print(f"Detected direct Reddit URL: {arg}")
                discovered_urls.append(arg)
            else:
                print(f"Skipped invalid input: {arg}")

    # Remove duplicates
    discovered_urls = list(set(discovered_urls))

    if not discovered_urls:
        print("No valid Reddit URLs found. Exiting.")
        return

    print(f"\nTotal valid URLs to scrape: {len(discovered_urls)}")
    logging.info(f"Total valid URLs to scrape: {len(discovered_urls)}")

    # Start scraping
    scrape_reddit_posts(discovered_urls, current_working_directory, log_filename)

if __name__ == "__main__":
    main()
