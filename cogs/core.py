import os
import discord
from discord.ext import commands
from config import SUPPORT_SERVER_URL
class HelpView(discord.ui.View):
 def __init__(self,bot,author_id): super().__init__(timeout=180); self.bot=bot; self.author_id=author_id; self.message=None
 def home_embed(self): return discord.Embed(title='LightCore Help',description='Use .help to open the LightCore help menu.',color=discord.Color.blurple())
 async def interaction_check(self,i):
  if i.user.id!=self.author_id: await i.response.send_message('This help menu belongs to someone else.',ephemeral=True); return False
  return True
 async def on_timeout(self):
  for x in self.children:x.disabled=True
  if self.message:
   try: await self.message.edit(view=self)
   except discord.HTTPException: pass
class Core(commands.Cog):
 def __init__(self,bot): self.bot=bot
 @commands.command(name='help')
 async def help(self,ctx): view=HelpView(self.bot,ctx.author.id); view.message=await ctx.send(embed=view.home_embed(),view=view)
 @commands.command(name='ping')
 async def ping(self,ctx): await ctx.send(f'LightCore latency: {round(self.bot.latency*1000)}ms')
 @commands.command(name='about')
 async def about(self,ctx):
  embed=discord.Embed(title='LightCore',description='All-in-one Discord moderation, community, leveling, tickets, music and utility bot.',color=discord.Color.blurple()); links=[f'[Support Server]({SUPPORT_SERVER_URL})']
  for label,key in (('Privacy Policy','PRIVACY_POLICY_URL'),('Terms of Service','TERMS_URL'),('Invite LightCore','INVITE_URL')):
   if os.getenv(key): links.append(f'[{label}]({os.getenv(key)})')
  embed.add_field(name='Public links',value=' | '.join(links),inline=False); await ctx.send(embed=embed)
async def setup(bot): await bot.add_cog(Core(bot))
