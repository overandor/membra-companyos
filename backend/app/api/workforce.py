"""MEMBRA CompanyOS — Workforce API Endpoints (/v1/workforce/*)."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.database import get_db
from app.config.departments import list_departments, get_department
from app.config.employees import list_employees, get_employee, EMPLOYEE_MAP
from app.config.datasources import list_datasources
from app.services.opportunity_scanner import OpportunityScannerService
from app.services.proofbook_service import ProofBookService
from app.services.agent_runtime import get_agent_runtime, RuntimeTask
from app.models.opportunity import OnChainOpportunity
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/workforce")


@router.get("/employees", tags=["workforce"])
async def get_employees(
    department_id: Optional[str] = None,
    wallet_type: Optional[str] = None,
    status: Optional[str] = None,
):
    """List all 60 employees with filters."""
    employees = list_employees(department_id=department_id)
    if wallet_type:
        employees = [e for e in employees if e.wallet_type == wallet_type]
    if status:
        employees = [e for e in employees if e.status == status]
    return {
        "count": len(employees),
        "employees": [
            {
                "employee_id": e.employee_id,
                "name": e.name,
                "department_id": e.department_id,
                "title": e.title,
                "role": e.role,
                "wallet_address": e.wallet_address,
                "wallet_type": e.wallet_type,
                "permissions": e.permissions,
                "risk_limit": e.risk_limit,
                "status": e.status,
                "profit_mandate": e.profit_mandate,
            }
            for e in employees
        ],
    }


@router.get("/employees/{employee_id}", tags=["workforce"])
async def get_employee_detail(employee_id: str):
    """Get detailed info for a single employee."""
    try:
        emp = get_employee(employee_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "employee_id": emp.employee_id,
        "name": emp.name,
        "department_id": emp.department_id,
        "title": emp.title,
        "role": emp.role,
        "system_prompt": emp.system_prompt,
        "task_prompt": emp.task_prompt,
        "approved_data_sources": emp.approved_data_sources,
        "tools": emp.tools,
        "wallet_address": emp.wallet_address,
        "wallet_type": emp.wallet_type,
        "permissions": emp.permissions,
        "risk_limit": emp.risk_limit,
        "profit_mandate": emp.profit_mandate,
        "compliance_constraints": emp.compliance_constraints,
        "reporting_format": emp.reporting_format,
        "status": emp.status,
    }


@router.post("/seed", tags=["workforce"])
async def seed_workforce(db: AsyncSession = Depends(get_db)):
    """Seed initial opportunities by running all active scanners."""
    scanner = OpportunityScannerService(db)
    opportunities = await scanner.scan_all()
    return {
        "status": "seeded",
        "opportunities_discovered": len(opportunities),
        "opportunity_ids": [o.id for o in opportunities],
    }


@router.post("/employees/{employee_id}/run", tags=["workforce"])
async def run_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run a single employee's scanning task."""
    try:
        emp = get_employee(employee_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")
    if emp.status != "active":
        raise HTTPException(status_code=400, detail="Employee not active")

    scanner = OpportunityScannerService(db)
    opportunities = await scanner.scan_all(employee_id=employee_id)
    return {
        "employee_id": employee_id,
        "name": emp.name,
        "opportunities_discovered": len(opportunities),
        "opportunity_ids": [o.id for o in opportunities],
    }


@router.get("/departments", tags=["workforce"])
async def get_departments():
    """List all 12 departments with full config."""
    depts = list_departments()
    return {
        "count": len(depts),
        "departments": [
            {
                "department_id": d.department_id,
                "name": d.name,
                "mission": d.mission,
                "risk_limit": d.risk_limit,
                "approved_data_sources": d.approved_data_sources,
                "allowed_tools": d.allowed_tools,
                "wallet_policy": d.wallet_policy,
                "reporting_schedule": d.reporting_schedule,
                "escalation_rules": d.escalation_rules,
                "risk_tolerance": d.risk_tolerance,
                "profit_mandate": d.profit_mandate,
                "compliance_constraints": d.compliance_constraints,
            }
            for d in depts
        ],
    }


@router.get("/contributions", tags=["workforce"])
async def get_contributions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    """Get employee opportunity discovery contributions."""
    result = await db.execute(
        select(
            OnChainOpportunity.discovered_by_employee_id,
            func.count(OnChainOpportunity.id).label("count"),
            func.sum(OnChainOpportunity.expected_profit).label("total_expected_profit"),
        )
        .group_by(OnChainOpportunity.discovered_by_employee_id)
        .order_by(desc("count"))
        .limit(limit)
    )
    rows = result.all()
    contributions = []
    for row in rows:
        emp = EMPLOYEE_MAP.get(row.discovered_by_employee_id)
        contributions.append({
            "employee_id": row.discovered_by_employee_id,
            "name": emp.name if emp else "Unknown",
            "department_id": emp.department_id if emp else None,
            "opportunities_discovered": row.count,
            "total_expected_profit": float(row.total_expected_profit or 0),
        })
    return {
        "count": len(contributions),
        "contributions": contributions,
    }


@router.post("/employees/{employee_id}/task", tags=["workforce"])
async def submit_employee_task(
    employee_id: str,
    task_type: str,
    payload: dict = None,
    priority: int = 3,
):
    """Submit a task to the Agent Runtime queue for an employee."""
    try:
        emp = get_employee(employee_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")
    runtime = await get_agent_runtime()
    task = RuntimeTask(
        task_id=f"task-{employee_id}-{__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}",
        task_type=task_type,
        employee_id=employee_id,
        department_id=emp.department_id,
        payload=payload or {},
        priority=priority,
    )
    await runtime.submit_task(task)
    await runtime.heartbeat(employee_id)
    return {"status": "submitted", "task_id": task.task_id, "employee_id": employee_id}


@router.get("/employees/{employee_id}/heartbeat", tags=["workforce"])
async def check_employee_heartbeat(employee_id: str):
    """Check if an employee has a recent heartbeat."""
    try:
        emp = get_employee(employee_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Employee not found")
    runtime = await get_agent_runtime()
    alive = await runtime.is_alive(employee_id)
    return {"employee_id": employee_id, "name": emp.name, "alive": alive}


@router.get("/queue", tags=["workforce"])
async def get_queue_status(department_id: Optional[str] = None):
    """Get Agent Runtime task queue size."""
    runtime = await get_agent_runtime()
    size = await runtime.pool.queue.size(department_id)
    return {"queue_size": size, "department_id": department_id}
