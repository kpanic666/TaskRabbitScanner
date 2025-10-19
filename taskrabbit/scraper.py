import time
import re
from typing import List, Dict
from selenium.webdriver.common.by import By
from .selectors import NAME_SELECTORS_CARD, RATE_SELECTORS_CARD

# This module contains the scraping and pagination helpers extracted from TaskRabbitParser.
# Each function accepts `ctx`, which is the TaskRabbitParser instance, so it can
# access `driver`, `wait`, constants (SLEEP_*), and helper methods like
# `is_potential_name()` and `is_valid_person_name()`.


def extract_tasker_data(ctx) -> List[Dict[str, str]]:
    """Extract tasker names and hourly rates from all paginated pages."""
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    logger.info("Extracting tasker data from all pages...")
    all_taskers: List[Dict[str, str]] = []

    # First, get all available page numbers
    available_pages = get_available_page_numbers(ctx)
    if not available_pages:
        logger.info("No pagination found, processing single page...")
        available_pages = [1]

    logger.info(f"Found {len(available_pages)} pages to process: {available_pages}")

    # Process each page individually
    for page_num in available_pages:
        logger.info(f"Processing page {page_num}...")

        # Navigate to the specific page if not page 1
        if page_num > 1:
            success = navigate_to_page_number(ctx, page_num)
            if not success:
                logger.warning(f"Failed to navigate to page {page_num}, skipping...")
                continue
            time.sleep(ctx.__dict__.get('SLEEP_PAGE_NAVIGATION', 3))

        # Debug: capture all visible names before extraction
        debug_visible_names(ctx)

        # Extract taskers from current page
        page_taskers = extract_taskers_from_current_page(ctx)

        if not page_taskers:
            logger.warning(f"No taskers found on page {page_num}, but continuing to next page...")
            continue

        logger.info(f"Found {len(page_taskers)} taskers on page {page_num}")
        all_taskers.extend(page_taskers)

    logger.info(f"Total taskers extracted from all pages: {len(all_taskers)}")
    return all_taskers


def extract_taskers_from_current_page(ctx) -> List[Dict[str, str]]:
    """Extract tasker names and hourly rates from the current page only."""
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver

    logger.debug("Extracting taskers from current page...")
    taskers: List[Dict[str, str]] = []

    # Enhanced debug logging to capture what we actually see
    logger.info(f"Current URL: {driver.current_url}")
    logger.info(f"Page title: {driver.title}")

    # Wait for tasker cards to load
    time.sleep(ctx.__dict__.get('SLEEP_CARD_LOADING', 5))

    # Find tasker cards using the mobile card selector from HTML analysis
    tasker_card_selector = "//div[@data-testid='tasker-card-mobile']"
    tasker_cards = driver.find_elements(By.XPATH, tasker_card_selector)

    if not tasker_cards:
        # Fallback to other selectors
        fallback_selectors = [
            "//div[contains(@class, 'mui-1m4n54b')]",
            "//div[contains(@data-testid, 'tasker')]",
            "//div[contains(@class, 'tasker')]",
            "//div[contains(@class, 'card')]",
        ]
        for selector in fallback_selectors:
            tasker_cards = driver.find_elements(By.XPATH, selector)
            if tasker_cards:
                logger.info(f"Found {len(tasker_cards)} tasker cards with fallback selector: {selector}")
                break
    else:
        logger.info(f"Found {len(tasker_cards)} tasker cards with primary selector")

    if not tasker_cards:
        logger.error("No tasker cards found on page")
        return []

    # Limit to 15 taskers per page as specified
    if len(tasker_cards) > 15:
        logger.info(f"Found {len(tasker_cards)} cards, limiting to 15 per page as specified")
        tasker_cards = tasker_cards[:15]
    logger.info(f"Processing {len(tasker_cards)} tasker cards")

    # Extract name and rate from each card
    for i, card in enumerate(tasker_cards):
        try:
            # Extract name
            name = "Name not found"
            for selector in NAME_SELECTORS_CARD:
                try:
                    name_elements = card.find_elements(By.XPATH, selector)
                    for name_element in name_elements:
                        if name_element and name_element.is_displayed():
                            name_text = name_element.text.strip()
                            if ctx.is_potential_name(name_text):
                                name = name_text
                                break
                    if name != "Name not found":
                        break
                except Exception:
                    continue

            # Aggressive extraction fallback
            if name == "Name not found":
                try:
                    card_text = card.text
                    name_patterns = re.findall(r"\b[A-Z][a-z]+ [A-Z]\.|\b[A-Z][A-Z]+ [A-Z]\.", card_text)
                    if name_patterns:
                        name = name_patterns[0]
                    else:
                        all_text_elements = card.find_elements(By.XPATH, ".//*[text()]")
                        for elem in all_text_elements:
                            elem_text = elem.text.strip()
                            if ctx.is_potential_name(elem_text):
                                name = elem_text
                                break
                        if name == "Name not found":
                            card_html = card.get_attribute('innerHTML')
                            if card_html:
                                html_name_patterns = re.findall(r">([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)*\s+[A-Z]\.)<|>([A-Z][A-Z]+(?:\s+[A-Z][A-Z]+)*\s+[A-Z]\.)<", card_html)
                                for pattern_match in html_name_patterns:
                                    potential_name = pattern_match[0] or pattern_match[1]
                                    if potential_name and ctx.is_potential_name(potential_name):
                                        name = potential_name
                                        break
                except Exception as e:
                    logger.debug(f"Error in fallback name extraction: {e}")

            if name == "Name not found":
                try:
                    card_text = card.text.strip()
                    logger.warning(f"Could not find valid name in card {i+1}. Card text preview: '{card_text[:200]}...'")
                    all_buttons = card.find_elements(By.XPATH, ".//button")
                    logger.debug(f"Card {i+1} has {len(all_buttons)} buttons:")
                    for btn_idx, btn in enumerate(all_buttons[:5]):
                        try:
                            btn_text = btn.text.strip()
                            if btn_text:
                                logger.debug(f"  Button {btn_idx+1}: '{btn_text}' (classes: {btn.get_attribute('class')})")
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"Error debugging card {i+1}: {e}")
                continue

            # Additional validation
            if not ctx.is_valid_person_name(name):
                logger.warning(f"Invalid name format in card {i+1}: '{name}'")
                continue

            # Extract rate
            rate = "Rate not found"
            for selector in RATE_SELECTORS_CARD:
                try:
                    rate_elements = card.find_elements(By.XPATH, selector)
                    for rate_element in rate_elements:
                        if rate_element and rate_element.is_displayed():
                            rate_text = rate_element.text.strip()
                            if '$' in rate_text and '/hr' in rate_text and len(rate_text) < 20:
                                if re.search(r"\$\d+(?:\.\d+)?/hr", rate_text):
                                    rate = rate_text
                                    break
                    if rate != "Rate not found":
                        break
                except Exception:
                    continue

            if rate == "Rate not found":
                try:
                    card_text = card.text
                    rate_matches = re.findall(r"\$\d+(?:\.\d+)?/hr", card_text)
                    if rate_matches:
                        rate = rate_matches[0]
                    else:
                        card_html = card.get_attribute('innerHTML')
                        if card_html:
                            html_rate_matches = re.findall(r"\$\d+(?:\.\d+)?/hr", card_html)
                            if html_rate_matches:
                                rate = html_rate_matches[0]
                            else:
                                price_matches = re.findall(r"\$(\d+\.\d+)", card_html)
                                if price_matches:
                                    rate = f"${price_matches[0]}/hr"
                except Exception:
                    pass

            # Extract reviews
            review_rating = "Not found"
            review_count = "Not found"
            try:
                review_selectors = [
                    ".//*[contains(text(), '(') and contains(text(), 'review')]",
                    ".//*[contains(text(), '★') or contains(text(), '⭐')]",
                ]
                for selector in review_selectors:
                    review_elements = card.find_elements(By.XPATH, selector)
                    for elem in review_elements:
                        text = elem.text.strip()
                        match = re.search(r"(\d+\.\d+)\s*\((\d+)\s*review", text)
                        if match:
                            review_rating = match.group(1)
                            review_count = match.group(2)
                            break
                    if review_rating != "Not found":
                        break
                if review_rating == "Not found":
                    card_text = card.text
                    match = re.search(r"(\d+\.\d+)\s*\((\d+)\s*review", card_text)
                    if match:
                        review_rating = match.group(1)
                        review_count = match.group(2)
                    else:
                        card_html = card.get_attribute('innerHTML')
                        if card_html:
                            html_match = re.search(r"(\d+\.\d+)\s*\((\d+)\s*review", card_html)
                            if html_match:
                                review_rating = html_match.group(1)
                                review_count = html_match.group(2)
            except Exception:
                pass

            # Extract task counts
            furniture_tasks = "Not found"
            overall_tasks = "Not found"
            try:
                card_text = card.text
                furniture_match = re.search(r"(\d+)\s+Furniture Assembly tasks", card_text)
                if furniture_match:
                    furniture_tasks = furniture_match.group(1)
                overall_patterns = [
                    r"(\d+)\s+Assembly tasks overall",
                    r"(\d+)\s+tasks overall",
                    r"(\d+)\s+overall tasks",
                    r"(\d+)\s+total tasks",
                    r"(\d+)\s+tasks completed",
                ]
                for pattern in overall_patterns:
                    overall_match = re.search(pattern, card_text, re.IGNORECASE)
                    if overall_match:
                        overall_tasks = overall_match.group(1)
                        break
                if furniture_tasks == "Not found" or overall_tasks == "Not found":
                    card_html = card.get_attribute('innerHTML')
                    if card_html:
                        if furniture_tasks == "Not found":
                            html_furniture_match = re.search(r"(\d+)\s+Furniture Assembly tasks", card_html)
                            if html_furniture_match:
                                furniture_tasks = html_furniture_match.group(1)
                        if overall_tasks == "Not found":
                            for pattern in overall_patterns:
                                html_overall_match = re.search(pattern, card_html, re.IGNORECASE)
                                if html_overall_match:
                                    overall_tasks = html_overall_match.group(1)
                                    break
                            if overall_tasks == "Not found":
                                overall_tasks = "None"
            except Exception:
                pass

            # Flags
            two_hour_minimum = False
            try:
                card_text = card.text
                card_html = card.get_attribute('innerHTML') or ''
                minimum_patterns = [
                    r"2\s*Hour\s*Minimum",
                    r"2\s*hr\s*minimum",
                    r"2\s*hour\s*min",
                    r"minimum\s*2\s*hour",
                    r"min\s*2\s*hr",
                ]
                for pattern in minimum_patterns:
                    if re.search(pattern, card_text, re.IGNORECASE):
                        two_hour_minimum = True
                        break
                if not two_hour_minimum:
                    for pattern in minimum_patterns:
                        if re.search(pattern, card_html, re.IGNORECASE):
                            two_hour_minimum = True
                            break
                if not two_hour_minimum:
                    minimum_selectors = [
                        ".//*[contains(text(), '2 Hour Minimum')]",
                        ".//*[contains(text(), '2 hour minimum')]",
                        ".//*[contains(text(), '2hr minimum')]",
                        ".//*[contains(text(), 'Minimum 2 hour')]",
                        ".//*[contains(text(), 'minimum 2 hr')]",
                    ]
                    for selector in minimum_selectors:
                        try:
                            elements = card.find_elements(By.XPATH, selector)
                            if elements and any(elem.is_displayed() for elem in elements):
                                two_hour_minimum = True
                                break
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"Error extracting 2 Hour Minimum flag: {e}")

            elite_status = False
            try:
                card_text = card.text
                card_html = card.get_attribute('innerHTML') or ''
                elite_patterns = [r"\bElite\b", r"\bELITE\b", r"\belite\b"]
                for pattern in elite_patterns:
                    if re.search(pattern, card_text):
                        elite_status = True
                        break
                if not elite_status:
                    for pattern in elite_patterns:
                        if re.search(pattern, card_html):
                            elite_status = True
                            break
                if not elite_status:
                    elite_selectors = [
                        ".//*[contains(text(), 'Elite')]",
                        ".//*[contains(text(), 'ELITE')]",
                        ".//*[contains(text(), 'elite')]",
                        ".//*[contains(@class, 'elite')]",
                        ".//*[contains(@class, 'Elite')]",
                    ]
                    for selector in elite_selectors:
                        try:
                            elements = card.find_elements(By.XPATH, selector)
                            if elements and any(elem.is_displayed() for elem in elements):
                                elite_status = True
                                break
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"Error extracting Elite status: {e}")

            # Clean hourly rate by removing '/hr' suffix
            clean_rate = rate
            if rate != "Rate not found" and rate.endswith('/hr'):
                clean_rate = rate.replace('/hr', '')

            tasker = {
                'name': name,
                'hourly_rate': clean_rate,
                'review_rating': review_rating,
                'review_count': review_count,
                'furniture_tasks': furniture_tasks,
                'overall_tasks': overall_tasks,
                'two_hour_minimum': two_hour_minimum,
                'elite_status': elite_status,
            }
            taskers.append(tasker)
            logger.info(
                f"Card {i+1}: {name} - {rate} - Rating: {review_rating} ({review_count} reviews) - "
                f"Tasks: {furniture_tasks} furniture, {overall_tasks} overall - 2Hr Min: {two_hour_minimum} - Elite: {elite_status}"
            )

            if rate == "Rate not found":
                logger.debug(f"Card {i+1} text sample: {card.text[:200]}...")
                try:
                    dollar_elements = card.find_elements(By.XPATH, ".//*[contains(text(), '$')]")
                    if dollar_elements:
                        logger.debug(f"Found {len(dollar_elements)} elements with $ in card {i+1}")
                        for elem in dollar_elements[:3]:
                            logger.debug(f"  $ element: '{elem.text.strip()}'")
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"Error processing tasker card {i+1}: {e}")
            continue

    if not taskers:
        logger.error("No taskers found with card-based extraction")
        try:
            with open('/tmp/taskrabbit_page_debug.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except Exception:
            pass
        return []

    logger.info(f"Successfully extracted {len(taskers)} taskers from current page")
    return taskers


def debug_visible_names(ctx):
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver
    logger.info("=== DEBUGGING VISIBLE NAMES ON PAGE ===")
    try:
        text_elements = driver.find_elements(By.XPATH, "//*[text()]")
        potential_names = []
        for element in text_elements:
            try:
                if element.is_displayed():
                    text = element.text.strip()
                    if (
                        text and len(text) < 50 and any(c.isalpha() for c in text)
                        and (' ' in text or '.' in text)
                        and not any(keyword in text.lower() for keyword in ['http', 'www', 'email', 'phone', 'address'])
                    ):
                        potential_names.append(text)
            except Exception:
                continue
        unique_names = list(set(potential_names))
        unique_names.sort()
        logger.info(f"Found {len(unique_names)} potential names on page:")
        for i, name in enumerate(unique_names[:50]):
            logger.info(f"  {i+1}. '{name}'")
        return unique_names
    except Exception as e:
        logger.error(f"Error in debug_visible_names: {e}")
        return []


def debug_page_structure(ctx):
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver
    try:
        logger.info("=== DEBUGGING PAGE STRUCTURE FOR PAGINATION ===")
        pagination_keywords = ['page', 'next', 'prev', 'pagination', 'pager']
        for keyword in pagination_keywords:
            selectors = [
                f"//*[contains(@class, '{keyword}')]",
                f"//*[contains(@id, '{keyword}')]",
                f"//*[contains(text(), '{keyword}')]",
                f"//*[contains(@data-testid, '{keyword}')]",
            ]
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with '{keyword}' using selector: {selector}")
                        for i, element in enumerate(elements[:3]):
                            try:
                                tag = element.tag_name
                                text = element.text.strip()[:50]
                                class_attr = element.get_attribute('class') or ''
                                id_attr = element.get_attribute('id') or ''
                                href = element.get_attribute('href') or ''
                                logger.info(f"  Element {i+1}: <{tag}> text='{text}' class='{class_attr}' id='{id_attr}' href='{href}'")
                            except Exception:
                                continue
                except Exception:
                    continue
        numeric_selectors = [
            "//a[text()='1']", "//a[text()='2']", "//a[text()='3']", "//a[text()='4']", "//a[text()='5']",
            "//button[text()='1']", "//button[text()='2']", "//button[text()='3']", "//button[text()='4']", "//button[text()='5']",
        ]
        for selector in numeric_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.info(f"Found numeric elements with selector: {selector}")
                    for element in elements:
                        try:
                            href = element.get_attribute('href') or ''
                            class_attr = element.get_attribute('class') or ''
                            logger.info(f"  Numeric element: href='{href}' class='{class_attr}'")
                        except Exception:
                            continue
            except Exception:
                continue
        logger.info("=== END PAGE STRUCTURE DEBUG ===")
    except Exception as e:
        logger.error(f"Error in debug_page_structure: {e}")


def get_available_page_numbers(ctx) -> List[int]:
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver
    try:
        page_numbers: List[int] = []
        debug_page_structure(ctx)
        logger.debug("Searching for pagination elements...")
        pagination_selectors = [
            "//nav//a[contains(@href, 'page=')]",
            "//div[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
            "//ul[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
            "//div[contains(@class, 'page')]//a[contains(@href, 'page=')]",
            "//nav//button[contains(@aria-label, 'Page')]",
            "//div[contains(@class, 'pagination')]//button[contains(@aria-label, 'Page')]",
            "//a[contains(@href, 'page=')]",
            "//button[contains(@aria-label, 'Page')]",
            "//div[contains(@class, 'page')]//a",
            "//nav//a",
            "//div[contains(@class, 'pagination')]//a",
            "//ul[contains(@class, 'pagination')]//a",
            "//span[contains(@class, 'page')]//a",
            "//div[contains(@data-testid, 'page')]//a",
            "//div[contains(@data-testid, 'pagination')]//a",
        ]
        mui_pagination_selectors = [
            "//button[contains(@class, 'MuiPaginationItem-page')]",
            "//button[contains(@class, 'MuiPaginationItem-root')]",
        ]
        for selector in mui_pagination_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} MUI pagination elements with selector: {selector}")
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        class_attr = element.get_attribute('class') or ''
                        logger.debug(f"MUI Pagination element: text='{text}', class='{class_attr}'")
                        if text.isdigit():
                            page_num = int(text)
                            if page_num not in page_numbers:
                                page_numbers.append(page_num)
            except Exception as e:
                logger.debug(f"Error processing MUI pagination element: {e}")
                continue
        if page_numbers:
            page_numbers.sort()
            logger.info(f"Found visible MUI page numbers: {page_numbers}")
            if len(page_numbers) >= 2:
                max_page = max(page_numbers)
                if max_page > len(page_numbers):
                    logger.info(f"Detected ellipsis pagination. Max page: {max_page}, visible pages: {len(page_numbers)}")
                    all_pages = list(range(1, max_page + 1))
                    if ctx.max_pages and len(all_pages) > ctx.max_pages:
                        all_pages = all_pages[:ctx.max_pages]
                        logger.info(f"Limited to first {ctx.max_pages} pages: {all_pages}")
                    else:
                        logger.info(f"Generated complete page range: 1 to {max_page} ({len(all_pages)} pages)")
                    return all_pages
            if ctx.max_pages and len(page_numbers) > ctx.max_pages:
                page_numbers = page_numbers[:ctx.max_pages]
                logger.info(f"Limited to first {ctx.max_pages} pages: {page_numbers}")
            return page_numbers
        for selector in pagination_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} elements with selector: {selector}")
                for element in elements:
                    if element.is_displayed():
                        href = element.get_attribute('href') or ''
                        text = element.text.strip()
                        tag_name = element.tag_name
                        class_attr = element.get_attribute('class') or ''
                        logger.debug(f"Pagination element: tag={tag_name}, text='{text}', href='{href}', class='{class_attr}'")
                        if 'page=' in href:
                            page_match = re.search(r"page=(\d+)", href)
                            if page_match:
                                page_num = int(page_match.group(1))
                                if page_num not in page_numbers:
                                    page_numbers.append(page_num)
                        elif text.isdigit():
                            page_num = int(text)
                            if page_num not in page_numbers:
                                page_numbers.append(page_num)
            except Exception as e:
                logger.debug(f"Error processing pagination element: {e}")
                continue
        if page_numbers:
            page_numbers.sort()
            logger.info(f"Found page numbers: {page_numbers}")
            if ctx.max_pages and len(page_numbers) > ctx.max_pages:
                page_numbers = page_numbers[:ctx.max_pages]
                logger.info(f"Limited to first {ctx.max_pages} pages: {page_numbers}")
            return page_numbers
        text_selectors = [
            "//nav//a[text()]",
            "//div[contains(@class, 'pagination')]//a[text()]",
            "//ul[contains(@class, 'pagination')]//a[text()]",
        ]
        for selector in text_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed():
                        text = element.text.strip()
                        if text.isdigit():
                            page_num = int(text)
                            if page_num not in page_numbers:
                                page_numbers.append(page_num)
            except Exception:
                continue
        if page_numbers:
            page_numbers.sort()
            logger.info(f"Found page numbers from text: {page_numbers}")
            if ctx.max_pages and len(page_numbers) > ctx.max_pages:
                page_numbers = page_numbers[:ctx.max_pages]
                logger.info(f"Limited to first {ctx.max_pages} pages: {page_numbers}")
            return page_numbers
        logger.debug("No pagination page numbers found")
        return []
    except Exception as e:
        logger.debug(f"Error getting available page numbers: {e}")
        return []


def navigate_to_page_number(ctx, page_num: int) -> bool:
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver
    try:
        mui_page_selectors = [
            f"//button[contains(@class, 'MuiPaginationItem-page') and text()='{page_num}']",
            f"//button[contains(@class, 'MuiPaginationItem-root') and text()='{page_num}']",
        ]
        for selector in mui_page_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        element_class = element.get_attribute('class') or ''
                        aria_current = element.get_attribute('aria-current') or ''
                        if (
                            'selected' in element_class.lower()
                            or 'current' in element_class.lower()
                            or 'active' in element_class.lower()
                            or aria_current == 'page'
                        ):
                            logger.debug(f"Skipping current page button for page {page_num}")
                            continue
                        try:
                            logger.info(f"Trying JavaScript click for MUI page {page_num} button")
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(4)
                            current_page_elements = driver.find_elements(
                                By.XPATH,
                                f"//button[contains(@class, 'MuiPaginationItem') and (contains(@class, 'selected') or @aria-current='page') and text()='{page_num}']",
                            )
                            if current_page_elements:
                                logger.info(f"Successfully navigated to page {page_num} via JavaScript (verified by selected state)")
                                return True
                            current_url = driver.current_url
                            if f"page={page_num}" in current_url:
                                logger.info(f"Successfully navigated to page {page_num} via JavaScript (verified by URL)")
                                return True
                        except Exception as js_error:
                            logger.debug(f"JavaScript click failed: {js_error}")
                        logger.info(
                            f"Trying regular click for MUI page {page_num} button with selector: {selector}"
                        )
                        element.click()
                        time.sleep(ctx.__dict__.get('SLEEP_CONTINUE_BUTTON', 2))
                        current_url = driver.current_url
                        if f"page={page_num}" in current_url:
                            logger.info(f"Successfully navigated to page {page_num}")
                            return True
                        else:
                            time.sleep(2)
                            current_url = driver.current_url
                            if f"page={page_num}" in current_url:
                                logger.info(
                                    f"Successfully navigated to page {page_num} after additional wait"
                                )
                                return True
                            else:
                                try:
                                    current_page_elements = driver.find_elements(
                                        By.XPATH,
                                        f"//button[contains(@class, 'MuiPaginationItem') and (contains(@class, 'selected') or @aria-current='page') and text()='{page_num}']",
                                    )
                                    if current_page_elements:
                                        logger.info(
                                            f"Successfully navigated to page {page_num} (verified by selected state)"
                                        )
                                        return True
                                except Exception:
                                    pass
                                logger.debug(
                                    f"Navigation to page {page_num} may have failed - URL is {current_url}"
                                )
            except Exception as e:
                logger.debug(f"Error with MUI page selector {selector}: {e}")
                continue
        page_selectors = [
            f"//nav//a[contains(@href, 'page={page_num}')]",
            f"//div[contains(@class, 'pagination')]//a[contains(@href, 'page={page_num}')]",
            f"//ul[contains(@class, 'pagination')]//a[contains(@href, 'page={page_num}')]",
            f"//div[contains(@class, 'page')]//a[contains(@href, 'page={page_num}')]",
            f"//nav//a[text()='{page_num}']",
            f"//div[contains(@class, 'pagination')]//a[text()='{page_num}']",
            f"//ul[contains(@class, 'pagination')]//a[text()='{page_num}']",
            f"//nav//button[contains(@aria-label, 'Page {page_num}')]",
            f"//div[contains(@class, 'pagination')]//button[contains(@aria-label, 'Page {page_num}')]",
        ]
        for selector in page_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        element_class = element.get_attribute('class') or ''
                        aria_current = element.get_attribute('aria-current') or ''
                        if (
                            'disabled' in element_class.lower()
                            or 'current' in element_class.lower()
                            or 'active' in element_class.lower()
                            or aria_current == 'page'
                        ):
                            logger.debug(
                                f"Skipping current/disabled page button for page {page_num}"
                            )
                            continue
                        logger.info(f"Clicking page {page_num} button with selector: {selector}")
                        element.click()
                        return True
            except Exception as e:
                logger.debug(f"Error with page selector {selector}: {e}")
                continue
        logger.debug(f"No clickable page {page_num} button found")
        return False
    except Exception as e:
        logger.debug(f"Error navigating to page {page_num}: {e}")
        return False


def check_for_next_page(ctx) -> bool:
    logger = ctx.__dict__.get('logger') or __import__('logging').getLogger(__name__)
    driver = ctx.driver
    try:
        next_page_selectors = [
            "//a[contains(@aria-label, 'Next')]",
            "//button[contains(@aria-label, 'Next')]",
            "//a[contains(text(), 'Next')]",
            "//button[contains(text(), 'Next')]",
            "//a[contains(@class, 'next')]",
            "//button[contains(@class, 'next')]",
            "//a[@rel='next']",
            "//button[@rel='next']",
            "//a[contains(@href, 'page=')][last()]",
            "//nav//a[last()]",
            "//div[contains(@class, 'pagination')]//a[last()]",
        ]
        for selector in next_page_selectors:
            try:
                next_elements = driver.find_elements(By.XPATH, selector)
                for element in next_elements:
                    if element.is_displayed() and element.is_enabled():
                        element_text = element.text.lower()
                        element_class = element.get_attribute('class') or ''
                        element_href = element.get_attribute('href') or ''
                        if 'disabled' in element_class.lower():
                            continue
                        if (
                            'next' in element_text
                            or 'next' in element_class.lower()
                            or 'page=' in element_href
                        ):
                            logger.debug(f"Found next page indicator: {selector}")
                            return True
            except Exception:
                continue
        try:
            current_url = driver.current_url
            if 'page=' in current_url:
                page_match = re.search(r"page=(\d+)", current_url)
                if page_match:
                    current_page = int(page_match.group(1))
                    page_source = driver.page_source
                    total_pages_patterns = [
                        rf'Page {current_page} of (\d+)',
                        rf'{current_page} of (\d+)',
                        rf'page {current_page} of (\d+)',
                        r'of (\d+) pages?'
                    ]
                    for pattern in total_pages_patterns:
                        match = re.search(pattern, page_source, re.IGNORECASE)
                        if match:
                            total_pages = int(match.group(1))
                            return current_page < total_pages
        except Exception:
            pass
        try:
            page_number_selectors = [
                "//nav//a[contains(@href, 'page=')]",
                "//div[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
                "//ul[contains(@class, 'pagination')]//a[contains(@href, 'page=')]",
            ]
            current_url = driver.current_url
            current_page_match = re.search(r"page=(\d+)", current_url)
            current_page = int(current_page_match.group(1)) if current_page_match else 1
            for selector in page_number_selectors:
                try:
                    page_elements = driver.find_elements(By.XPATH, selector)
                    for element in page_elements:
                        href = element.get_attribute('href') or ''
                        page_match = re.search(r"page=(\d+)", href)
                        if page_match:
                            page_num = int(page_match.group(1))
                            if page_num > current_page:
                                return True
                except Exception:
                    continue
        except Exception:
            pass
        try:
            page_source = driver.page_source.lower()
            more_indicators = ['show more', 'load more', 'next page', 'page 2', 'more results']
            if any(indicator in page_source for indicator in more_indicators):
                return True
        except Exception:
            pass
        return False
    except Exception:
        return False
