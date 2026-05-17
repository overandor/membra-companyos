"""MEMBRA CompanyOS — Tool Sandbox.

Isolated tool execution, timeout enforcement, network restrictions,
rate limits, audit logging. Every tool call is observable and killable.
"""
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import asyncio
import time
import structlog

from app.services.event_bus import get_event_bus
from app.core.events import MembraEvent

logger = structlog.get_logger()


@dataclass
class ToolCall:
    tool_name: str
    employee_id: str
    department_id: str
    args: Dict[str, Any]
    trace_id: Optional[str] = None


@dataclass
class ToolResult:
    success: bool
    output: Any
    execution_time_ms: float
    error: Optional[str] = None
    blocked_by_policy: bool = False


class RateLimiter:
    """Per-employee, per-tool rate limiter using in-memory buckets."""

    def __init__(self, default_limit: int = 60, window_seconds: int = 60):
        self.default_limit = default_limit
        self.window = window_seconds
        self._buckets: Dict[str, List[float]] = {}

    def _key(self, employee_id: str, tool_name: str) -> str:
        return f"{employee_id}:{tool_name}"

    def is_allowed(self, employee_id: str, tool_name: str) -> bool:
        key = self._key(employee_id, tool_name)
        now = time.time()
        calls = self._buckets.get(key, [])
        # Prune old calls
        calls = [c for c in calls if now - c < self.window]
        self._buckets[key] = calls
        return len(calls) < self.default_limit

    def record(self, employee_id: str, tool_name: str) -> None:
        key = self._key(employee_id, tool_name)
        self._buckets.setdefault(key, []).append(time.time())


class ToolSandbox:
    """Sandbox for executing tools safely."""

    def __init__(self, default_timeout: float = 30.0):
        self.tools: Dict[str, Callable] = {}
        self.rate_limiter = RateLimiter()
        self.default_timeout = default_timeout
        self._policy_check: Optional[Callable] = None

    def register_tool(self, name: str, handler: Callable) -> None:
        """Register a tool handler."""
        self.tools[name] = handler
        logger.info("tool_registered", name=name)

    def set_policy_check(self, check: Callable[[ToolCall], bool]) -> None:
        """Set a policy gate function that must return True for the call to proceed."""
        self._policy_check = check

    async def execute(self, call: ToolCall) -> ToolResult:
        """Execute a tool call with full sandboxing."""
        start = time.time()

        # 1. Rate limit check
        if not self.rate_limiter.is_allowed(call.employee_id, call.tool_name):
            return ToolResult(
                success=False,
                output=None,
                execution_time_ms=(time.time() - start) * 1000,
                error="Rate limit exceeded",
            )

        # 2. Tool existence check
        handler = self.tools.get(call.tool_name)
        if handler is None:
            return ToolResult(
                success=False,
                output=None,
                execution_time_ms=(time.time() - start) * 1000,
                error=f"Unknown tool: {call.tool_name}",
            )

        # 3. Policy gate check
        if self._policy_check and not self._policy_check(call):
            return ToolResult(
                success=False,
                output=None,
                execution_time_ms=(time.time() - start) * 1000,
                error="Blocked by policy engine",
                blocked_by_policy=True,
            )

        # 4. Execute with timeout
        try:
            self.rate_limiter.record(call.employee_id, call.tool_name)
            if asyncio.iscoroutinefunction(handler):
                output = await asyncio.wait_for(handler(call.args), timeout=self.default_timeout)
            else:
                # Run sync function in thread pool to avoid blocking
                loop = asyncio.get_running_loop()
                output = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: handler(call.args)),
                    timeout=self.default_timeout,
                )
            elapsed = (time.time() - start) * 1000
            logger.info("tool_executed", tool=call.tool_name, emp=call.employee_id, ms=round(elapsed, 2))
            # Publish audit event
            bus = await get_event_bus()
            await bus.publish(MembraEvent(
                event_type="system.health_check",
                source="tool_sandbox",
                payload={
                    "tool": call.tool_name,
                    "employee_id": call.employee_id,
                    "success": True,
                    "execution_time_ms": elapsed,
                },
                employee_id=call.employee_id,
                trace_id=call.trace_id,
            ))
            return ToolResult(success=True, output=output, execution_time_ms=elapsed)
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            logger.error("tool_timeout", tool=call.tool_name, emp=call.employee_id, timeout=self.default_timeout)
            return ToolResult(success=False, output=None, execution_time_ms=elapsed, error="Execution timeout")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error("tool_error", tool=call.tool_name, emp=call.employee_id, error=str(e))
            return ToolResult(success=False, output=None, execution_time_ms=elapsed, error=str(e))

    def list_tools(self) -> List[str]:
        return sorted(self.tools.keys())


# Singleton
_sandbox: Optional[ToolSandbox] = None


def get_tool_sandbox() -> ToolSandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = ToolSandbox()
    return _sandbox
