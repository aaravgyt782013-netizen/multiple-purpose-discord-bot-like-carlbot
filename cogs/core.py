import discord
from discord.ext import commands
from discord import app_commands

from config import BRAND, PREFIX


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(title=f"{BRAND} Help", description="All-in-one Discord server toolkit.", color=discord.Color.blurple())
        embed.add_field(name="Moderation", value="ban, kick, mute, warn, warnings", inline=True)
        embed.add_field(name="Community", value="rank, balance, shop, tickets, roles", inline=True)
        embed.add_field(name="Configuration", value="panel, embed, welcome, autorule", inline=True)
        embed.set_footer(text=BRAND)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"🏓 {BRAND} latency: {round(self.bot.latency * 1000)}ms")

    @commands.hybrid_command(name="about")
    async def about(self, ctx: commands.Context):
        await ctx.send(f"**{BRAND}** • prefix `{PREFIX}` • discord.py 2.7.1")


async def setup(bot):
    await bot.add_cog(Core(bot))
