const fs=require('fs');
const path=require('path');
const {EmbedBuilder}=require('discord.js');

module.exports=function attachEconomyPlus(client,prefix='.'){
 const P=prefix||'.';
 const file=path.join(process.cwd(),'data','global-economy.json');
 fs.mkdirSync(path.dirname(file),{recursive:true});
 const load=()=>{try{return JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{return {users:{}}}};
 const save=db=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const user=(db,id)=>db.users[id]||(db.users[id]={balance:0,daily:0,work:0,luck:0,bank:0,inventory:{}});
 const embed=(t,d)=>new EmbedBuilder().setTitle(t).setDescription(d).setColor(0x5865f2).setTimestamp();
 const shops={coffee:{name:'Coffee',price:50,emoji:'☕'},cookie:{name:'Cookie',price:100,emoji:'🍪'},lucky:{name:'Lucky Charm',price:500,emoji:'🍀'},badge:{name:'Collector Badge',price:1000,emoji:'🏅'}};
 client.on('messageCreate',async m=>{
  try{
   if(m.author.bot||!m.guild||!m.content.startsWith(P))return;
   const p=m.content.slice(P.length).trim().split(/\s+/),root=(p.shift()||'').toLowerCase();
   if(root!=='eco')return;
   const sub=(p.shift()||'help').toLowerCase(),db=load(),me=user(db,m.author.id);
   if(['profile','stats'].includes(sub))return m.reply({embeds:[embed('💰 Economy Profile',`**User:** ${m.author}\n💵 Wallet: **${me.balance.toLocaleString()}**\n🏦 Bank: **${Number(me.bank||0).toLocaleString()}**\n🍀 Luck: **${me.luck||0}**\n🎒 Items: **${Object.values(me.inventory||{}).reduce((a,b)=>a+b,0)}**`)]});
   if(sub==='deposit'||sub==='dep'){
    const n=Number(p[0]);if(!Number.isInteger(n)||n<=0)return m.reply(`Usage: ${P}eco deposit <amount>`);if(n>me.balance)return m.reply('❌ Not enough wallet balance.');me.balance-=n;me.bank=(me.bank||0)+n;save(db);return m.reply(`🏦 Deposited **${n.toLocaleString()}** coins.`);
   }
   if(sub==='withdraw'||sub==='with'){
    const n=Number(p[0]);if(!Number.isInteger(n)||n<=0)return m.reply(`Usage: ${P}eco withdraw <amount>`);if(n>(me.bank||0))return m.reply('❌ Not enough bank balance.');me.bank-=n;me.balance+=n;save(db);return m.reply(`💵 Withdrew **${n.toLocaleString()}** coins.`);
   }
   if(sub==='shop')return m.reply({embeds:[embed('🛒 Economy Shop',Object.entries(shops).map(([id,x])=>`${x.emoji} **${x.name}** — \`${id}\` — **${x.price.toLocaleString()}** coins`).join('\n')+`\n\nBuy with \`${P}eco buy <item> [amount]\``)]});
   if(sub==='buy'){
    const item=shops[(p[0]||'').toLowerCase()];const n=Math.max(1,Math.min(99,Number(p[1])||1));if(!item)return m.reply(`❌ Item not found. Use ${P}eco shop.`);const total=item.price*n;if(me.balance<total)return m.reply(`❌ You need **${total.toLocaleString()}** coins.`);me.balance-=total;me.inventory=item.id?me.inventory:{};const key=Object.keys(shops).find(k=>shops[k]===item);me.inventory[key]=(me.inventory[key]||0)+n;save(db);return m.reply(`🛒 Bought **${n}× ${item.name}** for **${total.toLocaleString()}** coins.`);
   }
   if(sub==='inventory'||sub==='inv'){
    const rows=Object.entries(me.inventory||{}).filter(([,n])=>n>0).map(([id,n])=>`${shops[id]?.emoji||'📦'} **${shops[id]?.name||id}** × ${n}`);return m.reply({embeds:[embed('🎒 Inventory',rows.length?rows.join('\n'):'Your inventory is empty.')]});
   }
   if(sub==='help')return m.reply({embeds:[embed('💰 Economy Plus',`\`${P}balance\` • wallet\n\`${P}daily\` • daily reward\n\`${P}work\` • work reward\n\`${P}pay @user <amount>\` • transfer\n\`${P}eco profile\` • wallet/bank/profile\n\`${P}eco deposit <amount>\` • bank\n\`${P}eco withdraw <amount>\` • bank\n\`${P}eco shop\` • shop\n\`${P}eco buy <item> [amount]\` • purchase\n\`${P}eco inventory\` • items`)]});
  }catch(e){console.error('[ECONOMY-PLUS]',e?.stack||e)}
 });
};
