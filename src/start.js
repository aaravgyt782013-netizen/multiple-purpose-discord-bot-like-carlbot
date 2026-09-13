const http = require('http');

process.on('uncaughtException', (err) => console.error('[FATAL] Uncaught exception:', err?.stack || err));
process.on('unhandledRejection', (err) => console.error('[FATAL] Unhandled rejection:', err?.stack || err));
process.on('warning', (warning) => console.warn('[NODE WARNING]', warning?.stack || warning));
process.on('exit', (code) => console.error(`[PROCESS] Node is exiting with code ${code}`));

const port = Number(process.env.PORT || 10000);
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('LightCore Discord bot is running.\n');
});
server.listen(port, '0.0.0.0', () => console.log(`[HTTP] Health server listening on port ${port}`));

if (!process.env.DISCORD_TOKEN) {
  console.error('[CONFIG] DISCORD_TOKEN is missing. Add it in Render Environment Variables.');
  process.exitCode = 1;
} else {
  console.log('[START] Starting LightCore Discord bot...');
  require('./index.js');
  require('./prefix.js');
}

setInterval(() => console.log('[HEALTH] LightCore process is alive.'), 60000).unref();
