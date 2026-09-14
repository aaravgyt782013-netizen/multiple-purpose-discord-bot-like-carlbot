from datetime import timedelta

import discord
from discord.ext import commands

from database import connect, ensure_guild


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log_action(self, guild_id, action, target_id, moderator_id, reason):
        with connect() as db:
            cur = db.execute("INSERT INTO moderation_logs(guild_id,action,target_id,moderator_id,reason) VALUES(?,?,?,?,?)", (guild_id, action, target_id, moderator_id, reason))
            return cur.lastrowid

    @commands.hybrid_command(name="ban", aliases=["b"], description="Ban a member.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.ban(reason=reason)
        case = self.log_action(ctx.guild.id, "ban", member.id, ctx.author.id, reason)
        await ctx.send(f"🔨 Banned {member.mention} • Case #{case}: {reason}")

    @commands.hybrid_command(name="kick", aliases=["k"], description="Kick a member.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.kick(reason=reason)
        case = self.log_action(ctx.guild.id, "kick", member.id, ctx.author.id, reason)
        await ctx.send(f"👢 Kicked {member.mention} • Case #{case}: {reason}")

    @commands.hybrid_command(name="mute", aliases=["m"], description="Timeout a member for a number of minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
        minutes = max(1, min(minutes, 40320))
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        case = self.log_action(ctx.guild.id, "mute", member.id, ctx.author.id, reason)
        await ctx.send(f"🔇 Timed out {member.mention} for {minutes} minutes • Case #{case}.")

    @commands.hybrid_command(name="warn", description="Warn a member; 3 warnings automatically timeout for 10 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        ensure_guild(ctx.guild.id)
        with connect() as db:
            db.execute("INSERT INTO warnings (guild_id,user_id,moderator_id,reason) VALUES (?,?,?,?)", (ctx.guild.id, member.id, ctx.author.id, reason))
            count = db.execute("SELECT COUNT(*) AS c FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()["c"]
        case = self.log_action(ctx.guild.id, "warn", member.id, ctx.author.id, reason)
        extra = ""
        if count >= 3 and not member.guild_permissions.administrator:
            try:
                await member.timeout(discord.utils.utcnow() + timedelta(minutes=10), reason=f"Automatic punishment at {count} warnings")
                auto_case = self.log_action(ctx.guild.id, "auto_timeout", member.id, self.bot.user.id, f"Reached {count} warnings")
                extra = f" Automatic timeout applied • Case #{auto_case}."
            except discord.HTTPException:
                extra = " Automatic timeout could not be applied; check my Moderate Members permission."
        await ctx.send(f"⚠️ Warned {member.mention} ({count} total) • Case #{case}.{extra}")

    @commands.hybrid_command(name="warnings", description="Show a member's recent warnings.")
    @commands.has_permissions(moderate_members=True)
    async def warnings(self, ctx, member: discord.Member):
        with connect() as db:
            rows = db.execute("SELECT reason,moderator_id,created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 10", (ctx.guild.id, member.id)).fetchall()
        if not rows:
            return await ctx.send(f"{member.mention} has no warnings.")
        text = "\n".join(f"• {r['reason']} — <@{r['moderator_id']}> ({r['created_at']})" for r in rows)
        await ctx.send(embed=discord.Embed(title=f"Warnings: {member}", description=text, color=discord.Color.orange()))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
