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
import os
from datetime import datetime
from typing import List, Dict
from taskrabbit.categories import CATEGORIES
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from taskrabbit.utils import (
    close_overlays_and_popups as utils_close_overlays_and_popups,
    remove_all_overlays_aggressively as utils_remove_all_overlays_aggressively,
    click_continue_button as utils_click_continue_button,
)
from taskrabbit import scraper as scraper
from taskrabbit.extraction import extract_all_visible_text as extraction_extract_all_visible_text

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration constants - modify these to adjust behavior
MAX_PAGES_FOR_TESTING = None     # Set to None to scan all pages, or number to limit pages

# Sleep duration constants (in seconds) - modify these to adjust timing
SLEEP_OVERLAY_REMOVAL = 0.5          # After removing overlays/popups
SLEEP_IFRAME_REMOVAL = 0.5         # After removing iframe overlays
SLEEP_CONTINUE_BUTTON = 2          # After clicking continue buttons
SLEEP_PAGE_LOAD = 3                # General page loading wait
SLEEP_SCROLL_WAIT = 1              # After scrolling elements into view
SLEEP_ADDRESS_INPUT = 1.5            # After entering address
SLEEP_ADDRESS_CONTINUE = 1.5         # After clicking continue from address
SLEEP_FURNITURE_OPTION = 1         # After selecting furniture options
SLEEP_SIZE_OPTION = 1              # After selecting size options
SLEEP_TASK_DETAILS = 1             # After entering task details
SLEEP_OPTIONS_COMPLETE = 3         # After completing all options
SLEEP_PAGE_NAVIGATION = 3         # After navigating to new page
SLEEP_CARD_LOADING = 5             # Waiting for tasker cards to load

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
        # Debug output disabled to reduce terminal verbosity
        pass
    
    def close_overlays_and_popups(self):
        """Close overlays/popups via shared utils while preserving timing."""
        sleeps = {
            'SLEEP_OVERLAY_REMOVAL': SLEEP_OVERLAY_REMOVAL,
        }
        utils_close_overlays_and_popups(self.driver, self.wait, logger, sleeps)
    
    def remove_all_overlays_aggressively(self):
        """Aggressively remove overlays via shared utils, then standard cleanup."""
        sleeps = {
            'SLEEP_IFRAME_REMOVAL': SLEEP_IFRAME_REMOVAL,
            'SLEEP_OVERLAY_REMOVAL': SLEEP_OVERLAY_REMOVAL,
        }
        utils_remove_all_overlays_aggressively(self.driver, self.wait, logger, sleeps)
    
    def click_continue_button(self):
        """Click continue/next buttons using shared utils."""
        sleeps = {
            'SLEEP_CONTINUE_BUTTON': SLEEP_CONTINUE_BUTTON,
        }
        return utils_click_continue_button(self.driver, self.wait, sleeps)
    
    def navigate_to_category_page(self):
        """Navigate directly to the category page using configured URL"""
        print(f"Navigating to {self.category_name} page...")
        
        # Go directly to the category page
        direct_url = self.category_config['url']
        self.driver.get(direct_url)
        time.sleep(3)
        
        # Loaded category page
        
        # Close any overlays that might appear even with direct navigation
        self.close_overlays_and_popups()
        
        self.debug_page_elements(f"{self.category_name} page (direct navigation)")
        
        # Try to find a direct booking link or navigate to category booking
        # Looking for booking options
        
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
                # Clicked Book Now button
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
            elif option_type == 'vehicle_requirements':
                self._select_vehicle_requirements_option(option_value)
            else:
                logger.warning(f"Unknown option type: {option_type}")
        
        time.sleep(SLEEP_OPTIONS_COMPLETE)
        self.debug_page_elements(f"After {self.category_name} options selection")
    
    def _select_furniture_type_option(self, option_value: str):
        """Select furniture type option (for furniture assembly category)."""
        
        # Looking for furniture option
        
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
        # Looking for size option
        
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
        # Looking for task details text box
        
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
                        # Found task details field
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
                # Entered task details
                
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
                    # Entered task details with JavaScript
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
        # Looking for final button
        
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
                # Found final button
                final_btn.click()
                time.sleep(SLEEP_CONTINUE_BUTTON)
                return True
            except TimeoutException:
                continue
        
        logger.warning(f"No '{button_text}' button found, trying default continue button")
        return self.click_continue_button()
    
    def _select_plumbing_type_option(self, option_value: str):
        """Select plumbing type option (for plumbing category)."""
        # Looking for plumbing option
        
        # For plumbing, the flow might be simpler and go directly to task details
        # This is a placeholder that can be expanded based on actual plumbing page structure
        # Using simplified plumbing flow
        
        # Continue to next step
        self.click_continue_button()

    def _select_vehicle_requirements_option(self, option_value: str):
        """Select vehicle requirements option (for Smart Home Installation category)."""
        logger.info("Selecting vehicle requirements option...")
        
        try:
            # Wait for the vehicle requirements section to load
            time.sleep(2)
            
            # Look for "Not needed for task" option
            selectors = [
                "//span[contains(text(), 'Not needed for task')]",
                "//label[contains(text(), 'Not needed for task')]",
                "//div[contains(text(), 'Not needed for task')]",
                "//button[contains(text(), 'Not needed for task')]"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        element = elements[0]
                        # Try to find the clickable parent (radio button or checkbox)
                        clickable_element = element
                        
                        # Check if we need to click a parent element (radio button/checkbox)
                        parent = element.find_element(By.XPATH, "./..")
                        if parent.tag_name in ['label', 'div'] and 'input' in parent.get_attribute('innerHTML'):
                            clickable_element = parent
                        
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", clickable_element)
                        time.sleep(1)
                        clickable_element.click()
                        logger.info("Selected 'Not needed for task' option")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find 'Not needed for task' option, trying to continue anyway")
            
            # Wait a moment for the selection to register
            time.sleep(1)
            
            # Continue to next step
            self.click_continue_button()
            
        except Exception as e:
            logger.error(f"Error selecting vehicle requirements option: {e}")
            # Try to continue anyway
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
        return scraper.extract_tasker_data(self)
    
    def extract_all_visible_text(self):
        """Extract all visible text that might be tasker names and rates."""
        return extraction_extract_all_visible_text(self)

    def extract_taskers_from_current_page(self) -> List[Dict[str, str]]:
        """Extract tasker names and hourly rates from the current page only."""
        return scraper.extract_taskers_from_current_page(self)
    
    def debug_visible_names(self):
        """Debug method to capture all visible text that looks like names on the page."""
        return scraper.debug_visible_names(self)
    
    def debug_page_structure(self):
        """Debug method to inspect page structure for pagination elements."""
        return scraper.debug_page_structure(self)

    def get_available_page_numbers(self) -> List[int]:
        """Get all available page numbers from the pagination controls."""
        return scraper.get_available_page_numbers(self)
    
    def navigate_to_page_number(self, page_num: int) -> bool:
        """Navigate to a specific page number by clicking the page button."""
        return scraper.navigate_to_page_number(self, page_num)
    
    def check_for_next_page(self) -> bool:
        """Check if there's a next page available for pagination."""
        return scraper.check_for_next_page(self)
    
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

if __name__ == "__main__":
    # Delegate to modular CLI for backward compatibility
    from taskrabbit.cli import main as cli_main
    raise SystemExit(cli_main(max_pages=MAX_PAGES_FOR_TESTING, headless=False))
