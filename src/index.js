require('dotenv').config();
const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const minecraftStatus = require('./minecraft-status');

const BOT_TOKEN = process.env.BOT_TOKEN;
const BOT_NAME = (process.env.BOT_NAME || '').trim();
const CLIENT_ID = process.env.CLIENT_ID || '';

if (!BOT_TOKEN) {
  console.error('Missing BOT_TOKEN environment variable.');
  process.exit(1);
}

const client = new Client({
  intents: [GatewayIntentBits.Guilds]
});

async function registerCommands() {
  if (!CLIENT_ID) throw new Error('Missing CLIENT_ID environment variable.');
  const rest = new REST({ version: '10' }).setToken(BOT_TOKEN);
  await rest.put(
    Routes.applicationCommands(CLIENT_ID),
    { body: minecraftStatus.commands }
  );
}

client.once('ready', async () => {
  console.log(`Logged in as ${client.user.tag}`);
  if (BOT_NAME && BOT_NAME !== client.user.username) {
    try {
      await client.user.setUsername(BOT_NAME);
      console.log(`Bot name set to ${BOT_NAME}`);
    } catch (error) {
      console.error('Could not set BOT_NAME:', error.message);
    }
  }
  minecraftStatus.startMonitor(client);
});

client.on('interactionCreate', async interaction => {
  try {
    if (interaction.isButton()) {
      const handled = await minecraftStatus.handleButton(interaction);
      if (handled) return;
    }
    if (interaction.isChatInputCommand()) {
      await minecraftStatus.handleCommand(interaction);
    }
  } catch (error) {
    console.error('Interaction error:', error);
    const payload = { content: '❌ Something went wrong while processing that command.', ephemeral: true };
    if (interaction.deferred || interaction.replied) await interaction.followUp(payload).catch(() => {});
    else await interaction.reply(payload).catch(() => {});
  }
});

(async () => {
  try {
    await registerCommands();
    await client.login(BOT_TOKEN);
  } catch (error) {
    console.error('Startup error:', error);
    process.exit(1);
  }
})();
