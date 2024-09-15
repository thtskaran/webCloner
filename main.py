import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from urllib.parse import urlparse, urljoin

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
REQUEST_DELAY = 0.1  # Reduced delay between requests in seconds

visited_urls = set()

def download_content(url, save_path):
    try:
        response = requests.get(url)
        ensure_dir(os.path.dirname(save_path))
        with open(save_path, 'wb') as file:
            file.write(response.content)
        logging.info(f"Downloaded: {url} to {save_path}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_html(soup, path):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as file:
        file.write(str(soup.prettify()))

def process_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc, parsed_url.path

def generate_filename(url_path):
    filename = url_path.strip('/').replace('/', '_')
    if not filename:
        filename = 'index.html'
    if not filename.endswith('.html'):
        filename += '.html'
    return filename

def worker(driver, urls_to_visit):
    while urls_to_visit:
        current_url = urls_to_visit.pop(0)
        if current_url in visited_urls:
            logging.debug(f"URL already visited: {current_url}. Skipping.")
            continue
        visited_urls.add(current_url)
        logging.debug(f"Visiting URL: {current_url}")

        base_url, path = process_url(current_url)
        try:
            driver.get(current_url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            save_path = os.path.join(SAVE_DIRECTORY, generate_filename(path))
            save_html(soup, save_path)

            logging.debug(f"Extracting resources from URL: {current_url}")
            for tag, attribute, folder in [('img', 'src', ''), ('script', 'src', ''), ('link', 'href', 'css')]:
                for element in soup.find_all(tag):
                    src = element.get(attribute)
                    if src:
                        resource_url = urljoin(base_url, src)
                        resource_path = os.path.join(SAVE_DIRECTORY, folder, urlparse(resource_url).path.lstrip('/'))
                        download_content(resource_url, resource_path)

            for link in soup.find_all('a', href=True):
                href = link['href']
                linked_url = urljoin(base_url, href)
                if linked_url.startswith(base_url) and linked_url not in visited_urls:
                    logging.debug(f"Adding new URL to visit: {linked_url}")
                    urls_to_visit.append(linked_url)
        except Exception as e:
            logging.error(f"Error processing URL {current_url}: {e}")

def setup_driver():
    options = Options()
    options.headless = True

    driver = webdriver.Firefox(service=Service(WEBDRIVER_PATH), options=options)
    return driver

def main():
    urls_to_visit = [START_URL]

    driver = setup_driver()
    if driver:
        worker(driver, urls_to_visit)
        driver.quit()
        logging.info("Closed driver for the current session")

    logging.info("Site cloning completed.")

if __name__ == "__main__":
    main()

print("Site cloning completed.")
