# Common XPath/CSS selector constants shared across modules

# Overlays and popups
IFRAME_OVERLAY_XPATH = "//iframe[contains(@aria-label, 'Modal Overlay')]"
IFRAME_CONTAINER_WITH_IFRAME_XPATH = "//div[contains(@class, 'box-') and .//iframe]"

OVERLAY_SELECTORS = [
    "//div[contains(@class, 'fb_lightbox-overlay')]",
    "//div[contains(@id, 'sidebar-overlay-lightbox')]",
    "//div[contains(@class, 'overlay')]",
    "//div[contains(@class, 'lightbox')]",
    "//div[contains(@class, 'modal')]",
    "//div[contains(@class, 'popup')]",
    "//button[contains(@class, 'close')]",
    "//div[contains(@class, 'close')]",
    "//button[contains(@aria-label, 'close')]",
    "//button[contains(@aria-label, 'Close')]",
    "//span[contains(@class, 'close')]",
    "//a[contains(@class, 'close')]",
    "//button[text()='×']",
    "//button[text()='X']",
    "//span[text()='×']",
    "//span[text()='X']",
]

AGGRESSIVE_IFRAME_SELECTORS = [
    "//iframe[contains(@id, 'lightbox')]",
    "//iframe[contains(@class, 'lightbox')]",
    "//iframe[contains(@id, 'modal')]",
    "//iframe[contains(@class, 'modal')]",
    "//iframe[contains(@aria-label, 'Modal')]",
    "//iframe[contains(@class, 'box-')]",
]

AGGRESSIVE_CONTAINER_SELECTORS = [
    "//div[contains(@class, 'overlay')]",
    "//div[contains(@class, 'modal')]",
    "//div[contains(@class, 'lightbox')]",
    "//div[contains(@class, 'popup')]",
    "//div[contains(@style, 'position: fixed')]",
    "//div[contains(@style, 'position:fixed')]",
    "//div[contains(@style, 'z-index') and contains(@style, '999')]",
]

# Continue/Next buttons
CONTINUE_SELECTORS = [
    "//button[contains(text(), 'Continue')]",
    "//a[contains(text(), 'Continue')]",
    "//button[contains(text(), 'Next')]",
    "//a[contains(text(), 'Next')]",
    "//input[@type='submit']",
    "//button[@type='submit']",
    "//button[contains(text(), 'Proceed')]",
    "//button[contains(text(), 'Go')]",
]

# Visible scan selectors for potential names and rates
NAME_SELECTORS_VISIBLE_SCAN = [
    ".//span[contains(@class, 'mui-5xjf89')]",
    ".//button[contains(@class, 'TRTextButtonPrimary-Root') or contains(@class, 'mui-1pbxn54')]",
    ".//button[contains(@class, 'MuiButton-textPrimary')]",
]

RATE_SELECTORS_VISIBLE_SCAN = [
    "//div[contains(@class, 'mui-loubxv')]",
    "//div[contains(@class, 'rate') and contains(text(), '$') and contains(text(), '/hr')]",
    "//span[contains(text(), '$') and contains(text(), '/hr')]",
    "//div[contains(text(), '$') and contains(text(), '/hr')]",
]

# Per-card extraction selectors
NAME_SELECTORS_CARD = [
    ".//button[contains(@class, 'mui-1pbxn54')]",
    ".//button[contains(@class, 'TRTextButtonPrimary-Root')]",
    ".//span[contains(@class, 'mui-5xjf89')]",
    ".//h3",
    ".//*[text()[contains(., '.') and string-length(.) < 20]]",
]

RATE_SELECTORS_CARD = [
    ".//div[contains(@class, 'mui-loubxv')]",
    ".//*[contains(text(), '$') and contains(text(), '/hr')]",
    ".//*[contains(text(), '$')]",
    ".//div[contains(@class, 'rate')]",
    ".//span[contains(text(), '$')]",
]
