#!/usr/bin/env python3

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_card_structure():
    """Debug the actual structure of tasker cards to find correct selectors."""
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # Navigate to furniture assembly page
        logger.info("Navigating to furniture assembly page")
        driver.get("https://www.taskrabbit.com/services/handyman/assemble-furniture")
        time.sleep(3)
        
        # Enter address
        logger.info("Entering address")
        address_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Enter your address']")))
        address_input.clear()
        address_input.send_keys("New York, NY")
        time.sleep(2)
        
        # Select first suggestion if available
        try:
            suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'suggestion') or contains(@class, 'option')]")))
            suggestion.click()
        except:
            pass
        
        # Continue
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(3)
        
        # Select furniture type
        logger.info("Selecting furniture type")
        furniture_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Both IKEA and non-IKEA furniture')]")))
        furniture_option.click()
        time.sleep(2)
        
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(3)
        
        # Select size
        logger.info("Selecting size")
        size_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Medium')]")))
        size_option.click()
        time.sleep(2)
        
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(3)
        
        # Add task details
        logger.info("Adding task details")
        details_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//textarea[contains(@placeholder, 'details')]")))
        details_input.send_keys("build stool")
        time.sleep(2)
        
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(5)
        
        # Now debug the tasker cards
        logger.info("=== DEBUGGING TASKER CARDS ===")
        logger.info(f"Current URL: {driver.current_url}")
        
        # Find tasker cards
        card_selectors = [
            "//div[@data-testid='tasker-card-mobile']",
            "//div[contains(@class, 'mui-1m4n54b')]"
        ]
        
        cards = []
        for selector in card_selectors:
            found_cards = driver.find_elements(By.XPATH, selector)
            if found_cards:
                cards = found_cards
                logger.info(f"Found {len(cards)} cards with selector: {selector}")
                break
        
        if not cards:
            logger.error("No tasker cards found!")
            return
        
        # Debug first 3 cards in detail
        for card_idx, card in enumerate(cards[:3]):
            logger.info(f"\n=== CARD {card_idx + 1} DEBUG ===")
            
            # Get all text in card
            try:
                card_text = card.text.strip()
                logger.info(f"Card text (first 300 chars): '{card_text[:300]}...'")
            except Exception as e:
                logger.error(f"Error getting card text: {e}")
            
            # Find all buttons in card
            try:
                all_buttons = card.find_elements(By.XPATH, ".//button")
                logger.info(f"Found {len(all_buttons)} buttons in card {card_idx + 1}")
                
                for btn_idx, btn in enumerate(all_buttons):
                    try:
                        btn_text = btn.text.strip()
                        btn_classes = btn.get_attribute('class')
                        if btn_text:
                            logger.info(f"  Button {btn_idx+1}: '{btn_text}'")
                            logger.info(f"    Classes: {btn_classes}")
                            
                            # Check if this looks like a name
                            if '.' in btn_text and len(btn_text) < 20:
                                logger.info(f"    *** POTENTIAL NAME: '{btn_text}' ***")
                    except Exception as e:
                        logger.debug(f"  Button {btn_idx+1}: Error - {e}")
            except Exception as e:
                logger.error(f"Error finding buttons in card {card_idx + 1}: {e}")
            
            # Find all clickable elements
            try:
                clickable = card.find_elements(By.XPATH, ".//*[@role='button' or @tabindex or contains(@class, 'button') or contains(@class, 'Button')]")
                logger.info(f"Found {len(clickable)} clickable elements in card {card_idx + 1}")
                
                for click_idx, elem in enumerate(clickable[:5]):
                    try:
                        elem_text = elem.text.strip()
                        if elem_text and len(elem_text) < 50:
                            logger.info(f"  Clickable {click_idx+1}: '{elem_text}'")
                            if '.' in elem_text and len(elem_text) < 20:
                                logger.info(f"    *** POTENTIAL NAME: '{elem_text}' ***")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error finding clickable elements in card {card_idx + 1}: {e}")
        
        # Save page source
        with open('/tmp/debug_cards.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("Saved page source to /tmp/debug_cards.html")
        
    except Exception as e:
        logger.error(f"Error in debug: {e}")
        
    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    debug_card_structure()
