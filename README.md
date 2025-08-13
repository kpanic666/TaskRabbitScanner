# TaskRabbit Furniture Assembly Tasker Parser

This Python script automates the TaskRabbit booking flow to extract the top 10 taskers for Furniture Assembly category and saves their names and hourly rates to a CSV file.

## Features

- Automated navigation through TaskRabbit's booking flow
- Follows the complete customer journey for Furniture Assembly
- Extracts tasker names and hourly rates
- Saves data to CSV format
- Configurable headless/visible browser mode
- Comprehensive logging

## Requirements

- Python 3.7+
- Chrome browser installed
- ChromeDriver (automatically managed by webdriver-manager)

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

Run the parser:
```bash
python taskrabbit_parser.py
```

The script will:
1. Navigate to TaskRabbit.com
2. Click Services → Furniture Assembly
3. Click Book Now
4. Enter address: 6619 10th Ave, brooklyn, 11219, NY
5. Select "Both ikea and non-Ikea furniture"
6. Choose "Medium size task"
7. Enter quantity "1"
8. Sort by "Recommended"
9. Extract top 10 taskers' names and hourly rates
10. Save to `taskrabbit_taskers.csv`

## Configuration

- Set `headless=True` in the `TaskRabbitParser` constructor for headless mode
- Adjust timeout values in the `WebDriverWait` initialization if needed
- Modify the CSV filename in the `save_to_csv` method

## Output

The script generates a CSV file with the following columns:
- `name`: Tasker's name
- `hourly_rate`: Tasker's hourly rate

## Notes

- The script includes anti-detection measures to avoid being blocked
- Wait times are included to handle dynamic content loading
- Error handling and logging are implemented for debugging
- The parser follows the exact navigation flow specified
