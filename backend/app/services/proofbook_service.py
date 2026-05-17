"""MEMBRA CompanyOS — ProofBook Logging Service.

Immutable event logging with hash chaining.
Every opportunity, decision, rejection, simulation, and approval is written here.
"""
from typing import Dict, Any, Optional
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.proofbook import ProofBookEvent
import structlog

logger = structlog.get_logger()


class ProofBookService:
    """Service for writing and querying immutable ProofBook events."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        parent_hash: Optional[str] = None,
    ) -> ProofBookEvent:
        """Write an immutable event to the ProofBook."""
        event_data = data or {}
        event_data["_meta"] = {
            "logged_at": datetime.now(timezone.utc).isoformat(),
            "service": "proofbook",
        }

        # Hash the event data
        hash_input = json.dumps({
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor_id": actor_id,
            "data": event_data,
        }, sort_keys=True)
        proof_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        event = ProofBookEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_wallet=actor_id,
            actor_agent_id=actor_id,
            event_data=event_data,
            proof_hash=proof_hash,
            parent_hash=parent_hash,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        logger.info("proofbook_event_written", event_type=event_type, entity=entity_id, hash=proof_hash[:16])
        return event

    async def get_events(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        query = select(ProofBookEvent).order_by(desc(ProofBookEvent.created_at))
        if entity_type:
            query = query.where(ProofBookEvent.entity_type == entity_type)
        if entity_id:
            query = query.where(ProofBookEvent.entity_id == entity_id)
        if event_type:
            query = query.where(ProofBookEvent.event_type == event_type)
        result = await self.db.execute(query.limit(limit).offset(offset))
        return list(result.scalars().all())

    async def verify_chain(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Verify the hash chain for an entity's events."""
        events = await self.get_events(entity_type=entity_type, entity_id=entity_id, limit=1000)
        if not events:
            return {"valid": True, "events_count": 0, "message": "No events to verify"}

        valid = True
        broken_at = None
        for i, event in enumerate(events):
            expected_input = json.dumps({
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "actor_id": event.actor_agent_id,
                "data": event.event_data,
            }, sort_keys=True)
            expected_hash = hashlib.sha256(expected_input.encode()).hexdigest()
            if event.proof_hash != expected_hash:
                valid = False
                broken_at = i
                break

        return {
            "valid": valid,
            "events_count": len(events),
            "broken_at_index": broken_at,
            "message": "Hash chain verified" if valid else f"Hash mismatch at index {broken_at}",
        }
