import os
import logging
import requests
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from base64 import b64encode
import subprocess
from collections import deque

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Configurations from JSON
START_URL = config['start_url']
WEBDRIVER_PATH = config['webdriver_path']
SAVE_DIRECTORY = config['save_directory']
REQUEST_DELAY = config['request_delay']
MAX_WORKERS = config['max_workers']
RUNNING_PERIOD = config['running_period']
PAUSE_PERIOD = config['pause_period']
CAPTCHA_ENABLED = config['captcha_enabled']
CAPTCHA_TEXT = config['captcha_text']
USE_PROXY = config['use_proxy']
PROXY_FILE = config['proxy_file']
SAVE_MEDIA = config['save_media']
HEADLESS_BROWSER = config['headless_browser']

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

visited_urls = set()
saved_files = set()
cdn_links = {}
first_page_saved = False  # Flag to track if the first page has been saved

def get_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE) as f:
            proxies = [line.strip() for line in f]
    return proxies

def test_proxy(proxy_auth):
    try:
        host, port, user, password = proxy_auth.split(':')
        proxy = {
            "http": f"http://{user}:{password}@{host}:{port}",
            "https": f"https://{user}:{password}@{host}:{port}"
        }
        auth_string = f"{user}:{password}"
        encoded_credentials = b64encode(auth_string.encode()).decode('ascii')
        headers = {
            'Proxy-Authorization': f'Basic {encoded_credentials}'
        }

        response = requests.get('http://httpbin.org/ip', proxies=proxy, headers=headers)
        response.raise_for_status()
        ip = response.json().get('origin', '')
        logging.info(f"Proxy is working. IP: {ip}")
        return proxy, headers
    except Exception as e:
        logging.error(f"Proxy test failed: {e}")
        return None, None

def get_working_proxy(proxies):
    for proxy_auth in proxies:
        proxy, headers = test_proxy(proxy_auth)
        if proxy:
            return proxy, headers
    return None, None

def download_content(url, save_path, proxy=None, headers=None):
    if save_path in saved_files:
        logging.info(f"Already saved: {url} to {save_path}")
        return
    try:
        response = requests.get(url, proxies=proxy, headers=headers)
        ensure_dir(os.path.dirname(save_path))
        with open(save_path, 'wb') as file:
            file.write(response.content)
        saved_files.add(save_path)
        logging.info(f"Downloaded: {url} to {save_path}")
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_html(soup, path):
    if path in saved_files:
        logging.info(f"HTML file already saved: {path}")
        return
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as file:
        file.write(str(soup.prettify()))
    saved_files.add(path)

def process_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc, parsed_url.path

def generate_filename(url_path):
    global first_page_saved
    
    if not first_page_saved:
        first_page_saved = True
        return os.path.join(SAVE_DIRECTORY, 'index.html')
    
    parts = url_path.strip('/').split('/')
    
    # Determine filename from last part
    if parts and '.' in parts[-1]:
        filename = parts.pop()  # Get the last part if it contains an extension
    else:
        filename = parts.pop()  # Use the last part without adding .html
    
    if parts:
        directory_path = os.path.join(SAVE_DIRECTORY, *parts)
    else:
        directory_path = SAVE_DIRECTORY
    save_path = os.path.join(directory_path, filename)
    
    return save_path

def download_resources(resource_list, proxy=None, headers=None):
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_resource = {executor.submit(download_content, res[0], res[1], proxy, headers): res for res in resource_list}
        for future in as_completed(future_to_resource):
            res = future_to_resource[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error downloading resource {res[0]}: {e}")

def worker(driver, urls_to_visit, proxy, headers):
    start_time = time.time()

    while urls_to_visit:
        current_time = time.time()
        
        if (current_time - start_time) >= RUNNING_PERIOD:
            logging.info("Pausing main tasks to download CDN links")
            return
        
        current_url = urls_to_visit.popleft()
        if current_url in visited_urls:
            logging.debug(f"URL already visited: {current_url}. Skipping.")
            continue
        visited_urls.add(current_url)
        logging.debug(f"Visiting URL: {current_url}")

        base_url, path = process_url(current_url)
        try:
            driver.get(current_url)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Check for CAPTCHA
            if CAPTCHA_ENABLED and CAPTCHA_TEXT in str(soup):
                logging.info("CAPTCHA detected. Please complete the CAPTCHA in the browser window.")
                input("Press Enter after solving the CAPTCHA to continue...")
                # Reload page after solving CAPTCHA
                driver.get(current_url)
                soup = BeautifulSoup(driver.page_source, 'html.parser')

            save_path = generate_filename(path)

            # Collect image URLs
            resource_list = []
            logging.debug(f"Extracting resources from URL: {current_url}")
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    resource_url = urljoin(base_url, src)
                    resource_path_parts = ['images'] + urlparse(resource_url).path.strip('/').split('/')
                    resource_path = os.path.join(SAVE_DIRECTORY, *resource_path_parts)

                    if SAVE_MEDIA and urlparse(resource_url).netloc == urlparse(base_url).netloc:
                        resource_list.append((resource_url, resource_path))
                    else:
                        cdn_links[resource_url] = resource_path

                    # Replace the URL in the HTML with the local path
                    img['src'] = os.path.relpath(resource_path, os.path.dirname(save_path))

            # Save the modified HTML
            save_html(soup, save_path)

            # Download the images
            if SAVE_MEDIA:
                download_resources(resource_list, proxy, headers)

            # Add new URLs to visit
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
    options.headless = HEADLESS_BROWSER

    driver = webdriver.Firefox(service=Service(WEBDRIVER_PATH), options=options)
    return driver

def download_cdn_resources(proxy, headers):
    if not cdn_links:
        logging.info("No CDN links to download.")
        return
    
    logging.info("Downloading CDN resources...")
    
    proxy_http = proxy["http"]
    proxy_https = proxy["https"]

    for url, path in cdn_links.items():
        ensure_dir(os.path.dirname(path))
        command = [
            "wget",
            "-e", f"use_proxy=yes",
            "-e", f"http_proxy={proxy_http}",
            "-e", f"https_proxy={proxy_https}", 
                        "-O", path,
            url
        ]

        try:
            subprocess.run(command, check=True)
            saved_files.add(path)
            logging.info(f"Downloaded via wget: {url} to {path}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error downloading {url} via wget: {e}")

    logging.info("CDN resource download completed.")

def main():
    urls_to_visit = deque([START_URL])

    proxies = get_proxies()
    if USE_PROXY and proxies:
        proxy, headers = get_working_proxy(proxies)
        
        if not proxy:
            logging.error("No working proxies found. Exiting program.")
            return
    else:
        proxy, headers = None, None

    if config['headless_browser'] and config['captcha_enabled']:
        logging.warning("Both headless_browser and captcha_enabled are set to True. Disabling headless mode to handle CAPTCHA.")
        config['headless_browser'] = False  # Override headless mode

    driver = setup_driver()
    if driver:
        while urls_to_visit:
            worker(driver, urls_to_visit, proxy, headers)

            logging.info("Paused for CDN download...")

            time.sleep(PAUSE_PERIOD)
            download_cdn_resources(proxy, headers)
            
            logging.info("Resuming main tasks...")

        # Close the browser after finishing all tasks
        driver.quit()
        logging.info("Closed driver for the current session")

    logging.info("Site cloning completed.")

if __name__ == "__main__":
    main()
