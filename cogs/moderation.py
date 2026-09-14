import discord
from discord.ext import commands

from database import connect, ensure_guild


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.ban(reason=reason)
        await ctx.send(f"🔨 Banned {member.mention}: {reason}")

    @commands.hybrid_command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"👢 Kicked {member.mention}: {reason}")

    @commands.hybrid_command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
        await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"🔇 Timed out {member.mention} for {minutes} minutes.")

    @commands.hybrid_command(name="warn")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        ensure_guild(ctx.guild.id)
        with connect() as db:
            db.execute("INSERT INTO warnings (guild_id,user_id,moderator_id,reason) VALUES (?,?,?,?)", (ctx.guild.id, member.id, ctx.author.id, reason))
        await ctx.send(f"⚠️ Warned {member.mention}: {reason}")

    @commands.hybrid_command(name="warnings")
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx, member: discord.Member):
        with connect() as db:
            rows = db.execute("SELECT reason, moderator_id, created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 10", (ctx.guild.id, member.id)).fetchall()
        if not rows:
            return await ctx.send(f"{member.mention} has no warnings.")
        text = "\n".join(f"• {r['reason']} — <@{r['moderator_id']}> ({r['created_at']})" for r in rows)
        await ctx.send(embed=discord.Embed(title=f"Warnings: {member}", description=text, color=discord.Color.orange()))

    @ban.error
    @kick.error
    @mute.error
    @warn.error
    @warnings.error
    async def moderation_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use that command.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Please check the member and command arguments.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
