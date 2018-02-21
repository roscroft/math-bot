"""Runs bots for a Discord server."""
import os
import sys
import traceback
from discord.ext import commands
import config

def extensions_generator():
    """Returns a generator for all cog files that aren't in do_not_use."""
    cog_path = "./cogs"
    do_not_use = ["__init__.py"]
    for cog_file in os.listdir(cog_path):
        if (os.path.isfile(os.path.join(cog_path, cog_file)) and
                cog_file.endswith(".py") and cog_file not in do_not_use):
            yield f"cogs.{cog_file[:-3]}"

DESCRIPTION = "A basic bot that runs a couple of uninteresting cogs."

# logger = logging.getLogger(__name__)

class MathBot(commands.Bot):
    """Defines the mathbot class and functions."""

    def __init__(self):
        super().__init__(command_prefix=["$", "!"], description=DESCRIPTION)
        self.default_nick = "MathBot"

        for extension in extensions_generator():
            try:
                self.load_extension(extension)
                print(f"Successfully loaded extension {extension}.")
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    def run(self):
        """Runs the bot with the token from the config file."""
        super().run(config.token, reconnect=True)

    async def on_ready(self):
        """Prints bot initialization info"""
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        """Handles commands based on messages sent"""
        if message.author.bot:
            return

        await self.process_commands(message)

    async def on_member_update(self, before, after):
        """Resets bot's nickname anytime it is changed."""
        if before.id == self.user.id and before.nick != after.nick:
            await after.edit(nick=self.default_nick)
