import {useCallback,useEffect,useState} from 'react';
import {api,Student,Domains} from './api';
import {Profile} from './components/Profile';
import {DoubtBoard} from './components/DoubtBoard';
import {Sessions} from './components/Sessions';
import {Assessment} from './components/Assessment';
import {Benchmark} from './components/Benchmark';

export default function App(){
 const [students,setStudents]=useState<Student[]>([]),[domains,setDomains]=useState<Domains>({});
 const [actor,setActor]=useState('student-08'),[tab,setTab]=useState('Doubt board'),[revision,setRevision]=useState(0);
 const [error,setError]=useState(''),[notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[metrics,setMetrics]=useState<any>();
 const refresh=useCallback(()=>setRevision(x=>x+1),[]);
 useEffect(()=>{Promise.all([api<Student[]>('/students',actor),api<Domains>('/domains',actor),api('/metrics',actor)])
   .then(([s,d,m])=>{setStudents(s);setDomains(d);setMetrics(m)}).catch(e=>setError(e.message));},[actor,revision]);
 const run=async(task:()=>Promise<unknown>,message='Saved')=>{setBusy(true);setError('');setNotice('');try{await task();setNotice(message);refresh()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 const [dispatch,setDispatch]=useState<any>();
 const student=students.find(s=>s.id===actor);
 return <><header><div><strong>TRIAGE<span>15</span></strong><p>Campus peer help · 15-minute sessions</p></div><label>Demo identity<select value={actor} onChange={e=>{setActor(e.target.value);setNotice('');setError('')}}>{students.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label></header>
 <main><p className="banner">Local demo · Synthetic profiles · All times Asia/Kolkata (IST) · Identity selection is not authentication.</p>
 {metrics&&<div className="metrics"><div><b>{(metrics.doubts.OPEN||0)+(metrics.doubts.UNMATCHED||0)}</b> waiting requests</div><div><b>{metrics.sessions.OFFERED||0}</b> mentor offers</div><div><b>{metrics.resolved_sessions}</b> resolved sessions</div><div><b>{metrics.average_rating?.toFixed(1)||'—'}</b> average feedback ({metrics.feedback_count})</div></div>}
 <nav>{['Doubt board','My sessions','Profile & availability','Assessments','Benchmark'].map(t=><button aria-pressed={tab===t} key={t} onClick={()=>setTab(t)}>{t}</button>)}</nav>
 {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status" className="success">{notice}</p>}{busy&&<p role="status">Working…</p>}
 {!student?<p>Loading profiles…</p>:<fieldset disabled={busy} className="workspace">
 {tab==='Doubt board'&&<><div className="section-head"><div><h1>Find the right peer.</h1><p>Post a focused question. Dispatch considers all waiting requests together.</p></div><button className="primary" onClick={()=>run(async()=>setDispatch(await api('/dispatch/run',actor,'POST')),'Dispatch finished')}>Run dispatch</button></div>
 {dispatch&&<section><h2>Dispatch result</h2><p>{dispatch.result.assignments.length} offers created · {dispatch.result.unassigned.length} waiting · {dispatch.result.final_validation_rejections.length} final conflicts rejected</p><p>Candidate matrix utility: optimized {dispatch.result.comparison.optimized.total_utility.toFixed(2)} / greedy {dispatch.result.comparison.greedy.total_utility.toFixed(2)}</p><details><summary>Unassigned explanations</summary>{dispatch.result.unassigned.map((x:any)=><p key={x.id}>{x.id}: {x.reason}</p>)}</details></section>}
 <DoubtBoard actor={actor} domains={domains} students={students} revision={revision} run={run}/></>}
 {tab==='My sessions'&&<Sessions actor={actor} students={students} revision={revision} run={run}/>}
 {tab==='Profile & availability'&&<Profile key={actor+revision} student={student} domains={domains} run={run}/>}
 {tab==='Assessments'&&<Assessment key={actor} actor={actor} run={run}/>}
 {tab==='Benchmark'&&<Benchmark actor={actor} run={run}/>}
 </fieldset>}
 </main><footer>Deterministic optimization, not AI. Suitability is a ranking score, not a promise of resolution.</footer></>;
}
export type Run=(task:()=>Promise<unknown>,message?:string)=>Promise<void>;
