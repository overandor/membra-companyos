"""MEMBRA CompanyOS — Approval Workflow.

Multi-stage reviews, treasury gating, human escalation queue,
governance signatures. No execution without proper approval chain.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import structlog

from app.services.event_bus import get_event_bus
from app.core.events import (
    MembraEvent,
    OpportunityApproved,
    OpportunityRejected,
    OpportunityExecutionProposed,
    TreasuryApprovalRequired,
    TreasuryApproved,
)

logger = structlog.get_logger()


class ApprovalStage(Enum):
    PENDING = "pending"
    SIMULATION_REVIEW = "simulation_review"
    RISK_REVIEW = "risk_review"
    COMPLIANCE_REVIEW = "compliance_review"
    TREASURY_REVIEW = "treasury_review"
    GOVERNANCE_VOTE = "governance_vote"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class ApprovalRequest:
    request_id: str
    opportunity_id: str
    employee_id: str
    department_id: str
    stages: List[ApprovalStage] = field(default_factory=list)
    current_stage: ApprovalStage = ApprovalStage.PENDING
    signatures: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class ApprovalWorkflow:
    """Multi-stage approval workflow with treasury gating."""

    def __init__(self):
        self._requests: Dict[str, ApprovalRequest] = {}
        self._stage_handlers: Dict[ApprovalStage, callable] = {}
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._stage_handlers = {
            ApprovalStage.SIMULATION_REVIEW: self._handle_simulation_review,
            ApprovalStage.RISK_REVIEW: self._handle_risk_review,
            ApprovalStage.COMPLIANCE_REVIEW: self._handle_compliance_review,
            ApprovalStage.TREASURY_REVIEW: self._handle_treasury_review,
            ApprovalStage.GOVERNANCE_VOTE: self._handle_governance_vote,
        }

    async def create_request(
        self,
        request_id: str,
        opportunity_id: str,
        employee_id: str,
        department_id: str,
        required_stages: Optional[List[ApprovalStage]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        stages = required_stages or [
            ApprovalStage.SIMULATION_REVIEW,
            ApprovalStage.RISK_REVIEW,
            ApprovalStage.COMPLIANCE_REVIEW,
            ApprovalStage.TREASURY_REVIEW,
        ]
        req = ApprovalRequest(
            request_id=request_id,
            opportunity_id=opportunity_id,
            employee_id=employee_id,
            department_id=department_id,
            stages=stages,
            current_stage=stages[0] if stages else ApprovalStage.APPROVED,
            metadata=metadata or {},
        )
        self._requests[request_id] = req
        logger.info("approval_request_created", request_id=request_id, opp=opportunity_id)
        bus = await get_event_bus()
        await bus.publish(OpportunityExecutionProposed(
            source="approval_workflow",
            payload={"request_id": request_id, "stage": req.current_stage.value},
            employee_id=employee_id,
        ))
        return req

    async def advance(self, request_id: str, signer_id: str, decision: str, notes: str = "") -> ApprovalRequest:
        """Advance an approval request with a decision."""
        req = self._requests.get(request_id)
        if req is None:
            raise ValueError(f"Approval request not found: {request_id}")

        req.signatures.append({
            "stage": req.current_stage.value,
            "signer_id": signer_id,
            "decision": decision,
            "notes": notes,
            "signed_at": datetime.now(timezone.utc).isoformat(),
        })

        if decision == "reject":
            req.current_stage = ApprovalStage.REJECTED
            req.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("approval_rejected", request_id=request_id, signer=signer_id)
            bus = await get_event_bus()
            await bus.publish(OpportunityRejected(
                source="approval_workflow",
                payload={"request_id": request_id, "signer": signer_id, "notes": notes},
                employee_id=req.employee_id,
            ))
            return req

        if decision == "escalate":
            req.current_stage = ApprovalStage.ESCALATED
            req.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("approval_escalated", request_id=request_id, signer=signer_id)
            bus = await get_event_bus()
            await bus.publish(TreasuryApprovalRequired(
                source="approval_workflow",
                payload={"request_id": request_id, "reason": notes},
                employee_id=req.employee_id,
            ))
            return req

        # Advance to next stage
        current_idx = req.stages.index(req.current_stage) if req.current_stage in req.stages else -1
        next_idx = current_idx + 1
        if next_idx < len(req.stages):
            req.current_stage = req.stages[next_idx]
            req.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("approval_advanced", request_id=request_id, stage=req.current_stage.value)
        else:
            req.current_stage = ApprovalStage.APPROVED
            req.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info("approval_approved", request_id=request_id)
            bus = await get_event_bus()
            await bus.publish(OpportunityApproved(
                source="approval_workflow",
                payload={"request_id": request_id, "opportunity_id": req.opportunity_id},
                employee_id=req.employee_id,
            ))
            await bus.publish(TreasuryApproved(
                source="approval_workflow",
                payload={"request_id": request_id, "opportunity_id": req.opportunity_id},
                employee_id=req.employee_id,
            ))
        return req

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._requests.get(request_id)

    def list_requests(self, status: Optional[str] = None) -> List[ApprovalRequest]:
        reqs = list(self._requests.values())
        if status:
            reqs = [r for r in reqs if r.current_stage.value == status]
        return reqs

    # --- Stage Handlers (placeholder hooks for deterministic logic) ---
    async def _handle_simulation_review(self, req: ApprovalRequest) -> bool:
        return req.metadata.get("simulation_passed", False)

    async def _handle_risk_review(self, req: ApprovalRequest) -> bool:
        return req.metadata.get("risk_score", 1.0) < 0.85

    async def _handle_compliance_review(self, req: ApprovalRequest) -> bool:
        return req.metadata.get("compliance_score", 0.0) >= 0.70

    async def _handle_treasury_review(self, req: ApprovalRequest) -> bool:
        amount = req.metadata.get("amount", 0)
        return amount <= 50000

    async def _handle_governance_vote(self, req: ApprovalRequest) -> bool:
        return req.metadata.get("governance_quorum_met", False)


# Singleton
_approval_workflow: Optional[ApprovalWorkflow] = None


def get_approval_workflow() -> ApprovalWorkflow:
    global _approval_workflow
    if _approval_workflow is None:
        _approval_workflow = ApprovalWorkflow()
    return _approval_workflow
