from typing import Dict
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .selectors import (
    IFRAME_OVERLAY_XPATH,
    IFRAME_CONTAINER_WITH_IFRAME_XPATH,
    OVERLAY_SELECTORS,
    AGGRESSIVE_IFRAME_SELECTORS,
    AGGRESSIVE_CONTAINER_SELECTORS,
    CONTINUE_SELECTORS,
)


def close_overlays_and_popups(driver, wait: WebDriverWait, logger, sleeps: Dict[str, float]) -> None:
    """Close common overlays/popups that can block interactions."""
    SLEEP_OVERLAY_REMOVAL = sleeps.get('SLEEP_OVERLAY_REMOVAL', 0.5)
    # Handle iframe overlays
    try:
        iframe_overlays = driver.find_elements(By.XPATH, IFRAME_OVERLAY_XPATH)
        for iframe in iframe_overlays:
            if iframe.is_displayed():
                driver.execute_script("arguments[0].remove();", iframe)
                time.sleep(SLEEP_OVERLAY_REMOVAL)
    except Exception:
        pass

    # Handle parent containers of iframe overlays
    try:
        iframe_containers = driver.find_elements(By.XPATH, IFRAME_CONTAINER_WITH_IFRAME_XPATH)
        for container in iframe_containers:
            if container.is_displayed():
                driver.execute_script("arguments[0].remove();", container)
                time.sleep(SLEEP_OVERLAY_REMOVAL)
    except Exception:
        pass

    for selector in OVERLAY_SELECTORS:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                if element.is_displayed():
                    try:
                        element.click()
                        time.sleep(SLEEP_OVERLAY_REMOVAL)
                    except Exception as e:
                        try:
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(SLEEP_OVERLAY_REMOVAL)
                        except Exception:
                            logger.debug(f"Failed to close overlay with JavaScript: {e}")
                            continue
        except Exception as e:
            logger.debug(f"Error with overlay selector {selector}: {e}")
            continue

    # Try ESC key
    try:
        driver.find_element(By.TAG_NAME, 'body').send_keys("\u001b")
        time.sleep(SLEEP_OVERLAY_REMOVAL)
    except Exception:
        pass


def remove_all_overlays_aggressively(driver, wait: WebDriverWait, logger, sleeps: Dict[str, float]) -> None:
    """Aggressively remove overlays and modals that might block interactions."""
    SLEEP_IFRAME_REMOVAL = sleeps.get('SLEEP_IFRAME_REMOVAL', 0.5)

    try:
        for selector in AGGRESSIVE_IFRAME_SELECTORS:
            iframes = driver.find_elements(By.XPATH, selector)
            for iframe in iframes:
                if iframe.is_displayed():
                    driver.execute_script("arguments[0].remove();", iframe)
                    time.sleep(SLEEP_IFRAME_REMOVAL)
    except Exception:
        pass

    try:
        for selector in AGGRESSIVE_CONTAINER_SELECTORS:
            containers = driver.find_elements(By.XPATH, selector)
            for container in containers:
                if container.is_displayed():
                    try:
                        rect = container.rect
                        if rect.get('width', 0) > 500 and rect.get('height', 0) > 300:
                            driver.execute_script("arguments[0].remove();", container)
                            time.sleep(SLEEP_IFRAME_REMOVAL)
                    except Exception as e:
                        logger.debug(f"Error removing element: {e}")
                        continue
    except Exception:
        pass

    try:
        driver.execute_script(
            """
            var elements = document.querySelectorAll('*');
            for (var i = 0; i < elements.length; i++) {
                var style = window.getComputedStyle(elements[i]);
                var zIndex = parseInt(style.zIndex);
                if (zIndex > 1000 && style.position === 'fixed') {
                    elements[i].remove();
                }
            }
            """
        )
    except Exception:
        pass

    close_overlays_and_popups(driver, wait, logger, sleeps)


def click_continue_button(driver, wait: WebDriverWait, sleeps: Dict[str, float]) -> bool:
    """Click continue/next buttons with multiple selectors."""
    SLEEP_CONTINUE_BUTTON = sleeps.get('SLEEP_CONTINUE_BUTTON', 2)

    for selector in CONTINUE_SELECTORS:
        try:
            continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            continue_btn.click()
            time.sleep(SLEEP_CONTINUE_BUTTON)
            return True
        except TimeoutException:
            continue
    return False
