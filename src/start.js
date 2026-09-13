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

  // Older versions of the help menu passed the first UTF-16 code unit of
  // an emoji to Discord. Some emojis are surrogate pairs, which made .help
  // fail at runtime. Normalize select-menu emojis before the bot starts.
  try {
    const { StringSelectMenuBuilder } = require('discord.js');
    const originalAddOptions = StringSelectMenuBuilder.prototype.addOptions;
    StringSelectMenuBuilder.prototype.addOptions = function (...options) {
      const fixed = options.map(option => {
        if (!option || typeof option !== 'object' || !option.emoji) return option;
        const copy = { ...option, emoji: typeof option.emoji === 'string' ? Array.from(option.emoji)[0] : option.emoji };
        return copy;
      });
      return originalAddOptions.call(this, ...fixed);
    };
  } catch (error) {
    console.warn('[HELP PATCH] Could not install emoji compatibility patch:', error?.message || error);
  }

  // This build is prefix-first. Remove stale global slash commands left by
  // older deployments so Discord does not show commands that are no longer
  // handled by the running client.
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
