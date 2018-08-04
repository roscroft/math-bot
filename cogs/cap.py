"""Defines the functions used for handling citadel caps."""
from datetime import datetime
from datetime import timedelta
import logging
import asyncio
import aiohttp
import asyncpg
import async_timeout
from discord.ext import commands
from config import cap_channel
from config import player_url
from config import clan_url
from dbs import SESSION, Account, MyHTMLParser, upsert

class Cap():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.cap_report = self.bot.loop.create_task(self.report_caps())
        self.bot.build_tick_checker = self.bot.loop.create_task(self.get_build_tick())

    async def in_cap_channel(ctx):
        """Checks if the context channel is the cap channel."""
        return ctx.channel.id == cap_channel

    async def cap_handler_and_channel(ctx):
        """Checks if the channel is the cap channel and the user is a cap handler."""
        return ("cap handler" in map(
            lambda r: r.name, ctx.author.roles)) and ctx.channel.id == cap_channel

    @commands.group(invoke_without_command=True)
    async def cap(self, ctx):
        """Defines the cap command group."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Try '$cap help'.")

    @cap.command()
    @commands.check(in_cap_channel)
    async def list(self, ctx):
        """Lists the capped users."""
        userlist = []
        async for msg_lines in ctx.channel.history(limit=500).filter(
                lambda m: m.author == self.bot.user).filter(lambda m: "capped" in m.content).map(
                    lambda m: m.content.split("\n")):
            for cap_report in msg_lines:
                name_index = cap_report.find(" has")
                userlist.append(cap_report[:name_index])
        userlist.reverse()
        ret_str = ""
        for (pos, val) in enumerate(userlist):
            ret_str += f"{pos+1}. {val}\n"
        await ctx.send(ret_str)

    @cap.command()
    @commands.check(cap_handler_and_channel)
    async def force(self, ctx, *, force_user):
        """Forces a single user to update."""
        out_msg = ""
        if force_user == "all":
            capped_users = SESSION.query(Account.rsn, Account.last_cap_time).all()
            for (user, cap_date) in capped_users:
                cap_date = datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg += (f"{user} has capped at the citadel on {date_report} "
                            f"at {time_report}.\n")
        else:
            cap_date = SESSION.query(
                Account.last_cap_time).filter(Account.rsn == force_user).first()
            if cap_date is not None:
                cap_date = cap_date[0]
                cap_date = datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg = (f"{force_user} has capped at the citadel on {date_report} "
                           f"at {time_report}.")
            else:
                out_msg = f"{force_user} not in database."
        await ctx.send(out_msg)

    @cap.command(name="del")
    @commands.check(cap_handler_and_channel)
    async def _del(self, ctx, which):
        """Deletes specified message."""
        if which == "all":
            async for msg in ctx.channel.history().filter(lambda m: m.author == self.bot.user):
                await msg.delete()
        elif which == "noncap":
            async for msg in ctx.channel.history().filter(
                    lambda m: m.author == self.bot.user).filter(
                        lambda m: "capped" not in m.content):
                await msg.delete()
        else:
            before_msg = await ctx.channel.get_message(which)
            async for msg in ctx.channel.history(before=before_msg).filter(
                    lambda m: m.author == self.bot.user):
                await msg.delete()

    @cap.command(name="recheck")
    async def recheck(self, ctx):
        """Rechecks all alogs for cap messages."""
        await self.report_caps()

    @cap.command(name="tick")
    async def tick(self, ctx):
        """Displays the last build tick."""
        await ctx.send(f"Last build tick: {self.bot.last_build_tick}")

    async def report_caps(self):
        """Reports caps."""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            clan_parser = MyHTMLParser()
            async with aiohttp.ClientSession() as session:
                req_html = await fetch(session, clan_url)
            clan_parser.feed(req_html)
            clan_list = clan_parser.data
            add_list = []
            cap_list = []
            logging.info(f"Last build tick: {self.bot.last_build_tick}")
            for user in clan_list:
                cap_date = await check_alog(user, "capped")
                # Add the cap only if it exists, it's been since the last build tick, and
                # there's no message already in the channel.
                if cap_date is not None:
                    logging.info(f"Cap date for {user}: {cap_date}")
                    if cap_date < self.bot.last_build_tick:
                        logging.info("Not reporting cap: before build tick.")
                    else:
                        cap_date = datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                        add_list.append(update_db(cap_date, user))

                        datetime_list = cap_date.split(" ")
                        cap_str = (f"{user} has capped at the citadel on {datetime_list[0]}"
                                   f" at {datetime_list[1]}.")
                        cap_msg_list = await self.bot.cap_ch.history().filter(
                            lambda m: m.author == self.bot.user).map(lambda m: m.content).filter(
                                lambda m, c_s=cap_str: c_s in m).flatten()
                        if cap_msg_list:
                            logging.info("Not report cap: cap message exists.")
                        if not cap_msg_list:
                            cap_list.append((user, cap_str))

            logging.info(cap_list)

            for user, cap_str in cap_list:
                await self.bot.cap_ch.send(cap_str)

            add_list = [item for item in add_list if item is not None]
            SESSION.add_all(add_list)
            SESSION.commit()

            await asyncio.sleep(600)

    async def get_build_tick(self):
        """Returns the most recent build tick - Wednesday 1600 UTC"""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            today_utc = datetime.utcnow()
            d_off = (today_utc.weekday() - 2) % 7
            h_off = (today_utc.hour - 16)
            m_off = today_utc.minute
            s_off = today_utc.second
            ms_off = today_utc.microsecond
            tdel = timedelta(
                days=d_off, hours=h_off, minutes=m_off, seconds=s_off, microseconds=ms_off)
            self.bot.last_build_tick = today_utc - tdel
            logging.info("Last build tick:")
            logging.info(self.bot.last_build_tick)

            await asyncio.sleep(3600)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Cap(bot))

async def check_alog(username, search_string):
    """Returns date if search string is in user history, or if it has previously been recorded."""
    url = f"{player_url}{username}&activities=20"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as alog_resp:
            data_json = await alog_resp.json()
    try:
        activities = data_json['activities']
    except KeyError:
        logging.info(f"{username}'s profile is private.")
        return None
    for activity in activities:
        if search_string in activity['details']:
            cap_date = activity['date']
            # logging.info(f"{search_string} found: {username}, {cap_date}")
            db_date = datetime.strptime(cap_date, "%d-%b-%Y %H:%M")
            return db_date
    return None

async def fetch(session, url):
    """Fetches a web request asynchronously."""
    async with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()

def update_db(cap_date, user):
    """Returns an insert record or None for the database."""
    primary_key_map = {"rsn": user}
    account_dict = {"rsn": user, "last_cap_time": cap_date}
    account_record = Account(**account_dict)
    return upsert(SESSION, Account, primary_key_map, account_record)


