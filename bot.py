import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode

# ====== Настройки Render ======
API_TOKEN = os.getenv("API_TOKEN")  # Твой токен бота из Environment Variables
if not API_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения!")

WEBHOOK_HOST = 'https://car-service-bot-ubk9.onrender.com'  # твой URL на Render
WEBHOOK_PATH = f'/webhook/{API_TOKEN}'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Render предоставляет порт через переменную окружения PORT
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = int(os.environ.get('PORT', 8000))

# ====== Инициализация бота ======
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# ====== Хендлеры ======
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer("Бот запущен и работает!")

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
