const fs=require('fs');const path=require('path');
const {EmbedBuilder,PermissionFlagsBits,ChannelType}=require('discord.js');
module.exports=function attach(client,prefix='.'){
 const P=prefix||'.',file=path.join(process.cwd(),'data','community-suite.json');fs.mkdirSync(path.dirname(file),{recursive:true});let db={};try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{}
 const fresh=()=>({leveling:{enabled:true,cooldown:60,multiplier:1,rewards:{},users:{}},welcome:null,responders:[],embeds:{}});
 const gd=id=>{const g=db[id]||(db[id]=fresh()),f=fresh();for(const k of Object.keys(f))if(g[k]===undefined)g[k]=f[k];return g};const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const E=(t,d)=>new EmbedBuilder().setTitle(`✨ ${t}`).setDescription(d).setColor([0x5865f2,0x7c3aed,0x2563eb,0x06b6d4][Math.floor(Math.random()*4)]).setTimestamp();
 const ok=(m,p)=>m.guild.ownerId===m.author.id||m.member.permissions.has(p);
 const fill=(s,m)=>String(s||'').replaceAll('{user}',`${m}`).replaceAll('{username}',m.user.username).replaceAll('{server}',m.guild.name).replaceAll('{membercount}',String(m.guild.memberCount)).replaceAll('{channel}',`${m.channel}`);
 const xpNeed=l=>100+(l*l*50);
 function levelData(g,id){return g.leveling.users[id]||(g.leveling.users[id]={xp:0,total:0,level:1,last:0})}
 async function levelCommand(m,c,a,g){
  if(c==='leveling'){
   if(!ok(m,PermissionFlagsBits.ManageGuild))return m.reply('🚫 **Manage Server** is required.');
   const s=(a[0]||'status').toLowerCase();if(['on','enable'].includes(s))g.leveling.enabled=true;else if(['off','disable'].includes(s))g.leveling.enabled=false;else if(s==='cooldown'){g.leveling.cooldown=Math.max(5,Math.min(3600,Number(a[1])||60));}else if(s==='multiplier'){g.leveling.multiplier=Math.max(.1,Math.min(10,Number(a[1])||1));}else if(s==='reward'){const level=Number(a[1]),role=m.mentions.roles.first();if(!Number.isInteger(level)||level<1||!role)return m.reply(`Usage: ${P}leveling reward <level> @role`);g.leveling.rewards[level]=role.id;}else if(s==='remove-reward'){delete g.leveling.rewards[a[1]];}else return m.reply({embeds:[E('📈 LEVELING CONFIG',`**Status:** ${g.leveling.enabled?'🟢 Enabled':'🔴 Disabled'}\n**Cooldown:** ${g.leveling.cooldown}s\n**Multiplier:** ${g.leveling.multiplier}x\n**Rewards:** ${Object.keys(g.leveling.rewards).length}`)]});save();return m.reply({embeds:[E('📈 LEVELING UPDATED','Your leveling configuration has been saved.')]});
  }
  if(['level','rank','xp'].includes(c)){
   const target=m.mentions.users.first()||m.author,d=levelData(g,target.id),need=xpNeed(d.level);return m.reply({embeds:[E('📈 LEVEL CARD',`👤 **${target}**\n🏅 **Level:** ${d.level}\n✨ **XP:** ${d.xp.toLocaleString()} / ${need.toLocaleString()}\n📊 **Total XP:** ${d.total.toLocaleString()}\n📈 **Multiplier:** ${g.leveling.multiplier}x`)]});
  }
  if(c==='leaderboard'){
   const top=Object.entries(g.leveling.users).sort((a,b)=>b[1].total-a[1].total).slice(0,10);return m.reply({embeds:[E('🏆 LEVEL LEADERBOARD',top.length?top.map((x,i)=>`**${i+1}.** <@${x[0]}> — Level **${x[1].level}** • **${x[1].total.toLocaleString()} XP**`).join('\n'):'No XP data yet.')]});
  }
  if(c==='setxp'){
   if(!ok(m,PermissionFlagsBits.ManageGuild))return m.reply('🚫 **Manage Server** is required.');const u=m.mentions.users.first(),n=Number(a.find(x=>/^\d+$/.test(x)));if(!u||!Number.isInteger(n)||n<0)return m.reply(`Usage: ${P}setxp @user <xp>`);const d=levelData(g,u.id);d.xp=n;d.total=n;d.level=1;while(d.xp>=xpNeed(d.level)){d.xp-=xpNeed(d.level);d.level++}save();return m.reply(`✅ Set ${u}'s XP.`);
  }
  if(c==='reward'||c==='rewards'){const text=Object.entries(g.leveling.rewards).map(([l,r])=>`🏅 Level **${l}** → <@&${r}>`).join('\n')||'No level rewards configured.';return m.reply({embeds:[E('🎁 LEVEL REWARDS',text)]});}
  return false;
 }
 async function handle(m,c,a){const g=gd(m.guild.id);
  if(['membercount','members'].includes(c))return m.reply({embeds:[E('👥 MEMBER COUNT',`**Total:** ${m.guild.memberCount.toLocaleString()}\n👤 Humans: **${m.guild.members.cache.filter(x=>!x.user.bot).size.toLocaleString()}**\n🤖 Bots: **${m.guild.members.cache.filter(x=>x.user.bot).size.toLocaleString()}**`)]});
  if(c==='serverinfo')return m.reply({embeds:[E('🏠 SERVER INFORMATION',`**${m.guild.name}**\n\n👑 Owner: <@${m.guild.ownerId}>\n👥 Members: **${m.guild.memberCount.toLocaleString()}**\n💬 Channels: **${m.guild.channels.cache.size}**\n🎭 Roles: **${m.guild.roles.cache.size}**\n🚀 Boosts: **${m.guild.premiumSubscriptionCount||0}**\n🆔 ID: \`${m.guild.id}\`\n📅 Created: <t:${Math.floor(m.guild.createdTimestamp/1000)}:D>`)]});
  if(['level','rank','leaderboard','xp','setxp','leveling','reward','rewards'].includes(c))return levelCommand(m,c,a,g);
  if(c==='welcome'){
   if(!ok(m,PermissionFlagsBits.ManageGuild))return m.reply('🚫 **Manage Server** is required.');const sub=(a.shift()||'status').toLowerCase();if(['off','disable'].includes(sub)){g.welcome=null;save();return m.reply('👋 Welcome system disabled.')}const ch=m.mentions.channels.first()||m.channel,text=a.filter(x=>!/^<#\d+>$/.test(x)).join(' ')||'Welcome {user} to **{server}**!';g.welcome={channel:ch.id,message:text};save();return m.reply({embeds:[E('👋 WELCOME CONFIGURED',`**Channel:** ${ch}\n**Message:** ${text}\n\nVariables: \`{user}\` \`{username}\` \`{server}\` \`{membercount}\``)]});
  }
  if(c==='autoresponder'||c==='ar'){
   if(!ok(m,PermissionFlagsBits.ManageGuild))return m.reply('🚫 **Manage Server** is required.');const sub=(a.shift()||'list').toLowerCase();if(['add','create'].includes(sub)){const trigger=(a.shift()||'').toLowerCase(),response=a.join(' ');if(!trigger||!response)return m.reply(`Usage: ${P}autoresponder add <trigger> <response>`);g.responders.push({id:Date.now().toString(36),trigger,response,contains:false,enabled:true});save();return m.reply(`✅ Autoresponder \`${trigger}\` added.`)}if(['remove','delete'].includes(sub)){const id=a.shift();g.responders=g.responders.filter(x=>x.id!==id&&x.trigger!==id);save();return m.reply('🗑️ Autoresponder removed.')}if(sub==='contains'){const id=a.shift(),r=g.responders.find(x=>x.id===id||x.trigger===id);if(!r)return m.reply('❌ Responder not found.');r.contains=true;save();return m.reply('✅ Responder now matches messages containing the trigger.')}if(sub==='enable'||sub==='disable'){const r=g.responders.find(x=>x.id===a[0]||x.trigger===a[0]);if(!r)return m.reply('❌ Responder not found.');r.enabled=sub==='enable';save();return m.reply(`✅ Responder ${r.enabled?'enabled':'disabled'}.`)}return m.reply({embeds:[E('🤖 AUTO RESPONDERS',g.responders.map(r=>`\`${r.id}\` • ${r.enabled?'🟢':'🔴'} • **${r.trigger}**`).join('\n')||'None configured.')]});
  }
  if(c==='embed'||c==='embedcreate'){
   if(!ok(m,PermissionFlagsBits.ManageMessages))return m.reply('🚫 **Manage Messages** is required.');const ch=m.mentions.channels.first()||m.channel;const raw=a.filter(x=>!/^<#\d+>$/.test(x)).join(' ');const parts=raw.split('|').map(x=>x.trim());const title=parts[0]||'Announcement',desc=parts[1]||' ';let color=0x5865f2;if(parts[2]&&/^#?[0-9a-f]{6}$/i.test(parts[2]))color=parseInt(parts[2].replace('#',''),16);const e=new EmbedBuilder().setTitle(`✨ ${fill(title,m)}`).setDescription(fill(desc,m)).setColor(color).setTimestamp();await ch.send({embeds:[e]});return m.reply(`✅ Embed sent to ${ch}.`);
  }
  if(c==='embedhelp')return m.reply({embeds:[E('🧩 EMBED BUILDER',`Usage: \`${P}embed #channel Title | Description | #5865f2\`\nVariables: \`{user}\` \`{username}\` \`{server}\` \`{membercount}\`\n\nThe builder supports configurable title, description and color.`)]});
  if(c==='say'){
   if(!ok(m,PermissionFlagsBits.ManageMessages))return m.reply('🚫 **Manage Messages** is required.');const ch=m.mentions.channels.first()||m.channel,text=a.filter(x=>!/^<#\d+>$/.test(x)).join(' ');if(!text)return m.reply(`Usage: ${P}say [#channel] <message>`);await ch.send({content:fill(text,m)});return m.reply(`✅ Sent to ${ch}.`);
  }
  return false;
 }
 const old=client.listeners('messageCreate').at(-1);if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;const g=gd(m.guild.id);
   if(!m.content.startsWith(P)){
    for(const r of g.responders){if(!r.enabled)continue;const text=m.content.toLowerCase(),hit=r.contains?text.includes(r.trigger):text===r.trigger;if(hit){await m.channel.send(fill(r.response,m)).catch(()=>{});break;}}
    if(g.leveling.enabled){const d=levelData(g,m.author.id),now=Date.now();if(now-d.last>=g.leveling.cooldown*1000){d.last=now;const gain=Math.floor((15+Math.random()*11)*g.leveling.multiplier);d.xp+=gain;d.total+=gain;let leveled=false;while(d.xp>=xpNeed(d.level)){d.xp-=xpNeed(d.level);d.level++;leveled=true;const roleId=g.leveling.rewards[d.level];if(roleId){const role=m.guild.roles.cache.get(roleId);if(role)await m.member.roles.add(role).catch(()=>{});}}if(leveled)m.channel.send({embeds:[E('🎉 LEVEL UP!',`${m.author} reached **Level ${d.level}**!`)]}).catch(()=>{});save();}}
   }else{const parts=m.content.slice(P.length).trim().split(/\s+/);const c=(parts.shift()||'').toLowerCase();if(!(await handle(m,c,parts)))return old(m);}
  }catch(e){console.error('[COMMUNITY SUITE]',e);}})}
 client.on('guildMemberAdd',async member=>{try{const g=gd(member.guild.id);if(g.welcome){const ch=member.guild.channels.cache.get(g.welcome.channel);if(ch?.isTextBased())await ch.send({embeds:[E('👋 WELCOME!',fill(g.welcome.message,{...member,user:member.user,guild:member.guild,channel:ch}))]});}save()}catch(e){console.error('[WELCOME]',e)}});
};
