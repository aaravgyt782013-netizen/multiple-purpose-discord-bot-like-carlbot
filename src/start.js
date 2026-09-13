require('dotenv').config();
const http = require('http');

process.on('uncaughtException', error => console.error('[FATAL] Uncaught exception:', error?.stack || error));
process.on('unhandledRejection', error => console.error('[FATAL] Unhandled rejection:', error?.stack || error));
process.on('warning', warning => console.warn('[NODE WARNING]', warning?.stack || warning));

const port = Number(process.env.PORT || 10000);
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('LightCore Discord bot is running.\n');
});
server.listen(port, '0.0.0.0', () => console.log(`[HTTP] Health server listening on port ${port}`));

if (!process.env.DISCORD_TOKEN) {
  console.error('[CONFIG] DISCORD_TOKEN is missing. Add it to Render Environment Variables.');
  process.exitCode = 1;
} else {
  console.log(`[START] Loading LightCore with Render prefix: ${process.env.PREFIX || '!'}`);

  // Compatibility fix for the interactive help menu. The previous code used
  // label[0] for emojis; multi-code-unit emojis could become invalid Discord
  // emoji data and make the whole .help command fail. Normalize recursively.
  try {
    const { StringSelectMenuBuilder } = require('discord.js');
    const originalAddOptions = StringSelectMenuBuilder.prototype.addOptions;
    const fixOptions = value => {
      if (Array.isArray(value)) return value.map(fixOptions);
      if (!value || typeof value !== 'object' || !value.emoji) return value;
      return { ...value, emoji: typeof value.emoji === 'string' ? Array.from(value.emoji)[0] : value.emoji };
    };
    StringSelectMenuBuilder.prototype.addOptions = function (...options) {
      return originalAddOptions.call(this, ...fixOptions(options));
    };
  } catch (error) {
    console.warn('[HELP PATCH] Could not install emoji compatibility patch:', error?.message || error);
  }

  // Prefix-first build: remove stale global slash commands from older builds.
  if (process.env.CLIENT_ID) {
    try {
      const { REST, Routes } = require('discord.js');
      const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
      rest.put(Routes.applicationCommands(process.env.CLIENT_ID), { body: [] })
        .then(() => console.log('[DISCORD] Cleared stale global slash commands.'))
        .catch(error => console.warn('[DISCORD] Could not clear stale slash commands:', error?.message || error));
    } catch (error) {
      console.warn('[DISCORD] Slash cleanup unavailable:', error?.message || error);
    }
  }

  require('./prefix.js');
}

setInterval(() => console.log('[HEALTH] LightCore process is alive.'), 60000).unref();
