import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup

API_TOKEN = os.getenv("8632548132:AAFY5z3rURfCWYcxuYEnmjqriQ_QckSjrwg")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- БАЗА ---
conn = sqlite3.connect('car.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS cars (
    user_id INTEGER,
    brand TEXT,
    model TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS records (
    user_id INTEGER,
    text TEXT,
    mileage TEXT,
    date TEXT
)
''')
conn.commit()

# --- МЕНЮ ---
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add("🚗 Добавить авто")
menu.add("📝 Добавить запись")
menu.add("📋 История")

# --- СОСТОЯНИЯ ---
class AddCar(StatesGroup):
    brand = State()
    model = State()

class AddRecord(StatesGroup):
    text = State()
    mileage = State()
    date = State()

# --- START ---
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("🚗 Сервисная книжка авто", reply_markup=menu)

# --- ДОБАВИТЬ АВТО ---
@dp.message_handler(lambda m: m.text == "🚗 Добавить авто")
async def add_car(message: types.Message):
    await message.answer("Введи марку:")
    await AddCar.brand.set()

@dp.message_handler(state=AddCar.brand)
async def get_brand(message: types.Message, state: FSMContext):
    await state.update_data(brand=message.text)
    await message.answer("Введи модель:")
    await AddCar.model.set()

@dp.message_handler(state=AddCar.model)
async def get_model(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO cars VALUES (?, ?, ?)",
                   (message.from_user.id, data['brand'], message.text))
    conn.commit()
    await message.answer("✅ Авто добавлено", reply_markup=menu)
    await state.finish()

# --- ДОБАВИТЬ ЗАПИСЬ ---
@dp.message_handler(lambda m: m.text == "📝 Добавить запись")
async def add_record(message: types.Message):
    await message.answer("Что сделали? (например: Замена масла)")
    await AddRecord.text.set()

@dp.message_handler(state=AddRecord.text)
async def record_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Пробег:")
    await AddRecord.mileage.set()

@dp.message_handler(state=AddRecord.mileage)
async def record_mileage(message: types.Message, state: FSMContext):
    await state.update_data(mileage=message.text)
    await message.answer("Дата (например 01.03.2026):")
    await AddRecord.date.set()

@dp.message_handler(state=AddRecord.date)
async def record_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO records VALUES (?, ?, ?, ?)",
                   (message.from_user.id, data['text'], data['mileage'], message.text))
    conn.commit()

    await message.answer("✅ Запись добавлена", reply_markup=menu)
    await state.finish()

# --- ИСТОРИЯ ---
@dp.message_handler(lambda m: m.text == "📋 История")
async def history(message: types.Message):
    cursor.execute("SELECT text, mileage, date FROM records WHERE user_id=?",
                   (message.from_user.id,))
    rows = cursor.fetchall()

    if not rows:
        await message.answer("❌ Нет записей")
    else:
        text = ""
        for r in rows:
            text += f"🔧 {r[0]}\n📍 {r[1]} км\n📅 {r[2]}\n\n"

        await message.answer(text)

# --- ЗАПУСК ---
if __name__ == "__main__":
    executor.start_polling(dp)
