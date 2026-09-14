const fs=require('fs'),path=require('path');
const {ChannelType,PermissionFlagsBits,EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle}=require('discord.js');

module.exports=function attachEasyCommands(client,prefix='.'){
 const P=prefix||'.';
 const file=path.join(process.cwd(),'data','ticket-suite-v2.json');
 fs.mkdirSync(path.dirname(file),{recursive:true});
 const read=()=>{try{return JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{return {}}};
 const write=d=>fs.writeFileSync(file,JSON.stringify(d,null,2));
 const fresh=()=>({categories:[{id:'support',name:'Support',emoji:'🎫',description:'General support',category:null,role:null,logChannel:null,transcriptChannel:null}],panel:{title:'🎫 Support Center',description:'Select a ticket category below to open a private ticket.',color:0x5865f2,buttonLabel:'Open Ticket',buttonEmoji:'🎫'},applications:{enabled:false,channel:null,title:'📝 Staff Application',description:'Apply by selecting an application type below.',color:0x5865f2,buttonLabel:'Apply Now',buttonEmoji:'📝',questions:['What are you applying for?','Why should we choose you?','What experience do you have?']},counter:0});
 const data=g=>{const d=read();if(!d[g])d[g]=fresh();const f=fresh();for(const k of Object.keys(f))if(d[g][k]===undefined)d[g][k]=f[k];return {all:d,d:d[g]};};
 const clean=(s,n=90)=>String(s||'').replace(/[<>]/g,'').slice(0,n);
 const can=m=>m.guild.ownerId===m.author.id||m.member?.permissions.has(PermissionFlagsBits.ManageGuild);
 const panel=d=>({embeds:[new EmbedBuilder().setTitle(d.panel?.title||'🎫 Support Center').setDescription(d.panel?.description||'Select a ticket category below to open a private ticket.').setColor(d.panel?.color||0x5865f2).setFooter({text:'LightCore • Easy Ticket System'}).setTimestamp()],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_easy_ticket_setup').setLabel('⚡ Quick Setup').setStyle(ButtonStyle.Success),new ButtonBuilder().setCustomId('lc_easy_ticket_panel').setLabel('🎫 Open Ticket Panel').setStyle(ButtonStyle.Primary))]});
 const categoryMenu=d=>({embeds:[new EmbedBuilder().setTitle(d.panel?.title||'🎫 Support Center').setDescription(d.panel?.description||'Choose a category to open a private ticket.').setColor(d.panel?.color||0x5865f2).setFooter({text:'LightCore • Ticket System'}).setTimestamp()],components:[{type:1,components:[{type:3,custom_id:'lc_ticket_category',placeholder:'🎫 Select a ticket category',options:(d.categories||[]).slice(0,25).map(c=>({label:clean(c.name,100),value:c.id,description:clean(c.description||'Support',100),emoji:c.emoji||'🎫'}))}]}]});
 async function quickSetup(guild){
  const {all,d}=data(guild.id);
  if(!d.categories?.length)d.categories=fresh().categories;
  for(const c of d.categories){
   let cat=c.category&&guild.channels.cache.get(c.category);if(!cat||cat.type!==ChannelType.GuildCategory)cat=await guild.channels.create({name:`🎫・${clean(c.name)}`,type:ChannelType.GuildCategory,reason:'LightCore easy ticket setup'});c.category=cat.id;
   let role=c.role&&guild.roles.cache.get(c.role);if(!role)role=guild.roles.cache.find(r=>r.name.toLowerCase()===`${c.name.toLowerCase()} staff`);if(!role)role=await guild.roles.create({name:`${clean(c.name)} Staff`,reason:'LightCore easy ticket setup'});c.role=role.id;
   const ow=[{id:guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:role.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory,PermissionFlagsBits.ManageMessages,PermissionFlagsBits.ManageChannels]}];
   let log=c.logChannel&&guild.channels.cache.get(c.logChannel);if(!log||log.type!==ChannelType.GuildText)log=await guild.channels.create({name:`${c.id}-logs`.slice(0,100),type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:ow,reason:'LightCore easy ticket setup'});c.logChannel=log.id;
   let tr=c.transcriptChannel&&guild.channels.cache.get(c.transcriptChannel);if(!tr||tr.type!==ChannelType.GuildText)tr=await guild.channels.create({name:`${c.id}-transcripts`.slice(0,100),type:ChannelType.GuildText,parent:cat.id,permissionOverwrites:ow,reason:'LightCore easy ticket setup'});c.transcriptChannel=tr.id;
  }
  write(all);return d;
 }
 async function guide(m){
  const d=data(m.guild.id).d;
  if(!can(m))return m.reply({embeds:[new EmbedBuilder().setTitle('🎫 Ticket Center').setDescription('Click **Open Ticket Panel** to see the available ticket types.\n\nIf the server has not been configured yet, ask a server manager to run `.ticket setup`.').setColor(0x5865f2)]});
  return m.reply(panel(d));
 }
 async function setupAndPost(m){
  if(!can(m))return m.reply('❌ You need **Manage Server** to run the quick ticket setup.');
  try{const d=await quickSetup(m.guild);await m.reply({embeds:[new EmbedBuilder().setTitle('✅ Tickets Ready').setDescription('Your ticket system is configured automatically.\n\n**Created/checked:**\n🎫 Ticket category\n👥 Staff role\n📋 Logs channel\n📜 Transcript channel\n\nThe panel is ready below. Members only need to choose a ticket type.').setColor(0x57f287).setTimestamp()});await m.channel.send(categoryMenu(d));}catch(e){console.error('[EASY TICKETS]',e?.stack||e);return m.reply(`❌ Ticket setup failed: ${clean(e?.message||'check my permissions')}`)}
 }
 async function sendPanel(m){const d=data(m.guild.id).d;return m.channel.send(categoryMenu(d));}
 const previous=client.listeners('messageCreate').at(-1);
 client.on('messageCreate',async m=>{try{
  if(m.author.bot||!m.guild)return;
  if(!m.content.startsWith(P))return previous?.(m);
  const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();
  if(c==='ticket'||c==='tickets'){
   const sub=(a[0]||'').toLowerCase();
   if(!sub)return guide(m);
   if(['setup','quicksetup','configure','config'].includes(sub))return setupAndPost(m);
   if(['panel','post'].includes(sub))return sendPanel(m);
   if(['help','guide'].includes(sub))return m.reply({embeds:[new EmbedBuilder().setTitle('🎫 Easy Tickets').setDescription(`**For admins**\n\`${P}ticket setup\` → automatically creates everything\n\`${P}ticket panel\` → posts the ticket panel\n\n**For members**\nClick a category on the panel → ticket opens automatically.\n\nExisting advanced ticket commands still work.`).setColor(0x5865f2)]});
   return previous?.(m);
  }
  if(c==='ticketsetup')return setupAndPost(m);
  if(c==='setup'&&['tickets','ticket'].includes((a[0]||'').toLowerCase()))return setupAndPost(m);
  if(c==='t'&&!a.length)return guide(m);
  return previous?.(m);
 }catch(e){console.error('[EASY COMMANDS]',e?.stack||e)}});
 client.on('interactionCreate',async i=>{try{
  if(!i.guild||!i.isButton())return;
  if(i.customId==='lc_easy_ticket_setup'){if(!can({guild:i.guild,member:i.member,author:i.user}))return i.reply({content:'❌ You need Manage Server to use Quick Setup.',ephemeral:true});await i.deferReply({ephemeral:true});await quickSetup(i.guild);await i.editReply('✅ Ticket system is ready. Use **🎫 Open Ticket Panel** or run `.ticket panel`.');return;}
  if(i.customId==='lc_easy_ticket_panel'){const d=data(i.guild.id).d;await i.reply({...categoryMenu(d),ephemeral:true});return;}
 }catch(e){console.error('[EASY TICKET BUTTON]',e?.stack||e);if(!i.replied&&!i.deferred)await i.reply({content:'❌ Something went wrong. Check my channel permissions.',ephemeral:true}).catch(()=>{});}});
 console.log('[EASY] Guided ticket setup + simple command aliases loaded');
};
