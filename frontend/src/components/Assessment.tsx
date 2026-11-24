import {useEffect,useState} from 'react';
import {api,time} from '../api';
import {Run} from '../App';
export function Assessment({actor,run}:{actor:string;run:Run}){
 const [domain,setDomain]=useState('Python'),[questions,setQuestions]=useState<any[]>([]),[answers,setAnswers]=useState<Record<string,number>>({}),[history,setHistory]=useState<any[]>([]),[error,setError]=useState('');
 const loadHistory=()=>api('/students/'+actor+'/assessments',actor).then(setHistory);
 useEffect(()=>{let live=true;setQuestions([]);setAnswers({});Promise.all([api('/assessments/'+domain+'/questions',actor),api('/students/'+actor+'/assessments',actor)]).then(([q,h])=>{if(live){setQuestions(q);setHistory(h);setError('')}}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[actor,domain]);
 return <><h1>Assessment evidence</h1><p>Five questions provide limited evidence, not professional verification. Assessments are optional; seekers never need one.</p>{error&&<p role="alert">{error}</p>}<label>Domain<select value={domain} onChange={e=>setDomain(e.target.value)}>{['Python','JavaScript','SQL'].map(d=><option key={d}>{d}</option>)}</select></label><form onSubmit={e=>{e.preventDefault();void run(async()=>{await api('/assessments/submit',actor,'POST',{domain,answers});await loadHistory()},'Assessment scored')}}>
 {questions.map(q=><section key={q.id}><h2>{q.prompt}</h2>{q.options.map((o:string,i:number)=><label className="check" key={i}><input required type="radio" name={q.id} checked={answers[q.id]===i} onChange={()=>setAnswers({...answers,[q.id]:i})}/>{o}</label>)}</section>)}<button disabled={questions.length===0||Object.keys(answers).length!==questions.length}>Submit assessment</button></form><h2>Previous attempts</h2>{!history.length&&<p>No attempts. Your declared skills are provisional.</p>}{history.map(h=><p key={h.id}>{h.domain}: {h.score}% ({h.correct_count}/{h.question_count}) · version {h.version} · {time(h.created_at)}</p>)}</>;
}
