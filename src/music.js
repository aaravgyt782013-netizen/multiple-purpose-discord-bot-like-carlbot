const play = require('play-dl');
const { joinVoiceChannel, createAudioPlayer, createAudioResource, AudioPlayerStatus, NoSubscriberBehavior, VoiceConnectionStatus, entersState } = require('@discordjs/voice');
const { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');

/**
 * LightCore Music — original queue/player implementation.
 * Supports YouTube URLs/search, SoundCloud URLs, queues, controls and buttons.
 */
module.exports = function attachMusic(client, prefix='.') {
  const P = prefix || '.';
  const C = 0x5865f2;
  const queues = new Map();

  const clean = (v,n=200) => String(v||'').replace(/[<>]/g,'').slice(0,n);
  const embed = (title, desc) => new EmbedBuilder().setTitle(title).setDescription(desc).setColor(C).setTimestamp();

  function state(guildId) {
    let s=queues.get(guildId);
    if(!s){
      s={queue:[],current:null,connection:null,player:createAudioPlayer({behaviors:{noSubscriber:NoSubscriberBehavior.Pause}}),volume:100,loop:'off',textChannel:null,voiceChannel:null,playing:false,loading:false,requester:null};
      s.player.on('error',e=>{console.error('[MUSIC PLAYER]',e?.message||e); next(guildId).catch(()=>{});});
      s.player.on(AudioPlayerStatus.Idle,()=>{ if(s.playing&&!s.loading) next(guildId).catch(()=>{}); });
      queues.set(guildId,s);
    }
    return s;
  }

  async function sourceInfo(query) {
    if(/^https?:\/\//i.test(query)){
      const type=await play.validate(query);
      if(type==='yt_video'){
        const info=await play.video_info(query);
        return {url:query,title:info.video_details.title||'YouTube track',duration:info.video_details.durationRaw||'Unknown',thumbnail:info.video_details.thumbnails?.[0]?.url||null,source:'YouTube'};
      }
      if(type==='so_track'){
        const info=await play.soundcloud(query);
        return {url:query,title:info.name||'SoundCloud track',duration:'Unknown',thumbnail:info.thumbnail||null,source:'SoundCloud'};
      }
      throw new Error('Unsupported music URL. Use a YouTube video or SoundCloud track URL.');
    }
    const results=await play.search(query,{limit:1,source:{youtube:'video',soundcloud:'tracks'}});
    if(!results?.length)throw new Error('No music results found.');
    const x=results[0];
    return {url:x.url,title:x.title||'Unknown track',duration:x.durationRaw||'Unknown',thumbnail:x.thumbnails?.[0]?.url||null,source:'YouTube',requestQuery:query};
  }

  async function connect(message) {
    const vc=message.member?.voice?.channel;
    if(!vc)return {error:'❌ Join a voice channel first.'};
    const me=message.guild.members.me;
    if(!me?.permissionsIn(vc).has('Connect'))return {error:'❌ I need **Connect** permission in that voice channel.'};
    const s=state(message.guild.id);
    if(s.connection && s.voiceChannel===vc.id) return {s,vc};
    if(s.connection)s.connection.destroy();
    const connection=joinVoiceChannel({channelId:vc.id,guildId:message.guild.id,adapterCreator:message.guild.voiceAdapterCreator,selfDeaf:true});
    try{await entersState(connection,VoiceConnectionStatus.Ready,15000);}catch(e){connection.destroy();return {error:'❌ I could not connect to the voice channel.'};}
    connection.subscribe(s.player);s.connection=connection;s.voiceChannel=vc.id;
    connection.on(VoiceConnectionStatus.Disconnected,async()=>{try{await Promise.race([entersState(connection,VoiceConnectionStatus.Signalling,5000),entersState(connection,VoiceConnectionStatus.Connecting,5000)]);}catch{connection.destroy();if(s.connection===connection)s.connection=null;}});
    return {s,vc};
  }

  async function streamTrack(track) {
    if(track.source==='SoundCloud'){
      const st=await play.stream(track.url,{discordPlayerCompatibility:true});
      return createAudioResource(st.stream,{inputType:st.type,inlineVolume:true,metadata:track});
    }
    const st=await play.stream(track.url,{discordPlayerCompatibility:true});
    return createAudioResource(st.stream,{inputType:st.type,inlineVolume:true,metadata:track});
  }

  async function nowPlaying(guildId) {
    const s=state(guildId);if(!s.current)return;
    const ch=s.textChannel;if(!ch?.isTextBased())return;
    const t=s.current;
    const row=new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId('music_pause').setLabel(s.player.state.status===AudioPlayerStatus.Paused?'Resume':'Pause').setEmoji(s.player.state.status===AudioPlayerStatus.Paused?'▶️':'⏸️').setStyle(ButtonStyle.Primary),
      new ButtonBuilder().setCustomId('music_skip').setLabel('Skip').setEmoji('⏭️').setStyle(ButtonStyle.Secondary),
      new ButtonBuilder().setCustomId('music_stop').setLabel('Stop').setEmoji('⏹️').setStyle(ButtonStyle.Danger),
      new ButtonBuilder().setCustomId('music_loop').setLabel(`Loop: ${s.loop}`).setEmoji('🔁').setStyle(ButtonStyle.Secondary)
    );
    const e=embed('🎵 Now Playing',`**${clean(t.title,250)}**\nSource: **${t.source}**\nDuration: **${clean(t.duration)}**\nRequested by: <@${t.requester}>\n\nQueue: **${s.queue.length}** track(s) • Volume: **${s.volume}%** • Loop: **${s.loop}**`).setURL(t.url);
    if(t.thumbnail)e.setThumbnail(t.thumbnail);
    await ch.send({embeds:[e],components:[row]}).catch(()=>{});
  }

  async function playCurrent(guildId) {
    const s=state(guildId);if(s.loading)return;
    if(!s.current){s.current=s.queue.shift()||null;}
    if(!s.current){s.playing=false;return;}
    s.loading=true;s.playing=true;
    try{
      const resource=await streamTrack(s.current);
      if(resource.volume)resource.volume.setVolume(s.volume/100);
      s.player.play(resource);
      s.loading=false;
      await nowPlaying(guildId);
    }catch(e){
      console.error('[MUSIC STREAM]',e?.stack||e);
      s.loading=false;
      if(s.textChannel?.isTextBased())await s.textChannel.send(`❌ Could not play **${clean(s.current.title)}**. Skipping…`).catch(()=>{});
      s.current=null;
      await next(guildId);
    }
  }

  async function next(guildId) {
    const s=state(guildId);if(s.loading)return;
    if(s.loop==='track'&&s.current){s.player.stop();return playCurrent(guildId);}
    s.current=null;
    if(s.queue.length){return playCurrent(guildId);}
    s.playing=false;
    if(s.textChannel?.isTextBased())await s.textChannel.send('⏹️ Queue finished.').catch(()=>{});
  }

  async function add(message,query) {
    if(!query)return message.reply(`Usage: ${P}play <song name or URL>`);
    const con=await connect(message);if(con.error)return message.reply(con.error);
    const s=con.s;s.textChannel=message.channel;s.requester=message.author.id;
    try{
      const track=await sourceInfo(query);track.requester=message.author.id;
      if(!s.current&&!s.loading){s.current=track;await playCurrent(message.guild.id);return message.reply({embeds:[embed('🎶 Added to player',`**${clean(track.title,250)}**\n▶️ Starting playback now.`)]});}
      s.queue.push(track);return message.reply({embeds:[embed('➕ Added to Queue',`**${clean(track.title,250)}**\nPosition: **${s.queue.length}**`)]});
    }catch(e){return message.reply(`❌ ${clean(e?.message||'Could not find that track.')}`);}
  }

  async function handle(message,c,args){
    if(!message.guild)return false;
    const id=message.guild.id,s=state(id);
    if(c==='play'||c==='p'){await add(message,args.join(' '));return true;}
    if(c==='join'||c==='connect'){const r=await connect(message);if(r.error)return message.reply(r.error);s.textChannel=message.channel;return message.reply(`🔊 Joined **${r.vc.name}**.`);}
    if(c==='leave'||c==='disconnect'){if(s.connection)s.connection.destroy();s.connection=null;s.voiceChannel=null;s.player.stop(true);s.queue=[];s.current=null;s.playing=false;return message.reply('👋 Left the voice channel and cleared the queue.');}
    if(c==='pause'){if(s.player.state.status===AudioPlayerStatus.Playing){s.player.pause();return message.reply('⏸️ Playback paused.');}return message.reply('❌ Nothing is currently playing.');}
    if(c==='resume'||c==='unpause'){if(s.player.state.status===AudioPlayerStatus.Paused){s.player.unpause();return message.reply('▶️ Playback resumed.');}return message.reply('❌ Playback is not paused.');}
    if(c==='skip'||c==='next'){if(!s.current&&!s.queue.length)return message.reply('❌ Nothing is queued.');s.loop='off'===s.loop?'off':s.loop;s.player.stop();return message.reply('⏭️ Skipped.');}
    if(c==='stop'){s.queue=[];s.current=null;s.playing=false;s.player.stop(true);return message.reply('⏹️ Playback stopped and queue cleared.');}
    if(c==='queue'||c==='q'){
      if(!s.current&&!s.queue.length)return message.reply('📭 Queue is empty.');
      const lines=(s.current?[`**Now:** ${clean(s.current.title,100)}`]:[]).concat(s.queue.slice(0,20).map((t,i)=>`${i+1}. ${clean(t.title,90)}`));
      if(s.queue.length>20)lines.push(`…and ${s.queue.length-20} more.`);
      return message.reply({embeds:[embed('📜 Music Queue',lines.join('\n')+`\n\n**${s.queue.length}** queued • Loop: **${s.loop}**`)]});
    }
    if(c==='nowplaying'||c==='np'||c==='current'){if(!s.current)return message.reply('❌ Nothing is currently playing.');const t=s.current;return message.reply({embeds:[embed('🎵 Now Playing',`**${clean(t.title,250)}**\nSource: **${t.source}**\nDuration: **${clean(t.duration)}**\nVolume: **${s.volume}%** • Loop: **${s.loop}**`).setURL(t.url)]});}
    if(c==='volume'||c==='vol'){const v=Math.min(Math.max(Number(args[0]),0),100);if(!Number.isFinite(v))return message.reply(`Usage: ${P}volume <0-100>`);s.volume=v;const r=s.player.state.resource;if(r?.volume)r.volume.setVolume(v/100);return message.reply(`🔊 Volume set to **${v}%**.`);}
    if(c==='loop'||c==='repeat'){const mode=(args[0]||'track').toLowerCase();if(!['off','track','queue'].includes(mode))return message.reply(`Usage: ${P}loop off|track|queue`);s.loop=mode;return message.reply(`🔁 Loop mode: **${mode}**.`);}
    if(c==='shuffle'){for(let i=s.queue.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[s.queue[i],s.queue[j]]=[s.queue[j],s.queue[i]];}return message.reply(s.queue.length?'🔀 Queue shuffled.':'📭 Nothing to shuffle.');}
    if(c==='remove'){const n=Number(args[0]);if(!Number.isInteger(n)||n<1||n>s.queue.length)return message.reply(`Usage: ${P}remove <queue position>`);const [x]=s.queue.splice(n-1,1);return message.reply(`🗑️ Removed **${clean(x.title)}**.`);}
    if(c==='move'){const from=Number(args[0]),to=Number(args[1]);if(!Number.isInteger(from)||!Number.isInteger(to)||from<1||to<1||from>s.queue.length||to>s.queue.length)return message.reply(`Usage: ${P}move <from> <to>`);const [x]=s.queue.splice(from-1,1);s.queue.splice(to-1,0,x);return message.reply('↔️ Queue position changed.');}
    if(c==='clearqueue'){s.queue=[];return message.reply('🧹 Queue cleared. The current track keeps playing.');}
    if(c==='musichelp'){return message.reply({embeds:[embed('🎧 LightCore Music',`**Playback**\n\`${P}play <song/url>\` • \`${P}join\` • \`${P}leave\` • \`${P}pause\` • \`${P}resume\` • \`${P}skip\` • \`${P}stop\`\n\n**Queue**\n\`${P}queue\` • \`${P}shuffle\` • \`${P}remove <position>\` • \`${P}move <from> <to>\` • \`${P}clearqueue\`\n\n**Player**\n\`${P}nowplaying\` • \`${P}volume <0-100>\` • \`${P}loop off|track|queue\`\n\nSupports YouTube search/URLs and SoundCloud track URLs.`)]});}
    return false;
  }

  const old=client.listeners('messageCreate').at(-1);
  if(old){client.removeListener('messageCreate',old);client.on('messageCreate',async m=>{try{if(m.author.bot||!m.guild)return;if(!m.content.startsWith(P))return old(m);const parts=m.content.slice(P.length).trim().split(/\s+/);const c=(parts.shift()||'').toLowerCase();if(!(await handle(m,c,parts)))return old(m);}catch(e){console.error('[MUSIC]',e);}});}

  client.on('interactionCreate',async i=>{
    try{
      if(!i.isButton()||!i.customId.startsWith('music_')||!i.guild)return;
      const s=state(i.guild.id);
      if(!s.voiceChannel||i.member?.voice?.channelId!==s.voiceChannel)return i.reply({content:'❌ Join my current music voice channel first.',ephemeral:true});
      if(i.customId==='music_pause'){if(s.player.state.status===AudioPlayerStatus.Paused)s.player.unpause();else s.player.pause();return i.reply({content:s.player.state.status===AudioPlayerStatus.Paused?'⏸️ Paused.':'▶️ Resumed.',ephemeral:true});}
      if(i.customId==='music_skip'){s.player.stop();return i.reply({content:'⏭️ Skipped.',ephemeral:true});}
      if(i.customId==='music_stop'){s.queue=[];s.current=null;s.playing=false;s.player.stop(true);return i.reply({content:'⏹️ Stopped and cleared.',ephemeral:true});}
      if(i.customId==='music_loop'){s.loop=s.loop==='off'?'track':s.loop==='track'?'queue':'off';return i.reply({content:`🔁 Loop: **${s.loop}**`,ephemeral:true});}
    }catch(e){console.error('[MUSIC BUTTON]',e);if(i.isRepliable()&&!i.replied)i.reply({content:'❌ Music control failed.',ephemeral:true}).catch(()=>{});}
  });

  return {queues};
};
