"""Defines functions related to the database."""
from datetime import datetime
from discord.ext import commands
from utils.config import registration_channel
from cogs.xp import rsn_exists

class Database():
    """Defines database commands."""

    def __init__(self, bot):
        self.bot = bot

    async def handle_registration(self, ctx, rsn, is_main):
        """Handles registration output."""
        async with self.bot.pool.acquire() as con:
            exists = await rsn_exists(con, rsn)
        disc_id = str(ctx.author.id)

        if not exists:
            await ctx.send(f"Username {rsn} not found in clan database.")
            return

        # First check if the user is currently registered for the username.
        names_stmt = """SELECT EXISTS(SELECT 1 FROM account_owned WHERE rsn = $1 AND
            end_dtg IS NULL);"""
        async with self.bot.pool.acquire() as con:
            exists = await con.fetchval(names_stmt, rsn)
        if exists:
            await ctx.send(f"Username {rsn} already registered.")
            return

        # Send message to registration channel for approval.
        self.bot.reg_ch = self.bot.get_channel(registration_channel)
        approve_msg = await self.bot.reg_ch.send(f"Discord user {ctx.author.name} is attempting to "
                                                 f"register Runescape username {rsn}. React with "
                                                 ":white_check_mark: to approve, or :x: to "
                                                 "disapprove.")
        await approve_msg.add_reaction(u"\u2705")
        await approve_msg.add_reaction(u"\u274c")

        def approval(reaction, user):
            """Checks for approval reaction."""
            return (user != self.bot.user) and (reaction.emoji == u"\u2705" or reaction.emoji == u"\u274c")

        reaction, _ = await self.bot.wait_for('reaction_add', check=approval)

        if reaction.emoji == u"\u2705":
            await ctx.author.send(f"Your registration as {rsn} has been approved.")
            await self.register_user(disc_id, rsn, is_main)
            await approve_msg.delete()
            await self.bot.reg_ch.send(f"Discord user {ctx.author.name} approved as Runescape "
                                       f"user {rsn}.")
        elif reaction.emoji == u"\u274c":
            await ctx.author.send(f"Your registration as {rsn} has been disapproved. "
                                  "You must reregister with a valid username.")
            await approve_msg.delete()
            return

    async def register_user(self, disc_id, rsn, is_main):
        """Inserts account registers into the database."""
        async with self.bot.pool.acquire() as con:
            # Make sure discord id is in the database.
            async with con.transaction():
                disc_stmt = """INSERT INTO account(disc_id, total_caps) VALUES ($1, 0) ON CONFLICT
                     (disc_id) DO NOTHING;"""
                await con.execute(disc_stmt, disc_id)
            # Insert the new record.
            async with con.transaction():
                account_stmt = """INSERT INTO account_owned(disc_id, rsn, is_main, start_dtg)
                     VALUES ($1, $2, $3, $4);"""
                start_dtg = datetime.now()
                await con.execute(account_stmt, disc_id, rsn, is_main, start_dtg)

    async def handle_change(self, ctx, old_rsn, new_rsn, is_main):
        """Handles name changes."""
        # First, check that both the old and new rsns are valid.
        async with self.bot.pool.acquire() as con:
            old_exists = await rsn_exists(con, old_rsn)
            new_exists = await rsn_exists(con, new_rsn)
        disc_id = str(ctx.author.id)

        if not old_exists:
            await ctx.send(f"Username {old_rsn} not found in clan database.")
            return
        if not new_exists:
            await ctx.send(f"Username {new_rsn} not found in clan database.")
            return

        # Next, check if the user is currently registered for the old username.
        names_stmt = """SELECT start_dtg FROM account_owned WHERE disc_id = $1 AND
            rsn = $2 AND end_dtg IS NULL;"""
        async with self.bot.pool.acquire() as con:
            start_dtg = await con.fetchval(names_stmt, disc_id, old_rsn)
            print(start_dtg)
        if start_dtg is None:
            await ctx.send(f"You do not currently own username {old_rsn}.")
            return

        # Send message to registration channel for approval.
        self.bot.reg_ch = self.bot.get_channel(registration_channel)
        change_str = (f"Discord user {ctx.author.name} is attempting to change Runescape username "
                      f"{old_rsn} to {new_rsn}. React with :white_check_mark: to approve, or :x: "
                      "to disapprove.")
        change_msg = await self.bot.reg_ch.send(change_str)
        await change_msg.add_reaction(u"\u2705")
        await change_msg.add_reaction(u"\u274c")

        def approval(reaction, user):
            """Checks for approval reaction."""
            return reaction.emoji == u"\u2705" or reaction.emoji == u"\u274c"

        reaction, _ = await self.bot.wait_for('reaction_add', check=approval)

        if reaction.emoji == u"\u2705":
            await ctx.author.send(f"Your name change to {new_rsn} has been approved.")
            await self.name_change(disc_id, old_rsn, start_dtg, old_rsn, is_main)
            await change_msg.delete()
            await self.bot.reg_ch.send(f"Discord user {ctx.author.name} changed Runescape username "
                                       f"from {old_rsn} to {new_rsn}.")
        elif reaction.emoji == u"\u274c":
            await ctx.author.send(f"Your name change from {old_rsn} to {new_rsn} has been "
                                  "disapproved.")
            await change_msg.delete()
            return

    async def name_change(self, disc_id, old_rsn, start_dtg, new_rsn, is_main):
        """Processes name changes."""
        new_start_dtg = datetime.now()
        end_dtg = new_start_dtg
        async with self.bot.pool.acquire() as con:
            # End ownership of old account.
            async with con.transaction():
                old_stmt = """UPDATE account_owned SET is_main = False, end_dtg = $1
                    WHERE disc_id = $2 AND rsn = $3 AND start_dtg = $4;"""
                await con.execute(old_stmt, end_dtg, disc_id, old_rsn, start_dtg)
            # Begin ownership of new account.
            async with con.transaction():
                account_stmt = """INSERT INTO account_owned(disc_id, rsn, is_main, start_dtg)
                     VALUES ($1, $2, $3, $4);"""
                start_dtg = datetime.now()
                await con.execute(account_stmt, disc_id, new_rsn, is_main, new_start_dtg)

    @commands.group()
    async def register(self, ctx):
        """Registers a player in the database if the rsn is valid."""
        pass

    @register.command(name="main")
    async def _main(self, ctx, rsn):
        """Registers the given rsn as the player's current main account."""
        await self.handle_registration(ctx, rsn, True)

    @register.command(name="alt")
    async def _alt(self, ctx, rsn):
        """Registers the given rsn as the player's current main account."""
        await self.handle_registration(ctx, rsn, False)

    @commands.group()
    async def change(self, ctx):
        """Used for name changes."""
        pass

    @change.command(name="main")
    async def changemain(self, ctx, old_rsn, new_rsn):
        """Changes the old rsn to the new rsn."""
        await self.handle_change(ctx, old_rsn, new_rsn, True)

    @change.command(name="alt")
    async def changealt(self, ctx, old_rsn, new_rsn):
        """Changes the old rsn to the new rsn."""
        await self.handle_change(ctx, old_rsn, new_rsn, False)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Database(bot))
