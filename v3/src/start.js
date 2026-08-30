require('dotenv').config();
const http = require('http');

// Bind Render's HTTP port before loading the Discord bot. index.js loads
// several modules/database code synchronously, so requiring it first can
// delay Render's port detection.
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

  // Give the HTTP listener a turn in the event loop before loading the bot.
  // This guarantees Render can detect the port even if bot modules are slow.
  setTimeout(() => {
    try {
      require('./index.js');
    } catch (err) {
      console.error('❌ Discord bot startup error:', err);
    }
  }, 0);

  // Registration uses Discord REST directly and does not need to wait for
  // client.login(). Run it after the bot import has been scheduled.
  setTimeout(() => {
    try {
      require('./register.js');
    } catch (err) {
      console.error('❌ Slash registration startup error:', err);
    }
  }, 1000);
});

process.on('SIGTERM', () => server.close(() => process.exit(0)));
process.on('SIGINT', () => server.close(() => process.exit(0)));
