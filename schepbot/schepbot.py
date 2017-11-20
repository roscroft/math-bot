#!/usr/bin/python3.6
"""Reads in clan data html and parses out the list of clan members."""
import subprocess
import math
import argparse
import json
import requests
import discord
from sqlalchemy import Column, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    with open("/home/austin/Documents/schepbot/url.txt", "r") as url_file:
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
    parser.add_argument("-f", "--force", help="Force sends a message", action="store_true")
    args = parser.parse_args()
    # if args.reset:
    #     erase_caps()
    if args.check or args.update:
        username = "Tendril drop"
        search_string = "tendril"
        add_tess_to_db(username, search_string)
        username = "Milow"
        search_string = "Ace"
        add_tess_to_db(username, search_string)
        token = ""
        with open("/home/austin/Documents/schepbot/token.txt", "r") as tokenfile:
            token = tokenfile.read().strip()
        if args.check:
            run_bot(token)
    elif args.init:
        init_db()
    elif args.bot:
        token = ""
        with open("/home/austin/Documents/schepbot/token.txt", "r") as tokenfile:
            token = tokenfile.read().strip()
        run_bot(token)
    elif args.force:
        token = ""
        with open("/home/austin/Documents/schepbot/token.txt", "r") as tokenfile:
            token = tokenfile.read().strip()
        run_bot(token)

def run_bot(token):
    """Actually runs the bot"""
    # The regular bot definition things
    response_map = {
        "does waffle have a life": "Waffle does not have a life.",
        "what's that smell": "It's gyne.",
        "raqle": "sgb btw"
    }

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
        schep_questions = ["does schep have tess", "did schep get tess", "does schep have tess yet"]
        milow_questions = ["does milow have ace", "did milow get ace", "does milow have ace yet"]
        if (message.content.lower() in schep_questions) or (message.content.lower()[:-1] in schep_questions):
            schep_has_tess = SESSION.query(
                HasTess.has_tess).filter(HasTess.name == "Tendril drop").first()
            if schep_has_tess is None or schep_has_tess[0] is False:
                await client.send_message(message.channel, f"Schep does not have Tess.", tts=True)
            else:
                await client.send_message(message.channel, f"Schep finally got Tess!")
        
        elif (message.content.lower() in milow_questions) or (message.content.lower()[:-1] in milow_questions):
            schep_has_tess = SESSION.query(
                HasTess.has_tess).filter(HasTess.name == "Milow").first()
            if schep_has_tess is None or schep_has_tess[0] is False:
                await client.send_message(message.channel, f"Milow does not have Ace.", tts=True)
            else:
                await client.send_message(message.channel, f"Milow finally got Ace!")

        elif message.content.startswith('!update'):
            role_list = [role.name for role in message.author.roles]
            if "cap handler" in role_list:
                await client.send_message(message.channel, "Manually updating...")
                subprocess.call(['./runschepbot.sh'])

        elif message.content.lower().startswith("<@!381213507997270017> when will"):
            emojis = client.get_all_emojis()
            for emoji in emojis:
                if emoji.name == "luke":
                    luke_emoji = emoji
            await client.send_message(message.channel, f"{luke_emoji} Soon:tm: {luke_emoji}")

        elif message.content.lower().startswith("markdonalds"):
            emojis = client.get_all_emojis()
            for emoji in emojis:
                if emoji.name == "mRage":
                    luke_emoji = emoji
            await client.send_message(message.channel, f"{luke_emoji}")

        elif message.content.lower() in response_map:
            await client.send_message(message.channel, f"{response_map[message.content.lower()]}")

        elif message.content.startswith("$chance"):
            query_list = message.content.split(" ")
            if len(query_list) != 4:
                await client.send_message(message.channel,
                                          ("Usage: $chance <streak> <enrage> <lotd>, "
                                           "where <lotd> is 1 or 0"))
            else:
                try:
                    streak = int(query_list[1])
                    enrage = int(query_list[2])
                    lotd = int(query_list[3])
                    droprate = math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
                    if lotd == 1:
                        lotd_string = "with"
                    else:
                        lotd_string = "without"
                    out_string = (f"The chance of a unique at Telos with streak {streak} and "
                                    f"enrage {enrage} {lotd_string} LotD is: 1/{droprate}")
                    await client.send_message(message.channel, out_string)
                except (IndexError, TypeError):
                    await client.send_message(message.channel,
                                              ("Usage: $chance <streak> <enrage> <lotd>, "
                                               "where <lotd> is 1 or 0"))

        elif message.content.startswith("$halp"):
            await client.send_message(message.channel,
                                          ("Usage: $chance <streak> <enrage> <lotd>, "
                                           "where <lotd> is 1 or 0"))

    client.run(token)

if __name__ == "__main__":
    main()
