import os
import io
import logging
from flask import Flask
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
import qrcode

# === Налаштування ===
TOKEN = os.getenv("BOT_TOKEN")
PDF_HEIGHT_MM = 297
TEMPLATE_PATH = "приклад.pdf"
FONT_REGULAR = "DejaVuSans.ttf"
FONT_BOLD = "DejaVuSans-Bold.ttf"

pdfmetrics.registerFont(TTFont("DejaVu", FONT_REGULAR))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", FONT_BOLD))

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

# === Стани ===
(
    STEP_TICKET_NO, STEP_ORDER_NO, STEP_RACE_NO, STEP_RACE_NAME,
    STEP_DEPARTURE_TIME, STEP_DEPARTURE_DATE,
    STEP_ARRIVAL_TIME, STEP_ARRIVAL_DATE,
    STEP_FROM, STEP_TO, STEP_SEAT, STEP_PASSENGER, STEP_PRICE
) = range(13)

user_data = {}

# === Генерація PDF ===
def draw_text_left(c, x_mm, y_mm_top_origin, text, size=10.8, bold=False):
    y_mm = PDF_HEIGHT_MM - y_mm_top_origin
    x_pt = x_mm * mm
    y_pt = y_mm * mm
    font_name = "DejaVu-Bold" if bold else "DejaVu"
    c.setFont(font_name, size)
    c.drawString(x_pt, y_pt - 1, text)

def draw_centered_text(c, x_mm, y_mm_top_origin, text, size=10.8, bold=False):
    y_mm = PDF_HEIGHT_MM - y_mm_top_origin
    x_pt = x_mm * mm
    y_pt = y_mm * mm
    font_name = "DejaVu-Bold" if bold else "DejaVu"
    c.setFont(font_name, size)
    text_width = c.stringWidth(text, font_name, size)
    c.drawString(x_pt - text_width / 2, y_pt - 1, text)

def generate_pdf(data):
    overlay_path = "_overlay_temp.pdf"
    c = canvas.Canvas(overlay_path, pagesize=A4)

    c.setFillColorRGB(1, 1, 1)
    c.rect(156.79 * mm - 1.5 * mm, (PDF_HEIGHT_MM - 49.63) * mm - 1.5 * mm, 3 * mm, 3 * mm, fill=True, stroke=False)
    c.rect(156.79 * mm - 1.5 * mm, (PDF_HEIGHT_MM - 50.94) * mm - 1.5 * mm, 3 * mm, 3 * mm, fill=True, stroke=False)

    coords = {
        "№ Рейсу": (53.75, 50.81, True),
        "Рейс": (82.31, 49.29, True),
        "Станція відправлення": (90.56, 62.67, True),
        "Станція прибуття": (89.50, 72.83, True),
        "Час відправлення": (156.58, 49.97, True),
        "Дата відправлення": (157.22, 55.89, False),
        "Час прибуття": (186.63, 49.75, True),
        "Дата прибуття": (186.42, 55.47, False),
        "Ціна": (177.32, 87.79, True),
        "Місце": (97.55, 86.38, True)
    }

    for key, (x, y, bold) in coords.items():
        draw_centered_text(c, x, y, data[key], size=10.8, bold=bold)

    draw_text_left(c, 13.25, 86.8, data["Пасажир"], size=10.8, bold=True)
    draw_text_left(c, 59, 13.25, data["Номер замовлення"], size=10.8, bold=True)
    draw_text_left(c, 105, 38.03, data["Квиток №"], size=10.8, bold=True)

    qr = qrcode.QRCode(version=1, box_size=5, border=1)
    qr.add_data(data["Квиток №"])
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    qr_img = ImageReader(buf)
    qr_x_pt = 27.72 * mm - 15 * mm
    qr_y_pt = (PDF_HEIGHT_MM - 54.2) * mm - 15 * mm
    c.drawImage(qr_img, qr_x_pt, qr_y_pt, 30 * mm, 30 * mm)

    c.save()

    base = PdfReader(TEMPLATE_PATH)
    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output

# === Обробники ===
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Введіть номер квитка:")
    return STEP_TICKET_NO

def step_handler(update: Update, context: CallbackContext):
    text = update.message.text
    step = context.user_data.get("step", STEP_TICKET_NO)
    user_data = context.user_data

    steps = [
        (STEP_TICKET_NO, "Квиток №", STEP_ORDER_NO, "Введіть номер замовлення:"),
        (STEP_ORDER_NO, "Номер замовлення", STEP_RACE_NO, "Введіть № рейсу:"),
        (STEP_RACE_NO, "№ Рейсу", STEP_RACE_NAME, "Введіть найменування рейсу:"),
        (STEP_RACE_NAME, "Рейс", STEP_DEPARTURE_TIME, "Введіть час відправлення:"),
        (STEP_DEPARTURE_TIME, "Час відправлення", STEP_DEPARTURE_DATE, "Введіть дату відправлення:"),
        (STEP_DEPARTURE_DATE, "Дата відправлення", STEP_ARRIVAL_TIME, "Введіть час прибуття:"),
        (STEP_ARRIVAL_TIME, "Час прибуття", STEP_ARRIVAL_DATE, "Введіть дату прибуття:"),
        (STEP_ARRIVAL_DATE, "Дата прибуття", STEP_FROM, "Станція відправлення:"),
        (STEP_FROM, "Станція відправлення", STEP_TO, "Станція прибуття:"),
        (STEP_TO, "Станція прибуття", STEP_SEAT, "Введіть № місця:"),
        (STEP_SEAT, "Місце", STEP_PASSENGER, "Введіть ПІБ пасажира:"),
        (STEP_PASSENGER, "Пасажир", STEP_PRICE, "Введіть ціну:"),
        (STEP_PRICE, "Ціна", -1, None)
    ]

    for s in steps:
        if step == s[0]:
            user_data[s[1]] = text
            if s[2] == -1:
                try:
                    pdf = generate_pdf(user_data)
                    update.message.reply_document(document=pdf, filename="ticket.pdf")
                    return ConversationHandler.END
                except Exception as e:
                    update.message.reply_text("❌ Помилка створення квитка")
                    return ConversationHandler.END
            else:
                update.message.reply_text(s[3])
                user_data["step"] = s[2]
                return s[2]

    update.message.reply_text("❌ Невідомий стан")
    return ConversationHandler.END

# === Flask + Bot ===
@app.route('/')
def index():
    return "Flask is alive"

def run_bot():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STEP_TICKET_NO: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_ORDER_NO: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_RACE_NO: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_RACE_NAME: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_DEPARTURE_TIME: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_DEPARTURE_DATE: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_ARRIVAL_TIME: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_ARRIVAL_DATE: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_FROM: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_TO: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_SEAT: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_PASSENGER: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
            STEP_PRICE: [MessageHandler(Filters.text & ~Filters.command, step_handler)],
        },
        fallbacks=[]
    )
    dp.add_handler(conv)
    updater.start_polling()

if __name__ == '__main__':
    import threading
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
