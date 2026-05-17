"""MEMBRA CompanyOS — Treasury Service.

Manages treasury policies, wallet registry, and approval queues.
No employee may move funds directly unless a treasury approval policy authorizes it.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.opportunity import OnChainOpportunity, WalletRegistry, TreasuryPolicy, ApprovalStatus, ExecutionStatus
from app.config.employees import list_employees
from app.services.proofbook_service import ProofBookService
import structlog

logger = structlog.get_logger()


class TreasuryService:
    """Treasury policy and wallet management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.proof = ProofBookService(db)

    async def list_wallets(self, chain: Optional[str] = None) -> List[WalletRegistry]:
        query = select(WalletRegistry).order_by(desc(WalletRegistry.created_at))
        if chain:
            query = query.where(WalletRegistry.chain == chain)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_policies(self, status: Optional[str] = None) -> List[TreasuryPolicy]:
        query = select(TreasuryPolicy).order_by(desc(TreasuryPolicy.created_at))
        if status:
            query = query.where(TreasuryPolicy.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def propose_execution(self, opportunity_id: str, proposer_id: str) -> Dict[str, Any]:
        """Propose an approved opportunity for treasury execution."""
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "Opportunity not found"}

        if opp.approval_status != ApprovalStatus.APPROVED.value:
            return {"error": f"Opportunity not approved. Current status: {opp.approval_status}"}

        if opp.execution_status != ExecutionStatus.NOT_EXECUTED.value:
            return {"error": f"Opportunity already in execution status: {opp.execution_status}"}

        opp.execution_status = ExecutionStatus.PENDING_TREASURY.value
        opp.execution_result_json = {
            "proposed_at": datetime.now(timezone.utc).isoformat(),
            "proposer_id": proposer_id,
            "status": "pending_multisig",
            "required_approvals": 3,
            "current_approvals": 0,
        }
        await self.db.commit()
        await self.db.refresh(opp)

        await self.proof.log(
            event_type="execution_proposed",
            entity_type="opportunity",
            entity_id=opportunity_id,
            actor_id=proposer_id,
            data={
                "required_approvals": 3,
                "proposed_at": opp.execution_result_json["proposed_at"],
            },
        )
        logger.info("execution_proposed", opportunity=opportunity_id, proposer=proposer_id)
        return {"status": "proposed", "opportunity_id": opportunity_id, "required_approvals": 3}

    async def approve_execution(self, opportunity_id: str, approver_id: str) -> Dict[str, Any]:
        """Record a treasury approval for execution (simulated multisig step)."""
        result = await self.db.execute(
            select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id)
        )
        opp = result.scalar_one_or_none()
        if not opp:
            return {"error": "Opportunity not found"}

        if opp.execution_status != ExecutionStatus.PENDING_TREASURY.value:
            return {"error": f"Opportunity not pending treasury. Status: {opp.execution_status}"}

        exec_json = opp.execution_result_json or {}
        current = exec_json.get("current_approvals", 0) + 1
        required = exec_json.get("required_approvals", 3)
        exec_json["current_approvals"] = current
        exec_json["approvers"] = exec_json.get("approvers", []) + [approver_id]

        if current >= required:
            opp.execution_status = ExecutionStatus.EXECUTED.value
            exec_json["executed_at"] = datetime.now(timezone.utc).isoformat()
            exec_json["tx_hash"] = f"simulated_tx_{opportunity_id}_{datetime.now(timezone.utc).timestamp()}"
            logger.info("execution_completed", opportunity=opportunity_id, tx=exec_json["tx_hash"])
        else:
            logger.info("execution_approval_received", opportunity=opportunity_id, current=current, required=required)

        opp.execution_result_json = exec_json
        await self.db.commit()
        await self.db.refresh(opp)

        await self.proof.log(
            event_type="execution_approved" if current < required else "execution_completed",
            entity_type="opportunity",
            entity_id=opportunity_id,
            actor_id=approver_id,
            data={
                "current_approvals": current,
                "required_approvals": required,
                "executed": current >= required,
            },
        )
        return {
            "status": "approved" if current < required else "executed",
            "opportunity_id": opportunity_id,
            "current_approvals": current,
            "required_approvals": required,
        }

    async def get_stats(self) -> Dict[str, Any]:
        """Get treasury and workforce high-level stats."""
        from sqlalchemy import func

        wallet_count = await self.db.scalar(select(func.count(WalletRegistry.id)))
        policy_count = await self.db.scalar(select(func.count(TreasuryPolicy.id)))
        opp_total = await self.db.scalar(select(func.count(OnChainOpportunity.id)))
        opp_approved = await self.db.scalar(
            select(func.count(OnChainOpportunity.id)).where(OnChainOpportunity.approval_status == "approved")
        )
        opp_executed = await self.db.scalar(
            select(func.count(OnChainOpportunity.id)).where(OnChainOpportunity.execution_status == "executed")
        )
        opp_rejected = await self.db.scalar(
            select(func.count(OnChainOpportunity.id)).where(OnChainOpportunity.approval_status == "rejected")
        )

        employees = list_employees()
        wallet_types = {}
        for emp in employees:
            wallet_types[emp.wallet_type] = wallet_types.get(emp.wallet_type, 0) + 1

        return {
            "wallets": {
                "total": wallet_count or 0,
            },
            "policies": {
                "total": policy_count or 0,
            },
            "opportunities": {
                "total": opp_total or 0,
                "approved": opp_approved or 0,
                "executed": opp_executed or 0,
                "rejected": opp_rejected or 0,
            },
            "workforce": {
                "total_employees": len(employees),
                "wallet_type_distribution": wallet_types,
            },
        }
