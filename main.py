from aiogram import executor

from IITU_INO_telegram_bot import handlers
from IITU_INO_telegram_bot.admin_handlers import setup_admin_handlers
from IITU_INO_telegram_bot.bot import dp
from IITU_INO_telegram_bot.handlers import setup_handlers
from database import Database

db = Database()


async def on_startup(dp):
    # Connection to the database
    await db.connect_to_db()
    setup_admin_handlers(dp, db)
    setup_handlers(dp, db)
    handlers.logger.info(f"Connected to the database on startup")


if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
