import time
from datetime import datetime, timezone

import discord
from discord.ext import commands


class Status(commands.Cog):
    """Live Discord presence lookup; no historical presence database is created."""

    def __init__(self, bot):
        self.bot = bot
        self.status_since = {}

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        key = (after.guild.id, after.id) if after.guild else None
        if key is None:
            return
        before_state = (before.status, self._activity_key(before), self._platform_key(before))
        after_state = (after.status, self._activity_key(after), self._platform_key(after))
        if key not in self.status_since:
            self.status_since[key] = time.monotonic()
        if before_state != after_state:
            self.status_since[key] = time.monotonic()

    @staticmethod
    def _activity_key(member):
        activities = []
        for activity in member.activities or ():
            if isinstance(activity, discord.CustomActivity):
                activities.append(("custom", activity.name, activity.state))
            else:
                activities.append((type(activity).__name__, getattr(activity, "name", None), getattr(activity, "details", None), getattr(activity, "state", None)))
        return tuple(activities)

    @staticmethod
    def _platform_key(member):
        status = member.desktop_status, member.mobile_status, member.web_status
        return tuple(str(value) for value in status)

    @staticmethod
    def _status_label(status):
        return {
            discord.Status.online: ("🟢", "Online"),
            discord.Status.idle: ("🌙", "Idle"),
            discord.Status.dnd: ("⛔", "Do Not Disturb"),
            discord.Status.offline: ("⚫", "Offline"),
        }.get(status, ("⚫", str(status).title()))

    @staticmethod
    def _activity_text(activity):
        if isinstance(activity, discord.CustomActivity):
            return f"Custom status: {activity.state or activity.name or 'No text'}"
        if isinstance(activity, discord.Streaming):
            return f"Streaming: {activity.name or 'Unknown'}"
        if isinstance(activity, discord.Spotify):
            return f"Listening: {activity.title} — {activity.artist}"
        if isinstance(activity, discord.Game):
            return f"Playing: {activity.name}"
        if isinstance(activity, discord.Activity):
            kind = str(activity.type).replace("ActivityType.", "").replace("_", " ").title()
            return f"{kind}: {activity.name or 'Unknown'}"
        return str(activity)

    @staticmethod
    def _platform_text(member):
        platforms = []
        if member.desktop_status != discord.Status.offline:
            platforms.append("Desktop")
        if member.mobile_status != discord.Status.offline:
            platforms.append("Mobile")
        if member.web_status != discord.Status.offline:
            platforms.append("Web")
        return ", ".join(platforms) if platforms else "Not detectable"

    @commands.hybrid_command(name="status", description="Show a user's current Discord presence and activity.")
    async def status(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        emoji, label = self._status_label(member.status)
        activities = [self._activity_text(a) for a in (member.activities or ())]
        custom = next((a.state or a.name for a in (member.activities or ()) if isinstance(a, discord.CustomActivity) and (a.state or a.name)), None)
        non_custom = [text for text in activities if not text.startswith("Custom status:")]
        key = (member.guild.id, member.id)
        elapsed = time.monotonic() - self.status_since[key] if key in self.status_since else None

        embed = discord.Embed(title=f"{emoji} {member.display_name}'s Status", color=discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Presence", value=f"**{label}**", inline=True)
        embed.add_field(name="Platform", value=self._platform_text(member), inline=True)
        embed.add_field(name="Activity", value="\n".join(non_custom) if non_custom else "Nothing detectable", inline=False)
        embed.add_field(name="Custom status", value=custom or "None", inline=False)
        if elapsed is not None:
            embed.add_field(name="Status duration", value=self._duration(elapsed) + " (observed by LightCore)", inline=False)
        else:
            embed.add_field(name="Status duration", value="Not available yet — duration starts when LightCore observes the presence.", inline=False)
        embed.set_footer(text=f"LightCore • Live presence • {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
        await ctx.send(embed=embed)

    @staticmethod
    def _duration(seconds):
        seconds = max(0, int(seconds))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        if days:
            return f"{days}d {hours}h {minutes}m"
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"


async def setup(bot):
    await bot.add_cog(Status(bot))
