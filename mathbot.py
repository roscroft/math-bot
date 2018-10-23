"""Runs bots for a Discord server."""
import os
import sys
import traceback
import logging
from discord.ext import commands
from utils import config

def extensions_generator():
    """Returns a generator for all cog files that aren't in do_not_use."""
    cog_path = "./cogs"
    do_not_use = ["__init__.py", "__pycache__"]
    for cog in os.listdir(cog_path):
        if cog not in do_not_use:
            yield f"cogs.{cog[:-3]}"

def submodules_generator():
    """Returns a generator for all submodule add-ons."""
    sub_path = "./subs"
    do_not_use = ["solver"]
    for item in os.listdir(sub_path):
        path = os.path.join(sub_path, item)
        if item not in do_not_use:
            for sub in os.listdir(path):
                if sub == f"{item}.py" and sub not in do_not_use:
                    yield f"subs.{item}.{sub[:-3]}"

DESCRIPTION = "A basic bot that runs a couple of uninteresting cogs."

log = logging.getLogger(__name__)

class MathBot(commands.Bot):
    """Defines the mathbot class and functions."""

    def __init__(self):
        super().__init__(command_prefix=["$", "!"], description=DESCRIPTION)
        self.token = config.token
        self.default_nick = "MathBot"
        self.add_command(self.load)

        for extension in extensions_generator():
            try:
                self.load_extension(extension)
                logging.info(f"Successfully loaded extension {extension}.")
            except Exception:
                logging.exception(f'Failed to load extension {extension}.')
                # traceback.print_exc()

        for submodule in submodules_generator():
            try:
                self.load_extension(submodule)
                logging.info(f"Successfully loaded submodule {submodule}.")
            except Exception:
                logging.exception(f'Failed to load submodule {submodule}.')
                # traceback.print_exc()

    async def on_ready(self):
        """Prints bot initialization info"""
        logging.info('Logged in as')
        logging.info(self.user.name)
        logging.info(self.user.id)
        logging.info('------')

    async def on_message(self, message):
        """Handles commands based on messages sent"""
        if message.author.bot:
            return
        await self.process_commands(message)

    def run(self):
        """Runs the bot with the token from the config file."""
        super().run(self.token, reconnect=True)

    async def on_member_update(self, before, after):
        """Resets bot's nickname anytime it is changed."""
        if before.id == self.user.id and before.nick != after.nick:
            await after.edit(nick=self.default_nick)

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx, extension):
        """Loads a specified extension into the bot."""
        try:
            self.load_extension(extension)
            await ctx.send(f"Successfully loaded extension {extension}.")
        except Exception:
            await ctx.send(f'Failed to load extension {extension}.')
            logging.exception(f'Failed to load extension {extension}.')
