#!/usr/bin/env python3
"""
Debug script to examine tasker element structure for rate extraction
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_tasker_rates():
    """Debug tasker rate extraction by examining HTML structure"""
    
    # Setup Chrome options
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Initialize driver
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    try:
        # Navigate directly to a sample tasker recommendations page
        # This URL should work if we can get to the recommendations page
        logger.info("Navigating to TaskRabbit recommendations page...")
        driver.get("https://www.taskrabbit.com/book/2030/recommendations")
        time.sleep(5)
        
        # Find tasker elements
        tasker_elements = driver.find_elements(By.XPATH, "//div[contains(@data-testid, 'tasker')]")
        logger.info(f"Found {len(tasker_elements)} tasker elements")
        
        if tasker_elements:
            # Examine the first few tasker elements
            for i, element in enumerate(tasker_elements[:3]):
                logger.info(f"\n=== TASKER ELEMENT {i+1} ===")
                logger.info(f"Full HTML: {element.get_attribute('outerHTML')[:500]}...")
                logger.info(f"Text content: {element.text}")
                
                # Look for any elements containing dollar signs
                dollar_elements = element.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                logger.info(f"Found {len(dollar_elements)} elements with '$':")
                for j, dollar_elem in enumerate(dollar_elements):
                    logger.info(f"  ${j+1}: '{dollar_elem.text}' (tag: {dollar_elem.tag_name})")
                
                # Look for common price-related attributes
                price_elements = element.find_elements(By.XPATH, ".//*[contains(@class, 'price') or contains(@class, 'rate') or contains(@class, 'cost')]")
                logger.info(f"Found {len(price_elements)} price-related elements:")
                for j, price_elem in enumerate(price_elements):
                    logger.info(f"  Price {j+1}: '{price_elem.text}' (class: {price_elem.get_attribute('class')})")
        
        else:
            logger.warning("No tasker elements found. Page might not be loaded correctly.")
            logger.info(f"Current URL: {driver.current_url}")
            logger.info(f"Page title: {driver.title}")
            
            # Save page source for debugging
            with open('/Users/kpanic/Developer/TaskRabbitScanner/debug_page.html', 'w') as f:
                f.write(driver.page_source)
            logger.info("Saved page source to debug_page.html")
    
    except Exception as e:
        logger.error(f"Error during debugging: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_tasker_rates()
