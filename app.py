from flask import Flask
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import threading
import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
PDF_SERVER_URL = "https://ticket-pdf-app.onrender.com/generate"

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram bot is running"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Привіт! Надішли дані в 13 рядках...")

def handle_message(update: Update, context: CallbackContext):
    lines = update.message.text.strip().split('\n')
    if len(lines) != 13:
        update.message.reply_text("⚠️ Має бути 13 рядків")
        return
    fields = ["Квиток №", "Номер замовлення", "№ Рейсу", "Рейс", "Час відправлення", "Дата відправлення",
              "Час прибуття", "Дата прибуття", "Станція відправлення", "Станція прибуття", "Місце", "Пасажир", "Ціна"]
    data = dict(zip(fields, lines))
    try:
        r = requests.post(PDF_SERVER_URL, json=data)
        if r.status_code == 200:
            update.message.reply_document(document=r.content, filename=f"ticket_{data['Квиток №']}.pdf")
        else:
            update.message.reply_text(f"❌ PDF помилка: {r.status_code}")
    except Exception as e:
        update.message.reply_text(f"❌ Виняток: {e}")

def run_bot():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
