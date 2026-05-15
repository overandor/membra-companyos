"""MEMBRA CompanyOS — API Routes."""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.services.orchestrator import OrchestratorService
from app.models.intent import Intent, Objective
from app.models.task import Task
from app.models.agent import Agent
from app.models.company import Company
from app.models.job import Job
from app.models.worldbridge import WorldAsset, AssetListing
from app.models.proofbook import ProofBookEvent

router = APIRouter(prefix="/api/v1")


# ───────────────────────────────────────────────────────────────
# Health & System
# ───────────────────────────────────────────────────────────────

@router.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy", "service": "membra-companyos", "version": "1.0.0"}


@router.get("/status", tags=["system"])
async def system_status(db: AsyncSession = Depends(get_db)):
    """Return high-level orchestration status."""
    return {
        "status": "operational",
        "intentos": "active",
        "taskos": "active",
        "agentos": "active",
        "jobos": "active",
        "companyos": "active",
        "governanceos": "active",
        "proofbook": "active",
        "settlementos": "active",
        "worldbridge": "active",
    }


# ───────────────────────────────────────────────────────────────
# IntentOS
# ───────────────────────────────────────────────────────────────

@router.post("/intents", tags=["intentos"])
async def create_intent(
    raw_text: str,
    user_wallet: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a raw user intent."""
    orch = OrchestratorService(db)
    intent = await orch.ingest_intent(raw_text, user_wallet)
    return {"id": intent.id, "status": intent.status, "message": "Intent ingested"}


@router.post("/intents/{intent_id}/parse", tags=["intentos"])
async def parse_intent(intent_id: str, db: AsyncSession = Depends(get_db)):
    """Parse an intent into structured objective."""
    orch = OrchestratorService(db)
    intent = await orch.parse_intent(intent_id)
    return {
        "id": intent.id,
        "status": intent.status,
        "parsed": intent.parsed_json,
        "confidence": intent.confidence_score,
    }


@router.get("/intents", tags=["intentos"])
async def list_intents(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Intent).order_by(desc(Intent.created_at))
    if status:
        query = query.where(Intent.status == status)
    result = await db.execute(query.limit(limit).offset(offset))
    intents = result.scalars().all()
    return {"items": [{"id": i.id, "raw_text": i.raw_text, "status": i.status, "created_at": i.created_at} for i in intents]}


# ───────────────────────────────────────────────────────────────
# TaskOS
# ───────────────────────────────────────────────────────────────

@router.post("/objectives/{objective_id}/tasks", tags=["taskos"])
async def create_task(
    objective_id: str,
    title: str,
    task_type: str,
    priority: int = 3,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a task within an objective."""
    orch = OrchestratorService(db)
    task = await orch.create_task(objective_id, title, task_type, priority=priority, description=description)
    return {"id": task.id, "status": task.status, "message": "Task created"}


@router.get("/tasks", tags=["taskos"])
async def list_tasks(
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Task).order_by(desc(Task.created_at))
    if status:
        query = query.where(Task.status == status)
    if owner_id:
        query = query.where(Task.owner_id == owner_id)
    result = await db.execute(query.limit(limit))
    tasks = result.scalars().all()
    return {"items": [{"id": t.id, "title": t.title, "status": t.status, "type": t.task_type} for t in tasks]}


@router.post("/tasks/{task_id}/assign", tags=["taskos"])
async def assign_task(
    task_id: str,
    assignee_type: str,
    assignee_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Assign a task to an entity."""
    orch = OrchestratorService(db)
    assignment = await orch.assign_task(task_id, assignee_type, assignee_id)
    return {"id": assignment.id, "status": "assigned", "message": "Task assigned"}


# ───────────────────────────────────────────────────────────────
# AgentOS
# ───────────────────────────────────────────────────────────────

@router.post("/agents", tags=["agentos"])
async def create_agent(
    agent_type: str,
    name: str,
    description: Optional[str] = None,
    allowed_actions: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent."""
    agent = Agent(
        agent_type=agent_type,
        name=name,
        description=description,
        allowed_actions=allowed_actions or [],
        status="active",
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return {"id": agent.id, "status": agent.status, "message": "Agent registered"}


@router.get("/agents", tags=["agentos"])
async def list_agents(
    agent_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent).order_by(desc(Agent.created_at))
    if agent_type:
        query = query.where(Agent.agent_type == agent_type)
    if status:
        query = query.where(Agent.status == status)
    result = await db.execute(query)
    agents = result.scalars().all()
    return {"items": [{"id": a.id, "name": a.name, "type": a.agent_type, "status": a.status} for a in agents]}


# ───────────────────────────────────────────────────────────────
# JobOS
# ───────────────────────────────────────────────────────────────

@router.post("/jobs", tags=["jobos"])
async def create_job(
    job_type: str,
    title: str,
    payment_amount: float = 0,
    payment_currency: str = "USDC",
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a paid job or bounty."""
    orch = OrchestratorService(db)
    job = await orch.create_job(None, job_type, title, payment_amount=payment_amount, payment_currency=payment_currency, description=description)
    return {"id": job.id, "status": job.status, "message": "Job created"}


@router.get("/jobs", tags=["jobos"])
async def list_jobs(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).order_by(desc(Job.created_at))
    if status:
        query = query.where(Job.status == status)
    if job_type:
        query = query.where(Job.job_type == job_type)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {"items": [{"id": j.id, "title": j.title, "type": j.job_type, "status": j.status, "payment": str(j.payment_amount)} for j in jobs]}


# ───────────────────────────────────────────────────────────────
# CompanyOS
# ───────────────────────────────────────────────────────────────

@router.post("/companies", tags=["companyos"])
async def create_company(
    name: str,
    slug: str,
    description: Optional[str] = None,
    owner_wallet: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Register a new company / operating unit."""
    company = Company(
        name=name,
        slug=slug,
        description=description,
        owner_wallet=owner_wallet,
        status="active",
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return {"id": company.id, "slug": company.slug, "message": "Company created"}


@router.get("/companies", tags=["companyos"])
async def list_companies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).order_by(desc(Company.created_at)))
    companies = result.scalars().all()
    return {"items": [{"id": c.id, "name": c.name, "slug": c.slug, "status": c.status} for c in companies]}


# ───────────────────────────────────────────────────────────────
# WorldBridge
# ───────────────────────────────────────────────────────────────

@router.post("/assets", tags=["worldbridge"])
async def register_asset(
    asset_type: str,
    name: str,
    owner_wallet: str,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Register a real-world asset."""
    orch = OrchestratorService(db)
    asset = await orch.create_asset(asset_type, name, owner_wallet, description=description)
    return {"id": asset.id, "status": asset.status, "message": "Asset registered"}


@router.get("/assets", tags=["worldbridge"])
async def list_assets(
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WorldAsset).order_by(desc(WorldAsset.created_at))
    if asset_type:
        query = query.where(WorldAsset.asset_type == asset_type)
    if status:
        query = query.where(WorldAsset.status == status)
    result = await db.execute(query)
    assets = result.scalars().all()
    return {"items": [{"id": a.id, "name": a.name, "type": a.asset_type, "status": a.status} for a in assets]}


@router.post("/assets/{asset_id}/listings", tags=["worldbridge"])
async def create_listing(
    asset_id: str,
    listing_type: str,
    title: str,
    price: float = 0,
    db: AsyncSession = Depends(get_db),
):
    """Create a marketplace listing for an asset."""
    orch = OrchestratorService(db)
    listing = await orch.create_listing(asset_id, listing_type, title, price=price)
    return {"id": listing.id, "status": listing.status, "message": "Listing created"}


# ───────────────────────────────────────────────────────────────
# ProofBook
# ───────────────────────────────────────────────────────────────

@router.get("/proofbook", tags=["proofbook"])
async def query_proofbook(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Query immutable ProofBook events."""
    query = select(ProofBookEvent).order_by(desc(ProofBookEvent.created_at))
    if entity_type:
        query = query.where(ProofBookEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(ProofBookEvent.entity_id == entity_id)
    result = await db.execute(query.limit(limit))
    events = result.scalars().all()
    return {"items": [{"id": e.id, "event_type": e.event_type, "entity_type": e.entity_type, "entity_id": e.entity_id, "hash": e.proof_hash} for e in events]}
