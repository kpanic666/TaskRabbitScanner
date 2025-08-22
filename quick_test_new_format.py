#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from taskrabbit_parser import TaskRabbitParser
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_new_format():
    """Test the new data extraction format with just the first page."""
    parser = TaskRabbitParser()
    
    try:
        # Initialize browser
        parser.setup_driver()
        
        # Navigate to furniture assembly and complete booking flow
        parser.navigate_to_furniture_assembly()
        parser.enter_address_details()
        parser.select_furniture_options()
        
        # Wait for page to load
        import time
        time.sleep(10)
        
        # Extract just from the first page
        logger.info("Extracting taskers from first page only...")
        taskers = parser.extract_taskers_from_current_page()
        
        logger.info(f"Extracted {len(taskers)} taskers with new format:")
        for i, tasker in enumerate(taskers[:5]):  # Show first 5
            logger.info(f"{i+1}. {tasker}")
        
        # Save to CSV with new format
        if taskers:
            parser.save_to_csv(taskers)
            logger.info("Saved taskers with new format to CSV")
        else:
            logger.warning("No taskers extracted")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if parser.driver:
            parser.driver.quit()

if __name__ == "__main__":
    test_new_format()
