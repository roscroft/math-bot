"""Defines functions related to the database."""
from datetime import datetime
from discord.ext import commands
from utils.config import registration_channel
from cogs.xp import rsn_exists

class Database():
    """Defines database commands."""

    def __init__(self, bot):
        self.bot = bot

    async def handle_approval(self, ctx, msg_dct, rsn_dct):
        """Sends the approval message to registration channel. Etc."""
        self.bot.reg_ch = self.bot.get_channel(registration_channel)
        register = rsn_dct["register"]

        approve_msg = await self.bot.reg_ch.send(msg_dct["approve"])
        await approve_msg.add_reaction(u"\u2705")
        await approve_msg.add_reaction(u"\u274c")

        def approval(reaction, user):
            """Checks for approval reaction."""
            return (user != self.bot.user) and (
                reaction.emoji == u"\u2705" or reaction.emoji == u"\u274c")

        reaction, _ = await self.bot.wait_for('reaction_add', check=approval)

        if reaction.emoji == u"\u2705":
            await ctx.author.send(msg_dct["approved"])
            if register:
                await self.register_user(rsn_dct)
            elif not register:
                await self.name_change(rsn_dct)
            await approve_msg.delete()
            await self.bot.reg_ch.send(msg_dct["finalized"])
        elif reaction.emoji == u"\u274c":
            await ctx.author.send(msg_dct["denied"])
            await approve_msg.delete()
            return

    async def handle_registration(self, ctx, rsn, is_main):
        """Handles registration output."""
        async with self.bot.pool.acquire() as con:
            exists = await rsn_exists(con, rsn)
        disc_id = str(ctx.author.id)

        if not exists:
            await ctx.send(f"Username {rsn} not found in clan database.")
            return

        # First check if the user is currently registered for the username.
        # Next, check if the user is already registered for a main. If so,
        # begin the name change process.
        names_stmt = """SELECT EXISTS(SELECT 1 FROM account_owned WHERE rsn = $1 AND
            end_dtg IS NULL);"""
        id_stmt = """SELECT EXISTS(SELECT 1 FROM account_owned WHERE disc_id = $1 AND
            is_main = True);"""
        async with self.bot.pool.acquire() as con:
            name_exists = await con.fetchval(names_stmt, rsn)
            id_exists = await con.fetchval(id_stmt, str(ctx.author.id))
        if name_exists:
            await ctx.send(f"Username {rsn} already registered.")
            return
        if id_exists:
            await ctx.send(f"You already have a main account registered. Use '$change "
                           "main <old_name> <new_name>' to change your name.")
            return

        rsn_dct = {"disc_id": disc_id, "new_rsn": rsn, "is_main": is_main, "register": True}
        msg_dct = {}
        msg_dct["approve"] = (f"Discord user {ctx.author.name} is attempting to register Runescape "
                              f"username {rsn}. React with :white_check_mark: to approve, or :x: "
                              "to disapprove.")
        msg_dct["approved"] = (f"Your registration as {rsn} has been approved.")
        msg_dct["finalized"] = (f"Discord user {ctx.author.name} approved as Runescape "
                                f"user {rsn}.")
        msg_dct["denied"] = (f"Your registration as {rsn} has been denied. "
                             "You must reregister with a valid username.")

        await self.handle_approval(ctx, msg_dct, rsn_dct)

    async def register_user(self, rsn_dct):
        """Inserts account registers into the database."""
        rsn = rsn_dct["new_rsn"]
        disc_id = rsn_dct["disc_id"]
        is_main = rsn_dct["is_main"]
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

        msg_dct = {}
        msg_dct["approve"] = (f"Discord user {ctx.author.name} is attempting to change Runescape "
                              f"username {old_rsn} to {new_rsn}. React with :white_check_mark: to "
                              "approve, or :x: to disapprove.")
        msg_dct["approved"] = (f"Your name change to {new_rsn} has been approved.")
        msg_dct["finalized"] = (f"Discord user {ctx.author.name} changed Runescape username from "
                                f"{old_rsn} to {new_rsn}")
        msg_dct["denied"] = (f"Your name change from {old_rsn} to {new_rsn} has been denied.")
        rsn_dct = {"new_rsn": new_rsn, "old_rsn": old_rsn, "disc_id": disc_id,
                   "start_dtg": start_dtg, "is_main": is_main, "register": False}
        await self.handle_approval(ctx, msg_dct, rsn_dct)

    async def name_change(self, rsn_dct):
        """Processes name changes."""
        disc_id = rsn_dct["disc_id"]
        old_rsn = rsn_dct["old_rsn"]
        new_rsn = rsn_dct["new_rsn"]
        start_dtg = rsn_dct["start_dtg"]
        is_main = rsn_dct["is_main"]
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
