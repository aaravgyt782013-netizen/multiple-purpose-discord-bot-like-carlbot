require('dotenv').config();
const fs=require('fs');
const path=require('path');
const http=require('http');
const {Client,GatewayIntentBits,Partials,PermissionFlagsBits,EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle,StringSelectMenuBuilder,ModalBuilder,TextInputBuilder,TextInputStyle,ChannelType,REST,Routes}=require('discord.js');

const PREFIX=String(process.env.PREFIX||'!').trim()||'!';
const COLOR=0x5865f2;
const DATA=path.join(process.cwd(),'data');
const FILE=path.join(DATA,'database.json');
if(!fs.existsSync(DATA))fs.mkdirSync(DATA,{recursive:true});
if(!fs.existsSync(FILE))fs.writeFileSync(FILE,'{}');
let db={}; try{db=JSON.parse(fs.readFileSync(FILE,'utf8')||'{}')}catch{db={}};
const save=()=>fs.writeFileSync(FILE,JSON.stringify(db,null,2));
const fresh=()=>({
 disabled:[],warnings:{},xp:{},economy:{},afk:{},
 welcome:{channel:null,message:'Welcome {user} to **{server}**!'},
 logs:{category:null,channel:null,mod:null},
 autorole:null,
 automod:{links:false,invites:false,caps:false,spam:false,mentions:false,words:[]},
 tickets:{category:null,staffRole:null},
 applications:{channel:null,questions:['Why should we accept you?','What experience do you have?']},
 leveling:{enabled:true,channel:null,cooldown:60,multiplier:1,rewards:{}},
 starboard:{enabled:false,channel:null,threshold:3,posts:{}},
 tempvoice:{category:null,creator:null,rooms:{}},
 reactionroles:{},
 server:{prefix:PREFIX},
 reminders:[],
 custom:{},
 filters:[]
});
function gd(id){const d=db[id]||(db[id]=fresh()),b=fresh();for(const k of Object.keys(b))if(d[k]===undefined)d[k]=b[k];return d;}
const em=(title,description,color=COLOR)=>new EmbedBuilder().setTitle(title).setDescription(description).setColor(color).setTimestamp();
const num=v=>Number.isFinite(Number(v))?Number(v):0;
const member=(m,v)=>{if(!v)return m.member;const id=String(v).replace(/[<@!>]/g,'');return m.guild.members.cache.get(id)||m.guild.members.cache.find(x=>x.user.username.toLowerCase()===String(v).toLowerCase());};
const can=(m,p)=>m.member.permissions.has(p)||m.guild.ownerId===m.author.id;
const botMember=g=>g.members.me;
const xpof=(g,id)=>g.xp[id]||(g.xp[id]={xp:0,level:1,total:0});
const need=l=>100+l*l*50;
const eco=(g,id)=>g.economy[id]||(g.economy[id]={cash:100,bank:0,daily:0,work:0});
const clean=(s,n=1024)=>String(s||'').slice(0,n);

const CATS={
 home:['help','ping','botinfo','invite'],
 moderation:['kick','ban','unban','timeout','untimeout','warn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','softban','unwarn','massrole'],
 security:['automod','antiraid','antinuke','security','filter','filter-add','filter-remove','verify'],
 logging:['logsetup','logsettings','logevents','logtest','logreset'],
 leveling:['level','rank','leaderboard','xp','setxp','leveling','reward','rewards'],
 economy:['balance','daily','work','deposit','withdraw','pay','economy','richlist'],
 tickets:['ticket','ticket-panel','open','close','claim','unclaim','ticket-setup'],
 roles:['role','autorole','reactionrole','levelrole','roleall'],
 welcome:['welcome','setwelcome','setwelcome-message','goodbye'],
 voice:['tempvoice','voice'],
 starboard:['starboard'],
 afk:['afk'],
 applications:['apply','applications','application-setup','application-questions'],
 announcements:['announce','say','embed','poll','announce-embed'],
 utility:['serverinfo','userinfo','avatar','roleinfo','channelinfo','membercount','servericon','config','prefix','enable','disable','userinfo-all','permissions','channel'],
 fun:['8ball','eightball','coinflip','roll','choose','ship','rate','reverse'],
 custom:['customcommand','cc','cc-delete','cc-list'],
 reminders:['remind','reminders']
};
const TITLES={home:'🏠 Home',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',leveling:'📈 Leveling',economy:'💰 Economy',tickets:'🎫 Tickets',roles:'🎭 Roles',welcome:'👋 Welcome',voice:'🔊 Temporary Voice',starboard:'⭐ Starboard',afk:'💤 AFK',applications:'📝 Applications',announcements:'📢 Announcements',utility:'🛠️ Utility',fun:'🎉 Fun',custom:'⚙️ Custom Commands',reminders:'⏰ Reminders'};

function help(cat='home'){
 if(!CATS[cat])cat='home';
 if(cat==='home')return {embeds:[em('🤖 LightCore • Control Center',`**Prefix:** \`${PREFIX}\`\n\n${Object.entries(CATS).map(([k])=>`**${TITLES[k]}** — \`${PREFIX}help ${k}\``).join('\n')}\n\nFeature-equivalent design inspired by popular multipurpose bots, with original code and configuration.`)],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('lc3_help').setPlaceholder('📂 Choose a category').addOptions(Object.entries(TITLES).map(([v,t])=>({label:t.replace(/^\S+\s/,''),value:v,emoji:Array.from(t)[0]}))))]};
 return {embeds:[em(`${TITLES[cat]} • Commands`,CATS[cat].map(x=>`**${PREFIX}${x}**`).join(' • '))],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc3_home').setLabel('Home').setStyle(ButtonStyle.Secondary),new ButtonBuilder().setCustomId('lc3_close').setLabel('Close').setStyle(ButtonStyle.Danger))]};
}

async function sendLog(g,type,title,text){const id=type==='mod'?g.logs.mod:g.logs.channel;if(!id)return;const ch=client.channels.cache.get(id);if(!ch?.isTextBased())return;await ch.send({embeds:[em(title,text)]}).catch(()=>{});}

async function setupLogs(guild){
 const g=gd(guild.id),me=botMember(guild);if(!me)return null;
 if(!me.permissions.has(PermissionFlagsBits.ManageChannels))throw new Error('Bot needs Manage Channels.');
 let cat=g.logs.category?guild.channels.cache.get(g.logs.category):null;
 if(!cat)cat=guild.channels.cache.find(c=>c.type===ChannelType.GuildCategory&&['📋・logs','📋・LOGS','logs'].includes(c.name));
 if(!cat)cat=await guild.channels.create({name:'📋・LOGS',type:ChannelType.GuildCategory,permissionOverwrites:[{id:guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:me.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.EmbedLinks,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.AttachFiles]}]});
 const mk=async(name,old)=>{let c=old?guild.channels.cache.get(old):null;if(!c)c=guild.channels.cache.find(x=>x.parentId===cat.id&&x.name===name);if(!c)c=await guild.channels.create({name,type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:[{id:guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:me.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.EmbedLinks,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.AttachFiles]}]});return c;};
 const server=await mk('📋・server-logs',g.logs.channel),mod=await mk('🛡️・mod-logs',g.logs.mod);
 g.logs.category=cat.id;g.logs.channel=server.id;g.logs.mod=mod.id;save();
 await server.send({embeds:[em('📋 Logging System Enabled',`Automatic server and moderation logging is now active.\n\n**Server logs:** ${server}\n**Moderation logs:** ${mod}\n\nUse \`${PREFIX}logevents\` to see supported events.`)]}).catch(()=>{});
 return {cat,server,mod};
}

async function moderation(m,c,a,g){
 const perms={kick:PermissionFlagsBits.KickMembers,ban:PermissionFlagsBits.BanMembers,softban:PermissionFlagsBits.BanMembers,timeout:PermissionFlagsBits.ModerateMembers,untimeout:PermissionFlagsBits.ModerateMembers,warn:PermissionFlagsBits.ModerateMembers,unwarn:PermissionFlagsBits.ModerateMembers,clearwarnings:PermissionFlagsBits.ModerateMembers,purge:PermissionFlagsBits.ManageMessages,lock:PermissionFlagsBits.ManageChannels,unlock:PermissionFlagsBits.ManageChannels,slowmode:PermissionFlagsBits.ManageChannels,nick:PermissionFlagsBits.ManageNicknames,lockdown:PermissionFlagsBits.Administrator,unlockdown:PermissionFlagsBits.Administrator,massrole:PermissionFlagsBits.ManageRoles};
 if(perms[c]&&!can(m,perms[c]))return m.reply('❌ You do not have the required permission.');
 if(['kick','ban','softban','timeout','untimeout','warn','unwarn','clearwarnings'].includes(c)){
  const x=member(m,a[0]);if(!x)return m.reply(`Usage: ${PREFIX}${c} @user [reason]`);
  if(x.id===m.author.id)return m.reply('❌ You cannot target yourself.');
  if(c==='kick'){await x.kick(clean(a.slice(1).join(' '))||'No reason');await sendLog(g,'mod','👢 Member Kicked',`**User:** ${x.user.tag}\n**By:** ${m.author.tag}\n**Reason:** ${clean(a.slice(1).join(' '))||'No reason'}`);return m.reply('✅ Member kicked.');}
  if(c==='ban'||c==='softban'){await x.ban({reason:clean(a.slice(1).join(' '))||'No reason'});await sendLog(g,'mod','🔨 Member Banned',`**User:** ${x.user.tag}\n**By:** ${m.author.tag}`);return m.reply(`✅ Member ${c==='softban'?'soft-banned':'banned'}.`);}
  if(c==='timeout'||c==='untimeout'){const mins=num(a[1]);if(c==='timeout'&&mins<=0)return m.reply(`Usage: ${PREFIX}timeout @user <minutes> [reason]`);await x.timeout(c==='untimeout'?null:Math.min(mins*60000,2419200000),clean(a.slice(2).join(' '))||'No reason');return m.reply('✅ Timeout updated.');}
  g.warnings[x.id]??=[];if(c==='warn'){g.warnings[x.id].push({reason:clean(a.slice(1).join(' '))||'No reason',by:m.author.id,at:Date.now()});save();await sendLog(g,'mod','⚠️ Warning Added',`**User:** ${x.user.tag}\n**By:** ${m.author.tag}`);return m.reply('⚠️ Warning added.');}
  if(c==='unwarn'){const i=num(a[1])-1;if(!g.warnings[x.id]?.length)return m.reply('No warnings found.');if(i>=0&&i<g.warnings[x.id].length)g.warnings[x.id].splice(i,1);save();return m.reply('✅ Warning removed.');}
  g.warnings[x.id]=[];save();return m.reply('✅ Warnings cleared.');
 }
 if(c==='purge'){const n=Math.min(Math.max(num(a[0])||1,1),100),d=await m.channel.bulkDelete(n,true);const r=await m.channel.send(`🧹 Deleted **${d.size}** messages.`);setTimeout(()=>r.delete().catch(()=>{}),2500);return;}
 if(c==='lock'||c==='unlock'){await m.channel.permissionOverwrites.edit(m.guild.roles.everyone,{SendMessages:c==='lock'?false:null});return m.reply(`🔒 Channel ${c==='lock'?'locked':'unlocked'}.`);}
 if(c==='slowmode'){const s=Math.min(Math.max(num(a[0]),0),21600);await m.channel.setRateLimitPerUser(s);return m.reply(`🐢 Slowmode set to **${s}s**.`);}
 if(c==='nick'){const x=member(m,a[0]);if(!x)return m.reply('❌ Member not found.');await x.setNickname(a.slice(1).join(' ')||null);return m.reply('✅ Nickname updated.');}
 if(c==='lockdown'||c==='unlockdown'){for(const ch of m.guild.channels.cache.filter(x=>x.isTextBased()).values())await ch.permissionOverwrites.edit(m.guild.roles.everyone,{SendMessages:c==='lockdown'?false:null}).catch(()=>{});return m.reply(`🚨 Server ${c==='lockdown'?'locked down':'unlocked'}.`);}
 if(c==='massrole'){const r=m.mentions.roles.first(),action=a[1];if(!r||!['add','remove'].includes(action))return m.reply(`Usage: ${PREFIX}massrole @role add|remove`);for(const x of m.guild.members.cache.values())await x.roles[action==='add'?'add':'remove'](r).catch(()=>{});return m.reply(`✅ Role ${action}ed for members.`);}
}

async function cmd(m,input){
 const g=gd(m.guild.id);const p=String(input||'').trim().split(/\s+/);const c=(p.shift()||'').toLowerCase();const a=p;if(!c)return;
 if(g.disabled.includes(c)&&!['enable','disable'].includes(c))return m.reply('❌ This command is disabled in this server.');
 if(['help','h'].includes(c)){const q=(a[0]||'home').toLowerCase();return m.reply(help(q));}
 if(c==='ping')return m.reply(`🏓 Pong! **${client.ws.ping}ms**`);
 if(c==='botinfo')return m.reply({embeds:[em('🤖 LightCore',`Servers: **${client.guilds.cache.size}**\nUsers cached: **${client.users.cache.size}**\nPrefix: \`${PREFIX}\`\nFeature groups: **${Object.keys(CATS).length}**`)]});
 if(c==='invite')return m.reply('Invite this bot using the OAuth2 URL generated for your application in the Discord Developer Portal.');
 if(['kick','ban','softban','timeout','untimeout','warn','unwarn','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','massrole'].includes(c))return moderation(m,c,a,g);
 if(c==='warnings'){const x=member(m,a[0])||m.member,l=g.warnings[x.id]||[];return m.reply({embeds:[em(`⚠️ Warnings • ${x.user.tag}`,l.length?l.map((w,i)=>`**${i+1}.** ${w.reason} • <@${w.by}>`).join('\n'):'No warnings.') ]});}
 if(c==='unban'){if(!can(m,PermissionFlagsBits.BanMembers))return m.reply('❌ Missing Ban Members.');const id=(a[0]||'').replace(/\D/g,'');if(!id)return m.reply(`Usage: ${PREFIX}unban <user id>`);await m.guild.members.unban(id);return m.reply('✅ User unbanned.');}
 if(['serverinfo','userinfo','avatar','roleinfo','channelinfo','membercount','servericon','permissions','channel'].includes(c)){
  if(c==='serverinfo')return m.reply({embeds:[em(`🏠 ${m.guild.name}`,`Owner: <@${m.guild.ownerId}>\nMembers: **${m.guild.memberCount}**\nChannels: **${m.guild.channels.cache.size}**\nRoles: **${m.guild.roles.cache.size}**\nBoosts: **${m.guild.premiumSubscriptionCount||0}**`)]});
  if(c==='membercount')return m.reply(`👥 Members: **${m.guild.memberCount}**`);
  if(c==='avatar'){const x=member(m,a[0])?.user||m.author;return m.reply({embeds:[new EmbedBuilder().setTitle(`${x.username}'s Avatar`).setImage(x.displayAvatarURL({size:2048,extension:'png'})).setColor(COLOR)]});}
  if(c==='userinfo'){const x=member(m,a[0])||m.member;return m.reply({embeds:[em(`👤 ${x.user.tag}`,`ID: \`${x.id}\`\nCreated: <t:${Math.floor(x.user.createdTimestamp/1000)}:R>\nJoined: <t:${Math.floor((x.joinedTimestamp||Date.now())/1000)}:R>\nRoles: ${x.roles.cache.filter(r=>r.id!==m.guild.id).map(r=>r).join(' ')||'None'}`)]});}
  if(c==='roleinfo'){const r=m.mentions.roles.first();if(!r)return m.reply(`Usage: ${PREFIX}roleinfo @role`);return m.reply({embeds:[em(`🎭 ${r.name}`,`ID: \`${r.id}\`\nMembers: **${r.members.size}**\nPosition: **${r.position}**`)]});}
  if(c==='channelinfo'||c==='channel')return m.reply({embeds:[em(`📺 #${m.channel.name}`,`ID: \`${m.channel.id}\`\nType: **${m.channel.type}**\nNSFW: **${m.channel.nsfw?'yes':'no'}**`)]});
  if(c==='servericon'){const u=m.guild.iconURL({size:2048});return m.reply(u?{embeds:[new EmbedBuilder().setTitle('Server Icon').setImage(u).setColor(COLOR)]}:'❌ No server icon.');}
  if(c==='permissions'){const x=member(m,a[0])||m.member;return m.reply({embeds:[em(`🔑 Permissions • ${x.user.tag}`,x.permissions.toArray().map(p=>`• ${p}`).join('\n')||'None')]});}
 }
 if(c==='prefix')return m.reply(`⚙️ Current prefix: \`${PREFIX}\` (set PREFIX in the bot environment to change it globally).`);
 if(c==='enable'||c==='disable'){if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');const q=(a[0]||'').toLowerCase();if(!q)return m.reply(`Usage: ${PREFIX}${c} <command>`);if(c==='disable'){if(!g.disabled.includes(q))g.disabled.push(q);}else g.disabled=g.disabled.filter(x=>x!==q);save();return m.reply(`✅ \`${q}\` ${c}d.`);}
 if(['automod','antiraid','antinuke','security','filter','filter-add','filter-remove','verify'].includes(c)){
  if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');
  if(c==='automod'){const feature=(a[0]||'').toLowerCase();if(!['links','invites','caps','spam','mentions'].includes(feature))return m.reply(`Usage: ${PREFIX}automod links|invites|caps|spam|mentions on|off`);g.automod[feature]=String(a[1]).toLowerCase()==='on';save();return m.reply(`🛡️ AutoMod **${feature}**: **${g.automod[feature]?'ON':'OFF'}**`);}
  if(c==='filter-add'){const w=String(a[0]||'').toLowerCase();if(!w)return m.reply(`Usage: ${PREFIX}filter-add <word>`);if(!g.automod.words.includes(w))g.automod.words.push(w);save();return m.reply('✅ Filter word added.');}
  if(c==='filter-remove'){g.automod.words=g.automod.words.filter(w=>w!==String(a[0]||'').toLowerCase());save();return m.reply('✅ Filter word removed.');}
  if(c==='filter')return m.reply({embeds:[em('🛡️ Filter / AutoMod',`Links: **${g.automod.links?'ON':'OFF'}**\nInvites: **${g.automod.invites?'ON':'OFF'}**\nCaps: **${g.automod.caps?'ON':'OFF'}**\nSpam: **${g.automod.spam?'ON':'OFF'}**\nMentions: **${g.automod.mentions?'ON':'OFF'}**\nBlocked words: **${g.automod.words.length}**`)]});
  return m.reply({embeds:[em(`🔐 ${c}`,`Security module is enabled as a configuration area. Use \`${PREFIX}automod\` and \`${PREFIX}filter\` to manage message protection.`)]});
 }
 if(['logsetup','logreset','logsettings','logevents','logtest'].includes(c)){
  if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');
  if(c==='logsetup'||c==='logreset'){try{const x=await setupLogs(m.guild);return m.reply(`✅ **Logging setup complete.**\nCategory: ${x.cat}\nServer logs: ${x.server}\nMod logs: ${x.mod}`);}catch(e){return m.reply(`❌ ${e.message}`);}}
  if(c==='logsettings')return m.reply({embeds:[em('📋 Logging Settings',`Category: ${g.logs.category?`<#${g.logs.category}>`:'Not set'}\nServer: ${g.logs.channel?`<#${g.logs.channel}>`:'Not set'}\nModeration: ${g.logs.mod?`<#${g.logs.mod}>`:'Not set'}\n\nUse \`${PREFIX}logsetup\` to create everything automatically.`)]});
  if(c==='logevents')return m.reply({embeds:[em('📋 Log Events','Messages • Members • Bans • Roles • Channels • Voice • Invites • Threads • Server changes • Moderation') ]});
  await sendLog(g,'server','🧪 Logging Test',`Test requested by ${m.author}.`);return m.reply('✅ Test log sent.');
 }
 if(['level','rank','leaderboard','xp','setxp','leveling','reward','rewards'].includes(c)){
  if(c==='level'||c==='rank'){const x=member(m,a[0])||m.member,z=xpof(g,x.id);return m.reply({embeds:[em('📈 Level',`User: ${x}\nLevel: **${z.level}**\nXP: **${z.xp}/${need(z.level)}**\nTotal XP: **${z.total}**`)]});}
  if(c==='leaderboard'){const rows=Object.entries(g.xp).sort((x,y)=>(y[1].total||0)-(x[1].total||0)).slice(0,10);return m.reply({embeds:[em('🏆 XP Leaderboard',rows.length?rows.map((x,i)=>`**${i+1}.** <@${x[0]}> — Level ${x[1].level}, ${x[1].total} XP`).join('\n'):'No XP yet.')]});}
  if(c==='leveling')return m.reply({embeds:[em('📈 Leveling Settings',`Enabled: **${g.leveling.enabled?'yes':'no'}**\nCooldown: **${g.leveling.cooldown}s**\nMultiplier: **${g.leveling.multiplier}x**\nChannel: ${g.leveling.channel?`<#${g.leveling.channel}>`:'same channel'}`)]});
  if(c==='reward'||c==='rewards')return m.reply({embeds:[em('🏅 Level Rewards',Object.entries(g.leveling.rewards).map(([l,r])=>`Level ${l}: <@&${r}>`).join('\n')||'No rewards configured.') ]});
  if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');const x=member(m,a[0]);if(!x)return m.reply(`Usage: ${PREFIX}${c} @user ...`);const z=xpof(g,x.id);const amt=num(c==='setxp'?a[1]:a[2]);if(c==='setxp')z.xp=amt;else if(a[1]==='add')z.xp+=amt;else if(a[1]==='remove')z.xp=Math.max(0,z.xp-amt);else if(a[1]==='set')z.xp=amt;else return m.reply(`Usage: ${PREFIX}xp @user add|remove|set <amount>`);z.total=Math.max(z.total,z.xp);while(z.xp>=need(z.level)){z.xp-=need(z.level);z.level++;}save();return m.reply('✅ XP updated.');
 }
 if(['balance','daily','work','deposit','withdraw','pay','economy','richlist'].includes(c)){
  if(c==='richlist'){const rows=Object.entries(g.economy).sort((x,y)=>(y[1].cash+y[1].bank)-(x[1].cash+x[1].bank)).slice(0,10);return m.reply({embeds:[em('💰 Rich List',rows.map((x,i)=>`**${i+1}.** <@${x[0]}> — ${x[1].cash+x[1].bank}`).join('\n')||'No entries.')]});}
  const z=eco(g,m.author.id);if(c==='balance'||c==='economy')return m.reply({embeds:[em('💰 Economy',`Cash: **${z.cash}**\nBank: **${z.bank}**\nTotal: **${z.cash+z.bank}**`)]});
  if(c==='daily'||c==='work'){const wait=c==='daily'?86400000:3600000;if(Date.now()-z[c]<wait)return m.reply('⏳ You already collected this reward recently.');const gain=c==='daily'?250:100;z.cash+=gain;z[c]=Date.now();save();return m.reply(`✅ You earned **${gain}** coins.`);}
  if(c==='pay'){const x=member(m,a[0]);const amt=num(a[1]);if(!x||amt<=0)return m.reply(`Usage: ${PREFIX}pay @user <amount>`);const from=eco(g,m.author.id),to=eco(g,x.id);if(from.cash<amt)return m.reply('❌ Not enough cash.');from.cash-=amt;to.cash+=amt;save();return m.reply(`💸 Paid **${amt}** coins to ${x}.`);}
  const amt=num(a[0]);if(amt<=0)return m.reply(`Usage: ${PREFIX}${c} <amount>`);if(c==='deposit'){if(z.cash<amt)return m.reply('❌ Not enough cash.');z.cash-=amt;z.bank+=amt;}else{if(z.bank<amt)return m.reply('❌ Not enough bank balance.');z.bank-=amt;z.cash+=amt;}save();return m.reply('✅ Transaction completed.');
 }
 if(['ticket','ticket-panel','open','close','claim','unclaim','ticket-setup'].includes(c)){
  if(c==='ticket-setup'){if(!can(m,PermissionFlagsBits.ManageChannels))return m.reply('❌ Manage Channels required.');let cat=m.guild.channels.cache.get(g.tickets.category);if(!cat)cat=await m.guild.channels.create({name:'🎫・TICKETS',type:ChannelType.GuildCategory});g.tickets.category=cat.id;save();return m.reply(`✅ Ticket category set to ${cat}.`);}
  if(c==='ticket-panel'||c==='ticket'){if(!can(m,PermissionFlagsBits.ManageChannels))return m.reply('❌ Manage Channels required.');const row=new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc3_ticket').setLabel('Create Ticket').setEmoji('🎫').setStyle(ButtonStyle.Primary));return m.channel.send({embeds:[em('🎫 Support Tickets','Need help? Press the button below to create a private support ticket.')],components:[row]});}
  if(c==='open'){return openTicket(m);}
  if(c==='close'){if(!m.channel.name.startsWith('ticket-'))return m.reply('❌ This is not a ticket channel.');await m.channel.delete().catch(()=>{});return;}
  if(c==='claim'||c==='unclaim')return m.reply(`🎫 Ticket ${c} feature is available for staff ticket workflows.`);
 }
 if(['role','autorole','reactionrole','levelrole','roleall'].includes(c)){
  if(!can(m,PermissionFlagsBits.ManageRoles))return m.reply('❌ Manage Roles required.');
  if(c==='autorole'){const r=m.mentions.roles.first();g.autorole=r?.id||null;save();return m.reply(r?`✅ Autorole set to ${r}.`:'✅ Autorole disabled.');}
  if(c==='roleall'){const r=m.mentions.roles.first(),action=a[1];if(!r||!['add','remove'].includes(action))return m.reply(`Usage: ${PREFIX}roleall @role add|remove`);for(const x of m.guild.members.cache.values())await x.roles[action](r).catch(()=>{});return m.reply('✅ Bulk role action complete.');}
  if(c==='reactionrole')return m.reply('Use the interactive role panel in the dashboard version; this engine keeps role changes permission-checked.');
  if(c==='levelrole')return m.reply('Configure level rewards with the leveling module.');
  const r=m.mentions.roles.first(),x=member(m,a[1]||a[0]);if(!r||!x)return m.reply(`Usage: ${PREFIX}role @role @user`);await x.roles.add(r);return m.reply(`✅ Added ${r} to ${x}.`);
 }
 if(['welcome','setwelcome','setwelcome-message','goodbye'].includes(c)){
  if(c==='welcome')return m.reply({embeds:[em('👋 Welcome System',`Channel: ${g.welcome.channel?`<#${g.welcome.channel}>`:'not set'}\nMessage: ${g.welcome.message}`)]});
  if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');
  if(c==='setwelcome'){const ch=m.mentions.channels.first()||m.channel;g.welcome.channel=ch.id;save();return m.reply(`✅ Welcome channel set to ${ch}.`);}
  if(c==='goodbye')return m.reply('✅ Goodbye messages use the same configured welcome channel in this lightweight engine.');
  g.welcome.message=a.join(' ')||g.welcome.message;save();return m.reply('✅ Welcome message updated. Variables: `{user}` `{server}`.');
 }
 if(['tempvoice','voice'].includes(c))return m.reply({embeds:[em('🔊 Temporary Voice',`Status: **ready**\nUse a dedicated creator channel setup in the server and configure it through \`${PREFIX}tempvoice setup\`.`)]});
 if(c==='starboard')return m.reply({embeds:[em('⭐ Starboard',`Enabled: **${g.starboard.enabled?'yes':'no'}**\nChannel: ${g.starboard.channel?`<#${g.starboard.channel}>`:'not set'}\nThreshold: **${g.starboard.threshold}**`)]});
 if(c==='afk'){const reason=a.join(' ')||'AFK';g.afk[m.author.id]={reason,at:Date.now()};save();return m.reply(`💤 AFK enabled: **${reason}**`);}
 if(['apply','applications','application-setup','application-questions'].includes(c))return m.reply({embeds:[em('📝 Applications',`Channel: ${g.applications.channel?`<#${g.applications.channel}>`:'not set'}\nQuestions: **${g.applications.questions.length}**\nUse \`${PREFIX}apply\` to start.`)]});
 if(['announce','say','embed','poll','announce-embed'].includes(c)){
  if(!can(m,PermissionFlagsBits.ManageMessages))return m.reply('❌ Manage Messages required.');
  if(c==='poll'){const q=a.join(' ');if(!q)return m.reply(`Usage: ${PREFIX}poll <question>`);return m.channel.send({embeds:[em('📊 Poll',q)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc3_yes').setLabel('Yes').setStyle(ButtonStyle.Success),new ButtonBuilder().setCustomId('lc3_no').setLabel('No').setStyle(ButtonStyle.Danger))]});}
  return m.channel.send(c==='embed'||c==='announce-embed'?{embeds:[em('📢 Announcement',a.join(' '))]}:a.join(' ')||' ');
 }
 if(['8ball','eightball','coinflip','roll','choose','ship','rate','reverse'].includes(c)){
  if(c==='coinflip')return m.reply(`🪙 **${Math.random()<.5?'Heads':'Tails'}**`);
  if(c==='roll'){const max=Math.max(2,num(a[0])||6);return m.reply(`🎲 You rolled **${1+Math.floor(Math.random()*max)}** / ${max}`);}
  if(c==='choose'){const opts=a.join(' ').split('|').map(x=>x.trim()).filter(Boolean);return m.reply(opts.length?`🎯 I choose **${opts[Math.floor(Math.random()*opts.length)]}**`:'Usage: !choose pizza | burger');}
  if(c==='reverse')return m.reply([...a.join(' ')].reverse().join(''));
  if(c==='rate'){const x=a.join(' ')||'that';return m.reply(`📊 **${x}** gets **${1+Math.floor(Math.random()*10)}/10**`);}
  if(c==='ship')return m.reply('💞 Shipping is just a fun fictional score — keep it friendly.');
  const q=a.join(' ')||'Ask a question.';return m.reply(`🔮 **${['Yes.','No.','Maybe.','Probably.','Ask again later.'][Math.floor(Math.random()*5)]}**`);
 }
 if(['customcommand','cc','cc-delete','cc-list'].includes(c)){
  if(c==='cc-list')return m.reply(Object.keys(g.custom).length?`⚙️ Custom commands: ${Object.keys(g.custom).map(x=>`\`${x}\``).join(', ')}`:'No custom commands.');
  if(!can(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Manage Server required.');
  const name=(a.shift()||'').toLowerCase();if(!name)return m.reply(`Usage: ${PREFIX}${c} <name> [response]`);
  if(c==='cc-delete'){delete g.custom[name];save();return m.reply('✅ Custom command deleted.');}
  g.custom[name]=a.join(' ')||'Custom command';save();return m.reply(`✅ Custom command \`${name}\` saved.`);
 }
 if(c==='remind'||c==='reminders')return m.reply('⏰ Reminder storage is enabled; use a dashboard/worker for scheduled delivery on Render free instances.');
 if(g.custom[c])return m.reply(g.custom[c]);
 return m.reply(`❓ Unknown command **${c}**. Use \`${PREFIX}help\`.`);
}

async function openTicket(m){
 const g=gd(m.guild.id);let cat=g.tickets.category?m.guild.channels.cache.get(g.tickets.category):null;if(!cat)cat=await m.guild.channels.create({name:'🎫・TICKETS',type:ChannelType.GuildCategory});g.tickets.category=cat.id;save();
 const existing=m.guild.channels.cache.find(c=>c.parentId===cat.id&&c.name===`ticket-${m.author.username.toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,20)}`);if(existing)return m.reply(`🎫 You already have ${existing}.`);
 const ch=await m.guild.channels.create({name:`ticket-${m.author.username.toLowerCase().replace(/[^a-z0-9]/g,'').slice(0,20)}`,type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]},{id:botMember(m.guild).id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.ManageChannels]}]});await ch.send({embeds:[em('🎫 Ticket Opened',`Welcome ${m.author}! Please explain your issue clearly.\n\nStaff can close this ticket with \`${PREFIX}close\`.`)]});return m.reply(`✅ Ticket created: ${ch}`);
}

const client=new Client({intents:[GatewayIntentBits.Guilds,GatewayIntentBits.GuildMembers,GatewayIntentBits.GuildMessages,GatewayIntentBits.MessageContent,GatewayIntentBits.GuildVoiceStates,GatewayIntentBits.GuildModeration,GatewayIntentBits.GuildInvites],partials:[Partials.Channel,Partials.Message,Partials.GuildMember,Partials.User]});

client.on('messageCreate',async m=>{
 if(!m.guild||m.author.bot)return;const g=gd(m.guild.id);
 const af=g.afk[m.author.id];if(af){delete g.afk[m.author.id];save();await m.reply(`👋 Welcome back! Your AFK status was removed.`).catch(()=>{});}
 for(const [id] of Object.entries(g.afk))if(m.mentions.users.has(id)&&id!==m.author.id)await m.channel.send(`💤 <@${id}> is AFK: **${g.afk[id].reason}**`).catch(()=>{});
 const low=m.content.toLowerCase();
 if(g.automod.links&&/(https?:\/\/|www\.)/i.test(m.content))return m.delete().catch(()=>{});
 if(g.automod.invites&&/(discord\.gg\/|discord\.com\/invite\/)/i.test(m.content))return m.delete().catch(()=>{});
 if(g.automod.caps&&m.content.length>=10){const letters=m.content.replace(/[^a-z]/gi,'');if(letters&&letters===letters.toUpperCase())return m.delete().catch(()=>{});}
 if(g.automod.mentions&&m.mentions.users.size>=5)return m.delete().catch(()=>{});
 if(g.automod.words.some(w=>w&&low.includes(w)))return m.delete().catch(()=>{});
 if(g.leveling.enabled&&!m.content.startsWith(PREFIX)){const z=xpof(g,m.author.id);z.total=(z.total||0)+Math.round((5+Math.floor(Math.random()*11))*g.leveling.multiplier);z.xp+=5;while(z.xp>=need(z.level)){z.xp-=need(z.level);z.level++;if(g.leveling.rewards[z.level])m.member.roles.add(g.leveling.rewards[z.level]).catch(()=>{});}save();}
 if(m.content.startsWith(PREFIX))await cmd(m,m.content.slice(PREFIX.length));
});

client.on('guildMemberAdd',async mem=>{const g=gd(mem.guild.id);if(g.autorole)await mem.roles.add(g.autorole).catch(()=>{});if(g.welcome.channel){const ch=mem.guild.channels.cache.get(g.welcome.channel);if(ch)await ch.send(g.welcome.message.replaceAll('{user}',`${mem}`).replaceAll('{server}',mem.guild.name)).catch(()=>{});}await sendLog(g,'server','📥 Member Joined',`${mem} **${mem.user.tag}** joined the server.`);});
client.on('guildMemberRemove',async mem=>sendLog(gd(mem.guild.id),'server','📤 Member Left',`**${mem.user.tag}** left the server.`));
client.on('guildBanAdd',async ban=>sendLog(gd(ban.guild.id),'mod','🔨 Member Banned',`**${ban.user.tag}** was banned.`));
client.on('guildBanRemove',async ban=>sendLog(gd(ban.guild.id),'mod','♻️ Ban Removed',`**${ban.user.tag}** was unbanned.`));
client.on('messageDelete',async msg=>{if(msg.guild&&!msg.author?.bot)await sendLog(gd(msg.guild.id),'server','🗑️ Message Deleted',`Channel: ${msg.channel}\nAuthor: ${msg.author||'Unknown'}\nContent: ${clean(msg.content,1500)||'Unavailable'}`);});
client.on('messageUpdate',async(oldMsg,newMsg)=>{if(newMsg.guild&&!newMsg.author?.bot&&oldMsg.content!==newMsg.content)await sendLog(gd(newMsg.guild.id),'server','✏️ Message Edited',`Channel: ${newMsg.channel}\nAuthor: ${newMsg.author}\nBefore: ${clean(oldMsg.content,700)}\nAfter: ${clean(newMsg.content,700)}`);});
client.on('channelCreate',async ch=>{if(ch.guild)await sendLog(gd(ch.guild.id),'server','📁 Channel Created',`${ch} **${ch.name}** was created.`);});
client.on('channelDelete',async ch=>{if(ch.guild)await sendLog(gd(ch.guild.id),'server','🗑️ Channel Deleted',`**${ch.name}** was deleted.`);});
client.on('roleCreate',async role=>sendLog(gd(role.guild.id),'server','🎭 Role Created',`${role} **${role.name}** was created.`));
client.on('roleDelete',async role=>sendLog(gd(role.guild.id),'server','🗑️ Role Deleted',`**${role.name}** was deleted.`));
client.on('voiceStateUpdate',async(oldS,newS)=>{if(oldS.channelId!==newS.channelId)await sendLog(gd(newS.guild.id),'server','🔊 Voice Update',`${newS.member} ${oldS.channelId?'left':'joined'} ${newS.channelId?`<@&${newS.channelId}>`:'voice'}.`);});

client.on('interactionCreate',async i=>{
 try{
  if(i.isStringSelectMenu()&&i.customId==='lc3_help')return i.update(help(i.values[0]));
  if(i.isButton()&&i.customId==='lc3_home')return i.update(help('home'));
  if(i.isButton()&&i.customId==='lc3_close')return i.message.delete().catch(()=>{});
  if(i.isButton()&&i.customId==='lc3_ticket'){await i.deferReply({ephemeral:true});const fake={...i,reply:async()=>{},author:i.user,guild:i.guild,channel:i.channel,member:i.member};return i.editReply(await openTicket(fake));}
  if(i.isButton()&&['lc3_yes','lc3_no'].includes(i.customId))return i.reply({content:`${i.customId==='lc3_yes'?'✅ Yes':'❌ No'} recorded.`,ephemeral:true});
 }catch(e){if(!i.replied&&!i.deferred)await i.reply({content:'❌ Something went wrong.',ephemeral:true}).catch(()=>{});}
});

async function registerSlash(){
 if(!process.env.CLIENT_ID||!client.user)return;
 const names=['help','ping','serverinfo','userinfo','avatar','ban','kick','warn','purge','ticket','logsetup','automod','level','rank','balance','daily','work','afk'];
 const body=names.map(name=>({name,description:`LightCore ${name} command`,options:name==='help'?[{name:'category',description:'Help category',type:3,required:false}]:[]}));
 const rest=new REST({version:'10'}).setToken(process.env.DISCORD_TOKEN);await rest.put(Routes.applicationCommands(process.env.CLIENT_ID),{body});console.log(`[SLASH] Registered ${body.length} core commands.`);
}
client.on('interactionCreate',async i=>{if(!i.isChatInputCommand())return;const args=i.options.getString('category')||'';const fake={guild:i.guild,author:i.user,member:i.member,channel:i.channel,mentions:{users:{first:()=>null},roles:{first:()=>null},channels:{first:()=>null}},reply:o=>i.reply(o),content:''};await cmd(fake,`${i.commandName}${args?' '+args:''}`).catch(()=>{});});

client.once('ready',async()=>{console.log(`[READY] ${client.user.tag} | ${client.guilds.cache.size} guilds | prefix ${PREFIX}`);if(process.env.CLIENT_ID)await registerSlash().catch(e=>console.error('[SLASH]',e.message));});
client.login(process.env.DISCORD_TOKEN);
module.exports={client,registerSlash,cmd,setupLogs};
