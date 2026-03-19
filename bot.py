import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # например, https://myapp.onrender.com
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Настройка бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Настройка базы данных
conn = sqlite3.connect("cars.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS cars(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER,
    work_type TEXT,
    cost REAL,
    date TEXT
)
""")
conn.commit()

# --- Меню ---
def main_menu(user_id):
    cursor.execute("SELECT id, name FROM cars WHERE user_id=?", (user_id,))
    cars = cursor.fetchall()
    kb = InlineKeyboardMarkup()
    for car_id, name in cars:
        kb.add(InlineKeyboardButton(name, callback_data=f"car_{car_id}"))
    kb.add(InlineKeyboardButton("Добавить машину", callback_data="add_car"))
    return kb

def car_menu(car_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Добавить запись", callback_data=f"add_record_{car_id}"))
    kb.add(InlineKeyboardButton("Просмотреть записи", callback_data=f"view_records_{car_id}"))
    kb.add(InlineKeyboardButton("Назад", callback_data="back_main"))
    return kb

# --- Хендлеры ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Привет! Выбери машину:", reply_markup=main_menu(msg.from_user.id))

@dp.callback_query_handler(lambda c: c.data.startswith("car_"))
async def select_car(cb: types.CallbackQuery):
    car_id = int(cb.data.split("_")[1])
    await cb.message.edit_text("Меню машины:", reply_markup=car_menu(car_id))

@dp.callback_query_handler(lambda c: c.data=="add_car")
async def add_car(cb: types.CallbackQuery):
    await cb.message.answer("Введите название машины:")
    dp.register_message_handler(process_car_name, state=None, chat_id=cb.from_user.id)

async def process_car_name(msg: types.Message):
    cursor.execute("INSERT INTO cars(user_id, name) VALUES(?,?)", (msg.from_user.id, msg.text))
    conn.commit()
    await msg.answer("Машина добавлена!", reply_markup=main_menu(msg.from_user.id))

@dp.callback_query_handler(lambda c: c.data.startswith("add_record_"))
async def add_record(cb: types.CallbackQuery):
    car_id = int(cb.data.split("_")[2])
    await cb.message.answer("Введите тип работы:")
    dp.register_message_handler(lambda m: process_work_type(m, car_id), state=None)

async def process_work_type(msg: types.Message, car_id):
    work_type = msg.text
    await msg.answer("Введите стоимость:")
    dp.register_message_handler(lambda m: process_cost(m, car_id, work_type), state=None)

async def process_cost(msg: types.Message, car_id, work_type):
    cost = float(msg.text)
    await msg.answer("Введите дату в формате ГГГГ-ММ-ДД:")
    dp.register_message_handler(lambda m: process_date(m, car_id, work_type, cost), state=None)

async def process_date(msg: types.Message, car_id, work_type, cost):
    date = msg.text
    cursor.execute("INSERT INTO records(car_id, work_type, cost, date) VALUES(?,?,?,?)", 
                   (car_id, work_type, cost, date))
    conn.commit()
    await msg.answer("Запись добавлена!")

@dp.callback_query_handler(lambda c: c.data.startswith("view_records_"))
async def view_records(cb: types.CallbackQuery):
    car_id = int(cb.data.split("_")[2])
    cursor.execute("SELECT work_type, cost, date FROM records WHERE car_id=?", (car_id,))
    records = cursor.fetchall()
    if records:
        text = "\n".join([f"{r[0]} | {r[1]} ₽ | {r[2]}" for r in records])
    else:
        text = "Нет записей"
    await cb.message.answer(text)

@dp.callback_query_handler(lambda c: c.data=="back_main")
async def back_main(cb: types.CallbackQuery):
    await cb.message.edit_text("Главное меню:", reply_markup=main_menu(cb.from_user.id))

# --- Webhook запуск ---
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
