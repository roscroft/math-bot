"""Contains functions used for calculating various pet related things."""
import re
import math
import json
from discord.ext import commands

DROPRATES = json.load(open(f"./cogfiles/droprates.json"))
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
        return f"No pet information listed for {boss}."
    pet_hm_info = boss_entry.get("pet (hm)")
    if boss == "telos":
        out_msg = (f"With <100% enrage, Tess has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}. With >100% enrage, Tess has droprate "
                   f"1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
    else:
        out_msg = (f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold "
                   f"{pet_info[1]}.\n")
        if pet_hm_info is not None:
            out_msg += (f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and "
                        f"threshold {pet_hm_info[1]}.\n")
    return f"{out_msg}"

def chance_helper(match, hardmode):
    """Returns pet chance with the given killcount."""
    boss = match.group(1)
    boss_entry = DROPRATES[boss]
    pet_info = boss_entry.get("pet")
    if pet_info is None:
        return f"No pet information listed for {boss}."
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
    return f"{out_msg}"

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
        out_msg = "Invalid droprate (use the denominator)."
    elif threshold < 0:
        out_msg = "Invalid threshold."
    elif killcount < 0:
        out_msg = "Invalid killcount."
    else:
        chance = pet_chance(droprate, threshold, killcount)
        out_msg = f"Your chance of not getting the pet by now is: {chance}%"
    return f"{out_msg}"

class Pet():
    """Defines the pet command and functions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def pet(self, ctx, *, args):
        """Try '$pet help' for detailed pet command information."""
        if ctx.invoked_subcommand is None:
            regex_handlers = {}
            regex_handlers[f"{BOSS_STR}"] = droprate_reply
            regex_handlers[f"{BOSS_STR}" + r" (\d+)"] = chance_reply
            regex_handlers[f"{BOSS_STR}" + r" (\d+)"] = hm_chance_reply
            regex_handlers[r"(\d+) (\d+) (\d+)"] = manual_reply

            out_msg = ""

            for regex, func in regex_handlers.items():
                match = re.compile(regex).fullmatch(args)
                if match:
                    out_msg = func(match)
            out_msg = f"```{out_msg}```"
            await ctx.send(out_msg)

    @pet.command(name="help")
    async def pet_help(self, ctx):
        """Provides a help message for bot usage."""
        out_msg = ("```Pet Cog\n\n"
                   "  $pet <boss>                   - Displays pet droprate for the given boss.\n"
                   "  $pet <boss> <kc>              - Displays chance of not getting pet by given"
                   " killcount.\n"
                   "  $pet hm <boss> <kc>           - Like above, but hardmode.\n"
                   "  $pet <droprate> <thresh> <kc> - Manual pet function, input values to get"
                   " chance of not getting pet.\n"
                   "  $pet help                     - Returns this message.```")
        await ctx.send(out_msg)

    @commands.command()
    async def bosslist(self, ctx):
        """Returns the list of tracked bosses."""
        bosses = list(DROPRATES.keys())
        out_msg = f"The tracked bosses are: {bosses}"
        out_msg = f"```{out_msg}```"
        await ctx.send(out_msg)

    @commands.command()
    async def droplist(self, ctx, boss):
        """Returns the entire droplist for a specified boss."""
        try:
            drops = list(DROPRATES[boss].keys())
            out_msg = f"The drops for {boss} are: {drops}"
        except KeyError:
            out_msg = f"The requested boss isn't listed."
        out_msg = f"```{out_msg}```"
        await ctx.send(out_msg)

    @commands.command()
    async def drop(self, ctx, *args):
        """Returns the drop chance for a specified boss and drop."""
        boss = args[0].lower()
        item = " ".join(args[1:]).lower()
        try:
            droprate = DROPRATES[boss][item]
            out_msg = f"The droprate for {boss} of {item} is: 1/{droprate}"
        except KeyError:
            out_msg = "Specified drop or boss not listed."
        out_msg = f"```{out_msg}```"
        await ctx.send(out_msg)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Pet(bot))
