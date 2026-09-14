import json
import re

import discord
from discord.ext import commands

from database import connect, get_setting, set_setting


def default_config():
    return {
        "title": "LightCore Support",
        "description": "Choose a support category below to open a private ticket.",
        "color": 0x5865F2,
        "panel_channel_id": None,
        "claim_required": False,
        "categories": [
            {"name": "General Support", "emoji": "🎫", "role_id": None, "category_id": None},
            {"name": "Report a User", "emoji": "🚨", "role_id": None, "category_id": None},
            {"name": "Billing", "emoji": "💳", "role_id": None, "category_id": None},
        ],
    }


def load_config(guild_id):
    raw = get_setting(guild_id, "ticket_config")
    if not raw:
        return default_config()
    try:
        config = default_config()
        config.update(json.loads(raw))
        config["categories"] = config.get("categories") or default_config()["categories"]
        return config
    except (TypeError, ValueError, json.JSONDecodeError):
        return default_config()


def save_config(guild_id, config):
    set_setting(guild_id, "ticket_config", json.dumps(config, separators=(",", ":")))


def color_value(value):
    value = value.strip().replace("#", "")
    if len(value) != 6:
        raise ValueError("Color must be a 6-digit hex value such as #5865F2.")
    return int(value, 16)


class TicketClaimView(discord.ui.View):
    def __init__(self, guild_id, ticket_id, role_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.ticket_id = ticket_id
        self.role_id = role_id
        button = discord.ui.Button(label="Claim Ticket", emoji="🙋", style=discord.ButtonStyle.primary, custom_id=f"lightcore:ticket:claim:{ticket_id}")
        button.callback = self.claim
        self.add_item(button)

    async def claim(self, interaction):
        guild = interaction.guild
        if not guild:
            return await interaction.response.send_message("This button can only be used in a server.", ephemeral=True)
        if self.role_id and not any(role.id == self.role_id for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You need the configured support role to claim this ticket.", ephemeral=True)
        with connect() as db:
            row = db.execute("SELECT claimed_by FROM ticket_meta WHERE ticket_id=?", (self.ticket_id,)).fetchone()
            if not row:
                db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (self.ticket_id,))
                claimed_by = None
            else:
                claimed_by = row["claimed_by"]
            if claimed_by:
                return await interaction.response.send_message(f"❌ This ticket is already claimed by <@{claimed_by}>.", ephemeral=True)
            db.execute("UPDATE ticket_meta SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?", (interaction.user.id, self.ticket_id))
        await interaction.response.edit_message(content=f"🙋 Ticket claimed by {interaction.user.mention}.", view=self)


class TicketCategoryView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        config = load_config(guild_id)
        options = []
        for index, item in enumerate(config["categories"][:25]):
            options.append(discord.SelectOption(label=item["name"][:100], value=str(index), emoji=item.get("emoji") or "🎫", description="Open a ticket in this category."))
        if not options:
            options = [discord.SelectOption(label="No categories configured", value="none", description="Ask a server manager to run .ticketsetup")]
        select = discord.ui.Select(placeholder="Choose a ticket category…", options=options, custom_id=f"lightcore:ticket:categories:{guild_id}")
        select.callback = self.create_ticket
        self.add_item(select)

    async def create_ticket(self, interaction):
        if interaction.data.get("values", ["none"])[0] == "none":
            return await interaction.response.send_message("❌ No ticket categories are configured yet.", ephemeral=True)
        index = int(interaction.data["values"][0])
        config = load_config(interaction.guild.id)
        try:
            item = config["categories"][index]
        except IndexError:
            return await interaction.response.send_message("❌ That ticket category no longer exists. Re-publish the panel.", ephemeral=True)

        with connect() as db:
            row = db.execute("SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status='open'", (interaction.guild.id, interaction.user.id)).fetchone()
        if row:
            existing = interaction.guild.get_channel(row["channel_id"])
            if existing:
                return await interaction.response.send_message(f"You already have an open ticket: {existing.mention}", ephemeral=True)

        parent = interaction.guild.get_channel(item.get("category_id")) if item.get("category_id") else None
        if parent and not isinstance(parent, discord.CategoryChannel):
            parent = None
        support_role = interaction.guild.get_role(item.get("role_id")) if item.get("role_id") else None
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        safe = re.sub(r"[^a-z0-9-]+", "-", item["name"].lower()).strip("-")[:30] or "support"
        username = re.sub(r"[^a-z0-9-]+", "-", interaction.user.name.lower()).strip("-")[:20] or "user"
        channel = await interaction.guild.create_text_channel(f"{safe}-{username}", category=parent, overwrites=overwrites, reason=f"LightCore ticket: {item['name']}")
        with connect() as db:
            cur = db.execute("INSERT INTO tickets(guild_id,channel_id,user_id,status) VALUES(?,?,?,'open')", (interaction.guild.id, channel.id, interaction.user.id))
            ticket_id = cur.lastrowid
            db.execute("INSERT OR REPLACE INTO ticket_meta(ticket_id,category) VALUES(?,?)", (ticket_id, item["name"]))

        ping = support_role.mention if support_role else "Support team"
        embed = discord.Embed(title=f"🎫 {item['name']}", description=f"Welcome {interaction.user.mention}!\n{ping}, a new ticket has been opened.", color=discord.Color(config["color"]))
        embed.add_field(name="Ticket", value=f"`#{ticket_id}`", inline=True)
        embed.add_field(name="Category", value=item["name"], inline=True)
        if config.get("claim_required"):
            await channel.send(embed=embed, view=TicketClaimView(interaction.guild.id, ticket_id, item.get("role_id")))
        else:
            await channel.send(embed=embed)
        await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)


class TicketEditor(commands.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.message = None
        self.selected_category = 0
        self.rebuild()

    def config(self):
        return load_config(self.guild_id)

    def embed(self):
        cfg = self.config()
        channel = self.cog.bot.get_channel(cfg.get("panel_channel_id")) if cfg.get("panel_channel_id") else None
        desc = (cfg.get("description") or "").strip()[:4096]
        embed = discord.Embed(title=f"🎫 Ticket Setup • {cfg.get('title') or 'Untitled'}", description=desc or "No description set.", color=discord.Color(cfg.get("color", 0x5865F2)))
        embed.add_field(name="Panel channel", value=channel.mention if channel else "Not selected", inline=True)
        embed.add_field(name="Claim required", value="Yes" if cfg.get("claim_required") else "No", inline=True)
        lines = []
        for i, item in enumerate(cfg.get("categories", [])[:25], 1):
            role = f"<@&{item['role_id']}>" if item.get("role_id") else "No support role"
            parent = f"<#{item['category_id']}>" if item.get("category_id") else "No parent category"
            lines.append(f"**{i}.** {item.get('emoji','🎫')} {item.get('name','Unnamed')} • {role} • {parent}")
        embed.add_field(name="Categories", value="\n".join(lines) or "No categories", inline=False)
        embed.set_footer(text="Changes are saved immediately. Publish Panel posts the current configuration.")
        return embed

    def rebuild(self):
        self.clear_items()
        buttons = [
            ("Panel Text", "📝", "text", discord.ButtonStyle.primary),
            ("Color", "🎨", "color", discord.ButtonStyle.secondary),
            ("Panel Channel", "📍", "channel", discord.ButtonStyle.secondary),
            ("Claim", "🙋", "claim", discord.ButtonStyle.primary),
            ("Categories", "🗂️", "categories", discord.ButtonStyle.secondary),
            ("Publish Panel", "📢", "publish", discord.ButtonStyle.success),
        ]
        for i, (label, emoji, action, style) in enumerate(buttons):
            button = discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"lightcore:ticketsetup:{self.guild_id}:{action}", row=i // 4)
            button.callback = self.callback(action)
            self.add_item(button)

    async def interaction_check(self, interaction):
        return interaction.user.guild_permissions.manage_channels

    def callback(self, action):
        async def inner(interaction):
            if action == "text":
                return await interaction.response.send_modal(TicketTextModal(self))
            if action == "color":
                return await interaction.response.send_modal(TicketColorModal(self))
            if action == "channel":
                return await interaction.response.send_message("Use the channel selector below to choose where the final panel should be posted.", view=PanelChannelView(self), ephemeral=True)
            if action == "claim":
                cfg = self.config(); cfg["claim_required"] = not cfg.get("claim_required", False); save_config(self.guild_id, cfg)
                return await interaction.response.edit_message(embed=self.embed(), view=self)
            if action == "categories":
                return await interaction.response.edit_message(embed=CategoryManagerView(self).embed(), view=CategoryManagerView(self))
            if action == "publish":
                return await self.cog.publish_panel(interaction, self.guild_id)
        return inner

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class TicketTextModal(discord.ui.Modal, title="Edit Ticket Panel Text"):
    title_input = discord.ui.TextInput(label="Panel title", max_length=256)
    description_input = discord.ui.TextInput(label="Panel description", style=discord.TextStyle.paragraph, max_length=4000)

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        cfg = editor.config()
        self.title_input.default = cfg.get("title", "")
        self.description_input.default = cfg.get("description", "")

    async def on_submit(self, interaction):
        cfg = self.editor.config(); cfg["title"] = str(self.title_input); cfg["description"] = str(self.description_input); save_config(self.editor.guild_id, cfg)
        await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)


class TicketColorModal(discord.ui.Modal, title="Edit Ticket Panel Color"):
    color = discord.ui.TextInput(label="Hex color", placeholder="#5865F2", max_length=7)

    def __init__(self, editor):
        super().__init__(); self.editor = editor; self.color.default = f"#{editor.config().get('color', 0x5865F2):06X}"

    async def on_submit(self, interaction):
        try:
            value = color_value(str(self.color))
        except ValueError as exc:
            return await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        cfg = self.editor.config(); cfg["color"] = value; save_config(self.editor.guild_id, cfg)
        await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)


class PanelChannelView(discord.ui.View):
    def __init__(self, editor):
        super().__init__(timeout=120); self.editor = editor
        select = discord.ui.ChannelSelect(channel_types=[discord.ChannelType.text], placeholder="Choose the ticket panel channel…")
        select.callback = self.select
        self.add_item(select)

    async def select(self, interaction):
        channel = interaction.data.get("values", [None])[0]
        cfg = self.editor.config(); cfg["panel_channel_id"] = int(channel); save_config(self.editor.guild_id, cfg)
        await interaction.response.send_message("✅ Panel channel saved. Return to `.ticketsetup` to publish it.", ephemeral=True)


class CategoryManagerView(discord.ui.View):
    def __init__(self, editor):
        super().__init__(timeout=300); self.editor = editor
        self.rebuild()

    def config(self): return self.editor.config()

    def embed(self):
        cfg = self.config(); embed = discord.Embed(title="🗂️ Ticket Categories", description="Select a category to edit, or add a new one. Each category has its own emoji, support role and Discord category channel.", color=discord.Color(cfg.get("color", 0x5865F2)))
        lines = [f"**{i}.** {x.get('emoji','🎫')} {x.get('name','Unnamed')} • role: {f'<@&{x[\"role_id\"]}>' if x.get('role_id') else 'none'} • parent: {f'<#{x[\"category_id\"]}>' if x.get('category_id') else 'none'}" for i, x in enumerate(cfg.get("categories", []), 1)]
        embed.add_field(name="Configured", value="\n".join(lines) or "None", inline=False)
        return embed

    def rebuild(self):
        self.clear_items(); cfg = self.config(); options = [discord.SelectOption(label=x["name"][:100], value=str(i), emoji=x.get("emoji") or "🎫") for i, x in enumerate(cfg.get("categories", [])[:25])]
        if options:
            select = discord.ui.Select(placeholder="Select a category to edit…", options=options, custom_id=f"lightcore:ticketsetup:catselect:{self.editor.guild_id}")
            select.callback = self.select
            self.add_item(select)
        for label, emoji, action, style in [("Add", "➕", "add", discord.ButtonStyle.success), ("Remove", "➖", "remove", discord.ButtonStyle.danger), ("Rename", "✏️", "rename", discord.ButtonStyle.primary), ("Back", "↩️", "back", discord.ButtonStyle.secondary)]:
            button = discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"lightcore:ticketsetup:cat:{self.editor.guild_id}:{action}")
            button.callback = self.action(action); self.add_item(button)

    async def select(self, interaction):
        self.editor.selected_category = int(interaction.data["values"][0]); await interaction.response.edit_message(embed=self.embed(), view=self)

    def action(self, action):
        async def inner(interaction):
            if action == "back":
                self.editor.rebuild(); return await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)
            if action == "add":
                return await interaction.response.send_modal(CategoryModal(self.editor, None))
            index = getattr(self.editor, "selected_category", 0); cfg = self.config()
            if index >= len(cfg.get("categories", [])):
                return await interaction.response.send_message("❌ Select a valid category first.", ephemeral=True)
            if action == "remove":
                cfg["categories"].pop(index); save_config(self.editor.guild_id, cfg); self.rebuild(); return await interaction.response.edit_message(embed=self.embed(), view=self)
            if action == "rename":
                return await interaction.response.send_modal(RenameCategoryModal(self.editor, index))
        return inner


class CategoryModal(discord.ui.Modal, title="Add Ticket Category"):
    name = discord.ui.TextInput(label="Category name", placeholder="General Support", max_length=80)
    emoji = discord.ui.TextInput(label="Emoji", placeholder="🎫", max_length=8, required=False)
    support_role_id = discord.ui.TextInput(label="Support role ID (optional)", required=False, max_length=25)
    parent_category_id = discord.ui.TextInput(label="Discord category channel ID (optional)", required=False, max_length=25)

    def __init__(self, editor, index):
        super().__init__(); self.editor = editor; self.index = index

    async def on_submit(self, interaction):
        try:
            role_id = int(str(self.support_role_id)) if str(self.support_role_id).strip() else None
            parent_id = int(str(self.parent_category_id)) if str(self.parent_category_id).strip() else None
        except ValueError:
            return await interaction.response.send_message("❌ Role/category IDs must be numbers.", ephemeral=True)
        cfg = self.editor.config(); item = {"name": str(self.name).strip(), "emoji": str(self.emoji).strip() or "🎫", "role_id": role_id, "category_id": parent_id}
        if self.index is None: cfg["categories"].append(item)
        else: cfg["categories"][self.index] = item
        if len(cfg["categories"]) > 25:
            cfg["categories"] = cfg["categories"][:25]
        save_config(self.editor.guild_id, cfg)
        await interaction.response.send_message("✅ Category saved. Open `.ticketsetup` again to continue editing.", ephemeral=True)


class RenameCategoryModal(discord.ui.Modal, title="Rename Ticket Category"):
    name = discord.ui.TextInput(label="New category name", max_length=80)

    def __init__(self, editor, index):
        super().__init__(); self.editor = editor; self.index = index; self.name.default = editor.config()["categories"][index]["name"]

    async def on_submit(self, interaction):
        cfg = self.editor.config(); cfg["categories"][self.index]["name"] = str(self.name).strip(); save_config(self.editor.guild_id, cfg)
        await interaction.response.send_message("✅ Category renamed.", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.bot.add_view(TicketCategoryView(self, guild.id))

    async def publish_panel(self, interaction, guild_id):
        cfg = load_config(guild_id); channel = self.bot.get_channel(cfg.get("panel_channel_id")) if cfg.get("panel_channel_id") else None
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("❌ Choose a text channel first with **Panel Channel**.", ephemeral=True)
        if not cfg.get("categories"):
            return await interaction.response.send_message("❌ Add at least one ticket category first.", ephemeral=True)
        embed = discord.Embed(title=cfg.get("title") or "Support", description=cfg.get("description") or "Choose a ticket category.", color=discord.Color(cfg.get("color", 0x5865F2)))
        embed.set_footer(text="LightCore • Ticket Support")
        message = await channel.send(embed=embed, view=TicketCategoryView(self, guild_id))
        cfg["published_message_id"] = message.id; save_config(guild_id, cfg)
        await interaction.response.send_message(f"✅ Ticket panel published in {channel.mention}. You can re-run `.ticketsetup` and publish an updated panel later.", ephemeral=True)

    @commands.hybrid_command(name="ticketsetup", description="Open the interactive ticket setup editor.")
    @commands.has_permissions(manage_channels=True)
    async def ticketsetup(self, ctx):
        editor = TicketEditor(self, ctx.guild.id)
        editor.message = await ctx.send(embed=editor.embed(), view=editor)

    @commands.hybrid_command(name="ticketpanel", description="Publish the current configured ticket panel.")
    @commands.has_permissions(manage_channels=True)
    async def ticketpanel(self, ctx):
        await self.publish_panel(ctx, ctx.guild.id)

    @commands.hybrid_command(name="setticketcategory", description="Set the legacy default ticket category channel.")
    @commands.has_permissions(manage_guild=True)
    async def setticketcategory(self, ctx, category: discord.CategoryChannel):
        set_setting(ctx.guild.id, "ticket_category", category.id)
        await ctx.send(f"Ticket default category set to **{category.name}**.")

    @commands.hybrid_command(name="setticketlog", description="Set the ticket transcript log channel.")
    @commands.has_permissions(manage_guild=True)
    async def setticketlog(self, ctx, channel: discord.TextChannel):
        set_setting(ctx.guild.id, "ticket_log_channel", channel.id)
        await ctx.send(f"Ticket transcript channel set to {channel.mention}.")

    @commands.hybrid_command(name="close", description="Close the current LightCore ticket and save its transcript.")
    async def close(self, ctx):
        with connect() as db:
            row = db.execute("SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'", (ctx.guild.id, ctx.channel.id)).fetchone()
        if not row:
            return await ctx.send("This is not an open LightCore ticket channel.")
        lines = []
        try:
            async for message in ctx.channel.history(limit=500, oldest_first=True):
                stamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                content = message.content.replace("\n", " ")
                lines.append(f"[{stamp}] {message.author} ({message.author.id}): {content}")
        except discord.HTTPException:
            pass
        transcript = "\n".join(lines) or "No messages captured."
        with connect() as db:
            db.execute("UPDATE tickets SET status='closed', closed_at=CURRENT_TIMESTAMP WHERE id=?", (row["id"],))
            db.execute("INSERT INTO ticket_transcripts(ticket_id,transcript) VALUES(?,?)", (row["id"], transcript[:50000]))
        log_id = get_setting(ctx.guild.id, "ticket_log_channel")
        log_channel = ctx.guild.get_channel(log_id) if log_id else None
        if log_channel:
            await log_channel.send(embed=discord.Embed(title=f"LightCore Ticket #{row['id']} Closed", description=f"```text\n{transcript[:3800]}\n```", color=discord.Color.blurple()))
        await ctx.send("Closing ticket and saving its transcript…")
        await ctx.channel.delete(reason=f"LightCore ticket closed by {ctx.author}")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
