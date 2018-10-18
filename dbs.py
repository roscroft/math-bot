#!/usr/bin/python3.6
"""Creates all tables in the database."""
import asyncio
import asyncpg

async def create_database(reinit, pool=None):
    """Calls the individual table creation functions."""
    if pool is not None:
        conn = await pool.acquire()
    else:
        conn = await asyncpg.connect('postgresql://austin:postgre@localhost/clan')

    if reinit:
        await conn.execute('''
            DROP TABLE IF EXISTS account;
            DROP TABLE IF EXISTS rs;
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
        CREATE TABLE IF NOT EXISTS cap(
            id serial,
            rsn text NOT NULL,
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
            attack_level integer,
            attack_xp integer,
            defence_level integer,
            defence_xp integer,
            strength_level integer,
            strength_xp integer,
            constitution_level integer,
            constitution_xp integer,
            ranged_level integer,
            ranged_xp integer,
            prayer_level integer,
            prayer_xp integer,
            magic_level integer,
            magic_xp integer,
            cooking_level integer,
            cooking_xp integer,
            woodcutting_level integer,
            woodcutting_xp integer,
            fletching_level integer,
            fletching_xp integer,
            fishing_level integer,
            fishing_xp integer,
            firemaking_level integer,
            firemaking_xp integer,
            crafting_level integer,
            crafting_xp integer,
            smithing_level integer,
            smithing_xp integer,
            mining_level integer,
            mining_xp integer,
            herblore_level integer,
            herblore_xp integer,
            agility_level integer,
            agility_xp integer,
            theiving_level integer,
            theiving_xp integer,
            slayer_level integer,
            slayer_xp integer,
            farming_level integer,
            farming_xp integer,
            runecrafting_level integer,
            runecrafting_xp integer,
            hunter_level integer,
            hunter_xp integer,
            construction_level integer,
            construction_xp integer,
            summoning_level integer,
            summoning_xp integer,
            dungeoneering_level integer,
            dungeoneering_xp integer,
            divination_level integer,
            divination_xp integer,
            invention_level integer,
            invention_xp integer,
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
