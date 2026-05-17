"""MEMBRA CompanyOS — Policy Engine.

Deterministic compliance checks, treasury approval gating,
risk thresholds, execution permissions.
Every decision is audit-safe and reproducible.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from app.services.event_bus import get_event_bus
from app.core.events import MembraEvent, PolicyViolationDetected, ComplianceCheckCompleted

logger = structlog.get_logger()


class PolicyResult(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    SIMULATE_ONLY = "simulate_only"


@dataclass
class PolicyRule:
    """A single policy rule."""
    name: str
    description: str
    check: callable
    action_on_fail: PolicyResult


@dataclass
class ExecutionContext:
    """Context for policy evaluation."""
    employee_id: str
    department_id: str
    action: str
    target: str
    amount: Optional[float] = None
    chain: Optional[str] = None
    risk_score: Optional[float] = None
    compliance_score: Optional[float] = None
    simulation_passed: bool = False
    metadata: Dict[str, Any] = None


class PolicyEngine:
    """Deterministic policy engine with built-in rules."""

    def __init__(self):
        self.rules: List[PolicyRule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Register MEMBRA's core safety policies."""
        self.rules.append(PolicyRule(
            name="no_execution_without_simulation",
            description="On-chain actions require simulation first",
            check=lambda ctx: ctx.simulation_passed or ctx.action in {"read", "scan", "propose"},
            action_on_fail=PolicyResult.SIMULATE_ONLY,
        ))
        self.rules.append(PolicyRule(
            name="no_direct_fund_moves",
            description="No employee can move funds without treasury approval",
            check=lambda ctx: ctx.action not in {"transfer", "withdraw", "spend", "execute"} or ctx.employee_id.startswith("treasury"),
            action_on_fail=PolicyResult.ESCALATE,
        ))
        self.rules.append(PolicyRule(
            name="risk_threshold",
            description="Reject opportunities above department risk tolerance",
            check=lambda ctx: ctx.risk_score is None or ctx.risk_score < 0.85,
            action_on_fail=PolicyResult.DENY,
        ))
        self.rules.append(PolicyRule(
            name="compliance_minimum",
            description="Require minimum compliance score before approval",
            check=lambda ctx: ctx.compliance_score is None or ctx.compliance_score >= 0.70,
            action_on_fail=PolicyResult.DENY,
        ))
        self.rules.append(PolicyRule(
            name="watch_only_no_proposal",
            description="WATCH_ONLY employees cannot propose execution",
            check=lambda ctx: ctx.action != "propose_execution",
            action_on_fail=PolicyResult.DENY,
        ))
        self.rules.append(PolicyRule(
            name="treasury_amount_limit",
            description="Treasury actions above $50k require governance",
            check=lambda ctx: ctx.amount is None or ctx.amount <= 50000 or ctx.department_id == "dept-governance",
            action_on_fail=PolicyResult.ESCALATE,
        ))

    def evaluate(self, ctx: ExecutionContext) -> Dict[str, Any]:
        """Evaluate all rules against an execution context."""
        violations = []
        final_result = PolicyResult.ALLOW
        for rule in self.rules:
            try:
                passed = rule.check(ctx)
            except Exception as e:
                logger.error("policy_check_error", rule=rule.name, error=str(e))
                passed = False
            if not passed:
                violations.append({
                    "rule": rule.name,
                    "description": rule.description,
                    "result": rule.action_on_fail.value,
                })
                # Escalate > Deny > Simulate > Allow
                if rule.action_on_fail == PolicyResult.ESCALATE:
                    final_result = PolicyResult.ESCALATE
                elif final_result not in (PolicyResult.ESCALATE,) and rule.action_on_fail == PolicyResult.DENY:
                    final_result = PolicyResult.DENY
                elif final_result == PolicyResult.ALLOW and rule.action_on_fail == PolicyResult.SIMULATE_ONLY:
                    final_result = PolicyResult.SIMULATE_ONLY

        result = {
            "result": final_result.value,
            "violations": violations,
            "context": {
                "employee_id": ctx.employee_id,
                "action": ctx.action,
                "amount": ctx.amount,
            },
        }
        logger.info("policy_evaluated", result=final_result.value, violations=len(violations))
        return result

    async def evaluate_async(self, ctx: ExecutionContext) -> Dict[str, Any]:
        """Async wrapper with event publishing."""
        result = self.evaluate(ctx)
        bus = await get_event_bus()
        if result["violations"]:
            await bus.publish(PolicyViolationDetected(
                source="policy_engine",
                payload=result,
                employee_id=ctx.employee_id,
                trace_id=ctx.metadata.get("trace_id") if ctx.metadata else None,
            ))
        else:
            await bus.publish(ComplianceCheckCompleted(
                source="policy_engine",
                payload=result,
                employee_id=ctx.employee_id,
                trace_id=ctx.metadata.get("trace_id") if ctx.metadata else None,
            ))
        return result


# Singleton
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
