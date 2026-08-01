# Headful Extractor

A Python-based B2B leads extraction tool that uses a headful (visible) Playwright browser to scrape company email addresses from multiple business directories. Extracted leads are saved locally to text files and optionally pushed to a remote API endpoint.

## Supported Sources

| Script | Source |
|---|---|
| `europages.py` | [Europages](https://www.europages.co.uk) — European B2B directory |
| `madeinchina.py` | [Made-in-China](https://www.made-in-china.com) — Chinese manufacturer directory |
| `thomasnet.py` | [ThomasNet](https://www.thomasnet.com) — North American industrial supplier directory |

## How It Works

1. A headful Chromium browser is launched via Playwright.
2. The script navigates to the target directory and paginates through search results.
3. Company profile pages are collected and visited one by one.
4. For each company, the tool attempts to find and visit the company's external website.
5. Contact/about pages are detected using multilingual keyword matching (`lib/pagebrowser.py`).
6. Email addresses are extracted from raw HTML using regex with false-positive filtering (`lib/extract.py`).
7. Unique emails are saved to a timestamped `.txt` file and pushed to the configured API endpoint.

## Project Structure

```
headful-extractor/
├── europages.py          # Scraper for Europages
├── madeinchina.py        # Scraper for Made-in-China
├── thomasnet.py          # Scraper for ThomasNet
├── main_async.py         # Generic async entry point
└── lib/
    ├── extract.py        # Email extraction & filtering logic
    └── pagebrowser.py    # Contact page detection & API push helpers
```

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/) with Chromium
- [playwright-stealth](https://github.com/AtuboDad/playwright_stealth) (used by `thomasnet.py`)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)
- [requests](https://docs.python-requests.org/)

Install dependencies:

```bash
pip install playwright beautifulsoup4 requests playwright-stealth
playwright install chromium
```

## Usage

Run any scraper directly with Python:

```bash
python europages.py
python madeinchina.py
python thomasnet.py
```

Each script will prompt for (or use the configured) search query, then begin scraping. Discovered emails are appended to a timestamped file, e.g.:

```
found_emails_copper_20260721_053920.txt
```

## Configuration

The API endpoint for pushing leads is defined in `lib/pagebrowser.py`:

```python
POST_URL = "https://boothx.mdpa.com.mx/leads/api/v1/push"
```

Update `SEARCH_QUERY` and `BASE_URL` at the top of each scraper script to target a different category or region.

## Output Format

Each output file contains one email address per line:

```
contact@example-company.com
info@another-supplier.de
sales@manufacturer.cn
```

## Notes

- The browser runs in **headful** (non-headless) mode intentionally, which helps bypass bot detection on some sites.
- `thomasnet.py` additionally uses `playwright-stealth` for extra fingerprint evasion.
- The email extractor handles Cloudflare email obfuscation and unicode-escaped characters.
- False positives (image filenames, CDN URLs, mock domains) are filtered out automatically.
