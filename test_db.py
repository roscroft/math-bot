import asyncio
import asyncpg
import datetime

async def main():

    conn = await asyncpg.connect('postgresql://austin:postgre@localhost/clan')

    # await conn.execute('''
    #     CREATE TABLE account(
    #         disc_id text PRIMARY KEY,
    #         rsn text
    #     )
    # ''')

    # await conn.execute('''
    #     INSERT INTO account(disc_id, rsn) VALUES($1, $2)
    # ''', '215367025705484289', 'iMath')

    # row = await conn.fetchrow(
    #     'SELECT * FROM account WHERE rsn = $1', 'iMath')

    account_id_stmt = f'''SELECT id FROM account LEFT JOIN name on account.id = name.disc_id WHERE name.rsn = "iMath"'''
    value = await conn.fetchval(account_id_stmt)
    print(value)

    await conn.close()

asyncio.get_event_loop().run_until_complete(main())

# class Account(BASE):
#     """Relates Discord IDs to RSNs"""
#     __tablename__ = 'account'
#     disc_id = Column(String(50), primary_key=True)
#     rsn = Column(String(50), primary_key=True)
#     last_cap_time = Column(DateTime)
#     total_caps = Column(Integer)
#     search_string = Column(String(50))
#     satisfies = Column(Boolean)
