# bot.py
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DATABASE ---
conn = sqlite3.connect("cars.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS cars(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    photo TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id INTEGER,
    work_type TEXT,
    cost REAL,
    date TEXT,
    FOREIGN KEY(car_id) REFERENCES cars(id)
)
""")
conn.commit()

# --- STATES ---
class CarStates(StatesGroup):
    name = State()
    photo = State()
    edit_name = State()
    edit_photo = State()

class RecordStates(StatesGroup):
    work_type = State()
    cost = State()
    date = State()
    edit_work_type = State()
    edit_cost = State()
    edit_date = State()

# --- KEYBOARDS ---
def car_options_kb(car_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Добавить запись", callback_data=f"add_record_{car_id}"))
    kb.add(InlineKeyboardButton("Редактировать машину", callback_data=f"edit_car_{car_id}"))
    kb.add(InlineKeyboardButton("Удалить машину", callback_data=f"delete_car_{car_id}"))
    return kb

def record_options_kb(record_id):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Редактировать запись", callback_data=f"edit_record_{record_id}"))
    kb.add(InlineKeyboardButton("Удалить запись", callback_data=f"delete_record_{record_id}"))
    return kb

# --- COMMANDS ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Привет! Используй /add_car чтобы добавить машину или /list_cars для просмотра.")

# --- ADD CAR ---
@dp.message_handler(commands=["add_car"])
async def add_car_start(msg: types.Message):
    await msg.answer("Введите название машины:")
    await CarStates.name.set()

@dp.message_handler(state=CarStates.name)
async def car_name(msg: types.Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await msg.answer("Отправьте фото машины или /skip чтобы пропустить:")
    await CarStates.photo.set()

@dp.message_handler(content_types=['photo'], state=CarStates.photo)
async def car_photo(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data['name']
    photo_file_id = msg.photo[-1].file_id
    cursor.execute("INSERT INTO cars(name, photo) VALUES (?,?)", (name, photo_file_id))
    conn.commit()
    await msg.answer("Машина добавлена с фото!")
    await state.finish()

@dp.message_handler(commands=['skip'], state=CarStates.photo)
async def skip_photo(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data['name']
    cursor.execute("INSERT INTO cars(name) VALUES (?)", (name,))
    conn.commit()
    await msg.answer("Машина добавлена без фото!")
    await state.finish()

# --- LIST CARS ---
@dp.message_handler(commands=["list_cars"])
async def list_cars(msg: types.Message):
    cursor.execute("SELECT id, name, photo FROM cars")
    cars = cursor.fetchall()
    if not cars:
        await msg.answer("Машин нет.")
        return
    for car in cars:
        car_id, name, photo = car
        text = f"{name}"
        if photo:
            await msg.answer_photo(photo, caption=text, reply_markup=car_options_kb(car_id))
        else:
            await msg.answer(text, reply_markup=car_options_kb(car_id))

# --- CALLBACK HANDLERS ---
@dp.callback_query_handler(lambda c: c.data.startswith("delete_car_"))
async def delete_car(cb: types.CallbackQuery):
    car_id = int(cb.data.split("_")[2])
    cursor.execute("DELETE FROM cars WHERE id=?", (car_id,))
    cursor.execute("DELETE FROM records WHERE car_id=?", (car_id,))
    conn.commit()
    await cb.message.answer("Машина и все записи удалены!")

@dp.callback_query_handler(lambda c: c.data.startswith("edit_car_"))
async def edit_car_start(cb: types.CallbackQuery, state: FSMContext):
    car_id = int(cb.data.split("_")[2])
    await state.update_data(car_id=car_id)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Изменить название", callback_data="edit_car_name"))
    kb.add(InlineKeyboardButton("Изменить фото", callback_data="edit_car_photo"))
    await cb.message.answer("Выберите, что редактировать:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data=="edit_car_name", state="*")
async def edit_car_name_cb(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Введите новое название машины:")
    await CarStates.edit_name.set()

@dp.message_handler(state=CarStates.edit_name)
async def edit_car_name(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    cursor.execute("UPDATE cars SET name=? WHERE id=?", (msg.text, car_id))
    conn.commit()
    await msg.answer("Название машины обновлено!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data=="edit_car_photo", state="*")
async def edit_car_photo_cb(cb: types.CallbackQuery, state: FSMContext):
    await cb.message.answer("Отправьте новое фото или /skip чтобы оставить старое:")
    await CarStates.edit_photo.set()

@dp.message_handler(content_types=['photo'], state=CarStates.edit_photo)
async def edit_car_photo(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    photo_file_id = msg.photo[-1].file_id
    cursor.execute("UPDATE cars SET photo=? WHERE id=?", (photo_file_id, car_id))
    conn.commit()
    await msg.answer("Фото машины обновлено!")
    await state.finish()

@dp.message_handler(commands=['skip'], state=CarStates.edit_photo)
async def skip_edit_photo(msg: types.Message, state: FSMContext):
    await msg.answer("Фото оставлено без изменений.")
    await state.finish()

# --- RECORDS ---
@dp.callback_query_handler(lambda c: c.data.startswith("add_record_"))
async def add_record_start(cb: types.CallbackQuery, state: FSMContext):
    car_id = int(cb.data.split("_")[2])
    await state.update_data(car_id=car_id)
    await cb.message.answer("Введите тип работы:")
    await RecordStates.work_type.set()

@dp.message_handler(state=RecordStates.work_type)
async def record_work(msg: types.Message, state: FSMContext):
    await state.update_data(work_type=msg.text)
    await msg.answer("Введите стоимость:")
    await RecordStates.cost.set()

@dp.message_handler(state=RecordStates.cost)
async def record_cost(msg: types.Message, state: FSMContext):
    try:
        cost = float(msg.text)
    except:
        await msg.answer("Введите число!")
        return
    await state.update_data(cost=cost)
    await msg.answer("Введите дату (например 2026-03-19):")
    await RecordStates.date.set()

@dp.message_handler(state=RecordStates.date)
async def record_date(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    car_id = data['car_id']
    work_type = data['work_type']
    cost = data['cost']
    date = msg.text
    cursor.execute("INSERT INTO records(car_id, work_type, cost, date) VALUES (?,?,?,?)",
                   (car_id, work_type, cost, date))
    conn.commit()
    await msg.answer("Запись добавлена!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("delete_record_"))
async def delete_record(cb: types.CallbackQuery):
    record_id = int(cb.data.split("_")[2])
    cursor.execute("DELETE FROM records WHERE id=?", (record_id,))
    conn.commit()
    await cb.message.answer("Запись удалена!")

@dp.callback_query_handler(lambda c: c.data.startswith("edit_record_"))
async def edit_record_start(cb: types.CallbackQuery, state: FSMContext):
    record_id = int(cb.data.split("_")[2])
    await state.update_data(record_id=record_id)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Изменить тип работы", callback_data="edit_record_work"))
    kb.add(InlineKeyboardButton("Изменить стоимость", callback_data="edit_record_cost"))
    kb.add(InlineKeyboardButton("Изменить дату", callback_data="edit_record_date"))
    await cb.message.answer("Выберите что редактировать:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data=="edit_record_work", state="*")
async def edit_record_work_cb(cb: types.CallbackQuery):
    await cb.message.answer("Введите новый тип работы:")
    await RecordStates.edit_work_type.set()

@dp.message_handler(state=RecordStates.edit_work_type)
async def edit_record_work(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    record_id = data['record_id']
    cursor.execute("UPDATE records SET work_type=? WHERE id=?", (msg.text, record_id))
    conn.commit()
    await msg.answer("Тип работы обновлён!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data=="edit_record_cost", state="*")
async def edit_record_cost_cb(cb: types.CallbackQuery):
    await cb.message.answer("Введите новую стоимость:")
    await RecordStates.edit_cost.set()

@dp.message_handler(state=RecordStates.edit_cost)
async def edit_record_cost(msg: types.Message, state: FSMContext):
    try:
        cost = float(msg.text)
    except:
        await msg.answer("Введите число!")
        return
    data = await state.get_data()
    record_id = data['record_id']
    cursor.execute("UPDATE records SET cost=? WHERE id=?", (cost, record_id))
    conn.commit()
    await msg.answer("Стоимость обновлена!")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data=="edit_record_date", state="*")
async def edit_record_date_cb(cb: types.CallbackQuery):
    await cb.message.answer("Введите новую дату (например 2026-03-19):")
    await RecordStates.edit_date.set()

@dp.message_handler(state=RecordStates.edit_date)
async def edit_record_date(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    record_id = data['record_id']
    cursor.execute("UPDATE records SET date=? WHERE id=?", (msg.text, record_id))
    conn.commit()
    await msg.answer("Дата обновлена!")
    await state.finish()

# --- RUN ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
