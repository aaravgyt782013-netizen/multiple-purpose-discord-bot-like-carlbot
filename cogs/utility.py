import time
from datetime import datetime, timezone

import discord
from discord.ext import commands


BOT_VERSION = "1.0.0"


class Utility(commands.Cog):
    """R.O.T.I.-style utility and information commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="uptime", description="Show how long LightCore has been online.")
    async def uptime(self, ctx):
        seconds = max(0, int(time.monotonic() - getattr(self.bot, "started_at", time.monotonic())))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, seconds = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or days:
            parts.append(f"{hours}h")
        if minutes or hours or days:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds:02d}s")
        started = getattr(self.bot, "started_at_wall", None)
        embed = discord.Embed(
            title="⏱️ LightCore • Uptime",
            description=f"LightCore has been online for **{' '.join(parts)}**.",
            color=discord.Color.blurple(),
        )
        if started:
            embed.add_field(name="Started", value=discord.utils.format_dt(started, "F"), inline=False)
        embed.set_footer(text="LightCore • Utility")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="botinfo", description="Show LightCore version, library, server and shard information.")
    async def botinfo(self, ctx):
        user_count = sum(g.member_count or 0 for g in self.bot.guilds)
        shard_count = self.bot.shard_count or 1
        shard_id = ctx.guild.shard_id if ctx.guild else 0
        embed = discord.Embed(title="🤖 LightCore • Bot Info", color=discord.Color.blurple())
        embed.add_field(name="Bot Version", value=BOT_VERSION, inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds):,}", inline=True)
        embed.add_field(name="Users", value=f"{user_count:,} cached memberships", inline=True)
        embed.add_field(name="Shards", value=f"{shard_count:,}", inline=True)
        embed.add_field(name="Current Shard", value=str(shard_id), inline=True)
        if self.bot.user:
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text="LightCore • Bot Information")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="avatar", description="Show a user's full avatar.")
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        avatar = member.display_avatar
        embed = discord.Embed(title=f"🖼️ {member.display_name}'s Avatar", color=discord.Color.blurple())
        embed.set_image(url=avatar.url)
        embed.add_field(name="Open Full Size", value=f"[Click here]({avatar.url})", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banner", description="Show a user's profile banner if one is set.")
    async def banner(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        try:
            user = await self.bot.fetch_user(member.id)
        except discord.HTTPException:
            return await ctx.send("❌ I could not fetch that user's profile right now.")
        if not user.banner:
            return await ctx.send(f"❌ **{member.display_name}** does not have a profile banner set.")
        embed = discord.Embed(title=f"🎨 {member.display_name}'s Banner", color=discord.Color.blurple())
        embed.set_image(url=user.banner.url)
        embed.add_field(name="Open Full Size", value=f"[Click here]({user.banner.url})", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="servericon", description="Show the current server icon full-size.")
    async def servericon(self, ctx):
        guild = ctx.guild
        if not guild:
            return await ctx.send("❌ This command can only be used in a server.")
        if not guild.icon:
            return await ctx.send("❌ This server does not have an icon set.")
        embed = discord.Embed(title=f"🖼️ {guild.name} • Server Icon", color=discord.Color.blurple())
        embed.set_image(url=guild.icon.url)
        embed.add_field(name="Open Full Size", value=f"[Click here]({guild.icon.url})", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="roleinfo", description="Show details about a server role.")
    async def roleinfo(self, ctx, role: discord.Role):
        members = sum(1 for member in ctx.guild.members if role in member.roles)
        enabled = [name.replace("_", " ").title() for name, value in role.permissions if value]
        permissions = ", ".join(enabled[:20]) if enabled else "None"
        if len(enabled) > 20:
            permissions += f" … (+{len(enabled) - 20} more)"
        embed = discord.Embed(title=f"🏷️ Role Info • {role.name}", color=role.color if role.color.value else discord.Color.blurple())
        embed.add_field(name="Mention", value=role.mention, inline=True)
        embed.add_field(name="Color", value=f"`{role.color}`", inline=True)
        embed.add_field(name="Position", value=str(role.position), inline=True)
        embed.add_field(name="Members", value=f"{members:,}", inline=True)
        embed.add_field(name="Hoisted", value=str(role.hoist), inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(role.created_at, "F"), inline=False)
        embed.add_field(name="Permissions", value=permissions[:1024], inline=False)
        embed.set_footer(text=f"Role ID: {role.id} • LightCore")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="channelinfo", description="Show details about a channel.")
    async def channelinfo(self, ctx, channel: discord.abc.GuildChannel = None):
        channel = channel or ctx.channel
        channel_type = str(channel.type).replace("ChannelType.", "").replace("_", " ").title()
        topic = getattr(channel, "topic", None) or "None"
        slowmode = getattr(channel, "slowmode_delay", None)
        slowmode_text = f"{slowmode}s" if slowmode is not None else "Not applicable"
        embed = discord.Embed(title=f"📺 Channel Info • #{channel.name}", color=discord.Color.blurple())
        embed.add_field(name="Type", value=channel_type, inline=True)
        embed.add_field(name="Category", value=channel.category.mention if getattr(channel, "category", None) else "None", inline=True)
        embed.add_field(name="Created", value=discord.utils.format_dt(channel.created_at, "F"), inline=True)
        embed.add_field(name="Slowmode", value=slowmode_text, inline=True)
        embed.add_field(name="Topic", value=topic[:1024], inline=False)
        embed.set_footer(text=f"Channel ID: {channel.id} • LightCore")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="firstmessage", description="Find and link the first message in a channel.")
    async def firstmessage(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        try:
            async for message in channel.history(limit=1, oldest_first=True):
                embed = discord.Embed(
                    title=f"📜 First Message • #{channel.name}",
                    description=f"[Jump to the first message]({message.jump_url})",
                    color=discord.Color.blurple(),
                )
                embed.add_field(name="Author", value=message.author.mention, inline=True)
                embed.add_field(name="Sent", value=discord.utils.format_dt(message.created_at, "F"), inline=True)
                embed.add_field(name="Message ID", value=str(message.id), inline=True)
                preview = message.content.strip() or "[No text content]"
                embed.add_field(name="Content", value=preview[:1024], inline=False)
                await ctx.send(embed=embed)
                return
        except discord.Forbidden:
            return await ctx.send("❌ I need View Channel and Read Message History to find the first message.")
        except discord.HTTPException:
            return await ctx.send("❌ Discord rejected the history request. Try again later.")
        await ctx.send("❌ No messages were found in that channel.")


async def setup(bot):
    await bot.add_cog(Utility(bot))
