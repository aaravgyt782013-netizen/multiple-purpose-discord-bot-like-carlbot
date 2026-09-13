const {EmbedBuilder}=require('discord.js');

/** Global LightCore embed skin. Keeps feature-specific colors/content while giving
 * every EmbedBuilder a consistent, polished footer/timestamp/default accent. */
module.exports=function installEmbedTheme(client){
 const marker=Symbol.for('lightcore.embedThemeInstalled');
 if(EmbedBuilder.prototype[marker])return;
 Object.defineProperty(EmbedBuilder.prototype,marker,{value:true,enumerable:false});
 const original=EmbedBuilder.prototype.toJSON;
 EmbedBuilder.prototype.toJSON=function(...args){
  const out=original.apply(this,args);
  if(!out.color)out.color=0x5865f2;
  if(!out.timestamp)out.timestamp=new Date().toISOString();
  if(!out.footer)out.footer={text:'LightCore • All-in-One Discord Bot'};
  else if(!out.footer.text)out.footer.text='LightCore • All-in-One Discord Bot';
  if(client?.user?.displayAvatarURL&&!out.footer.icon_url){
   try{out.footer.icon_url=client.user.displayAvatarURL({size:64,extension:'png'});}catch{}
  }
  return out;
 };
};
