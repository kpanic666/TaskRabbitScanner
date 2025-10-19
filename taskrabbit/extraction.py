from typing import List, Tuple
from selenium.webdriver.common.by import By
import logging
from .selectors import NAME_SELECTORS_VISIBLE_SCAN, RATE_SELECTORS_VISIBLE_SCAN


def extract_all_visible_text(ctx) -> Tuple[List[str], List[str]]:
    """Extract all visible potential names and rate strings on the current page.
    Returns (potential_names, rates).
    """
    logger = ctx.__dict__.get('logger') or logging.getLogger(__name__)
    driver = ctx.driver

    logger.debug("Extracting all visible text...")
    potential_names: List[str] = []
    rates: List[str] = []

    # Names
    for selector in NAME_SELECTORS_VISIBLE_SCAN:
        try:
            name_elements = driver.find_elements(By.XPATH, selector)
            for element in name_elements:
                if element.is_displayed():
                    text = (element.text or '').strip()
                    if (
                        text and '.' in text and len(text) < 50 and len(text.split()) <= 3
                        and any(c.isalpha() for c in text)
                        and not any(k in text.lower() for k in ['select', 'continue', 'read', 'more', 'book', 'view', 'how', 'help', 'about', 'task', 'review', 'experience'])
                    ):
                        potential_names.append(text)
        except Exception as e:
            logger.debug(f"Error extracting names with selector {selector}: {e}")
            continue

    # Rates
    for selector in RATE_SELECTORS_VISIBLE_SCAN:
        try:
            rate_elements = driver.find_elements(By.XPATH, selector)
            for element in rate_elements:
                if element.is_displayed():
                    text = (element.text or '').strip()
                    if '$' in text and '/hr' in text and len(text) < 20:
                        rates.append(text)
        except Exception as e:
            logger.debug(f"Error extracting rates with selector {selector}: {e}")
            continue

    # Deduplicate
    potential_names = list(set(potential_names))
    rates = list(set(rates))

    logger.info(f"Extracted {len(potential_names)} potential names and {len(rates)} rates")
    return potential_names, rates
