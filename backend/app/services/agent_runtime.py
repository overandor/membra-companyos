"""MEMBRA CompanyOS — Agent Runtime.

Task queue, worker pool, retries, heartbeat monitoring.
Redis-backed for durability and horizontal scaling.
"""
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import json
import redis.asyncio as redis
from app.core.config import settings
from app.services.event_bus import get_event_bus, EventBus
from app.core.events import MembraEvent
import structlog

logger = structlog.get_logger()

TASK_QUEUE_PREFIX = "membra:queue:task"
HEARTBEAT_PREFIX = "membra:heartbeat"
WORKER_PREFIX = "membra:worker"


@dataclass
class RuntimeTask:
    """Task envelope for the runtime queue."""
    task_id: str
    task_type: str
    employee_id: str
    department_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 3  # 1 = highest, 5 = lowest
    retries: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: Optional[str] = None


class TaskQueue:
    """Redis-backed task queue with priority support."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def enqueue(self, task: RuntimeTask) -> None:
        """Push task to the queue (lower priority number = higher priority)."""
        key = f"{TASK_QUEUE_PREFIX}:{task.department_id}"
        data = json.dumps(task.__dict__, default=str)
        score = task.priority * 1000000 + int(datetime.now(timezone.utc).timestamp())
        await self.redis.zadd(key, {data: score})
        # Also push to a global queue for cross-department tasks
        await self.redis.zadd(f"{TASK_QUEUE_PREFIX}:global", {data: score})
        logger.debug("task_enqueued", task_id=task.task_id, type=task.task_type, emp=task.employee_id)

    async def dequeue(self, department_id: Optional[str] = None, timeout: int = 5) -> Optional[RuntimeTask]:
        """Pop the highest-priority task from the queue."""
        keys = [f"{TASK_QUEUE_PREFIX}:{department_id}"] if department_id else []
        keys.append(f"{TASK_QUEUE_PREFIX}:global")
        for key in keys:
            items = await self.redis.zrange(key, 0, 0, withscores=False)
            if items:
                await self.redis.zrem(key, items[0])
                data = json.loads(items[0])
                return RuntimeTask(**data)
        return None

    async def size(self, department_id: Optional[str] = None) -> int:
        key = f"{TASK_QUEUE_PREFIX}:{department_id or 'global'}"
        return await self.redis.zcard(key)


class RetryPolicy:
    """Exponential backoff with jitter."""

    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 3):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def next_delay(self, retry_count: int) -> float:
        import random
        delay = min(self.base_delay * (2 ** retry_count), self.max_delay)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    def can_retry(self, retry_count: int) -> bool:
        return retry_count < self.max_retries


class HeartbeatMonitor:
    """Track employee/agent liveness via Redis TTL keys."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def beat(self, employee_id: str, ttl_seconds: int = 60) -> None:
        """Register a heartbeat for an employee."""
        key = f"{HEARTBEAT_PREFIX}:{employee_id}"
        await self.redis.setex(key, ttl_seconds, datetime.now(timezone.utc).isoformat())

    async def is_alive(self, employee_id: str) -> bool:
        """Check if an employee has a recent heartbeat."""
        key = f"{HEARTBEAT_PREFIX}:{employee_id}"
        return await self.redis.exists(key) > 0

    async def get_stale(self, threshold_seconds: int = 120) -> list:
        """Return employees with no recent heartbeat."""
        keys = await self.redis.keys(f"{HEARTBEAT_PREFIX}:*")
        stale = []
        for key in keys:
            emp_id = key.decode().split(":")[-1] if isinstance(key, bytes) else key.split(":")[-1]
            if not await self.is_alive(emp_id):
                stale.append(emp_id)
        return stale


class WorkerPool:
    """Async worker pool that consumes tasks from the queue."""

    def __init__(
        self,
        redis_client: redis.Redis,
        bus: EventBus,
        max_workers: int = 4,
        poll_interval: float = 1.0,
    ):
        self.redis = redis_client
        self.bus = bus
        self.queue = TaskQueue(redis_client)
        self.heartbeat = HeartbeatMonitor(redis_client)
        self.retry = RetryPolicy()
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.handlers: Dict[str, Callable] = {}
        self._tasks: list = []
        self._running = False

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler for a task type."""
        self.handlers[task_type] = handler
        logger.info("handler_registered", task_type=task_type)

    async def start(self) -> None:
        """Start the worker pool."""
        self._running = True
        for i in range(self.max_workers):
            t = asyncio.create_task(self._worker_loop(worker_id=i))
            self._tasks.append(t)
        logger.info("worker_pool_started", workers=self.max_workers)

    async def stop(self) -> None:
        """Stop the worker pool gracefully."""
        self._running = False
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("worker_pool_stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Main loop for a single worker."""
        worker_key = f"{WORKER_PREFIX}:{worker_id}"
        await self.redis.setex(worker_key, 300, "active")
        while self._running:
            try:
                await self.redis.setex(worker_key, 300, "active")
                task = await self.queue.dequeue(timeout=5)
                if task is None:
                    await asyncio.sleep(self.poll_interval)
                    continue
                await self._execute_task(task)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("worker_loop_error", worker=worker_id, error=str(e))
                await asyncio.sleep(self.poll_interval)
        await self.redis.delete(worker_key)

    async def _execute_task(self, task: RuntimeTask) -> None:
        """Execute a single task with retry logic."""
        handler = self.handlers.get(task.task_type)
        if handler is None:
            logger.warning("no_handler_for_task", task_type=task.task_type, task_id=task.task_id)
            return

        try:
            await self.heartbeat.beat(task.employee_id)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task)
            else:
                result = handler(task)
            logger.info("task_completed", task_id=task.task_id, type=task.task_type)
            await self.bus.publish(MembraEvent(
                event_type="employee.submitted_report",
                source="agent_runtime",
                payload={"task_id": task.task_id, "status": "completed", "result": result},
                employee_id=task.employee_id,
                trace_id=task.trace_id,
            ))
        except Exception as e:
            logger.error("task_failed", task_id=task.task_id, error=str(e), retries=task.retries)
            if self.retry.can_retry(task.retries):
                task.retries += 1
                delay = self.retry.next_delay(task.retries)
                await asyncio.sleep(delay)
                await self.queue.enqueue(task)
                await self.bus.publish(MembraEvent(
                    event_type="system.health_check",
                    source="agent_runtime",
                    payload={"task_id": task.task_id, "status": "retrying", "retry": task.retries},
                    employee_id=task.employee_id,
                    trace_id=task.trace_id,
                ))
            else:
                await self.bus.publish(MembraEvent(
                    event_type="system.health_check",
                    source="agent_runtime",
                    payload={"task_id": task.task_id, "status": "failed_permanently", "error": str(e)},
                    employee_id=task.employee_id,
                    trace_id=task.trace_id,
                ))


class AgentRuntime:
    """Facade for the complete agent runtime."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self.pool: Optional[WorkerPool] = None

    async def start(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        bus = await get_event_bus()
        self.pool = WorkerPool(self._redis, bus)
        await self.pool.start()
        logger.info("agent_runtime_started")

    async def stop(self) -> None:
        if self.pool:
            await self.pool.stop()
        if self._redis:
            await self._redis.close()
        logger.info("agent_runtime_stopped")

    async def submit_task(self, task: RuntimeTask) -> None:
        if self.pool is None:
            raise RuntimeError("AgentRuntime not started")
        await self.pool.queue.enqueue(task)

    def register_handler(self, task_type: str, handler: Callable) -> None:
        if self.pool is None:
            raise RuntimeError("AgentRuntime not started")
        self.pool.register_handler(task_type, handler)

    async def heartbeat(self, employee_id: str) -> None:
        if self.pool:
            await self.pool.heartbeat.beat(employee_id)

    async def is_alive(self, employee_id: str) -> bool:
        if self.pool:
            return await self.pool.heartbeat.is_alive(employee_id)
        return False


# Singleton
_runtime: Optional[AgentRuntime] = None


async def get_agent_runtime() -> AgentRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime()
        await _runtime.start()
    return _runtime
