import json
import os
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")  # Ваш токен бота
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # URL вашего Render сервиса
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "cars_data.json"

# ================= Helper Functions =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ================= Keyboards =================
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("Добавить авто"))
main_kb.add(KeyboardButton("Список авто"))
main_kb.add(KeyboardButton("Добавить запись"))

# ================= Handlers =================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Это бот для ведения записи по вашим авто 🚗", reply_markup=main_kb)

@dp.message_handler(lambda m: m.text == "Добавить авто")
async def add_car(message: types.Message):
    await message.answer("Введите марку и модель авто через пробел, например: Toyota Camry")
    await dp.current_state(user=message.from_user.id).set_state("ADDING_CAR")

@dp.message_handler(state="ADDING_CAR")
async def save_car(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data:
        data[user_id] = {"cars": {}, "records": {}}
    car_id = str(len(data[user_id]["cars"]) + 1)
    data[user_id]["cars"][car_id] = {"name": message.text, "records": []}
    save_data(data)
    await message.answer(f"Авто '{message.text}' добавлено ✅", reply_markup=main_kb)
    await dp.current_state(user=message.from_user.id).reset_state()

@dp.message_handler(lambda m: m.text == "Список авто")
async def list_cars(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data or not data[user_id]["cars"]:
        await message.answer("У вас пока нет добавленных авто.")
        return
    cars_list = "\n".join([f"{cid}. {info['name']}" for cid, info in data[user_id]["cars"].items()])
    await message.answer(f"Ваши авто:\n{cars_list}")

@dp.message_handler(lambda m: m.text == "Добавить запись")
async def add_record_step1(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data or not data[user_id]["cars"]:
        await message.answer("Сначала добавьте авто!")
        return
    cars_list = "\n".join([f"{cid}. {info['name']}" for cid, info in data[user_id]["cars"].items()])
    await message.answer(f"Выберите авто по номеру:\n{cars_list}")
    await dp.current_state(user=message.from_user.id).set_state("SELECT_CAR_FOR_RECORD")

@dp.message_handler(state="SELECT_CAR_FOR_RECORD")
async def select_car_for_record(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    car_id = message.text.strip()
    if car_id not in data[user_id]["cars"]:
        await message.answer("Неверный номер авто. Попробуйте снова.")
        return
    await dp.current_state(user=message.from_user.id).update_data(car_id=car_id)
    await message.answer("Введите тип работы:")
    await dp.current_state(user=message.from_user.id).set_state("RECORD_TYPE")

@dp.message_handler(state="RECORD_TYPE")
async def record_type(message: types.Message):
    state_data = await dp.current_state(user=message.from_user.id).get_data()
    await dp.current_state(user=message.from_user.id).update_data(record_type=message.text)
    await message.answer("Введите стоимость работы:")
    await dp.current_state(user=message.from_user.id).set_state("RECORD_COST")

@dp.message_handler(state="RECORD_COST")
async def record_cost(message: types.Message):
    if not message.text.isdigit():
        await message.answer("Введите число для стоимости:")
        return
    await dp.current_state(user=message.from_user.id).update_data(record_cost=int(message.text))
    await message.answer("Введите дату (например 2026-03-19):")
    await dp.current_state(user=message.from_user.id).set_state("RECORD_DATE")

@dp.message_handler(state="RECORD_DATE")
async def record_date(message: types.Message):
    try:
        datetime.strptime(message.text, "%Y-%m-%d")
    except ValueError:
        await message.answer("Неверный формат даты. Введите в формате YYYY-MM-DD")
        return
    state_data = await dp.current_state(user=message.from_user.id).get_data()
    record = {
        "type": state_data["record_type"],
        "cost": state_data["record_cost"],
        "date": message.text
    }
    data = load_data()
    user_id = str(message.from_user.id)
    car_id = state_data["car_id"]
    data[user_id]["cars"][car_id]["records"].append(record)
    save_data(data)
    await message.answer("Запись добавлена ✅", reply_markup=main_kb)
    await dp.current_state(user=message.from_user.id).reset_state()

# ================= Webhook =================
async def handle(request):
    update = types.Update(**await request.json())
    await dp.process_update(update)
    return web.Response()

app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle)

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
