# Web Copier

Web Copier is a Python-based project designed to automate the process of copying websites, including those with advanced anti-bot measures. This tool leverages Selenium for browser automation, allowing it to bypass many common anti-bot techniques and scrape content from websites that are otherwise difficult to scrape.

## Features

- **Automated Browser Interaction**: Uses Selenium to interact with web pages as a real user would.
- **Proxy Support**: Supports rotating proxies to avoid IP bans.
- **CAPTCHA Handling**: Detects CAPTCHA challenges and pauses for manual resolution.
- **Resource Downloading**: Downloads and saves media resources (images, scripts, etc.) locally.
- **Configurable**: All settings are configurable via a [`config.json`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fconfig.json%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/config.json") file.
- **Logging**: Detailed logging for monitoring the scraping process.
- **Efficient Resource Downloading**: Uses `wget` for downloading resources, which is faster and more reliable for large files.

## Project Structure

```

driver/
    geckodriver
proxies.txt
config.json
main.py
```

## Getting Started

### Prerequisites

- Python 3.x
- Selenium
- BeautifulSoup
- Requests
- Geckodriver (for Firefox)
- `wget` (for efficient resource downloading)

### Installation

1. **Clone the repository**:
    ```sh
    git clone https://github.com/yourusername/web-copier.git
    cd web-copier
    ```

2. **Install the required Python packages**:
    ```sh
    pip install -r requirements.txt
    ```

3. **Download Geckodriver**:
    - Download the appropriate version of Geckodriver for your operating system from [here](https://github.com/mozilla/geckodriver/releases).
    - Place the Geckodriver executable in the [`driver/`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fdriver%2F%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/driver/") directory.

4. **Install `wget`**:
    ```sh
    sudo apt-get install wget
    ```

### Configuration

Edit the [`config.json`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fconfig.json%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/config.json") file to set your desired configuration:

```json
{
    "start_url": "http://example.com",
    "webdriver_path": "driver/geckodriver",
    "save_directory": "./cloned_site",
    "request_delay": 0.1,
    "max_workers": 10,
    "running_period": 100,
    "pause_period": 100,
    "captcha_enabled": true,
    "captcha_text": "We don't want unauthorised bots visiting our website.",
    "use_proxy": true,
    "proxy_file": "proxies.txt",
    "save_media": true,
    "headless_browser": true
}
```

### Running the Project

1. **Prepare the proxy file**:
    - Create a [`proxies.txt`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fproxies.txt%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/proxies.txt") file with your proxy details in the format `host:port:user:pass`, one per line.

2. **Run the main script**:
    ```sh
    python main.py
    ```

## How It Works

1. **Initialization**:
    - Loads configuration from [`config.json`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fconfig.json%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/config.json").
    - Reads proxies from [`proxies.txt`](command:_github.copilot.openRelativePath?%5B%7B%22scheme%22%3A%22file%22%2C%22authority%22%3A%22%22%2C%22path%22%3A%22%2Fhome%2Fkaran%2FProjects%2FwebCloner%2Fproxies.txt%22%2C%22query%22%3A%22%22%2C%22fragment%22%3A%22%22%7D%2C%22e657b272-a7f7-42c1-a389-cc4686533e54%22%5D "/home/karan/Projects/webCloner/proxies.txt") and tests them.

2. **Browser Setup**:
    - Sets up a Selenium WebDriver instance.
    - Configures the browser based on the settings (e.g., headless mode).

3. **Scraping Process**:
    - Visits the start URL and begins scraping.
    - Handles CAPTCHA challenges by pausing for manual resolution.
    - Downloads and saves media resources.
    - Logs all activities for monitoring.

4. **Resource Downloading**:
    - Downloads CDN resources using `wget` if proxies are configured. `wget` is used because it is faster and more reliable for downloading large files compared to other methods.

## Contributing

This project is in its early stages, and contributions are welcome! If you have ideas for improvements or new features, please feel free to fork the repository and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

- [Selenium](https://www.selenium.dev/)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [Requests](https://docs.python-requests.org/en/master/)
- [wget](https://www.gnu.org/software/wget/)

---

For any questions or support, please open an issue on the GitHub repository.

Happy scraping!