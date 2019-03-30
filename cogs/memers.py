#!/usr/bin/python3.6
"""Defines commands used for the Memers server."""
import datetime
import json
import random
import re
import asyncio
from string import Template

import discord
from discord.ext import commands
from utils import config

MAX_VOTES = 10
MAX_NUM_STARS = 5
STARBOARD_CHANNEL_ID = 553644760255037440

async def is_mod(ctx):
    """Checks if the user is a mod."""
    return str(ctx.author.id) in Memers.get_mods()

def check_votes(user):
    """Checks if a user is banned from submitting."""
    with open(f"./resources/votes.json", "r+") as vote_file:
        votes = json.load(vote_file)
    if user in votes:
        votes_left = MAX_VOTES - len(votes[user])
    else:
        votes_left = MAX_VOTES
    return votes_left > 0

def add_to_json(filename, call, response, user, is_img, call_regex=None):
    """Adds a record to the given json file."""
    with open(f"./resources/{filename}", "r+") as response_file:
        responses = json.load(response_file)
    can_submit = check_votes(user)
    if can_submit:
        if call in responses:
            out_msg = "This call already exists. Please use a different one."
        else:
            responses[call] = {}
            responses[call]["response"] = response
            responses[call]["user"] = user
            if call_regex:
                responses[call]["call_regex"] = call_regex
            with open(f"./resources/{filename}", "w") as response_file:
                json.dump(responses, response_file)
            if not is_img:
                out_msg = f"{user} added call/response pair '{call}' -> '{response}'!"
            else:
                out_msg = f"{user} added image call/response pair {call} -> <{response}>!"
    else:
        out_msg = "You are banned from submitting."
    return out_msg

def remove_from_json(filename, call):
    """Removes the given record from the given json file."""
    with open(f"./resources/{filename}", "r+") as response_file:
        responses = json.load(response_file)
    if call in responses:
        response = responses[call]["response"]
        user = responses[call]["user"]
        responses.pop(call)
        with open(f"./resources/{filename}", "w") as response_file:
            json.dump(responses, response_file)
        return (user, response)
    return (None, None)

def list_from_json(filename, is_img):
    """Lists all records from the given json file."""
    out_msg = "Call -> Response\n"
    with open(f"./resources/{filename}", "r+") as response_file:
        responses = json.load(response_file)
        for call, response_dict in responses.items():
            response = response_dict["response"]
            user = response_dict["user"]
            if not is_img:
                out_msg += f"{call} -> {response}, by {user}\n"
            else:
                out_msg += f"{call}\n"
    out_msg = f"```{out_msg}```"
    return out_msg

def list_user_adds(filename, user, is_img):
    """Lists all adds by a user."""
    out_msg = "Call -> Response\n"
    with open(f"./resources/{filename}", "r+") as response_file:
        responses = json.load(response_file)
        for call, response_dict in responses.items():
            response = response_dict["response"]
            sub_user = response_dict["user"]
            if user == sub_user:
                if not is_img:
                    out_msg += f"{call} -> {response}\n"
                else:
                    out_msg += f"{call}\n"
    if out_msg == "Call -> Response\n":
        out_msg = f"Nothing submitted by {user}."
    out_msg = f"```{out_msg}```"
    return out_msg

def get_call_response_vars(call, response):
    """Parses the variables from a call/response pair."""
    wildcard_regex = re.compile(r'\$(\w+)')
    call_vars = wildcard_regex.findall(call)
    response_vars = wildcard_regex.findall(response)
    return call_vars, response_vars

def validate_call_response_vars(call, response):
    """Checks if the variables in a call/response pair are valid.
    If not, it also returns an error message."""
    # call_var_names, response_var_names = get_call_response_vars(call, response)
    call_vars, response_vars = get_call_response_vars(call, response)
    print(call_vars)
    print(response_vars)
    if len(call_vars) != len(set(call_vars)):
        return "Cannot add call/response pair: duplicate variable in call."

    for response_var in response_vars:
        if response_var not in call_vars:
            # '$author' is a reserved variable set to the author's name
            if response_var != 'author':
                return (f"Cannot add call/response pair: Variable {response_var} in "
                        "response not found in call.")
    return None

class Memers():
    """Defines the cap command and functions."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.victim = ""
        self.bot.victim_choice = self.bot.loop.create_task(self.choose_victim())
        self.bot.pct = 0.10
        self.bot.max_votes = MAX_VOTES
        self.message_buff = None
        self.message_author_buff = []

    @staticmethod
    def get_mods():
        """Returns a list of all mods."""
        mods_file = "./resources/mods.json"
        with open(mods_file, "r+") as mod_file:
            mods = json.load(mod_file)
        return mods

    @commands.group()
    async def cool(self, ctx):
        """Says if a user is cool.
        In reality this just checks if a subcommand is being invoked.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(f"No, {ctx.subcommand_passed} is not cool.")

    @cool.command(name='bot')
    async def _bot(self, ctx):
        """Is the bot cool?"""
        await ctx.send('Yes, the bot is cool.')

    @commands.command()
    # @commands.is_owner()
    async def add(self, ctx, call, response):
        """Adds a new call/response pair. Bad additions will get your privileges revoked."""
        filename = "responses.json"
        user = ctx.author.name
        if " " not in call:
            out_msg = "If you're getting this message then your call was probably terrible."
        elif '$' in call:
            out_msg = validate_call_response_vars(call, response)
            if out_msg is None:
                call_regex = re.sub(r"(\$\w+)", "(.*)", call)
                out_msg = add_to_json(filename, call, response, user, False, call_regex=call_regex)
        else:
            out_msg = add_to_json(filename, call, response, user, False)
        await ctx.send(out_msg)

    @commands.command(name="rm", hidden=True)
    @commands.check(is_mod)
    async def remove(self, ctx, call):
        """Removes a call/response pair. Bot mods only!"""
        filename = "responses.json"
        (user, response) = remove_from_json(filename, call)
        if response is not None:
            out_msg = f"Removed {user}'s text call/response pair '{call}' -> '{response}'!"
        else:
            out_msg = f"Text call '{call}' not found."
        await ctx.author.send(out_msg)

    @commands.command()
    async def calls(self, ctx):
        """Lists the existing call/responses pairs."""
        filename = "responses.json"
        out_msg = list_from_json(filename, False)
        await ctx.author.send(out_msg)

    @commands.command()
    async def blame(self, ctx, user):
        """Lists all added pairs by a given user."""
        filename = "responses.json"
        out_msg = list_user_adds(filename, user, False)
        await ctx.author.send(out_msg)

    @commands.group(invoke_without_command=True)
    async def img(self, ctx, call):
        """Provides the parser for image call/response commands."""
        # if ctx.invoked_subcommand is None and ctx.channel.id != config.main_channel:
        if ctx.invoked_subcommand is None:
            with open(f"./resources/image_responses.json", "r+") as response_file:
                responses = json.load(response_file)
                try:
                    found_url = responses[call]['response']
                    image_embed = discord.Embed()
                    image_embed.set_image(url=found_url)
                    await ctx.send(content=None, embed=image_embed)
                except KeyError:
                    print("No response in file!")

    @img.command(name="add")
    # @commands.is_owner()
    async def _add(self, ctx, call, image_url):
        """Adds a new image response."""
        filename = "image_responses.json"
        user = ctx.author.name
        out_msg = add_to_json(filename, call, image_url, user, True)
        await ctx.send(out_msg)

    @img.command(name="rm")
    @commands.check(is_mod)
    async def _remove(self, ctx, call):
        """Removes an image response. Bot mods only!"""
        filename = "image_responses.json"
        image_url = remove_from_json(filename, call)
        if image_url is not None:
            out_msg = f"Removed image call/response pair {call} -> <{image_url}>!"
        else:
            out_msg = f"Image call {call} not found."
        await ctx.author.send(out_msg)

    @img.command(name="calls")
    async def _calls(self, ctx):
        """Lists the existing image call/responses pairs."""
        filename = "image_responses.json"
        out_msg = list_from_json(filename, True)
        await ctx.author.send(out_msg)

    @img.command(name="blame")
    async def _blame(self, ctx, user):
        """Lists all added pairs by a given user."""
        filename = "image_responses.json"
        out_msg = list_user_adds(filename, user, True)
        await ctx.author.send(out_msg)

    @commands.command()
    async def voteban(self, ctx, user):
        """Votes to disallow a user from adding images or text calls."""
        filename = "votes.json"
        try:
            with open(f"./resources/{filename}", "r+") as vote_file:
                votes = json.load(vote_file)
        except FileNotFoundError:
            with open(f"./resources/{filename}", "w+") as vote_file:
                json.dump({}, vote_file)
            votes = {}
        voter = ctx.author.name
        if user in votes:
            votes_against = votes[user]
            if voter in votes_against:
                await ctx.author.send(f"You have already voted against {user}!")
            else:
                votes_against.append(voter)
                votes[user] = votes_against
                num_votes_left = self.bot.max_votes-len(votes_against)
                await ctx.send(f"You have voted against {user}. "
                               f"{num_votes_left} more votes until submission ban.")
        else:
            votes[user] = [voter]
            num_votes_left = self.bot.max_votes-1
            await ctx.send(f"You have voted against {user}. "
                           f"{num_votes_left} more votes until submission ban.")
        with open(f"./resources/{filename}", "w") as vote_file:
            json.dump(votes, vote_file)

    @commands.command()
    async def votes(self, ctx, user):
        """Displays the current number of votes against a user."""
        filename = "votes.json"
        with open(f"./resources/{filename}", "r+") as vote_file:
            votes = json.load(vote_file)
        if user in votes:
            num_votes_left = self.bot.max_votes-len(votes[user])
            await ctx.send(f"{user} has {num_votes_left} more votes until submission ban.")
        else:
            num_votes_left = self.bot.max_votes
            await ctx.send(f"{user} has {num_votes_left} more votes until submission ban.")

    @commands.command()
    async def snap(self, ctx, *args):
        """Determines whether you have been snapped by Thanos or not."""
        if args:
            name = ' '.join(args)
        else:
            name = ctx.author.name
        total = 0
        for char in name:
            total += ord(char)
        if total % 2 == 0:
            await ctx.send(f"{name.title()}, you were spared by Thanos.")
        else:
            await ctx.send(f"{name.title()}, you were slain by Thanos, "
                           "for the good of the Universe.")

    @commands.command()
    @commands.is_owner()
    async def clearvotes(self, ctx, user):
        """Clears votes against a player, effectively unbanning them."""
        filename = "votes.json"
        with open(f"./resources/{filename}", "r+") as vote_file:
            votes = json.load(vote_file)
        votes[user] = []
        await ctx.send(f"Cleared votes for {user}.")
        with open(f"./resources/{filename}", "w") as vote_file:
            json.dump(votes, vote_file)

    @commands.command()
    @commands.is_owner()
    async def player(self, ctx, player):
        """Sets a new player victim. Bot owner only!"""
        self.bot.victim = player
        await ctx.send(f"New victim chosen: {self.bot.victim}")

    @commands.command()
    @commands.is_owner()
    async def pct(self, ctx, pct):
        """Sets the chance that the bot adds a random reaction."""
        self.bot.pct = float(pct)/100.0
        await ctx.send(f"New reaction percentage chosen: {self.bot.pct}")

    @commands.group()
    @commands.is_owner()
    async def mod(self, ctx):
        """Provides the ability to add and remove bot moderators."""
        pass

    @mod.command(name="list")
    @commands.is_owner()
    async def modlist(self, ctx):
        """Lists all mods on the server."""
        out_msg = ""
        mods = Memers.get_mods()
        for _, mod_name in mods.items():
            out_msg += f"Mod: {mod_name}\n"
        out_msg = f"```{out_msg}```"
        await ctx.send(out_msg)

    @mod.command(name="add")
    @commands.is_owner()
    async def modadd(self, ctx, new_mod: discord.Member):
        """Adds a new mod."""
        new_mod_name = new_mod.name
        new_mod_id = str(new_mod.id)
        out_msg = ""
        mods = Memers.get_mods()
        if new_mod_id in mods:
            out_msg = f"{new_mod_name} is already a mod!"
        else:
            mods[new_mod_id] = new_mod_name
            with open(f"./resources/mods.json", "w") as mod_file:
                json.dump(mods, mod_file)
            out_msg = f"{new_mod_name} added to the mod list."
        await ctx.send(out_msg)

    @mod.command(name="rm")
    @commands.is_owner()
    async def modrm(self, ctx, old_mod: discord.Member):
        """Removes a current mod."""
        old_mod_name = old_mod.name
        old_mod_id = str(old_mod.id)
        out_msg = ""
        mods = Memers.get_mods()
        if old_mod_id not in mods:
            out_msg = f"{old_mod_name} is not a mod!"
        else:
            mods.pop(old_mod_id)
            with open(f"./resources/mods.json", "w") as mod_file:
                json.dump(mods, mod_file)
            out_msg = f"{old_mod_name} removed from the mod list."
        await ctx.send(out_msg)

    async def choose_victim(self):
        """Chooses a victim to add reactions to."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            guild_members = self.bot.get_guild(config.guild_id).members
            victim_member = random.sample(guild_members, 1)[0]
            self.bot.victim = victim_member.name
            print(f"New victim: {self.bot.victim}")
            await asyncio.sleep(10000)

    async def on_reaction_add(self, reaction, user):
        """Defines on_reaction_add behavior for starboard."""
        if reaction.emoji != '⭐' or user.bot or reaction.message.channel.id == STARBOARD_CHANNEL_ID:
            return

        if reaction.count >= MAX_NUM_STARS:
            channel_mention = reaction.message.channel.mention

            with open('resources/starboard.txt', 'r+') as f:
                starboard_ids = f.read().splitlines()

            if str(reaction.message.id) in starboard_ids:
                async for message in reaction.message.guild.get_channel(STARBOARD_CHANNEL_ID).history():
                    if str(reaction.message.id) in message.content:
                        await message.edit(content=f":star: {reaction.count} {channel_mention} ID: {reaction.message.id}")
                return

            starboard_ids.append(str(reaction.message.id))
            with open('resources/starboard.txt', 'w') as f:
                f.write('\n'.join(starboard_ids))

            embed = discord.Embed(colour=discord.Colour(0),
                                  url=f'https://discordapp.com/channels/{reaction.message.guild.id}/{reaction.message.channel.id}/{reaction.message.id}',
                                  timestamp=datetime.datetime.now(),
                                  description=reaction.message.content)

            embed.set_author(name=reaction.message.author, icon_url=reaction.message.author.avatar_url)

            embeds = reaction.message.embeds

            bot_self = reaction.message.guild.get_channel(STARBOARD_CHANNEL_ID)
            await bot_self.send(f":star: {reaction.count} {channel_mention} ID: {reaction.message.id}", embed=embed)
            for embed in embeds:
                await bot_self.send(embed=embed)

    async def on_message(self, ctx):
        """Defines on_message behavior for responses and victim reaction adding."""
        if ctx.author.bot:
            return

        # Handle random reaction adding
        reaction_pct = random.random()
        if self.bot.victim == ctx.author.name and reaction_pct < self.bot.pct:
            add_emoji = random.sample(self.bot.emojis, 1)[0]
            await ctx.add_reaction(add_emoji)

        # Handle call/response
        # if ctx.channel.id != config.main_channel:
        if not ctx.content.startswith("$"):
            with open(f"./resources/responses.json", "r+") as response_file:
                responses = json.load(response_file)
            for call, response_dict in responses.items():
                response = response_dict.get('response', None)
                if response is None:
                    await ctx.channel.send("No response exists.")
                if '$' in call:
                    call_regex = response_dict.get('call_regex', None)
                    if not call_regex:
                        continue

                    call_vars, response_vars = get_call_response_vars(call, response)
                    call_search = re.search(call_regex, ctx.content.lower())
                    if not call_search:
                        continue

                    call_var_mapping = dict(zip(call_vars, call_search.groups()))
                    call_var_mapping['author'] = ctx.author.name
                    await ctx.channel.send(Template(response).substitute(call_var_mapping))
                else:
                    if call in ctx.content.lower():
                        await ctx.channel.send(f"{response}")

        # Special call/responses
        if ctx.channel.id != config.main_channel:
            if ctx.content.lower() in ["i'm dad", "im dad"]:
                await ctx.channel.send(f"No you're not, you're {ctx.author.mention}.")

        if ctx.content.lower() == "out":
            await ctx.channel.send(f":point_right: :door: :rage:")

        if ctx.content.lower() == "in":
            await ctx.channel.send(f":grinning: :door: :point_left:")

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Memers(bot))
