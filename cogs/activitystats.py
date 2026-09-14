import asyncio
import io
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from database import connect

PAGE_SIZE = 10
FLUSH_SECONDS = 60


def utcnow():
    return datetime.now(timezone.utc)


def parse_utc(value):
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return utcnow()


def day_start(dt):
    return dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def format_voice(seconds):
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


class ActivityLeaderboardView(discord.ui.View):
    def __init__(self, cog, guild_id, stat, period="all", page=1):
        super().__init__(timeout=180)
        self.cog = cog
        self.guild_id = guild_id
        self.stat = stat
        self.period = period
        self.page = max(1, page)
        self.message = None
        previous = discord.ui.Button(label="Previous", emoji="◀️", style=discord.ButtonStyle.secondary)
        next_button = discord.ui.Button(label="Next", emoji="▶️", style=discord.ButtonStyle.secondary)
        previous.callback = self.previous
        next_button.callback = self.next_page
        self.add_item(previous)
        self.add_item(next_button)

    async def interaction_check(self, interaction):
        if interaction.guild_id != self.guild_id:
            await interaction.response.send_message(
                embed=discord.Embed(description="❌ This leaderboard belongs to another server.", color=discord.Color.red()),
                ephemeral=True,
            )
            return False
        return True

    async def previous(self, interaction):
        self.page = max(1, self.page - 1)
        embed, file = await self.cog.leaderboard_page(self.guild_id, self.stat, self.period, self.page)
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def next_page(self, interaction):
        rows, _ = await self.cog.fetch_leaderboard(self.guild_id, self.stat, self.period, self.page + 1)
        if not rows:
            return await interaction.response.send_message(
                embed=discord.Embed(description="❌ There are no more pages.", color=discord.Color.red()),
                ephemeral=True,
            )
        self.page += 1
        embed, file = await self.cog.leaderboard_page(self.guild_id, self.stat, self.period, self.page)
        await interaction.response.edit_message(embed=embed, attachments=[file], view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ActivityStats(commands.Cog):
    """Persistent Statbot-style activity tracking with batched database writes."""

    def __init__(self, bot):
        self.bot = bot
        self.pending = defaultdict(lambda: {"messages": 0, "voice_seconds": 0})
        self.voice_last_tick = {}
        self.flush_task = None
        self.flush_lock = asyncio.Lock()

    async def cog_load(self):
        await self._recover_voice_sessions()
        self.flush_task = asyncio.create_task(self._flush_loop(), name="lightcore-activity-flush")

    async def cog_unload(self):
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()
        self.voice_last_tick.clear()

    def record_message(self, guild_id, user_id):
        self.pending[(guild_id, user_id)]["messages"] += 1

    def _add_voice_pending(self, guild_id, user_id, seconds):
        if seconds > 0:
            self.pending[(guild_id, user_id)]["voice_seconds"] += int(seconds)

    async def _recover_voice_sessions(self):
        now = utcnow()
        with connect() as db:
            sessions = db.execute("SELECT guild_id,user_id,joined_at FROM activity_voice_sessions").fetchall()
            for row in sessions:
                guild = self.bot.get_guild(row["guild_id"])
                member = guild.get_member(row["user_id"]) if guild else None
                if not member or not member.voice or not member.voice.channel:
                    db.execute("DELETE FROM activity_voice_sessions WHERE guild_id=? AND user_id=?", (row["guild_id"], row["user_id"]))
                    continue
                self.voice_last_tick[(row["guild_id"], row["user_id"])] = parse_utc(row["joined_at"])
        await self.flush()
        now = utcnow()
        with connect() as db:
            for row in db.execute("SELECT guild_id,user_id FROM activity_voice_sessions").fetchall():
                self.voice_last_tick[(row["guild_id"], row["user_id"])] = now

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(FLUSH_SECONDS)
            await self.flush()

    async def flush(self):
        async with self.flush_lock:
            now = utcnow()
            with connect() as db:
                sessions = db.execute("SELECT guild_id,user_id,joined_at FROM activity_voice_sessions").fetchall()
                for row in sessions:
                    key = (row["guild_id"], row["user_id"])
                    start = self.voice_last_tick.get(key, parse_utc(row["joined_at"]))
                    if start < now:
                        self._add_voice_pending(row["guild_id"], row["user_id"], (now - start).total_seconds())
                    self.voice_last_tick[key] = now

                for (guild_id, user_id), values in list(self.pending.items()):
                    messages = int(values["messages"])
                    voice_seconds = int(values["voice_seconds"])
                    if not messages and not voice_seconds:
                        continue
                    db.execute(
                        "INSERT INTO activity_stats(guild_id,user_id,message_count,voice_seconds) VALUES(?,?,?,?) "
                        "ON CONFLICT(guild_id,user_id) DO UPDATE SET message_count=message_count+excluded.message_count, voice_seconds=voice_seconds+excluded.voice_seconds",
                        (guild_id, user_id, messages, voice_seconds),
                    )
                    bucket = day_start(now).isoformat()
                    db.execute(
                        "INSERT INTO activity_buckets(guild_id,user_id,bucket_start,message_count,voice_seconds) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(guild_id,user_id,bucket_start) DO UPDATE SET message_count=message_count+excluded.message_count, voice_seconds=voice_seconds+excluded.voice_seconds",
                        (guild_id, user_id, bucket, messages, voice_seconds),
                    )
                self.pending.clear()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        self.record_message(message.guild.id, message.author.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild or before.channel == after.channel:
            return
        key = (member.guild.id, member.id)
        now = utcnow()
        if before.channel is not None:
            start = self.voice_last_tick.pop(key, None)
            if start is None:
                with connect() as db:
                    row = db.execute("SELECT joined_at FROM activity_voice_sessions WHERE guild_id=? AND user_id=?", key).fetchone()
                start = parse_utc(row["joined_at"]) if row else now
            self._add_voice_pending(member.guild.id, member.id, (now - start).total_seconds())
            with connect() as db:
                db.execute("DELETE FROM activity_voice_sessions WHERE guild_id=? AND user_id=?", key)
        if after.channel is not None:
            with connect() as db:
                db.execute(
                    "INSERT INTO activity_voice_sessions(guild_id,user_id,joined_at,channel_id) VALUES(?,?,?,?) "
                    "ON CONFLICT(guild_id,user_id) DO UPDATE SET joined_at=excluded.joined_at,channel_id=excluded.channel_id",
                    (member.guild.id, member.id, now.isoformat(), after.channel.id),
                )
            self.voice_last_tick[key] = now

    def _cutoff(self, period):
        now = utcnow()
        if period == "weekly":
            return now - timedelta(days=7)
        if period == "monthly":
            return now - timedelta(days=30)
        return None

    async def fetch_leaderboard(self, guild_id, stat, period="all", page=1):
        offset = (max(1, page) - 1) * PAGE_SIZE
        column = "message_count" if stat == "messages" else "voice_seconds"
        cutoff = self._cutoff(period)
        with connect() as db:
            if cutoff:
                rows = db.execute(
                    f"SELECT user_id,SUM({column}) AS value FROM activity_buckets WHERE guild_id=? AND bucket_start>=? GROUP BY user_id ORDER BY value DESC,user_id ASC LIMIT ? OFFSET ?",
                    (guild_id, cutoff.isoformat(), PAGE_SIZE, offset),
                ).fetchall()
                total = db.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM activity_buckets WHERE guild_id=? AND bucket_start>=? AND (message_count>0 OR voice_seconds>0)",
                    (guild_id, cutoff.isoformat()),
                ).fetchone()[0]
            else:
                rows = db.execute(
                    f"SELECT user_id,{column} AS value FROM activity_stats WHERE guild_id=? AND {column}>0 ORDER BY value DESC,user_id ASC LIMIT ? OFFSET ?",
                    (guild_id, PAGE_SIZE, offset),
                ).fetchall()
                total = db.execute(f"SELECT COUNT(*) FROM activity_stats WHERE guild_id=? AND {column}>0", (guild_id,)).fetchone()[0]
        return rows, total

    async def _avatar(self, member, size=72):
        try:
            return Image.open(io.BytesIO(await member.display_avatar.read())).convert("RGB").resize((size, size))
        except Exception:
            return Image.new("RGB", (size, size), (45, 45, 55))

    async def leaderboard_page(self, guild_id, stat, period, page):
        rows, total = await self.fetch_leaderboard(guild_id, stat, period, page)
        guild = self.bot.get_guild(guild_id)
        title = "MESSAGES" if stat == "messages" else "VOICE TIME"
        period_label = {"all": "ALL TIME", "weekly": "LAST 7 DAYS", "monthly": "LAST 30 DAYS"}.get(period, "ALL TIME")
        image = Image.new("RGB", (1000, 790), (18, 18, 24))
        draw = ImageDraw.Draw(image)
        title_font = ImageFont.load_default(size=34)
        row_font = ImageFont.load_default(size=25)
        small = ImageFont.load_default(size=18)
        draw.text((42, 30), f"LIGHTCORE • {title}", fill="white", font=title_font)
        draw.text((42, 72), period_label, fill=(180, 180, 195), font=small)
        for index, row in enumerate(rows, (page - 1) * PAGE_SIZE + 1):
            y = 115 + ((index - 1) % PAGE_SIZE) * 66
            member = guild.get_member(row["user_id"]) if guild else None
            avatar = await self._avatar(member) if member else Image.new("RGB", (54, 54), (45, 45, 55))
            mask = Image.new("L", (54, 54), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 54, 54), fill=255)
            image.paste(avatar.resize((54, 54)), (45, y), mask)
            name = (member.display_name if member else f"User {row['user_id']}")[:28]
            value = f"{int(row['value']):,} messages" if stat == "messages" else format_voice(row["value"])
            draw.text((125, y + 7), f"#{index}", fill=(180, 180, 195), font=small)
            draw.text((195, y + 3), name, fill="white", font=row_font)
            draw.text((720, y + 8), value, fill="white", font=small)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        draw.text((42, 750), f"Page {page}/{pages} • {total} active users • LightCore", fill=(160, 160, 175), font=small)
        out = io.BytesIO()
        image.save(out, "PNG")
        out.seek(0)
        file = discord.File(out, filename="lightcore-leaderboard.png")
        embed = discord.Embed(title=f"📊 {title.title()} Leaderboard", description=f"{period_label.title()} • page **{page}/{pages}**", color=discord.Color.blurple())
        embed.set_image(url="attachment://lightcore-leaderboard.png")
        embed.set_footer(text="LightCore • Activity Statistics")
        return embed, file

    async def _rank(self, guild_id, user_id, stat, period="all"):
        column = "message_count" if stat == "messages" else "voice_seconds"
        cutoff = self._cutoff(period)
        with connect() as db:
            if cutoff:
                value = db.execute(
                    f"SELECT COALESCE(SUM({column}),0) FROM activity_buckets WHERE guild_id=? AND user_id=? AND bucket_start>=?",
                    (guild_id, user_id, cutoff.isoformat()),
                ).fetchone()[0]
                rank = db.execute(
                    f"SELECT COUNT(*) FROM (SELECT user_id,SUM({column}) value FROM activity_buckets WHERE guild_id=? AND bucket_start>=? GROUP BY user_id HAVING value>?)",
                    (guild_id, cutoff.isoformat(), value),
                ).fetchone()[0] + 1
            else:
                value = db.execute(
                    f"SELECT COALESCE({column},0) FROM activity_stats WHERE guild_id=? AND user_id=?",
                    (guild_id, user_id),
                ).fetchone()[0]
                rank = db.execute(
                    f"SELECT COUNT(*) FROM activity_stats WHERE guild_id=? AND {column}>?",
                    (guild_id, value),
                ).fetchone()[0] + 1
        return int(value or 0), int(rank)

    async def stats_card(self, member):
        guild_id = member.guild.id
        messages, message_rank = await self._rank(guild_id, member.id, "messages")
        voice_seconds, voice_rank = await self._rank(guild_id, member.id, "voice")
        image = Image.new("RGB", (1000, 520), (18, 18, 24))
        draw = ImageDraw.Draw(image)
        big = ImageFont.load_default(size=34)
        font = ImageFont.load_default(size=25)
        small = ImageFont.load_default(size=19)
        avatar = await self._avatar(member, 150)
        mask = Image.new("L", (150, 150), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
        image.paste(avatar, (55, 55), mask)
        draw.text((245, 65), member.display_name[:26], fill="white", font=big)
        draw.text((245, 110), "ACTIVITY STATISTICS", fill=(180, 180, 195), font=small)
        draw.rounded_rectangle((55, 245, 470, 420), radius=18, fill=(30, 30, 40))
        draw.rounded_rectangle((530, 245, 945, 420), radius=18, fill=(30, 30, 40))
        draw.text((85, 275), "MESSAGES", fill="white", font=font)
        draw.text((85, 325), f"{messages:,}", fill="white", font=big)
        draw.text((85, 370), f"Server rank #{message_rank}", fill=(180, 180, 195), font=small)
        draw.text((560, 275), "VOICE TIME", fill="white", font=font)
        draw.text((560, 325), format_voice(voice_seconds), fill="white", font=big)
        draw.text((560, 370), f"Server rank #{voice_rank}", fill=(180, 180, 195), font=small)
        draw.text((55, 465), "LIGHTCORE • ACTIVITY STATS", fill=(160, 160, 175), font=small)
        out = io.BytesIO()
        image.save(out, "PNG")
        out.seek(0)
        return out

    @commands.hybrid_group(name="top", invoke_without_command=True, description="View activity leaderboards.")
    async def top(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📊 Activity Leaderboards",
                description="Use `.top messages`, `.top voice`, `.top messages weekly`, or `.top voice monthly`.",
                color=discord.Color.blurple(),
            )
            await ctx.send(embed=embed)

    @top.command(name="messages", description="Leaderboard ranked by messages.")
    async def top_messages(self, ctx, period: str = "all"):
        period = period.lower()
        if period not in {"all", "weekly", "monthly"}:
            return await ctx.send(embed=discord.Embed(description="❌ Period must be `all`, `weekly`, or `monthly`.", color=discord.Color.red()))
        await self.flush()
        embed, file = await self.leaderboard_page(ctx.guild.id, "messages", period, 1)
        view = ActivityLeaderboardView(self, ctx.guild.id, "messages", period)
        message = await ctx.send(embed=embed, file=file, view=view)
        view.message = message

    @top.command(name="voice", description="Leaderboard ranked by voice time.")
    async def top_voice(self, ctx, period: str = "all"):
        period = period.lower()
        if period not in {"all", "weekly", "monthly"}:
            return await ctx.send(embed=discord.Embed(description="❌ Period must be `all`, `weekly`, or `monthly`.", color=discord.Color.red()))
        await self.flush()
        embed, file = await self.leaderboard_page(ctx.guild.id, "voice", period, 1)
        view = ActivityLeaderboardView(self, ctx.guild.id, "voice", period)
        message = await ctx.send(embed=embed, file=file, view=view)
        view.message = message

    @commands.hybrid_command(name="mystats", description="Show a visual activity statistics card.")
    async def mystats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await self.flush()
        card = await self.stats_card(member)
        embed = discord.Embed(title="📊 My Activity Statistics", color=discord.Color.blurple())
        embed.set_image(url="attachment://lightcore-activity.png")
        embed.set_footer(text="LightCore • Activity Statistics")
        await ctx.send(embed=embed, file=discord.File(card, filename="lightcore-activity.png"))


async def setup(bot):
    await bot.add_cog(ActivityStats(bot))
