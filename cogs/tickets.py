import io
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks
from database import connect

PRIORITIES = {"low": "🟢", "normal": "🔵", "high": "🟠", "urgent": "🔴"}


def get_system(guild_id):
    with connect() as db:
        return db.execute("SELECT * FROM ticket_systems WHERE guild_id=?", (guild_id,)).fetchone()


def get_types(guild_id, enabled_only=False):
    q = "SELECT * FROM ticket_types WHERE guild_id=?"
    if enabled_only:
        q += " AND enabled=1"
    with connect() as db:
        return db.execute(q + " ORDER BY id", (guild_id,)).fetchall()


def get_type(guild_id, type_id):
    with connect() as db:
        return db.execute("SELECT * FROM ticket_types WHERE guild_id=? AND id=?", (guild_id, type_id)).fetchone()


def get_ticket(channel_id):
    with connect() as db:
        return db.execute("""SELECT t.*, ty.name type_name, ty.emoji type_emoji,
            ty.description type_description, ty.support_role_id, ty.log_channel_id,
            ty.transcript_channel_id, ty.discord_category_id
            FROM ticket_instances t JOIN ticket_types ty ON ty.id=t.type_id
            WHERE t.channel_id=? AND t.status='open'""", (channel_id,)).fetchone()


def is_staff(member, role_id=None):
    return bool(member.guild_permissions.administrator or member.guild_permissions.manage_guild or
                member.guild_permissions.manage_channels or (role_id and any(r.id == role_id for r in member.roles)))


async def make_transcript(channel):
    lines = [f"LightCore Ticket Transcript | {channel.guild.name} | #{channel.name}", "=" * 90]
    async for message in channel.history(limit=None, oldest_first=True):
        text = (message.content or "").replace("\n", " ")
        if message.attachments:
            text += " " + " ".join(a.url for a in message.attachments)
        lines.append(f"[{message.created_at.astimezone(timezone.utc).isoformat()}] {message.author} ({message.author.id}): {text}")
    return "\n".join(lines)


class PanelView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog, self.guild_id = cog, guild_id
        rows = get_types(guild_id, True)[:25]
        options = [discord.SelectOption(label=r["name"][:100], value=str(r["id"]),
                    description=r["description"][:100], emoji=r["emoji"] or "🎫") for r in rows]
        select = discord.ui.Select(placeholder="Choose a ticket type…", options=options or
                                   [discord.SelectOption(label="No ticket types configured", value="none")],
                                   disabled=not options, custom_id=f"lightcore:tickets:select:{guild_id}")
        select.callback = self.open_ticket
        self.add_item(select)
        edit = discord.ui.Button(label="Edit", emoji="✏️", style=discord.ButtonStyle.secondary,
                                 custom_id=f"lightcore:tickets:edit:{guild_id}")
        edit.callback = self.edit_panel
        self.add_item(edit)

    async def open_ticket(self, interaction):
        value = interaction.data["values"][0]
        if value == "none":
            return await interaction.response.send_message("❌ No ticket types are configured.", ephemeral=True)
        await self.cog.create_ticket(interaction, int(value))

    async def edit_panel(self, interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Manage Channels is required.", ephemeral=True)
        await interaction.response.send_message("✏️ Opening the ticket setup editor…", ephemeral=True)
        await self.cog.start_setup(interaction, editing=True)


class SetupState:
    def __init__(self, guild_id, existing=None):
        self.guild_id = guild_id
        self.title = existing["title"] if existing else "Support Tickets"
        self.description = existing["description"] if existing else "Choose a ticket type below to contact our support team."
        self.panel_channel_id = existing["panel_channel_id"] if existing else None
        self.auto_close_minutes = existing["auto_close_minutes"] if existing else 1440
        self.types = []
        if existing:
            for r in get_types(guild_id, False):
                self.types.append({"id": r["id"], "name": r["name"], "emoji": r["emoji"],
                    "description": r["description"], "support_role_id": r["support_role_id"],
                    "log_channel_id": r["log_channel_id"], "transcript_channel_id": r["transcript_channel_id"],
                    "discord_category_id": r["discord_category_id"]})


class SetupView(discord.ui.View):
    def __init__(self, cog, state):
        super().__init__(timeout=900)
        self.cog, self.state = cog, state

    async def interaction_check(self, interaction):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Manage Channels is required.", ephemeral=True)
            return False
        return True

    def summary(self):
        types = "\n".join(f"{x['emoji']} **{x['name']}** • support <@&{x['support_role_id']}> • log <#{x['log_channel_id']}> • transcript <#{x['transcript_channel_id']}>" for x in self.state.types)
        return (f"**Panel:** {self.state.title}\n**Target:** <#{self.state.panel_channel_id}>\n"
                f"**Auto-close:** {self.state.auto_close_minutes} minutes\n\n**Categories:**\n{types or 'None yet'}")

    @discord.ui.button(label="Panel Name", emoji="📝", style=discord.ButtonStyle.primary)
    async def name(self, i, _):
        await i.response.send_modal(PanelModal(self.state))

    @discord.ui.button(label="Add Category", emoji="➕", style=discord.ButtonStyle.success)
    async def add(self, i, _):
        await i.response.send_modal(CategoryModal(self.state))

    @discord.ui.button(label="Edit Category", emoji="✏️", style=discord.ButtonStyle.secondary)
    async def edit_category(self, i, _):
        await i.response.send_message("Select a category to edit:", view=CategoryPicker(self.cog, self.state, False), ephemeral=True)

    @discord.ui.button(label="Target Channel", emoji="📢", style=discord.ButtonStyle.primary)
    async def target(self, i, _):
        await i.response.send_message("Choose where the panel should be published:", view=TargetPicker(self.state), ephemeral=True)

    @discord.ui.button(label="Auto-Close", emoji="⏱️", style=discord.ButtonStyle.secondary, row=1)
    async def auto(self, i, _):
        await i.response.send_modal(AutoCloseModal(self.state))

    @discord.ui.button(label="Review", emoji="👀", style=discord.ButtonStyle.secondary, row=1)
    async def review(self, i, _):
        await i.response.edit_message(embed=discord.Embed(title="Review Ticket Setup", description=self.summary(), color=discord.Color.blurple()), view=self)

    @discord.ui.button(label="Delete Category", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def delete_category(self, i, _):
        await i.response.send_message("Select a category to remove:", view=CategoryPicker(self.cog, self.state, True), ephemeral=True)

    @discord.ui.button(label="✅ Finish Setup", style=discord.ButtonStyle.success, row=2)
    async def finish(self, i, _):
        if not self.state.panel_channel_id:
            return await i.response.send_message("❌ Select a target channel before finishing.", ephemeral=True)
        if not self.state.types:
            return await i.response.send_message("❌ Add at least one ticket category before finishing.", ephemeral=True)
        await self.cog.commit_setup(i, self.state)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, row=2)
    async def cancel(self, i, _):
        await i.response.edit_message(content="❌ Setup cancelled. No ticket configuration or Discord resources were changed.", embed=None, view=None)


class PanelModal(discord.ui.Modal, title="Ticket Panel"):
    title_input = discord.ui.TextInput(label="Panel name", max_length=100)
    description = discord.ui.TextInput(label="Panel description", style=discord.TextStyle.paragraph, max_length=1000)

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.title_input.default = state.title
        self.description.default = state.description

    async def on_submit(self, i):
        self.state.title = str(self.title_input).strip()
        self.state.description = str(self.description).strip()
        await i.response.edit_message(embed=discord.Embed(title="Ticket Setup", description=SetupView(i.client.get_cog("TicketCog"), self.state).summary(), color=discord.Color.blurple()))


class CategoryModal(discord.ui.Modal, title="Add Ticket Category"):
    name = discord.ui.TextInput(label="Category name", max_length=60)
    emoji = discord.ui.TextInput(label="Emoji", max_length=8, required=False)
    support_role = discord.ui.TextInput(label="Support role ID", max_length=25)
    log_channel = discord.ui.TextInput(label="Log channel ID", max_length=25)
    transcript_channel = discord.ui.TextInput(label="Transcript channel ID", max_length=25)

    def __init__(self, state, existing=None):
        super().__init__()
        self.state, self.existing = state, existing
        if existing:
            self.name.default = existing["name"]
            self.emoji.default = existing["emoji"]
            self.support_role.default = str(existing["support_role_id"] or "")
            self.log_channel.default = str(existing["log_channel_id"] or "")
            self.transcript_channel.default = str(existing["transcript_channel_id"] or "")

    async def on_submit(self, i):
        try:
            role_id = int(str(self.support_role).strip())
            log_id = int(str(self.log_channel).strip())
            transcript_id = int(str(self.transcript_channel).strip())
        except ValueError:
            return await i.response.send_message("❌ Support role, log channel and transcript channel IDs must be numeric.", ephemeral=True)
        role = i.guild.get_role(role_id)
        log = i.guild.get_channel(log_id)
        transcript = i.guild.get_channel(transcript_id)
        if not role or not isinstance(log, discord.TextChannel) or not isinstance(transcript, discord.TextChannel):
            return await i.response.send_message("❌ Check that the role and both channels exist in this server.", ephemeral=True)
        item = {"id": self.existing["id"] if self.existing else None, "name": str(self.name).strip(),
                "emoji": str(self.emoji).strip() or "🎫", "description": "Open a support ticket.",
                "support_role_id": role_id, "log_channel_id": log_id, "transcript_channel_id": transcript_id,
                "discord_category_id": self.existing["discord_category_id"] if self.existing else None}
        if self.existing:
            self.state.types = [item if x["id"] == self.existing["id"] else x for x in self.state.types]
        else:
            self.state.types.append(item)
        await i.response.edit_message(content="", embed=discord.Embed(title="Ticket Setup", description=SetupView(i.client.get_cog("TicketCog"), self.state).summary(), color=discord.Color.blurple()), view=SetupView(i.client.get_cog("TicketCog"), self.state))


class CategoryPicker(discord.ui.View):
    def __init__(self, cog, state, deleting):
        super().__init__(timeout=180)
        self.cog, self.state, self.deleting = cog, state, deleting
        opts = [discord.SelectOption(label=x["name"][:100], value=str(n)) for n, x in enumerate(state.types)]
        select = discord.ui.Select(placeholder="Choose category…", options=opts[:25])
        select.callback = self.pick
        self.add_item(select)

    async def pick(self, i):
        idx = int(i.data["values"][0])
        item = self.state.types[idx]
        if self.deleting:
            self.state.types.pop(idx)
            await i.response.send_message(f"🗑️ **{item['name']}** removed from the pending setup. Press **Finish Setup** to apply the change.", ephemeral=True)
        else:
            await i.response.send_modal(CategoryModal(self.state, item))


class TargetPicker(discord.ui.View):
    def __init__(self, state):
        super().__init__(timeout=180)
        self.state = state
        s = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Ticket panel target channel")
        s.callback = self.pick
        self.add_item(s)

    async def pick(self, i):
        self.state.panel_channel_id = int(i.data["values"][0])
        await i.response.send_message(f"✅ Panel target set to <#{self.state.panel_channel_id}>. Nothing is published until **Finish Setup**.", ephemeral=True)


class AutoCloseModal(discord.ui.Modal, title="Ticket Auto-Close"):
    minutes = discord.ui.TextInput(label="Inactive minutes", max_length=7)
    def __init__(self, state):
        super().__init__(); self.state = state; self.minutes.default = str(state.auto_close_minutes)
    async def on_submit(self, i):
        try: value = max(0, min(10080, int(str(self.minutes))))
        except ValueError: return await i.response.send_message("❌ Enter a number from 0 to 10080.", ephemeral=True)
        self.state.auto_close_minutes = value
        await i.response.send_message(f"✅ Auto-close set to **{value} minutes**." if value else "✅ Auto-close disabled.", ephemeral=True)


class TicketControls(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None); self.cog, self.ticket_id = cog, ticket_id
    @discord.ui.button(label="Claim", emoji="🙋", style=discord.ButtonStyle.primary, custom_id="lightcore:tickets:claim")
    async def claim(self, i, _): await self.cog.claim(i, self.ticket_id)
    @discord.ui.button(label="Priority", emoji="🚩", style=discord.ButtonStyle.secondary, custom_id="lightcore:tickets:priority")
    async def priority(self, i, _): await i.response.send_message("Choose priority:", view=PriorityView(self.cog, self.ticket_id), ephemeral=True)
    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="lightcore:tickets:close")
    async def close(self, i, _): await self.cog.close_ticket(i, self.ticket_id)


class PriorityView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=120)
        for value, emoji in PRIORITIES.items():
            b = discord.ui.Button(label=value.title(), emoji=emoji)
            b.callback = self.make(cog, ticket_id, value); self.add_item(b)
    @staticmethod
    def make(cog, ticket_id, value):
        async def callback(i): await cog.set_priority(i, ticket_id, value)
        return callback


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot; self.autoclose.start()
    def cog_unload(self): self.autoclose.cancel()

    async def cog_load(self):
        with connect() as db:
            panels = db.execute("SELECT guild_id,panel_message_id FROM ticket_systems WHERE panel_message_id IS NOT NULL AND enabled=1").fetchall()
            tickets = db.execute("SELECT id FROM ticket_instances WHERE status='open'").fetchall()
        for r in panels: self.bot.add_view(PanelView(self, r["guild_id"]), message_id=r["panel_message_id"])
        for r in tickets: self.bot.add_view(TicketControls(self, r["id"]))

    async def start_setup(self, interaction, editing=False):
        state = SetupState(interaction.guild.id, get_system(interaction.guild.id) if editing else None)
        embed = discord.Embed(title="🎫 Ticket Setup", description="Build your ticket panel step by step. **Nothing is created or published until you press ✅ Finish Setup.**\n\n" + SetupView(self, state).summary(), color=discord.Color.blurple())
        await interaction.followup.send(embed=embed, view=SetupView(self, state), ephemeral=True)

    @commands.hybrid_command(name="ticketsetup", description="Open the interactive TicketV2-style setup wizard")
    @commands.has_guild_permissions(manage_channels=True)
    async def ticketsetup(self, ctx):
        await ctx.send("🎫 Opening the interactive ticket setup wizard…", ephemeral=True)
        # The wizard owns all mutations; this command itself creates nothing.
        await self.start_setup(ctx, editing=False)

    @commands.hybrid_group(name="ticketcategory", description="Manage ticket categories")
    @commands.has_guild_permissions(manage_channels=True)
    async def ticketcategory(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `.ticketcategory list`, `.ticketcategory add`, or `.ticketcategory delete <name>`.", ephemeral=True)

    @ticketcategory.command(name="list", description="List configured ticket categories")
    async def category_list(self, ctx):
        rows = get_types(ctx.guild.id, False)
        text = "\n".join(f"{r['emoji']} **{r['name']}** • support <@&{r['support_role_id']}> • log <#{r['log_channel_id']}> • transcript <#{r['transcript_channel_id']}>" for r in rows)
        await ctx.send(text or "No ticket categories configured.", ephemeral=True)

    @ticketcategory.command(name="add", description="Open the setup flow to add a category")
    async def category_add(self, ctx):
        await self.start_setup(ctx, editing=True)

    @ticketcategory.command(name="delete", description="Delete a ticket category after confirmation")
    async def category_delete(self, ctx, *, name: str):
        row = next((r for r in get_types(ctx.guild.id, False) if r["name"].casefold() == name.casefold()), None)
        if not row: return await ctx.send("❌ Ticket category not found.", ephemeral=True)
        with connect() as db:
            open_count = db.execute("SELECT COUNT(*) c FROM ticket_instances WHERE type_id=? AND status='open'", (row["id"],)).fetchone()["c"]
        if open_count:
            return await ctx.send(f"⚠️ **{row['name']}** has **{open_count} open ticket(s)**. Close them first; the category was not deleted.", ephemeral=True)
        view = DeleteConfirm(self, ctx.guild, row)
        await ctx.send(f"⚠️ Delete **{row['name']}** from the panel and delete its organizing Discord category if LightCore created one? This cannot be undone.", view=view, ephemeral=True)

    @commands.hybrid_command(name="ticketclaim", description="Claim the current ticket")
    async def ticketclaim(self, ctx):
        row = get_ticket(ctx.channel.id)
        if not row: return await ctx.send("❌ This is not an open ticket.", ephemeral=True)
        await self.claim(ctx, row["id"])

    @commands.hybrid_command(name="ticketpriority", description="Set the current ticket priority")
    async def ticketpriority(self, ctx, priority: str):
        value = priority.casefold()
        if value not in PRIORITIES: return await ctx.send("❌ Priority must be low, normal, high, or urgent.", ephemeral=True)
        row = get_ticket(ctx.channel.id)
        if not row: return await ctx.send("❌ This is not an open ticket.", ephemeral=True)
        await self.set_priority(ctx, row["id"], value)

    @commands.hybrid_command(name="ticketclose", description="Close the current ticket")
    async def ticketclose(self, ctx):
        row = get_ticket(ctx.channel.id)
        if not row: return await ctx.send("❌ This is not an open ticket.", ephemeral=True)
        await self.close_ticket(ctx, row["id"])

    async def commit_setup(self, interaction, state):
        guild = interaction.guild
        old = get_system(guild.id)
        created_categories = []
        try:
            with connect() as db:
                db.execute("INSERT INTO ticket_systems(guild_id,panel_channel_id,auto_close_minutes,title,description,enabled) VALUES(?,?,?,?,?,1) ON CONFLICT(guild_id) DO UPDATE SET panel_channel_id=excluded.panel_channel_id,auto_close_minutes=excluded.auto_close_minutes,title=excluded.title,description=excluded.description,enabled=1", (guild.id, state.panel_channel_id, state.auto_close_minutes, state.title, state.description))
                existing = {r["id"]: r for r in db.execute("SELECT * FROM ticket_types WHERE guild_id=?", (guild.id,)).fetchall()}
                wanted = {x["id"] for x in state.types if x["id"]}
                for old_id, old_row in existing.items():
                    if old_id not in wanted:
                        db.execute("UPDATE ticket_types SET enabled=0 WHERE id=?", (old_id,))
            # Discord category creation happens only after explicit Finish Setup.
            for item in state.types:
                if item["discord_category_id"] and isinstance(guild.get_channel(item["discord_category_id"]), discord.CategoryChannel):
                    category_id = item["discord_category_id"]
                else:
                    category = await guild.create_category(name=item["name"][:100], reason="LightCore TicketV2 setup confirmation")
                    category_id = category.id; created_categories.append(category_id)
                with connect() as db:
                    if item["id"]:
                        db.execute("UPDATE ticket_types SET name=?,emoji=?,support_role_id=?,log_channel_id=?,transcript_channel_id=?,discord_category_id=?,enabled=1 WHERE id=? AND guild_id=?", (item["name"],item["emoji"],item["support_role_id"],item["log_channel_id"],item["transcript_channel_id"],category_id,item["id"],guild.id))
                    else:
                        db.execute("INSERT INTO ticket_types(guild_id,name,emoji,description,support_role_id,log_channel_id,transcript_channel_id,discord_category_id,enabled) VALUES(?,?,?,?,?,?,?,?,1)", (guild.id,item["name"],item["emoji"],item["description"],item["support_role_id"],item["log_channel_id"],item["transcript_channel_id"],category_id))
            ok, message = await self.publish_panel(guild)
            if not ok: raise RuntimeError(message)
            await interaction.response.edit_message(content="", embed=discord.Embed(title="✅ Ticket Setup Complete", description=message + "\n\nAll changes were committed only after your explicit confirmation.", color=discord.Color.green()), view=None)
        except Exception as exc:
            for cid in created_categories:
                channel = guild.get_channel(cid)
                if channel:
                    try: await channel.delete(reason="Rollback failed TicketV2 setup")
                    except discord.HTTPException: pass
            raise exc

    async def publish_panel(self, guild):
        s = get_system(guild.id); channel = guild.get_channel(s["panel_channel_id"] if s else 0)
        if not isinstance(channel, discord.TextChannel): return False, "❌ Panel target channel is missing."
        embed = discord.Embed(title=s["title"], description=s["description"], color=s["color"])
        rows = get_types(guild.id, True)
        embed.add_field(name="Ticket categories", value="\n".join(f"{r['emoji']} **{r['name']}** — {r['description']}" for r in rows[:25]) or "None", inline=False)
        view = PanelView(self, guild.id); message = None
        if s["panel_message_id"]:
            try: message = await channel.fetch_message(s["panel_message_id"])
            except discord.HTTPException: pass
        if message: await message.edit(embed=embed, view=view)
        else: message = await channel.send(embed=embed, view=view)
        with connect() as db:
            db.execute("UPDATE ticket_systems SET panel_message_id=? WHERE guild_id=?", (message.id,guild.id))
        self.bot.add_view(view, message_id=message.id)
        return True, f"Ticket panel is live in {channel.mention}."

    async def create_ticket(self, interaction, type_id):
        t = get_type(interaction.guild.id, type_id)
        if not t or not t["enabled"]: return await interaction.response.send_message("❌ Ticket category unavailable.", ephemeral=True)
        with connect() as db:
            existing = db.execute("SELECT channel_id FROM ticket_instances WHERE guild_id=? AND opener_id=? AND status='open'", (interaction.guild.id,interaction.user.id)).fetchone()
        if existing and interaction.guild.get_channel(existing["channel_id"]): return await interaction.response.send_message(f"❌ You already have <#{existing['channel_id']}> open.", ephemeral=True)
        category = interaction.guild.get_channel(t["discord_category_id"])
        role = interaction.guild.get_role(t["support_role_id"])
        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False), interaction.user: discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True,attach_files=True)}
        if role: overwrites[role] = discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True,attach_files=True)
        if interaction.guild.me: overwrites[interaction.guild.me] = discord.PermissionOverwrite(view_channel=True,send_messages=True,manage_channels=True,read_message_history=True,attach_files=True)
        channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name[:18]}", category=category if isinstance(category,discord.CategoryChannel) else None, overwrites=overwrites, topic=f"[PRIORITY: NORMAL] {t['name']}", reason="LightCore TicketV2")
        with connect() as db:
            cur=db.execute("INSERT INTO ticket_instances(guild_id,channel_id,opener_id,type_id) VALUES(?,?,?,?)",(interaction.guild.id,channel.id,interaction.user.id,type_id)); ticket_id=cur.lastrowid
            db.execute("INSERT OR IGNORE INTO ticket_participants(ticket_id,user_id) VALUES(?,?)",(ticket_id,interaction.user.id))
        embed=discord.Embed(title=f"{t['emoji']} {t['name']}",description=f"Welcome {interaction.user.mention}.\n\n**Priority:** 🔵 Normal",color=discord.Color.blurple())
        embed.set_footer(text=f"Ticket #{ticket_id} • Claim / Priority / Close")
        await channel.send(content=f"{interaction.user.mention} {role.mention if role else ''}".strip(),embed=embed,view=TicketControls(self,ticket_id)); self.bot.add_view(TicketControls(self,ticket_id))
        await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}",ephemeral=True)

    async def claim(self, interaction, ticket_id):
        row=get_ticket(interaction.channel.id)
        if not row or row["id"]!=ticket_id: return await interaction.response.send_message("❌ Ticket not found.",ephemeral=True)
        if not is_staff(interaction.user,row["support_role_id"]): return await interaction.response.send_message("❌ Support staff only.",ephemeral=True)
        if row["claimed_by"] and row["claimed_by"]!=interaction.user.id: return await interaction.response.send_message(f"❌ Already claimed by <@{row['claimed_by']}>.",ephemeral=True)
        with connect() as db: db.execute("UPDATE ticket_instances SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE id=?",(interaction.user.id,ticket_id))
        await interaction.response.send_message(f"🙋 Ticket claimed by {interaction.user.mention}.")

    async def set_priority(self, interaction, ticket_id, value):
        row=get_ticket(interaction.channel.id)
        if not row: return await interaction.response.send_message("❌ Ticket not found.",ephemeral=True)
        if not is_staff(interaction.user,row["support_role_id"]): return await interaction.response.send_message("❌ Support staff only.",ephemeral=True)
        with connect() as db: db.execute("UPDATE ticket_instances SET priority=?,last_activity=CURRENT_TIMESTAMP WHERE id=?",(value,ticket_id))
        try: await interaction.channel.edit(topic=f"[PRIORITY: {value.upper()}] {row['type_name']}")
        except discord.HTTPException: pass
        await interaction.response.send_message(f"🚩 Priority set to **{value}** {PRIORITIES[value]}.")

    async def close_ticket(self, interaction, ticket_id):
        row=get_ticket(interaction.channel.id)
        if not row: return await interaction.response.send_message("❌ Ticket not found.",ephemeral=True)
        if not is_staff(interaction.user,row["support_role_id"]) and interaction.user.id!=row["opener_id"]: return await interaction.response.send_message("❌ Only the ticket opener or support staff can close this ticket.",ephemeral=True)
        await self._close(interaction.channel,row,interaction.user,"manual")
        if not interaction.response.is_done(): await interaction.response.send_message("🔒 Ticket closed.",ephemeral=True)

    async def _close(self, channel, row, actor, reason):
        transcript=await make_transcript(channel)
        with connect() as db:
            db.execute("UPDATE ticket_instances SET status='closed',closed_at=CURRENT_TIMESTAMP,closed_by=? WHERE id=?",(actor.id,row["id"]))
            db.execute("INSERT INTO ticket_transcript_v2(ticket_id,guild_id,channel_id,closed_by,content) VALUES(?,?,?,?,?)",(row["id"],channel.guild.id,channel.id,actor.id,transcript))
        destination=channel.guild.get_channel(row["transcript_channel_id"])
        if isinstance(destination,discord.TextChannel):
            data=discord.File(io.BytesIO(transcript.encode("utf-8")),filename=f"ticket-{row['id']}.txt")
            embed=discord.Embed(title=f"📄 Ticket #{row['id']} Transcript",description=f"**Category:** {row['type_name']}\n**Closed by:** {actor.mention}\n**Reason:** {reason}",color=discord.Color.orange())
            await destination.send(embed=embed,file=data)
        log=channel.guild.get_channel(row["log_channel_id"])
        if isinstance(log,discord.TextChannel): await log.send(embed=discord.Embed(title=f"🔒 Ticket #{row['id']} Closed",description=f"**Category:** {row['type_name']}\n**Channel:** #{channel.name}\n**Closed by:** {actor.mention}\n**Reason:** {reason}",color=discord.Color.orange()))
        await channel.send(f"🔒 Ticket closed by {actor.mention}. Transcript sent to the category's configured destination.")
        await discord.utils.sleep_until(datetime.now(timezone.utc)+timedelta(seconds=3))
        try: await channel.delete(reason=f"Ticket closed: {reason}")
        except discord.HTTPException: pass

    @tasks.loop(minutes=1)
    async def autoclose(self):
        now=datetime.now(timezone.utc)
        with connect() as db: rows=db.execute("SELECT id,channel_id,guild_id,type_id,last_activity FROM ticket_instances WHERE status='open'").fetchall()
        for r in rows:
            s=get_system(r["guild_id"])
            if not s or not s["auto_close_minutes"]: continue
            try: last=datetime.fromisoformat(r["last_activity"].replace(" ","T").replace("+00:00","" )).replace(tzinfo=timezone.utc)
            except ValueError: continue
            if (now-last).total_seconds() < s["auto_close_minutes"]*60: continue
            channel=self.bot.get_channel(r["channel_id"]); row=get_ticket(r["channel_id"])
            if channel and row: await self._close(channel,row,self.bot.user,"auto-close inactivity")

    @autoclose.before_loop
    async def before_autoclose(self): await self.bot.wait_until_ready()


class DeleteConfirm(discord.ui.View):
    def __init__(self,cog,guild,row):
        super().__init__(timeout=60); self.cog,self.guild,self.row=cog,guild,row
    @discord.ui.button(label="Yes, delete",emoji="✅",style=discord.ButtonStyle.danger)
    async def yes(self,i,_):
        with connect() as db: db.execute("UPDATE ticket_types SET enabled=0 WHERE id=? AND guild_id=?",(self.row["id"],self.guild.id))
        category=self.guild.get_channel(self.row["discord_category_id"])
        if isinstance(category,discord.CategoryChannel):
            try: await category.delete(reason="Ticket category deleted by administrator")
            except discord.HTTPException: pass
        await self.cog.publish_panel(self.guild)
        await i.response.edit_message(content=f"✅ **{self.row['name']}** was deleted from the ticket panel and its organizing Discord category was removed.",view=None)
    @discord.ui.button(label="No",style=discord.ButtonStyle.secondary)
    async def no(self,i,_): await i.response.edit_message(content="❌ Category deletion cancelled.",view=None)


async def setup(bot): await bot.add_cog(TicketCog(bot))
