import discord
from discord.ext import commands
from database import connect, get_setting, set_setting

CATEGORIES={"moderation":"mod-logs","messages":"message-logs","members":"member-logs","voice":"voice-logs","server":"server-logs"}
class Logging(commands.Cog):
    def __init__(self,bot):self.bot=bot
    async def cog_load(self):
        with connect() as db:db.execute("CREATE TABLE IF NOT EXISTS log_config (guild_id INTEGER NOT NULL, category TEXT NOT NULL, channel_id INTEGER, enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(guild_id,category))")
    async def _channels(self,guild):
        with connect() as db:rows=db.execute("SELECT category,channel_id,enabled FROM log_config WHERE guild_id=?",(guild.id,)).fetchall()
        return {r["category"]:r for r in rows}
    async def send_log(self,guild,title,description,event_type=None,actor_id=None,channel_id=None,target_id=None,category="server"):
        if event_type:
            with connect() as db:db.execute("INSERT INTO event_logs(guild_id,event_type,actor_id,channel_id,target_id,details) VALUES(?,?,?,?,?,?)",(guild.id,event_type,actor_id,channel_id,target_id,description[:4000]))
        rows=await self._channels(guild);row=rows.get(category) or rows.get("server")
        if not row or not row["enabled"] or not row["channel_id"]:return
        channel=guild.get_channel(row["channel_id"])
        if channel:
            try:await channel.send(embed=discord.Embed(title=title,description=description[:4000],color=discord.Color.blurple()))
            except discord.HTTPException:pass
    def _overwrites(self,guild):
        overwrites={guild.default_role:discord.PermissionOverwrite(view_channel=False)}
        if guild.me:overwrites[guild.me]=discord.PermissionOverwrite(view_channel=True,send_messages=True,embed_links=True,read_message_history=True)
        for role in guild.roles:
            if role.is_default():continue
            if role.permissions.manage_guild or role.permissions.administrator:overwrites[role]=discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)
        return overwrites
    @commands.hybrid_command(name="logsetup",description="Automatically create the complete private logging system.")
    @commands.has_permissions(manage_guild=True)
    async def logsetup(self,ctx):
        guild=ctx.guild;category=discord.utils.get(guild.categories,name="📋 Logs")
        if category is None:category=await guild.create_category("📋 Logs",overwrites=self._overwrites(guild),reason="LightCore automatic log setup")
        with connect() as db:db.execute("CREATE TABLE IF NOT EXISTS log_config (guild_id INTEGER NOT NULL, category TEXT NOT NULL, channel_id INTEGER, enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(guild_id,category))")
        created=[]
        for key,name in CATEGORIES.items():
            channel=discord.utils.get(category.text_channels,name=name)
            if channel is None:channel=await guild.create_text_channel(name,category=category,overwrites=self._overwrites(guild),reason="LightCore automatic log setup")
            with connect() as db:db.execute("INSERT INTO log_config(guild_id,category,channel_id,enabled) VALUES(?,?,?,1) ON CONFLICT(guild_id,category) DO UPDATE SET channel_id=excluded.channel_id,enabled=1",(guild.id,key,channel.id))
            set_setting(guild.id,"log_channel",channel.id) if key=="server" else None;created.append(channel.mention)
        await ctx.send("✅ Logging auto-setup complete. Created/updated: " + ", ".join(created))
    @commands.hybrid_command(name="logconfig",description="Enable, disable, or redirect one logging category.")
    @commands.has_permissions(manage_guild=True)
    async def logconfig(self,ctx,category:str,channel:discord.TextChannel=None):
        category=category.lower()
        if category not in CATEGORIES:return await ctx.send("❌ Category must be: `moderation`, `messages`, `members`, `voice`, or `server`.")
        with connect() as db:db.execute("CREATE TABLE IF NOT EXISTS log_config (guild_id INTEGER NOT NULL, category TEXT NOT NULL, channel_id INTEGER, enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(guild_id,category))")
        with connect() as db:
            row=db.execute("SELECT channel_id,enabled FROM log_config WHERE guild_id=? AND category=?",(ctx.guild.id,category)).fetchone()
            if channel:db.execute("INSERT INTO log_config(guild_id,category,channel_id,enabled) VALUES(?,?,?,1) ON CONFLICT(guild_id,category) DO UPDATE SET channel_id=excluded.channel_id,enabled=1",(ctx.guild.id,category,channel.id));return await ctx.send(f"✅ `{category}` logs now go to {channel.mention}.")
            enabled=0 if row and row["enabled"] else 1;db.execute("INSERT INTO log_config(guild_id,category,channel_id,enabled) VALUES(?,?,?,?) ON CONFLICT(guild_id,category) DO UPDATE SET enabled=excluded.enabled",(ctx.guild.id,category,row["channel_id"] if row else None,enabled))
        await ctx.send(f"✅ `{category}` logging is now **{'enabled' if enabled else 'disabled'}**.")
    @commands.hybrid_command(name="setlog",description="Set the server logging channel.")
    @commands.has_permissions(manage_guild=True)
    async def setlog(self,ctx,channel:discord.TextChannel):
        set_setting(ctx.guild.id,"log_channel",channel.id);await ctx.send(f"Logging channel set to {channel.mention}.")
    @commands.Cog.listener()
    async def on_message_delete(self,message):
        if message.guild and not message.author.bot:await self.send_log(message.guild,"Message deleted",f"**Author:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** {message.content[:1500] or '[empty]'}","message_delete",message.author.id,message.channel.id,category="messages")
    @commands.Cog.listener()
    async def on_message_edit(self,before,after):
        if before.guild and not before.author.bot and before.content!=after.content:await self.send_log(before.guild,"Message edited",f"**Author:** {before.author.mention}\n**Channel:** {before.channel.mention}\n**Before:** {before.content[:700]}\n**After:** {after.content[:700]}","message_edit",before.author.id,before.channel.id,category="messages")
    @commands.Cog.listener()
    async def on_member_join(self,member):await self.send_log(member.guild,"Member joined",f"{member.mention} joined the server.","member_join",member.id,target_id=member.id,category="members")
    @commands.Cog.listener()
    async def on_member_remove(self,member):await self.send_log(member.guild,"Member left",f"**User:** {member} ({member.id})","member_leave",member.id,target_id=member.id,category="members")
    @commands.Cog.listener()
    async def on_voice_state_update(self,member,before,after):
        if member.bot or before.channel==after.channel:return
        await self.send_log(member.guild,"Voice state changed",f"**User:** {member.mention}\n**Before:** {before.channel.mention if before.channel else 'None'}\n**After:** {after.channel.mention if after.channel else 'None'}","voice_state",member.id, target_id=member.id,category="voice")
    @commands.Cog.listener()
    async def on_member_ban(self,guild,user):await self.send_log(guild,"Member banned",f"**User:** {user.mention if hasattr(user,'mention') else user}","member_ban",target_id=user.id,category="moderation")
    @commands.Cog.listener()
    async def on_member_unban(self,guild,user):await self.send_log(guild,"Member unbanned",f"**User:** {user}","member_unban",target_id=user.id,category="moderation")
    @commands.Cog.listener()
    async def on_guild_channel_create(self,channel):
        if channel.guild:await self.send_log(channel.guild,"Channel created",f"{channel.mention} was created.","channel_create",target_id=channel.id,category="server")
    @commands.Cog.listener()
    async def on_guild_channel_delete(self,channel):await self.send_log(channel.guild,"Channel deleted",f"**Channel:** #{channel.name}","channel_delete",target_id=channel.id,category="server")
async def setup(bot):await bot.add_cog(Logging(bot))
