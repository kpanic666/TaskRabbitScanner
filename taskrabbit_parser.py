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
MAX_PAGES_FOR_TESTING = None   # Set to None to scan all pages, or number to limit pages
DEFAULT_ADDRESS = "448 W 46th St, new york, 10036, NY"

# Address dictionary for location selection
ADDRESSES = {
    "Manhattan - Upper West Side": "163 W 73rd St, New York, NY 10023",
    "Manhattan - Upper East Side": "178 E 75th St, New York, NY 10021",
    "Manhattan - Soho": "387 W Broadway, New York, NY 10012",
    "Brooklyn - Downtown": "19 Monroe Pl, Brooklyn, NY 11201",
    "Queens": "137-08 70th Ave, Flushing, NY 11367"
}

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
SLEEP_CARD_LOADING = 7            # Waiting for tasker cards to load
SLEEP_CATEGORY_NAVIGATION = 2     # After navigating to category page

class TaskRabbitParser:
    def __init__(self, category: str = 'furniture_assembly', headless: bool = False, max_pages: int = None, address: str = DEFAULT_ADDRESS, address_name: str = None):
        """Initialize the TaskRabbit parser with Chrome WebDriver."""
        self.base_url = "https://www.taskrabbit.com"
        self.driver = None
        self.wait = None
        self.headless = headless
        self.max_pages = max_pages  # Limit number of pages to process (None = all pages)
        self.address = address
        self.address_name = address_name
        self.category_flow_completed = False
        
        # Category configuration
        if category not in CATEGORIES:
            raise ValueError(f"Category '{category}' not supported. Available categories: {list(CATEGORIES.keys())}")
        
        self.category = category
        self.category_config = CATEGORIES[category]
        self.category_name = self.category_config['name']
        
        # Extract address index (use address_name if provided, otherwise extract zip code)
        address_index = self._extract_address_index(address, address_name)
        
        # Generate CSV filename with category, timestamp, and address index
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        category_filename = self.category_name.replace(' ', '_').lower()
        self.csv_filename = f"Taskers/{category_filename}_{timestamp}_{address_index}.csv"
    
    def _extract_address_index(self, address: str, address_name: str = None) -> str:
        """Extract the address index from address_name if provided, otherwise extract zip code."""
        if address_name:
            # Create a short name from the address_name for the filename
            # Format: keep borough, use initials for second part
            if ' - ' in address_name:
                parts = address_name.split(' - ', 1)
                borough = parts[0].lower().replace(' ', '_')
                location = parts[1]
                # Extract initials from location words
                words = location.split()
                initials = ''.join(word[0].lower() for word in words)
                short_name = f"{borough}_{initials}"
            else:
                # No separator, just use the name as-is
                short_name = address_name.lower().replace(' ', '_')
            return short_name
        else:
            # Fallback to zip code extraction
            import re
            # Look for a 5-digit zip code pattern
            zip_match = re.search(r'\b(\d{5})\b', address)
            if zip_match:
                return zip_match.group(1)
            # Fallback: if no zip code found, use a hash of the address
            return str(hash(address))[:8]
        
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
        time.sleep(SLEEP_CATEGORY_NAVIGATION)
        
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

            # General Mounting flow can require choosing "Other Mounting"
            # immediately after "Book now", before address appears.
            if self.category == 'general_mounting':
                logger.info("General Mounting: attempting immediate 'Other Mounting' selection after Book Now")
                self._select_other_mounting_option("Other Mounting")
                self.debug_page_elements("After selecting Other Mounting from category page")
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
            "//input[@data-testid='input-text-location-street-address']",
            "//input[@id='location']",
            "//input[@name='location']",
            "//input[@role='combobox']",
            "//input[@placeholder='Street address']",
            "//input[@name='address']",
            "//input[contains(@id, 'address')]",
            "//label[contains(text(), 'Street address')]/following::input[@type='text'][1]",
            "//label[contains(text(), 'Street address')]/following-sibling::input",
            "//input[@type='text'][1]",
            "//input[@type='text']",
            "//input[contains(@placeholder, 'address')]",
            "//input[contains(@class, 'address')]",
            "//input[contains(@placeholder, 'zip')]",
            "//textarea[contains(@placeholder, 'address')]"
        ]
        
        address_field = None
        for selector in address_selectors:
            try:
                if selector == "//input[@type='text'][1]":
                    # For TV mounting, get all text inputs and select the first one
                    elements = self.driver.find_elements(By.XPATH, "//input[@type='text']")
                    if elements:
                        address_field = elements[0]
                        logger.info("Found first text input field")
                        break
                else:
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
        address_field.send_keys(self.address)
        time.sleep(SLEEP_ADDRESS_INPUT)
        
        # Click Continue button (or "Set location" for TV mounting)
        continue_selectors = [
            "//button[contains(text(), 'Set location')]",
            "//button[contains(text(), 'Continue')]",
            "//a[contains(text(), 'Continue')]",
            "//button[contains(text(), 'Next')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//button[contains(@class, 'submit')]",
            "//button[contains(@class, 'continue')]"
        ]
        
        continue_btn = None
        for selector in continue_selectors:
            try:
                # Try with a shorter timeout for TV mounting
                continue_btn = WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.XPATH, selector)))
                logger.info(f"Found Continue button with selector: {selector}")
                break
            except TimeoutException:
                continue
        
        if not continue_btn:
            logger.error("Could not find Continue button")
            self.debug_page_elements("Continue button not found")
            # Try to find any button as a last resort
            try:
                all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                logger.info(f"Found {len(all_buttons)} buttons on page")
                for i, btn in enumerate(all_buttons[:5]):
                    logger.info(f"  Button {i}: text='{btn.text}', type='{btn.get_attribute('type')}'")
            except Exception as e:
                logger.info(f"Could not list buttons: {e}")
            raise Exception("Continue button not found")
        
        continue_btn.click()
        time.sleep(SLEEP_ADDRESS_CONTINUE)
        self.debug_page_elements("After clicking Continue")

        # For General Mounting, TaskRabbit may immediately ask for
        # "Items to install" right after "Set location".
        if self.category == 'general_mounting':
            self._fill_general_mounting_items_to_install()

    def _fill_general_mounting_items_to_install(self):
        """Fill the 'Items to install' input when it appears in general mounting flow."""
        logger.info("General Mounting: checking for 'Items to install' field...")
        short_wait = WebDriverWait(self.driver, 4)

        # Pull text from configured task_details value for this category.
        details_text = ''
        for option in self.category_config.get('options', []):
            if option.get('type') == 'task_details':
                details_text = option.get('value', '')
                break

        if not details_text:
            logger.info("General Mounting: no task_details configured, skipping items input")
            return

        selectors = [
            "//input[@name='Items to install']",
            "//input[contains(@aria-labelledby, 'scoping-question') and @type='text']",
            "//label[contains(., 'Items to install')]/following::input[@type='text'][1]",
            "//input[@data-testid='input-text']",
        ]

        for selector in selectors:
            try:
                field = short_wait.until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )

                if not field.is_displayed():
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
                time.sleep(0.4)
                field.clear()
                field.send_keys(details_text)
                logger.info(f"General Mounting: entered items text: '{details_text}'")
                time.sleep(SLEEP_TASK_DETAILS)

                # Required next step for General Mounting:
                # scroll down and select "Hours of help requested" = 2.
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(SLEEP_SCROLL_WAIT)

                hour_selectors = [
                    "//input[@type='radio' and @name='Hours of help requested' and @value='2']",
                    "//label[.//input[@name='Hours of help requested' and @value='2']]",
                    "//input[@name='Hours of help requested' and @value='2']/ancestor::label[1]",
                ]

                hour_selected = False
                for hour_selector in hour_selectors:
                    try:
                        hour_element = short_wait.until(
                            EC.element_to_be_clickable((By.XPATH, hour_selector))
                        )
                        try:
                            hour_element.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", hour_element)
                        logger.info("General Mounting: selected 'Hours of help requested' value 2")
                        self.driver.execute_script("window.scrollBy(0, 500);")
                        time.sleep(SLEEP_SCROLL_WAIT)

                        ladder_selectors = [
                            "//input[@type='radio' and @name='Ladder needed & max reach' and @value='No ladder needed']",
                            "//label[.//input[@name='Ladder needed & max reach' and @value='No ladder needed']]",
                            "//input[@name='Ladder needed & max reach' and @value='No ladder needed']/ancestor::label[1]",
                        ]

                        ladder_selected = False
                        for ladder_selector in ladder_selectors:
                            try:
                                ladder_element = short_wait.until(
                                    EC.element_to_be_clickable((By.XPATH, ladder_selector))
                                )
                                try:
                                    ladder_element.click()
                                except Exception:
                                    self.driver.execute_script("arguments[0].click();", ladder_element)
                                logger.info("General Mounting: selected 'No ladder needed'")
                                ladder_selected = True
                                break
                            except TimeoutException:
                                continue
                            except Exception as e:
                                logger.warning(f"General Mounting: failed selecting ladder option with selector {ladder_selector}: {e}")
                                continue

                        if not ladder_selected:
                            logger.warning("General Mounting: could not select 'No ladder needed'")

                        # Finalize this question set like other categories:
                        # scroll to bottom and confirm.
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(SLEEP_SCROLL_WAIT)
                        self.click_final_button("Submit answer")
                        self.category_flow_completed = True

                        hour_selected = True
                        break
                    except TimeoutException:
                        continue
                    except Exception as e:
                        logger.warning(f"General Mounting: failed selecting hours with selector {hour_selector}: {e}")
                        continue

                if not hour_selected:
                    logger.warning("General Mounting: could not select 'Hours of help requested' value 2")
                return
            except TimeoutException:
                continue
            except Exception as e:
                logger.warning(f"General Mounting: failed filling selector {selector}: {e}")
                continue

        logger.info("General Mounting: 'Items to install' field not found right after location step")
        
    def select_category_options(self):
        """Select category-specific options through the booking flow."""
        if self.category == 'general_mounting' and self.category_flow_completed:
            logger.info("General Mounting flow already completed; skipping additional option steps")
            return

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
            elif option_type == 'tv_count':
                self._select_tv_count_option(option_value)
            elif option_type == 'someone_around':
                self._select_someone_around_option(option_value)
            elif option_type == 'tv_type':
                self._select_tv_type_option(option_value)
            elif option_type == 'fixed_profile':
                self._select_fixed_profile_option(option_value)
            elif option_type == 'other_mounting':
                self._select_other_mounting_option(option_value)
            elif option_type == 'hours_needed':
                self._select_hours_needed_option(option_value)
            elif option_type == 'ladder_needed':
                self._select_ladder_needed_option(option_value)
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
                # If task_details is empty, skip entering text and just click final button
                if not task_details:
                    logger.info("Task details value is empty, skipping text entry")
                    # Scroll down to make sure button is visible
                    logger.info("Scrolling down to reveal button...")
                    self.driver.execute_script("window.scrollBy(0, 300);")
                    time.sleep(SLEEP_SCROLL_WAIT)
                    
                    if final_button:
                        self.click_final_button(final_button)
                    else:
                        self.click_continue_button()
                else:
                    # Clear the field and enter task details
                    task_details_field.clear()
                    task_details_field.send_keys(task_details)
                    time.sleep(SLEEP_TASK_DETAILS)
                    # Entered task details
                    
                    # Scroll down to make sure button is visible
                    logger.info("Scrolling down to reveal button...")
                    # Use different scroll distance for general_mounting category
                    scroll_distance = 500 if self.category_name == 'General Mounting' else 300
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_distance});")
                    time.sleep(SLEEP_SCROLL_WAIT)
                    
                    if final_button:
                        self.click_final_button(final_button)
                    else:
                        self.click_continue_button()
            except Exception as e:
                logger.warning(f"Failed to enter task details: {e}")
                # Try JavaScript approach as fallback
                try:
                    if task_details:
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

    def _select_tv_count_option(self, option_value: str):
        """Select TV count option (first radio button for TV mounting category)."""
        logger.info("Selecting TV count option (first radio button)...")
        
        try:
            time.sleep(1)
            
            # Look for radio buttons for TV count
            selectors = [
                "//input[@type='radio']",
                "//label[contains(@class, 'radio')]",
                "//div[@role='radio']"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) >= 1:
                        # Select the first radio button
                        element = elements[0]
                        
                        # If it's an input, click it directly
                        if element.tag_name == 'input':
                            element.click()
                        else:
                            # Try to find the associated input or click the element
                            try:
                                input_element = element.find_element(By.XPATH, ".//input[@type='radio']")
                                input_element.click()
                            except Exception:
                                element.click()
                        
                        logger.info("Selected first TV count option")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find TV count radio buttons, trying to continue anyway")
            
            # Scroll down a little
            self.driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting TV count option: {e}")
            self.click_continue_button()

    def _select_someone_around_option(self, option_value: str):
        """Select someone around option (third radio button for TV mounting category)."""
        logger.info("Selecting someone around option (Not needed. No TVs above 60\")...")
        
        try:
            time.sleep(1)
            
            # Try clicking the label element directly - more reliable than input
            selectors = [
                "//label[contains(@class, 'TRRadioButton-Root') and contains(., 'Not needed. No TVs above 60')]",
                "//label[p[contains(text(), 'Not needed. No TVs above 60')]]",
                "//input[@name='Help lifting the TV' and contains(@value, 'Not needed')]/parent::span/parent::span/parent::label",
                "//input[@name='Help lifting the TV' and contains(@value, 'Not needed')]"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Select the element
                        element = elements[0]
                        
                        # Scroll element into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # Click the element
                        element.click()
                        
                        logger.info("Selected 'Not needed. No TVs above 60\"' option")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find specific radio button, trying third radio button as fallback")
                # Fallback to third radio button by name
                try:
                    elements = self.driver.find_elements(By.XPATH, "//input[@name='Help lifting the TV']")
                    if elements and len(elements) >= 3:
                        element = elements[2]
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        element.click()
                        logger.info("Selected third radio button by name as fallback")
                        option_selected = True
                except Exception as e:
                    logger.warning(f"Fallback by name also failed: {e}")
            
            # Scroll down a little
            self.driver.execute_script("window.scrollBy(0, 100);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting someone around option: {e}")
            self.click_continue_button()

    def _select_tv_type_option(self, option_value: str):
        """Select TV type option (Drywall, plaster, or wood checkbox for TV mounting category)."""
        logger.info("Selecting TV type option (Drywall, plaster, or wood)...")
        
        try:
            time.sleep(1)
            
            # Look for specific checkbox for TV type
            selectors = [
                "//input[@type='checkbox' and @value='Drywall, plaster, or wood']",
                "//input[@name='Wall type' and @value='Drywall, plaster, or wood']",
                "//label[p[contains(text(), 'Drywall, plaster, or wood')]]",
                "//label[contains(@class, 'TRCheckbox-label') and contains(., 'Drywall, plaster, or wood')]"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Select the checkbox
                        element = elements[0]
                        
                        # Scroll element into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # If it's an input, click it directly
                        if element.tag_name == 'input':
                            element.click()
                        else:
                            # Try to find the associated input or click the element
                            try:
                                input_element = element.find_element(By.XPATH, ".//input[@type='checkbox']")
                                input_element.click()
                            except Exception:
                                element.click()
                        
                        logger.info("Selected 'Drywall, plaster, or wood' checkbox")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find specific TV type checkbox, trying first checkbox as fallback")
                # Fallback to first checkbox
                try:
                    elements = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                    if elements:
                        elements[0].click()
                        logger.info("Selected first checkbox as fallback")
                        option_selected = True
                except Exception as e:
                    logger.warning(f"Fallback also failed: {e}")
            
            # Scroll all the way to the bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting TV type option: {e}")

    def _select_fixed_profile_option(self, option_value: str):
        """Select fixed profile option (Fixed / low profile checkbox for TV mounting category)."""
        logger.info("Selecting fixed profile option (Fixed / low profile)...")
        
        try:
            time.sleep(1)
            
            # Look for specific checkbox for fixed profile
            selectors = [
                "//input[@type='checkbox' and @value='Fixed / low profile']",
                "//input[@name='Mount type' and @value='Fixed / low profile']",
                "//label[p[contains(text(), 'Fixed / low profile')]]",
                "//label[contains(@class, 'TRCheckbox-label') and contains(., 'Fixed / low profile')]"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Select the checkbox
                        element = elements[0]
                        
                        # Scroll element into view first
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                        time.sleep(0.5)
                        
                        # If it's an input, click it directly
                        if element.tag_name == 'input':
                            element.click()
                        else:
                            # Try to find the associated input or click the element
                            try:
                                input_element = element.find_element(By.XPATH, ".//input[@type='checkbox']")
                                input_element.click()
                            except Exception:
                                element.click()
                        
                        logger.info("Selected 'Fixed / low profile' checkbox")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find specific fixed profile checkbox, trying first checkbox as fallback")
                # Fallback to first checkbox
                try:
                    elements = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                    if elements:
                        elements[0].click()
                        logger.info("Selected first checkbox as fallback")
                        option_selected = True
                except Exception as e:
                    logger.warning(f"Fallback also failed: {e}")
            
            # Scroll down a little
            self.driver.execute_script("window.scrollBy(0, 100);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting fixed profile option: {e}")

    def _select_other_mounting_option(self, option_value: str):
        """Select other mounting option (click 'Other Mounting' button for general mounting category)."""
        logger.info("Selecting other mounting option (Other Mounting button)...")
        
        try:
            # Clear overlays first to match Book Now interaction reliability.
            self.remove_all_overlays_aggressively()
            short_wait = WebDriverWait(self.driver, 5)
            time.sleep(1)
            
            # Look for the "Other Mounting" button
            selectors = [
                "//button[contains(@class, 'TRButtonChoice-Root') and contains(text(), 'Other Mounting')]",
                "//button[contains(@class, 'TRButtonChoice-Root') and contains(text(), 'Other mounting')]",
                "//button[contains(@class, 'TRButton-Root') and contains(text(), 'Other Mounting')]",
                "//button[contains(@class, 'TRButton-Root') and contains(text(), 'Other mounting')]",
                "//button[contains(text(), 'Other Mounting')]",
                "//button[contains(text(), 'Other mounting')]",
                "//a[contains(text(), 'Other Mounting')]",
                "//a[contains(text(), 'Other mounting')]",
                "//div[contains(text(), 'Other Mounting')]",
                "//div[contains(text(), 'Other mounting')]",
                "//span[contains(text(), 'Other Mounting')]"
            ]
            
            button_clicked = False
            for selector in selectors:
                try:
                    # Wait for element to be present and clickable
                    element = short_wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    
                    # Scroll element into view first
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.5)
                    
                    # Try regular click first
                    try:
                        element.click()
                        logger.info("Clicked 'Other Mounting' button with regular click")
                        button_clicked = True
                        break
                    except Exception as e:
                        logger.warning(f"Regular click failed: {e}, trying JavaScript click")
                        # Try JavaScript click as fallback
                        try:
                            self.driver.execute_script("arguments[0].click();", element)
                            logger.info("Clicked 'Other Mounting' button with JavaScript click")
                            button_clicked = True
                            break
                        except Exception as e2:
                            logger.warning(f"JavaScript click also failed: {e2}")
                            continue
                except TimeoutException:
                    logger.warning(f"Timeout waiting for element with selector: {selector}")
                    continue
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue
            
            if not button_clicked:
                logger.warning("Could not find or click 'Other Mounting' button")
                # Debug: log all buttons on page
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    logger.info(f"Found {len(all_buttons)} buttons on page")
                    for i, btn in enumerate(all_buttons[:10]):
                        logger.info(f"  Button {i+1}: {btn.text}")
                except Exception as e:
                    logger.warning(f"Could not debug buttons: {e}")
            
            # Wait for page to load
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error selecting other mounting option: {e}")

    def _select_hours_needed_option(self, option_value: str):
        """Select hours needed option (second radio button for general mounting category)."""
        logger.info("Selecting hours needed option (second radio button)...")
        
        try:
            time.sleep(1)
            
            # Look for radio buttons for hours needed
            selectors = [
                "//input[@type='radio']",
                "//label[contains(@class, 'radio')]",
                "//div[@role='radio']"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) >= 2:
                        # Select the second radio button
                        element = elements[1]
                        
                        # If it's an input, click it directly
                        if element.tag_name == 'input':
                            element.click()
                        else:
                            # Try to find the associated input or click the element
                            try:
                                input_element = element.find_element(By.XPATH, ".//input[@type='radio']")
                                input_element.click()
                            except Exception:
                                element.click()
                        
                        logger.info("Selected second hours needed option")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find hours needed radio buttons, trying to continue anyway")
            
            # Scroll down 500px
            self.driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting hours needed option: {e}")

    def _select_ladder_needed_option(self, option_value: str):
        """Select ladder needed option (first radio button for general mounting category)."""
        logger.info("Selecting ladder needed option (first radio button)...")
        
        try:
            time.sleep(1)
            
            # Look for radio buttons for ladder needed
            selectors = [
                "//input[@type='radio']",
                "//label[contains(@class, 'radio')]",
                "//div[@role='radio']"
            ]
            
            option_selected = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) >= 1:
                        # Select the first radio button
                        element = elements[0]
                        
                        # If it's an input, click it directly
                        if element.tag_name == 'input':
                            element.click()
                        else:
                            # Try to find the associated input or click the element
                            try:
                                input_element = element.find_element(By.XPATH, ".//input[@type='radio']")
                                input_element.click()
                            except Exception:
                                element.click()
                        
                        logger.info("Selected first ladder needed option")
                        option_selected = True
                        break
                except Exception:
                    continue
            
            if not option_selected:
                logger.warning("Could not find ladder needed radio buttons, trying to continue anyway")
            
            # Scroll all the way to the bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(SLEEP_SCROLL_WAIT)
            
        except Exception as e:
            logger.error(f"Error selecting ladder needed option: {e}")
               
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
    
    def _get_csv_fieldnames(self) -> List[str]:
        """Return CSV columns for the current category."""
        fieldnames = [
            'name', 'hourly_rate', 'review_rating', 'review_count',
            'furniture_tasks', 'overall_tasks',
        ]
        if self.category == 'general_mounting':
            fieldnames.extend(['general_mounting_tasks', 'overall_mounting_tasks'])
        elif self.category == 'tv_mounting':
            fieldnames.extend(['tv_mounting_tasks', 'overall_mounting_tasks'])
        fieldnames.extend(['two_hour_minimum', 'elite_status'])
        return fieldnames

    def save_to_csv(self, taskers: List[Dict[str, str]]):
        """Save extracted tasker data to CSV file."""
        logger.info(f"Saving {len(taskers)} taskers to CSV...")
        
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = self._get_csv_fieldnames()
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
