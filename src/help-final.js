const {EmbedBuilder,ActionRowBuilder,StringSelectMenuBuilder,ButtonBuilder,ButtonStyle}=require('discord.js');
module.exports=function(client,prefix='.'){
 const P=prefix||'.';
 const groups={
  home:['help','ping','uptime','botinfo','invite','support','serverinfo','membercount','userinfo','avatar','roleinfo','channelinfo','servericon'],
  moderation:['kick','ban','unban','softban','timeout','untimeout','warn','unwarn','warnings','clearwarnings','purge','lock','unlock','slowmode','nick','lockdown','unlockdown','massrole'],
  security:['automod','antiraid','antinuke','security','filter','filter-add','filter-remove','verify','honeypot'],
  logging:['logsetup','setlog','logdisable','logsettings','logevents','logtest','logreset'],
  leveling:['level','rank','xp','leaderboard','setxp','leveling','reward','rewards'],
  economy:['balance','bal','daily','work','beg','deposit','withdraw','pay','richlist','luck','eco'],
  music:['play','p','join','connect','leave','disconnect','pause','resume','unpause','skip','next','stop','queue','q','nowplaying','np','current','volume','vol','loop','repeat','shuffle','remove','move','clearqueue','musichelp'],
  tickets:['ticket','ticket setup','ticket panel','ticket categories','ticket addcategory','ticket editcategory','ticket delcategory','ticket editpanel title','ticket editpanel description','ticket editpanel color','ticket editpanel button','ticket open','ticket close','ticket claim','ticket unclaim','ticket add','ticket remove','ticket rename','ticket logs','ticket transcripts','application setup','application panel','application edit title','application edit description','application edit color','application edit button','application questions','application question add','application question remove','application question edit','apply'],
  giveaways:['giveaway','gcreate'],
  fun:['8ball','eightball','coinflip','roll','choose','ship','rate','cat','dog','joke','reverse'],
  counters:['counter','counter autosetup','counter setup','counter remove','counter update'],
  memberstats:['stats','stat','stats @user','serverstats','members','messages','messages @user','memberstats','membersstats'],
  notifications:['notifier add','notifier list','notifier remove','notifier enable','notifier disable','notifier test'],
  invites:['invites','invites-leaderboard','inviteconfig'],
  announcements:['announce','say','embed','embedhelp','poll','announce-embed'],
  roles:['role','role give','role remove','role duplicate','deleterole','autorole','reactionrole','levelrole','roleall'],
  channels:['channel create','channel duplicate','category delete'],
  welcome:['welcome','setwelcome','setwelcome-message','goodbye'],
  autoresponder:['autoresponder','ar'],
  custom:['customcommand','cc','cc-delete','cc-list'],
  afk:['afk'],
  stars:['stars','starleaderboard','starconfig','starboard'],
  voice:['tempvoice','voice'],
  configuration:['permissions','perm','emoji','emoji-list','config','prefix','enable','disable']
 };
 const names={home:'🏠 Home',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',leveling:'📈 Leveling',economy:'💰 Economy',music:'🎧 Music',tickets:'🎫 Tickets & Applications',giveaways:'🎉 Giveaways',fun:'🎭 Fun',counters:'📊 Counters',memberstats:'📈 Member & User Stats',notifications:'🔔 Notifications',invites:'🔗 Invites',announcements:'📢 Announcements',roles:'🎭 Roles',channels:'📁 Channels',welcome:'👋 Welcome',autoresponder:'🤖 Auto Responder',custom:'⚙️ Custom Commands',afk:'💤 AFK',stars:'⭐ Stars',voice:'🔊 Voice',configuration:'✨ Configuration'};
 const icons=['✦','◆','◇','✧','●','◈'];
 const colors=[0x5865F2,0x7C3AED,0x06B6D4,0x3B82F6,0x8B5CF6,0x4F46E5];
 const color=()=>colors[Math.floor(Date.now()/8000)%colors.length];
 const cleanName=k=>names[k].replace(/^\S+\s/,'');
 const allCats=Object.keys(groups);
 const total=allCats.reduce((n,k)=>n+groups[k].length,0);
 const footer={text:'LIGHTCORE  •  HELP CENTER'};
 const menu=()=>new StringSelectMenuBuilder().setCustomId('lc_help_category').setPlaceholder('✦  Browse command categories').addOptions(allCats.slice(0,25).map(k=>({label:cleanName(k),value:k,emoji:names[k].split(' ')[0],description:`${groups[k].length} command${groups[k].length===1?'':'s'}`})));
 function home(){
  const body=allCats.map((k,i)=>`${icons[i%icons.length]} **${cleanName(k)}**  ·  \`${groups[k].length}\` command${groups[k].length===1?'':'s'}\n   └ \`${P}help ${k}\``).join('\n');
  return {embeds:[new EmbedBuilder().setAuthor({name:'LIGHTCORE  •  COMMAND CENTER',iconURL:client.user?.displayAvatarURL?.({size:64})}).setTitle('✦ Help Center').setDescription(`**Your all-in-one Discord command center.**\n\n> **Prefix**  \`${P}\`\n> **Categories**  \`${allCats.length}\`\n> **Commands indexed**  \`${total}\`\n\n${body}\n\n**QUICK GUIDE**\nSelect a category below to view its complete command index.\n✨ Commands are displayed in their configured order, with pagination for large categories.`).setColor(color()).setFooter(footer).setTimestamp()],components:[new ActionRowBuilder().addComponents(menu())]};
 }
 function category(cat,page=0){
  if(!groups[cat])return home();
  const items=groups[cat];
  const pageSize=12;
  const pages=Math.max(1,Math.ceil(items.length/pageSize));
  page=Math.min(Math.max(Number(page)||0,0),pages-1);
  const start=page*pageSize;
  const current=items.slice(start,start+pageSize);
  const list=current.map((x,i)=>`${String(start+i+1).padStart(2,'0')}  ${icons[(start+i)%icons.length]}  \`${P}${x}\``).join('\n');
  const note=cat==='tickets'?`\n\n**STAFF FLOW**\n> 🛡️ Setup and configuration require the appropriate server permissions.\n> 🎫 Ticket actions follow the configured staff permissions.`:cat==='economy'?`\n\n**ECONOMY**\n> 💰 Member commands manage personal balances and rewards.\n> 🔐 Administrative economy controls depend on server configuration.`:'';
  const rows=[new ActionRowBuilder().addComponents(menu())];
  if(pages>1)rows.push(new ActionRowBuilder().addComponents(
   new ButtonBuilder().setCustomId(`lc_help_prev:${cat}:${page}`).setLabel('Previous').setEmoji('◀️').setStyle(ButtonStyle.Secondary).setDisabled(page===0),
   new ButtonBuilder().setCustomId('lc_help_home').setLabel('Home').setEmoji('🏠').setStyle(ButtonStyle.Primary),
   new ButtonBuilder().setCustomId(`lc_help_next:${cat}:${page}`).setLabel('Next').setEmoji('▶️').setStyle(ButtonStyle.Secondary).setDisabled(page>=pages-1)
  ));
  return {embeds:[new EmbedBuilder().setAuthor({name:`LIGHTCORE  •  ${cleanName(cat).toUpperCase()}`,iconURL:client.user?.displayAvatarURL?.({size:64})}).setTitle(`${names[cat]}  ›  Command Index`).setDescription(`**${items.length} commands**  ·  **Page ${page+1}/${pages}**\n\n${list}${note}\n\n> ✦ Commands are numbered and kept in the configured order.\n> ✦ Use the category menu to switch sections.`).setColor(color()).setFooter({text:'LIGHTCORE  •  COMMAND INDEX'}).setTimestamp()],components:rows};
 }
 function help(cat='home',page=0){return cat==='home'?home():category(cat,page);}
 const marker=Symbol.for('lightcore.helpFinalInstalled');if(client[marker])return;client[marker]=true;
 const old=client.listeners('messageCreate').at(-1);
 if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();if(c==='help'||c==='h'){await m.reply(help((a[0]||'home').toLowerCase(),Number(a[1])||0));return}return old(m)}catch(e){console.error('[HELP ORDERED]',e)}})}
 client.on('interactionCreate',async i=>{try{
  if(i.isStringSelectMenu()&&i.customId==='lc_help_category')return i.update(help(i.values[0],0));
  if(i.isButton()&&i.customId==='lc_help_home')return i.update(help('home',0));
  if(i.isButton()&&(i.customId.startsWith('lc_help_prev:')||i.customId.startsWith('lc_help_next:'))){const [action,cat,raw]=i.customId.split(':');const p=Number(raw)||0;return i.update(help(cat,action==='lc_help_prev'?p-1:p+1));}
 }catch(e){console.error('[HELP INTERACTION]',e);if(i.isRepliable()&&!i.replied&&!i.deferred)i.reply({content:'❌ The Help Center could not update.',ephemeral:true}).catch(()=>{});}});
};
