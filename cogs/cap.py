#!/usr/bin/python3.6
"""Defines the functions used for handling citadel caps."""
import os
import asyncio
import datetime
from discord.ext import commands
from config import cap_channel
from alog_check import SESSION, Account

ABSPATH = os.path.dirname(os.path.abspath(__file__))

class Cap():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.cap_ch = self.bot.get_channel(cap_channel)

        self.bot.cap_report = self.bot.loop.create_task(self.report_caps())

    async def in_cap_channel(self, ctx):
        """Checks if the context channel is the cap channel."""
        return ctx.channel == cap_channel

    async def cap_handler_and_channel(self, ctx):
        """Checks if the channel is the cap channel and the user is a cap handler."""
        return ("cap handler" in ctx.author.roles) and ctx.channel == cap_channel

    @commands.command()
    async def cap_help(self, ctx):
        """Provides a help message for bot usage."""
        out_msg = ("Commands:\n!delmsgs <argument> - using a message id will "
                   "delete all messages before that id. Using 'all' will delete "
                   "all messages, and using 'noncap' will delete all non-cap report "
                   "messages.\n!update - force a manual check of all alogs.\n!list "
                   "- generates a list of all users who have capped recently, by "
                   "looking at cap reports in the channel. Note that if there are "
                   "no cap messages, this will do nothing.\n!force <argument> - "
                   "the bot will check the database for cap info about the user, "
                   "and will send a message to the channel if cap info exists. "
                   "Using 'all' will send an update message to the channel for "
                   "every user in the database.")
        await ctx.send(out_msg)

    @commands.command()
    @commands.check(cap_handler_and_channel)
    async def delmsgs(self, ctx, which):
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

    @commands.command()
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
        print(userlist)
        ret_str = ""
        for (_, i) in enumerate(userlist):
            ret_str += f"{i+1}. {userlist[i]}\n"
        await ctx.send(ret_str)

    @commands.command()
    @commands.check(cap_handler_and_channel)
    async def force(self, ctx, force_user):
        """Forces a single user to update."""
        if force_user == "all":
            capped_users = SESSION.query(Account.name, Account.last_cap_time).all()
            for (user, cap_date) in capped_users:
                cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg = (f"{user} has capped at the citadel on {date_report} ",
                           f"at {time_report}.")
        else:
            cap_date = SESSION.query(Account.last_cap_time).filter(Account.name == user).first()
            if cap_date is not None:
                cap_date = cap_date[0]
                cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                out_msg = (f"{user} has capped at the citadel on {date_report} ",
                           "at {time_report}.")
        await ctx.send(out_msg)

    async def report_caps(self):
        """Reports caps."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            with open(f"{ABSPATH}/cogfiles/new_caps.txt", "r") as new_caps:
                for cap in new_caps:
                    cap = cap.strip()
                    if not cap:
                        continue
                    await self.bot.cap_ch.send(cap)
            await asyncio.sleep(600)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Cap(bot))
