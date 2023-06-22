from typing import Union

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import AdminFilter

from aiogram import types
from aiogram.dispatcher.filters.state import StatesGroup, State

from bot import bot

import logging

logging.basicConfig(
    filename="bot.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


class MyAdminFilter(AdminFilter):
    def __init__(self, db):
        super().__init__()
        self.db = db

    async def check(self, obj: Union[types.Message, types.CallbackQuery]):
        user_id = obj.from_user.id
        admins = await self.db.get_admins()
        is_admin = user_id in admins
        if isinstance(obj, types.CallbackQuery):
            # Query callback checking
            is_admin = is_admin and obj.data.startswith('admin_')
        return is_admin


class Form(StatesGroup):
    command_response = State()
    remove_command = State()
    panel_command = State()
    subcommand = State()


def setup_admin_handlers(dp, db):
    @dp.message_handler(commands=['is_admin'])
    async def handle_is_admin(msg: types.Message):
        logger.info(f"Received a /is_admin command from user {msg.from_user.id} | {msg.from_user.username}")
        is_admin = await MyAdminFilter(db).check(msg)
        if is_admin:
            await msg.reply("Yes, you are an admin.")
        else:
            await msg.reply("No, you are not an admin.")

    @dp.message_handler(MyAdminFilter(db), commands=['remove_command'])
    async def handle_remove_command(msg: types.Message):
        logger.info(f"Received a /remove_command by admin {msg.from_user.id} | {msg.from_user.username}")
        await bot.send_message(msg.from_user.id,
                               "Which command you want to remove? (Enter the command name in formal '/some_command'): ")
        await Form.remove_command.set()

    @dp.message_handler(state=Form.remove_command)
    async def remove_command_step(msg: types.Message, state: FSMContext):
        command = msg.text.strip()
        if not command.startswith('/'):
            await msg.reply("Incorrect format. Please enter the command name in formal '/some_command'.")
            return
        command = command[1:]
        await db.remove_command(command)
        logger.info(f"Command /{command} was removed by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Command /{command} was successfully removed.")
        await state.finish()

    @dp.message_handler(MyAdminFilter(db), commands=['add_command'])
    async def handle_add_command(msg: types.Message):
        logger.info(f"Received a /add_command command by admin {msg.from_user.id} | {msg.from_user.username}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Command", callback_data="admin_add_command_response"))
        keyboard.add(
            types.InlineKeyboardButton("Panel", callback_data="admin_add_command_panel"))
        await msg.reply("Choose:", reply_markup=keyboard)

    @dp.callback_query_handler(MyAdminFilter(db))
    async def handle_add_command_callback(query: types.CallbackQuery, state: FSMContext):
        logger.info(f"Received a /{query.data} command from user {query.from_user.id} | {query.from_user.username}")
        if query.data == "admin_add_command_response":
            await bot.send_message(query.from_user.id,
                                   "Please enter the command name (starting with '/') and the response text separated by a space.")
            await Form.command_response.set()
        elif query.data == "admin_add_command_panel":
            await bot.send_message(query.from_user.id, "Please enter the panel command name (starting with '/').")
            await Form.panel_command.set()

    @dp.message_handler(state=Form.command_response)
    async def add_command_response_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 2 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the command name (starting with '/') and the response text separated by a space.")
            return
        command = data[0][1:]
        response = data[1]
        await db.add_command(command, response)
        logger.info(f"New command /{command} was added by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Command /{command} with response '{response}' was successfully added.")
        await state.finish()

    @dp.message_handler(state=Form.panel_command)
    async def add_command_panel_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) < 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the panel command name (starting with '/') and the response text separated by a space.")
            return
        command = data[0][1:]
        response = data[1] if len(data) > 1 else None
        panel_id = await db.add_panel(command, response)
        logger.info(f"New panel /{command} was added by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(
            f"Panel /{command} was successfully added. Now you can add subcommands to this panel. Please enter the subcommand name (starting with '/') and the response text separated by a space.")
        await state.update_data(panel_id=panel_id)
        await Form.subcommand.set()

    @dp.message_handler(state=Form.subcommand)
    async def add_subcommand_step(msg: types.Message, state: FSMContext):
        if msg.text.strip() == '/exit':
            await state.finish()
            await msg.reply("Exited panel editing mode.")
            return
        data = msg.text.split(maxsplit=1)
        if len(data) != 2 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the subcommand name (starting with '/') and the response text separated by a space. To exit panel editing mode, enter /exit.")
            return
        subcommand = data[0][1:]
        response = data[1]
        await db.add_command(subcommand, response)
        state_data = await state.get_data()
        panel_id = state_data['panel_id']
        await db.add_panel_command(panel_id, subcommand)
        panel_command = await db.get_panel_command(panel_id)
        panel_name = panel_command['command']
        logger.info(f"New subcommand /{subcommand} was added to panel /{panel_name} by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(
            f"Subcommand /{subcommand} with response '{response}' was successfully added to panel /{panel_name}. To exit panel editing mode, enter /exit.")
