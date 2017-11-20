#!/usr/bin/python3.6
"""Runs the telos droprate bot"""
import argparse
import math
import discord
from decimal import Decimal

def main():
    """Runs the stuff."""
    parser = argparse.ArgumentParser(
        description="Choose to check for new caps or zero out existing caps.")
    parser.add_argument("-b", "--bot", help="Runs only the bot", action="store_true")
    args = parser.parse_args()
    if args.bot:
        token = ""
        with open("/home/austin/Documents/schepbot/token2.txt", "r") as tokenfile:
            token = tokenfile.read().strip()
        run_bot(token)

def run_bot(token):
    """Actually runs the bot"""
    # The regular bot definition things
    client = discord.Client()

    def pet_chance(droprate, threshold, kc, threshold_counter):
        if kc < threshold or threshold_counter == 9:
            return math.pow((1-(threshold_counter/droprate)), kc)
        chance = math.pow((1-(threshold_counter/droprate)), threshold)
        kc = kc - threshold
        threshold_counter += 1
        return chance*pet_chance(droprate, threshold, kc, threshold_counter)

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
            await client.send_message(message.channel, "Calculating % chance of not getting pet by current kc...")
            query_list = message.content.split(" ")
            if len(query_list) != 4:
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
                        chance = pet_chance(droprate, thresh, kc, 1)*100
                        chance = truncate_decimals(chance)
                        await client.send_message(message.channel, f"Your percent chance of not getting the pet by now is: {chance}%")
                except (IndexError, TypeError):
                    await client.send_message(message.channel, "Usage: $pet <droprate> <thresh> <kc>")
                except ValueError as inst:
                    await client.send_message(message.channel, f"{inst}")

    client.run(token)

if __name__ == "__main__":
    main()
