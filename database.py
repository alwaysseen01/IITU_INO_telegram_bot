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

