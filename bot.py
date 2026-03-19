import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

# ====== Переменные окружения ======
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения!")

WEBHOOK_HOST = 'https://car-service-bot-ubk9.onrender.com'
WEBHOOK_PATH = f'/webhook/{API_TOKEN}'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 8000))

# ====== Инициализация бота ======
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ====== Хранилище данных ======
users_data = {}  # user_id -> {"cars": [], "appointments": []}

# ====== Главное меню ======
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("Мои машины", callback_data="my_cars"),
        InlineKeyboardButton("Новая запись", callback_data="new_appointment"),
        InlineKeyboardButton("Мои записи", callback_data="my_appointments"),
        InlineKeyboardButton("Помощь", callback_data="help")
    )
    return kb

# ====== Хендлеры ======
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(f"Привет, {message.from_user.first_name}! 🚗 Ваш Car Service Book готов.", reply_markup=main_menu())

# ====== Callback кнопки ======
@dp.callback_query_handler(lambda c: True)
async def callbacks(call: types.CallbackQuery):
    user_id = call.from_user.id
    if user_id not in users_data:
        users_data[user_id] = {"cars": [], "appointments": []}

    if call.data == "help":
        await bot.answer_callback_query(call.id)
        await bot.send_message(user_id, "Главное меню:\nМои машины — посмотреть добавленные машины\nНовая запись — создать запись на обслуживание\nМои записи — история и управление записями")
    elif call.data == "my_cars":
        await bot.answer_callback_query(call.id)
        cars = users_data[user_id]["cars"]
        if cars:
            await bot.send_message(user_id, "Ваши машины:\n" + "\n".join(cars))
        else:
            await bot.send_message(user_id, "У вас пока нет машин. Добавьте новую через /add_car")
    elif call.data == "new_appointment":
        if not users_data[user_id]["cars"]:
            await bot.answer_callback_query(call.id)
            await bot.send_message(user_id, "Сначала добавьте машину через /add_car")
            return
        await bot.answer_callback_query(call.id)
        await bot.send_message(user_id, "Напишите через запятую: Машина, Дата(ДД.ММ.ГГГГ), Описание услуги, Стоимость\nНапример: Toyota Camry, 21.03.2026, ТО, 3000")
    elif call.data == "my_appointments":
        await bot.answer_callback_query(call.id)
        appts = users_data[user_id]["appointments"]
        if appts:
            text = ""
            for i, a in enumerate(appts, 1):
                text += f"{i}. {a['car']} | {a['date']} | {a['desc']} | {a['price']}₽\n"
            await bot.send_message(user_id, text)
        else:
            await bot.send_message(user_id, "У вас пока нет записей.")

# ====== Добавление машины ======
@dp.message_handler(commands=['add_car'])
async def add_car(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        users_data[user_id] = {"cars": [], "appointments": []}
    car_name = message.text.replace("/add_car", "").strip()
    if not car_name:
        await message.answer("Введите название машины после команды, например: /add_car Toyota Camry")
        return
    users_data[user_id]["cars"].append(car_name)
    await message.answer(f"Машина '{car_name}' добавлена.", reply_markup=main_menu())

# ====== Создание записи ======
@dp.message_handler()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    # Проверяем формат записи: Машина, Дата, Описание, Стоимость
    if "," in text and len(text.split(",")) == 4:
        car, date_str, desc, price = [x.strip() for x in text.split(",")]
        try:
            datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            await message.answer("Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        users_data[user_id]["appointments"].append({
            "car": car,
            "date": date_str,
            "desc": desc,
            "price": price
        })
        await message.answer(f"Запись добавлена для {car}: {date_str}, {desc}, {price}₽", reply_markup=main_menu())
    else:
        await message.answer("Неверный формат. Для записи используйте: Машина, Дата, Описание услуги, Стоимость", reply_markup=main_menu())

# ====== Стартап и шаддаун ======
async def on_startup(dispatcher):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(dispatcher):
    print("Удаляем webhook...")
    await bot.delete_webhook()
    print("Webhook удалён")

# ====== Запуск webhook ======
if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
