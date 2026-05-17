"use client";
import{useState,useEffect}from"react";
const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export default function Dashboard(){
const[tab,setTab]=useState("overview");
const[data,setData]=useState({employees:[],departments:[],opportunities:[],stats:null,health:null,queue:0,employeeStatus:null});
const[loading,setLoading]=useState(true);
const[selectedEmployee,setSelectedEmployee]=useState(null);
const[analysisResult,setAnalysisResult]=useState(null);
const[analyzing,setAnalyzing]=useState(false);
useEffect(()=>{fetchData();},[]);
const fetchData=async()=>{setLoading(true);try{const[e,d,o,s,h,q]=await Promise.all([fetch(API+"/api/v1/workforce/employees").then(r=>r.json()),fetch(API+"/api/v1/workforce/departments").then(r=>r.json()),fetch(API+"/api/v1/opportunities").then(r=>r.json()),fetch(API+"/api/v1/treasury/stats").then(r=>r.json()),fetch(API+"/api/v1/metrics/health").then(r=>r.json()),fetch(API+"/api/v1/execution/tasks/queue-size").then(r=>r.json())]);setData({employees:e.employees||[],departments:d.departments||[],opportunities:o.opportunities||[],stats:s,health:h,queue:q.size||0});}catch(e){console.error(e);}setLoading(false);};
const wb=(t)=>({WATCH_ONLY:"bg-gray-700 text-gray-300",PAPER:"bg-blue-900 text-blue-300",PROPOSAL_ONLY:"bg-yellow-900 text-yellow-300",TREASURY_GATED:"bg-red-900 text-red-300"})[t]||"bg-gray-700";
const oc=(s)=>s==="approved"||s==="executed"?"text-green-400":s==="rejected"||s==="failed"?"text-red-400":s==="pending"?"text-yellow-400":"text-gray-400";
const analyzeOpportunity=async(employeeId,oppId)=>{setAnalyzing(true);try{const res=await fetch(API+"/api/v1/llm-employees/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({employee_id:employeeId,opportunity_id:oppId})});const result=await res.json();setAnalysisResult(result);}catch(e){console.error(e);}setAnalyzing(false);};
const runEmployeeScan=async(employeeId)=>{try{await fetch(API+"/api/v1/llm-employees/"+employeeId+"/scan",{method:"POST"});fetchData();}catch(e){console.error(e);}};
const{employees,departments,opportunities,stats,health,queue}=data;
return(
<main className="min-h-screen p-6 bg-[#0a0a0f] text-white">
<header className="mb-6">
<div className="flex justify-between items-start">
<div>
<h1 className="text-4xl font-bold text-[#c9a84c] mb-2">MEMBRA CompanyOS</h1>
<p className="text-sm text-gray-400">AI-Powered Autonomous Company Orchestration</p>
</div>
<div className="text-right">
<div className="text-xs text-gray-500">System Status</div>
<div className={health?.services?.redis==="up"?"text-green-400":"text-red-400"}>{health?.services?.redis==="up"?"Operational":"Degraded"}</div>
<div className="text-xs text-gray-500 mt-1">Queue: {queue} tasks</div>
</div>
</div>
<div className="mt-4 flex gap-2 flex-wrap">
{[{k:"overview",l:"Overview"},{k:"employees",l:"Employees"},{k:"opportunities",l:"Opportunities"},{k:"departments",l:"Departments"},{k:"execution",l:"Execution"},{k:"llm",l:"LLM Employees"}].map(t=>(
<button key={t.k} onClick={()=>setTab(t.k)} className={`px-3 py-1.5 text-xs rounded border ${tab===t.k?"bg-[#c9a84c] text-black border-[#c9a84c] font-medium":"bg-transparent text-gray-400 border-gray-700 hover:border-gray-600"}`}>{t.l}</button>
))}
</div>
</header>
{loading&&<div className="text-center text-gray-500 py-20">Loading...</div>}
{!loading&&tab==="overview"&&(<>
<section className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4 hover:border-[#c9a84c] transition-colors"><div className="text-xs text-gray-500 mb-1">Employees</div><div className="text-3xl font-bold">{employees.length}</div><div className="text-xs text-green-400 mt-1">60 Active</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4 hover:border-[#c9a84c] transition-colors"><div className="text-xs text-gray-500 mb-1">Departments</div><div className="text-3xl font-bold">{departments.length}</div><div className="text-xs text-gray-400 mt-1">12 Teams</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4 hover:border-[#c9a84c] transition-colors"><div className="text-xs text-gray-500 mb-1">Opportunities</div><div className="text-3xl font-bold">{opportunities.length}</div><div className="text-xs text-yellow-400 mt-1">{opportunities.filter(o=>o.approval_status==="pending").length} Pending</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4 hover:border-[#c9a84c] transition-colors"><div className="text-xs text-gray-500 mb-1">Executed</div><div className="text-3xl font-bold text-green-400">{stats?.opportunities?.executed||0}</div><div className="text-xs text-gray-400 mt-1">Total P&L</div></div>
</section>
<section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2"><span className="w-2 h-2 bg-[#c9a84c] rounded-full"></span>Recent Opportunities</h2>
<div className="space-y-2 max-h-64 overflow-y-auto">
{opportunities.slice(0,10).map(o=>(
<div key={o.id} className="flex justify-between text-xs bg-[#0a0a0f] p-3 rounded border border-gray-900 hover:border-gray-700">
<div className="flex-1"><span className="text-gray-400 font-medium">{o.chain}</span><span className="text-[#c9a84c] ml-2">{o.protocol}</span><div className="text-gray-500 mt-1">{o.opportunity_type}</div></div>
<div className="text-right ml-3"><div className="text-green-400 font-bold">+${o.expected_profit?.toFixed(0)}</div><div className={oc(o.approval_status)} text-xs mt-1">{o.approval_status}</div></div>
</div>
))}
{opportunities.length===0&&<div className="text-gray-600 text-xs py-8 text-center">No opportunities yet.</div>}
</div>
</div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2"><span className="w-2 h-2 bg-green-400 rounded-full"></span>System Health</h2>
<div className="space-y-3">
{health&&Object.entries(health.services).map(([k,v])=>(
<div key={k} className="flex justify-between items-center text-xs"><span className="text-gray-400 capitalize">{k}</span><span className={`px-2 py-0.5 rounded ${v==="up"?"bg-green-900 text-green-300":"bg-red-900 text-red-300"}`}>{v}</span></div>
))}
<div className="border-t border-gray-800 pt-3 mt-3">
<div className="flex justify-between text-xs text-gray-400 mb-1"><span>Task Queue</span><span>{queue}</span></div>
<div className="flex justify-between text-xs text-gray-400"><span>LLM Provider</span><span className="text-[#c9a84c]">Ready</span></div>
</div>
</div>
</div>
</section></>)}
{!loading&&tab==="employees"&&(<>
<section className="mb-4 flex gap-2">
<input type="text" placeholder="Search employees..." className="bg-[#12121a] border border-gray-800 rounded px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#c9a84c]" />
<button onClick={fetchData} className="px-3 py-1.5 text-xs bg-[#c9a84c] text-black rounded font-medium">Refresh</button>
</section>
<section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mt-6">
{employees.map(e=>(
<div key={e.employee_id} className="bg-[#12121a] border border-gray-800 rounded-lg p-4 hover:border-[#c9a84c] transition-all cursor-pointer" onClick={()=>setSelectedEmployee(e)}>
<div className="flex justify-between mb-2"><div className="text-sm font-semibold truncate">{e.name}</div><span className="text-[10px] px-2 py-0.5 rounded bg-green-900 text-green-300">{e.status}</span></div>
<div className="text-xs text-gray-500 mb-2">{e.title}</div>
<div className="text-[10px] text-gray-600 mb-3 uppercase">{e.department_id?.replace("dept-","")}</div>
<div className="flex gap-2 mb-2"><span className={`text-[10px] px-2 py-0.5 rounded ${wb(e.wallet_type)}`}>{e.wallet_type}</span><span className="text-[10px] text-gray-600">Limit:${e.risk_limit?.toLocaleString()}</span></div>
<div className="flex gap-2 mt-3"><button onClick={(ev)=>{ev.stopPropagation();runEmployeeScan(e.employee_id);}} className="flex-1 text-[10px] py-1 bg-[#c9a84c] text-black rounded font-medium">Scan</button><button onClick={(ev)=>{ev.stopPropagation();setSelectedEmployee(e);setTab("llm");}} className="flex-1 text-[10px] py-1 bg-gray-800 text-gray-300 rounded">LLM</button></div>
</div>
))}
</section>)}
{!loading&&tab==="opportunities"&&(<section className="mt-6">
<div className="flex gap-2 mb-4">
<button onClick={fetchData} className="px-3 py-1.5 text-xs bg-[#c9a84c] text-black rounded font-medium">Refresh</button>
<button className="px-3 py-1.5 text-xs bg-gray-800 text-gray-300 rounded">Filter</button>
</div>
<div className="overflow-x-auto">
<table className="w-full text-xs"><thead><tr className="text-left text-gray-500 border-b border-gray-800"><th className="pb-3">Type</th><th className="pb-3">Chain</th><th className="pb-3">Protocol</th><th className="pb-3">Profit</th><th className="pb-3">Conf</th><th className="pb-3">Risk</th><th className="pb-3">Compliance</th><th className="pb-3">Sim</th><th className="pb-3">Approval</th><th className="pb-3">Action</th></tr></thead><tbody>
{opportunities.map(o=>(
<tr key={o.id} className="border-b border-gray-900 hover:bg-[#1a1a24]">
<td className="py-3 text-gray-300">{o.opportunity_type}</td>
<td className="py-3 text-gray-400">{o.chain}</td>
<td className="py-3 text-[#c9a84c]">{o.protocol}</td>
<td className="py-3 text-green-400 font-bold">${o.expected_profit?.toFixed(0)}</td>
<td className="py-3 text-gray-400">{(o.confidence_score*100).toFixed(0)}%</td>
<td className="py-3 text-gray-400">{o.risk_score!==null?(o.risk_score*100).toFixed(0):"-"}</td>
<td className="py-3 text-gray-400">{o.compliance_score!==null?(o.compliance_score*100).toFixed(0):"-"}</td>
<td className="py-3 text-gray-500">{o.simulation_status}</td>
<td className={"py-3 "+oc(o.approval_status)}>{o.approval_status}</td>
<td className="py-3"><button onClick={()=>analyzeOpportunity("emp-f-01",o.id)} className="px-2 py-1 text-[10px] bg-[#c9a84c] text-black rounded">Analyze</button></td>
</tr>
))}
</tbody></table>
{opportunities.length===0&&<div className="text-gray-600 text-xs py-8 text-center">No opportunities yet.</div>}
</div>
</section>)}
{!loading&&tab==="departments"&&(<section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
{departments.map(d=>(
<div key={d.department_id} className="bg-[#12121a] border border-gray-800 rounded-lg p-5 hover:border-[#c9a84c] transition-colors">
<div className="text-lg font-bold text-[#c9a84c] mb-1">{d.name}</div>
<div className="text-xs text-gray-500 mb-3">{d.department_id}</div>
<div className="text-xs text-gray-400 mb-4 line-clamp-2">{d.mission}</div>
<div className="flex gap-2 mb-3"><span className={`text-[10px] px-2 py-0.5 rounded ${wb(d.wallet_policy)}`}>{d.wallet_policy}</span><span className="text-[10px] text-gray-600">Risk:{d.risk_tolerance}</span></div>
<div className="text-[10px] text-gray-600">Limit:${d.risk_limit?.toLocaleString()}</div>
<div className="text-[10px] text-gray-600 mt-1">Profit:{d.profit_mandate?.min_profit_percent||0}%</div>
</div>
))}
</section>)}
{!loading&&tab==="execution"&&(<section className="mt-6">
<div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500 mb-1">Task Queue</div><div className="text-3xl font-bold">{queue}</div><div className="text-xs text-gray-400 mt-1">Pending tasks</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500 mb-1">Opportunities</div><div className="text-3xl font-bold">{opportunities.length}</div><div className="text-xs text-gray-400 mt-1">Total tracked</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500 mb-1">Policy Engine</div><div className="text-3xl font-bold text-green-400">Active</div><div className="text-xs text-gray-400 mt-1">Enforcing rules</div></div>
</div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2"><span className="w-2 h-2 bg-[#c9a84c] rounded-full"></span>Execution Layer Status</h2>
<div className="grid grid-cols-2 md:grid-cols-3 gap-4">
{health&&Object.entries(health.services).map(([k,v])=>(
<div key={k} className="flex justify-between items-center text-xs border-b border-gray-900 pb-2"><span className="text-gray-400 capitalize">{k}</span><span className={`px-2 py-0.5 rounded ${v==="up"?"bg-green-900 text-green-300":"bg-red-900 text-red-300"}`}>{v}</span></div>
))}
</div>
</div></section>)}
{!loading&&tab==="llm"&&(<section className="mt-6">
{!selectedEmployee&&<div className="bg-[#12121a] border border-gray-800 rounded-lg p-6 text-center"><div className="text-gray-500 text-sm">Select an employee from the Employees tab to view LLM capabilities</div></div>}
{selectedEmployee&&(<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-lg font-bold text-[#c9a84c] mb-2">{selectedEmployee.name}</h2>
<div className="text-xs text-gray-500 mb-4">{selectedEmployee.title} · {selectedEmployee.department_id?.replace("dept-","")}</div>
<div className="space-y-3">
<div><div className="text-xs text-gray-500 mb-1">System Prompt</div><div className="text-xs text-gray-300 bg-[#0a0a0f] p-2 rounded max-h-24 overflow-y-auto">{selectedEmployee.system_prompt?.substring(0,200)}...</div></div>
<div><div className="text-xs text-gray-500 mb-1">Task Prompt</div><div className="text-xs text-gray-300 bg-[#0a0a0f] p-2 rounded max-h-24 overflow-y-auto">{selectedEmployee.task_prompt?.substring(0,200)}...</div></div>
<div className="flex gap-2 mt-4"><button onClick={()=>runEmployeeScan(selectedEmployee.employee_id)} className="flex-1 text-xs py-2 bg-[#c9a84c] text-black rounded font-medium">Run Scan</button><button onClick={()=>{setSelectedEmployee(null);setTab("employees");}} className="flex-1 text-xs py-2 bg-gray-800 text-gray-300 rounded">Back</button></div>
</div>
</div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3">LLM Analysis Result</h2>
{analyzing&&<div className="text-center text-gray-500 py-8">Analyzing with LLM...</div>}
{!analyzing&&analysisResult&&(<div className="space-y-3">
<div className="flex justify-between text-xs"><span className="text-gray-400">Decision</span><span className={`font-bold ${analysisResult.analysis?.decision==="approve"?"text-green-400":analysisResult.analysis?.decision==="reject"?"text-red-400":"text-yellow-400"}`}>{analysisResult.analysis?.decision}</span></div>
<div className="flex justify-between text-xs"><span className="text-gray-400">Confidence</span><span>{(analysisResult.analysis?.confidence*100).toFixed(0)}%</span></div>
<div className="flex justify-between text-xs"><span className="text-gray-400">Risk Assessment</span><span className="capitalize">{analysisResult.analysis?.risk_assessment}</span></div>
<div><div className="text-xs text-gray-500 mb-1">Reasoning</div><div className="text-xs text-gray-300 bg-[#0a0a0f] p-2 rounded">{analysisResult.analysis?.reasoning}</div></div>
<div><div className="text-xs text-gray-500 mb-1">Suggested Actions</div><div className="flex flex-wrap gap-1">{analysisResult.analysis?.suggested_actions?.map((a,i)=>(<span key={i} className="text-[10px] px-2 py-0.5 bg-gray-800 text-gray-300 rounded">{a}</span>))}</div></div>
</div>)}
{!analyzing&&!analysisResult&&<div className="text-center text-gray-500 py-8 text-xs">Select an opportunity to analyze</div>}
</div>
</div>)}
</section>)}
</main>
);
}