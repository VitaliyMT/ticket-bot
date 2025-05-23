import os
import io
import qrcode
import tempfile
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, Bot
from telegram.ext import (
    Dispatcher, CommandHandler, MessageHandler, Filters,
    ConversationHandler, CallbackContext
)
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# --- Telegram токен ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВ_ТУТ_СВІЙ_ТОКЕН")

# --- Flask ---
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)

pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", "DejaVuSans-Bold.ttf"))

# --- Стан ---
(
    TICKET_NUM, ORDER_NUM, TRIP_NUM, ROUTE, DEPART_TIME, DEPART_DATE,
    ARR_TIME, ARR_DATE, FROM_ST, TO_ST, SEAT, PASSENGER, PRICE
) = range(13)

# --- Діалогові функції ---
def start(update: Update, context: CallbackContext):
    context.user_data.clear()
    update.message.reply_text("Введіть номер квитка:")
    return TICKET_NUM

def ask_next(update: Update, context: CallbackContext, key, next_state, prompt):
    context.user_data[key] = update.message.text.strip()
    update.message.reply_text(prompt)
    return next_state

def ask_order_num(update, context): return ask_next(update, context, "Квиток №", ORDER_NUM, "Введіть номер замовлення:")
def ask_trip_num(update, context): return ask_next(update, context, "Номер замовлення", TRIP_NUM, "Введіть № рейсу:")
def ask_route(update, context): return ask_next(update, context, "№ Рейсу", ROUTE, "Введіть найменування рейсу:")
def ask_depart_time(update, context): return ask_next(update, context, "Рейс", DEPART_TIME, "Введіть час відправлення:")
def ask_depart_date(update, context): return ask_next(update, context, "Час відправлення", DEPART_DATE, "Введіть дату відправлення:")
def ask_arr_time(update, context): return ask_next(update, context, "Дата відправлення", ARR_TIME, "Введіть час прибуття:")
def ask_arr_date(update, context): return ask_next(update, context, "Час прибуття", ARR_DATE, "Введіть дату прибуття:")
def ask_from_st(update, context): return ask_next(update, context, "Дата прибуття", FROM_ST, "Введіть станцію відправлення:")
def ask_to_st(update, context): return ask_next(update, context, "Станція відправлення", TO_ST, "Введіть станцію прибуття:")
def ask_seat(update, context): return ask_next(update, context, "Станція прибуття", SEAT, "Введіть № місця:")
def ask_passenger(update, context): return ask_next(update, context, "Місце", PASSENGER, "Введіть ім’я пасажира:")
def ask_price(update, context): return ask_next(update, context, "Пасажир", PRICE, "Введіть ціну квитка:")

def generate_and_send(update: Update, context: CallbackContext):
    context.user_data["Ціна"] = update.message.text.strip()

    ticket_number = context.user_data["Квиток №"]
    template_path = "приклад.pdf"
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name

    generate_ticket(context.user_data, template_path, tmp_path)

    with open(tmp_path, "rb") as f:
        update.message.reply_document(f, filename=f"ticket_{ticket_number}.pdf")

    os.remove(tmp_path)

    keyboard = [['🎫 Створити наступний квиток']]
    update.message.reply_text("✅ Квиток створено! Створити новий?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ConversationHandler.END

def handle_next_ticket(update: Update, context: CallbackContext):
    return start(update, context)

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("❌ Скасовано.")
    return ConversationHandler.END

# --- PDF генератор ---
def generate_ticket(data, template_path, output_path):
    PDF_HEIGHT_MM = 297
    overlay_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    c = canvas.Canvas(overlay_path, pagesize=A4)

    def draw_centered_text(x_mm, y_mm, text, bold=False):
        y_pt = (PDF_HEIGHT_MM - y_mm) * mm
        x_pt = x_mm * mm
        font = "DejaVu-Bold" if bold else "DejaVu"
        c.setFont(font, 10.8)
        width = c.stringWidth(text, font, 10.8)
        c.drawString(x_pt - width / 2, y_pt - 1, text)

    def draw_left_text(x_mm, y_mm, text, bold=False):
        y_pt = (PDF_HEIGHT_MM - y_mm) * mm
        x_pt = x_mm * mm
        font = "DejaVu-Bold" if bold else "DejaVu"
        c.setFont(font, 10.8)
        c.drawString(x_pt, y_pt - 1, text)

    coords = {
        "№ Рейсу": (53.75, 50.81, True),
        "Рейс": (82.31, 49.29, True),
        "Станція відправлення": (90.56, 62.67, True),
        "Станція прибуття": (89.50, 72.83, True),
        "Час відправлення": (156.58, 49.97, True),
        "Дата відправлення": (157.22, 55.89, False),
        "Час прибуття": (186.63, 49.75, True),
        "Дата прибуття": (186.42, 55.47, False),
        "Ціна": (177.32, 88.52, True),
        "Місце": (97.55, 86.38, True),
    }

    for key, (x, y, bold) in coords.items():
        draw_centered_text(x, y, data[key], bold=bold)

    draw_left_text(13.25, 86.8, data["Пасажир"], bold=True)
    draw_left_text(59.70, 13.66, data["Номер замовлення"], bold=True)
    draw_left_text(105.70, 38.83, data["Квиток №"], bold=True)

    qr = qrcode.make(data["Квиток №"])
    buf = io.BytesIO()
    qr.save(buf)
    buf.seek(0)
    qr_img = ImageReader(buf)
    qr_x = 27.72 * mm - 15 * mm
    qr_y = (PDF_HEIGHT_MM - 54.2) * mm - 15 * mm
    c.drawImage(qr_img, qr_x, qr_y, 30 * mm, 30 * mm)

    c.setFillColorRGB(1, 1, 1)
    c.rect(156.79 * mm - 1.5 * mm, (PDF_HEIGHT_MM - 49.63) * mm - 1.5 * mm, 3 * mm, 3 * mm, fill=True, stroke=False)
    c.rect(156.79 * mm - 1.5 * mm, (PDF_HEIGHT_MM - 50.94) * mm - 1.5 * mm, 3 * mm, 3 * mm, fill=True, stroke=False)

    c.save()

    base = PdfReader(template_path)
    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    os.remove(overlay_path)

# --- Telegram Dispatcher ---
from telegram.ext import Dispatcher

dispatcher = Dispatcher(bot, None, use_context=True)

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TICKET_NUM: [MessageHandler(Filters.text & ~Filters.command, ask_order_num)],
        ORDER_NUM: [MessageHandler(Filters.text & ~Filters.command, ask_trip_num)],
        TRIP_NUM: [MessageHandler(Filters.text & ~Filters.command, ask_route)],
        ROUTE: [MessageHandler(Filters.text & ~Filters.command, ask_depart_time)],
        DEPART_TIME: [MessageHandler(Filters.text & ~Filters.command, ask_depart_date)],
        DEPART_DATE: [MessageHandler(Filters.text & ~Filters.command, ask_arr_time)],
        ARR_TIME: [MessageHandler(Filters.text & ~Filters.command, ask_arr_date)],
        ARR_DATE: [MessageHandler(Filters.text & ~Filters.command, ask_from_st)],
        FROM_ST: [MessageHandler(Filters.text & ~Filters.command, ask_to_st)],
        TO_ST: [MessageHandler(Filters.text & ~Filters.command, ask_seat)],
        SEAT: [MessageHandler(Filters.text & ~Filters.command, ask_passenger)],
        PASSENGER: [MessageHandler(Filters.text & ~Filters.command, ask_price)],
        PRICE: [MessageHandler(Filters.text & ~Filters.command, generate_and_send)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
dispatcher.add_handler(conv_handler)
dispatcher.add_handler(MessageHandler(Filters.text("🎫 Створити наступний квиток"), handle_next_ticket))

# --- Webhook endpoint ---
@app.route(f'/{BOT_TOKEN}', methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

@app.route('/')
def index():
    return "Flask is alive"

# --- Головний запуск ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
