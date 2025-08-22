#!/usr/bin/env python3

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_name_extraction():
    """Quick test to debug name extraction from TaskRabbit page."""
    
    # Setup Chrome driver
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Navigate directly to recommendations page (if we have a saved URL)
        driver.get("https://www.taskrabbit.com/book/2030/recommendations")
        time.sleep(5)
        
        print("=== TESTING NAME EXTRACTION SELECTORS ===")
        
        # Test different selectors for names
        selectors_to_test = [
            "//button[contains(@class, 'mui-1pbxn54')]",
            "//button[contains(@class, 'TRTextButtonPrimary-Root')]",
            "//button[text()[contains(., '.')]]",
            "//span[contains(@class, 'mui-5xjf89')]",
            "//*[text()[contains(., '.') and string-length(.) < 20]]"
        ]
        
        for i, selector in enumerate(selectors_to_test, 1):
            print(f"\n{i}. Testing selector: {selector}")
            try:
                elements = driver.find_elements(By.XPATH, selector)
                print(f"   Found {len(elements)} elements")
                
                for j, elem in enumerate(elements[:5]):  # Show first 5
                    try:
                        text = elem.text.strip()
                        if text and len(text) < 50:  # Reasonable name length
                            print(f"   [{j+1}] '{text}' (displayed: {elem.is_displayed()})")
                    except Exception as e:
                        print(f"   [{j+1}] Error getting text: {e}")
                        
            except Exception as e:
                print(f"   Error with selector: {e}")
        
        # Test tasker card detection
        print("\n=== TESTING TASKER CARD DETECTION ===")
        card_selectors = [
            "//div[@data-testid='tasker-card-mobile']",
            "//div[contains(@class, 'mui-1m4n54b')]"
        ]
        
        for selector in card_selectors:
            print(f"Testing card selector: {selector}")
            cards = driver.find_elements(By.XPATH, selector)
            print(f"Found {len(cards)} cards")
            
            if cards:
                print("Testing name extraction within first card:")
                card = cards[0]
                for name_selector in selectors_to_test[:3]:  # Test top 3 name selectors
                    try:
                        name_elements = card.find_elements(By.XPATH, name_selector)
                        print(f"  {name_selector}: {len(name_elements)} elements")
                        for elem in name_elements[:2]:
                            try:
                                text = elem.text.strip()
                                if text:
                                    print(f"    Text: '{text}'")
                            except:
                                pass
                    except Exception as e:
                        print(f"  Error: {e}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_name_extraction()
