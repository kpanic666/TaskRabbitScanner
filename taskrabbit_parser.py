#!/usr/bin/env python3
"""
TaskRabbit Furniture Assembly Tasker Parser

This script automates the TaskRabbit booking flow to extract top 10 taskers
for Furniture Assembly category and saves their names and hourly rates to CSV.
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
                        except:
                            # Try JavaScript click if regular click fails
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"Closed overlay/popup with JavaScript: {selector}")
                                time.sleep(1)
                            except:
                                continue
            except:
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
                        except:
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
        selected_selector = None
        
        for selector in furniture_type_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        both_option = element
                        selected_selector = selector
                        logger.info(f"Found 'Both IKEA and non-IKEA furniture' option with selector: {selector}")
                        logger.info(f"Element text: '{element.text}'")
                        break
                if both_option:
                    break
            except Exception as e:
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
                    except:
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
        selected_selector = None
        
        for selector in size_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        medium_option = element
                        selected_selector = selector
                        logger.info(f"Found 'Medium - Est. 2-3 hrs' option with selector: {selector}")
                        logger.info(f"Element text: '{element.text}'")
                        break
                if medium_option:
                    break
            except Exception as e:
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
                    except:
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
        selected_selector = None
        
        for selector in task_details_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        task_details_field = element
                        selected_selector = selector
                        logger.info(f"Found task details field with selector: {selector}")
                        logger.info(f"Element tag: '{element.tag_name}', placeholder: '{element.get_attribute('placeholder')}'")
                        break
                if task_details_field:
                    break
            except Exception as e:
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
        """Extract top 10 taskers' names and hourly rates."""
        logger.info("Extracting tasker data...")
        self.debug_page_elements("Before extracting tasker data")
        taskers = []
        
        # Wait for tasker cards to load
        time.sleep(5)
        
        # Find tasker cards/elements with multiple selectors
        tasker_selectors = [
            "//div[contains(@class, 'tasker')]",
            "//div[contains(@class, 'card')]",
            "//div[contains(@data-testid, 'tasker')]",
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
        
        for i, element in enumerate(tasker_elements[:10]):  # Get top 10
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
                
                # Accept taskers with either name or rate (we'll try to get both but don't require both)
                if name or rate:
                    # If we have a rate but no name, try to find name in nearby elements
                    if rate and not name:
                        try:
                            # Look for name in parent or sibling elements
                            parent = element.find_element(By.XPATH, "./..")
                            for name_selector in name_selectors[:5]:  # Try first 5 name selectors on parent
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
                    
                    # If we have a name but no rate, try to find rate in nearby elements  
                    if name and not rate:
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
                    
                    # Add tasker if we have at least a name or rate
                    taskers.append({
                        'name': name or 'Unknown',
                        'hourly_rate': rate or 'Not listed'
                    })
                    logger.info(f"Added tasker: {name or 'Unknown'} - {rate or 'Not listed'}")
                else:
                    logger.warning(f"Could not extract any data for tasker element {i+1}: name='{name}', rate='{rate}'")
                    
            except Exception as e:
                logger.warning(f"Error extracting data for tasker element {i+1}: {e}")
                continue
                
        return taskers
    
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
            
            # Extract and save data
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
