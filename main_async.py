#python code to run a headful browser using playwright (async version)
#this code semi automates the process of leads extraction from europages.co.uk
from playwright.async_api import async_playwright
import lib.pagebrowser as pagebrowser
import asyncio
import re


SEARCH_QUERY = "cnc machines"
ALL_PAGES = []
ALL_WEBSITES = []
ALL_EMAILS = []
CURRENT_PAGE = 1
BASE_URL = "https://europages.co.uk"  # Replace with the actual base URL of the site you want to scrape


#function to get company pages from the search results page
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

#function to process each company page and visit the website link if available
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
                    ALL_EMAILS.extend(emails)
                    print(f"Found emails: {emails}")
                    
            else:
                print("No website link found on this company page.")
        except Exception as e:
            continue  # skip to the next company page if there's an error
        finally:
            if page2:
                await page2.close()

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
        #page.pause()
        searchBox = page.locator("input[name='q']")
        print("Search box found...")
        # little delay to see the search box
        searchQuery = input(f"Enter search query (default: {SEARCH_QUERY}): ")
        if searchQuery.strip():
            SEARCH_QUERY = searchQuery.strip()
        await searchBox.fill(SEARCH_QUERY)
        await searchBox.press("Enter")
        await page.locator('div[data-test="company"]').first.wait_for()
        # check if accept cookies button is present and click it
        acceptCookiesButton = page.locator('div[id="cookiescript_accept"]')
        if await acceptCookiesButton.count() > 0:
            print("Accept cookies button found. Clicking it...")
            await acceptCookiesButton.first.click()
            await page.wait_for_timeout(1000)  # Wait for a second after clicking accept cookies

        while CURRENT_PAGE < 10:
            #check if the search results page has loaded correctly by checking the title of the page
            title = await page.title()
            if SEARCH_QUERY.lower() in title.lower():
                companyPages = await getCompanyPages(page)
                await processPages(context, companyPages)
                print(f"Finished processing page {CURRENT_PAGE}.")
                await scrollPage(page)
                #click the next page button
                nextPageLink = page.locator('a[data-test="pagination-next"]')
                if await nextPageLink.count() > 0:
                    await nextPageLink.first.click()
                    await page.locator('div[data-test="company"]').first.wait_for()
                    CURRENT_PAGE += 1
                else:
                    print("No more pages to process.")
                    break
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