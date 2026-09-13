const fs=require('fs');
const path=require('path');
const {ChannelType,PermissionFlagsBits,EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle,StringSelectMenuBuilder}=require('discord.js');

module.exports=function attachEnhancements(client,prefix='.'){
 const P=prefix||'.';
 const DATA=path.join(process.cwd(),'data');
 const FILE=path.join(DATA,'enhancements.json');
 if(!fs.existsSync(DATA))fs.mkdirSync(DATA,{recursive:true});
 let db={};try{db=JSON.parse(fs.readFileSync(FILE,'utf8')||'{}')}catch{db={}};
 const save=()=>fs.writeFileSync(FILE,JSON.stringify(db,null,2));
 const guild=id=>db[id]||(db[id]={afk:{},logs:{}});
 const clean=(v,n=900)=>String(v??'').replace(/`/g,'').slice(0,n);
 const em=(t,d)=>new EmbedBuilder().setTitle(t).setDescription(d).setColor(0x5865f2).setTimestamp();
 const music=['play','p','join','connect','leave','disconnect','pause','resume','unpause','skip','next','stop','queue','q','nowplaying','np','current','volume','vol','loop','repeat','shuffle','remove','move','clearqueue','musichelp'];
 const categories={
  home:{name:'🏠 Home',cmds:['help','ping','botinfo','invite']},
  music:{name:'🎧 Music',cmds:music},
  moderation:{name:'🛡️ Moderation',cmds:['kick','ban','unban','timeout','untimeout','warn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','softban','unwarn','massrole']},
  security:{name:'🛡️ Security',cmds:['automod','antiraid','antinuke','security','filter','verify']},
  logging:{name:'📋 Logging',cmds:['logsetup','logsettings','logevents','logtest','setlog','logdisable']},
  leveling:{name:'📈 Leveling',cmds:['level','rank','leaderboard','xp','setxp','leveling','reward','rewards']},
  economy:{name:'💰 Economy',cmds:['balance','daily','work','deposit','withdraw','pay','economy','richlist']},
  tickets:{name:'🎫 Tickets',cmds:['ticket','ticket-panel','open','close','claim','unclaim','ticket-setup']},
  roles:{name:'🎭 Roles',cmds:['role','autorole','reactionrole','levelrole','roleall']},
  welcome:{name:'👋 Welcome',cmds:['welcome','setwelcome','setwelcome-message','goodbye']},
  voice:{name:'🔊 Voice',cmds:['tempvoice','voice']},
  starboard:{name:'⭐ Starboard',cmds:['starboard']},
  afk:{name:'💤 AFK',cmds:['afk']},
  applications:{name:'📝 Applications',cmds:['apply','applications','application-setup','application-questions']},
  announcements:{name:'📢 Announcements',cmds:['announce','say','embed','poll','announce-embed']},
  utility:{name:'🛠️ Utility',cmds:['serverinfo','userinfo','avatar','roleinfo','channelinfo','membercount','servericon','config','prefix','enable','disable','permissions','channel']},
  fun:{name:'🎉 Fun',cmds:['8ball','eightball','coinflip','roll','choose','ship','rate','reverse']},
  custom:{name:'⚙️ Custom',cmds:['customcommand','cc','cc-delete','cc-list']},
  reminders:{name:'⏰ Reminders',cmds:['remind','reminders']}
 };
 const pretty=x=>x.replace(/^\w/,m=>m.toUpperCase());
 function helpPayload(cat='home'){
  if(!categories[cat])cat='home';
  const c=categories[cat];
  if(cat==='home'){
   const rows=Object.entries(categories).map(([k,v])=>`> **${v.name}**  •  \`${P}help ${k}\``).join('\n');
   return {embeds:[em('✨ LIGHTCORE • HELP CENTER',`**Prefix:** \`${P}\`\n\n${rows}\n\n> 💫 Select a category below to browse commands.`)],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('lc_help_enhanced').setPlaceholder('✨ Browse command categories').addOptions(Object.entries(categories).map(([k,v])=>({label:pretty(v.name.replace(/^\S+\s/,'')),value:k,emoji:v.name.split(' ')[0]}))))]};
  }
  const chunks=[];for(let i=0;i<c.cmds.length;i+=10)chunks.push(c.cmds.slice(i,i+10).map(x=>`\`${P}${x}\``).join('  •  '));
  return {embeds:[em(`${c.name} • COMMANDS`,`> ✦ **${c.cmds.length}** commands\n\n${chunks.join('\n\n')}`)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_help_home').setLabel('Help Home').setEmoji('🏠').setStyle(ButtonStyle.Secondary))]};
 }
 function ensureLogs(g){g.logs||={};return g.logs;}
 const LOG_TYPES=['messages','members','moderation','roles','channels','voice','server','invites','threads','automod','boosts'];
 const LOG_NAMES={messages:'💬・message-logs',members:'👥・member-logs',moderation:'🛡️・moderation-logs',roles:'🎭・role-logs',channels:'📝・channel-logs',voice:'🔊・voice-logs',server:'⚙️・server-logs',invites:'🔗・invite-logs',threads:'🧵・thread-logs',automod:'🤖・automod-logs',boosts:'🚀・boost-logs'};
 const logTitles={messages:'Message Logs',members:'Member Logs',moderation:'Moderation Logs',roles:'Role Logs',channels:'Channel Logs',voice:'Voice Logs',server:'Server Logs',invites:'Invite Logs',threads:'Thread Logs',automod:'Automod Logs',boosts:'Boost Logs'};
 async function ensureLogChannel(guild,type){
  const g=guild(id=guild.id),l=ensureLogs(g);let category=l.category?guild.channels.cache.get(l.category):null;
  if(!category)category=guild.channels.cache.find(c=>c.type===ChannelType.GuildCategory&&c.name==='📋・LOGS');
  if(!category)category=await guild.channels.create({name:'📋・LOGS',type:ChannelType.GuildCategory});
  l.category=category.id;
  let ch=l[type]?guild.channels.cache.get(l[type]):null;
  if(!ch)ch=guild.channels.cache.find(c=>c.parentId===category.id&&c.name===LOG_NAMES[type]);
  if(!ch)ch=await guild.channels.create({name:LOG_NAMES[type],type:ChannelType.GuildText,parent:category.id});
  l[type]=ch.id;save();return ch;
 }
 async function log(guild,type,title,text){const l=ensureLogs(guild(id=guild.id));const id=l[type];if(!id)return;const ch=client.channels.cache.get(id);if(ch?.isTextBased())await ch.send({embeds:[em(title,text)]}).catch(()=>{});}
 async function setupLogs(m,only){
  if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return m.reply('❌ Manage Server required.');
  const types=only&&LOG_TYPES.includes(only)?[only]:LOG_TYPES;
  for(const t of types)await ensureLogChannel(m.guild,t);
  const l=ensureLogs(guild(m.guild.id));
  return m.reply({embeds:[em('📋 LOGGING SYSTEM READY',`Configured **${types.length}** separate log streams.\n\n${types.map(t=>`${LOG_NAMES[t]}  →  <#${l[t]}>`).join('\n')}\n\nUse \`${P}setlog <type> #channel\` to move one stream without affecting the others.`)]});
 }
 async function handle(m,c,a){
  if(!m.guild)return false;
  if(c==='help'||c==='h'){return m.reply(helpPayload((a[0]||'home').toLowerCase()));}
  if(c==='musichelp'||c==='music'){return m.reply(helpPayload('music'));}
  if(c==='afk'){
   const g=guild(m.guild.id),reason=clean(a.join(' '),180)||'AFK';g.afk[m.author.id]={reason,at:Date.now()};save();
   return m.reply({embeds:[em('💤 AFK MODE ENABLED',`> 🌙 **${m.author} is now AFK**\n>\n> **Reason:** ${reason}\n> **Since:** <t:${Math.floor(Date.now()/1000)}:R>`)]});
  }
  if(c==='logsetup')return setupLogs(m,a[0]?.toLowerCase());
  if(c==='setlog'){
   if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return m.reply('❌ Manage Server required.');
   const type=(a[0]||'').toLowerCase(),ch=m.mentions.channels.first();if(!LOG_TYPES.includes(type)||!ch)return m.reply(`Usage: ${P}setlog <${LOG_TYPES.join('|')}> #channel`);
   const l=ensureLogs(guild(m.guild.id));l[type]=ch.id;save();return m.reply(`✅ ${logTitles[type]} → ${ch}`);
  }
  if(c==='logdisable'){
   if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return m.reply('❌ Manage Server required.');
   const type=(a[0]||'').toLowerCase();if(!LOG_TYPES.includes(type))return m.reply(`Usage: ${P}logdisable <${LOG_TYPES.join('|')}>`);const l=ensureLogs(guild(m.guild.id));delete l[type];save();return m.reply(`🔕 ${logTitles[type]} disabled.`);
  }
  if(c==='logsettings'){
   const l=ensureLogs(guild(m.guild.id));return m.reply({embeds:[em('📋 LOG SETTINGS',LOG_TYPES.map(t=>`${LOG_NAMES[t]}  •  ${l[t]?`<#${l[t]}>`:'OFF'}`).join('\n'))]});
  }
  if(c==='logevents')return m.reply({embeds:[em('📚 LOG EVENTS',LOG_TYPES.map(t=>`**${pretty(t)}** — ${logTitles[t]}`).join('\n'))]});
  if(c==='logtest'){const l=ensureLogs(guild(m.guild.id));for(const t of LOG_TYPES)if(l[t])await log(m.guild,t,'🧪 Log Test',`Test event for **${logTitles[t]}**.`);return m.reply('✅ Test sent to every configured log stream.');}
  return false;
 }
 const old=client.listeners('messageCreate').at(-1);
 if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{
  try{
   if(m.author.bot||!m.guild)return;
   const c0=m.content||'';
   const g=guild(m.guild.id);
   if(g.afk[m.author.id]&&!c0.startsWith(P)){delete g.afk[m.author.id];save();m.reply({embeds:[em('👋 WELCOME BACK',`> ✨ Welcome back ${m.author}! Your AFK status has been removed.`)]}).catch(()=>{});}
   for(const id of m.mentions.users.keys())if(id!==m.author.id&&g.afk[id]){const x=g.afk[id];m.reply({embeds:[em('💤 USER IS AFK',`> 👤 <@${id}> is currently AFK.\n> 💬 **Reason:** ${clean(x.reason,180)}\n> ⏱️ **Since:** <t:${Math.floor(x.at/1000)}:R>`)]}).catch(()=>{});break;}
   if(!c0.startsWith(P))return old(m);
   const parts=c0.slice(P.length).trim().split(/\s+/);const c=(parts.shift()||'').toLowerCase();if(!(await handle(m,c,parts)))return old(m);
  }catch(e){console.error('[ENHANCEMENTS]',e);}
 });}
 // Replace the old two-stream logger listeners with per-event streams. Only listeners that are clearly logger handlers are removed.
 const events=['messageDelete','messageUpdate','messageDeleteBulk','guildMemberAdd','guildMemberRemove','guildMemberUpdate','guildBanAdd','guildBanRemove','roleCreate','roleDelete','channelCreate','channelDelete','channelUpdate','voiceStateUpdate','inviteCreate','threadCreate','threadDelete'];
 for(const ev of events){for(const fn of client.listeners(ev)){const s=Function.prototype.toString.call(fn);if(s.includes('sendLog('))client.removeListener(ev,fn);}}
 client.on('messageDelete',m=>{if(m.guild&&!m.author?.bot)log(m.guild,'messages','🗑️ Message Deleted',`**Author:** ${m.author||'Unknown'}\n**Channel:** ${m.channel}\n**Content:** ${clean(m.content)||'Unavailable'}`);});
 client.on('messageUpdate',(o,n)=>{if(n.guild&&!n.author?.bot&&o.content!==n.content)log(n.guild,'messages','✏️ Message Edited',`**Author:** ${n.author}\n**Channel:** ${n.channel}\n**Before:** ${clean(o.content)||'Unavailable'}\n**After:** ${clean(n.content)||'Unavailable'}`);});
 client.on('messageDeleteBulk',(col,ch)=>log(ch.guild,'messages','🧹 Bulk Delete',`**Channel:** ${ch}\n**Messages:** ${col.size}`));
 client.on('guildMemberAdd',m=>log(m.guild,'members','📥 Member Joined',`**User:** ${m.user}\n**ID:** \`${m.id}\`\n**Account:** <t:${Math.floor(m.user.createdTimestamp/1000)}:R>`));
 client.on('guildMemberRemove',m=>log(m.guild,'members','📤 Member Left',`**User:** ${m.user}\n**ID:** \`${m.id}\``));
 client.on('guildMemberUpdate',(o,n)=>{const changes=[];if(o.nickname!==n.nickname)changes.push(`Nickname: **${o.nickname||'none'}** → **${n.nickname||'none'}**`);if(o.roles.cache.size!==n.roles.cache.size)changes.push(`Roles: **${o.roles.cache.size}** → **${n.roles.cache.size}**`);if(changes.length)log(n.guild,'members','📝 Member Updated',`**User:** ${n.user}\n${changes.join('\n')}`);});
 client.on('guildBanAdd',b=>log(b.guild,'moderation','🔨 Member Banned',`**User:** ${b.user}`));
 client.on('guildBanRemove',b=>log(b.guild,'moderation','🔓 Member Unbanned',`**User:** ${b.user}`));
 client.on('roleCreate',r=>log(r.guild,'roles','➕ Role Created',`**Role:** ${r}`));
 client.on('roleDelete',r=>log(r.guild,'roles','🗑️ Role Deleted',`**Role:** ${r.name}\n**ID:** \`${r.id}\``));
 client.on('channelCreate',c=>log(c.guild,'channels','➕ Channel Created',`**Channel:** ${c}\n**Type:** ${c.type}`));
 client.on('channelDelete',c=>log(c.guild,'channels','🗑️ Channel Deleted',`**Name:** ${c.name}\n**ID:** \`${c.id}\``));
 client.on('channelUpdate',(o,n)=>log(n.guild,'channels','📝 Channel Updated',`**Channel:** ${n}\n**Name:** ${o.name} → ${n.name}`));
 client.on('voiceStateUpdate',(o,n)=>{if(o.channelId!==n.channelId)log(n.guild,'voice','🔊 Voice State',`**User:** ${n.member?.user||o.member?.user}\n**From:** ${o.channel?o.channel.name:'None'}\n**To:** ${n.channel?n.channel.name:'None'}`);});
 client.on('inviteCreate',i=>log(i.guild,'invites','🔗 Invite Created',`**Code:** \`${i.code}\`\n**Channel:** ${i.channel}`));
 client.on('threadCreate',t=>log(t.guild,'threads','🧵 Thread Created',`**Thread:** ${t}`));
 client.on('threadDelete',t=>log(t.guild,'threads','🗑️ Thread Deleted',`**Thread:** ${t.name}\n**ID:** \`${t.id}\``));
 client.on('guildMemberUpdate',(o,n)=>{if(n.premiumSince&&!o.premiumSince)log(n.guild,'boosts','🚀 Server Boost',`**User:** ${n.user} boosted the server.`);});
 client.on('interactionCreate',async i=>{try{if(i.isStringSelectMenu()&&i.customId==='lc_help_enhanced'){return i.update(helpPayload(i.values[0]));}if(i.isButton()&&i.customId==='lc_help_home'){return i.update(helpPayload('home'));}}catch(e){console.error('[HELP UI]',e);}});
 console.log('[ENHANCEMENTS] Music help + AFK + per-event logging loaded.');
};
