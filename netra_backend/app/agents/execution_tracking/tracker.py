"""ExecutionTracker - Orchestrates execution tracking, monitoring, and recovery.

This module provides the main orchestration layer that coordinates between
registry, heartbeat monitoring, timeout management, and recovery mechanisms
to provide comprehensive agent death detection and recovery.

Business Value: Single interface that eliminates silent agent failures,
provides real-time execution visibility, and enables automatic recovery.
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from netra_backend.app.agents.execution_tracking.heartbeat import HeartbeatMonitor, HeartbeatStatus
from netra_backend.app.agents.execution_tracking.registry import ExecutionRecord, ExecutionRegistry, ExecutionState
from netra_backend.app.agents.execution_tracking.timeout import TimeoutInfo, TimeoutManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ExecutionProgress(BaseModel):
    """Progress update for execution tracking."""
    stage: str
    percentage: float
    message: str
    details: Dict[str, Any] = {}


class ExecutionStatus(BaseModel):
    """Comprehensive execution status combining all tracking data."""
    execution_record: ExecutionRecord
    heartbeat_status: Optional[HeartbeatStatus] = None
    timeout_info: Optional[TimeoutInfo] = None
    websocket_status: Dict[str, Any] = {}
    health_check: Dict[str, Any] = {}
    
    class Config:
        arbitrary_types_allowed = True


class AgentExecutionContext(BaseModel):
    """Context for agent execution tracking."""
    run_id: str
    agent_name: str
    thread_id: str
    user_id: str
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = {}


class AgentExecutionResult(BaseModel):
    """Result of agent execution with tracking metadata."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_id: str
    duration_seconds: float
    recovery_actions: List[str] = []


class ExecutionTracker:
    """Orchestrates execution tracking, monitoring, and recovery.
    
    This class provides the unified interface for all execution tracking
    functionality, coordinating between registry, heartbeat monitoring,
    timeout management, and WebSocket notifications.
    
    Key Features:
    - Unified tracking interface for agent execution
    - Automatic heartbeat monitoring and death detection
    - Configurable timeout management
    - WebSocket integration for real-time notifications
    - Comprehensive recovery mechanisms
    - Detailed metrics and health reporting
    """
    
    def __init__(
        self,
        websocket_bridge: Optional['AgentWebSocketBridge'] = None,
        heartbeat_interval: float = 5.0,
        timeout_check_interval: float = 5.0
    ):
        """Initialize ExecutionTracker with all components.
        
        Args:
            websocket_bridge: AgentWebSocketBridge for real-time notifications
            heartbeat_interval: Heartbeat check interval in seconds
            timeout_check_interval: Timeout check interval in seconds
        """
        self.websocket_bridge = websocket_bridge
        
        # Initialize core components
        self.registry = ExecutionRegistry()
        self.heartbeat_monitor = HeartbeatMonitor(heartbeat_interval_seconds=heartbeat_interval)
        self.timeout_manager = TimeoutManager(check_interval_seconds=timeout_check_interval)
        
        # Setup callbacks
        self._setup_callbacks()
        
        # Metrics
        self._total_executions_started = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._recovered_executions = 0
        
        logger.info(" PASS:  ExecutionTracker initialized with comprehensive monitoring")
    
    def _setup_callbacks(self) -> None:
        """Setup callbacks between components."""
        # HeartbeatMonitor callbacks
        self.heartbeat_monitor.add_failure_callback(self._handle_heartbeat_failure)
        
        # TimeoutManager callbacks  
        self.timeout_manager.add_timeout_callback(self._handle_timeout)
    
    async def start_execution(
        self, 
        run_id: str, 
        agent_name: str, 
        context: AgentExecutionContext
    ) -> str:
        """Start tracking a new agent execution.
        
        Args:
            run_id: Original run ID from agent execution
            agent_name: Name of the executing agent
            context: Execution context with metadata
            
        Returns:
            str: Unique execution ID for tracking
        """
        # Register execution in registry
        record = await self.registry.register_execution(
            run_id=run_id,
            agent_name=agent_name,
            context=context.dict() if hasattr(context, 'dict') else context
        )
        
        execution_id = record.execution_id
        
        # Set timeout based on agent type
        timeout_seconds = self.timeout_manager.get_timeout_for_agent(agent_name)
        await self.timeout_manager.set_timeout(execution_id, timeout_seconds, agent_name)
        
        # Start heartbeat monitoring
        await self.heartbeat_monitor.start_monitoring(execution_id)
        
        # Update state to initializing
        await self.registry.update_execution_state(execution_id, ExecutionState.INITIALIZING)
        
        # Send WebSocket notification
        await self._send_execution_started_notification(execution_id, record, context)
        
        self._total_executions_started += 1
        logger.info(f"[U+1F680] Started execution tracking for {agent_name} (execution_id: {execution_id})")
        
        return execution_id
    
    async def update_execution_progress(
        self, 
        execution_id: str, 
        progress: ExecutionProgress
    ) -> None:
        """Update execution progress.
        
        Args:
            execution_id: The execution ID to update
            progress: Progress information
        """
        # Send heartbeat (this shows the agent is alive)
        await self.heartbeat_monitor.send_heartbeat(execution_id, {"progress": progress.dict()})
        
        # Update registry with progress
        await self.registry.update_execution_state(
            execution_id, 
            ExecutionState.RUNNING,
            {"progress": progress.dict()}
        )
        
        # Send WebSocket progress update
        await self._send_progress_update(execution_id, progress)
    
    async def complete_execution(
        self, 
        execution_id: str, 
        result: AgentExecutionResult
    ) -> None:
        """Complete an execution successfully.
        
        Args:
            execution_id: The execution ID to complete
            result: Execution result data
        """
        # Update registry state
        final_state = ExecutionState.SUCCESS if result.success else ExecutionState.FAILED
        await self.registry.update_execution_state(
            execution_id, 
            final_state,
            {"result": result.dict() if hasattr(result, 'dict') else result}
        )
        
        # Stop monitoring
        await self.heartbeat_monitor.stop_monitoring(execution_id)
        await self.timeout_manager.clear_timeout(execution_id)
        
        # Update metrics
        if result.success:
            self._successful_executions += 1
        else:
            self._failed_executions += 1
        
        # Send WebSocket completion notification
        await self._send_execution_completed_notification(execution_id, result)
        
        logger.info(f" PASS:  Completed execution tracking for {execution_id} (success: {result.success})")
    
    async def handle_execution_failure(
        self, 
        execution_id: str, 
        error: Exception
    ) -> None:
        """Handle execution failure with recovery options.
        
        Args:
            execution_id: The execution ID that failed
            error: The error that occurred
        """
        # Update registry state
        await self.registry.update_execution_state(
            execution_id,
            ExecutionState.FAILED,
            {"error": str(error)}
        )
        
        # Stop monitoring
        await self.heartbeat_monitor.stop_monitoring(execution_id)
        await self.timeout_manager.clear_timeout(execution_id)
        
        # Get execution record for recovery decision
        record = await self.registry.get_execution(execution_id)
        if not record:
            logger.error(f"Failed to get execution record for {execution_id}")
            return
        
        # Send WebSocket failure notification
        await self._send_execution_failed_notification(execution_id, error, record)
        
        # Consider recovery options
        await self._consider_recovery(execution_id, record, error)
        
        self._failed_executions += 1
        logger.error(f" FAIL:  Execution failed: {execution_id} - {error}")
    
    async def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatus]:
        """Get comprehensive status of an execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            ExecutionStatus or None if not found
        """
        record = await self.registry.get_execution(execution_id)
        if not record:
            return None
        
        heartbeat_status = await self.heartbeat_monitor.get_heartbeat_status(execution_id)
        timeout_info = await self.timeout_manager.get_timeout_info(execution_id)
        
        return ExecutionStatus(
            execution_record=record,
            heartbeat_status=heartbeat_status,
            timeout_info=timeout_info,
            websocket_status={"bridge_available": self.websocket_bridge is not None},
            health_check=await self._get_execution_health(execution_id)
        )
    
    async def get_all_active_executions(self) -> List[ExecutionStatus]:
        """Get status of all active executions.
        
        Returns:
            List of ExecutionStatus objects for active executions
        """
        active_records = await self.registry.get_active_executions()
        statuses = []
        
        for record in active_records:
            status = await self.get_execution_status(record.execution_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    async def _handle_heartbeat_failure(self, execution_id: str, heartbeat_status: HeartbeatStatus) -> None:
        """Handle heartbeat failure (agent death detection).
        
        Args:
            execution_id: The execution ID with heartbeat failure
            heartbeat_status: Current heartbeat status
        """
        logger.critical(f"[U+1F480] HEARTBEAT FAILURE DETECTED: {execution_id}")
        
        # Get execution record
        record = await self.registry.get_execution(execution_id)
        if not record:
            logger.error(f"Cannot find execution record for failed heartbeat: {execution_id}")
            return
        
        # Update state to failed
        await self.registry.update_execution_state(
            execution_id,
            ExecutionState.FAILED,
            {
                "error": "Agent death detected - heartbeat failure",
                "heartbeat_failure": heartbeat_status.dict()
            }
        )
        
        # Clean up timeout
        await self.timeout_manager.clear_timeout(execution_id)
        
        # Send WebSocket death notification
        await self._send_agent_death_notification(execution_id, record, "heartbeat_failure")
        
        # Consider recovery
        await self._consider_recovery(execution_id, record, Exception("Agent death detected"))
        
        self._failed_executions += 1
        logger.critical(f"[U+1F480] Agent death handled for: {execution_id}")
    
    async def _handle_timeout(self, execution_id: str, timeout_info: TimeoutInfo) -> None:
        """Handle execution timeout.
        
        Args:
            execution_id: The execution ID that timed out
            timeout_info: Timeout information
        """
        logger.error(f"[U+23F0] TIMEOUT DETECTED: {execution_id} (after {timeout_info.timeout_seconds}s)")
        
        # Get execution record
        record = await self.registry.get_execution(execution_id)
        if not record:
            logger.error(f"Cannot find execution record for timeout: {execution_id}")
            return
        
        # Update state to timeout
        await self.registry.update_execution_state(
            execution_id,
            ExecutionState.TIMEOUT,
            {
                "error": f"Execution timed out after {timeout_info.timeout_seconds}s",
                "timeout_info": timeout_info.dict()
            }
        )
        
        # Stop heartbeat monitoring
        await self.heartbeat_monitor.stop_monitoring(execution_id)
        
        # Send WebSocket timeout notification
        await self._send_agent_death_notification(execution_id, record, "timeout")
        
        # Consider recovery
        await self._consider_recovery(execution_id, record, Exception(f"Timeout after {timeout_info.timeout_seconds}s"))
        
        self._failed_executions += 1
        logger.error(f"[U+23F0] Timeout handled for: {execution_id}")
    
    async def _consider_recovery(
        self, 
        execution_id: str, 
        record: ExecutionRecord, 
        error: Exception
    ) -> None:
        """Consider recovery options for a failed execution.
        
        Args:
            execution_id: The failed execution ID
            record: Execution record
            error: The error that caused the failure
        """
        # For now, just log the failure
        # In a full implementation, this would include:
        # - Retry logic based on error type
        # - Fallback agent selection
        # - Circuit breaker pattern
        # - Dead letter queue
        
        logger.info(f" CYCLE:  Considering recovery for {execution_id} (agent: {record.agent_name})")
        
        # Could implement recovery strategies here based on:
        # - Error type (timeout vs heartbeat failure vs exception)
        # - Agent type (some agents are more critical)
        # - Retry count (don't retry forever)
        # - System load (don't retry if system is overloaded)
    
    async def _send_execution_started_notification(
        self,
        execution_id: str,
        record: ExecutionRecord,
        context: AgentExecutionContext
    ) -> None:
        """Send execution started notification via WebSocket."""
        if not self.websocket_bridge:
            return
        
        try:
            await self.websocket_bridge.notify_execution_started(
                run_id=context.run_id,
                agent_name=record.agent_name,
                execution_id=execution_id,
                estimated_duration_ms=self.timeout_manager.get_timeout_for_agent(record.agent_name) * 1000
            )
        except Exception as e:
            logger.warning(f"Failed to send execution started notification: {e}")
    
    async def _send_progress_update(
        self,
        execution_id: str,
        progress: ExecutionProgress
    ) -> None:
        """Send progress update via WebSocket."""
        if not self.websocket_bridge:
            return
        
        try:
            record = await self.registry.get_execution(execution_id)
            if record:
                await self.websocket_bridge.notify_execution_progress(
                    run_id=record.run_id,
                    agent_name=record.agent_name,
                    progress_data={
                        "stage": progress.stage,
                        "percentage": progress.percentage,
                        "message": progress.message,
                        **progress.details
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to send progress update: {e}")
    
    async def _send_execution_completed_notification(
        self,
        execution_id: str,
        result: AgentExecutionResult
    ) -> None:
        """Send execution completed notification via WebSocket."""
        if not self.websocket_bridge:
            return
        
        try:
            record = await self.registry.get_execution(execution_id)
            if record:
                await self.websocket_bridge.notify_execution_completed(
                    run_id=record.run_id,
                    agent_name=record.agent_name,
                    execution_result={
                        "success": result.success,
                        "duration_seconds": result.duration_seconds,
                        "recovery_actions": result.recovery_actions
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to send execution completed notification: {e}")
    
    async def _send_execution_failed_notification(
        self,
        execution_id: str,
        error: Exception,
        record: ExecutionRecord
    ) -> None:
        """Send execution failed notification via WebSocket."""
        if not self.websocket_bridge:
            return
        
        try:
            await self.websocket_bridge.notify_execution_failed(
                run_id=record.run_id,
                agent_name=record.agent_name,
                error_details={
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "execution_id": execution_id
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send execution failed notification: {e}")
    
    async def _send_agent_death_notification(
        self,
        execution_id: str,
        record: ExecutionRecord,
        death_type: str
    ) -> None:
        """Send agent death notification via WebSocket."""
        if not self.websocket_bridge:
            return
        
        try:
            await self.websocket_bridge.notify_agent_death(
                run_id=record.run_id,
                agent_name=record.agent_name,
                death_type=death_type,
                details={
                    "execution_id": execution_id,
                    "death_detected_at": record.updated_at.isoformat()
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send agent death notification: {e}")
    
    async def _get_execution_health(self, execution_id: str) -> Dict[str, Any]:
        """Get health information for an execution."""
        record = await self.registry.get_execution(execution_id)
        if not record:
            return {"status": "not_found"}
        
        heartbeat_status = await self.heartbeat_monitor.get_heartbeat_status(execution_id)
        timeout_info = await self.timeout_manager.get_timeout_info(execution_id)
        
        health = {
            "status": "healthy",
            "execution_state": record.state.value,
            "is_active": record.state not in [ExecutionState.SUCCESS, ExecutionState.FAILED, ExecutionState.ABORTED]
        }
        
        if heartbeat_status:
            health["heartbeat_alive"] = heartbeat_status.is_alive
            health["missed_heartbeats"] = heartbeat_status.missed_heartbeats
        
        if timeout_info:
            health["has_timeout"] = True
            health["remaining_seconds"] = timeout_info.remaining_seconds
            health["has_timed_out"] = timeout_info.has_timed_out
        
        # Determine overall health
        if record.state in [ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.ABORTED]:
            health["status"] = "failed"
        elif heartbeat_status and not heartbeat_status.is_alive:
            health["status"] = "dead"
        elif timeout_info and timeout_info.has_timed_out:
            health["status"] = "timed_out"
        
        return health
    
    async def get_tracker_metrics(self) -> Dict[str, Any]:
        """Get comprehensive tracker metrics.
        
        Returns:
            Dictionary with all tracking metrics
        """
        registry_metrics = await self.registry.get_execution_metrics()
        heartbeat_metrics = await self.heartbeat_monitor.get_monitor_metrics()
        timeout_metrics = await self.timeout_manager.get_timeout_metrics()
        
        return {
            "tracker_metrics": {
                "total_executions_started": self._total_executions_started,
                "successful_executions": self._successful_executions,
                "failed_executions": self._failed_executions,
                "recovered_executions": self._recovered_executions,
                "success_rate": (
                    self._successful_executions / max(1, self._total_executions_started)
                ),
                "websocket_bridge_available": self.websocket_bridge is not None
            },
            "registry_metrics": registry_metrics.dict(),
            "heartbeat_metrics": heartbeat_metrics,
            "timeout_metrics": timeout_metrics
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with overall health information
        """
        registry_health = await self.registry.get_health_status()
        heartbeat_health = await self.heartbeat_monitor.get_health_status()
        timeout_health = await self.timeout_manager.get_health_status()
        
        # Determine overall health
        overall_status = "healthy"
        issues = []
        
        if registry_health["status"] != "healthy":
            overall_status = "degraded"
            issues.append(f"Registry: {registry_health['status']}")
        
        if heartbeat_health["status"] != "healthy":
            if heartbeat_health["status"] == "critical":
                overall_status = "critical"
            elif overall_status != "critical":
                overall_status = "degraded"
            issues.append(f"Heartbeat: {heartbeat_health['status']}")
        
        if timeout_health["status"] != "healthy":
            if timeout_health["status"] == "critical":
                overall_status = "critical"
            elif overall_status != "critical":
                overall_status = "degraded"
            issues.append(f"Timeout: {timeout_health['status']}")
        
        return {
            "status": overall_status,
            "issues": issues,
            "components": {
                "registry": registry_health,
                "heartbeat_monitor": heartbeat_health,
                "timeout_manager": timeout_health
            },
            "active_executions": registry_health.get("active_executions", 0),
            "dead_agents": len(heartbeat_health.get("dead_agents", [])),
            "timed_out_agents": timeout_health.get("timed_out_executions", 0)
        }
    
    async def shutdown(self) -> None:
        """Shutdown the execution tracker and all components."""
        logger.info("[U+1F6D1] Shutting down ExecutionTracker...")
        
        # Shutdown all components
        await self.heartbeat_monitor.shutdown()
        await self.timeout_manager.shutdown()
        await self.registry.shutdown()
        
        logger.info("[U+1F6D1] ExecutionTracker shutdown completed")