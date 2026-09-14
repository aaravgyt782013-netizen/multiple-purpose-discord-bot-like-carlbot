import random
import discord
from discord.ext import commands

from database import connect, get_setting


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown = set()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.author.id in self.cooldown:
            return
        if not get_setting(message.guild.id, "level_enabled"):
            return
        self.cooldown.add(message.author.id)
        try:
            gain = random.randint(8, 15)
            with connect() as db:
                row = db.execute("SELECT xp, level FROM xp WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id)).fetchone()
                xp, level = (row[0], row[1]) if row else (0, 0)
                xp += gain
                needed = 100 + level * 50
                if xp >= needed:
                    xp -= needed
                    level += 1
                    await message.channel.send(f"🎉 {message.author.mention} reached **Level {level}**!")
                db.execute("INSERT OR REPLACE INTO xp(guild_id,user_id,xp,level) VALUES(?,?,?,?)", (message.guild.id, message.author.id, xp, level))
        finally:
            self.cooldown.discard(message.author.id)

    @commands.hybrid_command(name="rank")
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        with connect() as db:
            row = db.execute("SELECT xp, level FROM xp WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
        xp, level = (row[0], row[1]) if row else (0, 0)
        embed = discord.Embed(title=f"{member.display_name}'s LightCore Rank", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="XP", value=str(xp))
        embed.set_footer(text="LightCore Leveling")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="levels")
    async def levels(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT user_id, level, xp FROM xp WHERE guild_id=? ORDER BY level DESC, xp DESC LIMIT 10", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"**{i}.** <@{r['user_id']}> — Lv. {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1)) or "No XP data yet."
        await ctx.send(embed=discord.Embed(title="LightCore Leaderboard", description=text, color=discord.Color.gold()))


async def setup(bot):
    await bot.add_cog(Leveling(bot))
