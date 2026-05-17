"""MEMBRA CompanyOS — LLM Employee API Endpoints.

Endpoints for LLM-powered employee decision-making, task execution,
and status monitoring.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.services.llm_employee import get_llm_employee_service

router = APIRouter(prefix="/api/v1/llm-employees", tags=["llm-employees"])


class AnalyzeRequest(BaseModel):
    employee_id: str
    opportunity_id: str
    context: Optional[Dict[str, Any]] = None


class TaskRequest(BaseModel):
    employee_id: str
    task_type: str
    task_data: Dict[str, Any] = {}
    trace_id: Optional[str] = None


@router.post("/analyze")
async def analyze_opportunity(req: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """LLM employee analyzes an opportunity and provides decision."""
    service = get_llm_employee_service(db)
    result = await service.analyze_opportunity(
        req.employee_id,
        req.opportunity_id,
        req.context
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/execute-task")
async def execute_task(req: TaskRequest, db: AsyncSession = Depends(get_db)):
    """Execute a task using LLM employee capabilities."""
    service = get_llm_employee_service(db)
    result = await service.execute_employee_task(
        req.employee_id,
        req.task_type,
        req.task_data,
        req.trace_id
    )
    return result


@router.get("/{employee_id}/status")
async def get_employee_status(employee_id: str, db: AsyncSession = Depends(get_db)):
    """Get current status and recent activity of an LLM employee."""
    service = get_llm_employee_service(db)
    result = await service.get_employee_status(employee_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{employee_id}/scan")
async def scan_opportunities(employee_id: str, db: AsyncSession = Depends(get_db)):
    """Trigger opportunity scanning for a specific employee."""
    service = get_llm_employee_service(db)
    result = await service.execute_employee_task(
        employee_id,
        "scan_opportunities",
        {},
    )
    return result


@router.post("/{employee_id}/report")
async def generate_report(
    employee_id: str,
    report_type: str = "summary",
    data: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db)
):
    """Generate a report using the employee's LLM capabilities."""
    service = get_llm_employee_service(db)
    result = await service.execute_employee_task(
        employee_id,
        "generate_report",
        {"report_type": report_type, "data": data},
    )
    return result
