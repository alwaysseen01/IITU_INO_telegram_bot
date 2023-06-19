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

    # An extraction of the RESPONSE message from the database
    conn = await connect_to_db()
    response = await conn.fetchval("SELECT response FROM commands WHERE command = $1", "start")
    await bot.send_message(msg.from_user.id, f"{response}, {msg.from_user.first_name}")

    # An extraction of the AVAILABLE TELEGRAM-KEYBOARD ELEMENTS from the database
    commands = await conn.fetch("SELECT command FROM panel_commands WHERE panel_id = (SELECT id FROM commands WHERE command = $1)", "start")
    keyboard = types.InlineKeyboardMarkup()
    for command in commands:
        keyboard.add(types.InlineKeyboardButton(command['command'], callback_data=command['command']))
    await msg.reply("Here is the list of commands that I can do:", reply_markup=keyboard)


# -------------------------- CALLBACK QUERY ------------------------------------------
@dp.callback_query_handler()
async def handle_callback_query(query: types.CallbackQuery):
    command = query.data
    conn = await connect_to_db()
    response = await get_command_response(command)
    logger.info(f"Received /{command} command from user: {query.from_user.id} | {query.from_user.username}")

    if command == "help":
        help_commands = await conn.fetch("SELECT command FROM commands")
        commands_text = "\n".join([f"/{command['command']}" for command in help_commands if command['command'] != "help" and command['command'] != "start"])
        response = f"{response}\n{commands_text}"
        await bot.send_message(query.from_user.id, response)
    elif command == "joke":
        joke_text = await get_joke_text()
        response = f"{response}\n{joke_text}"
        await bot.send_message(query.from_user.id, response)


async def get_command_response(command: str) -> str:
    conn = await connect_to_db()
    response = await conn.fetchval("SELECT response FROM commands WHERE command = $1", command)
    return response


async def get_joke_text() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            data = await response.json()
            joke_text = f"{data['setup']} {data['punchline']}"
            return joke_text
# --------------------------------------------------------------------------------------


@dp.message_handler()
async def handle_command(msg: types.Message):
    if msg.is_command():
        command = msg.get_command()[1:]
        logger.info(f"Received /{command} command from user: {msg.from_user.id} | {msg.from_user.username}")
        response = await get_command_response(command)
        if response:
            # ----------------- HELP COMMAND ---------------------------------------------
            if command == "help":
                conn = await connect_to_db()
                commands = await conn.fetch("SELECT command FROM commands")
                commands_text = "\n".join([f"/{command['command']}" for command in commands if command['command'] != "help" and command['command'] != "start"])
                response = f"{response}\n{commands_text}"
            # ----------------------------------------------------------------------------
            await bot.send_message(msg.from_user.id, response)
        else:
            await msg.reply(f"Sorry, I don't have a response for the /{command} command.")
    else:
        await msg.reply("Sorry, I can't understand you! I was made only for functioning by commands. Send /help to see available ones.")

async def schedule_reminder(reminder_id, chat_id, text, delay):
    await asyncio.sleep(delay)
    conn = await connect_to_db()
    await conn.execute("DELETE FROM reminders WHERE id = $1", reminder_id)
    await bot.send_message(chat_id, f"Reminder: {text}")


@dp.message_handler(commands=['remind'])
async def set_reminder(msg: types.Message):
    args = msg.get_args().split(maxsplit=2)
    if len(args) != 3:
        conn = await connect_to_db()
        response = await conn.fetchval("SELECT response FROM commands WHERE command = $1", "remind")
        await msg.reply(response)
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
async def handle_joke_command(msg: types.Message):
    conn = await connect_to_db()
    response = await conn.fetchval("SELECT response FROM commands WHERE command = $1", "joke")
    joke_text = await get_joke_text()
    response = f"{response}\n{joke_text}"
    await bot.send_message(msg.from_user.id, response)
