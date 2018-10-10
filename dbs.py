#!/usr/bin/python3.6
"""Runs the alog checks and updates the database/outfiles appropriately"""

async def create_database(pool, reinit):
    """Calls the individual table creation functions."""
    conn = await pool.acquire()

    if reinit:
        await conn.execute('''
            DROP TABLE IF EXISTS rs;
            DROP TABLE IF EXISTS account;
            DROP TABLE IF EXISTS xp;
        ''')
    await create_rs_table(conn)
    await create_account_table(conn)
    await create_xp_table(conn)

async def create_rs_table(conn):
    """Creates a table called rs."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS rs(
            id text not null,
            last_cap_time timestamp,
            total_caps integer,
            PRIMARY KEY (id)
        )
    ''')

async def create_account_table(conn):
    """Creates a table called account."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS account(
            disc_id text NOT NULL,
            rsn text NOT NULL,
            PRIMARY KEY (disc_id, rsn),
        )
    ''')

async def create_xp_table(conn):
    """Creates a table called xp."""
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS xp(
            id serial,
            rsn text NOT NULL,
            date timestamp,
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
            PRIMARY KEY(id, rsn)
        )
    ''')

def main():
    """Defines behavior when called directly."""
    pass

if __name__ == "__main__":
    main()
