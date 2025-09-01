"""TimeoutManager - Enforces execution timeouts and detects hung agents.

This module provides configurable timeout management for agent executions,
preventing hung agents from causing infinite loading states and resource leaks.

Business Value: Ensures all agent executions complete within reasonable time,
preventing resource exhaustion and providing predictable user experience.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TimeoutInfo(BaseModel):
    """Information about execution timeout configuration and status."""
    execution_id: str
    timeout_seconds: float
    started_at: datetime
    timeout_at: datetime
    remaining_seconds: float
    has_timed_out: bool
    timeout_reason: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TimeoutManager:
    """Enforces execution timeouts and detects hung agents.
    
    This class provides configurable timeout management for different types
    of agent executions, with automatic cleanup and recovery triggering.
    
    Key Features:
    - Agent-specific timeout configuration
    - Real-time timeout monitoring
    - Automatic timeout detection and cleanup
    - Extension support for long-running operations
    - Comprehensive metrics and reporting
    """
    
    def __init__(self, check_interval_seconds: float = 5.0):
        """Initialize TimeoutManager with configuration.
        
        Args:
            check_interval_seconds: How often to check for timeouts
        """
        self.check_interval = check_interval_seconds
        
        # Timeout configuration per agent type
        self.timeout_config = {
            "default": 30.0,
            "triage": 15.0,
            "data": 60.0,
            "optimization": 45.0,
            "reporting": 30.0,
            "actions": 20.0,
            "synthetic_data": 120.0,
            "corpus_admin": 30.0,
            "data_helper": 45.0
        }
        
        # Monitoring state
        self._timeouts: Dict[str, TimeoutInfo] = {}
        self._lock = asyncio.Lock()
        self._timeout_callbacks: List[Callable] = []
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # Metrics
        self._total_timeouts_set = 0
        self._timeout_triggers = 0
        self._extensions_granted = 0
        self._manual_clears = 0
        
        logger.info(f"✅ TimeoutManager initialized with {check_interval_seconds}s check interval")
    
    def get_timeout_for_agent(self, agent_name: str) -> float:
        """Get configured timeout for an agent type.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            float: Timeout in seconds
        """
        # Extract agent type from name (handle names like "triage_v2" -> "triage")
        agent_type = agent_name.lower().split('_')[0]
        return self.timeout_config.get(agent_type, self.timeout_config["default"])
    
    def set_agent_timeout(self, agent_name: str, timeout_seconds: float) -> None:
        """Set timeout configuration for an agent type.
        
        Args:
            agent_name: Name of the agent type
            timeout_seconds: Timeout in seconds
        """
        agent_type = agent_name.lower().split('_')[0]
        old_timeout = self.timeout_config.get(agent_type, self.timeout_config["default"])
        self.timeout_config[agent_type] = timeout_seconds
        
        logger.info(f"🕐 Updated timeout for {agent_type}: {old_timeout}s -> {timeout_seconds}s")
    
    async def set_timeout(self, execution_id: str, timeout_seconds: Optional[float] = None, agent_name: Optional[str] = None) -> TimeoutInfo:
        """Set timeout for an execution.
        
        Args:
            execution_id: The execution ID to monitor
            timeout_seconds: Custom timeout, or None to use agent default
            agent_name: Agent name for default timeout lookup
            
        Returns:
            TimeoutInfo: The timeout information record
            
        Raises:
            ValueError: If execution_id is invalid
        """
        if not execution_id:
            raise ValueError("execution_id is required")
        
        # Determine timeout value
        if timeout_seconds is None:
            if agent_name:
                timeout_seconds = self.get_timeout_for_agent(agent_name)
            else:
                timeout_seconds = self.timeout_config["default"]
        
        now = datetime.now(UTC)
        timeout_at = now + timedelta(seconds=timeout_seconds)
        
        timeout_info = TimeoutInfo(
            execution_id=execution_id,
            timeout_seconds=timeout_seconds,
            started_at=now,
            timeout_at=timeout_at,
            remaining_seconds=timeout_seconds,
            has_timed_out=False
        )
        
        async with self._lock:
            self._timeouts[execution_id] = timeout_info
            self._total_timeouts_set += 1
        
        # Start monitor task if not running
        if not self._is_running:
            await self._start_monitor_task()
        
        logger.info(f"⏰ Set timeout for {execution_id}: {timeout_seconds}s ({agent_name or 'unknown'})")
        return timeout_info
    
    async def extend_timeout(self, execution_id: str, additional_seconds: float, reason: str = "extension_requested") -> bool:
        """Extend timeout for an execution.
        
        This is useful for operations that need more time, like complex data analysis.
        
        Args:
            execution_id: The execution ID to extend
            additional_seconds: Additional time to add
            reason: Reason for the extension
            
        Returns:
            bool: True if extended, False if execution not found or already timed out
        """
        async with self._lock:
            if execution_id not in self._timeouts:
                return False
            
            timeout_info = self._timeouts[execution_id]
            
            if timeout_info.has_timed_out:
                logger.warning(f"⚠️ Cannot extend timeout for already timed out execution: {execution_id}")
                return False
            
            # Extend the timeout
            timeout_info.timeout_at += timedelta(seconds=additional_seconds)
            timeout_info.timeout_seconds += additional_seconds
            now = datetime.now(UTC)
            timeout_info.remaining_seconds = (timeout_info.timeout_at - now).total_seconds()
            
            self._extensions_granted += 1
        
        logger.info(
            f"⏰ Extended timeout for {execution_id}: +{additional_seconds}s "
            f"(total: {timeout_info.timeout_seconds}s, reason: {reason})"
        )
        return True
    
    async def clear_timeout(self, execution_id: str) -> bool:
        """Clear timeout for an execution (when it completes).
        
        Args:
            execution_id: The execution ID to clear
            
        Returns:
            bool: True if cleared, False if not found
        """
        async with self._lock:
            if execution_id not in self._timeouts:
                return False
            
            del self._timeouts[execution_id]
            self._manual_clears += 1
        
        logger.debug(f"✅ Cleared timeout for {execution_id}")
        return True
    
    async def check_timeouts(self) -> List[str]:
        """Check for timed out executions and return their IDs.
        
        Returns:
            List of execution IDs that have timed out
        """
        now = datetime.now(UTC)
        timed_out_executions = []
        
        async with self._lock:
            for execution_id, timeout_info in list(self._timeouts.items()):
                # Update remaining time
                timeout_info.remaining_seconds = (timeout_info.timeout_at - now).total_seconds()
                
                if not timeout_info.has_timed_out and now >= timeout_info.timeout_at:
                    timeout_info.has_timed_out = True
                    timeout_info.timeout_reason = "execution_timeout"
                    timed_out_executions.append(execution_id)
                    
                    self._timeout_triggers += 1
                    
                    logger.error(
                        f"⏰ TIMEOUT DETECTED: {execution_id} - "
                        f"exceeded {timeout_info.timeout_seconds}s limit"
                    )
        
        return timed_out_executions
    
    async def get_remaining_time(self, execution_id: str) -> Optional[float]:
        """Get remaining time for an execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            float: Remaining seconds, or None if not found
        """
        async with self._lock:
            if execution_id not in self._timeouts:
                return None
            
            timeout_info = self._timeouts[execution_id]
            now = datetime.now(UTC)
            remaining = (timeout_info.timeout_at - now).total_seconds()
            return max(0.0, remaining)
    
    async def get_timeout_info(self, execution_id: str) -> Optional[TimeoutInfo]:
        """Get detailed timeout information for an execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            TimeoutInfo or None if not found
        """
        async with self._lock:
            timeout_info = self._timeouts.get(execution_id)
            if timeout_info:
                # Update remaining time
                now = datetime.now(UTC)
                timeout_info.remaining_seconds = (timeout_info.timeout_at - now).total_seconds()
            return timeout_info
    
    async def get_all_timeouts(self) -> List[TimeoutInfo]:
        """Get all timeout information.
        
        Returns:
            List of TimeoutInfo objects
        """
        async with self._lock:
            now = datetime.now(UTC)
            # Update remaining times
            for timeout_info in self._timeouts.values():
                timeout_info.remaining_seconds = (timeout_info.timeout_at - now).total_seconds()
            
            return list(self._timeouts.values())
    
    async def get_expired_timeouts(self) -> List[TimeoutInfo]:
        """Get executions that have timed out.
        
        Returns:
            List of TimeoutInfo objects for timed out executions
        """
        async with self._lock:
            return [info for info in self._timeouts.values() if info.has_timed_out]
    
    def add_timeout_callback(self, callback: Callable[[str, TimeoutInfo], None]) -> None:
        """Add callback to be called when timeout is detected.
        
        Args:
            callback: Async function to call with (execution_id, timeout_info)
        """
        self._timeout_callbacks.append(callback)
        logger.debug(f"Added timeout callback: {callback.__name__}")
    
    async def _start_monitor_task(self) -> None:
        """Start the background timeout monitoring task."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("🔍 Started timeout monitoring loop")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop that checks for timeouts."""
        while self._is_running:
            try:
                await asyncio.sleep(self.check_interval)
                timed_out_ids = await self.check_timeouts()
                
                # Trigger callbacks for timed out executions
                for execution_id in timed_out_ids:
                    timeout_info = await self.get_timeout_info(execution_id)
                    if timeout_info:
                        await self._trigger_timeout_callbacks(execution_id, timeout_info)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in timeout monitor loop: {e}")
                # Continue monitoring even if there's an error
                await asyncio.sleep(1)
    
    async def _trigger_timeout_callbacks(self, execution_id: str, timeout_info: TimeoutInfo) -> None:
        """Trigger all timeout callbacks for a timed out execution."""
        logger.critical(
            f"🚨 TRIGGERING TIMEOUT RECOVERY for: {execution_id} - "
            f"exceeded {timeout_info.timeout_seconds}s limit"
        )
        
        # Call all registered timeout callbacks
        for callback in self._timeout_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution_id, timeout_info)
                else:
                    callback(execution_id, timeout_info)
            except Exception as e:
                logger.error(f"Error in timeout callback {callback.__name__}: {e}")
    
    async def get_timeout_metrics(self) -> Dict[str, Any]:
        """Get timeout metrics.
        
        Returns:
            Dictionary with timeout statistics
        """
        async with self._lock:
            active_timeouts = len(self._timeouts)
            timed_out_count = len([info for info in self._timeouts.values() if info.has_timed_out])
        
        return {
            "is_running": self._is_running,
            "active_timeouts": active_timeouts,
            "timed_out_executions": timed_out_count,
            "total_timeouts_set": self._total_timeouts_set,
            "timeout_triggers": self._timeout_triggers,
            "extensions_granted": self._extensions_granted,
            "manual_clears": self._manual_clears,
            "check_interval_seconds": self.check_interval,
            "timeout_config": self.timeout_config.copy()
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with health information
        """
        metrics = await self.get_timeout_metrics()
        expired_timeouts = await self.get_expired_timeouts()
        
        # Determine health based on expired timeouts
        status = "healthy"
        if expired_timeouts:
            if len(expired_timeouts) > 5:
                status = "critical"
            elif len(expired_timeouts) > 2:
                status = "degraded"
            else:
                status = "warning"
        
        return {
            "status": status,
            "monitor_running": self._is_running,
            "expired_timeouts": [
                {
                    "execution_id": info.execution_id,
                    "timeout_seconds": info.timeout_seconds,
                    "started_at": info.started_at.isoformat(),
                    "timeout_at": info.timeout_at.isoformat(),
                    "timeout_reason": info.timeout_reason
                }
                for info in expired_timeouts
            ],
            **metrics
        }
    
    async def bulk_clear_timeouts(self, execution_ids: List[str]) -> int:
        """Clear timeouts for multiple executions.
        
        Args:
            execution_ids: List of execution IDs to clear
            
        Returns:
            int: Number of timeouts actually cleared
        """
        cleared_count = 0
        async with self._lock:
            for execution_id in execution_ids:
                if execution_id in self._timeouts:
                    del self._timeouts[execution_id]
                    cleared_count += 1
        
        if cleared_count > 0:
            logger.info(f"🧹 Bulk cleared {cleared_count} timeouts")
        
        return cleared_count
    
    async def get_timeout_summary(self) -> Dict[str, Any]:
        """Get a summary of timeout status for monitoring dashboards.
        
        Returns:
            Dictionary with timeout summary information
        """
        all_timeouts = await self.get_all_timeouts()
        
        summary = {
            "total_active": len(all_timeouts),
            "by_agent_type": {},
            "timeout_distribution": {},
            "remaining_time_stats": {
                "min": float('inf'),
                "max": 0.0,
                "avg": 0.0
            },
            "urgent_timeouts": []  # < 10 seconds remaining
        }
        
        remaining_times = []
        
        for timeout_info in all_timeouts:
            # Count by agent type (extract from execution_id)
            agent_type = "unknown"
            if "_" in timeout_info.execution_id:
                agent_type = timeout_info.execution_id.split("_")[0]
            
            summary["by_agent_type"][agent_type] = summary["by_agent_type"].get(agent_type, 0) + 1
            
            # Count by timeout duration
            timeout_bucket = f"{int(timeout_info.timeout_seconds // 10) * 10}s"
            summary["timeout_distribution"][timeout_bucket] = summary["timeout_distribution"].get(timeout_bucket, 0) + 1
            
            # Track remaining time
            if not timeout_info.has_timed_out:
                remaining_times.append(timeout_info.remaining_seconds)
                
                # Flag urgent timeouts
                if timeout_info.remaining_seconds < 10:
                    summary["urgent_timeouts"].append({
                        "execution_id": timeout_info.execution_id,
                        "remaining_seconds": timeout_info.remaining_seconds
                    })
        
        # Calculate remaining time statistics
        if remaining_times:
            summary["remaining_time_stats"] = {
                "min": min(remaining_times),
                "max": max(remaining_times),
                "avg": sum(remaining_times) / len(remaining_times)
            }
        
        return summary
    
    async def shutdown(self) -> None:
        """Shutdown the timeout manager and cleanup resources."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            self._timeouts.clear()
        
        logger.info("🛑 TimeoutManager shutdown completed")
    
    def __len__(self) -> int:
        """Return number of active timeouts."""
        return len(self._timeouts)