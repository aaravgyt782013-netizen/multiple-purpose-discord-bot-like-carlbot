const {EmbedBuilder,ActionRowBuilder,StringSelectMenuBuilder,ButtonBuilder,ButtonStyle}=require('discord.js');
module.exports=function(client,prefix='.'){
 const P=prefix||'.';
 const groups={
  home:['help','ping','uptime','botinfo','invite','support','serverinfo','membercount','userinfo','avatar','roleinfo','channelinfo','servericon'],
  moderation:['kick','ban','unban','softban','timeout','untimeout','warn','unwarn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','massrole'],
  security:['automod','antiraid','antinuke','security','filter','verify','honeypot'],
  logging:['logsetup','setlog','logdisable','logsettings','logevents','logtest'],
  leveling:['level','rank','xp','leaderboard','setxp','leveling','reward','rewards'],
  economy:['balance','bal','daily','work','beg','deposit','withdraw','pay','richlist','luck','eco'],
  music:['play','p','join','connect','leave','disconnect','pause','resume','unpause','skip','next','stop','queue','q','nowplaying','np','current','volume','vol','loop','repeat','shuffle','remove','move','clearqueue','musichelp'],
  tickets:['ticket','open','ticket-panel','ticket-setup','close','claim','unclaim'],
  giveaways:['giveaway','gcreate'],
  fun:['8ball','coinflip','roll','choose','ship','rate','cat','dog','joke'],
  counters:['counter','counter autosetup','counter setup','counter remove','counter update'],
  notifications:['notifier add','notifier list','notifier remove','notifier enable','notifier disable','notifier test'],
  invites:['invites','invites-leaderboard','inviteconfig'],
  announcements:['announce','say','embed','embedhelp','poll','announce-embed'],
  roles:['role','role give','role remove','role duplicate','deleterole','autorole','reactionrole','levelrole','roleall'],
  channels:['channel create','channel duplicate','category delete'],
  welcome:['welcome','setwelcome','goodbye'],
  autoresponder:['autoresponder','ar'],
  custom:['customcommand','cc','cc-delete','cc-list'],
  afk:['afk'],
  stars:['stars','starleaderboard','starconfig','starboard'],
  voice:['tempvoice','voice'],
  configuration:['permissions','perm','emoji','emoji-list','config','prefix','enable','disable']
 };
 const names={home:'🏠 Home',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',leveling:'📈 Leveling',economy:'💰 Economy',music:'🎧 Music',tickets:'🎫 Tickets',giveaways:'🎉 Giveaways',fun:'🎭 Fun',counters:'📊 Counters',notifications:'🔔 Notifications',invites:'🔗 Invites',announcements:'📢 Announcements',roles:'🎭 Roles',channels:'📁 Channels',welcome:'👋 Welcome',autoresponder:'🤖 Auto Responder',custom:'⚙️ Custom Commands',afk:'💤 AFK',stars:'⭐ Stars',voice:'🔊 Voice',configuration:'✨ Configuration'};
 const em=['✨','⚡','🌟','💫','🔷','🔹'];
 function help(cat='home'){
  if(!groups[cat])cat='home';
  const options=Object.keys(groups).map(k=>({label:names[k].replace(/^\S+\s/,''),value:k,emoji:names[k].split(' ')[0]}));
  if(cat==='home')return {embeds:[new EmbedBuilder().setTitle(`${em[Math.floor(Date.now()/5000)%em.length]} LIGHTCORE • HELP CENTER`).setDescription(`> **Prefix:** \`${P}\`\n> **Categories:** **${Object.keys(groups).length}**\n\n${Object.keys(groups).map((k,i)=>`${em[i%em.length]} **${names[k]}**\n   └─ \`${P}help ${k}\``).join('\n')}\n\n> 📌 Commands are displayed one-per-line in a clean, ordered layout.`).setColor([0x5865f2,0x7c3aed,0x2563eb,0x06b6d4][Math.floor(Date.now()/5000)%4]).setTimestamp()],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('lc_help_ordered').setPlaceholder('📂 Select a category').addOptions(options.slice(0,25)))]};
  const list=groups[cat].map((x,i)=>`${em[i%em.length]} \`${P}${x}\``).join('\n');
  return {embeds:[new EmbedBuilder().setTitle(`${names[cat]} • COMMANDS`).setDescription(`> **${groups[cat].length} commands**\n\n${list}\n\n> 🔙 Use \`${P}help\` for the main menu.`).setColor([0x5865f2,0x7c3aed,0x2563eb,0x06b6d4][Math.floor(Date.now()/5000)%4]).setTimestamp()],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_help_ordered_home').setLabel('Help Home').setEmoji('🏠').setStyle(ButtonStyle.Secondary))]};
 }
 const old=client.listeners('messageCreate').at(-1);
 if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();if(c==='help'||c==='h')return m.reply(help((a[0]||'home').toLowerCase()));return old(m)}catch(e){console.error('[HELP ORDERED]',e)}})}
 client.on('interactionCreate',async i=>{try{if(i.isStringSelectMenu()&&i.customId==='lc_help_ordered')return i.update(help(i.values[0]));if(i.isButton()&&i.customId==='lc_help_ordered_home')return i.update(help('home'));}catch(e){console.error('[HELP INTERACTION]',e)}});
};
