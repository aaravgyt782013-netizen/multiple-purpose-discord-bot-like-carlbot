const fs=require('fs');
const path=require('path');
const {EmbedBuilder,AuditLogEvent}=require('discord.js');
const FILE=path.join(process.cwd(),'data','database.json');
const COLOR=0x5865f2;
const db=()=>{try{return JSON.parse(fs.readFileSync(FILE,'utf8')||'{}')}catch{return {}}};
const embed=(title,desc,icon)=>new EmbedBuilder().setTitle(`${icon} ${title}`).setDescription(desc).setColor(COLOR).setTimestamp();
const send=async(client,guild,type,title,desc,icon='📋')=>{const state=db();const g=state[guild.id]||{};const logs=g.logs||{};if(logs.events&&logs.events[type]===false)return;const id=logs.channel;if(!id)return;const ch=client.channels.cache.get(id);if(!ch?.isTextBased?.())return;await ch.send({embeds:[embed(title,desc,icon)]}).catch(()=>{});};
function setup(client){
  for(const fn of client.listeners('guildEmojisUpdate'))if(String(fn).includes('Emoji List Updated'))client.removeListener('guildEmojisUpdate',fn);
  client.on('emojiCreate',async e=>{const a=await e.guild.fetchAuditLogs({limit:5,type:AuditLogEvent.EmojiCreate}).then(x=>x.entries.find(v=>v.targetId===e.id)||x.entries.first()).catch(()=>null);await send(client,e.guild,'emoji','Emoji Created',`😀 **Emoji:** ${e}\n🏷️ **Name:** \`${e.name}\`\n👤 **By:** ${a?.executor?`${a.executor.tag} (${a.executor.id})`:'Unknown'}`,'➕');});
  client.on('emojiDelete',async e=>{const a=await e.guild.fetchAuditLogs({limit:5,type:AuditLogEvent.EmojiDelete}).then(x=>x.entries.find(v=>v.targetId===e.id)||x.entries.first()).catch(()=>null);await send(client,e.guild,'emoji','Emoji Deleted',`😀 **Emoji:** **${e.name}**\n🆔 ID: \`${e.id}\`\n👤 **By:** ${a?.executor?`${a.executor.tag} (${a.executor.id})`:'Unknown'}`,'➖');});
  client.on('emojiUpdate',async(oldE,newE)=>{const changes=[];if(oldE.name!==newE.name)changes.push(`🏷️ Name: **${oldE.name}** → **${newE.name}**`);if(oldE.animated!==newE.animated)changes.push('🎞️ Animation state changed');if(!changes.length)return;await send(client,newE.guild,'emoji','Emoji Updated',`😀 ${newE}\n${changes.join('\n')}`,'✏️');});
  client.on('webhooksUpdate',async channel=>{if(!channel.guild)return;await send(client,channel.guild,'webhook','Webhooks Updated',`🔗 **Channel:** ${channel}\n🆔 ID: \`${channel.id}\`\n📌 Webhook configuration changed.`,'🪝');});
}
module.exports={setup};
