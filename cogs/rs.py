"""Defines RS-related commands in the RS class."""
import time
import random
import datetime
import aiohttp
import discord
from discord.ext import commands
from utils.config import player_url

async def get_alog(username):
    """Returns a nicely formatted string containing data from the users' adventurer's log."""
    url = f"{player_url}{username}&activities=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as alog_resp:
            data_json = await alog_resp.json()
    try:
        out_msg = f"Adventurer's Log for {username}:\n"
        activities = data_json["activities"]
        for activity in activities:
            date = activity['date']
            text = activity['text']
            out_msg += f"Date: {date}      Log Entry: {text}\n"
    except KeyError:
        out_msg = f"{username}'s profile is private."
    out_msg = f"```{out_msg}```"
    return out_msg

class RS():
    """Defines RS commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def roll(self, ctx, *args):
        """Rolls a random number."""
        try:
            if len(args) == 1:
                minint = 1
                maxint = int(args[0])
            elif len(args) == 2:
                minint = int(args[0])
                maxint = int(args[1])
            else:
                await ctx.send('Error: invalid arguments. Syntax is `~roll [maxint]` or `~roll [minint] [maxint]`.')
                return
        except ValueError:
            await ctx.send('Error: one or both arguments are not valid numbers.')
            return
        if minint >= maxint:
            await ctx.send(f'Error: min greater than or equal to max ({minint} >= {maxint})')
        else:
            await ctx.send(f'Rolled {random.randint(minint, maxint)}!')

    @commands.command()
    async def reset(self, ctx):
        """Calculates and sends the time until reset."""
        utc_time = datetime.datetime.utcnow()
        hours = 24-utc_time.hour-1
        minutes = 60-utc_time.minute-1
        seconds = 60-utc_time.second-1
        await ctx.send(f"Reset is in {hours} hours, {minutes} minutes, and {seconds} seconds.")

    @commands.command()
    async def alog(self, ctx, *, user):
        """Returns information from the user's adventurer's log."""
        " ".join(user)
        await ctx.send(get_alog(user))

    @commands.command(aliases=['rax', 'spooder', 'araxxor'])
    async def araxxi(self, ctx):
        """Returns an embed detailing the current Araxxor rotation."""
        rotations = ['Path 1 - Minions', 'Path 2 - Acid', 'Path 3 - Darkness']
        utc_time = time.time()*1000
        current_rotation = int(((((utc_time//1000)//(24*60*60))+3)%(4*len(rotations)))//4)
        days_until_next = int(4 - (((utc_time/1000)//(24*60*60))+3)%(4*len(rotations))%4)
        next_rotation = current_rotation + 1

        if next_rotation == len(rotations):
            next_rotation = 0

        top_path = 'OPEN'
        mid_path = 'OPEN'
        bot_path = 'OPEN'

        if current_rotation == 0:
            top_path = 'CLOSED'
        elif current_rotation == 1:
            mid_path = 'CLOSED'
        elif current_rotation == 2:
            bot_path = 'CLOSED'

        footer_str = (f"Next path to be closed will be {rotations[next_rotation]} in "
                      f"{days_until_next} day{'s' if days_until_next > 1 else ''}.")

        rax_embed = discord.Embed(title="Arraxor/Araxxi Rotation", color=0x38fe4f)
        rax_embed.set_thumbnail(url="http://i.imgur.com/9m39UaE.png")
        rax_embed.add_field(name="Top Path (Minions)", value=top_path, inline=False)
        rax_embed.add_field(name="Middle Path (Acid)", value=mid_path, inline=False)
        rax_embed.add_field(name="Bottom Path (Darkness)", value=bot_path, inline=False)
        rax_embed.set_footer(text=footer_str, icon_url="http://i.imgur.com/9m39UaE.png")

        await ctx.send(content=None, embed=rax_embed)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(RS(bot))
