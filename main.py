#python code to run a headful browser using playwright
#this code semi automates the process of extraction from europages only.
from playwright.sync_api import sync_playwright
import asyncio
import re


SEARCH_QUERY = "cnc machines"
ALL_PAGES = []
ALL_WEBSITES = []
CURRENT_PAGE = 1
BASE_URL = "https://europages.co.uk"
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
CF_RE = re.compile(r'data-cfemail="([a-f0-9]+)"')

#function to get company pages from the search results page
def getCompanyPages(page):
    # Implementation for getting company pages from the search results page
    links = page.locator("a.company-name-link")
    print(f"Found {links.count()} company links on the search results page.")
    company_links = []
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        #check if href is not None and not already in the list
        if href and href not in company_links and href not in ALL_PAGES:
            company_links.append(BASE_URL+href)
    ALL_PAGES.extend(company_links)
    return company_links

#function to process each company page and visit the website link if available
def processPages(context, companyPages):
    for link in companyPages:
        try:
            page2 = context.new_page()
            page2.goto(link)
            page2.locator("div.vis-card").first.wait_for()
            print(f"Visiting company page: {link}")
            #check if the company page has a website link
            websiteLink = page2.locator("a.text-primary-120")
            if websiteLink.count() > 0:
                websiteHref = websiteLink.first.get_attribute("href")
                if websiteHref and websiteHref not in ALL_WEBSITES:
                    ALL_WEBSITES.append(websiteHref)
                    print(f"Found website link: {websiteHref}")
            else:
                print("No website link found on this company page.")
            page2.close()
        except Exception as e:
            continue  # skip to the next company page if there's an error

# function to scroll the page dynamically until the next page button is found or a maximum number of scrolls is reached
def scrollPage(page, scrolls=12):
    for _ in range(scrolls):
        page.mouse.wheel(0, 1000)  # scroll down to load more results
        page.wait_for_timeout(200)  # wait for 200ms to allow lazy loading
    page.wait_for_timeout(500)  # give the observer + Vue reactivity a beat to fire
    page.wait_for_selector('a[data-test="pagination-next"]', timeout=5000)

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

# function to extract email addresses from a given text using regex
def extractEmails(text):
    found = EMAIL_RE.findall(text)
    seen = set()
    unique_emails = []
    for email in found:
        if email not in seen:
            key = email.lower()  # Use lowercase for case-insensitive comparison
            if key not in seen:
                seen.add(key)
                unique_emails.append(email)
    return unique_emails

#def function to decode Cloudflare email protection
def decodeCloudflareEmail(encoded):
    r = int(encoded[:2], 16)
    return ''.join(chr(int(encoded[i:i+2], 16) ^ r) for i in range(2, len(encoded), 2))

# function to extract cloudflare protected emails from a given text using regex
def extractCloudflareEmails(text):
    return [decodeCloudflareEmail(match) for match in CF_RE.findall(text)]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        slow_mo=100,  # Slow down by 100ms to see the actions
    )
    context = browser.new_context()
    page = context.new_page()
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    print("Page title:", page.title())
    print("Page URL:", page.url)
    #page.pause()
    searchBox = page.locator("input[name='q']")
    print("Search box found...")
    # little delay to see the search box
    page.wait_for_timeout(10000)
    searchBox.fill(SEARCH_QUERY)
    searchBox.press("Enter")
    page.locator('div[data-test="company"]').first.wait_for()
    # check if accept cookies button is present and click it
    acceptCookiesButton = page.locator('div[id="cookiescript_accept"]')
    if acceptCookiesButton.count() > 0:
        print("Accept cookies button found. Clicking it...")
        acceptCookiesButton.first.click()
        page.wait_for_timeout(1000)  # Wait for a second after clicking accept cookies

    while CURRENT_PAGE < 10:
        #check if the search results page has loaded correctly by checking the title of the page
        if SEARCH_QUERY.lower() in page.title().lower():
            companyPages = getCompanyPages(page)
            processPages(context, companyPages)
            print(f"Finished processing page {CURRENT_PAGE}.")
            scrollPage(page)
            #click the next page button
            nextPageLink = page.locator('a[data-test="pagination-next"]')
            if nextPageLink.count() > 0:
                nextPageLink.first.click()
                page.locator('div[data-test="company"]').first.wait_for()
                CURRENT_PAGE += 1
            else:
                print("No more pages to process.")
                break
        else:
            print("No results found or invalid page loaded.")
            break
    for website in ALL_WEBSITES:
        print(website)

    input("Press Enter to close the browser...")
    browser.close()

