import io
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from database import connect, ensure_guild

log = logging.getLogger(__name__)


class AdvancedSafe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started_at = getattr(bot, "started_at", time.monotonic())

    @commands.hybrid_command(name="weekly", description="Claim the weekly LightCoins reward.")
    @commands.cooldown(1, 604800, commands.BucketType.member)
    async def weekly(self, ctx):
        ensure_guild(ctx.guild.id)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, ctx.author.id))
            db.execute("UPDATE balances SET balance=balance+500 WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
        await ctx.send("🎁 Weekly reward: **500 LightCoins**.")

    @commands.hybrid_command(name="petadopt", description="Adopt a LightCore pet.")
    @commands.cooldown(1, 3600, commands.BucketType.member)
    async def petadopt(self, ctx, species: str = "fox", *, name: str = "Buddy"):
        allowed = {"fox", "wolf", "cat", "dog", "dragon", "owl", "rabbit"}
        species = species.lower()[:20]
        name = name.strip()[:32] or "Buddy"
        if species not in allowed:
            return await ctx.send("Choose: " + ", ".join(sorted(allowed)))
        with connect() as db:
            if db.execute("SELECT 1 FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone():
                return await ctx.send("🐾 You already have a pet in this server.")
            db.execute("INSERT INTO pets(guild_id,user_id,name,species) VALUES(?,?,?,?)", (ctx.guild.id, ctx.author.id, name, species))
        await ctx.send(f"🐾 Adopted **{name}** the {species}!")

    @commands.hybrid_command(name="pet", description="View your LightCore pet.")
    async def pet(self, ctx):
        with connect() as db:
            row = db.execute("SELECT name,species,level,energy FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
        if not row:
            return await ctx.send("🐾 No pet yet. Use `.petadopt`.")
        await ctx.send(f"🐾 **{row['name']}** the {row['species']} • Level {row['level']} • Energy {row['energy']}/100")

    @commands.hybrid_command(name="hunt", description="Hunt for LightCoins and train your pet.")
    @commands.cooldown(3, 60, commands.BucketType.member)
    async def hunt(self, ctx):
        amount = random.randint(15, 80)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, ctx.author.id))
            db.execute("UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?", (amount, ctx.guild.id, ctx.author.id))
            db.execute("UPDATE pets SET energy=MAX(0,energy-10), level=level+1 WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
        await ctx.send(f"🏹 Hunt complete: **+{amount} LightCoins**.")

    @commands.hybrid_command(name="battle", description="Run a harmless pet battle between two players.")
    @commands.cooldown(2, 60, commands.BucketType.member)
    async def battle(self, ctx, opponent: discord.Member):
        if opponent.bot or opponent.id == ctx.author.id:
            return await ctx.send("Choose another real member.")
        with connect() as db:
            me = db.execute("SELECT level FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
            them = db.execute("SELECT level FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, opponent.id)).fetchone()
            if not me or not them:
                return await ctx.send("Both players need pets first.")
            winner = ctx.author if me["level"] + random.randint(0, 4) >= them["level"] + random.randint(0, 4) else opponent
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, winner.id))
            db.execute("UPDATE balances SET balance=balance+50 WHERE guild_id=? AND user_id=?", (ctx.guild.id, winner.id))
        await ctx.send(f"⚔️ **{winner.display_name}** won and earned **50 LightCoins**.")

    @commands.hybrid_command(name="massban", description="Ban up to 25 members by mention or ID.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def massban(self, ctx, members: str, *, reason: str = "Mass moderation"):
        ids = list(dict.fromkeys(int(x) for x in re.findall(r"\d{15,20}", members)))[:25]
        if not ids:
            return await ctx.send("❌ Provide member mentions or IDs.")
        ok = bad = 0
        for user_id in ids:
            try:
                await ctx.guild.ban(discord.Object(id=user_id), reason=reason, delete_message_seconds=0)
                ok += 1
            except (discord.Forbidden, discord.HTTPException):
                bad += 1
        await ctx.send(f"Moderation batch finished: **{ok}** succeeded, **{bad}** failed.")

    async def preset_mute(self, ctx, member, minutes, reason):
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        with connect() as db:
            db.execute("INSERT INTO moderation_logs(guild_id,action,target_id,moderator_id,reason) VALUES(?,?,?,?,?)", (ctx.guild.id, f"mute_{minutes}m", member.id, ctx.author.id, reason))
        await ctx.send(f"🔇 {member.mention} timed out for **{minutes} minutes**.")

    @commands.hybrid_command(name="mute5", description="Timeout a member for 5 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute5(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self.preset_mute(ctx, member, 5, reason)

    @commands.hybrid_command(name="mute15", description="Timeout a member for 15 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute15(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self.preset_mute(ctx, member, 15, reason)

    @commands.hybrid_command(name="mute60", description="Timeout a member for 60 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute60(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self.preset_mute(ctx, member, 60, reason)

    @commands.hybrid_command(name="modcases", description="Show recent numbered moderation cases.")
    @commands.has_permissions(moderate_members=True)
    async def modcases(self, ctx, limit: int = 10):
        limit = max(1, min(limit, 20))
        with connect() as db:
            rows = db.execute("SELECT id,action,target_id,moderator_id,reason FROM moderation_logs WHERE guild_id=? ORDER BY id DESC LIMIT ?", (ctx.guild.id, limit)).fetchall()
        if not rows:
            return await ctx.send("No moderation cases recorded.")
        await ctx.send("\n".join(f"**Case #{r['id']}** • `{r['action']}` • <@{r['target_id']}> • <@{r['moderator_id']}> • {r['reason'] or 'No reason'}" for r in rows))

    def ticket_row(self, ctx):
        with connect() as db:
            return db.execute("SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'", (ctx.guild.id, ctx.channel.id)).fetchone()

    @commands.hybrid_command(name="ticketclaim", description="Claim the current open ticket.")
    @commands.has_permissions(manage_channels=True)
    async def ticketclaim(self, ctx):
        row = self.ticket_row(ctx)
        if not row:
            return await ctx.send("❌ This is not an open LightCore ticket.")
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row["id"],))
            db.execute("UPDATE ticket_meta SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (ctx.author.id, row["id"]))
        await ctx.send(f"🎫 Ticket claimed by {ctx.author.mention}.")

    @commands.hybrid_command(name="ticketpriority", description="Set current ticket priority.")
    @commands.has_permissions(manage_channels=True)
    async def ticketpriority(self, ctx, priority: str):
        priority = priority.lower()
        if priority not in {"low", "normal", "high", "urgent"}:
            return await ctx.send("Use `low`, `normal`, `high`, or `urgent`.")
        row = self.ticket_row(ctx)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row["id"],))
            db.execute("UPDATE ticket_meta SET priority=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (priority, row["id"]))
        await ctx.send(f"🏷️ Priority: **{priority}**.")

    @commands.hybrid_command(name="ticketautoclose", description="Set ticket inactivity auto-close minutes; 0 disables it.")
    @commands.has_permissions(manage_channels=True)
    async def ticketautoclose(self, ctx, minutes: int):
        row = self.ticket_row(ctx)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        minutes = max(0, min(minutes, 10080))
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row["id"],))
            db.execute("UPDATE ticket_meta SET auto_close_minutes=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (minutes, row["id"]))
        await ctx.send("♻️ Auto-close disabled." if minutes == 0 else f"♻️ Auto-close: **{minutes} minutes**.")

    @commands.hybrid_command(name="giveawayreroll", description="Reroll an ended giveaway by message ID.")
    @commands.has_permissions(manage_guild=True)
    async def giveawayreroll(self, ctx, message_id: int):
        with connect() as db:
            giveaway = db.execute("SELECT id,prize FROM giveaways WHERE guild_id=? AND message_id=? AND status='ended'", (ctx.guild.id, message_id)).fetchone()
            if not giveaway:
                return await ctx.send("❌ Ended giveaway not found in this server.")
            rows = db.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (giveaway["id"],)).fetchall()
        if not rows:
            return await ctx.send("❌ No eligible entries remain.")
        winner = random.choice(rows)["user_id"]
        await ctx.send(f"🎉 Rerolled **{giveaway['prize']}** — winner: <@{winner}>")

    @commands.hybrid_command(name="levelroles", description="Show configured level milestone roles.")
    async def levelroles(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT level,role_id FROM level_rewards WHERE guild_id=? ORDER BY level", (ctx.guild.id,)).fetchall()
        await ctx.send("\n".join(f"Level **{r['level']}** → <@&{r['role_id']}>" for r in rows) if rows else "⭐ No milestone roles configured.")

    @commands.hybrid_command(name="xpboost", description="Give a member a temporary 2× XP boost.")
    @commands.has_permissions(manage_guild=True)
    async def xpboost(self, ctx, member: discord.Member, minutes: int = 60):
        minutes = max(5, min(minutes, 10080))
        expires = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat()
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO xp_boosters(guild_id,user_id,multiplier,expires_at) VALUES(?,?,?,?)", (ctx.guild.id, member.id, 2.0, expires))
        await ctx.send(f"🚀 {member.mention}: **2× XP** for {minutes} minutes.")

    @commands.hybrid_command(name="lbpage", description="Show a paginated level leaderboard page.")
    async def lbpage(self, ctx, page: int = 1):
        page = max(1, page); offset = (page - 1) * 10
        with connect() as db:
            rows = db.execute("SELECT user_id,level,xp FROM xp WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10 OFFSET ?", (ctx.guild.id, offset)).fetchall()
        if not rows:
            return await ctx.send("No users on that leaderboard page.")
        text = "\n".join(f"**{offset+i}.** <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1))
        await ctx.send(embed=discord.Embed(title=f"⭐ Leaderboard • Page {page}", description=text, color=discord.Color.blurple()))

    @commands.hybrid_command(name="uptime", description="Show LightCore uptime.")
    async def uptime(self, ctx):
        total = int(time.monotonic() - self.started_at); d, total = divmod(total, 86400); h, total = divmod(total, 3600); m, s = divmod(total, 60)
        await ctx.send(f"⏱️ Uptime: **{d}d {h}h {m}m {s}s**")

    @commands.hybrid_command(name="stats", description="Show LightCore server and bot statistics.")
    async def stats(self, ctx):
        await ctx.send(embed=discord.Embed(title="📊 LightCore Stats", description=f"Servers: **{len(self.bot.guilds)}**\nCached users: **{len(self.bot.users)}**\nLatency: **{round(self.bot.latency*1000)}ms**\nThis server: **{ctx.guild.member_count} members**", color=discord.Color.blurple()))

    @commands.hybrid_command(name="invites", description="Show current server invite usage.")
    @commands.has_permissions(manage_guild=True)
    async def invites(self, ctx):
        try:
            invites = await ctx.guild.invites()
        except discord.Forbidden:
            return await ctx.send("❌ I need Manage Server to read invites.")
        invites = sorted(invites, key=lambda x: x.uses or 0, reverse=True)[:15]
        await ctx.send("🔗 " + "\n".join(f"`{i.code}` — {i.uses or 0} uses — {i.inviter.mention if i.inviter else 'unknown'}" for i in invites) if invites else "No invites found.")

    @commands.hybrid_command(name="serverbackup", description="Export this server's LightCore records as JSON.")
    @commands.has_permissions(manage_guild=True)
    async def serverbackup(self, ctx):
        gid = ctx.guild.id
        tables = ("guild_settings", "warnings", "moderation_logs", "event_logs", "xp", "level_rewards", "balances", "custom_commands", "shop_items", "role_panels", "tickets", "member_events", "applications", "application_submissions", "temp_voice_channels", "pets", "reward_claims", "xp_boosters")
        with connect() as db:
            data = {table: [dict(r) for r in db.execute(f"SELECT * FROM {table} WHERE guild_id=?", (gid,)).fetchall()] for table in tables}
        raw = json.dumps({"version": 1, "guild_id": gid, "data": data}, default=str, indent=2).encode()
        await ctx.send("📦 Backup created.", file=discord.File(io.BytesIO(raw), filename=f"lightcore-{gid}-backup.json"))

    @commands.hybrid_command(name="serverrestore", description="Restore a LightCore JSON backup for this server only.")
    @commands.has_permissions(manage_guild=True)
    async def serverrestore(self, ctx, backup: discord.Attachment):
        try:
            payload = json.loads((await backup.read()).decode())
            if int(payload.get("guild_id")) != ctx.guild.id:
                return await ctx.send("❌ Cross-server restore blocked.")
            tables = {"guild_settings", "warnings", "moderation_logs", "event_logs", "xp", "level_rewards", "balances", "custom_commands", "shop_items", "role_panels", "tickets", "member_events", "applications", "application_submissions", "temp_voice_channels", "pets", "reward_claims", "xp_boosters"}
            with connect() as db:
                for table in tables:
                    for row in payload.get("data", {}).get(table, []):
                        if not isinstance(row, dict) or ("guild_id" in row and int(row["guild_id"]) != ctx.guild.id):
                            continue
                        cols = list(row); values = [row[c] for c in cols]
                        db.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", values)
            await ctx.send("♻️ Guild-scoped backup restored.")
        except Exception as exc:
            log.exception("Backup restore failed")
            await ctx.send(f"❌ Restore failed safely: `{type(exc).__name__}`.")

    @commands.hybrid_command(name="invite", description="Show the public LightCore invite link.")
    async def invite(self, ctx):
        url = os.getenv("INVITE_URL")
        if not url:
            return await ctx.send("🔗 Public invite URL is not configured yet. Set `INVITE_URL` on the host.")
        await ctx.send(f"🚀 Invite LightCore: {url}")


async def setup(bot):
    await bot.add_cog(AdvancedSafe(bot))
