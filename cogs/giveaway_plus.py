import random

import discord
from discord.ext import commands

from database import connect


class GiveawayPlus(commands.Cog):
    @commands.hybrid_command(name="giveawaybonus", description="Configure extra entry weight for a role on an active giveaway.")
    @commands.has_permissions(manage_guild=True)
    async def giveawaybonus(self, ctx, message_id: int, role: discord.Role, multiplier: int = 2):
        multiplier = max(1, min(multiplier, 10))
        with connect() as db:
            row = db.execute("SELECT id FROM giveaways WHERE guild_id=? AND message_id=? AND status='active'", (ctx.guild.id, message_id)).fetchone()
            if not row:
                return await ctx.send("❌ Active giveaway not found in this server.")
            db.execute("INSERT OR REPLACE INTO giveaway_bonus_roles(giveaway_id,role_id,multiplier) VALUES(?,?,?)", (row['id'], role.id, multiplier))
        await ctx.send(f"🎁 {role.mention} now has **{multiplier}×** entry weight for this giveaway.")

    @commands.hybrid_command(name="giveawaypick", description="Pick a weighted winner from an active giveaway's recorded entries.")
    @commands.has_permissions(manage_guild=True)
    async def giveawaypick(self, ctx, message_id: int):
        with connect() as db:
            giveaway = db.execute("SELECT id,prize FROM giveaways WHERE guild_id=? AND message_id=? AND status='active'", (ctx.guild.id, message_id)).fetchone()
            if not giveaway:
                return await ctx.send("❌ Active giveaway not found in this server.")
            entries = db.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (giveaway['id'],)).fetchall()
            bonuses = {r['role_id']: r['multiplier'] for r in db.execute("SELECT role_id,multiplier FROM giveaway_bonus_roles WHERE giveaway_id=?", (giveaway['id'],)).fetchall()}
        weighted = []
        for entry in entries:
            member = ctx.guild.get_member(entry['user_id'])
            if not member or member.bot:
                continue
            weight = max([bonuses.get(role.id, 1) for role in member.roles] or [1])
            weighted.extend([member] * weight)
        if not weighted:
            return await ctx.send("❌ No eligible entries found.")
        winner = random.choice(weighted)
        await ctx.send(f"🎉 Weighted winner for **{giveaway['prize']}**: {winner.mention}")


async def setup(bot):
    await bot.add_cog(GiveawayPlus(bot))
