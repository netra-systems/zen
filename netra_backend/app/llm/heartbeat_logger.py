"""LLM heartbeat logging module.

Provides heartbeat logging for long-running LLM calls with correlation tracking.
Each function must be ≤8 lines as per architecture requirements.
"""
import asyncio
import time
import uuid
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HeartbeatLogger:
    """Manages heartbeat logging for long-running LLM operations."""
    
    def __init__(self, interval_seconds: float = 2.5):
        """Initialize heartbeat logger with interval."""
        self.interval_seconds = interval_seconds
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._start_times: Dict[str, float] = {}
        self._agent_names: Dict[str, str] = {}
        self.log_as_json = True  # Default to JSON logging

    def generate_correlation_id(self) -> str:
        """Generate unique correlation ID for tracking."""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        return UnifiedIdGenerator.generate_base_id("llm_heartbeat")

    def start_heartbeat(self, correlation_id: str, agent_name: str) -> None:
        """Start heartbeat logging for an LLM operation."""
        self._record_heartbeat_start(correlation_id, agent_name)
        self._create_heartbeat_task(correlation_id)

    def _record_heartbeat_start(self, correlation_id: str, agent_name: str) -> None:
        """Record the start of a heartbeat operation."""
        self._start_times[correlation_id] = time.time()
        self._agent_names[correlation_id] = agent_name

    def _create_heartbeat_task(self, correlation_id: str) -> None:
        """Create the async heartbeat task."""
        try:
            task = asyncio.create_task(self._heartbeat_loop(correlation_id))
            self._active_tasks[correlation_id] = task
        except RuntimeError:
            pass

    def stop_heartbeat(self, correlation_id: str) -> None:
        """Stop heartbeat logging for an LLM operation."""
        if correlation_id in self._active_tasks:
            self._cancel_task(correlation_id)
            self._cleanup_tracking_data(correlation_id)

    def _cancel_task(self, correlation_id: str) -> None:
        """Cancel the heartbeat task."""
        task = self._active_tasks[correlation_id]
        task.cancel()
        del self._active_tasks[correlation_id]

    def _cleanup_tracking_data(self, correlation_id: str) -> None:
        """Clean up tracking data for correlation ID."""
        self._start_times.pop(correlation_id, None)
        self._agent_names.pop(correlation_id, None)

    async def _heartbeat_loop(self, correlation_id: str) -> None:
        """Main heartbeat loop that logs status periodically."""
        try:
            while True:
                await asyncio.sleep(self.interval_seconds)
                self._log_heartbeat(correlation_id)
        except asyncio.CancelledError:
            pass

    def _log_heartbeat(self, correlation_id: str) -> None:
        """Log a single heartbeat message with JSON data."""
        elapsed_time = self._calculate_elapsed_time(correlation_id)
        agent_name = self._agent_names.get(correlation_id, "unknown")
        heartbeat_data = self._build_heartbeat_data(agent_name, correlation_id, elapsed_time)
        self._log_heartbeat_data(heartbeat_data)

    def _calculate_elapsed_time(self, correlation_id: str) -> float:
        """Calculate elapsed time since operation start."""
        start_time = self._start_times.get(correlation_id, time.time())
        return time.time() - start_time

    def _build_heartbeat_data(self, agent_name: str, correlation_id: str, elapsed_time: float) -> Dict[str, Any]:
        """Build heartbeat data dictionary for JSON logging."""
        return {
            "type": "llm_heartbeat",
            "agent_name": agent_name,
            "correlation_id": correlation_id,
            "elapsed_time_seconds": round(elapsed_time, 1),
            "status": "processing",
            "timestamp": time.time()
        }

    def _log_heartbeat_data(self, data: Dict[str, Any]) -> None:
        """Log heartbeat data as JSON or text."""
        if self.log_as_json:
            import json
            logger.info(f"LLM heartbeat: {json.dumps(data)}")
        else:
            self._log_heartbeat_text(data)

    def _log_heartbeat_text(self, data: Dict[str, Any]) -> None:
        """Log heartbeat in text format."""
        msg = self._build_heartbeat_text_message(data)
        logger.info(msg)
    
    def _build_heartbeat_text_message(self, data: Dict[str, Any]) -> str:
        """Build heartbeat text message from data."""
        return (f"LLM heartbeat: {data['agent_name']} - {data['correlation_id']} - "
                f"elapsed: {data['elapsed_time_seconds']}s - status: {data['status']}")

    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active operations."""
        return {correlation_id: self._get_operation_info(correlation_id)
                for correlation_id in self._active_tasks}

    def _get_operation_info(self, correlation_id: str) -> Dict[str, Any]:
        """Get operation information for a correlation ID."""
        return {
            "agent_name": self._agent_names.get(correlation_id, "unknown"),
            "elapsed_time": self._calculate_elapsed_time(correlation_id),
            "start_time": self._start_times.get(correlation_id, 0)
        }


# Global heartbeat logger instance (will be configured on first use)
_heartbeat_logger: Optional[HeartbeatLogger] = None


def get_heartbeat_logger() -> HeartbeatLogger:
    """Get the global heartbeat logger instance."""
    global _heartbeat_logger
    if _heartbeat_logger is None:
        _heartbeat_logger = HeartbeatLogger()
    return _heartbeat_logger


def start_llm_heartbeat(correlation_id: str, agent_name: str) -> None:
    """Start heartbeat logging for an LLM operation."""
    get_heartbeat_logger().start_heartbeat(correlation_id, agent_name)


def stop_llm_heartbeat(correlation_id: str) -> None:
    """Stop heartbeat logging for an LLM operation."""
    get_heartbeat_logger().stop_heartbeat(correlation_id)


def generate_llm_correlation_id() -> str:
    """Generate a new correlation ID for LLM operations."""
    return get_heartbeat_logger().generate_correlation_id()