import {useState} from 'react';
import {api} from '../api';
import {Run} from '../App';
export function Benchmark({actor,run}:{actor:string;run:Run}){
 const [result,setResult]=useState<any>();
 return <><h1>Measure the allocation</h1><p>50 reproducible synthetic candidate matrices, seed 15015. Both algorithms receive identical edges. Timings vary by machine.</p><button onClick={()=>run(async()=>setResult((await api('/benchmarks/run',actor,'POST')).result),'Benchmark finished')}>Run real benchmark</button>
 {result&&<><section><h2>{result.optimized_wins} utility wins · {result.equal} ties</h2><p>Illustrative matrix [9,8] / [8,1]: optimized utility {result.illustration.optimized_utility}, greedy utility {result.illustration.greedy_utility}.</p><p>This is matrix-level evaluation; scheduling and database constraints have separate integration tests.</p></section><div className="table-wrap"><table><caption>Per-scenario results (optimized / greedy)</caption><thead><tr>{['Scenario','Assignments','Utility','Avg suitability','Urgent rate','Unassigned','Invalid','Runtime ms'].map(t=><th key={t}>{t}</th>)}</tr></thead><tbody>{result.scenarios.map((r:any)=><tr key={r.scenario}><td>{r.scenario+1}</td>{['assignment_count','total_utility','average_suitability','urgent_assignment_rate','unassigned_requests','invalid_assignments','runtime_ms'].map(k=><td key={k}>{[r.optimized[k],r.greedy[k]].map(v=>v===null?'n/a':Number(v).toFixed(2)).join(' / ')}</td>)}</tr>)}</tbody></table></div></>}
 </>;
}
