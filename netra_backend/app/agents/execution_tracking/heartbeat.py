"""HeartbeatMonitor - Detects dead/stuck agents via heartbeat monitoring.

This module implements real-time heartbeat monitoring to detect agent death
within 30 seconds, preventing silent failures and infinite loading states.

Business Value: Core detection mechanism that enables immediate recovery from
agent failures, directly supporting the mission-critical chat functionality.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HeartbeatStatus(BaseModel):
    """Status of an execution's heartbeat monitoring."""
    execution_id: str
    last_heartbeat: datetime
    is_alive: bool
    missed_heartbeats: int
    heartbeat_interval: float
    next_expected: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HeartbeatMonitor:
    """Monitors agent liveness during execution with periodic heartbeat checks.
    
    This class provides real-time monitoring of agent heartbeats to detect
    stuck or dead agents within the configured timeout period (default 30 seconds).
    
    Key Features:
    - Configurable heartbeat intervals (default 5 seconds)
    - Death detection within 30 seconds (6 missed heartbeats)
    - Automatic recovery trigger on heartbeat failure
    - Thread-safe monitoring for concurrent executions
    - Comprehensive metrics and health reporting
    """
    
    def __init__(
        self,
        heartbeat_interval_seconds: float = 5.0,
        timeout_seconds: float = 30.0,
        max_missed_heartbeats: int = 6,
        recovery_delay_seconds: float = 2.0
    ):
        """Initialize HeartbeatMonitor with configuration.
        
        Args:
            heartbeat_interval_seconds: Expected interval between heartbeats
            timeout_seconds: Total timeout before considering agent dead
            max_missed_heartbeats: Maximum missed heartbeats before declaring dead
            recovery_delay_seconds: Delay before triggering recovery
        """
        self.heartbeat_interval = heartbeat_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.max_missed_heartbeats = max_missed_heartbeats
        self.recovery_delay = recovery_delay_seconds
        
        # Monitoring state
        self._monitored_executions: Dict[str, HeartbeatStatus] = {}
        self._lock = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None
        self._failure_callbacks: List[Callable] = []
        self._is_running = False
        
        # Metrics
        self._total_monitored = 0
        self._heartbeat_failures = 0
        self._false_positives = 0
        self._recovery_triggers = 0
        
        logger.info(
            f" PASS:  HeartbeatMonitor initialized: {heartbeat_interval_seconds}s interval, "
            f"{timeout_seconds}s timeout, max {max_missed_heartbeats} missed beats"
        )
    
    async def start_monitoring(self, execution_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start monitoring heartbeat for an execution.
        
        Args:
            execution_id: Unique execution ID to monitor
            metadata: Optional metadata for the execution
            
        Raises:
            ValueError: If execution_id is invalid or already being monitored
        """
        if not execution_id:
            raise ValueError("execution_id is required")
        
        async with self._lock:
            if execution_id in self._monitored_executions:
                logger.warning(f" WARNING: [U+FE0F] Already monitoring execution {execution_id}")
                return
            
            now = datetime.now(UTC)
            status = HeartbeatStatus(
                execution_id=execution_id,
                last_heartbeat=now,
                is_alive=True,
                missed_heartbeats=0,
                heartbeat_interval=self.heartbeat_interval,
                next_expected=now + timedelta(seconds=self.heartbeat_interval)
            )
            
            self._monitored_executions[execution_id] = status
            self._total_monitored += 1
        
        # Start monitor task if not running
        if not self._is_running:
            await self._start_monitor_task()
        
        logger.info(f"[U+1F497] Started heartbeat monitoring for execution {execution_id}")
    
    async def send_heartbeat(self, execution_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send heartbeat for an execution.
        
        Args:
            execution_id: The execution ID sending the heartbeat
            metadata: Optional metadata about current execution state
            
        Returns:
            bool: True if heartbeat was recorded, False if not monitoring this execution
        """
        async with self._lock:
            if execution_id not in self._monitored_executions:
                logger.debug(f"Heartbeat received for unmonitored execution: {execution_id}")
                return False
            
            status = self._monitored_executions[execution_id]
            now = datetime.now(UTC)
            
            # Update heartbeat status
            status.last_heartbeat = now
            status.next_expected = now + timedelta(seconds=self.heartbeat_interval)
            status.missed_heartbeats = 0
            status.is_alive = True
            
        logger.debug(f"[U+1F497] Heartbeat received for execution {execution_id}")
        return True
    
    async def stop_monitoring(self, execution_id: str) -> bool:
        """Stop monitoring an execution.
        
        Args:
            execution_id: The execution ID to stop monitoring
            
        Returns:
            bool: True if was monitoring and stopped, False if wasn't monitoring
        """
        async with self._lock:
            if execution_id not in self._monitored_executions:
                return False
            
            del self._monitored_executions[execution_id]
        
        logger.info(f"[U+1F6D1] Stopped heartbeat monitoring for execution {execution_id}")
        return True
    
    async def is_alive(self, execution_id: str) -> Optional[bool]:
        """Check if an execution is considered alive.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            bool: True if alive, False if dead, None if not monitoring
        """
        async with self._lock:
            if execution_id not in self._monitored_executions:
                return None
            return self._monitored_executions[execution_id].is_alive
    
    async def get_heartbeat_status(self, execution_id: str) -> Optional[HeartbeatStatus]:
        """Get detailed heartbeat status for an execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            HeartbeatStatus or None if not monitoring
        """
        async with self._lock:
            return self._monitored_executions.get(execution_id)
    
    async def get_all_monitored_executions(self) -> List[HeartbeatStatus]:
        """Get status of all monitored executions.
        
        Returns:
            List of HeartbeatStatus objects
        """
        async with self._lock:
            return list(self._monitored_executions.values())
    
    async def get_dead_executions(self) -> List[HeartbeatStatus]:
        """Get executions that are considered dead.
        
        Returns:
            List of HeartbeatStatus objects for dead executions
        """
        async with self._lock:
            return [status for status in self._monitored_executions.values() if not status.is_alive]
    
    def add_failure_callback(self, callback: Callable[[str, HeartbeatStatus], None]) -> None:
        """Add callback to be called when heartbeat failure is detected.
        
        Args:
            callback: Async function to call with (execution_id, status)
        """
        self._failure_callbacks.append(callback)
        logger.debug(f"Added heartbeat failure callback: {callback.__name__}")
    
    async def _start_monitor_task(self) -> None:
        """Start the background monitoring task."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(" SEARCH:  Started heartbeat monitoring loop")
    
    async def _monitor_loop(self) -> None:
        """Main monitoring loop that checks for missed heartbeats."""
        while self._is_running:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self._check_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}")
                # Continue monitoring even if there's an error
                await asyncio.sleep(1)
    
    async def _check_heartbeats(self) -> None:
        """Check all monitored executions for missed heartbeats."""
        now = datetime.now(UTC)
        dead_executions = []
        
        async with self._lock:
            for execution_id, status in list(self._monitored_executions.items()):
                if now > status.next_expected:
                    status.missed_heartbeats += 1
                    status.next_expected = now + timedelta(seconds=self.heartbeat_interval)
                    
                    if status.missed_heartbeats >= self.max_missed_heartbeats and status.is_alive:
                        # Agent is now considered dead
                        status.is_alive = False
                        dead_executions.append((execution_id, status))
                        self._heartbeat_failures += 1
                        
                        logger.critical(
                            f"[U+1F480] AGENT DEATH DETECTED: {execution_id} - "
                            f"{status.missed_heartbeats} missed heartbeats "
                            f"(last: {status.last_heartbeat.isoformat()})"
                        )
        
        # Trigger failure callbacks outside of lock
        for execution_id, status in dead_executions:
            await self._trigger_failure_callbacks(execution_id, status)
    
    async def _trigger_failure_callbacks(self, execution_id: str, status: HeartbeatStatus) -> None:
        """Trigger all failure callbacks for a dead execution."""
        self._recovery_triggers += 1
        
        logger.critical(
            f" ALERT:  TRIGGERING RECOVERY for dead agent: {execution_id} - "
            f"Recovery delay: {self.recovery_delay}s"
        )
        
        # Optional delay before recovery
        if self.recovery_delay > 0:
            await asyncio.sleep(self.recovery_delay)
        
        # Call all registered failure callbacks
        for callback in self._failure_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution_id, status)
                else:
                    callback(execution_id, status)
            except Exception as e:
                logger.error(f"Error in heartbeat failure callback {callback.__name__}: {e}")
    
    async def get_monitor_metrics(self) -> Dict[str, Any]:
        """Get monitoring metrics.
        
        Returns:
            Dictionary with monitoring statistics
        """
        async with self._lock:
            active_count = len(self._monitored_executions)
            alive_count = len([s for s in self._monitored_executions.values() if s.is_alive])
            dead_count = active_count - alive_count
        
        return {
            "is_running": self._is_running,
            "active_executions": active_count,
            "alive_executions": alive_count,
            "dead_executions": dead_count,
            "total_monitored": self._total_monitored,
            "heartbeat_failures": self._heartbeat_failures,
            "false_positives": self._false_positives,
            "recovery_triggers": self._recovery_triggers,
            "heartbeat_interval_seconds": self.heartbeat_interval,
            "timeout_seconds": self.timeout_seconds,
            "max_missed_heartbeats": self.max_missed_heartbeats
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with health information
        """
        metrics = await self.get_monitor_metrics()
        dead_executions = await self.get_dead_executions()
        
        # Determine health based on dead executions
        status = "healthy"
        if dead_executions:
            if len(dead_executions) > 3:
                status = "critical"
            elif len(dead_executions) > 1:
                status = "degraded"
            else:
                status = "warning"
        
        return {
            "status": status,
            "monitor_running": self._is_running,
            "dead_agents": [
                {
                    "execution_id": status.execution_id,
                    "missed_heartbeats": status.missed_heartbeats,
                    "last_heartbeat": status.last_heartbeat.isoformat(),
                    "time_since_last": (datetime.now(UTC) - status.last_heartbeat).total_seconds()
                }
                for status in dead_executions
            ],
            **metrics
        }
    
    async def force_check_execution(self, execution_id: str) -> bool:
        """Force an immediate check of a specific execution.
        
        This is useful for testing or when you suspect an execution has died.
        
        Args:
            execution_id: The execution ID to check immediately
            
        Returns:
            bool: True if execution is alive after check, False if dead
        """
        async with self._lock:
            if execution_id not in self._monitored_executions:
                return False
            
            status = self._monitored_executions[execution_id]
            now = datetime.now(UTC)
            
            # Check if heartbeat is overdue
            if now > status.next_expected:
                status.missed_heartbeats += 1
                status.next_expected = now + timedelta(seconds=self.heartbeat_interval)
                
                if status.missed_heartbeats >= self.max_missed_heartbeats:
                    status.is_alive = False
                    logger.warning(f" WARNING: [U+FE0F] Force check detected dead execution: {execution_id}")
            
            return status.is_alive
    
    async def revive_execution(self, execution_id: str) -> bool:
        """Manually revive a dead execution (for recovery scenarios).
        
        This should only be used during recovery when we know the agent
        has been restarted or fixed.
        
        Args:
            execution_id: The execution ID to revive
            
        Returns:
            bool: True if revived, False if not found
        """
        async with self._lock:
            if execution_id not in self._monitored_executions:
                return False
            
            status = self._monitored_executions[execution_id]
            now = datetime.now(UTC)
            
            # Reset heartbeat status
            status.is_alive = True
            status.missed_heartbeats = 0
            status.last_heartbeat = now
            status.next_expected = now + timedelta(seconds=self.heartbeat_interval)
            
        logger.info(f" CYCLE:  Manually revived execution: {execution_id}")
        return True
    
    async def shutdown(self) -> None:
        """Shutdown the heartbeat monitor and cleanup resources."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        async with self._lock:
            self._monitored_executions.clear()
        
        logger.info("[U+1F6D1] HeartbeatMonitor shutdown completed")
    
    def __len__(self) -> int:
        """Return number of monitored executions."""
        return len(self._monitored_executions)