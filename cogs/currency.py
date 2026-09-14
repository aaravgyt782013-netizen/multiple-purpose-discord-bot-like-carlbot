import random
from datetime import datetime, timedelta, timezone
import discord
from discord.ext import commands
from database import connect, ensure_guild

CLAIMS = {'hourly': (3600, 50), 'daily': (86400, 250), 'weekly': (604800, 1500)}

def em(title, text, color=discord.Color.blurple()):
    e = discord.Embed(title=title, description=text, color=color); e.set_footer(text='LightCore • Economy'); return e

def remain(sec):
    sec=max(1,int(sec)); d,sec=divmod(sec,86400); h,sec=divmod(sec,3600); m,_=divmod(sec,60)
    return f'{d}d {h}h' if d else (f'{h}h {m}m' if h else f'{m}m')

class EcoPages(discord.ui.View):
    def __init__(self,cog,guild_id): super().__init__(timeout=180); self.cog=cog; self.guild_id=guild_id; self.page=1; self.message=None
    async def interaction_check(self,i):
        if i.guild_id!=self.guild_id: await i.response.send_message(embed=em('❌ Error','This leaderboard belongs to another server.',discord.Color.red()),ephemeral=True); return False
        return True
    @discord.ui.button(label='Previous',emoji='◀️',style=discord.ButtonStyle.secondary)
    async def prev(self,i,b): self.page=max(1,self.page-1); await self.cog.edit_eco(i,self)
    @discord.ui.button(label='Next',emoji='▶️',style=discord.ButtonStyle.secondary)
    async def nxt(self,i,b):
        if not self.cog.has_page(self.guild_id,self.page+1): return await i.response.send_message(embed=em('❌ No more pages','There are no more users.',discord.Color.red()),ephemeral=True)
        self.page+=1; await self.cog.edit_eco(i,self)

class Currency(commands.Cog):
    """Non-gambling LightCoins, pets, rewards, shop and social features."""
    def __init__(self,bot): self.bot=bot
    def ensure(self,g,u):
        ensure_guild(g)
        with connect() as db: db.execute('INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)',(g,u))
    def bal(self,g,u):
        self.ensure(g,u)
        with connect() as db: return db.execute('SELECT balance FROM balances WHERE guild_id=? AND user_id=?',(g,u)).fetchone()['balance']
    def add(self,g,u,n):
        self.ensure(g,u)
        with connect() as db: db.execute('UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?',(n,g,u))
    def claim(self,g,u,k):
        cd,reward=CLAIMS[k]; now=datetime.now(timezone.utc)
        with connect() as db:
            r=db.execute('SELECT claimed_at FROM reward_claims WHERE guild_id=? AND user_id=? AND reward_type=?',(g,u,k)).fetchone()
            if r:
                try: last=datetime.fromisoformat(r['claimed_at'].replace('Z','+00:00')); last=last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last
                except ValueError: last=now-timedelta(seconds=cd)
                left=cd-int((now-last).total_seconds())
                if left>0:return 0,left
            db.execute('INSERT INTO reward_claims(guild_id,user_id,reward_type,claimed_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,reward_type) DO UPDATE SET claimed_at=excluded.claimed_at',(g,u,k,now.isoformat()))
            db.execute('INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)',(g,u)); db.execute('UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?',(reward,g,u))
        return reward,0
    @commands.hybrid_command(name='balance',aliases=['bal'],description='Show a member balance.')
    async def balance(self,ctx,member:discord.Member=None):
        member=member or ctx.author; n=self.bal(ctx.guild.id,member.id); e=em('💰 Balance',f'**{member.display_name}** has **{n:,} LightCoins**.',discord.Color.gold()); e.set_thumbnail(url=member.display_avatar.url); await ctx.send(embed=e)
    async def _claim(self,ctx,k):
        n,left=self.claim(ctx.guild.id,ctx.author.id,k)
        if not n:return await ctx.send(embed=em('⏳ Cooldown',f'Your **{k}** reward is ready in **{remain(left)}**.',discord.Color.orange()))
        await ctx.send(embed=em(f'💰 {k.title()} reward',f'You received **{n:,} LightCoins**.',discord.Color.green()))
    @commands.hybrid_command(name='hourly',description='Claim the hourly reward.')
    async def hourly(self,ctx):await self._claim(ctx,'hourly')
    @commands.hybrid_command(name='daily',description='Claim the daily reward.')
    async def daily(self,ctx):await self._claim(ctx,'daily')
    @commands.hybrid_command(name='weekly',description='Claim the weekly reward.')
    async def weekly(self,ctx):await self._claim(ctx,'weekly')
    @commands.hybrid_command(name='pay',description='Transfer LightCoins to another member.')
    async def pay(self,ctx,member:discord.Member,amount:commands.Range[int,1,1000000000]):
        if member.bot or member.id==ctx.author.id:return await ctx.send(embed=em('❌ Invalid recipient','Choose another human member.',discord.Color.red()))
        if self.bal(ctx.guild.id,ctx.author.id)<amount:return await ctx.send(embed=em('❌ Insufficient funds','You cannot afford this transfer.',discord.Color.red()))
        self.add(ctx.guild.id,ctx.author.id,-amount);self.add(ctx.guild.id,member.id,amount);await ctx.send(embed=em('💸 Payment sent',f'Sent **{amount:,} LightCoins** to {member.mention}.',discord.Color.green()))
    def petrow(self,g,u):
        with connect() as db:return db.execute('SELECT * FROM pets WHERE guild_id=? AND user_id=?',(g,u)).fetchone()
    @commands.hybrid_command(name='adopt',description='Adopt a virtual pet.')
    async def adopt(self,ctx,name:commands.Range[str,1,24],species:str='fox'):
        if self.petrow(ctx.guild.id,ctx.author.id):return await ctx.send(embed=em('🐾 Already adopted','You already have a pet.',discord.Color.orange()))
        with connect() as db:db.execute('INSERT INTO pets(guild_id,user_id,name,species,level,energy,xp) VALUES(?,?,?,?,1,100,0)',(ctx.guild.id,ctx.author.id,name,species.lower()[:20]))
        await ctx.send(embed=em('🐾 Pet adopted',f'**{name}** the **{species}** is now yours!',discord.Color.green()))
    @commands.hybrid_command(name='pet',description='View a pet.')
    async def petcmd(self,ctx,member:discord.Member=None):
        member=member or ctx.author;p=self.petrow(ctx.guild.id,member.id)
        if not p:return await ctx.send(embed=em('🐾 No pet','This member has no pet.',discord.Color.orange()))
        await ctx.send(embed=em('🐾 Pet Profile',f"**{p['name']}** • {p['species']}\nLevel **{p['level']}** • XP **{p['xp']}**\nEnergy **{p['energy']}/100**",discord.Color.blurple()))
    @commands.hybrid_command(name='feed',description='Feed your pet.')
    async def feed(self,ctx):
        p=self.petrow(ctx.guild.id,ctx.author.id)
        if not p:return await ctx.send(embed=em('🐾 No pet','Adopt a pet first.',discord.Color.orange()))
        n=min(100,p['energy']+30)
        with connect() as db:db.execute('UPDATE pets SET energy=? WHERE guild_id=? AND user_id=?',(n,ctx.guild.id,ctx.author.id))
        await ctx.send(embed=em('🍖 Pet fed',f"**{p['name']}** now has **{n}/100** energy.",discord.Color.green()))
    @commands.hybrid_command(name='train',description='Train your pet.')
    async def train(self,ctx):
        p=self.petrow(ctx.guild.id,ctx.author.id)
        if not p:return await ctx.send(embed=em('🐾 No pet','Adopt a pet first.',discord.Color.orange()))
        if p['energy']<20:return await ctx.send(embed=em('⚡ Too tired','Feed your pet before training.',discord.Color.orange()))
        xp=p['xp']+25;lv=p['level']
        while xp>=lv*100:xp-=lv*100;lv+=1
        sp=p['species'];note=''
        if lv>=5 and not sp.startswith('evolved-'):sp='evolved-'+sp;note=' ✨ Evolution unlocked!'
        with connect() as db:db.execute('UPDATE pets SET xp=?,level=?,energy=?,species=? WHERE guild_id=? AND user_id=?',(xp,lv,p['energy']-20,sp,ctx.guild.id,ctx.author.id))
        await ctx.send(embed=em('🏋️ Training complete',f"**{p['name']}** is level **{lv}**.{note}",discord.Color.green()))
    @commands.hybrid_command(name='petbattle',description='Battle another pet without currency wagering.')
    async def petbattle(self,ctx,opponent:discord.Member):
        a=self.petrow(ctx.guild.id,ctx.author.id);b=self.petrow(ctx.guild.id,opponent.id)
        if opponent.bot or opponent.id==ctx.author.id or not a or not b:return await ctx.send(embed=em('❌ Battle unavailable','Both players need different human accounts with pets.',discord.Color.red()))
        if a['energy']<20 or b['energy']<20:return await ctx.send(embed=em('⚡ Too tired','Both pets need 20 energy.',discord.Color.orange()))
        pa=a['level']*100+a['xp']+a['energy'];pb=b['level']*100+b['xp']+b['energy'];w=None if pa==pb else(ctx.author if pa>pb else opponent)
        with connect() as db:db.execute('UPDATE pets SET energy=energy-20 WHERE guild_id=? AND user_id IN (?,?)',(ctx.guild.id,ctx.author.id,opponent.id))
        if w:self.add(ctx.guild.id,w.id,50);msg=f'🏆 **{w.display_name}** wins and receives **50 LightCoins**.'
        else:msg='🤝 Draw! Both pets matched each other.'
        await ctx.send(embed=em('⚔️ Pet Battle',msg,discord.Color.gold()))
    async def activity(self,ctx,k,lo,hi,title,flavor):
        now=datetime.now(timezone.utc);cd={'hunt':45,'fish':35,'crime':60}[k]
        with connect() as db:
            r=db.execute('SELECT claimed_at FROM reward_claims WHERE guild_id=? AND user_id=? AND reward_type=?',(ctx.guild.id,ctx.author.id,k)).fetchone()
            if r:
                try:last=datetime.fromisoformat(r['claimed_at'].replace('Z','+00:00'));last=last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last
                except ValueError:last=now-timedelta(seconds=cd)
                left=cd-int((now-last).total_seconds())
                if left>0:return await ctx.send(embed=em('⏳ Cooldown',f'Try again in **{remain(left)}**.',discord.Color.orange()))
            n=random.randint(lo,hi);db.execute('INSERT INTO reward_claims(guild_id,user_id,reward_type,claimed_at) VALUES(?,?,?,?) ON CONFLICT(guild_id,user_id,reward_type) DO UPDATE SET claimed_at=excluded.claimed_at',(ctx.guild.id,ctx.author.id,k,now.isoformat()));db.execute('INSERT OR IGNORE INTO balances(guild_id,user_id,balance) VALUES(?,?,0)',(ctx.guild.id,ctx.author.id));db.execute('UPDATE balances SET balance=balance+? WHERE guild_id=? AND user_id=?',(n,ctx.guild.id,ctx.author.id))
        await ctx.send(embed=em(title,f'{flavor}\nYou earned **{n:,} LightCoins**.',discord.Color.green()))
    @commands.hybrid_command(name='hunt',description='Fictional hunt reward command.')
    async def hunt(self,ctx):await self.activity(ctx,'hunt',40,180,'🏹 Hunt complete','Your expedition returned with a reward.')
    @commands.hybrid_command(name='fish',description='Fishing reward command.')
    async def fish(self,ctx):await self.activity(ctx,'fish',30,160,'🎣 Fishing complete','The fishing trip paid off!')
    @commands.hybrid_command(name='crime',description='Fictional crime-themed reward command; no wagering.')
    async def crime(self,ctx):await self.activity(ctx,'crime',60,220,'🕵️ Fictional caper','Your imaginary caper ended with a reward.')
    def shoprows(self,g):
        with connect() as db:return db.execute('SELECT name,price,description,role_id,stock FROM shop_items WHERE guild_id=? ORDER BY price,name',(g,)).fetchall()
    @commands.hybrid_group(name='shop',invoke_without_command=True,description='View the server shop.')
    async def shop(self,ctx):
        rows=self.shoprows(ctx.guild.id);text='\n\n'.join(f"**{r['name']}** — {r['price']:,} LightCoins\n{r['description'] or 'No description.'}" for r in rows) or 'The shop is empty. Managers can use `.shopadd`.'
        await ctx.send(embed=em('🛒 LightCore Shop',text))
    @shop.command(name='buy',description='Buy a shop item or role.')
    async def shopbuy(self,ctx,item:str):
        r=next((x for x in self.shoprows(ctx.guild.id) if x['name'].lower()==item.lower()),None)
        if not r:return await ctx.send(embed=em('❌ Item not found','Check `.shop`.',discord.Color.red()))
        if r['stock']==0:return await ctx.send(embed=em('❌ Out of stock','That item is unavailable.',discord.Color.red()))
        if self.bal(ctx.guild.id,ctx.author.id)<r['price']:return await ctx.send(embed=em('❌ Insufficient funds','You cannot afford this item.',discord.Color.red()))
        self.add(ctx.guild.id,ctx.author.id,-r['price'])
        if r['stock']>0:
            with connect() as db:db.execute('UPDATE shop_items SET stock=stock-1 WHERE guild_id=? AND name=?',(ctx.guild.id,r['name']))
        role=ctx.guild.get_role(r['role_id']) if r['role_id'] else None;note=''
        if role:
            try:await ctx.author.add_roles(role,reason='LightCore shop purchase');note=f' Role granted: {role.mention}.'
            except discord.HTTPException:note=' ⚠️ I could not grant the configured role.'
        await ctx.send(embed=em('🛍️ Purchase complete',f"Bought **{r['name']}** for **{r['price']:,} LightCoins**.{note}",discord.Color.green()))
    @commands.hybrid_command(name='shopadd',description='Add or replace a shop item or role reward.')
    @commands.has_permissions(manage_guild=True)
    async def shopadd(self,ctx,name:str,price:commands.Range[int,1,1000000000],description:str,role:discord.Role=None,stock:int=-1):
        if stock<-1:return await ctx.send(embed=em('❌ Invalid stock','Stock must be -1 or greater.',discord.Color.red()))
        with connect() as db:db.execute('INSERT INTO shop_items(guild_id,name,price,description,role_id,stock) VALUES(?,?,?,?,?,?) ON CONFLICT(guild_id,name) DO UPDATE SET price=excluded.price,description=excluded.description,role_id=excluded.role_id,stock=excluded.stock',(ctx.guild.id,name,price,description,role.id if role else None,stock))
        await ctx.send(embed=em('🛒 Shop updated',f'**{name}** is available for **{price:,} LightCoins**.',discord.Color.green()))
    @commands.hybrid_command(name='shopremove',description='Remove a shop item.')
    @commands.has_permissions(manage_guild=True)
    async def shopremove(self,ctx,name:str):
        with connect() as db:cur=db.execute('DELETE FROM shop_items WHERE guild_id=? AND name=?',(ctx.guild.id,name))
        if not cur.rowcount:return await ctx.send(embed=em('❌ Item not found','No matching shop item.',discord.Color.red()))
        await ctx.send(embed=em('🗑️ Shop item removed',f'Removed **{name}**.',discord.Color.green()))
    def has_page(self,g,p):
        with connect() as db:return db.execute('SELECT 1 FROM balances WHERE guild_id=? ORDER BY balance DESC,user_id ASC LIMIT 1 OFFSET ?',(g,(p-1)*10)).fetchone() is not None
    def eco(self,g,p):
        with connect() as db:rows=db.execute('SELECT user_id,balance FROM balances WHERE guild_id=? ORDER BY balance DESC,user_id ASC LIMIT 10 OFFSET ?',(g,(p-1)*10)).fetchall();total=db.execute('SELECT COUNT(*) FROM balances WHERE guild_id=?',(g,)).fetchone()[0]
        guild=self.bot.get_guild(g);lines=[f"**#{i}** {(guild.get_member(r['user_id']).display_name if guild and guild.get_member(r['user_id']) else 'User '+str(r['user_id']))} — **{r['balance']:,} LightCoins**" for i,r in enumerate(rows,(p-1)*10+1)];pages=max(1,(total+9)//10);return em('🏆 Economy Leaderboard','\n'.join(lines) or 'No economy users yet.',discord.Color.gold()),pages
    async def edit_eco(self,i,v):
        e,p=self.eco(v.guild_id,v.page);e.description=(e.description or '')+f'\n\nPage **{v.page}/{p}**';await i.response.edit_message(embed=e,view=v)
    @commands.hybrid_command(name='ecoleaderboard',description='Show the paginated wealth leaderboard.')
    async def ecoleaderboard(self,ctx):
        v=EcoPages(self,ctx.guild.id);e,p=self.eco(ctx.guild.id,1);e.description=(e.description or '')+f'\n\nPage **1/{p}**';v.message=await ctx.send(embed=e,view=v)
    @commands.hybrid_command(name='marry',description='Create a playful in-game partnership.')
    async def marry(self,ctx,member:discord.Member):
        if member.bot or member.id==ctx.author.id:return await ctx.send(embed=em('❌ Invalid partner','Choose another human member.',discord.Color.red()))
        with connect() as db:
            if db.execute('SELECT 1 FROM marriages WHERE guild_id=? AND user_id IN (?,?)',(ctx.guild.id,ctx.author.id,member.id)).fetchone():return await ctx.send(embed=em('💍 Already partnered','One of you already has a partnership.',discord.Color.orange()))
            if self.bal(ctx.guild.id,ctx.author.id)<500:return await ctx.send(embed=em('💰 500 LightCoins required','You need 500 LightCoins for this social feature.',discord.Color.red()))
            db.execute('UPDATE balances SET balance=balance-500 WHERE guild_id=? AND user_id=?',(ctx.guild.id,ctx.author.id));db.execute('INSERT INTO marriages(guild_id,user_id,partner_id) VALUES(?,?,?),(?,?,?)',(ctx.guild.id,ctx.author.id,member.id,ctx.guild.id,member.id,ctx.author.id))
        await ctx.send(embed=em('💍 Partnership created',f'{ctx.author.mention} and {member.mention} now have an in-game partnership!',discord.Color.pink()))
    @commands.hybrid_command(name='divorce',description='End your in-game partnership.')
    async def divorce(self,ctx):
        with connect() as db:
            r=db.execute('SELECT partner_id FROM marriages WHERE guild_id=? AND user_id=?',(ctx.guild.id,ctx.author.id)).fetchone()
            if not r:return await ctx.send(embed=em('💔 No partnership','You have no active in-game partnership.',discord.Color.orange()))
            db.execute('DELETE FROM marriages WHERE guild_id=? AND user_id IN (?,?)',(ctx.guild.id,ctx.author.id,r['partner_id']))
        await ctx.send(embed=em('💔 Partnership ended','Your in-game partnership has ended.',discord.Color.green()))

async def setup(bot):await bot.add_cog(Currency(bot))
