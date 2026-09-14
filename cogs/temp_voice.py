import discord
from discord.ext import commands

from database import connect, get_setting, set_setting


class TempVoice(commands.Cog):
    """Join-to-create temporary voice channels with an owner control panel."""

    def __init__(self, bot):
        self.bot = bot
        self.owners: dict[int, int] = {}

    async def cog_load(self):
        with connect() as db:
            rows = db.execute(
                "SELECT channel_id, owner_id FROM temp_voice_channels WHERE status='active'"
            ).fetchall()
        stale = []
        for row in rows:
            channel = self.bot.get_channel(row["channel_id"])
            if isinstance(channel, discord.VoiceChannel):
                self.owners[channel.id] = row["owner_id"]
                self.bot.add_view(TempVoicePanel(self, channel.id, row["owner_id"]))
            else:
                stale.append(row["channel_id"])
        if stale:
            with connect() as db:
                db.executemany(
                    "UPDATE temp_voice_channels SET status='deleted' WHERE channel_id=?",
                    ((cid,) for cid in stale),
                )

    @commands.hybrid_command(name="tempvoice_setup", description="Configure a Join-to-Create temporary voice channel.")
    @commands.has_guild_permissions(manage_channels=True)
    async def tempvoice_setup(self, ctx, category: discord.CategoryChannel, join_channel: discord.VoiceChannel):
        set_setting(ctx.guild.id, "tempvoice_category", category.id)
        set_setting(ctx.guild.id, "tempvoice_join_channel", join_channel.id)
        await ctx.send(f"✅ LightCore Temp Voice enabled: join {join_channel.mention} to create a private VC.")

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
        if after.channel.id != join_channel_id or not category_id:
            return
        category = member.guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            return
        channel = await member.guild.create_voice_channel(f"{member.display_name}'s VC", category=category)
        self.owners[channel.id] = member.id
        with connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO temp_voice_channels(channel_id,guild_id,owner_id,status) VALUES(?,?,?,'active')",
                (channel.id, member.guild.id, member.id),
            )
        await member.move_to(channel)
        panel = TempVoicePanel(self, channel.id, member.id)
        self.bot.add_view(panel)
        await self._send_panel(channel, member, panel)

    async def _send_panel(self, channel, owner, panel):
        embed = discord.Embed(
            title="LightCore • Temp Voice",
            description="Use the buttons below to manage your temporary voice channel.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Owner", value=owner.mention)
        await channel.send(embed=embed, view=panel)


class TempVoicePanel(discord.ui.View):
    def __init__(self, cog, channel_id, owner_id):
        super().__init__(timeout=None)
        self.cog, self.channel_id, self.owner_id = cog, channel_id, owner_id
        buttons = [
            ("Rename", "✏️", discord.ButtonStyle.primary, self.rename),
            ("Lock", "🔒", discord.ButtonStyle.secondary, self.lock),
            ("Unlock", "🔓", discord.ButtonStyle.success, self.unlock),
            ("Limit", "👥", discord.ButtonStyle.primary, self.limit),
            ("Transfer", "👑", discord.ButtonStyle.secondary, self.transfer),
        ]
        for label, emoji, style, callback in buttons:
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=style,
                custom_id=f"lightcore:tempvoice:{channel_id}:{label.lower()}",
            )
            button.callback = callback
            self.add_item(button)

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the temporary channel owner can use this panel.", ephemeral=True)
            return False
        return True

    async def rename(self, interaction):
        await interaction.response.send_modal(RenameModal(self.channel_id))

    async def lock(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Channel no longer exists.", ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Channel locked.", ephemeral=True)

    async def unlock(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("Channel no longer exists.", ephemeral=True)
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Channel unlocked.", ephemeral=True)

    async def limit(self, interaction):
        await interaction.response.send_modal(LimitModal(self.channel_id))

    async def transfer(self, interaction):
        await interaction.response.send_modal(TransferModal(self.cog, self.channel_id, self.owner_id, self))


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
        await interaction.response.send_message(f"✅ User limit set to {value or 'unlimited'}.", ephemeral=True)


class TransferModal(discord.ui.Modal, title="Transfer Ownership"):
    user_id = discord.ui.TextInput(label="New owner's Discord user ID", max_length=20)

    def __init__(self, cog, channel_id, owner_id, view):
        super().__init__()
        self.cog, self.channel_id, self.owner_id, self.panel = cog, channel_id, owner_id, view

    async def on_submit(self, interaction):
        member = interaction.guild.get_member(int(self.user_id.value)) if self.user_id.value.isdigit() else None
        if not member:
            return await interaction.response.send_message("Member not found.", ephemeral=True)
        self.cog.owners[self.channel_id] = member.id
        self.panel.owner_id = member.id
        with connect() as db:
            db.execute("UPDATE temp_voice_channels SET owner_id=? WHERE channel_id=?", (member.id, self.channel_id))
        await interaction.response.send_message(f"👑 Ownership transferred to {member.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TempVoice(bot))
