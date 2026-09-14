import time
import discord
from discord.ext import commands
BOT_VERSION="1.0.0"
class Utility(commands.Cog):
    def __init__(self,bot):self.bot=bot
    async def cog_load(self):
        music=self.bot.get_cog("Music")
        if music:
            async def fresh_panel(ctx):
                try:
                    msg=await ctx.send(embed=music._embed(ctx.guild.id),view=MusicPanelPlus(music,ctx.guild.id));music.panel_messages[ctx.guild.id]=msg
                except discord.HTTPException:pass
            music._send_or_update_panel=fresh_panel
            old=next((c for c in self.bot.walk_commands() if c.qualified_name=="nowplaying"),None)
            if old:
                async def nowplaying(cog,ctx):
                    player=ctx.voice_client
                    if not getattr(player,"current",None):return await ctx.send("❌ Nothing is currently playing.")
                    await fresh_panel(ctx)
                old.callback=nowplaying
    @commands.hybrid_command(name="resume",description="Resume paused music.")
    async def resume(self,ctx):
        player=ctx.voice_client
        if not player or not getattr(player,"current",None):return await ctx.send("❌ Nothing is currently playing.")
        await player.pause(False);await ctx.send("▶️ Playback resumed.")
    @commands.hybrid_command(name="uptime",description="Show how long LightCore has been online.")
    async def uptime(self,ctx):
        seconds=max(0,int(time.monotonic()-getattr(self.bot,"started_at",time.monotonic())));days,rem=divmod(seconds,86400);hours,rem=divmod(rem,3600);minutes,seconds=divmod(rem,60);parts=[]
        if days:parts.append(f"{days}d")
        if hours or days:parts.append(f"{hours}h")
        if minutes or hours or days:parts.append(f"{minutes}m")
        parts.append(f"{seconds:02d}s");e=discord.Embed(title="⏱️ LightCore • Uptime",description=f"LightCore has been online for **{' '.join(parts)}**.",color=discord.Color.blurple());e.set_footer(text="LightCore • Utility");await ctx.send(embed=e)
    @commands.hybrid_command(name="botinfo",description="Show LightCore version, library, server and shard information.")
    async def botinfo(self,ctx):
        users=sum(g.member_count or 0 for g in self.bot.guilds);shards=self.bot.shard_count or 1;sid=ctx.guild.shard_id if ctx.guild else 0;e=discord.Embed(title="🤖 LightCore • Bot Info",color=discord.Color.blurple());e.add_field(name="Bot Version",value=BOT_VERSION);e.add_field(name="discord.py",value=discord.__version__);e.add_field(name="Servers",value=f"{len(self.bot.guilds):,}");e.add_field(name="Users",value=f"{users:,} cached memberships");e.add_field(name="Shards",value=str(shards));e.add_field(name="Current Shard",value=str(sid));await ctx.send(embed=e)
    @commands.hybrid_command(name="avatar",description="Show a user's full avatar.")
    async def avatar(self,ctx,member:discord.Member=None):member=member or ctx.author;e=discord.Embed(title=f"🖼️ {member.display_name}'s Avatar",color=discord.Color.blurple());e.set_image(url=member.display_avatar.url);await ctx.send(embed=e)
    @commands.hybrid_command(name="banner",description="Show a user's profile banner if set.")
    async def banner(self,ctx,member:discord.Member=None):
        member=member or ctx.author;user=await self.bot.fetch_user(member.id)
        if not user.banner:return await ctx.send(f"❌ **{member.display_name}** does not have a profile banner set.")
        e=discord.Embed(title=f"🎨 {member.display_name}'s Banner",color=discord.Color.blurple());e.set_image(url=user.banner.url);await ctx.send(embed=e)
    @commands.hybrid_command(name="servericon",description="Show the current server icon full-size.")
    async def servericon(self,ctx):
        if not ctx.guild or not ctx.guild.icon:return await ctx.send("❌ This server does not have an icon set.")
        e=discord.Embed(title=f"🖼️ {ctx.guild.name} • Server Icon",color=discord.Color.blurple());e.set_image(url=ctx.guild.icon.url);await ctx.send(embed=e)
    @commands.hybrid_command(name="roleinfo",description="Show server role details.")
    async def roleinfo(self,ctx,role:discord.Role):
        members=sum(role in m.roles for m in ctx.guild.members);perms=[n.replace("_"," ").title() for n,v in role.permissions if v];e=discord.Embed(title=f"🏷️ Role Info • {role.name}",color=role.color if role.color.value else discord.Color.blurple());e.add_field(name="Color",value=str(role.color));e.add_field(name="Position",value=str(role.position));e.add_field(name="Members",value=f"{members:,}");e.add_field(name="Permissions",value=", ".join(perms[:20]) or "None",inline=False);await ctx.send(embed=e)
    @commands.hybrid_command(name="channelinfo",description="Show channel details.")
    async def channelinfo(self,ctx,channel:discord.abc.GuildChannel=None):
        channel=channel or ctx.channel;typ=str(channel.type).replace("ChannelType.","").replace("_"," ").title();topic=getattr(channel,"topic",None) or "None";slow=getattr(channel,"slowmode_delay",None);e=discord.Embed(title=f"📺 Channel Info • #{channel.name}",color=discord.Color.blurple());e.add_field(name="Type",value=typ);e.add_field(name="Created",value=discord.utils.format_dt(channel.created_at,"F"));e.add_field(name="Slowmode",value=f"{slow}s" if slow is not None else "N/A");e.add_field(name="Topic",value=topic[:1024],inline=False);await ctx.send(embed=e)
    @commands.hybrid_command(name="firstmessage",description="Find and link the first message in a channel.")
    async def firstmessage(self,ctx,channel:discord.TextChannel=None):
        channel=channel or ctx.channel
        try:
            async for message in channel.history(limit=1,oldest_first=True):return await ctx.send(f"📜 [Jump to the first message in #{channel.name}]({message.jump_url})")
        except discord.Forbidden:return await ctx.send("❌ I need Read Message History to inspect that channel.")
        await ctx.send("❌ No messages were found.")
class MusicPanelPlus(discord.ui.View):
    def __init__(self,cog,guild_id):
        super().__init__(timeout=None);self.cog=cog;self.guild_id=guild_id
        items=[("Pause","⏸️","pause",discord.ButtonStyle.primary,0),("Skip","⏭️","skip",discord.ButtonStyle.primary,0),("Stop","⏹️","stop",discord.ButtonStyle.danger,0),("Shuffle","🔀","shuffle",discord.ButtonStyle.secondary,0),("Vol -","🔉","voldown",discord.ButtonStyle.secondary,1),("Vol +","🔊","volup",discord.ButtonStyle.secondary,1),("Queue","📜","queue",discord.ButtonStyle.secondary,1),("Loop","🔁","loop",discord.ButtonStyle.primary,1)]
        for label,emoji,action,style,row in items:
            b=discord.ui.Button(label=label,emoji=emoji,style=style,row=row);b.callback=self.cb(action);self.add_item(b)
    def cb(self,action):
        async def callback(interaction):
            player=interaction.guild.voice_client if interaction.guild else None
            if not player:return await interaction.response.send_message("❌ Music is not connected.",ephemeral=True)
            if action=="pause":await player.pause(not player.paused)
            elif action=="skip":await player.skip()
            elif action=="stop":self.cog.queues[self.guild_id].clear();await player.stop()
            elif action=="shuffle":import random;random.shuffle(self.cog.queues[self.guild_id])
            elif action=="voldown":await player.set_volume(max(0,int(getattr(player,"volume",100))-10))
            elif action=="volup":await player.set_volume(min(100,int(getattr(player,"volume",100))+10))
            elif action=="loop":m=["off","track","queue"];self.cog.loop_modes[self.guild_id]=m[(m.index(self.cog.loop_modes[self.guild_id])+1)%3]
            elif action=="queue":return await interaction.response.send_message("📜 Queue: "+("\n".join(f"{i}. {t.title}" for i,t in enumerate(self.cog.queues[self.guild_id],1)) or "Empty"),ephemeral=True)
            await interaction.response.edit_message(embed=self.cog._embed(self.guild_id),view=MusicPanelPlus(self.cog,self.guild_id))
        return callback
async def setup(bot):await bot.add_cog(Utility(bot))
