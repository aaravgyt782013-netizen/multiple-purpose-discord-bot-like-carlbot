const fs=require('fs');
const path=require('path');
const {EmbedBuilder,PermissionFlagsBits}=require('discord.js');

module.exports=function attachGlobalEconomy(client,prefix='.'){
 const P=prefix||'.';
 const OWNER_ID='1244215702345482301';
 const file=path.join(process.cwd(),'data','global-economy.json');
 fs.mkdirSync(path.dirname(file),{recursive:true});
 let db={users:{}};
 try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{}
 if(!db||typeof db!=='object')db={users:{}};
 if(!db.users||typeof db.users!=='object')db.users={};
 const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const user=id=>db.users[id]||(db.users[id]={balance:0,daily:0,work:0,luck:0});
 const embed=(title,description)=>new EmbedBuilder().setTitle(title).setDescription(description).setColor(0x5865f2).setTimestamp();
 const amount=x=>{const n=Number(String(x||'').replace(/,/g,''));return Number.isFinite(n)&&Number.isInteger(n)?n:NaN};
 const isOwner=m=>m.author.id===OWNER_ID;
 const ownerOnly=m=>{if(!isOwner(m))return m.reply({embeds:[embed('🚫 Owner Only','Only the configured economy owner can add, set, remove money, or change luck.')]});return null};

 async function economy(m,args){
  if(!m.guild)return;
  const c=(args.shift()||'').toLowerCase();
  const me=user(m.author.id);
  if(['balance','bal','money','wallet'].includes(c)){
   return m.reply({embeds:[embed('💰 GLOBAL WALLET',`**User:** ${m.author}\n💵 **Global Balance:** ${me.balance.toLocaleString()} coins\n🍀 **Luck:** ${me.luck}`)]});
  }
  if(c==='daily'){
   const now=Date.now();
   if(now-me.daily<86400000)return m.reply(`⏳ Daily is ready <t:${Math.floor((me.daily+86400000)/1000)}:R>.`);
   me.balance+=1000;me.daily=now;save();
   return m.reply({embeds:[embed('🎁 GLOBAL DAILY','You received **1,000** global coins.')]});
  }
  if(c==='work'){
   const now=Date.now();
   if(now-me.work<3600000)return m.reply(`⏳ Work is ready <t:${Math.floor((me.work+3600000)/1000)}:R>.`);
   me.balance+=500;me.work=now;save();
   return m.reply({embeds:[embed('💼 GLOBAL WORK','You earned **500** global coins.')]});
  }
  if(c==='pay'){
   const target=m.mentions.users.first();
   const n=amount(args.find(x=>/^\d[\d,]*$/.test(x)));
   if(!target||!Number.isInteger(n)||n<=0)return m.reply(`Usage: ${P}pay @user <amount>`);
   if(n>me.balance)return m.reply('❌ You do not have enough global coins.');
   if(target.bot)return m.reply('❌ Bots cannot receive global coins.');
   const other=user(target.id);me.balance-=n;other.balance+=n;save();
   return m.reply({embeds:[embed('💸 GLOBAL TRANSFER',`Sent **${n.toLocaleString()}** coins to ${target}.`)]});
  }
  if(['richlist','leaderboard','top'].includes(c)){
   const top=Object.entries(db.users).sort((a,b)=>b[1].balance-a[1].balance).slice(0,10);
   const text=top.length?top.map((x,i)=>`**${i+1}.** <@${x[0]}> — **${Number(x[1].balance||0).toLocaleString()}**`).join('\n'):'No global economy users yet.';
   return m.reply({embeds:[embed('🏆 GLOBAL RICHLIST',text)]});
  }
  if(c==='luck'){
   const target=m.mentions.users.first()||m.author;
   return m.reply({embeds:[embed('🍀 GLOBAL LUCK',`**${target}** has luck level **${user(target.id).luck}**.`)]});
  }
  if(['add','set','remove','rem','take','setluck','luckset'].includes(c)){
   const denied=ownerOnly(m);if(denied)return;
   const target=m.mentions.users.first();
   if(!target)return m.reply(`Usage: ${P}eco ${c} @user <amount>`);
   const n=amount(args.find(x=>/^\d[\d,]*$/.test(x)));
   if(!Number.isInteger(n)||n<0)return m.reply(`Usage: ${P}eco ${c} @user <amount>`);
   const e=user(target.id);
   if(['setluck','luckset'].includes(c)){e.luck=Math.min(100,n);save();return m.reply({embeds:[embed('🍀 LUCK UPDATED',`Set ${target}'s global luck to **${e.luck}**.`)]});}
   if(c==='add'){e.balance+=n;}
   else if(c==='set'){e.balance=n;}
   else {if(n>e.balance)return m.reply('❌ Cannot remove more coins than the user owns.');e.balance-=n;}
   save();
   return m.reply({embeds:[embed('🛠️ GLOBAL ECONOMY UPDATED',`**User:** ${target}\n**New balance:** ${e.balance.toLocaleString()} coins`)]});
  }
  if(['help',''].includes(c)){
   return m.reply({embeds:[embed('🌐 GLOBAL ECONOMY',`These coins are shared across **all servers** where this bot is installed.\n\n**Commands**\n\`${P}balance\` — global balance\n\`${P}daily\` — daily reward\n\`${P}work\` — work reward\n\`${P}pay @user <amount>\` — transfer coins\n\`${P}richlist\` — global leaderboard\n\`${P}luck [@user]\` — view luck\n\n**Owner controls**\n\`${P}eco add @user <amount>\`\n\`${P}eco set @user <amount>\`\n\`${P}eco remove @user <amount>\`\n\`${P}eco setluck @user <0-100>\`\n\n🔒 Only economy owner ID **${OWNER_ID}** can modify balances or luck.`)]});
  }
  return null;
 }

 client.on('messageCreate',async m=>{
  try{
   if(m.author.bot||!m.guild||!m.content.startsWith(P))return;
   const parts=m.content.slice(P.length).trim().split(/\s+/);const root=(parts.shift()||'').toLowerCase();
   if(root==='eco')return economy(m,parts);
   if(['balance','bal','money','wallet','daily','work','pay','richlist','leaderboard','top','luck'].includes(root))return economy(m,[root,...parts]);
  }catch(e){console.error('[GLOBAL-ECONOMY]',e)}
 });
};
