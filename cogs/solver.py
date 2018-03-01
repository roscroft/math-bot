"""Calls the Julia Tower Puzzle solver."""
import julia
from discord.ext import commands

class Solver():
    """Provides the solver command call."""

    def __init__(self, bot):
        self.bot = bot
        julia_caller = julia.Julia()
        self.solve_tower = julia_caller.include("./cogfiles/tower.jl")

    @commands.command()
    async def solve(self, ctx, top, right, bottom, left):
        """Calls the julia solver with the given vision numbers."""
        await ctx.send("Solving... (first time called will be slow)")
        # Tower puzzles are always of size 5
        top = list(map(int, top.split(" ")))
        right = list(map(int, right.split(" ")))
        bottom = list(map(int, bottom.split(" ")))
        left = list(map(int, left.split(" ")))
        num_elems = len(top)
        output = self.solve_tower(num_elems, top, right, bottom, left)
        await ctx.send("Solution found!")
        await ctx.send(output)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Solver(bot))
