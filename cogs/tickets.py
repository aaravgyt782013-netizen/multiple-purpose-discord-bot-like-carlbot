import io
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from database import connect

PRIORITIES = {"low": "🟢", "normal": "🔵", "high": "🟠", "urgent": "🔴"}


def system(guild_id):
    with connect() as db:
        return db.execute("SELECT * FROM ticket_systems WHERE guild_id=?", (guild_id,)).fetchone()


def types(guild_id, enabled=True):
    with connect() as db:
        q = "SELECT * FROM ticket_types WHERE guild_id=?"
        if enabled:
            q += " AND enabled=1"
        return db.execute(q + " ORDER BY id", (guild_id,)).fetchall()


def current_ticket(channel_id):
    with connect() as db:
        return db.execute("SELECT t.*,ty.name type_name,ty.support_role_id FROM ticket_instances t JOIN ticket_types ty ON ty.id=t.type_id WHERE t.channel_id=? AND t.status='open'", (channel_id,)).fetchone()


def staff(member, role_id=None):
    return bool(member.guild_permissions.administrator or member.guild_permissions.manage_guild or member.guild_permissions.manage_channels or (role_id and any(r.id == role_id for r in member.roles)))


async def transcript(channel):
    lines = [f"LightCore Ticket Transcript | {channel.guild.name} | #{channel.name}", "=" * 80]
    async for m in channel.history(limit=None, oldest_first=True):
        body = (m.content or "").replace("\n", " ")
        if m.attachments:
            body += " " + " ".join(a.url for a in m.attachments)
        lines.append(f"[{m.created_at.astimezone(timezone.utc).isoformat()}] {m.author} ({m.author.id}): {body}")
    return "\n".join(lines)


class Panel(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog, self.guild_id = cog, guild_id
        opts = [discord.SelectOption(label=t["name"][:100], value=str(t["id"]), description=t["description"][:100], emoji=t["emoji"] or "🎫") for t in types(guild_id)[:25]]
        if opts:
            s = discord.ui.Select(placeholder="Select a ticket type…", options=opts, custom_id=f"lightcore:ticket:v2:select:{guild_id}")
            s.callback = self.select
            self.add_item(s)
        else:
            self.add_item(discord.ui.Button(label="No ticket types configured", disabled=True))

    async def select(self, interaction):
        await self.cog.create_ticket(interaction, int(interaction.data["values"][0]))


class Setup(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=900)
        self.cog, self.guild_id = cog, guild_id

    async def interaction_check(self, i):
        if not i.user.guild_permissions.manage_channels:
            await i.response.send_message("❌ Manage Channels is required.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Add Type", emoji="➕", style=discord.ButtonStyle.success)
    async def add(self, i, _):
        await i.response.send_modal(TypeModal(self.guild_id))

    @discord.ui.button(label="Panel / Logs", emoji="⚙️", style=discord.ButtonStyle.primary)
    async def channels(self, i, _):
        await i.response.send_message("Select the panel channel, then the transcript log channel.", view=ChannelSetup(self.guild_id), ephemeral=True)

    @discord.ui.button(label="Auto-Close", emoji="⏱️", style=discord.ButtonStyle.secondary)
    async def auto(self, i, _):
        await i.response.send_modal(AutoCloseModal(self.guild_id))

    @discord.ui.button(label="Publish", emoji="📢", style=discord.ButtonStyle.success)
    async def publish(self, i, _):
        ok, msg = await self.cog.publish(i.guild)
        await i.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Types", emoji="📋", style=discord.ButtonStyle.secondary, row=1)
    async def list_types(self, i, _):
        rows = types(self.guild_id, False)
        text = "\n".join(f"`{r['id']}` {r['emoji']} **{r['name']}** • <@&{r['support_role_id']}>" if r['support_role_id'] else f"`{r['id']}` {r['emoji']} **{r['name']}**" for r in rows)
        await i.response.send_message(text or "No ticket types.", ephemeral=True)


class ChannelSetup(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        p = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Ticket panel channel")
        p.callback = self.panel
        self.add_item(p)
        l = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Transcript log channel")
        l.callback = self.log
        self.add_item(l)

    async def panel(self, i):
        cid = int(i.data["values"][0])
        with connect() as db:
            db.execute("INSERT INTO ticket_systems(guild_id,panel_channel_id) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET panel_channel_id=excluded.panel_channel_id", (self.guild_id, cid))
        await i.response.send_message(f"✅ Panel channel: <#{cid}>", ephemeral=True)

    async def log(self, i):
        cid = int(i.data["values"][0])
        with connect() as db:
            db.execute("INSERT INTO ticket_systems(guild_id,log_channel_id) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET log_channel_id=excluded.log_channel_id", (self.guild_id, cid))
        await i.response.send_message(f"✅ Transcript log: <#{cid}>", ephemeral=True)


class TypeModal(discord.ui.Modal, title="Ticket Type"):
    name = discord.ui.TextInput(label="Name", max_length=80)
    description = discord.ui.TextInput(label="Description", max_length=100, required=False)
    emoji = discord.ui.TextInput(label="Emoji", max_length=8, required=False)
    support_role = discord.ui.TextInput(label="Support role ID", max_length=25, required=False)
    category = discord.ui.TextInput(label="Discord category ID", max_length=25, required=False)

    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, i):
        try:
            role_id = int(str(self.support_role)) if str(self.support_role).strip() else None
            category_id = int(str(self.category)) if str(self.category).strip() else None
        except ValueError:
            return await i.response.send_message("❌ IDs must be numeric.", ephemeral=True)
        if role_id and not i.guild.get_role(role_id):
            return await i.response.send_message("❌ Support role is not in this server.", ephemeral=True)
        if category_id and not isinstance(i.guild.get_channel(category_id), discord.CategoryChannel):
            return await i.response.send_message("❌ Category ID is not a Discord category.", ephemeral=True)
        with connect() as db:
            db.execute("INSERT INTO ticket_types(guild_id,name,emoji,description,support_role_id,category_channel_id) VALUES(?,?,?,?,?,?)", (self.guild_id, str(self.name).strip(), str(self.emoji).strip() or "🎫", str(self.description).strip() or "Open a support ticket.", role_id, category_id))
        await i.response.send_message(f"✅ Created **{self.name}**.", ephemeral=True)


class AutoCloseModal(discord.ui.Modal, title="Ticket Auto-Close"):
    minutes = discord.ui.TextInput(label="Inactive minutes", placeholder="1440; use 0 to disable", max_length=7)

    def __init__(self, guild_id):
        super().__init__()
        row = system(guild_id)
        self.guild_id = guild_id
        self.minutes.default = str(row["auto_close_minutes"] if row else 1440)

    async def on_submit(self, i):
        try:
            value = max(0, min(10080, int(str(self.minutes))))
        except ValueError:
            return await i.response.send_message("❌ Enter a number of minutes.", ephemeral=True)
        with connect() as db:
            db.execute("INSERT INTO ticket_systems(guild_id,auto_close_minutes) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET auto_close_minutes=excluded.auto_close_minutes", (self.guild_id, value))
        await i.response.send_message(f"✅ Auto-close: **{value} minutes**." if value else "✅ Auto-close disabled.", ephemeral=True)


class Controls(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None)
        self.cog, self.ticket_id = cog, ticket_id

    @discord.ui.button(label="Claim", emoji="🙋", style=discord.ButtonStyle.primary, custom_id="lightcore:ticket:v2:claim")
    async def claim(self, i, _):
        await self.cog.claim(i, self.ticket_id)

    @discord.ui.button(label="Priority", emoji="🚩", style=discord.ButtonStyle.secondary, custom_id="lightcore:ticket:v2:priority")
    async def priority(self, i, _):
        await i.response.send_message("Choose priority:", view=Priority(self.cog, self.ticket_id), ephemeral=True)

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="lightcore:ticket:v2:close")
    async def close(self, i, _):
        await self.cog.close(i, self.ticket_id)


class Priority(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=120)
        for name, emoji in PRIORITIES.items():
            b = discord.ui.Button(label=name.title(), emoji=emoji)
            b.callback = self.make(cog, ticket_id, name)
            self.add_item(b)

    @staticmethod
    def make(cog, ticket_id, value):
        async def cb(i):
            await cog.set_priority(i, ticket_id, value)
        return cb


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.autoclose.start()

    def cog_unload(self):
        self.autoclose.cancel()

    async def cog_load(self):
        with connect() as db:
            panels = db.execute("SELECT guild_id,panel_message_id FROM ticket_systems WHERE panel_message_id IS NOT NULL AND enabled=1").fetchall()
            open_rows = db.execute("SELECT id FROM ticket_instances WHERE status='open'").fetchall()
        for r in panels:
            self.bot.add_view(Panel(self, r["guild_id"]), message_id=r["panel_message_id"])
        for r in open_rows:
            self.bot.add_view(Controls(self, r["id"]))

    async def publish(self, guild):
        s = system(guild.id)
        if not s or not s["panel_channel_id"]:
            return False, "❌ Choose a panel channel in `.ticket setup` first."
        channel = guild.get_channel(s["panel_channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return False, "❌ Panel channel is missing."
        embed = discord.Embed(title=s["title"], description=s["description"], color=s["color"])
        rows = types(guild.id)
        embed.add_field(name="Ticket types", value="\n".join(f"{r['emoji']} **{r['name']}** — {r['description']}" for r in rows[:25]) or "No types configured.", inline=False)
        view = Panel(self, guild.id)
        msg = None
        if s["panel_message_id"]:
            try:
                msg = await channel.fetch_message(s["panel_message_id"])
            except discord.HTTPException:
                pass
        if msg:
            await msg.edit(embed=embed, view=view)
        else:
            msg = await channel.send(embed=embed, view=view)
        with connect() as db:
            db.execute("INSERT INTO ticket_systems(guild_id,panel_channel_id,panel_message_id) VALUES(?,?,?) ON CONFLICT(guild_id) DO UPDATE SET panel_channel_id=excluded.panel_channel_id,panel_message_id=excluded.panel_message_id", (guild.id, channel.id, msg.id))
        self.bot.add_view(view, message_id=msg.id)
        return True, f"✅ Ticket panel published in {channel.mention}."

    async def create_ticket(self, i, type_id):
        with connect() as db:
            t = db.execute("SELECT * FROM ticket_types WHERE id=? AND guild_id=? AND enabled=1", (type_id, i.guild.id)).fetchone()
            existing = db.execute("SELECT channel_id FROM ticket_instances WHERE guild_id=? AND opener_id=? AND status='open'", (i.guild.id, i.user.id)).fetchone()
        if not t:
            return await i.response.send_message("❌ Ticket type unavailable.", ephemeral=True)
        if existing and i.guild.get_channel(existing["channel_id"]):
            return await i.response.send_message(f"❌ You already have <#{existing['channel_id']}> open.", ephemeral=True)
        category = i.guild.get_channel(t["category_channel_id"]) if t["category_channel_id"] else None
        role = i.guild.get_role(t["support_role_id"]) if t["support_role_id"] else None
        overwrites = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)}
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        if i.guild.me:
            overwrites[i.guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True, attach_files=True)
        channel = await i.guild.create_text_channel(f"ticket-{i.user.name[:18]}", category=category if isinstance(category, discord.CategoryChannel) else None, overwrites=overwrites, topic=f"[PRIORITY: NORMAL] {t['name']}", reason="LightCore TicketV2 rebuild")
        with connect() as db:
            cur = db.execute("INSERT INTO ticket_instances(guild_id,channel_id,opener_id,type_id) VALUES(?,?,?,?)", (i.guild.id, channel.id, i.user.id, type_id))
            ticket_id = cur.lastrowid
            db.execute("INSERT OR IGNORE INTO ticket_participants(ticket_id,user_id) VALUES(?,?)", (ticket_id, i.user.id))
        e = discord.Embed(title=f"{t['emoji']} {t['name']}", description=f"Welcome {i.user.mention}. A support member will be with you shortly.\n\n**Priority:** 🔵 Normal", color=discord.Color.blurple())
        e.set_footer(text=f"Ticket #{ticket_id} • Controls below")
        await channel.send(content=f"{i.user.mention} {role.mention if role else ''}".strip(), embed=e, view=Controls(self, ticket_id))
        self.bot.add_view(Controls(self, ticket_id))
        await i.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)

    async def claim(self, i, ticket_id):
        with connect() as db:
            row = db.execute("SELECT t.*,ty.support_role_id FROM ticket_instances t JOIN ticket_types ty ON ty.id=t.type_id WHERE t.id=? AND t.status='open'", (ticket_id,)).fetchone()
            if not row:
                return await i.response.send_message("❌ Ticket is closed or missing.", ephemeral=True)
            if not staff(i.user, row["support_role_id"]):
                return await i.response.send_message("❌ Support staff only.", ephemeral=True)
            if row["claimed_by"] and row["claimed_by"] != i.user.id:
                return await i.response.send_message(f"❌ Already claimed by <@{row['claimed_by']}>.", ephemeral=True)
            db.execute("UPDATE ticket_instances SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE id=?", (i.user.id, ticket_id))
        await i.response.send_message(f"🙋 Claimed by {i.user.mention}.")

    async def set_priority(self, i, ticket_id, priority):
        row = current_ticket(i.channel.id)
        if not row or row["id"] != ticket_id or not staff(i.user, row["support_role_id"]):
            return await i.response.send_message("❌ Staff only in an open ticket.", ephemeral=True)
        with connect() as db:
            db.execute("UPDATE ticket_instances SET priority=?,last_activity=CURRENT_TIMESTAMP WHERE id=?", (priority, ticket_id))
        await i.channel.edit(topic=f"[PRIORITY: {priority.upper()}] {row['type_name']}")
        await i.response.send_message(f"🚩 Priority set to **{priority.upper()}**.")

    async def close(self, i, ticket_id):
        row = current_ticket(i.channel.id)
        if not row:
            return await i.response.send_message("❌ Ticket not found.", ephemeral=True)
        if not (i.user.id == row["opener_id"] or staff(i.user, row["support_role_id"])):
            return await i.response.send_message("❌ Only the opener or ticket staff can close it.", ephemeral=True)
        await i.response.defer()
        await self.finish_close(i.guild, i.channel, row, i.user.id)
        await i.followup.send("🔒 Ticket closed and transcript logged.", ephemeral=True)

    async def finish_close(self, guild, channel, row, closed_by=None):
        text = await transcript(channel)
        s = system(guild.id)
        log = guild.get_channel(s["log_channel_id"]) if s and s["log_channel_id"] else None
        if log:
            embed = discord.Embed(title="📄 Ticket Closed", description=f"Ticket **#{row['id']}** • {channel.mention}", color=discord.Color.red())
            embed.add_field(name="Closed by", value=f"<@{closed_by}>" if closed_by else "Auto-close")
            embed.add_field(name="Priority", value=row["priority"].upper())
            await log.send(embed=embed, file=discord.File(io.BytesIO(text.encode()), filename=f"ticket-{row['id']}-transcript.txt"))
        with connect() as db:
            db.execute("INSERT INTO ticket_transcript_v2(ticket_id,guild_id,channel_id,closed_by,content) VALUES(?,?,?,?,?)", (row["id"], guild.id, channel.id, closed_by, text))
            db.execute("UPDATE ticket_instances SET status='closed',closed_at=CURRENT_TIMESTAMP,closed_by=? WHERE id=?", (closed_by, row["id"]))
        await channel.send("🔒 This ticket is now closed. The channel is locked; a transcript has been logged.")
        await channel.set_permissions(guild.default_role, view_channel=False, send_messages=False)
        opener = guild.get_member(row["opener_id"])
        if opener:
            await channel.set_permissions(opener, send_messages=False, view_channel=True, read_message_history=True)

    @commands.hybrid_group(name="ticket", description="TicketV2-style ticket management.", invoke_without_command=True)
    async def ticket(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `.ticket setup`, `.ticket panel`, `.ticket list`, `.ticket claim`, `.ticket close`, `.ticket priority`, `.ticket add`, `.ticket remove`, or `.ticket rename`.")

    @ticket.command(name="setup", description="Open the interactive ticket setup wizard.")
    @commands.has_permissions(manage_channels=True)
    async def setup(self, ctx):
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_systems(guild_id) VALUES(?)", (ctx.guild.id,))
        s = system(ctx.guild.id)
        await ctx.send(embed=discord.Embed(title="🎫 Ticket Setup Wizard", description="Build ticket types, assign individual support roles, configure transcript logging and inactivity auto-close, then publish the panel.", color=s["color"]), view=Setup(self, ctx.guild.id))

    @ticket.command(name="panel", description="Publish or refresh the ticket panel.")
    @commands.has_permissions(manage_channels=True)
    async def panel(self, ctx):
        _, msg = await self.publish(ctx.guild)
        await ctx.send(msg)

    @ticket.command(name="list", description="List ticket types and open ticket count.")
    @commands.has_permissions(manage_channels=True)
    async def list_cmd(self, ctx):
        rows = types(ctx.guild.id, False)
        with connect() as db:
            count = db.execute("SELECT COUNT(*) c FROM ticket_instances WHERE guild_id=? AND status='open'", (ctx.guild.id,)).fetchone()["c"]
        text = "\n".join(f"`{r['id']}` {r['emoji']} **{r['name']}**" for r in rows) or "No ticket types configured."
        await ctx.send(embed=discord.Embed(title="🎫 Ticket Types", description=text, color=discord.Color.blurple()).set_footer(text=f"Open tickets: {count}"))

    @ticket.command(name="claim", description="Claim the current ticket.")
    async def claim_cmd(self, ctx):
        row = current_ticket(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        if not staff(ctx.author, row["support_role_id"]):
            return await ctx.send("❌ Support staff only.")
        with connect() as db:
            if row["claimed_by"] and row["claimed_by"] != ctx.author.id:
                return await ctx.send(f"❌ Already claimed by <@{row['claimed_by']}>.")
            db.execute("UPDATE ticket_instances SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE id=?", (ctx.author.id, row["id"]))
        await ctx.send(f"🙋 Claimed by {ctx.author.mention}.")

    @ticket.command(name="close", description="Close the current ticket and log a transcript.")
    async def close_cmd(self, ctx):
        row = current_ticket(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        if not (ctx.author.id == row["opener_id"] or staff(ctx.author, row["support_role_id"])):
            return await ctx.send("❌ Only the opener or ticket staff can close it.")
        await ctx.send("🔒 Closing and generating transcript…")
        await self.finish_close(ctx.guild, ctx.channel, row, ctx.author.id)

    @ticket.command(name="priority", description="Set priority: low, normal, high, urgent.")
    async def priority_cmd(self, ctx, priority: str):
        priority = priority.lower()
        row = current_ticket(ctx.channel.id)
        if priority not in PRIORITIES or not row:
            return await ctx.send("❌ Use low, normal, high or urgent in an open ticket.")
        if not staff(ctx.author, row["support_role_id"]):
            return await ctx.send("❌ Support staff only.")
        with connect() as db:
            db.execute("UPDATE ticket_instances SET priority=?,last_activity=CURRENT_TIMESTAMP WHERE id=?", (priority, row["id"]))
        await ctx.channel.edit(topic=f"[PRIORITY: {priority.upper()}] {row['type_name']}")
        await ctx.send(f"🚩 Priority set to **{priority.upper()}**.")

    @ticket.command(name="add", description="Add a member to the current ticket.")
    @commands.has_permissions(manage_channels=True)
    async def add_cmd(self, ctx, member: discord.Member):
        row = current_ticket(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        await ctx.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        with connect() as db:
            db.execute("INSERT OR IGNORE INTO ticket_participants(ticket_id,user_id) VALUES(?,?)", (row["id"], member.id))
        await ctx.send(f"✅ Added {member.mention}.")

    @ticket.command(name="remove", description="Remove a member from the current ticket.")
    @commands.has_permissions(manage_channels=True)
    async def remove_cmd(self, ctx, member: discord.Member):
        row = current_ticket(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        if member.id == row["opener_id"]:
            return await ctx.send("❌ The opener cannot be removed.")
        await ctx.channel.set_permissions(member, overwrite=None)
        with connect() as db:
            db.execute("DELETE FROM ticket_participants WHERE ticket_id=? AND user_id=?", (row["id"], member.id))
        await ctx.send(f"✅ Removed {member.mention}.")

    @ticket.command(name="rename", description="Rename the current ticket channel.")
    @commands.has_permissions(manage_channels=True)
    async def rename_cmd(self, ctx, *, name: str):
        row = current_ticket(ctx.channel.id)
        if not row:
            return await ctx.send("❌ This is not an open ticket.")
        clean = "-".join(name.lower().split())[:90]
        await ctx.channel.edit(name=clean)
        with connect() as db:
            db.execute("UPDATE ticket_instances SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
        await ctx.send(f"✅ Renamed to **#{clean}**.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        row = current_ticket(message.channel.id)
        if row:
            with connect() as db:
                db.execute("UPDATE ticket_instances SET last_activity=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))

    @tasks.loop(minutes=5)
    async def autoclose(self):
        now = datetime.now(timezone.utc)
        with connect() as db:
            rows = db.execute("SELECT t.*,s.auto_close_minutes,ty.support_role_id,ty.name type_name FROM ticket_instances t JOIN ticket_systems s ON s.guild_id=t.guild_id JOIN ticket_types ty ON ty.id=t.type_id WHERE t.status='open' AND s.auto_close_minutes>0").fetchall()
        for row in rows:
            try:
                last = datetime.fromisoformat(row["last_activity"].replace(" ", "T")).replace(tzinfo=timezone.utc)
                if now - last < timedelta(minutes=row["auto_close_minutes"]):
                    continue
                guild = self.bot.get_guild(row["guild_id"])
                channel = guild.get_channel(row["channel_id"]) if guild else None
                if channel:
                    await self.finish_close(guild, channel, row, None)
            except Exception:
                continue

    @autoclose.before_loop
    async def before_autoclose(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TicketCog(bot))
