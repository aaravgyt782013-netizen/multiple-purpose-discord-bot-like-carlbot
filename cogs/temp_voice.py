import discord
from discord.ext import commands

from database import connect


class TempVoice(commands.Cog):
    """Join-to-create temporary voice channels with an owner control panel."""

    def __init__(self, bot):
        self.bot = bot
        self.owners: dict[int, int] = {}

    @commands.hybrid_command(name="tempvoice_setup")
    @commands.has_guild_permissions(manage_channels=True)
    async def tempvoice_setup(self, ctx, category: discord.CategoryChannel, join_channel: discord.VoiceChannel):
        """Configure the Join to Create channel."""
        with connect() as db:
            db.execute(
                """INSERT INTO guild_settings (guild_id, key, value) VALUES (?, 'tempvoice_category', ?)
                   ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value""",
                (ctx.guild.id, str(category.id)),
            )
            db.execute(
                """INSERT INTO guild_settings (guild_id, key, value) VALUES (?, 'tempvoice_join_channel', ?)
                   ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value""",
                (ctx.guild.id, str(join_channel.id)),
            )
        await ctx.send(f"✅ LightCore Temp Voice enabled: join {join_channel.mention} to create a private VC.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not after.channel or before.channel == after.channel:
            return
        with connect() as db:
            rows = db.execute(
                "SELECT key, value FROM guild_settings WHERE guild_id=? AND key IN ('tempvoice_category','tempvoice_join_channel')",
                (member.guild.id,),
            ).fetchall()
        settings = {r["key"]: r["value"] for r in rows}
        if str(after.channel.id) != settings.get("tempvoice_join_channel"):
            return
        category = member.guild.get_channel(int(settings["tempvoice_category"]))
        if not isinstance(category, discord.CategoryChannel):
            return
        channel = await member.guild.create_voice_channel(f"{member.display_name}'s VC", category=category)
        self.owners[channel.id] = member.id
        await member.move_to(channel)
        await self._send_panel(channel, member)

    async def _send_panel(self, channel, owner):
        embed = discord.Embed(title="LightCore • Temp Voice", description="Use the buttons below to manage your temporary voice channel.", color=discord.Color.blurple())
        embed.add_field(name="Owner", value=owner.mention)
        await channel.send(embed=embed, view=TempVoicePanel(self, channel.id, owner.id))


class TempVoicePanel(discord.ui.View):
    def __init__(self, cog, channel_id, owner_id):
        super().__init__(timeout=None)
        self.cog, self.channel_id, self.owner_id = cog, channel_id, owner_id

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the temporary channel owner can use this panel.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rename", style=discord.ButtonStyle.primary, emoji="✏️")
    async def rename(self, interaction, button):
        await interaction.response.send_modal(RenameModal(self.channel_id))

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.secondary, emoji="🔒")
    async def lock(self, interaction, button):
        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Channel locked.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.success, emoji="🔓")
    async def unlock(self, interaction, button):
        channel = interaction.guild.get_channel(self.channel_id)
        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Channel unlocked.", ephemeral=True)

    @discord.ui.button(label="Limit", style=discord.ButtonStyle.primary, emoji="👥")
    async def limit(self, interaction, button):
        await interaction.response.send_modal(LimitModal(self.channel_id))

    @discord.ui.button(label="Transfer", style=discord.ButtonStyle.secondary, emoji="👑")
    async def transfer(self, interaction, button):
        await interaction.response.send_modal(TransferModal(self.cog, self.channel_id, self.owner_id, self))


class RenameModal(discord.ui.Modal, title="Rename Temp VC"):
    name = discord.ui.TextInput(label="New channel name", max_length=100)
    def __init__(self, channel_id):
        super().__init__(); self.channel_id = channel_id
    async def on_submit(self, interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        await channel.edit(name=self.name.value)
        await interaction.response.send_message("✅ Renamed.", ephemeral=True)


class LimitModal(discord.ui.Modal, title="Set User Limit"):
    limit = discord.ui.TextInput(label="Limit (0 = unlimited)", max_length=2)
    def __init__(self, channel_id):
        super().__init__(); self.channel_id = channel_id
    async def on_submit(self, interaction):
        try: value = max(0, min(99, int(self.limit.value)))
        except ValueError: return await interaction.response.send_message("Enter a number from 0 to 99.", ephemeral=True)
        await interaction.guild.get_channel(self.channel_id).edit(user_limit=value)
        await interaction.response.send_message(f"✅ User limit set to {value or 'unlimited'}.", ephemeral=True)


class TransferModal(discord.ui.Modal, title="Transfer Ownership"):
    user_id = discord.ui.TextInput(label="New owner's Discord user ID", max_length=20)
    def __init__(self, cog, channel_id, owner_id, view):
        super().__init__(); self.cog, self.channel_id, self.owner_id, self.panel = cog, channel_id, owner_id, view
    async def on_submit(self, interaction):
        member = interaction.guild.get_member(int(self.user_id.value)) if self.user_id.value.isdigit() else None
        if not member: return await interaction.response.send_message("Member not found.", ephemeral=True)
        self.cog.owners[self.channel_id] = member.id
        self.panel.owner_id = member.id
        await interaction.response.send_message(f"👑 Ownership transferred to {member.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TempVoice(bot))
