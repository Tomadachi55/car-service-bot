import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from aiohttp import web
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Логирование
logging.basicConfig(level=logging.INFO)

# Конфиг из окружения
API_TOKEN = os.getenv("API_TOKEN")  # Ваш токен Telegram
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://car-service-bot-ubk9.onrender.com")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

PORT = int(os.getenv("PORT", 8000))  # Render назначает порт через переменную PORT
WEBAPP_HOST = "0.0.0.0"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ==========================
# Хендлеры для Telegram
# ==========================
@dp.message_handler(commands=["start", "help"])
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я Car Service Bot 🚗")

@dp.message_handler(commands=["ping"])
async def cmd_ping(message: types.Message):
    await message.answer("Бот живой ✅")

# ==========================
# aiohttp web для Render
# ==========================
async def handle_root(request):
    return web.Response(text="Car Service Bot is running 🚗")

app = web.Application()
app.router.add_get('/', handle_root)  # Чтобы Render Health Check не ругался

# ==========================
# Startup / Shutdown
# ==========================
async def on_startup(dp):
    logging.info("Установка webhook...")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    logging.info("Удаляем webhook...")
    await bot.delete_webhook()

# ==========================
# Запуск webhook
# ==========================
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=PORT,
        web_app=app
    )
