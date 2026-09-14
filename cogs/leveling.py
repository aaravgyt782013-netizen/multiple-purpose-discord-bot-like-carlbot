import io
import random
import time
from datetime import datetime

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from database import connect, get_setting, set_setting


class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    def needed(self, level):
        return 100 + level * 50

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or not get_setting(message.guild.id, "level_enabled"):
            return
        guild_id, user_id = message.guild.id, message.author.id
        cooldown = max(0, int(get_setting(guild_id, "level_cooldown") or 60))
        key = (guild_id, user_id); now = time.monotonic()
        if now - self.cooldowns.get(key, 0) < cooldown:
            return
        self.cooldowns[key] = now
        lo = max(1, int(get_setting(guild_id, "level_xp_min") or 15)); hi = max(lo, int(get_setting(guild_id, "level_xp_max") or 25))
        with connect() as db:
            booster = db.execute("SELECT multiplier,expires_at FROM xp_boosters WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
            multiplier = 1.0
            if booster:
                try:
                    if datetime.fromisoformat(booster["expires_at"]) > datetime.utcnow():
                        multiplier = float(booster["multiplier"])
                    else:
                        db.execute("DELETE FROM xp_boosters WHERE guild_id=? AND user_id=?", (guild_id, user_id))
                except ValueError:
                    db.execute("DELETE FROM xp_boosters WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            row = db.execute("SELECT xp,level FROM xp WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
            xp, level = (row["xp"], row["level"]) if row else (0, 0)
            xp += int(random.randint(lo, hi) * multiplier)
            leveled = False
            while xp >= self.needed(level):
                xp -= self.needed(level); level += 1; leveled = True
            db.execute("INSERT OR REPLACE INTO xp(guild_id,user_id,xp,level) VALUES(?,?,?,?)", (guild_id, user_id, xp, level))
            reward = db.execute("SELECT role_id FROM level_rewards WHERE guild_id=? AND level=?", (guild_id, level)).fetchone() if leveled else None
        if leveled:
            template = get_setting(guild_id, "level_message") or "🎉 {user} reached **Level {level}**!"
            await message.channel.send(template.replace("{user}", message.author.mention).replace("{level}", str(level)))
            if reward:
                role = message.guild.get_role(reward["role_id"])
                if role:
                    try:
                        await message.author.add_roles(role, reason="LightCore level milestone")
                    except discord.HTTPException:
                        pass

    @commands.hybrid_command(name="rank", description="Show a visual LightCore rank card.")
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        with connect() as db:
            row = db.execute("SELECT xp,level FROM xp WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
            xp, level = (row["xp"], row["level"]) if row else (0, 0)
            position = db.execute("SELECT COUNT(*) FROM xp WHERE guild_id=? AND (level>? OR (level=? AND xp>?))", (ctx.guild.id, level, level, xp)).fetchone()[0] + 1
        await ctx.send(file=discord.File(await self.rank_card(member, xp, level, position), filename="lightcore-rank.png"))

    @commands.hybrid_command(name="leaderboard", aliases=["levels", "lb"], description="Show the server XP leaderboard.")
    async def leaderboard(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT user_id,level,xp FROM xp WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"**{i}.** <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1)) or "No XP data yet."
        await ctx.send(embed=discord.Embed(title="LightCore • XP Leaderboard", description=text, color=discord.Color.blurple()))

    @commands.hybrid_command(name="leaderboardpage", description="Show a selected XP leaderboard page.")
    async def leaderboardpage(self, ctx, page: int = 1):
        page = max(1, page); offset = (page - 1) * 10
        with connect() as db:
            rows = db.execute("SELECT user_id,level,xp FROM xp WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10 OFFSET ?", (ctx.guild.id, offset)).fetchall()
        if not rows: return await ctx.send("No users on that leaderboard page.")
        await ctx.send(embed=discord.Embed(title=f"⭐ Leaderboard • Page {page}", description="\n".join(f"**{offset+i}.** <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i, r in enumerate(rows, 1)), color=discord.Color.blurple()))

    @commands.hybrid_group(name="levelconfig", invoke_without_command=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def levelconfig(self, ctx):
        await ctx.send("Use `.levelconfig rate`, `cooldown`, `message`, `reward`, or `enable`.")

    @levelconfig.command(name="rate")
    async def rate(self, ctx, minimum: int = 8, maximum: int = 15):
        set_setting(ctx.guild.id, "level_xp_min", max(1, minimum)); set_setting(ctx.guild.id, "level_xp_max", max(max(1, minimum), maximum)); await ctx.send("✅ XP rate updated.")

    @levelconfig.command(name="cooldown")
    async def cooldown(self, ctx, seconds: commands.Range[int, 0, 3600] = 60):
        set_setting(ctx.guild.id, "level_cooldown", seconds); await ctx.send(f"✅ XP cooldown set to **{seconds}s**.")

    @levelconfig.command(name="message")
    async def message(self, ctx, *, text):
        set_setting(ctx.guild.id, "level_message", text); await ctx.send("✅ Level-up message saved. Placeholders: `{user}`, `{level}`.")

    @levelconfig.command(name="reward")
    async def reward(self, ctx, level: commands.Range[int, 1, 1000], role: discord.Role):
        with connect() as db: db.execute("INSERT OR REPLACE INTO level_rewards(guild_id,level,role_id) VALUES(?,?,?)", (ctx.guild.id, level, role.id))
        await ctx.send(f"✅ Level {level} reward set to {role.mention}.")

    @levelconfig.command(name="enable")
    async def enable(self, ctx, enabled: bool = True):
        set_setting(ctx.guild.id, "level_enabled", int(enabled)); await ctx.send(f"✅ Leveling {'enabled' if enabled else 'disabled'}.")

    async def rank_card(self, member, xp, level, position):
        image = Image.new("RGB", (900, 280), (18, 18, 24)); draw = ImageDraw.Draw(image)
        avatar = Image.open(io.BytesIO(await member.display_avatar.read())).convert("RGB").resize((150, 150)); mask = Image.new("L", (150, 150), 0); ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255); image.paste(avatar, (50, 55), mask)
        font = ImageFont.load_default(size=30); small = ImageFont.load_default(size=20); draw.text((240,55), member.display_name[:24], fill="white", font=font); draw.text((240,100), f"LEVEL {level} • RANK #{position}", fill=(180,180,195), font=small)
        needed = self.needed(level); draw.text((240,140), f"XP {xp:,} / {needed:,}", fill="white", font=small); draw.rounded_rectangle((240,185,840,212), radius=10, fill=(50,50,60)); draw.rounded_rectangle((240,185,240+int(600*min(1,xp/needed)),212), radius=10, fill=(115,125,255)); draw.text((50,235), "LIGHTCORE • LEVELING", fill=(160,160,175), font=small)
        out = io.BytesIO(); image.save(out, "PNG"); out.seek(0); return out


async def setup(bot):
    await bot.add_cog(Leveling(bot))
