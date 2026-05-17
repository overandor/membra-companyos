"""MEMBRA CompanyOS — Full Employee Registry (60 Employees).

Dynamically generated from shared schemas, department configs, and role templates.
"""
from typing import List, Dict
from app.config.employee_schema import EmployeeConfig
from app.config.employee_generator import generate_employees

ALL_EMPLOYEES: List[EmployeeConfig] = generate_employees()
EMPLOYEE_MAP: Dict[str, EmployeeConfig] = {e.employee_id: e for e in ALL_EMPLOYEES}


def get_employee(employee_id: str) -> EmployeeConfig:
    if employee_id not in EMPLOYEE_MAP:
        raise ValueError(f"Employee {employee_id} not found")
    return EMPLOYEE_MAP[employee_id]


def list_employees(department_id: str = None) -> List[EmployeeConfig]:
    if department_id:
        return [e for e in ALL_EMPLOYEES if e.department_id == department_id]
    return ALL_EMPLOYEES


def count_employees() -> int:
    return len(ALL_EMPLOYEES)
