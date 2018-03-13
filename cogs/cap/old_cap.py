#!/usr/bin/python3.6
"""Defines the functions used for handling citadel caps."""
import asyncio
import datetime
from discord.ext import commands
from config import cap_channel
from alog_check import SESSION, Account

class Cap():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.cap_report = self.bot.loop.create_task(self.report_caps())

    async def in_cap_channel(ctx):
        """Checks if the context channel is the cap channel."""
        return ctx.channel.id == cap_channel

    async def cap_handler_and_channel(ctx):
        """Checks if the channel is the cap channel and the user is a cap handler."""
        return ("cap handler" in map(
            lambda r: r.name, ctx.author.roles)) and ctx.channel.id == cap_channel

    @commands.group(invoke_without_command=True)
    async def cap(self, ctx):
        """Try '$cap help' for detailed cap command information."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Try '$cap help'.")

    @cap.command(name="help")
    async def cap_help(self, ctx):
        """Provides a help message for bot usage."""
        out_msg = ("```Cap Cog\n"
                   "These commands will only work in the cap channel.\n"
                   "  $cap list                     - Generates a list of members who have cap"
                   " messages in the channel.\n"
                   "  $cap force <arg>              - Forces the bot to update. Valid arguments are"
                   " all, or any player name.\n"
                   "  $cap del <arg>                - Deletes bot messages. Arguments: all, noncap,"
                   " or a specific message id (deletes all messages before given id).\n"
                   "  $cap help                     - Returns this message.```")
        await ctx.send(out_msg)

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
            capped_users = SESSION.query(Account.name, Account.last_cap_time).all()
            for (user, cap_date) in capped_users:
                cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg += (f"{user} has capped at the citadel on {date_report} "
                            f"at {time_report}.\n")
        else:
            cap_date = SESSION.query(
                Account.last_cap_time).filter(Account.name == force_user).first()
            if cap_date is not None:
                cap_date = cap_date[0]
                cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg = (f"{force_user} has capped at the citadel on {date_report} "
                           f"at {time_report}.")
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

    async def report_caps(self):
        """Reports caps."""
        await self.bot.wait_until_ready()
        self.bot.cap_ch = self.bot.get_channel(cap_channel)
        while not self.bot.is_closed():
            with open(f"./cogs/cap/resources/new_caps.txt", "r+") as new_caps:
                for cap in new_caps:
                    print(cap)
                    cap = cap.strip()
                    if not cap:
                        continue
                    await self.bot.cap_ch.send(cap)

            await asyncio.sleep(600)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Cap(bot))
