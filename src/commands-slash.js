const { REST, Routes, EmbedBuilder, ActionRowBuilder, StringSelectMenuBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

const PREFIX='.';
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
const icons=['✨','⚡','🌟','💫','🔷','🔹'];
function panel(cat='home'){
 if(!groups[cat])cat='home';
 const options=Object.keys(groups).map(k=>({label:names[k].replace(/^\S+\s/,''),value:k,emoji:names[k].split(' ')[0]}));
 const color=[0x5865f2,0x7c3aed,0x2563eb,0x06b6d4][Math.floor(Date.now()/5000)%4];
 if(cat==='home') return {embeds:[new EmbedBuilder().setTitle(`${icons[Math.floor(Date.now()/5000)%icons.length]} LIGHTCORE • COMMAND CENTER`).setDescription(`> **Prefix:** \`${PREFIX}\`\n> **Categories:** **${Object.keys(groups).length}**\n> **Total listed commands:** **${Object.values(groups).reduce((n,x)=>n+x.length,0)}**\n\n${Object.keys(groups).map((k,i)=>`${icons[i%icons.length]} **${names[k]}**\n   └─ Use \`/commands ${k}\` or \`${PREFIX}help ${k}\``).join('\n')}\n\n> 📌 Select a category below to see **every command, one per line**.`).setColor(color).setTimestamp()],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('lc_commands_category').setPlaceholder('📂 Select a category').addOptions(options))]};
 const list=groups[cat].map((x,i)=>`${icons[i%icons.length]} \`${PREFIX}${x}\``).join('\n');
 return {embeds:[new EmbedBuilder().setTitle(`${names[cat]} • ALL COMMANDS`).setDescription(`> **${groups[cat].length} commands in this category**\n\n${list}\n\n> 🔙 Use \`/commands\` for the main command center.`).setColor(color).setTimestamp()],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_commands_home').setLabel('Command Center').setEmoji('🏠').setStyle(ButtonStyle.Secondary))]};
}

module.exports=function install(client){
 const marker=Symbol.for('lightcore.commandsSlashInstalled');
 if(client[marker])return;
 client[marker]=true;
 client.once('ready',async()=>{
  try{
   const rest=new REST({version:'10'}).setToken(process.env.DISCORD_TOKEN);
   await rest.put(Routes.applicationCommands(client.user.id),{body:[{name:'commands',description:'Open the LightCore command center',options:[{name:'category',description:'Show every command in a category',type:3,required:false,choices:Object.keys(groups).map(k=>({name:names[k].replace(/^\S+\s/,''),value:k}))}]}]});
   console.log('[SLASH] Registered only /commands globally.');
  }catch(error){console.error('[SLASH REGISTER] Failed:',error?.stack||error);}
 });
 client.on('interactionCreate',async i=>{
  try{
   if(i.isChatInputCommand()&&i.commandName==='commands')return i.reply(panel(i.options.getString('category')||'home'));
   if(i.isStringSelectMenu()&&i.customId==='lc_commands_category')return i.update(panel(i.values[0]));
   if(i.isButton()&&i.customId==='lc_commands_home')return i.update(panel('home'));
  }catch(error){console.error('[COMMANDS INTERACTION]',error?.stack||error);}
 });
};
