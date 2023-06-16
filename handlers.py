import asyncio
from datetime import datetime, timedelta

import aiohttp
from aiogram import types

from database import connect_to_db
from main import dp, bot

import logging

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


@dp.message_handler(commands=['start'])
async def send_start_keyboard(msg: types.Message):
    logger.info(f"Received /start command from user {msg.from_user.id}")
    commands = ["/help", "/remind", "/joke"]
    keyboard = types.InlineKeyboardMarkup()
    for command in commands:
        keyboard.add(types.InlineKeyboardButton(command, callback_data=command))
    await msg.reply("Here is the list of commands that I can do:", reply_markup=keyboard)


@dp.message_handler(commands=['help'])
async def send_keyboard(msg: types.Message):
    logger.info(f"Received /help command from user {msg.from_user.id}")
    commands = ["/start", "/remind", "/joke"]
    keyboard = types.InlineKeyboardMarkup()
    for command in commands:
        keyboard.add(types.InlineKeyboardButton(command, callback_data=command))
    await msg.reply("Here is the list of commands that I can do:", reply_markup=keyboard)


@dp.callback_query_handler()
async def handle_callback_query(query: types.CallbackQuery):
    command = query.data
    if command == "/start":
        await bot.send_message(query.from_user.id,
                               f"Hello there! I'm a test bot made by Igor Ruzhilov (INO Studio). Nice to see you here, {query.from_user.first_name}")
    elif command == "/remind":
        await bot.send_message(query.from_user.id, "How to use: /remind [time in minutes] [reminder text]")
    elif command == "/joke":
        async with aiohttp.ClientSession() as session:
            async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
                data = await response.json()
                joke = f"{data['setup']} {data['punchline']}"
                await bot.send_message(query.from_user.id, joke)


async def schedule_reminder(reminder_id, chat_id, text, delay):
    await asyncio.sleep(delay)
    conn = await connect_to_db()
    await conn.execute("DELETE FROM reminders WHERE id = $1", reminder_id)
    await bot.send_message(chat_id, f"Напоминание: {text}")


@dp.message_handler(commands=['remind'])
async def set_reminder(msg: types.Message):
    logger.info(f"Received /remind command from user {msg.from_user.id}")
    args = msg.get_args().split(maxsplit=1)
    if len(args) != 2:
        await msg.reply("How to use: /remind [time in minutes] [reminder text]")
        return

    try:
        delay = int(args[0])
    except ValueError:
        await msg.reply("Incorrect time. Please, enter the time in minutes.")
        return

    text = args[1]
    chat_id = msg.chat.id

    # Saving the info about reminder to the database
    conn = await connect_to_db()
    logger.info(f"Connected to the database")
    reminder_id = await conn.fetchval(
        "INSERT INTO reminders (chat_id, text, remind_at) VALUES ($1, $2, $3) RETURNING id",
        chat_id, text, datetime.now() + timedelta(minutes=delay)
    )
    logger.info(f"Inserted a reminder to the database from user {msg.from_user.id}")

    # Planning the sending of reminder-message
    asyncio.create_task(schedule_reminder(reminder_id, chat_id, text, delay * 60))

    await msg.reply(f"Reminder was successfully set in {delay} minutes.")


@dp.message_handler(commands=['joke'])
async def send_joke(msg: types.Message):
    logger.info(f"Received /joke command from user {msg.from_user.id}")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            data = await response.json()
            joke = f"{data['setup']} {data['punchline']}"
            await msg.reply(joke)
