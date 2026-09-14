import discord
from discord.ext import commands


class Embeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="embed")
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx, title: str, *, description: str):
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        embed.set_footer(text="LightCore")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="announce")
    @commands.has_permissions(manage_messages=True)
    async def announce(self, ctx, *, message: str):
        embed = discord.Embed(title="📢 Announcement", description=message, color=discord.Color.blurple())
        embed.set_footer(text="LightCore")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Embeds(bot))
