require('dotenv').config();
const http = require('http');
const Module = require('module');

process.on('uncaughtException', (err) => console.error('[FATAL] Uncaught exception:', err?.stack || err));
process.on('unhandledRejection', (err) => console.error('[FATAL] Unhandled rejection:', err?.stack || err));
process.on('warning', (warning) => console.warn('[NODE WARNING]', warning?.stack || warning));

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
  console.log(`[START] Starting LightCore with Render prefix: ${process.env.PREFIX || '!'}`);

  // Load the main bot first. Prefix handling is loaded once below.
  require('./index.js');

  // The prefix command module historically used '!' as its built-in default.
  // Rewrite that default at load time so Render's PREFIX is the actual prefix
  // for every guild, without storing a secret or requiring a guild ID.
  const originalLoader = Module._extensions['.js'];
  Module._extensions['.js'] = function(lightCoreLoader(module, filename) {
    if (filename.endsWith('/src/prefix.js') || filename.endsWith('\\src\\prefix.js')) {
      const fs = require('fs');
      let source = fs.readFileSync(filename, 'utf8');
      const configured = JSON.stringify(process.env.PREFIX || '!');
      source = source.replaceAll("prefix: '!'", `prefix: ${configured}`);
      source = source.replace(
        "const d=data(m.guild.id), p=d.prefix || '!';",
        "const d=data(m.guild.id); d.prefix=process.env.PREFIX || d.prefix || '!'; const p=d.prefix;"
      );
      return module._compile(source, filename);
    }
    return originalLoader(module, filename);
  };

  require('./prefix.js');
}

setInterval(() => console.log('[HEALTH] LightCore process is alive.'), 60000).unref();
