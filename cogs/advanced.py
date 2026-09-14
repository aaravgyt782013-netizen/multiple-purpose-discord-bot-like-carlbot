import io
import json
import logging
import random
import re
from datetime import timedelta

import discord
from discord.ext import commands, tasks

from database import connect, ensure_guild

log = logging.getLogger(__name__)


class Advanced(commands.Cog):
    """Public-bot expansion features with guild-scoped persistence and cooldowns."""

    def __init__(self, bot):
        self.bot = bot
        self.started_at = getattr(bot, "started_at", __import__("time").monotonic())
        self.invites = {}
        self.ticket_watchdog.start()

    def cog_unload(self):
        self.ticket_watchdog.cancel()

    # ---------- Economy / progression ----------
    @commands.hybrid_command(name="weekly", description="Claim the weekly LightCoins reward.")
    @commands.cooldown(1, 604800, commands.BucketType.member)
    async def weekly(self, ctx):
        ensure_guild(ctx.guild.id)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, ctx.author.id))
            db.execute("UPDATE balances SET balance=balance+500 WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id))
        await ctx.send("🎁 You claimed **500 LightCoins** for your weekly reward!")

    @commands.hybrid_command(name="pet", description="View your LightCore pet.")
    @commands.cooldown(3, 20, commands.BucketType.member)
    async def pet(self, ctx):
        with connect() as db:
            row = db.execute("SELECT * FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
        if not row:
            return await ctx.send("🐾 You do not have a pet yet. Use `.petadopt`.")
        await ctx.send(f"🐾 **{row['name']}** the {row['species']} • Level {row['level']} • Energy {row['energy']}/100")

    @commands.hybrid_command(name="petadopt", description="Adopt a pet.")
    @commands.cooldown(1, 3600, commands.BucketType.member)
    async def petadopt(self, ctx, species: str = "fox", *, name: str = "Buddy"):
        species = species.lower()[:20]
        name = name.strip()[:32] or "Buddy"
        allowed = {"fox", "wolf", "cat", "dog", "dragon", "owl", "rabbit"}
        if species not in allowed:
            return await ctx.send(f"Choose a pet species from: {', '.join(sorted(allowed))}.")
        with connect() as db:
            existing = db.execute("SELECT 1 FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
            if existing:
                return await ctx.send("🐾 You already have a pet here.")
            db.execute("INSERT INTO pets(guild_id,user_id,name,species) VALUES(?,?,?,?)", (ctx.guild.id, ctx.author.id, name, species))
        await ctx.send(f"🐾 Adopted **{name}** the {species}!")

    @commands.hybrid_command(name="hunt", description="Hunt for a random amount of LightCoins.")
    @commands.cooldown(3, 60, commands.BucketType.member)
    async def hunt(self, ctx):
        amount = random.randint(15, 80)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, ctx.author.id))
            db.execute("UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?", (amount, ctx.guild.id, ctx.author.id))
            pet = db.execute("SELECT name,energy,level FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
            if pet:
                db.execute("UPDATE pets SET energy=MAX(0, energy-10), level=level+? WHERE guild_id=? AND user_id=?", (1 if random.random() < .2 else 0, ctx.guild.id, ctx.author.id))
        await ctx.send(f"🏹 You found **{amount} LightCoins** while hunting!")

    @commands.hybrid_command(name="battle", description="Battle another user's pet for a harmless XP/coin reward.")
    @commands.cooldown(2, 60, commands.BucketType.member)
    async def battle(self, ctx, opponent: discord.Member):
        if opponent.bot or opponent.id == ctx.author.id:
            return await ctx.send("Choose another real server member.")
        with connect() as db:
            me = db.execute("SELECT * FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, ctx.author.id)).fetchone()
            them = db.execute("SELECT * FROM pets WHERE guild_id=? AND user_id=?", (ctx.guild.id, opponent.id)).fetchone()
            if not me or not them:
                return await ctx.send("Both players need a pet first. Use `.petadopt`.")
            winner = ctx.author if (me["level"] + random.randint(0, 4)) >= (them["level"] + random.randint(0, 4)) else opponent
            db.execute("INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)", (ctx.guild.id, winner.id))
            db.execute("UPDATE balances SET balance=balance+50 WHERE guild_id=? AND user_id=?", (ctx.guild.id, winner.id))
        await ctx.send(f"⚔️ **{winner.display_name}** won the pet battle and earned 50 LightCoins!")

    # ---------- Moderation ----------
    @commands.hybrid_command(name="massban", description="Ban multiple members by mention or ID.")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def massban(self, ctx, members: str, *, reason: str = "Mass moderation"):
        ids = [int(x) for x in re.findall(r"\d{15,20}", members)]
        if not ids:
            return await ctx.send("❌ Provide one or more member mentions/IDs.")
        ids = list(dict.fromkeys(ids))[:25]
        success = 0
        failed = 0
        for user_id in ids:
            try:
                await ctx.guild.ban(discord.Object(id=user_id), reason=reason, delete_message_seconds=0)
                success += 1
            except (discord.Forbidden, discord.HTTPException):
                failed += 1
        await ctx.send(f"🔨 Mass ban complete: **{success}** succeeded, **{failed}** failed.")

    async def _preset_mute(self, ctx, member, minutes, reason):
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
        with connect() as db:
            db.execute("INSERT INTO moderation_logs(guild_id,action,target_id,moderator_id,reason) VALUES(?,?,?,?,?)", (ctx.guild.id, f"mute_{minutes}m", member.id, ctx.author.id, reason))
        await ctx.send(f"🔇 Timed out {member.mention} for **{minutes} minutes**.")

    @commands.hybrid_command(name="mute5", description="Timeout a member for 5 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute5(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self._preset_mute(ctx, member, 5, reason)

    @commands.hybrid_command(name="mute15", description="Timeout a member for 15 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute15(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self._preset_mute(ctx, member, 15, reason)

    @commands.hybrid_command(name="mute60", description="Timeout a member for 60 minutes.")
    @commands.has_permissions(moderate_members=True)
    async def mute60(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        await self._preset_mute(ctx, member, 60, reason)

    @commands.hybrid_command(name="modcases", description="Show recent numbered moderation cases.")
    @commands.has_permissions(moderate_members=True)
    async def modcases(self, ctx, limit: int = 10):
        limit = max(1, min(limit, 20))
        with connect() as db:
            rows = db.execute("SELECT id,action,target_id,moderator_id,reason,created_at FROM moderation_logs WHERE guild_id=? ORDER BY id DESC LIMIT ?", (ctx.guild.id, limit)).fetchall()
        if not rows:
            return await ctx.send("No moderation cases recorded yet.")
        text = "\n".join(f"**Case #{r['id']}** • `{r['action']}` • <@{r['target_id']}> • <@{r['moderator_id']}> • {r['reason'] or 'No reason'}" for r in rows)
        await ctx.send(embed=discord.Embed(title="🧾 Moderation Cases", description=text, color=discord.Color.orange()))

    # ---------- Tickets ----------
    def ticket_row(self, channel_id):
        with connect() as db:
            return db.execute("SELECT id,guild_id,user_id FROM tickets WHERE channel_id=? AND status='open'", (channel_id,)).fetchone()

    @commands.hybrid_command(name="ticketclaim", description="Claim the current ticket.")
    @commands.has_permissions(manage_channels=True)
    async def ticketclaim(self, ctx):
        row = self.ticket_row(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This channel is not an open LightCore ticket.")
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row['id'],))
            db.execute("UPDATE ticket_meta SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (ctx.author.id, row['id']))
        await ctx.send(f"🎫 Ticket **#{row['id']}** claimed by {ctx.author.mention}.")

    @commands.hybrid_command(name="ticketpriority", description="Set the current ticket priority.")
    @commands.has_permissions(manage_channels=True)
    async def ticketpriority(self, ctx, priority: str):
        priority = priority.lower()
        if priority not in {"low", "normal", "high", "urgent"}:
            return await ctx.send("Priority must be `low`, `normal`, `high`, or `urgent`.")
        row = self.ticket_row(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This channel is not an open ticket.")
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row['id'],))
            db.execute("UPDATE ticket_meta SET priority=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (priority, row['id']))
        await ctx.send(f"🏷️ Ticket priority set to **{priority}**.")

    @commands.hybrid_command(name="ticketautoclose", description="Set automatic ticket inactivity closing in minutes; 0 disables it.")
    @commands.has_permissions(manage_channels=True)
    async def ticketautoclose(self, ctx, minutes: int):
        row = self.ticket_row(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This channel is not an open ticket.")
        minutes = max(0, min(minutes, 10080))
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (row['id'],))
            db.execute("UPDATE ticket_meta SET auto_close_minutes=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (minutes, row['id']))
        await ctx.send("♻️ Auto-close disabled." if minutes == 0 else f"♻️ Auto-close set to **{minutes} minutes** of inactivity.")

    @tasks.loop(minutes=5)
    async def ticket_watchdog(self):
        with connect() as db:
            rows = db.execute("SELECT t.channel_id,m.auto_close_minutes,m.last_activity FROM tickets t JOIN ticket_meta m ON m.ticket_id=t.id WHERE t.status='open' AND m.auto_close_minutes>0").fetchall()
        now = __import__("datetime").datetime.utcnow()
        for row in rows:
            try:
                last = __import__("datetime").datetime.fromisoformat(row["last_activity"])
                if (now - last).total_seconds() < row["auto_close_minutes"] * 60:
                    continue
                channel = self.bot.get_channel(row["channel_id"])
                if channel:
                    await channel.send("🔒 Ticket auto-closed after the configured inactivity period.")
                    await channel.edit(name=f"closed-{channel.name[:80]}")
                with connect() as db:
                    db.execute("UPDATE tickets SET status='closed',closed_at=CURRENT_TIMESTAMP WHERE channel_id=?", (row["channel_id"],))
            except Exception:
                log.exception("Ticket watchdog failed for channel %s", row["channel_id"])

    @ticket_watchdog.before_loop
    async def before_ticket_watchdog(self):
        await self.bot.wait_until_ready()

    # ---------- Giveaways ----------
    @commands.hybrid_command(name="giveawayreroll", description="Reroll an ended giveaway by message ID.")
    @commands.has_permissions(manage_guild=True)
    async def giveawayreroll(self, ctx, message_id: int):
        with connect() as db:
            giveaway = db.execute("SELECT * FROM giveaways WHERE guild_id=? AND message_id=? AND status='ended'", (ctx.guild.id, message_id)).fetchone()
            if not giveaway:
                return await ctx.send("❌ That ended giveaway was not found in this server.")
            entries = db.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (giveaway['id'],)).fetchall()
        candidates = [self.bot.get_user(r['user_id']) or await self.bot.fetch_user(r['user_id']) for r in entries]
        candidates = [u for u in candidates if u and not u.bot]
        if not candidates:
            return await ctx.send("❌ There are no eligible entries to reroll.")
        winner = random.choice(candidates)
        with connect() as db:
            db.execute("UPDATE giveaways SET winner_id=? WHERE id=?", (winner.id, giveaway['id']))
        await ctx.send(f"🎉 Rerolled **{giveaway['prize']}** — new winner: {winner.mention}")

    @commands.hybrid_command(name="giveawaybonus", description="Grant a giveaway entry bonus to a role.")
    @commands.has_permissions(manage_guild=True)
    async def giveawaybonus(self, ctx, message_id: int, role: discord.Role, multiplier: int = 2):
        multiplier = max(1, min(multiplier, 10))
        with connect() as db:
            giveaway = db.execute("SELECT id FROM giveaways WHERE guild_id=? AND message_id=? AND status='active'", (ctx.guild.id, message_id)).fetchone()
            if not giveaway:
                return await ctx.send("❌ Active giveaway not found in this server.")
            db.execute("INSERT OR REPLACE INTO giveaway_bonus_roles(giveaway_id,role_id,multiplier) VALUES(?,?,?)", (giveaway['id'], role.id, multiplier))
        await ctx.send(f"🎁 Members with {role.mention} now receive **{multiplier}×** giveaway weight when entries are processed.")

    # ---------- Leveling ----------
    @commands.hybrid_command(name="levelroles", description="Show configured level milestone roles.")
    async def levelroles(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT level,role_id FROM level_rewards WHERE guild_id=? ORDER BY level", (ctx.guild.id,)).fetchall()
        if not rows:
            return await ctx.send("⭐ No milestone roles are configured yet. Use the level configuration commands.")
        await ctx.send("⭐ " + "\n".join(f"Level **{r['level']}** → <@&{r['role_id']}>" for r in rows))

    @commands.hybrid_command(name="xpboost", description="Apply a temporary 2× XP booster to a member.")
    @commands.has_permissions(manage_guild=True)
    async def xpboost(self, ctx, member: discord.Member, minutes: int = 60):
        minutes = max(5, min(minutes, 10080))
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO xp_boosters(guild_id,user_id,multiplier,expires_at) VALUES(?,?,?,?,?)", (ctx.guild.id, member.id, 2.0, __import__("datetime").datetime.utcnow() + timedelta(minutes=minutes)))
        await ctx.send(f"🚀 {member.mention} now has **2× XP** for {minutes} minutes.")

    @commands.hybrid_command(name="lbpage", description="Show a paginated level leaderboard page.")
    async def lbpage(self, ctx, page: int = 1):
        page = max(1, page)
        offset = (page - 1) * 10
        with connect() as db:
            rows = db.execute("SELECT user_id,level,xp FROM xp WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10 OFFSET ?", (ctx.guild.id, offset)).fetchall()
        if not rows:
            return await ctx.send("No users are on that leaderboard page.")
        text = "\n".join(f"**{offset+i}.** <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1))
        await ctx.send(embed=discord.Embed(title=f"⭐ Level Leaderboard • Page {page}", description=text, color=discord.Color.blurple()))

    # ---------- General / operations ----------
    @commands.hybrid_command(name="uptime", description="Show LightCore uptime.")
    async def uptime(self, ctx):
        seconds = int(__import__("time").monotonic() - self.started_at)
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        await ctx.send(f"⏱️ Uptime: **{days}d {hours}h {minutes}m {seconds}s**")

    @commands.hybrid_command(name="stats", description="Show bot and server statistics.")
    async def stats(self, ctx):
        await ctx.send(embed=discord.Embed(title="📊 LightCore Stats", description=f"Servers: **{len(self.bot.guilds)}**\nMembers cached: **{len(self.bot.users)}**\nLatency: **{round(self.bot.latency*1000)}ms**\nThis server members: **{ctx.guild.member_count}**", color=discord.Color.blurple()))

    @commands.hybrid_command(name="invites", description="Show tracked invite usage for this server.")
    @commands.has_permissions(manage_guild=True)
    async def invites(self, ctx):
        rows = []
        try:
            current = await ctx.guild.invites()
            rows = sorted(current, key=lambda x: x.uses or 0, reverse=True)[:15]
        except discord.Forbidden:
            return await ctx.send("❌ I need **Manage Server** to read invite usage.")
        if not rows:
            return await ctx.send("No invites could be read.")
        await ctx.send("🔗 " + "\n".join(f"`{i.code}` — {i.uses or 0} uses — {i.inviter.mention if i.inviter else 'unknown'}" for i in rows))

    @commands.hybrid_command(name="serverbackup", description="Export this server's LightCore configuration/data as JSON.")
    @commands.has_permissions(manage_guild=True)
    async def serverbackup(self, ctx):
        gid = ctx.guild.id
        with connect() as db:
            data = {}
            for table in ("guild_settings", "warnings", "moderation_logs", "xp", "level_rewards", "balances", "shop_items", "tickets", "ticket_transcripts", "giveaways", "giveaway_entries", "member_events", "applications", "application_submissions", "temp_voice_channels", "pets", "reward_claims", "xp_boosters", "ticket_meta", "giveaway_bonus_roles"):
                rows = db.execute(f"SELECT * FROM {table} WHERE guild_id=?", (gid,)).fetchall()
                data[table] = [dict(row) for row in rows]
        payload = json.dumps({"version": 1, "guild_id": gid, "guild_name": ctx.guild.name, "data": data}, default=str, indent=2).encode()
        await ctx.send("📦 LightCore server backup created.", file=discord.File(io.BytesIO(payload), filename=f"lightcore-{gid}-backup.json"))

    @commands.hybrid_command(name="serverrestore", description="Restore LightCore guild-scoped data from a backup JSON file.")
    @commands.has_permissions(manage_guild=True)
    async def serverrestore(self, ctx, backup: discord.Attachment):
        if not backup.filename.lower().endswith(".json"):
            return await ctx.send("❌ Please attach a LightCore `.json` backup.")
        try:
            payload = json.loads((await backup.read()).decode())
            if int(payload.get("guild_id")) != ctx.guild.id:
                return await ctx.send("❌ That backup belongs to a different server. Cross-server restores are blocked.")
            data = payload.get("data", {})
            allowed = {"guild_settings", "warnings", "moderation_logs", "xp", "level_rewards", "balances", "shop_items", "tickets", "ticket_transcripts", "giveaways", "giveaway_entries", "member_events", "applications", "application_submissions", "temp_voice_channels", "pets", "reward_claims", "xp_boosters", "ticket_meta", "giveaway_bonus_roles"}
            with connect() as db:
                for table, rows in data.items():
                    if table not in allowed or not isinstance(rows, list):
                        continue
                    for row in rows:
                        if "guild_id" in row and int(row["guild_id"]) != ctx.guild.id:
                            continue
                    # Restores are intentionally limited to this guild and use INSERT OR REPLACE.
                    cols = None
                    for row in rows:
                        if not isinstance(row, dict) or not row:
                            continue
                        cols = list(row)
                        values = [row[c] for c in cols]
                        placeholders = ",".join("?" for _ in cols)
                        db.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})", values)
            await ctx.send("♻️ Guild-scoped LightCore data restored. No data from another guild was accepted.")
        except Exception as exc:
            log.exception("Server restore failed")
            await ctx.send(f"❌ Restore failed safely: `{type(exc).__name__}`. The backup was not accepted as a cross-server import.")

    @commands.hybrid_command(name="invite", description="Show the public LightCore invite link.")
    async def invite(self, ctx):
        url = os.getenv("INVITE_URL", "")
        if not url:
            return await ctx.send("🔗 The public invite URL is not configured yet. Set `INVITE_URL` on the host.")
        await ctx.send(f"🚀 Invite LightCore: {url}")


async def setup(bot):
    await bot.add_cog(Advanced(bot))
