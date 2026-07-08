"""
Find (and optionally open) a website's contact page, regardless of language.
Async version -- designed to be imported as a dependency and awaited from
your own main.py / worker loop.

Detection checks two signals at once, since neither is reliable alone:
  - the href / URL slug     (e.g. "/nous-contacter", "/kontakt")
  - the visible link text   (e.g. "Contact Us", "联系我们", "اتصل بنا")

A URL slug is often left in English even on non-English sites (SEO habit),
while the visible label is usually localized -- checking both catches far
more real-world cases than either alone.

Some small sites skip a dedicated page entirely and just drop a mailto:
link in the nav. That's detected and returned separately, since there's
nothing to "open" -- just an address to use directly.

Known blind spot: sites where "Contact" is a JS-driven button/modal with
no real href at all. Bare "#" hrefs are filtered out to avoid false
positives, but a true no-href button won't be caught by static parsing --
that would need actual click-simulation, which isn't attempted here.
"""

import asyncio
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.async_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
import lib.extract as extract

CONTACT_KEYWORDS = [
    # English
    "contact", "contact us", "contact-us", "get in touch", "reach us",
    # French
    "contactez-nous", "nous-contacter", "nous contacter",
    # German -- also covers Dutch/Polish/Scandinavian (same word)
    "kontakt", "kontaktieren",
    # Spanish
    "contacto", "contáctenos", "contactenos", "contáctanos",
    # Italian
    "contatti", "contattaci",
    # Portuguese
    "contato", "contactos", "fale conosco", "entre em contato",
    # Dutch
    "neem contact op",
    # Turkish
    "iletişim", "iletisim",
    # Russian
    "контакты", "связаться с нами",
    # Arabic
    "اتصل بنا", "تواصل معنا",
    # Chinese
    "联系我们", "联系",
    # Japanese
    "お問い合わせ", "連絡先",
    # Korean
    "문의하기", "연락처",
    # Vietnamese
    "liên hệ",
    # Greek
    "επικοινωνία",
    # Hindi
    "संपर्क करें", "संपर्क",
]


def _extract_contact_candidates(html: str, base_url: str) -> dict:
    """Pure, synchronous parsing logic -- kept separate so it can run in
    a worker thread and stays independently unit-testable."""
    soup = BeautifulSoup(html, "html.parser")
    page_candidates = []
    mailto_candidates = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True).lower()

        if not href or href == "#":
            continue  # JS-triggered element (e.g. modal), not a real link

        if href.lower().startswith("mailto:"):
            if any(kw in text for kw in CONTACT_KEYWORDS) or not text:
                mailto_candidates.append(href[7:].split("?")[0])
            continue

        if href.startswith(("javascript:", "tel:")):
            continue  # not a navigable page

        combined = f"{href.lower()} {text}"
        if any(kw in combined for kw in CONTACT_KEYWORDS):
            page_candidates.append(urljoin(base_url, href))

    seen = set()
    unique_pages = [u for u in page_candidates if not (u in seen or seen.add(u))]
    unique_mailto = list(dict.fromkeys(mailto_candidates))
    return {"pages": unique_pages, "mailto": unique_mailto}


async def find_contact_link(html: str, base_url: str) -> dict:
    """
    Async entry point. Offloads the (CPU-bound) parsing to a worker
    thread via asyncio.to_thread so it never blocks the event loop --
    matters once you've got several pages being processed concurrently.

    Returns {"pages": [...absolute urls...], "mailto": [...addresses...]}
    Both lists are deduped and ordered by first appearance. Check "pages"
    first; fall back to "mailto" if it's empty.
    """
    return await asyncio.to_thread(_extract_contact_candidates, html, base_url)


async def open_contact_page(playwright_page: Page, homepage_url: str, timeout_ms: int = 15000) -> dict:
    """
    Navigate to homepage_url, locate the contact page, and open it.

    Takes an already-created Playwright async `Page` so it drops into an
    existing browser/context you're managing in main.py, rather than
    launching its own browser per call -- launch one browser at startup
    and reuse contexts/pages; spinning up a fresh browser per site would
    be far too slow across any real batch.

    Returns a status dict instead of raising, so one bad site doesn't take
    down a batch job:
      {"status": "opened", "url": ...}
      {"status": "mailto_only", "email": ...}
      {"status": "broken_link", "url": ...}   # link found but didn't load
      {"status": "not_found"}
      {"status": "timeout", "url": ...}
      {"status": "error", "message": ...}
    """
    try:
        await playwright_page.goto(homepage_url, wait_until="domcontentloaded", timeout=timeout_ms)
        html = await playwright_page.content()
        result = await find_contact_link(html, playwright_page.url)

        if result["pages"]:
            target = result["pages"][0]
            response = await playwright_page.goto(target, wait_until="domcontentloaded", timeout=timeout_ms)
            if response and response.ok:
                return {"status": "opened", "url": target}
            return {"status": "broken_link", "url": target}

        if result["mailto"]:
            return {"status": "mailto_only", "email": result["mailto"][0]}

        return {"status": "not_found"}

    except PlaywrightTimeoutError:
        return {"status": "timeout", "url": homepage_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def ExtractEmailsFromPage(playwright_context: BrowserContext, url: str, timeout: int = 20000):
    foundEmails = []
    seen = set()
    playwright_page = await playwright_context.new_page()
    try:
        await playwright_page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        print(f"Opened page: {url}")
        await playwright_page.wait_for_timeout(3000)  # wait for 1 second to allow the page to load
        html = await playwright_page.content()
        foundEmails.extend(extract.extractEmails(html))
        foundEmails.extend(extract.extractCloudflareEmails(html))
        seen.update(email.lower() for email in foundEmails)
        result = await find_contact_link(html, playwright_page.url)
        if result["pages"]:
            target = result["pages"][0]
            response = await playwright_page.goto(target, wait_until="domcontentloaded", timeout=timeout)
            if response and response.ok:
                print(f"Successfully opened contact page: {target}")
                await playwright_page.wait_for_timeout(1000)  # wait for 1 second to allow the contact page to load
                contact_html = await playwright_page.content()
                foundEmails.extend(extract.extractEmails(contact_html, initSet=seen))
                foundEmails.extend(extract.extractCloudflareEmails(contact_html))
        await playwright_page.close()
        return foundEmails
    except PlaywrightTimeoutError:
        print(f"Timeout while trying to open {url}")
        await playwright_page.close()
        return foundEmails  # return whatever emails were found before the timeout
    except Exception as e:
        print(f"Error occurred while opening {url}: {e}")
        await playwright_page.close()
        return foundEmails  # return whatever emails were found before the error
    