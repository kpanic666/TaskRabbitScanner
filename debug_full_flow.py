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

def debug_full_flow():
    """Debug the full TaskRabbit flow to understand name extraction."""
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # Step 1: Go to furniture assembly page
        logger.info("Step 1: Navigating to furniture assembly page")
        driver.get("https://www.taskrabbit.com/services/handyman/assemble-furniture")
        time.sleep(3)
        
        # Step 2: Enter address
        logger.info("Step 2: Entering address")
        address_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Enter your address']")))
        address_input.clear()
        address_input.send_keys("New York, NY")
        time.sleep(2)
        
        # Select first suggestion
        try:
            suggestion = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'suggestion') or contains(@class, 'option')]")))
            suggestion.click()
        except:
            logger.info("No address suggestion found, continuing...")
        
        # Continue button
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(3)
        
        # Step 3: Select furniture type
        logger.info("Step 3: Selecting furniture type")
        furniture_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Both IKEA and non-IKEA furniture')]")))
        furniture_option.click()
        time.sleep(2)
        
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
        continue_btn.click()
        time.sleep(3)
        
        # Step 4: Select size
        logger.info("Step 4: Selecting size")
        try:
            size_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Medium')]")))
            size_option.click()
            time.sleep(2)
            
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()
            time.sleep(3)
        except:
            logger.info("Size selection not found or not required")
        
        # Step 5: Add task details
        logger.info("Step 5: Adding task details")
        try:
            details_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//textarea[@placeholder='Describe your task']")))
            details_input.send_keys("build stool")
            time.sleep(2)
            
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()
            time.sleep(5)
        except:
            logger.info("Task details not found or not required")
        
        # Step 6: Now we should be on the taskers page
        logger.info("Step 6: Analyzing taskers page")
        logger.info(f"Current URL: {driver.current_url}")
        logger.info(f"Page title: {driver.title}")
        
        # Wait for page to fully load
        time.sleep(5)
        
        # Test name extraction
        logger.info("=== TESTING NAME EXTRACTION ON LOADED PAGE ===")
        
        selectors_to_test = [
            "//button[contains(@class, 'mui-1pbxn54')]",
            "//button[contains(@class, 'TRTextButtonPrimary-Root')]", 
            "//button[text()[contains(., '.')]]",
            "//*[text()[contains(., '.') and string-length(.) < 20]]"
        ]
        
        for i, selector in enumerate(selectors_to_test, 1):
            logger.info(f"{i}. Testing selector: {selector}")
            try:
                elements = driver.find_elements(By.XPATH, selector)
                logger.info(f"   Found {len(elements)} elements")
                
                for j, elem in enumerate(elements[:10]):  # Show first 10
                    try:
                        text = elem.text.strip()
                        if text and len(text) < 50:
                            logger.info(f"   [{j+1}] '{text}' (displayed: {elem.is_displayed()})")
                    except Exception as e:
                        logger.info(f"   [{j+1}] Error getting text: {e}")
                        
            except Exception as e:
                logger.info(f"   Error with selector: {e}")
        
        # Test card detection
        logger.info("\n=== TESTING CARD DETECTION ===")
        card_selectors = [
            "//div[@data-testid='tasker-card-mobile']",
            "//div[contains(@class, 'mui-1m4n54b')]"
        ]
        
        for selector in card_selectors:
            logger.info(f"Testing card selector: {selector}")
            cards = driver.find_elements(By.XPATH, selector)
            logger.info(f"Found {len(cards)} cards")
            
            if cards:
                logger.info("Testing name extraction within first 3 cards:")
                for card_idx, card in enumerate(cards[:3]):
                    logger.info(f"  Card {card_idx + 1}:")
                    for name_selector in selectors_to_test[:2]:
                        try:
                            name_elements = card.find_elements(By.XPATH, name_selector)
                            logger.info(f"    {name_selector}: {len(name_elements)} elements")
                            for elem in name_elements[:2]:
                                try:
                                    text = elem.text.strip()
                                    if text:
                                        logger.info(f"      Text: '{text}'")
                                except:
                                    pass
                        except Exception as e:
                            logger.info(f"    Error: {e}")
        
        # Save page source for analysis
        with open('/tmp/debug_full_flow.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info("Saved page source to /tmp/debug_full_flow.html")
        
    except Exception as e:
        logger.error(f"Error in debug flow: {e}")
        
    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    debug_full_flow()
