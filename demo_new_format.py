#!/usr/bin/env python3

import csv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_demo_csv():
    """Create a demo CSV with the new format using sample data from the screenshot."""
    
    # Sample data based on the screenshot and previous extractions
    demo_taskers = [
        {
            'name': 'Ivan T.',
            'hourly_rate': '$39.23/hr',
            'review_rating': '5.0',
            'review_count': '64',
            'furniture_tasks': '137',
            'overall_tasks': '124'
        },
        {
            'name': 'Evgenii B.',
            'hourly_rate': '$49.55/hr',
            'review_rating': '5.0',
            'review_count': '1249',
            'furniture_tasks': '2416',
            'overall_tasks': '2411'
        },
        {
            'name': 'Mike F.',
            'hourly_rate': '$39.23/hr',
            'review_rating': '4.9',
            'review_count': '371',
            'furniture_tasks': '415',
            'overall_tasks': '391'
        },
        {
            'name': 'DMITRY L.',
            'hourly_rate': '$52.65/hr',
            'review_rating': '5.0',
            'review_count': '220',
            'furniture_tasks': '377',
            'overall_tasks': '374'
        },
        {
            'name': 'Petra r.',
            'hourly_rate': '$36.13/hr',
            'review_rating': '5.0',
            'review_count': '48',
            'furniture_tasks': '49',
            'overall_tasks': '43'
        }
    ]
    
    # Save to CSV with new format
    csv_filename = '/Users/kpanic/Developer/TaskRabbitScanner/taskrabbit_taskers.csv'
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['name', 'hourly_rate', 'review_rating', 'review_count', 'furniture_tasks', 'overall_tasks']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for tasker in demo_taskers:
            writer.writerow(tasker)
    
    logger.info(f"Created demo CSV with {len(demo_taskers)} taskers in new format")
    logger.info("CSV structure now includes:")
    logger.info("- name: Tasker name (e.g., 'Ivan T.')")
    logger.info("- hourly_rate: Rate per hour (e.g., '$39.23/hr')")
    logger.info("- review_rating: Average review rating (e.g., '5.0')")
    logger.info("- review_count: Number of reviews (e.g., '64')")
    logger.info("- furniture_tasks: Number of furniture assembly tasks (e.g., '137')")
    logger.info("- overall_tasks: Number of overall assembly tasks (e.g., '124')")
    
    # Display the demo data
    logger.info("\nDemo data:")
    for i, tasker in enumerate(demo_taskers, 1):
        logger.info(f"{i}. {tasker['name']} - {tasker['hourly_rate']} - Rating: {tasker['review_rating']} ({tasker['review_count']} reviews) - Tasks: {tasker['furniture_tasks']} furniture, {tasker['overall_tasks']} overall")

if __name__ == "__main__":
    create_demo_csv()
