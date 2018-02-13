#!/usr/bin/python3.6
"""Contains functions used for calculating various pet related things."""
import os
import re
import math
import json
from discord.ext import commands

ABSPATH = os.path.dirname(os.path.abspath(__file__))
STREAK_INCREASE = 11.58
DROPRATES = json.load(open(f"{ABSPATH}/droprates.json"))
BOSS_LIST = DROPRATES.keys()
BOSS_STR = "(" + "|".join(BOSS_LIST) + ")"

def truncate_decimals(num):
    """Replaced my old function with a builtin, can decide on significance."""
    return "{0:.4g}".format(num)

def pet_chance(droprate, threshold, killcount):
    """Calls recursive pet_chance_counter function to determine chance of not getting pet."""
    def pet_chance_counter(droprate, threshold, killcount, threshold_counter):
        """Calculates chance of not getting pet recursively."""
        if killcount < threshold or threshold_counter == 9:
            return math.pow((1-(threshold_counter/droprate)), killcount)
        chance = math.pow((1-(threshold_counter/droprate)), threshold)
        killcount = killcount - threshold
        threshold_counter += 1
        return chance*pet_chance_counter(droprate, threshold, killcount, threshold_counter)
    chance = pet_chance_counter(droprate, threshold, killcount, 1)
    chance *= 100
    return truncate_decimals(chance)

def droprate_reply(match):
    """Returns pet droprate info for normal mode and hard mode."""
    boss = match.group(1)
    boss_entry = DROPRATES[boss]
    pet_info = boss_entry.get("pet")
    if pet_info is None:
        raise ValueError(f"No pet information listed for {boss}.")
    pet_hm_info = boss_entry.get("pet (hm)")
    if boss == "telos":
        out_msg = (f"With <100% enrage, Tess has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}. With >100% enrage, Tess has droprate "
                   f"1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
    else:
        out_msg = (f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}.")
        if pet_hm_info is not None:
            out_msg += (f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and "
                        f"threshold {pet_hm_info[1]}.")
    return out_msg

def chance_helper(match, hardmode):
    """Returns pet chance with the given killcount."""
    boss = match.group(1)
    boss_entry = DROPRATES[boss]
    pet_info = boss_entry.get("pet")
    if pet_info is None:
        raise ValueError(f"No pet information listed for {boss}.")
    pet_hm_info = boss_entry.get("pet (hm)")
    killcount = int(match.group(2))
    if boss == "telos":
        chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
        out_msg = f"Your chance of not getting Tess by now is: {chance}%"
    else:
        if hardmode:
            if pet_hm_info is None:
                out_msg = "No difference in pet chance, using normal mode.\n"
                out_msg += chance_helper(match, 0)
            else:
                chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                out_msg = (f"Your chance of not getting the pet by now in hardmode "
                           f"is: {chance}%")
        else:
            chance = pet_chance(pet_info[0], pet_info[1], killcount)
            out_msg = f"Your chance of not getting the pet by now is: {chance}%"
    return out_msg

def chance_reply(match):
    """Calls chance_helper and specifies normal mode."""
    return chance_helper(match, 0)

def hm_chance_reply(match):
    """Calls chance_helper and specifies hard mode."""
    return chance_helper(match, 1)

def manual_reply(match):
    """Manually calculates pet chance with given threshold and droprate."""
    droprate = int(match.group(1))
    threshold = int(match.group(2))
    killcount = int(match.group(3))
    if droprate < 1:
        raise ValueError("Invalid droprate (use the denominator).")
    elif threshold < 0:
        raise ValueError("Invalid threshold.")
    elif killcount < 0:
        raise ValueError("Invalid killcount")
    else:
        chance = pet_chance(droprate, threshold, killcount)
        out_msg = f"Your chance of not getting the pet by now is: {chance}%"
    return out_msg

def help_reply(match):
    """Returns a help message for pets."""
    del match
    out_msg = ("List of commands:\n$pet <BOSS_STR> - displays pet droprate for boss."
               "\n$pet <BOSS_STR> <killcount> - displays chance of getting boss pet with "
               "given killcount."
               "\n$pet hm <BOSS_STR> <killcount> - displays chance of getting boss pet in"
               " hardmode with given killcount."
               "\n$pet <droprate> <threshold> <killcount> - displays chance of getting "
               "boss pet, with given droprate, threshold, and killcount."
               "$pet help - returns the above list.")
    return out_msg

class Pet():
    """Defines the pet command and functions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def pet(self, ctx, *, args):
        """Runs a regex handler to pick a function based on the provided arguments."""
        try:
            regex_handlers = {}
            regex_handlers[f"{BOSS_STR}"] = droprate_reply
            regex_handlers[f"{BOSS_STR}" + r" (\d+)"] = chance_reply
            regex_handlers[f"{BOSS_STR}" + r" (\d+)"] = hm_chance_reply
            regex_handlers[r"(\d+) (\d+) (\d+)"] = manual_reply
            regex_handlers[r"help"] = help_reply

            for regex, func in regex_handlers.items():
                match = re.compile(regex).fullmatch(args)
                if match:
                    out_msg = func(match)

            await ctx.send(out_msg)

        except ValueError as inst:
            await ctx.send(f"{inst}")

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Pet(bot))
