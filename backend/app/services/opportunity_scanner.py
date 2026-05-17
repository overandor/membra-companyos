"""MEMBRA CompanyOS — Opportunity Scanner Service.

Discovers on-chain profit opportunities by scanning data sources.
All discoveries are logged to ProofBook.
No execution without simulation + risk + compliance + governance approval.
"""
from typing import Dict, Any, List, Optional
import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.models.opportunity import OnChainOpportunity, OpportunityType
from app.config.employees import get_employee, list_employees
from app.config.datasources import get_datasource
from app.services.proofbook_service import ProofBookService

logger = structlog.get_logger()


class OpportunityScannerService:
    """Scans data sources for on-chain profit opportunities."""

    OPPORTUNITY_TYPES = [t.value for t in OpportunityType]
    CHAINS = ["solana", "ethereum", "bitcoin", "arbitrum", "base", "optimism"]
    PROTOCOLS = [
        "jupiter", "orca", "raydium", "marinade", "lido",
        "aave", "uniswap", "curve", "compound", "maker",
        "jito", "drift", "kamino", "solend", "marginfi",
        "pendle", "etherfi", "renzo", "eigenlayer",
    ]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proof = ProofBookService(db)

    async def scan_all(self, employee_id: Optional[str] = None) -> List[OnChainOpportunity]:
        """Run a discovery scan. If employee_id provided, scan as that employee."""
        if employee_id:
            emp = get_employee(employee_id)
            return await self._scan_as_employee(emp)

        opportunities = []
        for emp in list_employees():
            if emp.status != "active":
                continue
            # Only finance, strategy, engineering, sales employees actively scan
            if emp.department_id in {
                "dept-finance", "dept-strategy", "dept-engineering",
                "dept-sales", "dept-product",
            }:
                try:
                    ops = await self._scan_as_employee(emp)
                    opportunities.extend(ops)
                except Exception as e:
                    logger.error("scan_failed", employee=emp.employee_id, error=str(e))
        return opportunities

    async def _scan_as_employee(self, emp) -> List[OnChainOpportunity]:
        """Simulate scanning based on employee role and approved data sources."""
        opportunities = []
        num_to_discover = random.randint(0, 3)

        for _ in range(num_to_discover):
            opp = await self._create_opportunity(emp)
            if opp:
                opportunities.append(opp)

        logger.info("scan_complete", employee=emp.employee_id, discovered=len(opportunities))
        return opportunities

    async def _create_opportunity(self, emp) -> Optional[OnChainOpportunity]:
        """Create a simulated opportunity for the employee."""
        opp_type = random.choice(self.OPPORTUNITY_TYPES)
        chain = random.choice(self.CHAINS)
        protocol = random.choice(self.PROTOCOLS)

        # Validate employee has access to data sources for this chain
        has_source = any(
            ds.startswith(chain) or ds in {"dex_screener", "birdeye", "jupiter_quote", "coingecko", "defillama"}
            for ds in emp.approved_data_sources
        )
        if not has_source:
            return None

        base_capital = random.uniform(1000, 500000)
        expected_profit = base_capital * random.uniform(0.001, 0.15)
        profit_pct = (expected_profit / base_capital) * 100
        fees = expected_profit * random.uniform(0.05, 0.30)
        slippage = random.uniform(0.01, 2.0)
        liquidity = base_capital * random.uniform(2, 100)
        confidence = random.uniform(0.3, 0.95)
        window = random.randint(60, 86400)

        # Enforce employee risk limit
        if base_capital > emp.risk_limit and emp.risk_limit > 0:
            base_capital = emp.risk_limit * 0.8
            expected_profit = base_capital * random.uniform(0.001, 0.05)

        opp = OnChainOpportunity(
            discovered_by_employee_id=emp.employee_id,
            chain=chain,
            protocol=protocol,
            opportunity_type=opp_type,
            asset_in=f"{chain.upper()}_ASSET_A",
            asset_out=f"{chain.upper()}_ASSET_B",
            expected_profit=round(expected_profit, 2),
            expected_profit_percent=round(profit_pct, 4),
            required_capital=round(base_capital, 2),
            estimated_fees=round(fees, 2),
            slippage_estimate=round(slippage, 4),
            liquidity_depth=round(liquidity, 2),
            execution_window_seconds=window,
            confidence_score=round(confidence, 4),
            simulation_status="not_simulated",
            approval_status="not_reviewed",
            execution_status="not_executed",
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=window),
            evidence_json={
                "data_sources_used": emp.approved_data_sources[:3],
                "tools_used": emp.tools[:2],
                "discovery_method": emp.role,
                "employee_name": emp.name,
                "discovery_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            recommended_action=self._recommend_action(opp_type, confidence, profit_pct),
        )
        self.db.add(opp)
        await self.db.commit()
        await self.db.refresh(opp)

        await self.proof.log(
            event_type="opportunity_discovered",
            entity_type="opportunity",
            entity_id=opp.id,
            actor_id=emp.employee_id,
            data={
                "opportunity_type": opp_type,
                "chain": chain,
                "protocol": protocol,
                "expected_profit": expected_profit,
                "confidence": confidence,
            },
        )
        return opp

    def _recommend_action(self, opp_type: str, confidence: float, profit_pct: float) -> str:
        if confidence < 0.5:
            return "REJECT: Low confidence. Gather more data before reconsideration."
        if profit_pct < 0.1:
            return "HOLD: Profit too small to justify fees and risk. Monitor for improvement."
        if confidence > 0.8 and profit_pct > 1.0:
            return "SIMULATE: High confidence and attractive returns. Proceed to simulation immediately."
        return "REVIEW: Moderate opportunity. Queue for risk and compliance review."

    async def list_opportunities(
        self,
        status: Optional[str] = None,
        opp_type: Optional[str] = None,
        chain: Optional[str] = None,
        min_confidence: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OnChainOpportunity]:
        query = select(OnChainOpportunity).order_by(desc(OnChainOpportunity.created_at))
        if status:
            if status in {"not_simulated", "pending", "simulated", "failed"}:
                query = query.where(OnChainOpportunity.simulation_status == status)
            elif status in {"not_reviewed", "pending_risk", "pending_compliance", "pending_finance", "pending_governance", "approved", "rejected"}:
                query = query.where(OnChainOpportunity.approval_status == status)
            elif status in {"not_executed", "proposed", "pending_treasury", "executed", "failed", "cancelled"}:
                query = query.where(OnChainOpportunity.execution_status == status)
        if opp_type:
            query = query.where(OnChainOpportunity.opportunity_type == opp_type)
        if chain:
            query = query.where(OnChainOpportunity.chain == chain)
        if min_confidence is not None:
            query = query.where(OnChainOpportunity.confidence_score >= min_confidence)
        result = await self.db.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def get_opportunity(self, opportunity_id: str) -> Optional[OnChainOpportunity]:
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        return result.scalar_one_or_none()
