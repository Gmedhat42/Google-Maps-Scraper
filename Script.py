from bs4 import BeautifulSoup
import asyncio
from pyppeteer import launch
import re
import csv
import logging
from datetime import datetime
from pyppeteer.errors import TimeoutError

chromium_path = r"C:\Users\gmedh\OneDrive\Documents\chrome-win\chrome-win\chrome.exe"

# Configure logging
logging.basicConfig(filename='scraping_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

async def patch_pyppeteer():
    return await launch(executablePath=chromium_path, headless=False)

def extract_lat_long(url):
    pattern = r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None, None

async def get_page_content(url, semaphore):
    async with semaphore:
        try:
            browser = await patch_pyppeteer()
            page = await browser.newPage()
            await page.goto(url)
            await page.setViewport({'width': 1280, 'height': 800})

            await page.waitForSelector('div[role="feed"]', timeout=20000)

            restaurants_processed = []

            while True:
                await page.evaluate('''
                    var feed = document.querySelector('div[role="feed"]');
                    if (feed) {
                        feed.scrollTop = feed.scrollHeight;
                    }
                ''')
                await asyncio.sleep(2)

                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                restaurant_containers = soup.find_all('div', class_='Nv2PK THOPZb CpccDe')

                if not restaurant_containers:
                    break

                new_restaurants_found = False

                for container in restaurant_containers:
                    name = container.find('div', class_='qBF1Pd fontHeadlineSmall')
                    if name:
                        star_rating = container.find('span', class_='MW4etd')
                        reviews_count = container.find('span', class_='UY7F9')
                        link = container.find('a', class_='hfpxzc')

                        if name and star_rating and reviews_count and link:
                            name_text = name.get_text(strip=True)
                            star_rating_text = star_rating.get_text(strip=True)
                            reviews_count_text = reviews_count.get_text(strip=True).strip('()')
                            link_url = link['href']
                            
                            lat, lon = extract_lat_long(link_url)
                            if lat and lon:
                                restaurant_info = {
                                    "Name": name_text,
                                    "Star Rating": star_rating_text,
                                    "Reviews Count": reviews_count_text,
                                    "URL": link_url,
                                    "Latitude": lat,
                                    "Longitude": lon
                                }
                                if restaurant_info not in restaurants_processed:
                                    restaurants_processed.append(restaurant_info)
                                    new_restaurants_found = True
                                    logging.info(f"Collected: {restaurant_info}")

                if not new_restaurants_found:
                    break

            await browser.close()
            return restaurants_processed

        except TimeoutError as e:
            logging.error(f"TimeoutError in get_page_content: {e}")
            return []
        except Exception as e:
            logging.error(f"Error in get_page_content: {e}")
            return []

async def save_to_csv(restaurants):
    if restaurants:
        keys = restaurants[0].keys()
        try:
            with open('restaurants_data.csv', 'a', newline='', encoding='utf-8') as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writerows(restaurants)
            logging.info(f"Saved {len(restaurants)} records to CSV.")
        except Exception as e:
            logging.error(f"Error saving to CSV: {e}")

async def fetch_and_save(url, semaphore):
    restaurants = await get_page_content(url, semaphore)
    await save_to_csv(restaurants)
    return restaurants

async def main():
    districts = input("Enter the district names (comma-separated): ").split(',')
    districts = [d.strip() for d in districts]
    
    search_queries = [
        "Restaurants", "cafés", "Italian Restaurant", "Dessert", "Japanese Restaurant",
        "Sushi Restaurant", "Asian Restaurant", "Western restaurant", "Fast Food", "Seafood",
        "Chicken restaurant", "Syrian restaurant", "Shawarma", "Burger", "Bakery", "Coffee shop",
        "Oriental restaurant", "Koshary", "Food Trucks"
    ]

    zoom_levels = ["11z","13z", "14z", "15z"]
    price_filters = ["0","2", "3", "4"]
    hours_filter = ["", "1"]

    all_restaurants = []

    with open('restaurants_data.csv', 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=["Name", "Star Rating", "Reviews Count", "URL", "Latitude", "Longitude"])
        dict_writer.writeheader()

    semaphore = asyncio.Semaphore(8)  # Max 10 concurrent requests
    tasks = []

    for district in districts:
        for query in search_queries:
            encoded_query = f"{query} {district}".replace(" ", "+")
            for zoom in zoom_levels:
                for price in price_filters:
                    for hours in hours_filter:
                        url = f"https://www.google.com/maps/search/{encoded_query}/@29.8373953,31.2317992,{zoom}/data=!3m1!4b1!4m5!2m4!5m3!5m2!1s2023-05-26!2i3!6e5!3s0x0%3A0x0?entry=ttu"
                        
                        if price != "0":
                            url += f"&price={price}"
                        
                        if hours == "1":
                            url += "&opennow=1&hour=0000"
                        
                        logging.info(f"Scraping: {query} in {district} (Zoom: {zoom}, Price: {price}, 24h: {hours == '1'})")
                        tasks.append(fetch_and_save(url, semaphore))

    results = await asyncio.gather(*tasks)

    all_restaurants = [item for sublist in results for item in sublist]

    logging.info(f"\nTotal unique restaurants found: {len(all_restaurants)}")

asyncio.get_event_loop().run_until_complete(main())
