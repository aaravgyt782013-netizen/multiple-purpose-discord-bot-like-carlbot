import io
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont

from database import connect, ensure_guild, get_setting

PAGE_SIZE = 10
FLUSH_SECONDS = 60


def utcnow():
    return datetime.now(timezone.utc)


def hour_bucket(dt=None):
    dt = dt or utcnow()
    return dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")


def parse_time(value):
    if not value:
        return utcnow()
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class ActivityLeaderboardView(discord.ui.View):
    def __init__(self, cog, ctx, stat, period):
        super().__init__(timeout=180)
        self.cog, self.ctx, self.stat, self.period, self.page = cog, ctx, stat, period, 0
        self.refresh_buttons()

    def refresh_buttons(self):
        _, total = self.cog.query_activity(self.ctx.guild.id, self.stat, self.period, self.page)
        self.max_page = max(0, (total - 1) // PAGE_SIZE)
        self.previous.disabled = self.page <= 0
        self.next.disabled = self.page >= self.max_page

    def embed(self):
        rows, _ = self.cog.query_activity(self.ctx.guild.id, self.stat, self.period, self.page)
        title = "Messages" if self.stat == "messages" else "Voice Time"
        scope = {"all": "All Time", "weekly": "This Week", "monthly": "This Month"}[self.period]
        lines = []
        for rank, row in enumerate(rows, self.page * PAGE_SIZE + 1):
            member = self.ctx.guild.get_member(row["user_id"])
            if member:
                name = member.display_name[:32]
                # Discord clients render this as a clickable avatar URL while keeping the
                # leaderboard compact; the rendered mystats card provides the full avatar.
                who = f"[◉]({member.display_avatar.url}) **{name}**"
            else:
                who = f"**User {row['user_id']}**"
            value = self.cog.format_voice(row["value"]) if self.stat == "voice" else f"{row['value']:,} messages"
            lines.append(f"**#{rank}** {who}\n└ {value}")
        embed = discord.Embed(title=f"📊 LightCore • {title} Leaderboard", description="\n\n".join(lines) or "No activity recorded yet.", color=discord.Color.blurple())
        embed.set_footer(text=f"{scope} • Page {self.page + 1}/{self.max_page + 1} • LightCore Activity")
        return embed

    async def previous_page(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(embed=self.cog.error_embed("This leaderboard belongs to the command user."), ephemeral=True)
        self.page -= 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def next_page(self, interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(embed=self.cog.error_embed("This leaderboard belongs to the command user."), ephemeral=True)
        self.page += 1
        self.refresh_buttons()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        await self.previous_page(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        await self.next_page(interaction)


class MemberStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.activity_pending = {}
        self.voice_sessions = {}
        self.activity_flush.start()

    def cog_unload(self):
        self.activity_flush.cancel()

    def error_embed(self, text):
        embed = discord.Embed(title="❌ Error", description=text, color=discord.Color.red())
        embed.set_footer(text="LightCore • Activity Stats")
        return embed

    @tasks.loop(seconds=FLUSH_SECONDS)
    async def activity_flush(self):
        await self.flush_activity()

    @activity_flush.before_loop
    async def before_activity_flush(self):
        await self.bot.wait_until_ready()

    async def _record_member_event(self, member, event_type):
        if not member.guild or not get_setting(member.guild.id, "memberstats_enabled"):
            return
        with connect() as db:
            db.execute("INSERT INTO member_events (guild_id,user_id,event_type) VALUES (?,?,?)", (member.guild.id, member.id, event_type))

    def add_activity(self, guild_id, user_id, messages=0, seconds=0):
        row = self.activity_pending.setdefault((guild_id, user_id), {"messages": 0, "seconds": 0})
        row["messages"] += messages
        row["seconds"] += seconds

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self._record_member_event(member, "join")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await self._record_member_event(member, "leave")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild and not message.author.bot:
            self.add_activity(message.guild.id, message.author.id, messages=1)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot or not member.guild:
            return
        before_id = before.channel.id if before.channel else None
        after_id = after.channel.id if after.channel else None
        if before_id == after_id:
            return
        key = (member.guild.id, member.id)
        now = utcnow()
        if key in self.voice_sessions:
            started = self.voice_sessions.pop(key)
            self.add_activity(member.guild.id, member.id, seconds=max(0, int((now - started).total_seconds())))
            with connect() as db:
                db.execute("DELETE FROM activity_voice_sessions WHERE guild_id=? AND user_id=?", key)
        if after.channel:
            self.voice_sessions[key] = now
            with connect() as db:
                db.execute("INSERT OR REPLACE INTO activity_voice_sessions(guild_id,user_id,joined_at,channel_id) VALUES(?,?,?,?)", (member.guild.id, member.id, now.isoformat(), after.channel.id))

    @commands.Cog.listener()
    async def on_ready(self):
        now = utcnow()
        with connect() as db:
            rows = db.execute("SELECT guild_id,user_id,joined_at,channel_id FROM activity_voice_sessions").fetchall()
            db.execute("DELETE FROM activity_voice_sessions")
            for row in rows:
                guild = self.bot.get_guild(row["guild_id"])
                member = guild.get_member(row["user_id"]) if guild else None
                if member and member.voice and member.voice.channel:
                    # Preserve time spent before the restart, then start a fresh in-memory interval.
                    elapsed = max(0, int((now - parse_time(row["joined_at"])).total_seconds()))
                    self.add_activity(row["guild_id"], row["user_id"], seconds=elapsed)
                    self.voice_sessions[(row["guild_id"], row["user_id"])] = now
                    db.execute("INSERT OR REPLACE INTO activity_voice_sessions(guild_id,user_id,joined_at,channel_id) VALUES(?,?,?,?)", (row["guild_id"], row["user_id"], now.isoformat(), member.voice.channel.id))
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.bot or not member.voice or not member.voice.channel:
                        continue
                    key = (guild.id, member.id)
                    if key not in self.voice_sessions:
                        self.voice_sessions[key] = now
                        db.execute("INSERT OR REPLACE INTO activity_voice_sessions(guild_id,user_id,joined_at,channel_id) VALUES(?,?,?,?)", (guild.id, member.id, now.isoformat(), member.voice.channel.id))

    async def flush_activity(self):
        now = utcnow()
        pending = self.activity_pending
        self.activity_pending = {}
        for key, started in list(self.voice_sessions.items()):
            elapsed = max(0, int((now - started).total_seconds()))
            if elapsed:
                self.add_to_pending_map(pending, key, seconds=elapsed)
                self.voice_sessions[key] = now
        if not pending:
            return
        bucket = hour_bucket(now)
        with connect() as db:
            for (guild_id, user_id), delta in pending.items():
                messages, seconds = int(delta["messages"]), int(delta["seconds"])
                if not messages and not seconds:
                    continue
                db.execute("INSERT INTO activity_stats(guild_id,user_id,message_count,voice_seconds) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET message_count=message_count+excluded.message_count,voice_seconds=voice_seconds+excluded.voice_seconds", (guild_id, user_id, messages, seconds))
                db.execute("INSERT INTO activity_buckets(guild_id,user_id,bucket_start,message_count,voice_seconds) VALUES(?,?,?,?,?) ON CONFLICT(guild_id,user_id,bucket_start) DO UPDATE SET message_count=message_count+excluded.message_count,voice_seconds=voice_seconds+excluded.voice_seconds", (guild_id, user_id, bucket, messages, seconds))

    @staticmethod
    def add_to_pending_map(target, key, messages=0, seconds=0):
        row = target.setdefault(key, {"messages": 0, "seconds": 0})
        row["messages"] += messages
        row["seconds"] += seconds

    def query_activity(self, guild_id, stat, period, page):
        column = "message_count" if stat == "messages" else "voice_seconds"
        offset = max(0, page) * PAGE_SIZE
        with connect() as db:
            if period == "all":
                rows = db.execute(f"SELECT user_id,{column} AS value FROM activity_stats WHERE guild_id=? AND {column}>0 ORDER BY {column} DESC,user_id ASC LIMIT ? OFFSET ?", (guild_id, PAGE_SIZE, offset)).fetchall()
                total = db.execute(f"SELECT COUNT(*) FROM activity_stats WHERE guild_id=? AND {column}>0", (guild_id,)).fetchone()[0]
            else:
                days = 7 if period == "weekly" else 31
                start = hour_bucket(utcnow() - timedelta(days=days))
                rows = db.execute(f"SELECT user_id,SUM({column}) AS value FROM activity_buckets WHERE guild_id=? AND bucket_start>=? GROUP BY user_id HAVING SUM({column})>0 ORDER BY value DESC,user_id ASC LIMIT ? OFFSET ?", (guild_id, start, PAGE_SIZE, offset)).fetchall()
                total = db.execute(f"SELECT COUNT(*) FROM (SELECT user_id FROM activity_buckets WHERE guild_id=? AND bucket_start>=? GROUP BY user_id HAVING SUM({column})>0)", (guild_id, start)).fetchone()[0]
        return rows, total

    def format_voice(self, seconds):
        hours, rem = divmod(int(seconds or 0), 3600)
        minutes = rem // 60
        return f"{hours:,}h {minutes:02d}m" if hours else f"{minutes:,}m"

    async def avatar(self, member, size):
        try:
            return Image.open(io.BytesIO(await member.display_avatar.read())).convert("RGB").resize((size, size))
        except Exception:
            return Image.new("RGB", (size, size), (55, 58, 68))

    async def activity_card(self, member, messages, voice, message_rank, voice_rank):
        image = Image.new("RGB", (1000, 390), (18, 20, 27))
        draw = ImageDraw.Draw(image)
        avatar = await self.avatar(member, 170)
        mask = Image.new("L", (170, 170), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 170, 170), fill=255)
        image.paste(avatar, (55, 60), mask)
        title = ImageFont.load_default(size=34)
        value = ImageFont.load_default(size=25)
        small = ImageFont.load_default(size=18)
        draw.text((270, 52), member.display_name[:30], fill="white", font=title)
        draw.text((270, 105), f"Messages: {messages:,}", fill=(205, 210, 220), font=value)
        draw.text((270, 145), f"Voice: {self.format_voice(voice)}", fill=(205, 210, 220), font=value)
        draw.text((270, 205), f"Message Rank: #{message_rank}", fill=(150, 190, 255), font=small)
        draw.text((270, 235), f"Voice Rank: #{voice_rank}", fill=(150, 190, 255), font=small)
        draw.text((55, 335), "LIGHTCORE • ACTIVITY STATS", fill=(135, 140, 153), font=small)
        out = io.BytesIO(); image.save(out, "PNG"); out.seek(0); return out

    @commands.hybrid_group(name="top", invoke_without_command=True, description="Show activity leaderboards.")
    async def top(self, ctx):
        await ctx.send(embed=discord.Embed(title="📊 LightCore Activity", description="Use `.top messages`, `.top messages weekly`, `.top messages monthly`, `.top voice`, `.top voice weekly`, or `.top voice monthly`.", color=discord.Color.blurple()))

    @top.command(name="messages")
    async def top_messages(self, ctx, period: str = "all"):
        period = period.lower() if period else "all"
        if period not in {"all", "weekly", "monthly"}:
            return await ctx.send(embed=self.error_embed("Period must be `all`, `weekly`, or `monthly`."))
        view = ActivityLeaderboardView(self, ctx, "messages", period)
        await ctx.send(embed=view.embed(), view=view)

    @top.command(name="voice")
    async def top_voice(self, ctx, period: str = "all"):
        period = period.lower() if period else "all"
        if period not in {"all", "weekly", "monthly"}:
            return await ctx.send(embed=self.error_embed("Period must be `all`, `weekly`, or `monthly`."))
        view = ActivityLeaderboardView(self, ctx, "voice", period)
        await ctx.send(embed=view.embed(), view=view)

    @commands.hybrid_command(name="mystats", description="Show a visual activity card for a member.")
    async def mystats(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await self.flush_activity()
        with connect() as db:
            row = db.execute("SELECT message_count,voice_seconds FROM activity_stats WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
            messages, voice = (row["message_count"], row["voice_seconds"]) if row else (0, 0)
            message_rank = db.execute("SELECT COUNT(*) FROM activity_stats WHERE guild_id=? AND message_count>?", (ctx.guild.id, messages)).fetchone()[0] + 1
            voice_rank = db.execute("SELECT COUNT(*) FROM activity_stats WHERE guild_id=? AND voice_seconds>?", (ctx.guild.id, voice)).fetchone()[0] + 1
        card = await self.activity_card(member, messages, voice, message_rank, voice_rank)
        await ctx.send(file=discord.File(card, filename="lightcore-activity.png"))

    def _bar(self, value, maximum):
        size = 12
        filled = int((value / maximum) * size) if maximum else 0
        return "█" * filled + "░" * (size - filled)

    @commands.hybrid_command(name="memberstats", description="Show server growth, activity, and retention statistics.")
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
            lines.append(f"{user.mention if user else row[0]} — {row['message_count']:,} messages")
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
        start = utcnow() - timedelta(days=days)
        with connect() as db:
            rows = db.execute("SELECT substr(created_at,1,10) day,event_type,COUNT(*) c FROM member_events WHERE guild_id=? AND created_at>=? AND event_type IN ('join','leave') GROUP BY day,event_type ORDER BY day", (ctx.guild.id, start.strftime("%Y-%m-%d %H:%M:%S"))).fetchall()
        by_day = {}
        for row in rows: by_day.setdefault(row[0], {})[row[1]] = row[2]
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
        await ctx.send(embed=discord.Embed(title="📈 Retention", description=f"Estimated retention: **{rate}%** based on recorded join/leave events.", color=discord.Color.blurple()))


async def setup(bot):
    await bot.add_cog(MemberStats(bot))
