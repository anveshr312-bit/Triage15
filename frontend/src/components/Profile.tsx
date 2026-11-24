import {useState} from 'react';
import {api,Domains,Student,time,fromIST} from '../api';
import {Run} from '../App';
export function Profile({student,domains,run}:{student:Student;domains:Domains;run:Run}){
 const [mentoring,setMentoring]=useState(student.mentoring),[skills,setSkills]=useState(student.skills),[domain,setDomain]=useState('Python'),[level,setLevel]=useState(3);
 return <><h1>Profile & availability</h1><p>Self-declared levels are shown separately from assessment evidence.</p><div className="columns"><section><h2>{student.name}</h2><label className="check"><input type="checkbox" checked={mentoring} onChange={e=>setMentoring(e.target.checked)}/> Opt into mentoring</label>
 <label>Domain<select value={domain} onChange={e=>setDomain(e.target.value)}>{Object.keys(domains).map(d=><option key={d}>{d}</option>)}</select></label><label>Self-declared level (1–5)<input type="number" min="1" max="5" value={level} onChange={e=>setLevel(+e.target.value)}/></label>
 <div className="tags">{domains[domain]?.map(tag=><label className="check" key={tag}><input type="checkbox" checked={skills.some(s=>s.domain===domain&&s.tag===tag)} onChange={e=>setSkills(e.target.checked?[...skills,{domain,tag,level}]:skills.filter(s=>!(s.domain===domain&&s.tag===tag)))}/>{tag}</label>)}</div>
 <ul>{skills.map(s=><li key={s.domain+s.tag}>{s.domain} / {s.tag}: level {s.level} (self-declared)</li>)}</ul>
 <button onClick={()=>run(()=>api('/students/'+student.id+'/profile',student.id,'PUT',{mentoring,skills}))}>Save profile</button></section>
 <section><h2>Available windows</h2><p>Slots are rounded inward to the 15-minute grid. Add windows within the next seven days.</p>
 {student.availability.length===0&&<p>No availability set.</p>}{student.availability.map(w=><p key={w.id}>{time(w.start)} – {time(w.end)} <button onClick={()=>run(()=>api(`/students/${student.id}/availability/${w.id}`,student.id,'DELETE'))}>Remove</button></p>)}
 <form onSubmit={e=>{e.preventDefault();const f=e.currentTarget;const data=new FormData(f);void run(async()=>{await api('/students/'+student.id+'/availability',student.id,'POST',{start:fromIST(String(data.get('start'))),end:fromIST(String(data.get('end')))});f.reset()})}}><label>Start (IST)<input required name="start" type="datetime-local"/></label><label>End (IST)<input required name="end" type="datetime-local"/></label><button>Add availability</button></form></section></div>
 <section><h2>Register a synthetic demo profile</h2><form onSubmit={e=>{e.preventDefault();const f=e.currentTarget;void run(async()=>{await api('/students',student.id,'POST',{name:String(new FormData(f).get('name'))});f.reset()},'Profile created; select it in the identity menu')}}><label>Display name<input required minLength={2} maxLength={80} name="name"/></label><button>Create profile</button></form></section></>;
}
