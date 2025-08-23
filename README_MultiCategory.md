# TaskRabbit Multi-Category Parser

This enhanced version of the TaskRabbit parser now supports multiple categories and organizes results in a structured folder system.

## New Features

### 1. Multi-Category Support
- **Furniture Assembly** (existing functionality)
- **Plumbing** (newly added)
- Easily extensible for additional categories

### 2. Organized File Structure
- All CSV files are now saved in the `Taskers/` folder
- Filename format: `CATEGORY_NAME_date_time.csv`
- Example: `furniture_assembly_20231123_143052.csv`

### 3. Configurable Navigation Flows
- Each category has its own configuration
- Navigation flows can be customized per category
- Options are defined in the `CATEGORIES` dictionary

## Usage

### Command Line Options

```bash
# Run default category (Furniture Assembly)
python taskrabbit_parser.py

# Run specific category
python taskrabbit_parser.py furniture_assembly
python taskrabbit_parser.py plumbing

# Run all categories
python taskrabbit_parser.py all
```

### Programmatic Usage

```python
from taskrabbit_parser import TaskRabbitParser, run_parser_for_category, run_all_categories

# Single category
parser = TaskRabbitParser(category='plumbing', headless=False, max_pages=5)
parser.run()

# Using helper functions
csv_file = run_parser_for_category('furniture_assembly')
results = run_all_categories(max_pages=3)
```

## Category Configuration

Categories are defined in the `CATEGORIES` dictionary:

```python
CATEGORIES = {
    'furniture_assembly': {
        'name': 'Furniture Assembly',
        'url': 'https://www.taskrabbit.com/services/handyman/assemble-furniture',
        'options': [
            {'type': 'furniture_type', 'value': 'Both IKEA and non-IKEA furniture'},
            {'type': 'size', 'value': 'Medium - Est. 2-3 hrs'},
            {'type': 'task_details', 'value': 'build stool'}
        ]
    },
    'plumbing': {
        'name': 'Plumbing',
        'url': 'https://www.taskrabbit.com/services/plumbing',
        'options': [
            {'type': 'task_details', 'value': 'fix leaky faucet'}
        ]
    }
}
```

## Adding New Categories

To add a new category:

1. Add entry to `CATEGORIES` dictionary
2. Define the category URL and options
3. Implement any category-specific option handlers if needed

Example for adding "Electrical" category:

```python
'electrical': {
    'name': 'Electrical',
    'url': 'https://www.taskrabbit.com/services/electrical',
    'options': [
        {'type': 'task_details', 'value': 'install light fixture'}
    ]
}
```

## File Organization

```
TaskRabbitScanner/
├── Taskers/                          # All CSV outputs go here
│   ├── furniture_assembly_20231123_143052.csv
│   ├── plumbing_20231123_143155.csv
│   └── ...
├── taskrabbit_parser.py              # Main parser (now multi-category)
├── demo_multi_category.py            # Demo script
└── README_MultiCategory.md           # This file
```

## Demo Script

Run the demo to see the multi-category functionality:

```bash
python demo_multi_category.py
```

The demo includes:
1. Single category extraction
2. Plumbing category extraction  
3. All categories extraction
4. Category information display

## Backward Compatibility

The parser maintains backward compatibility:
- Default behavior runs Furniture Assembly category
- Existing scripts will continue to work
- CSV format remains the same

## Future Expansion

The architecture supports easy addition of more categories:
- Home Repairs
- Moving Services
- Cleaning
- Handyman Services
- And more...

Each category can have its own navigation flow and options while sharing the core extraction logic.
