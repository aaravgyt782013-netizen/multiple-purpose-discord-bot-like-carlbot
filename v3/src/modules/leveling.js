function xpFor(level){return 100+level*75}
function addXP(db,guild,user,amount){let r=db.prepare('SELECT * FROM xp WHERE guild=? AND user=?').get(guild,user);if(!r){db.prepare('INSERT INTO xp VALUES(?,?,?,?)').run(guild,user,0,0);r=db.prepare('SELECT * FROM xp WHERE guild=? AND user=?').get(guild,user)}let xp=r.xp+amount,level=r.level,up=false;while(xp>=xpFor(level)){xp-=xpFor(level);level++;up=true}db.prepare('UPDATE xp SET xp=?,level=? WHERE guild=? AND user=?').run(xp,level,guild,user);return {xp,level,up}}
const cooldown=new Map();
async function onMessage(m,db){if(!m.guild||m.author.bot)return;const key=`${m.guild.id}:${m.author.id}`,now=Date.now();if(now-(cooldown.get(key)||0)<60000)return;cooldown.set(key,now);const r=addXP(db,m.guild.id,m.author.id,Math.floor(Math.random()*11)+10);if(r.up)await m.channel.send(`🎉 ${m.author} reached **Level ${r.level}**!`).catch(()=>{})}
module.exports={addXP,onMessage,xpFor};
