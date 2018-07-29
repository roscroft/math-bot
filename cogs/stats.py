"""Defines the functions used for handling citadel caps."""
from datetime import datetime
import asyncio
import json
import aiohttp
import async_timeout
from discord.ext import commands
from sqlalchemy import desc
from config import cap_channel
from config import player_url
from config import clan_url
from alog_check import MyHTMLParser, SESSION, XP

class Stats():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.xp_report = self.bot.loop.create_task(self.report_xp())

    @commands.group(invoke_without_command=True)
    async def skill(self, *args)




    async def skill(self, ctx, username, skill):
        """Returns xp in the requested skill."""
        with open(f"./resources/skills_alias.json", "r+") as skills_file:
            skill_names = json.load(skills_file)
        skill_name = skill_names.get(skill, None)
        level_column = f"{skill_name}_level"
        xp_column = f"{skill_name}_xp"
        if skill_name is None:
            out_msg = "Not a valid skill name. Try '$skilllist' for a list of skills."
        else:
            last_update = SESSION.query(XP).filter(
                XP.name == username).order_by(desc(XP.date)).first()
            if last_update is None:
                out_msg = "User not in database."
            else:
                skill_level = getattr(last_update, level_column)
                skill_xp = getattr(last_update, xp_column)
                skill_xp = str(skill_xp)
                skill_xp = f"{skill_xp[:-1]}.{skill_xp[-1]}"
                out_msg = f"{username} has {skill_level} {skill_name.title()} with {skill_xp} XP."
        await ctx.send(out_msg)

    @commands.command(name="skilllist")
    async def skilllist(self, ctx):
        """Direct messages a user with a list of skill aliases."""
        with open(f"./resources/skills_alias.json", "r+") as skills_file:
            skill_names = json.load(skills_file)
        out_msg = "List of skills and their aliases:\n```"
        for alias, skill in skill_names.items():
            out_msg += f"{skill.title()}: {alias}\n"
        out_msg = out_msg[:-1] + "```"
        await ctx.author.send(out_msg)

    @commands.group(invoke_without_command=True)
    async def stat(self, ctx):
        """Try '$stat help' for detailed cap command information."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Try '$stat help'.")

    async def report_xp(self):
        """Adds all xp records to databse."""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            clan_parser = MyHTMLParser()
            async with aiohttp.ClientSession() as session:
                req_html = await fetch(session, clan_url)
            clan_parser.feed(req_html)
            clan_list = clan_parser.data
            add_list = []
            for user in clan_list:
                xp_record = check_xp(user)
                if xp_record is not None:
                    add_list.append(xp_record)
            SESSION.add_all(add_list)
            SESSION.commit()

            await asyncio.sleep(86400)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Stats(bot))

async def check_xp(username):
    """Creates a record with the current datetime for user's levels and xp."""
    url = f"{player_url}{username}&activities=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as alog_resp:
            data_json = await alog_resp.json()
    try:
        name = data_json['name']
        skillvalues = data_json['skillvalues']
    except KeyError:
        print(f"{username}'s profile is private.")
        return None
    with open(f"./resources/skills.json", "r+") as skills_file:
        skill_names = json.load(skills_file)

    xp_dict = {}
    xp_dict["name"] = name
    xp_dict["date"] = datetime.datetime.now()
    for skill in skillvalues:
        level = skill["level"]
        xp = skill["xp"]
        skill_name = skill_names[f"{skill['id']}"]

        xp_dict[f"{skill_name}_level"] = level
        xp_dict[f"{skill_name}_xp"] = xp

    xp_record = XP(**xp_dict)
    return xp_record

async def fetch(session, url):
    """Fetches a web request asynchronously."""
    async with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()
