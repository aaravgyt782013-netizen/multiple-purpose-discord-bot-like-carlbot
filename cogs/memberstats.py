from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

from database import connect, ensure_guild


class MemberStats(commands.Cog):
    """Server-growth statistics only. Activity counters are owned by ActivityStats."""

    def __init__(self, bot):
        self.bot = bot

    def _bar(self, value, maximum):
        size = 12
        filled = int((value / maximum) * size) if maximum else 0
        return "█" * filled + "░" * (size - filled)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not member.guild:
            return
        with connect() as db:
            db.execute("INSERT INTO member_events (guild_id, user_id, event_type) VALUES (?, ?, ?)", (member.guild.id, member.id, "join"))

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not member.guild:
            return
        with connect() as db:
            db.execute("INSERT INTO member_events (guild_id, user_id, event_type) VALUES (?, ?, ?)", (member.guild.id, member.id, "leave"))

    @commands.hybrid_command(name="memberstats", description="Show server growth and retention statistics.")
    @commands.has_permissions(manage_guild=True)
    async def memberstats(self, ctx):
        ensure_guild(ctx.guild.id)
        with connect() as db:
            joins = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='join'", (ctx.guild.id,)).fetchone()[0]
            leaves = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='leave'", (ctx.guild.id,)).fetchone()[0]
            active = db.execute("SELECT user_id,message_count FROM activity_stats WHERE guild_id=? AND message_count>0 ORDER BY message_count DESC LIMIT 5", (ctx.guild.id,)).fetchall()
        retention = round(max(0, joins - leaves) / joins * 100, 1) if joins else 0
        lines = []
        for row in active:
            user = ctx.guild.get_member(row["user_id"])
            lines.append(f"{user.mention if user else row['user_id']} — {row['message_count']:,} messages")
        embed = discord.Embed(title="LightCore Member Statistics", color=discord.Color.blurple())
        embed.add_field(name="Recorded joins", value=f"{joins:,}")
        embed.add_field(name="Recorded leaves", value=f"{leaves:,}")
        embed.add_field(name="Net change", value=f"{joins - leaves:+,}")
        embed.add_field(name="Retention", value=f"{retention}%")
        embed.add_field(name="Current members", value=f"{ctx.guild.member_count:,}")
        embed.add_field(name="Most active members", value="\n".join(lines) if lines else "No message activity recorded yet.", inline=False)
        embed.set_footer(text="LightCore • Member Stats")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="growth", description="Show a text graph of recent daily joins and leaves.")
    @commands.has_permissions(manage_guild=True)
    async def growth(self, ctx, days: commands.Range[int, 1, 30] = 14):
        start = datetime.now(timezone.utc) - timedelta(days=days)
        with connect() as db:
            rows = db.execute("SELECT substr(created_at,1,10) day, event_type, COUNT(*) c FROM member_events WHERE guild_id=? AND created_at>=? AND event_type IN ('join','leave') GROUP BY day,event_type ORDER BY day", (ctx.guild.id, start.strftime("%Y-%m-%d %H:%M:%S"))).fetchall()
        by_day = {}
        for row in rows:
            by_day.setdefault(row[0], {})[row[1]] = row[2]
        maximum = max((max(data.get("join", 0), data.get("leave", 0)) for data in by_day.values()), default=1)
        lines = [f"`{day}` +{data.get('join',0):<3} {self._bar(data.get('join',0), maximum)} -{data.get('leave',0):<3}" for day, data in by_day.items()]
        text = "\n".join(lines) or "No recorded events in this period."
        await ctx.send(embed=discord.Embed(title=f"Member Growth • Last {days} days", description=f"```text\n{text[:3900]}\n```", color=discord.Color.blurple()))

    @commands.hybrid_command(name="retention", description="Show basic member retention statistics.")
    @commands.has_permissions(manage_guild=True)
    async def retention(self, ctx):
        with connect() as db:
            joins = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='join'", (ctx.guild.id,)).fetchone()[0]
            leaves = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='leave'", (ctx.guild.id,)).fetchone()[0]
        rate = round(max(0, joins - leaves) / joins * 100, 1) if joins else 0
        embed = discord.Embed(title="📈 Retention", description=f"Estimated retention: **{rate}%** based on recorded join/leave events.", color=discord.Color.blurple())
        embed.set_footer(text="LightCore • Member Stats")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MemberStats(bot))
