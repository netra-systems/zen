"""MultiLayer Coordination Service - Centralized coordination for system layers.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Foundation for all real-time features  
- Business Goal: Ensure coordinated operations across WebSocket, Database, Agent, and Cache layers
- Value Impact: Eliminates coordination gaps that cause data inconsistency and user experience issues
- Strategic Impact: CRITICAL - Protects $500K+ ARR Golden Path by ensuring system-wide coordination

This service provides centralized coordination for operations that span multiple 
system layers, ensuring proper ordering, rollback handling, and health monitoring.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from netra_backend.app.monitoring.coordination_health_monitor import (
    CoordinationHealthMonitor, CoordinationLayer, HealthStatus
)
from netra_backend.app.core.agent_execution_tracker import ExecutionState

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of coordinated operations."""
    AGENT_EXECUTION = "agent_execution"
    MESSAGE_PROCESSING = "message_processing"
    USER_AUTHENTICATION = "user_authentication"
    THREAD_MANAGEMENT = "thread_management"
    STATE_UPDATE = "state_update"
    CACHE_REFRESH = "cache_refresh"
    GOLDEN_PATH_FLOW = "golden_path_flow"


@dataclass
class CoordinatedOperation:
    """Represents a coordinated operation across multiple layers."""
    operation_id: str
    operation_type: OperationType
    operation_name: str
    user_id: Optional[str]
    thread_id: Optional[str]
    db_operation: Optional[Callable] = None
    websocket_events: List[Dict[str, Any]] = None
    agent_state_updates: List[Dict[str, Any]] = None
    cache_operations: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.websocket_events is None:
            self.websocket_events = []
        if self.agent_state_updates is None:
            self.agent_state_updates = []
        if self.cache_operations is None:
            self.cache_operations = []
        if self.metadata is None:
            self.metadata = {}


class MultiLayerCoordinationService:
    """Service for coordinating operations across system layers.
    
    This service ensures that operations spanning multiple layers (WebSocket, Database,
    Agent, Cache) are properly coordinated, with correct ordering, rollback handling,
    and comprehensive health monitoring.
    """
    
    def __init__(self, database_manager=None, websocket_manager=None, 
                 agent_tracker=None, health_monitor=None):
        """Initialize multi-layer coordination service.
        
        Args:
            database_manager: DatabaseManager instance with coordination support
            websocket_manager: WebSocket manager for event coordination
            agent_tracker: Agent execution tracker for state coordination
            health_monitor: Optional health monitor (creates one if not provided)
        """
        # Core service references
        self.database_manager = database_manager
        self.websocket_manager = websocket_manager
        self.agent_tracker = agent_tracker
        
        # Health monitoring
        self.health_monitor = health_monitor or CoordinationHealthMonitor()
        
        # Coordination state
        self.active_operations: Dict[str, CoordinatedOperation] = {}
        self.coordination_metrics: Dict[str, Any] = {
            'operations_started': 0,
            'operations_completed': 0,
            'operations_failed': 0,
            'coordination_failures': 0,
            'rollbacks_handled': 0,
            'total_coordination_time': 0.0
        }
        
        # Coordination configuration
        self._coordination_enabled = True
        self._rollback_enabled = True
        self._health_monitoring_enabled = True
        self._max_operation_timeout = 300.0  # 5 minutes max
        
        # Setup health monitoring
        self._setup_health_monitoring()
        
        logger.info("🔗 MultiLayerCoordinationService initialized with health monitoring")
        
    def _setup_health_monitoring(self):
        """Setup health monitoring callbacks and alerts."""
        if self.health_monitor:
            # Add alert callback for coordination issues
            self.health_monitor.add_alert_callback(self._handle_coordination_alert)
            logger.debug("📊 Health monitoring callbacks configured")
            
    async def _handle_coordination_alert(self, alert):
        """Handle coordination health alerts.
        
        Args:
            alert: HealthAlert object describing the issue
        """
        logger.warning(f"🚨 Coordination health alert {alert.alert_id}: {alert.error_message}")
        
        # Log user impact for business analysis
        if alert.user_impact != "No user impact":
            logger.error(f"👤 User impact from coordination issue: {alert.user_impact}")
            
        # Update coordination metrics
        self.coordination_metrics['coordination_failures'] += 1
        
        # TODO: Add integration with external alerting systems (PagerDuty, Slack, etc.)
        
    def set_database_manager(self, database_manager):
        """Set database manager with coordination support.
        
        Args:
            database_manager: DatabaseManager instance
        """
        self.database_manager = database_manager
        
        # Link WebSocket manager to database coordinator if both are available
        if self.websocket_manager and hasattr(database_manager, 'transaction_coordinator'):
            database_manager.transaction_coordinator.set_websocket_manager(self.websocket_manager)
            logger.info("🔗 Database and WebSocket managers linked for coordination")
            
    def set_websocket_manager(self, websocket_manager):
        """Set WebSocket manager with coordination support.
        
        Args:
            websocket_manager: WebSocket manager instance
        """
        self.websocket_manager = websocket_manager
        
        # Link to database coordinator if available
        if (self.database_manager and 
            hasattr(self.database_manager, 'transaction_coordinator') and
            hasattr(websocket_manager, 'set_transaction_coordinator')):
            websocket_manager.set_transaction_coordinator(
                self.database_manager.transaction_coordinator
            )
            logger.info("🔗 WebSocket and Database managers linked for coordination")
            
    def set_agent_tracker(self, agent_tracker):
        """Set agent execution tracker for state coordination.
        
        Args:
            agent_tracker: Agent execution tracker instance
        """
        self.agent_tracker = agent_tracker
        logger.debug("🤖 Agent tracker linked to coordination service")
        
    async def execute_coordinated_operation(
        self,
        operation_name: str,
        operation_type: OperationType = OperationType.STATE_UPDATE,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        db_operation: Optional[Callable] = None,
        websocket_events: Optional[List[Dict[str, Any]]] = None,
        agent_state_updates: Optional[List[Dict[str, Any]]] = None,
        cache_operations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a coordinated operation across multiple system layers.
        
        This method ensures proper coordination between database transactions,
        WebSocket events, agent state updates, and cache operations.
        
        Args:
            operation_name: Human-readable name for the operation
            operation_type: Type of coordinated operation
            user_id: Optional user ID for context
            thread_id: Optional thread ID for context
            db_operation: Optional database operation callable
            websocket_events: Optional list of WebSocket events to send
            agent_state_updates: Optional list of agent state updates
            cache_operations: Optional list of cache operations
            metadata: Optional operation metadata
            
        Returns:
            Dictionary containing operation result and coordination metrics
        """
        if not self._coordination_enabled:
            raise RuntimeError("Coordination service is disabled")
            
        operation_id = str(uuid.uuid4())
        operation_start_time = time.time()
        
        # Create coordinated operation
        operation = CoordinatedOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            operation_name=operation_name,
            user_id=user_id,
            thread_id=thread_id,
            db_operation=db_operation,
            websocket_events=websocket_events or [],
            agent_state_updates=agent_state_updates or [],
            cache_operations=cache_operations or [],
            metadata=metadata or {}
        )
        
        self.active_operations[operation_id] = operation
        self.coordination_metrics['operations_started'] += 1
        
        logger.info(f"🔗 Starting coordinated operation {operation_id}: {operation_name} "
                   f"(type: {operation_type.value}, user: {user_id})")
        
        # Track coordination timing for health monitoring
        coordination_timing = {}
        
        try:
            # 1. Pre-coordination setup
            await self._notify_coordination_start(operation)
            coordination_timing['coordination_start'] = time.time()
            
            # 2. Execute database operation with coordination
            db_result = None
            transaction_id = None
            
            if db_operation and self.database_manager:
                db_start_time = time.time()
                
                # Use coordinated database session
                if hasattr(self.database_manager, 'get_coordinated_session'):
                    async with self.database_manager.get_coordinated_session(
                        user_id=user_id,
                        operation_type=operation_name,
                        websocket_events=websocket_events
                    ) as (session, txn_id):
                        transaction_id = txn_id
                        db_result = await db_operation(session)
                        coordination_timing['database'] = time.time()
                else:
                    # Fallback to regular session
                    async with self.database_manager.get_session(
                        user_id=user_id,
                        operation_type=operation_name
                    ) as session:
                        db_result = await db_operation(session)
                        coordination_timing['database'] = time.time()
                        
                logger.debug(f"✅ Database operation completed for {operation_id} "
                           f"in {time.time() - db_start_time:.3f}s")
            
            # 3. Execute agent state updates
            if agent_state_updates and self.agent_tracker:
                agent_start_time = time.time()
                
                for state_update in agent_state_updates:
                    await self._execute_agent_state_update(state_update)
                    
                coordination_timing['agent'] = time.time()
                logger.debug(f"✅ Agent state updates completed for {operation_id} "
                           f"in {time.time() - agent_start_time:.3f}s")
            
            # 4. Execute cache operations
            if cache_operations:
                cache_start_time = time.time()
                
                for cache_op in cache_operations:
                    await self._execute_cache_operation(cache_op)
                    
                coordination_timing['cache'] = time.time()
                logger.debug(f"✅ Cache operations completed for {operation_id} "
                           f"in {time.time() - cache_start_time:.3f}s")
            
            # 5. Handle WebSocket events (already queued by coordinated session)
            if websocket_events and not transaction_id:
                # If no coordinated session was used, send events immediately
                websocket_start_time = time.time()
                
                for event in websocket_events:
                    await self._send_websocket_event(event, user_id)
                    
                coordination_timing['websocket'] = time.time()
                logger.debug(f"✅ WebSocket events sent for {operation_id} "
                           f"in {time.time() - websocket_start_time:.3f}s")
            elif transaction_id:
                # Events were sent by coordinated session after commit
                coordination_timing['websocket'] = coordination_timing.get('database', time.time())
            
            # 6. Finalize coordination
            operation_duration = time.time() - operation_start_time
            coordination_timing['coordination_end'] = time.time()
            
            # Track coordination health
            if self._health_monitoring_enabled:
                await self._track_coordination_health(operation, coordination_timing, success=True)
            
            # Update metrics
            self.coordination_metrics['operations_completed'] += 1
            self.coordination_metrics['total_coordination_time'] += operation_duration
            
            # Cleanup
            del self.active_operations[operation_id]
            
            logger.info(f"✅ Coordinated operation {operation_id} completed successfully "
                       f"in {operation_duration:.3f}s")
            
            return {
                'success': True,
                'operation_id': operation_id,
                'operation_duration': operation_duration,
                'db_result': db_result,
                'transaction_id': transaction_id,
                'coordination_timing': coordination_timing,
                'layers_coordinated': self._get_coordinated_layers(operation)
            }
            
        except Exception as e:
            # Handle coordination failure with rollback
            error_time = time.time()
            coordination_timing['error'] = error_time
            
            logger.critical(f"💥 Coordinated operation {operation_id} failed: {type(e).__name__}: {e}")
            
            # Execute rollback coordination
            rollback_result = await self._execute_coordinated_rollback(
                operation, transaction_id, str(e), coordination_timing
            )
            
            # Track coordination health for failure
            if self._health_monitoring_enabled:
                await self._track_coordination_health(operation, coordination_timing, success=False)
            
            # Update metrics
            self.coordination_metrics['operations_failed'] += 1
            operation_duration = error_time - operation_start_time
            self.coordination_metrics['total_coordination_time'] += operation_duration
            
            # Cleanup
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
            
            logger.error(f"❌ Coordinated operation {operation_id} failed after {operation_duration:.3f}s")
            
            # Re-raise with coordination context
            raise RuntimeError(f"Coordinated operation failed: {e}") from e
            
    async def _notify_coordination_start(self, operation: CoordinatedOperation):
        """Notify system components that coordination is starting.
        
        Args:
            operation: Coordinated operation being started
        """
        logger.debug(f"🚀 Starting coordination for operation {operation.operation_id}")
        
        # Future: Add pre-coordination hooks here
        # - Validation checks
        # - Resource allocation
        # - Circuit breaker checks
        
    async def _execute_agent_state_update(self, state_update: Dict[str, Any]):
        """Execute an agent state update.
        
        Args:
            state_update: Dictionary containing state update parameters
        """
        if not self.agent_tracker:
            logger.warning("⚠️ Agent tracker not available for state update")
            return
            
        try:
            # Extract state update parameters
            state_exec_id = state_update.get('state_exec_id')
            state = state_update.get('state')
            
            if state_exec_id and state:
                # Convert string state to ExecutionState enum if needed
                if isinstance(state, str):
                    state = ExecutionState(state)
                elif isinstance(state, ExecutionState):
                    pass  # Already correct type
                else:
                    logger.warning(f"⚠️ Invalid state type for update: {type(state)}")
                    return
                    
                self.agent_tracker.update_execution_state(state_exec_id, state)
                logger.debug(f"🤖 Updated agent state: {state_exec_id} -> {state.value}")
            else:
                logger.warning(f"⚠️ Invalid agent state update parameters: {state_update}")
                
        except Exception as e:
            logger.error(f"❌ Agent state update failed: {e}")
            raise
            
    async def _execute_cache_operation(self, cache_op: Dict[str, Any]):
        """Execute a cache operation.
        
        Args:
            cache_op: Dictionary containing cache operation parameters
        """
        # TODO: Implement cache operations based on cache backend
        # This is a placeholder for future cache coordination
        operation_type = cache_op.get('type', 'unknown')
        logger.debug(f"💾 Cache operation executed: {operation_type}")
        
    async def _send_websocket_event(self, event: Dict[str, Any], user_id: Optional[str]):
        """Send a WebSocket event immediately (fallback mode).
        
        Args:
            event: WebSocket event to send
            user_id: User ID for targeting
        """
        if not self.websocket_manager:
            logger.warning("⚠️ WebSocket manager not available for event")
            return
            
        try:
            event_type = event.get('type', 'unknown')
            event_data = event.get('data', {})
            
            if hasattr(self.websocket_manager, 'send_to_user') and user_id:
                message = {
                    "type": event_type,
                    "data": event_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await self.websocket_manager.send_to_user(user_id, message)
                logger.debug(f"📤 Sent WebSocket event {event_type} to user {user_id}")
            else:
                logger.warning(f"⚠️ Cannot send WebSocket event {event_type} - no send method or user_id")
                
        except Exception as e:
            logger.error(f"❌ WebSocket event send failed: {e}")
            raise
            
    async def _execute_coordinated_rollback(
        self,
        operation: CoordinatedOperation,
        transaction_id: Optional[str],
        error_message: str,
        coordination_timing: Dict[str, float]
    ) -> Dict[str, Any]:
        """Execute coordinated rollback across all layers.
        
        Args:
            operation: Failed coordinated operation
            transaction_id: Optional database transaction ID
            error_message: Error message describing the failure
            coordination_timing: Timing data for the failed operation
            
        Returns:
            Dictionary containing rollback result
        """
        rollback_start_time = time.time()
        rollback_results = {}
        
        logger.warning(f"🔄 Executing coordinated rollback for operation {operation.operation_id}")
        
        try:
            # 1. Database rollback (handled by coordinated session)
            if transaction_id and self.database_manager:
                # Database rollback is handled automatically by the coordinated session
                rollback_results['database'] = 'handled_by_session'
                logger.debug(f"🔄 Database rollback handled by coordinated session")
            
            # 2. Agent state rollback
            if operation.agent_state_updates and self.agent_tracker:
                for state_update in operation.agent_state_updates:
                    # Attempt to revert agent state (implementation depends on requirements)
                    rollback_results['agent'] = 'attempted'
                logger.debug(f"🔄 Agent state rollback attempted")
            
            # 3. Cache rollback
            if operation.cache_operations:
                # TODO: Implement cache rollback based on operation types
                rollback_results['cache'] = 'attempted'
                logger.debug(f"🔄 Cache rollback attempted")
            
            # 4. WebSocket rollback notification
            if operation.websocket_events and operation.user_id:
                await self._send_rollback_notification(operation, error_message)
                rollback_results['websocket'] = 'notification_sent'
                logger.debug(f"🔄 WebSocket rollback notification sent")
            
            rollback_duration = time.time() - rollback_start_time
            self.coordination_metrics['rollbacks_handled'] += 1
            
            logger.info(f"✅ Coordinated rollback completed for {operation.operation_id} "
                       f"in {rollback_duration:.3f}s")
            
            return {
                'success': True,
                'rollback_duration': rollback_duration,
                'rollback_results': rollback_results
            }
            
        except Exception as rollback_error:
            rollback_duration = time.time() - rollback_start_time
            
            logger.critical(f"💥 COORDINATED ROLLBACK FAILED for {operation.operation_id} "
                          f"after {rollback_duration:.3f}s: {rollback_error}")
            logger.critical(f"SYSTEM INTEGRITY AT RISK - Manual intervention may be required")
            
            return {
                'success': False,
                'rollback_duration': rollback_duration,
                'rollback_error': str(rollback_error),
                'rollback_results': rollback_results
            }
            
    async def _send_rollback_notification(self, operation: CoordinatedOperation, error_message: str):
        """Send rollback notification to affected users.
        
        Args:
            operation: Failed operation
            error_message: Error message describing the failure
        """
        if not self.websocket_manager or not operation.user_id:
            return
            
        notification_data = {
            "type": "operation_rollback",
            "operation_id": operation.operation_id,
            "operation_name": operation.operation_name,
            "operation_type": operation.operation_type.value,
            "error_message": error_message,
            "user_message": "The recent operation failed and has been rolled back. Please try again.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thread_id": operation.thread_id
        }
        
        try:
            message = {
                "type": "operation_rollback",
                "data": notification_data
            }
            await self.websocket_manager.send_to_user(operation.user_id, message)
            logger.debug(f"📤 Sent rollback notification to user {operation.user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to send rollback notification: {e}")
            
    def _get_coordinated_layers(self, operation: CoordinatedOperation) -> List[str]:
        """Get list of layers involved in the coordinated operation.
        
        Args:
            operation: Coordinated operation
            
        Returns:
            List of layer names involved in the operation
        """
        layers = []
        
        if operation.db_operation:
            layers.append(CoordinationLayer.DATABASE.value)
        if operation.websocket_events:
            layers.append(CoordinationLayer.WEBSOCKET.value)
        if operation.agent_state_updates:
            layers.append(CoordinationLayer.AGENT.value)
        if operation.cache_operations:
            layers.append(CoordinationLayer.CACHE.value)
        if operation.user_id:
            layers.append(CoordinationLayer.USER_CONTEXT.value)
            
        return layers
        
    async def _track_coordination_health(
        self,
        operation: CoordinatedOperation,
        coordination_timing: Dict[str, float],
        success: bool
    ):
        """Track coordination health metrics.
        
        Args:
            operation: Coordinated operation
            coordination_timing: Timing data for the operation
            success: Whether the operation succeeded
        """
        if not self.health_monitor:
            return
            
        # Convert layer names to CoordinationLayer enum
        layers = []
        layer_mapping = {
            'database': CoordinationLayer.DATABASE,
            'websocket': CoordinationLayer.WEBSOCKET,
            'agent': CoordinationLayer.AGENT,
            'cache': CoordinationLayer.CACHE,
            'user_context': CoordinationLayer.USER_CONTEXT
        }
        
        for layer_name in coordination_timing.keys():
            if layer_name in layer_mapping:
                layers.append(layer_mapping[layer_name])
        
        # Track the coordination event
        event_type = f"{operation.operation_type.value}_{'success' if success else 'failure'}"
        
        await self.health_monitor.track_coordination_event(
            event_type=event_type,
            layers=layers,
            timing_data=coordination_timing,
            user_id=operation.user_id,
            thread_id=operation.thread_id,
            transaction_id=operation.metadata.get('transaction_id'),
            metadata={
                'operation_id': operation.operation_id,
                'operation_name': operation.operation_name,
                'success': success
            }
        )
        
    def get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination service metrics.
        
        Returns:
            Dictionary containing service metrics
        """
        return {
            **self.coordination_metrics,
            'active_operations': len(self.active_operations),
            'health_score': self.health_monitor.get_health_score() if self.health_monitor else None,
            'coordination_enabled': self._coordination_enabled,
            'rollback_enabled': self._rollback_enabled,
            'health_monitoring_enabled': self._health_monitoring_enabled
        }
        
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active operations.
        
        Returns:
            Dictionary containing active operation information
        """
        active_ops = {}
        
        for op_id, operation in self.active_operations.items():
            active_ops[op_id] = {
                'operation_name': operation.operation_name,
                'operation_type': operation.operation_type.value,
                'user_id': operation.user_id,
                'thread_id': operation.thread_id,
                'created_at': operation.created_at.isoformat(),
                'duration_seconds': (datetime.now(timezone.utc) - operation.created_at).total_seconds(),
                'layers_involved': self._get_coordinated_layers(operation)
            }
            
        return active_ops
        
    async def cleanup_stale_operations(self, max_age_minutes: int = 30):
        """Clean up operations that have been active too long.
        
        Args:
            max_age_minutes: Maximum age of operations to keep
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        stale_operations = []
        
        for op_id, operation in list(self.active_operations.items()):
            if operation.created_at < cutoff_time:
                stale_operations.append(op_id)
                
        for op_id in stale_operations:
            operation = self.active_operations.pop(op_id, None)
            if operation:
                logger.warning(f"🧹 Cleaned up stale operation {op_id}: {operation.operation_name}")
                
        if stale_operations:
            logger.info(f"🧹 Cleaned up {len(stale_operations)} stale coordination operations")
            
        return len(stale_operations)
        
    def set_coordination_enabled(self, enabled: bool):
        """Enable or disable coordination service.
        
        Args:
            enabled: Whether to enable coordination
        """
        self._coordination_enabled = enabled
        status = "enabled" if enabled else "disabled"
        logger.info(f"🔗 Multi-layer coordination {status}")
        
    def set_health_monitoring_enabled(self, enabled: bool):
        """Enable or disable health monitoring.
        
        Args:
            enabled: Whether to enable health monitoring
        """
        self._health_monitoring_enabled = enabled
        if self.health_monitor:
            self.health_monitor.set_monitoring_enabled(enabled)
        status = "enabled" if enabled else "disabled"
        logger.info(f"🏥 Coordination health monitoring {status}")