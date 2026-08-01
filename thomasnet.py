"""
This script is a robust email extraction module for extracting email leads from thomasnet

"""
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import requests
from lib.pagebrowser import POST_URL
import lib.pagebrowser as pagebrowser
from urllib.parse import urlparse, urlunparse
from datetime import datetime


# -- Define global variables ---
SEARCH_QUERY = ""
ALL_PAGES = []
ALL_WEBSITES = []
ALL_EMAILS = []
CURRENT_PAGE = 1
FILENAME = ""
BASE_URL = "https://www.thomasnet.com"  # Replace with the actual base URL of the site you want to scrape

# -- function to create txt file and write the found emails to it
def save_emails_to_file(emails, filename="found_emails.txt", mode="a"):
    with open(filename, mode) as f:
        for email in emails:
            f.write(f"{email}\n")


# -- function to push leads to the API endpoint --
def push_leads_to_api(leads, source):
    payload = {
        "leads": leads,
        "source": source,
        "keywords": SEARCH_QUERY,
        "location": "america"
    }
    try:
        response = requests.post(POST_URL, json=payload)
        if response.status_code == 201:
            print(f"Successfully pushed {len(leads)} leads to the API.")
        else:
            print(f"Failed to push leads. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error occurred while pushing leads to the API: {e}")


#async function to open a tab and visit a company website link
async def visitCompanyWebsite(context, websiteLink):
    page = await context.new_page()
    try:
        await page.goto(websiteLink)
        print(f"Visiting company website: {websiteLink}")
        await page.wait_for_load_state("networkidle")
    except Exception as e:
        print(f"Error occurred while visiting {websiteLink}: {e}")
    finally:
        await page.close()

# -- function to introduce a human-like delay --
async def human_delay(a=700, b=1800):
    await asyncio.sleep(random.uniform(a / 1000, b / 1000))


# -- function to simulate human-like mouse movements --
async def human_mouse(page):

    width = 1800
    height = 900

    for _ in range(random.randint(4, 8)):

        x = random.randint(50, width)
        y = random.randint(50, height)

        await page.mouse.move(
            x,
            y,
            steps=random.randint(15, 40)
        )

        await asyncio.sleep(random.uniform(0.05, 0.15))

# -- function to simulate random scrolling on the page --
async def random_scroll(page):

    for _ in range(random.randint(2, 5)):

        amount = random.randint(300, 900)

        await page.mouse.wheel(0, amount)

        await human_delay(500, 1200)


async def main():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./playwrite-userss-data",
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=False,  # Set to True for headless mode
            viewport=None,
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
            args=[
                "--start-maximized",
            ]
        )
        # ----------------------------------------------
        # Apply stealth settings to the browser context
        # ----------------------------------------------
        stealth = Stealth()
        await stealth.apply_stealth_async(context)

        page = context.pages[0] if context.pages else await context.new_page()
        print("User-Agent:")
        print(await page.evaluate("navigator.userAgent"))

        print()

        print("Browser Version:")
        print(await page.evaluate("navigator.userAgentData?.brands"))

        print()

        print(await page.evaluate("""
        () => ({
            webdriver: navigator.webdriver,
            platform: navigator.platform,
            language: navigator.language,
            languages: navigator.languages,
            hardwareConcurrency: navigator.hardwareConcurrency,
        })
        """))

        print("Browser version:", context.browser.version)

        page.on(
            "request",
            lambda request: print(">>", request.method, request.url)
        )

        page.on(
            "response",
            lambda response: print("<<", response.status, response.url)
        )

        global SEARCH_QUERY
        print(await context.cookies())
        response = await page.goto(
            "https://made-in-china.com",
            wait_until="domcontentloaded",
            timeout=90000
        )
        print("Status:", response.status if response else None)
        if response:
            print(response.headers)


        cookies = await context.cookies()
        print(f"ThomasNet cookies: {len(cookies)}")

        for c in cookies:
            print(c["name"], c["value"][:20], c["domain"])

        #await human_delay()
        #await human_mouse(page)
        #await random_scroll(page)
        print(f"Page title: {await page.title()}")
       
        
        input("Press Enter to continue after the search results page has loaded...")

        

if __name__ == "__main__":
    asyncio.run(main())