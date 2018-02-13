#!/usr/bin/python3.6
"""Runs bots for a Discord server."""
import os
import subprocess
import random
import datetime
import csv
import json
import requests
import discord
from discord.ext import commands
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alog_check import Account
from config import cap_channel

ABSPATH = os.path.dirname(os.path.abspath(__file__))
ENGINE = create_engine(f"sqlite:///{ABSPATH}/dbs/clan_info.db")
MASTER_SESSION = sessionmaker(bind=ENGINE)
BASE = declarative_base()
REQUEST_SESSION = requests.session()
SESSION = MASTER_SESSION()

class MathBot(discord.Client):
    """Defines the mathbot class and functions."""
    async def on_ready(self):
        """Prints bot initialization info"""
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        """Handles commands based on messages sent"""

        channel = message.channel
        channel_id = message.channel.id
        content = message.content
        author = message.author
        author_name = author.name
        role_list = [role.name for role in author.roles]
        reaction_pct = random.random()

        with open(f"{ABSPATH}/textfiles/victim.txt", "r+") as victim_file:
            victim = victim_file.read().strip().split("~")[0]
            if victim == author_name and reaction_pct < 1:
                emojis = self.emojis()
                add_emoji = random.sample(emojis, 1)[0]
                # for emoji in emojis:
                #     if emoji.name == "nice":
                #         nice_emoji = emoji
                await message.add_reaction(add_emoji)

        for command, func in command_map.items():
            if content.startswith(command):
                out_msg = func(content)
                if out_msg is not None:
                    await channel.send(out_msg)

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

        if content.startswith("$help"):
            out_msg = "Try '$telos help' or '$pet help'."
            await channel.send(out_msg)

        elif content.startswith("$bosslist"):
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            bosses = list(droprate_json.keys())
            await channel.send(f"The tracked bosses are: {bosses}")

        elif content.startswith("$droplist"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droplist = droprate_json[boss]
                drops = list(droplist.keys())
                await channel.send(f"The drops for {boss} are: {drops}")
            except KeyError:
                await channel.send("The requested boss isn't listed.")

        elif content.startswith("$drop"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            item = " ".join(query_list[2:]).lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droprate = droprate_json[boss][item]
                await self.send_message(
                    channel, f"The droprate for {boss} of {item} is: 1/{droprate}")
            except KeyError:
                await channel.send("Specified drop or boss not listed.")

        elif content.startswith('!reboot') and "cap handler" in role_list:
            await channel.send("Rebooting bot.")
            subprocess.call(['./runmathbot.sh'])

        elif content.lower().startswith("<@!410521956954275850> when will"):
            await channel.send(f":crystal_ball: Soon:tm: :crystal_ball:")

        elif content.lower().startswith("markdonalds"):
            emojis = self.emojis()
            for emoji in emojis:
                if emoji.name == "mRage":
                    luke_emoji = emoji
            await channel.send(f"{luke_emoji}")

        elif content.startswith("!add") and author_name == "Roscroft":
            new_row = content[5:]
            new_row += "\n"
            with open(f"{ABSPATH}/textfiles/responses.csv", "a+") as responses:
                responses.write(new_row)

        elif content.startswith("!player") and author_name == "Roscroft":
            victim = content[8:]
            now = datetime.datetime.now()
            with open(f"{ABSPATH}/textfiles/victim.txt", "w+") as victim_file:
                victim_file.write(f"{victim}~{now}")

        elif content.startswith('!vis'):
            await channel.send("It's actually ~vis")

        elif channel_id == cap_channel:
            if content.startswith('!delmsgs') and ("cap handler" in role_list):
                info = content.split(" ")[1]
                if info == "all":
                    async for msg in channel.history().filter(lambda m: m.author == self.user):
                        await msg.delete()
                elif info == "noncap":
                    async for msg in channel.history().filter(
                            lambda m: m.author == self.user).filter(
                                lambda m: "capped" not in m.content):
                        await msg.delete()
                else:
                    # Try to interpret info as a message id. Thankfully bots fail gracefully
                    before_msg = await self.get_message(channel, info)
                    async for msg in channel.history().filter(lambda m: m.author == self.user):
                        await msg.delete()

            elif content.startswith('!help'):
                await self.send_message(
                    channel, ("Commands:\n!delmsgs <argument> - using a message id will "
                              "delete all messages before that id. Using 'all' will delete "
                              "all messages, and using 'noncap' will delete all non-cap report "
                              "messages.\n!update - force a manual check of all alogs.\n!list "
                              "- generates a list of all users who have capped recently, by "
                              "looking at cap reports in the channel. Note that if there are "
                              "no cap messages, this will do nothing.\n!force <argument> - "
                              "the bot will check the database for cap info about the user, "
                              "and will send a message to the channel if cap info exists. "
                              "Using 'all' will send an update message to the channel for "
                              "every user in the database."))

            elif content.startswith('!list'):
                userlist = []
                async for msg in self.logs_from(channel, limit=500):
                    if msg.author == self.user and ("capped" in msg.content):
                        msg_lines = msg.content.split("\n")
                        for cap_report in msg_lines:
                            name_index = cap_report.find(" has")
                            userlist.append(cap_report[:name_index])
                print(userlist)
                ret_str = ""
                for i in range(len(userlist)):
                    ret_str += f"{i+1}. {userlist[i]}\n"
                await channel.send(ret_str)

            elif content.startswith('!update') and ("cap handler" in role_list):
                await channel.send("Manually updating...")
                subprocess.call(['./runmathbot.sh'])

            elif content.startswith('!force') and ("cap handler" in role_list):
                user = content.split(" ")[1]
                if user == "all":
                    capped_users = SESSION.query(Account.name, Account.last_cap_time).all()
                    for (user, cap_date) in capped_users:
                        cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                        datetime_list = cap_date.split(" ")
                        date_report = datetime_list[0]
                        time_report = datetime_list[1]
                        msg_string = (f"{user} has capped at the citadel on {date_report} ",
                                      f"at {time_report}.")
                        await self.send_message(
                            discord.Object(id=cap_channel), msg_string)
                else:
                    cap_date = SESSION.query(
                        Account.last_cap_time).filter(Account.name == user).first()
                    if cap_date is not None:
                        cap_date = cap_date[0]
                        cap_date = datetime.datetime.strftime(cap_date, "%d-%b-%Y %H:%M")
                        datetime_list = cap_date.split(" ")
                        date_report = datetime_list[0]
                        time_report = datetime_list[1]
                        msg_string = (f"{user} has capped at the citadel on {date_report} ",
                                      "at {time_report}.")
                        await self.send_message(discord.Object(id=cap_channel), msg_string)

        else:
            with open(f"{ABSPATH}/textfiles/responses.csv", "r+") as responses:
                reader = csv.DictReader(responses)
                for response in reader:
                    if response['call'] in content.lower():
                        await channel.send(f"{response['answer']}")

    async def choose_victim(self):
        """Chooses a victim to add reactions to"""
        await self.wait_until_ready()
        now = datetime.datetime.now()
        with open(f"{ABSPATH}/textfiles/victim.txt", "r+") as victim_file:
            victim_list = victim_file.read().strip().split("~")
            victim = victim_list[0]
            try:
                timestamp = datetime.datetime.strptime(victim_list[1], "%Y-%m-%d %H:%M:%S.%f")
                hours_since = (now-timestamp).seconds//3600
            except IndexError:
                timestamp = None
                hours_since = None
            if timestamp is None or victim == "" or hours_since < 6:
                server = self.get_guild(339514092106678273)
                members = list(server.members)
                victim = random.sample(members, 1)[0]
                print(f"New victim: {victim.name}")
                victim_file.seek(0)
                victim_file.truncate()
                victim_file.write(f"{victim.name}~{now}")

    # async def report_caps(capped_users):
    async def report_caps(self):
        """Reports caps."""
        await self.wait_until_ready()
        with open(f"{ABSPATH}/textfiles/new_caps.txt", "r") as new_caps:
            for cap in new_caps:
                cap = cap.strip()
                if not cap:
                    continue
                await self.send_message(discord.Object(id=cap_channel), cap)
