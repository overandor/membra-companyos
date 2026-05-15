#!/usr/bin/env python3
"""MEMBRA CompanyOS — Seed script for demo data."""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_maker, init_db
from app.models.intent import Intent, Objective
from app.models.task import Task
from app.models.agent import Agent
from app.models.company import Company
from app.models.job import Job
from app.models.worldbridge import WorldAsset


async def seed():
    await init_db()
    async with async_session_maker() as db:
        # Create a demo company
        company = Company(name="MEMBRA Demo Co", slug="membra-demo", description="Demo operating unit")
        db.add(company)
        await db.commit()
        await db.refresh(company)
        print(f"Created company: {company.name} ({company.id})")

        # Create intents
        intents = [
            Intent(raw_text="I have a window and 2 hours free — want to monetize it", status="pending", confidence_score=0.0),
            Intent(raw_text="Need a delivery route optimized for 5 stops", status="pending", confidence_score=0.0),
            Intent(raw_text="Track KPIs for our ad inventory this week", status="pending", confidence_score=0.0),
        ]
        for intent in intents:
            db.add(intent)
        await db.commit()
        print(f"Created {len(intents)} demo intents")

        # Create objectives
        objectives = [
            Objective(intent_id=intents[0].id, title="Monetize window as ad inventory", priority="high", company_id=company.id),
            Objective(intent_id=intents[1].id, title="Optimize delivery route", priority="medium", company_id=company.id),
        ]
        for obj in objectives:
            db.add(obj)
        await db.commit()
        print(f"Created {len(objectives)} demo objectives")

        # Create tasks
        tasks = [
            Task(objective_id=objectives[0].id, title="Photograph window for listing", task_type="media", priority=2, company_id=company.id),
            Task(objective_id=objectives[0].id, title="Set pricing for window ad slot", task_type="finance", priority=1, company_id=company.id),
            Task(objective_id=objectives[1].id, title="Map 5-stop route", task_type="logistics", priority=1, company_id=company.id),
        ]
        for task in tasks:
            db.add(task)
        await db.commit()
        print(f"Created {len(tasks)} demo tasks")

        # Create agents
        agents = [
            Agent(agent_type="strategy", name="StrategyBot", description="High-level planning and objective creation", allowed_actions=["create_objective", "create_task"]),
            Agent(agent_type="finance", name="FinanceBot", description="Pricing, budgeting, and settlement", allowed_actions=["set_price", "calculate_payout"]),
            Agent(agent_type="operations", name="OpsBot", description="Task execution and logistics", allowed_actions=["assign_task", "route_optimize"]),
        ]
        for agent in agents:
            db.add(agent)
        await db.commit()
        print(f"Created {len(agents)} demo agents")

        # Create jobs
        jobs = [
            Job(task_id=tasks[0].id, job_type="bounty", title="Window photography", payment_amount=25, payment_currency="USDC", company_id=company.id),
            Job(task_id=tasks[1].id, job_type="task", title="Pricing analysis", payment_amount=50, payment_currency="USDC", company_id=company.id),
        ]
        for job in jobs:
            db.add(job)
        await db.commit()
        print(f"Created {len(jobs)} demo jobs")

        # Create world assets
        assets = [
            WorldAsset(asset_type="window", asset_category="real_estate", name="Bedroom window facing Main St", description="High-traffic visibility window", owner_wallet="0xDemoOwner1", status="active"),
            WorldAsset(asset_type="vehicle", asset_category="transport", name="Delivery van — Toyota Hiace", description="Available for route assignments", owner_wallet="0xDemoOwner2", status="active"),
        ]
        for asset in assets:
            db.add(asset)
        await db.commit()
        print(f"Created {len(assets)} demo assets")

        print("\n✅ Seed complete! Database populated with demo data.")


if __name__ == "__main__":
    asyncio.run(seed())
