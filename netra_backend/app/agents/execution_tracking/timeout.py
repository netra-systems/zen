"""Timeout module for agent execution tracking.

This module provides timeout management functionality that has been consolidated
into the SSOT agent_execution_tracker module. This module is a compatibility
layer for existing code that expects the timeout module.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Any, Dict
import asyncio
from datetime import datetime, timezone

# Import SSOT TimeoutConfig for compatibility
try:
    from netra_backend.app.core.agent_execution_tracker import TimeoutConfig
except ImportError:
    # Fallback definition if SSOT is not available
    @dataclass
    class TimeoutConfig:
        """Fallback timeout configuration."""
        agent_execution_timeout: float = 25.0
        llm_api_timeout: float = 15.0


@dataclass
class TimeoutInfo:
    """Information about an execution timeout.

    This is a compatibility class for the timeout module structure.
    The SSOT implementation now uses TimeoutConfig in the core module.
    """
    execution_id: str
    timeout_seconds: float
    elapsed_seconds: float
    started_at: datetime
    timeout_at: datetime
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @property
    def is_expired(self) -> bool:
        """Check if the timeout has been exceeded."""
        return self.elapsed_seconds >= self.timeout_seconds


class TimeoutManager:
    """Timeout manager for agent executions.

    This is a compatibility class. The SSOT implementation is in
    netra_backend.app.core.agent_execution_tracker.AgentExecutionTracker
    """

    def __init__(self, check_interval_seconds: float = 5.0):
        self.check_interval_seconds = check_interval_seconds
        self._tracked_executions: Dict[str, TimeoutInfo] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._shutdown = False

    async def start_monitoring(self):
        """Start monitoring for timeouts."""
        if self._monitoring_task is not None:
            return

        self._shutdown = False
        self._monitoring_task = asyncio.create_task(self._monitor_timeouts())

    async def stop_monitoring(self):
        """Stop monitoring for timeouts."""
        self._shutdown = True
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

    def add_execution(self, execution_id: str, timeout_seconds: float) -> TimeoutInfo:
        """Add execution to timeout tracking."""
        now = datetime.now(timezone.utc)
        timeout_info = TimeoutInfo(
            execution_id=execution_id,
            timeout_seconds=timeout_seconds,
            elapsed_seconds=0.0,
            started_at=now,
            timeout_at=now  # Will be updated during monitoring
        )
        self._tracked_executions[execution_id] = timeout_info
        return timeout_info

    def remove_execution(self, execution_id: str):
        """Remove execution from timeout tracking."""
        self._tracked_executions.pop(execution_id, None)

    def get_timeout_info(self, execution_id: str) -> Optional[TimeoutInfo]:
        """Get timeout info for an execution."""
        return self._tracked_executions.get(execution_id)

    async def _monitor_timeouts(self):
        """Monitor for execution timeouts."""
        while not self._shutdown:
            try:
                now = datetime.now(timezone.utc)
                expired_executions = []

                for execution_id, timeout_info in self._tracked_executions.items():
                    elapsed = (now - timeout_info.started_at).total_seconds()
                    timeout_info.elapsed_seconds = elapsed

                    if elapsed >= timeout_info.timeout_seconds:
                        expired_executions.append((execution_id, timeout_info))

                # Handle expired executions
                for execution_id, timeout_info in expired_executions:
                    await self._handle_timeout(execution_id, timeout_info)
                    self.remove_execution(execution_id)

                await asyncio.sleep(self.check_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue monitoring
                print(f"Error in timeout monitoring: {e}")
                await asyncio.sleep(1.0)

    async def _handle_timeout(self, execution_id: str, timeout_info: TimeoutInfo):
        """Handle timeout for an execution.

        This is a placeholder that should be overridden by subclasses
        or connected to a callback system.
        """
        pass  # Will be handled by the calling system