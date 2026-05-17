"use client";
import{useState,useEffect}from"react";
const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export default function Dashboard(){
const[tab,setTab]=useState("overview");
const[data,setData]=useState({employees:[],departments:[],opportunities:[],stats:null});
const[loading,setLoading]=useState(true);
useEffect(()=>{fetchData();},[]);
const fetchData=async()=>{setLoading(true);try{const[e,d,o,s]=await Promise.all([fetch(API+"/api/v1/workforce/employees").then(r=>r.json()),fetch(API+"/api/v1/workforce/departments").then(r=>r.json()),fetch(API+"/api/v1/opportunities").then(r=>r.json()),fetch(API+"/api/v1/treasury/stats").then(r=>r.json()),]);setData({employees:e.employees||[],departments:d.departments||[],opportunities:o.opportunities||[],stats:s});}catch(e){console.error(e);}setLoading(false);};
const wb=(t)=>({WATCH_ONLY:"bg-gray-700 text-gray-300",PAPER:"bg-blue-900 text-blue-300",PROPOSAL_ONLY:"bg-yellow-900 text-yellow-300",TREASURY_GATED:"bg-red-900 text-red-300"})[t]||"bg-gray-700";
const oc=(s)=>s==="approved"||s==="executed"?"text-green-400":s==="rejected"||s==="failed"?"text-red-400":s==="pending"?"text-yellow-400":"text-gray-400";
const{employees,departments,opportunities,stats}=data;
return(
<main className="min-h-screen p-6 bg-[#0a0a0f] text-white">
<h1 className="text-3xl font-bold text-[#c9a84c]">MEMBRA CompanyOS</h1>
<p className="text-sm text-gray-400">60-Employee On-Chain Profit Intelligence</p>
<div className="mt-3 flex gap-2">
{[{k:"overview",l:"Overview"},{k:"employees",l:"Employees"},{k:"opportunities",l:"Opportunities"},{k:"departments",l:"Departments"}].map(t=>(
<button key={t.k} onClick={()=>setTab(t.k)} className={`px-3 py-1 text-xs rounded border ${tab===t.k?"bg-[#c9a84c] text-black border-[#c9a84c]":"bg-transparent text-gray-400 border-gray-700"}`}>{t.l}</button>
))}
</div>
{loading&&<div className="text-center text-gray-500 py-20">Loading...</div>}
{!loading&&tab==="overview"&&(<><section className="grid grid-cols-2 md:grid-cols-4 gap-4 my-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500">Employees</div><div className="text-2xl font-bold">{employees.length}</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500">Departments</div><div className="text-2xl font-bold">{departments.length}</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500">Opportunities</div><div className="text-2xl font-bold">{opportunities.length}</div></div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4"><div className="text-xs text-gray-500">Executed</div><div className="text-2xl font-bold text-green-400">{stats?.opportunities?.executed||0}</div></div>
</section>
<section className="grid grid-cols-1 md:grid-cols-2 gap-6">
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3">Recent Opportunities</h2>
<div className="space-y-2 max-h-64 overflow-y-auto">
{opportunities.slice(0,10).map(o=>(
<div key={o.id} className="flex justify-between text-xs bg-[#0a0a0f] p-2 rounded">
<div><span className="text-gray-400">{o.chain}</span><span className="text-[#c9a84c] ml-1">{o.protocol}</span><div className="text-gray-500">{o.opportunity_type}</div></div>
<div className="text-right"><div className="text-green-400">+${o.expected_profit?.toFixed(0)}</div><div className={oc(o.approval_status)}>{o.approval_status}</div></div>
</div>
))}
{opportunities.length===0&&<div className="text-gray-600 text-xs">No opportunities yet.</div>}
</div>
</div>
<div className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<h2 className="text-sm font-semibold text-gray-300 mb-3">Wallet Modes</h2>
{[{wt:"WATCH_ONLY",l:"Watch Only"},{wt:"PAPER",l:"Paper"},{wt:"PROPOSAL_ONLY",l:"Proposal"},{wt:"TREASURY_GATED",l:"Treasury"}].map(w=>(
<div key={w.wt} className="flex justify-between text-xs mb-2"><span className={`px-2 py-0.5 rounded ${wb(w.wt)}`}>{w.l}</span><span className="text-gray-400">{employees.filter(e=>e.wallet_type===w.wt).length}</span></div>
))}
</div>
</section></>)}
{!loading&&tab==="employees"&&(<section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mt-6">
{employees.map(e=>(
<div key={e.employee_id} className="bg-[#12121a] border border-gray-800 rounded-lg p-3 hover:border-gray-600">
<div className="flex justify-between mb-1"><div className="text-sm font-semibold truncate">{e.name}</div><span className="text-[10px] px-1.5 py-0.5 rounded bg-green-900 text-green-300">{e.status}</span></div>
<div className="text-xs text-gray-500 mb-1">{e.title}</div>
<div className="text-[10px] text-gray-600 mb-2">{e.department_id?.replace("dept-","")}</div>
<div className="flex gap-2"><span className={`text-[10px] px-1.5 py-0.5 rounded ${wb(e.wallet_type)}`}>{e.wallet_type}</span><span className="text-[10px] text-gray-600">${e.risk_limit?.toLocaleString()}</span></div>
</div>
))}
</section>)}
{!loading&&tab==="opportunities"&&(<section className="mt-6">
<button onClick={fetchData} className="px-3 py-1 text-xs bg-[#c9a84c] text-black rounded font-medium mb-4">Refresh</button>
<div className="overflow-x-auto">
<table className="w-full text-xs"><thead><tr className="text-left text-gray-500 border-b border-gray-800"><th className="pb-2">Type</th><th className="pb-2">Chain</th><th className="pb-2">Protocol</th><th className="pb-2">Profit</th><th className="pb-2">Conf</th><th className="pb-2">Risk</th><th className="pb-2">Compliance</th><th className="pb-2">Sim</th><th className="pb-2">Approval</th><th className="pb-2">Exec</th></tr></thead><tbody>
{opportunities.map(o=>(
<tr key={o.id} className="border-b border-gray-900 hover:bg-[#1a1a24]">
<td className="py-2 text-gray-300">{o.opportunity_type}</td>
<td className="py-2 text-gray-400">{o.chain}</td>
<td className="py-2 text-[#c9a84c]">{o.protocol}</td>
<td className="py-2 text-green-400">${o.expected_profit?.toFixed(0)}</td>
<td className="py-2 text-gray-400">{(o.confidence_score*100).toFixed(0)}%</td>
<td className="py-2 text-gray-400">{o.risk_score!==null?(o.risk_score*100).toFixed(0):"-"}</td>
<td className="py-2 text-gray-400">{o.compliance_score!==null?(o.compliance_score*100).toFixed(0):"-"}</td>
<td className="py-2 text-gray-500">{o.simulation_status}</td>
<td className={"py-2 "+oc(o.approval_status)}>{o.approval_status}</td>
<td className={"py-2 "+oc(o.execution_status)}>{o.execution_status}</td>
</tr>
))}
</tbody></table>
{opportunities.length===0&&<div className="text-gray-600 text-xs py-8 text-center">No opportunities yet.</div>}
</div>
</section>)}
{!loading&&tab==="departments"&&(<section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
{departments.map(d=>(
<div key={d.department_id} className="bg-[#12121a] border border-gray-800 rounded-lg p-4">
<div className="text-lg font-bold text-[#c9a84c] mb-1">{d.name}</div>
<div className="text-xs text-gray-500 mb-2">{d.department_id}</div>
<div className="text-xs text-gray-400 mb-3 line-clamp-2">{d.mission}</div>
<div className="flex gap-2 mb-2"><span className={`text-[10px] px-1.5 py-0.5 rounded ${wb(d.wallet_policy)}`}>{d.wallet_policy}</span><span className="text-[10px] text-gray-600">Risk:{d.risk_tolerance}</span></div>
<div className="text-[10px] text-gray-600">Limit:${d.risk_limit?.toLocaleString()}</div>
</div>
))}
</section>)}
</main>
);
}