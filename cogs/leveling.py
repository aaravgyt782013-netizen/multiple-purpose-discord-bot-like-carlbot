import io
import random
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from database import connect

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = set()

    def needed(self, level):
        return 100 + level * 50

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild or message.author.id in self.cooldowns:
            return
        self.cooldowns.add(message.author.id)
        try:
            with connect() as db:
                settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM guild_settings WHERE guild_id=? AND key LIKE 'level_%'", (message.guild.id,)).fetchall()}
                if settings.get("level_enabled", "1") == "0": return
                lo, hi = int(settings.get("level_xp_min", 8)), int(settings.get("level_xp_max", 15))
                row = db.execute("SELECT xp,level FROM xp WHERE guild_id=? AND user_id=?", (message.guild.id,message.author.id)).fetchone()
                xp, level = (row[0],row[1]) if row else (0,0)
                xp += random.randint(lo, hi); leveled = False
                while xp >= self.needed(level): xp -= self.needed(level); level += 1; leveled = True
                db.execute("INSERT OR REPLACE INTO xp(guild_id,user_id,xp,level) VALUES(?,?,?,?)", (message.guild.id,message.author.id,xp,level))
            if leveled:
                text = settings.get("level_message", "🎉 {user} reached **Level {level}**!").replace("{user}",message.author.mention).replace("{level}",str(level))
                await message.channel.send(text)
                role_id = settings.get(f"level_role_{level}")
                role = message.guild.get_role(int(role_id)) if role_id else None
                if role: await message.author.add_roles(role, reason="LightCore level reward")
        finally:
            self.cooldowns.discard(message.author.id)

    @commands.hybrid_command(name="rank")
    async def rank(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        with connect() as db:
            row = db.execute("SELECT xp,level FROM xp WHERE guild_id=? AND user_id=?", (ctx.guild.id,member.id)).fetchone()
            xp, level = (row[0],row[1]) if row else (0,0)
            position = db.execute("SELECT COUNT(*) FROM xp WHERE guild_id=? AND (level>? OR (level=? AND xp>?))", (ctx.guild.id,level,level,xp)).fetchone()[0] + 1
        card = await self.rank_card(member,xp,level,position)
        await ctx.send(file=discord.File(card, filename="lightcore-rank.png"))

    @commands.hybrid_command(name="leaderboard", aliases=["levels","lb"])
    async def leaderboard(self, ctx):
        with connect() as db:
            rows = db.execute("SELECT user_id,level,xp FROM xp WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10", (ctx.guild.id,)).fetchall()
        text = "\n".join(f"**{i}.** <@{r['user_id']}> — Level {r['level']} ({r['xp']} XP)" for i,r in enumerate(rows,1)) or "No XP data yet."
        await ctx.send(embed=discord.Embed(title="LightCore • XP Leaderboard",description=text,color=discord.Color.blurple()))

    @commands.hybrid_group(name="levelconfig", invoke_without_command=True)
    @commands.has_guild_permissions(manage_guild=True)
    async def levelconfig(self, ctx):
        await ctx.send("Use `.levelconfig rate`, `.levelconfig message`, `.levelconfig reward`, or `.levelconfig enable`.")

    @levelconfig.command(name="rate")
    async def rate(self, ctx, minimum:int=8, maximum:int=15):
        with connect() as db:
            for key,value in (("level_xp_min",max(1,minimum)),("level_xp_max",max(minimum,maximum))): db.execute("INSERT OR REPLACE INTO guild_settings(guild_id,key,value) VALUES(?,?,?)",(ctx.guild.id,key,str(value)))
        await ctx.send("✅ XP rate updated.")

    @levelconfig.command(name="message")
    async def message(self, ctx, *, text):
        with connect() as db: db.execute("INSERT OR REPLACE INTO guild_settings(guild_id,key,value) VALUES(?,?,?)",(ctx.guild.id,"level_message",text))
        await ctx.send("✅ Level-up message saved. Placeholders: `{user}`, `{level}`.")

    @levelconfig.command(name="reward")
    async def reward(self, ctx, level:int, role:discord.Role):
        with connect() as db: db.execute("INSERT OR REPLACE INTO guild_settings(guild_id,key,value) VALUES(?,?,?)",(ctx.guild.id,f"level_role_{level}",str(role.id)))
        await ctx.send(f"✅ Level {level} reward set to {role.mention}.")

    @levelconfig.command(name="enable")
    async def enable(self, ctx, enabled:bool=True):
        with connect() as db: db.execute("INSERT OR REPLACE INTO guild_settings(guild_id,key,value) VALUES(?,?,?)",(ctx.guild.id,"level_enabled","1" if enabled else "0"))
        await ctx.send(f"✅ Leveling {'enabled' if enabled else 'disabled'}.")

    async def rank_card(self, member, xp, level, position):
        image = Image.new("RGB",(900,280),(18,18,24)); draw=ImageDraw.Draw(image)
        avatar=Image.open(io.BytesIO(await member.display_avatar.read())).convert("RGB").resize((150,150))
        mask=Image.new("L",(150,150),0); ImageDraw.Draw(mask).ellipse((0,0,150,150),fill=255); image.paste(avatar,(50,55),mask)
        font=ImageFont.load_default(size=30); small=ImageFont.load_default(size=20)
        draw.text((240,55),member.display_name[:24],fill="white",font=font); draw.text((240,100),f"LEVEL {level}  •  RANK #{position}",fill=(180,180,195),font=small)
        needed=self.needed(level); draw.text((240,140),f"XP  {xp:,} / {needed:,}",fill="white",font=small)
        draw.rounded_rectangle((240,185,840,212),radius=10,fill=(50,50,60)); draw.rounded_rectangle((240,185,240+int(600*min(1,xp/needed)),212),radius=10,fill=(115,125,255))
        draw.text((50,235),"LIGHTCORE • LEVELING",fill=(160,160,175),font=small)
        out=io.BytesIO(); image.save(out,"PNG"); out.seek(0); return out

async def setup(bot):
    await bot.add_cog(Leveling(bot))
