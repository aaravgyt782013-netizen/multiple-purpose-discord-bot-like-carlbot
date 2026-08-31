require('dotenv').config();
const { REST, Routes } = require('discord.js');
const { slashCommands } = require('./commands');
const token=process.env.DISCORD_TOKEN,clientId=process.env.CLIENT_ID,guildId=process.env.DEV_GUILD_ID||process.env.REGISTER_GUILD_ID;
if(!token)throw new Error('DISCORD_TOKEN missing');
if(!clientId)throw new Error('CLIENT_ID missing');
const rest=new REST({version:'10'}).setToken(token);
(async()=>{try{if(guildId){console.log(`🧹 Clearing old global commands...`);await rest.put(Routes.applicationCommands(clientId),{body:[]});console.log(`🔄 Registering ${slashCommands.length} slash commands in guild ${guildId}...`);await rest.put(Routes.applicationGuildCommands(clientId,guildId),{body:slashCommands});console.log(`✅ Registered ${slashCommands.length} guild slash commands with no global duplicates.`);}else{console.log(`🔄 Registering ${slashCommands.length} slash commands globally...`);await rest.put(Routes.applicationCommands(clientId),{body:slashCommands});console.log(`✅ Registered ${slashCommands.length} global slash commands.`);}}catch(error){console.error('❌ Slash command registration failed:',error?.message||error);process.exitCode=1;}})();
