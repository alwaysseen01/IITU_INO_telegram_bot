import asyncio
from datetime import datetime

import aiohttp
from aiogram import types

from bot import bot

import logging

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def setup_handlers(dp, db):
    @dp.message_handler(commands=["start", "help"])
    async def handle_basic_commands(msg: types.Message):
        if msg.is_command():
            command = msg.get_command()[1:]
            logger.info(f"Received /{command} command from user: {msg.from_user.id} | {msg.from_user.username}")
            response = await db.get_command_response(command)
            if response:
                # ----------------- START COMMAND ---------------------------------------------
                if command == "start":
                    # An extraction of the RESPONSE message from the database
                    await bot.send_message(msg.from_user.id, f"{response}, {msg.from_user.first_name}")

                    # An extraction of the AVAILABLE TELEGRAM-KEYBOARD ELEMENTS from the database
                    commands = await db.get_panel_commands("start")
                    keyboard = types.InlineKeyboardMarkup()
                    for command in commands:
                        keyboard.add(types.InlineKeyboardButton(command['command'], callback_data=command['command']))
                    await msg.reply("Here is the list of commands that I can do:", reply_markup=keyboard)
                # ----------------- HELP COMMAND ---------------------------------------------
                elif command == "help":
                    commands = await db.select_all_from_table("commands")
                    commands_text = "\n".join([f"/{command['command']}" for command in commands if
                                               command['command'] != "help" and command['command'] != "start"])
                    response = f"{response}\n{commands_text}"
                    await bot.send_message(msg.from_user.id, response)
                # ----------------------------------------------------------------------------

    @dp.message_handler(commands=['remind'])
    async def handle_reminder_command(msg: types.Message):
        args = msg.get_args().split(maxsplit=2)
        if len(args) != 3:
            response = await db.get_command_response("remind")
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
        reminder_id = await db.add_reminder(chat_id, text, remind_at)
        logger.info(f"Inserted a reminder to the database from user {msg.from_user.id} | {msg.from_user.username}")

        # Planning the sending of reminder-message
        delay = (remind_at - datetime.now()).total_seconds()
        logger.info(f"TEST REMINDER_ID: {reminder_id}")
        asyncio.create_task(schedule_reminder(reminder_id, chat_id, text, delay))

        await msg.reply(f"Reminder was successfully set at {remind_at.strftime('%d.%m.%y %H:%M')}.")

    async def schedule_reminder(reminder_id, chat_id, text, delay):
        await asyncio.sleep(delay)
        await db.delete_from_table(reminder_id, "reminders")
        logger.info(f"Deleted reminder_id: {reminder_id} from the database")
        await bot.send_message(chat_id, f"Reminder: {text}")

    @dp.message_handler(commands=['joke'])
    async def handle_joke_command(msg: types.Message):
        logger.info(f"Received /joke command from user: {msg.from_user.id} | {msg.from_user.username}")
        command = msg.get_command()
        command = command[1:]
        response = await db.get_command_response(command)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://v2.jokeapi.dev/joke/Any") as joke_response:
                data = await joke_response.json()
                if data['type'] == 'single':
                    joke = "\n" + data['joke']
                    response += joke
                else:
                    joke = "\n" + f"{data['setup']}\n{data['delivery']}"
                    response += joke
                await bot.send_message(msg.from_user.id, response)

    @dp.message_handler()
    async def handle_custom_commands(msg: types.Message):
        if msg.is_command():
            command = msg.get_command()[1:]
            logger.info(f"Received /{command} command from user: {msg.from_user.id} | {msg.from_user.username}")
            response = await db.get_command_response(command)
            if response:
                panel_id = await db.get_panel_id(command)
                if panel_id is not None:
                    # The command is a panel
                    commands = await db.get_panel_commands(command)
                    keyboard = types.InlineKeyboardMarkup()
                    for command in commands:
                        keyboard.add(types.InlineKeyboardButton(command['command'], callback_data=command['command']))
                    await msg.reply(response, reply_markup=keyboard)
                else:
                    # The command is not a panel
                    await bot.send_message(msg.from_user.id, response)
            else:
                await msg.reply(f"Sorry, I don't have a response for the /{command} command.")
        else:
            await msg.reply(
                "Sorry, I can't understand you! I was made only for functioning by commands. Send /help to see available ones.")

    # -------------------------- CALLBACK QUERY ------------------------------------------
    @dp.callback_query_handler(text="help")
    async def handle_help_command_callback(query: types.CallbackQuery):
        command = query.data
        logger.info(f"Received /{command} command from user: {query.from_user.id} | {query.from_user.username}")
        response = await db.get_command_response(command)
        commands = await db.select_all_from_table("commands")
        commands_text = "\n".join([f"/{command['command']}" for command in commands if
                                   command['command'] != "help" and command['command'] != "start"])
        response = f"{response}\n{commands_text}"
        await bot.send_message(query.from_user.id, response)

    @dp.callback_query_handler(text="joke")
    async def handle_joke_command_callback(query: types.CallbackQuery):
        command = query.data
        logger.info(f"Received /joke command from user: {query.from_user.id} | {query.from_user.username}")
        response = await db.get_command_response(command)
        async with aiohttp.ClientSession() as session:
            async with session.get("https://v2.jokeapi.dev/joke/Any") as joke_response:
                data = await joke_response.json()
                if data['type'] == 'single':
                    joke = "\n" + data['joke']
                    response += joke
                else:
                    joke = "\n" + f"{data['setup']}\n{data['delivery']}"
                    response += joke
                await bot.send_message(query.from_user.id, response)

    @dp.callback_query_handler()
    async def handle_callback_query(query: types.CallbackQuery):
        command = query.data
        logger.info(f"Received /{command} command from user: {query.from_user.id} | {query.from_user.username}")
        response = await db.get_command_response(command)
        if response:
            panel_id = await db.get_panel_id(command)
            if panel_id is not None:
                # The command is a panel
                commands = await db.get_panel_commands(command)
                keyboard = types.InlineKeyboardMarkup()
                for command in commands:
                    keyboard.add(types.InlineKeyboardButton(command['command'], callback_data=command['command']))
                await bot.send_message(query.from_user.id, response, reply_markup=keyboard)
            else:
                # The command is not a panel
                await bot.send_message(query.from_user.id, response)
        else:
            await bot.send_message(query.from_user.id, f"Sorry, I don't have a response for the /{command} command.")

    # --------------------------------------------------------------------------------------
