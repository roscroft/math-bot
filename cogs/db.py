"""Defines functions related to the database."""
from datetime import datetime
import logging
import asyncio
import aiohttp
from discord.ext import commands
from utils.config import cap_channel
from utils.config import player_url
from utils.helpers import get_clan_list
from cogs.xp import rsn_exists

class Database():
    """Defines database commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def register(self, ctx):
        """Registers a player in the database if the rsn is valid."""
        pass

    @register.command(name="main")
    async def _main(self, ctx, rsn):
        """Registers the given rsn as the player's current main account."""
       async with self.bot.pool.acquire() as con:
           exists = rsn_exists(con, rsn)
           if not exists:
               await ctx.send(f"Username {rsn} not found in clan database.")
            else:
                pass
                # Send message to registration channel for approval.

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Database(bot))
