import time
import re
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException, 
    NoSuchElementException,
    ElementClickInterceptedException
)

from .exceptions import PorterAPIError

time.sleep(2) 
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



def _validate_phone(phone: str) -> str:
    """Validate phone number format"""
    if not re.fullmatch(r"\d{10}", phone):
        raise PorterAPIError(
            "Phone number must be exactly 10 digits. "
            "No country codes, spaces, or special characters please! 📱"
        )
    return phone

def _parse_price_range(price_text: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse price range from text like '₹585 - ₹615'"""
    match = re.findall(r"\d+", price_text.replace(",", ""))
    if len(match) == 2:
        return int(match[0]), int(match[1])
    elif len(match) == 1:
        return int(match[0]), int(match[0])
    return None, None

def _parse_capacity(capacity_text: str) -> Optional[int]:
    """Parse capacity from text like '500 kg'"""
    match = re.search(r"(\d+)", capacity_text.replace(",", ""))
    return int(match.group(1)) if match else None

class PorterAPI:
    SUPPORTED_CITIES = [
        "Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune"
    ]
    SERVICE_TYPES = ["two_wheelers", "trucks", "packers_and_movers"]

    def __init__(self, name: str, phone: str, headless: bool = True):
        """
        Initialize Porter API client
        
        Args:
            name: Your name (be nice, use your real name!)
            phone: 10-digit phone number
            headless: Run browser in headless mode (True = invisible, False = see the magic)
        """
        self.name = name
        self.phone = _validate_phone(phone)
        self.headless = headless

    def get_supported_cities(self) -> List[str]:
        """Get list of supported cities"""
        return self.SUPPORTED_CITIES.copy()

    def get_supported_service_types(self) -> List[str]:
        """Get list of supported service types"""
        return self.SERVICE_TYPES.copy()

    def _create_error_response(self, error_msg: str, details: str = None, suggestion: str = None) -> Dict:
        """Create a standardized error response"""
        response = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if details:
            response["details"] = details
            
        if not suggestion:
            suggestion = (
                "Try running the script again, or if the issue persists, "
                "please create an issue at: https://github.com/telomelonia/porter/issues"
            )
        response["suggestion"] = suggestion
        
        return response
    
    def select_requirement_type(self, driver, wait, requirement_type: str = "personal") -> bool:
        """Select the requirement type (Personal User or Business User)"""
        try:
            print(f"🎯 Selecting requirement type: {requirement_type}")
            time.sleep(2)
            
            # Try multiple selectors for the requirement radio buttons
            selectors_to_try = [
                f'input[value="{requirement_type}"]',
                '.FareEstimateRequirement_requirement-input__4YZ93',
                '[class*="requirement-input"]',
                'input[name="requirement"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        target_element = elements[0]
                        
                        if target_element.is_selected():
                            print("✅ Requirement already selected")
                            return True
                        
                        try:
                            target_element.click()
                            print("✅ Successfully clicked requirement radio button")
                            time.sleep(1)
                            return True
                            
                        except ElementClickInterceptedException:
                            parent_label = target_element.find_element(By.XPATH, "./..")
                            parent_label.click()
                            print("✅ Successfully clicked parent label")
                            time.sleep(1)
                            return True
                            
                except Exception as e:
                    continue
            
            # Alternative approach: Find by text content
            try:
                labels = driver.find_elements(By.TAG_NAME, "label")
                for label in labels:
                    if "Personal User" in label.text:
                        label.click()
                        print("✅ Successfully clicked Personal User label")
                        time.sleep(1)
                        return True
                        
            except Exception:
                pass
            
            # Final attempt: Use JavaScript
            try:
                js_script = """
                const radioButtons = document.querySelectorAll('input[name="requirement"]');
                for (let radio of radioButtons) {
                    if (radio.value === 'personal') {
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change'));
                        return true;
                    }
                }
                return false;
                """
                result = driver.execute_script(js_script)
                if result:
                    print("✅ Successfully selected requirement using JavaScript")
                    time.sleep(1)
                    return True
                    
            except Exception:
                pass
            
            print("⚠️ Could not select requirement type (continuing anyway)")
            return False
            
        except Exception as e:
            print(f"⚠️ Error in select_requirement_type: {e}")
            return False
        
    def select_address_from_autocomplete(self, driver, wait, input_element, address: str) -> bool:
        """Fill address input and select from autocomplete dropdown"""
        try:
            print(f"📍 Entering address: {address}")
            
            input_element.clear()
            input_element.send_keys(address)
            time.sleep(2)
            
            # Try multiple selectors for autocomplete options
            autocomplete_selectors = [
                "[class*='autocomplete'] li",
                "[class*='suggestion'] li", 
                "[class*='dropdown'] li",
                "[class*='option']",
                "ul li",
                ".pac-item",
                "[role='option']"
            ]
            
            for selector in autocomplete_selectors:
                try:
                    autocomplete_options = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if autocomplete_options:
                        first_option = autocomplete_options[0]
                        
                        try:
                            first_option.click()
                            print("✅ Successfully selected from autocomplete")
                            time.sleep(1)
                            return True
                        except ElementClickInterceptedException:
                            driver.execute_script("arguments[0].click();", first_option)
                            print("✅ Successfully selected using JavaScript")
                            time.sleep(1)
                            return True
                            
                except Exception:
                    continue
            
            # Fallback: keyboard navigation
            print("🎹 Using keyboard navigation...")
            input_element.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            input_element.send_keys(Keys.ENTER)
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"⚠️ Error in address selection: {e}")
            return False
        
    def select_service_type(self, driver, wait, service_type: str) -> bool:
        """Select the service type with robust error handling"""
        try:
            print(f"🚛 Looking for service type: {service_type}")
            time.sleep(3)
            
            service_mapping = {
                "two_wheelers": "Two Wheelers",
                "trucks": "Trucks", 
                "packers_and_movers": "Packers & Movers"
            }
            
            target_text = service_mapping.get(service_type, "Trucks")
            print(f"🎯 Target service: {target_text}")
            
            # Try to find category selector containers
            selectors_to_try = [
                "CategorySelector_category-select-container__LgXjx",
                "[class*='CategorySelector'][class*='container']",
                "[class*='category-select-container']",
                "[class*='category'][class*='container']"
            ]
            
            service_containers = []
            for selector in selectors_to_try:
                try:
                    if selector.startswith("["):
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    else:
                        elements = driver.find_elements(By.CLASS_NAME, selector)
                    
                    if elements:
                        service_containers = elements
                        break
                except Exception:
                    continue
            
            if not service_containers:
                print("❌ No service containers found!")
                return False
            
            print(f"✅ Found {len(service_containers)} service containers")
            
            # Look for the container with our target text
            for i, container in enumerate(service_containers):
                try:
                    container_text = container.text
                    
                    if target_text.lower() in container_text.lower():
                        print(f"✅ Found target service in container {i}")
                        
                        try:
                            container.click()
                            print("✅ Successfully clicked service container")
                            time.sleep(2)
                            return True
                            
                        except ElementClickInterceptedException:
                            driver.execute_script("arguments[0].click();", container)
                            print("✅ Successfully clicked using JavaScript")
                            time.sleep(2)
                            return True
                            
                except Exception:
                    continue
                    
            print(f"❌ Could not find service type: {target_text}")
            return False
            
        except Exception as e:
            print(f"❌ Error in select_service_type: {e}")
            return False
        
    def get_quote(self, pickup_address: str, drop_address: str, city: str, service_type: str = "trucks") -> Dict:
        """
        Get delivery quotes from Porter.in
        
        Args:
            pickup_address: Where to pick up from
            drop_address: Where to deliver to  
            city: City name (must be supported)
            service_type: Type of service needed
            
        Returns:
            Dictionary with quotes or error information
        """
        # Validate inputs
        if city not in self.SUPPORTED_CITIES:
            return self._create_error_response(
                f"City '{city}' is not supported 🏙️",
                f"Supported cities: {', '.join(self.SUPPORTED_CITIES)}",
                "Please use one of the supported cities or request Porter.in to expand!"
            )
            
        if service_type not in self.SERVICE_TYPES:
            return self._create_error_response(
                f"Service type '{service_type}' is not supported 🚛",
                f"Supported services: {', '.join(self.SERVICE_TYPES)}",
                "Check your service_type parameter spelling!"
            )
        
        # Initialize the Selenium driver
        driver = None
        try:
            driver = get_selenium_driver()
            wait = WebDriverWait(driver, 15)
            print("🚀 Driver initialized. Navigating to https://porter.in")

            driver.get("https://porter.in/")
            
            # Select city
            print(f"🏙️ Selecting city: {city}")
            city_selector = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "CitySelector_city-selected-text__1dNz4")))
            city_selector.click()
            
            city_elements = driver.find_elements(By.CSS_SELECTOR, '[class^="CitySelectorModal_city-title"]')
            city_found = False
            for el in city_elements:
                if city.lower() in el.text.lower():
                    el.click()
                    city_found = True
                    print(f"✅ Selected city: {city}")
                    break
                    
            if not city_found:
                return self._create_error_response(
                    f"Could not find city '{city}' on Porter.in 🗺️",
                    "The city might not be available or Porter.in changed their interface",
                    "Double-check the city name or try a different supported city"
                )
                
            # Open estimate form
            print("📋 Opening estimate form...")
            estimate_card = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "EstimateCard_estimate-card__NgFIr")))
            estimate_card.click()
            
            # Select service type
            if not self.select_service_type(driver, wait, service_type):
                return self._create_error_response(
                    f"Could not select service type: {service_type} 🚛",
                    "Porter.in might have changed their interface",
                    "Try a different service type or report this issue"
                )
            
            # Select requirement type
            print("👤 Selecting requirement type...")
            self.select_requirement_type(driver, wait, "personal")
            
            # Fill pickup address
            print("📍 Filling pickup address...")
            try:
                pickup_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter pickup address"]')))
                self.select_address_from_autocomplete(driver, wait, pickup_input, pickup_address)
            except TimeoutException:
                return self._create_error_response(
                    "Could not find pickup address field 📍",
                    "Porter.in might have changed their form structure"
                )
            
            # Fill drop address
            print("🎯 Filling drop address...")
            try:
                drop_input = driver.find_element(By.CSS_SELECTOR, 'input[placeholder="Enter drop address"]')
                self.select_address_from_autocomplete(driver, wait, drop_input, drop_address)
            except NoSuchElementException:
                return self._create_error_response(
                    "Could not find drop address field 🎯",
                    "Porter.in might have changed their form structure"
                )
            
            # Fill contact details
            print("📱 Filling contact details...")
            try:
                mobile_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.FareEstimateForms_mobile-input__jy5wR')))
                mobile_input.clear()
                mobile_input.send_keys(self.phone)
                
                name_input = driver.find_element(By.CSS_SELECTOR, '.FareEstimateForms_name-input__n8xyD')
                name_input.clear()
                name_input.send_keys(self.name)
            except (TimeoutException, NoSuchElementException):
                return self._create_error_response(
                    "Could not fill contact details 📱",
                    "Porter.in might have changed their form fields"
                )
            
            # Submit form
            print("🚀 Submitting form...")
            try:
                submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.FormInput_submit__ea0jJ.FormInput_submit-enabled__DbSnE.FareEstimateForms_submit-container___lB5u')))
                submit_btn.click()
            except TimeoutException:
                return self._create_error_response(
                    "Could not submit the form 🚀",
                    "The submit button might not be clickable or form validation failed",
                    "Check if all fields are properly filled"
                )
            
            # Wait for results
            print("⏳ Waiting for results...")
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'FareEstimateResultVehicleCard_container__BdMav')))
                result_cards = driver.find_elements(By.CLASS_NAME, 'FareEstimateResultVehicleCard_container__BdMav')
            except TimeoutException:
                return self._create_error_response(
                    "Results took too long to load ⏰",
                    "Porter.in might be slow or the addresses couldn't be processed",
                    "Try different addresses or run the script again"
                )
            
            if not result_cards:
                return self._create_error_response(
                    "No delivery options found 📦",
                    "Porter.in couldn't find any vehicles for your route",
                    "Try different addresses or check if the route is serviceable"
                )
            
            # Parse results
            quotes = []
            for i, card in enumerate(result_cards):
                try:
                    vehicle_name = card.find_element(By.CLASS_NAME, 'FareEstimateResultVehicleCard_vehicle-name__d4107').text
                    price_text = card.find_element(By.CSS_SELECTOR, '.FareEstimateResultVehicleCard_vehicle-fare__3YMOc p').text
                    min_price, max_price = _parse_price_range(price_text)
                    capacity = card.find_element(By.CLASS_NAME, 'VehicleCapacity_vehicle-capacity__P53Z0').text
                    capacity_kg = _parse_capacity(capacity)
                    
                    quotes.append({
                        "vehicle_name": vehicle_name,
                        "price_range": price_text,
                        "min_price": min_price,
                        "max_price": max_price,
                        "capacity": capacity,
                        "capacity_kg": capacity_kg
                    })
                    print(f"✅ Parsed quote {i+1}: {vehicle_name}")
                    
                except Exception as e:
                    print(f"⚠️ Error parsing quote card {i+1}: {e}")
                    continue
            
            if not quotes:
                return self._create_error_response(
                    "Could not parse any quotes 📊",
                    "Porter.in returned results but we couldn't understand the format",
                    "Porter.in might have changed their result structure"
                )
                    
            print(f"🎉 Successfully retrieved {len(quotes)} quotes!")
            return {
                "success": True,
                "pickup_address": pickup_address,
                "drop_address": drop_address,
                "city": city,
                "service_type": service_type,
                "user_name": self.name,
                "user_phone": self.phone,
                "quotes": quotes,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except WebDriverException as e:
            return self._create_error_response(
                "Browser automation failed 🌐",
                f"WebDriver error: {str(e)}",
                "Make sure Chrome is installed and try updating ChromeDriver"
            )
            
        except Exception as e:
            return self._create_error_response(
                "Unexpected error occurred 🤯",
                f"Error: {str(e)}",
                "This is probably a bug - please report it on GitHub!"
            )
            
        finally:
            if driver:
                try:
                    driver.quit()
                    print("🛑 Browser closed")
                except Exception:
                    pass

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