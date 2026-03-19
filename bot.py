import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ---------- База данных ----------
DB_FILE = "cars.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            user_id INTEGER,
            car_name TEXT,
            info TEXT,
            PRIMARY KEY(user_id, car_name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            user_id INTEGER,
            car_name TEXT,
            record TEXT,
            record_date TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Главные команды ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply("Привет! Я твоя сервисная книжка 🚗\nВыбирай команду ниже:", reply_markup=main_menu())

def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Добавить авто", callback_data="add_car"),
        InlineKeyboardButton("📋 Мои авто", callback_data="list_cars")
    )
    return kb

# ---------- Добавление авто ----------
@dp.callback_query_handler(lambda c: c.data == "add_car")
async def add_car(call: types.CallbackQuery):
    await call.message.answer("Введите название/марку автомобиля:")
    dp.register_message_handler(receive_car_name, state=None)

async def receive_car_name(message: types.Message):
    user_id = message.from_user.id
    car_name = message.text.strip()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars WHERE user_id=? AND car_name=?", (user_id, car_name))
    if cursor.fetchone():
        await message.reply("Такое авто уже есть!")
    else:
        cursor.execute("INSERT INTO cars (user_id, car_name, info) VALUES (?, ?, ?)", (user_id, car_name, ""))
        conn.commit()
        await message.reply(f"Авто '{car_name}' добавлено!")
    conn.close()
    dp.unregister_message_handler(receive_car_name, state=None)

# ---------- Список авто ----------
@dp.callback_query_handler(lambda c: c.data == "list_cars")
async def list_cars(call: types.CallbackQuery):
    user_id = call.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT car_name FROM cars WHERE user_id=?", (user_id,))
    cars = cursor.fetchall()
    conn.close()

    if not cars:
        await call.message.answer("У тебя пока нет авто. Добавь через '➕ Добавить авто'")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    for (car_name,) in cars:
        kb.add(InlineKeyboardButton(car_name, callback_data=f"car_{car_name}"))
    await call.message.answer("Выбери авто:", reply_markup=kb)

# ---------- Детали авто ----------
@dp.callback_query_handler(lambda c: c.data.startswith("car_"))
async def car_detail(call: types.CallbackQuery):
    user_id = call.from_user.id
    car_name = call.data[4:]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT info FROM cars WHERE user_id=? AND car_name=?", (user_id, car_name))
    car_info = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM records WHERE user_id=? AND car_name=?", (user_id, car_name))
    record_count = cursor.fetchone()[0]
    conn.close()

    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📝 Добавить запись", callback_data=f"add_record_{car_name}"),
        InlineKeyboardButton("📄 Показать историю", callback_data=f"show_history_{car_name}"),
        InlineKeyboardButton("⬅️ Назад", callback_data="list_cars")
    )

    text = f"Авто: {car_name}\nИнформация: {car_info if car_info else 'Нет информации'}\nЗаписей: {record_count}"
    await call.message.answer(text, reply_markup=kb)

# ---------- Добавление записи ----------
@dp.callback_query_handler(lambda c: c.data.startswith("add_record_"))
async def add_record(call: types.CallbackQuery):
    user_id = call.from_user.id
    car_name = call.data[len("add_record_"):]
    await call.message.answer(f"Введите текст записи для '{car_name}':")
    dp.register_message_handler(lambda message: receive_record(message, car_name), state=None)

async def receive_record(message: types.Message, car_name):
    user_id = message.from_user.id
    record = message.text.strip()
    record_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO records (user_id, car_name, record, record_date) VALUES (?, ?, ?, ?)",
                   (user_id, car_name, record, record_date))
    conn.commit()
    conn.close()

    await message.reply(f"Запись добавлена для '{car_name}'!")
    dp.unregister_message_handler(lambda message: receive_record(message, car_name), state=None)

# ---------- История авто ----------
@dp.callback_query_handler(lambda c: c.data.startswith("show_history_"))
async def show_history(call: types.CallbackQuery):
    user_id = call.from_user.id
    car_name = call.data[len("show_history_"):]
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT record, record_date FROM records WHERE user_id=? AND car_name=? ORDER BY record_date DESC",
                   (user_id, car_name))
    records = cursor.fetchall()
    conn.close()

    if not records:
        await call.message.answer("История пустая.")
    else:
        text = "\n".join([f"{i+1}. [{date}] {r}" for i, (r, date) in enumerate(records)])
        await call.message.answer(f"История для '{car_name}':\n{text}")

# ---------- Запуск бота ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
