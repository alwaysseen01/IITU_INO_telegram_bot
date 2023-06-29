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

    edit_command = State()
    edit_panel = State()
    edit_command_name = State()
    edit_command_response = State()
    edit_panel_name = State()
    edit_panel_response = State()
    edit_panel_subcommand = State()
    edit_subcommand_name = State()
    edit_subcommand_response = State()


def setup_admin_handlers(dp, db):
    @dp.message_handler(commands=['is_admin'])
    async def handle_is_admin(msg: types.Message):
        logger.info(f"Received a /is_admin command from user {msg.from_user.id} | {msg.from_user.username}")
        is_admin = await MyAdminFilter(db).check(msg)
        if is_admin:
            await msg.reply("Yes, you are an admin.")
        else:
            await msg.reply("No, you are not an admin.")

    @dp.message_handler(MyAdminFilter(db), commands=['edit_command'])
    async def handle_edit_command(msg: types.Message):
        logger.info(f"Received a /edit_command command by admin {msg.from_user.id} | {msg.from_user.username}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Edit command", callback_data="admin_edit_command"))
        keyboard.add(
            types.InlineKeyboardButton("Edit panel-command", callback_data="admin_edit_panel_command"))
        await msg.reply("Choose:", reply_markup=keyboard)

    @dp.callback_query_handler(MyAdminFilter(db),
                               lambda query: query.data in ["admin_edit_command", "admin_edit_panel_command"])
    async def handle_edit_command_callback(query: types.CallbackQuery):
        logger.info(f"Received a /{query.data} command from user {query.from_user.id} | {query.from_user.username}")
        if query.data == "admin_edit_command":
            await bot.send_message(query.from_user.id,
                                   "Please enter the command name (starting with '/') that you want to edit.")
            await Form.edit_command.set()
        elif query.data == "admin_edit_panel_command":
            await bot.send_message(query.from_user.id,
                                   "Please enter the panel-command name (starting with '/') that you want to edit.")
            await Form.edit_panel.set()

    @dp.message_handler(state=Form.edit_command)
    async def edit_command_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the command name (starting with '/') that you want to edit.")
            return
        command = data[0][1:]
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Edit command name", callback_data="admin_edit_command_name"))
        keyboard.add(
            types.InlineKeyboardButton("Edit command response", callback_data="admin_edit_command_response"))
        await msg.reply("Choose what you want to edit exactly:", reply_markup=keyboard)
        await state.update_data(command=command)

    @dp.callback_query_handler(MyAdminFilter(db),
                               lambda query: query.data in ["admin_edit_command_name", "admin_edit_command_response"], state=Form.edit_command)
    async def handle_edit_command_name_response_callback(query: types.CallbackQuery, state: FSMContext):
        state_data = await state.get_data()
        old_command = state_data['command']
        if query.data == "admin_edit_command_name":
            await state.update_data(old_command=old_command)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new name for the command (starting with '/').")
            await Form.edit_command_name.set()
        elif query.data == "admin_edit_command_response":
            await state.update_data(old_command=old_command)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new response for the command.")
            await Form.edit_command_response.set()

    @dp.message_handler(state=Form.edit_command_name)
    async def edit_command_name_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the new command name (starting with '/').")
            return
        new_command = data[0][1:]
        state_data = await state.get_data()
        old_command = state_data['old_command']
        await db.update_command_name(old_command, new_command)
        logger.info(f"Command /{old_command} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Command /{old_command} was successfully updated to /{new_command}.")
        await state.finish()

    @dp.message_handler(state=Form.edit_command_response)
    async def edit_command_response_step(msg: types.Message, state: FSMContext):
        new_response = msg.text
        await state.update_data(response=new_response)
        state_data = await state.get_data()
        command = state_data['command']
        await db.edit_command_response(command, new_response)
        logger.info(
            f"Response for command /{command} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Response for command /{command} was successfully updated to '{new_response}'.")
        await state.finish()

    @dp.message_handler(state=Form.edit_panel)
    async def edit_panel_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the panel command name (starting with '/') that you want to edit.")
            return
        command = data[0][1:]
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Edit panel-command name", callback_data="admin_edit_panel_name"))
        keyboard.add(
            types.InlineKeyboardButton("Edit panel-command response", callback_data="admin_edit_panel_response"))
        keyboard.add(
            types.InlineKeyboardButton("Edit panel-subcommand (name or response)", callback_data="admin_edit_panel_subcommand"))
        await msg.reply("Choose what you want to edit:", reply_markup=keyboard)
        await state.update_data(command=command)

    @dp.callback_query_handler(MyAdminFilter(db),
                               lambda query: query.data in ["admin_edit_panel_name", "admin_edit_panel_response", "admin_edit_panel_subcommand"], state=Form.edit_panel)
    async def handle_edit_choice_callback(query: types.CallbackQuery, state: FSMContext):
        logger.info(f"Received a /{query.data} command from user {query.from_user.id} | {query.from_user.username}")
        state_data = await state.get_data()
        old_command = state_data['command']
        if query.data == "admin_edit_panel_name":
            await state.update_data(old_command=old_command)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new panel command name (starting with '/').")
            await Form.edit_panel_name.set()
        elif query.data == "admin_edit_panel_response":
            await state.update_data(old_command=old_command)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new response text.")
            await Form.edit_panel_response.set()
        elif query.data == "admin_edit_panel_subcommand":
            await state.update_data(old_command=old_command)
            await bot.send_message(query.from_user.id,
                                   "Please enter the subcommand name (starting with '/') that you want to edit.")
            await Form.edit_panel_subcommand.set()

    @dp.message_handler(state=Form.edit_panel_name)
    async def edit_panel_name_step(msg: types.Message, state: FSMContext):
        data = msg.text.strip()
        if not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the new panel command name (starting with '/').")
            return
        new_command = data[1:]
        state_data = await state.get_data()
        old_command = state_data['command']
        await db.update_command_name(old_command, new_command)
        logger.info(f"Panel /{old_command} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Panel /{old_command} was successfully updated to /{new_command}.")
        await state.finish()

    @dp.message_handler(state=Form.edit_panel_response)
    async def edit_panel_response_step(msg: types.Message, state: FSMContext):
        new_response = msg.text
        await state.update_data(response=new_response)
        state_data = await state.get_data()
        command = state_data['command']
        await db.edit_command_response(command, new_response)
        logger.info(f"Response for panel /{command} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Response for panel /{command} was successfully updated to '{new_response}'.")
        await state.finish()

    @dp.message_handler(state=Form.edit_panel_subcommand)
    async def edit_subcommand_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the subcommand name (starting with '/') that you want to edit.")
            return
        subcommand = data[0][1:]
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Edit subcommand name", callback_data="admin_edit_subcommand_name"))
        keyboard.add(
            types.InlineKeyboardButton("Edit subcommand response", callback_data="admin_edit_subcommand_response"))
        await msg.reply("Choose what you want to edit:", reply_markup=keyboard)
        await state.update_data(subcommand=subcommand)

    @dp.callback_query_handler(MyAdminFilter(db),
                               lambda query: query.data in ["admin_edit_subcommand_name", "admin_edit_subcommand_response"], state=Form.edit_panel_subcommand)
    async def handle_edit_choice_callback(query: types.CallbackQuery, state: FSMContext):
        logger.info(f"Received a /{query.data} command from admin {query.from_user.id} | {query.from_user.username}")
        state_data = await state.get_data()
        old_subcommand = state_data['subcommand']
        if query.data == "admin_edit_subcommand_name":
            await state.update_data(old_subcommand=old_subcommand)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new subcommand name (starting with '/').")
            await Form.edit_subcommand_name.set()
        elif query.data == "admin_edit_subcommand_response":
            await state.update_data(old_subcommand=old_subcommand)
            await bot.send_message(query.from_user.id,
                                   "Please enter the new response text.")
            await Form.edit_subcommand_response.set()

    @dp.message_handler(state=Form.edit_subcommand_name)
    async def edit_subcommand_name_step(msg: types.Message, state: FSMContext):
        data = msg.text.split(maxsplit=1)
        if len(data) != 1 or not data[0].startswith('/'):
            await msg.reply(
                "Incorrect format. Please enter the new subcommand name (starting with '/').")
            return
        new_subcommand = data[0][1:]
        await state.update_data(subcommand=new_subcommand)
        state_data = await state.get_data()
        old_subcommand = state_data['old_subcommand']
        await db.update_command_name(old_subcommand, new_subcommand)
        logger.info(f"Subcommand /{old_subcommand} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Subcommand /{old_subcommand} was successfully updated to /{new_subcommand}.")
        await state.finish()

    @dp.message_handler(state=Form.edit_subcommand_response)
    async def edit_subcommand_response_step(msg: types.Message, state: FSMContext):
        new_response = msg.text
        await state.update_data(response=new_response)
        state_data = await state.get_data()
        command = state_data['subcommand']
        await db.edit_command_response(command, new_response)
        logger.info(
            f"Response for subcommand /{command} was updated by admin {msg.from_user.id} | {msg.from_user.username}")
        await msg.reply(f"Response for subcommand /{command} was successfully updated to '{new_response}'.")
        await state.finish()

    @dp.message_handler(MyAdminFilter(db), commands=['remove_command'])
    async def handle_remove_command(msg: types.Message):
        logger.info(f"Received a /remove_command by admin {msg.from_user.id} | {msg.from_user.username}")
        await bot.send_message(msg.from_user.id,
                               "Which command you want to remove? (Enter the command name in form \"/some_command\"): ")
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

    @dp.callback_query_handler(MyAdminFilter(db), lambda query: query.data in ["admin_add_command_response", "admin_add_command_panel"])
    async def handle_add_command_callback(query: types.CallbackQuery, state: FSMContext):
        logger.info(f"Received a /{query.data} command from user {query.from_user.id} | {query.from_user.username}")
        if query.data == "admin_add_command_response":
            await bot.send_message(query.from_user.id,
                                   "Please enter the command name (starting with '/') and the response text separated by a space.")
            await Form.command_response.set()
        elif query.data == "admin_add_command_panel":
            await bot.send_message(query.from_user.id,
                                   "Please enter the panel command name (starting with '/') and the response text separated by a space.")
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
        if len(data) != 2 or not data[0].startswith('/'):
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
