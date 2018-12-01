"""Defines the functions used for gathering and reporting xp."""
from datetime import datetime
import asyncio
import json
import logging
import aiohttp
import discord
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
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
    if argument == "all":
        skill_info = "all"
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
            return cls(rsn)
        except commands.BadArgument:
            async with ctx.bot.pool.acquire() as con:
                exists = await rsn_exists(con, player)
            if not exists:
                await ctx.send(f"Error: Player {player} not found in database.")
            return cls(player)

class XP():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.xp_report = self.bot.loop.create_task(self.report_xp())

    async def get_players(self, ctx, players):
        """Converts list of players into a readable list, includes author."""
        if not players:
            auth = await Player.convert(ctx, ctx.author.name)
            players = [auth]
        players = [player.rsn for player in players if player is not None]
        logging.info(f"Players requested: {players}")
        return players

    async def get_xp_list(self, ctx, info, players):
        """Gets the skill info for each player, returns a list sorted by xp value."""
        # We have the skill ID and member, so we need to pull the most recent XP record for the
        # given user(s). If no user(s) are supplied, default to the registered rsn of the
        # Discord member who sent the command.
        players = await self.get_players(ctx, players)
        skill_id = info["id"]
        xp_list = []
        # Now that we have a tuple of the valid players from the command, we can retrieve xp
        # and skill values for each player in the specified skill.
        for player in players:
            async with self.bot.pool.acquire() as con:
                xp_stmt = """SELECT (skills -> $1 ->> 'level')::integer AS level,
                            (skills -> $1 ->> 'xp')::decimal AS xp,
                            (skills -> $1 ->> 'rank')::integer AS rank
                            FROM xp WHERE rsn = $2 ORDER BY dtg DESC LIMIT 1;"""
                xp_res = await con.fetchrow(xp_stmt, skill_id, player)
                if xp_res is None:
                    await ctx.send(f"Player {player} not found in database.")
                else:
                    xp_list.append([player, xp_res["level"], xp_res["xp"], xp_res["rank"]])

        xp_list = sorted(xp_list, key=lambda x: x[3])
        return xp_list

    async def get_xp_history(self, ctx, info, players):
        """Gets historical xp info for each player."""
        players = await self.get_players(ctx, players)
        skill_id = info["id"]
        skill = info["skill"]
        plt.clf()
        for player in players:
            player_dict = {}
            async with self.bot.pool.acquire() as con:
                async with con.transaction():
                    xp_stmt = """SELECT (skills -> $1 ->> 'xp')::float AS xp, dtg
                                FROM xp WHERE rsn = $2 ORDER BY dtg DESC;"""
                    async for record in con.cursor(xp_stmt, skill_id, player):
                        player_dict[record["dtg"]] = record["xp"]
            player_series = pd.Series(player_dict)
            player_series.plot()
            plt.xlabel("Date")
            plt.ylabel(f"XP Amount")
            plt.title(f"{skill.title()} XP Gains")
            plt.tight_layout()
            plt.savefig('./figures/hist.png')
            with open('./figures/hist.png', 'rb') as histogram:
                await ctx.send(file=discord.File(histogram))

    @commands.group(invoke_without_command=True)
    async def xp(self, ctx, info: get_skill_info, players: commands.Greedy[Player] = None):
        """Handles the xp commands - allows users to retrieve level and xp values for themselves
        and others."""
        if info is None:
            await ctx.send("Please enter a valid skill name.")
            return
        if ctx.invoked_subcommand is None:
            xp_list = await self.get_xp_list(ctx, info, players)
            skill = info["skill"]
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

    @xp.command(name="graph")
    async def graph(self, ctx, info: get_skill_info, players: commands.Greedy[Player] = None):
        """Plots line graph of requested skill for requested players."""
        xp_list = await self.get_xp_list(ctx, info, players)
        skill = info["skill"]
        plt.clf()
        players = [rec[0] for rec in xp_list]
        values = [rec[2] for rec in xp_list]
        fig, axes = plt.subplots(figsize=(16, 6))
        axes.set_facecolor("#F3F3F3")
        index = np.arange(len(players))
        plt.bar(index, values, alpha=0.4, color="gold", edgecolor="black", align='center')
        plt.xlabel("Players")
        plt.ylabel(f"XP Amount")
        plt.title(f"Clan {skill.title()} XP Comparison")
        plt.xticks(index, players)
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.savefig('./figures/hist.png')
        with open('./figures/hist.png', 'rb') as histogram:
            await ctx.send(file=discord.File(histogram))

    @xp.command(name="gains")
    async def gains(self, ctx, info: get_skill_info, players: commands.Greedy[Player] = None):
        """Plots gains of requested skill for requested players."""
        await self.get_xp_history(ctx, info, players)

    @commands.group(name="max", invoke_without_command=True)
    async def max(self, ctx, players: commands.Greedy[Player] = None):
        """Returns max percentage/details for requested players."""
        if ctx.invoked_subcommand is None:
            players = await self.get_players(ctx, players)
            if players is None:
                return
            output = []
            for player in players:
                async with self.bot.pool.acquire() as con:
                    max_pct_stmt = '''SELECT max_pct FROM comp WHERE rsn = $1 ORDER BY dtg LIMIT 1;'''
                    max_pct = await con.fetchval(max_pct_stmt, player)
                output.append((player, max_pct))
            max_pct_output = sorted(output, key=lambda x: x[1])
            out_msg = "Percent to Max:\n"
            for rsn, max_pct in max_pct_output:
                out_msg += f"{rsn}: {round(max_pct*100,2)}%\n"
            await ctx.send(f"```{out_msg[:-1]}```")

    @commands.group(name="comp", invoke_without_command=True)
    async def comp(self, ctx, players: commands.Greedy[Player] = None):
        """Returns comp percentage/details for requested players."""
        if ctx.invoked_subcommand is None:
            players = await self.get_players(ctx, players)
            output = []
            for player in players:
                async with self.bot.pool.acquire() as con:
                    comp_pct_stmt = '''SELECT comp_pct FROM comp WHERE rsn = $1 ORDER BY dtg LIMIT 1;'''
                    comp_pct = await con.fetchval(comp_pct_stmt, player)
                output.append((player, comp_pct))
            comp_pct_output = sorted(output, key=lambda x: x[1])
            out_msg = "Percent to Comp:\n"
            for rsn, comp_pct in comp_pct_output:
                out_msg += f"{rsn}: {round(comp_pct*100,2)}%\n"
            await ctx.send(f"```{out_msg[:-1]}```")

    @xp.command(name="check")
    @commands.is_owner()
    async def check(self, ctx):
        """Rechecks xp and adds new records."""
        await ctx.send("Updating xp records...")
        await self.report_xp()

    async def report_comp(self, xp_dict):
        """Adds in comp percentage records from xp records."""
        comp_counted_xp = 0
        comp_needed_xp = 0
        max_counted_xp = 0
        max_needed_xp = 0
        skills = xp_dict["skills"]
        for skill_id, data in skills.items():
            # Get the max level xp from the database
            async with self.bot.pool.acquire() as con:
                comp_level_stmt = '''SELECT max_level FROM level_experience WHERE skill_id = $1'''
                comp_level = await con.fetchval(comp_level_stmt, skill_id)
                comp_xp_stmt = '''SELECT (xp_amount ->> $1)::integer as comp_xp FROM level_experience
                                WHERE skill_id = $2'''
                max_level = 99
                max_xp_stmt = '''SELECT (xp_amount ->> $1)::integer as max_xp FROM level_experience
                                WHERE skill_id = $2'''
                comp_xp = await con.fetchval(comp_xp_stmt, str(comp_level), skill_id)
                max_xp = await con.fetchval(max_xp_stmt, str(max_level), skill_id)
            comp_needed_xp += comp_xp
            comp_counted_xp += min(comp_xp, data["xp"])
            max_needed_xp += max_xp
            max_counted_xp += min(max_xp, data["xp"])
        comp_pct = comp_counted_xp/(comp_needed_xp*1.0)
        max_pct = max_counted_xp/(max_needed_xp*1.0)
        return (max_pct, comp_pct)

    async def report_xp(self):
        """Adds all xp records to databse."""
        try:
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
                        (max_pct, comp_pct) = await self.report_comp(xp_dict)
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
                                comp_stmt = """INSERT INTO comp(rsn, dtg, max_pct, comp_pct)
                                    VALUES($1, $2, $3, $4);"""
                                await con.execute(
                                    comp_stmt, xp_dict["rsn"], xp_dict["dtg"], max_pct, comp_pct)
                    else:
                        continue

                await asyncio.sleep(86400)
        except Exception as e:
            print(e)

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
        skill_xp = int(skillinfo.get("xp", 0))/10.0
        rank = skillinfo.get("rank", 0)
        skill_id = skillinfo.get("id", 100)
        xp_values[skill_id] = {"level": level, "xp": skill_xp, "rank": rank}
    xp_dict["skills"] = xp_values
    return xp_dict
