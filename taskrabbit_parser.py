#!/usr/bin/env python3
"""
TaskRabbit Furniture Assembly Tasker Parser

This script automates the TaskRabbit booking flow to extract all available taskers
for Furniture Assembly category and saves their names and hourly rates to CSV.
Supports dynamic pagination to capture taskers from multiple pages.
"""

import time
import csv
import logging
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TaskRabbitParser:
    def __init__(self, headless: bool = False):
        """Initialize the TaskRabbit parser with Chrome WebDriver."""
        self.base_url = "https://www.taskrabbit.com"
        self.driver = None
        self.wait = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        
    def debug_page_elements(self, description=""):
        """Debug helper to log current page elements."""
        logger.info(f"DEBUG - {description}")
        logger.info(f"Current URL: {self.driver.current_url}")
        logger.info(f"Page title: {self.driver.title}")
        
        # Log some common elements
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")[:10]
            logger.info(f"Found {len(links)} links, first 10:")
            for i, link in enumerate(links):
                logger.info(f"  {i+1}. {link.text[:50]} - {link.get_attribute('href')}")
        except Exception as e:
            logger.info(f"Error getting links: {e}")
    
    def close_overlays_and_popups(self):
        """Close any overlays, popups, or modals that might interfere with navigation"""
        logger.info("Checking for and closing overlays/popups...")
        
        # First, handle iframe overlays specifically
        try:
            iframe_overlays = self.driver.find_elements(By.XPATH, "//iframe[contains(@aria-label, 'Modal Overlay')]")
            for iframe in iframe_overlays:
                if iframe.is_displayed():
                    logger.info(f"Found modal overlay iframe: {iframe.get_attribute('id')}")
                    # Try to remove the iframe entirely
                    self.driver.execute_script("arguments[0].remove();", iframe)
                    logger.info("Removed modal overlay iframe")
                    time.sleep(1)
        except Exception as e:
            logger.info(f"No iframe overlays found or couldn't remove: {e}")
        
        # Handle parent containers of iframe overlays
        try:
            iframe_containers = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'box-') and .//iframe]")
            for container in iframe_containers:
                if container.is_displayed():
                    logger.info("Found iframe container, removing...")
                    self.driver.execute_script("arguments[0].remove();", container)
                    logger.info("Removed iframe container")
                    time.sleep(1)
        except Exception as e:
            logger.info(f"No iframe containers found: {e}")
        
        # List of common overlay selectors
        overlay_selectors = [
            # Facebook and social media overlays
            "//div[contains(@class, 'fb_lightbox-overlay')]",
            "//div[contains(@id, 'sidebar-overlay-lightbox')]",
            
            # Generic overlay selectors
            "//div[contains(@class, 'overlay')]",
            "//div[contains(@class, 'lightbox')]",
            "//div[contains(@class, 'modal')]",
            "//div[contains(@class, 'popup')]",
            
            # Close buttons
            "//button[contains(@class, 'close')]",
            "//div[contains(@class, 'close')]",
            "//button[contains(@aria-label, 'close')]",
            "//button[contains(@aria-label, 'Close')]",
            "//span[contains(@class, 'close')]",
            "//a[contains(@class, 'close')]",
            
            # X buttons
            "//button[text()='×']",
            "//button[text()='X']",
            "//span[text()='×']",
            "//span[text()='X']"
        ]
        
        for selector in overlay_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        try:
                            element.click()
                            logger.info(f"Closed overlay/popup with selector: {selector}")
                            time.sleep(1)
                        except Exception as e:
                            # Try JavaScript click if regular click fails
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"Closed overlay/popup with JavaScript: {selector}")
                                time.sleep(1)
                            except Exception:
                                logger.debug(f"Failed to close overlay with JavaScript: {e}")
                                continue
            except Exception as e:
                logger.debug(f"Error with overlay selector {selector}: {e}")
                continue
        
        # Additional method: Press ESC key to close modals
        try:
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            logger.info("Pressed ESC key to close any modals")
            time.sleep(1)
        except Exception as e:
            logger.info(f"Could not press ESC key: {e}")
    
    def remove_all_overlays_aggressively(self):
        """Aggressively remove all types of overlays and modals that might block interactions"""
        logger.info("Aggressively removing all overlays and modals...")
        
        # First, remove any iframe overlays with specific IDs or classes
        try:
            # Remove iframes with lightbox or modal in their ID/class
            iframe_selectors = [
                "//iframe[contains(@id, 'lightbox')]",
                "//iframe[contains(@class, 'lightbox')]",
                "//iframe[contains(@id, 'modal')]",
                "//iframe[contains(@class, 'modal')]",
                "//iframe[contains(@aria-label, 'Modal')]",
                "//iframe[contains(@class, 'box-')]"
            ]
            
            for selector in iframe_selectors:
                iframes = self.driver.find_elements(By.XPATH, selector)
                for iframe in iframes:
                    if iframe.is_displayed():
                        logger.info(f"Removing iframe overlay: {iframe.get_attribute('id')} / {iframe.get_attribute('class')}")
                        self.driver.execute_script("arguments[0].remove();", iframe)
                        time.sleep(0.5)
        except Exception as e:
            logger.info(f"Error removing iframe overlays: {e}")
        
        # Remove parent containers that might contain overlays
        try:
            container_selectors = [
                "//div[contains(@class, 'overlay')]",
                "//div[contains(@class, 'modal')]",
                "//div[contains(@class, 'lightbox')]",
                "//div[contains(@class, 'popup')]",
                "//div[contains(@style, 'position: fixed')]",
                "//div[contains(@style, 'position:fixed')]",
                "//div[contains(@style, 'z-index') and contains(@style, '999')]"
            ]
            
            for selector in container_selectors:
                containers = self.driver.find_elements(By.XPATH, selector)
                for container in containers:
                    if container.is_displayed():
                        # Check if this container is blocking the main content
                        try:
                            rect = container.rect
                            if rect['width'] > 500 and rect['height'] > 300:  # Large overlay
                                logger.info(f"Removing large overlay container: {container.get_attribute('class')}")
                                self.driver.execute_script("arguments[0].remove();", container)
                                time.sleep(0.5)
                        except Exception as e:
                            logger.debug(f"Error removing element: {e}")
                            continue
        except Exception as e:
            logger.info(f"Error removing container overlays: {e}")
        
        # Force remove any elements with high z-index that might be blocking
        try:
            self.driver.execute_script("""
                var elements = document.querySelectorAll('*');
                for (var i = 0; i < elements.length; i++) {
                    var style = window.getComputedStyle(elements[i]);
                    var zIndex = parseInt(style.zIndex);
                    if (zIndex > 1000 && style.position === 'fixed') {
                        elements[i].remove();
                    }
                }
            """)
            logger.info("Removed high z-index fixed position elements")
        except Exception as e:
            logger.info(f"Error removing high z-index elements: {e}")
        
        # Final cleanup - call the standard overlay removal
        self.close_overlays_and_popups()
    
    def click_continue_button(self):
        """Helper method to click continue/next buttons with multiple selectors."""
        continue_selectors = [
            "//button[contains(text(), 'Continue')]",
            "//a[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//a[contains(text(), 'Next')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//button[contains(text(), 'Proceed')]",
            "//button[contains(text(), 'Go')]"
        ]
        
        for selector in continue_selectors:
            try:
                continue_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found Continue button with selector: {selector}")
                continue_btn.click()
                time.sleep(3)
                return True
            except TimeoutException:
                continue
        
        logger.info("No Continue button found, proceeding without clicking")
        return False
    
    def navigate_to_furniture_assembly(self):
        """Navigate directly to furniture assembly page using shortcut URL"""
        logger.info("Navigating directly to furniture assembly page...")
        
        # Go directly to the furniture assembly page
        direct_url = "https://www.taskrabbit.com/services/handyman/assemble-furniture"
        self.driver.get(direct_url)
        time.sleep(3)
        
        logger.info(f"Loaded furniture assembly page directly: {direct_url}")
        
        # Close any overlays that might appear even with direct navigation
        self.close_overlays_and_popups()
        
        self.debug_page_elements("Furniture Assembly page (direct navigation)")
        
        # Step 4: Try to find a direct booking link or navigate to general furniture assembly
        logger.info("Looking for booking options...")
        
        # Look for Book Now or similar buttons
        booking_selectors = [
            "//button[contains(text(), 'Book Now')]",
            "//a[contains(text(), 'Book Now')]",
            "//button[contains(text(), 'Book')]",
            "//a[contains(text(), 'Book')]",
            "//button[contains(text(), 'Get Started')]",
            "//a[contains(text(), 'Get Started')]"
        ]
        
        book_now = None
        for selector in booking_selectors:
            try:
                book_now = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found start booking button: {selector}")
                break
            except TimeoutException:
                continue
        
        if book_now:
            # Aggressive overlay removal before clicking
            self.remove_all_overlays_aggressively()
            
            # Try multiple click methods
            try:
                book_now.click()
                logger.info("Successfully clicked Book Now button with regular click")
            except Exception as e:
                logger.warning(f"Regular click failed: {e}")
                try:
                    # Force JavaScript click
                    self.driver.execute_script("arguments[0].click();", book_now)
                    logger.info("Successfully clicked Book Now button with JavaScript click")
                except Exception as e2:
                    logger.warning(f"JavaScript click failed: {e2}")
                    # Try scrolling into view and clicking
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", book_now)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", book_now)
                        logger.info("Successfully clicked Book Now button after scrolling")
                    except Exception as e3:
                        logger.error(f"All click methods failed: {e3}")
                        raise Exception("Could not click Book Now button")
            
            time.sleep(3)
            self.debug_page_elements("After clicking start booking")
        else:
            logger.error("Could not find booking button")
            raise Exception("Booking button not found")
        
    def enter_address_details(self):
        """Enter the specified address and continue through the booking flow."""
        logger.info("Entering address details...")
        self.debug_page_elements("Before entering address")
        
        # Check if we need to start the booking process first
        start_booking_selectors = [
            "//button[contains(text(), 'Get Started')]",
            "//button[contains(text(), 'Start Booking')]",
            "//a[contains(text(), 'Get Started')]",
            "//a[contains(text(), 'Start Booking')]",
            "//button[contains(text(), 'Book Now')]",
            "//a[contains(text(), 'Book Now')]"
        ]
        
        # Try to click a start booking button if present
        for selector in start_booking_selectors:
            try:
                start_btn = self.driver.find_element(By.XPATH, selector)
                if start_btn.is_displayed():
                    logger.info(f"Found start booking button: {selector}")
                    start_btn.click()
                    time.sleep(3)
                    self.debug_page_elements("After clicking start booking")
                    break
            except NoSuchElementException:
                continue
        
        # Enter street address
        address_selectors = [
            "//input[@placeholder='Street address']",
            "//input[@name='address']",
            "//input[contains(@id, 'address')]",
            "//input[@type='text']",
            "//input[contains(@placeholder, 'address')]",
            "//input[contains(@class, 'address')]",
            "//input[contains(@placeholder, 'zip')]",
            "//input[contains(@placeholder, 'location')]",
            "//input[contains(@name, 'location')]",
            "//textarea[contains(@placeholder, 'address')]"
        ]
        
        address_field = None
        for selector in address_selectors:
            try:
                address_field = self.wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                logger.info(f"Found address field with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not address_field:
            logger.error("Could not find address field")
            self.debug_page_elements("Address field not found")
            raise Exception("Address field not found")
        
        address_field.clear()
        address_field.send_keys("6619 10th Ave, brooklyn, 11219, NY")
        time.sleep(2)
        
        # Click Continue button
        continue_selectors = [
            "//button[contains(text(), 'Continue')]",
            "//a[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//input[@type='submit']",
            "//button[@type='submit']"
        ]
        
        continue_btn = None
        for selector in continue_selectors:
            try:
                continue_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found Continue button with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not continue_btn:
            logger.error("Could not find Continue button")
            self.debug_page_elements("Continue button not found")
            raise Exception("Continue button not found")
        
        continue_btn.click()
        time.sleep(5)
        self.debug_page_elements("After clicking Continue")
        
    def select_furniture_options(self):
        """Select furniture assembly options through the booking flow."""
        logger.info("Selecting furniture assembly options...")
        self.debug_page_elements("Before selecting furniture options")
        
        # Step 1: Look for "Both IKEA and non-IKEA furniture" option
        logger.info("Looking for 'Both IKEA and non-IKEA furniture' option...")
        
        # First, look for the question text to confirm we're on the right page
        question_indicators = [
            "What type of furniture do you need assembled or disassembled?",
            "What type of furniture",
            "IKEA",
            "furniture type"
        ]
        
        page_text = self.driver.page_source.lower()
        question_found = any(indicator.lower() in page_text for indicator in question_indicators)
        
        if question_found:
            logger.info("Found furniture type question on page")
        else:
            logger.info("Furniture type question not clearly identified, proceeding with selection")
        
        # Comprehensive selectors for "Both IKEA and non-IKEA furniture" option
        furniture_type_selectors = [
            # Direct text matches
            "//button[contains(text(), 'Both IKEA and non-IKEA furniture')]",
            "//label[contains(text(), 'Both IKEA and non-IKEA furniture')]",
            "//div[contains(text(), 'Both IKEA and non-IKEA furniture')]",
            "//span[contains(text(), 'Both IKEA and non-IKEA furniture')]",
            
            # Variations with different casing
            "//button[contains(text(), 'Both IKEA and non-IKEA')]",
            "//button[contains(text(), 'IKEA and non-IKEA')]",
            "//label[contains(text(), 'Both IKEA and non-IKEA')]",
            "//label[contains(text(), 'IKEA and non-IKEA')]",
            
            # Radio button or checkbox inputs with associated labels
            "//input[@type='radio']/following-sibling::*[contains(text(), 'Both IKEA and non-IKEA')]",
            "//input[@type='checkbox']/following-sibling::*[contains(text(), 'Both IKEA and non-IKEA')]",
            "//input[@type='radio']/parent::*[contains(text(), 'Both IKEA and non-IKEA')]",
            "//input[@type='checkbox']/parent::*[contains(text(), 'Both IKEA and non-IKEA')]",
            
            # Value-based selections
            "//input[@value='both']",
            "//input[@value='both_ikea_non_ikea']",
            "//option[contains(text(), 'Both IKEA and non-IKEA')]",
            
            # Fallback options
            "//button[contains(text(), 'Both')]",
            "//label[contains(text(), 'Both')]",
            "//div[contains(text(), 'Both') and contains(text(), 'IKEA')]"
        ]
        
        both_option = None
        
        for selector in furniture_type_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        both_option = element
                        logger.info(f"Found 'Both IKEA and non-IKEA furniture' option with selector: {selector}")
                        logger.info(f"Element text: '{element.text}'")
                        break
                if both_option:
                    break
            except Exception:
                continue
        
        if both_option:
            try:
                # Try different click methods
                if both_option.tag_name.lower() == 'input':
                    # For radio buttons or checkboxes, click directly
                    both_option.click()
                elif both_option.tag_name.lower() == 'label':
                    # For labels, try clicking the associated input or the label itself
                    try:
                        input_element = both_option.find_element(By.XPATH, ".//input")
                        input_element.click()
                    except Exception as e:
                        logger.debug(f"Error with continue selector {selector}: {e}")
                        both_option.click()
                else:
                    # For buttons or other elements
                    both_option.click()
                
                time.sleep(2)
                logger.info("Successfully selected 'Both IKEA and non-IKEA furniture' option")
            except Exception as e:
                logger.warning(f"Failed to click furniture option: {e}")
                # Try JavaScript click as fallback
                try:
                    self.driver.execute_script("arguments[0].click();", both_option)
                    logger.info("Successfully selected furniture option using JavaScript click")
                except Exception as e2:
                    logger.error(f"Failed to select furniture option with JavaScript: {e2}")
        else:
            logger.warning("Could not find 'Both IKEA and non-IKEA furniture' option")
            # Debug: log available options
            try:
                all_buttons = self.driver.find_elements(By.XPATH, "//button | //label | //input[@type='radio'] | //input[@type='checkbox']")
                logger.info("Available options on page:")
                for i, btn in enumerate(all_buttons[:10]):  # Show first 10
                    if btn.is_displayed():
                        logger.info(f"  {i+1}. {btn.tag_name}: '{btn.text}' (value: {btn.get_attribute('value')})")
            except Exception as e:
                logger.info(f"Could not debug available options: {e}")
            
            logger.info("Proceeding without selecting furniture type")
        
        # Continue to next step
        self.click_continue_button()
        
        # Step 2: Look for "Medium - Est. 2-3 hrs" size selection
        logger.info("Looking for 'Medium - Est. 2-3 hrs' size selection...")
        
        # Comprehensive selectors for "Medium - Est. 2-3 hrs" option
        size_selectors = [
            # Direct text matches with full text
            "//button[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//label[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//div[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//span[contains(text(), 'Medium - Est. 2-3 hrs')]",
            
            # Variations with different formatting
            "//button[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//label[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//div[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//span[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            
            # Radio button or checkbox inputs with associated labels
            "//input[@type='radio']/following-sibling::*[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//input[@type='checkbox']/following-sibling::*[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//input[@type='radio']/parent::*[contains(text(), 'Medium - Est. 2-3 hrs')]",
            "//input[@type='checkbox']/parent::*[contains(text(), 'Medium - Est. 2-3 hrs')]",
            
            # Value-based selections
            "//input[@value='medium']",
            "//input[@value='medium_2_3_hrs']",
            "//option[contains(text(), 'Medium - Est. 2-3 hrs')]",
            
            # Fallback options
            "//button[contains(text(), 'Medium')]",
            "//label[contains(text(), 'Medium')]",
            "//div[contains(text(), 'Medium') and contains(text(), 'Est')]"
        ]
        
        medium_option = None
        
        for selector in size_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        medium_option = element
                        logger.info(f"Found 'Medium - Est. 2-3 hrs' option with selector: {selector}")
                        logger.info(f"Element text: '{element.text}'")
                        break
                if medium_option:
                    break
            except Exception:
                continue
        
        if medium_option:
            try:
                # Try different click methods
                if medium_option.tag_name.lower() == 'input':
                    # For radio buttons or checkboxes, click directly
                    medium_option.click()
                elif medium_option.tag_name.lower() == 'label':
                    # For labels, try clicking the associated input or the label itself
                    try:
                        input_element = medium_option.find_element(By.XPATH, ".//input")
                        input_element.click()
                    except Exception:
                        medium_option.click()
                else:
                    # For buttons or other elements
                    medium_option.click()
                
                time.sleep(2)
                logger.info("Successfully selected 'Medium - Est. 2-3 hrs' option")
                
                # Scroll down to make sure Continue button is visible
                logger.info("Scrolling down to reveal Continue button...")
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)
                
                self.click_continue_button()
            except Exception as e:
                logger.warning(f"Failed to click medium size option: {e}")
                # Try JavaScript click as fallback
                try:
                    self.driver.execute_script("arguments[0].click();", medium_option)
                    logger.info("Successfully selected medium size option using JavaScript click")
                    self.click_continue_button()
                except Exception as e2:
                    logger.error(f"Failed to select medium size option with JavaScript: {e2}")
        else:
            logger.warning("Could not find 'Medium - Est. 2-3 hrs' option")
            # Debug: log available size options
            try:
                all_buttons = self.driver.find_elements(By.XPATH, "//button | //label | //input[@type='radio'] | //input[@type='checkbox']")
                logger.info("Available size options on page:")
                for i, btn in enumerate(all_buttons[:10]):  # Show first 10
                    if btn.is_displayed() and ('medium' in btn.text.lower() or 'size' in btn.text.lower() or 'hrs' in btn.text.lower()):
                        logger.info(f"  {i+1}. {btn.tag_name}: '{btn.text}' (value: {btn.get_attribute('value')})")
            except Exception as e:
                logger.info(f"Could not debug available size options: {e}")
            
            logger.info("Proceeding without selecting size")
        

        # Step 4: Look for task details text box and enter "build stool"
        logger.info("Looking for task details text box to enter 'build stool'...")
        
        # Comprehensive selectors for task details text input
        task_details_selectors = [
            # Text areas and input fields for task details
            "//textarea[contains(@placeholder, 'details')]",
            "//textarea[contains(@placeholder, 'task')]",
            "//textarea[contains(@placeholder, 'Tell us')]",
            "//input[@type='text' and contains(@placeholder, 'details')]",
            "//input[@type='text' and contains(@placeholder, 'task')]",
            "//input[@type='text' and contains(@placeholder, 'Tell us')]",
            
            # Generic text areas and inputs
            "//textarea",
            "//input[@type='text']",
            
            # By name or id attributes
            "//textarea[contains(@name, 'details')]",
            "//textarea[contains(@name, 'task')]",
            "//textarea[contains(@id, 'details')]",
            "//textarea[contains(@id, 'task')]",
            "//input[contains(@name, 'details')]",
            "//input[contains(@name, 'task')]",
            "//input[contains(@id, 'details')]",
            "//input[contains(@id, 'task')]"
        ]
        
        task_details_field = None
        
        for selector in task_details_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        task_details_field = element
                        logger.info(f"Found task details field with selector: {selector}")
                        logger.info(f"Element tag: '{element.tag_name}', placeholder: '{element.get_attribute('placeholder')}'")
                        break
                if task_details_field:
                    break
            except Exception:
                continue
        
        if task_details_field:
            try:
                # Clear the field and enter "build stool"
                task_details_field.clear()
                task_details_field.send_keys("build stool")
                time.sleep(2)
                logger.info("Successfully entered 'build stool' in task details field")
                
                # Scroll down to make sure Continue button is visible
                logger.info("Scrolling down to reveal Continue button...")
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(1)
                
                self.click_continue_button()
            except Exception as e:
                logger.warning(f"Failed to enter task details: {e}")
                # Try JavaScript approach as fallback
                try:
                    self.driver.execute_script("arguments[0].value = 'build stool';", task_details_field)
                    logger.info("Successfully entered task details using JavaScript")
                    self.click_continue_button()
                except Exception as e2:
                    logger.error(f"Failed to enter task details with JavaScript: {e2}")
        else:
            logger.warning("Could not find task details text field")
            # Debug: log available text inputs
            try:
                all_inputs = self.driver.find_elements(By.XPATH, "//textarea | //input[@type='text']")
                logger.info("Available text input fields on page:")
                for i, inp in enumerate(all_inputs[:10]):  # Show first 10
                    if inp.is_displayed():
                        logger.info(f"  {i+1}. {inp.tag_name}: placeholder='{inp.get_attribute('placeholder')}', name='{inp.get_attribute('name')}', id='{inp.get_attribute('id')}'")
            except Exception as e:
                logger.info(f"Could not debug available text inputs: {e}")
            
            logger.info("Proceeding without entering task details")
        
        time.sleep(5)
        self.debug_page_elements("After furniture options selection")
        
    def sort_by_recommended(self):
        """Skip sorting - taskers are already sorted by Recommended by default."""
        logger.info("Skipping sort step - taskers are already sorted by Recommended by default")
            
    def is_valid_person_name(self, text: str) -> bool:
        """Validate if the extracted text is likely a person's name."""
        if not text or len(text) < 2:
            return False
        
        # Filter out common non-name phrases
        invalid_phrases = [
            "how i can help",
            "about me",
            "my experience",
            "what i do",
            "services",
            "skills",
            "description",
            "profile",
            "bio",
            "overview",
            "details",
            "info",
            "contact",
            "book now",
            "view profile",
            "hire me",
            "get quote",
            "message",
            "reviews",
            "rating",
            "stars",
            "feedback",
            "testimonial"
        ]
        
        text_lower = text.lower().strip()
        
        # Check if it contains invalid phrases
        for phrase in invalid_phrases:
            if phrase in text_lower:
                return False
        
        # Check if it contains colons (like "How I can help:")
        if ":" in text:
            return False
        
        # Check if it's too long (names are usually short)
        if len(text) > 50:
            return False
        
        # Check if it contains mostly numbers or special characters
        if len([c for c in text if c.isalnum()]) < len(text) * 0.5:
            return False
        
        # Check if it looks like a typical name pattern (letters, spaces, dots, apostrophes)
        import re
        name_pattern = r"^[A-Za-z\s\.\'\-]+$"
        if not re.match(name_pattern, text):
            return False
        
        # Must contain at least one letter
        if not any(c.isalpha() for c in text):
            return False
        
        return True

    def extract_tasker_data(self) -> List[Dict[str, str]]:
        """Extract tasker names and hourly rates from all paginated pages."""
        logger.info("Extracting tasker data from all pages...")
        all_taskers = []
        
        # First, get all available page numbers
        available_pages = self.get_available_page_numbers()
        if not available_pages:
            logger.info("No pagination found, processing single page...")
            available_pages = [1]
        
        logger.info(f"Found {len(available_pages)} pages to process: {available_pages}")
        
        # Process each page individually
        for page_num in available_pages:
            logger.info(f"Processing page {page_num}...")
            
            # Navigate to the specific page if not page 1
            if page_num > 1:
                success = self.navigate_to_page_number(page_num)
                if not success:
                    logger.warning(f"Failed to navigate to page {page_num}, skipping...")
                    continue
                time.sleep(5)  # Wait for page to load after clicking
            
            # Extract taskers from current page
            page_taskers = self.extract_taskers_from_current_page()
            
            if not page_taskers:
                logger.warning(f"No taskers found on page {page_num}, but continuing to next page...")
                continue  # Continue to next page instead of breaking
            
            logger.info(f"Found {len(page_taskers)} taskers on page {page_num}")
            all_taskers.extend(page_taskers)
        
        logger.info(f"Total taskers extracted from all pages: {len(all_taskers)}")
        return all_taskers
    
    def extract_taskers_from_current_page(self) -> List[Dict[str, str]]:
        """Extract tasker names and hourly rates from the current page only."""
        logger.debug("Extracting taskers from current page...")
        taskers = []
        
        # Wait for tasker cards to load
        time.sleep(5)
        
        # Find tasker cards/elements with multiple selectors
        tasker_selectors = [
            "//div[contains(@data-testid, 'tasker')]",  # Primary working selector
            "//div[contains(@class, 'tasker')]",
            "//div[contains(@class, 'card')]",
            "//div[contains(@class, 'TaskerCard')]",
            "//div[contains(@class, 'provider')]",
            "//div[contains(@class, 'worker')]",
            "//article",
            "//div[contains(@class, 'profile')]"
        ]
        
        tasker_elements = []
        for selector in tasker_selectors:
            tasker_elements = self.driver.find_elements(By.XPATH, selector)
            if tasker_elements:
                logger.info(f"Found {len(tasker_elements)} tasker elements with selector: {selector}")
                break
        
        if not tasker_elements:
            logger.error("No tasker elements found")
            self.debug_page_elements("No tasker elements found")
            return []
        
        for i, element in enumerate(tasker_elements):  # Get all taskers
            try:
                # Extract name with comprehensive selectors for modern TaskRabbit
                name_selectors = [
                    # Modern TaskRabbit selectors
                    ".//h1", ".//h2", ".//h3", ".//h4", ".//h5", ".//h6",
                    ".//div[contains(@class, 'name')]",
                    ".//span[contains(@class, 'name')]",
                    ".//p[contains(@class, 'name')]",
                    ".//div[contains(@data-testid, 'name')]",
                    ".//span[contains(@data-testid, 'name')]",
                    ".//strong", ".//b",
                    
                    # Generic text elements that might contain names
                    ".//div[contains(@class, 'title')]",
                    ".//span[contains(@class, 'title')]",
                    ".//div[contains(@class, 'header')]",
                    ".//span[contains(@class, 'header')]",
                    
                    # Fallback - any text element
                    ".//div[text()]",
                    ".//span[text()]",
                    ".//p[text()]"
                ]
                
                name = None
                for name_selector in name_selectors:
                    try:
                        name_element = element.find_element(By.XPATH, name_selector)
                        potential_name = name_element.text.strip()
                        
                        # Filter out non-names and validate it's actually a person's name
                        if potential_name:
                            is_valid = self.is_valid_person_name(potential_name)
                            logger.debug(f"Name validation: '{potential_name}' -> {is_valid}")
                            if is_valid:
                                name = potential_name
                                break
                    except NoSuchElementException:
                        continue
                
                # Extract hourly rate with comprehensive selectors for modern TaskRabbit
                rate_selectors = [
                    # Direct text searches for dollar amounts
                    ".//*[contains(text(), '$')]",
                    ".//*[contains(text(), '/hr')]",
                    ".//*[contains(text(), 'per hour')]",
                    ".//*[contains(text(), 'hour')]",
                    # Common price-related classes and attributes
                    ".//span[contains(@class, 'price')]",
                    ".//div[contains(@class, 'price')]",
                    ".//span[contains(@class, 'rate')]",
                    ".//div[contains(@class, 'rate')]",
                    ".//span[contains(@class, 'cost')]",
                    ".//div[contains(@class, 'cost')]",
                    ".//span[contains(@class, 'pricing')]",
                    ".//div[contains(@class, 'pricing')]",
                    ".//span[contains(@class, 'hourly')]",
                    ".//div[contains(@class, 'hourly')]",
                    ".//span[contains(@class, 'wage')]",
                    ".//div[contains(@class, 'wage')]",
                    # Data test IDs
                    ".//span[contains(@data-testid, 'price')]",
                    ".//div[contains(@data-testid, 'price')]",
                    ".//span[contains(@data-testid, 'rate')]",
                    ".//div[contains(@data-testid, 'rate')]",
                    ".//span[contains(@data-testid, 'cost')]",
                    ".//div[contains(@data-testid, 'cost')]",
                    # Specific element types with dollar signs
                    ".//span[contains(text(), '$')]",
                    ".//div[contains(text(), '$')]",
                    ".//p[contains(text(), '$')]",
                    ".//strong[contains(text(), '$')]",
                    ".//b[contains(text(), '$')]",
                    ".//em[contains(text(), '$')]",
                    ".//label[contains(text(), '$')]",
                    # Broader searches
                    ".//text()[contains(., '$')]/..",
                    ".//*[@title and contains(@title, '$')]",
                    ".//*[@aria-label and contains(@aria-label, '$')]"
                ]
                
                rate = None
                for rate_selector in rate_selectors:
                    try:
                        rate_element = element.find_element(By.XPATH, rate_selector)
                        rate_text = rate_element.text.strip()
                        if rate_text and ('$' in rate_text or '/hr' in rate_text or 'per hour' in rate_text):
                            rate = rate_text
                            break
                    except NoSuchElementException:
                        continue
                
                # If no rate found, try to get all text from the element and search for price patterns
                if not rate:
                    try:
                        all_text = element.text
                        import re
                        # Look for price patterns like $25/hr, $30 per hour, etc.
                        price_patterns = [
                            r'\$\d+(?:\.\d{2})?(?:/hr|/hour|\s*per\s*hour)?',
                            r'\d+(?:\.\d{2})?\s*(?:dollars?|USD)(?:/hr|/hour|\s*per\s*hour)?'
                        ]
                        for pattern in price_patterns:
                            match = re.search(pattern, all_text, re.IGNORECASE)
                            if match:
                                rate = match.group(0)
                                break
                    except Exception as e:
                        logger.debug(f"Error in regex rate extraction: {e}")
                
                # Final fallback: examine HTML structure for any price information
                if not rate:
                    try:
                        # Get the full HTML of the element
                        html_content = element.get_attribute('outerHTML')
                        import re
                        # Look for any dollar amounts in the HTML
                        html_price_patterns = [
                            r'\$\d+(?:\.\d{2})?(?:/hr|/hour|\s*per\s*hour)?',
                            r'>\$\d+(?:\.\d{2})?<',
                            r'price["\'][^>]*>\$?\d+(?:\.\d{2})?',
                            r'rate["\'][^>]*>\$?\d+(?:\.\d{2})?'
                        ]
                        for pattern in html_price_patterns:
                            match = re.search(pattern, html_content, re.IGNORECASE)
                            if match:
                                # Clean up the match to extract just the price
                                price_match = re.search(r'\$?\d+(?:\.\d{2})?', match.group(0))
                                if price_match:
                                    rate = price_match.group(0)
                                    if not rate.startswith('$'):
                                        rate = '$' + rate
                                    logger.debug(f"Found rate via HTML parsing: '{rate}'")
                                    break
                    except Exception as e:
                        logger.debug(f"Error in HTML rate extraction: {e}")
                
                # Debug logging for rate extraction
                if not rate:
                    logger.debug(f"Rate extraction debug for tasker {i+1}:")
                    logger.debug(f"  Element text: '{element.text[:200]}...'")
                    # Try to find any element with dollar sign
                    try:
                        dollar_elements = element.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                        for j, dollar_elem in enumerate(dollar_elements[:3]):
                            logger.debug(f"  Dollar element {j+1}: '{dollar_elem.text}'")
                        # Also log a snippet of the HTML for manual inspection
                        html_snippet = element.get_attribute('outerHTML')[:300]
                        logger.debug(f"  HTML snippet: {html_snippet}...")
                    except Exception as e:
                        logger.debug(f"  Debug error: {e}")
                
                # Try to get both name and rate, with enhanced fallback logic
                if rate and not name:
                    # If we have a rate but no name, try to find name in nearby elements
                    try:
                        # Look for name in parent or sibling elements
                        parent = element.find_element(By.XPATH, "./..")
                        for name_selector in name_selectors[:8]:  # Try more name selectors on parent
                            try:
                                name_element = parent.find_element(By.XPATH, name_selector)
                                potential_name = name_element.text.strip()
                                if potential_name and self.is_valid_person_name(potential_name):
                                    name = potential_name
                                    logger.debug(f"Found valid name in parent element: '{name}'")
                                    break
                            except NoSuchElementException:
                                continue
                    except Exception as e:
                        logger.debug(f"Error finding name for rate: {e}")
                
                if name and not rate:
                    # If we have a name but no rate, try to find rate in nearby elements  
                    try:
                        # Look for rate in parent or sibling elements
                        parent = element.find_element(By.XPATH, "./..")
                        for rate_selector in rate_selectors[:10]:  # Try first 10 rate selectors on parent
                            try:
                                rate_element = parent.find_element(By.XPATH, rate_selector)
                                rate_text = rate_element.text.strip()
                                if rate_text and ('$' in rate_text or '/hr' in rate_text):
                                    rate = rate_text
                                    break
                            except NoSuchElementException:
                                continue
                    except Exception as e:
                        logger.debug(f"Error finding rate for name: {e}")
                
                # Only add tasker if we have BOTH name and rate, or if we have a very high confidence single piece
                if name and rate:
                    # We have both name and rate - this is ideal
                    taskers.append({
                        'name': name,
                        'hourly_rate': rate
                    })
                    logger.info(f"Added complete tasker: {name} - {rate}")
                elif name and not rate:
                    # We have name but no rate - only add if it's a very clear name
                    if len(name.split()) >= 2 and any(char.isupper() for char in name):
                        taskers.append({
                            'name': name,
                            'hourly_rate': 'Not listed'
                        })
                        logger.info(f"Added tasker with name only: {name} - Not listed")
                elif rate and not name:
                    # We have rate but no name - skip these to avoid "Unknown" entries
                    logger.debug(f"Skipping rate-only element: {rate} (no name found)")
                    continue
                else:
                    logger.debug(f"Skipping element {i+1}: no valid name or rate found")
                    
            except Exception as e:
                logger.warning(f"Error extracting data for tasker element {i+1}: {e}")
                continue
                
        return taskers
    
    def debug_page_structure(self):
        """Debug method to inspect page structure for pagination elements."""
        try:
            logger.info("=== DEBUGGING PAGE STRUCTURE FOR PAGINATION ===")
            
            # Check for any elements containing common pagination keywords
            pagination_keywords = ['page', 'next', 'prev', 'pagination', 'pager']
            
            for keyword in pagination_keywords:
                # Look for elements with keyword in class, id, or text
                selectors = [
                    f"//*[contains(@class, '{keyword}')]",
                    f"//*[contains(@id, '{keyword}')]",
                    f"//*[contains(text(), '{keyword}')]",
                    f"//*[contains(@data-testid, '{keyword}')]"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            logger.info(f"Found {len(elements)} elements with '{keyword}' using selector: {selector}")
                            for i, element in enumerate(elements[:3]):  # Show first 3 elements
                                try:
                                    tag = element.tag_name
                                    text = element.text.strip()[:50]  # First 50 chars
                                    class_attr = element.get_attribute('class') or ''
                                    id_attr = element.get_attribute('id') or ''
                                    href = element.get_attribute('href') or ''
                                    logger.info(f"  Element {i+1}: <{tag}> text='{text}' class='{class_attr}' id='{id_attr}' href='{href}'")
                                except Exception:
                                    continue
                    except Exception:
                        continue
            
            # Also look for any numeric links (potential page numbers)
            numeric_selectors = [
                "//a[text()='1']", "//a[text()='2']", "//a[text()='3']", "//a[text()='4']", "//a[text()='5']",
                "//button[text()='1']", "//button[text()='2']", "//button[text()='3']", "//button[text()='4']", "//button[text()='5']"
            ]
            
            for selector in numeric_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.info(f"Found numeric elements with selector: {selector}")
                        for element in elements:
                            try:
                                href = element.get_attribute('href') or ''
                                class_attr = element.get_attribute('class') or ''
                                logger.info(f"  Numeric element: href='{href}' class='{class_attr}'")
                            except Exception:
                                continue
                except Exception:
                    continue
                    
            logger.info("=== END PAGE STRUCTURE DEBUG ===")
            
        except Exception as e:
            logger.error(f"Error in debug_page_structure: {e}")

    def get_available_page_numbers(self) -> List[int]:
        """Get all available page numbers from the pagination controls."""
        try:
            page_numbers = []
            
            # Add comprehensive debugging
            self.debug_page_structure()
            
            # Add debug logging to see what pagination elements exist
            logger.debug("Searching for pagination elements...")
            
            # Look for pagination controls with page numbers - expanded selectors
            pagination_selectors = [
                "//nav//a[contains(@href, 'page=')]",
                "//div[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
                "//ul[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
                "//div[contains(@class, 'page')]//a[contains(@href, 'page=')]",
                "//nav//button[contains(@aria-label, 'Page')]",
                "//div[contains(@class, 'pagination')]//button[contains(@aria-label, 'Page')]",
                "//a[contains(@href, 'page=')]",  # Any link with page parameter
                "//button[contains(@aria-label, 'Page')]",  # Any button with Page aria-label
                "//div[contains(@class, 'page')]//a",  # Any link in page-related div
                "//nav//a",  # Any link in nav
                "//div[contains(@class, 'pagination')]//a",  # Any link in pagination div
                "//ul[contains(@class, 'pagination')]//a",  # Any link in pagination ul
                "//span[contains(@class, 'page')]//a",  # Any link in page span
                "//div[contains(@data-testid, 'page')]//a",  # TaskRabbit specific
                "//div[contains(@data-testid, 'pagination')]//a"  # TaskRabbit specific
            ]
            
            # First, look specifically for MUI pagination buttons (Material-UI)
            mui_pagination_selectors = [
                "//button[contains(@class, 'MuiPaginationItem-page')]",
                "//button[contains(@class, 'MuiPaginationItem-root')]"
            ]
            
            for selector in mui_pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} MUI pagination elements with selector: {selector}")
                    
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            class_attr = element.get_attribute('class') or ''
                            
                            logger.debug(f"MUI Pagination element: text='{text}', class='{class_attr}'")
                            
                            # Extract page number from button text
                            if text.isdigit():
                                page_num = int(text)
                                if page_num not in page_numbers:
                                    page_numbers.append(page_num)
                                    logger.debug(f"Added page number {page_num} from MUI button text")
                                    
                except Exception as e:
                    logger.debug(f"Error processing MUI pagination element: {e}")
                    continue
            
            # If we found MUI pagination, check if we need to find the total number of pages
            if page_numbers:
                page_numbers.sort()
                logger.info(f"Found visible MUI page numbers: {page_numbers}")
                
                # If we see a pattern like [1,2,3,4,5,24], we need to fill in the missing pages
                # The last number is likely the total page count
                if len(page_numbers) >= 2:
                    max_page = max(page_numbers)
                    # Check if there's a gap (indicating ellipsis pagination)
                    if max_page > len(page_numbers):
                        logger.info(f"Detected ellipsis pagination. Max page: {max_page}, visible pages: {len(page_numbers)}")
                        # Generate all page numbers from 1 to max_page
                        all_pages = list(range(1, max_page + 1))
                        logger.info(f"Generated complete page range: 1 to {max_page} ({len(all_pages)} pages)")
                        return all_pages
            
                return page_numbers

            # Fallback to original selectors for other pagination types
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        if element.is_displayed():
                            # Try to extract page number from href
                            href = element.get_attribute('href') or ''
                            text = element.text.strip()
                            tag_name = element.tag_name
                            class_attr = element.get_attribute('class') or ''
                            
                            logger.debug(f"Pagination element: tag={tag_name}, text='{text}', href='{href}', class='{class_attr}'")
                            
                            # Extract page number from href
                            import re
                            if 'page=' in href:
                                page_match = re.search(r'page=(\d+)', href)
                                if page_match:
                                    page_num = int(page_match.group(1))
                                    if page_num not in page_numbers:
                                        page_numbers.append(page_num)
                                        logger.debug(f"Added page number {page_num} from href")
                            
                            # Also try to extract from text if it's a number
                            elif text.isdigit():
                                page_num = int(text)
                                if page_num not in page_numbers:
                                    page_numbers.append(page_num)
                                    logger.debug(f"Added page number {page_num} from text")
                                    
                except Exception as e:
                    logger.debug(f"Error processing pagination element: {e}")
                    continue
            
            # If we found page numbers, sort them and return
            if page_numbers:
                page_numbers.sort()
                logger.info(f"Found page numbers: {page_numbers}")
                return page_numbers
            
            # Fallback: look for text-based pagination
            text_selectors = [
                "//nav//a[text()]",
                "//div[contains(@class, 'pagination')]//a[text()]",
                "//ul[contains(@class, 'pagination')]//a[text()]"
            ]
            
            for selector in text_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.strip()
                            if text.isdigit():
                                page_num = int(text)
                                if page_num not in page_numbers:
                                    page_numbers.append(page_num)
                except Exception:
                    continue
            
            if page_numbers:
                page_numbers.sort()
                logger.info(f"Found page numbers from text: {page_numbers}")
                return page_numbers
            
            logger.debug("No pagination page numbers found")
            return []
            
        except Exception as e:
            logger.debug(f"Error getting available page numbers: {e}")
            return []
    
    def navigate_to_page_number(self, page_num: int) -> bool:
        """Navigate to a specific page number by clicking the page button."""
        try:
            # First, try MUI pagination buttons (Material-UI)
            mui_page_selectors = [
                f"//button[contains(@class, 'MuiPaginationItem-page') and text()='{page_num}']",
                f"//button[contains(@class, 'MuiPaginationItem-root') and text()='{page_num}']"
            ]
            
            for selector in mui_page_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Check if it's not the current page
                            element_class = element.get_attribute('class') or ''
                            aria_current = element.get_attribute('aria-current') or ''
                            
                            # Skip if it's the current page
                            if ('selected' in element_class.lower() or 
                                'current' in element_class.lower() or 
                                'active' in element_class.lower() or
                                aria_current == 'page'):
                                logger.debug(f"Skipping current page button for page {page_num}")
                                continue
                            
                            # Try JavaScript click first (more reliable for React/MUI components)
                            try:
                                logger.info(f"Trying JavaScript click for MUI page {page_num} button")
                                self.driver.execute_script("arguments[0].click();", element)
                                time.sleep(4)  # Wait longer for JavaScript navigation
                                
                                # Check if navigation succeeded by looking for page content changes
                                # Verify by checking if the current page indicator has changed
                                current_page_elements = self.driver.find_elements(By.XPATH, 
                                    f"//button[contains(@class, 'MuiPaginationItem') and (contains(@class, 'selected') or @aria-current='page') and text()='{page_num}']")
                                
                                if current_page_elements:
                                    logger.info(f"Successfully navigated to page {page_num} via JavaScript (verified by selected state)")
                                    return True
                                
                                # Alternative: check URL
                                current_url = self.driver.current_url
                                if f"page={page_num}" in current_url:
                                    logger.info(f"Successfully navigated to page {page_num} via JavaScript (verified by URL)")
                                    return True
                                    
                            except Exception as js_error:
                                logger.debug(f"JavaScript click failed: {js_error}")
                            
                            # Fallback to regular click
                            logger.info(f"Trying regular click for MUI page {page_num} button with selector: {selector}")
                            element.click()
                            
                            # Wait for page to load and verify navigation
                            time.sleep(3)
                            
                            # Verify that we've navigated to the correct page
                            current_url = self.driver.current_url
                            if f"page={page_num}" in current_url:
                                logger.info(f"Successfully navigated to page {page_num}")
                                return True
                            else:
                                # Try to wait a bit more and check again
                                time.sleep(2)
                                current_url = self.driver.current_url
                                if f"page={page_num}" in current_url:
                                    logger.info(f"Successfully navigated to page {page_num} after additional wait")
                                    return True
                                else:
                                    # Alternative verification: check if page content has changed
                                    # Look for current page indicator in pagination
                                    try:
                                        current_page_elements = self.driver.find_elements(By.XPATH, 
                                            f"//button[contains(@class, 'MuiPaginationItem') and (contains(@class, 'selected') or @aria-current='page') and text()='{page_num}']")
                                        if current_page_elements:
                                            logger.info(f"Successfully navigated to page {page_num} (verified by selected state)")
                                            return True
                                    except Exception:
                                        pass
                                    
                                    logger.debug(f"Navigation to page {page_num} may have failed - URL is {current_url}")
                                    # Continue to try other selectors
                            
                except Exception as e:
                    logger.debug(f"Error with MUI page selector {selector}: {e}")
                    continue
            
            # Fallback to traditional page selectors
            page_selectors = [
                f"//nav//a[contains(@href, 'page={page_num}')]",
                f"//div[contains(@class, 'pagination')]//a[contains(@href, 'page={page_num}')]",
                f"//ul[contains(@class, 'pagination')]//a[contains(@href, 'page={page_num}')]",
                f"//div[contains(@class, 'page')]//a[contains(@href, 'page={page_num}')]",
                f"//nav//a[text()='{page_num}']",
                f"//div[contains(@class, 'pagination')]//a[text()='{page_num}']",
                f"//ul[contains(@class, 'pagination')]//a[text()='{page_num}']",
                f"//nav//button[contains(@aria-label, 'Page {page_num}')]",
                f"//div[contains(@class, 'pagination')]//button[contains(@aria-label, 'Page {page_num}')]"
            ]
            
            for selector in page_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            # Check if it's not disabled or current page
                            element_class = element.get_attribute('class') or ''
                            aria_current = element.get_attribute('aria-current') or ''
                            
                            # Skip if it's the current page or disabled
                            if ('disabled' in element_class.lower() or 
                                'current' in element_class.lower() or 
                                'active' in element_class.lower() or
                                aria_current == 'page'):
                                logger.debug(f"Skipping current/disabled page button for page {page_num}")
                                continue
                            
                            # Click the page number button
                            logger.info(f"Clicking page {page_num} button with selector: {selector}")
                            element.click()
                            return True
                            
                except Exception as e:
                    logger.debug(f"Error with page selector {selector}: {e}")
                    continue
            
            logger.debug(f"No clickable page {page_num} button found")
            return False
            
        except Exception as e:
            logger.debug(f"Error navigating to page {page_num}: {e}")
            return False
    
    def check_for_next_page(self) -> bool:
        """Check if there's a next page available for pagination."""
        try:
            # Look for pagination indicators
            next_page_selectors = [
                "//a[contains(@aria-label, 'Next')]",
                "//button[contains(@aria-label, 'Next')]",
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]",
                "//a[contains(@class, 'next')]",
                "//button[contains(@class, 'next')]",
                "//a[@rel='next']",
                "//button[@rel='next']",
                "//a[contains(@href, 'page=')][last()]",  # Last pagination link
                "//nav//a[last()]",  # Last link in navigation
                "//div[contains(@class, 'pagination')]//a[last()]"
            ]
            
            for selector in next_page_selectors:
                try:
                    next_elements = self.driver.find_elements(By.XPATH, selector)
                    for element in next_elements:
                        if element.is_displayed() and element.is_enabled():
                            # Check if it's actually a "next" link and not disabled
                            element_text = element.text.lower()
                            element_class = element.get_attribute('class') or ''
                            element_href = element.get_attribute('href') or ''
                            
                            # Skip if it's disabled
                            if 'disabled' in element_class.lower():
                                continue
                            
                            # Check if it's a valid next page link
                            if ('next' in element_text or 
                                'next' in element_class.lower() or
                                'page=' in element_href):
                                logger.debug(f"Found next page indicator: {selector}")
                                return True
                except Exception:
                    continue
            
            # Alternative method: Check current page number vs total pages
            try:
                # Look for page indicators like "Page 1 of 24" or similar
                
                current_url = self.driver.current_url
                if 'page=' in current_url:
                    # Extract current page number from URL
                    import re
                    page_match = re.search(r'page=(\d+)', current_url)
                    if page_match:
                        current_page = int(page_match.group(1))
                        
                        # Try to find total pages in the page content
                        page_source = self.driver.page_source
                        total_pages_patterns = [
                            rf'Page {current_page} of (\d+)',
                            rf'{current_page} of (\d+)',
                            rf'page {current_page} of (\d+)',
                            r'of (\d+) pages?'
                        ]
                        
                        for pattern in total_pages_patterns:
                            match = re.search(pattern, page_source, re.IGNORECASE)
                            if match:
                                total_pages = int(match.group(1))
                                logger.debug(f"Found pagination info: page {current_page} of {total_pages}")
                                return current_page < total_pages
                
            except Exception as e:
                logger.debug(f"Error checking page numbers: {e}")
            
            # Check if there are more pages by looking for page numbers
            try:
                # Look for pagination with page numbers
                page_number_selectors = [
                    "//nav//a[contains(@href, 'page=')]",
                    "//div[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
                    "//ul[contains(@class, 'pagination')]//a[contains(@href, 'page=')]"
                ]
                
                current_url = self.driver.current_url
                import re
                current_page_match = re.search(r'page=(\d+)', current_url)
                current_page = int(current_page_match.group(1)) if current_page_match else 1
                
                for selector in page_number_selectors:
                    try:
                        page_elements = self.driver.find_elements(By.XPATH, selector)
                        for element in page_elements:
                            href = element.get_attribute('href') or ''
                            page_match = re.search(r'page=(\d+)', href)
                            if page_match:
                                page_num = int(page_match.group(1))
                                if page_num > current_page:
                                    logger.debug(f"Found higher page number: {page_num}")
                                    return True
                    except Exception:
                        continue
                        
            except Exception as e:
                logger.debug(f"Error checking page numbers: {e}")
            
            # Final check: Look for any indication of more results
            try:
                page_source = self.driver.page_source.lower()
                more_indicators = ['show more', 'load more', 'next page', 'page 2', 'more results']
                if any(indicator in page_source for indicator in more_indicators):
                    logger.debug("Found indication of more pages in page source")
                    return True
            except Exception as e:
                logger.debug(f"Error checking page source: {e}")
            
            logger.debug("No next page found")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking for next page: {e}")
            return False
    
    def save_to_csv(self, taskers: List[Dict[str, str]], filename: str = "taskrabbit_taskers.csv"):
        """Save tasker data to CSV file."""
        logger.info(f"Saving data to {filename}...")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'hourly_rate']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for tasker in taskers:
                writer.writerow(tasker)
                
        logger.info(f"Successfully saved {len(taskers)} taskers to {filename}")
    
    def run(self):
        """Main execution method."""
        try:
            logger.info("Starting TaskRabbit parser...")
            self.setup_driver()
            
            # Navigate through the booking flow
            self.navigate_to_furniture_assembly()
            self.enter_address_details()
            self.select_furniture_options()
            self.sort_by_recommended()
            
            # Extract and save data from all pages
            taskers = self.extract_tasker_data()
            
            if taskers:
                self.save_to_csv(taskers)
                logger.info(f"Successfully extracted {len(taskers)} taskers")
            else:
                logger.error("No taskers found!")
                
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")

if __name__ == "__main__":
    parser = TaskRabbitParser(headless=False)  # Set to True for headless mode
    parser.run()
