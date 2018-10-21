#!/usr/bin/python3.6
"""Creates all tables in the database."""
import asyncio
import asyncpg
from utils.config import db_name

async def create_database(reinit, pool=None):
    """Calls the individual table creation functions."""
    if pool is not None:
        conn = await pool.acquire()
    else:
        conn = await asyncpg.connect(db_name)

    if reinit:
        await conn.execute('''
            DROP TABLE IF EXISTS account cascade;
            DROP TABLE IF EXISTS rs cascade;
            DROP TABLE IF EXISTS account_owned;
            DROP TABLE IF EXISTS caps;
            DROP TABLE IF EXISTS xp;
        ''')
        await create_account_table(conn)
        await create_rs_table(conn)
        await create_account_owned_table(conn)
        await create_caps_table(conn)
        await create_xp_table(conn)

async def create_account_table(conn):
    """Creates account table for unique account information."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS account(
            disc_id text NOT NULL,
            highest_role text,
            total_caps integer,
            PRIMARY KEY (disc_id)
        )
    ''')

async def create_rs_table(conn):
    """Creates rs table for runescape information."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS rs(
            rsn text NOT NULL,
            clan_rank text,
            PRIMARY KEY (rsn)
        )
    ''')

async def create_account_owned_table(conn):
    """Creates account_owned table, tracking historical name data."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS account_owned(
            id serial,
            disc_id text NOT NULL,
            rsn text NOT NULL,
            is_main boolean,
            start_dtg timestamp,
            end_dtg timestamp,
            PRIMARY KEY (id),
            FOREIGN KEY (disc_id) REFERENCES account(disc_id),
            FOREIGN KEY (rsn) REFERENCES rs(rsn)
        )
    ''')

async def create_caps_table(conn):
    """Creates caps table for tracking cap information."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS caps(
            id serial,
            rsn text UNIQUE NOT NULL,
            last_cap_time timestamp,
            PRIMARY KEY (id),
            FOREIGN KEY (rsn) REFERENCES rs(rsn)
        )
    ''')

async def create_xp_table(conn):
    """Creates a table called xp."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS xp(
            id serial,
            rsn text NOT NULL,
            dtg timestamp,
            skills json,
            PRIMARY KEY(id),
            FOREIGN KEY (rsn) REFERENCES rs(rsn)
        )
    ''')

def main():
    """Runs the database creation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(create_database(True))

if __name__ == "__main__":
    main()
