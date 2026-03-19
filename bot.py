import os
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL")  # например https://your-app-name.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 8000))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ================== Database ==================
conn = sqlite3.connect("cars.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    photo TEXT
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER,
    work_type TEXT,
    cost TEXT,
    date TEXT
)""")
conn.commit()

# ================== States ==================
class AddCar(StatesGroup):
    name = State()
    photo = State()

class AddRecord(StatesGroup):
    car_id = State()
    work_type = State()
    cost = State()
    date = State()

# ================== Helpers ==================
def get_cars_keyboard(user_id):
    cursor.execute("SELECT id, name FROM cars WHERE user_id=?", (user_id,))
    cars = cursor.fetchall()
    kb = InlineKeyboardMarkup()
    for car_id, name in cars:
        kb.add(InlineKeyboardButton(text=name, callback_data=f"car_{car_id}"))
    return kb

def get_car_records_keyboard(car_id):
    cursor.execute("SELECT id, work_type FROM records WHERE car_id=?", (car_id,))
    records = cursor.fetchall()
    kb = InlineKeyboardMarkup()
    for rec_id, work_type in records:
        kb.add(InlineKeyboardButton(text=work_type, callback_data=f"record_{rec_id}"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back_to_cars"))
    return kb

# ================== Handlers ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Добавить машину"), KeyboardButton("Мои машины"))
    await message.answer("Привет! Управляй своими машинами.", reply_markup=kb)

@dp.message_handler(lambda msg: msg.text == "Добавить машину")
async def add_car_start(message: types.Message):
    await message.answer("Введите название машины:")
    await AddCar.name.set()

@dp.message_handler(state=AddCar.name)
async def add_car_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Прикрепите фото машины или напишите /skip, чтобы пропустить:")
    await AddCar.photo.set()

@dp.message_handler(content_types=["photo"], state=AddCar.photo)
async def add_car_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = message.photo[-1].file_id
    cursor.execute("INSERT INTO cars (user_id, name, photo) VALUES (?, ?, ?)",
                   (message.from_user.id, data['name'], photo_id))
    conn.commit()
    await message.answer("Машина добавлена ✅")
    await state.finish()

@dp.message_handler(commands=["skip"], state=AddCar.photo)
async def skip_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO cars (user_id, name) VALUES (?, ?)",
                   (message.from_user.id, data['name']))
    conn.commit()
    await message.answer("Машина добавлена без фото ✅")
    await state.finish()

@dp.message_handler(lambda msg: msg.text == "Мои машины")
async def my_cars(message: types.Message):
    kb = get_cars_keyboard(message.from_user.id)
    if kb.inline_keyboard:
        await message.answer("Выберите машину:", reply_markup=kb)
    else:
        await message.answer("У вас пока нет машин.")

@dp.callback_query_handler(lambda c: c.data.startswith("car_"))
async def car_selected(callback_query: types.CallbackQuery):
    car_id = int(callback_query.data.split("_")[1])
    cursor.execute("SELECT name, photo FROM cars WHERE id=?", (car_id,))
    car = cursor.fetchone()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Добавить запись", callback_data=f"addrec_{car_id}"))
    kb.add(InlineKeyboardButton("Редактировать машину", callback_data=f"editcar_{car_id}"))
    kb.add(InlineKeyboardButton("Удалить машину", callback_data=f"delcar_{car_id}"))
    kb.add(InlineKeyboardButton("Посмотреть записи", callback_data=f"records_{car_id}"))
    if car[1]:
        await bot.send_photo(callback_query.from_user.id, photo=car[1], caption=car[0], reply_markup=kb)
    else:
        await bot.send_message(callback_query.from_user.id, text=car[0], reply_markup=kb)

# ================== Add Record ==================
@dp.callback_query_handler(lambda c: c.data.startswith("addrec_"))
async def add_record_start(callback_query: types.CallbackQuery, state: FSMContext):
    car_id = int(callback_query.data.split("_")[1])
    await state.update_data(car_id=car_id)
    await callback_query.message.answer("Введите тип работы:")
    await AddRecord.work_type.set()

@dp.message_handler(state=AddRecord.work_type)
async def add_record_work(message: types.Message, state: FSMContext):
    await state.update_data(work_type=message.text)
    await message.answer("Введите стоимость:")
    await AddRecord.cost.set()

@dp.message_handler(state=AddRecord.cost)
async def add_record_cost(message: types.Message, state: FSMContext):
    await state.update_data(cost=message.text)
    await message.answer("Введите дату (например 2026-03-19):")
    await AddRecord.date.set()

@dp.message_handler(state=AddRecord.date)
async def add_record_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute(
        "INSERT INTO records (car_id, work_type, cost, date) VALUES (?, ?, ?, ?)",
        (data['car_id'], data['work_type'], data['cost'], data['date'])
    )
    conn.commit()
    await message.answer("Запись добавлена ✅")
    await state.finish()

# ================== Records view ==================
@dp.callback_query_handler(lambda c: c.data.startswith("records_"))
async def view_records(callback_query: types.CallbackQuery):
    car_id = int(callback_query.data.split("_")[1])
    kb = get_car_records_keyboard(car_id)
    await callback_query.message.answer("Выберите запись:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "back_to_cars")
async def back_to_cars(callback_query: types.CallbackQuery):
    kb = get_cars_keyboard(callback_query.from_user.id)
    await callback_query.message.answer("Выберите машину:", reply_markup=kb)

# ================== Webhook ==================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    logging.info("Webhook set")

async def on_shutdown(dp):
    logging.warning('Shutting down..')
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')

if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
