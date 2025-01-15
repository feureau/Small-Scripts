import sys
import os
import configparser
import logging
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import tkinter as tk
from tkinter import filedialog
import re

def is_valid_reddit_url(url):
    """
    Validates if the URL is a proper Reddit post URL.
    """
    # Adjust the regex as needed to match valid Reddit post URLs
    regex = r'^https?://(www\.)?old\.reddit\.com/r/\w+/comments/\w+/?'
    return re.match(regex, url) is not None

def read_urls_from_url_files(file_paths):
    """
    Reads URLs from a list of .url files.
    """
    urls = []
    for file_path in file_paths:
        if file_path.lower().endswith('.url') and os.path.isfile(file_path):
            config = configparser.ConfigParser()
            try:
                config.read(file_path, encoding='utf-8')
                url = config.get('InternetShortcut', 'URL')
                if is_valid_reddit_url(url):
                    urls.append(url)
                else:
                    print(f"Invalid Reddit URL in {file_path}: {url}")
            except (configparser.NoSectionError, configparser.NoOptionError) as e:
                print(f"Failed to parse {file_path}: {e}")
        else:
            print(f"Skipped non-.url file: {file_path}")
    return urls

def read_urls_from_directory(directory_path):
    """
    Reads URLs from all .url files in the specified directory.
    """
    urls = []
    for filename in os.listdir(directory_path):
        if filename.lower().endswith('.url'):
            file_path = os.path.join(directory_path, filename)
            config = configparser.ConfigParser()
            try:
                config.read(file_path, encoding='utf-8')
                url = config.get('InternetShortcut', 'URL')
                if is_valid_reddit_url(url):
                    urls.append(url)
                else:
                    print(f"Invalid Reddit URL in {file_path}: {url}")
            except (configparser.NoSectionError, configparser.NoOptionError) as e:
                print(f"Failed to parse {file_path}: {e}")
    return urls

def select_directory():
    """
    Opens a dialog to select a directory and returns the selected path.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Bring the dialog to the front
    selected_dir = filedialog.askdirectory(title="Select Folder Containing .url Files")
    root.destroy()
    return selected_dir

def scrape_reddit_posts(urls, output_filename, log_filename):
    """
    Scrapes the title, upvotes, and entire comment tree from Reddit URLs using Selenium.
    Displays the output on the console in real-time and saves it to a text file.
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
    firefox_options.binary_location = "C:/Program Files/Mozilla Firefox/firefox.exe"  # Update if necessary

    # Initialize WebDriver with the provided GeckoDriver path
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

    with open(output_filename, "w", encoding="utf-8") as file:
        for url in urls:
            try:
                logging.info(f"Scraping URL: {url}")
                print(f"Scraping URL: {url}...")
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

                        upvotes_element = comment_element.find_element(By.CSS_SELECTOR, "span.score.unvoted")
                        upvotes = upvotes_element.text.strip()

                        comment_tree.append((comment_text, upvotes, 0))  # Assuming depth 0 for now
                        # Print comment to console immediately
                        print(f"- {comment_text} (Upvotes: {upvotes})")
                        logging.info(f"Comment: {comment_text} (Upvotes: {upvotes})")
                    except NoSuchElementException as nse:
                        logging.warning(f"Failed to extract a comment in {url}: {nse}")
                        print(f"Failed to extract a comment: {nse}")

                print("\n" + "="*80 + "\n")
                logging.info("="*80)

                # Write the same data to the file
                file.write(f"URL: {url}\n")
                file.write(f"Title: {title}\n")
                file.write(f"Post Upvotes: {post_upvotes}\n")
                file.write("Comments Tree:\n")
                for comment_text, upvotes, depth in comment_tree:
                    indent = "  " * depth
                    file.write(f"{indent}- {comment_text} (Upvotes: {upvotes})\n")
                file.write("\n" + "="*80 + "\n")

            except TimeoutException as te:
                logging.error(f"Timeout while scraping {url}: {te}")
                print(f"Failed to scrape {url} due to timeout: {te}")
                file.write(f"Failed to scrape {url} due to timeout: {te}\n")
                file.write("\n" + "="*80 + "\n")
            except NoSuchElementException as nse:
                logging.error(f"Element not found while scraping {url}: {nse}")
                print(f"Failed to scrape {url} due to missing elements: {nse}")
                file.write(f"Failed to scrape {url} due to missing elements: {nse}\n")
                file.write("\n" + "="*80 + "\n")
            except Exception as e:
                logging.error(f"An unexpected error occurred while scraping {url}: {e}")
                print(f"Failed to scrape {url} due to an unexpected error: {e}")
                file.write(f"Failed to scrape {url} due to an unexpected error: {e}\n")
                file.write("\n" + "="*80 + "\n")

    driver.quit()
    logging.info(f"Scraping complete! Data saved to '{output_filename}'.")
    print(f"Scraping complete! Data saved to '{output_filename}'.")

def main():
    """
    Main function to handle input methods and initiate scraping.
    """
    # Collect command-line arguments (excluding the script name)
    input_args = sys.argv[1:]

    if input_args:
        # Assume drag-and-drop of .url files; input_args contains file paths
        print("Received the following input files:")
        for arg in input_args:
            print(f"- {arg}")
        urls = read_urls_from_url_files(input_args)

        # Determine the common directory of the input files
        input_dirs = set(os.path.dirname(os.path.abspath(arg)) for arg in input_args if os.path.isfile(arg))
        if len(input_dirs) == 1:
            input_directory = input_dirs.pop()
            print(f"All input files are from the directory: {input_directory}")
        else:
            # If multiple directories, default to the script's directory
            input_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
            print(f"Input files are from multiple directories. Saving output and log in the script's directory: {input_directory}")

    else:
        # No arguments; prompt user to select a folder or use script's directory
        print("No input files provided. Prompting for folder selection...")
        selected_dir = select_directory()
        if selected_dir:
            print(f"Selected directory: {selected_dir}")
            urls = read_urls_from_directory(selected_dir)
            input_directory = selected_dir
        else:
            # Use the script's directory
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            print(f"No directory selected. Using script's directory: {script_dir}")
            urls = read_urls_from_directory(script_dir)
            input_directory = script_dir

    if not urls:
        print("No valid Reddit URLs found. Exiting.")
        return

    # Define the output and log filenames
    output_filename = os.path.join(input_directory, "reddit_posts.txt")
    log_filename = os.path.join(input_directory, "scraping.log")

    # Start scraping
    scrape_reddit_posts(urls, output_filename, log_filename)

if __name__ == "__main__":
    main()
