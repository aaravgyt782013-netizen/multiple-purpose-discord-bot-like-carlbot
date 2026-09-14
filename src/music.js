const {DisTube}=require('distube');
const {YouTubePlugin}=require('@distube/youtube');
const {EmbedBuilder}=require('discord.js');

module.exports=function attachMusic(client,prefix='.'){
 const P=prefix||'.',INST=Symbol.for('lightcore.distubeInstalled');
 if(client[INST])return client[Symbol.for('lightcore.distube')];
 const distube=new DisTube(client,{plugins:[new YouTubePlugin()],emitNewSongOnly:true});
 client[INST]=true;client[Symbol.for('lightcore.distube')]=distube;
 const clean=(v,n=240)=>String(v||'').replace(/[<>]/g,'').slice(0,n);
 const em=(title,description)=>new EmbedBuilder().setTitle(title).setDescription(description).setColor(0x5865f2).setTimestamp();
 distube.on('playSong',(q,s)=>q.textChannel?.send({embeds:[em('🎵 Now Playing',`**${clean(s.name)}**\n🎧 ${clean(s.uploader?.name||'YouTube')} • ⏱️ ${clean(s.formattedDuration||'Unknown')}\n🔊 Volume: **${q.volume}%** • 🔁 Repeat: **${q.repeatMode}**`)]}).catch(()=>{}));
 distube.on('addSong',(q,s)=>q.songs.length>1&&q.textChannel?.send({embeds:[em('➕ Added to Queue',`**${clean(s.name)}**\nPosition: **${q.songs.length-1}**`)]}).catch(()=>{}));
 distube.on('error',(e,q)=>{console.error('[DISTUBE MUSIC]',e?.stack||e);q?.textChannel?.send(`❌ Music error: ${clean(e?.message||'Playback failed.',300)}`).catch(()=>{});});
 distube.on('finish',(q)=>q.textChannel?.send('⏹️ Queue finished.').catch(()=>{}));
 distube.on('empty',(q)=>q.textChannel?.send('👋 Everyone left the voice channel, so I left too.').catch(()=>{}));
 distube.on('debug',d=>console.log('[DISTUBE]',clean(d,500)));

 async function handle(m,c,a){
  if(!m.guild)return false;
  const q=()=>distube.getQueue(m.guild.id);
  if(c==='play'||c==='p'){
   const song=a.join(' ').trim();if(!song)return m.reply(`Usage: ${P}play <song name or URL>`);
   const vc=m.member?.voice?.channel;if(!vc)return m.reply('❌ Join a voice channel first.');
   const me=m.guild.members.me;if(me&&!me.permissionsIn(vc).has('Connect'))return m.reply('❌ I need **Connect** permission in that voice channel.');
   if(me&&!me.permissionsIn(vc).has('Speak'))return m.reply('❌ I need **Speak** permission in that voice channel.');
   try{await distube.play(vc,song,{textChannel:m.channel,member:m.member,message:m});return true;}catch(e){console.error('[MUSIC PLAY]',e?.stack||e);return m.reply(`❌ ${clean(e?.message||'I could not play that track.',300)`);}
  }
  if(c==='join'||c==='connect'){
   const vc=m.member?.voice?.channel;if(!vc)return m.reply('❌ Join a voice channel first.');
   try{await distube.voices.join(vc);return m.reply(`🔊 Joined **${vc.name}**.`);}catch(e){return m.reply(`❌ ${clean(e?.message||'Could not join the voice channel.',300)}`);}
  }
  if(c==='leave'||c==='disconnect'){
   try{await distube.stop(m.guild.id);}catch{}distube.voices.leave(m.guild.id);return m.reply('👋 Left voice and cleared the queue.');
  }
  if(c==='pause'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');await x.pause();return m.reply('⏸️ Paused.');}
  if(c==='resume'||c==='unpause'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');await x.resume();return m.reply('▶️ Resumed.');}
  if(c==='skip'||c==='next'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');try{await x.skip();return m.reply('⏭️ Skipped.');}catch{return m.reply('❌ There is nothing after the current track.');}}
  if(c==='stop'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');await x.stop();return m.reply('⏹️ Stopped and cleared the queue.');}
  if(c==='queue'||c==='q'){
   const x=q();if(!x)return m.reply('📭 Queue is empty.');
   const lines=x.songs.slice(0,20).map((s,i)=>`${i===0?'🎵 **Now:**':'`'+i+'`'} ${clean(s.name,100)} • ${clean(s.formattedDuration||'Unknown')}`);
   if(x.songs.length>20)lines.push(`…and **${x.songs.length-20}** more.`);
   return m.reply({embeds:[em('📜 Music Queue',lines.join('\n')+`\n\n🔊 Volume: **${x.volume}%** • 🔁 Repeat: **${x.repeatMode}**`)]});
  }
  if(c==='nowplaying'||c==='np'||c==='current'){
   const x=q();if(!x)return m.reply('❌ Nothing is playing.');const s=x.songs[0];if(!s)return m.reply('❌ Nothing is playing.');
   return m.reply({embeds:[em('🎵 Now Playing',`**${clean(s.name)}**\n🎧 ${clean(s.uploader?.name||'YouTube')} • ⏱️ ${clean(s.formattedDuration||'Unknown')}\n🔊 Volume: **${x.volume}%** • 🔁 Repeat: **${x.repeatMode}**`).setURL(s.url)]});
  }
  if(c==='volume'||c==='vol'){const x=q(),v=Number(a[0]);if(!x)return m.reply('❌ Nothing is playing.');if(!Number.isInteger(v)||v<0||v>100)return m.reply(`Usage: ${P}volume <0-100>`);x.setVolume(v);return m.reply(`🔊 Volume set to **${v}%**.`);}
  if(c==='loop'||c==='repeat'){
   const x=q();if(!x)return m.reply('❌ Nothing is playing.');const mode=(a[0]||'').toLowerCase();const map={off:0,track:1,song:1,queue:2,all:2};if(mode&&!Object.prototype.hasOwnProperty.call(map,mode))return m.reply(`Usage: ${P}loop off|track|queue`);const n=x.setRepeatMode(mode?map[mode]:undefined);return m.reply(`🔁 Repeat mode: **${n===0?'off':n===1?'track':'queue'}**.`);
  }
  if(c==='autoplay'||c==='ap'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');const on=x.toggleAutoplay();return m.reply(`🤖 Autoplay: **${on?'On':'Off'}**.`);}
  if(c==='shuffle'){const x=q();if(!x)return m.reply('❌ Nothing is playing.');await x.shuffle();return m.reply('🔀 Queue shuffled.');}
  if(c==='clearqueue'){const x=q();if(!x)return m.reply('📭 Queue is empty.');const current=x.songs[0];x.songs.splice(1);if(current)x.songs[0]=current;return m.reply('🧹 Queue cleared; current track keeps playing.');}
  if(c==='musichelp'||c==='music')return m.reply({embeds:[em('🎧 LightCore Music',`**Start**\n\`${P}play <song>\` — search and play\n\`${P}play <URL>\` — play a URL\n\`${P}join\` • \`${P}leave\`\n\n**Controls**\n\`${P}pause\` • \`${P}resume\` • \`${P}skip\` • \`${P}stop\`\n\n**Queue**\n\`${P}queue\` • \`${P}shuffle\` • \`${P}clearqueue\`\n\n**Player**\n\`${P}nowplaying\` • \`${P}volume 0-100\` • \`${P}loop off/track/queue\` • \`${P}autoplay\``)]});
  return false;
 }
 client.on('messageCreate',async m=>{try{if(m.author?.bot||!m.guild||!m.content.startsWith(P))return;const a=m.content.slice(P.length).trim().split(/\s+/),c=(a.shift()||'').toLowerCase();await handle(m,c,a);}catch(e){console.error('[MUSIC ROUTER]',e?.stack||e);}});
 console.log('[MUSIC] DisTube music engine loaded.');
 return distube;
};
