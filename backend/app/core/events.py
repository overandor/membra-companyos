"""MEMBRA CompanyOS — Typed Event Schemas.

All events flowing through the EventBus are defined here.
Audit-safe payloads with strict typing.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class MembraEvent(BaseModel):
    """Base event envelope."""
    event_id: str = Field(default_factory=lambda: f"evt-{datetime.now(timezone.utc).isoformat()}")
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str  # service / component that emitted the event
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    employee_id: Optional[str] = None
    department_id: Optional[str] = None


# --- Workforce Events ---
class EmployeeDiscoveredOpportunity(MembraEvent):
    event_type: str = "employee.discovered_opportunity"
    payload: Dict[str, Any] = Field(default_factory=dict)


class EmployeeSubmittedReport(MembraEvent):
    event_type: str = "employee.submitted_report"
    payload: Dict[str, Any] = Field(default_factory=dict)


class EmployeeHeartbeat(MembraEvent):
    event_type: str = "employee.heartbeat"
    payload: Dict[str, Any] = Field(default_factory=dict)


# --- Opportunity Lifecycle Events ---
class OpportunityDiscovered(MembraEvent):
    event_type: str = "opportunity.discovered"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunitySimulated(MembraEvent):
    event_type: str = "opportunity.simulated"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityRiskScored(MembraEvent):
    event_type: str = "opportunity.risk_scored"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityComplianceScored(MembraEvent):
    event_type: str = "opportunity.compliance_scored"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityApproved(MembraEvent):
    event_type: str = "opportunity.approved"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityRejected(MembraEvent):
    event_type: str = "opportunity.rejected"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityExecutionProposed(MembraEvent):
    event_type: str = "opportunity.execution_proposed"
    payload: Dict[str, Any] = Field(default_factory=dict)


class OpportunityExecuted(MembraEvent):
    event_type: str = "opportunity.executed"
    payload: Dict[str, Any] = Field(default_factory=dict)


# --- Treasury Events ---
class TreasuryRebalanceProposed(MembraEvent):
    event_type: str = "treasury.rebalance_proposed"
    payload: Dict[str, Any] = Field(default_factory=dict)


class TreasuryApprovalRequired(MembraEvent):
    event_type: str = "treasury.approval_required"
    payload: Dict[str, Any] = Field(default_factory=dict)


class TreasuryApproved(MembraEvent):
    event_type: str = "treasury.approved"
    payload: Dict[str, Any] = Field(default_factory=dict)


class TreasuryPolicyUpdated(MembraEvent):
    event_type: str = "treasury.policy_updated"
    payload: Dict[str, Any] = Field(default_factory=dict)


# --- Policy / Compliance Events ---
class PolicyViolationDetected(MembraEvent):
    event_type: str = "policy.violation_detected"
    payload: Dict[str, Any] = Field(default_factory=dict)


class ComplianceCheckCompleted(MembraEvent):
    event_type: str = "compliance.check_completed"
    payload: Dict[str, Any] = Field(default_factory=dict)


# --- System Events ---
class SystemHealthCheck(MembraEvent):
    event_type: str = "system.health_check"
    payload: Dict[str, Any] = Field(default_factory=dict)


class SystemShutdown(MembraEvent):
    event_type: str = "system.shutdown"
    payload: Dict[str, Any] = Field(default_factory=dict)
