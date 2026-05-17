"""MEMBRA CompanyOS — Shared Employee Schema.

Single source of truth for employee data structure.
No duplicated EmployeeConfig calls.
"""
from typing import List, Dict, Any
from pydantic import BaseModel
import hashlib


class EmployeeConfig(BaseModel):
    """Employee configuration — shared schema."""
    employee_id: str
    employee_number: int
    name: str
    department_id: str
    title: str
    role: str
    system_prompt: str
    task_prompt: str
    approved_data_sources: List[str]
    tools: List[str]
    wallet_address: str
    wallet_type: str
    permissions: List[str]
    risk_limit: float
    profit_mandate: str
    compliance_constraints: List[str]
    reporting_format: str
    status: str = "active"


def _w(name: str, dept: str, idx: int) -> str:
    """Deterministic watch-only wallet address."""
    return f"membra{hashlib.sha256(f'membra-{dept}-{name}-{idx}-watch-only'.encode()).hexdigest()[:32]}{idx:02d}"


BASE_PROMPT = (
    "You are a MEMBRA CompanyOS employee. "
    "You operate under strict compliance constraints. "
    "You may not promise guaranteed profit, use private keys, or move funds without treasury approval. "
    "You report in JSON with confidence scores. "
    "Every decision is logged to ProofBook."
)
