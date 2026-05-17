"""MEMBRA CompanyOS — FastAPI Application Entry Point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import structlog

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import router
from app.api.llm import router as llm_router
from app.api.workforce import router as workforce_router
from app.api.opportunities import router as opportunities_router
from app.api.datasources import router as datasources_router
from app.api.treasury import router as treasury_router
from app.api.metrics import router as metrics_router
from app.api.execution import router as execution_router
from app.api.llm_employees import router as llm_employees_router
from app.services.event_bus import get_event_bus
from app.services.agent_runtime import get_agent_runtime

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: startup and shutdown events."""
    logger.info("membra_startup", version=settings.app_version, environment=settings.environment)
    if settings.environment in ("development", "staging"):
        await init_db()
        logger.info("db_initialized")
    bus = await get_event_bus()
    await bus.start_listener()
    logger.info("event_bus_listening")
    runtime = await get_agent_runtime()
    logger.info("agent_runtime_started")
    yield
    await runtime.stop()
    await bus.disconnect()
    logger.info("membra_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="MEMBRA CompanyOS — AI-powered autonomous company orchestration layer.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routes
app.include_router(router)
app.include_router(llm_router)
app.include_router(workforce_router)
app.include_router(opportunities_router)
app.include_router(datasources_router)
app.include_router(treasury_router)
app.include_router(metrics_router)
app.include_router(execution_router)
app.include_router(llm_employees_router)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "modules": [
            "IntentOS",
            "TaskOS",
            "AgentOS",
            "JobOS",
            "CompanyOS",
            "GovernanceOS",
            "ProofBook",
            "SettlementOS",
            "WorldBridge",
            "ProfitIntelligenceOS",
            "WorkforceOS",
            "OpportunityOS",
            "TreasuryOS",
        ],
        "docs": "/docs",
        "health": "/api/v1/health",
    }
