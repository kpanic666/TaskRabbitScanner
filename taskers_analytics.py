#!/usr/bin/env python3
"""
Taskers Analytics Script
Analyzes the latest CSV file for each category in the Taskers folder.
Shows statistics for hourly rates: mean, median, min, max for top 10 and all taskers.
"""

import os
import csv
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import statistics
import matplotlib.pyplot as plt
import numpy as np


def parse_hourly_rate(rate_str):
    """Parse hourly rate string like '$43.36' to float."""
    if not rate_str or rate_str == 'Not found':
        return None
    try:
        return float(rate_str.replace('$', '').replace(',', ''))
    except (ValueError, AttributeError):
        return None


def extract_category_and_datetime(filename):
    """
    Extract category name and datetime from filename.
    Example: 'furniture_assembly_20251104_101126.csv' 
    -> ('furniture_assembly', datetime(2025, 11, 4, 10, 11, 26))
    """
    # Remove .csv extension
    name = filename.replace('.csv', '')
    
    # Pattern: category_YYYYMMDD_HHMMSS
    match = re.match(r'(.+)_(\d{8})_(\d{6})$', name)
    if match:
        category = match.group(1)
        date_str = match.group(2)
        time_str = match.group(3)
        
        try:
            dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return category, dt
        except ValueError:
            return None, None
    
    return None, None


def get_latest_files_by_category(taskers_folder):
    """
    Find the latest file for each category in the Taskers folder.
    Returns dict: {category: filepath}
    """
    category_files = defaultdict(list)
    
    # Scan all CSV files in the folder
    for filename in os.listdir(taskers_folder):
        if not filename.endswith('.csv'):
            continue
        
        category, dt = extract_category_and_datetime(filename)
        if category and dt:
            filepath = os.path.join(taskers_folder, filename)
            category_files[category].append((dt, filepath))
    
    # Get the latest file for each category
    latest_files = {}
    for category, files in category_files.items():
        files.sort(reverse=True)  # Sort by datetime, most recent first
        latest_files[category] = files[0][1]  # Get filepath of latest
    
    return latest_files


def calculate_statistics(rates):
    """Calculate mean, median, min, max for a list of rates."""
    if not rates:
        return None, None, None, None
    
    return (
        statistics.mean(rates),
        statistics.median(rates),
        min(rates),
        max(rates)
    )


def analyze_category_file(filepath):
    """
    Analyze a single category CSV file.
    Returns statistics for top 5, top 15, and all taskers.
    """
    all_rates = []
    top_5_rates = []
    top_15_rates = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader):
            rate = parse_hourly_rate(row.get('hourly_rate'))
            if rate is not None:
                all_rates.append(rate)
                if idx < 5:
                    top_5_rates.append(rate)
                if idx < 15:
                    top_15_rates.append(rate)
    
    top_5_stats = calculate_statistics(top_5_rates)
    top_15_stats = calculate_statistics(top_15_rates)
    all_stats = calculate_statistics(all_rates)
    
    return {
        'total_taskers': len(all_rates),
        'top_5': {
            'mean': top_5_stats[0],
            'median': top_5_stats[1],
            'min': top_5_stats[2],
            'max': top_5_stats[3],
        },
        'top_15': {
            'mean': top_15_stats[0],
            'median': top_15_stats[1],
            'min': top_15_stats[2],
            'max': top_15_stats[3],
        },
        'all': {
            'mean': all_stats[0],
            'median': all_stats[1],
            'min': all_stats[2],
            'max': all_stats[3],
        }
    }


def format_category_name(category):
    """Format category name: remove symbols, replace underscores with spaces, capitalize."""
    # Replace underscores and other symbols with spaces
    formatted = category.replace('_', ' ').replace(',', '').replace('&', 'and')
    # Capitalize each word
    formatted = ' '.join(word.capitalize() for word in formatted.split())
    return formatted


def format_price(value):
    """Format price value for display."""
    if value is None:
        return "N/A"
    return f"${value:.2f}"


def plot_analytics_graphs(analytics_data):
    """Generate bar charts for mean and median values across categories."""
    
    # Sort categories alphabetically
    categories = sorted(analytics_data.keys())
    formatted_categories = [format_category_name(cat) for cat in categories]
    
    # Extract data for plotting
    top_5_means = [analytics_data[cat]['top_5']['mean'] for cat in categories]
    top_15_means = [analytics_data[cat]['top_15']['mean'] for cat in categories]
    all_means = [analytics_data[cat]['all']['mean'] for cat in categories]
    
    top_5_medians = [analytics_data[cat]['top_5']['median'] for cat in categories]
    top_15_medians = [analytics_data[cat]['top_15']['median'] for cat in categories]
    all_medians = [analytics_data[cat]['all']['median'] for cat in categories]
    
    # Set up bar positions
    x = np.arange(len(categories))
    width = 0.25  # Width of each bar
    
    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
    
    # MEAN VALUES CHART
    bars1 = ax1.bar(x - width, top_5_means, width, label='Top 5', color='#2E86AB', alpha=0.8)
    bars2 = ax1.bar(x, top_15_means, width, label='Top 15', color='#A23B72', alpha=0.8)
    bars3 = ax1.bar(x + width, all_means, width, label='All', color='#F18F01', alpha=0.8)
    
    ax1.set_xlabel('Category', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Mean Price per Hour ($)', fontsize=12, fontweight='bold')
    ax1.set_title('Mean Hourly Rates by Category and Tasker Group', fontsize=14, fontweight='bold', pad=20)
    ax1.set_xticks(x)
    ax1.set_xticklabels(formatted_categories, rotation=45, ha='right')
    ax1.legend(fontsize=10)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    
    # Add value labels on bars for mean chart
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.0f}',
                    ha='center', va='bottom', fontsize=7)
    
    # MEDIAN VALUES CHART
    bars4 = ax2.bar(x - width, top_5_medians, width, label='Top 5', color='#2E86AB', alpha=0.8)
    bars5 = ax2.bar(x, top_15_medians, width, label='Top 15', color='#A23B72', alpha=0.8)
    bars6 = ax2.bar(x + width, all_medians, width, label='All', color='#F18F01', alpha=0.8)
    
    ax2.set_xlabel('Category', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Median Price per Hour ($)', fontsize=12, fontweight='bold')
    ax2.set_title('Median Hourly Rates by Category and Tasker Group', fontsize=14, fontweight='bold', pad=20)
    ax2.set_xticks(x)
    ax2.set_xticklabels(formatted_categories, rotation=45, ha='right')
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)
    
    # Add value labels on bars for median chart
    for bars in [bars4, bars5, bars6]:
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:.0f}',
                    ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    plt.show()


def print_analytics_table(analytics_data):
    """Print analytics data as three separate formatted tables."""
    
    # Sort categories alphabetically
    categories = sorted(analytics_data.keys())
    
    # Print TOP 5 TABLE
    print("\n" + "=" * 110)
    print("TOP 5 TASKERS - HOURLY RATE ANALYTICS")
    print("=" * 110)
    print()
    
    header = (
        f"{'Category':<40} | "
        f"{'Total':<6} | "
        f"{'Mean':<12} {'Median':<12} {'Min':<12} {'Max':<12}"
    )
    print(header)
    print("-" * 110)
    
    for category in categories:
        data = analytics_data[category]
        formatted_name = format_category_name(category)
        
        row = (
            f"{formatted_name:<40} | "
            f"{data['total_taskers']:<6} | "
            f"{format_price(data['top_5']['mean']):<12} "
            f"{format_price(data['top_5']['median']):<12} "
            f"{format_price(data['top_5']['min']):<12} "
            f"{format_price(data['top_5']['max']):<12}"
        )
        print(row)
    
    print("=" * 110)
    
    # Print TOP 15 TABLE
    print("\n" + "=" * 110)
    print("TOP 15 TASKERS - HOURLY RATE ANALYTICS")
    print("=" * 110)
    print()
    
    print(header)
    print("-" * 110)
    
    for category in categories:
        data = analytics_data[category]
        formatted_name = format_category_name(category)
        
        row = (
            f"{formatted_name:<40} | "
            f"{data['total_taskers']:<6} | "
            f"{format_price(data['top_15']['mean']):<12} "
            f"{format_price(data['top_15']['median']):<12} "
            f"{format_price(data['top_15']['min']):<12} "
            f"{format_price(data['top_15']['max']):<12}"
        )
        print(row)
    
    print("=" * 110)
    
    # Print ALL TASKERS TABLE
    print("\n" + "=" * 110)
    print("ALL TASKERS - HOURLY RATE ANALYTICS")
    print("=" * 110)
    print()
    
    print(header)
    print("-" * 110)
    
    for category in categories:
        data = analytics_data[category]
        formatted_name = format_category_name(category)
        
        row = (
            f"{formatted_name:<40} | "
            f"{data['total_taskers']:<6} | "
            f"{format_price(data['all']['mean']):<12} "
            f"{format_price(data['all']['median']):<12} "
            f"{format_price(data['all']['min']):<12} "
            f"{format_price(data['all']['max']):<12}"
        )
        print(row)
    
    print("=" * 110)
    print()


def main():
    """Main function to run the analytics."""
    # Get the Taskers folder path
    script_dir = Path(__file__).parent
    taskers_folder = script_dir / "Taskers"
    
    if not taskers_folder.exists():
        print(f"Error: Taskers folder not found at {taskers_folder}")
        return
    
    print(f"Analyzing Taskers data from: {taskers_folder}")
    
    # Get latest files by category
    latest_files = get_latest_files_by_category(taskers_folder)
    
    if not latest_files:
        print("No valid category files found.")
        return
    
    print(f"Found {len(latest_files)} categories with data.")
    
    # Analyze each category
    analytics_data = {}
    for category, filepath in latest_files.items():
        filename = os.path.basename(filepath)
        print(f"Processing: {filename}")
        analytics_data[category] = analyze_category_file(filepath)
    
    # Print results
    print_analytics_table(analytics_data)
    
    # Generate graphs
    print("\nGenerating visualization graphs...")
    plot_analytics_graphs(analytics_data)


if __name__ == "__main__":
    main()
