"""MEMBRA CompanyOS — Treasury & ProofBook API Endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.treasury import TreasuryService
from app.services.proofbook_service import ProofBookService
from app.services.approval_workflow import get_approval_workflow

router = APIRouter(prefix="/api/v1")


@router.get("/treasury/wallets", tags=["treasury"])
async def get_wallets(chain: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    svc = TreasuryService(db)
    wallets = await svc.list_wallets(chain=chain)
    return {
        "count": len(wallets),
        "wallets": [
            {
                "id": w.id,
                "wallet_address": w.wallet_address,
                "wallet_type": w.wallet_type,
                "owner_type": w.owner_type,
                "owner_id": w.owner_id,
                "chain": w.chain,
                "label": w.label,
                "purpose": w.purpose,
                "is_active": w.is_active,
            }
            for w in wallets
        ],
    }


@router.get("/treasury/policies", tags=["treasury"])
async def get_policies(status: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    svc = TreasuryService(db)
    policies = await svc.list_policies(status=status)
    return {
        "count": len(policies),
        "policies": [
            {
                "id": p.id,
                "policy_name": p.policy_name,
                "policy_type": p.policy_type,
                "max_amount": p.max_amount,
                "min_signers": p.min_signers,
                "status": p.status,
                "cooldown_hours": p.cooldown_hours,
            }
            for p in policies
        ],
    }


@router.get("/treasury/stats", tags=["treasury"])
async def get_treasury_stats(db: AsyncSession = Depends(get_db)):
    svc = TreasuryService(db)
    return await svc.get_stats()


@router.get("/proofbook/opportunities", tags=["proofbook"])
async def get_proofbook_opportunities(
    opportunity_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    svc = ProofBookService(db)
    events = await svc.get_events(
        entity_type="opportunity",
        entity_id=opportunity_id,
        limit=limit,
    )
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor_wallet": e.actor_wallet,
                "proof_hash": e.proof_hash,
                "parent_hash": e.parent_hash,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.get("/treasury/approvals", tags=["treasury"])
async def list_treasury_approvals(status: Optional[str] = None):
    """List treasury approval requests."""
    wf = get_approval_workflow()
    reqs = wf.list_requests(status=status)
    return {
        "count": len(reqs),
        "requests": [
            {
                "request_id": r.request_id,
                "opportunity_id": r.opportunity_id,
                "current_stage": r.current_stage.value,
                "employee_id": r.employee_id,
                "signatures": r.signatures,
                "created_at": r.created_at,
            }
            for r in reqs
        ],
    }


@router.get("/treasury/approvals/{request_id}", tags=["treasury"])
async def get_treasury_approval(request_id: str):
    """Get a specific approval request."""
    wf = get_approval_workflow()
    req = wf.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return {
        "request_id": req.request_id,
        "opportunity_id": req.opportunity_id,
        "current_stage": req.current_stage.value,
        "stages": [s.value for s in req.stages],
        "signatures": req.signatures,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "metadata": req.metadata,
    }


@router.post("/treasury/approvals/{request_id}/advance", tags=["treasury"])
async def advance_treasury_approval(
    request_id: str,
    signer_id: str,
    decision: str,
    notes: str = "",
):
    """Advance a treasury approval request."""
    wf = get_approval_workflow()
    req = wf.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    req = await wf.advance(request_id, signer_id, decision, notes)
    return {
        "request_id": req.request_id,
        "current_stage": req.current_stage.value,
        "signatures": req.signatures,
    }
