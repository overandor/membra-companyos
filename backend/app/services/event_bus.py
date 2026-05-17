"""MEMBRA CompanyOS — Event Bus Service.

Redis-backed async pub/sub with typed events.
All services publish and subscribe through this bus for loose coupling.
"""
from typing import Callable, Dict, List, Any, Optional
import asyncio
import json
import redis.asyncio as redis
from app.core.config import settings
from app.core.events import MembraEvent
import structlog

logger = structlog.get_logger()


class EventBus:
    """Async event bus using Redis pub/sub."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._listeners: Dict[str, List[Callable]] = {}
        self._task: Optional[asyncio.Task] = None

    async def connect(self):
        """Connect to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            self._pubsub = self._redis.pubsub()
            logger.info("event_bus_connected", redis=settings.redis_url)

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("event_bus_disconnected")

    async def publish(self, event: MembraEvent) -> None:
        """Publish an event to the bus."""
        try:
            if self._redis is None:
                await self.connect()
            payload = json.dumps(event.model_dump(mode="json"), default=str)
            await self._redis.publish(event.event_type, payload)
            # Also publish to a catch-all channel
            await self._redis.publish("membra.events.all", payload)
            logger.debug("event_published", event_type=event.event_type, source=event.source)
        except Exception as e:
            logger.warning("event_publish_failed", event_type=event.event_type, error=str(e))

    def subscribe(self, event_type: str, handler: Callable[[MembraEvent], Any]) -> None:
        """Subscribe to an event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        logger.info("event_subscribed", event_type=event_type)

    async def start_listener(self) -> None:
        """Start the background listener task."""
        if self._pubsub is None:
            await self.connect()
        channels = list(self._listeners.keys()) + ["membra.events.all"]
        await self._pubsub.subscribe(*channels)
        self._task = asyncio.create_task(self._listener_loop())
        logger.info("event_listener_started", channels=channels)

    async def _listener_loop(self) -> None:
        """Background loop that reads messages and dispatches."""
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    event = MembraEvent(**data)
                    await self._dispatch(event)
                except Exception as e:
                    logger.error("event_dispatch_error", error=str(e))
        except asyncio.CancelledError:
            logger.info("event_listener_cancelled")
        except Exception as e:
            logger.error("event_listener_fatal", error=str(e))

    async def _dispatch(self, event: MembraEvent) -> None:
        """Dispatch event to registered handlers."""
        handlers = self._listeners.get(event.event_type, [])
        # Also dispatch catch-all handlers
        handlers += self._listeners.get("membra.events.all", [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error("event_handler_error", event_type=event.event_type, error=str(e))


# Singleton
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
    return _event_bus
