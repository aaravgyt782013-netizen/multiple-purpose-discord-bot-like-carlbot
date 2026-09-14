import json
import re

import discord
from discord.ext import commands

from database import connect, get_setting, set_setting


DEFAULT_TICKET_CATEGORIES = [
    {"name": "General Support", "emoji": "🎫", "role_id": None, "category_id": None},
    {"name": "Report a User", "emoji": "🚨", "role_id": None, "category_id": None},
    {"name": "Billing", "emoji": "💳", "role_id": None, "category_id": None},
]


def default_config():
    return {
        "title": "LightCore Support",
        "description": "Choose a support category below to open a private ticket.",
        "color": 0x5865F2,
        "panel_channel_id": None,
        "published_message_id": None,
        "claim_required": False,
        "categories": [dict(item) for item in DEFAULT_TICKET_CATEGORIES],
    }


def load_config(guild_id):
    raw = get_setting(guild_id, "ticket_config")
    if not raw:
        return default_config()
    try:
        saved = json.loads(raw)
        config = default_config()
        if isinstance(saved, dict):
            config.update(saved)
        categories = config.get("categories")
        if not isinstance(categories, list):
            categories = [dict(item) for item in DEFAULT_TICKET_CATEGORIES]
        clean = []
        for item in categories[:25]:
            if not isinstance(item, dict):
                continue
            clean.append(
                {
                    "name": str(item.get("name") or "General Support")[:80],
                    "emoji": str(item.get("emoji") or "🎫")[:8],
                    "role_id": int(item["role_id"]) if item.get("role_id") else None,
                    "category_id": int(item["category_id"]) if item.get("category_id") else None,
                }
            )
        config["categories"] = clean
        return config
    except (TypeError, ValueError, json.JSONDecodeError):
        return default_config()


def save_config(guild_id, config):
    set_setting(guild_id, "ticket_config", json.dumps(config, separators=(",", ":")))


def color_value(value):
    value = value.strip().replace("#", "")
    if len(value) != 6:
        raise ValueError("Color must be a 6-digit hex value such as #5865F2.")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise ValueError("Color must be a valid 6-digit hexadecimal value.") from exc


def clean_channel_name(value, fallback="support"):
    value = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:30]
    return value or fallback


class TicketClaimView(discord.ui.View):
    def __init__(self, guild_id, ticket_id, role_id):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.role_id = role_id
        button = discord.ui.Button(
            label="Claim Ticket",
            emoji="🙋",
            style=discord.ButtonStyle.primary,
            custom_id=f"lightcore:ticket:claim:{ticket_id}",
        )
        button.callback = self.claim
        self.add_item(button)

    async def claim(self, interaction):
        if not interaction.guild:
            return await interaction.response.send_message("This button can only be used in a server.", ephemeral=True)
        if self.role_id and not any(role.id == self.role_id for role in interaction.user.roles):
            return await interaction.response.send_message("❌ You need the configured support role to claim this ticket.", ephemeral=True)
        with connect() as db:
            row = db.execute("SELECT claimed_by FROM ticket_meta WHERE ticket_id=?", (self.ticket_id,)).fetchone()
            claimed_by = row["claimed_by"] if row else None
            if not row:
                db.execute("INSERT OR IGNORE INTO ticket_meta(ticket_id) VALUES(?)", (self.ticket_id,))
            if claimed_by:
                return await interaction.response.send_message(f"❌ This ticket is already claimed by <@{claimed_by}>.", ephemeral=True)
            db.execute(
                "UPDATE ticket_meta SET claimed_by=?,last_activity=CURRENT_TIMESTAMP WHERE ticket_id=?",
                (interaction.user.id, self.ticket_id),
            )
        await interaction.response.edit_message(content=f"🙋 Ticket claimed by {interaction.user.mention}.", view=self)


class TicketPanelView(discord.ui.View):
    """Persistent live ticket panel. The dropdown is rebuilt from saved config."""

    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        config = load_config(guild_id)
        options = [
            discord.SelectOption(
                label=item["name"][:100],
                value=str(index),
                emoji=item.get("emoji") or "🎫",
                description="Open a ticket in this category.",
            )
            for index, item in enumerate(config.get("categories", [])[:25])
        ]
        if not options:
            options = [
                discord.SelectOption(
                    label="No categories configured",
                    value="none",
                    description="Ask a server manager to run .ticketsetup",
                )
            ]
        select = discord.ui.Select(
            placeholder="Choose a ticket category…",
            options=options,
            custom_id=f"lightcore:ticket:categories:{guild_id}",
            row=0,
        )
        select.callback = self.create_ticket
        self.add_item(select)
        edit = discord.ui.Button(
            label="Edit",
            emoji="✏️",
            style=discord.ButtonStyle.secondary,
            custom_id=f"lightcore:ticket:edit:{guild_id}",
            row=1,
        )
        edit.callback = self.edit_panel
        self.add_item(edit)

    async def edit_panel(self, interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ You need Manage Channels to edit this panel.", ephemeral=True)
        editor = TicketEditor(self.cog, self.guild_id)
        await interaction.response.send_message(embed=editor.embed(), view=editor, ephemeral=True)
        editor.message = await interaction.original_response()

    async def create_ticket(self, interaction):
        value = interaction.data.get("values", ["none"])[0]
        if value == "none":
            return await interaction.response.send_message("❌ No ticket categories are configured yet.", ephemeral=True)
        try:
            index = int(value)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid ticket category.", ephemeral=True)
        config = load_config(interaction.guild.id)
        if index >= len(config["categories"]):
            return await interaction.response.send_message("❌ That category no longer exists. The live panel may need a refresh.", ephemeral=True)
        item = config["categories"][index]

        with connect() as db:
            row = db.execute(
                "SELECT channel_id FROM tickets WHERE guild_id=? AND user_id=? AND status='open'",
                (interaction.guild.id, interaction.user.id),
            ).fetchone()
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

        safe = clean_channel_name(item["name"], "support")
        username = clean_channel_name(interaction.user.name, "user")[:20]
        channel = await interaction.guild.create_text_channel(
            f"{safe}-{username}",
            category=parent,
            overwrites=overwrites,
            reason=f"LightCore ticket: {item['name']}",
        )
        with connect() as db:
            cur = db.execute(
                "INSERT INTO tickets(guild_id,channel_id,user_id,status) VALUES(?,?,?,'open')",
                (interaction.guild.id, channel.id, interaction.user.id),
            )
            ticket_id = cur.lastrowid
            db.execute(
                "INSERT OR REPLACE INTO ticket_meta(ticket_id,category) VALUES(?,?)",
                (ticket_id, item["name"]),
            )

        ping = support_role.mention if support_role else "Support team"
        embed = discord.Embed(
            title=f"🎫 {item['name']}",
            description=f"Welcome {interaction.user.mention}!\n{ping}, a new ticket has been opened.",
            color=discord.Color(config["color"]),
        )
        embed.add_field(name="Ticket", value=f"`#{ticket_id}`", inline=True)
        embed.add_field(name="Category", value=item["name"], inline=True)
        if config.get("claim_required"):
            await channel.send(
                embed=embed,
                view=TicketClaimView(interaction.guild.id, ticket_id, item.get("role_id")),
            )
        else:
            await channel.send(embed=embed)
        await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)


class TicketEditor(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=600)
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
        published = bool(cfg.get("published_message_id"))
        embed = discord.Embed(
            title=f"🎫 Ticket Setup • {cfg.get('title') or 'Untitled'}",
            description=(cfg.get("description") or "No description set.")[:4096],
            color=discord.Color(cfg.get("color", 0x5865F2)),
        )
        embed.add_field(name="Panel channel", value=channel.mention if channel else "Not selected", inline=True)
        embed.add_field(name="Claim required", value="Yes" if cfg.get("claim_required") else "No", inline=True)
        embed.add_field(name="Published", value="Yes" if published else "No", inline=True)
        lines = []
        for i, item in enumerate(cfg.get("categories", [])[:25], 1):
            role_text = f"<@&{item['role_id']}>" if item.get("role_id") else "No support role"
            parent_text = f"<#{item['category_id']}>" if item.get("category_id") else "No parent category"
            lines.append(f"**{i}.** {item.get('emoji','🎫')} {item.get('name','Unnamed')} • {role_text} • {parent_text}")
        embed.add_field(name="Categories", value="\n".join(lines) or "No categories", inline=False)
        embed.set_footer(text="Edits are saved to the existing configuration. Published content/categories are synced in place.")
        return embed

    def rebuild(self):
        self.clear_items()
        buttons = [
            ("Panel Text", "📝", "text", discord.ButtonStyle.primary),
            ("Color", "🎨", "color", discord.ButtonStyle.secondary),
            ("Panel Channel", "📍", "channel", discord.ButtonStyle.secondary),
            ("Claim", "🙋", "claim", discord.ButtonStyle.primary),
            ("Categories", "🗂️", "categories", discord.ButtonStyle.secondary),
            ("Sync Live Panel", "🔄", "sync", discord.ButtonStyle.success),
            ("Publish", "📢", "publish", discord.ButtonStyle.success),
        ]
        for i, (label, emoji, action, style) in enumerate(buttons):
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=style,
                custom_id=f"lightcore:ticketsetup:{self.guild_id}:{action}",
                row=i // 4,
            )
            button.callback = self.callback(action)
            self.add_item(button)

    async def interaction_check(self, interaction):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need Manage Channels to edit ticket setup.", ephemeral=True)
            return False
        return True

    def callback(self, action):
        async def inner(interaction):
            if action == "text":
                return await interaction.response.send_modal(TicketTextModal(self))
            if action == "color":
                return await interaction.response.send_modal(TicketColorModal(self))
            if action == "channel":
                return await interaction.response.send_message(
                    "Choose the channel where the ticket panel is configured to live.",
                    view=PanelChannelView(self),
                    ephemeral=True,
                )
            if action == "claim":
                cfg = self.config()
                cfg["claim_required"] = not cfg.get("claim_required", False)
                save_config(self.guild_id, cfg)
                await self.cog.sync_published_panel(self.guild_id)
                return await interaction.response.edit_message(embed=self.embed(), view=self)
            if action == "categories":
                manager = CategoryManagerView(self)
                return await interaction.response.edit_message(embed=manager.embed(), view=manager)
            if action == "sync":
                ok, message = await self.cog.sync_published_panel(self.guild_id)
                return await interaction.response.send_message(message, ephemeral=True)
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
        cfg = self.editor.config()
        cfg["title"] = str(self.title_input).strip() or "LightCore Support"
        cfg["description"] = str(self.description_input).strip() or "Choose a support category below to open a private ticket."
        save_config(self.editor.guild_id, cfg)
        await self.editor.cog.sync_published_panel(self.editor.guild_id)
        await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)


class TicketColorModal(discord.ui.Modal, title="Edit Ticket Panel Color"):
    color = discord.ui.TextInput(label="Hex color", placeholder="#5865F2", max_length=7)

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.color.default = f"#{editor.config().get('color', 0x5865F2):06X}"

    async def on_submit(self, interaction):
        try:
            value = color_value(str(self.color))
        except ValueError as exc:
            return await interaction.response.send_message(f"❌ {exc}", ephemeral=True)
        cfg = self.editor.config()
        cfg["color"] = value
        save_config(self.editor.guild_id, cfg)
        await self.editor.cog.sync_published_panel(self.editor.guild_id)
        await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)


class PanelChannelView(discord.ui.View):
    def __init__(self, editor):
        super().__init__(timeout=120)
        self.editor = editor
        select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Choose the ticket panel channel…",
        )
        select.callback = self.select
        self.add_item(select)

    async def select(self, interaction):
        channel_id = interaction.data.get("values", [None])[0]
        if not channel_id:
            return await interaction.response.send_message("❌ No channel selected.", ephemeral=True)
        cfg = self.editor.config()
        old_channel_id = cfg.get("panel_channel_id")
        cfg["panel_channel_id"] = int(channel_id)
        save_config(self.editor.guild_id, cfg)
        if cfg.get("published_message_id") and old_channel_id and old_channel_id != int(channel_id):
            await interaction.response.send_message(
                "⚠️ The panel channel is saved for future publishing. Discord cannot move an existing message between channels, so the current live panel remains in its original channel.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("✅ Panel channel saved.", ephemeral=True)


class CategoryManagerView(discord.ui.View):
    def __init__(self, editor):
        super().__init__(timeout=300)
        self.editor = editor
        self.rebuild()

    def config(self):
        return self.editor.config()

    def embed(self):
        cfg = self.config()
        embed = discord.Embed(
            title="🗂️ Ticket Categories",
            description="Add, edit, rename or remove categories. Changes automatically update the published dropdown without touching existing tickets.",
            color=discord.Color(cfg.get("color", 0x5865F2)),
        )
        lines = []
        for i, item in enumerate(cfg.get("categories", []), 1):
            role_text = f"<@&{item['role_id']}>" if item.get("role_id") else "none"
            parent_text = f"<#{item['category_id']}>" if item.get("category_id") else "none"
            lines.append(f"**{i}.** {item.get('emoji','🎫')} {item.get('name','Unnamed')} • role: {role_text} • parent: {parent_text}")
        embed.add_field(name="Configured", value="\n".join(lines) or "None", inline=False)
        return embed

    def rebuild(self):
        self.clear_items()
        cfg = self.config()
        options = [
            discord.SelectOption(label=x["name"][:100], value=str(i), emoji=x.get("emoji") or "🎫")
            for i, x in enumerate(cfg.get("categories", [])[:25])
        ]
        if options:
            select = discord.ui.Select(
                placeholder="Select a category to edit…",
                options=options,
                custom_id=f"lightcore:ticketsetup:catselect:{self.editor.guild_id}",
            )
            select.callback = self.select
            self.add_item(select)
        for label, emoji, action, style in [
            ("Add", "➕", "add", discord.ButtonStyle.success),
            ("Edit", "✏️", "edit", discord.ButtonStyle.primary),
            ("Remove", "➖", "remove", discord.ButtonStyle.danger),
            ("Back", "↩️", "back", discord.ButtonStyle.secondary),
        ]:
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=style,
                custom_id=f"lightcore:ticketsetup:cat:{self.editor.guild_id}:{action}",
            )
            button.callback = self.action(action)
            self.add_item(button)

    async def select(self, interaction):
        try:
            self.editor.selected_category = int(interaction.data["values"][0])
        except (KeyError, ValueError):
            return await interaction.response.send_message("❌ Invalid category.", ephemeral=True)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    def action(self, action):
        async def inner(interaction):
            if action == "back":
                self.editor.rebuild()
                return await interaction.response.edit_message(embed=self.editor.embed(), view=self.editor)
            if action == "add":
                return await interaction.response.send_modal(CategoryModal(self.editor))
            cfg = self.config()
            index = getattr(self.editor, "selected_category", 0)
            if index >= len(cfg.get("categories", [])):
                return await interaction.response.send_message("❌ Select a valid category first.", ephemeral=True)
            if action == "remove":
                cfg["categories"].pop(index)
                save_config(self.editor.guild_id, cfg)
                await self.editor.cog.sync_published_panel(self.editor.guild_id)
                self.editor.selected_category = max(0, min(index, len(cfg["categories"]) - 1))
                self.rebuild()
                return await interaction.response.edit_message(embed=self.embed(), view=self)
            if action == "edit":
                return await interaction.response.send_modal(CategoryModal(self.editor, index=index))

        return inner


class CategoryModal(discord.ui.Modal, title="Edit Ticket Category"):
    name = discord.ui.TextInput(label="Category name", placeholder="General Support", max_length=80)
    emoji = discord.ui.TextInput(label="Emoji", placeholder="🎫", max_length=8, required=False)
    support_role_id = discord.ui.TextInput(label="Support role ID (optional)", required=False, max_length=25)
    parent_category_id = discord.ui.TextInput(label="Discord category channel ID (optional)", required=False, max_length=25)

    def __init__(self, editor, index=None):
        super().__init__()
        self.editor = editor
        self.index = index
        if index is not None:
            item = editor.config()["categories"][index]
            self.name.default = item.get("name", "")
            self.emoji.default = item.get("emoji", "🎫")
            self.support_role_id.default = str(item.get("role_id") or "")
            self.parent_category_id.default = str(item.get("category_id") or "")

    async def on_submit(self, interaction):
        try:
            role_id = int(str(self.support_role_id).strip()) if str(self.support_role_id).strip() else None
            parent_id = int(str(self.parent_category_id).strip()) if str(self.parent_category_id).strip() else None
        except ValueError:
            return await interaction.response.send_message("❌ Role/category IDs must be numbers.", ephemeral=True)
        cfg = self.editor.config()
        item = {
            "name": str(self.name).strip()[:80] or "Support",
            "emoji": str(self.emoji).strip()[:8] or "🎫",
            "role_id": role_id,
            "category_id": parent_id,
        }
        if self.index is None:
            if len(cfg["categories"]) >= 25:
                return await interaction.response.send_message("❌ Discord allows at most 25 dropdown options.", ephemeral=True)
            cfg["categories"].append(item)
        else:
            cfg["categories"][self.index] = item
        save_config(self.editor.guild_id, cfg)
        await self.editor.cog.sync_published_panel(self.editor.guild_id)
        manager = CategoryManagerView(self.editor)
        await interaction.response.edit_message(embed=manager.embed(), view=manager)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.bot.add_view(TicketPanelView(self, guild.id))
            with connect() as db:
                rows = db.execute(
                    "SELECT id FROM tickets WHERE guild_id=? AND status='open'",
                    (guild.id,),
                ).fetchall()
            cfg = load_config(guild.id)
            for row in rows:
                ticket_id = row["id"]
                role_id = None
                with connect() as db:
                    meta = db.execute("SELECT category FROM ticket_meta WHERE ticket_id=?", (ticket_id,)).fetchone()
                if meta:
                    for item in cfg["categories"]:
                        if item.get("name") == meta["category"]:
                            role_id = item.get("role_id")
                            break
                if cfg.get("claim_required"):
                    self.bot.add_view(TicketClaimView(guild.id, ticket_id, role_id))

    def panel_embed(self, guild_id):
        cfg = load_config(guild_id)
        embed = discord.Embed(
            title=cfg.get("title") or "Support",
            description=cfg.get("description") or "Choose a ticket category.",
            color=discord.Color(cfg.get("color", 0x5865F2)),
        )
        embed.set_footer(text="LightCore • Ticket Support")
        return embed

    async def sync_published_panel(self, guild_id):
        cfg = load_config(guild_id)
        message_id = cfg.get("published_message_id")
        channel_id = cfg.get("panel_channel_id")
        if not message_id or not channel_id:
            return False, "ℹ️ No published ticket panel is saved yet. Use Publish after choosing a channel."
        channel = self.bot.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return False, "❌ The configured panel channel is unavailable."
        try:
            message = await channel.fetch_message(int(message_id))
            await message.edit(embed=self.panel_embed(guild_id), view=TicketPanelView(self, guild_id))
            return True, "✅ Live ticket panel updated in place."
        except discord.NotFound:
            return False, "⚠️ The saved panel message no longer exists. Use Publish to create a new one."
        except discord.Forbidden:
            return False, "❌ I cannot edit the saved ticket panel message. Check Manage Messages permissions."
        except discord.HTTPException as exc:
            return False, f"❌ Discord rejected the panel update: {exc}"

    async def publish_panel(self, source, guild_id):
        cfg = load_config(guild_id)
        channel = self.bot.get_channel(cfg.get("panel_channel_id")) if cfg.get("panel_channel_id") else None
        if not isinstance(channel, discord.TextChannel):
            message = "❌ Choose a text channel first with **Panel Channel**."
            if hasattr(source, "response"):
                return await source.response.send_message(message, ephemeral=True)
            return await source.send(message)
        if not cfg.get("categories"):
            message = "❌ Add at least one ticket category first."
            if hasattr(source, "response"):
                return await source.response.send_message(message, ephemeral=True)
            return await source.send(message)

        existing_id = cfg.get("published_message_id")
        if existing_id:
            ok, message = await self.sync_published_panel(guild_id)
            if hasattr(source, "response"):
                return await source.response.send_message(message, ephemeral=True)
            return await source.send(message)

        message = await channel.send(embed=self.panel_embed(guild_id), view=TicketPanelView(self, guild_id))
        cfg["published_message_id"] = message.id
        save_config(guild_id, cfg)
        if hasattr(source, "response"):
            return await source.response.send_message(
                f"✅ Ticket panel published in {channel.mention}. You can now use **✏️ Edit** on the panel itself.",
                ephemeral=True,
            )
        return await source.send(f"✅ Ticket panel published in {channel.mention}.")

    @commands.hybrid_command(name="ticketsetup", description="Open the editable ticket panel setup.")
    @commands.has_permissions(manage_channels=True)
    async def ticketsetup(self, ctx):
        editor = TicketEditor(self, ctx.guild.id)
        editor.message = await ctx.send(embed=editor.embed(), view=editor)

    @commands.hybrid_command(name="ticketpanel", description="Publish or synchronize the configured ticket panel.")
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
            row = db.execute(
                "SELECT id FROM tickets WHERE guild_id=? AND channel_id=? AND status='open'",
                (ctx.guild.id, ctx.channel.id),
            ).fetchone()
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
            db.execute(
                "INSERT INTO ticket_transcripts(ticket_id,transcript) VALUES(?,?)",
                (row["id"], transcript[:50000]),
            )
        log_id = get_setting(ctx.guild.id, "ticket_log_channel")
        log_channel = ctx.guild.get_channel(log_id) if log_id else None
        if log_channel:
            await log_channel.send(
                embed=discord.Embed(
                    title=f"LightCore Ticket #{row['id']} Closed",
                    description=f"```text\n{transcript[:3800]}\n```",
                    color=discord.Color.blurple(),
                )
            )
        await ctx.send("Closing ticket and saving its transcript…")
        await ctx.channel.delete(reason=f"LightCore ticket closed by {ctx.author}")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
