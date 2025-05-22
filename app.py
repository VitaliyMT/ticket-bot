import os
import requests
from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

API_URL = "https://ticket-pdf-app.onrender.com/generate"
BOT_TOKEN = os.getenv("BOT_TOKEN")

FIELDS = [
    "Квиток №", "Номер замовлення", "№ Рейсу", "Рейс", "Час відправлення", "Дата відправлення",
    "Час прибуття", "Дата прибуття", "Станція відправлення", "Станція прибуття",
    "Місце", "Пасажир", "Ціна"
]

user_data = {}

def start(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    user_data[user_id] = {}
    context.user_data['step'] = 0
    update.message.reply_text(f"Введіть: {FIELDS[0]}")

def handle_input(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    step = context.user_data.get('step', 0)
    user_data[user_id][FIELDS[step]] = update.message.text

    if step + 1 < len(FIELDS):
        context.user_data['step'] = step + 1
        update.message.reply_text(f"Введіть: {FIELDS[step + 1]}")
    else:
        update.message.reply_text("⏳ Генеруємо квиток, зачекайте...")
        try:
            response = requests.post(API_URL, json=user_data[user_id])
            if response.status_code == 200:
                with open("ticket.pdf", "wb") as f:
                    f.write(response.content)
                update.message.reply_document(document=InputFile("ticket.pdf"))
            else:
                update.message.reply_text("❌ Помилка генерації PDF.")
        except Exception as e:
            update.message.reply_text(f"⚠️ Сталася помилка: {e}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_input))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
