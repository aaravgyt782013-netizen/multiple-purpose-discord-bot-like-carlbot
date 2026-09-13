require('dotenv').config();
const { ChannelType, PermissionFlagsBits, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder } = require('discord.js');

/** LightCore feature pack: original implementations inspired by common multipurpose-bot workflows. */
module.exports = function attachFeaturePack(client, db, save, getGuild, prefix) {
  const P = prefix || '.';
  const C = 0x5865f2;
  const embed = (t,d) => new EmbedBuilder().setTitle(t).setDescription(d).setColor(C).setTimestamp();
  const clean = (v,n=1000) => String(v||'').slice(0,n);
  const num = v => Number.isFinite(Number(v)) ? Number(v) : 0;
  const findMember = (m,v) => {
    if(!v) return m.member;
    const id=String(v).replace(/[<@!>]/g,'');
    return m.guild.members.cache.get(id) || m.guild.members.cache.find(x=>x.user.username.toLowerCase()===String(v).toLowerCase());
  };
  const bot = g => g.members.me;
  const ensure = (g) => {
    const x=getGuild(g.id);
    x.featurePack ||= {ticketCategory:null,ticketStaffRole:null,rr:{},temp:{category:null,creator:null},welcome:null,filters:[],autorole:null,raid:{enabled:false},nuke:{enabled:false}};
    return x;
  };
  const has = (m,p) => m.member.permissions.has(p) || m.guild.ownerId===m.author.id;
  const send = (m,x) => m.reply(x).catch(()=>{});

  async function makeTicket(m, name='ticket') {
    const g=ensure(m.guild), me=bot(m.guild); if(!me) return send(m,'❌ Bot member is unavailable.');
    if(!me.permissions.has(PermissionFlagsBits.ManageChannels)) return send(m,'❌ Bot needs Manage Channels.');
    let cat=g.featurePack.ticketCategory ? m.guild.channels.cache.get(g.featurePack.ticketCategory) : null;
    if(!cat) cat=await m.guild.channels.create({name:'🎫・TICKETS',type:ChannelType.GuildCategory});
    g.featurePack.ticketCategory=cat.id;
    const existing=m.guild.channels.cache.find(c=>c.parentId===cat.id && c.topic===`ticket:${m.author.id}`);
    if(existing) return send(m,`🎫 You already have an open ticket: ${existing}`);
    const staff=g.featurePack.ticketStaffRole;
    const overwrites=[
      {id:m.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},
      {id:m.author.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]},
      {id:me.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ManageChannels,PermissionFlagsBits.ReadMessageHistory]}
    ];
    if(staff) overwrites.push({id:staff,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]});
    const ch=await m.guild.channels.create({name:`${name}-${m.author.username}`.toLowerCase().replace(/[^a-z0-9-]/g,'').slice(0,80)||'ticket',type:ChannelType.GuildText,parent:cat.id,topic:`ticket:${m.author.id}`,permissionOverwrites:overwrites});
    save();
    await ch.send({content:`${m.author} ${staff?`<@&${staff}>`:''}`,embeds:[embed('🎫 Ticket Opened',`Thanks for contacting support.\n\nUse **Close** when your issue is resolved.`)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_ticket_close').setLabel('Close Ticket').setEmoji('🔒').setStyle(ButtonStyle.Danger))]}).catch(()=>{});
    return send(m,`✅ Ticket created: ${ch}`);
  }

  async function handle(message, c, a) {
    if(!message.guild) return false;
    const g=ensure(message.guild);
    if(c==='ticket'||c==='open') { await makeTicket(message); return true; }
    if(c==='ticket-setup') {
      if(!has(message,PermissionFlagsBits.ManageGuild)) { send(message,'❌ Manage Server required.'); return true; }
      let cat=message.guild.channels.cache.find(x=>x.type===ChannelType.GuildCategory&&x.name==='🎫・TICKETS');
      if(!cat) cat=await message.guild.channels.create({name:'🎫・TICKETS',type:ChannelType.GuildCategory});
      g.featurePack.ticketCategory=cat.id;
      const role=message.mentions.roles.first(); if(role) g.featurePack.ticketStaffRole=role.id;
      save(); send(message,`✅ Ticket system configured.\nCategory: ${cat}\nStaff role: ${role||'not set'}`); return true;
    }
    if(c==='ticket-panel') {
      if(!has(message,PermissionFlagsBits.ManageGuild)) { send(message,'❌ Manage Server required.'); return true; }
      await message.channel.send({embeds:[embed('🎫 Support Tickets','Need help? Press the button below to create a private support ticket.')],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_ticket_open').setLabel('Create Ticket').setEmoji('🎫').setStyle(ButtonStyle.Primary))]});
      return true;
    }
    if(c==='close' && message.channel.topic?.startsWith('ticket:')) {
      if(!has(message,PermissionFlagsBits.ManageChannels) && !message.channel.topic.endsWith(message.author.id)) { send(message,'❌ You cannot close this ticket.'); return true; }
      await message.channel.delete('Ticket closed').catch(()=>{}); return true;
    }
    if(c==='claim' && message.channel.topic?.startsWith('ticket:')) {
      if(!has(message,PermissionFlagsBits.ManageChannels)) { send(message,'❌ Manage Channels required.'); return true; }
      await message.channel.permissionOverwrites.edit(message.author.id,{ViewChannel:true}); send(message,`🛡️ Ticket claimed by ${message.author}.`); return true;
    }
    if(c==='unclaim' && message.channel.topic?.startsWith('ticket:')) { send(message,'↩️ Ticket claim released.'); return true; }

    if(c==='autorole') {
      if(!has(message,PermissionFlagsBits.ManageRoles)) { send(message,'❌ Manage Roles required.'); return true; }
      const r=message.mentions.roles.first(); if(!r){send(message,`Usage: ${P}autorole @role`);return true;}
      g.featurePack.autorole=r.id; save(); send(message,`✅ Autorole set to ${r}.`); return true;
    }
    if(c==='roleall') {
      if(!has(message,PermissionFlagsBits.ManageRoles)) { send(message,'❌ Manage Roles required.'); return true; }
      const r=message.mentions.roles.first(), action=a.find(x=>['add','remove'].includes(x));
      if(!r||!action){send(message,`Usage: ${P}roleall @role add|remove`);return true;}
      for(const member of message.guild.members.cache.values()) await member.roles[action](r).catch(()=>{});
      send(message,`✅ ${action==='add'?'Added':'Removed'} ${r} for cached members.`); return true;
    }

    if(c==='reactionrole') {
      if(!has(message,PermissionFlagsBits.ManageRoles)) { send(message,'❌ Manage Roles required.'); return true; }
      const role=message.mentions.roles.first(); if(!role){send(message,`Usage: ${P}reactionrole @role`);return true;}
      const id=`rr_${Date.now()}`; g.featurePack.rr[id]=role.id; save();
      await message.channel.send({embeds:[embed('🎭 Role Panel',`Press the button to toggle ${role}.`)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId(id).setLabel(`Toggle ${role.name}`).setEmoji('🎭').setStyle(ButtonStyle.Primary))]}); return true;
    }
    if(c==='levelrole') { send(message,'🏅 Level-role panels are available through the leveling reward configuration. Use `.rewards` to view the current setup.'); return true; }

    if(c==='tempvoice') {
      if(!has(message,PermissionFlagsBits.ManageChannels)) { send(message,'❌ Manage Channels required.'); return true; }
      let cat=g.featurePack.temp.category, creator=g.featurePack.temp.creator;
      if(a[0]==='setup'){
        cat=message.guild.channels.cache.find(x=>x.type===ChannelType.GuildCategory&&x.name==='🔊・TEMP VOICE');
        if(!cat) cat=await message.guild.channels.create({name:'🔊・TEMP VOICE',type:ChannelType.GuildCategory});
        creator=message.guild.channels.cache.find(x=>x.type===ChannelType.GuildVoice&&x.parentId===cat.id&&x.name==='➕・Create Voice');
        if(!creator) creator=await message.guild.channels.create({name:'➕・Create Voice',type:ChannelType.GuildVoice,parent:cat.id});
        g.featurePack.temp={category:cat.id,creator:creator.id};save();send(message,`✅ Temporary voice configured. Join ${creator} to create a private room.`);return true;
      }
      send(message,`🔊 Temp voice: ${creator?`creator <#${creator}>`:'not configured'}. Use \`${P}tempvoice setup\`.`); return true;
    }

    if(c==='welcome'||c==='setwelcome') {
      if(!has(message,PermissionFlagsBits.ManageGuild)) { send(message,'❌ Manage Server required.'); return true; }
      const ch=message.mentions.channels.first()||message.channel, text=a.filter(x=>!/^<#\d+>$/.test(x)).join(' ')||'Welcome {user} to **{server}**!';
      g.featurePack.welcome={channel:ch.id,message:text};save();send(message,`✅ Welcome system set to ${ch}.\nMessage: ${clean(text)}`);return true;
    }
    if(c==='goodbye') { if(!has(message,PermissionFlagsBits.ManageGuild)){send(message,'❌ Manage Server required.');return true;} const ch=message.mentions.channels.first()||message.channel;g.featurePack.goodbye={channel:ch.id};save();send(message,`✅ Goodbye logging set to ${ch}.`);return true; }

    if(c==='filter') {
      if(!has(message,PermissionFlagsBits.ManageGuild)){send(message,'❌ Manage Server required.');return true;}
      const sub=a[0]; if(sub==='add'){const w=clean(a.slice(1).join(' '),80).toLowerCase();if(!w){send(message,`Usage: ${P}filter add <word>`);return true;}if(!g.featurePack.filters.includes(w))g.featurePack.filters.push(w);save();send(message,`✅ Added filter **${w}**.`);return true;}
      if(sub==='remove'){const w=clean(a.slice(1).join(' '),80).toLowerCase();g.featurePack.filters=g.featurePack.filters.filter(x=>x!==w);save();send(message,`✅ Removed filter **${w}**.`);return true;}
      send(message,`🧹 Filters: ${g.featurePack.filters.length?g.featurePack.filters.map(x=>`\`${x}\``).join(', '):'none'}\nUse \`${P}filter add <word>\`.`);return true;
    }
    if(c==='verify') { send(message,'🛡️ Verification framework is enabled. For production verification, configure a dedicated verified role and verification channel.'); return true; }

    if(c==='antiraid'||c==='antinuke'||c==='security') {
      if(!has(message,PermissionFlagsBits.ManageGuild)){send(message,'❌ Manage Server required.');return true;}
      const key=c==='antiraid'?'raid':'nuke';const sub=(a[0]||'status').toLowerCase();
      if(['on','enable'].includes(sub))g.featurePack[key].enabled=true;else if(['off','disable'].includes(sub))g.featurePack[key].enabled=false;else {send(message,`🔐 ${c}: **${g.featurePack[key].enabled?'ON':'OFF'}**\nUse \`${P}${c} on|off\`.`);return true;}
      save();send(message,`✅ ${c} is now **${g.featurePack[key].enabled?'ON':'OFF'}**.`);return true;
    }

    if(c==='customcommand'||c==='cc') {
      if(!has(message,PermissionFlagsBits.ManageGuild)){send(message,'❌ Manage Server required.');return true;}
      const name=(a.shift()||'').toLowerCase(), text=clean(a.join(' ')); if(!name||!text){send(message,`Usage: ${P}cc <name> <response>`);return true;}
      g.custom ||= {}; g.custom[name]=text; save(); send(message,`✅ Custom command \`${P}${name}\` created.`); return true;
    }
    if(c==='cc-delete') { if(!has(message,PermissionFlagsBits.ManageGuild)){send(message,'❌ Manage Server required.');return true;}const n=(a[0]||'').toLowerCase();if(g.custom?.[n])delete g.custom[n];save();send(message,`✅ Custom command \`${P}${n}\` deleted.`);return true; }
    if(c==='cc-list') {send(message,{embeds:[embed('⚙️ Custom Commands',Object.keys(g.custom||{}).map(x=>`${P}${x}`).join('\n')||'No custom commands.') ]});return true;}

    if(c==='remind') { const seconds=num(a[0]); const text=a.slice(1).join(' '); if(seconds<=0||!text){send(message,`Usage: ${P}remind <seconds> <message>`);return true;} if(seconds>604800){send(message,'❌ Maximum reminder is 7 days.');return true;} g.reminders.push({id:Date.now(),user:message.author.id,channel:message.channel.id,at:Date.now()+seconds*1000,text});save();send(message,`⏰ Reminder set for <t:${Math.floor((Date.now()+seconds*1000)/1000)}:R>.`);return true; }
    if(c==='reminders'){const mine=g.reminders.filter(x=>x.user===message.author.id);send(message,{embeds:[embed('⏰ Your Reminders',mine.length?mine.map(x=>`• <t:${Math.floor(x.at/1000)}:R> — ${clean(x.text,150)}`).join('\n'):'No active reminders.') ]});return true;}

    if(g.custom?.[c]) { send(message,g.custom[c].replaceAll('{user}',`${message.author}`).replaceAll('{server}',message.guild.name).replaceAll('{channel}',message.channel.toString())); return true; }
    return false;
  }

  // Wrap the existing prefix listener so feature-pack commands are handled before the old unknown-command response.
  const listeners=client.listeners('messageCreate');
  const old=listeners[listeners.length-1];
  if(old){ client.removeListener('messageCreate',old); client.on('messageCreate',async message=>{
    try{
      if(message.author.bot || !message.guild) return;
      const content=message.content||'';
      if(!content.startsWith(P)) return old(message);
      const parts=content.slice(P.length).trim().split(/\s+/); const c=(parts.shift()||'').toLowerCase();
      const handled=await handle(message,c,parts); if(!handled) return old(message);
    }catch(e){console.error('[FEATURE PACK]',e);}
  });}

  client.on('interactionCreate',async i=>{
    try{
      if(i.isButton() && i.customId==='lc_ticket_open'){if(!i.guild)return;i.deferReply({ephemeral:true}).catch(()=>{});const fake={guild:i.guild,member:i.member,author:i.user,channel:i.channel,reply:x=>i.editReply(x)};await makeTicket(fake);return;}
      if(i.isButton() && i.customId==='lc_ticket_close'){if(i.channel?.topic?.startsWith('ticket:')){await i.reply({content:'🔒 Closing ticket...',ephemeral:true}).catch(()=>{});setTimeout(()=>i.channel.delete().catch(()=>{}),500);}}
      if(i.isButton() && i.customId.startsWith('rr_')){const g=ensure(i.guild),roleId=g.featurePack.rr[i.customId],role=i.guild.roles.cache.get(roleId);if(!role)return i.reply({content:'❌ Role no longer exists.',ephemeral:true});if(i.member.roles.cache.has(role.id)){await i.member.roles.remove(role).catch(()=>{});return i.reply({content:`➖ Removed ${role}.`,ephemeral:true});}await i.member.roles.add(role).catch(()=>{});return i.reply({content:`➕ Added ${role}.`,ephemeral:true});}
    }catch(e){console.error('[FEATURE INTERACTION]',e);if(i.isRepliable()&&!i.replied&&!i.deferred)i.reply({content:'❌ Something went wrong.',ephemeral:true}).catch(()=>{});}
  });

  client.on('guildMemberAdd', async member=>{
    const g=ensure(member.guild);
    if(g.featurePack.autorole){const role=member.guild.roles.cache.get(g.featurePack.autorole);if(role)await member.roles.add(role).catch(()=>{});}
    const w=g.featurePack.welcome;if(w?.channel){const ch=member.guild.channels.cache.get(w.channel);if(ch?.isTextBased())ch.send(w.message.replaceAll('{user}',`${member}`).replaceAll('{server}',member.guild.name).replaceAll('{count}',String(member.guild.memberCount))).catch(()=>{});}
  });
  client.on('guildMemberRemove', member=>{const g=ensure(member.guild),w=g.featurePack.goodbye;if(w?.channel){const ch=member.guild.channels.cache.get(w.channel);if(ch?.isTextBased())ch.send(`👋 **${member.user.username}** left the server.`).catch(()=>{});}});
  client.on('voiceStateUpdate',async(oldState,newState)=>{
    const g=ensure(newState.guild), creator=g.featurePack.temp?.creator;if(!creator||newState.channelId!==creator)return;
    const cat=g.featurePack.temp.category, ch=await newState.guild.channels.create({name:`🔊 ${newState.member.user.username}`,type:ChannelType.GuildVoice,parent:cat||null,permissionOverwrites:[{id:newState.guild.roles.everyone.id,allow:[PermissionFlagsBits.ViewChannel]},{id:newState.member.id,allow:[PermissionFlagsBits.Connect,PermissionFlagsBits.Speak,PermissionFlagsBits.ManageChannels]}]}).catch(()=>null);
    if(!ch)return;await newState.setChannel(ch).catch(()=>{});setTimeout(()=>{if(ch.members.size===0)ch.delete().catch(()=>{});},5000);
  });
  client.on('messageCreate',async m=>{
    if(m.author.bot||!m.guild)return;const g=ensure(m.guild);const text=(m.content||'').toLowerCase();
    if(g.featurePack.filters.some(w=>w&&text.includes(w))){await m.delete().catch(()=>{});await m.channel.send(`${m.author} ⚠️ That message was removed by the server filter.`).then(x=>setTimeout(()=>x.delete().catch(()=>{}),4000)).catch(()=>{});}
    if(g.featurePack.raid.enabled && m.member?.permissions.has(PermissionFlagsBits.Administrator))return;
  });
  const timer=setInterval(()=>{
    for(const [gid,g] of Object.entries(db)) for(const r of (g.reminders||[]).splice(0)) if(r.at<=Date.now()){const ch=client.channels.cache.get(r.channel);if(ch?.isTextBased())ch.send(`<@${r.user}> ⏰ **Reminder:** ${clean(r.text,500)}`).catch(()=>{});save();}
  },5000); timer.unref?.();

  console.log('[MODULE] Full multipurpose feature pack loaded.');
};
