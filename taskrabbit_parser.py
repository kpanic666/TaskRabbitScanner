#!/usr/bin/env python3
"""
TaskRabbit Multi-Category Tasker Parser

This script automates the TaskRabbit booking flow to extract all available taskers
for multiple categories (Furniture Assembly, Plumbing, etc.) and saves their names 
and hourly rates to CSV files organized by category.
Supports dynamic pagination to capture taskers from multiple pages.
"""

import time
import csv
import logging
import re
import os
from datetime import datetime
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration constants - modify these to adjust behavior
MAX_PAGES_FOR_TESTING = None      # Set to None to scan all pages, or number to limit pages

# Sleep duration constants (in seconds) - modify these to adjust timing
SLEEP_OVERLAY_REMOVAL = 1          # After removing overlays/popups
SLEEP_IFRAME_REMOVAL = 0.5         # After removing iframe overlays
SLEEP_CONTINUE_BUTTON = 1          # After clicking continue buttons
SLEEP_PAGE_LOAD = 1                # General page loading wait
SLEEP_SCROLL_WAIT = 0.5              # After scrolling elements into view
SLEEP_ADDRESS_INPUT = 2            # After entering address
SLEEP_ADDRESS_CONTINUE = 2         # After clicking continue from address
SLEEP_FURNITURE_OPTION = 1         # After selecting furniture options
SLEEP_SIZE_OPTION = 1              # After selecting size options
SLEEP_TASK_DETAILS = 1             # After entering task details
SLEEP_OPTIONS_COMPLETE = 1         # After completing all options
SLEEP_PAGE_NAVIGATION = 1         # After navigating to new page
SLEEP_CARD_LOADING = 1             # Waiting for tasker cards to load

# Category configuration
CATEGORIES = {
    'furniture_assembly': {
        'name': 'Furniture Assembly',
        'url': 'https://www.taskrabbit.com/services/handyman/assemble-furniture',
        'options': [
            {'type': 'furniture_type', 'value': 'Both IKEA and non-IKEA furniture'},
            {'type': 'size', 'value': 'Medium - Est. 2-3 hrs'},
            {'type': 'task_details', 'value': 'build stool'}
        ]
    },
    'plumbing': {
        'name': 'Plumbing',
        'url': 'https://www.taskrabbit.com/services/handyman/plumbing',
        'options': [
            # Plumbing skips furniture type selection and goes directly to size and task details
            {'type': 'size', 'value': 'Medium - Est. 2-3 hrs'},
            {'type': 'task_details', 'value': 'fix leaky faucet', 'final_button': 'See taskers & Price'}
        ]
    }
}

class TaskRabbitParser:
    def __init__(self, category: str = 'furniture_assembly', headless: bool = False, max_pages: int = None):
        """Initialize the TaskRabbit parser with Chrome WebDriver."""
        self.base_url = "https://www.taskrabbit.com"
        self.driver = None
        self.wait = None
        self.headless = headless
        self.max_pages = max_pages  # Limit number of pages to process (None = all pages)
        
        # Category configuration
        if category not in CATEGORIES:
            raise ValueError(f"Category '{category}' not supported. Available categories: {list(CATEGORIES.keys())}")
        
        self.category = category
        self.category_config = CATEGORIES[category]
        self.category_name = self.category_config['name']
        
        # Generate CSV filename with category and timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        category_filename = self.category_name.replace(' ', '_').lower()
        self.csv_filename = f"Taskers/{category_filename}_{timestamp}.csv"
        
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
                    time.sleep(SLEEP_OVERLAY_REMOVAL)
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
                    time.sleep(SLEEP_OVERLAY_REMOVAL)
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
                            time.sleep(SLEEP_OVERLAY_REMOVAL)
                        except Exception as e:
                            # Try JavaScript click if regular click fails
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                logger.info(f"Closed overlay/popup with JavaScript: {selector}")
                                time.sleep(SLEEP_OVERLAY_REMOVAL)
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
            time.sleep(SLEEP_OVERLAY_REMOVAL)
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
                        time.sleep(SLEEP_IFRAME_REMOVAL)
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
                                time.sleep(SLEEP_IFRAME_REMOVAL)
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
                time.sleep(SLEEP_CONTINUE_BUTTON)
                return True
            except TimeoutException:
                continue
        
        logger.info("No Continue button found, proceeding without clicking")
        return False
    
    def navigate_to_category_page(self):
        """Navigate directly to the category page using configured URL"""
        logger.info(f"Navigating directly to {self.category_name} page...")
        
        # Go directly to the category page
        direct_url = self.category_config['url']
        self.driver.get(direct_url)
        time.sleep(3)
        
        logger.info(f"Loaded {self.category_name} page directly: {direct_url}")
        
        # Close any overlays that might appear even with direct navigation
        self.close_overlays_and_popups()
        
        self.debug_page_elements(f"{self.category_name} page (direct navigation)")
        
        # Try to find a direct booking link or navigate to category booking
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
                        time.sleep(SLEEP_OVERLAY_REMOVAL)
                        self.driver.execute_script("arguments[0].click();", book_now)
                        logger.info("Successfully clicked Book Now button after scrolling")
                    except Exception as e3:
                        logger.error(f"All click methods failed: {e3}")
                        raise Exception("Could not click Book Now button")
            
            time.sleep(SLEEP_CONTINUE_BUTTON)
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
                    time.sleep(SLEEP_CONTINUE_BUTTON)
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
        time.sleep(SLEEP_ADDRESS_INPUT)
        
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
        time.sleep(SLEEP_ADDRESS_CONTINUE)
        self.debug_page_elements("After clicking Continue")
        
    def select_category_options(self):
        """Select category-specific options through the booking flow."""
        logger.info(f"Selecting {self.category_name} options...")
        self.debug_page_elements(f"Before selecting {self.category_name} options")
        
        # Process each option defined in the category configuration
        for option in self.category_config['options']:
            option_type = option['type']
            option_value = option['value']
            
            logger.info(f"Processing option: {option_type} = {option_value}")
            
            if option_type == 'furniture_type':
                self._select_furniture_type_option(option_value)
            elif option_type == 'size':
                self._select_size_option(option_value)
            elif option_type == 'task_details':
                final_button = option.get('final_button')
                self._enter_task_details(option_value, final_button)
            elif option_type == 'plumbing_type':
                self._select_plumbing_type_option(option_value)
            else:
                logger.warning(f"Unknown option type: {option_type}")
        
        time.sleep(SLEEP_OPTIONS_COMPLETE)
        self.debug_page_elements(f"After {self.category_name} options selection")
    
    def _select_furniture_type_option(self, option_value: str):
        """Select furniture type option (for furniture assembly category)."""
        
        logger.info(f"Looking for '{option_value}' option...")
        
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
        
        # Comprehensive selectors for the furniture type option
        furniture_type_selectors = [
            # Direct text matches
            f"//button[contains(text(), '{option_value}')]",
            f"//label[contains(text(), '{option_value}')]",
            f"//div[contains(text(), '{option_value}')]",
            f"//span[contains(text(), '{option_value}')]",
            
            # Variations with different casing
            "//button[contains(text(), 'Both IKEA and non-IKEA')]",
            "//button[contains(text(), 'IKEA and non-IKEA')]",
            "//label[contains(text(), 'Both IKEA and non-IKEA')]",
            "//label[contains(text(), 'IKEA and non-IKEA')]",
            
            # Radio button or checkbox inputs with associated labels
            f"//input[@type='radio']/following-sibling::*[contains(text(), '{option_value}')]",
            f"//input[@type='checkbox']/following-sibling::*[contains(text(), '{option_value}')]",
            f"//input[@type='radio']/parent::*[contains(text(), '{option_value}')]",
            f"//input[@type='checkbox']/parent::*[contains(text(), '{option_value}')]",
            
            # Value-based selections
            "//input[@value='both']",
            "//input[@value='both_ikea_non_ikea']",
            f"//option[contains(text(), '{option_value}')]",
            
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
                        logger.info(f"Found '{option_value}' option with selector: {selector}")
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
                
                time.sleep(SLEEP_FURNITURE_OPTION)
                logger.info(f"Successfully selected '{option_value}' option")
            except Exception as e:
                logger.warning(f"Failed to click furniture option: {e}")
                # Try JavaScript click as fallback
                try:
                    self.driver.execute_script("arguments[0].click();", both_option)
                    logger.info("Successfully selected furniture option using JavaScript click")
                except Exception as e2:
                    logger.error(f"Failed to select furniture option with JavaScript: {e2}")
        else:
            logger.warning(f"Could not find '{option_value}' option")
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
    
    def _select_size_option(self, option_value: str):
        """Select size option."""
        logger.info(f"Looking for '{option_value}' size selection...")
        
        # Comprehensive selectors for the size option
        size_selectors = [
            # Direct text matches with full text
            f"//button[contains(text(), '{option_value}')]",
            f"//label[contains(text(), '{option_value}')]",
            f"//div[contains(text(), '{option_value}')]",
            f"//span[contains(text(), '{option_value}')]",
            
            # Variations with different formatting
            "//button[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//label[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//div[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            "//span[contains(text(), 'Medium') and contains(text(), '2-3 hrs')]",
            
            # Radio button or checkbox inputs with associated labels
            f"//input[@type='radio']/following-sibling::*[contains(text(), '{option_value}')]",
            f"//input[@type='checkbox']/following-sibling::*[contains(text(), '{option_value}')]",
            f"//input[@type='radio']/parent::*[contains(text(), '{option_value}')]",
            f"//input[@type='checkbox']/parent::*[contains(text(), '{option_value}')]",
            
            # Value-based selections
            "//input[@value='medium']",
            "//input[@value='medium_2_3_hrs']",
            f"//option[contains(text(), '{option_value}')]",
            
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
                        logger.info(f"Found '{option_value}' option with selector: {selector}")
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
                
                time.sleep(SLEEP_SIZE_OPTION)
                logger.info(f"Successfully selected '{option_value}' option")
                
                # Scroll down to make sure Continue button is visible
                logger.info("Scrolling down to reveal Continue button...")
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(SLEEP_SCROLL_WAIT)
                
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
            logger.warning(f"Could not find '{option_value}' option")
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
    
    def _enter_task_details(self, task_details: str, final_button: str = None):
        """Enter task details in the text field."""
        logger.info(f"Looking for task details text box to enter '{task_details}'...")
        
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
                # Clear the field and enter task details
                task_details_field.clear()
                task_details_field.send_keys(task_details)
                time.sleep(SLEEP_TASK_DETAILS)
                logger.info(f"Successfully entered '{task_details}' in task details field")
                
                # Scroll down to make sure button is visible
                logger.info("Scrolling down to reveal button...")
                self.driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(SLEEP_SCROLL_WAIT)
                
                if final_button:
                    self.click_final_button(final_button)
                else:
                    self.click_continue_button()
            except Exception as e:
                logger.warning(f"Failed to enter task details: {e}")
                # Try JavaScript approach as fallback
                try:
                    self.driver.execute_script(f"arguments[0].value = '{task_details}';", task_details_field)
                    logger.info("Successfully entered task details using JavaScript")
                    if final_button:
                        self.click_final_button(final_button)
                    else:
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
    
    def click_final_button(self, button_text: str):
        """Click the final button with specific text (e.g., 'See taskers & Price')."""
        logger.info(f"Looking for '{button_text}' button...")
        
        # Comprehensive selectors for the final button
        button_selectors = [
            f"//button[contains(text(), '{button_text}')]",
            f"//a[contains(text(), '{button_text}')]",
            f"//input[@type='submit' and contains(@value, '{button_text}')]",
            f"//button[contains(@aria-label, '{button_text}')]",
            f"//div[contains(@role, 'button') and contains(text(), '{button_text}')]",
            # Fallback patterns for "See taskers & Price"
            "//button[contains(text(), 'See taskers')]",
            "//a[contains(text(), 'See taskers')]",
            "//button[contains(text(), 'taskers') and contains(text(), 'Price')]",
            "//a[contains(text(), 'taskers') and contains(text(), 'Price')]"
        ]
        
        for selector in button_selectors:
            try:
                final_btn = WebDriverWait(self.driver, SLEEP_CONTINUE_BUTTON).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                logger.info(f"Found '{button_text}' button with selector: {selector}")
                final_btn.click()
                time.sleep(SLEEP_CONTINUE_BUTTON)
                return True
            except TimeoutException:
                continue
        
        logger.warning(f"No '{button_text}' button found, trying default continue button")
        return self.click_continue_button()
    
    def _select_plumbing_type_option(self, option_value: str):
        """Select plumbing type option (for plumbing category)."""
        logger.info(f"Looking for plumbing option: '{option_value}'...")
        
        # For plumbing, the flow might be simpler and go directly to task details
        # This is a placeholder that can be expanded based on actual plumbing page structure
        logger.info("Plumbing category detected - using simplified flow")
        
        # Continue to next step
        self.click_continue_button()
               
    def is_valid_person_name(self, name: str) -> bool:
        """Check if a string looks like a valid person name."""
        if not name or len(name) < 3:
            return False
        
        # Should contain at least one space and end with a period (initial)
        if ' ' not in name or not name.endswith('.'):
            return False
        
        # Should not contain numbers or special characters (except period)
        if any(char.isdigit() or char in '!@#$%^&*()_+=[]{}|;:,<>?/~`' for char in name.replace('.', '')):
            return False
        
        # Should be reasonable length
        if len(name) > 50:
            return False
        
        # Split into parts and validate structure
        parts = name.split()
        if len(parts) < 2:
            return False
        
        # Last part should be a single letter followed by period (initial)
        if not (len(parts[-1]) == 2 and parts[-1][0].isalpha() and parts[-1][1] == '.'):
            return False
        
        # All other parts should be alphabetic (first name, middle names, etc.)
        for part in parts[:-1]:
            if not part.isalpha():
                return False
        
        return True
    
    def is_potential_name(self, text: str) -> bool:
        """More flexible name validation for initial extraction."""
        if not text or len(text) < 3 or len(text) > 50:
            return False
        
        # Should end with a period (initial)
        if not text.endswith('.'):
            return False
        
        # Should contain at least one space
        if ' ' not in text:
            return False
        
        # Should not contain obvious non-name content
        if any(word in text.lower() for word in ['review', 'task', 'hour', '$', '/hr', 'read', 'more', 'select', 'continue']):
            return False
        
        # Should have reasonable word count (2-4 words)
        word_count = len(text.split())
        if word_count < 2 or word_count > 4:
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
                time.sleep(SLEEP_PAGE_NAVIGATION)  # Wait for page to load after clicking
            
            # Debug: capture all visible names before extraction
            self.debug_visible_names()
            
            # Extract taskers from current page
            page_taskers = self.extract_taskers_from_current_page()
            
            if not page_taskers:
                logger.warning(f"No taskers found on page {page_num}, but continuing to next page...")
                continue  # Continue to next page instead of breaking
            
            logger.info(f"Found {len(page_taskers)} taskers on page {page_num}")
            all_taskers.extend(page_taskers)
        
        logger.info(f"Total taskers extracted from all pages: {len(all_taskers)}")
        return all_taskers
    
    def extract_all_visible_text(self):
        """Extract all visible text that might be tasker names and rates."""
        logger.debug("Extracting all visible text...")
        
        potential_names = []
        rates = []
        
        # Extract names from span elements (tasker name buttons)
        name_selectors = [
            ".//span[contains(@class, 'mui-5xjf89')]",
            ".//button[contains(@class, 'TRTextButtonPrimary-Root') or contains(@class, 'mui-1pbxn54')]",
            ".//button[contains(@class, 'MuiButton-textPrimary')]"
        ]
        
        for selector in name_selectors:
            try:
                name_elements = self.driver.find_elements(By.XPATH, selector)
                for element in name_elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if (text and 
                            '.' in text and 
                            len(text) < 50 and 
                            len(text.split()) <= 3 and  # Max 3 words
                            any(c.isalpha() for c in text) and
                            not any(keyword in text.lower() for keyword in ['select', 'continue', 'read', 'more', 'book', 'view', 'how', 'help', 'about', 'task', 'review', 'experience'])):
                            potential_names.append(text)
            except Exception as e:
                logger.debug(f"Error extracting names with selector {selector}: {e}")
                continue
        
        # Extract rates from specific rate elements
        rate_selectors = [
            "//div[contains(@class, 'mui-loubxv')]",  # Primary rate selector from HTML analysis
            "//div[contains(@class, 'rate') and contains(text(), '$') and contains(text(), '/hr')]",
            "//span[contains(text(), '$') and contains(text(), '/hr')]",
            "//div[contains(text(), '$') and contains(text(), '/hr')]"
        ]
        
        for selector in rate_selectors:
            try:
                rate_elements = self.driver.find_elements(By.XPATH, selector)
                for element in rate_elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if '$' in text and '/hr' in text and len(text) < 20:
                            rates.append(text)
            except Exception as e:
                logger.debug(f"Error extracting rates with selector {selector}: {e}")
                continue
        
        # Remove duplicates
        potential_names = list(set(potential_names))
        rates = list(set(rates))
        
        logger.info(f"Extracted {len(potential_names)} potential names and {len(rates)} rates")
        
        return potential_names, rates

    def extract_taskers_from_current_page(self) -> List[Dict[str, str]]:
        """Extract tasker names and hourly rates from the current page only."""
        logger.debug("Extracting taskers from current page...")
        taskers = []
        
        # Enhanced debug logging to capture what we actually see
        logger.info(f"Current URL: {self.driver.current_url}")
        logger.info(f"Page title: {self.driver.title}")
        
        # Wait for tasker cards to load
        time.sleep(SLEEP_CARD_LOADING)  # Increased wait time for better loading
        
        # Find tasker cards using the mobile card selector from HTML analysis
        tasker_card_selector = "//div[@data-testid='tasker-card-mobile']"
        tasker_cards = self.driver.find_elements(By.XPATH, tasker_card_selector)
        
        if not tasker_cards:
            # Fallback to other selectors
            fallback_selectors = [
                "//div[contains(@class, 'mui-1m4n54b')]",  # From HTML analysis
                "//div[contains(@data-testid, 'tasker')]",
                "//div[contains(@class, 'tasker')]",
                "//div[contains(@class, 'card')]"
            ]
            
            for selector in fallback_selectors:
                tasker_cards = self.driver.find_elements(By.XPATH, selector)
                if tasker_cards:
                    logger.info(f"Found {len(tasker_cards)} tasker cards with fallback selector: {selector}")
                    break
        else:
            logger.info(f"Found {len(tasker_cards)} tasker cards with primary selector")
        
        if not tasker_cards:
            logger.error("No tasker cards found on page")
            return []
        
        # Limit to 15 taskers per page as specified
        if len(tasker_cards) > 15:
            logger.info(f"Found {len(tasker_cards)} cards, limiting to 15 per page as specified")
            tasker_cards = tasker_cards[:15]
        logger.info(f"Processing {len(tasker_cards)} tasker cards")
        
        # Extract name and rate from each card
        for i, card in enumerate(tasker_cards):
            try:
                # Extract name from span within the card (names are in review sections)
                name = "Name not found"
                name_selectors = [
                    ".//button[contains(@class, 'mui-1pbxn54')]",  # Primary: Tasker name buttons
                    ".//button[contains(@class, 'TRTextButtonPrimary-Root')]",  # Secondary: Button fallback
                    ".//span[contains(@class, 'mui-5xjf89')]",  # Tertiary: Review names (not tasker names)
                    ".//h3",  # Generic heading fallback
                    ".//*[text()[contains(., '.') and string-length(.) < 20]]",  # Any element with dot pattern
                ]
                
                for selector in name_selectors:
                    try:
                        name_elements = card.find_elements(By.XPATH, selector)
                        for name_element in name_elements:
                            if name_element and name_element.is_displayed():
                                name_text = name_element.text.strip()
                                # More flexible name validation
                                if self.is_potential_name(name_text):
                                    name = name_text
                                    break
                        if name != "Name not found":
                            break
                    except Exception:
                        continue
                
                # If still not found, try more aggressive extraction approaches
                if name == "Name not found":
                    try:
                        # Strategy 1: Extract from all card text using regex
                        card_text = card.text
                        import re
                        # Look for name patterns: "FirstName L." or "FIRSTNAME L." 
                        name_patterns = re.findall(r'\b[A-Z][a-z]+ [A-Z]\.|\b[A-Z][A-Z]+ [A-Z]\.', card_text)
                        if name_patterns:
                            name = name_patterns[0]
                        else:
                            # Strategy 2: Look for any text element with name pattern
                            all_text_elements = card.find_elements(By.XPATH, ".//*[text()]")
                            for elem in all_text_elements:
                                elem_text = elem.text.strip()
                                if self.is_potential_name(elem_text):
                                    name = elem_text
                                    break
                            
                            # Strategy 3: Look for specific patterns in card HTML
                            if name == "Name not found":
                                # Try to find names in the card's innerHTML
                                card_html = card.get_attribute('innerHTML')
                                if card_html:
                                    # Look for names in button text or span text
                                    html_name_patterns = re.findall(r'>([A-Z][a-z]+ [A-Z]\.)<|>([A-Z][A-Z]+ [A-Z]\.)<', card_html)
                                    for pattern_match in html_name_patterns:
                                        potential_name = pattern_match[0] or pattern_match[1]
                                        if potential_name and self.is_potential_name(potential_name):
                                            name = potential_name
                                            break
                    except Exception as e:
                        logger.debug(f"Error in fallback name extraction: {e}")
                        pass
                
                if name == "Name not found":
                    # Debug: Show what text is actually in this card
                    try:
                        card_text = card.text.strip()
                        logger.warning(f"Could not find valid name in card {i+1}. Card text preview: '{card_text[:200]}...'")
                        
                        # Debug: Show all buttons in this card
                        all_buttons = card.find_elements(By.XPATH, ".//button")
                        logger.debug(f"Card {i+1} has {len(all_buttons)} buttons:")
                        for btn_idx, btn in enumerate(all_buttons[:5]):  # Show first 5 buttons
                            try:
                                btn_text = btn.text.strip()
                                if btn_text:
                                    logger.debug(f"  Button {btn_idx+1}: '{btn_text}' (classes: {btn.get_attribute('class')})")
                            except Exception:
                                pass
                    except Exception as e:
                        logger.debug(f"Error debugging card {i+1}: {e}")
                    continue
                
                # Additional validation with is_valid_person_name
                if not self.is_valid_person_name(name):
                    logger.warning(f"Invalid name format in card {i+1}: '{name}'")
                    continue
                
                # Extract rate from rate element within the card
                rate = "Rate not found"
                rate_selectors = [
                    ".//div[contains(@class, 'mui-loubxv')]",  # Primary rate selector from HTML analysis
                    ".//*[contains(text(), '$') and contains(text(), '/hr')]",  # Direct text search
                    ".//*[contains(text(), '$')]",  # Any element with $
                    ".//div[contains(@class, 'rate')]",
                    ".//span[contains(text(), '$')]"
                ]
                
                for selector in rate_selectors:
                    try:
                        rate_elements = card.find_elements(By.XPATH, selector)
                        for rate_element in rate_elements:
                            if rate_element and rate_element.is_displayed():
                                rate_text = rate_element.text.strip()
                                # Look for rate pattern like $39.23/hr
                                if '$' in rate_text and '/hr' in rate_text and len(rate_text) < 20:
                                    # Validate it's a proper rate format
                                    import re
                                    if re.search(r'\$\d+\.\d+/hr', rate_text):
                                        rate = rate_text
                                        break
                        if rate != "Rate not found":
                            break
                    except Exception:
                        continue
                
                # If rate still not found, try more aggressive extraction methods
                if rate == "Rate not found":
                    try:
                        # Strategy 1: Extract from card text
                        card_text = card.text
                        import re
                        rate_matches = re.findall(r'\$\d+\.\d+/hr', card_text)
                        if rate_matches:
                            rate = rate_matches[0]
                        else:
                            # Strategy 2: Extract from innerHTML
                            card_html = card.get_attribute('innerHTML')
                            if card_html:
                                html_rate_matches = re.findall(r'\$\d+\.\d+/hr', card_html)
                                if html_rate_matches:
                                    rate = html_rate_matches[0]
                                else:
                                    # Strategy 3: Look for any price pattern in HTML
                                    price_matches = re.findall(r'\$(\d+\.\d+)', card_html)
                                    if price_matches:
                                        rate = f"${price_matches[0]}/hr"
                    except Exception:
                        pass
                
                # Extract review rating and count
                review_rating = "Not found"
                review_count = "Not found"
                try:
                    # Look for review pattern like "5.0 (64 reviews)"
                    review_selectors = [
                        ".//*[contains(text(), '(') and contains(text(), 'review')]",
                        ".//*[contains(text(), '★') or contains(text(), '⭐')]"
                    ]
                    
                    for selector in review_selectors:
                        review_elements = card.find_elements(By.XPATH, selector)
                        for elem in review_elements:
                            text = elem.text.strip()
                            import re
                            # Match pattern like "5.0 (64 reviews)" or "★ 5.0 (64 reviews)"
                            match = re.search(r'(\d+\.\d+)\s*\((\d+)\s*review', text)
                            if match:
                                review_rating = match.group(1)
                                review_count = match.group(2)
                                break
                        if review_rating != "Not found":
                            break
                    
                    # If not found, try extracting from card text and HTML
                    if review_rating == "Not found":
                        card_text = card.text
                        match = re.search(r'(\d+\.\d+)\s*\((\d+)\s*review', card_text)
                        if match:
                            review_rating = match.group(1)
                            review_count = match.group(2)
                        else:
                            # Try innerHTML extraction
                            card_html = card.get_attribute('innerHTML')
                            if card_html:
                                html_match = re.search(r'(\d+\.\d+)\s*\((\d+)\s*review', card_html)
                                if html_match:
                                    review_rating = html_match.group(1)
                                    review_count = html_match.group(2)
                except Exception:
                    pass
                
                # Extract task counts
                furniture_tasks = "Not found"
                overall_tasks = "Not found"
                try:
                    card_text = card.text
                    import re
                    
                    # Look for "137 Furniture Assembly tasks"
                    furniture_match = re.search(r'(\d+)\s+Furniture Assembly tasks', card_text)
                    if furniture_match:
                        furniture_tasks = furniture_match.group(1)
                    
                    # Look for overall tasks with multiple patterns
                    overall_patterns = [
                        r'(\d+)\s+Assembly tasks overall',
                        r'(\d+)\s+tasks overall',
                        r'(\d+)\s+overall tasks',
                        r'(\d+)\s+total tasks',
                        r'(\d+)\s+tasks completed'
                    ]
                    
                    for pattern in overall_patterns:
                        overall_match = re.search(pattern, card_text, re.IGNORECASE)
                        if overall_match:
                            overall_tasks = overall_match.group(1)
                            break
                    
                    # If not found in text, try innerHTML
                    if furniture_tasks == "Not found" or overall_tasks == "Not found":
                        card_html = card.get_attribute('innerHTML')
                        if card_html:
                            if furniture_tasks == "Not found":
                                html_furniture_match = re.search(r'(\d+)\s+Furniture Assembly tasks', card_html)
                                if html_furniture_match:
                                    furniture_tasks = html_furniture_match.group(1)
                            
                            if overall_tasks == "Not found":
                                # Try multiple patterns in HTML as well
                                for pattern in overall_patterns:
                                    html_overall_match = re.search(pattern, card_html, re.IGNORECASE)
                                    if html_overall_match:
                                        overall_tasks = html_overall_match.group(1)
                                        break
                                
                                # If still not found, set to None instead of unreliable fallback
                                if overall_tasks == "Not found":
                                    overall_tasks = "None"
                except Exception:
                    pass
                
                # Extract "2 Hour Minimum" flag
                two_hour_minimum = False
                try:
                    card_text = card.text
                    card_html = card.get_attribute('innerHTML') or ''
                    
                    # Look for "2 Hour Minimum" text in various formats
                    minimum_patterns = [
                        r'2\s*Hour\s*Minimum',
                        r'2\s*hr\s*minimum',
                        r'2\s*hour\s*min',
                        r'minimum\s*2\s*hour',
                        r'min\s*2\s*hr'
                    ]
                    
                    # Check in card text first
                    for pattern in minimum_patterns:
                        if re.search(pattern, card_text, re.IGNORECASE):
                            two_hour_minimum = True
                            break
                    
                    # If not found in text, check in HTML
                    if not two_hour_minimum:
                        for pattern in minimum_patterns:
                            if re.search(pattern, card_html, re.IGNORECASE):
                                two_hour_minimum = True
                                break
                    
                    # Also look for specific elements that might contain the flag
                    if not two_hour_minimum:
                        minimum_selectors = [
                            ".//*[contains(text(), '2 Hour Minimum')]",
                            ".//*[contains(text(), '2 hour minimum')]",
                            ".//*[contains(text(), '2hr minimum')]",
                            ".//*[contains(text(), 'Minimum 2 hour')]",
                            ".//*[contains(text(), 'minimum 2 hr')]"
                        ]
                        
                        for selector in minimum_selectors:
                            try:
                                elements = card.find_elements(By.XPATH, selector)
                                if elements and any(elem.is_displayed() for elem in elements):
                                    two_hour_minimum = True
                                    break
                            except Exception:
                                continue
                                
                except Exception as e:
                    logger.debug(f"Error extracting 2 Hour Minimum flag: {e}")
                    pass
                
                # Extract "Elite" status flag
                elite_status = False
                try:
                    card_text = card.text
                    card_html = card.get_attribute('innerHTML') or ''
                    
                    # Look for "Elite" text in various formats
                    elite_patterns = [
                        r'\bElite\b',
                        r'\bELITE\b',
                        r'\belite\b'
                    ]
                    
                    # Check in card text first
                    for pattern in elite_patterns:
                        if re.search(pattern, card_text):
                            elite_status = True
                            break
                    
                    # If not found in text, check in HTML
                    if not elite_status:
                        for pattern in elite_patterns:
                            if re.search(pattern, card_html):
                                elite_status = True
                                break
                    
                    # Also look for specific elements that might contain the Elite status
                    if not elite_status:
                        elite_selectors = [
                            ".//*[contains(text(), 'Elite')]",
                            ".//*[contains(text(), 'ELITE')]",
                            ".//*[contains(text(), 'elite')]",
                            ".//*[contains(@class, 'elite')]",
                            ".//*[contains(@class, 'Elite')]"
                        ]
                        
                        for selector in elite_selectors:
                            try:
                                elements = card.find_elements(By.XPATH, selector)
                                if elements and any(elem.is_displayed() for elem in elements):
                                    elite_status = True
                                    break
                            except Exception:
                                continue
                                
                except Exception as e:
                    logger.debug(f"Error extracting Elite status: {e}")
                    pass
                
                # Clean hourly rate by removing '/hr' suffix
                clean_rate = rate
                if rate != "Rate not found" and rate.endswith('/hr'):
                    clean_rate = rate.replace('/hr', '')
                
                # Create tasker entry
                tasker = {
                    'name': name,
                    'hourly_rate': clean_rate,
                    'review_rating': review_rating,
                    'review_count': review_count,
                    'furniture_tasks': furniture_tasks,
                    'overall_tasks': overall_tasks,
                    'two_hour_minimum': two_hour_minimum,
                    'elite_status': elite_status
                }
                
                taskers.append(tasker)
                logger.info(f"Card {i+1}: {name} - {rate} - Rating: {review_rating} ({review_count} reviews) - Tasks: {furniture_tasks} furniture, {overall_tasks} overall - 2Hr Min: {two_hour_minimum} - Elite: {elite_status}")
                
                # Debug: log card structure if rate not found
                if rate == "Rate not found":
                    logger.debug(f"Card {i+1} text sample: {card.text[:200]}...")
                    # Try to find any text with $ symbol
                    try:
                        dollar_elements = card.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                        if dollar_elements:
                            logger.debug(f"Found {len(dollar_elements)} elements with $ in card {i+1}")
                            for elem in dollar_elements[:3]:  # Show first 3
                                logger.debug(f"  $ element: '{elem.text.strip()}'")
                    except Exception:
                        pass
                
            except Exception as e:
                logger.warning(f"Error processing tasker card {i+1}: {e}")
                continue
        
        if not taskers:
            logger.error("No taskers found with card-based extraction")
            # Save page source for debugging
            try:
                with open('/tmp/taskrabbit_page_debug.html', 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.info("Saved page source to /tmp/taskrabbit_page_debug.html for debugging")
            except Exception as e:
                logger.warning(f"Could not save page source: {e}")
            return []
        
        # Log final results
        logger.info(f"Successfully extracted {len(taskers)} taskers from current page")
        
        return taskers
    
    def debug_visible_names(self):
        """Debug method to capture all visible text that looks like names on the page."""
        logger.info("=== DEBUGGING VISIBLE NAMES ON PAGE ===")
        try:
            # Get all text elements that might contain names
            text_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
            potential_names = []
            
            for element in text_elements:
                try:
                    if element.is_displayed():
                        text = element.text.strip()
                        # Look for text that might be names (contains letters, short, has spaces or dots)
                        if (text and len(text) < 50 and 
                            any(c.isalpha() for c in text) and
                            (' ' in text or '.' in text) and
                            not any(keyword in text.lower() for keyword in ['http', 'www', 'email', 'phone', 'address'])):
                            potential_names.append(text)
                except Exception:
                    continue
            
            # Remove duplicates and sort
            unique_names = list(set(potential_names))
            unique_names.sort()
            
            logger.info(f"Found {len(unique_names)} potential names on page:")
            for i, name in enumerate(unique_names[:50]):  # Show first 50
                logger.info(f"  {i+1}. '{name}'")
                
            return unique_names
            
        except Exception as e:
            logger.error(f"Error in debug_visible_names: {e}")
            return []
    
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
                        # Apply max_pages limit if specified
                        if self.max_pages and len(all_pages) > self.max_pages:
                            all_pages = all_pages[:self.max_pages]
                            logger.info(f"Limited to first {self.max_pages} pages: {all_pages}")
                        else:
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
                # Apply max_pages limit if specified
                if self.max_pages and len(page_numbers) > self.max_pages:
                    page_numbers = page_numbers[:self.max_pages]
                    logger.info(f"Limited to first {self.max_pages} pages: {page_numbers}")
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
                # Apply max_pages limit if specified
                if self.max_pages and len(page_numbers) > self.max_pages:
                    page_numbers = page_numbers[:self.max_pages]
                    logger.info(f"Limited to first {self.max_pages} pages: {page_numbers}")
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
                            time.sleep(SLEEP_CONTINUE_BUTTON)
                            
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
    
    def save_to_csv(self, taskers: List[Dict[str, str]]):
        """Save extracted tasker data to CSV file."""
        logger.info(f"Saving {len(taskers)} taskers to CSV...")
        
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'hourly_rate', 'review_rating', 'review_count', 'furniture_tasks', 'overall_tasks', 'two_hour_minimum', 'elite_status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for tasker in taskers:
                writer.writerow(tasker)
        
        logger.info(f"Successfully saved {len(taskers)} taskers to {self.csv_filename}")
    
    def run(self):
        """Main execution method."""
        try:
            logger.info(f"Starting TaskRabbit parser for {self.category_name}...")
            
            # Ensure Taskers directory exists
            os.makedirs('Taskers', exist_ok=True)
            
            self.setup_driver()
            
            # Navigate through the booking flow
            self.navigate_to_category_page()
            self.enter_address_details()
            self.select_category_options()
            
            # Extract and save data from all pages
            taskers = self.extract_tasker_data()
            
            if taskers:
                self.save_to_csv(taskers)
                logger.info(f"Successfully extracted {len(taskers)} {self.category_name} taskers to {self.csv_filename}")
            else:
                logger.error("No taskers found!")
                
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")

def run_parser_for_category(category: str, headless: bool = False, max_pages: int = None):
    """Run the parser for a specific category."""
    parser = TaskRabbitParser(category=category, headless=headless, max_pages=max_pages)
    parser.run()
    return parser.csv_filename

def run_all_categories(headless: bool = False, max_pages: int = None):
    """Run the parser for all configured categories."""
    results = {}
    for category in CATEGORIES.keys():
        logger.info(f"\n{'='*50}")
        logger.info(f"Starting extraction for {CATEGORIES[category]['name']}")
        logger.info(f"{'='*50}")
        try:
            csv_file = run_parser_for_category(category, headless, max_pages)
            results[category] = csv_file
            logger.info(f"Completed {CATEGORIES[category]['name']} - saved to {csv_file}")
        except Exception as e:
            logger.error(f"Failed to extract {CATEGORIES[category]['name']}: {e}")
            results[category] = None
    
    return results

def interactive_category_selection():
    """Interactive category selection when no command line arguments provided."""
    print("TaskRabbit Multi-Category Parser")
    print("\nAvailable categories:")
    
    # Display categories with numbers
    category_list = list(CATEGORIES.keys())
    for i, category_key in enumerate(category_list, 1):
        category_name = CATEGORIES[category_key]['name']
        print(f"{i}. {category_name} ({category_key})")
    
    print(f"{len(category_list) + 1}. All categories")
    
    while True:
        try:
            choice = input(f"\nSelect category (1-{len(category_list) + 1}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            
            choice_num = int(choice)
            
            if 1 <= choice_num <= len(category_list):
                selected_category = category_list[choice_num - 1]
                print(f"Selected: {CATEGORIES[selected_category]['name']}")
                return selected_category
            elif choice_num == len(category_list) + 1:
                print("Selected: All categories")
                return 'all'
            else:
                print(f"Invalid choice. Please enter 1-{len(category_list) + 1} or 'q'.")
                
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None

if __name__ == "__main__":
    import sys
    
    # Check if category is specified as command line argument
    if len(sys.argv) > 1:
        specified_category = sys.argv[1].lower()
        if specified_category == 'all':
            # Run all categories
            results = run_all_categories(headless=False, max_pages=MAX_PAGES_FOR_TESTING)
            print("\nExtraction Results:")
            for cat, file in results.items():
                status = "✓" if file else "✗"
                print(f"{status} {CATEGORIES[cat]['name']}: {file or 'Failed'}")
        elif specified_category in CATEGORIES:
            category = specified_category
            parser = TaskRabbitParser(category=category, headless=False, max_pages=MAX_PAGES_FOR_TESTING)
            parser.run()
        else:
            print(f"Unknown category: {specified_category}")
            print(f"Available categories: {', '.join(CATEGORIES.keys())}, all")
            sys.exit(1)
    else:
        # Interactive category selection
        selected_category = interactive_category_selection()
        
        if selected_category is None:
            sys.exit(0)
        elif selected_category == 'all':
            # Run all categories
            results = run_all_categories(headless=False, max_pages=MAX_PAGES_FOR_TESTING)
            print("\nExtraction Results:")
            for cat, file in results.items():
                status = "✓" if file else "✗"
                print(f"{status} {CATEGORIES[cat]['name']}: {file or 'Failed'}")
        else:
            # Run selected category
            parser = TaskRabbitParser(category=selected_category, headless=False, max_pages=MAX_PAGES_FOR_TESTING)
            parser.run()
