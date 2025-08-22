#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from taskrabbit_parser import TaskRabbitParser
import logging
from selenium.webdriver.common.by import By

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_name_extraction():
    """Debug name extraction on the recommendations page."""
    parser = TaskRabbitParser()
    
    try:
        # Initialize browser
        parser.setup_driver()
        
        # Navigate to furniture assembly and complete booking flow
        parser.navigate_to_furniture_assembly()
        parser.enter_address_details()
        parser.select_furniture_options()
        # Task size and description are handled within select_furniture_options()
        
        # Wait for page to load
        import time
        time.sleep(5)
        
        # Find tasker cards
        tasker_cards = parser.driver.find_elements(By.XPATH, "//div[@data-testid='tasker-card-mobile']")
        logger.info(f"Found {len(tasker_cards)} tasker cards")
        
        if tasker_cards:
            # Debug first card
            card = tasker_cards[0]
            logger.info("=== DEBUGGING FIRST CARD ===")
            
            # Try all name selectors
            name_selectors = [
                ".//span[contains(@class, 'mui-5xjf89')]",
                ".//span[contains(@class, 'MuiTypography-subtitle4')]", 
                ".//button[contains(@class, 'mui-1pbxn54')]",
                ".//button[contains(@class, 'TRTextButtonPrimary-Root')]"
            ]
            
            for i, selector in enumerate(name_selectors):
                try:
                    elements = card.find_elements(By.XPATH, selector)
                    logger.info(f"Selector {i+1} ({selector}): Found {len(elements)} elements")
                    for j, elem in enumerate(elements):
                        try:
                            text = elem.text.strip()
                            logger.info(f"  Element {j+1}: '{text}' (displayed: {elem.is_displayed()})")
                            if text:
                                # Test validation
                                is_potential = parser.is_potential_name(text)
                                is_valid = parser.is_valid_person_name(text)
                                logger.info(f"    is_potential_name: {is_potential}, is_valid_person_name: {is_valid}")
                        except Exception as e:
                            logger.info(f"  Element {j+1}: Error getting text - {e}")
                except Exception as e:
                    logger.error(f"Error with selector {i+1}: {e}")
            
            # Show card text for manual inspection
            logger.info("=== CARD TEXT ===")
            logger.info(card.text[:500] + "..." if len(card.text) > 500 else card.text)
            
    except Exception as e:
        logger.error(f"Error during debug: {e}")
    finally:
        if parser.driver:
            parser.driver.quit()

if __name__ == "__main__":
    debug_name_extraction()
