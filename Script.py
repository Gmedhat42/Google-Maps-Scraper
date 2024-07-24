import requests
import os
import asyncio
from bs4 import BeautifulSoup
from requests_html import HTMLSession, AsyncHTMLSession
from pyppeteer import launch

url = 'https://www.google.com/maps/search/Restaurants+new+cairo/@29.8373953,31.2317992,11z/data=!3m1!4b1?entry=ttu'

os.environ['PYPPETEER_EXECUTABLE_PATH'] = r"C:\Users\gmedh\OneDrive\Documents\chrome-win\chrome-win\chrome.exe"

async def main():
    browser = await launch(executablePath=r"C:\Users\gmedh\OneDrive\Documents\chrome-win\chrome-win\chrome.exe")
    page = await browser.newPage()
    
    await page.goto(url, waitUntil='networkidle0')
    
    content = await page.content()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Prettify the HTML
    pretty_html = soup.prettify()
    
    print(pretty_html)
    
    # If you still want to find specific elements, you can do so like this:
    restaurant_containers = soup.find_all('div', class_='Nv2PK')
    for container in restaurant_containers:
        print(container.prettify())
        print("\n" + "-"*50 + "\n")  # Separator between restaurants
    
    await browser.close()

asyncio.get_event_loop().run_until_complete(main())