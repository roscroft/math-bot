"""Defines the functions used for gathering and reporting xp."""
from datetime import datetime
import asyncio
import json
import logging
import aiohttp
from discord.ext import commands
from utils.config import player_url
from utils.helpers import get_clan_list, update_names

def get_skill_dict():
    """Returns the dictionary containing all skills and ids."""
    with open(f"./resources/skills.json", "r+") as skills_file:
        skill_names = json.load(skills_file)
    return skill_names

def get_skill_info(argument):
    """Converts a skill name to a dictionary containing the full skill name and id."""
    skill_names = get_skill_dict()
    skills = {**skill_names["nicknames"], **skill_names["fullnames"]}
    skill_info = skills.get(argument, None)
    return skill_info

async def rsn_from_id(con, disc_id):
    """Retrieves the most current main rsn given a player's discord id.
    Returns None is player is not registered with an rsn."""
    rsn_stmt = """SELECT rsn FROM account_owned WHERE disc_id = $1 AND is_main = True
            AND end_dtg IS NULL ORDER BY end_dtg DESC LIMIT 1;
            """
    rsn = await con.fetchval(rsn_stmt, str(disc_id))
    logging.info(rsn)
    return rsn

async def rsn_exists(con, rsn):
    """Checks if a given rsn is present in the database (clan members only)."""
    rsn_stmt = """SELECT EXISTS(SELECT 1 FROM rs WHERE rsn = $1)"""
    exists = await con.fetchval(rsn_stmt, rsn)
    return exists

class XP():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.xp_report = self.bot.loop.create_task(self.report_xp())

    class Player():
        """Defines the Player class, used to capture either a Discord user or rsn."""
        def __init__(self, rsn):
            self.rsn = rsn

        @classmethod
        async def convert(cls, ctx, player):
            """Converts a Discord user to a valid rsn, or confirms an rsn."""
            try:
                member = await commands.MemberConverter().convert(ctx, player)
                logging.info(f"Member: {member}")
                async with ctx.bot.pool.acquire() as con:
                    rsn = await rsn_from_id(con, member.id)
                if rsn is None:
                    await ctx.send(f"Error: Player {player} not found in database.")
                    return None
                return cls(rsn)
            except commands.BadArgument:
                async with ctx.bot.pool.acquire() as con:
                    exists = await rsn_exists(con, player)
                if not exists:
                    await ctx.send(f"Error: Player {player} not found in database.")
                    return None
                return cls(player)

    @commands.group(invoke_without_command=True)
    async def xp(self, ctx, info: get_skill_info, players: commands.Greedy[Player]=None):
        """Handles the xp commands - allows users to retrieve level and xp values for themselves
        and others."""
        if ctx.invoked_subcommand is None:
            # We have the skill ID and member, so we need to pull the most recent XP record for the
            # given user(s). If no user(s) are supplied, default to the registered rsn of the
            # Discord member who sent the command.
            skill = info["skill"]
            skill_id = info["id"]
            actual_players = []
            logging.info(f"Players requested: {players}")
            
            if not players:
                async with self.bot.pool.acquire() as con:
                    logging.info(ctx.author.id)
                    username = await rsn_from_id(con, ctx.author.id)
                    actual_players = (username,)
            else:
                for player in players:
                    logging.info(player.rsn)
                    if player.rsn.startswith("Error:"):
                        await ctx.send(player)
                    else:
                        actual_players += (player.rsn,)
            players = actual_players
            # Now that we have a tuple of the valid players from the command, we can retrieve xp
            # and skill values for each player in the specified skill.
            xp_list = []
            for player in players:
                async with self.bot.pool.acquire() as con:
                    xp_stmt = """SELECT (skills -> $1 ->> 'level')::integer AS level,
                              (skills -> $1 ->> 'xp')::integer AS xp,
                              (skills -> $1 ->> 'rank')::integer AS rank
                              FROM xp WHERE rsn = $2 ORDER BY dtg DESC LIMIT 1;"""
                    xp_res = await con.fetchrow(xp_stmt, skill_id, player)
                    if xp_res is None:
                        await ctx.send(f"Player {player} not found in database.")
                    else:
                        xp_list.append([player, xp_res["level"], xp_res["xp"], xp_res["rank"]])

            xp_list = sorted(xp_list, key=lambda x: x[3])
            out_msg = f"{skill.title()}:\n"
            for num, rec in enumerate(xp_list):
                out_msg += f"{num+1}. {rec[0]} has level {rec[1]} {skill}, with {rec[2]} xp.\n"
            await ctx.send(f"```{out_msg}```")

    @xp.command(name="list")
    async def list(self, ctx):
        """Sends a direct message containing skill nicknames."""
        skill_names = get_skill_dict()
        out_msg = "List of skills and their aliases:\n```"
        nicknames = skill_names["nicknames"]
        for nickname, skill_info in nicknames.items():
            out_msg += f"{skill_info['skill']}: {nickname}\n"
        out_msg = out_msg[:-1] + "```"
        await ctx.author.send(out_msg)

    @xp.command(name="check")
    @commands.is_owner()
    async def check(self, ctx):
        """Rechecks xp and adds new records."""
        await self.report_xp()

    async def report_xp(self):
        """Adds all xp records to databse."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            logging.info("Updating xp records...")
            clan_list = await get_clan_list()
            logging.info(clan_list)
            logging.info(len(clan_list))
            async with self.bot.pool.acquire() as con:
                await update_names(con, clan_list)
            for user in clan_list:
                logging.info(user)
                xp_dict = await check_xp(user)
                if xp_dict is not None:
                    async with self.bot.pool.acquire() as con:
                        await con.set_type_codec(
                            'json',
                            encoder=json.dumps,
                            decoder=json.loads,
                            schema='pg_catalog'
                        )
                        async with con.transaction():
                            xp_stmt = """INSERT INTO xp(rsn, dtg, skills)
                                VALUES($1, $2, $3::json)"""
                            await con.execute(
                                xp_stmt, xp_dict["rsn"], xp_dict["dtg"], xp_dict["skills"])
                else:
                    continue

            await asyncio.sleep(86400)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(XP(bot))

async def check_xp(username):
    """Creates a record with the current datetime for user's levels and xp."""
    url = f"{player_url}{username}&activities=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as alog_resp:
            data_json = await alog_resp.json()
    name = data_json.get('name', None)
    skillvalues = data_json.get('skillvalues', None)
    if name is None or skillvalues is None:
        logging.info(f"{username}'s profile is private.")
        return None

    xp_dict = {}
    xp_dict["rsn"] = name
    xp_dict["dtg"] = datetime.now()
    xp_values = {}
    for skillinfo in skillvalues:
        level = skillinfo.get("level", 0)
        xp = skillinfo.get("xp", 0)
        rank = skillinfo.get("rank", 0)
        skill_id = skillinfo.get("id", 100)
        xp_values[skill_id] = {"level": level, "xp": xp, "rank": rank}
    xp_dict["skills"] = xp_values

    return xp_dict
