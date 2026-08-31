require('dotenv').config();
const fs=require('fs'),path=require('path');
const Database=require('better-sqlite3');
const {Client,REST,EmbedBuilder,PermissionFlagsBits}=require('discord.js');
const commands=require('./commands');
const music=require('./modules/music');
const tickets=require('./modules/tickets');
const applications=require('./modules/applications');
const setup=require('./modules/setupWizards');
process.env.PREFIX='!';

// Discord allows one command with a given name per application/scope. When a
// test guild is configured, use guild-only registration and actively clear the
// global scope so old global copies cannot appear alongside the guild copy.
const setupCommands=[
  {name:'ticketsetup',description:'Interactive ticket system setup wizard',default_member_permissions:String(PermissionFlagsBits.ManageGuild)},
  {name:'applicationsetup',description:'Interactive application system setup wizard',default_member_permissions:String(PermissionFlagsBits.ManageGuild)}
];
const seenBody=body=>{const seen=new Set();return (Array.isArray(body)?body:[]).filter(c=>{if(!c?.name||seen.has(c.name))return false;seen.add(c.name);return true;});};
const originalPut=REST.prototype.put;
REST.prototype.put=async function(route,options){
  const r=String(route),isGlobal=/\/applications\/\d+\/commands$/.test(r),isGuild=/\/applications\/\d+\/guilds\/\d+\/commands$/.test(r),testGuild=process.env.DEV_GUILD_ID||process.env.REGISTER_GUILD_ID;
  if(isGlobal&&testGuild){console.log('🧹 Clearing global slash commands (guild-only test mode prevents duplicates)...');return originalPut.call(this,route,{body:[]});}
  if((isGlobal||isGuild)&&options?.body){
    const body=seenBody(options.body);
    for(const extra of setupCommands)if(!body.some(c=>c.name===extra.name))body.push(extra);
    console.log(`🔄 Command sync payload: ${body.length} unique slash commands.`);
    return originalPut.call(this,route,{...options,body});
  }
  return originalPut.call(this,route,options);
};

const dbFile=process.env.DB_FILE||'./data/bot.sqlite';
fs.mkdirSync(path.dirname(path.resolve(dbFile)),{recursive:true});
const setupDb=new Database(dbFile);setupDb.pragma('journal_mode = WAL');
tickets.init(setupDb);applications.init(setupDb);
const setupCtx={db:setupDb,tickets,applications};

const clientHelp=()=>{const list=commands.prefixCommands.map(x=>`!${x}`),chunks=[];for(let i=0;i<list.length;i+=45)chunks.push(list.slice(i,i+45).join(' '));const embed=new EmbedBuilder().setTitle('🤖 Aarav All-In-One • Client Commands').setDescription(`**${commands.prefixCommands.length} client commands**\nPrefix: !\n\nUse !help anytime to view them.`).setColor(0x5865f2).setTimestamp().setFooter({text:'Aarav All-In-One'});chunks.forEach((x,i)=>embed.addFields({name:`Commands ${i*45+1}–${Math.min((i+1)*45,list.length)}`,value:x||'None'}));return{embeds:[embed]};};
const originalCommandListEmbed=commands.commandListEmbed;
commands.commandListEmbed=(category='home')=>category==='home'||category==='client'?clientHelp().embeds[0]:originalCommandListEmbed(category);

// Intercept only our setup interactions before the normal command dispatcher.
// Everything else is passed through untouched.
const originalEmit=Client.prototype.emit;let musicBound=false;
Client.prototype.emit=function(event,...args){
  if(event==='interactionCreate'){
    const i=args[0];
    const isSetup=(i?.isChatInputCommand?.()&&['ticketsetup','applicationsetup'].includes(i.commandName))||String(i?.customId||'').startsWith('setup:');
    if(isSetup){setup.handle(i,setupCtx).catch(e=>{console.error('❌ Setup interaction:',e);if(i?.isRepliable?.()&&!i.replied&&!i.deferred)i.reply({content:`❌ ${e.message}`,ephemeral:true}).catch(()=>{});});return true;}
  }
  const result=originalEmit.call(this,event,...args);
  if(event==='ready'&&!musicBound){
    musicBound=true;
    this.on('interactionCreate',async i=>{if(!i.isChatInputCommand()||!['play','pause','resume','skip','stop','queue','nowplaying','volume'].includes(i.commandName)||i.replied||i.deferred)return;try{await music.handle(i,i.commandName);}catch(e){if(!i.replied&&!i.deferred)await i.reply({content:`❌ ${e.message}`,ephemeral:true}).catch(()=>{});}});
    this.on('messageCreate',async m=>{if(!m.guild||m.author.bot||!m.content.startsWith('!'))return;const parts=m.content.slice(1).trim().split(/\s+/),name=(parts.shift()||'').toLowerCase(),aliases={music:'play',join:'play',leavevc:'stop',pausemusic:'pause',resumemusic:'resume',skipmusic:'skip',stopmusic:'stop',queueview:'queue',np:'nowplaying',vol:'volume',next:'skip',disconnect:'stop'},canonical=aliases[name]||name;if(!['play','pause','resume','skip','stop','queue','nowplaying','volume'].includes(canonical))return;const fake={guild:m.guild,guildId:m.guild.id,channel:m.channel,user:m.author,member:m.member,options:{getString:()=>parts.join(' '),getInteger:()=>Number(parts[0])||null},replied:false,deferred:false,reply:async x=>{fake.replied=true;return m.reply(typeof x==='string'?x:x?.content||'Done.')}};await music.handle(fake,canonical).catch(e=>m.reply(`❌ ${e.message}`).catch(()=>{}));});
    console.log('🎵 Music system attached: voice playback + queue.');
  }
  return result;
};

try{require('./index.js');}catch(err){console.error('❌ Bot startup failed:',err);process.exitCode=1;}
