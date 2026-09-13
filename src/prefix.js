require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { Client, GatewayIntentBits, Partials, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, StringSelectMenuBuilder, ButtonBuilder, ButtonStyle, ChannelType } = require('discord.js');

const DATA_DIR = path.join(process.cwd(), 'data');
const DATA_FILE = path.join(DATA_DIR, 'database.json');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE, '{}');
let db = {};
try { db = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8') || '{}'); } catch { db = {}; }
const save = () => fs.writeFileSync(DATA_FILE, JSON.stringify(db, null, 2));
function data(gid) {
  return db[gid] ||= { prefix: '!', disabled: [], warnings: {}, xp: {}, economy: {}, welcome:{channel:null,message:'Welcome {user} to **{server}**!'}, logs:{channel:null,mod:null}, autorole:null, automod:{links:false,invites:false,caps:false,spam:false}, tickets:{category:null}, applications:{channel:null,questions:[]} };
}
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildVoiceStates],
  partials: [Partials.Channel, Partials.Message]
});
const color = 0x5865f2;
const embed = (title, desc) => new EmbedBuilder().setTitle(title).setDescription(desc).setColor(color).setTimestamp();
const getMember = (m, value) => {
  if (!value) return m.member;
  const id = value.replace(/[<@!>]/g, '');
  return m.guild.members.cache.get(id) || m.guild.members.cache.find(x => x.user.username.toLowerCase() === value.toLowerCase());
};
const need = (m, perm) => m.member.permissions.has(perm) || m.guild.ownerId === m.author.id;
const categories = {
  home: ['help','ping','botinfo','about'],
  moderation: ['kick','ban','unban','timeout','untimeout','warn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown'],
  security: ['automod','antinuke','antiraid','security'],
  logging: ['logs','setlogs','setmodlogs','logconfig'],
  leveling: ['level','rank','leaderboard','xp','setxp','leveling','reward','rewards'],
  economy: ['balance','daily','work','deposit','withdraw','pay','economy','richlist'],
  tickets: ['ticket','open','close','claim','unclaim','ticket-setup'],
  roles: ['role','autorole','reactionrole','rr','levelrole'],
  welcome: ['welcome','setwelcome','setwelcome-message'],
  voice: ['tempvoice','voice'],
  starboard: ['starboard'],
  afk: ['afk'],
  applications: ['apply','applications','application-setup','application-questions'],
  announcements: ['announce','say','embed','poll'],
  music: ['play','skip','stop','queue','leave'],
  utility: ['serverinfo','userinfo','avatar','roleinfo','channelinfo','membercount','servericon','invite','config','prefix','enable','disable'],
  fun: ['8ball','coinflip','roll','choose']
};
const descriptions = {
  help:'Interactive command center', ping:'Show bot latency', botinfo:'Show bot information', about:'Show bot information',
  kick:'Kick a member', ban:'Ban a member', unban:'Unban a user', timeout:'Timeout a member', untimeout:'Remove a timeout', warn:'Warn a member', warnings:'View warnings', clearwarnings:'Clear warnings', purge:'Delete recent messages', lock:'Lock the current channel', unlock:'Unlock the current channel', slowmode:'Set channel slowmode', nick:'Change a member nickname', lockdown:'Lock text channels', unlockdown:'Unlock text channels',
  automod:'Configure automatic moderation', antinuke:'Configure server security protection', antiraid:'Configure anti-raid protection', security:'Show security settings',
  logs:'Show logging settings', setlogs:'Set the server log channel', setmodlogs:'Set the moderation log channel', logconfig:'Show logging configuration',
  level:'Show a member level', rank:'Show a member rank', leaderboard:'Show the level leaderboard', xp:'Manage XP', setxp:'Set member XP', leveling:'Configure leveling', reward:'Manage a level reward', rewards:'List level rewards',
  balance:'Show your economy balance', daily:'Claim daily coins', work:'Work for coins', deposit:'Deposit coins', withdraw:'Withdraw coins', pay:'Pay another member', economy:'Show economy help', richlist:'Show economy leaderboard',
  ticket:'Ticket commands', open:'Open a ticket', close:'Close the current ticket', claim:'Claim a ticket', unclaim:'Unclaim a ticket', 'ticket-setup':'Configure tickets',
  role:'Add or remove roles', autorole:'Configure automatic roles', reactionrole:'Configure reaction roles', rr:'Reaction-role shortcut', levelrole:'Configure level roles',
  welcome:'Welcome system help', setwelcome:'Set welcome channel', 'setwelcome-message':'Set welcome message',
  tempvoice:'Temporary voice setup', voice:'Temporary voice commands', starboard:'Configure starboard', afk:'Set or remove AFK status',
  apply:'Submit an application', applications:'Application system help', 'application-setup':'Set application review channel', 'application-questions':'Set application questions',
  announce:'Send an announcement embed', say:'Send a message', embed:'Create an embed', poll:'Create a poll',
  play:'Play music from a supported URL', skip:'Skip the current track', stop:'Stop music', queue:'Show music queue', leave:'Leave voice',
  serverinfo:'Show server information', userinfo:'Show user information', avatar:'Show an avatar', roleinfo:'Show role information', channelinfo:'Show channel information', membercount:'Show member count', servericon:'Show server icon', invite:'Create a server invite', config:'Show server configuration', prefix:'Change the server prefix', enable:'Enable a command', disable:'Disable a command',
  '8ball':'Ask the 8ball', coinflip:'Flip a coin', roll:'Roll dice', choose:'Choose from options'
};
const titles = {home:'🏠 LightCore Help',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',leveling:'📈 Leveling',economy:'💰 Economy',tickets:'🎫 Tickets',roles:'🎭 Roles',welcome:'👋 Welcome',voice:'🔊 Temporary Voice',starboard:'⭐ Starboard',afk:'💤 AFK',applications:'📝 Applications',announcements:'📢 Announcements',music:'🎵 Music',utility:'🛠️ Utility',fun:'🎉 Fun'};
const label = {home:'Home',moderation:'Moderation',security:'Security',logging:'Logging',leveling:'Leveling',economy:'Economy',tickets:'Tickets',roles:'Roles',welcome:'Welcome',voice:'Temporary Voice',starboard:'Starboard',afk:'AFK',applications:'Applications',announcements:'Announcements',music:'Music',utility:'Utility',fun:'Fun'};
function helpMessage(m, category='home') {
  const d = data(m.guild.id), p = d.prefix || '!';
  if (category === 'home') {
    const rows = Object.keys(categories).map(k => `**${titles[k]}** — \`${p}help ${k}\``).join('\n');
    return { embeds: [embed('🤖 LightCore • All-in-One Command Center', `Prefix: \`${p}\`\n\n${rows}\n\nUse the menu below to browse commands.\nUse \`${p}help <command>\` for command details.`)], components: [menuRow('home')] };
  }
  const list = categories[category] || [];
  const lines = list.map(c => `**${p}${c}** — ${descriptions[c] || 'Command'}`).join('\n');
  return { embeds: [embed(`${titles[category] || 'Commands'}`, lines || 'No commands in this category.')], components: [menuRow(category), navRow()] };
}
function menuRow(selected) {
  const menu = new StringSelectMenuBuilder().setCustomId('lc-help-menu').setPlaceholder('📂 Select a category').addOptions(Object.keys(categories).map(k => ({label: label[k], value:k, emoji: titles[k].split(' ')[0]})));
  return new ActionRowBuilder().addComponents(menu);
}
function navRow() {
  return new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc-help-home').setLabel('Home').setStyle(ButtonStyle.Secondary), new ButtonBuilder().setCustomId('lc-help-close').setLabel('Close').setStyle(ButtonStyle.Danger));
}
async function execute(m, raw) {
  const d = data(m.guild.id), parts = raw.trim().split(/\s+/), command = (parts.shift() || '').toLowerCase(), args = parts;
  if (!command) return;
  if (d.disabled?.includes(command) && !['enable','disable'].includes(command)) return m.reply('❌ This command is disabled.');
  if (command === 'help' || command === 'h') {
    const category = (args[0] || 'home').toLowerCase();
    if (descriptions[category] && !categories[category]) return m.reply({embeds:[embed(`📖 ${d.prefix}${category}`, `**Usage:** \`${d.prefix}${category} ${category === 'ban' ? '@user [reason]' : ''}\`\n${descriptions[category]}`)]});
    if (!categories[category]) return m.reply({embeds:[embed('❓ Help', `Unknown category. Use \`${d.prefix}help\` to see the categories.`)]});
    return m.reply(helpMessage(m, category));
  }
  if (command === 'prefix') {
    if (!need(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ You need **Manage Server**.');
    if (!args[0] || args[0].length > 5) return m.reply(`Current prefix: \`${d.prefix}\`\nUsage: \`${d.prefix}prefix <new prefix>\``);
    d.prefix = args[0]; save(); return m.reply(`✅ Prefix changed to \`${d.prefix}\``);
  }
  if (['ping'].includes(command)) return m.reply(`🏓 Pong! **${client.ws.ping}ms**`);
  if (['botinfo','about'].includes(command)) return m.reply({embeds:[embed('🤖 LightCore', `Servers: **${client.guilds.cache.size}**\nUsers cached: **${client.users.cache.size}**\nPrefix here: \`${d.prefix}\``)]});
  if (command === 'serverinfo') return m.reply({embeds:[embed(`🏠 ${m.guild.name}`, `Owner: <@${m.guild.ownerId}>\nMembers: **${m.guild.memberCount}**\nChannels: **${m.guild.channels.cache.size}**\nRoles: **${m.guild.roles.cache.size}**`)]});
  if (command === 'membercount') return m.reply(`👥 Members: **${m.guild.memberCount}**`);
  if (command === 'avatar') { const u = getMember(m,args[0])?.user || m.author; return m.reply({embeds:[new EmbedBuilder().setTitle(`${u.username}'s Avatar`).setImage(u.displayAvatarURL({size:1024,dynamic:true})).setColor(color)]}); }
  if (['userinfo'].includes(command)) { const x=getMember(m,args[0]) || m.member; return m.reply({embeds:[embed(`👤 ${x.user.tag}`, `ID: \`${x.id}\`\nJoined: <t:${Math.floor(x.joinedTimestamp/1000)}:R>\nCreated: <t:${Math.floor(x.user.createdTimestamp/1000)}:R>`)]}); }
  if (command === 'kick') { if(!need(m,PermissionFlagsBits.KickMembers)) return m.reply('❌ Missing Kick Members.'); const x=getMember(m,args[0]); if(!x)return m.reply('❌ Member not found.'); await x.kick(args.slice(1).join(' ')||'No reason').catch(e=>{throw e}); return m.reply(`✅ Kicked **${x.user.tag}**.`); }
  if (command === 'ban') { if(!need(m,PermissionFlagsBits.BanMembers)) return m.reply('❌ Missing Ban Members.'); const x=getMember(m,args[0]); if(!x)return m.reply('❌ Member not found.'); await x.ban({reason:args.slice(1).join(' ')||'No reason'}); return m.reply(`✅ Banned **${x.user.tag}**.`); }
  if (command === 'timeout') { if(!need(m,PermissionFlagsBits.ModerateMembers)) return m.reply('❌ Missing Moderate Members.'); const x=getMember(m,args[0]); const mins=Number(args[1]); if(!x||!Number.isFinite(mins))return m.reply(`Usage: \`${d.prefix}timeout @user <minutes> [reason]\``); await x.timeout(Math.min(mins*60000,2419200000),args.slice(2).join(' ')||'No reason'); return m.reply(`✅ Timed out **${x.user.tag}**.`); }
  if (command === 'untimeout') { if(!need(m,PermissionFlagsBits.ModerateMembers))return m.reply('❌ Missing Moderate Members.'); const x=getMember(m,args[0]); if(!x)return m.reply('❌ Member not found.'); await x.timeout(null); return m.reply(`✅ Removed timeout from **${x.user.tag}**.`); }
  if (command === 'warn') { if(!need(m,PermissionFlagsBits.ModerateMembers))return m.reply('❌ Missing Moderate Members.'); const x=getMember(m,args[0]); if(!x)return m.reply('❌ Member not found.'); d.warnings[x.id] ||= []; d.warnings[x.id].push({reason:args.slice(1).join(' ')||'No reason',by:m.author.id,at:Date.now()}); save(); return m.reply(`⚠️ Warned **${x.user.tag}**.`); }
  if (['warnings','clearwarnings'].includes(command)) { const x=getMember(m,args[0])||m.member; if(command==='clearwarnings'){if(!need(m,PermissionFlagsBits.ModerateMembers))return m.reply('❌ Missing Moderate Members.'); d.warnings[x.id]=[];save();return m.reply('✅ Warnings cleared.');} const w=d.warnings[x.id]||[]; return m.reply({embeds:[embed(`⚠️ Warnings • ${x.user.tag}`,w.length?w.map((v,i)=>`**${i+1}.** ${v.reason}`).join('\n'):'No warnings.')]}); }
  if (command === 'purge') { if(!need(m,PermissionFlagsBits.ManageMessages))return m.reply('❌ Missing Manage Messages.'); const n=Math.min(Math.max(Number(args[0])||0,1),100); const deleted=await m.channel.bulkDelete(n,true); const msg=await m.channel.send(`🧹 Deleted **${deleted.size}** messages.`); setTimeout(()=>msg.delete().catch(()=>{}),3000); return; }
  if (['lock','unlock'].includes(command)) { if(!need(m,PermissionFlagsBits.ManageChannels))return m.reply('❌ Missing Manage Channels.'); const ch=m.channel; await ch.permissionOverwrites.edit(m.guild.roles.everyone,{SendMessages:command==='unlock'?null:false}); return m.reply(`✅ Channel ${command}ed.`); }
  if (command === 'slowmode') { if(!need(m,PermissionFlagsBits.ManageChannels))return m.reply('❌ Missing Manage Channels.'); const s=Math.min(Math.max(Number(args[0])||0,0),21600); await m.channel.setRateLimitPerUser(s); return m.reply(`✅ Slowmode set to **${s}s**.`); }
  if (command === 'nick') { if(!need(m,PermissionFlagsBits.ManageNicknames))return m.reply('❌ Missing Manage Nicknames.'); const x=getMember(m,args[0]); if(!x)return m.reply('❌ Member not found.'); await x.setNickname(args.slice(1).join(' ')||null); return m.reply('✅ Nickname updated.'); }
  if (command === 'level' || command === 'rank') { const id=getMember(m,args[0])?.id||m.author.id; const a=d.xp[id]||{xp:0,level:1}; return m.reply({embeds:[embed('📈 Level',`User: <@${id}>\nLevel: **${a.level||1}**\nXP: **${a.xp||0}**`)]}); }
  if (command === 'leaderboard') { const arr=Object.entries(d.xp||{}).sort((a,b)=>(b[1].level*1000+b[1].xp)-(a[1].level*1000+a[1].xp)).slice(0,10); return m.reply({embeds:[embed('🏆 Level Leaderboard',arr.length?arr.map((x,i)=>`**${i+1}.** <@${x[0]}> — Level ${x[1].level}, ${x[1].xp} XP`).join('\n'):'No XP data yet.')]}); }
  if (command === 'xp' || command === 'setxp') { if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.'); const x=getMember(m,args[0]); const amount=Number(args[1]); if(!x||!Number.isFinite(amount))return m.reply(`Usage: \`${d.prefix}xp set @user <amount>\``); d.xp[x.id] ||= {xp:0,level:1}; d.xp[x.id].xp=Math.max(0,amount); save(); return m.reply(`✅ XP for **${x.user.tag}** set to **${amount}**.`); }
  if (['balance','daily','work','deposit','withdraw','pay'].includes(command)) { const id=m.author.id; d.economy[id] ||= {cash:100,bank:0,lastDaily:0,lastWork:0}; const a=d.economy[id]; if(command==='balance')return m.reply(`💰 **${m.author.username}**\nCash: **${a.cash}**\nBank: **${a.bank}**`); if(command==='daily'){if(Date.now()-a.lastDaily<86400000)return m.reply('⏳ Daily is on cooldown.');a.cash+=250;a.lastDaily=Date.now();save();return m.reply('💰 You received **250** coins.');} if(command==='work'){if(Date.now()-a.lastWork<3600000)return m.reply('⏳ Work is on cooldown.');a.cash+=100;a.lastWork=Date.now();save();return m.reply('💼 You earned **100** coins.');} const amount=Number(args[0]); if(!Number.isFinite(amount)||amount<=0)return m.reply('❌ Enter a valid amount.'); if(command==='deposit'){if(a.cash<amount)return m.reply('❌ Not enough cash.');a.cash-=amount;a.bank+=amount;} if(command==='withdraw'){if(a.bank<amount)return m.reply('❌ Not enough bank balance.');a.bank-=amount;a.cash+=amount;} if(command==='pay'){const x=getMember(m,args[0]),amt=Number(args[1]);if(!x||!Number.isFinite(amt)||amt<=0)return m.reply(`Usage: \`${d.prefix}pay @user <amount>\``);if(a.cash<amt)return m.reply('❌ Not enough cash.');d.economy[x.id] ||= {cash:100,bank:0,lastDaily:0,lastWork:0};a.cash-=amt;d.economy[x.id].cash+=amt;}save();return m.reply('✅ Transaction completed.'); }
  if (command === 'announce' || command === 'embed') { if(!need(m,PermissionFlagsBits.ManageMessages))return m.reply('❌ Missing Manage Messages.'); const text=args.join(' ')||'Announcement'; await m.channel.send({embeds:[embed(command==='announce'?'📢 Announcement':'✨ Embed',text)]}); return m.delete().catch(()=>{}); }
  if (command === 'say') { if(!need(m,PermissionFlagsBits.ManageMessages))return m.reply('❌ Missing Manage Messages.'); await m.channel.send(args.join(' ')||''); return m.delete().catch(()=>{}); }
  if (command === 'poll') { const q=args.join(' ')||'Poll'; return m.channel.send({embeds:[embed('📊 Poll',q)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc-poll-yes').setLabel('👍 Yes').setStyle(ButtonStyle.Success),new ButtonBuilder().setCustomId('lc-poll-no').setLabel('👎 No').setStyle(ButtonStyle.Danger))]}); }
  if (['8ball','coinflip','roll','choose'].includes(command)) { if(command==='coinflip')return m.reply(Math.random()<.5?'🪙 Heads!':'🪙 Tails!'); if(command==='8ball')return m.reply(['🎱 Yes.','🎱 No.','🎱 Maybe.','🎱 Ask again later.'][Math.floor(Math.random()*4)]); if(command==='roll'){const n=Math.max(2,Math.min(Number(args[0])||6,1000));return m.reply(`🎲 You rolled **${Math.floor(Math.random()*n)+1}** / ${n}.`);} const opts=args.join(' ').split('|').map(x=>x.trim()).filter(Boolean);return m.reply(`🎯 I choose **${opts[Math.floor(Math.random()*opts.length)]||'nothing'}**.`); }
  if (command === 'ticket' || command === 'open') { const cat=d.tickets.category; const name=`ticket-${m.author.id}`; if(m.guild.channels.cache.find(c=>c.name===name))return m.reply('❌ You already have a ticket.'); const ch=await m.guild.channels.create({name,type:ChannelType.GuildText,parent:cat||undefined,permissionOverwrites:[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]}]}); await ch.send({content:`${m.author}`,embeds:[embed('🎫 Support Ticket','Please describe your issue.')],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc-ticket-close').setLabel('Close Ticket').setStyle(ButtonStyle.Danger))]}); return m.reply(`✅ Ticket created: ${ch}`); }
  if (command === 'close') { if(!m.channel.name.startsWith('ticket-'))return m.reply('❌ This is not a ticket.');await m.reply('🔒 Closing ticket...');setTimeout(()=>m.channel.delete().catch(()=>{}),1000);return; }
  if (command === 'claim' || command === 'unclaim') return m.reply(command==='claim'?'✅ Ticket claimed.':'✅ Ticket unclaimed.');
  if (command === 'setlogs' || command === 'logs' || command === 'logconfig') { if(command==='setlogs'){if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');d.logs.channel=m.channel.id;save();return m.reply('✅ Server log channel set to this channel.');} return m.reply({embeds:[embed('📋 Logging',`Server logs: ${d.logs.channel?`<#${d.logs.channel}>`:'Not set'}\nModeration logs: ${d.logs.mod?`<#${d.logs.mod}>`:'Not set'}`)]}); }
  if (command === 'setmodlogs') {if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');d.logs.mod=m.channel.id;save();return m.reply('✅ Moderation log channel set.');}
  if (command === 'setwelcome') {if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');d.welcome.channel=m.channel.id;save();return m.reply('✅ Welcome channel set to this channel.');}
  if (command === 'setwelcome-message') {if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');d.welcome.message=args.join(' ')||d.welcome.message;save();return m.reply('✅ Welcome message updated.');}
  if (command === 'setautorole' || command === 'autorole') {if(!need(m,PermissionFlagsBits.ManageRoles))return m.reply('❌ Missing Manage Roles.');const r=m.guild.roles.cache.find(x=>`<@&${x.id}>`===args[0])||m.guild.roles.cache.get(args[0]);if(command==='setautorole'){if(!r)return m.reply('❌ Mention a role.');d.autorole=r.id;save();return m.reply(`✅ Autorole set to <@&${r.id}>.`);}return m.reply(`Autorole: ${d.autorole?`<@&${d.autorole}>`:'Not set'}`);}
  if (command === 'role') {if(!need(m,PermissionFlagsBits.ManageRoles))return m.reply('❌ Missing Manage Roles.');const action=args.shift(),x=getMember(m,args.shift()),r=m.guild.roles.cache.find(v=>`<@&${v.id}>`===args[0])||m.guild.roles.cache.get(args[0]);if(!x||!r)return m.reply(`Usage: \`${d.prefix}role add @user @role\``);if(action==='add'){await x.roles.add(r);return m.reply(`✅ Added <@&${r.id}> to ${x}.`)}if(action==='remove'){await x.roles.remove(r);return m.reply(`✅ Removed <@&${r.id}> from ${x}.`)}return m.reply('Use add or remove.');}
  if (['automod','antinuke','antiraid','security'].includes(command)) {if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');return m.reply({embeds:[embed('🔐 Security', 'Security configuration is available. Use the command with `enable` or `disable` to configure supported protections.') ]});}
  if (command === 'config') return m.reply({embeds:[embed('⚙️ Configuration',`Prefix: \`${d.prefix}\`\nWelcome: ${d.welcome.channel?`<#${d.welcome.channel}>`:'Off'}\nLogs: ${d.logs.channel?`<#${d.logs.channel}>`:'Off'}\nAutorole: ${d.autorole?`<@&${d.autorole}>`:'Off'}`)]});
  if (command === 'disable' || command === 'enable') {if(!need(m,PermissionFlagsBits.ManageGuild))return m.reply('❌ Missing Manage Server.');const c=args[0]?.toLowerCase();if(!c)return m.reply(`Usage: \`${d.prefix}${command} <command>\``);d.disabled ||= [];if(command==='disable'&&!d.disabled.includes(c))d.disabled.push(c);if(command==='enable')d.disabled=d.disabled.filter(x=>x!==c);save();return m.reply(`✅ ${command==='disable'?'Disabled':'Enabled'} \`${c}\`.`);}
  if (command === 'invite') { const ch=m.channel; const inv=await ch.createInvite({maxAge:0,maxUses:0,unique:false}).catch(()=>null);return m.reply(inv?`🔗 ${inv.url}`:'❌ I cannot create an invite here.'); }
  return m.reply({embeds:[embed('❓ Unknown command',`I don't recognize \`${command}\`. Try \`${d.prefix}help\`.`)]});
}
client.on('messageCreate', async m => {
  if (!m.guild || m.author.bot) return;
  const d=data(m.guild.id), p=d.prefix || '!';
  if (!m.content.startsWith(p) && !(p !== '.' && m.content.startsWith('.'))) return;
  const raw = m.content.startsWith(p) ? m.content.slice(p.length) : m.content.slice(1);
  try { await execute(m, raw); } catch (e) { console.error('[PREFIX]', e); m.reply(`❌ Command error: ${e.message.slice(0,180)}`).catch(()=>{}); }
});
client.on('interactionCreate', async i => {
  if (i.isStringSelectMenu() && i.customId === 'lc-help-menu') {
    if (!i.guild) return;
    return i.update(helpMessage(i.message, i.values[0]));
  }
  if (i.isButton() && i.customId === 'lc-help-home') return i.update(helpMessage(i.message,'home'));
  if (i.isButton() && i.customId === 'lc-help-close') return i.message.delete().catch(()=>{});
  if (i.isButton() && ['lc-ticket-close'].includes(i.customId)) { if(!i.channel?.name.startsWith('ticket-'))return i.reply({content:'❌ Not a ticket.',ephemeral:true});await i.reply('🔒 Closing ticket...');setTimeout(()=>i.channel.delete().catch(()=>{}),1000); }
});
client.once('ready', () => console.log(`Prefix system online as ${client.user.tag}`));
client.login(process.env.DISCORD_TOKEN).catch(e => console.error('[PREFIX LOGIN]', e));
