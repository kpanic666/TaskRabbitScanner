#!/usr/bin/env python3
"""
CSV Analyzer for TaskRabbit Tasker Data

This script analyzes CSV files for 3 categories: furniture assembly, general mounting, and tv mounting.
It compares the most recent files with the earliest previous files to show task count changes.
"""

import os
import csv
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

TWO_HR_COEFFICIENT = 2.2
GM_COEFFICIENT = 1.47
TV_COEFFICIENT = 1.1
FA_COEFFICIENT = 1.6

# Category configuration
CATEGORIES = {
    'furniture_assembly': {
        'task_column': 'furniture_tasks',
        'file_pattern': 'furniture_assembly_'
    },
    'general_mounting': {
        'task_column': 'general_mounting_tasks',
        'file_pattern': 'general_mounting_'
    },
    'tv_mounting': {
        'task_column': 'tv_mounting_tasks',
        'file_pattern': 'tv_mounting_'
    }
}

# Address mapping from file suffixes
ADDRESS_MAP = {
    'manhattan_uws': 'Manhattan - Upper West Side',
    'manhattan_ues': 'Manhattan - Upper East Side',
    'manhattan_s': 'Manhattan - Soho',
    'brooklyn_d': 'Brooklyn - Downtown',
    'queens': 'Queens'
}


def parse_datetime_from_filename(filename: str) -> Optional[datetime]:
    """Extract datetime from CSV filename."""
    # Pattern: category_YYYYMMDD_HHMMSS_address.csv
    match = re.search(r'(\d{8})_(\d{6})', filename)
    if match:
        date_str = match.group(1)
        time_str = match.group(2)
        try:
            return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except ValueError:
            return None
    return None


def extract_address_from_filename(filename: str) -> str:
    """Extract address from CSV filename."""
    # Remove .csv extension
    base = filename.replace('.csv', '')
    # Try to find address suffix
    for suffix, address in ADDRESS_MAP.items():
        if base.endswith(suffix):
            return address
    return "Unknown"


def get_csv_files_in_directory(directory: str) -> List[str]:
    """Get all CSV files in the specified directory."""
    csv_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            csv_files.append(filename)
    return csv_files


def find_most_recent_files(directory: str, category: str) -> Optional[Tuple[str, datetime]]:
    """Find the most recent CSV file for a given category."""
    pattern = CATEGORIES[category]['file_pattern']
    csv_files = get_csv_files_in_directory(directory)
    
    category_files = []
    for filename in csv_files:
        if filename.startswith(pattern):
            dt = parse_datetime_from_filename(filename)
            if dt:
                category_files.append((filename, dt))
    
    if not category_files:
        return None
    
    # Sort by datetime descending and return the most recent
    category_files.sort(key=lambda x: x[1], reverse=True)
    return category_files[0]


def find_earliest_previous_file(directory: str, category: str, most_recent_file: str) -> Optional[Tuple[str, datetime]]:
    """Find the most recent previous CSV file for a given category (before most recent).
    Prefers files from a different day over files from the same day."""
    pattern = CATEGORIES[category]['file_pattern']
    csv_files = get_csv_files_in_directory(directory)
    
    most_recent_dt = parse_datetime_from_filename(most_recent_file)
    if not most_recent_dt:
        return None
    
    most_recent_date = most_recent_dt.date()
    
    category_files = []
    for filename in csv_files:
        if filename.startswith(pattern) and filename != most_recent_file:
            dt = parse_datetime_from_filename(filename)
            if dt and dt < most_recent_dt:
                category_files.append((filename, dt))
    
    if not category_files:
        return None
    
    # Group files by date
    files_by_date = {}
    for filename, dt in category_files:
        file_date = dt.date()
        if file_date not in files_by_date:
            files_by_date[file_date] = []
        files_by_date[file_date].append((filename, dt))
    
    # Find the most recent date that is different from most_recent_date
    available_dates = sorted(files_by_date.keys(), reverse=True)
    
    # Try to find a date different from most_recent_date (most recent first)
    target_date = None
    for date in available_dates:
        if date != most_recent_date:
            target_date = date
            break
    
    # If all files are from the same day, use the most recent date
    if target_date is None and available_dates:
        target_date = available_dates[0]
    
    if target_date is None:
        return None
    
    # Among files from target_date, pick the one with most recent time
    target_files = files_by_date[target_date]
    target_files.sort(key=lambda x: x[1], reverse=True)
    
    return target_files[0]


def read_taskers_from_csv(filepath: str, task_column: str) -> Dict[str, Dict]:
    """Read taskers from CSV file and return a dict of name -> task data."""
    taskers = {}
    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '').strip()
                task_count_str = row.get(task_column, '').strip()
                hourly_rate_str = row.get('hourly_rate', '').strip()
                two_hour_minimum_str = row.get('two_hour_minimum', '').strip()
                
                if name and task_count_str and task_count_str != 'None' and task_count_str != 'Not found':
                    try:
                        task_count = int(task_count_str)
                        
                        # Parse hourly rate (remove $ sign)
                        hourly_rate = 0.0
                        if hourly_rate_str and hourly_rate_str != 'None' and hourly_rate_str != 'Not found':
                            try:
                                hourly_rate = float(hourly_rate_str.replace('$', '').replace(',', ''))
                            except ValueError:
                                pass
                        
                        # Parse two_hour_minimum
                        two_hour_minimum = False
                        if two_hour_minimum_str and two_hour_minimum_str.lower() == 'true':
                            two_hour_minimum = True
                        
                        taskers[name] = {
                            'task_count': task_count,
                            'hourly_rate': hourly_rate,
                            'two_hour_minimum': two_hour_minimum
                        }
                    except ValueError:
                        pass
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    
    return taskers


def analyze_category(directory: str, category: str) -> Optional[Dict]:
    """Analyze a single category and return comparison data."""
    # Find most recent file
    most_recent_result = find_most_recent_files(directory, category)
    if not most_recent_result:
        print(f"No files found for category: {category}")
        return None
    
    most_recent_file, most_recent_dt = most_recent_result
    
    # Find earliest previous file
    previous_result = find_earliest_previous_file(directory, category, most_recent_file)
    if not previous_result:
        print(f"No previous file found for category: {category}")
        return None
    
    previous_file, previous_dt = previous_result
    
    # Read taskers from both files
    task_column = CATEGORIES[category]['task_column']
    current_taskers = read_taskers_from_csv(os.path.join(directory, most_recent_file), task_column)
    previous_taskers = read_taskers_from_csv(os.path.join(directory, previous_file), task_column)
    
    # Build comparison data in order of current file
    comparison_data = []
    for name in current_taskers:
        if name in previous_taskers:
            current_data = current_taskers[name]
            previous_data = previous_taskers[name]
            
            current_tasks = current_data['task_count']
            previous_tasks = previous_data['task_count']
            difference = current_tasks - previous_tasks
            
            # Get hourly rate from current file
            hourly_rate = current_data['hourly_rate']
            two_hour_minimum = current_data['two_hour_minimum']
            
            # Calculate total amount based on two_hour_minimum logic
            if two_hour_minimum:
                total_amount = hourly_rate * TWO_HR_COEFFICIENT * difference
            else:
                if category == 'general_mounting':
                    total_amount = hourly_rate * GM_COEFFICIENT * difference
                elif category == 'tv_mounting':
                    total_amount = hourly_rate * TV_COEFFICIENT * difference
                elif category == 'furniture_assembly':
                    total_amount = hourly_rate * FA_COEFFICIENT * difference
            
            comparison_data.append({
                'name': name,
                'previous_tasks': previous_tasks,
                'current_tasks': current_tasks,
                'difference': difference,
                'hourly_rate': hourly_rate,
                'two_hour_minimum': two_hour_minimum,
                'total_amount': total_amount
            })
    
    return {
        'category': category,
        'most_recent_file': most_recent_file,
        'most_recent_dt': most_recent_dt,
        'previous_file': previous_file,
        'previous_dt': previous_dt,
        'address': extract_address_from_filename(most_recent_file),
        'comparison_data': comparison_data
    }


def print_table(category_data: Dict):
    """Print a formatted table for a category."""
    category = category_data['category']
    most_recent_dt = category_data['most_recent_dt']
    previous_dt = category_data['previous_dt']
    address = category_data['address']
    comparison_data = category_data['comparison_data']
    
    # Format dates
    current_date_str = most_recent_dt.strftime("%Y-%m-%d %H:%M:%S")
    previous_date_str = previous_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Print header
    print(f"\n{'='*80}")
    print(f"Category: {category.replace('_', ' ').title()}")
    print(f"Address: {address}")
    print(f"{'='*80}")
    
    # Print table header
    print(f"\n{'Tasker Name':<15} | {f'Tasks ({previous_date_str})':<20} | {f'Tasks ({current_date_str})':<20} | {'Difference':<10} | {'Hourly Rate':<12} | {'Total Amount':<15}")
    print("-" * 110)
    
    # Print data
    for item in comparison_data:
        name = item['name']
        previous = item['previous_tasks']
        current = item['current_tasks']
        diff = item['difference']
        hourly_rate = item['hourly_rate']
        total_amount = item['total_amount']
        
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        hourly_rate_str = f"${hourly_rate:.2f}" if hourly_rate > 0 else "N/A"
        total_amount_str = f"${total_amount:.2f}" if total_amount > 0 else "N/A"
        
        print(f"{name:<15} | {previous:<20} | {current:<20} | {diff_str:<10} | {hourly_rate_str:<12} | {total_amount_str:<15}")
    
    print(f"\nTotal taskers compared: {len(comparison_data)}")


def main():
    """Main function to run the CSV analyzer."""
    taskers_dir = os.path.join(os.path.dirname(__file__), 'Taskers')
    
    if not os.path.exists(taskers_dir):
        print(f"Error: Taskers directory not found: {taskers_dir}")
        return
    
    print("TaskRabbit CSV Analyzer")
    print("=" * 80)
    print(f"Analyzing files in: {taskers_dir}\n")
    
    # Analyze each category
    results = {}
    for category in CATEGORIES.keys():
        result = analyze_category(taskers_dir, category)
        if result:
            results[category] = result
    
    # Print tables
    for category in ['furniture_assembly', 'general_mounting', 'tv_mounting']:
        if category in results:
            print_table(results[category])
    
    print("\n" + "=" * 80)
    print("Analysis complete.")


if __name__ == "__main__":
    main()
