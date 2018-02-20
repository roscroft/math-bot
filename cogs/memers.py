#!/usr/bin/python3.6
"""Defines commands used for the Memers server."""
import json
import random
import asyncio
import discord
from discord.ext import commands
import config

def add_to_json(filename, call, response):
    """Adds a record to the given json file."""
    with open(f"./cogfiles/{filename}", "r+") as response_file:
        responses = json.load(response_file)
    responses[call] = response
    with open(f"./cogfiles/{filename}", "w") as response_file:
        json.dump(responses, response_file)

def remove_from_json(filename, call):
    """Removes the given record from the given json file."""
    with open(f"./cogfiles/{filename}", "r+") as response_file:
        responses = json.load(response_file)
    response = responses[call]
    if call in responses:
        responses.pop(call)
        with open(f"./cogfiles/{filename}", "w") as response_file:
            json.dump(responses, response_file)
        return response
    return None

def list_from_json(filename):
    """Lists all records from the given json file."""
    out_msg = "Call -> Response\n"
    with open(f"./cogfiles/{filename}") as response_file:
        responses = json.load(response_file)
        for call, response in responses.items():
            out_msg += f"{call} -> {response}\n"
    out_msg = f"```{out_msg}```"
    return out_msg

class Memers():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.victim = ""
        self.bot.victim_choice = self.bot.loop.create_task(self.choose_victim())

    @commands.group()
    async def cool(self, ctx):
        """Says if a user is cool.
        In reality this just checks if a subcommand is being invoked.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send('No, {0.subcommand_passed} is not cool'.format(ctx))

    @cool.command(name='bot')
    async def _bot(self, ctx):
        """Is the bot cool?"""
        await ctx.send('Yes, the bot is cool.')

    @commands.command()
    async def markdonalds(self, ctx):
        """Lets the command markdonalds return the mRage emoji."""
        mrage = self.bot.get_emoji(413441118102093824)
        await ctx.send(f"{mrage}")

    @commands.command()
    async def vis(self, ctx):
        """Corrects usage of !vis."""
        await ctx.send(f"It's actually ~vis")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def add(self, ctx, call, response):
        """Adds a new call/response pair. Bot owner only!"""
        filename = "responses.json"
        add_to_json(filename, call, response)
        out_msg = f"Added text call/response pair {call} -> {response}!"
        await ctx.send(out_msg)

    @commands.command(name="rm", hidden=True)
    @commands.is_owner()
    async def remove(self, ctx, call):
        """Removes a call/response pair. Bot owner only!"""
        filename = "responses.json"
        response = remove_from_json(filename, call)
        if response is not None:
            out_msg = f"Removed text call/response pair {call} -> {response}!"
        else:
            out_msg = f"Text call {call} not found."
        await ctx.send(out_msg)

    @commands.command()
    async def calls(self, ctx):
        """Lists the existing call/responses pairs."""
        filename = "responses.json"
        out_msg = list_from_json(filename)
        await ctx.send(out_msg)

    @commands.group(invoke_without_command=True)
    async def img(self, ctx, call):
        """Provides the parser for image call/response commands."""
        if ctx.invoked_subcommand is None and ctx.channel.id != config.main_channel:
            with open(f"./cogfiles/image_responses.json", "r+") as response_file:
                responses = json.load(response_file)
                try:
                    found_url = responses[call]
                    image_embed = discord.Embed()
                    image_embed.set_image(url=found_url)
                    await ctx.send(content=None, embed=image_embed)
                except KeyError:
                    print("No response in file!")

    @img.command(name="add")
    @commands.is_owner()
    async def _add(self, ctx, call, image_url):
        """Adds a new image response. Bot owner only!"""
        filename = "image_responses.json"
        add_to_json(filename, call, image_url)
        out_msg = f"Added image call/response pair {call} -> <{image_url}>!"
        await ctx.send(out_msg)

    @img.command(name="rm")
    @commands.is_owner()
    async def _remove(self, ctx, call):
        """Removes an image response. Bot owner only!"""
        filename = "image_responses.json"
        image_url = remove_from_json(filename, call)
        if image_url is not None:
            out_msg = f"Removed image call/response pair {call} -> <{image_url}>!"
        else:
            out_msg = f"Image call {call} not found."
        await ctx.send(out_msg)

    @img.command(name="calls")
    async def _calls(self, ctx):
        """Lists the existing image call/responses pairs."""
        filename = "image_responses.json"
        out_msg = list_from_json(filename)
        await ctx.send(out_msg)

    @commands.command()
    @commands.is_owner()
    async def player(self, ctx, player):
        """Sets a new player victim. Bot owner only!"""
        self.bot.victim = player
        await ctx.send(f"New victim chosen: {self.bot.victim}")

    async def choose_victim(self):
        """Chooses a victim to add reactions to."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guild_members = self.bot.get_guild(config.guild_id).members
            victim_member = random.sample(guild_members, 1)[0]
            self.bot.victim = victim_member.name
            print(f"New victim: {self.bot.victim}")
            await asyncio.sleep(10000)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Memers(bot))

        # schep_questions = ["does schep have tess", "did schep get tess", "does schep have tess yet"]
        # milow_questions = ["does milow have ace", "did milow get ace", "does milow have ace yet"]
        # if (content.lower() in schep_questions) or (content.lower()[:-1] in schep_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Schep").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await channel.send(f"Schep does not have Tess, make sure to let him know ;)", tts=True)
        #     else:
        #         await channel.send(f"Schep finally got Tess!")

        # elif (content.lower() in milow_questions) or (content.lower()[:-1] in milow_questions):
        #     schep_has_tess = SESSION.query(
        #         HasTess.has_tess).filter(HasTess.name == "Milow").first()
        #     if schep_has_tess is None or schep_has_tess[0] is False:
        #         await channel.send(f"Milow does not have Ace.", tts=True)
        #     else:
        #         await channel.send(f"Milow finally got Ace!")
