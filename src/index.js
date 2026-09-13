require('dotenv').config();
const fs = require('fs');
const path = require('path');
const {
  Client, GatewayIntentBits, Partials, REST, Routes, SlashCommandBuilder,
  PermissionFlagsBits, EmbedBuilder, ChannelType, ActionRowBuilder, ButtonBuilder,
  ButtonStyle, StringSelectMenuBuilder
} = require('discord.js');

const DATA_DIR = path.join(process.cwd(), 'data');
const DATA_FILE = path.join(DATA_DIR, 'guilds.json');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE, '{}');
const load = () => JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
const save = d => fs.writeFileSync(DATA_FILE, JSON.stringify(d, null, 2));
let db = load();
const guildConfig = id => (db[id] ||= { prefix: process.env.PREFIX || '!', welcomeChannel: null, welcomeMessage: 'Welcome {user} to {server}!', logChannel: null, modLogChannel: null, autoRole: null, autoroleEnabled: false, automod: { links: false, invites: false, caps: false, spam: false }, levels: {}, warnings: {}, disabled: [] });

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMembers, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildModeration],
  partials: [Partials.Channel, Partials.Message]
});

const ok = (content, ephemeral=false) => ({ content: `✅ ${content}`, ephemeral });
const err = (content, ephemeral=true) => ({ content: `❌ ${content}`, ephemeral });
const embed = (title, description) => new EmbedBuilder().setTitle(title).setDescription(description).setColor(0x5865f2).setTimestamp();
const needPerm = (i, p) => i.memberPermissions?.has(p);
const isOwner = i => i.user.id === process.env.OWNER_ID || i.guild?.ownerId === i.user.id;

function commands() {
  const c = [];
  const add = (name, description, options=[]) => { let x = new SlashCommandBuilder().setName(name).setDescription(description); for (const o of options) x.addStringOption(o); c.push(x.toJSON()); };
  add('help','Show all bot features'); add('ping','Show bot latency'); add('botinfo','Show bot information'); add('serverinfo','Show server information'); add('userinfo','Show user information',[o=>o.setName('user').setDescription('User mention or ID').setRequired(false)]); add('avatar','Show a user avatar',[o=>o.setName('user').setDescription('User').setRequired(false)]); add('roleinfo','Show role information',[o=>o.setName('role').setDescription('Role ID').setRequired(true)]); add('channelinfo','Show channel information');
  add('say','Send a message',[o=>o.setName('message').setDescription('Message').setRequired(true)]); add('announce','Send an announcement',[o=>o.setName('message').setDescription('Announcement').setRequired(true)]); add('poll','Create a yes/no poll',[o=>o.setName('question').setDescription('Question').setRequired(true)]); add('8ball','Ask the magic 8ball',[o=>o.setName('question').setDescription('Question').setRequired(true)]); add('coinflip','Flip a coin'); add('roll','Roll a dice',[o=>o.setName('sides').setDescription('Number of sides').setRequired(false)]); add('choose','Choose between options',[o=>o.setName('options').setDescription('Separate with commas').setRequired(true)]);
  add('kick','Kick a member',[o=>o.setName('user').setDescription('User ID/mention').setRequired(true),o=>o.setName('reason').setDescription('Reason').setRequired(false)]); add('ban','Ban a member',[o=>o.setName('user').setDescription('User ID/mention').setRequired(true),o=>o.setName('reason').setDescription('Reason').setRequired(false)]); add('unban','Unban a user',[o=>o.setName('user').setDescription('User ID').setRequired(true)]); add('timeout','Timeout a member',[o=>o.setName('user').setDescription('User').setRequired(true),o=>o.setName('duration').setDescription('e.g. 10m, 2h, 1d').setRequired(true),o=>o.setName('reason').setDescription('Reason').setRequired(false)]); add('untimeout','Remove timeout',[o=>o.setName('user').setDescription('User').setRequired(true)]); add('warn','Warn a member',[o=>o.setName('user').setDescription('User').setRequired(true),o=>o.setName('reason').setDescription('Reason').setRequired(false)]); add('warnings','View warnings',[o=>o.setName('user').setDescription('User').setRequired(true)]); add('clearwarnings','Clear warnings',[o=>o.setName('user').setDescription('User').setRequired(true)]); add('purge','Delete messages',[o=>o.setName('amount').setDescription('1-100').setRequired(true)]); add('lock','Lock this channel'); add('unlock','Unlock this channel'); add('slowmode','Set slowmode seconds',[o=>o.setName('seconds').setDescription('0-21600').setRequired(true)]); add('nick','Change a member nickname',[o=>o.setName('user').setDescription('User').setRequired(true),o=>o.setName('nickname').setDescription('Nickname').setRequired(true)]);
  add('setwelcome','Set welcome channel',[o=>o.setName('channel').setDescription('Channel ID').setRequired(true)]); add('setwelcome-message','Set welcome message',[o=>o.setName('message').setDescription('Use {user} and {server}').setRequired(true)]); add('setlogs','Set logging channel',[o=>o.setName('channel').setDescription('Channel ID').setRequired(true)]); add('setmodlogs','Set moderation log channel',[o=>o.setName('channel').setDescription('Channel ID').setRequired(true)]); add('setautorole','Set automatic role',[o=>o.setName('role').setDescription('Role ID').setRequired(true)]); add('autorole','Enable/disable autorole',[o=>o.setName('enabled').setDescription('true or false').setRequired(true)]); add('automod','Configure automod',[o=>o.setName('feature').setDescription('links/invites/caps/spam').setRequired(true),o=>o.setName('enabled').setDescription('true or false').setRequired(true)]); add('config','Show server configuration'); add('disable','Disable a command',[o=>o.setName('command').setDescription('Command name').setRequired(true)]); add('enable','Enable a command',[o=>o.setName('command').setDescription('Command name').setRequired(true)]);
  add('ticket','Create a private support ticket'); add('close','Close the current ticket'); add('lockdown','Lock every text channel'); add('unlockdown','Unlock every text channel'); add('servericon','Show server icon'); add('membercount','Show member count'); add('invite','Create a server invite'); add('support','Show support information'); add('stats','Show bot statistics');
  return c;
}
const commandData = commands();

function parseDuration(s) { const m = /^([0-9]+)\s*(s|m|h|d|w)$/i.exec(s); if (!m) return null; return Number(m[1]) * ({s:1000,m:60000,h:3600000,d:86400000,w:604800000}[m[2].toLowerCase()]); }
function memberFrom(i, value) { return i.guild.members.cache.get(value.replace(/[<@!>]/g,'')) || i.guild.members.cache.find(m => m.user.username.toLowerCase() === value.toLowerCase()); }
async function log(guild, title, description, mod=false) { const cfg=guildConfig(guild.id); const id=mod?cfg.modLogChannel:cfg.logChannel; if(!id) return; const ch=guild.channels.cache.get(id); if(ch?.isTextBased()) ch.send({embeds:[embed(title,description)]}).catch(()=>{}); }

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  client.user.setActivity('/help • All-in-one', { type: 0 });
  const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
  try {
    if (process.env.GUILD_ID) await rest.put(Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID), { body: commandData });
    else await rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: commandData });
    console.log(`Registered ${commandData.length} slash commands.`);
  } catch(e) { console.error('Command registration failed:', e.message); }
});

client.on('guildMemberAdd', async member => {
  const cfg=guildConfig(member.guild.id);
  if(cfg.autoroleEnabled && cfg.autoRole) member.roles.add(cfg.autoRole).catch(()=>{});
  if(cfg.welcomeChannel) { const ch=member.guild.channels.cache.get(cfg.welcomeChannel); if(ch?.isTextBased()) ch.send({embeds:[embed('👋 Welcome!',cfg.welcomeMessage.replaceAll('{user}',`${member}`).replaceAll('{server}',member.guild.name))]}).catch(()=>{}); }
  await log(member.guild,'Member Joined',`${member.user.tag} joined the server.`);
});
client.on('guildMemberRemove', m => log(m.guild,'Member Left',`${m.user.tag} left the server.`));

client.on('messageDelete', m => { if(m.guild && !m.author?.bot) log(m.guild,'Message Deleted',`Message by ${m.author?.tag || 'unknown'} was deleted in ${m.channel}.`); });
client.on('messageCreate', async m => {
  if(!m.guild || m.author.bot) return;
  const cfg=guildConfig(m.guild.id);
  const text=m.content;
  const blocked = cfg.disabled.includes(text.split(/\s+/)[0].toLowerCase().replace(/^\//,''));
  if(blocked) return;
  if(cfg.automod.invites && /(discord\.gg|discord\.com\/invite)\//i.test(text)) { await m.delete().catch(()=>{}); await m.channel.send({content:`${m.author}, Discord invites are not allowed here.`}).then(x=>setTimeout(()=>x.delete().catch(()=>{}),5000)).catch(()=>{}); return; }
  if(cfg.automod.links && /https?:\/\//i.test(text) && !m.member.permissions.has(PermissionFlagsBits.ManageMessages)) { await m.delete().catch(()=>{}); return; }
  if(cfg.automod.caps && text.length >= 12 && text.replace(/[^A-Za-z]/g,'').length >= 8) { const letters=text.replace(/[^A-Za-z]/g,''); if(letters === letters.toUpperCase()) { await m.delete().catch(()=>{}); return; } }
  if(cfg.automod.spam) { const now=Date.now(); const key=`spam_${m.author.id}`; const x=cfg[key]||[]; cfg[key]=x.filter(t=>now-t<7000); cfg[key].push(now); if(cfg[key].length>=5){ await m.delete().catch(()=>{}); cfg[key]=[]; save(db); return; } save(db); }
});

client.on('interactionCreate', async i => {
  if(!i.isChatInputCommand() && !i.isButton() && !i.isStringSelectMenu()) return;
  if(i.isButton()) {
    if(i.customId === 'ticket-create') return createTicket(i);
    if(i.customId === 'ticket-close') { if(!i.channel.name.startsWith('ticket-')) return i.reply(err('This is not a ticket channel.')); await i.reply('🔒 Closing ticket...'); setTimeout(()=>i.channel.delete().catch(()=>{}),1200); return; }
    return;
  }
  if(i.isStringSelectMenu()) return;
  const cfg=guildConfig(i.guild.id); const cmd=i.commandName;
  if(cfg.disabled.includes(cmd) && !['enable','disable'].includes(cmd)) return i.reply(err('This command is disabled in this server.'));
  try {
    switch(cmd) {
      case 'help': return i.reply({embeds:[embed('🤖 All-in-One Bot',`**Moderation:** /kick /ban /unban /timeout /untimeout /warn /warnings /clearwarnings /purge /lock /unlock /slowmode /nick\n**Server:** /setwelcome /setwelcome-message /setlogs /setmodlogs /setautorole /autorole /automod /config /lockdown /unlockdown\n**Utility:** /serverinfo /userinfo /avatar /roleinfo /channelinfo /membercount /servericon /invite /stats /support\n**Fun:** /8ball /coinflip /roll /choose /poll /say /announce\n**Tickets:** /ticket /close\n\nUse `/config` to see the current server setup.`)]});
      case 'ping': return i.reply(`🏓 Pong! **${client.ws.ping}ms**`);
      case 'botinfo': return i.reply({embeds:[embed('🤖 Bot Info',`Servers: **${client.guilds.cache.size}**\nUsers cached: **${client.users.cache.size}**\nCommands: **${commandData.length}**\nNode: **${process.version}**`)]});
      case 'stats': return i.reply({embeds:[embed('📊 Statistics',`Servers: ${client.guilds.cache.size}\nUsers cached: ${client.users.cache.size}\nChannels cached: ${client.channels.cache.size}\nCommands: ${commandData.length}`)]});
      case 'serverinfo': return i.reply({embeds:[embed(`🏠 ${i.guild.name}`,`Owner: <@${i.guild.ownerId}>\nMembers: **${i.guild.memberCount}**\nChannels: **${i.guild.channels.cache.size}**\nRoles: **${i.guild.roles.cache.size}**\nCreated: <t:${Math.floor(i.guild.createdTimestamp/1000)}:D>`)]});
      case 'membercount': return i.reply(`👥 **${i.guild.memberCount}** members`);
      case 'servericon': return i.reply(i.guild.iconURL({size:1024}) || 'No server icon.');
      case 'userinfo': { const m=memberFrom(i,i.options.getString('user')||i.user.id)||i.member; return i.reply({embeds:[embed(`👤 ${m.user.tag}`,`ID: ${m.id}\nBot: ${m.user.bot?'Yes':'No'}\nJoined: <t:${Math.floor(m.joinedTimestamp/1000)}:R>\nRoles: ${m.roles.cache.filter(r=>r.id!==i.guild.id).map(r=>r).join(' ')||'None'}`).setThumbnail(m.user.displayAvatarURL())]}); }
      case 'avatar': { const m=memberFrom(i,i.options.getString('user')||i.user.id)||i.member; return i.reply({embeds:[embed(`🖼️ ${m.user.tag}`,m.user.displayAvatarURL({size:1024}))]}); }
      case 'roleinfo': { const r=i.guild.roles.cache.get(i.options.getString('role')); if(!r)return i.reply(err('Role not found.')); return i.reply({embeds:[embed(`🎭 ${r.name}`,`ID: ${r.id}\nMembers: ${r.members.size}\nPosition: ${r.position}\nMentionable: ${r.mentionable}`)]}); }
      case 'channelinfo': return i.reply({embeds:[embed(`📺 ${i.channel.name}`,`ID: ${i.channel.id}\nType: ${i.channel.type}\nPosition: ${i.channel.position}`)]});
      case 'say': if(!needPerm(i,PermissionFlagsBits.ManageMessages))return i.reply(err('You need Manage Messages.')); await i.channel.send(i.options.getString('message')); return i.reply({content:'Sent.',ephemeral:true});
      case 'announce': if(!needPerm(i,PermissionFlagsBits.ManageMessages))return i.reply(err('You need Manage Messages.')); return i.reply({embeds:[embed('📢 Announcement',i.options.getString('message'))]});
      case 'poll': { const q=i.options.getString('question'); return i.reply({embeds:[embed('📊 Poll',q)], components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('poll-yes').setLabel('👍 Yes').setStyle(ButtonStyle.Success),new ButtonBuilder().setCustomId('poll-no').setLabel('👎 No').setStyle(ButtonStyle.Danger))]}); }
      case '8ball': return i.reply(['🎱 Yes.','🎱 No.','🎱 Maybe.','🎱 Definitely.','🎱 Ask again later.'][Math.floor(Math.random()*5)]);
      case 'coinflip': return i.reply(`🪙 **${Math.random()<.5?'Heads':'Tails'}**`);
      case 'roll': { const n=Math.max(2,Math.min(1000,Number(i.options.getString('sides'))||6)); return i.reply(`🎲 You rolled **${Math.floor(Math.random()*n)+1}** / ${n}`); }
      case 'choose': { const a=i.options.getString('options').split(',').map(x=>x.trim()).filter(Boolean); return i.reply(a.length?`🎯 I choose **${a[Math.floor(Math.random()*a.length)]}**`:'Give me comma-separated options.'); }
      case 'kick': { if(!needPerm(i,PermissionFlagsBits.KickMembers))return i.reply(err('You need Kick Members.')); const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); if(!m.kickable)return i.reply(err('I cannot kick that member.')); await m.kick(i.options.getString('reason')||'No reason'); await log(i.guild,'Member Kicked',`${m.user.tag} was kicked by ${i.user.tag}.`,true); return i.reply(ok(`Kicked ${m.user.tag}.`)); }
      case 'ban': { if(!needPerm(i,PermissionFlagsBits.BanMembers))return i.reply(err('You need Ban Members.')); const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); if(!m.bannable)return i.reply(err('I cannot ban that member.')); await m.ban({reason:i.options.getString('reason')||'No reason'}); await log(i.guild,'Member Banned',`${m.user.tag} was banned by ${i.user.tag}.`,true); return i.reply(ok(`Banned ${m.user.tag}.`)); }
      case 'unban': if(!needPerm(i,PermissionFlagsBits.BanMembers))return i.reply(err('You need Ban Members.')); await i.guild.members.unban(i.options.getString('user')); return i.reply(ok('User unbanned.'));
      case 'timeout': { if(!needPerm(i,PermissionFlagsBits.ModerateMembers))return i.reply(err('You need Moderate Members.')); const m=memberFrom(i,i.options.getString('user')), ms=parseDuration(i.options.getString('duration')); if(!m||!ms)return i.reply(err('Member or duration invalid.')); if(ms>2419200000)return i.reply(err('Maximum timeout is 28 days.')); await m.timeout(ms,i.options.getString('reason')||'No reason'); return i.reply(ok(`Timed out ${m.user.tag}.`)); }
      case 'untimeout': { if(!needPerm(i,PermissionFlagsBits.ModerateMembers))return i.reply(err('You need Moderate Members.')); const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); await m.timeout(null); return i.reply(ok(`Removed timeout from ${m.user.tag}.`)); }
      case 'warn': { if(!needPerm(i,PermissionFlagsBits.ModerateMembers))return i.reply(err('You need Moderate Members.')); const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); const w=cfg.warnings[m.id] ||= []; w.push({reason:i.options.getString('reason')||'No reason',by:i.user.id,at:Date.now()}); save(db); await log(i.guild,'Member Warned',`${m.user.tag} was warned. Reason: ${w.at(-1).reason}`,true); return i.reply(ok(`${m.user.tag} warned. Total warnings: ${w.length}`)); }
      case 'warnings': { const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); const w=cfg.warnings[m.id]||[]; return i.reply({embeds:[embed(`⚠️ Warnings — ${m.user.tag}`,w.length?w.map((x,n)=>`**${n+1}.** ${x.reason} — <@${x.by}>`).join('\n'):'No warnings.') ]}); }
      case 'clearwarnings': if(!needPerm(i,PermissionFlagsBits.ModerateMembers))return i.reply(err('You need Moderate Members.')); { const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); delete cfg.warnings[m.id]; save(db); return i.reply(ok(`Cleared warnings for ${m.user.tag}.`)); }
      case 'purge': if(!needPerm(i,PermissionFlagsBits.ManageMessages))return i.reply(err('You need Manage Messages.')); { const n=Math.max(1,Math.min(100,Number(i.options.getString('amount'))||1)); const deleted=await i.channel.bulkDelete(n,true); return i.reply({content:`🧹 Deleted **${deleted.size}** messages.`,ephemeral:true}); }
      case 'lock': if(!needPerm(i,PermissionFlagsBits.ManageChannels))return i.reply(err('You need Manage Channels.')); await i.channel.permissionOverwrites.edit(i.guild.roles.everyone,{SendMessages:false}); return i.reply(ok('Channel locked.'));
      case 'unlock': if(!needPerm(i,PermissionFlagsBits.ManageChannels))return i.reply(err('You need Manage Channels.')); await i.channel.permissionOverwrites.edit(i.guild.roles.everyone,{SendMessages:null}); return i.reply(ok('Channel unlocked.'));
      case 'slowmode': if(!needPerm(i,PermissionFlagsBits.ManageChannels))return i.reply(err('You need Manage Channels.')); { const s=Math.max(0,Math.min(21600,Number(i.options.getString('seconds'))||0)); await i.channel.setRateLimitPerUser(s); return i.reply(ok(`Slowmode set to ${s}s.`)); }
      case 'nick': if(!needPerm(i,PermissionFlagsBits.ManageNicknames))return i.reply(err('You need Manage Nicknames.')); { const m=memberFrom(i,i.options.getString('user')); if(!m)return i.reply(err('Member not found.')); await m.setNickname(i.options.getString('nickname')); return i.reply(ok('Nickname updated.')); }
      case 'setwelcome': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.welcomeChannel=i.options.getString('channel'); save(db); return i.reply(ok('Welcome channel saved.'));
      case 'setwelcome-message': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.welcomeMessage=i.options.getString('message'); save(db); return i.reply(ok('Welcome message saved.'));
      case 'setlogs': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.logChannel=i.options.getString('channel'); save(db); return i.reply(ok('Log channel saved.'));
      case 'setmodlogs': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.modLogChannel=i.options.getString('channel'); save(db); return i.reply(ok('Moderation log channel saved.'));
      case 'setautorole': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.autoRole=i.options.getString('role'); save(db); return i.reply(ok('Autorole saved.'));
      case 'autorole': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); cfg.autoroleEnabled=i.options.getString('enabled').toLowerCase()==='true'; save(db); return i.reply(ok(`Autorole ${cfg.autoroleEnabled?'enabled':'disabled'}.`));
      case 'automod': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); { const f=i.options.getString('feature'); if(!Object.hasOwn(cfg.automod,f))return i.reply(err('Feature must be links, invites, caps or spam.')); cfg.automod[f]=i.options.getString('enabled').toLowerCase()==='true'; save(db); return i.reply(ok(`Automod ${f}: ${cfg.automod[f]?'ON':'OFF'}`)); }
      case 'config': return i.reply({embeds:[embed('⚙️ Server Configuration',`Welcome: ${cfg.welcomeChannel?`<#${cfg.welcomeChannel}>`:'Not set'}\nLogs: ${cfg.logChannel?`<#${cfg.logChannel}>`:'Not set'}\nMod logs: ${cfg.modLogChannel?`<#${cfg.modLogChannel}>`:'Not set'}\nAutorole: ${cfg.autoroleEnabled&&cfg.autoRole?`<@&${cfg.autoRole}>`:'Off'}\nAutomod: ${Object.entries(cfg.automod).map(([k,v])=>`${k}: ${v?'ON':'OFF'}`).join(' • ')}`)]});
      case 'disable': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); { const n=i.options.getString('command').replace(/^\//,'').toLowerCase(); if(!commandData.some(x=>x.name===n))return i.reply(err('Unknown command.')); if(!cfg.disabled.includes(n))cfg.disabled.push(n); save(db); return i.reply(ok(`/${n} disabled.`)); }
      case 'enable': if(!needPerm(i,PermissionFlagsBits.ManageGuild))return i.reply(err('You need Manage Server.')); { const n=i.options.getString('command').replace(/^\//,'').toLowerCase(); cfg.disabled=cfg.disabled.filter(x=>x!==n); save(db); return i.reply(ok(`/${n} enabled.`)); }
      case 'lockdown': if(!needPerm(i,PermissionFlagsBits.Administrator))return i.reply(err('You need Administrator.')); await Promise.all(i.guild.channels.cache.filter(c=>c.type===ChannelType.GuildText).map(c=>c.permissionOverwrites.edit(i.guild.roles.everyone,{SendMessages:false}).catch(()=>{}))); return i.reply(ok('Server lockdown enabled.'));
      case 'unlockdown': if(!needPerm(i,PermissionFlagsBits.Administrator))return i.reply(err('You need Administrator.')); await Promise.all(i.guild.channels.cache.filter(c=>c.type===ChannelType.GuildText).map(c=>c.permissionOverwrites.edit(i.guild.roles.everyone,{SendMessages:null}).catch(()=>{}))); return i.reply(ok('Server lockdown removed.'));
      case 'invite': { const inv=await i.channel.createInvite({maxAge:3600,maxUses:5,unique:true}); return i.reply(`🔗 ${inv.url}`); }
      case 'support': return i.reply({embeds:[embed('🛠️ Support','Use `/help` for commands. Configure moderation and logging with `/config`.')],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('ticket-create').setLabel('Create Ticket').setEmoji('🎫').setStyle(ButtonStyle.Primary))]});
      case 'ticket': return createTicket(i);
      case 'close': if(!i.channel.name.startsWith('ticket-'))return i.reply(err('Use this inside a ticket.')); await i.reply('🔒 Closing ticket...'); return setTimeout(()=>i.channel.delete().catch(()=>{}),1000);
    }
  } catch(e) { console.error(e); if(i.replied||i.deferred) i.followUp(err('Something went wrong while running that command.')); else i.reply(err('Something went wrong while running that command.')); }
});

async function createTicket(i) {
  const existing=i.guild.channels.cache.find(c=>c.name===`ticket-${i.user.id}`); if(existing)return i.reply({content:`You already have a ticket: ${existing}`,ephemeral:true});
  const ch=await i.guild.channels.create({name:`ticket-${i.user.id}`,type:ChannelType.GuildText,permissionOverwrites:[{id:i.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:i.user.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]}]});
  await ch.send({embeds:[embed('🎫 Support Ticket',`Hello ${i.user}! Explain your issue here. A staff member will help you.\n\nUse \`/close\` when finished.`)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('ticket-close').setLabel('Close Ticket').setEmoji('🔒').setStyle(ButtonStyle.Danger))]});
  return i.reply({content:`🎫 Ticket created: ${ch}`,ephemeral:true});
}

process.on('unhandledRejection', e => console.error('Unhandled rejection:', e));
if(!process.env.DISCORD_TOKEN || !process.env.CLIENT_ID) console.error('Missing DISCORD_TOKEN or CLIENT_ID in environment variables.');
else client.login(process.env.DISCORD_TOKEN);
