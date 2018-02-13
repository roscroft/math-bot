#!/usr/bin/python3.6
"""Runs the bot defined in mathbot.py."""
import argparse
import logging
import mathbot
import config
import discord

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(description="Choose script actions.")
    parser.add_argument("-b", "--bot", help="Runs only the bot.", action="store_true")
    args = parser.parse_args()
    if args.bot:
        run_bot()

def run_bot():
    """Actually runs the bot"""
    logger = logging.getLogger('mathbot')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='mathbot.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    client = mathbot.MathBot()
    client.loop.create_task(choose_victim())
    client.loop.create_task(report_caps())
    client.run(config.token)

if __name__ == "__main__":
    main()
