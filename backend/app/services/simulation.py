"""MEMBRA CompanyOS — Simulation Service (Placeholder).

Simulates on-chain opportunities before any approval or execution.
Hard rule: Never execute without simulation.
"""
from typing import Dict, Any, Optional
import random
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.opportunity import OnChainOpportunity, SimulationStatus
from app.services.proofbook_service import ProofBookService
import structlog

logger = structlog.get_logger()


class SimulationService:
    """Placeholder simulation engine for on-chain opportunities.

    In production, this connects to:
    - Historical data replay
    - Forked mainnet simulation
    - Slippage modeling
    - Gas/fee estimation
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proof = ProofBookService(db)

    async def simulate(self, opportunity: OnChainOpportunity) -> Dict[str, Any]:
        """Run a simulation for an opportunity. Returns results dict."""
        if opportunity.simulation_status == SimulationStatus.SIMULATED.value:
            return opportunity.simulation_result_json

        # Placeholder simulation logic
        base_profit = opportunity.expected_profit or 0
        base_fees = opportunity.estimated_fees or 0
        slippage = opportunity.slippage_estimate or 0

        # Simulate execution with randomized variance
        execution_variance = random.uniform(0.85, 1.15)
        simulated_profit = base_profit * execution_variance
        simulated_fees = base_fees * random.uniform(0.9, 1.2)
        simulated_slippage = slippage * random.uniform(0.5, 2.0)

        net_profit = simulated_profit - simulated_fees - (opportunity.required_capital or 0) * (simulated_slippage / 100)
        net_profit_pct = (net_profit / opportunity.required_capital * 100) if opportunity.required_capital else 0

        # Simulation success probability based on confidence
        sim_success = random.random() < (opportunity.confidence_score or 0.5)

        result = {
            "simulated_at": datetime.now(timezone.utc).isoformat(),
            "simulation_version": "1.0.0-placeholder",
            "simulated_profit": round(simulated_profit, 2),
            "simulated_fees": round(simulated_fees, 2),
            "simulated_slippage": round(simulated_slippage, 4),
            "net_profit": round(net_profit, 2),
            "net_profit_percent": round(net_profit_pct, 4),
            "execution_variance": round(execution_variance, 4),
            "simulation_success": sim_success,
            "risk_flags": [],
            "warnings": [],
            "recommendation": "",
        }

        # Add warnings based on simulation
        if simulated_slippage > 1.0:
            result["warnings"].append("HIGH_SLIPPAGE: Execution slippage exceeds 1%")
        if net_profit < 0:
            result["warnings"].append("NEGATIVE_PROFIT: Net profit negative after fees and slippage")
            result["recommendation"] = "REJECT: Simulation shows loss. Do not proceed."
        elif net_profit_pct < 0.1:
            result["warnings"].append("LOW_PROFIT: Marginal profit may not justify risk")
            result["recommendation"] = "HOLD: Low margin. Re-scan for better opportunity."
        else:
            result["recommendation"] = "APPROVE_FOR_REVIEW: Simulation positive. Proceed to risk review."

        # Update opportunity
        opportunity.simulation_status = (
            SimulationStatus.SIMULATED.value if sim_success else SimulationStatus.FAILED.value
        )
        opportunity.simulation_result_json = result
        await self.db.commit()
        await self.db.refresh(opportunity)

        await self.proof.log(
            event_type="opportunity_simulated",
            entity_type="opportunity",
            entity_id=opportunity.id,
            actor_id=opportunity.discovered_by_employee_id,
            data={
                "net_profit": net_profit,
                "net_profit_pct": net_profit_pct,
                "success": sim_success,
                "recommendation": result["recommendation"],
            },
        )
        logger.info("simulation_complete", opportunity=opportunity.id, success=sim_success)
        return result

    async def simulate_by_id(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return None
        return await self.simulate(opp)
