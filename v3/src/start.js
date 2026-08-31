// Aarav All-In-One Render entrypoint.
// - Uses ! as the client-command prefix.
// - Forces slash commands into every guild after the global sync so they appear immediately.
// - Patches the exported help renderer so !help lists every client command.
require('dotenv').config();

const { Client, REST, Routes, EmbedBuilder } = require('discord.js');
const commands = require('./commands');

process.env.PREFIX = '!';

// Keep a reference to the actual client created by index.js.
const originalLogin = Client.prototype.login;
Client.prototype.login = function (...args) {
  global.__aaravDiscordClient = this;
  return originalLogin.apply(this, args);
};

// index.js already performs the authoritative global PUT. Discord global
// commands can take time to propagate, so mirror that same command body to
// every guild the bot is actually connected to.
const originalPut = REST.prototype.put;
REST.prototype.put = async function (fullRoute, options) {
  const result = await originalPut.call(this, fullRoute, options);
  const route = String(fullRoute);
  const match = route.match(/\/applications\/(\d+)\/commands$/);
  const client = global.__aaravDiscordClient;

  if (match && client?.readyAt && client.guilds?.cache?.size) {
    const applicationId = match[1];
    let synced = 0;
    for (const guild of client.guilds.cache.values()) {
      try {
        await originalPut.call(
          this,
          Routes.applicationGuildCommands(applicationId, guild.id),
          options
        );
        synced++;
      } catch (err) {
        console.error(`⚠️ Could not sync commands to ${guild.name} (${guild.id}):`, err?.message || err);
      }
    }
    console.log(`⚡ Immediate guild slash sync: ${synced}/${client.guilds.cache.size} guilds.`);
  }

  return result;
};

// !help should show the complete client-command catalog.
const clientHelp = () => {
  const list = commands.prefixCommands.map(name => `!${name}`);
  const chunks = [];
  for (let i = 0; i < list.length; i += 45) chunks.push(list.slice(i, i + 45).join(' '));

  const embed = new EmbedBuilder()
    .setTitle('🤖 Aarav All-In-One • Client Commands')
    .setDescription(`**${commands.prefixCommands.length} client commands**\nPrefix: !\n\nUse !help anytime to open this list.`)
    .setColor(0x5865f2)
    .setTimestamp()
    .setFooter({ text: 'Client commands • aliases included' });

  chunks.forEach((chunk, index) => {
    embed.addFields({ name: `Commands ${index * 45 + 1}–${Math.min((index + 1) * 45, list.length)}`, value: chunk || 'None' });
  });
  return { embeds: [embed] };
};

const originalCommandListEmbed = commands.commandListEmbed;
commands.commandListEmbed = function (category = 'home') {
  if (category === 'home' || category === 'client') return clientHelp().embeds[0];
  return originalCommandListEmbed(category);
};

try {
  require('./index.js');
} catch (err) {
  console.error('❌ Bot startup failed:', err);
  process.exitCode = 1;
}
