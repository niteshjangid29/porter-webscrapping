from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_selenium_driver():
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")  # This is important for some versions of Chrome
    chrome_options.add_argument("--remote-debugging-port=9222")  # This is recommended

    # Path to the chromedriver installed by apt-get in the Dockerfile
    service = ChromeService(executable_path="/usr/bin/chromedriver")

    # Set up driver.
    # Explicitly use the service to avoid SeleniumManager's architecture issue.
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver


def scrape_h2_heading():
    """
    Initializes a Selenium driver, navigates to porter.in, scrapes the
    first <h2> heading, and returns it.

    Raises:
        TimeoutException: If the element is not found in time.
        WebDriverException: If there is an issue with the driver.
        Exception: For any other unexpected errors.

    Returns:
        str: The text content of the first <h2> element.
    """
    driver = None
    try:
        driver = get_selenium_driver()
        print("Driver initialized. Navigating to https://porter.in")
        driver.get("https://www.porter.in")

        # Wait up to 15 seconds for the first h2 element to be present
        wait = WebDriverWait(driver, 15)
        h2_element = wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "h2"))
        )
        
        heading_text = h2_element.text
        print(f"Successfully found h2 element with text: '{heading_text}'")
        return heading_text

    finally:
        if driver:
            driver.quit()
            print("Driver has been closed.")


def test_chromedriver_installation():
    
    # Get the Selenium driver
    driver = get_selenium_driver()

    try:
        # URL to test
        driver.get("https://www.porter.in")

        # Use an explicit wait for reliability instead of time.sleep()
        # Wait up to 10 seconds for the h2 element to be present on Facebook's page
        wait = WebDriverWait(driver, 10)
        element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h2")))
        element_text = element.text
        # Print the text of the element
        print(f"Found H2 element with text: '{element_text}'")

        # Check if the text is as expected
        assert "Connect with friends" in element_text
        print("ChromeDriver is installed and working as expected.")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the browser
        driver.quit()

# test_chromedriver_installation()
# scrape_h2_heading()