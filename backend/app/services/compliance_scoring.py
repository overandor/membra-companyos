"""MEMBRA CompanyOS — Compliance Scoring Service.

Scores opportunities on compliance dimension.
Blocks opportunities involving sanctioned entities, blacklisted contracts,
or prohibited jurisdictions. No execution without compliance score.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.opportunity import OnChainOpportunity, ApprovalStatus
from app.services.proofbook_service import ProofBookService
import structlog

logger = structlog.get_logger()


class ComplianceScoringService:
    """Evaluates regulatory and policy compliance for opportunities."""

    # Simulated blacklist for demonstration
    BLACKLISTED_CONTRACTS: List[str] = [
        "blacklisted_contract_1", "tornado_cash_proxied",
        "known_scam_token_v2", "mixer_proxy_xyz",
    ]
    BLACKLISTED_JURISDICTIONS = [" sanctioned_region_a", "embargoed_territory_b"]
    HIGH_RISK_TOKEN_CATEGORIES = ["privacy_coin", "mixing_service", "unregistered_security"]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proof = ProofBookService(db)

    async def score(self, opportunity: OnChainOpportunity) -> Dict[str, Any]:
        """Compute compliance score. Returns 0-1 (1 = fully compliant)."""
        flags = []
        checks_passed = []

        # 1. Blacklist check
        evidence = opportunity.evidence_json or {}
        if any(c in str(evidence) for c in self.BLACKLISTED_CONTRACTS):
            flags.append("BLACKLISTED_CONTRACT_DETECTED")
        else:
            checks_passed.append("blacklist_contract")

        # 2. Jurisdiction check
        if any(j in str(evidence) for j in self.BLACKLISTED_JURISDICTIONS):
            flags.append("PROHIBITED_JURISDICTION")
        else:
            checks_passed.append("jurisdiction")

        # 3. Simulation requirement check (hard rule)
        if opportunity.simulation_status != "simulated":
            flags.append("NOT_SIMULATED")
        else:
            checks_passed.append("simulation_completed")

        # 4. Risk score requirement check
        if opportunity.risk_score is None:
            flags.append("NO_RISK_SCORE")
        elif opportunity.risk_score < 0.30:
            flags.append("RISK_SCORE_TOO_LOW")
        else:
            checks_passed.append("risk_score_acceptable")

        # 5. Profit claim check (never promise guaranteed profit)
        rec = (opportunity.recommended_action or "").lower()
        if "guaranteed" in rec or "risk-free" in rec or "sure profit" in rec:
            flags.append("GUARANTEED_PROFIT_CLAIM")
        else:
            checks_passed.append("no_guaranteed_profit_language")

        # 6. Evidence completeness check
        ev = opportunity.evidence_json or {}
        if not ev.get("data_sources_used"):
            flags.append("MISSING_DATA_SOURCES")
        else:
            checks_passed.append("evidence_complete")

        # Score calculation
        total_checks = len(flags) + len(checks_passed)
        if total_checks == 0:
            compliance_score = 1.0
        else:
            compliance_score = len(checks_passed) / total_checks

        # Hard block if critical flags
        if any(f in {"BLACKLISTED_CONTRACT_DETECTED", "PROHIBITED_JURISDICTION", "GUARANTEED_PROFIT_CLAIM"} for f in flags):
            compliance_score = 0.0
            level = "BLOCKED"
            recommendation = "REJECT: Critical compliance violation. Opportunity permanently blocked."
        elif flags:
            level = "CONDITIONAL"
            recommendation = "CONDITIONAL: Address compliance flags before governance approval."
        else:
            level = "COMPLIANT"
            recommendation = "APPROVE: Fully compliant. Proceed to finance review."

        result = {
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "compliance_score": round(compliance_score, 4),
            "compliance_level": level,
            "flags": flags,
            "checks_passed": checks_passed,
            "recommendation": recommendation,
        }

        opportunity.compliance_score = round(compliance_score, 4)
        opportunity.compliance_review_json = result
        if opportunity.approval_status == ApprovalStatus.PENDING_COMPLIANCE.value:
            if level == "BLOCKED":
                opportunity.approval_status = ApprovalStatus.REJECTED.value
                opportunity.rejection_reason = "Compliance blocked: " + ", ".join(flags)
            elif level == "COMPLIANT":
                opportunity.approval_status = ApprovalStatus.PENDING_FINANCE.value
        await self.db.commit()
        await self.db.refresh(opportunity)

        await self.proof.log(
            event_type="opportunity_compliance_scored",
            entity_type="opportunity",
            entity_id=opportunity.id,
            actor_id=opportunity.discovered_by_employee_id,
            data={
                "compliance_score": compliance_score,
                "level": level,
                "flags": flags,
                "recommendation": recommendation,
            },
        )
        logger.info("compliance_score_complete", opportunity=opportunity.id, score=compliance_score, level=level)
        return result

    async def score_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return None
        return await self.score(opp)
