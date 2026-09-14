const fs=require('fs');
const path=require('path');
const {EmbedBuilder,ActionRowBuilder,ButtonBuilder,ButtonStyle,ModalBuilder,TextInputBuilder,TextInputStyle,PermissionFlagsBits}=require('discord.js');

module.exports=function attachCompetitionSuite(client,prefix='.'){
 const P=prefix||'.';
 const file=path.join(process.cwd(),'data','competition-suite.json');
 fs.mkdirSync(path.dirname(file),{recursive:true});
 let db={guilds:{}};
 try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{}
 if(!db||typeof db!=='object')db={guilds:{}};
 if(!db.guilds||typeof db.guilds!=='object')db.guilds={};
 const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const guild=id=>db.guilds[id]||(db.guilds[id]={leveling:{enabled:true,cooldown:60,xpMin:8,xpMax:15,rewards:{}},applications:{enabled:false,channel:null,reviewChannel:null,title:'Staff Application',description:'Apply by answering the questions below.',questions:['Why do you want to join the staff team?','What experience do you have?','How would you handle a difficult member?'],counter:0,applications:{}}});
 const embed=(title,description,color=0x5865f2)=>new EmbedBuilder().setTitle(title).setDescription(description).setColor(color).setTimestamp();
 const xpNeeded=l=>100+(l*l*50);
 const profile=(g,id)=>g.levels||(g.levels={});
 const getLevel=(g,id)=>profile(g,id)[id]||(profile(g,id)[id]={xp:0,level:1,total:0});
 const clean=(s,n=1000)=>String(s||'').slice(0,n);
 const isStaff=m=>m.member?.permissions?.has(PermissionFlagsBits.ManageGuild)||m.guild.ownerId===m.author.id;

 async function showLevel(m,target){
  const g=guild(m.guild.id),x=getLevel(g,target.id),need=xpNeeded(x.level);
  return m.reply({embeds:[embed('📈 Level Profile',`**User:** ${target}\n**Level:** ${x.level}\n**XP:** ${x.xp.toLocaleString()} / ${need.toLocaleString()}\n**Total XP:** ${x.total.toLocaleString()}\n**Progress:** ${Math.min(100,Math.floor(x.xp/need*100))}%`)]});
 }
 async function levelLeaderboard(m){
  const g=guild(m.guild.id),rows=Object.entries(g.levels||{}).sort((a,b)=>(b[1].level-a[1].level)||(b[1].total-a[1].total)).slice(0,10);
  return m.reply({embeds:[embed('🏆 Level Leaderboard',rows.length?rows.map((r,i)=>`**${i+1}.** <@${r[0]}> — Level **${r[1].level}** • ${r[1].total.toLocaleString()} XP`).join('\n'):'No XP recorded yet.')]});
 }
 async function setupApplications(m,g,args){
  if(!isStaff(m))return m.reply('❌ You need Manage Server to configure applications.');
  const sub=(args[0]||'').toLowerCase();
  if(sub==='enable'||sub==='on'){g.applications.enabled=true;save();return m.reply('✅ Applications enabled.');}
  if(sub==='disable'||sub==='off'){g.applications.enabled=false;save();return m.reply('✅ Applications disabled.');}
  if(sub==='channel'){
   const ch=m.mentions.channels.first();if(!ch)return m.reply(`Usage: ${P}application channel #channel`);g.applications.channel=ch.id;save();return m.reply(`✅ Application channel set to ${ch}.`);
  }
  if(sub==='review'){
   const ch=m.mentions.channels.first();if(!ch)return m.reply(`Usage: ${P}application review #channel`);g.applications.reviewChannel=ch.id;save();return m.reply(`✅ Review channel set to ${ch}.`);
  }
  if(sub==='question-add'){
   const q=args.slice(1).join(' ').trim();if(!q)return m.reply(`Usage: ${P}application question-add <question>`);if(g.applications.questions.length>=5)return m.reply('❌ Maximum 5 questions.');g.applications.questions.push(clean(q,300));save();return m.reply('✅ Application question added.');
  }
  if(sub==='question-remove'){
   const n=Number(args[1]);if(!Number.isInteger(n)||n<1||n>g.applications.questions.length)return m.reply(`Usage: ${P}application question-remove <number>`);g.applications.questions.splice(n-1,1);save();return m.reply('✅ Application question removed.');
  }
  if(sub==='questions')return m.reply({embeds:[embed('📝 Application Questions',g.applications.questions.map((q,i)=>`**${i+1}.** ${q}`).join('\n')||'No questions configured.')]});
  if(sub==='publish'){
   if(!g.applications.channel)return m.reply(`❌ Set a channel first: ${P}application channel #channel`);
   const ch=m.guild.channels.cache.get(g.applications.channel);if(!ch?.isTextBased())return m.reply('❌ Application channel no longer exists.');
   const row=new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('lc_apply_open').setLabel('Apply Now').setEmoji('📝').setStyle(ButtonStyle.Primary));
   await ch.send({embeds:[embed(`📝 ${g.applications.title}`,`${g.applications.description}\n\nClick **Apply Now** to start.`,0x5865f2)],components:[row]});
   return m.reply(`✅ Application panel published in ${ch}.`);
  }
  return m.reply({embeds:[embed('📝 Application Control Center',`**Status:** ${g.applications.enabled?'Enabled':'Disabled'}\n**Apply channel:** ${g.applications.channel?`<#${g.applications.channel}>`:'Not set'}\n**Review channel:** ${g.applications.reviewChannel?`<#${g.applications.reviewChannel}>`:'Not set'}\n**Questions:** ${g.applications.questions.length}\n\n**Setup**\n\`${P}application enable\`\n\`${P}application channel #channel\`\n\`${P}application review #channel\`\n\`${P}application question-add <question>\`\n\`${P}application question-remove <number>\`\n\`${P}application questions\`\n\`${P}application publish\``)]});
 }

 client.on('messageCreate',async m=>{
  try{
   if(m.author.bot||!m.guild||!m.content.startsWith(P))return;
   const p=m.content.slice(P.length).trim().split(/\s+/),root=(p.shift()||'').toLowerCase(),g=guild(m.guild.id);
   if(root==='level'||root==='rank'||root==='xp'){
    const target=m.mentions.users.first()||m.author;
    if(root==='xp'&&p[0]==='set'){
     if(!isStaff(m))return m.reply('❌ You need Manage Server to set XP.');
     const n=Math.max(0,Number(p[1]));if(!Number.isFinite(n))return m.reply(`Usage: ${P}xp set <amount> [@user]`);
     const t=m.mentions.users.first()||m.author,x=getLevel(g,t.id);x.xp=n;x.total=n;while(x.xp>=xpNeeded(x.level)){x.xp-=xpNeeded(x.level);x.level++;}save();return m.reply(`✅ ${t}'s XP set to **${n}**.`);
    }
    return showLevel(m,target);
   }
   if(root==='leaderboard'||root==='levels')return levelLeaderboard(m);
   if(root==='leveling'){
    if(!isStaff(m))return m.reply('❌ You need Manage Server.');
    const sub=(p.shift()||'').toLowerCase();
    if(sub==='on'||sub==='enable'){g.leveling.enabled=true;save();return m.reply('✅ Leveling enabled.');}
    if(sub==='off'||sub==='disable'){g.leveling.enabled=false;save();return m.reply('✅ Leveling disabled.');}
    if(sub==='cooldown'){const n=Math.max(5,Math.min(3600,Number(p[0])));if(!Number.isFinite(n))return m.reply(`Usage: ${P}leveling cooldown <seconds>`);g.leveling.cooldown=n;save();return m.reply(`✅ Level cooldown set to **${n}s**.`);}
    return m.reply({embeds:[embed('📈 Leveling Settings',`Status: **${g.leveling.enabled?'Enabled':'Disabled'}**\nCooldown: **${g.leveling.cooldown}s**\nXP per message: **${g.leveling.xpMin}-${g.leveling.xpMax}**\n\n\`${P}leveling on|off\`\n\`${P}leveling cooldown <seconds>\``)]});
   }
   if(root==='application'||root==='applications'||root==='apply'){
    if(root==='apply'){
     if(!g.applications.enabled)return m.reply('❌ Applications are currently closed.');
     if(g.applications.channel&&m.channel.id!==g.applications.channel)return m.reply(`❌ Please apply in <#${g.applications.channel}>.`);
     const first=g.applications.questions[0]||'Why should we accept you?';
     const modal=new ModalBuilder().setCustomId('lc_apply_modal_1').setTitle(clean(g.applications.title,45));
     modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q0').setLabel(clean(first,45)).setStyle(TextInputStyle.Paragraph).setRequired(true).setMaxLength(900)));
     return m.showModal(modal);
    }
    return setupApplications(m,g,p);
   }
   if(root==='8ball'||root==='eightball'){
    const q=p.join(' ').trim();if(!q)return m.reply(`Usage: ${P}8ball <question>`);
    const answers=['Absolutely.','Most likely.','Yes.','Signs point to yes.','Ask again later.','Probably not.','No.','Very doubtful.'];
    return m.reply({embeds:[embed('🎱 8Ball',`**Question:** ${clean(q)}\n**Answer:** ${answers[Math.floor(Math.random()*answers.length)]}`)]});
   }
   if(root==='roll'){
    const sides=Math.max(2,Math.min(1000,Number(p[0])||6));return m.reply(`🎲 You rolled **${1+Math.floor(Math.random()*sides)}** / ${sides}`);
   }
   if(root==='choose'){
    const opts=p.join(' ').split('|').map(x=>x.trim()).filter(Boolean);if(opts.length<2)return m.reply(`Usage: ${P}choose option 1 | option 2 | option 3`);return m.reply(`🎯 I choose **${opts[Math.floor(Math.random()*opts.length)]}**`);
   }
   if(root==='rate'){
    const text=p.join(' ').trim();if(!text)return m.reply(`Usage: ${P}rate <thing>`);return m.reply(`⭐ **${clean(text)}** gets **${Math.floor(Math.random()*101)}/100**.`);
   }
   if(root==='reverse')return m.reply(`🔄 ${p.join(' ').split('').reverse().join('')||'Nothing to reverse.'}`);
   if(root==='serverinfo'||root==='userinfo'||root==='avatar'||root==='channelinfo'){
    if(root==='serverinfo')return m.reply({embeds:[embed(`🏠 ${m.guild.name}`,`Owner: <@${m.guild.ownerId}>\nMembers: **${m.guild.memberCount}**\nChannels: **${m.guild.channels.cache.size}**\nRoles: **${m.guild.roles.cache.size}**\nBoosts: **${m.guild.premiumSubscriptionCount||0}**`)]});
    if(root==='channelinfo')return m.reply({embeds:[embed(`📺 #${m.channel.name}`,`ID: \`${m.channel.id}\`\nType: **${m.channel.type}**\nPosition: **${m.channel.position}**`)]});
    const u=m.mentions.users.first()||m.author;return m.reply({embeds:[embed(`👤 ${u.username}`,`ID: \`${u.id}\`\nCreated: <t:${Math.floor(u.createdTimestamp/1000)}:R>`)]});
   }
  }catch(e){console.error('[COMPETITION-SUITE]',e?.stack||e)}
 });

 client.on('messageCreate',async m=>{
  try{
   if(m.author.bot||!m.guild||!m.content||!m.content.startsWith(P))return;
   const root=m.content.slice(P.length).trim().split(/\s+/)[0]?.toLowerCase();
   if(!['level','rank','xp','leaderboard','levels','leveling'].includes(root))return;
   const g=guild(m.guild.id);if(!g.leveling.enabled)return;
   const now=Date.now(),x=getLevel(g,m.author.id);x.last=x.last||0;
   if(now-x.last<g.leveling.cooldown*1000)return;
   x.last=now;const gain=g.leveling.xpMin+Math.floor(Math.random()*(g.leveling.xpMax-g.leveling.xpMin+1));x.xp+=gain;x.total+=gain;
   let up=false;while(x.xp>=xpNeeded(x.level)){x.xp-=xpNeeded(x.level);x.level++;up=true;}
   save();
   if(up)m.channel.send({embeds:[embed('🎉 Level Up!',`${m.author} reached **Level ${x.level}**!`)]}).catch(()=>{});
  }catch(e){console.error('[LEVELING]',e?.stack||e)}
 });

 client.on('interactionCreate',async i=>{
  try{
   if(i.isButton()&&i.customId==='lc_apply_open'){
    const g=guild(i.guild.id);if(!g.applications.enabled)return i.reply({content:'❌ Applications are closed.',ephemeral:true});
    const modal=new ModalBuilder().setCustomId('lc_apply_modal_1').setTitle(clean(g.applications.title,45));
    const q=g.applications.questions[0]||'Why should we accept you?';
    modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('q0').setLabel(clean(q,45)).setStyle(TextInputStyle.Paragraph).setRequired(true).setMaxLength(900)));
    return i.showModal(modal);
   }
   if(i.isModalSubmit()&&i.customId==='lc_apply_modal_1'){
    const g=guild(i.guild.id);g.applications.counter++;const id=String(g.applications.counter).padStart(4,'0');
    const answer=i.fields.getTextInputValue('q0');g.applications.applications[id]={user:i.user.id,answer,status:'pending',created:Date.now()};save();
    const review=g.applications.reviewChannel?i.guild.channels.cache.get(g.applications.reviewChannel):null;
    if(review?.isTextBased())await review.send({embeds:[embed(`📝 Application #${id}`,`**Applicant:** ${i.user} (\`${i.user.id}\`)\n**Question 1:** ${g.applications.questions[0]}\n**Answer:** ${clean(answer,1500)}\n\nUse the application ID **${id}** for review.`)]}).catch(()=>{});
    return i.reply({content:`✅ Application **#${id}** submitted. Good luck!`,ephemeral:true});
   }
  }catch(e){console.error('[APPLICATIONS]',e?.stack||e)}
 });

 console.log('[COMPETITION] Economy-adjacent utilities + fun + leveling + guided applications loaded.');
};
