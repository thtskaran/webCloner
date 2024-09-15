import os
import time
import json
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options

# Configurations
START_URL = 'http://tryst.link'  # Replace with the target URL
WEBDRIVER_PATH = 'driver/geckodriver'  # Replace with the path to GeckoDriver
SAVE_DIRECTORY = './cloned_site'
DELAY_BETWEEN_LAUNCHES = 2  # Delay in seconds between launching browser instances

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
        print(f"Downloaded: {url} to {save_path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

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

# Function to enumerate site
def enumerate_site(driver, url):
    base_url, path = process_url(url)
    visited_urls = set()
    urls_to_visit = [url]

    while urls_to_visit:
        current_url = urls_to_visit.pop(0)

        if current_url in visited_urls:
            continue

        driver.get(current_url)
        time.sleep(DELAY_BETWEEN_LAUNCHES)  # Adding delay to ensure page loads completely
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        save_path = os.path.join(SAVE_DIRECTORY, generate_filename(path))
        save_html(soup, save_path)

        visited_urls.add(current_url)

        # Extract and download images and scripts
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                img_url = urljoin(base_url, src)
                img_path = os.path.join(SAVE_DIRECTORY, urlparse(img_url).path.lstrip('/'))
                download_content(img_url, img_path)

        for script in soup.find_all('script'):
            src = script.get('src')
            if src:
                script_url = urljoin(base_url, src)
                script_path = os.path.join(SAVE_DIRECTORY, urlparse(script_url).path.lstrip('/'))
                download_content(script_url, script_path)

        # Add new links to visit list
        for link in soup.find_all('a', href=True):
            href = link['href']
            linked_url = urljoin(base_url, href)
            if linked_url.startswith(base_url) and linked_url not in visited_urls:
                urls_to_visit.append(linked_url)

# Start WebDriver instance
try:
    driver = webdriver.Firefox(service=service, options=options)
    enumerate_site(driver, START_URL)
finally:
    # Close WebDriver instance
    try:
        driver.quit()
    except Exception as e:
        print(f"Error closing Firefox instance: {e}")

print("Site cloning completed.")
