#!/usr/bin/env python3
"""
Demo script for the multi-category TaskRabbit parser.

This script demonstrates how to use the new multi-category functionality
to extract taskers from different TaskRabbit categories.
"""

from taskrabbit_parser import TaskRabbitParser, CATEGORIES, run_parser_for_category, run_all_categories
import logging

# Configure logging for demo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def demo_single_category():
    """Demo: Extract taskers from a single category (Furniture Assembly)."""
    print("\n" + "="*60)
    print("DEMO 1: Single Category Extraction (Furniture Assembly)")
    print("="*60)
    
    try:
        # Create parser for furniture assembly
        parser = TaskRabbitParser(category='furniture_assembly', headless=False, max_pages=2)
        parser.run()
        print(f"✓ Successfully extracted furniture assembly taskers to: {parser.csv_filename}")
    except Exception as e:
        print(f"✗ Error extracting furniture assembly taskers: {e}")

def demo_plumbing_category():
    """Demo: Extract taskers from Plumbing category."""
    print("\n" + "="*60)
    print("DEMO 2: Plumbing Category Extraction")
    print("="*60)
    
    try:
        # Create parser for plumbing
        parser = TaskRabbitParser(category='plumbing', headless=False, max_pages=2)
        parser.run()
        print(f"✓ Successfully extracted plumbing taskers to: {parser.csv_filename}")
    except Exception as e:
        print(f"✗ Error extracting plumbing taskers: {e}")

def demo_all_categories():
    """Demo: Extract taskers from all configured categories."""
    print("\n" + "="*60)
    print("DEMO 3: All Categories Extraction")
    print("="*60)
    
    try:
        results = run_all_categories(headless=False, max_pages=2)
        
        print("\nExtraction Results:")
        for category, csv_file in results.items():
            category_name = CATEGORIES[category]['name']
            if csv_file:
                print(f"✓ {category_name}: {csv_file}")
            else:
                print(f"✗ {category_name}: Failed")
                
    except Exception as e:
        print(f"✗ Error in batch extraction: {e}")

def demo_category_info():
    """Demo: Show available categories and their configurations."""
    print("\n" + "="*60)
    print("DEMO 4: Available Categories Information")
    print("="*60)
    
    print("Configured Categories:")
    for category_key, config in CATEGORIES.items():
        print(f"\nCategory: {config['name']} (key: {category_key})")
        print(f"  URL: {config['url']}")
        print(f"  Options:")
        for option in config['options']:
            print(f"    - {option['type']}: {option['value']}")

if __name__ == "__main__":
    print("TaskRabbit Multi-Category Parser Demo")
    print("This demo will show the new multi-category functionality.")
    
    # Show category information first
    demo_category_info()
    
    # Ask user which demo to run
    print("\nAvailable demos:")
    print("1. Single category (Furniture Assembly)")
    print("2. Plumbing category")
    print("3. All categories")
    print("4. Just show info (already shown above)")
    
    choice = input("\nEnter demo number (1-4) or 'q' to quit: ").strip()
    
    if choice == '1':
        demo_single_category()
    elif choice == '2':
        demo_plumbing_category()
    elif choice == '3':
        demo_all_categories()
    elif choice == '4':
        print("Category information already displayed above.")
    elif choice.lower() == 'q':
        print("Demo cancelled.")
    else:
        print("Invalid choice. Please run the demo again.")
    
    print("\nDemo completed!")
