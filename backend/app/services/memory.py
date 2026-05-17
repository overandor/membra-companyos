"""MEMBRA CompanyOS — Memory Layer.

Vector memory, task memory, opportunity memory, department memory,
replayable reasoning traces.
Lightweight embedding store backed by Redis.
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import json
import math
import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

MEMORY_PREFIX = "membra:memory"


class MemoryStore:
    """Redis-backed memory store with vector search support."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def store(
        self,
        namespace: str,
        key: str,
        data: Dict[str, Any],
        embedding: Optional[List[float]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Store a memory entry."""
        redis_key = f"{MEMORY_PREFIX}:{namespace}:{key}"
        payload = {
            "data": data,
            "embedding": embedding or [],
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.redis.set(redis_key, json.dumps(payload, default=str))
        if ttl:
            await self.redis.expire(redis_key, ttl)
        logger.debug("memory_stored", namespace=namespace, key=key)

    async def retrieve(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single memory entry."""
        redis_key = f"{MEMORY_PREFIX}:{namespace}:{key}"
        raw = await self.redis.get(redis_key)
        if raw:
            return json.loads(raw)
        return None

    async def search(
        self,
        namespace: str,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Cosine-similarity search over stored embeddings."""
        pattern = f"{MEMORY_PREFIX}:{namespace}:*"
        keys = await self.redis.keys(pattern)
        results = []
        for key in keys:
            raw = await self.redis.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            emb = entry.get("embedding")
            if not emb or len(emb) != len(query_embedding):
                continue
            sim = _cosine_similarity(query_embedding, emb)
            key_name = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
            results.append((key_name, sim, entry["data"]))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    async def delete(self, namespace: str, key: str) -> None:
        redis_key = f"{MEMORY_PREFIX}:{namespace}:{key}"
        await self.redis.delete(redis_key)

    async def list_namespaces(self) -> List[str]:
        keys = await self.redis.keys(f"{MEMORY_PREFIX}:*")
        ns = set()
        for key in keys:
            parts = key.decode().split(":") if isinstance(key, bytes) else key.split(":")
            if len(parts) >= 3:
                ns.add(parts[2])
        return sorted(ns)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryLayer:
    """Facade for all memory namespaces."""

    def __init__(self, redis_client: redis.Redis):
        self.store = MemoryStore(redis_client)

    # --- Task Memory ---
    async def save_task_memory(self, task_id: str, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
        await self.store.store("task", task_id, data, embedding)

    async def get_task_memory(self, task_id: str) -> Optional[Dict[str, Any]]:
        entry = await self.store.retrieve("task", task_id)
        return entry["data"] if entry else None

    # --- Opportunity Memory ---
    async def save_opportunity_memory(self, opp_id: str, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
        await self.store.store("opportunity", opp_id, data, embedding)

    async def search_opportunity_memory(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        return await self.store.search("opportunity", query_embedding, top_k)

    # --- Department Memory ---
    async def save_department_memory(self, dept_id: str, data: Dict[str, Any]) -> None:
        await self.store.store("department", dept_id, data)

    async def get_department_memory(self, dept_id: str) -> Optional[Dict[str, Any]]:
        entry = await self.store.retrieve("department", dept_id)
        return entry["data"] if entry else None

    # --- Reasoning Traces ---
    async def save_reasoning_trace(self, trace_id: str, data: Dict[str, Any]) -> None:
        await self.store.store("reasoning", trace_id, data, ttl=86400 * 7)  # 7 days

    async def get_reasoning_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        entry = await self.store.retrieve("reasoning", trace_id)
        return entry["data"] if entry else None

    # --- Employee Memory ---
    async def save_employee_memory(self, emp_id: str, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> None:
        await self.store.store("employee", emp_id, data, embedding)

    async def search_employee_memory(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        return await self.store.search("employee", query_embedding, top_k)


# Singleton
_memory_layer: Optional[MemoryLayer] = None


async def get_memory_layer() -> MemoryLayer:
    global _memory_layer
    if _memory_layer is None:
        r = redis.from_url(settings.redis_url, decode_responses=True)
        _memory_layer = MemoryLayer(r)
    return _memory_layer
