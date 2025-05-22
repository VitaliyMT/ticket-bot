import os
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter
import qrcode
import io

BOT_TOKEN = os.environ.get("BOT_TOKEN")
app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

PDF_HEIGHT_MM = 297


def draw_text_left(c, x_mm, y_mm_top_origin, text, size=10.8, bold=False):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "DejaVuSans-Bold.ttf"))
    y_mm = PDF_HEIGHT_MM - y_mm_top_origin
    x_pt = x_mm * mm
    y_pt = y_mm * mm
    font_name = "DejaVu-Bold" if bold else "DejaVu"
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, size)
    c.drawString(x_pt, y_pt - 1, text)


def draw_centered_text(c, x_mm, y_mm_top_origin, text, size=10.8, bold=False):
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVu", "DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "DejaVuSans-Bold.ttf"))
    y_mm = PDF_HEIGHT_MM - y_mm_top_origin
    x_pt = x_mm * mm
    y_pt = y_mm * mm
    font_name = "DejaVu-Bold" if bold else "DejaVu"
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, size)
    text_width = c.stringWidth(text, font_name, size)
    c.drawString(x_pt - text_width / 2, y_pt - 1, text)


def generate_ticket(data, template_path, output_path):
    overlay_path = "_overlay_temp.pdf"
    c = canvas.Canvas(overlay_path, pagesize=A4)

    # Очистка шаблонних крапок
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

    base = PdfReader(template_path)
    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


# === Telegram Bot Handlers ===
def start(update, context):
    update.message.reply_text("Введіть номер квитка:")
    context.user_data["step"] = "ticket_id"


def handle_message(update, context):
    step = context.user_data.get("step")
    text = update.message.text

    if step == "ticket_id":
        context.user_data["Квиток №"] = text
        update.message.reply_text("Введіть номер замовлення:")
        context.user_data["step"] = "order_id"

    elif step == "order_id":
        context.user_data["Номер замовлення"] = text
        update.message.reply_text("Введіть № Рейсу:")
        context.user_data["step"] = "№ Рейсу"

    elif step in ["№ Рейсу", "Рейс", "Час відправлення", "Дата відправлення", "Час прибуття",
                  "Дата прибуття", "Станція відправлення", "Станція прибуття", "Місце", "Пасажир", "Ціна"]:
        context.user_data[step] = text
        next_steps = ["Рейс", "Час відправлення", "Дата відправлення", "Час прибуття",
                      "Дата прибуття", "Станція відправлення", "Станція прибуття", "Місце", "Пасажир", "Ціна"]
        next_index = next_steps.index(step) + 1 if step in next_steps else 0
        if next_index < len(next_steps):
            next_step = next_steps[next_index]
            update.message.reply_text(f"Введіть {next_step}:")
            context.user_data["step"] = next_step
        else:
            update.message.reply_text("Генеруємо PDF...")
            try:
                data = context.user_data
                output_path = f"ticket_{data['Квиток №']}.pdf"
                generate_ticket(data, "приклад.pdf", output_path)
                with open(output_path, "rb") as f:
                    update.message.reply_document(f)
            except Exception as e:
                update.message.reply_text(f"❌ Помилка: {e}")


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.before_first_request
def set_webhook():
    url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"
    bot.set_webhook(url)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
