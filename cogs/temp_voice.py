import discord
from discord.ext import commands

from database import connect, get_setting, set_setting


class TempVoice(commands.Cog):
    """Persistent Join-to-Create temporary voice channels with owner controls."""

    def __init__(self, bot):
        self.bot = bot
        self.owners = {}

    async def cog_load(self):
        with connect() as db:
            rows = db.execute("SELECT * FROM temp_voice_channels WHERE status='active'").fetchall()
        stale = []
        for row in rows:
            try:
                channel = self.bot.get_channel(row["channel_id"]) or await self.bot.fetch_channel(row["channel_id"])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                channel = None
            if isinstance(channel, discord.VoiceChannel):
                self.owners[channel.id] = row["owner_id"]
                self.bot.add_view(TempVoicePanel(self, channel.id, row["owner_id"]))
            else:
                stale.append(row["channel_id"])
        if stale:
            with connect() as db:
                db.executemany("UPDATE temp_voice_channels SET status='deleted' WHERE channel_id=?", ((cid,) for cid in stale))

    @commands.hybrid_group(name="tempvoice", invoke_without_command=True, description="Configure LightCore temporary voice channels.")
    @commands.has_guild_permissions(manage_channels=True)
    async def tempvoice(self, ctx):
        await ctx.send("Use `.tempvoice setup <category> <join-to-create-channel> [panel-text-channel]` to configure TempVoice.")

    @tempvoice.command(name="setup", description="Set the Join-to-Create channel, category, and panel text channel.")
    @commands.has_guild_permissions(manage_channels=True)
    async def setup(self, ctx, category: discord.CategoryChannel, join_channel: discord.VoiceChannel, panel_channel: discord.TextChannel = None):
        panel_channel = panel_channel or ctx.channel
        set_setting(ctx.guild.id, "tempvoice_category", category.id)
        set_setting(ctx.guild.id, "tempvoice_join_channel", join_channel.id)
        set_setting(ctx.guild.id, "tempvoice_panel_channel", panel_channel.id)
        await ctx.send(f"✅ TempVoice enabled. Join {join_channel.mention} to create a temporary VC. Panels will appear in {panel_channel.mention}.")

    @commands.hybrid_command(name="tempvoice_disable", description="Disable the Join-to-Create configuration.")
    @commands.has_guild_permissions(manage_channels=True)
    async def tempvoice_disable(self, ctx):
        set_setting(ctx.guild.id, "tempvoice_join_channel", None)
        set_setting(ctx.guild.id, "tempvoice_category", None)
        set_setting(ctx.guild.id, "tempvoice_panel_channel", None)
        await ctx.send("✅ TempVoice Join-to-Create has been disabled.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and before.channel.id in self.owners and not before.channel.members:
            with connect() as db:
                db.execute("UPDATE temp_voice_channels SET status='deleted' WHERE channel_id=?", (before.channel.id,))
            self.owners.pop(before.channel.id, None)
            try:
                await before.channel.delete(reason="LightCore temporary voice channel became empty")
            except discord.HTTPException:
                pass

        if not after.channel or before.channel == after.channel:
            return
        join_channel_id = get_setting(member.guild.id, "tempvoice_join_channel")
        category_id = get_setting(member.guild.id, "tempvoice_category")
        if not join_channel_id or after.channel.id != int(join_channel_id) or not category_id:
            return
        category = member.guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            return

        channel = await member.guild.create_voice_channel(f"{member.display_name}'s VC", category=category, reason="LightCore TempVoice")
        self.owners[channel.id] = member.id
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO temp_voice_channels(channel_id,guild_id,owner_id,status,locked,hidden,user_limit) VALUES(?,?,?,'active',0,0,0)", (channel.id, member.guild.id, member.id))
        await member.move_to(channel, reason="LightCore TempVoice")

        panel_channel_id = get_setting(member.guild.id, "tempvoice_panel_channel")
        panel_channel = member.guild.get_channel(int(panel_channel_id)) if panel_channel_id else None
        if not isinstance(panel_channel, discord.TextChannel):
            return
        panel = TempVoicePanel(self, channel.id, member.id)
        self.bot.add_view(panel)
        embed = discord.Embed(title="🔊 LightCore • Temp Voice", description=f"Your temporary channel is {channel.mention}. Use the controls below.", color=discord.Color.blurple())
        embed.add_field(name="Owner", value=member.mention)
        message = await panel_channel.send(content=member.mention, embed=embed, view=panel)
        with connect() as db:
            db.execute("UPDATE temp_voice_channels SET panel_message_id=? WHERE channel_id=?", (message.id, channel.id))

    async def update_panel(self, channel_id):
        with connect() as db:
            row = db.execute("SELECT * FROM temp_voice_channels WHERE channel_id=? AND status='active'", (channel_id,)).fetchone()
        if not row or not row["panel_message_id"]:
            return
        guild = self.bot.get_guild(row["guild_id"])
        channel = guild.get_channel(channel_id) if guild else None
        panel_channel_id = get_setting(row["guild_id"], "tempvoice_panel_channel")
        panel_channel = guild.get_channel(int(panel_channel_id)) if guild and panel_channel_id else None
        if not isinstance(panel_channel, discord.TextChannel):
            return
        try:
            message = await panel_channel.fetch_message(row["panel_message_id"])
            embed = discord.Embed(title="🔊 LightCore • Temp Voice", description=f"Temporary channel: {channel.mention if channel else 'deleted'}", color=discord.Color.blurple())
            embed.add_field(name="Owner", value=f"<@{row['owner_id']}>")
            embed.add_field(name="State", value=f"{'🔒 Locked' if row['locked'] else '🔓 Unlocked'} • {'🙈 Hidden' if row['hidden'] else '👁️ Visible'}")
            embed.add_field(name="Limit", value=str(row['user_limit'] or 'Unlimited'))
            await message.edit(embed=embed, view=TempVoicePanel(self, channel_id, row["owner_id"]))
        except discord.HTTPException:
            pass


class TempVoicePanel(discord.ui.View):
    def __init__(self, cog, channel_id, owner_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.channel_id = channel_id
        self.owner_id = owner_id
        controls = [
            ("Lock", "🔒", "lock", discord.ButtonStyle.secondary),
            ("Unlock", "🔓", "unlock", discord.ButtonStyle.success),
            ("Rename", "✏️", "rename", discord.ButtonStyle.primary),
            ("Limit", "👥", "limit", discord.ButtonStyle.primary),
            ("Kick", "🚪", "kick", discord.ButtonStyle.danger),
            ("Allow", "➕", "allow", discord.ButtonStyle.success),
            ("Transfer", "👑", "transfer", discord.ButtonStyle.secondary),
            ("Hide", "🙈", "hide", discord.ButtonStyle.secondary),
            ("Unhide", "👁️", "unhide", discord.ButtonStyle.success),
        ]
        for label, emoji, action, style in controls:
            button = discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=f"lightcore:tempvoice:{channel_id}:{action}")
            button.callback = self._callback(action)
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the temporary channel owner can use this panel.", ephemeral=True)
            return False
        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message("This temporary voice channel no longer exists.", ephemeral=True)
            return False
        if not interaction.user.voice or interaction.user.voice.channel != channel:
            await interaction.response.send_message("Join your temporary voice channel to use its controls.", ephemeral=True)
            return False
        return True

    def _callback(self, action):
        async def callback(interaction):
            channel = interaction.guild.get_channel(self.channel_id)
            if action == "rename":
                return await interaction.response.send_modal(RenameModal(self.channel_id))
            if action == "limit":
                return await interaction.response.send_modal(LimitModal(self.channel_id))
            if action == "transfer":
                return await interaction.response.send_modal(TransferModal(self.cog, self.channel_id))
            if action == "kick":
                members = [m for m in channel.members if m.id != self.owner_id]
                if not members:
                    return await interaction.response.send_message("No other members are currently in the channel.", ephemeral=True)
                return await interaction.response.send_message("Choose a member to kick:", view=KickSelect(self.channel_id, members), ephemeral=True)
            if action == "allow":
                return await interaction.response.send_modal(AllowModal(self.channel_id))
            if action in {"lock", "unlock"}:
                value = action == "lock"
                await channel.set_permissions(interaction.guild.default_role, connect=not value)
                with connect() as db:
                    db.execute("UPDATE temp_voice_channels SET locked=? WHERE channel_id=?", (int(value), self.channel_id))
                await interaction.response.send_message("🔒 Locked." if value else "🔓 Unlocked.", ephemeral=True)
            elif action in {"hide", "unhide"}:
                value = action == "hide"
                await channel.set_permissions(interaction.guild.default_role, view_channel=not value)
                with connect() as db:
                    db.execute("UPDATE temp_voice_channels SET hidden=? WHERE channel_id=?", (int(value), self.channel_id))
                await interaction.response.send_message("🙈 Hidden." if value else "👁️ Visible.", ephemeral=True)
            await self.cog.update_panel(self.channel_id)
        return callback


class RenameModal(discord.ui.Modal, title="Rename Temp VC"):
    name = discord.ui.TextInput(label="New channel name", max_length=100)
    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id
    async def on_submit(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Channel no longer exists.", ephemeral=True)
        await channel.edit(name=self.name.value)
        await interaction.response.send_message("✅ Renamed.", ephemeral=True)


class LimitModal(discord.ui.Modal, title="Set User Limit"):
    limit = discord.ui.TextInput(label="Limit (0 = unlimited)", max_length=2)
    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id
    async def on_submit(self, interaction):
        try:
            value = max(0, min(99, int(self.limit.value)))
        except ValueError:
            return await interaction.response.send_message("Enter a number from 0 to 99.", ephemeral=True)
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Channel no longer exists.", ephemeral=True)
        await channel.edit(user_limit=value)
        with connect() as db:
            db.execute("UPDATE temp_voice_channels SET user_limit=? WHERE channel_id=?", (value, self.channel_id))
        await interaction.response.send_message(f"✅ User limit set to {value or 'unlimited'}.", ephemeral=True)
        cog = interaction.client.get_cog("TempVoice")
        if cog:
            await cog.update_panel(self.channel_id)


class KickSelect(discord.ui.View):
    def __init__(self, channel_id, members):
        super().__init__(timeout=60)
        self.channel_id = channel_id
        select = discord.ui.Select(placeholder="Choose a member…", options=[discord.SelectOption(label=m.display_name[:100], value=str(m.id)) for m in members[:25]])
        select.callback = self.kick
        self.add_item(select)
    async def kick(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        member = interaction.guild.get_member(int(interaction.data["values"][0]))
        if not channel or not member:
            return await interaction.response.send_message("Member or channel not found.", ephemeral=True)
        await member.move_to(None, reason="LightCore TempVoice owner kick")
        await interaction.response.edit_message(content=f"🚪 Kicked {member.mention}.", view=None)


class AllowModal(discord.ui.Modal, title="Allow a User"):
    user_id = discord.ui.TextInput(label="Discord user ID", max_length=20)
    def __init__(self, channel_id):
        super().__init__()
        self.channel_id = channel_id
    async def on_submit(self, interaction):
        if not self.user_id.value.isdigit():
            return await interaction.response.send_message("Enter a valid Discord user ID.", ephemeral=True)
        member = interaction.guild.get_member(int(self.user_id.value))
        channel = interaction.guild.get_channel(self.channel_id)
        if not member or not channel:
            return await interaction.response.send_message("Member or channel not found.", ephemeral=True)
        await channel.set_permissions(member, connect=True, view_channel=True)
        await interaction.response.send_message(f"➕ Allowed {member.mention}.", ephemeral=True)


class TransferModal(discord.ui.Modal, title="Transfer Ownership"):
    user_id = discord.ui.TextInput(label="New owner's Discord user ID", max_length=20)
    def __init__(self, cog, channel_id):
        super().__init__()
        self.cog, self.channel_id = cog, channel_id
    async def on_submit(self, interaction):
        if not self.user_id.value.isdigit():
            return await interaction.response.send_message("Enter a valid Discord user ID.", ephemeral=True)
        member = interaction.guild.get_member(int(self.user_id.value))
        if not member:
            return await interaction.response.send_message("Member not found.", ephemeral=True)
        self.cog.owners[self.channel_id] = member.id
        with connect() as db:
            db.execute("UPDATE temp_voice_channels SET owner_id=? WHERE channel_id=?", (member.id, self.channel_id))
        await interaction.response.send_message(f"👑 Ownership transferred to {member.mention}.", ephemeral=True)
        await self.cog.update_panel(self.channel_id)


async def setup(bot):
    await bot.add_cog(TempVoice(bot))
