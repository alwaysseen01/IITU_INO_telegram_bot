from aiogram import executor

from IITU_INO_telegram_bot import handlers
from IITU_INO_telegram_bot.bot import dp
from database import connect_to_db


async def on_startup(dp):
    # Connection to the database
    conn = await connect_to_db()
    handlers.logger.info(f"Connected to the database on startup")


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
