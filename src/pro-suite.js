const fs=require('fs');
const path=require('path');
const {REST,Routes,EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle,PermissionFlagsBits,ApplicationCommandType}=require('discord.js');

module.exports=function attachProSuite(client,prefix='.'){
  const P=prefix||'.';
  const started=Date.now();
  const cooldowns=new Map();
  const aliases=new Map([
    ['h','help'],['?','help'],['p','ping'],['si','serverinfo'],['ui','userinfo'],['av','avatar'],
    ['np','nowplaying'],['q','queue'],['rm','remove'],['vc','voice'],['mc','membercount'],
    ['delchannel','deletechannel'],['delch','deletechannel'],['up','uptime'],['stats','botstats']
  ]);
  const dataDir=path.join(process.cwd(),'data');
  const file=path.join(dataDir,'pro-suite.json');
  if(!fs.existsSync(dataDir))fs.mkdirSync(dataDir,{recursive:true});
  let db={};try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{db={}};
  const save=()=>{try{fs.writeFileSync(file,JSON.stringify(db,null,2))}catch(e){console.error('[PRO DB]',e)}};
  const gd=id=>db[id]||(db[id]={cooldowns:{},disabled:[],restricted:{}});
  const fmt=ms=>{let s=Math.floor(ms/1000),d=Math.floor(s/86400);s%=86400;let h=Math.floor(s/3600);s%=3600;let m=Math.floor(s/60);s%=60;return `${d}d ${h}h ${m}m ${s}s`};
  const emb=(title,desc,color=0x5865f2)=>new EmbedBuilder().setTitle(title).setDescription(desc).setColor(color).setTimestamp();
  const has=(m,p)=>m.member?.permissions?.has(p)||m.guild?.ownerId===m.author.id;
  const bot=m=>m.guild?.members?.me;
  const blocked=(m,c)=>{const g=gd(m.guild.id);return g.disabled.includes(c)};
  const restricted=(m,c)=>{const r=gd(m.guild.id).restricted[c];if(!r)return false;const roleOk=!r.roles?.length||r.roles.some(id=>m.member.roles.cache.has(id));const channelOk=!r.channels?.length||r.channels.includes(m.channel.id);return roleOk&&channelOk};
  const cd=(m,c,seconds=3)=>{const key=`${m.guild.id}:${m.author.id}:${c}`,until=cooldowns.get(key)||0;if(until>Date.now())return Math.ceil((until-Date.now())/1000);cooldowns.set(key,Date.now()+seconds*1000);return 0};
  const usage=(m,c)=>m.reply(`Usage: ${P}${c}`);
  async function deleteChannel(m){
    if(!has(m,PermissionFlagsBits.ManageChannels))return m.reply('❌ You need **Manage Channels**.');
    const target=m.mentions.channels.first()||m.channel;
    const me=bot(m);if(!me?.permissionsIn(target).has(PermissionFlagsBits.ManageChannels))return m.reply('❌ I need **Manage Channels** in that channel.');
    if(target.id===m.channel.id){
      const row=new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId(`lc_delete_${target.id}`).setLabel('Delete this channel').setStyle(ButtonStyle.Danger),new ButtonBuilder().setCustomId('lc_delete_cancel').setLabel('Cancel').setStyle(ButtonStyle.Secondary));
      const msg=await m.reply({content:`⚠️ This will permanently delete ${target}. Continue?`,components:[row]});
      const col=msg.createMessageComponentCollector({time:15000});
      col.on('collect',async i=>{if(i.user.id!==m.author.id)return i.reply({content:'❌ Only the command author can confirm.',ephemeral:true});if(i.customId==='lc_delete_cancel'){await i.update({content:'❎ Cancelled.',components:[]});return col.stop();}await i.update({content:'🗑️ Deleting channel...',components:[]});await target.delete(`Requested by ${m.author.tag}`).catch(()=>{});col.stop()});
      return;
    }
    await m.reply(`🗑️ Deleting ${target}...`);await target.delete(`Requested by ${m.author.tag}`).catch(async()=>m.channel.send('❌ I could not delete that channel.').catch(()=>{}));
  }
  async function slashRegister(){
    if(!client.user||!process.env.DISCORD_TOKEN)return;
    const id=client.application?.id||process.env.CLIENT_ID;if(!id)return;
    const commands=[
      {name:'help',description:'Open the LightCore command center'},
      {name:'ping',description:'Check bot latency'},
      {name:'uptime',description:'Show bot uptime'},
      {name:'botstats',description:'Show bot statistics'},
      {name:'serverinfo',description:'Show server information'},
      {name:'membercount',description:'Show member count'},
      {name:'deletechannel',description:'Delete a channel (Manage Channels required)',options:[{name:'channel',description:'Channel to delete',type:7,required:false}]},
      {name:'music',description:'Open music command help'},
      {name:'ticket',description:'Open ticket command help'},
      {name:'economy',description:'Open economy command help'},
      {name:'leveling',description:'Open leveling command help'},
      {name:'logging',description:'Open logging command help'},
      {name:'invites',description:'Open invite tracking commands'},
      {name:'giveaways',description:'Open free giveaway commands'},
      {name:'userinfo',description:'Show user information',options:[{name:'user',description:'User',type:6,required:false}]},
      {name:'avatar',description:'Show a user avatar',options:[{name:'user',description:'User',type:6,required:false}]}
    ];
    try{const rest=new REST({version:'10'}).setToken(process.env.DISCORD_TOKEN);await rest.put(Routes.applicationCommands(id),{body:commands});console.log(`[PRO] Registered ${commands.length} global slash commands.`)}catch(e){console.error('[PRO SLASH]',e?.message||e)}
  }
  client.once('ready',()=>{console.log(`[PRO] LightCore Pro suite ready | uptime base ${new Date(started).toISOString()}`);slashRegister().catch(()=>{})});
  client.on('interactionCreate',async i=>{
    try{
      if(i.isButton()&&i.customId.startsWith('lc_delete_')){if(i.customId==='lc_delete_cancel')return i.update({content:'❎ Cancelled.',components:[]});const id=i.customId.slice('lc_delete_'.length),ch=i.guild?.channels.cache.get(id);if(!ch)return i.update({content:'❌ Channel no longer exists.',components:[]});if(!i.memberPermissions?.has(PermissionFlagsBits.ManageChannels))return i.reply({content:'❌ You need Manage Channels.',ephemeral:true});await i.update({content:'🗑️ Deleting channel...',components:[]});await ch.delete(`Requested by ${i.user.tag}`);return;}
      if(!i.isChatInputCommand())return;
      const c=i.commandName;
      const fake={guild:i.guild,member:i.member,author:i.user,channel:i.channel,mentions:{channels:{first:()=>i.options.getChannel('channel')},users:{first:()=>i.options.getUser('user')}},reply:async o=>i.reply(o),channelId:i.channelId};
      if(c==='help')return i.reply({embeds:[emb('🤖 LightCore Command Center',`Prefix: \`${P}\`\n\nUse **${P}help <category>** for detailed commands.\nCategories include moderation, security, logging, tickets, music, economy, leveling, applications, fun, utility, roles, welcome, voice and more.`)]});
      if(c==='ping')return i.reply(`🏓 Pong! **${client.ws.ping}ms**`);
      if(c==='uptime')return i.reply({embeds:[emb('⏱️ LightCore Uptime',`**Uptime:** ${fmt(Date.now()-started)}\n**Ping:** ${client.ws.ping}ms\n**Servers:** ${client.guilds.cache.size}\n**Users cached:** ${client.users.cache.size}`)]});
      if(c==='botstats')return i.reply({embeds:[emb('📊 LightCore Statistics',`**Servers:** ${client.guilds.cache.size}\n**Users cached:** ${client.users.cache.size}\n**Channels cached:** ${client.channels.cache.size}\n**Ping:** ${client.ws.ping}ms\n**Uptime:** ${fmt(Date.now()-started)}`)]});
      if(c==='serverinfo')return i.reply({embeds:[emb(`🏠 ${i.guild.name}`,`**Owner:** <@${i.guild.ownerId}>\n**Members:** ${i.guild.memberCount}\n**Channels:** ${i.guild.channels.cache.size}\n**Roles:** ${i.guild.roles.cache.size}\n**Boosts:** ${i.guild.premiumSubscriptionCount||0}`)]});
      if(c==='membercount')return i.reply(`👥 Members: **${i.guild.memberCount}**`);
      if(c==='deletechannel')return deleteChannel(fake);
      if(c==='music')return i.reply(`🎵 Use \`${P}musichelp\` or \`${P}play <song>\` for music.`);
      if(c==='ticket')return i.reply(`🎫 Use \`${P}ticket setup\` to configure tickets manually.`);
      if(c==='economy')return i.reply(`💰 Economy commands: \`${P}balance\`, \`${P}daily\`, \`${P}work\`, \`${P}pay @user <amount>\`.`);
      if(c==='leveling')return i.reply(`📈 Leveling commands: \`${P}level\`, \`${P}rank\`, \`${P}leaderboard\`, \`${P}setxp\`.`);
      if(c==='logging')return i.reply(`📋 Logging: \`${P}logsetup\`, \`${P}logsettings\`, \`${P}logevents\`.`);
      if(c==='invites')return i.reply(`📨 Invite tracking: \`${P}invites\`, \`${P}invites-leaderboard\`.`);
      if(c==='giveaways')return i.reply(`🎁 Free giveaways: \`${P}giveaway help\` or the giveaway commands provided by LightCore.`);
      if(c==='userinfo'){const u=i.options.getUser('user')||i.user;return i.reply({embeds:[emb(`👤 ${u.tag}`,`**ID:** \`${u.id}\`\n**Created:** <t:${Math.floor(u.createdTimestamp/1000)}:R>`)]});}
      if(c==='avatar'){const u=i.options.getUser('user')||i.user;return i.reply({embeds:[new EmbedBuilder().setTitle(`${u.username}'s Avatar`).setImage(u.displayAvatarURL({size:2048})).setColor(0x5865f2)]});}
    }catch(e){console.error('[PRO INTERACTION]',e?.stack||e);if(i.isRepliable()&&!i.replied&&!i.deferred)await i.reply({content:'❌ Something went wrong.',ephemeral:true}).catch(()=>{})}
  });
  client.on('messageCreate',async m=>{
    try{
      if(m.author.bot||!m.guild||!m.content.startsWith(P))return;
      const parts=m.content.slice(P.length).trim().split(/\s+/),raw=(parts.shift()||'').toLowerCase(),c=aliases.get(raw)||raw;
      if(['uptime','botstats','deletechannel'].includes(c)){
        const wait=cd(m,c,2);if(wait)return m.reply(`⏳ Slow down. Try again in **${wait}s**.`);
        if(blocked(m,c)||restricted(m,c))return m.reply('❌ This command is restricted or disabled here.');
        if(c==='uptime')return m.reply({embeds:[emb('⏱️ LightCore Uptime',`**Uptime:** ${fmt(Date.now()-started)}\n**Ping:** ${client.ws.ping}ms\n**Servers:** ${client.guilds.cache.size}\n**Users cached:** ${client.users.cache.size}`)]});
        if(c==='botstats')return m.reply({embeds:[emb('📊 LightCore Statistics',`**Servers:** ${client.guilds.cache.size}\n**Users cached:** ${client.users.cache.size}\n**Channels:** ${client.channels.cache.size}\n**Ping:** ${client.ws.ping}ms\n**Uptime:** ${fmt(Date.now()-started)}`)]});
        return deleteChannel(m);
      }
      if(['aliases','cooldowns','permissions'].includes(c)){
        if(c==='aliases')return m.reply({embeds:[emb('🔗 Command Aliases',Array.from(aliases.entries()).map(([a,v])=>`\`${P}${a}\` → \`${P}${v}\``).join('\n'))]});
        if(c==='cooldowns')return m.reply({embeds:[emb('⏱️ Cooldown Engine','LightCore applies short safety cooldowns to high-impact utility commands. More per-command controls can be configured from the dashboard.') ]});
        return m.reply({embeds:[emb('🛡️ Permission Engine','Commands check Discord permissions before administrative actions. Use Discord command permissions and server roles for additional control.') ]});
      }
    }catch(e){console.error('[PRO MESSAGE]',e?.stack||e)}
  });
};
