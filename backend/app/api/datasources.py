"""MEMBRA CompanyOS — Data Source API Endpoints."""
from fastapi import APIRouter
from app.config.datasources import list_datasources, get_datasource, datasources_for_department

router = APIRouter(prefix="/api/v1/datasources")


@router.get("", tags=["datasources"])
async def get_datasources():
    sources = list_datasources()
    return {
        "count": len(sources),
        "datasources": [
            {
                "source_id": s.source_id,
                "name": s.name,
                "type": s.type,
                "base_url": s.base_url,
                "auth_required": s.auth_required,
                "rate_limit": s.rate_limit,
                "reliability_score": s.reliability_score,
                "freshness_seconds": s.freshness_seconds,
                "allowed_departments": s.allowed_departments,
                "cache_policy": s.cache_policy,
                "description": s.description,
                "chain": s.chain,
                "fallback_sources": s.fallback_sources,
            }
            for s in sources
        ],
    }


@router.post("/sync", tags=["datasources"])
async def sync_datasources():
    return {"status": "synced", "sources_checked": len(list_datasources())}
