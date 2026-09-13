'use client';
import {useState} from 'react';
import './style.css';

const initial=[
 {name:'Support',emoji:'🎫',desc:'General support',staff:'Support Staff',questions:['What do you need help with?']},
 {name:'Report',emoji:'🚨',desc:'Report a member or issue',staff:'Moderators',questions:['Who/what are you reporting?','Please explain what happened.']},
 {name:'Application',emoji:'📝',desc:'Staff applications',staff:'Management',questions:['What position are you applying for?','Why should we choose you?','What experience do you have?']}
];
export default function Home(){
 const [cats,setCats]=useState(initial);const [active,setActive]=useState('Tickets');const [selected,setSelected]=useState(0);const [published,setPublished]=useState(false);
 const c=cats[selected]||cats[0];
 const add=()=>setCats([...cats,{name:'New Category',emoji:'🎫',desc:'New ticket category',staff:'Ticket Staff',questions:['Please describe your request.']}]);
 const update=(k,v)=>setCats(cats.map((x,i)=>i===selected?{...x,[k]:v}:x));
 return <main><aside><div className="brand"><span>◆</span> LightCore</div><p className="server">Discord Server</p>{['Overview','Tickets','Applications','Moderation','Logging','AutoMod','Welcome','Roles','Economy','Music','Settings'].map(x=><button className={active===x?'nav active':'nav'} onClick={()=>setActive(x)} key={x}>{x}</button>)}<div className="user">● Connected<br/><small>Discord server</small></div></aside>
 <section className="content"><header><div><p className="eyebrow">SERVER CONTROL CENTER</p><h1>{active}</h1><p className="muted">Configure LightCore without memorizing commands.</p></div><button className="publish" onClick={()=>setPublished(true)}>{published?'✓ Published':'Publish Changes'}</button></header>
 {active==='Tickets'?<><div className="hero"><div><h2>🎫 Ticket Center</h2><p>Create a complete R.O.T.I.-style ticket flow with guided setup, forms, staff controls, logs and transcripts.</p></div><span className="status">● Ready</span></div>
 <div className="grid"><div className="panel"><div className="panelhead"><div><h3>Ticket categories</h3><p>Each category can have its own staff role, questions and channels.</p></div><button onClick={add}>＋ Add category</button></div>{cats.map((x,i)=><button className={i===selected?'cat selected':'cat'} key={i} onClick={()=>setSelected(i)}><b>{x.emoji} {x.name}</b><span>{x.desc}</span><small>Staff: {x.staff} · {x.questions.length} questions</small></button>)}</div>
 <div className="panel editor"><h3>Edit {c.name}</h3><label>Name<input value={c.name} onChange={e=>update('name',e.target.value)}/></label><label>Description<textarea value={c.desc} onChange={e=>update('desc',e.target.value)}/></label><label>Staff role<input value={c.staff} onChange={e=>update('staff',e.target.value)}/></label><h4>Questions</h4>{c.questions.map((q,i)=><div className="question" key={i}><input value={q} onChange={e=>update('questions',c.questions.map((z,j)=>j===i?e.target.value:z))}/><button onClick={()=>update('questions',c.questions.filter((_,j)=>j!==i))}>×</button></div>)}<button className="addq" onClick={()=>update('questions',[...c.questions,'New question'])}>＋ Add question</button></div>
 <div className="panel flow"><h3>Ticket workflow</h3>{['Select category','Answer questions','Create private channel','Notify staff role','Staff claim / manage','Close + transcript + logs'].map((x,i)=><div className="step" key={x}><b>{i+1}</b><span>{x}</span><i>✓</i></div>)}</div><div className="panel preview"><h3>Panel preview</h3><div className="discord"><strong>{c.emoji} {c.name} Support</strong><p>{c.desc}</p><button>🎫 Open Ticket</button></div></div></div></>:<div className="empty panel"><h2>{active}</h2><p>This dashboard section is ready for the same guided configuration style. Ticket setup is fully visual here.</p></div>}
 </section></main>
}
