import sys
from typing import Dict, Optional
from .categories import CATEGORIES
import taskrabbit_parser as trp  # import top-level script containing TaskRabbitParser


def run_parser_for_category(category: str, headless: bool = False, max_pages: Optional[int] = None) -> str:
    """Run the parser for a specific category and return CSV filename."""
    parser = trp.TaskRabbitParser(category=category, headless=headless, max_pages=max_pages)
    parser.run()
    return parser.csv_filename


def run_all_categories(headless: bool = False, max_pages: Optional[int] = None) -> Dict[str, Optional[str]]:
    """Run the parser for all configured categories and return mapping to CSV paths (or None on failure)."""
    results: Dict[str, Optional[str]] = {}
    for category in CATEGORIES.keys():
        try:
            csv_file = run_parser_for_category(category, headless, max_pages)
            results[category] = csv_file
        except Exception:
            results[category] = None
    return results


def interactive_category_selection() -> Optional[str]:
    """Interactive category selection when no command line arguments provided."""
    print("TaskRabbit Multi-Category Parser")
    print("\nAvailable categories:")

    category_list = list(CATEGORIES.keys())
    for i, category_key in enumerate(category_list, 1):
        category_name = CATEGORIES[category_key]['name']
        print(f"{i}. {category_name} ({category_key})")

    print(f"{len(category_list) + 1}. All categories")

    while True:
        try:
            choice = input(f"\nSelect category (1-{len(category_list) + 1}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                print("Cancelled.")
                return None
            choice_num = int(choice)
            if 1 <= choice_num <= len(category_list):
                selected_category = category_list[choice_num - 1]
                print(f"Selected: {CATEGORIES[selected_category]['name']}")
                return selected_category
            elif choice_num == len(category_list) + 1:
                print("Selected: All categories")
                return 'all'
            else:
                print(f"Invalid choice. Please enter 1-{len(category_list) + 1} or 'q'.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")
        except KeyboardInterrupt:
            print("\nCancelled.")
            return None


def main(max_pages: Optional[int] = None, headless: bool = False) -> int:
    """CLI entrypoint mirroring original __main__ behavior."""
    # Check if category is specified as command line argument
    if len(sys.argv) > 1:
        specified_category = sys.argv[1].lower()
        if specified_category == 'all':
            results = run_all_categories(headless=headless, max_pages=max_pages)
            print("\nExtraction Results:")
            for cat, file in results.items():
                status = "\u2713" if file else "\u2717"
                print(f"{status} {CATEGORIES[cat]['name']}: {file or 'Failed'}")
            return 0
        elif specified_category in CATEGORIES:
            parser = trp.TaskRabbitParser(category=specified_category, headless=headless, max_pages=max_pages)
            parser.run()
            return 0
        else:
            print(f"Unknown category: {specified_category}")
            print(f"Available categories: {', '.join(CATEGORIES.keys())}, all")
            return 1
    else:
        selected_category = interactive_category_selection()
        if selected_category is None:
            return 0
        elif selected_category == 'all':
            results = run_all_categories(headless=headless, max_pages=max_pages)
            print("\nExtraction Results:")
            for cat, file in results.items():
                status = "\u2713" if file else "\u2717"
                print(f"{status} {CATEGORIES[cat]['name']}: {file or 'Failed'}")
            return 0
        else:
            parser = trp.TaskRabbitParser(category=selected_category, headless=headless, max_pages=max_pages)
            parser.run()
            return 0
