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

def generate
