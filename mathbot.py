"""Runs bots for a Discord server."""
import os
import sys
import json
import random
import logging
import traceback
import discord
from discord.ext import commands
from config import token
from config import main_channel

cog_path = "./cogs"
do_not_use = ["__init__.py"]

def extensions_generator():
    """Returns a generator for all cog files that aren't in do_not_use."""
    for cog_file in os.listdir(cog_path):
        if (os.path.isfile(os.path.join(cog_path, cog_file)) and
                cog_file.endswith(".py") and cog_file not in do_not_use):
            yield f"cogs.{cog_file[:-3]}"

description = "A basic bot that runs a couple of uninteresting cogs."

# logger = logging.getLogger(__name__)

class MathBot(commands.Bot):
    """Defines the mathbot class and functions."""

    def __init__(self):
        super().__init__(command_prefix=["$", "!"], description=description)
        self.default_nick = "MathBot"

        for extension in extensions_generator():
            try:
                self.load_extension(extension)
                print(f"Successfully loaded extension {extension}.")
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

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

        reaction_pct = random.random()

        if self.victim == message.author.name and reaction_pct < 1:
            add_emoji = random.sample(self.emojis, 1)[0]
            await message.add_reaction(add_emoji)

        if message.channel.id != main_channel:
            with open(f"./cogfiles/responses.json", "r+") as response_file:
                responses = json.load(response_file)
                try:
                    for call, response in responses.items():
                        if call in message.content.lower():
                            await message.channel.send(f"{response}")
                except KeyError:
                    print("No response in file!")

        await self.process_commands(message)

    async def on_member_update(self, before, after):
        """Resets bot's nickname anytime it is changed."""
        if before.id == self.user.id and before.nick != after.nick:
            await after.edit(nick=self.default_nick)

    # async def reset_nickname(self):
    #     """Changes the bot's nickname back to what it should be."""
    #     await self.wait_until_ready()
    #     while not self.is_closed():
    #         for guild in bot.guilds:
    #             await guild.me.edit(nick=self.default_nick)
    #         asyncio.sleep(600)

if __name__ == "__main__":
    bot = MathBot()
    logger = logging.getLogger('mathbot')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='./logs/mathbot.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    bot.run(token)
