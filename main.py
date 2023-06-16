from aiogram import Bot, Dispatcher, executor
from config import BOT_TOKEN
from database import connect_to_db
import handlers

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


async def on_startup(dp):
    # Connection to the database
    conn = await connect_to_db()
    handlers.logger.info(f"Connected to the database on startup")

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
