"""Defines the functions used for handling citadel caps."""
from datetime import datetime
import asyncio
import json
import aiohttp
from discord.ext import commands
from sqlalchemy import desc
from utils.config import cap_channel
from utils.config import player_url
from utils.helpers import get_clan_list

class XP():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.xp_report = self.bot.loop.create_task(self.report_xp())

    @commands.group(invoke_without_command=True)
    async def xp(self, *args):
        if ctx.invoked_subcommand is None:
            pass

    @xp.command(name="skills")
        """Sends a direct message containing skill nicknames."""
        with open(f"./resources/skills_alias.json", "r+") as skills_file:
            skill_names = json.load(skills_file)
        out_msg = "List of skills and their aliases:\n```"
        for alias, skill in skill_names.items():
            out_msg += f"{skill.title()}: {alias}\n"
        out_msg = out_msg[:-1] + "```"
        await ctx.author.send(out_msg)

    

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

    @commands.group(invoke_without_command=True)
    async def stat(self, ctx):
        """Try '$stat help' for detailed cap command information."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Try '$stat help'.")

    async def get_xp_list(self, clan_list):
        """Returns a dictionary of all users and their xp and level values."""
        xp_list = []
        for user in clan_list:
            xp_dict = await check_xp(user)




    async def report_xp(self):
        """Adds all xp records to databse."""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            logging.info("Updating xp records...")
            clan_list = await get_clan_list
            await self.update_name(clan_list)
            for user in clan_list:
                xp_dict = await check_xp(user)
                

            await asyncio.sleep(86400)


    async def report_caps(self, user=()):
        """Reports caps."""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            logging.info(f"Last build tick: {self.bot.last_build_tick}")
            if not user:
                clan_list = await get_clan_list()
            else:
                clan_list = user
            # Make sure all names are in the database prior to adding new cap records
            await self.update_names(clan_list)
            cap_list = await self.get_cap_list(clan_list)

            for name, cap_date, cap_str in cap_list:
                # Send messages to channel reporting the caps
                await self.bot.cap_ch.send(cap_str)

                # Put caps in database - update records to most recent time
                async with self.bot.pool.acquire() as con:
                    async with con.transaction():
                        upsert_stmt = f"""INSERT INTO caps(rsn, last_cap_time) 
                            VALUES($1, $2) ON CONFLICT ON CONSTRAINT caps_rsn_key 
                            DO UPDATE SET last_cap_time = EXCLUDED.last_cap_time;
                            """
                        await con.execute(upsert_stmt, name, cap_date)

            await asyncio.sleep(600)

    async def update_names(self, clan_list):
        """Adds all names from the clan list to the database."""
        async with self.bot.pool.acquire() as con:
            async with con.transaction():
                upsert_stmt = """INSERT INTO rs(rsn) VALUES($1) ON CONFLICT (rsn) DO NOTHING;
                """
                names = [(name,) for name in clan_list]
                await con.executemany(upsert_stmt, names)
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

    return xp_dict
