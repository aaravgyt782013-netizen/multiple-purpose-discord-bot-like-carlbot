require('dotenv').config();

const { REST, Routes } = require('discord.js');
const { slashCommands } = require('./commands');

const token = process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.DEV_GUILD_ID;

if (!token) throw new Error('DISCORD_TOKEN missing');
if (!clientId) throw new Error('CLIENT_ID missing');

const rest = new REST({ version: '10' }).setToken(token);

(async () => {
  try {
    const route = guildId
      ? Routes.applicationGuildCommands(clientId, guildId)
      : Routes.applicationCommands(clientId);

    console.log(`🔄 Registering ${slashCommands.length} slash commands ${guildId ? `in guild ${guildId}` : 'globally'}...`);
    await rest.put(route, { body: slashCommands });
    console.log(`✅ Registered ${slashCommands.length} slash commands.`);
  } catch (error) {
    console.error('❌ Slash command registration failed:', error?.message || error);
    process.exitCode = 1;
  }
})();