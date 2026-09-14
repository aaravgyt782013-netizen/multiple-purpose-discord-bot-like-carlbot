const fs=require('fs'),path=require('path');
const attachEmbedTheme=require('./embed-theme.js'),attach=require('./feature-pack.js'),attachServerFeatures=require('./server-features.js'),attachNotifier=require('./notifier.js'),attachUltimate=require('./ultimate-features.js'),attachFinalSuite=require('./final-suite.js'),attachMusic=require('./music.js'),attachCounterAutosetup=require('./counter-autosetup.js'),attachTemplateVoice=require('./template-voice.js'),attachRaidShield=require('./raid-shield.js'),attachGlobalEconomy=require('./global-economy.js'),attachEconomyPlus=require('./economy-plus.js'),attachCommunitySuite=require('./community-suite.js'),attachManagementSuite=require('./management-suite.js'),attachMembersStats=require('./members-stats.js'),attachTicketSuite=require('./ticket-suite-v2.js'),attachCoreUtilities=require('./core-utilities.js'),attachHelpFinal=require('./help-final.js'),attachAdvancedLogging=require('./advanced-logging.js'),attachGiveaways=require('./giveaway-system.js'),attachInvites=require('./invite-tracker.js'),attachCompetitionSuite=require('./competition-suite.js'),attachProSuite=require('./pro-suite.js');
module.exports=function(bot){
 if(!bot?.client)throw Error('LightCore client unavailable');
 const c=bot.client;
 attachEmbedTheme(c);
 const dataDir=path.join(process.cwd(),'data'),file=path.join(dataDir,'database.json');fs.mkdirSync(dataDir,{recursive:true});if(!fs.existsSync(file))fs.writeFileSync(file,'{}');
 let db={};try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}')}catch{db={}}
 const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
 const fresh=()=>({featurePack:{ticketCategory:null,ticketStaffRole:null,rr:{},temp:{category:null,creator:null},welcome:null,goodbye:null,filters:[],autorole:null,raid:{enabled:false},nuke:{enabled:false}},custom:{},reminders:[]});
 const gd=id=>{const d=db[id]||(db[id]=fresh()),f=fresh();for(const k of Object.keys(f))if(d[k]===undefined)d[k]=f[k];return d};
 const original=c.listeners('messageCreate')[0];if(original)c.removeListener('messageCreate',original);
 // Prevent accidental duplicate replies from legacy listeners while keeping intentional follow-ups possible.
 c.prependListener('messageCreate',m=>{
   if(m.author?.bot)return;
   if(!m.__lightcoreReplyGuard){
     m.__lightcoreReplyGuard=true;
     const reply=m.reply.bind(m);
     let replied=false;
     m.reply=async(...args)=>{if(replied)return null;replied=true;return reply(...args)};
   }
 });
 // One active implementation per feature. The old guided-ticket listener was a second ticket router
 // using the same custom IDs/data as ticket-suite-v2, which caused duplicate ticket responses/interactions.
 attach(c,db,save,gd,'.');attachServerFeatures(c,'.');attachNotifier(c,'.');attachUltimate(c,'.');attachFinalSuite(c,'.');attachMusic(c,'.');attachCounterAutosetup(c,'.');attachTemplateVoice(c,'.');attachRaidShield(c,'.');attachGlobalEconomy(c,'.');attachEconomyPlus(c,'.');attachCommunitySuite(c,'.');attachManagementSuite(c,'.');attachMembersStats(c,'.');attachTicketSuite(c,'.');attachCoreUtilities(c,'.');attachHelpFinal(c,'.');attachAdvancedLogging(c,'.');attachGiveaways(c,'.');attachInvites(c,'.');attachCompetitionSuite(c,'.');attachProSuite(c,'.');
 // Single fallback router. Dedicated modules own help, music, stats and tickets.
 const core=new Set('ping botinfo invite kick ban unban timeout untimeout warn warnings clearwarnings purge lock unlock slowmode nick lockdown unlockdown softban unwarn massrole serverinfo userinfo avatar roleinfo channelinfo membercount servericon permissions channel announce say embed poll announce-embed customcommand cc cc-delete cc-list remind reminders'.split(/\s+/));
 c.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild||!m.content.startsWith('.'))return;const parts=m.content.slice(1).trim().split(/\s+/),name=(parts.shift()||'').toLowerCase();if(!core.has(name))return;await bot.cmd?.(m,[name,...parts].join(' '));}catch(e){console.error('[CORE ROUTER]',e?.stack||e)}});
 // Guard duplicate interaction responses from overlapping legacy interaction listeners.
 c.prependListener('interactionCreate',i=>{
   if(i.__lightcoreInteractionGuard)return;
   i.__lightcoreInteractionGuard=true;
   for(const method of ['reply','update','deferReply','showModal']){
     if(typeof i[method]!=='function')continue;
     const fn=i[method].bind(i);i[method]=async(...args)=>{if(i.__lightcoreResponded)return null;i.__lightcoreResponded=true;return fn(...args)};
   }
 });
 console.log('[FEATURES] LightCore loaded with single-response guards | prefix .');
};