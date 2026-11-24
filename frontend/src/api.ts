export async function api<T = any>(path:string, student:string, method='GET', body?:unknown):Promise<T> {
  const response = await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(student?{'X-Demo-Student-ID':student}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const data = await response.json();
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));
  return data;
}
export const time = (value:string) => new Date(value).toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'});
export function fromIST(value:string) {return value?new Date(value+':00+05:30').toISOString():null;}
export interface Skill {domain:string;tag:string;level:number}
export interface Student {id:string;name:string;mentoring:boolean;skills:Skill[];availability:{id:string;start:string;end:string}[]}
export type Domains=Record<string,string[]>;
