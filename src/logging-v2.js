require('dotenv').config();
const fs=require('fs');
const path=require('path');
const {EmbedBuilder,AuditLogEvent,PermissionFlagsBits,ChannelType}=require('discord.js');

const DATA=path.join(process.cwd(),'data');
const FILE=path.join(DATA,'database.json');
const PREFIX=String(process.env.PREFIX||'!').trim()||'!';
const COLOR=0x5865f2;
const db=()=>{try{return JSON.parse(fs.readFileSync(FILE,'utf8')||'{}')}catch{return {}}};
const save=x=>fs.writeFileSync(FILE,JSON.stringify(x,null,2));
const defaults={messageDelete:true,messageEdit:true,messageBulkDelete:true,memberJoin:true,memberLeave:true,memberUpdate:true,ban:true,unban:true,role:true,channel:true,emoji:true,invite:true,voice:true,thread:true,automod:true,webhook:true,guild:true};
function settings(g){g.logs??={};g.logs.channel??=null;g.logs.mod??=null;g.logs.events??={...defaults};for(const k of Object.keys(defaults))if(g.logs.events[k]===undefined)g.logs.events[k]=defaults[k];g.logs.ignoreChannels??=[];g.logs.category??=null;return g.logs;}
const esc=s=>String(s??'').replace(/`/g,'ˋ').slice(0,900);
const tag=u=>u?`${u.tag||u.username||'Unknown'} (${u.id||'?'})`:'Unknown';
const emb=(title,description,icon='📋')=>new EmbedBuilder().setTitle(`${icon} ${title}`).setDescription(description).setColor(COLOR).setTimestamp();
const hasManage=m=>m.member?.permissions?.has(PermissionFlagsBits.ManageGuild)||m.guild.ownerId===m.author.id;
async function audit(guild,type,targetId){try{const x=await guild.fetchAuditLogs({limit:8,type});return x.entries.find(e=>!targetId||e.targetId===targetId)||x.entries.first()||null}catch{return null}}
async function send(client,g,type,title,description,icon='📋',mod=false){const s=settings(g);if(s.events[type]===false)return;const id=mod?s.mod:s.channel;if(!id||s.ignoreChannels.includes(id))return;const ch=client.channels.cache.get(id);if(!ch?.isTextBased?.())return;await ch.send({embeds:[emb(title,description,icon)]}).catch(()=>{})}

async function createLogSetup(guild,client){
  const me=guild.members.me||guild.members.cache.get(client.user.id);
  if(!me)return {ok:false,error:'I could not find my server member.'};
  const needed=PermissionFlagsBits.ManageChannels|PermissionFlagsBits.ViewChannel|PermissionFlagsBits.SendMessages|PermissionFlagsBits.EmbedLinks|PermissionFlagsBits.ReadMessageHistory;
  if((me.permissions.bitfield&needed)!==needed)return {ok:false,error:'I need Manage Channels, View Channel, Send Messages, Embed Links and Read Message History.'};
  const state=db();const g=state[guild.id]||(state[guild.id]={});const s=settings(g);
  let category=s.category?guild.channels.cache.get(s.category):null;
  if(!category)category=guild.channels.cache.find(c=>c.type===ChannelType.GuildCategory&&['logs','📋・logs','📋・logging'].includes(c.name.toLowerCase()));
  const botAllow=[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.EmbedLinks,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.AttachFiles];
  const overwrites=[{id:guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:client.user.id,allow:botAllow}];
  if(!category)category=await guild.channels.create({name:'📋・LOGS',type:ChannelType.GuildCategory,permissionOverwrites:overwrites}).catch(()=>null);
  if(!category)return {ok:false,error:'I could not create the log category. Check my Manage Channels permission.'};
  const make=async(name,oldId)=>{
    let ch=oldId?guild.channels.cache.get(oldId):null;
    if(!ch)ch=guild.channels.cache.find(c=>c.parentId===category.id&&c.type===ChannelType.GuildText&&c.name===name);
    if(!ch)ch=await guild.channels.create({name,type:ChannelType.GuildText,parent:category.id,permissionOverwrites:overwrites,topic:'LightCore automatic server logging — managed by the bot.'}).catch(()=>null);
    else await ch.permissionOverwrites.set(overwrites).catch(()=>{});
    return ch;
  };
  const server=await make('📋・server-logs',s.channel);
  const mod=await make('🛡️・mod-logs',s.mod);
  if(!server&&!mod)return {ok:false,error:'I could not create the log channels.'};
  s.category=category.id;if(server)s.channel=server.id;if(mod)s.mod=mod.id;save(state);
  if(server)await server.send({embeds:[emb('Logging System Enabled','✅ **Automatic logging is now active.**\n\n📥 Members • 🗑️ Messages • ✏️ Edits • 🎭 Roles • 📺 Channels • 🔨 Moderation • 🔊 Voice • 🔗 Invites • 🛡️ Security','🚀')]}).catch(()=>{});
  return {ok:true,category,server,mod};
}

function setup(client){
  client.on('messageCreate',async m=>{
    if(!m.guild||m.author.bot||!m.content?.startsWith(PREFIX))return;
    const p=m.content.slice(PREFIX.length).trim().split(/\s+/);const command=(p.shift()||'').toLowerCase();
    if(!['logsetup','logresetup'].includes(command))return;
    if(!hasManage(m))return m.reply('❌ **Manage Server** permission is required to configure logging.').catch(()=>{});
    const old=m.channel.sendTyping().catch(()=>{});
    await old;
    const result=await createLogSetup(m.guild,client);
    if(!result.ok)return m.reply(`❌ ${result.error}`).catch(()=>{});
    return m.reply({embeds:[emb('Logging Setup Complete',`✅ **Log channels created automatically.**\n\n📋 Server logs: ${result.server||'not created'}\n🛡️ Mod logs: ${result.mod||'not created'}\n📁 Category: ${result.category}\n\n🔒 The category is private by default. @everyone cannot view it, while the bot has the permissions needed to write logs.\n\nUse \`${PREFIX}logsettings\` to view settings and \`${PREFIX}logevents\` to control individual events.`,'🧾')]}).catch(()=>{});
  });
  client.on('messageDelete',async m=>{if(!m.guild||!m.author)return;const g=db()[m.guild.id]||{};await send(client,g,'messageDelete','Message Deleted',`👤 **Author:** ${tag(m.author)}\n📍 **Channel:** ${m.channel}\n📝 **Content:** ${esc(m.content||'*No cached content*')}`,'🗑️')});
  client.on('messageUpdate',async(a,b)=>{if(!b.guild||!b.author||a.content===b.content)return;const g=db()[b.guild.id]||{};await send(client,g,'messageEdit','Message Edited',`👤 **Author:** ${tag(b.author)}\n📍 **Channel:** ${b.channel}\n🔗 [Jump to message](${b.url})\n\n**Before:** ${esc(a.content||'*empty*')}\n**After:** ${esc(b.content||'*empty*')}`,'✏️')});
  client.on('messageDeleteBulk',async(ms,ch)=>{if(!ch?.guild)return;const g=db()[ch.guild.id]||{};await send(client,g,'messageBulkDelete','Bulk Messages Deleted',`📍 **Channel:** ${ch}\n🧹 **Messages removed:** ${ms.size}`,'🧹',true)});
  client.on('guildMemberAdd',async m=>{const g=db()[m.guild.id]||{};await send(client,g,'memberJoin','Member Joined',`👤 ${m}\n🆔 **ID:** \`${m.id}\`\n📅 **Account:** <t:${Math.floor(m.user.createdTimestamp/1000)}:R>\n👥 **Members:** ${m.guild.memberCount}`,'📥')});
  client.on('guildMemberRemove',async m=>{const g=db()[m.guild.id]||{};await send(client,g,'memberLeave','Member Left',`👤 **User:** ${tag(m.user)}\n🆔 **ID:** \`${m.id}\`\n👥 **Members:** ${m.guild.memberCount}`,'📤')});
  client.on('guildMemberUpdate',async(a,b)=>{const changes=[];if(a.nickname!==b.nickname)changes.push(`✏️ Nickname: **${a.nickname||'none'}** → **${b.nickname||'none'}**`);const ar=a.roles.cache.map(x=>x.id),br=b.roles.cache.map(x=>x.id);const add=br.filter(x=>!ar.includes(x)).map(x=>b.guild.roles.cache.get(x)).filter(Boolean);const rem=ar.filter(x=>!br.includes(x)).map(x=>b.guild.roles.cache.get(x)).filter(Boolean);if(add.length)changes.push(`➕ Roles: ${add.join(', ')}`);if(rem.length)changes.push(`➖ Roles: ${rem.join(', ')}`);if(!changes.length)return;const g=db()[b.guild.id]||{};await send(client,g,'memberUpdate','Member Updated',`👤 ${b}\n${changes.join('\n')}`,'👤')});
  client.on('guildBanAdd',async b=>{const g=db()[b.guild.id]||{};const a=await audit(b.guild,AuditLogEvent.MemberBanAdd,b.user.id);await send(client,g,'ban','Member Banned',`👤 **User:** ${tag(b.user)}\n🛡️ **Moderator:** ${tag(a?.executor)}\n📝 **Reason:** ${esc(a?.reason||'No reason provided')}`,'🔨',true)});
  client.on('guildBanRemove',async b=>{const g=db()[b.guild.id]||{};const a=await audit(b.guild,AuditLogEvent.MemberBanRemove,b.user.id);await send(client,g,'unban','Member Unbanned',`👤 **User:** ${tag(b.user)}\n🛡️ **Moderator:** ${tag(a?.executor)}\n📝 **Reason:** ${esc(a?.reason||'No reason provided')}`,'🔓',true)});
  client.on('roleCreate',async r=>{const g=db()[r.guild.id]||{};const a=await audit(r.guild,AuditLogEvent.RoleCreate,r.id);await send(client,g,'role','Role Created',`🎭 **Role:** ${r}\n🎨 **Color:** ${r.hexColor}\n👤 **By:** ${tag(a?.executor)}`,'➕')});
  client.on('roleDelete',async r=>{const g=db()[r.guild.id]||{};const a=await audit(r.guild,AuditLogEvent.RoleDelete,r.id);await send(client,g,'role','Role Deleted',`🎭 **Role:** **${esc(r.name)}**\n🆔 **ID:** \`${r.id}\`\n👤 **By:** ${tag(a?.executor)}`,'➖',true)});
  client.on('channelCreate',async c=>{if(!c.guild)return;const g=db()[c.guild.id]||{};const a=await audit(c.guild,AuditLogEvent.ChannelCreate,c.id);await send(client,g,'channel','Channel Created',`📺 **Channel:** ${c}\n🆔 **ID:** \`${c.id}\`\n👤 **By:** ${tag(a?.executor)}`,'➕')});
  client.on('channelDelete',async c=>{if(!c.guild)return;const g=db()[c.guild.id]||{};const a=await audit(c.guild,AuditLogEvent.ChannelDelete,c.id);await send(client,g,'channel','Channel Deleted',`📺 **Channel:** #${esc(c.name)}\n🆔 **ID:** \`${c.id}\`\n👤 **By:** ${tag(a?.executor)}`,'➖',true)});
  client.on('channelUpdate',async(a,b)=>{if(!b.guild)return;const changes=[];if(a.name!==b.name)changes.push(`🏷️ Name: **${a.name}** → **${b.name}**`);if(a.parentId!==b.parentId)changes.push('📁 Category changed');if(a.topic!==b.topic)changes.push('📝 Topic changed');if(!changes.length)return;const g=db()[b.guild.id]||{};const x=await audit(b.guild,AuditLogEvent.ChannelUpdate,b.id);await send(client,g,'channel','Channel Updated',`📺 ${b}\n${changes.join('\n')}\n👤 **By:** ${tag(x?.executor)}`,'✏️')});
  client.on('voiceStateUpdate',async(a,b)=>{const m=b.member||a.member;if(!m?.guild||a.channelId===b.channelId)return;const g=db()[m.guild.id]||{};await send(client,g,'voice','Voice State Changed',`👤 ${m}\n${a.channelId?`📤 From: <#${a.channelId}>`:'📥 From: none'}\n${b.channelId?`📥 To: <#${b.channelId}>`:'📤 To: none'}`,'🔊')});
  client.on('inviteCreate',async i=>{if(!i.guild)return;const g=db()[i.guild.id]||{};await send(client,g,'invite','Invite Created',`🔗 **Code:** \`${i.code}\`\n📍 **Channel:** ${i.channel||'Unknown'}\n👤 **Creator:** ${tag(i.inviter)}`,'🔗')});
  client.on('inviteDelete',async i=>{if(!i.guild)return;const g=db()[i.guild.id]||{};await send(client,g,'invite','Invite Deleted',`🔗 **Code:** \`${i.code}\`\n📍 **Channel:** ${i.channel||'Unknown'}`,'🗑️')});
  client.on('threadCreate',async t=>{if(!t.guild)return;const g=db()[t.guild.id]||{};await send(client,g,'thread','Thread Created',`🧵 **Thread:** ${t}\n📺 **Parent:** ${t.parent||'Unknown'}`,'🧵')});
  client.on('threadDelete',async t=>{if(!t.guild)return;const g=db()[t.guild.id]||{};await send(client,g,'thread','Thread Deleted',`🧵 **Thread:** **${esc(t.name)}**\n🆔 **ID:** \`${t.id}\``,'🗑️')});
}

module.exports={setup,createLogSetup};
