from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, PicklePersistence
from datetime import datetime, timedelta
import os
import schedule
import time
import re
import csv
import requests
import threading
import asyncio
from config import location, TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN  # Adjust this import according to your structure
from book_test import scrape_booking_prices_playwright  # Updated import

from flask import Flask
from threading import Thread

app = Flask(__name__)

# Define a simple route for monitoring
@app.route('/')
def home():
    return "Telegram Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8443)

# States for the conversation handler
WAITING_FOR_DATETIME, WAITING_FOR_DAYS = range(2)

# Global variables
schedule_time = None
days = None

# Function to start the bot and prompt the user for input
async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Добро пожаловать! \n\nПожалуйста, введите дату и время для планирования в формате 'YYYY-MM-DD HH:MM'.\n\n\n Внимание!!! Для 8 отелей на 90 дней программа займет + -4 часа, Планируйте с умом =)\n\n")
    return WAITING_FOR_DATETIME

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
            # Call the function to schedule the job in the main script
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
    schedule.every().day.at(target_datetime.strftime("%H:%M")).do(lambda: threading.Thread(target=asyncio.run, args=(job(location, checkin_dates),)).start())

    # Keep the script running in the background
    print(f"Задание запланировано на {target_datetime}")
    while True:
        schedule.run_pending()
        time.sleep(1)

# Main job function (unchanged)
async def job(location, checkin_dates):
    print(f"Задание началось в {datetime.now()}")
    # Call the scraping function and process data
    prices_data = await scrape_booking_prices_playwright(location, checkin_dates)
    
    for hotel_name, prices in prices_data.items():
        print(f"Обработка отеля: {hotel_name}")
        sanitized_hotel_name = re.sub(r"[^\w\s]", "", hotel_name).replace(" ", "_")
        output_file = f"{sanitized_hotel_name}.csv"
        
        with open(output_file, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Price"])
            writer.writerows(prices)

        send_telegram_message(output_file, hotel_name)

        if os.path.exists(output_file):
            os.remove(output_file)

    print(f"Задание завершено в {datetime.now()}")
    # Automatically restart the bot to allow new scheduling
    print("Бот возвращается к состоянию ожидания команды /start.")
    os.system("python bot_book_scrape.py")  # Restart the script

# Function to send a CSV file via Telegram
def send_telegram_message(file_path, hotel_name):
    try:
        with open(file_path, "rb") as file:
            response = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"Цены для {hotel_name}.\n Обновлено {datetime.now().strftime('%Y-%m-%d %H:%M')}"}, 
                files={"document": file},
            )
        if response.status_code == 200:
            print(f"Файл {file_path} успешно отправлен в Telegram.")
        else:
            print(f"Не удалось отправить файл. Код статуса: {response.status_code}, Ответ: {response.text}")
    except Exception as e:
        print(f"Не удалось отправить файл: {e}")

# Set up the bot with the conversation handler
persistence = PicklePersistence("bot_data")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).build()

conversation_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        WAITING_FOR_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_datetime)],
        WAITING_FOR_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_days)],
    },
    fallbacks=[CommandHandler("start", start)],
)

application.add_handler(conversation_handler)
application.run_polling()

# Add Flask as a separate thread to avoid blocking the bot
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    application.run_polling()