"""Runs bots for a Discord server."""
import os
import sys
import csv
import random
import logging
import traceback
import discord
from discord.ext import commands
from config import token

ABSPATH = os.path.dirname(os.path.abspath(__file__))

initial_extensions = ['cogs.pet',
                      'cogs.telos',
                      'cogs.cap',
                      'cogs.memers']

description = "A basic bot that runs a couple of uninteresting cogs."

# logger = logging.getLogger(__name__)

class MathBot(commands.Bot):
    """Defines the mathbot class and functions."""

    def __init__(self):
        super().__init__(command_prefix="$", description=description)

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
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
        reaction_pct = random.random()

        if self.victim == message.author.name and reaction_pct < 1:
            emojis = self.emojis()
            add_emoji = random.sample(emojis, 1)[0]
            await message.add_reaction(add_emoji)

        with open(f"{ABSPATH}/cogs/cogfiles/responses.csv", "r+") as responses:
            reader = csv.DictReader(responses)
            for response in reader:
                if response['call'] in message.content.lower():
                    await message.channel.send(f"{response['answer']}")

        await self.process_commands(message)

    @commands.command()
    async def reset(self, ctx):
        """Calculates and send the time until reset."""
        ctx.send("Eventually this will tell you how long until reset.")

if __name__ == "__main__":
    bot = MathBot()
    logger = logging.getLogger('mathbot')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='./logs/mathbot.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    bot.run(token)
