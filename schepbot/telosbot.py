#!/usr/bin/python3.6
"""Runs the telos droprate bot"""
import argparse
import json
import math
from decimal import Decimal
import discord

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(
        description="Choose to check for new caps or zero out existing caps.")
    parser.add_argument("-b", "--bot", help="Runs only the bot", action="store_true")
    args = parser.parse_args()
    if args.bot:
        token = ""
        with open("/home/austin/Documents/schepbot/tokens/token2.txt", "r") as tokenfile:
            token = tokenfile.read().strip()
        run_bot(token)

def run_bot(token):
    """Actually runs the bot"""
    # The regular bot definition things
    client = discord.Client()

    def pet_chance(droprate, threshold, kc):
        def pet_chance_counter(droprate, threshold, kc, threshold_counter):
            if kc < threshold or threshold_counter == 9:
                return math.pow((1-(threshold_counter/droprate)), kc)
            chance = math.pow((1-(threshold_counter/droprate)), threshold)
            kc = kc - threshold
            threshold_counter += 1
            return chance*pet_chance_counter(droprate, threshold, kc, threshold_counter)
        chance = pet_chance_counter(droprate, threshold, kc, 1)
        chance *= 100
        return truncate_decimals(chance)

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
        if message.content.startswith("$chance"):
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
                    if streak < 0:
                        raise ValueError("Invalid streak.")
                    elif enrage < 0 or enrage > 4000:
                        raise ValueError("Invalid enrage.")
                    elif lotd != 0 and lotd != 1:
                        raise ValueError("Invalid lotd value.")
                    else:
                        droprate = math.floor(10000.0/(10+0.25*(enrage+25*lotd)+3*streak))
                        if lotd == 1:
                            lotd_string = "with"
                        else:
                            lotd_string = "without"
                        out_string = (f"The chance of a unique at Telos with streak {streak} and "
                                      f"enrage {enrage} {lotd_string} LotD is: 1/{droprate}.")
                        await client.send_message(message.channel, out_string)
                except (IndexError, TypeError):
                    await client.send_message(message.channel,
                                              ("Usage: $chance <streak> <enrage> <lotd>, "
                                               "where <lotd> is 1 or 0"))
                except ValueError as inst:
                    await client.send_message(message.channel, f"{inst}")

        elif message.content.startswith("$halp"):
            await client.send_message(message.channel,
                                      ("Usage: $chance <streak> <enrage> <lotd>, "
                                       "where <lotd> is 1 or 0"))

        elif message.content.startswith("$pet"):
            query_list = message.content.split(" ")
            if len(query_list) == 2 or len(query_list) == 3 or (len(query_list) == 4 and query_list[3] == "hm"):
                try:
                    boss = query_list[1].lower()
                    droprate_json = json.load(open("/home/austin/Documents/schepbot/droprates.json"))
                    if not boss in droprate_json:
                        raise KeyError("Listed boss not in table.")
                    boss_entry = droprate_json[boss]
                    pet_info = boss_entry.get("pet")
                    pet_hm_info = boss_entry.get("pet (hm)")
                    if len(query_list) == 2:
                        if boss == "telos":
                            await client.send_message(message.channel, f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold {pet_info[1]} with <100% enrage.")
                            await client.send_message(message.channel, f"The pet from {boss} has droprate 1/{pet_hm_info[0]} and threshold {pet_hm_info[1]} with >100% enrage.")
                        else:
                            if pet_info is not None:
                                await client.send_message(message.channel, f"The pet from {boss} has droprate 1/{pet_info[0]} and threshold {pet_info[1]}.")
                            if pet_hm_info is not None:
                                await client.send_message(message.channel, f"The pet from hardmode {boss} has droprate 1/{pet_hm_info[0]} and threshold {pet_hm_info[1]}.")
                            if pet_info is None and pet_hm_info is None:
                                await client.send_message(message.channel, f"No pet information found for {boss}.")
                    elif len(query_list) == 3 or (len(query_list) == 4 and query_list[3] == "hm"):
                        kc = int(query_list[2])
                        # await client.send_message(message.channel, "Calculating % chance of not getting pet by current kc...")
                        if boss == "telos":
                            chance = pet_chance(pet_hm_info[0], pet_hm_info[1], kc)
                            await client.send_message(message.channel, f"Your percent chance of not getting Tess by now is: {chance}%")
                        else:
                            if len(query_list) == 4 and query_list[3] == "hm":
                                if pet_hm_info is None:
                                    await client.send_message(message.channel, f"There is no different droprate for the hardmode version of this boss (if there even is one).")
                                else:
                                    chance = pet_chance(pet_hm_info[0], pet_hm_info[1], kc)
                                    await client.send_message(message.channel, f"Your percent chance of not getting the pet by now in hardmode is: {chance}%")
                            elif pet_info is not None:
                                chance = pet_chance(pet_info[0], pet_info[1], kc)
                                await client.send_message(message.channel, f"Your percent chance of not getting the pet by now is: {chance}%")
                            elif pet_info is None and pet_hm_info is None:
                                await client.send_message(message.channel, f"No pet information found for {boss}.")
                except (KeyError, ValueError) as inst:
                    await client.send_message(message.channel, f"{inst}")
            elif len(query_list) != 4:
                await client.send_message(message.channel, "Usage: $pet <droprate> <thresh> <kc>")
            else:
                try:
                    droprate = int(query_list[1])
                    thresh = int(query_list[2])
                    kc = int(query_list[3])
                    if droprate < 1:
                        raise ValueError("Invalid droprate (use the denominator).")
                    elif thresh < 0:
                        raise ValueError("Invalid threshold.")
                    elif kc < 0:
                        raise ValueError("Invalid killcount")
                    else:
                        chance = pet_chance(droprate, thresh, kc)
                        # await client.send_message(message.channel, "Calculating % chance of not getting pet by current kc...")
                        await client.send_message(message.channel, f"Your percent chance of not getting the pet by now is: {chance}%")
                except (IndexError, TypeError):
                    await client.send_message(message.channel, "Usage: $pet <droprate> <thresh> <kc> or $pet <boss> <kc> or $pet <boss> <kc> hm.")
                except ValueError as inst:
                    await client.send_message(message.channel, f"{inst}")

        elif message.content.startswith("$bosslist"):
            droprate_json = json.load(open("/home/austin/Documents/schepbot/droprates.json"))
            bosses = list(droprate_json.keys())
            await client.send_message(message.channel, f"The tracked bosses are: {bosses}")

        elif message.content.startswith("$droplist"):
            query_list = message.content.split(" ")
            boss = query_list[1].lower()
            droprate_json = json.load(open("/home/austin/Documents/schepbot/droprates.json"))
            try:
                droplist = droprate_json[boss]
                drops = list(droplist.keys())
                await client.send_message(message.channel, f"The drops for {boss} are: {drops}")
            except KeyError:
                await client.send_message(message.channel, "The requested boss isn't listed.")

        elif message.content.startswith("$drop"):
            query_list = message.content.split(" ")
            boss = query_list[1].lower()
            item = " ".join(query_list[2:]).lower()
            droprate_json = json.load(open("/home/austin/Documents/schepbot/droprates.json"))
            try: 
                droprate = droprate_json[boss][item]
                await client.send_message(message.channel, f"The droprate for {boss} of {item} is: 1/{droprate}")
            except KeyError:
                await client.send_message(message.channel, "Specified drop or boss not listed.")

    client.run(token)

if __name__ == "__main__":
    main()
