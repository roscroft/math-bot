"""Contains functions used for calculating various Telos related things."""
import re
import math
from discord.ext import commands

STREAK_INCREASE = 11.58

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

def telos(enrage, streak, lotd):
    """Returns the drop chance at a given enrage and streak, with or without LotD."""
    denominator = math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
    cap = 9
    if denominator < cap:
        return 1.0/cap
    return 1/denominator

def expected_uniques(start_enrage, end_enrage):
    """Given a start enrage and end enrage, returns expected number of uniques and kills."""
    streak_total = math.ceil((end_enrage-start_enrage)/STREAK_INCREASE)
    sum_of_expectations_lotd = 0.0
    sum_of_expectations_no_lotd = 0.0
    for i in range(1, streak_total + 1):
        enrage = start_enrage + STREAK_INCREASE*i
        streak = i
        sum_of_expectations_lotd += telos(enrage, streak, 1)
        sum_of_expectations_no_lotd += telos(enrage, streak, 0)
    sum_of_expectations_no_lotd = truncate_decimals(sum_of_expectations_no_lotd)
    sum_of_expectations_lotd = truncate_decimals(sum_of_expectations_lotd)
    return (sum_of_expectations_no_lotd, sum_of_expectations_lotd, streak_total)

def kills_until_unique(start_enrage):
    """Given a start enrage, return the expected number of kills until a unique is obtained."""
    expected_uniques_lotd = 0.0
    expected_uniques_no_lotd = 0.0
    streak = 0
    while expected_uniques_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        streak += 1
    kills_for_lotd_unique = streak
    streak = 0
    while expected_uniques_no_lotd <= 1:
        enrage = start_enrage + STREAK_INCREASE*streak
        expected_uniques_lotd += telos(enrage, streak, 1)
        expected_uniques_no_lotd += telos(enrage, streak, 0)
        streak += 1
    kills_for_no_lotd_unique = streak
    return (kills_for_no_lotd_unique, kills_for_lotd_unique)

def bounds_reply(match):
    """Returns data on enrage bounds queries."""
    start_enrage = int(match.group(1))
    end_enrage = int(match.group(2))
    if start_enrage > end_enrage:
        out_msg = "Start enrage must be less than end enrage."
    else:
        (no_lotd, lotd, streak_total) = expected_uniques(start_enrage, end_enrage)
        out_msg = (f"Streaking from {start_enrage}% to {end_enrage}%:\n"
                   f"Expected number of kills: {streak_total}\n"
                   f"Expected uniques: {no_lotd} without LotD, {lotd} with LotD.")
    out_msg = f"```{out_msg}```"
    return out_msg

def start_reply(match):
    """Returns data on start enrage queries."""
    out_msg = ""
    start_enrage = int(match.group(1))
    if start_enrage > 4000:
        out_msg = "Using an enrage of 4000 (max chance).\n"
        start_enrage = 4000
    (no_lotd, lotd) = kills_until_unique(start_enrage)
    out_msg += (f"Streaking from {start_enrage}%:\n"
                f"Expected kills until unique: {no_lotd} without LotD, "
                f"{lotd} with LotD.")
    out_msg = f"```{out_msg}```"
    return out_msg

def chance_reply(match):
    """Returns data on individual chance queries."""
    out_msg = ""
    enrage = int(match.group(1))
    streak = int(match.group(2))
    if enrage > 4000:
        out_msg = "Using an enrage of 4000 (max chance).\n"
        enrage = 4000
    no_lotd = telos(enrage, streak, 0)
    lotd = telos(enrage, streak, 1)
    out_msg += (f"A kill with enrage {enrage}% and streak {streak}:\n"
                f"Unique chance: 1/{int(1/no_lotd)} without LotD, "
                f"1/{int(1/lotd)} with LotD.")
    out_msg = f"```{out_msg}```"
    return out_msg

class Telos():
    """Defines the telos command group and directs commands to their appropriate functions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def telos(self, ctx, *, args):
        """Try '$telos help' for detailed telos command information."""
        regex_handlers = {}
        regex_handlers[r"(\d{1,4})% (\d+)%"] = bounds_reply
        regex_handlers[r"(\d{1,4})%"] = start_reply
        regex_handlers[r"(\d{1,4})% (\d+)kc"] = chance_reply

        for regex, func in regex_handlers.items():
            match = re.compile(regex).fullmatch(args)
            if match:
                out_msg = func(match)

        await ctx.send(out_msg)

    @telos.command()
    async def help(self, ctx):
        """Provides a help message for bot usage."""
        out_msg = ("```Telos Cog\n\n"
                   "  $telos <enrage>% <enrage>%    - Expected uniques when streaking from first to"
                   " second enrage.\n"
                   "  $telos <enrage>%              - Expected number of kills until a unique"
                   " starting at the given enrage.\n"
                   "  $telos <enrage>% <streak>kc   - Chance of obtaining a unique with a kill at"
                   " the given enrage and streak.\n"
                   "  $telos pet <kc>               - Chance of not getting Tess by the time you"
                   " hit the given killcount.\n"
                   "  $telos help                   - Returns this message.```")
        await ctx.send(out_msg)

    @telos.command()
    async def pet(self, ctx, killcount):
        """Displays pet chance with the given killcount."""
        killcount = int(killcount)
        droprate = 700
        threshold = 300
        pet = pet_chance(droprate, threshold, killcount)
        out_msg = f"Your chance of not getting Tess by now is: {pet}%"
        out_msg = f"```{out_msg}```"
        await ctx.send(out_msg)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Telos(bot))
