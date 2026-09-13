const {EmbedBuilder,ActionRowBuilder,StringSelectMenuBuilder,ButtonBuilder,ButtonStyle,ApplicationCommandOptionType}=require('discord.js');

module.exports=function(client,prefix='.'){
 const P=prefix||'.';
 const groups={
  home:['help','ping','uptime','botinfo','invite','support','serverinfo','membercount','userinfo','avatar','roleinfo','channelinfo','servericon','permissions','config','prefix','enable','disable'],
  moderation:['ban','clearwarnings','kick','lock','lockdown','massrole','nick','purge','slowmode','softban','timeout','unban','unlock','unlockdown','unwarn','untimeout','warn','warnings'],
  security:['antiraid','antinuke','automod','filter','filter-add','filter-remove','honeypot','security','verify'],
  logging:['logdisable','logevents','logreset','logsettings','logsetup','logtest','setlog'],
  leveling:['leaderboard','level','leveling','levelrole','reward','rewards','rank','setxp','xp'],
  economy:['balance','bal','beg','daily','deposit','eco','economy','luck','pay','richlist','withdraw','work'],
  music:['clearqueue','connect','current','disconnect','join','leave','loop','move','musichelp','next','nowplaying','np','pause','p','play','q','queue','remove','repeat','resume','shuffle','skip','stop','unpause','vol','volume'],
  tickets:['application edit button','application edit color','application edit description','application edit title','application panel','application question add','application question edit','application question remove','application questions','application setup','apply','ticket','ticket add','ticket addcategory','ticket categories','ticket claim','ticket close','ticket delcategory','ticket editcategory','ticket editpanel button','ticket editpanel color','ticket editpanel description','ticket editpanel title','ticket logs','ticket open','ticket panel','ticket remove','ticket rename','ticket setup','ticket transcripts','ticket unclaim'],
  giveaways:['giveaway','gcreate'],
  fun:['8ball','cat','choose','coinflip','dog','eightball','joke','rate','reverse','roll','ship'],
  counters:['counter','counter autosetup','counter remove','counter setup','counter update'],
  memberstats:['memberstats','members','membersstats','messages','messages @user','serverstats','stat','stats','stats @user'],
  notifications:['notifier add','notifier disable','notifier enable','notifier list','notifier remove','notifier test'],
  invites:['inviteconfig','invites','invites-leaderboard'],
  announcements:['announce','announce-embed','embed','embedhelp','poll','say'],
  roles:['autorole','deleterole','levelrole','reactionrole','role','role duplicate','role give','role remove','roleall'],
  channels:['category delete','channel create','channel duplicate'],
  welcome:['goodbye','setwelcome','setwelcome-message','welcome'],
  autoresponder:['ar','autoresponder'],
  custom:['cc','cc-delete','cc-list','customcommand'],
  afk:['afk'],
  stars:['starboard','starconfig','starleaderboard','stars'],
  voice:['tempvoice','voice'],
  configuration:['config','disable','emoji','emoji-list','enable','permissions','perm','prefix'],
  utility:['channel','channelinfo','membercount','roleinfo','servericon','serverinfo','userinfo','userinfo-all'],
  reminders:['remind','reminders']
 };
 const names={
  home:'🏠 Home',moderation:'🛡️ Moderation',security:'🔐 Security',logging:'📋 Logging',leveling:'📈 Leveling',economy:'💰 Economy',music:'🎧 Music',tickets:'🎫 Tickets & Applications',giveaways:'🎉 Giveaways',fun:'🎭 Fun',counters:'📊 Counters',memberstats:'📈 Member & User Stats',notifications:'🔔 Notifications',invites:'🔗 Invites',announcements:'📢 Announcements',roles:'🎭 Roles',channels:'📁 Channels',welcome:'👋 Welcome',autoresponder:'🤖 Auto Responder',custom:'⚙️ Custom Commands',afk:'💤 AFK',stars:'⭐ Stars',voice:'🔊 Voice',configuration:'✨ Configuration',utility:'🛠️ Utility',reminders:'⏰ Reminders'
 };
 const order=Object.keys(groups);
 const icons=['✦','◆','◇','✧','●','◈'];
 const colors=[0x5865F2,0x7C3AED,0x06B6D4,0x3B82F6,0x8B5CF6,0x4F46E5];
 const color=()=>colors[Math.floor(Date.now()/8000)%colors.length];
 const cleanName=k=>names[k].replace(/^\S+\s/,'');
 const normalize=items=>[...new Set(items)].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:'base'}));
 for(const k of order)groups[k]=normalize(groups[k]);
 const total=order.reduce((n,k)=>n+groups[k].length,0);
 const footer={text:'LIGHTCORE  •  HELP CENTER'};
 const menu=()=>new StringSelectMenuBuilder().setCustomId('lc_help_category').setPlaceholder('✦  Browse command categories').addOptions(order.slice(0,25).map(k=>({label:cleanName(k).slice(0,100),value:k,emoji:names[k].split(' ')[0],description:`${groups[k].length} command${groups[k].length===1?'':'s'}`})));

 function home(){
  const body=order.map((k,i)=>`${icons[i%icons.length]} **${cleanName(k)}**  ·  \`${groups[k].length}\` command${groups[k].length===1?'':'s'}\n   └ \`${P}help ${k}\``).join('\n');
  return {embeds:[new EmbedBuilder()
   .setAuthor({name:'LIGHTCORE  •  COMMAND CENTER',iconURL:client.user?.displayAvatarURL?.({size:64})})
   .setTitle('✦ Help Center')
   .setDescription(`**Your all-in-one Discord command center.**\n\n> **Prefix**  \`${P}\`\n> **Categories**  \`${order.length}\`\n> **Commands indexed**  \`${total}\`\n\n${body}\n\n**HOW TO USE**\n> Select a category below. Every command is shown **one per line**, numbered and sorted in a consistent order.\n> Large categories use pages so no commands are hidden.`)
   .setColor(color()).setFooter(footer).setTimestamp()],components:[new ActionRowBuilder().addComponents(menu())]};
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
  const rows=[new ActionRowBuilder().addComponents(menu())];
  if(pages>1)rows.push(new ActionRowBuilder().addComponents(
   new ButtonBuilder().setCustomId(`lc_help_prev:${cat}:${page}`).setLabel('Previous').setEmoji('◀️').setStyle(ButtonStyle.Secondary).setDisabled(page===0),
   new ButtonBuilder().setCustomId('lc_help_home').setLabel('Home').setEmoji('🏠').setStyle(ButtonStyle.Primary),
   new ButtonBuilder().setCustomId(`lc_help_next:${cat}:${page}`).setLabel('Next').setEmoji('▶️').setStyle(ButtonStyle.Secondary).setDisabled(page>=pages-1)
  ));
  return {embeds:[new EmbedBuilder()
   .setAuthor({name:`LIGHTCORE  •  ${cleanName(cat).toUpperCase()}`,iconURL:client.user?.displayAvatarURL?.({size:64})})
   .setTitle(`${names[cat]}  ›  Command Index`)
   .setDescription(`**${items.length} commands**  ·  **Page ${page+1}/${pages}**\n\n${list}\n\n> ✦ One command per line\n> ✦ Alphabetically ordered for quick scanning\n> ✦ Use the dropdown to switch categories`)
   .setColor(color()).setFooter({text:'LIGHTCORE  •  COMMAND INDEX'}).setTimestamp()],components:rows};
 }

 function help(cat='home',page=0){return cat==='home'?home():category(cat,page);}
 const marker=Symbol.for('lightcore.helpFinalInstalled');if(client[marker])return;client[marker]=true;
 client[Symbol.for('lightcore.helpRenderer')]=help;

 const old=client.listeners('messageCreate').at(-1);
 if(old){
  client.removeListener('messageCreate',old);
  client.on('messageCreate',async m=>{try{
   if(m.author.bot||!m.guild)return;
   if(!m.content.startsWith(P))return old(m);
   const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();
   if(c==='help'||c==='h'){await m.reply(help((a[0]||'home').toLowerCase(),Number(a[1])||0));return}
   return old(m);
  }catch(e){console.error('[HELP ORDERED]',e)}});
 }

 client.once('ready',async()=>{
  try{
   const command={name:'help',description:'Open the LightCore Help Center',options:[
    {name:'category',description:'Choose a command category',type:ApplicationCommandOptionType.String,required:false,choices:order.slice(0,25).map(k=>({name:cleanName(k).slice(0,100),value:k}))},
    {name:'page',description:'Page number for the selected category',type:ApplicationCommandOptionType.Integer,required:false,min_value:1,max_value:50}
   ]};
   const commands=await client.application.commands.fetch();
   const existing=commands.find(c=>c.name==='help');
   if(existing)await existing.edit(command);else await client.application.commands.create(command);
   console.log('[SLASH] Registered /help without replacing existing application commands');
  }catch(e){console.error('[HELP SLASH REGISTER]',e?.stack||e)}
 });

 client.on('interactionCreate',async i=>{try{
  if(i.isChatInputCommand()&&i.commandName==='help'){
   const cat=i.options.getString('category')||'home';
   const page=Math.max(0,(i.options.getInteger('page')||1)-1);
   return i.reply(help(cat,page));
  }
  if(i.isStringSelectMenu()&&i.customId==='lc_help_category')return i.update(help(i.values[0],0));
  if(i.isButton()&&i.customId==='lc_help_home')return i.update(help('home',0));
  if(i.isButton()&&(i.customId.startsWith('lc_help_prev:')||i.customId.startsWith('lc_help_next:'))){const [action,cat,raw]=i.customId.split(':');const p=Number(raw)||0;return i.update(help(cat,action==='lc_help_prev'?p-1:p+1));}
 }catch(e){console.error('[HELP INTERACTION]',e);if(i.isRepliable()&&!i.replied&&!i.deferred)i.reply({content:'❌ The Help Center could not update.',ephemeral:true}).catch(()=>{});}});
};
