"""
Configuration for NotebookLM Skill
Centralizes constants, selectors, and paths
"""

from pathlib import Path

# Paths
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"
BROWSER_STATE_DIR = DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = DATA_DIR / "auth_info.json"
LIBRARY_FILE = DATA_DIR / "library.json"

# NotebookLM Selectors
QUERY_INPUT_SELECTORS = [
    "textarea.query-box-input",  # Primary
    'textarea[aria-label="Feld für Anfragen"]',  # Fallback German
    'textarea[aria-label="Input for queries"]',  # Fallback English
]

RESPONSE_SELECTORS = [
    ".to-user-container .message-text-content",  # Primary
    "[data-message-author='bot']",
    "[data-message-author='assistant']",
]

# Browser Configuration
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',  # Patches navigator.webdriver
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check'
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Project Management Selectors
NOTEBOOKLM_HOME = "https://notebooklm.google.com"
CREATE_NOTEBOOK_BUTTON_SELECTORS = [
    'button[aria-label="Create new notebook"]',
    'button:has-text("Create new")',
    'button:has-text("New notebook")',
    '[data-testid="create-notebook"]',
]

NOTEBOOK_TITLE_INPUT_SELECTORS = [
    'input[aria-label="Notebook title"]',
    'input[placeholder*="Untitled"]',
    '[data-testid="notebook-title-input"]',
]

# Add Source Selectors (Updated from UI inspection)
ADD_SOURCE_BUTTON_SELECTORS = [
    'button:has-text("Add sources")',
    'button[aria-label="Add source"]',
    'button:has-text("Upload a source")',
    '[data-testid="add-source-button"]',
]

WEBSITE_SOURCE_OPTION_SELECTORS = [
    'button:has-text("Websites")',
    'button:has-text("Website")',
    '[data-testid="website-source"]',
]

URL_INPUT_SELECTORS = [
    'textarea[aria-label="Enter URLs"]',
    'textarea[placeholder="Paste any links"]',
    'textarea[placeholder*="links"]',
    'input[placeholder*="URL"]',
]

SUBMIT_SOURCE_BUTTON_SELECTORS = [
    'button:has-text("Insert")',
    'button:has-text("Add")',
    'button[type="submit"]',
]

# Audio Overview Selectors
AUDIO_OVERVIEW_TAB_SELECTORS = [
    'button[aria-label="Audio Overview"]',
    'button:has-text("Audio Overview")',
    '[data-testid="audio-overview-tab"]',
]

GENERATE_AUDIO_BUTTON_SELECTORS = [
    'button:has-text("Generate")',
    'button[aria-label="Generate audio"]',
    '[data-testid="generate-audio"]',
]

AUDIO_PLAYER_SELECTORS = [
    'audio',
    '[data-testid="audio-player"]',
]

DOWNLOAD_AUDIO_BUTTON_SELECTORS = [
    'button[aria-label="Download"]',
    'button:has-text("Download")',
    '[data-testid="download-audio"]',
]

AUDIO_LOADING_SELECTORS = [
    '.audio-loading',
    '[data-testid="audio-loading"]',
    ':has-text("Generating")',
]

# Timeouts
LOGIN_TIMEOUT_MINUTES = 10
QUERY_TIMEOUT_SECONDS = 120
PAGE_LOAD_TIMEOUT = 30000
AUDIO_GENERATION_TIMEOUT = 600  # 10 minutes for audio generation
