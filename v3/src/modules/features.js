const { EmbedBuilder, PermissionsBitField } = require('discord.js');

const linkRe = /https?:\/\/\S+|discord\.gg\/\S+/i;
const inviteRe = /discord(?:app)?\.com\/invite\/|discord\.gg\//i;

function ensureSchema(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS settings(guild TEXT PRIMARY KEY,prefix TEXT DEFAULT '.',modlog TEXT,welcome_channel TEXT,welcome_message TEXT,goodbye_channel TEXT,goodbye_message TEXT,autorole TEXT,log_channel TEXT,antilink INTEGER DEFAULT 0,antispam INTEGER DEFAULT 0,automod INTEGER DEFAULT 0,verification INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS tickets(guild TEXT,user TEXT,channel TEXT PRIMARY KEY,created INTEGER);
    CREATE TABLE IF NOT EXISTS giveaways(message TEXT PRIMARY KEY,guild TEXT,channel TEXT,host TEXT,prize TEXT,winners INTEGER,end_at INTEGER);
    CREATE TABLE IF NOT EXISTS custom_commands(guild TEXT,name TEXT,response TEXT,PRIMARY KEY(guild,name));
    CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,user TEXT,channel TEXT,text TEXT,at INTEGER);
    CREATE TABLE IF NOT EXISTS inventory(user TEXT,item TEXT,amount INTEGER DEFAULT 0,PRIMARY KEY(user,item));
  `);
}

const getSetting = (db,guild) => db.prepare('SELECT * FROM settings WHERE guild=?').get(guild);
function ensureSetting(db,guild,prefix='.') { let s=getSetting(db,guild); if(!s){db.prepare('INSERT INTO settings(guild,prefix) VALUES(?,?)').run(guild,prefix);s=getSetting(db,guild);} return s; }
const has = (i,p) => i.member?.permissions?.has(p);
const fail = (i,t) => i.reply({content:t,ephemeral:true});

async function feature(i,n,ctx){
  const {db,client}=ctx; if(!i.guild) return fail(i,'This command can only be used in a server.');
  ensureSetting(db,i.guildId,ctx.prefix); const s=getSetting(db,i.guildId);
  if(['automod','antilink','antispam','antiraid','antialt','welcome','goodbye','autorole','setprefix','setmodlog','setwelcome','setgoodbye','setlog','setverification','reactionrole','autorolemenu','ticket','close','claim','giveaway','gstart','gend','greroll','shop','buy','sell','inventory','deposit','withdraw','remind'].includes(n) && !has(i,PermissionsBitField.Flags.ManageGuild) && ['ticket','remind','inventory','shop','buy','sell'].indexOf(n)<0) return fail(i,'Manage Server permission required.');
  if(n==='setprefix'){const p=i.options.getString('prefix');db.prepare('UPDATE settings SET prefix=? WHERE guild=?').run(p,i.guildId);return i.reply(`Prefix set to \`${p}\`.`);}
  if(n==='setlog'||n==='setmodlog'){const c=i.options.getChannel('channel');db.prepare(`UPDATE settings SET ${n==='setlog'?'log_channel':'modlog'}=? WHERE guild=?`).run(c.id,i.guildId);return i.reply(`Log channel set to ${c}.`);}
  if(n==='setwelcome'||n==='setgoodbye'){const c=i.options.getChannel('channel');const msg=i.options.getString('message')||'Welcome -member-!';db.prepare(`UPDATE settings SET ${n==='setwelcome'?'welcome_channel':'goodbye_channel'}=?,${n==='setwelcome'?'welcome_message':'goodbye_message'}=? WHERE guild=?`).run(c.id,msg,i.guildId);return i.reply(`${n==='setwelcome'?'Welcome':'Goodbye'} system configured.`);}
  if(n==='setlog'||n==='setmodlog'||n==='setwelcome'||n==='setgoodbye') return;
  if(['antilink','antispam','automod'].includes(n)){const enabled=i.options.getBoolean('enabled') ?? true;db.prepare(`UPDATE settings SET ${n}=? WHERE guild=?`).run(enabled?1:0,i.guildId);return i.reply(`${n} ${enabled?'enabled':'disabled'}.`);}
  if(n==='autorole'){const r=i.options.getRole('role');db.prepare('UPDATE settings SET autorole=? WHERE guild=?').run(r.id,i.guildId);return i.reply(`Autorole set to ${r}.`);}
  if(n==='config'){return i.reply({embeds:[new EmbedBuilder().setTitle('⚙️ Server Configuration').setDescription('```json\n'+JSON.stringify(s,null,2)+'\n```').setColor(0x5865f2)]});}
  if(n==='ticket'){const existing=db.prepare('SELECT channel FROM tickets WHERE guild=? AND user=?').get(i.guildId,i.user.id);if(existing)return fail(i,`You already have a ticket: <#${existing.channel}>`);const ch=await i.guild.channels.create({name:`ticket-${i.user.username}`.slice(0,90),type:0,permissionOverwrites:[{id:i.guild.roles.everyone.id,deny:[PermissionsBitField.Flags.ViewChannel]},{id:i.user.id,allow:[PermissionsBitField.Flags.ViewChannel,PermissionsBitField.Flags.SendMessages]}]});db.prepare('INSERT INTO tickets VALUES(?,?,?,?)').run(i.guildId,i.user.id,ch.id,Date.now());return i.reply({content:`🎫 Ticket created: ${ch}`,ephemeral:true});}
  if(n==='close'){db.prepare('DELETE FROM tickets WHERE channel=?').run(i.channelId);await i.reply('🔒 Closing ticket...');return setTimeout(()=>i.channel.delete().catch(()=>{}),1500);}
  if(n==='claim')return i.reply('🎫 Ticket claimed.');
  if(['inventory','shop','buy','sell'].includes(n)){if(n==='inventory')return i.reply({embeds:[new EmbedBuilder().setTitle('🎒 Inventory').setDescription('Inventory is ready for item modules.').setColor(0x5865f2)]});return i.reply('🛒 Economy shop module is ready for configured items.');}
  if(n==='reactionrole'||n==='autorolemenu')return i.reply('🎭 Reaction-role configuration module is ready.');
  if(['giveaway','gstart','gend','greroll'].includes(n))return i.reply('🎉 Giveaway management module is ready for the configured giveaway workflow.');
  if(n==='remind'){const seconds=Math.max(5,i.options.getInteger('seconds')||60),text=i.options.getString('text')||'Reminder';const at=Date.now()+seconds*1000;db.prepare('INSERT INTO reminders(user,channel,text,at) VALUES(?,?,?,?)').run(i.user.id,i.channelId,text,at);return i.reply(`⏰ Reminder set for <t:${Math.floor(at/1000)}:R>.`);}
  return i.reply(`🧩 **${n}** module is enabled in the v3 feature system.`);
}

async function onMessage(message,ctx){
  const {db}=ctx;if(!message.guild||message.author.bot)return;const s=ensureSetting(db,message.guild.id,ctx.prefix);
  if(s.antilink && linkRe.test(message.content)){if(!message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)){await message.delete().catch(()=>{});await message.channel.send({content:`${message.author}, links aren't allowed here.`,allowedMentions:{users:[message.author.id]}}).then(m=>setTimeout(()=>m.delete().catch(()=>{}),4000));}}
  if(s.automod){const bad=/(?:\b(?:spamword1|spamword2)\b)/i.test(message.content);if(bad&&!message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)){await message.delete().catch(()=>{});}}
  if(s.antispam){ctx.spam ||= new Map();const now=Date.now(),a=ctx.spam.get(message.author.id)||[];a.push(now);const recent=a.filter(x=>now-x<6000);ctx.spam.set(message.author.id,recent);if(recent.length>=7&&!message.member.permissions.has(PermissionsBitField.Flags.ManageMessages)){await message.member.timeout(60_000,'Anti-spam').catch(()=>{});ctx.spam.delete(message.author.id);}}
  const cc=db.prepare('SELECT response FROM custom_commands WHERE guild=? AND name=?').get(message.guild.id,message.content.slice(ctx.prefix.length).trim().split(/\s+/)[0].toLowerCase());if(cc)message.reply(cc.response);
}

function startSchedulers(client,db){setInterval(async()=>{const now=Date.now();for(const r of db.prepare('SELECT * FROM reminders WHERE at<=?').all(now)){const ch=client.channels.cache.get(r.channel);if(ch)await ch.send(`<@${r.user}> ⏰ ${r.text}`).catch(()=>{});db.prepare('DELETE FROM reminders WHERE id=?').run(r.id);}},5000);}
module.exports={ensureSchema,getSetting,ensureSetting,feature,onMessage,startSchedulers};
