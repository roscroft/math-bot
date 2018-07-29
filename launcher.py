"""Provides a launcher that sets up logging for the bot."""
import logging
import contextlib
from mathbot import MathBot

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

def run_bot():
    """Initializes the logger and the bot class."""
    log = logging.getLogger()

    bot = MathBot()
    bot.run()

def main():
    """Instantiates the bot using setup_logging as a context."""
    with setup_logging():
        run_bot()

if __name__ == "__main__":
    main()
