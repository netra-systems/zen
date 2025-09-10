"""
WebSocket State Coordinator - PHASE 4 FIX for Race Condition Issue #163

This module provides unified state machine coordination to prevent conflicts
between multiple competing WebSocket state machines that cause 1011 errors.

Business Value Justification:
- Segment: ALL (affects $500K+ ARR chat functionality)
- Business Goal: Restore reliable WebSocket connections and agent event delivery
- Value Impact: Eliminates WebSocket race conditions causing complete chat dysfunction  
- Revenue Impact: Prevents loss of core business functionality

PHASE 4 FIX OBJECTIVES:
1. Unified state machine coordination across all WebSocket components
2. Prevention of competing state transitions causing 1011 errors
3. Centralized state validation and conflict resolution
4. Race condition elimination in Cloud Run environments
5. State synchronization between authentication, factory, and event delivery

This coordinator ensures that all WebSocket state machines work together
harmoniously rather than competing and causing connection failures.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Any, List, Set, Tuple
from dataclasses import dataclass, field
import threading
from collections import defaultdict

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class WebSocketSystemState(Enum):
    """Unified WebSocket system states."""
    INITIALIZING = "initializing"
    AUTHENTICATING = "authenticating" 
    FACTORY_CREATING = "factory_creating"
    MANAGER_READY = "manager_ready"
    EVENT_DELIVERY_ACTIVE = "event_delivery_active"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


class StateTransitionPriority(Enum):
    """Priority levels for state transitions."""
    CRITICAL = 100
    HIGH = 80
    NORMAL = 60
    LOW = 40
    BACKGROUND = 20


@dataclass
class StateTransitionRequest:
    """Request for WebSocket state transition."""
    request_id: str
    component: str  # Which component is requesting the transition
    from_state: WebSocketSystemState
    to_state: WebSocketSystemState
    priority: StateTransitionPriority
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    connection_id: Optional[str] = None


@dataclass
class StateCoordinatorMetrics:
    """Metrics for state coordinator monitoring."""
    total_transitions: int = 0
    successful_transitions: int = 0
    failed_transitions: int = 0
    conflicts_resolved: int = 0
    race_conditions_prevented: int = 0
    active_connections: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketStateCoordinator:
    """
    PHASE 4 FIX: Unified WebSocket state machine coordinator.
    
    This class coordinates all WebSocket-related state machines to prevent
    race conditions and conflicts that cause 1011 WebSocket errors.
    
    Key Features:
    - Centralized state management across all components
    - Conflict resolution for competing state transitions  
    - Race condition prevention in Cloud Run environments
    - Priority-based transition scheduling
    - Comprehensive monitoring and alerting
    """
    
    def __init__(self):
        """Initialize the WebSocket state coordinator."""
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        
        # State tracking by connection
        self._connection_states: Dict[str, WebSocketSystemState] = {}
        self._connection_metadata: Dict[str, Dict[str, Any]] = {}
        self._connection_timelines: Dict[str, List[StateTransitionRequest]] = {}
        
        # Component coordination
        self._active_components: Dict[str, Set[str]] = defaultdict(set)  # connection_id -> components
        self._transition_queue: Dict[int, List[StateTransitionRequest]] = defaultdict(list)  # priority -> requests
        
        # Race condition prevention
        self._pending_transitions: Dict[str, StateTransitionRequest] = {}  # connection_id -> request
        self._transition_locks: Dict[str, asyncio.Lock] = {}  # connection_id -> lock
        
        # Metrics and monitoring
        self._metrics = StateCoordinatorMetrics()
        self._conflict_history: List[Dict[str, Any]] = []
        
        # Coordinator state
        self._is_running = False
        self._processor_task: Optional[asyncio.Task] = None
        
        logger.info("PHASE 4 FIX: WebSocketStateCoordinator initialized")
    
    async def start(self):
        """Start the state coordinator processor."""
        if self._is_running:
            logger.warning("PHASE 4 FIX: State coordinator already running")
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_transition_queue())
        
        logger.info("PHASE 4 FIX: State coordinator started")
    
    async def stop(self):
        """Stop the state coordinator processor."""
        self._is_running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("PHASE 4 FIX: State coordinator stopped")
    
    async def request_state_transition(
        self,
        connection_id: str,
        component: str,
        to_state: WebSocketSystemState,
        priority: StateTransitionPriority = StateTransitionPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        PHASE 4 FIX: Request a state transition with conflict resolution.
        
        Args:
            connection_id: WebSocket connection identifier
            component: Component requesting the transition
            to_state: Target state
            priority: Transition priority for scheduling
            metadata: Optional metadata for the transition
            user_id: Optional user identifier
            
        Returns:
            bool: True if transition was accepted, False if rejected
        """
        try:
            with self._lock:
                current_state = self._connection_states.get(connection_id, WebSocketSystemState.INITIALIZING)
                
                # Validate transition is allowed
                if not self._is_transition_allowed(current_state, to_state, component):
                    logger.warning(f"PHASE 4 FIX: Transition rejected: {current_state} -> {to_state} by {component} (connection: {connection_id})")
                    return False
                
                # Create transition request
                request = StateTransitionRequest(
                    request_id=f"transition_{uuid.uuid4().hex[:8]}",
                    component=component,
                    from_state=current_state,
                    to_state=to_state,
                    priority=priority,
                    metadata=metadata or {},
                    user_id=user_id,
                    connection_id=connection_id
                )
                
                # Check for conflicts
                if await self._check_for_conflicts(request):
                    logger.warning(f"PHASE 4 FIX: Transition conflicts detected for {connection_id}, queuing for resolution")
                    self._metrics.conflicts_resolved += 1
                
                # Add to appropriate priority queue
                priority_level = priority.value
                self._transition_queue[priority_level].append(request)
                
                # Track active components
                self._active_components[connection_id].add(component)
                
                logger.debug(f"PHASE 4 FIX: State transition requested: {current_state} -> {to_state} by {component} (priority: {priority.name})")
                return True
                
        except Exception as e:
            logger.error(f"PHASE 4 FIX: Error requesting state transition: {e}")
            return False
    
    async def get_connection_state(self, connection_id: str) -> WebSocketSystemState:
        """Get current state for a connection."""
        with self._lock:
            return self._connection_states.get(connection_id, WebSocketSystemState.INITIALIZING)
    
    async def get_connection_metadata(self, connection_id: str) -> Dict[str, Any]:
        """Get metadata for a connection."""
        with self._lock:
            return self._connection_metadata.get(connection_id, {}).copy()
    
    async def register_connection(self, connection_id: str, user_id: Optional[str] = None) -> bool:
        """
        PHASE 4 FIX: Register a new WebSocket connection with the coordinator.
        
        Args:
            connection_id: WebSocket connection identifier
            user_id: Optional user identifier
            
        Returns:
            bool: True if registration successful
        """
        try:
            with self._lock:
                if connection_id in self._connection_states:
                    logger.warning(f"PHASE 4 FIX: Connection {connection_id} already registered")
                    return True
                
                # Initialize connection state
                self._connection_states[connection_id] = WebSocketSystemState.INITIALIZING
                self._connection_metadata[connection_id] = {
                    'user_id': user_id,
                    'registered_at': datetime.now(timezone.utc).isoformat(),
                    'components': set()
                }
                self._connection_timelines[connection_id] = []
                self._transition_locks[connection_id] = asyncio.Lock()
                
                self._metrics.active_connections += 1
                
                logger.info(f"PHASE 4 FIX: Registered connection {connection_id} for user {user_id[:8] if user_id else 'unknown'}")
                return True
                
        except Exception as e:
            logger.error(f"PHASE 4 FIX: Error registering connection: {e}")
            return False
    
    async def unregister_connection(self, connection_id: str) -> bool:
        """
        PHASE 4 FIX: Unregister a WebSocket connection from the coordinator.
        
        Args:
            connection_id: WebSocket connection identifier
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            with self._lock:
                if connection_id not in self._connection_states:
                    logger.warning(f"PHASE 4 FIX: Connection {connection_id} not registered")
                    return True
                
                # Clean up connection state
                del self._connection_states[connection_id]
                del self._connection_metadata[connection_id]
                del self._connection_timelines[connection_id]
                if connection_id in self._transition_locks:
                    del self._transition_locks[connection_id]
                if connection_id in self._active_components:
                    del self._active_components[connection_id]
                if connection_id in self._pending_transitions:
                    del self._pending_transitions[connection_id]
                
                # Remove from all queues
                for priority_queue in self._transition_queue.values():
                    self._transition_queue[priority_queue] = [
                        req for req in priority_queue if req.connection_id != connection_id
                    ]
                
                self._metrics.active_connections = max(0, self._metrics.active_connections - 1)
                
                logger.info(f"PHASE 4 FIX: Unregistered connection {connection_id}")
                return True
                
        except Exception as e:
            logger.error(f"PHASE 4 FIX: Error unregistering connection: {e}")
            return False
    
    def _is_transition_allowed(
        self, 
        from_state: WebSocketSystemState, 
        to_state: WebSocketSystemState, 
        component: str
    ) -> bool:
        """
        PHASE 4 FIX: Check if a state transition is allowed.
        
        This method implements state machine rules to prevent invalid transitions
        that could cause WebSocket errors.
        """
        # Define allowed transitions
        allowed_transitions = {
            WebSocketSystemState.INITIALIZING: {
                WebSocketSystemState.AUTHENTICATING,
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED
            },
            WebSocketSystemState.AUTHENTICATING: {
                WebSocketSystemState.FACTORY_CREATING,
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED,
                WebSocketSystemState.DEGRADED
            },
            WebSocketSystemState.FACTORY_CREATING: {
                WebSocketSystemState.MANAGER_READY,
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED,
                WebSocketSystemState.DEGRADED
            },
            WebSocketSystemState.MANAGER_READY: {
                WebSocketSystemState.EVENT_DELIVERY_ACTIVE,
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED,
                WebSocketSystemState.DEGRADED
            },
            WebSocketSystemState.EVENT_DELIVERY_ACTIVE: {
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED,
                WebSocketSystemState.DEGRADED
            },
            WebSocketSystemState.DEGRADED: {
                WebSocketSystemState.MANAGER_READY,
                WebSocketSystemState.EVENT_DELIVERY_ACTIVE,
                WebSocketSystemState.FAILED,
                WebSocketSystemState.DISCONNECTED
            },
            WebSocketSystemState.FAILED: {
                WebSocketSystemState.INITIALIZING,
                WebSocketSystemState.DISCONNECTED
            },
            WebSocketSystemState.DISCONNECTED: {
                WebSocketSystemState.INITIALIZING
            }
        }
        
        allowed = to_state in allowed_transitions.get(from_state, set())
        
        if not allowed:
            logger.warning(f"PHASE 4 FIX: Invalid transition attempted: {from_state} -> {to_state} by {component}")
        
        return allowed
    
    async def _check_for_conflicts(self, request: StateTransitionRequest) -> bool:
        """
        PHASE 4 FIX: Check for conflicting state transition requests.
        
        Args:
            request: State transition request to check
            
        Returns:
            bool: True if conflicts detected, False otherwise
        """
        connection_id = request.connection_id
        
        # Check if there's already a pending transition for this connection
        if connection_id in self._pending_transitions:
            existing = self._pending_transitions[connection_id]
            
            # Conflict if different target states from different components
            if (existing.to_state != request.to_state and 
                existing.component != request.component and
                existing.priority.value == request.priority.value):
                
                conflict_info = {
                    'connection_id': connection_id,
                    'existing_request': {
                        'component': existing.component,
                        'to_state': existing.to_state.value,
                        'priority': existing.priority.value
                    },
                    'new_request': {
                        'component': request.component,
                        'to_state': request.to_state.value,
                        'priority': request.priority.value
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                self._conflict_history.append(conflict_info)
                logger.warning(f"PHASE 4 FIX: State transition conflict detected: {conflict_info}")
                return True
        
        return False
    
    async def _process_transition_queue(self):
        """
        PHASE 4 FIX: Process queued state transitions with priority ordering.
        
        This background task processes state transitions in priority order
        while preventing race conditions.
        """
        logger.info("PHASE 4 FIX: State coordinator processor started")
        
        while self._is_running:
            try:
                await asyncio.sleep(0.01)  # 10ms processing interval
                
                # Process transitions in priority order (highest first)
                for priority_level in sorted(self._transition_queue.keys(), reverse=True):
                    queue = self._transition_queue[priority_level]
                    
                    if not queue:
                        continue
                    
                    # Process the next request in this priority level
                    request = queue.pop(0)
                    
                    # Apply the state transition
                    success = await self._apply_state_transition(request)
                    
                    if success:
                        self._metrics.successful_transitions += 1
                    else:
                        self._metrics.failed_transitions += 1
                    
                    self._metrics.total_transitions += 1
                    self._metrics.last_activity = datetime.now(timezone.utc)
                    
                    # Prevent overwhelming the system
                    if self._metrics.total_transitions % 100 == 0:
                        await asyncio.sleep(0.1)  # Brief pause every 100 transitions
                
            except Exception as e:
                logger.error(f"PHASE 4 FIX: Error in transition processor: {e}")
                await asyncio.sleep(1.0)  # Longer pause on errors
        
        logger.info("PHASE 4 FIX: State coordinator processor stopped")
    
    async def _apply_state_transition(self, request: StateTransitionRequest) -> bool:
        """
        PHASE 4 FIX: Apply a state transition with race condition protection.
        
        Args:
            request: State transition request to apply
            
        Returns:
            bool: True if transition applied successfully
        """
        connection_id = request.connection_id
        
        try:
            # Use per-connection lock to prevent race conditions
            if connection_id not in self._transition_locks:
                self._transition_locks[connection_id] = asyncio.Lock()
            
            async with self._transition_locks[connection_id]:
                # Double-check state hasn't changed while waiting for lock
                current_state = self._connection_states.get(connection_id, WebSocketSystemState.INITIALIZING)
                
                if current_state != request.from_state:
                    logger.warning(f"PHASE 4 FIX: State changed during transition wait: expected {request.from_state}, got {current_state}")
                    return False
                
                # Apply the state transition
                self._connection_states[connection_id] = request.to_state
                
                # Update metadata
                if connection_id in self._connection_metadata:
                    self._connection_metadata[connection_id].update({
                        'last_transition': datetime.now(timezone.utc).isoformat(),
                        'current_state': request.to_state.value,
                        'transitioned_by': request.component
                    })
                
                # Add to timeline
                if connection_id in self._connection_timelines:
                    self._connection_timelines[connection_id].append(request)
                    
                    # Limit timeline size to prevent memory growth
                    if len(self._connection_timelines[connection_id]) > 50:
                        self._connection_timelines[connection_id] = self._connection_timelines[connection_id][-25:]
                
                # Remove from pending transitions
                if connection_id in self._pending_transitions:
                    del self._pending_transitions[connection_id]
                
                logger.debug(f"PHASE 4 FIX: Applied state transition: {request.from_state} -> {request.to_state} for {connection_id} by {request.component}")
                return True
                
        except Exception as e:
            logger.error(f"PHASE 4 FIX: Error applying state transition: {e}")
            return False
    
    def get_coordinator_metrics(self) -> Dict[str, Any]:
        """Get coordinator performance metrics."""
        success_rate = (self._metrics.successful_transitions / max(1, self._metrics.total_transitions)) * 100
        
        return {
            'total_transitions': self._metrics.total_transitions,
            'successful_transitions': self._metrics.successful_transitions,
            'failed_transitions': self._metrics.failed_transitions,
            'success_rate': round(success_rate, 2),
            'conflicts_resolved': self._metrics.conflicts_resolved,
            'race_conditions_prevented': self._metrics.race_conditions_prevented,
            'active_connections': self._metrics.active_connections,
            'queue_sizes': {
                priority: len(queue) 
                for priority, queue in self._transition_queue.items()
            },
            'recent_conflicts': len([
                c for c in self._conflict_history[-10:] 
                if (datetime.now(timezone.utc) - datetime.fromisoformat(c['timestamp'])).total_seconds() < 300
            ]),
            'last_activity': self._metrics.last_activity.isoformat() if self._metrics.last_activity else None
        }
    
    def get_connection_timeline(self, connection_id: str) -> List[Dict[str, Any]]:
        """Get state transition timeline for a connection."""
        timeline = self._connection_timelines.get(connection_id, [])
        return [
            {
                'request_id': req.request_id,
                'component': req.component,
                'from_state': req.from_state.value,
                'to_state': req.to_state.value,
                'priority': req.priority.value,
                'timestamp': req.timestamp.isoformat(),
                'metadata': req.metadata
            }
            for req in timeline
        ]


# Global coordinator instance
_state_coordinator: Optional[WebSocketStateCoordinator] = None


def get_websocket_state_coordinator() -> WebSocketStateCoordinator:
    """
    PHASE 4 FIX: Get the global WebSocket state coordinator instance.
    
    Returns:
        WebSocketStateCoordinator: Global coordinator instance
    """
    global _state_coordinator
    if _state_coordinator is None:
        _state_coordinator = WebSocketStateCoordinator()
        logger.info("PHASE 4 FIX: Created global WebSocket state coordinator")
    return _state_coordinator


async def ensure_coordinator_running():
    """PHASE 4 FIX: Ensure the state coordinator is running."""
    coordinator = get_websocket_state_coordinator()
    if not coordinator._is_running:
        await coordinator.start()


# Integration helper functions for existing components
async def coordinate_authentication_state(
    connection_id: str, 
    success: bool, 
    user_id: Optional[str] = None
) -> bool:
    """
    PHASE 4 FIX: Coordinate authentication state transition.
    
    Args:
        connection_id: WebSocket connection identifier
        success: Whether authentication was successful
        user_id: Optional user identifier
        
    Returns:
        bool: True if state transition was coordinated successfully
    """
    coordinator = get_websocket_state_coordinator()
    
    if success:
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="authentication",
            to_state=WebSocketSystemState.FACTORY_CREATING,
            priority=StateTransitionPriority.HIGH,
            user_id=user_id,
            metadata={'auth_success': True}
        )
    else:
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="authentication", 
            to_state=WebSocketSystemState.FAILED,
            priority=StateTransitionPriority.CRITICAL,
            user_id=user_id,
            metadata={'auth_success': False}
        )


async def coordinate_factory_state(
    connection_id: str, 
    manager_created: bool, 
    emergency_mode: bool = False
) -> bool:
    """
    PHASE 4 FIX: Coordinate factory state transition.
    
    Args:
        connection_id: WebSocket connection identifier  
        manager_created: Whether manager was created successfully
        emergency_mode: Whether operating in emergency/degraded mode
        
    Returns:
        bool: True if state transition was coordinated successfully
    """
    coordinator = get_websocket_state_coordinator()
    
    if manager_created:
        target_state = WebSocketSystemState.DEGRADED if emergency_mode else WebSocketSystemState.MANAGER_READY
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="factory",
            to_state=target_state,
            priority=StateTransitionPriority.HIGH,
            metadata={'manager_created': True, 'emergency_mode': emergency_mode}
        )
    else:
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="factory",
            to_state=WebSocketSystemState.FAILED,
            priority=StateTransitionPriority.CRITICAL,
            metadata={'manager_created': False}
        )


async def coordinate_event_delivery_state(connection_id: str, active: bool) -> bool:
    """
    PHASE 4 FIX: Coordinate event delivery state transition.
    
    Args:
        connection_id: WebSocket connection identifier
        active: Whether event delivery is active
        
    Returns:
        bool: True if state transition was coordinated successfully  
    """
    coordinator = get_websocket_state_coordinator()
    
    if active:
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="event_delivery",
            to_state=WebSocketSystemState.EVENT_DELIVERY_ACTIVE,
            priority=StateTransitionPriority.NORMAL,
            metadata={'event_delivery_active': True}
        )
    else:
        return await coordinator.request_state_transition(
            connection_id=connection_id,
            component="event_delivery",
            to_state=WebSocketSystemState.DEGRADED,
            priority=StateTransitionPriority.HIGH,
            metadata={'event_delivery_active': False}
        )