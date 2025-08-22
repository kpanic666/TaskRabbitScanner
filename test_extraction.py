#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from taskrabbit_parser import TaskRabbitParser
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_extraction():
    """Test the extraction functionality with proper waits."""
    parser = TaskRabbitParser()
    
    try:
        # Initialize browser
        parser.setup_driver()
        
        # Navigate to furniture assembly and complete booking flow
        parser.navigate_to_furniture_assembly()
        parser.enter_address_details()
        parser.select_furniture_options()
        
        # Wait for recommendations page to fully load
        logger.info("Waiting for tasker cards to load...")
        wait = WebDriverWait(parser.driver, 20)
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-testid='tasker-card-mobile']")))
        
        # Additional wait for content to render
        time.sleep(10)
        
        # Save page source for analysis
        with open('/tmp/taskrabbit_full_page.html', 'w', encoding='utf-8') as f:
            f.write(parser.driver.page_source)
        logger.info("Saved full page source to /tmp/taskrabbit_full_page.html")
        
        # Find tasker cards
        tasker_card_selector = "//div[@data-testid='tasker-card-mobile']"
        tasker_cards = parser.driver.find_elements(By.XPATH, tasker_card_selector)
        
        if not tasker_cards:
            # Try fallback selectors
            fallback_selectors = [
                "//div[contains(@class, 'mui-1m4n54b')]",
                "//div[contains(@data-testid, 'tasker')]",
                "//div[contains(@class, 'tasker')]"
            ]
            
            for selector in fallback_selectors:
                tasker_cards = parser.driver.find_elements(By.XPATH, selector)
                if tasker_cards:
                    logger.info(f"Found {len(tasker_cards)} tasker cards with fallback selector: {selector}")
                    break
        else:
            logger.info(f"Found {len(tasker_cards)} tasker cards with primary selector")
        
        if not tasker_cards:
            logger.error("No tasker cards found")
            return
        
        # Test extraction on first 5 cards
        test_cards = tasker_cards[:5]
        logger.info(f"Testing extraction on {len(test_cards)} cards")
        
        results = []
        
        for i, card in enumerate(test_cards):
            try:
                logger.info(f"\n--- Testing Card {i+1} ---")
                
                # Extract name
                name = "Name not found"
                name_selectors = [
                    ".//button[contains(@class, 'mui-1pbxn54')]",
                    ".//button[contains(@class, 'TRTextButtonPrimary-Root')]",
                    ".//button[contains(@class, 'MuiButton-textPrimary')]"
                ]
                
                for selector in name_selectors:
                    try:
                        name_element = card.find_element(By.XPATH, selector)
                        if name_element and name_element.is_displayed():
                            name_text = name_element.text.strip()
                            if name_text and '.' in name_text and len(name_text) < 50:
                                name = name_text
                                logger.info(f"Found name with selector '{selector}': {name}")
                                break
                    except Exception as e:
                        logger.debug(f"Name selector '{selector}' failed: {e}")
                        continue
                
                # Extract rate
                rate = "Rate not found"
                rate_selectors = [
                    ".//div[contains(@class, 'mui-loubxv')]",
                    ".//div[contains(text(), '$') and contains(text(), '/hr')]",
                    ".//span[contains(text(), '$') and contains(text(), '/hr')]"
                ]
                
                for selector in rate_selectors:
                    try:
                        rate_element = card.find_element(By.XPATH, selector)
                        if rate_element and rate_element.is_displayed():
                            rate_text = rate_element.text.strip()
                            if '$' in rate_text and '/hr' in rate_text:
                                rate = rate_text
                                logger.info(f"Found rate with selector '{selector}': {rate}")
                                break
                    except Exception as e:
                        logger.debug(f"Rate selector '{selector}' failed: {e}")
                        continue
                
                # Log all text in the card for debugging
                card_text = card.text
                logger.info(f"Card text preview: {card_text[:200]}...")
                
                results.append({
                    'name': name,
                    'rate': rate
                })
                
                logger.info(f"Result: {name} - {rate}")
                
            except Exception as e:
                logger.error(f"Error processing card {i+1}: {e}")
                continue
        
        # Summary
        logger.info(f"\n=== EXTRACTION TEST RESULTS ===")
        for i, result in enumerate(results):
            logger.info(f"Card {i+1}: {result['name']} - {result['rate']}")
        
        # Save page source for analysis
        with open('/tmp/test_extraction_debug.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("Saved page source to /tmp/test_extraction_debug.html")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_extraction()
