"""MEMBRA CompanyOS - Opportunity API Endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.opportunity_scanner import OpportunityScannerService
from app.services.simulation import SimulationService
from app.services.risk_scoring import RiskScoringService
from app.services.compliance_scoring import ComplianceScoringService
from app.services.treasury import TreasuryService
from app.services.policy_engine import get_policy_engine, ExecutionContext
from app.services.approval_workflow import get_approval_workflow, ApprovalStage

router = APIRouter(prefix="/api/v1/opportunities")


def _opp_dict(o):
    return {
        "id": o.id,
        "discovered_by_employee_id": o.discovered_by_employee_id,
        "chain": o.chain,
        "protocol": o.protocol,
        "opportunity_type": o.opportunity_type,
        "asset_in": o.asset_in,
        "asset_out": o.asset_out,
        "expected_profit": o.expected_profit,
        "expected_profit_percent": o.expected_profit_percent,
        "required_capital": o.required_capital,
        "estimated_fees": o.estimated_fees,
        "slippage_estimate": o.slippage_estimate,
        "liquidity_depth": o.liquidity_depth,
        "execution_window_seconds": o.execution_window_seconds,
        "confidence_score": o.confidence_score,
        "risk_score": o.risk_score,
        "compliance_score": o.compliance_score,
        "simulation_status": o.simulation_status,
        "approval_status": o.approval_status,
        "execution_status": o.execution_status,
        "expires_at": o.expires_at.isoformat() if o.expires_at else None,
        "recommended_action": o.recommended_action,
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.get("", tags=["opportunities"])
async def list_opportunities(
    status: str = None, opp_type: str = None,
    chain: str = None, min_confidence: float = None,
    limit: int = 100, offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    s = OpportunityScannerService(db)
    ops = await s.list_opportunities(status=status, opp_type=opp_type, chain=chain,
        min_confidence=min_confidence, limit=limit, offset=offset)
    return {"count": len(ops), "opportunities": [_opp_dict(o) for o in ops]}


@router.post("/scan", tags=["opportunities"])
async def scan_opportunities(employee_id: str = None, db: AsyncSession = Depends(get_db)):
    s = OpportunityScannerService(db)
    ops = await s.scan_all(employee_id=employee_id)
    return {"opportunities_discovered": len(ops), "opportunities": [_opp_dict(o) for o in ops]}


@router.get("/{opportunity_id}", tags=["opportunities"])
async def get_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    s = OpportunityScannerService(db)
    opp = await s.get_opportunity(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    d = _opp_dict(opp)
    d.update({
        "simulation_result_json": opp.simulation_result_json,
        "risk_review_json": opp.risk_review_json,
        "compliance_review_json": opp.compliance_review_json,
        "finance_review_json": opp.finance_review_json,
        "governance_review_json": opp.governance_review_json,
        "execution_result_json": opp.execution_result_json,
        "evidence_json": opp.evidence_json,
        "rejection_reason": opp.rejection_reason,
    })
    return d


@router.post("/{opportunity_id}/simulate", tags=["opportunities"])
async def simulate_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    sim = SimulationService(db)
    r = await sim.simulate_by_id(opportunity_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"opportunity_id": opportunity_id, "simulation": r}


@router.post("/{opportunity_id}/risk-review", tags=["opportunities"])
async def risk_review_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    svc = RiskScoringService(db)
    r = await svc.score_by_id(opportunity_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"opportunity_id": opportunity_id, "risk_review": r}


@router.post("/{opportunity_id}/compliance-review", tags=["opportunities"])
async def compliance_review_opportunity(opportunity_id: str, db: AsyncSession = Depends(get_db)):
    svc = ComplianceScoringService(db)
    r = await svc.score_by_id(opportunity_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"opportunity_id": opportunity_id, "compliance_review": r}


@router.post("/{opportunity_id}/approve", tags=["opportunities"])
async def approve_opportunity(opportunity_id: str, approver_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.opportunity import OnChainOpportunity, ApprovalStatus
    r = await db.execute(select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id))
    opp = r.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.simulation_status != "simulated":
        raise HTTPException(status_code=400, detail="Must simulate before approval")
    if opp.risk_score is None:
        raise HTTPException(status_code=400, detail="Must complete risk review before approval")
    if opp.compliance_score is None:
        raise HTTPException(status_code=400, detail="Must complete compliance review before approval")
    if opp.compliance_score <= 0:
        raise HTTPException(status_code=400, detail="Compliance blocked this opportunity")

    # Policy engine gate
    policy = get_policy_engine()
    ctx = ExecutionContext(
        employee_id=approver_id,
        department_id=opp.discovered_by_employee_id.split("-")[0] if opp.discovered_by_employee_id else "unknown",
        action="approve_opportunity",
        target=opportunity_id,
        amount=opp.expected_profit,
        chain=opp.chain,
        risk_score=opp.risk_score,
        compliance_score=opp.compliance_score,
        simulation_passed=opp.simulation_status == "simulated",
    )
    result = policy.evaluate(ctx)
    if result["result"] != "allow":
        raise HTTPException(status_code=403, detail={"blocked_by_policy": result})

    opp.approval_status = ApprovalStatus.APPROVED.value
    opp.governance_review_json = {"approved_by": approver_id, "approved_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
    await db.commit()
    await db.refresh(opp)
    return {"opportunity_id": opportunity_id, "status": "approved", "policy_check": result}


@router.post("/{opportunity_id}/reject", tags=["opportunities"])
async def reject_opportunity(opportunity_id: str, reason: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.opportunity import OnChainOpportunity, ApprovalStatus
    r = await db.execute(select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id))
    opp = r.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.approval_status = ApprovalStatus.REJECTED.value
    opp.rejection_reason = reason
    opp.execution_status = "cancelled"
    await db.commit()
    await db.refresh(opp)
    return {"opportunity_id": opportunity_id, "status": "rejected", "reason": reason}


@router.post("/{opportunity_id}/propose-execution", tags=["opportunities"])
async def propose_execution(opportunity_id: str, proposer_id: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.models.opportunity import OnChainOpportunity
    r = await db.execute(select(OnChainOpportunity).where(OnChainOpportunity.id == opportunity_id))
    opp = r.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if opp.approval_status != "approved":
        raise HTTPException(status_code=400, detail="Opportunity must be approved before execution proposal")

    # Create approval workflow request
    wf = get_approval_workflow()
    req = await wf.create_request(
        request_id=f"req-{opportunity_id}",
        opportunity_id=opportunity_id,
        employee_id=proposer_id,
        department_id=opp.discovered_by_employee_id.split("-")[0] if opp.discovered_by_employee_id else "unknown",
        metadata={
            "amount": opp.expected_profit,
            "chain": opp.chain,
            "risk_score": opp.risk_score,
            "compliance_score": opp.compliance_score,
            "simulation_passed": opp.simulation_status == "simulated",
        },
    )
    # Auto-advance through stages that have deterministic checks
    while req.current_stage not in {ApprovalStage.APPROVED, ApprovalStage.REJECTED, ApprovalStage.ESCALATED}:
        # In a real system, each stage would require human/automated review
        # For now, auto-approve if metadata supports it
        can_advance = True
        if req.current_stage == ApprovalStage.SIMULATION_REVIEW and not req.metadata.get("simulation_passed"):
            can_advance = False
        if req.current_stage == ApprovalStage.RISK_REVIEW and req.metadata.get("risk_score", 1.0) >= 0.85:
            can_advance = False
        if req.current_stage == ApprovalStage.COMPLIANCE_REVIEW and req.metadata.get("compliance_score", 0.0) < 0.70:
            can_advance = False
        if req.current_stage == ApprovalStage.TREASURY_REVIEW and req.metadata.get("amount", 0) > 50000:
            can_advance = False
        if not can_advance:
            break
        req = await wf.advance(req.request_id, "system", "approve", "auto-approved by policy")

    svc = TreasuryService(db)
    result = await svc.propose_execution(opportunity_id, proposer_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    result["approval_request"] = {
        "request_id": req.request_id,
        "current_stage": req.current_stage.value,
        "signatures": req.signatures,
    }
    return result
