# Telegram Booking Scraper Bot

This project is a Telegram bot that allows users to schedule automated hotel price scraping from Booking.com using Playwright. The bot interacts with users via Telegram, enabling them to specify a date range for hotel price collection. Once the data is gathered, the bot sends a CSV report to the user.

**Features:**

**User Interaction via Telegram**

Start the bot using /start
Set a specific date and time for the scraping job
Select the number of days for price tracking (e.g., 7, 15, 30, 90 days)

**Automated Scraping with Playwright**

Uses headless Chromium with randomized user agents to avoid detection
Collects hotel prices for specified check-in dates
Implements concurrency control to optimize web requests

**Data Processing & Storage**

Extracted prices are saved in CSV files
File naming ensures easy tracking of hotel data
CSV reports are automatically sent via Telegram

**Scheduling & Execution**

Uses Python's schedule and asyncio for automated job execution
Keeps the bot running to schedule future scraping tasks

**File Breakdown**

**bot_book_scrape.py**
A Telegram bot script that handles user interactions.
Manages user inputs for date selection and scraping duration.
Schedules the web scraping job based on user input.
Triggers the scrape_booking_prices_playwright function from book_test.py.
Sends the scraped data back to the user via Telegram messages.

**book_test.py**
A web scraping script that fetches hotel prices from Booking.com.
Uses Playwright for automated browsing and data extraction.
Implements concurrent requests with a semaphore to avoid getting blocked.
Randomizes user agents to mimic human behavior.
Saves collected data into CSV files.

**Setup & Usage**

1. Install Dependencies
Ensure you have Python 3.9+ and install the required packages:

pip install -r requirements.txt
playwright install

2. Configure Environment
Modify config.py with:

Telegram Bot Token
Telegram Chat ID
Hotel names for scraping
Location details

3. Run the Telegram Bot
Start the bot and interact with it via Telegram:

python bot_book_scrape.py
