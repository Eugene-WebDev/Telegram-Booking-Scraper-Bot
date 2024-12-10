from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, PicklePersistence
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

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    logging.info(f"Received webhook request: {json_str}")
    update = Update.de_json(json.loads(json_str), application.bot)
    asyncio.run(application.update_queue.put(update))  # Queue update for Telegram
    return 'ok', 200

# States for the conversation handler
WAITING_FOR_DATETIME, WAITING_FOR_DAYS = range(2)

# Global variables
schedule_time = None
days = None

# Function to start the bot and prompt the user for input
async def start(update: Update, context: CallbackContext) -> int:
    # Send a welcome message to the user
    await update.message.reply_text(
        "Добро пожаловать! \n\nПожалуйста, введите дату и время для планирования в формате 'YYYY-MM-DD HH:MM'.\n\n"
        "Внимание!!! Для 8 отелей на 90 дней программа займет + -4 часа. Планируйте с умом."
    )
    return WAITING_FOR_DATETIME  # Indicate that the bot is waiting for the date and time input

# Handler to get date and time from the user
async def get_datetime(update: Update, context: CallbackContext) -> int:
    global schedule_time
    user_input = update.message.text.strip()

    if not user_input:
        await update.message.reply_text("Вы не ввели дату и время. Пожалуйста, используйте формат 'YYYY-MM-DD HH:MM'.")
        return WAITING_FOR_DATETIME

    try:
        schedule_time = datetime.strptime(user_input, "%Y-%m-%d %H:%M")
        await update.message.reply_text(f"Дата и время установлены на {schedule_time}. Теперь выберите, на сколько дней нужно запланировать (нп, 7, 15, 30, 90).")
        return WAITING_FOR_DAYS
    except ValueError:
        await update.message.reply_text("Неверный формат. Пожалуйста, используйте формат 'YYYY-MM-DD HH:MM'.")
        return WAITING_FOR_DATETIME

# Handler to get the number of days from the user
async def get_days(update: Update, context: CallbackContext) -> int:
    global days
    user_input = update.message.text.strip()

    if not user_input:
        await update.message.reply_text("Вы не ввели значение. Пожалуйста, введите число для количества дней (нп. 3, 5, 7, 15, 30, 90).")
        return WAITING_FOR_DAYS

    try:
        user_input = int(user_input)
        if user_input > 0:  # Allow any positive number
            days = user_input
            await update.message.reply_text(f"Запланировано на {days} дней. Задание будет выполнено в {schedule_time}.")
            schedule_job(schedule_time, days)
            await update.message.reply_text("Задание успешно запланировано. Вы можете снова запланировать задание, отправив команду /start.")
            return ConversationHandler.END
        else:
            await update.message.reply_text("Неверный выбор. Пожалуйста, выберите 7, 15, 30 или 90 дней.")
            return WAITING_FOR_DAYS
    except ValueError:
        await update.message.reply_text("Неверный ввод. Пожалуйста, введите правильное число.")
        return WAITING_FOR_DAYS

# Function to schedule the job based on user input
def schedule_job(schedule_time, days):
    start_date = datetime.now()
    checkin_dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    # Schedule the job to run at the specified time
    target_datetime = schedule_time
    schedule.every().day.at(target_datetime.strftime("%H:%M")).do(lambda: asyncio.run(job(location, checkin_dates)))

    # Keep the script running in the background
    logging.info(f"Задание запланировано на {target_datetime}")
    while True:
        schedule.run_pending()
        time.sleep(1)

# Main job function
async def job(location, checkin_dates):
    logging.info(f"Задание началось в {datetime.now()}")
    prices_data = await scrape_booking_prices_playwright(location, checkin_dates)

    for hotel_name, prices in prices_data.items():
        logging.info(f"Обработка отеля: {hotel_name}")
        sanitized_hotel_name = re.sub(r"[^\w\s]", "", hotel_name).replace(" ", "_")
        output_file = f"hotel_prices_{sanitized_hotel_name}.csv"

        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Price"])
            writer.writerows(prices)

        send_telegram_message(output_file, hotel_name)

        if os.path.exists(output_file):
            os.remove(output_file)

    logging.info(f"Задание завершено в {datetime.now()}")

# Function to send a CSV file via Telegram
def send_telegram_message(file_path, hotel_name):
    try:
        with open(file_path, "rb") as file:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"Цены на отели для {hotel_name}. Обновлено {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                files={"document": file},
            )
        if response.status_code == 200:
            logging.info(f"Файл {file_path} успешно отправлен в Telegram.")
        else:
            logging.error(f"Не удалось отправить файл. Код статуса: {response.status_code}, Ответ: {response.text}")
    except Exception as e:
        logging.error(f"Не удалось отправить файл: {e}")

# Delete existing webhook before starting a new one
async def delete_webhook_async(bot):
    await bot.delete_webhook()

async def main():
    await delete_webhook_async(Bot(token=TELEGRAM_BOT_TOKEN))

asyncio.run(main())

# Set up the bot with the conversation handler
persistence = PicklePersistence("bot_data")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).read_timeout(60).build()

# Register handlers for the conversation
application.add_handler(CommandHandler("start", start))
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_FOR_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_datetime)],
        WAITING_FOR_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_days)]
    },
    fallbacks=[],
))

# Start the Flask app and webhook server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=443, debug=False)
