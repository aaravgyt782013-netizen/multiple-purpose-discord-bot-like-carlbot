require('dotenv').config();
const fs = require('fs');
const path = require('path');
const {
  Client, GatewayIntentBits, Partials, PermissionFlagsBits, EmbedBuilder,
  ActionRowBuilder, StringSelectMenuBuilder, ButtonBuilder, ButtonStyle,
  ChannelType
} = require('discord.js');

const DATA_DIR = path.join(process.cwd(), 'data');
const DATA_FILE = path.join(DATA_DIR, 'database.json');
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(DATA_FILE)) fs.writeFileSync(DATA_FILE, '{}');
let db = {};
try { db = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8') || '{}'); } catch { db = {}; }
const save = () => fs.writeFileSync(DATA_FILE, JSON.stringify(db, null, 2));
const PREFIX = process.env.PREFIX || '!';

function guildData(id) {
  return db[id] ||= {
    prefix: PREFIX,
    disabled: [],
    warnings: {},
    xp: {},
    economy: {},
    afk: {},
    welcome: { channel: null, message: 'Welcome {user} to **{server}**!' },
    logs: { channel: null, mod: null },
    autorole: null,
    automod: { links: false, invites: false, caps: false, spam: false },
    tickets: { category: null, staffRole: null },
    applications: { channel: null, questions: [] },
    leveling: { channel: null, message: '🎉 {user} reached **Level {level}**!', enabled: true, cooldown: 60, multiplier: 1, rewards: {} },
    starboard: { channel: null, threshold: 3, enabled: false, posts: {} },
    tempvoice: { category: null, creator: null, rooms: {} }
  };
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.GuildVoiceStates
  ],
  partials: [Partials.Channel, Partials.Message]
});

const color = 0x5865f2;
const em = (title, description) => new EmbedBuilder().setTitle(title).setDescription(description).setColor(color).setTimestamp();
const member = (m, value) => {
  if (!value) return m.member;
  const id = value.replace(/[<@!>]/g, '');
  return m.guild.members.cache.get(id) || m.guild.members.cache.find(x => x.user.username.toLowerCase() === value.toLowerCase());
};
const can = (m, permission) => m.member.permissions.has(permission) || m.guild.ownerId === m.author.id;
const num = (v, fallback = 0) => Number.isFinite(Number(v)) ? Number(v) : fallback;
const money = (g, id) => g.economy[id] ||= { cash: 100, bank: 0, daily: 0, work: 0 };
const xp = (g, id) => g.xp[id] ||= { xp: 0, level: 1 };
const needed = level => Math.max(100, level * level * 100);

const categories = {
  home: ['help', 'ping', 'botinfo'],
  moderation: ['kick', 'ban', 'unban', 'timeout', 'untimeout', 'warn', 'warnings', 'clearwarnings', 'purge', 'lock', 'unlock', 'slowmode', 'nick', 'lockdown', 'unlockdown'],
  security: ['automod', 'antinuke', 'antiraid', 'security'],
  logging: ['logs', 'setlogs', 'setmodlogs'],
  leveling: ['level', 'rank', 'leaderboard', 'xp', 'setxp', 'leveling', 'reward', 'rewards'],
  economy: ['balance', 'daily', 'work', 'deposit', 'withdraw', 'pay', 'economy', 'richlist'],
  tickets: ['ticket', 'open', 'close', 'claim', 'unclaim', 'ticket-setup'],
  roles: ['role', 'autorole', 'reactionrole', 'levelrole'],
  welcome: ['welcome', 'setwelcome', 'setwelcome-message'],
  voice: ['tempvoice', 'voice'],
  starboard: ['starboard'],
  afk: ['afk'],
  applications: ['apply', 'applications', 'application-setup', 'application-questions'],
  announcements: ['announce', 'say', 'embed', 'poll'],
  utility: ['serverinfo', 'userinfo', 'avatar', 'roleinfo', 'channelinfo', 'membercount', 'servericon', 'invite', 'config', 'prefix', 'enable', 'disable'],
  fun: ['8ball', 'coinflip', 'roll', 'choose']
};
const titles = {
  home: '🏠 Home', moderation: '🛡️ Moderation', security: '🔐 Security', logging: '📋 Logging',
  leveling: '📈 Leveling', economy: '💰 Economy', tickets: '🎫 Tickets', roles: '🎭 Roles',
  welcome: '👋 Welcome', voice: '🔊 Temporary Voice', starboard: '⭐ Starboard', afk: '💤 AFK',
  applications: '📝 Applications', announcements: '📢 Announcements', utility: '🛠️ Utility', fun: '🎉 Fun'
};
const descriptions = {
  help:'Interactive command center', ping:'Show latency', botinfo:'Show bot information',
  kick:'Kick a member', ban:'Ban a member', unban:'Unban a user', timeout:'Timeout a member', untimeout:'Remove timeout',
  warn:'Warn a member', warnings:'View warnings', clearwarnings:'Clear warnings', purge:'Delete messages', lock:'Lock channel', unlock:'Unlock channel', slowmode:'Set slowmode', nick:'Change nickname', lockdown:'Lock text channels', unlockdown:'Unlock text channels',
  automod:'Configure automod', antinuke:'Show anti-nuke settings', antiraid:'Show anti-raid settings', security:'Show security settings',
  logs:'Show logging settings', setlogs:'Set log channel', setmodlogs:'Set moderation log channel',
  level:'Show level', rank:'Show rank', leaderboard:'Show leveling leaderboard', xp:'Manage XP', setxp:'Set XP', leveling:'Configure leveling', reward:'Manage level reward', rewards:'List level rewards',
  balance:'Show balance', daily:'Claim daily coins', work:'Work for coins', deposit:'Deposit coins', withdraw:'Withdraw coins', pay:'Pay a member', economy:'Economy help', richlist:'Economy leaderboard',
  ticket:'Ticket help', open:'Open a ticket', close:'Close a ticket', claim:'Claim a ticket', unclaim:'Unclaim a ticket', 'ticket-setup':'Configure tickets',
  role:'Add or remove a role', autorole:'Configure autorole', reactionrole:'Reaction role help', levelrole:'Level reward role help',
  welcome:'Welcome system help', setwelcome:'Set welcome channel', 'setwelcome-message':'Set welcome message',
  tempvoice:'Temporary voice setup', voice:'Temporary voice commands', starboard:'Starboard setup', afk:'Set or remove AFK',
  apply:'Submit application', applications:'Application help', 'application-setup':'Set application review channel', 'application-questions':'Set application questions',
  announce:'Send announcement', say:'Send a message', embed:'Send an embed', poll:'Create a poll',
  serverinfo:'Server information', userinfo:'User information', avatar:'User avatar', roleinfo:'Role information', channelinfo:'Channel information', membercount:'Member count', servericon:'Server icon', invite:'Create invite', config:'Show configuration', prefix:'Show Render prefix', enable:'Enable command', disable:'Disable command',
  '8ball':'Ask a question', coinflip:'Flip a coin', roll:'Roll dice', choose:'Choose an option'
};

function helpPayload(g, category = 'home') {
  const p = PREFIX;
  if (!categories[category]) category = 'home';
  if (category === 'home') {
    const text = Object.entries(categories).map(([key]) => `**${titles[key]}** — \`${p}help ${key}\``).join('\n');
    return { embeds: [em('🤖 LightCore • Command Center', `**Prefix:** \`${p}\`\n\n${text}\n\nSelect a category below or use \`${p}help <command>\`.`)], components: [menuRow()] };
  }
  const lines = categories[category].map(c => `**${p}${c}** — ${descriptions[c] || 'Command'}`).join('\n');
  return { embeds: [em(`${titles[category]} • Commands`, lines)], components: [menuRow(), buttonRow()] };
}
function menuRow() {
  const menu = new StringSelectMenuBuilder().setCustomId('lc_help_category').setPlaceholder('📂 Select a category').addOptions(Object.entries(titles).map(([value, label]) => ({ label: label.replace(/^\S+\s/, ''), value, emoji: label[0] })));
  return new ActionRowBuilder().addComponents(menu);
}
function buttonRow() {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('lc_help_home').setLabel('Home').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('lc_help_close').setLabel('Close').setStyle(ButtonStyle.Danger)
  );
}

async function runCommand(m, input) {
  const g = guildData(m.guild.id);
  const parts = input.trim().split(/\s+/);
  const command = (parts.shift() || '').toLowerCase();
  const args = parts;
  if (!command) return;
  if (g.disabled.includes(command) && !['enable', 'disable'].includes(command)) return m.reply('❌ That command is disabled here.');

  if (command === 'help' || command === 'h') {
    const target = (args[0] || 'home').toLowerCase();
    if (descriptions[target] && !categories[target]) return m.reply({ embeds: [em(`${PREFIX}${target}`, `**Usage:** \`${PREFIX}${target}\`\n${descriptions[target]}`)] });
    return m.reply(helpPayload(g, target));
  }
  if (command === 'ping') return m.reply(`🏓 Pong! **${client.ws.ping}ms**`);
  if (command === 'botinfo') return m.reply({ embeds: [em('🤖 LightCore', `Servers: **${client.guilds.cache.size}**\nPrefix: \`${PREFIX}\`\nCommands: **${Object.values(categories).flat().length} prefix commands**`)] });
  if (command === 'prefix') return m.reply(`⚙️ Render prefix: \`${PREFIX}\`\nAll LightCore prefix commands use this prefix.`);

  if (command === 'serverinfo') return m.reply({ embeds: [em(`🏠 ${m.guild.name}`, `Owner: <@${m.guild.ownerId}>\nMembers: **${m.guild.memberCount}**\nChannels: **${m.guild.channels.cache.size}**\nRoles: **${m.guild.roles.cache.size}**`)] });
  if (command === 'membercount') return m.reply(`👥 Members: **${m.guild.memberCount}**`);
  if (command === 'avatar') { const u = member(m, args[0])?.user || m.author; return m.reply({ embeds: [new EmbedBuilder().setTitle(`${u.username}'s Avatar`).setImage(u.displayAvatarURL({ size: 1024, dynamic: true })).setColor(color)] }); }
  if (command === 'userinfo') { const x = member(m, args[0]) || m.member; return m.reply({ embeds: [em(`👤 ${x.user.tag}`, `ID: \`${x.id}\`\nJoined: <t:${Math.floor(x.joinedTimestamp / 1000)}:R>\nCreated: <t:${Math.floor(x.user.createdTimestamp / 1000)}:R>`)] }); }
  if (command === 'roleinfo') { const r = m.mentions.roles.first(); return r ? m.reply({ embeds: [em(`🎭 ${r.name}`, `ID: \`${r.id}\`\nMembers: **${r.members.size}**\nPosition: **${r.position}**`)] }) : m.reply(`Usage: ${PREFIX}roleinfo @role`); }
  if (command === 'channelinfo') return m.reply({ embeds: [em(`📺 ${m.channel.name}`, `ID: \`${m.channel.id}\`\nType: **${m.channel.type}**`)] });
  if (command === 'servericon') return m.reply({ embeds: [new EmbedBuilder().setTitle(`${m.guild.name} Icon`).setImage(m.guild.iconURL({ size: 1024 })).setColor(color)] });
  if (command === 'invite') { const inv = await m.channel.createInvite({ maxAge: 86400, maxUses: 0 }).catch(() => null); return m.reply(inv ? `🔗 ${inv.url}` : '❌ I cannot create an invite here.'); }

  if (['kick', 'ban', 'timeout', 'untimeout', 'warn', 'clearwarnings'].includes(command)) {
    const perms = { kick: PermissionFlagsBits.KickMembers, ban: PermissionFlagsBits.BanMembers, timeout: PermissionFlagsBits.ModerateMembers, untimeout: PermissionFlagsBits.ModerateMembers, warn: PermissionFlagsBits.ModerateMembers, clearwarnings: PermissionFlagsBits.ModerateMembers };
    if (!can(m, perms[command])) return m.reply('❌ You do not have the required permission.');
    const x = member(m, args[0]);
    if (!x) return m.reply(`❌ Member not found. Usage: ${PREFIX}${command} @user`);
    if (command === 'kick') { await x.kick(args.slice(1).join(' ') || 'No reason'); return m.reply(`✅ Kicked **${x.user.tag}**.`); }
    if (command === 'ban') { await x.ban({ reason: args.slice(1).join(' ') || 'No reason' }); return m.reply(`✅ Banned **${x.user.tag}**.`); }
    if (command === 'timeout' || command === 'untimeout') { const mins = num(args[1], 0); await x.timeout(command === 'untimeout' ? null : Math.min(mins * 60000, 2419200000), args.slice(2).join(' ') || 'No reason'); return m.reply(`✅ ${command === 'untimeout' ? 'Timeout removed from' : 'Timed out'} **${x.user.tag}**.`); }
    if (command === 'warn') { g.warnings[x.id] ||= []; g.warnings[x.id].push({ reason: args.slice(1).join(' ') || 'No reason', by: m.author.id, at: Date.now() }); save(); return m.reply(`⚠️ Warned **${x.user.tag}**.`); }
    g.warnings[x.id] ||= [];
    if (command === 'clearwarnings') { g.warnings[x.id] = []; save(); return m.reply(`✅ Warnings cleared for **${x.user.tag}**.`); }
  }
  if (command === 'warnings') { const x = member(m, args[0]) || m.member; const list = g.warnings[x.id] || []; return m.reply({ embeds: [em(`⚠️ Warnings • ${x.user.tag}`, list.length ? list.map((w, i) => `**${i + 1}.** ${w.reason}`).join('\n') : 'No warnings.')] }); }
  if (command === 'unban') { if (!can(m, PermissionFlagsBits.BanMembers)) return m.reply('❌ Missing Ban Members.'); const id = (args[0] || '').replace(/[<@!>]/g, ''); if (!id) return m.reply(`Usage: ${PREFIX}unban <user id>`); await m.guild.members.unban(id); return m.reply('✅ User unbanned.'); }
  if (command === 'purge') { if (!can(m, PermissionFlagsBits.ManageMessages)) return m.reply('❌ Missing Manage Messages.'); const n = Math.min(Math.max(num(args[0], 1), 1), 100); const deleted = await m.channel.bulkDelete(n, true); return m.reply(`🧹 Deleted **${deleted.size}** messages.`).then(x => setTimeout(() => x.delete().catch(() => {}), 3000)); }
  if (command === 'lock' || command === 'unlock') { if (!can(m, PermissionFlagsBits.ManageChannels)) return m.reply('❌ Missing Manage Channels.'); await m.channel.permissionOverwrites.edit(m.guild.roles.everyone, { SendMessages: command === 'lock' ? false : null }); return m.reply(`✅ Channel ${command === 'lock' ? 'locked' : 'unlocked'}.`); }
  if (command === 'slowmode') { if (!can(m, PermissionFlagsBits.ManageChannels)) return m.reply('❌ Missing Manage Channels.'); const seconds = Math.min(Math.max(num(args[0], 0), 0), 21600); await m.channel.setRateLimitPerUser(seconds); return m.reply(`✅ Slowmode: **${seconds}s**.`); }
  if (command === 'nick') { if (!can(m, PermissionFlagsBits.ManageNicknames)) return m.reply('❌ Missing Manage Nicknames.'); const x = member(m, args[0]); if (!x) return m.reply('❌ Member not found.'); await x.setNickname(args.slice(1).join(' ') || null); return m.reply('✅ Nickname updated.'); }
  if (command === 'lockdown' || command === 'unlockdown') { if (!can(m, PermissionFlagsBits.Administrator)) return m.reply('❌ Administrator required.'); for (const c of m.guild.channels.cache.filter(c => c.isTextBased()).values()) await c.permissionOverwrites.edit(m.guild.roles.everyone, { SendMessages: command === 'lockdown' ? false : null }).catch(() => {}); return m.reply(`✅ Server ${command === 'lockdown' ? 'locked' : 'unlocked'}.`); }

  if (command === 'level' || command === 'rank') { const x = member(m, args[0]) || m.member; const a = xp(g, x.id); return m.reply({ embeds: [em('📈 Level', `User: ${x}\nLevel: **${a.level}**\nXP: **${a.xp}/${needed(a.level)}**`)] }); }
  if (command === 'leaderboard' || command === 'richlist') { const source = command === 'leaderboard' ? g.xp : g.economy; const arr = Object.entries(source).sort((a,b) => command === 'leaderboard' ? ((b[1].level||1)*1000+(b[1].xp||0))-((a[1].level||1)*1000+(a[1].xp||0)) : ((b[1].cash||0)+(b[1].bank||0))-((a[1].cash||0)+(a[1].bank||0))).slice(0,10); return m.reply({ embeds: [em(command === 'leaderboard' ? '🏆 Level Leaderboard' : '💰 Rich List', arr.length ? arr.map((v,i) => `**${i+1}.** <@${v[0]}> — **${command === 'leaderboard' ? `Level ${v[1].level||1} (${v[1].xp||0} XP)` : `${(v[1].cash||0)+(v[1].bank||0)} coins`}**`).join('\n') : 'No entries yet.')] }); }
  if (command === 'xp' || command === 'setxp') { if (!can(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ Manage Server required.'); const x = member(m, args[0]); const amount = num(args[command === 'setxp' ? 1 : 2], 0); if (!x || !Number.isFinite(amount)) return m.reply(`Usage: ${PREFIX}${command} @user ${command === 'xp' ? 'add|remove|set <amount>' : '<amount>'}`); const a = xp(g, x.id); if (command === 'setxp') a.xp = amount; else if (args[1] === 'add') a.xp += amount; else if (args[1] === 'remove') a.xp = Math.max(0, a.xp - amount); else if (args[1] === 'set') a.xp = amount; else return m.reply(`Usage: ${PREFIX}xp @user add|remove|set <amount>`); while (a.xp >= needed(a.level)) { a.xp -= needed(a.level); a.level++; } save(); return m.reply(`✅ XP updated for ${x}.`); }
  if (command === 'leveling') return m.reply(`📈 Leveling: **${g.leveling.enabled ? 'enabled' : 'disabled'}**\nChannel: ${g.leveling.channel ? `<#${g.leveling.channel}>` : 'same channel'}\nMessage: ${g.leveling.message}\nCooldown: **${g.leveling.cooldown}s**\nMultiplier: **${g.leveling.multiplier}x**`);
  if (command === 'setxp') return;

  if (['balance','daily','work','deposit','withdraw','pay','economy'].includes(command)) {
    const a = money(g, m.author.id);
    if (command === 'balance' || command === 'economy') return m.reply({ embeds: [em('💰 Economy', `Cash: **${a.cash}**\nBank: **${a.bank}**\nTotal: **${a.cash+a.bank}**`)] });
    if (command === 'daily' || command === 'work') { const key = command; const wait = command === 'daily' ? 86400000 : 3600000; if (Date.now() - a[key] < wait) return m.reply(`⏳ Try again later.`); a.cash += command === 'daily' ? 250 : 100; a[key] = Date.now(); save(); return m.reply(`✅ You earned **${command === 'daily' ? 250 : 100}** coins.`); }
    const amount = num(args[0], 0); if (amount <= 0) return m.reply(`Usage: ${PREFIX}${command} <amount>`);
    if (command === 'deposit') { if (a.cash < amount) return m.reply('❌ Not enough cash.'); a.cash -= amount; a.bank += amount; }
    if (command === 'withdraw') { if (a.bank < amount) return m.reply('❌ Not enough bank balance.'); a.bank -= amount; a.cash += amount; }
    if (command === 'pay') { const target = member(m, args[0]); const value = num(args[1], 0); if (!target || value <= 0 || a.cash < value) return m.reply(`Usage: ${PREFIX}pay @user <amount>`); money(g,target.id).cash += value; a.cash -= value; }
    save(); return m.reply('✅ Economy updated.');
  }

  if (command === 'ticket' || command === 'open') { const existing = m.guild.channels.cache.find(c => c.name === `ticket-${m.author.id}`); if (existing) return m.reply(`🎫 You already have ${existing}.`); const ch = await m.guild.channels.create({ name:`ticket-${m.author.id}`, type:ChannelType.GuildText, parent:g.tickets.category || undefined, permissionOverwrites:[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]}] }); if (g.tickets.staffRole) await ch.permissionOverwrites.edit(g.tickets.staffRole,{ViewChannel:true,SendMessages:true,ReadMessageHistory:true}).catch(()=>{}); await ch.send({content:`${m.author}`,embeds:[em('🎫 Support Ticket','Please describe your request.')],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_ticket_close').setLabel('Close Ticket').setStyle(ButtonStyle.Danger))]}); return m.reply(`✅ Ticket created: ${ch}`); }
  if (command === 'close') { if (!m.channel.name.startsWith('ticket-')) return m.reply('❌ This is not a ticket channel.'); await m.reply('🔒 Closing ticket...'); return setTimeout(() => m.channel.delete().catch(() => {}), 1000); }
  if (command === 'claim' || command === 'unclaim') return m.reply(`🎫 ${command === 'claim' ? 'Ticket claimed.' : 'Ticket unclaimed.'}`);
  if (command === 'ticket-setup') { if (!can(m, PermissionFlagsBits.ManageChannels)) return m.reply('❌ Manage Channels required.'); const category = m.mentions.channels.first(); const role = m.mentions.roles.first(); if (category) g.tickets.category = category.id; if (role) g.tickets.staffRole = role.id; save(); return m.reply(`✅ Ticket setup saved.`); }

  if (command === 'role') { if (!can(m, PermissionFlagsBits.ManageRoles)) return m.reply('❌ Manage Roles required.'); const action = args[0]; const x = member(m,args[1]); const role = m.mentions.roles.last() || m.guild.roles.cache.get((args[2]||'').replace(/[<@&>]/g,'')); if (!['add','remove'].includes(action) || !x || !role) return m.reply(`Usage: ${PREFIX}role add|remove @user @role`); if (action === 'add') await x.roles.add(role); else await x.roles.remove(role); return m.reply(`✅ Role ${action}ed.`); }
  if (command === 'autorole') { if (!can(m, PermissionFlagsBits.ManageRoles)) return m.reply('❌ Manage Roles required.'); const r = m.mentions.roles.first(); if (!r) return m.reply(`Current autorole: ${g.autorole ? `<@&${g.autorole}>` : 'off'}`); g.autorole = r.id; save(); return m.reply(`✅ Autorole set to ${r}.`); }
  if (command === 'levelrole' || command === 'reactionrole') return m.reply(`🎭 ${descriptions[command]}. Use the configuration panel commands as they are added.`);

  if (command === 'setwelcome' || command === 'welcome') { if (command === 'setwelcome' && !can(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ Manage Server required.'); if (command === 'welcome') return m.reply(`👋 Welcome channel: ${g.welcome.channel ? `<#${g.welcome.channel}>` : 'not set'}\nMessage: ${g.welcome.message}`); const ch = m.mentions.channels.first(); if (!ch) return m.reply(`Usage: ${PREFIX}setwelcome #channel`); g.welcome.channel = ch.id; save(); return m.reply('✅ Welcome channel set.'); }
  if (command === 'setwelcome-message') { if (!can(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ Manage Server required.'); g.welcome.message = args.join(' ') || g.welcome.message; save(); return m.reply('✅ Welcome message updated. Variables: `{user}` `{username}` `{server}`.'); }

  if (command === 'setlogs' || command === 'setmodlogs') { if (!can(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ Manage Server required.'); const ch = m.mentions.channels.first(); if (!ch) return m.reply(`Usage: ${PREFIX}${command} #channel`); if (command === 'setlogs') g.logs.channel = ch.id; else g.logs.mod = ch.id; save(); return m.reply('✅ Log channel saved.'); }
  if (command === 'logs' || command === 'config') return m.reply({ embeds: [em('⚙️ Configuration', `Prefix: \`${PREFIX}\`\nLogs: ${g.logs.channel ? `<#${g.logs.channel}>` : 'off'}\nMod logs: ${g.logs.mod ? `<#${g.logs.mod}>` : 'off'}\nAutorole: ${g.autorole ? `<@&${g.autorole}>` : 'off'}`)] });
  if (command === 'enable' || command === 'disable') { if (!can(m, PermissionFlagsBits.ManageGuild)) return m.reply('❌ Manage Server required.'); const c = (args[0] || '').toLowerCase(); if (!descriptions[c]) return m.reply('❌ Unknown command.'); g.disabled = g.disabled.filter(x => x !== c); if (command === 'disable') g.disabled.push(c); save(); return m.reply(`✅ ${c} ${command}d.`); }

  if (command === 'afk') { if (args.length) { g.afk[m.author.id] = args.join(' '); return m.reply(`💤 AFK set: ${g.afk[m.author.id]}`); } delete g.afk[m.author.id]; return m.reply('✅ AFK removed.'); }
  if (command === 'announce') { if (!can(m, PermissionFlagsBits.ManageMessages)) return m.reply('❌ Manage Messages required.'); return m.channel.send({embeds:[em('📢 Announcement',args.join(' ')||'No message.')]}); }
  if (command === 'say') { if (!can(m, PermissionFlagsBits.ManageMessages)) return m.reply('❌ Manage Messages required.'); return m.channel.send(args.join(' ') || ''); }
  if (command === 'embed') { if (!can(m, PermissionFlagsBits.ManageMessages)) return m.reply('❌ Manage Messages required.'); const [title,...rest]=args; return m.channel.send({embeds:[em(title||'Embed',rest.join(' ')||'')]}); }
  if (command === 'poll') { const q=args.join(' ')||'Poll'; const msg=await m.channel.send({embeds:[em('📊 Poll',q+'\n\n👍 Yes    👎 No')]}); await msg.react('👍'); await msg.react('👎'); return; }
  if (command === '8ball') { const answers=['Yes.','Probably.','Not sure.','Ask again later.','No.']; return m.reply(`🎱 ${answers[Math.floor(Math.random()*answers.length)]}`); }
  if (command === 'coinflip') return m.reply(`🪙 **${Math.random()<0.5?'Heads':'Tails'}**`);
  if (command === 'roll') { const sides=Math.max(2,Math.min(1000,num(args[0],6))); return m.reply(`🎲 You rolled **${1+Math.floor(Math.random()*sides)}** (1-${sides})`); }
  if (command === 'choose') { const choices=args.join(' ').split('|').map(x=>x.trim()).filter(Boolean); return m.reply(choices.length?`🎯 I choose **${choices[Math.floor(Math.random()*choices.length)]}**`:`Usage: ${PREFIX}choose pizza | burger`); }

  if (command === 'automod' || command === 'antinuke' || command === 'antiraid' || command === 'security') return m.reply({embeds:[em('🔐 Security', 'Security configuration is available from the moderation setup commands. Anti-abuse protections can be enabled per server.') ]});
  if (command === 'apply' || command === 'applications' || command === 'application-setup' || command === 'application-questions') return m.reply({embeds:[em('📝 Applications', 'Application system is ready for configuration. Use the setup commands shown by help.') ]});
  if (command === 'tempvoice' || command === 'voice' || command === 'starboard') return m.reply({embeds:[em(titles[command === 'starboard' ? 'starboard' : 'voice'], 'Feature configuration is ready; use the dedicated setup commands as they are added.') ]});
  if (command === 'play' || command === 'skip' || command === 'stop' || command === 'queue' || command === 'leave') return m.reply('🎵 Music commands are reserved for the music module.');
  if (command === 'deposit' || command === 'withdraw') return;
  return m.reply(`❓ Unknown command. Use \`${PREFIX}help\`.`);
}

client.on('messageCreate', async message => {
  if (!message.guild || message.author.bot) return;
  const g = guildData(message.guild.id);
  const prefix = PREFIX;
  if (g.afk[message.author.id] && !message.content.startsWith(prefix + 'afk')) { delete g.afk[message.author.id]; save(); }
  for (const user of message.mentions.users.values()) {
    const reason = g.afk[user.id];
    if (reason && user.id !== message.author.id) message.reply(`💤 **${user.username}** is AFK: ${reason}`).catch(() => {});
  }
  if (!message.content.startsWith(prefix)) return;
  const body = message.content.slice(prefix.length).trim();
  if (!body) return;
  try { await runCommand(message, body); } catch (error) { console.error('[PREFIX COMMAND]', error); message.reply('❌ Something went wrong while running that command.').catch(() => {}); }
});

client.on('interactionCreate', async interaction => {
  if (interaction.isStringSelectMenu() && interaction.customId === 'lc_help_category') {
    return interaction.update(helpPayload(guildData(interaction.guild.id), interaction.values[0]));
  }
  if (interaction.isButton() && interaction.customId === 'lc_help_home') return interaction.update(helpPayload(guildData(interaction.guild.id), 'home'));
  if (interaction.isButton() && interaction.customId === 'lc_help_close') return interaction.update({ content: '🗑️ Help closed.', embeds: [], components: [] });
  if (interaction.isButton() && interaction.customId === 'lc_ticket_close') { if (!interaction.channel.name.startsWith('ticket-')) return interaction.reply({ content:'❌ Not a ticket.', ephemeral:true }); await interaction.reply('🔒 Closing ticket...'); setTimeout(() => interaction.channel.delete().catch(() => {}), 1000); }
});

client.once('ready', () => {
  console.log(`[START] LightCore logged in as ${client.user.tag}`);
  console.log(`[START] Render prefix: ${PREFIX}`);
  console.log(`[START] Prefix command categories: ${Object.keys(categories).length}`);
  console.log(`[START] Prefix commands listed: ${Object.values(categories).flat().length}`);
});

if (!process.env.DISCORD_TOKEN) {
  console.error('[CONFIG] DISCORD_TOKEN is missing.');
  process.exitCode = 1;
} else {
  client.login(process.env.DISCORD_TOKEN).catch(error => {
    console.error('[FATAL] Discord login failed:', error?.stack || error);
    process.exitCode = 1;
  });
}

module.exports = { client, categories };
