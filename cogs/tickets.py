import json
import re
import discord
from discord.ext import commands
from database import connect, get_setting, set_setting

DEFAULT_TICKET_CATEGORIES=[{"name":"General Support","emoji":"🎫","role_id":None,"category_id":None},{"name":"Report a User","emoji":"🚨","role_id":None,"category_id":None},{"name":"Billing","emoji":"💳","role_id":None,"category_id":None}]

def default_config(): return {"title":"LightCore Support","description":"Choose a support category below to open a private ticket.","color":0x5865F2,"panel_channel_id":None,"published_message_id":None,"claim_required":False,"categories":[dict(x) for x in DEFAULT_TICKET_CATEGORIES]}
def load_config(guild_id):
    raw=get_setting(guild_id,"ticket_config")
    if not raw:return default_config()
    try:
        cfg=default_config(); saved=json.loads(raw); cfg.update(saved if isinstance(saved,dict) else {})
        cats=cfg.get("categories") if isinstance(cfg.get("categories"),list) else DEFAULT_TICKET_CATEGORIES
        clean=[]
        for x in cats[:25]:
            if isinstance(x,dict): clean.append({"name":str(x.get("name") or "General Support")[:80],"emoji":str(x.get("emoji") or "🎫")[:8],"role_id":int(x["role_id"]) if x.get("role_id") else None,"category_id":int(x["category_id"]) if x.get("category_id") else None})
        cfg["categories"]=clean; return cfg
    except (TypeError,ValueError,json.JSONDecodeError): return default_config()
def save_config(guild_id,cfg): set_setting(guild_id,"ticket_config",json.dumps(cfg,separators=(",",":")))
def color_value(value):
    value=value.strip().replace("#","")
    if len(value)!=6: raise ValueError("Color must be a 6-digit hex value such as #5865F2.")
    try:return int(value,16)
    except ValueError as exc:raise ValueError("Color must be a valid 6-digit hexadecimal value.") from exc
def clean_channel_name(value,fallback="support"):
    value=re.sub(r"[^a-z0-9-]+","-",value.lower()).strip("-")[:30];return value or fallback

class TicketClaimView(discord.ui.View):
    def __init__(self,guild_id,ticket_id,role_id):
        super().__init__(timeout=None);self.ticket_id=ticket_id;self.role_id=role_id
        b=discord.ui.Button(label="Claim Ticket",emoji="🙋",style=discord.ButtonStyle.primary,custom_id=f"lightcore:ticket:claim:{ticket_id}");b.callback=self.claim;self.add_item(b)
    async def claim(self,i):
        if not i.guild:return await i.response.send_message("This button can only be used in a server.",ephemeral=True)
        if self.role_id and not any(r.id==self.role_id for r in i.user.roles):return await i.response.send_message("❌ You need the configured support role to claim this ticket.",ephemeral=True)
        with connect() as db:
            row=db.execute("SELECT claimed_by FROM ticket_meta WHERE ticket_id=?",(self.ticket_id,)).fetchone();claimed=row["claimed_by"] if row else None
            if not row:db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)",(self.ticket_id,))
            if claimed:return await i.response.send_message(f"❌ Already claimed by <@{claimed}>.",ephemeral=True)
            db.execute("UPDATE ticket_meta SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?",(i.user.id,self.ticket_id))
        await i.response.edit_message(content=f"🙋 Ticket claimed by {i.user.mention}.",view=self)

class TicketPanelView(discord.ui.View):
    def __init__(self,cog,guild_id):
        super().__init__(timeout=None);self.cog=cog;self.guild_id=guild_id;cfg=load_config(guild_id)
        opts=[discord.SelectOption(label=x["name"][:100],value=str(i),emoji=x.get("emoji") or "🎫") for i,x in enumerate(cfg.get("categories",[])[:25])]
        if not opts:opts=[discord.SelectOption(label="No categories configured",value="none")]
        s=discord.ui.Select(placeholder="Choose a ticket category…",options=opts,custom_id=f"lightcore:ticket:categories:{guild_id}");s.callback=self.create_ticket;self.add_item(s)
        b=discord.ui.Button(label="Edit",emoji="✏️",style=discord.ButtonStyle.secondary,custom_id=f"lightcore:ticket:edit:{guild_id}",row=1);b.callback=self.edit_panel;self.add_item(b)
    async def edit_panel(self,i):
        if not i.user.guild_permissions.manage_channels:return await i.response.send_message("❌ You need Manage Channels to edit this panel.",ephemeral=True)
        e=TicketEditor(self.cog,self.guild_id);await i.response.send_message(embed=e.embed(),view=e,ephemeral=True);e.message=await i.original_response()
    async def create_ticket(self,i):
        value=i.data.get("values",["none"])[0]
        if value=="none":return await i.response.send_message("❌ No ticket categories are configured yet.",ephemeral=True)
        try:index=int(value)
        except ValueError:return await i.response.send_message("❌ Invalid ticket category.",ephemeral=True)
        cfg=load_config(i.guild.id)
        if index>=len(cfg["categories"]):return await i.response.send_message("❌ That category no longer exists.",ephemeral=True)
        item=cfg["categories"][index]
        with connect() as db:row=db.execute("SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status='open'",(i.guild.id,i.user.id)).fetchone()
        if row:
            existing=i.guild.get_channel(row["channel_id"])
            if existing:return await i.response.send_message(f"You already have an open ticket: {existing.mention}",ephemeral=True)
        parent=i.guild.get_channel(item.get("category_id")) if item.get("category_id") else None
        if parent and not isinstance(parent,discord.CategoryChannel):parent=None
        role=i.guild.get_role(item.get("role_id")) if item.get("role_id") else None
        overwrites={i.guild.default_role:discord.PermissionOverwrite(view_channel=False),i.user:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)}
        if role:overwrites[role]=discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True)
        channel=await i.guild.create_text_channel(f"{clean_channel_name(item['name'])}-{clean_channel_name(i.user.name,'user')[:20]}",category=parent,overwrites=overwrites,reason=f"LightCore ticket: {item['name']}")
        with connect() as db:
            cur=db.execute("INSERT INTO tickets(guild_id,channel_id,user_id,status) VALUES(?,?,?,'open')",(i.guild.id,channel.id,i.user.id));tid=cur.lastrowid;db.execute("INSERT OR REPLACE INTO ticket_meta(ticket_id,category) VALUES(?,?)",(tid,item["name"]))
        e=discord.Embed(title=f"🎫 {item['name']}",description=f"Welcome {i.user.mention}!\n{role.mention if role else 'Support team'}, a new ticket has been opened.",color=discord.Color(cfg["color"]));e.add_field(name="Ticket",value=f"`#{tid}`");e.add_field(name="Category",value=item["name"])
        await channel.send(embed=e,view=TicketClaimView(i.guild.id,tid,item.get("role_id")) if cfg.get("claim_required") else None);await i.response.send_message(f"🎫 Ticket created: {channel.mention}",ephemeral=True)

class TicketEditor(discord.ui.View):
    def __init__(self,cog,guild_id):super().__init__(timeout=600);self.cog=cog;self.guild_id=guild_id;self.message=None;self.selected_category=0;self.rebuild()
    def config(self):return load_config(self.guild_id)
    def embed(self):
        cfg=self.config();ch=self.cog.bot.get_channel(cfg.get("panel_channel_id")) if cfg.get("panel_channel_id") else None;lines=[]
        for n,x in enumerate(cfg.get("categories",[])[:25],1):
            role=f"<@&{x['role_id']}>" if x.get("role_id") else "No support role";parent=f"<#{x['category_id']}>" if x.get("category_id") else "No parent category";lines.append(f"**{n}.** {x.get('emoji','🎫')} {x.get('name','Unnamed')} • {role} • {parent}")
        e=discord.Embed(title=f"🎫 Ticket Setup • {cfg.get('title') or 'Untitled'}",description=(cfg.get('description') or "No description set.")[:4096],color=discord.Color(cfg.get("color",0x5865F2)));e.add_field(name="Panel channel",value=ch.mention if ch else "Not selected");e.add_field(name="Claim required",value="Yes" if cfg.get("claim_required") else "No");e.add_field(name="Published",value="Yes" if cfg.get("published_message_id") else "No");e.add_field(name="Categories",value="\n".join(lines) or "No categories",inline=False);return e
    def rebuild(self):
        self.clear_items();buttons=[("Panel Text","📝","text",discord.ButtonStyle.primary),("Color","🎨","color",discord.ButtonStyle.secondary),("Panel Channel","📍","channel",discord.ButtonStyle.secondary),("Claim","🙋","claim",discord.ButtonStyle.primary),("Categories","🗂️","categories",discord.ButtonStyle.secondary),("Sync Live Panel","🔄","sync",discord.ButtonStyle.success),("Publish","📢","publish",discord.ButtonStyle.success)]
        for n,(label,emoji,action,style) in enumerate(buttons):b=discord.ui.Button(label=label,emoji=emoji,style=style,custom_id=f"lightcore:ticketsetup:{self.guild_id}:{action}",row=n//4);b.callback=self.callback(action);self.add_item(b)
    async def interaction_check(self,i):
        if not i.user.guild_permissions.manage_channels:await i.response.send_message("❌ You need Manage Channels to edit ticket setup.",ephemeral=True);return False
        return True
    def callback(self,action):
        async def inner(i):
            if action=="text":return await i.response.send_modal(TicketTextModal(self))
            if action=="color":return await i.response.send_modal(TicketColorModal(self))
            if action=="channel":return await i.response.send_message("Choose the ticket panel channel.",view=PanelChannelView(self),ephemeral=True)
            if action=="claim":
                cfg=self.config();cfg["claim_required"]=not cfg.get("claim_required",False);save_config(self.guild_id,cfg);await self.cog.sync_published_panel(self.guild_id);return await i.response.edit_message(embed=self.embed(),view=self)
            if action=="categories":m=CategoryManagerView(self);return await i.response.edit_message(embed=m.embed(),view=m)
            if action=="sync":ok,msg=await self.cog.sync_published_panel(self.guild_id);return await i.response.send_message(msg,ephemeral=True)
            if action=="publish":return await self.cog.publish_panel(i,self.guild_id)
        return inner

class TicketTextModal(discord.ui.Modal,title="Edit Ticket Panel Text"):
    title_input=discord.ui.TextInput(label="Panel title",max_length=256);description_input=discord.ui.TextInput(label="Panel description",style=discord.TextStyle.paragraph,max_length=4000)
    def __init__(self,e):super().__init__();self.editor=e;cfg=e.config();self.title_input.default=cfg.get("title","");self.description_input.default=cfg.get("description","")
    async def on_submit(self,i):
        cfg=self.editor.config();cfg["title"]=str(self.title_input).strip() or "LightCore Support";cfg["description"]=str(self.description_input).strip() or "Choose a support category below to open a private ticket.";save_config(self.editor.guild_id,cfg);await self.editor.cog.sync_published_panel(self.editor.guild_id);await i.response.edit_message(embed=self.editor.embed(),view=self.editor)

class TicketColorModal(discord.ui.Modal,title="Edit Ticket Panel Color"):
    color=discord.ui.TextInput(label="Hex color",placeholder="#5865F2",max_length=7)
    def __init__(self,e):super().__init__();self.editor=e;self.color.default=f"#{e.config().get('color',0x5865F2):06X}"
    async def on_submit(self,i):
        try:value=color_value(str(self.color))
        except ValueError as exc:return await i.response.send_message(f"❌ {exc}",ephemeral=True)
        cfg=self.editor.config();cfg["color"]=value;save_config(self.editor.guild_id,cfg);await self.editor.cog.sync_published_panel(self.editor.guild_id);await i.response.edit_message(embed=self.editor.embed(),view=self.editor)

class PanelChannelView(discord.ui.View):
    def __init__(self,e):super().__init__(timeout=120);self.editor=e;s=discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text],placeholder="Choose the ticket panel channel…");s.callback=self.select;self.add_item(s)
    async def select(self,i):
        cid=i.data.get("values",[None])[0]
        if not cid:return await i.response.send_message("❌ No channel selected.",ephemeral=True)
        cfg=self.editor.config();cfg["panel_channel_id"]=int(cid);save_config(self.editor.guild_id,cfg);await i.response.send_message("✅ Panel channel saved.",ephemeral=True)

class CategoryManagerView(discord.ui.View):
    def __init__(self,e):super().__init__(timeout=300);self.editor=e;self.rebuild()
    def rebuild(self):
        self.clear_items();cfg=self.editor.config();opts=[discord.SelectOption(label=x["name"][:100],value=str(i),emoji=x.get("emoji") or "🎫") for i,x in enumerate(cfg.get("categories",[])[:25])]
        if opts:s=discord.ui.Select(placeholder="Select a category…",options=opts);s.callback=self.select;self.add_item(s)
        for label,emoji,action,style in [("Add","➕","add",discord.ButtonStyle.success),("Edit","✏️","edit",discord.ButtonStyle.primary),("Remove","➖","remove",discord.ButtonStyle.danger),("Back","↩️","back",discord.ButtonStyle.secondary)]:b=discord.ui.Button(label=label,emoji=emoji,style=style);b.callback=self.action(action);self.add_item(b)
    def embed(self):
        cfg=self.editor.config();text="\n".join(f"**{i}.** {x.get('emoji','🎫')} {x.get('name','Unnamed')}" for i,x in enumerate(cfg.get('categories',[]),1));return discord.Embed(title="🗂️ Ticket Categories",description=text or "None",color=discord.Color(cfg.get('color',0x5865F2)))
    async def select(self,i):self.editor.selected_category=int(i.data["values"][0]);await i.response.edit_message(embed=self.embed(),view=self)
    def action(self,action):
        async def inner(i):
            if action=="back":self.editor.rebuild();return await i.response.edit_message(embed=self.editor.embed(),view=self.editor)
            if action=="add":return await i.response.send_modal(CategoryModal(self.editor))
            cfg=self.editor.config();idx=self.editor.selected_category
            if idx>=len(cfg.get("categories",[])):return await i.response.send_message("❌ Select a valid category first.",ephemeral=True)
            if action=="remove":cfg["categories"].pop(idx);save_config(self.editor.guild_id,cfg);await self.editor.cog.sync_published_panel(self.editor.guild_id);self.rebuild();return await i.response.edit_message(embed=self.embed(),view=self)
            if action=="edit":return await i.response.send_modal(CategoryModal(self.editor,idx))
        return inner

class CategoryModal(discord.ui.Modal,title="Edit Ticket Category"):
    name=discord.ui.TextInput(label="Category name",max_length=80);emoji=discord.ui.TextInput(label="Emoji",max_length=8,required=False);support_role_id=discord.ui.TextInput(label="Support role ID",required=False,max_length=25);parent_category_id=discord.ui.TextInput(label="Discord category ID",required=False,max_length=25)
    def __init__(self,e,index=None):
        super().__init__();self.editor=e;self.index=index
        if index is not None:
            x=e.config()["categories"][index];self.name.default=x.get("name","");self.emoji.default=x.get("emoji","🎫");self.support_role_id.default=str(x.get("role_id") or "");self.parent_category_id.default=str(x.get("category_id") or "")
    async def on_submit(self,i):
        try:r=int(str(self.support_role_id).strip()) if str(self.support_role_id).strip() else None;p=int(str(self.parent_category_id).strip()) if str(self.parent_category_id).strip() else None
        except ValueError:return await i.response.send_message("❌ IDs must be numbers.",ephemeral=True)
        cfg=self.editor.config();item={"name":str(self.name).strip()[:80] or "Support","emoji":str(self.emoji).strip()[:8] or "🎫","role_id":r,"category_id":p}
        if self.index is None:
            if len(cfg["categories"])>=25:return await i.response.send_message("❌ Discord allows at most 25 categories here.",ephemeral=True)
            cfg["categories"].append(item)
        else:cfg["categories"][self.index]=item
        save_config(self.editor.guild_id,cfg);await self.editor.cog.sync_published_panel(self.editor.guild_id);m=CategoryManagerView(self.editor);await i.response.edit_message(embed=m.embed(),view=m)

class Tickets(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        for g in self.bot.guilds:
            self.bot.add_view(TicketPanelView(self,g.id));cfg=load_config(g.id)
            with connect() as db:rows=db.execute("SELECT id FROM tickets WHERE guild_id=? AND status='open'",(g.id,)).fetchall()
            for row in rows:
                role=None
                with connect() as db:meta=db.execute("SELECT category FROM ticket_meta WHERE ticket_id=?",(row["id"],)).fetchone()
                if meta:
                    for x in cfg["categories"]:
                        if x.get("name")==meta["category"]:role=x.get("role_id");break
                if cfg.get("claim_required"):self.bot.add_view(TicketClaimView(g.id,row["id"],role))
    def panel_embed(self,gid):cfg=load_config(gid);return discord.Embed(title=cfg.get("title") or "Support",description=cfg.get("description") or "Choose a ticket category.",color=discord.Color(cfg.get("color",0x5865F2)))
    async def sync_published_panel(self,gid):
        cfg=load_config(gid);mid=cfg.get("published_message_id");cid=cfg.get("panel_channel_id")
        if not mid or not cid:return False,"ℹ️ No published ticket panel is saved yet."
        ch=self.bot.get_channel(int(cid))
        if not isinstance(ch,discord.TextChannel):return False,"❌ The configured panel channel is unavailable."
        try:m=await ch.fetch_message(int(mid));await m.edit(embed=self.panel_embed(gid),view=TicketPanelView(self,gid));return True,"✅ Live ticket panel updated."
        except discord.NotFound:return False,"⚠️ The saved panel message no longer exists."
        except discord.Forbidden:return False,"❌ I cannot edit the saved ticket panel message."
        except discord.HTTPException as exc:return False,f"❌ Discord rejected the update: {exc}"
    async def publish_panel(self,source,gid):
        cfg=load_config(gid);ch=self.bot.get_channel(cfg.get("panel_channel_id")) if cfg.get("panel_channel_id") else None
        if not isinstance(ch,discord.TextChannel):msg="❌ Choose a text channel first.";return await source.response.send_message(msg,ephemeral=True) if hasattr(source,"response") else await source.send(msg)
        if cfg.get("published_message_id"):ok,msg=await self.sync_published_panel(gid);return await source.response.send_message(msg,ephemeral=True) if hasattr(source,"response") else await source.send(msg)
        m=await ch.send(embed=self.panel_embed(gid),view=TicketPanelView(self,gid));cfg["published_message_id"]=m.id;save_config(gid,cfg);msg=f"✅ Ticket panel published in {ch.mention}.";return await source.response.send_message(msg,ephemeral=True) if hasattr(source,"response") else await source.send(msg)
    @commands.hybrid_command(name="ticketsetup",description="Open editable ticket setup.")
    @commands.has_permissions(manage_channels=True)
    async def ticketsetup(self,ctx):e=TicketEditor(self,ctx.guild.id);e.message=await ctx.send(embed=e.embed(),view=e)
    @commands.hybrid_command(name="ticketpanel",description="Publish or synchronize the ticket panel.")
    @commands.has_permissions(manage_channels=True)
    async def ticketpanel(self,ctx):await self.publish_panel(ctx,ctx.guild.id)
    @commands.hybrid_command(name="setticketcategory",description="Set the legacy ticket category.")
    @commands.has_permissions(manage_guild=True)
    async def setticketcategory(self,ctx,category:discord.CategoryChannel):set_setting(ctx.guild.id,"ticket_category",category.id);await ctx.send(f"Ticket category set to **{category.name}**.")
    @commands.hybrid_command(name="setticketlog",description="Set the ticket transcript log channel.")
    @commands.has_permissions(manage_guild=True)
    async def setticketlog(self,ctx,channel:discord.TextChannel):set_setting(ctx.guild.id,"ticket_log_channel",channel.id);await ctx.send(f"Ticket log channel set to {channel.mention}.")
    @commands.hybrid_command(name="close",description="Close the current LightCore ticket.")
    @commands.has_permissions(manage_channels=True)
    async def close(self,ctx):
        with connect() as db:row=db.execute("SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'",(ctx.guild.id,ctx.channel.id)).fetchone()
        if not row:return await ctx.send("This is not an open LightCore ticket channel.")
        lines=[]
        try:
            async for m in ctx.channel.history(limit=500,oldest_first=True):lines.append(f"[{m.created_at:%Y-%m-%d %H:%M:%S UTC}] {m.author} ({m.author.id}): {m.content.replace(chr(10),' ')}")
        except discord.HTTPException:pass
        transcript="\n".join(lines) or "No messages captured."
        with connect() as db:db.execute("UPDATE tickets SET status='closed',closed_at=CURRENT_TIMESTAMP WHERE id=?",(row["id"],));db.execute("INSERT INTO ticket_transcripts(ticket_id,transcript) VALUES(?,?)",(row["id"],transcript[:50000]))
        await ctx.send("Closing ticket and saving its transcript…");await ctx.channel.delete(reason=f"LightCore ticket closed by {ctx.author}")

async def setup(bot):await bot.add_cog(Tickets(bot))
