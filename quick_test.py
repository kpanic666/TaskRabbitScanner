#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from taskrabbit_parser import TaskRabbitParser
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_booking_flow():
    """Test the complete booking flow to reach tasker recommendations."""
    parser = TaskRabbitParser()
    
    try:
        # Initialize browser
        parser.setup_browser()
        
        # Navigate to furniture assembly
        parser.navigate_to_furniture_assembly()
        
        # Complete booking flow
        parser.enter_address()
        parser.select_furniture_options()
        parser.select_task_size()
        parser.enter_task_details()
        
        # Check if we reached recommendations page
        current_url = parser.driver.current_url
        logger.info(f"Final URL: {current_url}")
        
        if "recommendations" in current_url:
            logger.info("✅ Successfully reached tasker recommendations page!")
            
            # Try to extract a few taskers
            taskers = parser.extract_taskers_from_current_page()
            logger.info(f"Found {len(taskers)} taskers on current page")
            
            for i, tasker in enumerate(taskers[:5]):  # Show first 5
                logger.info(f"  {i+1}. {tasker['name']} - {tasker['hourly_rate']}")
                
        else:
            logger.error("❌ Failed to reach tasker recommendations page")
            logger.info("Current page title: " + parser.driver.title)
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
    finally:
        parser.close_browser()

if __name__ == "__main__":
    test_booking_flow()
