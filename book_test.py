import csv
import asyncio
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from config import hotel_names

# Pool of user-agents
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/116.0.1938.69 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
]

# Limit the number of concurrent pages
SEMAPHORE_LIMIT = 3  # Adjust this value based on your system's capability


async def scrape_hotel_prices(semaphore, context, hotel_name, checkin_dates):
    prices = []
    base_url = f"https://www.booking.com/hotel/pl/{hotel_name}.html"

    async with semaphore:
        page = await context.new_page()
        try:
            for date in checkin_dates:
                checkin_date = datetime.strptime(date, "%Y-%m-%d")
                checkout_date = checkin_date + timedelta(days=1)
                params = (
                    f"?checkin={checkin_date.strftime('%Y-%m-%d')}"
                    f"&checkout={checkout_date.strftime('%Y-%m-%d')}"
                    f"&group_adults=2&no_rooms=1&group_children=0"
                )
                full_url = base_url + params
                print(f"URL for {hotel_name} on {date}: {base_url}")

                try:
                    await page.goto(full_url, timeout=60000)
                    await page.wait_for_selector('span.prco-valign-middle-helper', timeout=20000)
                    price_element = await page.query_selector('span.prco-valign-middle-helper')
                    found_price = await price_element.inner_text() if price_element else "Not Available"
                    print(f"Price Found for {hotel_name} on {date}: {found_price}")
                    prices.append((date, found_price))
                except Exception as e:
                    print(f"Error scraping data for {hotel_name} on {date}: {e}")
                    prices.append((date, "Not Available"))

                await asyncio.sleep(random.uniform(4, 10))  # Add randomized delay to prevent blocking
        finally:
            await page.close()

    return hotel_name, prices


async def scrape_booking_prices_playwright(location, checkin_dates):
    prices_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

        user_agent = random.choice(USER_AGENTS)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1280, "height": 720},
        )

        semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
        tasks = [
            scrape_hotel_prices(semaphore, context, hotel_name, checkin_dates)
            for hotel_name in hotel_names
        ]

        results = await asyncio.gather(*tasks)
        for hotel_name, prices in results:
            prices_data[hotel_name] = prices

        await browser.close()

    # Save data to CSV
    csv_filename = f"{location}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Hotel Name", "Date", "Price"])
        for hotel_name, prices in prices_data.items():
            for date, price in prices:
                writer.writerow([hotel_name, date, price])

    print(f"Data saved to {csv_filename}")
    return prices_data

