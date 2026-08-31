// Render entrypoint: keep this wrapper minimal.
// The bot itself (src/index.js) owns the HTTP health server, Discord login,
// ready handling, and slash-command synchronization.
require('dotenv').config();

try {
  require('./index.js');
} catch (err) {
  console.error('❌ Bot startup failed:', err);
  process.exitCode = 1;
}
