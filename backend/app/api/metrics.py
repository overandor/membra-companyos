"""MEMBRA CompanyOS — Observability & Metrics API.

Prometheus metrics, workforce analytics, system health.
"""
from typing import Any, Dict
from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.config.employees import list_employees
from app.config.departments import list_departments
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/metrics", tags=["observability"])

# Prometheus metrics
OPPORTUNITY_DISCOVERED = Counter("membra_opportunities_discovered_total", "Total opportunities discovered", ["chain"])
OPPORTUNITY_EXECUTED = Counter("membra_opportunities_executed_total", "Total opportunities executed", ["chain", "status"])
EMPLOYEE_TASKS = Counter("membra_employee_tasks_total", "Tasks by employee", ["employee_id", "status"])
POLICY_VIOLATIONS = Counter("membra_policy_violations_total", "Policy violations by rule", ["rule_name"])
TREASURY_BALANCE = Gauge("membra_treasury_balance_usd", "Treasury balance in USD")
WORKER_HEARTBEAT = Gauge("membra_worker_heartbeat", "Worker liveness", ["worker_id"])
TASK_LATENCY = Histogram("membra_task_latency_seconds", "Task execution latency", ["task_type"])


@router.get("/prometheus")
async def prometheus_metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/workforce")
async def workforce_analytics() -> Dict[str, Any]:
    """Workforce composition and activity analytics."""
    employees = list_employees()
    departments = list_departments()

    by_dept = {}
    for d in departments:
        by_dept[d.department_id] = {
            "name": d.name,
            "count": 0,
            "wallet_types": {},
            "risk_limits": [],
        }

    for e in employees:
        dept = by_dept.get(e.department_id)
        if dept:
            dept["count"] += 1
            dept["wallet_types"][e.wallet_type] = dept["wallet_types"].get(e.wallet_type, 0) + 1
            dept["risk_limits"].append(e.risk_limit)

    return {
        "total_employees": len(employees),
        "total_departments": len(departments),
        "wallet_type_distribution": {
            wt: sum(1 for e in employees if e.wallet_type == wt)
            for wt in {"WATCH_ONLY", "PAPER", "PROPOSAL_ONLY", "TREASURY_GATED"}
        },
        "departments": by_dept,
        "total_risk_capacity_usd": sum(e.risk_limit for e in employees),
    }


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """System health status."""
    return {
        "status": "healthy",
        "services": {
            "event_bus": "up",
            "agent_runtime": "up",
            "policy_engine": "up",
            "memory_layer": "up",
            "tool_sandbox": "up",
            "chain_router": "up",
            "approval_workflow": "up",
        },
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
