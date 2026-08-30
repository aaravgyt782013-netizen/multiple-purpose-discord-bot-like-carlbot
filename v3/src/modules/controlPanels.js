const { ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder, ModalBuilder, TextInputBuilder, TextInputStyle, EmbedBuilder, PermissionFlagsBits, ChannelType } = require('discord.js');

function panel(kind, data={}) {
  if(kind==='help') return {
    embeds:[new EmbedBuilder().setTitle('🤖 Aarav All-In-One').setDescription('Select a category to browse commands. Use the buttons below to switch between slash and prefix commands.').setColor(0x5865f2)],
    components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('help:category').setPlaceholder('Select a command category').addOptions(
      {label:'Moderation',value:'mod',emoji:'🛡️'},{label:'Security',value:'security',emoji:'🔐'},{label:'Community',value:'community',emoji:'👥'},{label:'Economy',value:'economy',emoji:'💰'},{label:'Utility',value:'utility',emoji:'🧰'},{label:'Music',value:'music',emoji:'🎵'},{label:'Tickets & Applications',value:'support',emoji:'🎫'}
    )),new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('help:slash').setLabel('Slash Commands').setStyle(ButtonStyle.Primary),new ButtonBuilder().setCustomId('help:prefix').setLabel('Client Commands').setStyle(ButtonStyle.Secondary))]
  };
  if(kind==='ticket') return {embeds:[new EmbedBuilder().setTitle(data.title||'🎫 Support Tickets').setDescription(data.description||'Click the button below to create a private support ticket.').setColor(0x5865f2)],components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('ticket:create').setLabel(data.button||'Create Ticket').setEmoji('🎫').setStyle(ButtonStyle.Primary))]};
  if(kind==='application') return {embeds:[new EmbedBuilder().setTitle(data.title||'📝 Applications').setDescription(data.description||'Choose an application below.').setColor(0x5865f2)],components:[new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId('application:choose').setPlaceholder('Choose an application').addOptions((data.types||['Staff Application','Partner Application']).map((x,n)=>({label:x,value:`app:${n}`}))))]};
  return {embeds:[new EmbedBuilder().setTitle(data.title||'📢 Announcement').setDescription(data.description||'')],components:[]};
}

function editor(kind){
  const modal=new ModalBuilder().setCustomId(`edit:${kind}`).setTitle(`Edit ${kind} panel`);
  const title=new TextInputBuilder().setCustomId('title').setLabel('Panel title').setStyle(TextInputStyle.Short).setRequired(true);
  const desc=new TextInputBuilder().setCustomId('description').setLabel('Panel description').setStyle(TextInputStyle.Paragraph).setRequired(true);
  return modal.addComponents(new ActionRowBuilder().addComponents(title),new ActionRowBuilder().addComponents(desc));
}

async function handleInteraction(i,ctx){
  if(i.isStringSelectMenu() && i.customId==='help:category'){
    const map={mod:['🛡️ Moderation','kick • ban • timeout • warn • purge • lock • role'],security:['🔐 Security','automod • antilink • antispam • antiraid • verification'],community:['👥 Community','welcome • goodbye • autorole • reaction roles • leveling'],economy:['💰 Economy','balance • daily • work • pay • shop • inventory'],utility:['🧰 Utility','userinfo • serverinfo • poll • embed • announce • remind'],music:['🎵 Music','play • pause • resume • skip • queue • volume • loop • nowplaying'],support:['🎫 Support','tickets • applications • panels • transcripts']};const x=map[i.values[0]]||map.utility;return i.update({embeds:[new EmbedBuilder().setTitle(x[0]).setDescription('`/'+x[1].split(' • ').join('`  `/')+'`').setColor(0x5865f2)],components:i.message.components});
  }
  if(i.isButton() && i.customId==='help:slash') return i.reply({content:'Slash commands: use `/help` → category selector to browse the complete registered slash command list.',ephemeral:true});
  if(i.isButton() && i.customId==='help:prefix') return i.reply({content:`Client commands use the configured prefix \`${ctx.prefix}\`. Use \`${ctx.prefix}help\` for the full list.`,ephemeral:true});
  if(i.isButton() && i.customId==='ticket:create'){
    const exists=ctx.db.prepare('SELECT channel FROM tickets WHERE guild=? AND user=?').get(i.guildId,i.user.id);if(exists)return i.reply({content:`You already have ${exists.channel}.`,ephemeral:true});
    const ch=await i.guild.channels.create({name:`ticket-${i.user.username}`.slice(0,90),type:ChannelType.GuildText,permissionOverwrites:[{id:i.guild.roles.everyone.id,deny:[PermissionFlagsBits.ViewChannel]},{id:i.user.id,allow:[PermissionFlagsBits.ViewChannel,PermissionFlagsBits.SendMessages,PermissionFlagsBits.ReadMessageHistory]}]});ctx.db.prepare('INSERT INTO tickets VALUES(?,?,?,?)').run(i.guildId,i.user.id,ch.id,Date.now());await ch.send({content:`Welcome ${i.user}! Staff will be with you shortly.`,components:[new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('ticket:close').setLabel('Close Ticket').setStyle(ButtonStyle.Danger))]});return i.reply({content:`🎫 Ticket created: ${ch}`,ephemeral:true});
  }
  if(i.isButton() && i.customId==='ticket:close'){ctx.db.prepare('DELETE FROM tickets WHERE channel=?').run(i.channelId);await i.reply('🔒 Closing ticket...');return setTimeout(()=>i.channel.delete().catch(()=>{}),1200);}
  if(i.isButton() && i.customId==='panel:edit:ticket')return i.showModal(editor('ticket'));
  if(i.isButton() && i.customId==='panel:edit:application')return i.showModal(editor('application'));
  if(i.isModalSubmit() && i.customId.startsWith('edit:')){const kind=i.customId.slice(5);ctx.db.prepare(`INSERT INTO custom_commands(guild,name,response) VALUES(?,?,?) ON CONFLICT(guild,name) DO UPDATE SET response=excluded.response`).run(i.guildId,`panel_${kind}`,JSON.stringify({title:i.fields.getTextInputValue('title'),description:i.fields.getTextInputValue('description')}));return i.reply({content:`✅ ${kind} panel settings saved.`,ephemeral:true});}
  if(i.isStringSelectMenu() && i.customId==='application:choose'){
    const modal=new ModalBuilder().setCustomId(`application:submit:${i.values[0]}`).setTitle('Application');for(let n=1;n<=5;n++)modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId(`q${n}`).setLabel(`Question ${n}`).setStyle(TextInputStyle.Paragraph).setRequired(n===1)));return i.showModal(modal);
  }
  if(i.isModalSubmit() && i.customId.startsWith('application:submit:')){const answers=[];for(let n=1;n<=5;n++){const v=i.fields.getTextInputValue(`q${n}`);if(v)answers.push(`**Q${n}:** ${v}`)}const ch=await i.guild.channels.create({name:`application-${i.user.username}`.slice(0,90),type:ChannelType.GuildText});await ch.send({embeds:[new EmbedBuilder().setTitle(`📝 Application • ${i.user.tag}`).setDescription(answers.join('\n\n')).setColor(0x5865f2)]});return i.reply({content:`✅ Application submitted: ${ch}`,ephemeral:true});}
  return false;
}
module.exports={panel,editor,handleInteraction};
