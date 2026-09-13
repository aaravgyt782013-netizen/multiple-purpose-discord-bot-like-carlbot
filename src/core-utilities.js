const {EmbedBuilder}=require('discord.js');

module.exports=function attachCoreUtilities(client,prefix='.'){
 const P=prefix||'.';
 const format=ms=>{
  ms=Math.max(0,Number(ms)||0);
  const s=Math.floor(ms/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60),sec=s%60;
  return `${d}d ${h}h ${m}m ${sec}s`;
 };
 const uptimeEmbed=()=>new EmbedBuilder()
  .setTitle('⏱️ LightCore • Uptime')
  .setDescription(`**Bot Uptime**\n> \`${format(client.uptime)}\`\n\n**WebSocket Ping**\n> \`${client.ws?.ping??'N/A'}ms\`\n\n**Status**\n> 🟢 Online and operational`)
  .setColor(0x5865F2)
  .setFooter({text:'LIGHTCORE • SYSTEM STATUS'})
  .setTimestamp();

 const marker=Symbol.for('lightcore.uptimeInstalled');
 if(client[marker])return;
 client[marker]=true;

 const old=client.listeners('messageCreate').at(-1);
 if(old){
  client.removeListener('messageCreate',old);
  client.on('messageCreate',async m=>{
   try{
    if(m.author.bot||!m.guild)return;
    if(!m.content.startsWith(P))return old(m);
    const a=m.content.slice(P.length).trim().split(/\s+/);
    const c=(a.shift()||'').toLowerCase();
    if(c==='uptime'||c==='up')return m.reply({embeds:[uptimeEmbed()]});
    return old(m);
   }catch(e){console.error('[UPTIME]',e?.stack||e)}
  });
 }
};
