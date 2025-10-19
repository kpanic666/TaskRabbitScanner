# TaskRabbit Multi-Category Tasker Parser

Automates the TaskRabbit booking flow to extract taskers for multiple categories (e.g., Furniture Assembly, Plumbing, Electrical Help, etc.) and saves results as CSV files in the `Taskers/` folder. Supports multi-page scraping and both CLI and interactive modes.

## Features

- **Multi-category support** via `CATEGORIES` in `taskrabbit_parser.py`
- **Automated navigation** through category-specific booking flows
- **Pagination handling** to capture taskers across multiple pages
- **Rich extraction**: name, hourly rate, ratings, review counts, and more
- **CSV output per category** in `Taskers/` with timestamped filenames
- **Headless or visible** Chrome operation
- **Interactive mode** when no CLI args are provided

## Requirements

- Python 3.7+
- Google Chrome installed
- Selenium 4.15+ (driver managed by Selenium Manager; no manual ChromeDriver setup needed)

Install dependencies:

```bash
pip install -r requirements.txt
```

`requirements.txt`:

```text
selenium==4.15.2
webdriver-manager==4.0.1
```

Note: The script uses Selenium 4’s Selenium Manager to resolve ChromeDriver automatically. No explicit use of `webdriver-manager` is required, but it remains listed for compatibility.

## Usage

From the project root (`TaskRabbitScanner/`):

```bash
# Interactive mode (prompts for a category or All) if no args are provided
python taskrabbit_parser.py

# Run a specific category by key
python taskrabbit_parser.py furniture_assembly
python taskrabbit_parser.py plumbing
python taskrabbit_parser.py electrical

# Run all configured categories
python taskrabbit_parser.py all
```

Programmatic helpers in `taskrabbit_parser.py`:

```python
from taskrabbit_parser import TaskRabbitParser, run_parser_for_category, run_all_categories

# Single category
parser = TaskRabbitParser(category='plumbing', headless=False, max_pages=5)
parser.run()

# Helper functions
csv_file = run_parser_for_category('furniture_assembly', headless=True, max_pages=None)
results = run_all_categories(headless=False, max_pages=3)
```

## Categories

Categories are defined in `taskrabbit_parser.py` under `CATEGORIES`. Example keys currently included:

- `furniture_assembly` → Furniture Assembly
- `plumbing` → Plumbing
- `electrical` → Electrical Help
- `door_repair` → Door, Cabinet & Furniture Repair
- `sealing_caulking` → Sealing and caulking
- `appliance_installation` → Appliance Installation
- `flooring_tiling` → Flooring & Tiling Help
- `wall_repair` → Wall Repair
- `window_blinds_repair` → Window & Blinds Repair
- `smart_home` → Smart Home Installation
- `interior_painting` → Interior Painting

Each category has its own URL and option flow in `CATEGORIES[<key>]['options']`. The parser navigates accordingly (e.g., furniture type, size, task details, vehicle requirements).

## Configuration

Configuration lives in `taskrabbit_parser.py`:

- **Headless mode**: pass `headless=True` to `TaskRabbitParser(...)`
- **Page limit**: set `max_pages` in `TaskRabbitParser(...)` or `MAX_PAGES_FOR_TESTING` constant
- **Output directory**: CSVs are saved to `Taskers/` automatically (created if missing)
- **Timing controls**: adjust `SLEEP_*` constants for waits and page loads

Example constructor:

```python
TaskRabbitParser(category='furniture_assembly', headless=False, max_pages=None)
```

## Output

CSV files are saved as `Taskers/<category_name>_<YYYYMMDD_HHMMSS>.csv`. Columns include:

- `name`
- `hourly_rate`
- `review_rating`
- `review_count`
- `furniture_tasks`
- `overall_tasks`
- `two_hour_minimum`
- `elite_status`

## How it works

- Navigates directly to each category page
- Closes overlays/popups defensively
- Enters address `6619 10th Ave, brooklyn, 11219, NY`
- Selects category-specific options from `CATEGORIES`
- Extracts tasker cards, paginates, and writes CSV

## Notes

- Built with `selenium` and Chrome; keep Chrome up to date
- Waits and overlay handling are tuned for dynamic content
- When run without arguments, an interactive selector is shown

## Repository layout

```
TaskRabbitScanner/
├── Taskers/                      # CSV outputs (created automatically)
├── taskrabbit_parser.py          # Main script (multi-category)
├── README.md                     # This file
├── README_MultiCategory.md       # Legacy write-up about multi-category
└── requirements.txt              # Python dependencies
