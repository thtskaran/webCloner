import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
import threading

# Debug flag
DEBUG = False

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG if DEBUG else logging.INFO,
    handlers=[
        logging.StreamHandler()
    ]
)

# Configurations
START_URL = 'http://tryst.link'  # Replace with the target URL
WEBDRIVER_PATH = 'driver/geckodriver'  # Replace with the path to GeckoDriver
SAVE_DIRECTORY = './cloned_site'
MAX_WINDOWS = 6
DELAY_BETWEEN_LAUNCHES = 5  # Delay in seconds between launching browser instances

# Initialize WebDriver options
options = Options()
options.headless = True
service = Service(WEBDRIVER_PATH)

# Function to download content
def download_content(url, save_path):
    try:
        response = requests.get(url)
        ensure_dir(os.path.dirname(save_path))
        with open(save_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded: {url} to {save_path}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")

# Function to ensure directory exists
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Function to save HTML files
def save_html(soup, path):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as file:
        file.write(str(soup.prettify()))

# Function to process URLs
def process_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc, parsed_url.path

# Generate a filename from a URL
def generate_filename(url_path):
    filename = url_path.strip('/').replace('/', '_')
    if not filename:
        filename = 'index.html'
    if not filename.endswith('.html'):
        filename += '.html'
    return filename

visited_urls_lock = threading.Lock()  # Lock for thread-safe access to visited_urls
visited_urls = set()

def worker(driver, urls_to_visit):
    try:
        while True:
            with visited_urls_lock:
                if not urls_to_visit:
                    break
                current_url = urls_to_visit.pop(0)
                if current_url in visited_urls:
                    continue
                visited_urls.add(current_url)

            base_url, path = process_url(current_url)
            try:
                driver.get(current_url)
                time.sleep(DELAY_BETWEEN_LAUNCHES)  # Adding delay to ensure page loads completely
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                save_path = os.path.join(SAVE_DIRECTORY, generate_filename(path))
                save_html(soup, save_path)

                # Extract and download images, scripts, and CSS
                for tag, attribute, folder in [('img', 'src', ''), ('script', 'src', ''), ('link', 'href', 'css')]:
                    for element in soup.find_all(tag):
                        src = element.get(attribute)
                        if src:
                            resource_url = urljoin(base_url, src)
                            resource_path = os.path.join(SAVE_DIRECTORY, folder, urlparse(resource_url).path.lstrip('/'))
                            download_content(resource_url, resource_path)

                # Add new links to visit list
                with visited_urls_lock:
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        linked_url = urljoin(base_url, href)
                        if linked_url.startswith(base_url) and linked_url not in visited_urls:
                            urls_to_visit.append(linked_url)
            except Exception as e:
                logging.error(f"Error processing URL {current_url}: {e}")
    finally:
        driver.quit()
        logging.info("Closed driver for the current session")

def setup_driver():
    try:
        driver = webdriver.Firefox(service=Service(WEBDRIVER_PATH), options=Options())
        return driver
    except Exception as e:
        logging.error(f"Error starting Firefox instance: {e}")
        return None

def main():
    urls_to_visit = [START_URL]
    threads = []

    with ThreadPoolExecutor(max_workers=MAX_WINDOWS) as executor:
        for _ in range(MAX_WINDOWS):
            driver = setup_driver()
            if driver:
                thread = executor.submit(worker, driver, urls_to_visit)
                threads.append(thread)
                time.sleep(DELAY_BETWEEN_LAUNCHES)  # Adding delay between launching instances

        for task in as_completed(threads):
            try:
                task.result()
            except Exception as e:
                logging.error(f"Thread raised an exception: {e}")

    logging.info("Site cloning completed.")

if __name__ == "__main__":
    main()