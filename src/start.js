require('dotenv').config();
const http = require('http');

process.env.PREFIX = '.';

process.on('uncaughtException', error => console.error('[FATAL] Uncaught exception:', error?.stack || error));
process.on('unhandledRejection', error => console.error('[FATAL] Unhandled rejection:', error?.stack || error));
process.on('warning', warning => console.warn('[NODE WARNING]', warning?.stack || warning));

const port = Number(process.env.PORT || 10000);
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('LightCore all-in-one Discord bot is running.\n');
});
server.listen(port, '0.0.0.0', () => console.log(`[HTTP] Health server listening on port ${port}`));

if (!process.env.DISCORD_TOKEN) {
  console.error('[CONFIG] DISCORD_TOKEN is missing. Add it to Render Environment Variables.');
  process.exitCode = 1;
} else {
  console.log('[START] Loading LightCore All-in-One engine | prefix: .');
  const bot = require('./ultra.js');
  if (bot && bot.client && typeof bot.attachFeaturePack === 'function') {
    bot.attachFeaturePack(bot.client, bot.db, bot.save, bot.gd, '.');
  }
  if (bot && bot.client && bot.registerSlash) {
    bot.client.once('ready', async () => {
      try { await bot.registerSlash(); }
      catch (error) { console.error('[SLASH REGISTER] Failed:', error?.stack || error); }
    });
  }
}

setInterval(() => console.log('[HEALTH] LightCore process is alive.'), 60000).unref();
