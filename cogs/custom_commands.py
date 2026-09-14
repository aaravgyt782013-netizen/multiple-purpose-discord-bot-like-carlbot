import discord
from discord.ext import commands
from database import connect

class CustomCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="customadd")
    @commands.has_permissions(manage_guild=True)
    async def customadd(self, ctx, name: str, *, reply: str):
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO custom_commands(guild_id,name,response) VALUES(?,?,?)", (ctx.guild.id, name.lower(), reply))
        await ctx.send(f"Saved custom command: **{name.lower()}**")

    @commands.hybrid_command(name="customremove")
    @commands.has_permissions(manage_guild=True)
    async def customremove(self, ctx, name: str):
        with connect() as db:
            db.execute("DELETE FROM custom_commands WHERE guild_id=? AND name=?", (ctx.guild.id, name.lower()))
        await ctx.send("Custom command removed.")

    @commands.hybrid_command(name="customlist")
    async def customlist(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT name FROM custom_commands WHERE guild_id=? ORDER BY name", (ctx.guild.id,)).fetchall()
        await ctx.send("Custom commands: " + (", ".join(r['name'] for r in rows) if rows else "none"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        with connect() as db:
            row = db.execute("SELECT response FROM custom_commands WHERE guild_id=? AND name=?", (message.guild.id, message.content.lower())).fetchone()
        if row:
            await message.channel.send(row['response'])

async def setup(bot):
    await bot.add_cog(CustomCommands(bot))
