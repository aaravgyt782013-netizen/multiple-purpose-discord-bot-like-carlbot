const fs = require('node:fs');
const path = require('node:path');
const dns = require('node:dns').promises;
const mc = require('minecraft-protocol');
const { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const DATA_DIR = path.join(process.cwd(), 'data');
const MONITORS_FILE = path.join(DATA_DIR, 'minecraft-monitors.json');
const INTERVAL = Math.max(30, Number(process.env.MC_STATUS_INTERVAL_SECONDS || 60)) * 1000;
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(MONITORS_FILE)) fs.writeFileSync(MONITORS_FILE, '[]');

function readMonitors() {
  try {
    const value = JSON.parse(fs.readFileSync(MONITORS_FILE, 'utf8'));
    return Array.isArray(value) ? value : [];
  } catch { return []; }
}
function saveMonitors(value) { fs.writeFileSync(MONITORS_FILE, JSON.stringify(value, null, 2)); }

function parseAddress(input) {
  let value = String(input || '').trim().replace(/^minecraft:\/\//i, '').replace(/^https?:\/\//i, '').replace(/\/.*$/, '');
  if (!value) throw new Error('Minecraft server address is required.');
  if (value.startsWith('[')) {
    const end = value.indexOf(']');
    if (end < 0) throw new Error('Invalid IPv6 address.');
    const host = value.slice(1, end);
    const rawPort = value.slice(end + 1);
    const port = rawPort.startsWith(':') ? Number(rawPort.slice(1)) : 25565;
    return { host, port: Number.isInteger(port) && port > 0 && port <= 65535 ? port : 25565 };
  }
  const match = value.match(/^(.+):(\d+)$/);
  if (match) {
    const port = Number(match[2]);
    if (port < 1 || port > 65535) throw new Error('Port must be between 1 and 65535.');
    return { host: match[1], port };
  }
  return { host: value, port: 25565 };
}

function cleanMotd(value) {
  if (typeof value === 'string') return value.replace(/§[0-9A-FK-OR]/gi, '').trim() || 'N/A';
  if (!value) return 'N/A';
  const parts = [];
  const walk = item => {
    if (typeof item === 'string') parts.push(item);
    else if (Array.isArray(item)) item.forEach(walk);
    else if (item && typeof item === 'object') {
      if (typeof item.text === 'string') parts.push(item.text);
      if (item.extra) walk(item.extra);
    }
  };
  walk(value);
  return parts.join('').replace(/§[0-9A-FK-OR]/gi, '').trim() || 'N/A';
}

async function resolvePublicNetwork(host, port) {
  let targetHost = host;
  let targetPort = port;
  let srv = null;
  if (port === 25565 && !/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host) && !host.includes(':')) {
    try {
      const records = await dns.resolveSrv('_minecraft._tcp.' + host);
      if (records.length) {
        records.sort((a, b) => a.priority - b.priority || b.weight - a.weight);
        const record = records[0];
        targetHost = record.name.replace(/\.$/, '');
        targetPort = record.port;
        srv = { host: targetHost, port: targetPort };
      }
    } catch {}
  }
  let ip = null;
  try { ip = (await dns.lookup(targetHost, { family: 4 })).address; } catch {}
  return { targetHost, targetPort, ip, srv };
}

async function getStatus(address) {
  const input = parseAddress(address);
  const network = await resolvePublicNetwork(input.host, input.port);
  const started = Date.now();
  try {
    const result = await mc.ping({ host: network.targetHost, port: network.targetPort });
    const latency = Number.isFinite(result.latency) ? result.latency : Date.now() - started;
    const sample = Array.isArray(result.players && result.players.sample)
      ? result.players.sample.map(p => typeof p === 'string' ? p : p && p.name).filter(Boolean)
      : [];
    const version = result.version || {};
    return { online: true, inputHost: input.host, inputPort: input.port, publicIp: network.ip,
      srv: network.srv ? network.srv.host + ':' + network.srv.port : null, motd: cleanMotd(result.description),
      version: version.name || 'Unknown', protocol: version.protocol == null ? 'N/A' : version.protocol,
      onlinePlayers: result.players && result.players.online != null ? result.players.online : 0,
      maxPlayers: result.players && result.players.max != null ? result.players.max : 0,
      players: sample, latency, proxy: detectProxy(version.name, result.description), error: null };
  } catch (error) {
    return { online: false, inputHost: input.host, inputPort: input.port, publicIp: network.ip,
      srv: network.srv ? network.srv.host + ':' + network.srv.port : null, motd: 'Server did not respond.',
      version: 'N/A', protocol: 'N/A', onlinePlayers: 0, maxPlayers: 0, players: [], latency: null,
      proxy: [], error: error.message };
  }
}

function detectProxy(version, description) {
  const text = (cleanMotd(description) + ' ' + String(version || '')).toLowerCase();
  return ['velocity', 'bungeecord', 'waterfall', 'travertine'].filter(name => text.includes(name));
}
function shorten(value, max) {
  const text = String(value || 'N/A');
  return text.length > max ? text.slice(0, max - 3) + '...' : text;
}

function statusEmbed(status, address) {
  const embed = new EmbedBuilder().setTitle('Minecraft Server — ' + address).setColor(status.online ? 0x2ecc71 : 0xe74c3c).setTimestamp();
  if (status.online) {
    embed.setDescription(shorten(status.motd, 1000));
    embed.addFields(
      { name: 'Status', value: '🟢 Online', inline: true },
      { name: 'Version', value: shorten(String(status.version) + ' (protocol ' + status.protocol + ')', 100), inline: true },
      { name: 'Players', value: String(status.onlinePlayers) + ' / ' + String(status.maxPlayers), inline: true },
      { name: 'Latency', value: status.latency == null ? 'N/A' : String(status.latency) + ' ms', inline: true },
      { name: 'Numeric IP', value: status.publicIp ? status.publicIp + ':' + status.inputPort : 'Not resolved', inline: true },
      { name: 'SRV', value: status.srv || 'N/A', inline: true }
    );
    if (status.proxy.length) embed.addFields({ name: 'Proxy / Velocity Check', value: '**Proxy detected** — signatures: ' + status.proxy.join(', ') });
    embed.addFields({ name: 'Player Sample', value: status.players.length ? shorten(status.players.slice(0, 24).join(', '), 900) : 'The server did not provide a player sample.' });
  } else {
    embed.setDescription('The server could not be reached.');
    embed.addFields(
      { name: 'Status', value: '🔴 Offline', inline: true },
      { name: 'Host', value: status.inputHost, inline: true },
      { name: 'Port', value: String(status.inputPort), inline: true },
      { name: 'Numeric IP', value: status.publicIp ? status.publicIp + ':' + status.inputPort : 'Not resolved', inline: false },
      { name: 'Error', value: shorten(status.error || 'No response.', 900), inline: false }
    );
  }
  return embed.setFooter({ text: 'LightCore Minecraft Status • Public DNS/IP only; private proxy backends are not exposed' });
}

function actionRow(address) {
  const encoded = encodeURIComponent(address);
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('mc-refresh:' + encoded).setLabel('Refresh').setEmoji('🔄').setStyle(ButtonStyle.Primary),
    new ButtonBuilder().setCustomId('mc-players:' + encoded).setLabel('Players').setEmoji('👥').setStyle(ButtonStyle.Secondary)
  );
}

const commands = [
  new SlashCommandBuilder().setName('mcstatus').setDescription('Check a Minecraft Java server.').addStringOption(o => o.setName('server').setDescription('Example: play.example.com:25565').setRequired(true)),
  new SlashCommandBuilder().setName('mcplayers').setDescription('Show the player sample returned by a Minecraft server.').addStringOption(o => o.setName('server').setDescription('Minecraft server address').setRequired(true)),
  new SlashCommandBuilder().setName('mcip').setDescription('Show the public numeric IP and SRV target.').addStringOption(o => o.setName('server').setDescription('Minecraft server hostname').setRequired(true)),
  new SlashCommandBuilder().setName('mcmonitor').setDescription('Create an automatic Minecraft status monitor in this channel.').setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild).addStringOption(o => o.setName('server').setDescription('Minecraft server address').setRequired(true)),
  new SlashCommandBuilder().setName('mcunmonitor').setDescription('Stop a Minecraft status monitor.').setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild).addStringOption(o => o.setName('server').setDescription('Minecraft server address').setRequired(true)),
  new SlashCommandBuilder().setName('mcmonitors').setDescription('List Minecraft monitors in this server.').setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
].map(x => x.toJSON());
const commandNames = new Set(commands.map(x => x.name));

async function handleCommand(interaction) {
  const name = interaction.commandName;
  if (!commandNames.has(name)) return false;
  if (name === 'mcstatus') {
    const server = interaction.options.getString('server', true);
    await interaction.deferReply();
    const status = await getStatus(server);
    await interaction.editReply({ embeds: [statusEmbed(status, server)], components: [actionRow(server)] });
    return true;
  }
  if (name === 'mcplayers') {
    const server = interaction.options.getString('server', true);
    await interaction.deferReply({ ephemeral: true });
    const status = await getStatus(server);
    const players = status.players.length ? status.players.map((p, i) => (i + 1) + '. ' + p).join('\n') : 'No player sample was provided by the server.';
    await interaction.editReply({ embeds: [new EmbedBuilder().setTitle('Online Player Sample — ' + server).setColor(status.online ? 0x2ecc71 : 0xe74c3c).setDescription(shorten(players, 3900)).setFooter({ text: String(status.onlinePlayers) + ' / ' + String(status.maxPlayers) + ' online • Server-provided sample' })] });
    return true;
  }
  if (name === 'mcip') {
    const server = interaction.options.getString('server', true);
    await interaction.deferReply();
    const status = await getStatus(server);
    await interaction.editReply({ embeds: [new EmbedBuilder().setTitle('Network Details — ' + server).setColor(status.online ? 0x2ecc71 : 0xe74c3c).addFields(
      { name: 'Status', value: status.online ? '🟢 Online' : '🔴 Offline', inline: true },
      { name: 'Host', value: status.inputHost, inline: true },
      { name: 'Port', value: String(status.inputPort), inline: true },
      { name: 'Public IP', value: status.publicIp || 'Not resolved', inline: true },
      { name: 'SRV Target', value: status.srv || 'N/A', inline: false }
    ).setFooter({ text: 'Only publicly resolvable network information is shown.' })] });
    return true;
  }
  if (name === 'mcmonitor') {
    const server = interaction.options.getString('server', true);
    await interaction.deferReply();
    const status = await getStatus(server);
    const message = await interaction.channel.send({ embeds: [statusEmbed(status, server)], components: [actionRow(server)] });
    const monitors = readMonitors().filter(x => !(x.guildId === interaction.guildId && x.server.toLowerCase() === server.toLowerCase()));
    monitors.push({ guildId: interaction.guildId, channelId: interaction.channelId, messageId: message.id, server, createdBy: interaction.user.id, createdAt: new Date().toISOString() });
    saveMonitors(monitors);
    await interaction.editReply('✅ Monitoring ' + server + ' every ' + (INTERVAL / 1000) + 's in this channel.');
    return true;
  }
  if (name === 'mcunmonitor') {
    const server = interaction.options.getString('server', true);
    const before = readMonitors();
    const after = before.filter(x => !(x.guildId === interaction.guildId && x.server.toLowerCase() === server.toLowerCase()));
    saveMonitors(after);
    await interaction.reply({ content: after.length < before.length ? '🛑 Stopped monitoring ' + server + '.' : 'No monitor found for ' + server + '.', ephemeral: true });
    return true;
  }
  if (name === 'mcmonitors') {
    const monitors = readMonitors().filter(x => x.guildId === interaction.guildId);
    const description = monitors.length ? monitors.map((x, i) => (i + 1) + '. ' + x.server + ' → <#' + x.channelId + '>').join('\n') : 'No Minecraft monitors are configured.';
    await interaction.reply({ embeds: [new EmbedBuilder().setTitle('Active Minecraft Monitors').setColor(0x5865f2).setDescription(description)], ephemeral: true });
    return true;
  }
  return false;
}

async function handleButton(interaction) {
  if (!interaction.isButton() || !interaction.customId.startsWith('mc-')) return false;
  const parts = interaction.customId.split(':');
  const action = parts.shift();
  const server = decodeURIComponent(parts.join(':'));
  const status = await getStatus(server);
  if (action === 'mc-refresh') {
    await interaction.update({ embeds: [statusEmbed(status, server)], components: [actionRow(server)] });
    return true;
  }
  if (action === 'mc-players') {
    const players = status.players.length ? status.players.map((p, i) => (i + 1) + '. ' + p).join('\n') : 'No player sample was provided by the server.';
    await interaction.reply({ embeds: [new EmbedBuilder().setTitle('Online Player Sample — ' + server).setColor(status.online ? 0x2ecc71 : 0xe74c3c).setDescription(shorten(players, 3900)).setFooter({ text: String(status.onlinePlayers) + ' / ' + String(status.maxPlayers) + ' online • Server-provided sample' })], ephemeral: true });
    return true;
  }
  return false;
}

async function updateMonitor(client, monitor) {
  try {
    const channel = await client.channels.fetch(monitor.channelId);
    if (!channel || !channel.isTextBased()) return;
    const message = await channel.messages.fetch(monitor.messageId);
    const status = await getStatus(monitor.server);
    await message.edit({ embeds: [statusEmbed(status, monitor.server)], components: [actionRow(monitor.server)] });
  } catch (error) { console.error('Minecraft monitor ' + monitor.server + ': ' + error.message); }
}

function startMonitor(client) {
  const tick = async () => {
    for (const monitor of readMonitors()) await updateMonitor(client, monitor);
  };
  setTimeout(tick, 5000);
  setInterval(tick, INTERVAL);
}

module.exports = { commands, commandNames, handleCommand, handleButton, startMonitor, getStatus };