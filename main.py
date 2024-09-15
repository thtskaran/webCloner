import os
import logging
import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from base64 import b64encode

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
MAX_WORKERS = 10  # Number of threads for parallel downloading
RUNNING_PERIOD = 300  # Running period before pausing for CDN download (in seconds)
PAUSE_PERIOD = 300  # Pause period to download CDN resources (in seconds)

visited_urls = set()
saved_files = set()
cdn_links = {}

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
    filename = url_path.strip('/').replace('/', '_')
    if not filename:
        filename = 'index.html'
    if not filename.endswith('.html'):
        filename += '.html'
    return filename

def download_resources(resource_list, proxy=None, headers=None):
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_resource = {executor.submit(download_content, res[0], res[1], proxy, headers): res for res in resource_list}
        for future in as_completed(future_to_resource):
            res = future_to_resource[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error downloading resource {res[0]}: {e}")

def worker(driver, urls_to_visit, proxy=None, headers=None):
    start_time = time.time()

    while urls_to_visit:
        current_time = time.time()
        
        if current_time - start_time >= RUNNING_PERIOD:
            logging.info("Pausing main tasks to download CDN links")
            return
        
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

            # Collect image URLs
            resource_list = []
            logging.debug(f"Extracting resources from URL: {current_url}")
            for img in soup.find_all('img'):
                src = img.get('src')
                if src:
                    resource_url = urljoin(base_url, src)
                    resource_path = os.path.join(SAVE_DIRECTORY, 'images', urlparse(resource_url).path.lstrip('/'))

                    if urlparse(resource_url).netloc == urlparse(base_url).netloc:
                        resource_list.append((resource_url, resource_path))
                    else:
                        cdn_links[resource_url] = resource_path

                    # Replace the URL in the HTML with the local path
                    img['src'] = os.path.relpath(resource_path, os.path.dirname(save_path))

            # Save the modified HTML
            save_html(soup, save_path)

            # Download the images
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
    options.headless = True

    driver = webdriver.Firefox(service=Service(WEBDRIVER_PATH), options=options)
    return driver

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

def download_cdn_resources(proxy, headers):
    if not cdn_links:
        logging.info("No CDN links to download.")
        return
    
    logging.info("Downloading CDN resources...")

    resource_list = [(url, path) for url, path in cdn_links.items()]
    download_resources(resource_list, proxy=proxy, headers=headers)
    
    logging.info("CDN resource download completed.")

def main():
    urls_to_visit = [START_URL]

    proxy_auth = input("Enter proxy details (host:port:user:pass): ")
    proxy, headers = test_proxy(proxy_auth)
    
    if not proxy:
        logging.error("Invalid proxy details. Exiting program.")
        return

    driver = setup_driver()
    if driver:
        while urls_to_visit:
            worker(driver, urls_to_visit, proxy, headers)
            
            logging.info("Paused for CDN download...")

            time.sleep(PAUSE_PERIOD)
            download_cdn_resources(proxy, headers)
            
            logging.info("Resuming main tasks...")

        driver.quit()
        logging.info("Closed driver for the current session")

    logging.info("Site cloning completed.")

if __name__ == "__main__":
    main()
