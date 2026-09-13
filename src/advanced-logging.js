require('dotenv').config();
const fs=require('fs');
const path=require('path');
const {EmbedBuilder,AuditLogEvent,PermissionFlagsBits}=require('discord.js');

const DATA=path.join(process.cwd(),'data');
const FILE=path.join(DATA,'database.json');
const PREFIX=String(process.env.PREFIX||'!').trim()||'!';
const COLOR=0x5865f2;
const db=()=>{try{return JSON.parse(fs.readFileSync(FILE,'utf8')||'{}')}catch{return {}}};
const save=x=>fs.writeFileSync(FILE,JSON.stringify(x,null,2));
const settings=g=>{
  g.logs ||= {};
  if(!('channel' in g.logs))g.logs.channel=null;
  if(!('mod' in g.logs))g.logs.mod=null;
  if(!g.logs.events)g.logs.events={messageDelete:true,messageEdit:true,messageBulkDelete:true,memberJoin:true,memberLeave:true,memberUpdate:true,ban:true,unban:true,role:true,channel:true,emoji:true,invite:true,voice:true,thread:true,audit:true,automod:true,webhook:true,guild:true};
  if(!g.logs.ignoreChannels)g.logs.ignoreChannels=[];
  return g.logs;
};
const esc=s=>String(s??'').replace(/`/g,'ˋ').slice(0,900);
const userTag=u=>u?`${u.tag||u.username||'Unknown User'} (${u.id||'?'})`:'Unknown User';
const embed=(title,desc,icon='📋')=>new EmbedBuilder().setTitle(`${icon} ${title}`).setDescription(desc).setColor(COLOR).setTimestamp();
const channelOf=(client,id)=>id?client.channels.cache.get(id):null;
const target=(client,g,kind)=>channelOf(client,kind==='mod'?settings(g).mod:settings(g).channel);
async function send(client,g,type,title,desc,icon='📋',mod=false){const s=settings(g);if(s.events[type]===false)return;const ch=target(client,g,mod?'mod':'server');if(!ch?.isTextBased?.())return;if(s.ignoreChannels.includes(ch.id))return;await ch.send({embeds:[embed(title,desc,icon)]}).catch(()=>{});}
async function audit(guild,event,targetId){try{const logs=await guild.fetchAuditLogs({limit:6,type:event});return logs.entries.find(e=>!targetId||e.targetId===targetId)||logs.entries.first()||null;}catch{return null;}}
function mentionChannel(v){const m=String(v||'').match(/^<#(\d+)>$/);return m?.[1]||String(v||'').match(/\d{15,25}/)?.[0]||null;}
function renderSettings(g){const s=settings(g);return [`**Server logs:** ${s.channel?`<#${s.channel}>`:'OFF'}`,`**Moderation logs:** ${s.mod?`<#${s.mod}>`:'OFF'}`,'',...Object.entries(s.events).map(([k,v])=>`${v?'🟢':'🔴'} \`${k}\``),'',`**Ignored log channels:** ${s.ignoreChannels.length||0}`].join('\n');}

function setup(client){
  const listeners=client.listeners('messageCreate');
  const stable=listeners.find(fn=>String(fn).includes('m.content.startsWith(PREFIX)'));
  if(stable&&!stable.__advancedWrapped){
    client.removeListener('messageCreate',stable);
    const wrapper=async m=>{
      if(!m.guild||m.author.bot||!m.content?.startsWith(PREFIX))return stable(m);
      const parts=m.content.slice(PREFIX.length).trim().split(/\s+/);const command=(parts.shift()||'').toLowerCase();const args=parts;
      const state=db();const g=state[m.guild.id]||(state[m.guild.id]={});const s=settings(g);const reply=p=>m.reply(p).catch(()=>{});const mention=mentionChannel(args[0]);
      try{
        if(command==='loghelp'||(command==='help'&&args[0]?.toLowerCase()==='logging'))return reply({embeds:[embed('Logging Command Center',[
          `**${PREFIX}logsetup #channel** — set the main server log channel`,`**${PREFIX}logmod #channel** — set moderation/security logs`,`**${PREFIX}logsettings** — view every logging switch`,`**${PREFIX}logevents** — show enabled event types`,`**${PREFIX}logevents <event> on|off** — toggle one event`,`**${PREFIX}logignore #channel** — ignore a channel from logging`,`**${PREFIX}logunignore #channel** — remove an ignored channel`,`**${PREFIX}logtest** — send a test embed`,`**${PREFIX}logreset** — reset logging switches`,'','**Events:** messages • edits • bulk deletes • joins • leaves • member updates • bans • unbans • roles • channels • emojis • invites • voice • threads • automod • webhooks • server changes • audit actions'
        ].join('\n'),'🧾')]});
        if(['logsetup','setlogs2','logchannel'].includes(command)){if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return reply('❌ Manage Server permission required.');if(!mention)return reply(`Usage: ${PREFIX}logsetup #channel`);s.channel=mention;save(state);return reply(`✅ Server logging channel set to <#${mention}>.\n📋 Live event logging is now ready.`);}
        if(['logmod','modlogs'].includes(command)){if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return reply('❌ Manage Server permission required.');if(!mention)return reply(`Usage: ${PREFIX}logmod #channel`);s.mod=mention;save(state);return reply(`🛡️ Moderation/security logs set to <#${mention}>.`);}
        if(command==='logsettings')return reply({embeds:[embed('Logging Settings',renderSettings(g),'⚙️')]});
        if(command==='logevents'){if(!args.length)return reply({embeds:[embed('Logging Events',Object.entries(s.events).map(([k,v])=>`${v?'🟢 ENABLED':'🔴 DISABLED'} • \`${k}\``).join('\n'),'🧩')]});if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return reply('❌ Manage Server permission required.');const key=args[0].toLowerCase();if(!(key in s.events))return reply(`❌ Unknown event. Use ${PREFIX}logevents to see valid events.`);const value=['on','enable','enabled','true','yes'].includes((args[1]||'').toLowerCase());s.events[key]=value;save(state);return reply(`${value?'🟢':'🔴'} \`${key}\` logging is now **${value?'ON':'OFF'}**.`);}
        if(command==='logignore'||command==='logunignore'){if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return reply('❌ Manage Server permission required.');if(!mention)return reply(`Usage: ${PREFIX}${command} #channel`);if(command==='logignore'){if(!s.ignoreChannels.includes(mention))s.ignoreChannels.push(mention);}else s.ignoreChannels=s.ignoreChannels.filter(x=>x!==mention);save(state);return reply(`${command==='logignore'?'🚫 Ignoring':'✅ Logging restored for'} <#${mention}>.`);}
        if(command==='logtest'){if(!s.channel&&!s.mod)return reply(`❌ No log channel is configured. Use ${PREFIX}logsetup #channel first.`);if(s.channel){const ch=channelOf(client,s.channel);if(ch)await ch.send({embeds:[embed('Logging Test','✅ **LightCore logging is online.**\nThis is a test event; no moderation action was performed.','🧪')]}).catch(()=>{});}return reply('🧪 Test log sent.');}
        if(command==='logreset'){if(!m.member.permissions.has(PermissionFlagsBits.ManageGuild)&&m.guild.ownerId!==m.author.id)return reply('❌ Manage Server permission required.');s.events=Object.fromEntries(Object.keys(s.events).map(k=>[k,true]));s.ignoreChannels=[];save(state);return reply('♻️ Logging switches reset to default: all events enabled.');}
        return stable(m);
      }catch(e){console.error('[ADV LOG COMMAND]',e);return reply('❌ Logging command failed. Check Render logs.');}
    };
    wrapper.__advancedWrapped=true;client.on('messageCreate',wrapper);
  }

  client.on('messageDelete',async m=>{if(!m.guild||!m.author)return;const g=db()[m.guild.id]||{};await send(client,g,'messageDelete','Message Deleted',`👤 **Author:** ${userTag(m.author)}\n📍 **Channel:** ${m.channel}\n📝 **Content:** ${esc(m.content||'*No cached content*')}`,'🗑️');});
  client.on('messageUpdate',async(oldM,newM)=>{if(!newM.guild||!newM.author||oldM.content===newM.content)return;const g=db()[newM.guild.id]||{};await send(client,g,'messageEdit','Message Edited',`👤 **Author:** ${userTag(newM.author)}\n📍 **Channel:** ${newM.channel}\n🔗 [Jump to message](${newM.url})\n**Before:** ${esc(oldM.content||'*empty*')}\n**After:** ${esc(newM.content||'*empty*')}`,'✏️');});
  client.on('messageDeleteBulk',async(ms,ch)=>{if(!ch?.guild)return;const g=db()[ch.guild.id]||{};await send(client,g,'messageBulkDelete','Bulk Message Delete',`📍 **Channel:** ${ch}\n🧹 **Messages removed:** ${ms.size}`,'🧹',true);});
  client.on('guildMemberAdd',async m=>{const g=db()[m.guild.id]||{};await send(client,g,'memberJoin','Member Joined',`👤 ${m} • **${userTag(m.user)}**\n📅 Account: <t:${Math.floor(m.user.createdTimestamp/1000)}:R>\n👥 Members: **${m.guild.memberCount}**`,'📥');});
  client.on('guildMemberRemove',async m=>{const g=db()[m.guild.id]||{};await send(client,g,'memberLeave','Member Left',`👤 **${userTag(m.user)}**\n🆔 ID: \`${m.id}\`\n👥 Members: **${m.guild.memberCount}**`,'📤');});
  client.on('guildMemberUpdate',async(oldM,newM)=>{const g=db()[newM.guild.id]||{};const changes=[];if(oldM.nickname!==newM.nickname)changes.push(`✏️ Nickname: **${oldM.nickname||'none'}** → **${newM.nickname||'none'}**`);const a=oldM.roles.cache.map(r=>r.id),b=newM.roles.cache.map(r=>r.id);const added=b.filter(x=>!a.includes(x)).map(x=>newM.guild.roles.cache.get(x)).filter(Boolean);const removed=a.filter(x=>!b.includes(x)).map(x=>newM.guild.roles.cache.get(x)).filter(Boolean);if(added.length)changes.push(`➕ Roles: ${added.map(r=>r).join(', ')}`);if(removed.length)changes.push(`➖ Roles: ${removed.map(r=>r).join(', ')}`);if(!changes.length)return;await send(client,g,'memberUpdate','Member Updated',`👤 ${newM}\n${changes.join('\n')}`,'👤');});
  client.on('guildBanAdd',async b=>{const g=db()[b.guild.id]||{};const a=await audit(b.guild,AuditLogEvent.MemberBanAdd,b.user.id);await send(client,g,'ban','Member Banned',`👤 **User:** ${userTag(b.user)}\n🛡️ **Moderator:** ${userTag(a?.executor)}\n📝 **Reason:** ${a?.reason||'No reason provided'}`,'🔨',true);});
  client.on('guildBanRemove',async b=>{const g=db()[b.guild.id]||{};const a=await audit(b.guild,AuditLogEvent.MemberBanRemove,b.user.id);await send(client,g,'unban','Member Unbanned',`👤 **User:** ${userTag(b.user)}\n🛡️ **Moderator:** ${userTag(a?.executor)}\n📝 **Reason:** ${a?.reason||'No reason provided'}`,'🔓',true);});
  client.on('roleCreate',async r=>{const g=db()[r.guild.id]||{};const a=await audit(r.guild,AuditLogEvent.RoleCreate,r.id);await send(client,g,'role','Role Created',`🎭 **Role:** ${r}\n🎨 **Color:** ${r.hexColor}\n👤 **By:** ${userTag(a?.executor)}`,'➕');});
  client.on('roleDelete',async r=>{const g=db()[r.guild.id]||{};const a=await audit(r.guild,AuditLogEvent.RoleDelete,r.id);await send(client,g,'role','Role Deleted',`🎭 **Role:** **${esc(r.name)}**\n🆔 ID: \`${r.id}\`\n👤 **By:** ${userTag(a?.executor)}`,'➖',true);});
  client.on('roleUpdate',async(oldR,newR)=>{const g=db()[newR.guild.id]||{};const changes=[];if(oldR.name!==newR.name)changes.push(`🏷️ Name: **${oldR.name}** → **${newR.name}**`);if(oldR.hexColor!==newR.hexColor)changes.push(`🎨 Color: **${oldR.hexColor}** → **${newR.hexColor}**`);if(oldR.permissions.bitfield!==newR.permissions.bitfield)changes.push('🔐 Permissions changed');if(!changes.length)return;const a=await audit(newR.guild,AuditLogEvent.RoleUpdate,newR.id);await send(client,g,'role','Role Updated',`🎭 ${newR}\n${changes.join('\n')}\n👤 **By:** ${userTag(a?.executor)}`,'✏️');});
  client.on('channelCreate',async c=>{if(!c.guild)return;const g=db()[c.guild.id]||{};const a=await audit(c.guild,AuditLogEvent.ChannelCreate,c.id);await send(client,g,'channel','Channel Created',`📺 **Channel:** ${c}\n🆔 ID: \`${c.id}\`\n👤 **By:** ${userTag(a?.executor)}`,'➕');});
  client.on('channelDelete',async c=>{if(!c.guild)return;const g=db()[c.guild.id]||{};const a=await audit(c.guild,AuditLogEvent.ChannelDelete,c.id);await send(client,g,'channel','Channel Deleted',`📺 **Channel:** #${esc(c.name)}\n🆔 ID: \`${c.id}\`\n👤 **By:** ${userTag(a?.executor)}`,'➖',true);});
  client.on('channelUpdate',async(oldC,newC)=>{if(!newC.guild)return;const changes=[];if(oldC.name!==newC.name)changes.push(`🏷️ Name: **${oldC.name}** → **${newC.name}**`);if(oldC.parentId!==newC.parentId)changes.push('📁 Category changed');if(oldC.topic!==newC.topic)changes.push('📝 Topic changed');if(!changes.length)return;const g=db()[newC.guild.id]||{};const a=await audit(newC.guild,AuditLogEvent.ChannelUpdate,newC.id);await send(client,g,'channel','Channel Updated',`📺 ${newC}\n${changes.join('\n')}\n👤 **By:** ${userTag(a?.executor)}`,'✏️');});
  client.on('guildEmojisUpdate',async guild=>{const g=db()[guild.id]||{};await send(client,g,'emoji','Emoji List Updated',`😀 The server emoji list changed.\n📊 Current emojis: **${guild.emojis.cache.size}**`,'😀');});
  client.on('inviteCreate',async invite=>{if(!invite.guild)return;const g=db()[invite.guild.id]||{};await send(client,g,'invite','Invite Created',`🔗 **Code:** \`${invite.code}\`\n📍 **Channel:** ${invite.channel||'Unknown'}\n👤 **Creator:** ${userTag(invite.inviter)}`,'🔗');});
  client.on('inviteDelete',async invite=>{if(!invite.guild)return;const g=db()[invite.guild.id]||{};await send(client,g,'invite','Invite Deleted',`🔗 **Code:** \`${invite.code}\`\n📍 **Channel:** ${invite.channel||'Unknown'}`,'🗑️');});
  client.on('voiceStateUpdate',async(oldS,newS)=>{const m=newS.member||oldS.member;if(!m?.guild||oldS.channelId===newS.channelId)return;const g=db()[m.guild.id]||{};await send(client,g,'voice','Voice State Changed',`👤 ${m}\n${oldS.channelId?`📤 From: <#${oldS.channelId}>`:'📤 From: **not connected**'}\n${newS.channelId?`📥 To: <#${newS.channelId}>`:'📥 To: **not connected**'}`,'🔊');});
  client.on('threadCreate',async t=>{const g=db()[t.guild.id]||{};await send(client,g,'thread','Thread Created',`🧵 ${t}\n📍 Parent: ${t.parent||'Unknown'}`,'🧵');});
  client.on('threadDelete',async t=>{const g=db()[t.guild.id]||{};await send(client,g,'thread','Thread Deleted',`🧵 **${esc(t.name)}**\n🆔 ID: \`${t.id}\``,'🗑️');});
  client.on('autoModerationActionExecution',async e=>{const g=db()[e.guild.id]||{};await send(client,g,'automod','AutoMod Action',`🛡️ **Rule:** ${esc(e.ruleId||'Unknown')}\n👤 **User:** <@${e.userId}>\n📍 **Channel:** ${e.channelId?`<#${e.channelId}>`:'Unknown'}\n⚡ **Action:** \`${e.action?.type||'unknown'}\``,'🛡️',true);});
  client.on('guildUpdate',async(oldG,newG)=>{const changes=[];if(oldG.name!==newG.name)changes.push(`🏷️ Name: **${oldG.name}** → **${newG.name}**`);if(oldG.icon!==newG.icon)changes.push('🖼️ Server icon changed');if(oldG.banner!==newG.banner)changes.push('🎨 Banner changed');if(!changes.length)return;const g=db()[newG.id]||{};await send(client,g,'guild','Server Updated',changes.join('\n'),'🏠');});
  client.on('guildAuditLogEntryCreate',async(entry,guild)=>{const g=db()[guild.id]||{};if(!settings(g).events.audit)return;const ignored=[AuditLogEvent.MemberBanAdd,AuditLogEvent.MemberBanRemove,AuditLogEvent.RoleCreate,AuditLogEvent.RoleDelete,AuditLogEvent.RoleUpdate,AuditLogEvent.ChannelCreate,AuditLogEvent.ChannelDelete,AuditLogEvent.ChannelUpdate];if(ignored.includes(entry.action))return;await send(client,g,'audit','Audit Log Action',`⚡ **Action:** \`${entry.action}\`\n🎯 **Target:** \`${entry.targetId||'Unknown'}\`\n👤 **Executor:** ${userTag(entry.executor)}\n📝 **Reason:** ${entry.reason||'No reason provided'}`,'📚',true);});
}
module.exports={setup};
