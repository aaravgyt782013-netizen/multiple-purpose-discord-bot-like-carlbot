const {
  ActionRowBuilder, ButtonBuilder, ButtonStyle, StringSelectMenuBuilder,
  ModalBuilder, TextInputBuilder, TextInputStyle, EmbedBuilder,
  PermissionFlagsBits
} = require('discord.js');

function manager(i){return !!i.member?.permissions?.has(PermissionFlagsBits.ManageGuild) || !!i.member?.permissions?.has(PermissionFlagsBits.Administrator);}
function color(v){const s=String(v||'5865f2').replace('#','');return /^[0-9a-f]{6}$/i.test(s)?parseInt(s,16):0x5865f2;}
function ticketHome(db,g){
  const cats=db.prepare('SELECT * FROM ticket_categories WHERE guild=? ORDER BY name').all(g);
  const embed=new EmbedBuilder().setTitle('🎫 Ticket Setup').setDescription('Configure your ticket system interactively. Changes are saved immediately.\n\n**Categories:** '+(cats.length||0)).setColor(0x5865f2);
  const rows=[new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('setup:ticket:add').setLabel('Add / Edit Category').setEmoji('📂').setStyle(ButtonStyle.Primary),
    new ButtonBuilder().setCustomId('setup:ticket:category').setLabel('Category Settings').setEmoji('⚙️').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('setup:ticket:panel').setLabel('Panel Editor').setEmoji('🎨').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('setup:ticket:publish').setLabel('Publish Panel').setEmoji('📌').setStyle(ButtonStyle.Success)
  )];
  if(cats.length) rows.push(new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('setup:ticket:delete').setLabel('Delete Category').setEmoji('🗑️').setStyle(ButtonStyle.Danger)));
  return {embeds:[embed],components:rows};
}
function ticketCategoryModal(){return new ModalBuilder().setCustomId('setup:ticket:add:submit').setTitle('Ticket Category').addComponents(
  row('id','Category ID','support',true),row('name','Display name','Support',true),row('emoji','Emoji','🎫',false),
  row('discord_category','Discord category ID','Paste category channel ID',false),row('staff_role','Staff role ID','Paste role ID',false)
);}
function ticketSettingsModal(db,g,id){const c=db.prepare('SELECT * FROM ticket_categories WHERE guild=? AND id=?').get(g,id);return new ModalBuilder().setCustomId(`setup:ticket:settings:${id}`).setTitle(`${String(c?.name||id).slice(0,35)} Settings`).addComponents(
  row('category','Discord category ID',c?.category||'',false),row('staff','Staff role ID',c?.staff_role||'',false),row('logs','Log channel ID',c?.log_channel||'',false),row('transcript','Transcript channel ID',c?.transcript_channel||'',false),row('limit','Open tickets per user',String(c?.limit_per_user||1),false)
);}
function ticketPanelModal(db,g){const p=db.prepare('SELECT * FROM ticket_panels WHERE guild=?').get(g)||{};return new ModalBuilder().setCustomId('setup:ticket:panel:submit').setTitle('Ticket Panel Editor').addComponents(
  row('title','Panel title',p.title||'🎫 Support Center',true),row('description','Panel description',p.description||'Choose a category below.',true),row('color','HEX color',p.color||'5865f2',true),row('footer','Footer',p.footer||'',false),row('style','Layout: dropdown or buttons',p.style||'dropdown',true)
);}
function applicationHome(db,g){const forms=db.prepare('SELECT * FROM application_forms WHERE guild=? ORDER BY title').all(g);const embed=new EmbedBuilder().setTitle('📝 Application Setup').setDescription('Configure application forms, questions, review routing and the public application panel.\n\n**Forms:** '+(forms.length||0)).setColor(0x5865f2);return {embeds:[embed],components:[new ActionRowBuilder().addComponents(
  new ButtonBuilder().setCustomId('setup:app:add').setLabel('Create / Edit Form').setEmoji('📝').setStyle(ButtonStyle.Primary),
  new ButtonBuilder().setCustomId('setup:app:form').setLabel('Form Settings').setEmoji('⚙️').setStyle(ButtonStyle.Secondary),
  new ButtonBuilder().setCustomId('setup:app:panel').setLabel('Panel Editor').setEmoji('🎨').setStyle(ButtonStyle.Secondary),
  new ButtonBuilder().setCustomId('setup:app:publish').setLabel('Publish Panel').setEmoji('📌').setStyle(ButtonStyle.Success)
)]};}
function appFormModal(){return new ModalBuilder().setCustomId('setup:app:add:submit').setTitle('Application Form').addComponents(
  row('id','Form ID','staff',true),row('title','Form title','Staff Application',true),row('description','Description','Apply here.',true),row('review','Review channel ID','Paste channel ID',false),row('role','Accepted role ID','Paste role ID',false)
);}
function appSettingsModal(db,g,id){const f=db.prepare('SELECT * FROM application_forms WHERE guild=? AND id=?').get(g,id);return new ModalBuilder().setCustomId(`setup:app:settings:${id}`).setTitle(`${String(f?.title||id).slice(0,35)} Settings`).addComponents(
  row('review','Review channel ID',f?.review_channel||'',false),row('role','Accepted role ID',f?.accept_role||'',false),row('questions','Questions separated by |',(JSON.parse(f?.questions||'[]').map(q=>typeof q==='string'?q:q.label).join(' | ')).slice(0,3900),false)
);}
function appPanelModal(db,g){const p=db.prepare('SELECT * FROM application_panels WHERE guild=?').get(g)||{};return new ModalBuilder().setCustomId('setup:app:panel:submit').setTitle('Application Panel Editor').addComponents(
  row('title','Panel title',p.title||'📝 Applications',true),row('description','Panel description',p.description||'Choose an application below.',true),row('color','HEX color',p.color||'5865f2',true),row('footer','Footer',p.footer||'',false),row('style','Layout: dropdown or buttons',p.style||'dropdown',true)
);}
function row(id,label,value,required){const t=new TextInputBuilder().setCustomId(id).setLabel(label.slice(0,45)).setStyle(id==='description'||id==='questions'?TextInputStyle.Paragraph:TextInputStyle.Short).setRequired(required);if(value)t.setValue(String(value).slice(0,id==='description'||id==='questions'?4000:100));return new ActionRowBuilder().addComponents(t);}
function chooser(id,items,placeholder){return new ActionRowBuilder().addComponents(new StringSelectMenuBuilder().setCustomId(id).setPlaceholder(placeholder).addOptions(items.slice(0,25).map(x=>({label:String(x.label).slice(0,100),value:String(x.value),description:String(x.description||'').slice(0,100)}))));}
async function handle(i,{db,tickets,applications}){
  if(!i.guild)return false;
  if(i.isChatInputCommand()&&['ticketsetup','applicationsetup'].includes(i.commandName)){if(!manager(i))return i.reply({content:'⛔ Manage Server or Administrator is required.',ephemeral:true});return i.reply(i.commandName==='ticketsetup'?ticketHome(db,i.guildId):applicationHome(db,i.guildId));}
  if(!String(i.customId||'').startsWith('setup:'))return false;
  if(!manager(i))return i.reply({content:'⛔ Only server managers can edit setup.',ephemeral:true});
  if(i.isButton()&&i.customId==='setup:ticket:add')return i.showModal(ticketCategoryModal());
  if(i.isButton()&&i.customId==='setup:ticket:category'){const cats=db.prepare('SELECT id,name FROM ticket_categories WHERE guild=? ORDER BY name').all(i.guildId);if(!cats.length)return i.reply({content:'Create a category first.',ephemeral:true});return i.reply({content:'Select the ticket category to configure:',components:[chooser('setup:ticket:category:select',cats.map(c=>({label:c.name,value:c.id,description:`Configure ${c.id}`})),'Choose a category')],ephemeral:true});}
  if(i.isButton()&&i.customId==='setup:ticket:panel')return i.showModal(ticketPanelModal(db,i.guildId));
  if(i.isButton()&&i.customId==='setup:ticket:publish'){const ch=i.channel;await ch.send(tickets.panel(db,i.guildId));return i.reply({content:'✅ Ticket panel published here.',ephemeral:true});}
  if(i.isButton()&&i.customId==='setup:ticket:delete'){const cats=db.prepare('SELECT id,name FROM ticket_categories WHERE guild=? ORDER BY name').all(i.guildId);return i.reply({content:'Select the category to delete:',components:[chooser('setup:ticket:delete:select',cats.map(c=>({label:c.name,value:c.id})), 'Delete category')],ephemeral:true});}
  if(i.isStringSelectMenu()&&i.customId==='setup:ticket:category:select')return i.showModal(ticketSettingsModal(db,i.guildId,i.values[0]));
  if(i.isStringSelectMenu()&&i.customId==='setup:ticket:delete:select'){db.prepare('DELETE FROM ticket_categories WHERE guild=? AND id=?').run(i.guildId,i.values[0]);return i.update({content:'🗑️ Category deleted.',components:[]});}
  if(i.isModalSubmit()&&i.customId==='setup:ticket:add:submit'){const id=i.fields.getTextInputValue('id').trim().toLowerCase().replace(/[^a-z0-9_-]/g,'-').slice(0,32),name=i.fields.getTextInputValue('name'),emoji=i.fields.getTextInputValue('emoji')||'🎫',category=i.fields.getTextInputValue('discord_category')||null,staff=i.fields.getTextInputValue('staff_role')||null;db.prepare('INSERT INTO ticket_categories(guild,id,name,emoji,category,staff_role) VALUES(?,?,?,?,?,?) ON CONFLICT(guild,id) DO UPDATE SET name=excluded.name,emoji=excluded.emoji,category=excluded.category,staff_role=excluded.staff_role').run(i.guildId,id,name,emoji,category,staff);return i.reply({...ticketHome(db,i.guildId),ephemeral:true});}
  if(i.isModalSubmit()&&i.customId.startsWith('setup:ticket:settings:')){const id=i.customId.slice('setup:ticket:settings:'.length),v={category:i.fields.getTextInputValue('category')||null,staff_role:i.fields.getTextInputValue('staff')||null,log_channel:i.fields.getTextInputValue('logs')||null,transcript_channel:i.fields.getTextInputValue('transcript')||null,limit_per_user:Math.max(1,Math.min(20,Number(i.fields.getTextInputValue('limit'))||1))};db.prepare('UPDATE ticket_categories SET category=?,staff_role=?,log_channel=?,transcript_channel=?,limit_per_user=? WHERE guild=? AND id=?').run(v.category,v.staff_role,v.log_channel,v.transcript_channel,v.limit_per_user,i.guildId,id);return i.reply({content:`✅ **${id}** updated.\nStaff role: ${v.staff_role?`<@&${v.staff_role}>`:'none'}\nLogs: ${v.log_channel?`<#${v.log_channel}>`:'none'}\nTranscripts: ${v.transcript_channel?`<#${v.transcript_channel}>`:'none'}`,ephemeral:true});}
  if(i.isModalSubmit()&&i.customId==='setup:ticket:panel:submit'){const v=['title','description','color','footer','style'].map(x=>i.fields.getTextInputValue(x));const style=['dropdown','buttons'].includes(v[4].toLowerCase())?v[4].toLowerCase():'dropdown';db.prepare('INSERT INTO ticket_panels(guild,title,description,color,footer,style) VALUES(?,?,?,?,?,?) ON CONFLICT(guild) DO UPDATE SET title=excluded.title,description=excluded.description,color=excluded.color,footer=excluded.footer,style=excluded.style').run(i.guildId,v[0],v[1],v[2].replace('#',''),v[3],style);return i.reply({...ticketHome(db,i.guildId),ephemeral:true});}
  if(i.isButton()&&i.customId==='setup:app:add')return i.showModal(appFormModal());
  if(i.isButton()&&i.customId==='setup:app:form'){const forms=db.prepare('SELECT id,title FROM application_forms WHERE guild=? ORDER BY title').all(i.guildId);if(!forms.length)return i.reply({content:'Create a form first.',ephemeral:true});return i.reply({content:'Select the form to configure:',components:[chooser('setup:app:form:select',forms.map(f=>({label:f.title,value:f.id,description:`Configure ${f.id}`})),'Choose a form')],ephemeral:true});}
  if(i.isButton()&&i.customId==='setup:app:panel')return i.showModal(appPanelModal(db,i.guildId));
  if(i.isButton()&&i.customId==='setup:app:publish'){await i.channel.send(applications.panel(db,i.guildId));return i.reply({content:'✅ Application panel published here.',ephemeral:true});}
  if(i.isStringSelectMenu()&&i.customId==='setup:app:form:select')return i.showModal(appSettingsModal(db,i.guildId,i.values[0]));
  if(i.isModalSubmit()&&i.customId==='setup:app:add:submit'){const id=i.fields.getTextInputValue('id').trim().toLowerCase().replace(/[^a-z0-9_-]/g,'-').slice(0,32),title=i.fields.getTextInputValue('title'),description=i.fields.getTextInputValue('description'),review=i.fields.getTextInputValue('review')||null,role=i.fields.getTextInputValue('role')||null;db.prepare('INSERT INTO application_forms(guild,id,title,description,review_channel,accept_role) VALUES(?,?,?,?,?,?) ON CONFLICT(guild,id) DO UPDATE SET title=excluded.title,description=excluded.description,review_channel=excluded.review_channel,accept_role=excluded.accept_role').run(i.guildId,id,title,description,review,role);return i.reply({...applicationHome(db,i.guildId),ephemeral:true});}
  if(i.isModalSubmit()&&i.customId.startsWith('setup:app:settings:')){const id=i.customId.slice('setup:app:settings:'.length),review=i.fields.getTextInputValue('review')||null,role=i.fields.getTextInputValue('role')||null,qs=i.fields.getTextInputValue('questions').split('|').map(x=>x.trim()).filter(Boolean).slice(0,5);db.prepare('UPDATE application_forms SET review_channel=?,accept_role=?,questions=? WHERE guild=? AND id=?').run(review,role,JSON.stringify(qs),i.guildId,id);return i.reply({content:`✅ **${id}** updated with ${qs.length} questions.`,ephemeral:true});}
  if(i.isModalSubmit()&&i.customId==='setup:app:panel:submit'){const v=['title','description','color','footer','style'].map(x=>i.fields.getTextInputValue(x));const style=['dropdown','buttons'].includes(v[4].toLowerCase())?v[4].toLowerCase():'dropdown';db.prepare('INSERT INTO application_panels(guild,title,description,color,footer,style) VALUES(?,?,?,?,?,?) ON CONFLICT(guild) DO UPDATE SET title=excluded.title,description=excluded.description,color=excluded.color,footer=excluded.footer,style=excluded.style').run(i.guildId,v[0],v[1],v[2].replace('#',''),v[3],style);return i.reply({...applicationHome(db,i.guildId),ephemeral:true});}
  return false;
}
module.exports={handle};
