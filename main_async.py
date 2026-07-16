#python code to run a headful browser using playwright (async version)
#this code semi automates the process of leads extraction from europages.co.uk
from playwright.async_api import async_playwright
from datetime import datetime
from lib.pagebrowser import POST_URL
import lib.pagebrowser as pagebrowser
from urllib.parse import urlparse, urlunparse
import asyncio
import requests


# -- Define global variables ---
SEARCH_QUERY = ""
ALL_PAGES = []
ALL_WEBSITES = []
ALL_EMAILS = []
CURRENT_PAGE = 1
FILENAME = ""
BASE_URL = "https://europages.co.uk"  # Replace with the actual base URL of the site you want to scrape

#function to create txt file and write the found emails to it
def save_emails_to_file(emails, filename="found_emails.txt", mode="a"):
    with open(filename, mode) as f:
        for email in emails:
            f.write(f"{email}\n")

# -- function to get company pages from the search results page --
async def getCompanyPages(page):
    # Implementation for getting company pages from the search results page
    links = page.locator("a.company-name-link")
    count = await links.count()
    print(f"Found {count} company links on the search results page.")
    company_links = []
    for i in range(count):
        href = await links.nth(i).get_attribute("href")
        #check if href is not None and not already in the list
        if href and href not in company_links and href not in ALL_PAGES:
            company_links.append(BASE_URL+href)
    ALL_PAGES.extend(company_links)
    return company_links

# -- function to push leads to the API endpoint --
def push_leads_to_api(leads, source):
    payload = {
        "leads": leads,
        "source": source,
        "keywords": SEARCH_QUERY
    }
    try:
        response = requests.post(POST_URL, json=payload)
        if response.status_code == 201:
            print(f"Successfully pushed {len(leads)} leads to the API.")
        else:
            print(f"Failed to push leads. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error occurred while pushing leads to the API: {e}")


# -- function to process each company page and visit the website link if available --
async def processPages(context, companyPages):
    for link in companyPages:
        page2 = None
        try:
            page2 = await context.new_page()
            await page2.goto(link)
            await page2.locator("div.vis-card").first.wait_for()
            print(f"Visiting company page: {link}")
            #check if the company page has a website link
            websiteLink = page2.locator("a.text-primary-120")
            if await websiteLink.count() > 0:
                websiteHref = await websiteLink.first.get_attribute("href")
                if websiteHref and websiteHref not in ALL_WEBSITES:
                    print(f"Found website link: {websiteHref}")
                    ALL_WEBSITES.append(websiteHref)
                    print("Visiting company website to extract emails...")
                    emails = await pagebrowser.ExtractEmailsFromPage(context, websiteHref)  # Open the company website link
                    if emails:
                        push_leads_to_api(emails, websiteHref)  # Push the found emails to the API
                        # Note: SEARCH_QUERY is used internally in push_leads_to_api
                        ALL_EMAILS.extend(emails)
                        save_emails_to_file(emails, FILENAME)  # Save the found emails to the file
                    print(f"Found emails: {emails}")
                    
            else:
                print("No website link found on this company page.")
        except Exception as e:
            continue  # skip to the next company page if there's an error
        finally:
            if page2:
                await page2.close()

# -- fuction to rewrite url to move the next page --
def gotoPage(current_url: str, page: int):
    parsed = urlparse(current_url)
    new_path = ""
    if CURRENT_PAGE == 1:
        new_path =  parsed.path.replace("/search", f"/search/page/{str(page)}")
    else:
        new_path = parsed.path.replace(f"/page/{str(CURRENT_PAGE)}", f"/page/{str(page)}")
    return urlunparse(parsed._replace(path=new_path))

# function to scroll the page dynamically until the next page button is found or a maximum number of scrolls is reached
async def scrollPage(page, scrolls=12):
    for _ in range(scrolls):
        await page.mouse.wheel(0, 1000)  # scroll down to load more results
        await page.wait_for_timeout(200)  # wait for 200ms to allow lazy loading
    await page.wait_for_timeout(500)  # give the observer + Vue reactivity a beat to fire
    await page.wait_for_selector('a[data-test="pagination-next"]', timeout=5000)

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



async def main():
    global CURRENT_PAGE
    global FILENAME
    async with async_playwright() as p:
        global SEARCH_QUERY
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,  # Slow down by 100ms to see the actions
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(BASE_URL)
        await page.wait_for_load_state("networkidle")
        print("Page title:", await page.title())
        print("Page URL:", page.url)
        
        # -- Wait till captcha is solved
        await page.wait_for_selector("body.cookiescript_overlay", timeout=60000)
        await page.wait_for_timeout(1000) # little delay

        # -- check if accept cookies button is present and click it
        acceptCookiesButton = page.locator('div[id="cookiescript_accept"]')
        if await acceptCookiesButton.count() > 0:
            print("Accept cookies button found. Clicking it...")
            await acceptCookiesButton.first.click()
            await page.wait_for_timeout(1000)  # Wait for a second after clicking accept cookies
        
        # -- Locate the search query input
        searchBox = page.locator('[name="q"]')
        searchQuery = input(f"Enter search query (default: {SEARCH_QUERY}): ")
        if searchQuery.strip():
            SEARCH_QUERY = searchQuery.strip()
        await searchBox.fill(SEARCH_QUERY)
        await searchBox.press("Enter")
        FILENAME = f"found_emails_{SEARCH_QUERY.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        await page.locator('div[data-test="company"]').first.wait_for(timeout=20000)
        # check if accept cookies button is present and click it
        acceptCookiesButton = page.locator('div[id="cookiescript_accept"]')
        if await acceptCookiesButton.count() > 0:
            print("Accept cookies button found. Clicking it...")
            await acceptCookiesButton.first.click()
            await page.wait_for_timeout(1000)  # Wait for a second after clicking accept cookies

        while CURRENT_PAGE < 101:
            #check if the search results page has loaded correctly by checking the title of the page
            title = await page.title()
            if SEARCH_QUERY.lower() in title.lower():
                companyPages = await getCompanyPages(page)
                await processPages(context, companyPages)
                print(f"Finished processing page {CURRENT_PAGE}.")
                await scrollPage(page)
                try:
                    #click the next page button
                    nextPageLink = page.locator('a[data-test="pagination-next"]')
                    if await nextPageLink.count() > 0:
                        await nextPageLink.first.click()
                        await page.locator('div[data-test="company"]').first.wait_for(timeout=20000)
                        CURRENT_PAGE += 1
                    else:
                        # -- Force url pagination --
                        nPage = CURRENT_PAGE + 1
                        print("forcing url pagination...")
                        nextPageLink = gotoPage(page.url, nPage)
                        print(nextPageLink)
                        await page.goto(nextPageLink)
                        await page.locator('div[data-test="company"]').first.wait_for(timeout=20000)
                        CURRENT_PAGE += 1
                        
                except Exception as e:
                    print("Pagination error, forcing url pagination...")
                    nPage = CURRENT_PAGE + 1
                    nextPageLink = gotoPage(page.url, nPage)
                    print(nextPageLink)
                    await page.goto(nextPageLink)
                    await page.locator('div[data-test="company"]').first.wait_for(timeout=20000)
                    CURRENT_PAGE += 1
            else:
                print("No results found or invalid page loaded.")
                break

        for website in ALL_WEBSITES:
            print(website)

        print(f"Found emails: {ALL_EMAILS}")

        await asyncio.to_thread(input, "Press Enter to close the browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())