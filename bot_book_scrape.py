from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, PicklePersistence
from datetime import datetime, timedelta
import os
import schedule
import time
import re
import csv
import requests
from config import location, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN
from book_test import scrape_booking_prices_playwright
from flask import Flask, request
import json
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create a Flask application to handle webhook requests
app = Flask(__name__)

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json.loads(json_str), application.bot)
    asyncio.run(application.update_queue.put(update))  # Queue update for Telegram
    return 'ok', 200

# Delete existing webhook before starting a new one
async def delete_webhook_async(bot):
    await bot.delete_webhook()

async def main():
    await delete_webhook_async(Bot(token=TELEGRAM_BOT_TOKEN))

asyncio.run(main())

# Set up the bot with the conversation handler
persistence = PicklePersistence("bot_data")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).read_timeout(60).build()

# Flask app handles the webhook
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8085, debug=False)
