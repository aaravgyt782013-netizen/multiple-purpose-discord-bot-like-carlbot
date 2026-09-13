const { ActivityType } = require('discord.js');

module.exports = function attachLiveStats(client){
  const update = () => {
    const guilds = client.guilds.cache.size;
    const users = client.guilds.cache.reduce((total, guild) => total + (guild.memberCount || 0), 0);
    const channels = client.channels.cache.size;
    const ping = Math.max(0, Math.round(client.ws.ping || 0));
    const activities = [
      { name: `${guilds.toLocaleString()} servers`, type: ActivityType.Watching },
      { name: `${users.toLocaleString()} users`, type: ActivityType.Watching },
      { name: `${channels.toLocaleString()} channels`, type: ActivityType.Watching },
      { name: `${ping}ms latency`, type: ActivityType.Watching }
    ];
    const activity = activities[Math.floor(Date.now() / 15000) % activities.length];
    client.user?.setPresence({
      status: 'online',
      activities: [activity]
    });
    console.log(`[STATS] Watching: ${activity.name} | servers=${guilds} users=${users} channels=${channels} ping=${ping}ms`);
  };

  client.once('ready', () => {
    update();
    setInterval(update, 15000).unref();
  });
};
