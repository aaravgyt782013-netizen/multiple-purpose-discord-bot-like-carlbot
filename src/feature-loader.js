const fs=require('fs');
const path=require('path');
const attach=require('./feature-pack.js');
const attachMusic=require('./music.js');

module.exports=function loadFeaturePack(bot){
  if(!bot?.client) throw new Error('LightCore client is unavailable.');
  const dataDir=path.join(process.cwd(),'data');
  const file=path.join(dataDir,'database.json');
  if(!fs.existsSync(dataDir))fs.mkdirSync(dataDir,{recursive:true});
  if(!fs.existsSync(file))fs.writeFileSync(file,'{}');
  let db={};
  try{db=JSON.parse(fs.readFileSync(file,'utf8')||'{}');}catch{db={};}
  const save=()=>fs.writeFileSync(file,JSON.stringify(db,null,2));
  const fresh=()=>({featurePack:{ticketCategory:null,ticketStaffRole:null,rr:{},temp:{category:null,creator:null},welcome:null,goodbye:null,filters:[],autorole:null,raid:{enabled:false},nuke:{enabled:false}},custom:{},reminders:[]});
  const gd=id=>{const d=db[id]||(db[id]=fresh());const f=fresh();for(const k of Object.keys(f))if(d[k]===undefined)d[k]=f[k];return d;};
  attach(bot.client,db,save,gd,'.');
  attachMusic(bot.client,'.');
};
