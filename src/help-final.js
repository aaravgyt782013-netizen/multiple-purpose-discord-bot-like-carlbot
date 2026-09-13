const {EmbedBuilder,ActionRowBuilder,StringSelectMenuBuilder,ButtonBuilder,ButtonStyle}=require('discord.js');
module.exports=function(client,prefix='.'){
 const P=prefix||'.';
 const groups={
  home:['help','ping','uptime','botinfo','invite','serverinfo','userinfo','avatar','membercount'],
  moderation:['kick','ban','unban','softban','timeout','untimeout','warn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','massrole'],
  security:['automod','antiraid','antinuke','security','filter','verify','honeypot'],
  logging:['logsetup','setlog','logdisable','logsettings','logevents','logtest'],
  music:['play','p','join','connect','leave','disconnect','pause','resume','unpause','skip','next','stop','queue','q','nowplaying','np','current','volume','vol','loop','repeat','shuffle','remove','move','clearqueue','musichelp'],
  tickets:['ticket','open','ticket-panel','ticket-setup','close','claim','unclaim'],
  giveaways:['giveaway','gcreate'],
  fun:['8ball','coinflip','roll','choose','ship','rate','cat','dog','joke'],
  leveling:['level','rank','leaderboard','xp','setxp','leveling','reward','rewards'],
  economy:['balance','daily','work','beg','deposit','withdraw','pay','economy','inventory','shop','buy','richlist'],
  stars:['stars','starleaderboard','starconfig','starboard'],
  counters:['counter setup','counter remove','counter update'],
  notifications:['notifier add','notifier list','notifier remove','notifier enable','notifier disable','notifier test'],
  invites:['invites','invites-leaderboard','inviteconfig'],
  announcements:['announce','say','embed','poll','announce-embed'],
  roles:['role','autorole','reactionrole','levelrole','roleall'],
  welcome:['welcome','setwelcome','goodbye'],
  afk:['afk'],
  configuration:['permissions','perm','emoji','emoji-list','config','prefix','enable','disable']
 };
 const names={home:'🏠 Home',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',music:'🎧 Music',tickets:'🎫 Tickets',giveaways:'🎉 Giveaways',fun:'🎭 Fun',leveling:'📈 Leveling',economy:'💰 Economy',stars:'🌟 Stars',counters:'📊 Counters',notifications:'🔔 Notifications',invites:'🔗 Invites',announcements:'📢 Announcements',roles:'🎭 Roles',welcome:'👋 Welcome',afk:'💤 AFK',configuration:'⚙️ Configuration'};
 function help(cat='home'){
  if(!groups[cat])cat='home';
  const options=Object.keys(groups).map(k=>({label:names[k].replace(/^\S+\s/,''),value:k,emoji:names[k].split(' ')[0]}));
  const menu=new StringSelectMenuBuilder().setCustomId('lc_help_final_v2').setPlaceholder('✨ Select a command category').addOptions(options.slice(0,25));
  if(cat==='home')return {embeds:[new EmbedBuilder().setTitle('✨ LIGHTCORE • HELP CENTER').setDescription(`> ✨ **Prefix:** \`${P}\`\n> **Command groups:** **${Object.keys(groups).length}**\n\n${Object.keys(groups).map(k=>`${names[k]}  •  \`${P}help ${k}\``).join('\n')}\n\n> ➜ Select a category below.`).setColor(0x5865f2).setTimestamp()],components:[new ActionRowBuilder().addComponents(menu)]};
  const list=groups[cat].map(x=>`\`${P}${x}\``).join('  •  ');return {embeds:[new EmbedBuilder().setTitle(`${names[cat]} • COMMANDS`).setDescription(`> ✦ **${groups[cat].length}** commands\n\n${list}\n\n> ➜ Use \`${P}help\` to return to the command center.`).setColor(0x5865f2).setTimestamp()],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_help_final_v2_home').setLabel('Help Home').setEmoji('🏠').setStyle(ButtonStyle.Secondary))]};
 }
 const old=client.listeners('messageCreate').at(-1);if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();if(c==='help'||c==='h')return m.reply(help((a[0]||'home').toLowerCase()));return old(m)}catch(e){console.error('[HELP FINAL]',e)}})}
 client.on('interactionCreate',async i=>{try{if(i.isStringSelectMenu()&&i.customId==='lc_help_final_v2')return i.update(help(i.values[0]));if(i.isButton()&&i.customId==='lc_help_final_v2_home')return i.update(help('home'))}catch(e){console.error('[HELP INTERACTION]',e)}});
};
