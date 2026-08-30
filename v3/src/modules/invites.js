const { EmbedBuilder } = require('discord.js');

function ensure(db) {
  db.exec(`CREATE TABLE IF NOT EXISTS invite_stats (guild TEXT, user TEXT, regular INTEGER DEFAULT 0, fake INTEGER DEFAULT 0, left_count INTEGER DEFAULT 0, bonus INTEGER DEFAULT 0, PRIMARY KEY(guild,user)); CREATE TABLE IF NOT EXISTS invite_cache (guild TEXT, code TEXT, inviter TEXT, uses INTEGER DEFAULT 0, PRIMARY KEY(guild,code));`);
}

async function cacheGuild(guild, db) {
  if (!guild.members.me?.permissions.has('ManageGuild')) return;
  const invites = await guild.invites.fetch().catch(() => null);
  if (!invites) return;
  const tx = db.transaction(() => {
    for (const inv of invites.values()) {
      db.prepare(`INSERT INTO invite_cache(guild,code,inviter,uses) VALUES(?,?,?,?) ON CONFLICT(guild,code) DO UPDATE SET inviter=excluded.inviter,uses=excluded.uses`).run(guild.id, inv.code, inv.inviter?.id || '', inv.uses || 0);
    }
  }); tx();
}

async function identify(guild, db) {
  const before = db.prepare('SELECT code,uses,inviter FROM invite_cache WHERE guild=?').all(guild.id);
  await cacheGuild(guild, db);
  const after = db.prepare('SELECT code,uses,inviter FROM invite_cache WHERE guild=?').all(guild.id);
  return after.find(a => (a.uses || 0) > (before.find(b => b.code === a.code)?.uses || 0));
}

async function onJoin(member, db) {
  const hit = await identify(member.guild, db);
  if (!hit?.inviter) return null;
  const age = Date.now() - member.user.createdTimestamp;
  const fake = age < 7 * 24 * 60 * 60 * 1000;
  db.prepare(`INSERT INTO invite_stats(guild,user,regular,fake,left_count,bonus) VALUES(?,?,?,0,0,0) ON CONFLICT(guild,user) DO UPDATE SET regular=regular+excluded.regular,fake=fake+excluded.fake`).run(member.guild.id, hit.inviter, fake ? 0 : 1, fake ? 1 : 0);
  return { inviter: hit.inviter, fake, code: hit.code };
}

function onLeave(member, db) {
  const row = db.prepare('SELECT user FROM invite_stats WHERE guild=? AND regular>0 ORDER BY regular DESC').get(member.guild.id);
  if (!row) return;
  db.prepare('UPDATE invite_stats SET left_count=left_count+1 WHERE guild=? AND user=?').run(member.guild.id, row.user);
}

async function command(i, name, db) {
  if (name === 'invites') {
    const user = i.options.getUser?.('user') || i.user;
    const r = db.prepare('SELECT * FROM invite_stats WHERE guild=? AND user=?').get(i.guildId, user.id) || {regular:0,fake:0,left_count:0,bonus:0};
    return i.reply({embeds:[new EmbedBuilder().setTitle(`📨 Invites • ${user.tag}`).setDescription(`**Regular:** ${r.regular}\n**Fake:** ${r.fake}\n**Left:** ${r.left_count}\n**Bonus:** ${r.bonus}\n**Total:** ${r.regular+r.fake+r.bonus}`).setColor(0x5865f2)]});
  }
  if (name === 'invitetop' || name === 'inviteleaderboard') {
    const rows = db.prepare('SELECT user,regular,fake,left_count,bonus,(regular+fake+bonus) total FROM invite_stats WHERE guild=? ORDER BY total DESC LIMIT 10').all(i.guildId);
    return i.reply({embeds:[new EmbedBuilder().setTitle('🏆 Invite Leaderboard').setDescription(rows.map((r,n)=>`**${n+1}.** <@${r.user}> — ${r.total} total (${r.regular} regular)`).join('\n') || 'No invite data yet.').setColor(0x5865f2)]});
  }
}
module.exports={ensure,cacheGuild,onJoin,onLeave,command};
