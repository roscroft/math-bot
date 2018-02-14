#!/usr/bin/python3.6
"""Defines commands used for the Memers server."""
import os
import random
import asyncio
from discord.ext import commands
from config import guild_id

ABSPATH = os.path.dirname(os.path.abspath(__file__))

class Memers():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.victim = ""
        self.victim_choice = self.bot.loop.create_task(self.choose_victim())

    @commands.command()
    async def markdonalds(self, ctx):
        """Lets the command markdonalds return the mRage emoji."""
        mrage = self.bot.get_emoji(413441118102093824)
        await ctx.send(f"{mrage}")

    @commands.command()
    async def vis(self, ctx):
        """Corrects usage of !vis."""
        await ctx.send(f"It's actually ~vis")

    @commands.command()
    @commands.is_owner()
    async def add(self, ctx, call, response):
        """Adds a new call/response pair."""
        with open(f"{ABSPATH}/textfiles/responses.csv", "a+") as responses:
            responses.write(f"{call},{response}\n")
        await ctx.send(f"New call/response pair added: {call} -> {response}")

    @commands.command()
    @commands.is_owner()
    async def player(self, ctx, player):
        """Sets a new player victim."""
        self.victim = player
        await ctx.send(f"New victim chosen: {self.victim}")

    async def choose_victim(self):
        """Chooses a victim to add reactions to."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guild_members = self.bot.get_guild(guild_id).members
            victim_member = random.sample(guild_members, 1)[0]
            self.victim = victim_member.name
            print(f"New victim: {self.victim}")
            await asyncio.sleep(10000)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Memers(bot))

        # schep_questions = ["does schep have tess", "did schep get tess", "does schep have tess yet"]
        # milow_questions = ["does milow have ace", "did milow get ace", "does milow have ace yet"]
        # if (content.lower() in schep_questions) or (content.lower()[:-1] in schep_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Schep").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await channel.send(f"Schep does not have Tess, make sure to let him know ;)", tts=True)
        #     else:
        #         await channel.send(f"Schep finally got Tess!")

        # elif (content.lower() in milow_questions) or (content.lower()[:-1] in milow_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Milow").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await channel.send(f"Milow does not have Ace.", tts=True)
        #     else:
        #         await channel.send(f"Milow finally got Ace!")
