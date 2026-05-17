"""MEMBRA CompanyOS — Risk Scoring Service.

Scores opportunities on a 0-1 scale (0 = max risk, 1 = min risk).
No opportunity may proceed without a risk score.
"""
from typing import Dict, Any, Optional
import random
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.opportunity import OnChainOpportunity, ApprovalStatus
from app.config.employees import get_employee
from app.config.datasources import get_datasource
from app.services.proofbook_service import ProofBookService
import structlog

logger = structlog.get_logger()


class RiskScoringService:
    """Evaluates risk for on-chain opportunities."""

    # Chain risk weights (higher = safer)
    CHAIN_RISK = {
        "bitcoin": 0.90, "ethereum": 0.85, "solana": 0.75,
        "arbitrum": 0.80, "base": 0.80, "optimism": 0.78,
    }

    # Protocol risk weights
    PROTOCOL_RISK = {
        "aave": 0.92, "compound": 0.90, "uniswap": 0.88, "curve": 0.87,
        "lido": 0.91, "maker": 0.89, "jupiter": 0.85, "orca": 0.84,
        "raydium": 0.82, "marinade": 0.83, "solend": 0.80, "kamino": 0.79,
        "marginfi": 0.78, "drift": 0.77, "jito": 0.81, "pendle": 0.76,
        "etherfi": 0.75, "renzo": 0.74, "eigenlayer": 0.73,
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proof = ProofBookService(db)

    async def score(self, opportunity: OnChainOpportunity) -> Dict[str, Any]:
        """Compute risk score for an opportunity."""
        chain_risk = self.CHAIN_RISK.get(opportunity.chain, 0.60)
        protocol_risk = self.PROTOCOL_RISK.get(opportunity.protocol, 0.60)

        # Liquidity depth score (deeper = safer)
        liq_depth = opportunity.liquidity_depth or 1
        required = opportunity.required_capital or 1
        liquidity_score = min(1.0, liq_depth / (required * 3))

        # Confidence factor
        confidence_factor = opportunity.confidence_score or 0.5

        # Slippage risk (lower slippage = safer)
        slippage = opportunity.slippage_estimate or 1.0
        slippage_score = max(0.0, 1.0 - (slippage / 5.0))

        # Profit sustainability (moderate profit = more sustainable)
        profit_pct = opportunity.expected_profit_percent or 0
        sustainability_score = 1.0 if profit_pct < 5.0 else (0.7 if profit_pct < 20.0 else 0.4)

        # Composite score (weighted average)
        risk_score = (
            chain_risk * 0.20 +
            protocol_risk * 0.25 +
            liquidity_score * 0.20 +
            confidence_factor * 0.15 +
            slippage_score * 0.10 +
            sustainability_score * 0.10
        )

        # Risk flags
        flags = []
        if chain_risk < 0.70:
            flags.append("HIGH_CHAIN_RISK")
        if protocol_risk < 0.70:
            flags.append("HIGH_PROTOCOL_RISK")
        if liquidity_score < 0.30:
            flags.append("LOW_LIQUIDITY")
        if slippage > 2.0:
            flags.append("HIGH_SLIPPAGE")
        if profit_pct > 50:
            flags.append("SUSPICIOUSLY_HIGH_RETURN")

        # Risk level classification
        if risk_score >= 0.80:
            level = "LOW"
        elif risk_score >= 0.60:
            level = "MODERATE"
        elif risk_score >= 0.40:
            level = "HIGH"
        else:
            level = "CRITICAL"

        result = {
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "risk_score": round(risk_score, 4),
            "risk_level": level,
            "chain_risk": round(chain_risk, 4),
            "protocol_risk": round(protocol_risk, 4),
            "liquidity_score": round(liquidity_score, 4),
            "confidence_factor": round(confidence_factor, 4),
            "slippage_score": round(slippage_score, 4),
            "sustainability_score": round(sustainability_score, 4),
            "flags": flags,
            "recommendation": "",
        }

        if level in {"HIGH", "CRITICAL"}:
            result["recommendation"] = "REJECT: Risk too high. Do not proceed."
        elif flags:
            result["recommendation"] = "CONDITIONAL: Address flags before governance approval."
        else:
            result["recommendation"] = "APPROVE: Risk acceptable. Proceed to compliance review."

        opportunity.risk_score = round(risk_score, 4)
        opportunity.risk_review_json = result
        if opportunity.approval_status == ApprovalStatus.NOT_REVIEWED.value:
            opportunity.approval_status = ApprovalStatus.PENDING_COMPLIANCE.value
        await self.db.commit()
        await self.db.refresh(opportunity)

        await self.proof.log(
            event_type="opportunity_risk_scored",
            entity_type="opportunity",
            entity_id=opportunity.id,
            actor_id=opportunity.discovered_by_employee_id,
            data={
                "risk_score": risk_score,
                "risk_level": level,
                "flags": flags,
                "recommendation": result["recommendation"],
            },
        )
        logger.info("risk_score_complete", opportunity=opportunity.id, score=risk_score, level=level)
        return result

    async def score_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return None
        return await self.score(opp)
