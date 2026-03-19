import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

logging.basicConfig(level=logging.INFO)

API_TOKEN = os.getenv("API_TOKEN")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ===================== ДАННЫЕ =====================
cars = {}

# ===================== FSM =====================
class AddCar(StatesGroup):
    waiting_name = State()
    waiting_photo = State()

class AddRecord(StatesGroup):
    waiting_type = State()
    waiting_price = State()
    waiting_date = State()

# ===================== КЛАВИАТУРЫ =====================
def cars_keyboard():
    kb = InlineKeyboardMarkup()
    for car_id, car in cars.items():
        kb.add(InlineKeyboardButton(car["name"], callback_data=f"car_{car_id}"))
    return kb

# ===================== КОМАНДЫ =====================
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("/add_car"), KeyboardButton("/list_cars"))
    await message.answer("Привет! Управляй машинами и записями.", reply_markup=kb)

@dp.message_handler(commands=["add_car"])
async def cmd_add_car(message: types.Message):
    await message.answer("Введите название машины:")
    await AddCar.waiting_name.set()

@dp.message_handler(state=AddCar.waiting_name)
async def process_car_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отправьте фото машины:")
    await AddCar.waiting_photo.set()

@dp.message_handler(content_types=["photo"], state=AddCar.waiting_photo)
async def process_car_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    car_id = len(cars) + 1
    cars[car_id] = {
        "name": data["name"],
        "photo": message.photo[-1].file_id,
        "records": []
    }
    await message.answer(f"Машина '{data['name']}' добавлена!")
    await state.finish()

@dp.message_handler(commands=["list_cars"])
async def cmd_list_cars(message: types.Message):
    if not cars:
        await message.answer("Машин пока нет.")
        return
    await message.answer("Выберите машину:", reply_markup=cars_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("car_"))
async def process_car(callback_query: types.CallbackQuery):
    car_id = int(callback_query.data.split("_")[1])
    car = cars[car_id]

    text = f"Машина: {car['name']}\nЗаписей: {len(car['records'])}"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Добавить запись", callback_data=f"add_record_{car_id}"))
    kb.add(InlineKeyboardButton("Удалить машину", callback_data=f"del_car_{car_id}"))

    await bot.send_photo(
        callback_query.from_user.id,
        car["photo"],
        caption=text,
        reply_markup=kb
    )

# ===================== ЗАПИСИ =====================
@dp.callback_query_handler(lambda c: c.data.startswith("add_record_"))
async def add_record_start(callback_query: types.CallbackQuery):
    car_id = int(callback_query.data.split("_")[2])

    await callback_query.message.answer("Введите тип работы:")
    await AddRecord.waiting_type.set()
    await dp.current_state(user=callback_query.from_user.id).update_data(car_id=car_id)

@dp.message_handler(state=AddRecord.waiting_type)
async def process_record_type(message: types.Message, state: FSMContext):
    await state.update_data(type=message.text)
    await message.answer("Введите стоимость:")
    await AddRecord.waiting_price.set()

@dp.message_handler(state=AddRecord.waiting_price)
async def process_record_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Введите дату (например 2026-03-19):")
    await AddRecord.waiting_date.set()

@dp.message_handler(state=AddRecord.waiting_date)
async def process_record_date(message: types.Message, state: FSMContext):
    data = await state.get_data()
    car_id = data["car_id"]

    cars[car_id]["records"].append({
        "type": data["type"],
        "price": data["price"],
        "date": message.text
    })

    await message.answer(f"Запись добавлена для {cars[car_id]['name']}!")
    await state.finish()

# ===================== УДАЛЕНИЕ =====================
@dp.callback_query_handler(lambda c: c.data.startswith("del_car_"))
async def delete_car(callback_query: types.CallbackQuery):
    car_id = int(callback_query.data.split("_")[2])
    name = cars[car_id]["name"]

    del cars[car_id]

    await callback_query.message.answer(f"Машина '{name}' удалена!")

# ===================== ЗАПУСК =====================
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
