import asyncio
from datetime import datetime, timedelta

import aiohttp
from aiogram import types

from database import connect_to_db
from IITU_INO_telegram_bot.bot import bot, dp

import logging

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


@dp.message_handler(commands=['start'])
async def send_start_keyboard(msg: types.Message):
    logger.info(f"Received /start command from user {msg.from_user.id} | {msg.from_user.username}")
    commands = ["help", "remind", "joke"]
    keyboard = types.InlineKeyboardMarkup()
    for command in commands:
        keyboard.add(types.InlineKeyboardButton(command, callback_data=command))
    await bot.send_message(msg.from_user.id, f"Hello there! I'm a test bot made by Igor Ruzhilov (INO Studio). Nice to see you here, {msg.from_user.first_name}")
    await msg.reply("Here is the list of commands that I can do:", reply_markup=keyboard)


@dp.callback_query_handler()
async def handle_callback_query(query: types.CallbackQuery):
    command = query.data
    if command == "help":
        logger.info(f"Received /help command from user {query.from_user.id} | {query.from_user.username}")
        await bot.send_message(query.from_user.id, "Help is on the way! Here is the list of commands that I can do:\n/start\n/remind\n/joke")
    elif command == "remind":
        logger.info(f"Received /remind command from user {query.from_user.id} | {query.from_user.username}")
        await bot.send_message(query.from_user.id, "How to use: /remind [date and time in format dd.mm.yy h:m] [reminder text]")
    elif command == "joke":
        logger.info(f"Received /joke command from user {query.from_user.id} | {query.from_user.username}")
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


@dp.message_handler(commands=['help'])
async def send_help(msg: types.Message):
    logger.info(f"Received /help command from user: {msg.from_user.id} | {msg.from_user.username}")


@dp.message_handler(commands=['remind'])
async def set_reminder(msg: types.Message):
    logger.info(f"Received /remind command from user {msg.from_user.id} | {msg.from_user.username}")
    args = msg.get_args().split(maxsplit=2)
    if len(args) != 3:
        await msg.reply("How to use: /remind [date and time in format dd.mm.yy h:m] [reminder text]")
        return

    try:
        remind_at = datetime.strptime(args[0] + ' ' + args[1], '%d.%m.%y %H:%M')
    except ValueError:
        await msg.reply("Incorrect date and time format. Please, enter the date and time in format dd.mm.yy h:m.")
        return

    if remind_at < datetime.now():
        await msg.reply("It seems like this time is already behind!")
        return

    text = args[2]
    chat_id = msg.chat.id

    # Saving the info about reminder to the database
    conn = await connect_to_db()
    logger.info(f"Connected to the database")
    reminder_id = await conn.fetchval(
        "INSERT INTO reminders (chat_id, text, remind_at) VALUES ($1, $2, $3) RETURNING id",
        chat_id, text, remind_at
    )
    logger.info(f"Inserted a reminder to the database from user {msg.from_user.id} | {msg.from_user.username}")

    # Planning the sending of reminder-message
    delay = (remind_at - datetime.now()).total_seconds()
    asyncio.create_task(schedule_reminder(reminder_id, chat_id, text, delay))

    await msg.reply(f"Reminder was successfully set at {remind_at.strftime('%d.%m.%y %H:%M')}.")


@dp.message_handler(commands=['joke'])
async def send_joke(msg: types.Message):
    logger.info(f"Received /joke command from user {msg.from_user.id} | {msg.from_user.username}")
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            data = await response.json()
            joke = f"{data['setup']} {data['punchline']}"
            await msg.reply(joke)


@dp.message_handler()
async def handle_unknown_messages(msg: types.Message):
    await msg.reply("Sorry, I can't understand you! I was made only for functioning by commands. Send /help to see available ones.")
