# This script scrapes company information from the SIAL Paris website.

import requests # type: ignore[reportMissingImports]
from bs4 import BeautifulSoup # type: ignore[reportMissingImports]
from playwright.async_api import async_playwright  # type: ignore[reportMissingImports]
from datetime import datetime
from lib.pagebrowser import POST_URL, STEALTH
from pathlib import Path
import lib.pagebrowser as pagebrowser
from urllib.parse import urlparse, urlunparse
from lib.fingerprint import FINGERPRINT, MID
import asyncio


# -- Define global variables ---
SEARCH_QUERY = ""
ALL_PAGES = []
ALL_WEBSITES = []
ALL_EMAILS = []
CURRENT_PAGE = 1
FILENAME = ""
NEXT_PAGE =  True
BASE_URL = "https://made-in-china.com"  # Replace with the actual base URL of the site you want to scrape

