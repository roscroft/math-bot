"""Provides a launcher that sets up logging for the bot."""
import logging
import argparse
import contextlib
import asyncio
import asyncpg
from mathbot import MathBot
from utils import config
from utils.dbs import create_database

@contextlib.contextmanager
def setup_logging():
    """Sets up the bot logging."""
    try:
        # __enter__
        logging.getLogger('discord').setLevel(logging.WARN)
        logging.getLogger('discord.http').setLevel(logging.WARN)

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='./logs/mathbot.log', encoding='utf-8', mode='w')
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)

def run_bot(db_reinit):
    """Initializes the logger and the bot class."""
    loop = asyncio.get_event_loop()
    log = logging.getLogger()

    try:
        pool = loop.run_until_complete(asyncpg.create_pool(
            database=config.postgre_db, user=config.postgre_user,
            password=config.postgre_pwd, command_timeout=60, loop=loop))
    except Exception:
        log.exception("Could not set up PostgreSQL. Exiting.")

    loop.run_until_complete(create_database(pool, db_reinit))

    bot = MathBot()
    bot.pool = pool
    bot.run()

def main():
    """Instantiates the bot using setup_logging as a context."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--reinitialize", default=False, action="store_true")
    args = parser.parse_args()
    db_reinit = args.reinitialize

    with setup_logging():
        run_bot(db_reinit)

if __name__ == "__main__":
    main()
