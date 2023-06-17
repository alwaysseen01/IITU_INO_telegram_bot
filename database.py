import asyncpg
from config import DB_HOST, DB_NAME, DB_USER, DB_PASS


async def connect_to_db():
    conn = await asyncpg.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn


async def select_all_from_table(conn, table_name):
    rows = await conn.fetch(f'SELECT * FROM {table_name}')
    return rows
