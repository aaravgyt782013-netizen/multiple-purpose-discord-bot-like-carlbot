require('dotenv').config();
const http = require('http');

// Render Web Services require a listening HTTP port. Start it BEFORE
// Discord command registration so a slow global registration never causes
// Render to report "No open ports detected".
const port = Number(process.env.PORT || 10000);
const server = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, service: 'discord-bot' }));
  }
  res.writeHead(200, { 'content-type': 'text/plain; charset=utf-8' });
  res.end('Aarav All-In-One Discord Bot is running.');
});

server.listen(port, '0.0.0.0', () => {
  console.log(`🌐 Render health server listening on ${port}`);
});

// Start the Discord bot immediately. Slash registration is intentionally
// separate and may take longer without blocking Render's port detection.
require('./index.js');

// Register commands in parallel after the bot process has started.
setImmediate(() => {
  try {
    require('./register.js');
  } catch (err) {
    console.error('❌ Slash registration startup error:', err);
  }
});

process.on('SIGTERM', () => server.close(() => process.exit(0)));
process.on('SIGINT', () => server.close(() => process.exit(0)));
