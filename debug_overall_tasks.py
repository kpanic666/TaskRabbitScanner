#!/usr/bin/env python3

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_overall_tasks():
    """Debug script to examine card text for overall tasks extraction"""
    
    # Set up Chrome options
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Comment out to see browser
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate to TaskRabbit furniture assembly page
        logger.info("Navigating to TaskRabbit furniture assembly page...")
        driver.get("https://www.taskrabbit.com/services/furniture-assembly")
        
        # Wait for page to load
        time.sleep(3)
        
        # Enter address
        logger.info("Entering address...")
        address_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='address'], input[placeholder*='Address'], input[data-testid*='address']"))
        )
        address_input.clear()
        address_input.send_keys("10001")
        
        # Click continue or submit
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Get quotes')]"))
        )
        continue_button.click()
        time.sleep(3)
        
        # Select furniture type
        logger.info("Selecting furniture type...")
        furniture_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Both IKEA and non-IKEA furniture')]"))
        )
        furniture_option.click()
        time.sleep(2)
        
        # Select size
        logger.info("Selecting size...")
        size_option = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Medium')]"))
        )
        size_option.click()
        time.sleep(2)
        
        # Enter task details
        logger.info("Entering task details...")
        details_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "textarea, input[type='text']"))
        )
        details_input.clear()
        details_input.send_keys("build stool")
        
        # Click continue to get to taskers
        continue_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'See Taskers') or contains(text(), 'Get quotes')]"))
        )
        continue_button.click()
        
        # Wait for tasker cards to load
        logger.info("Waiting for tasker cards to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid*='tasker'], .tasker-card, [class*='tasker'], [class*='card']"))
        )
        time.sleep(5)
        
        # Find tasker cards
        card_selectors = [
            "[data-testid*='tasker']",
            ".tasker-card",
            "[class*='tasker']",
            "[class*='card']"
        ]
        
        cards = []
        for selector in card_selectors:
            try:
                found_cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if found_cards:
                    cards = found_cards
                    logger.info(f"Found {len(cards)} cards using selector: {selector}")
                    break
            except Exception:
                continue
        
        if not cards:
            logger.error("No tasker cards found")
            return
        
        # Focus on cards that might have "Not found" overall tasks
        # Based on CSV, these are: Andrey R., Denys A., Diana S., Adam U., Yaro R., Viktor O.
        target_names = ["Andrey R.", "Denys A.", "Diana S.", "Adam U.", "Yaro R.", "Viktor O."]
        
        for i, card in enumerate(cards[:10]):  # Check first 10 cards
            try:
                # Get card text and HTML
                card_text = card.text
                card_html = card.get_attribute('innerHTML')
                
                # Extract name for identification
                name = "Unknown"
                name_patterns = [
                    r'([A-Z][a-z]+ [A-Z]\.)',
                    r'([A-Z][A-Z]+ [A-Z]\.)',
                    r'([a-z]+ [a-z]\.)'
                ]
                
                for pattern in name_patterns:
                    name_match = re.search(pattern, card_text)
                    if name_match:
                        name = name_match.group(1)
                        break
                
                logger.info(f"\n=== CARD {i+1}: {name} ===")
                
                # Look for all task-related text patterns
                logger.info("Card text:")
                logger.info(card_text)
                
                # Search for various task patterns
                task_patterns = [
                    r'(\d+)\s+Assembly tasks overall',
                    r'(\d+)\s+tasks overall',
                    r'(\d+)\s+overall tasks',
                    r'(\d+)\s+total tasks',
                    r'(\d+)\s+tasks completed',
                    r'(\d+)\s+tasks',
                ]
                
                logger.info("\nSearching for task patterns in text:")
                for pattern in task_patterns:
                    matches = re.findall(pattern, card_text, re.IGNORECASE)
                    if matches:
                        logger.info(f"  Pattern '{pattern}' found: {matches}")
                
                logger.info("\nSearching for task patterns in HTML:")
                for pattern in task_patterns:
                    matches = re.findall(pattern, card_html, re.IGNORECASE)
                    if matches:
                        logger.info(f"  Pattern '{pattern}' found: {matches}")
                
                # Look for all numbers followed by text containing "task"
                all_task_mentions = re.findall(r'(\d+)\s+[^0-9]*task[^0-9]*', card_text, re.IGNORECASE)
                if all_task_mentions:
                    logger.info(f"All task mentions: {all_task_mentions}")
                
                logger.info("-" * 50)
                
            except Exception as e:
                logger.error(f"Error processing card {i+1}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error in debug script: {e}")
    
    finally:
        driver.quit()
        logger.info("Browser closed")

if __name__ == "__main__":
    debug_overall_tasks()
