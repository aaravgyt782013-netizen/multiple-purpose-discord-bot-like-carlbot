const fs=require('fs'),path=require('path');
const {ChannelType,PermissionFlagsBits,EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle,StringSelectMenuBuilder}=require('discord.js');

module.exports=function attachTicketSuite(client,prefix='.'){
 const P=prefix||'.';
 const file=path.join(process.cwd(),'data','ticket-suite-v2.json');
 fs.mkdirSync(path.dirname(file),{recursive:true});
 let db={};try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{db={};}
 const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const fresh=()=>({
  categories:[{id:'support',name:'Support',emoji:'🎫',description:'General support',category:null,role:null,logChannel:null,transcriptChannel:null}],
  panel:{title:'🎫 Support Center',description:'Select a ticket category below to open a private ticket.',color:0x5865f2,buttonLabel:'Open Ticket',buttonEmoji:'🎫'},
  applications:{enabled:false,channel:null,title:'📝 Staff Application',description:'Apply by selecting an application type below.',color:0x5865f2,buttonLabel:'Apply Now',buttonEmoji:'📝',questions:['What are you applying for?','Why should we choose you?','What experience do you have?']},
  counter:0
 });
 const gd=id=>{const d=db[id]||(db[id]=fresh()),f=fresh();for(const k of Object.keys(f))if(d[k]===undefined)d[k]=f[k];d.categories=(d.categories||[]).map(c=>({...fresh().categories[0],...c,logChannel:c.logChannel||null,transcriptChannel:c.transcriptChannel||null}));return d};
 const clean=(s,n=100)=>String(s||'').replace(/[<>]/g,'').slice(0,n);
 const canConfig=m=>!!m.member&&(m.guild.ownerId===m.author.id||m.member.permissions.has(PermissionFlagsBits.ManageGuild));
 const isStaff=(m,c)=>!!m.member&&(m.guild.ownerId===m.author.id||m.member.permissions.has(PermissionFlagsBits.ManageChannels)||m.member.permissions.has(PermissionFlagsBits.ManageGuild)||(c?.role&&m.member.roles.cache.has(c.role)));
 const ticketCategory=(m)=>{const p=m.channel?.parentId;return gd(m.guild.id).categories.find(c=>c.category===p)||null};
 const panel=d=>({embeds:[new EmbedBuilder().setTitle(d.panel.title).setDescription(d.panel.description).setColor(d.panel.color).setFooter({text:'LightCore • Ticket System'}).setTimestamp()],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('lc_ticket_category').setPlaceholder('🎫 Select a ticket category').addOptions(d.categories.slice(0,25).map(x=>({label:clean(x.name,100),value:x.id,description:clean(x.description,100),emoji:x.emoji||'🎫'}))))]});
 const appPanel=d=>({embeds:[new EmbedBuilder().setTitle(d.applications.title).setDescription(d.applications.description).setColor(d.applications.color).setFooter({text:'LightCore • Applications'}).setTimestamp()],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_apply_open').setLabel(d.applications.buttonLabel||'Apply Now').setEmoji(d.applications.buttonEmoji||'📝').setStyle(ButtonStyle.Primary))]});
 async function setup(m){
  if(!canConfig(m))return m.reply('❌ You need **Manage Server** to configure tickets.');
  const d=gd(m.guild.id);
  for(const c of d.categories){
   let cat=c.category&&m.guild.channels.cache.get(c.category);if(!cat||cat.type!==ChannelType.GuildCategory)cat=await m.guild.channels.create({name:`🎫・${clean(c.name,90)}`,type:ChannelType.GuildCategory,reason:'LightCore ticket category'});c.category=cat.id;
   let role=c.role&&m.guild.roles.cache.get(c.role);if(!role)role=m.guild.roles.cache.find(r=>r.name.toLowerCase()===`${c.name.toLowerCase()} staff`);if(!role)role=await m.guild.roles.create({name:`${clean(c.name,90)} Staff`,reason:'LightCore ticket staff role'});c.role=role.id;
   const staffOverwrites=[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:role.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.ManageMessages]}];
   let log=c.logChannel&&m.guild.channels.cache.get(c.logChannel);if(!log||log.type!==ChannelType.GuildText){log=await m.guild.channels.create({name:`${c.id}-logs`.slice(0,100),type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:staffOverwrites,reason:'LightCore ticket logs'});}
   c.logChannel=log.id;
   let tr=c.transcriptChannel&&m.guild.channels.cache.get(c.transcriptChannel);if(!tr||tr.type!==ChannelType.GuildText){tr=await m.guild.channels.create({name:`${c.id}-transcripts`.slice(0,100),type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:staffOverwrites,reason:'LightCore ticket transcripts'});}
   c.transcriptChannel=tr.id;
  }
  save();return m.reply('✅ Ticket system configured. Every category now has its own **staff role, logs channel and transcript channel**.');
 }
 async function log(d,c,guild,embed){const ch=c?.logChannel&&guild.channels.cache.get(c.logChannel);if(ch?.isTextBased())await ch.send({embeds:[embed.setFooter({text:`LightCore • ${c.name} logs`})]}).catch(()=>{});}
 async function transcript(d,c,ch,guild,closedBy){
  const out=c?.transcriptChannel&&guild.channels.cache.get(c.transcriptChannel);if(!out?.isTextBased())return;
  let before;const all=[];
  try{for(let i=0;i<10;i++){const batch=await ch.messages.fetch({limit:100,before});if(!batch.size)break;all.push(...batch.values());if(batch.size<100)break;before=batch.last().id;}}catch(e){console.error('[TICKET TRANSCRIPT FETCH]',e);}
  all.sort((a,b)=>a.createdTimestamp-b.createdTimestamp);
  const lines=[`LightCore Ticket Transcript`,`Server: ${guild.name} (${guild.id})`,`Channel: #${ch.name} (${ch.id})`,`Category: ${c.name}`,`Closed by: ${closedBy.tag||closedBy.username||closedBy.id}`,`Created: ${new Date(ch.createdTimestamp).toISOString()}`,`Closed: ${new Date().toISOString()}`,'','--- MESSAGES ---',...all.map(x=>`[${new Date(x.createdTimestamp).toISOString()}] ${x.author?.tag||x.author?.username||x.author?.id}: ${String(x.content||'[embed/attachment]').replace(/\n/g,' ')}${x.attachments?.size?` [attachments: ${[...x.attachments.values()].map(a=>a.url).join(', ')}]`:''}`)];
  const buf=Buffer.from(lines.join('\n'),'utf8');await out.send({content:`📄 Transcript for **#${ch.name}** • closed by <@${closedBy.id}>`,files:[{attachment:buf,name:`${clean(ch.name,60)}-transcript.txt`}]}).catch(e=>console.error('[TICKET TRANSCRIPT SEND]',e));
 }
 async function closeTicket(m){
  const d=gd(m.guild.id),c=ticketCategory(m);if(!c)return m.reply('❌ This channel is not a LightCore ticket.');if(!isStaff(m,c))return m.reply('❌ You need the category staff role or **Manage Channels**.');
  const ownerId=(m.channel.topic||'').replace(/^ticket:/,'');const e=new EmbedBuilder().setTitle('🔒 Ticket Closed').setDescription(`**Ticket:** #${m.channel.name}\n**Category:** ${c.name}\n**Closed by:** ${m.author}\n**Owner:** ${ownerId?`<@${ownerId}>`:'Unknown'}`).setColor(0xed4245).setTimestamp();
  await log(d,c,m.guild,e);await transcript(d,c,m.channel,m.guild,m.author);
  await m.channel.permissionOverwrites.edit(m.guild.roles.everyone,{ViewChannel:false,SendMessages:false}).catch(()=>{});
  if(ownerId)await m.channel.permissionOverwrites.edit(ownerId,{ViewChannel:false,SendMessages:false}).catch(()=>{});
  return m.reply('🔒 Ticket closed. A transcript was sent to the category transcript channel.');
 }
 async function open(m,id){
  const d=gd(m.guild.id),c=d.categories.find(x=>x.id===id)||d.categories[0];if(!c.category)return m.reply(`❌ Run ${P}ticket setup first.`);
  const existing=m.guild.channels.cache.find(x=>x.type===ChannelType.GuildText&&x.parentId===c.category&&x.topic===`ticket:${m.author.id}`);if(existing)return m.reply(`⚠️ You already have a ticket in this category: ${existing}`);
  d.counter++;const ch=await m.guild.channels.create({name:`${c.id}-${String(d.counter).padStart(4,'0')}`.slice(0,100),type:ChannelType.GuildText,parent:c.category,topic:`ticket:${m.author.id}`,permissionOverwrites:[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.AttachFiles]},{id:c.role,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.ManageMessages,PermissionFlagsBits.ManageChannels]}]});
  const row=new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_ticket_close').setLabel('Close').setEmoji('🔒').setStyle(ButtonStyle.Danger),new ButtonBuilder().setCustomId('lc_ticket_claim').setLabel('Claim').setEmoji('🙋').setStyle(ButtonStyle.Primary),new ButtonBuilder().setCustomId('lc_ticket_add').setLabel('Add Member').setEmoji('➕').setStyle(ButtonStyle.Secondary));
  await ch.send({content:`Welcome <@${m.author.id}> • **${c.name}**`,embeds:[new EmbedBuilder().setTitle(`🎫 ${c.name} Ticket`).setDescription('Please describe your issue clearly. Staff will assist you.\n\n🔒 **Staff controls:** close • claim • add member')],components:[row]});
  await log(d,c,m.guild,new EmbedBuilder().setTitle('🎫 Ticket Opened').setDescription(`**Category:** ${c.name}\n**Ticket:** ${ch}\n**Opened by:** ${m.author}`).setColor(0x57f287).setTimestamp());save();return m.reply(`✅ Ticket created: ${ch}`);
 }
 async function manage(m,c,a){
  const d=gd(m.guild.id);
  if(c==='setup')return setup(m);if(c==='panel'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');return m.channel.send(panel(d));}
  if(c==='open'||c==='create')return open(m,a[0]||d.categories[0].id);
  if(c==='categories'||c==='category')return m.reply({embeds:[new EmbedBuilder().setTitle('🎫 Ticket Categories').setDescription(d.categories.map(x=>`${x.emoji} **${x.name}** — \`${x.id}\`\n${x.description}\nStaff: <@&${x.role}> • Logs: ${x.logChannel?`<#${x.logChannel}>`:'not set'} • Transcripts: ${x.transcriptChannel?`<#${x.transcriptChannel}>`:'not set'}`).join('\n\n'))]});
  if(c==='addcategory'){
   if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const id=(a.shift()||'').toLowerCase().replace(/[^a-z0-9-]/g,'').slice(0,30),name=(a.shift()||'Support').slice(0,80),description=a.join(' ')||'Ticket category';if(!id)return m.reply(`Usage: ${P}ticket addcategory <id> <name> <description>`);if(d.categories.some(x=>x.id===id))return m.reply('❌ That category already exists.');d.categories.push({id,name,emoji:'🎫',description,category:null,role:null,logChannel:null,transcriptChannel:null});save();return setup(m);
  }
  if(c==='editcategory'){
   if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const id=a.shift();const x=d.categories.find(z=>z.id===id);if(!x)return m.reply('❌ Unknown category.');if(a[0])x.name=a.shift().replace(/_/g,' ').slice(0,80);if(a.length)x.description=a.join(' ').replace(/_/g,' ').slice(0,100);save();return setup(m);
  }
  if(c==='delcategory'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const id=a[0];if(d.categories.length<=1)return m.reply('❌ Keep at least one category.');d.categories=d.categories.filter(x=>x.id!==id);save();return m.reply('✅ Ticket category deleted.');}
  if(c==='editpanel'){
   if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const mode=(a.shift()||'').toLowerCase();if(mode==='title')d.panel.title=a.join(' ').replace(/_/g,' ').slice(0,256);else if(mode==='description')d.panel.description=a.join(' ').replace(/_/g,' ').slice(0,4000);else if(mode==='color'){const v=parseInt((a[0]||'').replace(/^#/,'')||'0',16);if(!Number.isInteger(v)||v<0||v>0xffffff)return m.reply(`Usage: ${P}ticket editpanel color <hex>`);d.panel.color=v;}else if(mode==='button'){d.panel.buttonLabel=(a.shift()||'Open Ticket').slice(0,80);d.panel.buttonEmoji=a.shift()||'🎫';}else return m.reply(`Usage: ${P}ticket editpanel title|description|color|button ...`);save();return m.reply('✅ Ticket panel updated. Use `.ticket panel` to publish it.');
  }
  if(c==='close')return closeTicket(m);
  const tc=ticketCategory(m);if(c==='claim'||c==='unclaim'||c==='rename'||c==='add'||c==='remove')if(!tc||!isStaff(m,tc))return m.reply('❌ This ticket action requires the category staff role or **Manage Channels**.');
  if(c==='claim'){await log(d,tc,m.guild,new EmbedBuilder().setTitle('🙋 Ticket Claimed').setDescription(`${m.author} claimed #${m.channel.name}`).setColor(0x5865f2).setTimestamp());return m.reply(`🙋 Ticket claimed by ${m.author}.`);}
  if(c==='unclaim')return m.reply('↩️ Ticket unclaimed.');
  if(c==='rename'){const n=a.join('-').toLowerCase().replace(/[^a-z0-9-]/g,'').slice(0,90);if(!n)return m.reply(`Usage: ${P}ticket rename <name>`);await m.channel.setName(n);return m.reply('✏️ Ticket renamed.');}
  if(c==='add'){const u=m.mentions.members.first();if(!u)return m.reply(`Usage: ${P}ticket add @user`);await m.channel.permissionOverwrites.edit(u.id,{ViewChannel:true,SendMessages:true,ReadMessageHistory:true});return m.reply(`➕ Added ${u}.`);}
  if(c==='remove'){const u=m.mentions.members.first();if(!u)return m.reply(`Usage: ${P}ticket remove @user`);await m.channel.permissionOverwrites.delete(u.id).catch(()=>{});return m.reply(`➖ Removed ${u}.`);}
  if(c==='logs'||c==='transcripts'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const id=a[0],x=d.categories.find(z=>z.id===id);if(!x)return m.reply('❌ Unknown category.');return m.reply(`${x.name}: Logs ${x.logChannel?`<#${x.logChannel}>`:'not set'} • Transcripts ${x.transcriptChannel?`<#${x.transcriptChannel}>`:'not set'}`);}
  return m.reply(`🎫 **Ticket v2**\n${P}ticket setup\n${P}ticket panel\n${P}ticket categories\n${P}ticket addcategory <id> <name> <description>\n${P}ticket editcategory <id> <name> <description>\n${P}ticket delcategory <id>\n${P}ticket editpanel title|description|color|button ...\n${P}ticket open <category-id>\n${P}ticket close / claim / unclaim\n${P}ticket add @user / remove @user\n${P}ticket rename <name>`);
 }
 async function openApplication(m,d){
  if(!d.applications.enabled)return m.reply(`❌ Run ${P}application setup first.`);
  const existing=m.guild.channels.cache.find(x=>x.type===ChannelType.GuildText&&x.topic===`application:${m.author.id}`);if(existing)return m.reply(`⚠️ You already have an application: ${existing}`);
  const base=d.categories[0],staff=base?.role;const ch=await m.guild.channels.create({name:`application-${m.author.username}`.toLowerCase().replace(/[^a-z0-9-]/g,'').slice(0,80),type:ChannelType.GuildText,parent:base?.category||null,topic:`application:${m.author.id}`,permissionOverwrites:[{id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]},{id:staff,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.ManageMessages]}].filter(x=>x.id)});
  await ch.send({embeds:[new EmbedBuilder().setTitle(d.applications.title).setDescription(`${d.applications.description}\n\n${d.applications.questions.map((q,i)=>`**${i+1}. ${q}**`).join('\n')}\n\nPlease answer each question in one message.`)]});return m.reply(`✅ Application channel: ${ch}`);
 }
 async function app(m,a){const d=gd(m.guild.id),sub=(a.shift()||'setup').toLowerCase();if(sub==='setup'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');d.applications.enabled=true;d.applications.channel=m.channel.id;save();return m.reply(`✅ Application system enabled in ${m.channel}.`);}if(sub==='panel'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');return m.channel.send(appPanel(d));}if(sub==='edit'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const mode=(a.shift()||'').toLowerCase();if(mode==='title')d.applications.title=a.join(' ').replace(/_/g,' ').slice(0,256);else if(mode==='description')d.applications.description=a.join(' ').replace(/_/g,' ').slice(0,4000);else if(mode==='color'){const v=parseInt((a[0]||'').replace(/^#/,'')||'0',16);if(!Number.isInteger(v)||v<0||v>0xffffff)return m.reply(`Usage: ${P}application edit color <hex>`);d.applications.color=v;}else if(mode==='button'){d.applications.buttonLabel=(a.shift()||'Apply Now').slice(0,80);d.applications.buttonEmoji=a.shift()||'📝';}else return m.reply(`Usage: ${P}application edit title|description|color|button ...`);save();return m.reply('✅ Application panel updated.');}if(sub==='questions'){return m.reply({embeds:[new EmbedBuilder().setTitle('📝 Application Questions').setDescription(d.applications.questions.map((q,i)=>`**${i+1}.** ${q}`).join('\n'))]});}if(sub==='question'){if(!canConfig(m))return m.reply('❌ You need **Manage Server**.');const mode=(a.shift()||'').toLowerCase();if(mode==='add'){const q=a.join(' ');if(!q)return m.reply(`Usage: ${P}application question add <question>`);d.applications.questions.push(q.slice(0,500));}else if(mode==='remove'){const n=Number(a[0]);if(!Number.isInteger(n)||n<1||n>d.applications.questions.length)return m.reply('❌ Invalid question number.');d.applications.questions.splice(n-1,1);}else if(mode==='edit'){const n=Number(a.shift());const q=a.join(' ');if(!Number.isInteger(n)||n<1||n>d.applications.questions.length||!q)return m.reply(`Usage: ${P}application question edit <number> <question>`);d.applications.questions[n-1]=q.slice(0,500);}else return m.reply(`Usage: ${P}application question add|remove|edit ...`);save();return m.reply('✅ Application questions updated.');}if(sub==='apply')return openApplication(m,d);return openApplication(m,d);}
 const old=client.listeners('messageCreate').at(-1);if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();if(c==='ticket'||c==='tickets')return manage(m,(a.shift()||'help').toLowerCase(),a);if(c==='application'||c==='applications')return app(m,a);if(c==='apply')return app(m,['apply']);return old(m);}catch(e){console.error('[TICKET V2]',e);}});}
 client.on('interactionCreate',async i=>{try{
  if(i.isStringSelectMenu()&&i.customId==='lc_ticket_category'){await i.deferReply({ephemeral:true});return open({guild:i.guild,author:i.user,member:i.member,channel:i.channel,reply:x=>i.editReply(x)},i.values[0]);}
  if(i.isButton()&&i.customId==='lc_apply_open'){await i.deferReply({ephemeral:true});return openApplication({guild:i.guild,author:i.user,member:i.member,channel:i.channel,reply:x=>i.editReply(x)},gd(i.guild.id));}
  if(i.isButton()&&i.customId==='lc_ticket_close'){await i.deferReply({ephemeral:true});const d=gd(i.guild.id),c=ticketCategory(i);if(!c||!isStaff(i,c))return i.editReply('❌ You need the category staff role or **Manage Channels**.');await log(d,c,i.guild,new EmbedBuilder().setTitle('🔒 Ticket Closed').setDescription(`**Ticket:** #${i.channel.name}\n**Closed by:** ${i.user}`).setColor(0xed4245).setTimestamp());await transcript(d,c,i.channel,i.guild,i.user);await i.channel.permissionOverwrites.edit(i.guild.roles.everyone,{ViewChannel:false,SendMessages:false}).catch(()=>{});return i.editReply('🔒 Ticket closed and transcript saved.');}
  if(i.isButton()&&i.customId==='lc_ticket_claim'){const c=ticketCategory(i);if(!c||!isStaff(i,c))return i.reply({content:'❌ Category staff role or Manage Channels required.',ephemeral:true});return i.reply({content:`🙋 Ticket claimed by ${i.user}.`,ephemeral:false});}
  if(i.isButton()&&i.customId==='lc_ticket_add'){const c=ticketCategory(i);if(!c||!isStaff(i,c))return i.reply({content:'❌ Category staff role or Manage Channels required.',ephemeral:true});return i.reply({content:`Use ${P}ticket add @user to add someone to this ticket.`,ephemeral:true});}
 }catch(e){console.error('[TICKET INTERACTION]',e);if(i.isRepliable()&&!i.replied&&!i.deferred)i.reply({content:'❌ Ticket action failed.',ephemeral:true}).catch(()=>{});}});
};
