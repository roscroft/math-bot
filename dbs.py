#!/usr/bin/python3.6
"""Runs the alog checks and updates the database/outfiles appropriately"""
import os
import argparse
from html.parser import HTMLParser
import requests
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ABSPATH = os.path.dirname(os.path.abspath(__file__))
ENGINE = create_engine(f"sqlite:///{ABSPATH}/clan.db")
MASTER_SESSION = sessionmaker(bind=ENGINE)
BASE = declarative_base()
REQUEST_SESSION = requests.session()
SESSION = MASTER_SESSION()

class Account(BASE):
    """Relates Discord IDs to RSNs"""
    __tablename__ = 'account'
    disc_id = Column(String(50), primary_key=True)
    rsn = Column(String(50), primary_key=True)
    last_cap_time = Column(DateTime)
    total_caps = Column(Integer)
    search_string = Column(String(50))
    satisfies = Column(Boolean)

class XP(BASE):
    """Stores users, dates, and skill levels/xp"""
    __tablename__ = 'xp'
    xp_id = Column(Integer, primary_key=True)
    disc_id = Column(String(50), ForeignKey("account.disc_id"), nullable=False)
    rsn = Column(String(50), ForeignKey("account.rsn"), nullable=False)
    date = Column(DateTime)
    attack_level = Column(Integer)
    attack_xp = Column(Integer)
    defence_level = Column(Integer)
    defence_xp = Column(Integer)
    strength_level = Column(Integer)
    strength_xp = Column(Integer)
    constitution_level = Column(Integer)
    constitution_xp = Column(Integer)
    ranged_level = Column(Integer)
    ranged_xp = Column(Integer)
    prayer_level = Column(Integer)
    prayer_xp = Column(Integer)
    magic_level = Column(Integer)
    magic_xp = Column(Integer)
    cooking_level = Column(Integer)
    cooking_xp = Column(Integer)
    woodcutting_level = Column(Integer)
    woodcutting_xp = Column(Integer)
    fletching_level = Column(Integer)
    fletching_xp = Column(Integer)
    fishing_level = Column(Integer)
    fishing_xp = Column(Integer)
    firemaking_level = Column(Integer)
    firemaking_xp = Column(Integer)
    crafting_level = Column(Integer)
    crafting_xp = Column(Integer)
    smithing_level = Column(Integer)
    smithing_xp = Column(Integer)
    mining_level = Column(Integer)
    mining_xp = Column(Integer)
    herblore_level = Column(Integer)
    herblore_xp = Column(Integer)
    agility_level = Column(Integer)
    agility_xp = Column(Integer)
    theiving_level = Column(Integer)
    theiving_xp = Column(Integer)
    slayer_level = Column(Integer)
    slayer_xp = Column(Integer)
    farming_level = Column(Integer)
    farming_xp = Column(Integer)
    runecrafting_level = Column(Integer)
    runecrafting_xp = Column(Integer)
    hunter_level = Column(Integer)
    hunter_xp = Column(Integer)
    construction_level = Column(Integer)
    construction_xp = Column(Integer)
    summoning_level = Column(Integer)
    summoning_xp = Column(Integer)
    dungeoneering_level = Column(Integer)
    dungeoneering_xp = Column(Integer)
    divination_level = Column(Integer)
    divination_xp = Column(Integer)
    invention_level = Column(Integer)
    invention_xp = Column(Integer)

def init_db():
    """Initializes and optionally clears out the clan info database"""
    BASE.metadata.bind = ENGINE
    BASE.metadata.create_all(ENGINE)

def upsert(session, table, primary_key_map, obj):
    """Decides whether to insert or update an object."""
    first = session.query(table).filter_by(**primary_key_map).first()
    if first != None:
        keys = table.__table__.columns.keys()
        session.query(table).filter_by(**primary_key_map).update(
            {column: getattr(obj, column) for column in keys})
        return None
    return obj

class MyHTMLParser(HTMLParser):
    """Builds an HTML parser."""
    def handle_data(self, data):
        if data.startswith("\nvar data;"):
            list_start = data.find("[")
            list_end = data.find("]")
            clan_members = data[list_start+1:list_end]
            clan_members = clan_members.split(", ")
            clan_list = []
            for item in clan_members:
                add_item = item[1:-1]
                add_item = add_item.replace(u'\xa0', u' ')
                clan_list.append(add_item)
            self.data = clan_list

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(description="Choose script actions.")
    parser.add_argument("-i", "--init", help="Reinitializes the database.", action="store_true")
    args = parser.parse_args()
    if args.init:
        init_db()

if __name__ == "__main__":
    main()
