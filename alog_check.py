#!/usr/bin/python3.6
"""Runs the alog checks and updates the database/outfiles appropriately"""
import argparse
import datetime
import csv
import json
from html.parser import HTMLParser
import requests
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ABSPATH = os.path.dirname(os.path.abspath(__file__))
ENGINE = create_engine(f"sqlite:///{ABSPATH}/dbs/clan_info.db")
MASTER_SESSION = sessionmaker(bind=ENGINE)
BASE = declarative_base()
REQUEST_SESSION = requests.session()
SESSION = MASTER_SESSION()

class Account(BASE):
    """Defines the class to handle account names and historical caps"""
    __tablename__ = 'account'
    name = Column(String(50), primary_key=True)
    last_cap_time = Column(DateTime)
    total_caps = Column(Integer)

class CheckInfo(BASE):
    """Stores if a user satisfies a check or not"""
    __tablename__ = 'checkInfo'
    name = Column(String(50), primary_key=True)
    search_string = Column(String(50))
    satisfies = Column(Boolean)

def init_db():
    """Initializes and optionally clears out the database"""
    BASE.metadata.bind = ENGINE
    BASE.metadata.create_all(ENGINE)

def upsert(table, primary_key_map, obj):
    """Decides whether to insert or update an object."""
    first = SESSION.query(table).filter_by(**primary_key_map).first()
    if first != None:
        keys = table.__table__.columns.keys()
        SESSION.query(table).filter_by(**primary_key_map).update(
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
    parser.add_argument("-c", "--check", help="Runs cap check.", action="store_true")
    parser.add_argument("-u", "--user", help="Runs user check.", action="store_true")
    parser.add_argument("-i", "--init", help="Reinitializes the databases.", action="store_true")
    args = parser.parse_args()
    if args.check:
        capped_users = []
        clan_parser = MyHTMLParser()
        url_str = ""
        with open(f"{ABSPATH}/tokens/clan_url.txt", "r") as url_file:
            url_str = url_file.read().strip()
        req_data = requests.get(url_str)
        req_html = req_data.text
        clan_parser.feed(req_html)
        clan_list = clan_parser.data
        print(len(clan_list))
        capped_users = add_cap_to_db(clan_list)
        write_to_file(capped_users, 0)
    elif args.user:
        with open(f"{ABSPATH}/checks/checkfile.csv", "r") as check_file:
            reader = csv.DictReader(check_file)
            for check in reader:
                add_check_to_db(check['name'], check['string'])
    elif args.init:
        init_db()

def check_alog(username, search_string):
    """Returns date if search string is in user history, or if it has previously been recorded."""
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
            date = activity['date']
            print(f"{search_string} found: {username}, {date}")
            return activity['date']
    return None

def add_cap_to_db(clan_list):
    """Displays cap info for a list of users."""
    add_list = []
    capped_users = []
    for user in clan_list:
        cap_date = check_alog(user, "capped")
        if cap_date is not None:
            db_date = datetime.datetime.strptime(cap_date, "%d-%b-%Y %H:%M")
            # cap_date = datetime.datetime.strptime(cap_date, "%a, %d %b %Y %H:%M:%S %Z")
            # If the cap date is not None, that means the user has a cap in their adventurer's log.
            # We need to do a few things. First, check to see if the cap date is already stored in
            # the database under last_cap_reported
            previous_report = SESSION.query(
                Account.last_cap_time).filter(Account.name == user).first()
            # Two outcomes: previous report is None, or it has a value. If it is none, then we
            # update it to be cap_date, and store the current time as last_cap_actual.
            # If it has a value, and it is the same as cap_date, we don't do anything. If it
            # has a different value, then we need to update the account dict in the same way as
            # if the previous report is none.
            if previous_report is None or previous_report[0] < db_date:
                # Check to see if the time is in the database. If so, probably indicates a name
                # change. If the time is already in, then we do not need to report it.
                same_time = SESSION.query(
                    Account.name, Account.last_cap_time).filter(
                        Account.last_cap_time == db_date).first()
                if same_time is not None:
                    print("Name change found.")
                else:
                    primary_key_map = {"name": user}
                    account_dict = {"name": user, "last_cap_time": db_date}
                    account_record = Account(**account_dict)
                    add_list.append(upsert(Account, primary_key_map, account_record))
                    print(f"{user} last capped at the citadel on {cap_date}.")
                    capped_users.append((user, cap_date))
                    # print(capped_users)
        else:
            pass
            # print(f"{user} has not capped at the citadel.")

    add_list = [item for item in add_list if item is not None]
    SESSION.add_all(add_list)
    SESSION.commit()
    return capped_users

def add_check_to_db(username, search_string):
    """Updates a user's record with results of the check."""
    add_list = []
    check_res = check_alog(username, search_string)
    if check_res is not None:
        check_report = SESSION.query(CheckInfo.satisfies).filter(CheckInfo.name == username).first()
        if check_report is None or check_report[0] is False:
            primary_key_map = {"name": username}
            account_dict = {"name": username, "satisfies": check_res}
            account_record = CheckInfo(**account_dict)
            add_list.append(upsert(CheckInfo, primary_key_map, account_record))
    add_list = [item for item in add_list if item is not None]
    SESSION.add_all(add_list)
    SESSION.commit()

def write_to_file(users, type_code):
    """Writes new caps to a file, which is read when the bot runs."""
    file_dict = {0: "new_caps.txt"}
    with open(f"{ABSPATH}/textfiles/{file_dict[type_code]}", "w+") as info_file:
        if type_code == 0:
            for (user, cap_date) in users:
                datetime_list = cap_date.split(" ")
                date_report = datetime_list[0]
                time_report = datetime_list[1]
                msg = f"{user} has capped at the citadel on {date_report} at {time_report}.\n"
                info_file.write(msg)

if __name__ == "__main__":
    main()
