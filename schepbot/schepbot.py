#!/usr/bin/python3.6
"""Reads in clan data html and parses out the list of clan members."""
import subprocess
import argparse
import random
import datetime
import csv
import json
import requests
import discord
from sqlalchemy import Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ABSPATH = "/home/austin/Documents/schepbot"
ENGINE = create_engine(f"sqlite:////home/austin/Documents/schepbot/tess.db")
MASTER_SESSION = sessionmaker(bind=ENGINE)
BASE = declarative_base()
REQUEST_SESSION = requests.session()
SESSION = MASTER_SESSION()

class HasTess(BASE):
    """Stores if a user has Tess or not"""
    __tablename__ = 'hasTess'
    name = Column(String(50), primary_key=True)
    has_tess = Column(Boolean)

def init_db():
    """Initialized and optionally clears out the database"""
    BASE.metadata.bind = ENGINE
    BASE.metadata.create_all(ENGINE)

def check_tess(username, search_string):
    """Returns true if Tess drop is in user history, or in past history"""
    url_str = ""
    with open(f"{ABSPATH}/tokens/url.txt", "r") as url_file:
        url_str = url_file.read().strip()
    url_str += username
    url_str += "&activities=20"
    data = REQUEST_SESSION.get(url_str).content
    data_json = json.loads(data)
    try:
        activities = data_json['activities']
    except KeyError:
        print(f"{username}'s profile is private.")
        return None
    for activity in activities:
        if search_string in activity['details']:
            return True
    return False

def add_tess_to_db(username, search_string):
    """Displays cap info for a list of users."""
    add_list = []
    tess_get = check_tess(username, search_string)
    if tess_get is not None:
        tess_report = SESSION.query(
            HasTess.has_tess).filter(HasTess.name == username).first()
        if tess_report is None or tess_report[0] is False:
            primary_key_map = {"name": username}
            account_dict = {"name": username, "has_tess":tess_get}
            account_record = HasTess(**account_dict)
            add_list.append(upsert(HasTess, primary_key_map, account_record))
    add_list = [item for item in add_list if item is not None]
    SESSION.add_all(add_list)
    SESSION.commit()

def upsert(table, primary_key_map, obj):
    """Decides whether to insert or update an object."""
    first = SESSION.query(table).filter_by(**primary_key_map).first()
    if first != None:
        keys = table.__table__.columns.keys()
        SESSION.query(table).filter_by(**primary_key_map).update(
            {column: getattr(obj, column) for column in keys})
        return None
    return obj

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(
        description="Choose to check for new caps or zero out existing caps.")
    parser.add_argument("-c", "--check", help="Runs the tess check and bot", action="store_true")
    parser.add_argument("-u", "--update", help="Runs only the tess check", action="store_true")
    parser.add_argument("-b", "--bot", help="Runs only the bot", action="store_true")
    # parser.add_argument("-r", "--reset", help="Zeros out existing caps", action="store_true")
    parser.add_argument("-i", "--init", help="Reinitializes the database", action="store_true")
    args = parser.parse_args()
    token = ""
    with open(f"{ABSPATH}/tokens/token.txt", "r") as tokenfile:
        token = tokenfile.read().strip()
    if args.check or args.update:
        # username = "Schep"
        # search_string = "tendril"
        # add_tess_to_db(username, search_string)
        # username = "Milow"
        # search_string = "Ace"
        # add_tess_to_db(username, search_string)
        if args.check:
            run_bot(token)
    elif args.init:
        init_db()
    elif args.bot:
        run_bot(token)

def run_bot(token):
    """Actually runs the bot"""
    # The regular bot definition things
    client = discord.Client()

    @client.event
    async def on_ready():
        """Prints bot initialization info"""
        print('Logged in as')
        print(client.user.name)
        print(client.user.id)
        print('------')

    @client.event
    async def on_message(message):
        """Handles commands based on messages sent"""
        channel = message.channel
        content = message.content
        reaction_pct = random.random()
        with open(f"{ABSPATH}/victim.txt", "r+") as victim_file:
            victim = victim_file.read().strip().split(" ")[0]
            author = message.author.name
            if victim == author and reaction_pct < 1:
                emojis = list(client.get_all_emojis())
                add_emoji = random.sample(emojis, 1)[0]
                # for emoji in emojis:
                #     if emoji.name == "nice":
                #         nice_emoji = emoji
                await client.add_reaction(message, add_emoji)

        # schep_questions = ["does schep have tess", "did schep get tess", "does schep have tess yet"]
        # milow_questions = ["does milow have ace", "did milow get ace", "does milow have ace yet"]
        # if (content.lower() in schep_questions) or (content.lower()[:-1] in schep_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Schep").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await client.send_message(channel, f"Schep does not have Tess, make sure to let him know ;)", tts=True)
        #     else:
        #         await client.send_message(channel, f"Schep finally got Tess!")

        # elif (content.lower() in milow_questions) or (content.lower()[:-1] in milow_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Milow").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await client.send_message(channel, f"Milow does not have Ace.", tts=True)
        #     else:
        #         await client.send_message(channel, f"Milow finally got Ace!")

        if content.startswith('!reboot'):
            role_list = [role.name for role in message.author.roles]
            if "cap handler" in role_list:
                await client.send_message(channel, "Rebooting bots.")
                subprocess.call(['./runschepbot.sh'])

        elif content.lower().startswith("<@!381213507997270017> when will"):
            await client.send_message(channel, f":crystal_ball: Soon:tm: :crystal_ball:")

        elif content.lower().startswith("markdonalds"):
            emojis = client.get_all_emojis()
            for emoji in emojis:
                if emoji.name == "mRage":
                    luke_emoji = emoji
            await client.send_message(channel, f"{luke_emoji}")

        elif content.startswith("!add") and message.author.name == "Roscroft":
            new_row = content[5:]
            new_row += "\n"
            with open(f"{ABSPATH}/responses.csv", "a+") as responses:
                responses.write(new_row)

        elif content.startswith("!player") and message.author.name == "Roscroft":
            victim = content[8:]
            now = datetime.datetime.now()
            with open(f"{ABSPATH}/victim.txt", "w+") as victim_file:
                victim_file.write(f"{victim} {now}")

        elif content.startswith("!pairings") and message.author.name == "Roscroft":
            server = client.get_server("339514092106678273")
            members = list(server.members)
            await client.send_message(channel, f"This would result in {len(members)*len(members)} messages.")
            # for member1 in members:
            #     for member2 in members:
            #         await client.send_message(channel, f"--ship {member1} {member2}")

        else:
            with open(f"{ABSPATH}/responses.csv", "r+") as responses:
                reader = csv.DictReader(responses)
                for response in reader:
                    if response['call'] in content.lower():
                        await client.send_message(channel, f"{response['answer']}")

    async def choose_victim():
        await client.wait_until_ready()
        now = datetime.datetime.now()
        with open(f"{ABSPATH}/victim.txt", "r+") as victim_file:
            victim_list = victim_file.read().strip().split("~")
            victim = victim_list[0]
            try:
                timestamp = f"{victim_list[1]} {victim_list[2]}"
                timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                hours_since = (now-timestamp).seconds//3600
            except IndexError:
                timestamp = None
                hours_since = None
            if timestamp is None or hours_since < 6 or victim == "":
                server = client.get_server("339514092106678273")
                members = list(server.members)
                victim = random.sample(members, 1)[0]
                print(victim.name)
                if not timestamp is None:
                    victim_file.seek(0)
                    victim_file.truncate()
                victim_file.write(f"{victim.name}~{now}")


    client.loop.create_task(choose_victim())
    client.run(token)

if __name__ == "__main__":
    main()
