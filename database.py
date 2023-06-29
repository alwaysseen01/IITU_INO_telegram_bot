import datetime

import asyncpg
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS


class Database:
    def __init__(self):
        self.pool = None

    async def connect_to_db(self):
        self.pool = await asyncpg.create_pool(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )

    async def select_all_from_table(self, table_name: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f'SELECT * FROM {table_name}')
        return rows

    async def get_command_response(self, command: str):
        async with self.pool.acquire() as conn:
            response = await conn.fetchval("SELECT response FROM commands WHERE command = $1", command)
        return response

    async def update_command_name(self, old_command: str, new_command: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE commands SET command = $1 WHERE command = $2",
                new_command, old_command
            )
            await conn.execute(
                "UPDATE panel_commands SET command = $1 WHERE command = $2",
                new_command, old_command
            )

    async def edit_command_response(self, command: str, new_response: str):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE commands SET response = $1 WHERE command = $2",
            new_response, command
        )

    async def get_panel_commands(self, parent_command: str):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT command FROM panel_commands WHERE panel_id = (SELECT id FROM commands WHERE command = $1)", parent_command)
        return rows

    async def delete_from_table(self, id: int, table_name: str):
        async with self.pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {table_name} WHERE id = $1", id)

    async def add_reminder(self, chat_id: int, reminder_text: str, remind_at: datetime.datetime):
        async with self.pool.acquire() as conn:
            reminder_id = await conn.fetchval(
                f"INSERT INTO reminders (chat_id, text, remind_at) VALUES ($1, $2, $3) RETURNING id",
                chat_id, reminder_text, remind_at
            )
        return reminder_id

    async def add_command(self, command: str, response: str):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO commands (command, response) VALUES ($1, $2)", command, response)

    async def remove_command(self, command: str):
        async with self.pool.acquire() as conn:
            panel_id = await conn.fetchval("SELECT id FROM commands WHERE command = $1", command)
            if panel_id is not None:
                child_commands = await conn.fetch("SELECT command FROM panel_commands WHERE panel_id = $1", panel_id)
                for child_command in child_commands:
                    await self.remove_command(child_command['command'])
                await conn.execute("DELETE FROM panel_commands WHERE panel_id = $1", panel_id)
            await conn.execute("DELETE FROM commands WHERE command = $1", command)

    async def add_panel(self, command: str, response: str = None):
        async with self.pool.acquire() as conn:
            panel_id = await conn.fetchval("INSERT INTO commands (command, response) VALUES ($1, $2) RETURNING id", command, response)
        return panel_id

    async def add_panel_command(self, panel_id: int, command: str):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO panel_commands (panel_id, command) VALUES ($1, $2)", panel_id, command)

    async def get_panel_command(self, panel_id: int):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT command FROM commands WHERE id = $1", panel_id)
        return row

    async def get_panel_id(self, command: str):
        async with self.pool.acquire() as conn:
            panel_id = await conn.fetchval("SELECT id FROM commands WHERE command = $1", command)
        return panel_id

    async def add_admin(self, telegram_id):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO admins (telegram_id) VALUES ($1)", telegram_id)

    async def remove_admin(self, telegram_id):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM admins WHERE telegram_id = $1", telegram_id)

    async def get_admins(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id FROM admins")
            return [row[0] for row in rows]

