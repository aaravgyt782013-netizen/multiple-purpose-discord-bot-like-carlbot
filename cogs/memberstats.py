import io
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from database import connect


class MemberStats(commands.Cog):
    """Live server statistics. Activity data comes from ActivityStats; this cog does not track messages."""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _font(size):
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default(size=size)

    async def _server_icon(self, guild, size=112):
        try:
            if guild.icon:
                return Image.open(io.BytesIO(await guild.icon.read())).convert("RGB").resize((size, size))
        except Exception:
            pass
        image = Image.new("RGB", (size, size), (40, 40, 52))
        ImageDraw.Draw(image).text((size // 2, size // 2), (guild.name[:1] or "?").upper(), fill="white", anchor="mm", font=self._font(48))
        return image

    async def _activity_totals(self, guild_id):
        cutoff_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        cutoff_week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        with connect() as db:
            today = int(db.execute("SELECT COALESCE(SUM(message_count),0) FROM activity_buckets WHERE guild_id=? AND bucket_start>=?", (guild_id, cutoff_today)).fetchone()[0] or 0)
            week = int(db.execute("SELECT COALESCE(SUM(message_count),0) FROM activity_buckets WHERE guild_id=? AND bucket_start>=?", (guild_id, cutoff_week)).fetchone()[0] or 0)
        activity = self.bot.get_cog("ActivityStats")
        if activity is not None:
            for (pending_guild, _user_id), values in activity.pending.items():
                if pending_guild == guild_id:
                    pending = int(values.get("messages", 0))
                    today += pending
                    week += pending
        return today, week

    async def _growth(self, guild_id, days=7):
        start = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
        values = {start + timedelta(days=i): [0, 0] for i in range(days)}
        with connect() as db:
            rows = db.execute("SELECT substr(created_at,1,10) day,event_type,COUNT(*) c FROM member_events WHERE guild_id=? AND created_at>=? GROUP BY day,event_type ORDER BY day", (guild_id, start.isoformat())).fetchall()
        for row in rows:
            try:
                day = datetime.strptime(row["day"], "%Y-%m-%d").date()
                if day in values:
                    values[day][0 if row["event_type"] == "join" else 1] = int(row["c"])
            except ValueError:
                continue
        return [values[start + timedelta(days=i)] for i in range(days)]

    @commands.hybrid_command(name="stats", description="Show a live Statbot-style server statistics card.")
    async def stats(self, ctx):
        guild = ctx.guild
        if guild is None:
            return await ctx.send(embed=discord.Embed(description="❌ This command can only be used in a server.", color=discord.Color.red()))
        total_members = guild.member_count or len(guild.members)
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        bot_count = sum(1 for member in guild.members if member.bot)
        boosts = guild.premium_subscription_count or 0
        channels = len(guild.channels)
        roles = max(0, len(guild.roles) - 1)
        today_messages, week_messages = await self._activity_totals(guild.id)
        growth = await self._growth(guild.id, 7)

        image = Image.new("RGB", (1200, 760), (17, 18, 24))
        draw = ImageDraw.Draw(image)
        title, section, value_font, small = self._font(38), self._font(22), self._font(30), self._font(18)
        muted, white, panel = (170, 173, 188), (245, 246, 250), (29, 30, 40)

        icon = await self._server_icon(guild)
        mask = Image.new("L", icon.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, icon.width, icon.height), fill=255)
        image.paste(icon, (48, 40), mask)
        draw.text((190, 48), guild.name[:34], fill=white, font=title)
        draw.text((190, 96), "LIVE SERVER STATISTICS", fill=muted, font=small)
        draw.text((190, 126), f"Updated {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}", fill=muted, font=small)

        cards = [
            (48, 190, 280, 305, "TOTAL MEMBERS", f"{total_members:,}"),
            (300, 190, 532, 305, "ONLINE", f"{online_members:,}"),
            (552, 190, 784, 305, "BOTS", f"{bot_count:,}"),
            (804, 190, 1036, 305, "BOOSTS", f"{boosts:,}"),
            (48, 325, 280, 440, "CHANNELS", f"{channels:,}"),
            (300, 325, 532, 440, "ROLES", f"{roles:,}"),
            (552, 325, 784, 440, "MESSAGES TODAY", f"{today_messages:,}"),
            (804, 325, 1036, 440, "MESSAGES / 7D", f"{week_messages:,}"),
        ]
        for x1, y1, x2, y2, label, value in cards:
            draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=panel)
            draw.text((x1 + 18, y1 + 16), label, fill=muted, font=section)
            draw.text((x1 + 18, y1 + 57), value, fill=white, font=value_font)

        gx, gy, gw, gh = 48, 480, 988, 220
        draw.rounded_rectangle((gx, gy, gx + gw, gy + gh), radius=18, fill=panel)
        draw.text((gx + 20, gy + 16), "JOIN / LEAVE TREND • LAST 7 DAYS", fill=white, font=section)
        graph_x, graph_y, graph_w, graph_h = gx + 42, gy + 62, gw - 78, 120
        max_value = max(1, max(max(pair) for pair in growth))
        step = graph_w / 6
        join_points, leave_points = [], []
        for i, (joins, leaves) in enumerate(growth):
            px = graph_x + i * step
            join_points.append((px, graph_y + graph_h - (joins / max_value) * graph_h))
            leave_points.append((px, graph_y + graph_h - (leaves / max_value) * graph_h))
            day = (datetime.now(timezone.utc).date() - timedelta(days=6 - i)).strftime("%a")
            draw.text((px, graph_y + graph_h + 12), day, fill=muted, font=small, anchor="ma")
        if len(join_points) > 1:
            draw.line(join_points, fill=(90, 210, 140), width=4)
            draw.line(leave_points, fill=(235, 105, 105), width=4)
        for px, py in join_points:
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(90, 210, 140))
        for px, py in leave_points:
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(235, 105, 105))
        draw.text((gx + gw - 170, gy + 18), "● joins   ● leaves", fill=muted, font=small)

        out = io.BytesIO()
        image.save(out, "PNG")
        out.seek(0)
        file = discord.File(out, filename="lightcore-server-stats.png")
        embed = discord.Embed(title="📊 Live Server Statistics", description="Current guild values + existing ActivityStats message totals.", color=discord.Color.blurple())
        embed.set_image(url="attachment://lightcore-server-stats.png")
        embed.set_footer(text="LightCore • Live Stats")
        await ctx.send(embed=embed, file=file)

    @commands.hybrid_command(name="memberstats", description="Show recorded server growth and retention statistics.")
    @commands.has_permissions(manage_guild=True)
    async def memberstats(self, ctx):
        with connect() as db:
            joins = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='join'", (ctx.guild.id,)).fetchone()[0]
            leaves = db.execute("SELECT COUNT(*) FROM member_events WHERE guild_id=? AND event_type='leave'", (ctx.guild.id,)).fetchone()[0]
        retention = round(max(0, joins - leaves) / joins * 100, 1) if joins else 0
        embed = discord.Embed(title="📈 Member Growth", color=discord.Color.blurple())
        embed.add_field(name="Recorded joins", value=f"{joins:,}")
        embed.add_field(name="Recorded leaves", value=f"{leaves:,}")
        embed.add_field(name="Net change", value=f"{joins - leaves:+,}")
        embed.add_field(name="Retention", value=f"{retention}%")
        embed.set_footer(text="LightCore • Member Growth")
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
        lines = [f"`{day}` +{data.get('join',0):<3} -{data.get('leave',0):<3}" for day, data in by_day.items()]
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
