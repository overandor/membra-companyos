"""MEMBRA CompanyOS — Core Orchestration Service.

The Orchestrator is the central nervous system. It accepts high-level
objectives, breaks them into tasks, assigns them to agents, and
coordinates execution with governance gates and proof collection.
"""
from typing import Dict, Any, List, Optional
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.intent import Intent, Objective
from app.models.task import Task, TaskDependency, TaskAssignment, TaskProof
from app.models.agent import Agent, AgentActionLog
from app.models.job import Job
from app.models.governance import ApprovalRequest, GovernancePolicy
from app.models.proofbook import ProofBookEvent
from app.models.worldbridge import WorldAsset, AssetListing
from app.core.config import settings


class OrchestratorService:
    """Central orchestration layer for MEMBRA CompanyOS."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_intent(self, raw_text: str, user_wallet: Optional[str] = None, metadata: Optional[Dict] = None) -> Intent:
        """Ingest raw user intent and create an Intent record."""
        intent = Intent(
            raw_text=raw_text,
            user_wallet=user_wallet,
            status="pending",
            confidence_score=0.0,
            metadata_json=metadata or {},
        )
        self.db.add(intent)
        await self.db.commit()
        await self.db.refresh(intent)
        await self._write_proof("intent_created", "intent", intent.id, user_wallet, {"raw_text": raw_text})
        return intent

    async def parse_intent(self, intent_id: str) -> Intent:
        """Parse intent using deterministic LLM fallback."""
        result = await self.db.execute(select(Intent).where(Intent.id == intent_id))
        intent = result.scalar_one_or_none()
        if not intent:
            raise ValueError(f"Intent {intent_id} not found")

        # Deterministic parsing (fallback when no LLM key)
        parsed = self._deterministic_parse(intent.raw_text)
        intent.parsed_json = parsed
        intent.structured_objective_json = parsed.get("objective", {})
        intent.status = "structured"
        intent.confidence_score = parsed.get("confidence", 0.5)
        intent.llm_provider = "deterministic"
        intent.llm_model = "rule_based"
        await self.db.commit()
        await self.db.refresh(intent)
        return intent

    def _deterministic_parse(self, raw_text: str) -> Dict[str, Any]:
        """Rule-based intent parsing when no LLM is available."""
        text = raw_text.lower()
        objective = {"title": raw_text[:120], "description": raw_text}
        confidence = 0.5

        # Simple keyword extraction
        if any(k in text for k in ["window", "apartment", "room", "space"]):
            objective["category"] = "real_estate"
            confidence = 0.7
        elif any(k in text for k in ["car", "vehicle", "drive", "delivery"]):
            objective["category"] = "vehicle"
            confidence = 0.7
        elif any(k in text for k in ["ad", "advertise", "display", "show"]):
            objective["category"] = "advertising"
            confidence = 0.7
        elif any(k in text for k in ["task", "work", "job", "help"]):
            objective["category"] = "labor"
            confidence = 0.6
        elif any(k in text for k in ["kpi", "metric", "dashboard", "track"]):
            objective["category"] = "analytics"
            confidence = 0.8
        else:
            objective["category"] = "general"

        return {
            "objective": objective,
            "confidence": confidence,
            "keywords": text.split()[:20],
        }

    async def create_objective(self, intent_id: str, title: str, **kwargs) -> Objective:
        """Create a structured objective from a parsed intent."""
        objective = Objective(
            intent_id=intent_id,
            title=title,
            description=kwargs.get("description"),
            company_id=kwargs.get("company_id"),
            priority=kwargs.get("priority", "medium"),
            target_completion=kwargs.get("target_completion"),
            success_criteria=kwargs.get("success_criteria", []),
            assigned_department=kwargs.get("assigned_department"),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(objective)
        await self.db.commit()
        await self.db.refresh(objective)
        await self._write_proof("objective_created", "objective", objective.id, kwargs.get("owner_wallet"), {"title": title})
        return objective

    async def create_task(self, objective_id: Optional[str], title: str, task_type: str, **kwargs) -> Task:
        """Create a task within an objective."""
        task = Task(
            objective_id=objective_id,
            company_id=kwargs.get("company_id"),
            title=title,
            description=kwargs.get("description"),
            task_type=task_type,
            priority=kwargs.get("priority", 3),
            owner_id=kwargs.get("owner_id"),
            owner_agent_id=kwargs.get("owner_agent_id"),
            estimated_hours=kwargs.get("estimated_hours"),
            deadline=kwargs.get("deadline"),
            proof_requirement=kwargs.get("proof_requirement", {}),
            output_schema=kwargs.get("output_schema", {}),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        await self._write_proof("task_created", "task", task.id, kwargs.get("owner_wallet"), {"title": title, "type": task_type})
        return task

    async def assign_task(self, task_id: str, assignee_type: str, assignee_id: str, **kwargs) -> TaskAssignment:
        """Assign a task to a human, agent, vendor, or system."""
        assignment = TaskAssignment(
            task_id=task_id,
            assignee_type=assignee_type,
            assignee_id=assignee_id,
            notes=kwargs.get("notes"),
        )
        self.db.add(assignment)

        # Update task status
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if task:
            task.status = "assigned"
            task.owner_id = assignee_id if assignee_type == "human" else task.owner_id
            task.owner_agent_id = assignee_id if assignee_type == "agent" else task.owner_agent_id

        await self.db.commit()
        await self.db.refresh(assignment)
        await self._write_proof("task_assigned", "task", task_id, kwargs.get("requester_wallet"), {"assignee_type": assignee_type, "assignee_id": assignee_id})
        return assignment

    async def create_job(self, task_id: Optional[str], job_type: str, title: str, **kwargs) -> Job:
        """Convert a task into a paid job."""
        job = Job(
            task_id=task_id,
            company_id=kwargs.get("company_id"),
            job_type=job_type,
            title=title,
            description=kwargs.get("description"),
            payment_amount=kwargs.get("payment_amount", 0),
            payment_currency=kwargs.get("payment_currency", "USDC"),
            assignee_wallet=kwargs.get("assignee_wallet"),
            deadline=kwargs.get("deadline"),
            proof_requirement=kwargs.get("proof_requirement", {}),
            location_json=kwargs.get("location", {}),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        await self._write_proof("job_posted", "job", job.id, kwargs.get("requester_wallet"), {"title": title, "job_type": job_type})
        return job

    async def request_approval(self, policy_id: str, entity_type: str, entity_id: str, requester_wallet: str, **kwargs) -> ApprovalRequest:
        """Request governance approval for an entity action."""
        request = ApprovalRequest(
            policy_id=policy_id,
            entity_type=entity_type,
            entity_id=entity_id,
            requester_wallet=requester_wallet,
            status="pending",
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        await self._write_proof("approval_requested", "approval", request.id, requester_wallet, {"entity_type": entity_type, "entity_id": entity_id})
        return request

    async def submit_task_proof(self, task_id: str, proof_type: str, proof_hash: str, **kwargs) -> TaskProof:
        """Submit proof for a completed task."""
        proof = TaskProof(
            task_id=task_id,
            proof_type=proof_type,
            proof_data=kwargs.get("proof_data", {}),
            ipfs_cid=kwargs.get("ipfs_cid"),
            proof_hash=proof_hash,
            verified="pending",
            verifier_id=kwargs.get("verifier_id"),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(proof)
        await self.db.commit()
        await self.db.refresh(proof)
        await self._write_proof("task_proof_submitted", "task_proof", proof.id, kwargs.get("submitter_wallet"), {"task_id": task_id, "proof_type": proof_type})
        return proof

    async def create_asset(self, asset_type: str, name: str, owner_wallet: str, **kwargs) -> WorldAsset:
        """Register a real-world asset in WorldBridge."""
        asset = WorldAsset(
            asset_type=asset_type,
            asset_category=kwargs.get("asset_category", "general"),
            name=name,
            description=kwargs.get("description"),
            owner_wallet=owner_wallet,
            status="active",
            location_json=kwargs.get("location", {}),
            capabilities_json=kwargs.get("capabilities", {}),
            pricing_json=kwargs.get("pricing", {}),
            media_json=kwargs.get("media", {}),
            proof_hash=kwargs.get("proof_hash"),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        await self._write_proof("asset_registered", "world_asset", asset.id, owner_wallet, {"asset_type": asset_type, "name": name})
        return asset

    async def create_listing(self, asset_id: str, listing_type: str, title: str, **kwargs) -> AssetListing:
        """Create a marketplace listing for an asset."""
        listing = AssetListing(
            asset_id=asset_id,
            listing_type=listing_type,
            title=title,
            description=kwargs.get("description"),
            price=kwargs.get("price", 0),
            currency=kwargs.get("currency", "USDC"),
            availability_json=kwargs.get("availability", {}),
            requirements_json=kwargs.get("requirements", {}),
            metadata_json=kwargs.get("metadata", {}),
        )
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)
        await self._write_proof("listing_created", "asset_listing", listing.id, kwargs.get("owner_wallet"), {"asset_id": asset_id, "listing_type": listing_type})
        return listing

    async def _write_proof(self, event_type: str, entity_type: str, entity_id: str, actor_wallet: Optional[str], event_data: Dict[str, Any]) -> ProofBookEvent:
        """Write an immutable event to ProofBook."""
        # Create hash chain
        data_str = json.dumps({"event_type": event_type, "entity_id": entity_id, "data": event_data, "ts": datetime.now(timezone.utc).isoformat()}, sort_keys=True)
        proof_hash = hashlib.sha256(data_str.encode()).hexdigest()

        event = ProofBookEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_wallet=actor_wallet,
            event_data=event_data,
            proof_hash=proof_hash,
            parent_hash=None,  # In production, query last hash and chain it
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event
