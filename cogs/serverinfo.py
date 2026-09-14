import discord
from discord.ext import commands


class ServerInfo(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.hybrid_command(name="serverinfo", description="Show information about this server.")
    async def serverinfo(self, ctx):
        guild = ctx.guild
        if guild is None: return await ctx.send("This command can only be used in a server.")
        created = discord.utils.format_dt(guild.created_at, "F")
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon: embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Members", value=f"{guild.member_count:,}")
        embed.add_field(name="Boosts", value=f"Level {guild.premium_tier} • {guild.premium_subscription_count or 0}")
        embed.add_field(name="Created", value=created)
        embed.add_field(name="Channels", value=str(len(guild.channels)))
        embed.add_field(name="Text / Voice", value=f"{len(guild.text_channels)} / {len(guild.voice_channels)}")
        embed.add_field(name="Roles", value=str(max(0, len(guild.roles) - 1)))
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else str(guild.owner_id))
        embed.set_footer(text="LightCore • Server Info")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="userinfo", description="Show information about a member.")
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"User Info • {member}", color=member.color if member.color.value else discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        roles = [role.mention for role in reversed(member.roles[1:])]
        embed.add_field(name="Joined", value=discord.utils.format_dt(member.joined_at, "F") if member.joined_at else "Unknown")
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, "F"))
        embed.add_field(name="Account Age", value=discord.utils.format_dt(member.created_at, "R"))
        embed.add_field(name="Roles", value=" ".join(roles[:20]) if roles else "None", inline=False)
        embed.add_field(name="Avatar", value=f"[Open avatar]({member.display_avatar.url})", inline=False)
        embed.set_footer(text=f"ID: {member.id} • LightCore")
        await ctx.send(embed=embed)


async def setup(bot): await bot.add_cog(ServerInfo(bot))
