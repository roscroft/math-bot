#!/usr/bin/python3.6
"""Runs the telos droprate bot"""
import argparse
import re
import json
import math
from decimal import Decimal
import discord

ABSPATH = "/home/austin/Documents/schepbot"

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(
        description="Choose to check for new caps or zero out existing caps.")
    parser.add_argument("-b", "--bot", help="Runs only the bot", action="store_true")
    args = parser.parse_args()
    token = ""
    with open(f"{ABSPATH}/tokens/token2.txt", "r") as tokenfile:
        token = tokenfile.read().strip()
    if args.bot:
        run_bot(token)

def run_bot(token):
    """Actually runs the bot"""
    # The regular bot definition things
    client = discord.Client()
    streak_increase = 11.58

    def pet_chance(droprate, threshold, killcount):
        """Calls recursive pet_chance_counter function to determine chance of getting pet."""
        def pet_chance_counter(droprate, threshold, killcount, threshold_counter):
            """Calculates chance of getting pet recursively."""
            if killcount < threshold or threshold_counter == 9:
                return math.pow((1-(threshold_counter/droprate)), killcount)
            chance = math.pow((1-(threshold_counter/droprate)), threshold)
            killcount = killcount - threshold
            threshold_counter += 1
            return chance*pet_chance_counter(droprate, threshold, killcount, threshold_counter)
        chance = 1-(pet_chance_counter(droprate, threshold, killcount, 1))
        chance *= 100
        return truncate_decimals(chance)

    def telos(enrage, streak, lotd):
        """Returns the drop chance at a given enrage and streak, with or without LotD."""
        droprate = 1/math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
        cap = 1.0/9
        if droprate > cap:
            return cap
        return droprate

    def expected_uniques(start_enrage, end_enrage):
        """Given a start enrage and end enrage, returns expected number of uniques and kills."""
        start_enrage = int(start_enrage)
        end_enrage = int(end_enrage)
        streak_total = math.ceil((end_enrage-start_enrage)/streak_increase)
        sum_of_expectations_lotd = 0.0
        sum_of_expectations_no_lotd = 0.0
        for i in range(1, streak_total + 1):
            enrage = start_enrage + streak_increase*i
            streak = i
            sum_of_expectations_lotd += telos(enrage, streak, 1)
            sum_of_expectations_no_lotd += telos(enrage, streak, 0)
        sum_of_expectations_no_lotd = truncate_decimals(sum_of_expectations_no_lotd)
        sum_of_expectations_lotd = truncate_decimals(sum_of_expectations_lotd)
        return (sum_of_expectations_no_lotd, sum_of_expectations_lotd, streak_total)

    def kills_until_unique(start_enrage):
        """Given a start enrage, return the expected number of kills until a unique is obtained."""
        start_enrage = int(start_enrage)
        expected_uniques_lotd = 0.0
        expected_uniques_no_lotd = 0.0
        streak = 0
        while expected_uniques_lotd <= 1:
            enrage = start_enrage + streak_increase*streak
            expected_uniques_lotd += telos(enrage, streak, 1)
            streak += 1
        kills_for_lotd_unique = streak
        streak = 0
        while expected_uniques_no_lotd <= 1:
            enrage = start_enrage + streak_increase*streak
            expected_uniques_lotd += telos(enrage, streak, 1)
            expected_uniques_no_lotd += telos(enrage, streak, 0)
            streak += 1
        kills_for_no_lotd_unique = streak
        return (kills_for_no_lotd_unique, kills_for_lotd_unique)

    def truncate_decimals(num):
        """Checks for significant figures and truncates decimals accordingly"""
        #Apparently I have to write my own damn significant figures checker
        if num % 1 == 0:
            result = num
        elif num > 10000:
            result = Decimal(num).quantize(Decimal('1.'))
        else:
            def first_power_of_ten(power, num):
                """Returns the first power of ten less than a number"""
                if num > power:
                    return power
                return first_power_of_ten(power/10, num)
            power = first_power_of_ten(1000, num)
            prec = power/1000
            result = Decimal(num).quantize(Decimal(str(prec)))
        return result

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
        content = message.content
        channel = message.channel

        if content.startswith("$telos"):
            # A couple different syntax options. If there are two percentages, consider it a request
            # For streaking from the lower to the higher. We'll build regular expressions to parse.
            try:
                bounds_str = r"\$telos (\d{1,4})% (\d{1,4})%"
                bounds_regex = re.compile(bounds_str)
                isbounds = bounds_regex.fullmatch(content)
                start_str = r"\$telos (\d{1,4})%"
                start_regex = re.compile(start_str)
                isstart = start_regex.fullmatch(content)
                chance_str = r"\$telos (\d{1,4})% (\d{1,4})kc"
                chance_regex = re.compile(chance_str)
                ischance = chance_regex.fullmatch(content)
                pet_str = r"\$telos pet (\d{1,5})"
                pet_regex = re.compile(pet_str)
                ispet = pet_regex.fullmatch(content)
                help_str = r"\$telos help"
                help_regex = re.compile(help_str)
                ishelp = help_regex.fullmatch(content)
                out_msg = "Nothing to return."
                if isbounds:
                    start_enrage = isbounds.group(1)
                    end_enrage = isbounds.group(2)
                    if start_enrage > end_enrage:
                        raise ValueError("Start enrage must be less than end enrage.")
                    (no_lotd, lotd, streak_total) = expected_uniques(start_enrage, end_enrage)
                    out_msg = (f"Streaking from {start_enrage}% to {end_enrage}%:\n"
                               f"Expected number of kills: {streak_total}\n"
                               f"Expected uniques: {no_lotd} without LotD, {lotd} with LotD.")
                elif isstart:
                    start_enrage = isstart.group(1)
                    if int(start_enrage) > 4000:
                        await client.send_message(channel, "Using an enrage of 4000 (max chance).")
                        start_enrage = "4000"
                    (no_lotd, lotd) = kills_until_unique(start_enrage)
                    out_msg = (f"Streaking from {start_enrage}%:\n"
                               f"Expected kills until unique: {no_lotd} without LotD, "
                               f"{lotd} with LotD.")
                elif ischance:
                    enrage = int(ischance.group(1))
                    streak = int(ischance.group(2))
                    if enrage > 4000:
                        await client.send_message(channel, "Using an enrage of 4000 (max chance).")
                        enrage = 4000
                    no_lotd = telos(enrage, streak, 0)
                    lotd = telos(enrage, streak, 1)
                    out_msg = (f"A kill with enrage {enrage}% and streak {streak}:\n"
                               f"Unique chance: 1/{int(1/no_lotd)} without LotD, "
                               f"1/{int(1/lotd)} with LotD.")
                elif ispet:
                    killcount = int(ispet.group(1))
                    droprate = 700
                    threshold = 300
                    pet = pet_chance(droprate, threshold, killcount)
                    out_msg = f"Your percent chance of getting Tess by now is: {pet}%"
                elif ishelp:
                    out_msg = ("List of commands:\n$telos <enrage>% <enrage>% - returns expected "
                               "uniques when streaking from the first enrage to the second enrage."
                               "\n$telos <enrage>% - returns expected number of kills until a "
                               "unique is obtained when starting at the given enrage.\n"
                               "$telos <enrage>% <streak>kc - returns the chance of obtaining a "
                               "unique with a kill at the given enrage and streak.\n"
                               "$telos pet <killcount> - returns the chance of getting the pet "
                               "by the time you have hit the given killcount.\n"
                               "$telos help - returns the above list.")
                if out_msg != "Nothing to return.":
                    await client.send_message(channel, out_msg)
            except ValueError as inst:
                await client.send_message(channel, f"{inst}")

        elif content.startswith("$halp"):
            await client.send_message(channel,
                                      ("Usage: $chance <streak> <enrage> <lotd>, "
                                       "where <lotd> is 1 or 0"))

        elif content.startswith("$pet"):
            query_list = content.split(" ")
            if len(query_list) == 2 or len(query_list) == 3 or (len(query_list) == 4 and query_list[3] == "hm"):
                try:
                    boss = query_list[1].lower()
                    droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
                    if not boss in droprate_json:
                        raise KeyError("Listed boss not in table.")
                    boss_entry = droprate_json[boss]
                    pet_info = boss_entry.get("pet")
                    pet_hm_info = boss_entry.get("pet (hm)")
                    if len(query_list) == 2:
                        if boss == "telos":
                            await client.send_message(channel, f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold {pet_info[1]} with <100% enrage.")
                            await client.send_message(channel, f"The pet from {boss} has droprate 1/{pet_hm_info[0]} and threshold {pet_hm_info[1]} with >100% enrage.")
                        else:
                            if pet_info is not None:
                                await client.send_message(channel, f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold {pet_info[1]}.")
                            if pet_hm_info is not None:
                                await client.send_message(channel, f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
                            if pet_info is None and pet_hm_info is None:
                                await client.send_message(channel, f"No pet information found for {boss}.")
                    elif len(query_list) == 3 or (len(query_list) == 4 and query_list[3] == "hm"):
                        killcount = int(query_list[2])
                        # await client.send_message(channel, "Calculating % chance of getting pet by current killcount...")
                        if boss == "telos":
                            chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                            await client.send_message(channel, f"Your percent chance of getting Tess by now is: {chance}%")
                        else:
                            if len(query_list) == 4 and query_list[3] == "hm":
                                if pet_hm_info is None:
                                    await client.send_message(channel, f"There is no different droprate for the hardmode version of this boss (if there even is one).")
                                else:
                                    chance = pet_chance(pet_hm_info[0], pet_hm_info[1], killcount)
                                    await client.send_message(channel, f"Your percent chance of getting the pet by now in hardmode is: {chance}%")
                            elif pet_info is not None:
                                chance = pet_chance(pet_info[0], pet_info[1], killcount)
                                await client.send_message(channel, f"Your percent chance of getting the pet by now is: {chance}%")
                            elif pet_info is None and pet_hm_info is None:
                                await client.send_message(channel, f"No pet information found for {boss}.")
                except (KeyError, ValueError) as inst:
                    await client.send_message(channel, f"{inst}")
            elif len(query_list) != 4:
                await client.send_message(channel, "Usage: $pet <droprate> <thresh> <killcount>")
            else:
                try:
                    droprate = int(query_list[1])
                    thresh = int(query_list[2])
                    killcount = int(query_list[3])
                    if droprate < 1:
                        raise ValueError("Invalid droprate (use the denominator).")
                    elif thresh < 0:
                        raise ValueError("Invalid threshold.")
                    elif killcount < 0:
                        raise ValueError("Invalid killcount")
                    else:
                        chance = pet_chance(droprate, thresh, killcount)
                        # await client.send_message(channel, "Calculating % chance of getting pet by current killcount...")
                        await client.send_message(channel, f"Your percent chance of getting the pet by now is: {chance}%")
                except (IndexError, TypeError):
                    await client.send_message(channel, "Usage: $pet <droprate> <thresh> <killcount> or $pet <boss> <killcount> or $pet <boss> <killcount> hm.")
                except ValueError as inst:
                    await client.send_message(channel, f"{inst}")

        elif content.startswith("$bosslist"):
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            bosses = list(droprate_json.keys())
            await client.send_message(channel, f"The tracked bosses are: {bosses}")

        elif content.startswith("$droplist"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droplist = droprate_json[boss]
                drops = list(droplist.keys())
                await client.send_message(channel, f"The drops for {boss} are: {drops}")
            except KeyError:
                await client.send_message(channel, "The requested boss isn't listed.")

        elif content.startswith("$drop"):
            query_list = content.split(" ")
            boss = query_list[1].lower()
            item = " ".join(query_list[2:]).lower()
            droprate_json = json.load(open(f"{ABSPATH}/droprates.json"))
            try:
                droprate = droprate_json[boss][item]
                await client.send_message(channel, f"The droprate for {boss} of {item} is: 1/{droprate}")
            except KeyError:
                await client.send_message(channel, "Specified drop or boss not listed.")

    client.run(token)

if __name__ == "__main__":
    main()
