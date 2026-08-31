require('dotenv').config();
const { Client, REST, EmbedBuilder } = require('discord.js');
const commands = require('./commands');
const music = require('./modules/music');
process.env.PREFIX='!';

const originalPut=REST.prototype.put;
REST.prototype.put=async function(route,options){
  const r=String(route),isGlobal=/\/applications\/\d+\/commands$/.test(r),testGuild=process.env.DEV_GUILD_ID||process.env.REGISTER_GUILD_ID;
  if(isGlobal&&testGuild){console.log('🧹 Clearing old global slash commands (guild-only mode prevents duplicates)...');return originalPut.call(this,route,{body:[]});}
  return originalPut.call(this,route,options);
};

const clientHelp=()=>{const list=commands.prefixCommands.map(x=>`!${x}`),chunks=[];for(let i=0;i<list.length;i+=45)chunks.push(list.slice(i,i+45).join(' '));const embed=new EmbedBuilder().setTitle('🤖 Aarav All-In-One • Client Commands').setDescription(`**${commands.prefixCommands.length} client commands**\nPrefix: !\n\nUse !help anytime to view them.`).setColor(0x5865f2).setTimestamp().setFooter({text:'Aarav All-In-One'});chunks.forEach((x,i)=>embed.addFields({name:`Commands ${i*45+1}–${Math.min((i+1)*45,list.length)}`,value:x||'None'}));return{embeds:[embed]};};
const originalCommandListEmbed=commands.commandListEmbed;
commands.commandListEmbed=(category='home')=>category==='home'||category==='client'?clientHelp().embeds[0]:originalCommandListEmbed(category);

// Attach the real music handler before index.js creates/logs the Client.
const originalEmit=Client.prototype.emit;let musicBound=false;
Client.prototype.emit=function(event,...args){const result=originalEmit.call(this,event,...args);if(event==='ready'&&!musicBound){musicBound=true;this.on('interactionCreate',async i=>{if(!i.isChatInputCommand()||!['play','pause','resume','skip','stop','queue','nowplaying','volume'].includes(i.commandName)||i.replied||i.deferred)return;try{await music.handle(i,i.commandName);}catch(e){if(!i.replied&&!i.deferred)await i.reply({content:`❌ ${e.message}`,ephemeral:true}).catch(()=>{});}});this.on('messageCreate',async m=>{if(!m.guild||m.author.bot||!m.content.startsWith('!'))return;const parts=m.content.slice(1).trim().split(/\s+/),name=(parts.shift()||'').toLowerCase(),aliases={music:'play',join:'play',leavevc:'stop',pausemusic:'pause',resumemusic:'resume',skipmusic:'skip',stopmusic:'stop',queueview:'queue',np:'nowplaying',vol:'volume',next:'skip',disconnect:'stop'},canonical=aliases[name]||name;if(!['play','pause','resume','skip','stop','queue','nowplaying','volume'].includes(canonical))return;const fake={guild:m.guild,guildId:m.guild.id,channel:m.channel,user:m.author,member:m.member,options:{getString:()=>parts.join(' '),getInteger:()=>Number(parts[0])||null},replied:false,deferred:false,reply:async x=>{fake.replied=true;return m.reply(typeof x==='string'?x:x?.content||'Done.')}};await music.handle(fake,canonical).catch(e=>m.reply(`❌ ${e.message}`).catch(()=>{}));});console.log('🎵 Music system attached: voice playback + YouTube search + queue.');}return result;};

try{require('./index.js');}catch(err){console.error('❌ Bot startup failed:',err);process.exitCode=1;}
