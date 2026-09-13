const {EmbedBuilder,PermissionFlagsBits,ChannelType}=require('discord.js');
const fs=require('fs');const path=require('path');
module.exports=function attach(client,prefix='.'){
 const P=prefix||'.';
 const file=path.join(process.cwd(),'data','management-suite.json');fs.mkdirSync(path.dirname(file),{recursive:true});
 let db={};try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{}
 const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const gd=id=>db[id]||(db[id]={reactionRoles:[]});
 const admin=(m,p=PermissionFlagsBits.ManageChannels)=>m.guild.ownerId===m.author.id||m.member.permissions.has(p);
 const E=(title,desc)=>new EmbedBuilder().setTitle(`✨ ${title}`).setDescription(desc).setColor([0x5865f2,0x2563eb,0x7c3aed,0x06b6d4][Math.floor(Math.random()*4)]).setTimestamp();
 const clean=(s)=>String(s||'').replace(/^['"`]|['"`]$/g,'');
 async function handle(m,c,a){
  if(['support','supportserver'].includes(c))return m.reply({embeds:[E('🛠️ SUPPORT SERVER','Need help with **LightCore**?\n\nJoin the support server here:\nhttps://discord.gg/FuVZ9KA3th')]});
  if(['servericon','icon'].includes(c)){
   const icon=m.guild.iconURL({size:1024,dynamic:true});
   return m.reply({embeds:[E('🖼️ SERVER ICON',icon?`**${m.guild.name}**\n[Open server icon](${icon})`:'This server does not have an icon.').setImage(icon||null)]});
  }
  if(['channel','channelcreate','createchannel'].includes(c)){
   if(!admin(m,PermissionFlagsBits.ManageChannels))return m.reply('🚫 **Manage Channels** is required.');
   const sub=(a.shift()||'create').toLowerCase();
   if(!['create','add'].includes(sub))return false;
   let type=(a.shift()||'text').toLowerCase(),types={text:ChannelType.GuildText,voice:ChannelType.GuildVoice,stage:ChannelType.GuildStageVoice,forum:ChannelType.GuildForum,announcement:ChannelType.GuildAnnouncement};
   if(!types[type]){a.unshift(type);type='text';}
   const name=clean(a.shift()||'new-channel').slice(0,100);let parent=m.mentions.channels.first();
   if(parent?.type!==ChannelType.GuildCategory)parent=null;
   const ch=await m.guild.channels.create({name,type:types[type],parent:parent?.id});
   return m.reply({embeds:[E('📁 CHANNEL CREATED',`Created ${ch} as **${type}**${parent?` in ${parent}`:''}.`)]});
  }
  if(['channelduplicate','duplicatechannel'].includes(c)){
   if(!admin(m,PermissionFlagsBits.ManageChannels))return m.reply('🚫 **Manage Channels** is required.');
   const ch=m.mentions.channels.first()||m.channel;const copy=await ch.clone({name:a.filter(x=>!/^<#\d+>$/.test(x)).join(' ')||undefined});return m.reply({embeds:[E('📋 CHANNEL DUPLICATED',`Created ${copy}.`)]});
  }
  if(['role','roles'].includes(c)){
   const sub=(a.shift()||'').toLowerCase();
   if(['give','add'].includes(sub)){
    if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const u=m.mentions.members.first(),r=m.mentions.roles.first();if(!u||!r)return m.reply(`Usage: ${P}role give @user @role`);if(r.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot manage that role.');await u.roles.add(r);return m.reply(`✅ Added ${r} to ${u}.`);
   }
   if(['remove','take'].includes(sub)){
    if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const u=m.mentions.members.first(),r=m.mentions.roles.first();if(!u||!r)return m.reply(`Usage: ${P}role remove @user @role`);if(r.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot manage that role.');await u.roles.remove(r);return m.reply(`✅ Removed ${r} from ${u}.`);
   }
   if(['delete','del','remove-role'].includes(sub)){
    if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const r=m.mentions.roles.first()||m.guild.roles.cache.get(a[0]);if(!r)return m.reply(`Usage: ${P}role delete @role`);if(r.managed||r.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot delete that role.');await r.delete();return m.reply('🗑️ Role deleted.');
   }
   if(['duplicate','copy'].includes(sub)){
    if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const r=m.mentions.roles.first()||m.guild.roles.cache.get(a[0]);if(!r)return m.reply(`Usage: ${P}role duplicate @role`);if(r.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot duplicate a role above my highest role.');const copy=await m.guild.roles.create({name:r.name,permissions:r.permissions,color:r.color,hoist:r.hoist,mentionable:r.mentionable,reason:`Duplicated by ${m.author.tag}`});return m.reply({embeds:[E('🎭 ROLE DUPLICATED',`Created ${copy}.`)]});
   }
   return false;
  }
  if(['deleterole','roledelete'].includes(c)){
   if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const r=m.mentions.roles.first()||m.guild.roles.cache.get(a[0]);if(!r)return m.reply(`Usage: ${P}deleterole @role`);if(r.managed||r.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot delete that role.');await r.delete();return m.reply('🗑️ Role deleted.');
  }
  if(['reactionrole','rr'].includes(c)){
   if(!admin(m,PermissionFlagsBits.ManageRoles))return m.reply('🚫 **Manage Roles** is required.');const sub=(a.shift()||'').toLowerCase(),g=gd(m.guild.id);
   if(['create','add','set'].includes(sub)){
    const ch=m.mentions.channels.first();const msgId=a.shift();const emoji=clean(a.shift());const role=m.mentions.roles.first();if(!ch||!msgId||!emoji||!role)return m.reply(`Usage: ${P}reactionrole create #channel <messageId> <emoji> @role`);
    const msg=await ch.messages.fetch(msgId).catch(()=>null);if(!msg)return m.reply('❌ Message not found.');if(role.position>=m.guild.members.me.roles.highest.position)return m.reply('❌ I cannot manage that role.');await msg.react(emoji).catch(()=>null);g.reactionRoles.push({channelId:ch.id,messageId:msg.id,emoji,roleId:role.id});save();return m.reply({embeds:[E('🎯 REACTION ROLE CREATED',`React with ${emoji} on ${msg.url} to get ${role}.`)]});
   }
   if(['remove','delete'].includes(sub)){const msgId=a.shift(),emoji=clean(a.shift());const before=g.reactionRoles.length;g.reactionRoles=g.reactionRoles.filter(x=>!(x.messageId===msgId&&(!emoji||x.emoji===emoji)));save();return m.reply(before===g.reactionRoles.length?'❌ Reaction role not found.':'🗑️ Reaction role removed.');}
   if(['list','show'].includes(sub)){return m.reply({embeds:[E('🎯 REACTION ROLES',g.reactionRoles.map(x=>`${x.emoji} → <@&${x.roleId}> • \`${x.messageId}\``).join('\n')||'None configured.')]});}
   return m.reply(`Usage: ${P}reactionrole create #channel <messageId> <emoji> @role`);
  }
  if(['category','categorydelete','deletecategory'].includes(c)){
   if(!admin(m,PermissionFlagsBits.ManageChannels))return m.reply('🚫 **Manage Channels** is required.');
   let cat=m.mentions.channels.first();if(!cat&&a[0])cat=m.guild.channels.cache.get(a[0]);if(!cat||cat.type!==ChannelType.GuildCategory)return m.reply(`Usage: ${P}category delete #category`);
   const sub=c==='category'?(a.shift()||'delete').toLowerCase():'delete';if(!['delete','remove'].includes(sub))return false;
   const channels=[...m.guild.channels.cache.filter(x=>x.parentId===cat.id).values()];for(const ch of channels)await ch.delete(`Category deleted by ${m.author.tag}`).catch(()=>{});await cat.delete(`Category and children deleted by ${m.author.tag}`).catch(()=>{});return m.reply({embeds:[E('🗑️ CATEGORY DELETED',`Deleted **${channels.length}** channel(s) and the category.`)]});
  }
  return false;
 }
 const old=client.listeners('messageCreate').at(-1);if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();if(!(await handle(m,c,a)))return old(m)}catch(e){console.error('[MANAGEMENT SUITE]',e);m.reply('❌ Something went wrong while processing that command.').catch(()=>{})}})}
 client.on('messageReactionAdd',async(reaction,user)=>{try{if(user.bot||!reaction.message.guild)return;const g=gd(reaction.message.guild.id),emoji=reaction.emoji.id?`<:${reaction.emoji.name}:${reaction.emoji.id}>`:reaction.emoji.name;const r=g.reactionRoles.find(x=>x.messageId===reaction.message.id&&(x.emoji===emoji||x.emoji===reaction.emoji.name));if(!r)return;const member=await reaction.message.guild.members.fetch(user.id),role=reaction.message.guild.roles.cache.get(r.roleId);if(role&&role.position<reaction.message.guild.members.me.roles.highest.position)await member.roles.add(role).catch(()=>{})}catch(e){console.error('[RR ADD]',e)}});
 client.on('messageReactionRemove',async(reaction,user)=>{try{if(user.bot||!reaction.message.guild)return;const g=gd(reaction.message.guild.id),emoji=reaction.emoji.id?`<:${reaction.emoji.name}:${reaction.emoji.id}>`:reaction.emoji.name;const r=g.reactionRoles.find(x=>x.messageId===reaction.message.id&&(x.emoji===emoji||x.emoji===reaction.emoji.name));if(!r)return;const member=await reaction.message.guild.members.fetch(user.id),role=reaction.message.guild.roles.cache.get(r.roleId);if(role&&role.position<reaction.message.guild.members.me.roles.highest.position)await member.roles.remove(role).catch(()=>{})}catch(e){console.error('[RR REMOVE]',e)}});
};
