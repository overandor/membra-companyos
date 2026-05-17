"""MEMBRA CompanyOS — Treasury & ProofBook API Endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.treasury import TreasuryService
from app.services.proofbook_service import ProofBookService

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
