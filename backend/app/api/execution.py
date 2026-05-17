"""MEMBRA CompanyOS — Execution Layer API.

Endpoints for Event Bus, Agent Runtime, Memory, Tool Sandbox,
Chain Adapters, and Approval Workflow.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.event_bus import get_event_bus
from app.services.agent_runtime import get_agent_runtime, RuntimeTask
from app.services.memory import get_memory_layer
from app.services.tool_sandbox import get_tool_sandbox, ToolCall
from app.services.chain_adapters import get_chain_router, ChainTransaction
from app.services.policy_engine import get_policy_engine, ExecutionContext
from app.services.approval_workflow import get_approval_workflow

router = APIRouter(prefix="/api/v1/execution", tags=["execution"])


# --- Event Bus ---
class PublishEvent(BaseModel):
    event_type: str
    source: str = "api"
    payload: Dict[str, Any] = {}
    employee_id: Optional[str] = None
    trace_id: Optional[str] = None


@router.post("/events/publish")
async def publish_event(event: PublishEvent):
    bus = await get_event_bus()
    from app.core.events import MembraEvent
    await bus.publish(MembraEvent(
        event_type=event.event_type,
        source=event.source,
        payload=event.payload,
        employee_id=event.employee_id,
        trace_id=event.trace_id,
    ))
    return {"status": "published"}


# --- Agent Runtime ---
class SubmitTask(BaseModel):
    task_id: str
    task_type: str
    employee_id: str
    department_id: str
    payload: Dict[str, Any] = {}
    priority: int = 3
    trace_id: Optional[str] = None


@router.post("/tasks/submit")
async def submit_task(task: SubmitTask):
    runtime = await get_agent_runtime()
    rt = RuntimeTask(
        task_id=task.task_id,
        task_type=task.task_type,
        employee_id=task.employee_id,
        department_id=task.department_id,
        payload=task.payload,
        priority=task.priority,
        trace_id=task.trace_id,
    )
    await runtime.submit_task(rt)
    return {"status": "submitted", "task_id": task.task_id}


@router.get("/tasks/queue-size")
async def queue_size(department_id: Optional[str] = None):
    runtime = await get_agent_runtime()
    size = await runtime.pool.queue.size(department_id)
    return {"size": size}


@router.get("/heartbeat/{employee_id}")
async def employee_heartbeat(employee_id: str):
    runtime = await get_agent_runtime()
    alive = await runtime.is_alive(employee_id)
    return {"employee_id": employee_id, "alive": alive}


# --- Memory Layer ---
class StoreMemory(BaseModel):
    namespace: str
    key: str
    data: Dict[str, Any]
    embedding: Optional[List[float]] = None


@router.post("/memory/store")
async def store_memory(req: StoreMemory):
    mem = await get_memory_layer()
    await mem.store.store(req.namespace, req.key, req.data, req.embedding)
    return {"status": "stored"}


@router.get("/memory/{namespace}/{key}")
async def get_memory(namespace: str, key: str):
    mem = await get_memory_layer()
    entry = await mem.store.retrieve(namespace, key)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    return entry


# --- Tool Sandbox ---
class ExecuteTool(BaseModel):
    tool_name: str
    employee_id: str
    department_id: str
    args: Dict[str, Any] = {}
    trace_id: Optional[str] = None


@router.post("/tools/execute")
async def execute_tool(req: ExecuteTool):
    sandbox = get_tool_sandbox()
    call = ToolCall(
        tool_name=req.tool_name,
        employee_id=req.employee_id,
        department_id=req.department_id,
        args=req.args,
        trace_id=req.trace_id,
    )
    result = await sandbox.execute(call)
    return {
        "success": result.success,
        "output": result.output,
        "execution_time_ms": result.execution_time_ms,
        "error": result.error,
        "blocked_by_policy": result.blocked_by_policy,
    }


@router.get("/tools/list")
async def list_tools():
    sandbox = get_tool_sandbox()
    return {"tools": sandbox.list_tools()}


# --- Chain Adapters ---
class SimulateTx(BaseModel):
    tx_id: str
    chain: str
    from_address: str
    to_address: str
    amount: float
    token: str = "USDC"


@router.post("/chain/simulate")
async def simulate_transaction(req: SimulateTx):
    router = get_chain_router()
    tx = ChainTransaction(
        tx_id=req.tx_id,
        chain=req.chain,
        from_address=req.from_address,
        to_address=req.to_address,
        amount=req.amount,
        token=req.token,
    )
    result = await router.simulate(tx)
    return result


# --- Policy Engine ---
class PolicyCheck(BaseModel):
    employee_id: str
    department_id: str
    action: str
    target: str
    amount: Optional[float] = None
    chain: Optional[str] = None
    risk_score: Optional[float] = None
    compliance_score: Optional[float] = None
    simulation_passed: bool = False


@router.post("/policy/check")
async def check_policy(req: PolicyCheck):
    engine = get_policy_engine()
    ctx = ExecutionContext(
        employee_id=req.employee_id,
        department_id=req.department_id,
        action=req.action,
        target=req.target,
        amount=req.amount,
        chain=req.chain,
        risk_score=req.risk_score,
        compliance_score=req.compliance_score,
        simulation_passed=req.simulation_passed,
    )
    result = engine.evaluate(ctx)
    return result


# --- Approval Workflow ---
class CreateApproval(BaseModel):
    request_id: str
    opportunity_id: str
    employee_id: str
    department_id: str


class AdvanceApproval(BaseModel):
    request_id: str
    signer_id: str
    decision: str  # approve, reject, escalate
    notes: str = ""


@router.post("/approvals/create")
async def create_approval(req: CreateApproval):
    wf = get_approval_workflow()
    request = await wf.create_request(
        request_id=req.request_id,
        opportunity_id=req.opportunity_id,
        employee_id=req.employee_id,
        department_id=req.department_id,
    )
    return {
        "request_id": request.request_id,
        "current_stage": request.current_stage.value,
        "stages": [s.value for s in request.stages],
    }


@router.post("/approvals/advance")
async def advance_approval(req: AdvanceApproval):
    wf = get_approval_workflow()
    request = await wf.advance(req.request_id, req.signer_id, req.decision, req.notes)
    return {
        "request_id": request.request_id,
        "current_stage": request.current_stage.value,
        "signatures": request.signatures,
    }


@router.get("/approvals/{request_id}")
async def get_approval(request_id: str):
    wf = get_approval_workflow()
    req = wf.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {
        "request_id": req.request_id,
        "opportunity_id": req.opportunity_id,
        "current_stage": req.current_stage.value,
        "stages": [s.value for s in req.stages],
        "signatures": req.signatures,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }
