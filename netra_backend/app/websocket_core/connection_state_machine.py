"""
WebSocket Connection State Machine

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & User Experience
- Value Impact: Eliminates race conditions between WebSocket transport ready and application ready
- Strategic Impact: Enables proper message queuing and prevents lost messages during connection setup

CRITICAL: Implements the application-level connection state management identified as missing
in our comprehensive WebSocket race condition analysis. This addresses the core issue where
WebSocket "accepted" (transport ready) was conflated with "ready to process messages" 
(fully operational).

The state machine provides:
1. Clear state transitions: CONNECTING  ->  ACCEPTED  ->  AUTHENTICATED  ->  SERVICES_READY  ->  PROCESSING_READY
2. Thread-safe state management with proper rollback on failures
3. Integration with existing is_websocket_connected_and_ready() function
4. Message queuing coordination to buffer messages until fully ready
"""

import asyncio
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Set, Callable
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.exceptions.agent_exceptions import AgentStateTransitionError
from shared.types.core_types import UserID, ConnectionID, ensure_user_id

logger = central_logger.get_logger(__name__)


class ApplicationConnectionState(str, Enum):
    """
    Application-level connection states for WebSocket connections.
    
    These states represent the application readiness, not just transport-level connectivity.
    This addresses the core race condition where WebSocket.accept() completion (transport ready)
    was being used to determine message processing readiness (application ready).
    """
    
    # Initial connection establishment
    CONNECTING = "connecting"           # WebSocket handshake in progress
    ACCEPTED = "accepted"               # WebSocket transport accepted, but not yet ready
    
    # Application setup phases
    AUTHENTICATED = "authenticated"     # User authentication completed
    SERVICES_READY = "services_ready"   # Required services initialized (supervisor, threads)
    PROCESSING_READY = "processing_ready"  # Fully operational, ready for message processing
    
    # Operational states
    PROCESSING = "processing"           # Actively processing messages
    IDLE = "idle"                      # Connected but not actively processing
    
    # Degraded/error states
    DEGRADED = "degraded"              # Partial functionality due to service unavailability
    RECONNECTING = "reconnecting"       # Attempting to restore full functionality
    
    # Terminal states
    CLOSING = "closing"                # Graceful shutdown in progress
    CLOSED = "closed"                  # Connection terminated
    FAILED = "failed"                  # Connection failed due to unrecoverable error
    
    @classmethod
    def is_operational(cls, state: 'ApplicationConnectionState') -> bool:
        """Check if state allows message processing."""
        return state in {
            cls.PROCESSING_READY, cls.PROCESSING, cls.IDLE, cls.DEGRADED
        }
    
    @classmethod
    def is_setup_phase(cls, state: 'ApplicationConnectionState') -> bool:
        """Check if state is part of connection setup."""
        return state in {
            cls.CONNECTING, cls.ACCEPTED, cls.AUTHENTICATED, cls.SERVICES_READY
        }
    
    @classmethod
    def is_terminal(cls, state: 'ApplicationConnectionState') -> bool:
        """Check if state is terminal (no further transitions)."""
        return state in {cls.CLOSED, cls.FAILED}


@dataclass
class StateTransitionInfo:
    """Information about a state transition."""
    from_state: ApplicationConnectionState
    to_state: ApplicationConnectionState
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Exception for state transition errors - alias to AgentStateTransitionError for SSOT
class StateTransitionError(AgentStateTransitionError):
    """Exception for connection state transition failures."""
    
    def __init__(self, message: str, connection_id: str = None, from_state: str = None, to_state: str = None):
        super().__init__(
            agent_name=f"ConnectionStateMachine({connection_id})" if connection_id else "ConnectionStateMachine",
            from_state=from_state or "unknown",
            to_state=to_state or "unknown", 
            transition_error=message
        )


@dataclass
class ConnectionStateTransition:
    """
    Represents an atomic connection state transition.
    
    Business Value: Provides atomic state change operations with validation
    and rollback capabilities to prevent race conditions in WebSocket setup.
    """
    connection_id: str
    from_state: ApplicationConnectionState
    to_state: ApplicationConnectionState
    user_id: UserID
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate transition data after initialization."""
        if not self.connection_id:
            raise ValueError("connection_id is required")
        
        if not isinstance(self.from_state, ApplicationConnectionState):
            raise ValueError("from_state must be ApplicationConnectionState")
            
        if not isinstance(self.to_state, ApplicationConnectionState):
            raise ValueError("to_state must be ApplicationConnectionState")
            
        self.user_id = ensure_user_id(self.user_id)


class ConnectionStateValidator:
    """
    Validates connection state transitions according to business rules.
    
    Business Value: Enforces correct WebSocket setup flow preventing
    message processing before connection is fully operational.
    """
    
    @staticmethod
    def is_valid_transition(from_state: ApplicationConnectionState, 
                          to_state: ApplicationConnectionState) -> bool:
        """
        Validate if state transition is allowed according to business rules.
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            True if transition is valid, False otherwise
        """
        # Terminal states can't transition (except FAILED can go to CONNECTING for retry)
        if ApplicationConnectionState.is_terminal(from_state) and to_state != ApplicationConnectionState.CONNECTING:
            return False
        
        # Define valid transitions
        valid_transitions = {
            ApplicationConnectionState.CONNECTING: {
                ApplicationConnectionState.ACCEPTED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.ACCEPTED: {
                ApplicationConnectionState.AUTHENTICATED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.AUTHENTICATED: {
                ApplicationConnectionState.SERVICES_READY,
                ApplicationConnectionState.DEGRADED,  # If services aren't available
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.SERVICES_READY: {
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,  # If partial services
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.PROCESSING_READY: {
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.PROCESSING: {
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.IDLE: {
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.DEGRADED: {
                ApplicationConnectionState.PROCESSING_READY,  # Recovery
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.RECONNECTING,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.RECONNECTING: {
                ApplicationConnectionState.SERVICES_READY,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.CLOSING: {
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.CLOSED: {},  # Terminal
            ApplicationConnectionState.FAILED: {
                ApplicationConnectionState.CONNECTING  # Allow retry
            }
        }
        
        return to_state in valid_transitions.get(from_state, set())
    
    @staticmethod
    def validate_transition(transition: ConnectionStateTransition) -> bool:
        """
        Validate a complete transition object.
        
        Args:
            transition: ConnectionStateTransition to validate
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        if not transition.connection_id:
            raise StateTransitionError(
                "Connection ID is required", 
                connection_id=transition.connection_id
            )
        
        if not ConnectionStateValidator.is_valid_transition(transition.from_state, transition.to_state):
            raise StateTransitionError(
                f"Invalid transition: {transition.from_state} -> {transition.to_state}",
                connection_id=transition.connection_id,
                from_state=transition.from_state.value,
                to_state=transition.to_state.value
            )
        
        return True


class ConnectionStateMachine:
    """
    Thread-safe WebSocket application connection state machine.
    
    CRITICAL FUNCTIONALITY:
    - Manages application-level connection state separate from WebSocket transport state
    - Provides thread-safe state transitions with validation
    - Integrates with existing is_websocket_connected_and_ready() function
    - Coordinates with MessageQueue to buffer messages during setup phases
    - Supports rollback on setup failures to prevent inconsistent states
    
    This addresses the root cause identified in our Five WHYS analysis:
    The system conflated "WebSocket accepted" with "ready to process messages".
    """
    
    def __init__(self, connection_id: ConnectionID, user_id: UserID, 
                 state_change_callbacks: Optional[Set[Callable]] = None):
        """
        Initialize connection state machine.
        
        Args:
            connection_id: Unique connection identifier
            user_id: User ID for this connection
            state_change_callbacks: Optional set of callbacks for state changes
        """
        self.connection_id = str(connection_id)
        self.user_id = ensure_user_id(user_id)
        self.state_change_callbacks = state_change_callbacks or set()
        
        # Thread safety
        self._lock = threading.RLock()
        self._state_history: list[StateTransitionInfo] = []
        
        # Current state
        self._current_state = ApplicationConnectionState.CONNECTING
        self._setup_start_time = time.time()
        self._last_transition_time = time.time()
        
        # Error tracking
        self._transition_failures = 0
        self._max_transition_failures = 5
        
        # Setup tracking
        self._setup_phases_completed: Set[ApplicationConnectionState] = set()
        self._setup_metadata: Dict[str, Any] = {}
        
        # Performance metrics
        self._metrics = {
            "total_transitions": 0,
            "failed_transitions": 0,
            "setup_duration_seconds": 0.0,
            "last_activity": time.time()
        }
        
        logger.info(f"ConnectionStateMachine initialized for {self.connection_id}, user: {self.user_id}")
    
    @property
    def current_state(self) -> ApplicationConnectionState:
        """Get current connection state (thread-safe)."""
        with self._lock:
            return self._current_state
    
    @property
    def is_operational(self) -> bool:
        """Check if connection is operational for message processing."""
        with self._lock:
            return ApplicationConnectionState.is_operational(self._current_state)
    
    @property
    def is_ready_for_messages(self) -> bool:
        """
        Check if connection is ready for message processing.
        
        This is the key integration point with is_websocket_connected_and_ready().
        Returns True only when we've reached PROCESSING_READY state or beyond.
        """
        with self._lock:
            return self._current_state in {
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.DEGRADED  # Allow degraded mode processing
            }
    
    @property
    def setup_duration(self) -> float:
        """Get setup duration in seconds."""
        with self._lock:
            if self._current_state == ApplicationConnectionState.CONNECTING:
                return time.time() - self._setup_start_time
            return self._metrics["setup_duration_seconds"]
    
    def add_state_change_callback(self, callback: Callable[[StateTransitionInfo], None]):
        """Add callback for state changes."""
        with self._lock:
            self.state_change_callbacks.add(callback)
    
    def remove_state_change_callback(self, callback: Callable[[StateTransitionInfo], None]):
        """Remove state change callback."""
        with self._lock:
            self.state_change_callbacks.discard(callback)
    
    def transition_to(self, new_state: ApplicationConnectionState, 
                      reason: Optional[str] = None, 
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Transition to new state with validation and rollback support.
        
        Args:
            new_state: Target state to transition to
            reason: Optional reason for the transition
            metadata: Optional metadata about the transition
            
        Returns:
            True if transition was successful, False otherwise
        """
        with self._lock:
            old_state = self._current_state
            
            # Validate transition
            if not self._is_valid_transition(old_state, new_state):
                logger.warning(f"Invalid state transition for {self.connection_id}: {old_state} -> {new_state}")
                self._metrics["failed_transitions"] += 1
                self._transition_failures += 1
                return False
            
            # Check if we've exceeded maximum failures
            if self._transition_failures >= self._max_transition_failures:
                logger.error(f"Connection {self.connection_id} exceeded maximum transition failures, forcing FAILED state")
                new_state = ApplicationConnectionState.FAILED
            
            # Perform transition
            try:
                self._current_state = new_state
                self._last_transition_time = time.time()
                self._metrics["total_transitions"] += 1
                self._metrics["last_activity"] = time.time()
                
                # Track setup completion
                if ApplicationConnectionState.is_setup_phase(old_state) and not ApplicationConnectionState.is_setup_phase(new_state):
                    self._metrics["setup_duration_seconds"] = time.time() - self._setup_start_time
                    logger.info(f"Setup completed for {self.connection_id} in {self._metrics['setup_duration_seconds']:.2f}s")
                
                # Record transition
                transition_info = StateTransitionInfo(
                    from_state=old_state,
                    to_state=new_state,
                    timestamp=datetime.now(timezone.utc),
                    reason=reason,
                    metadata=metadata or {}
                )
                self._state_history.append(transition_info)
                
                # Update setup tracking
                if ApplicationConnectionState.is_setup_phase(new_state):
                    self._setup_phases_completed.add(new_state)
                    if metadata:
                        self._setup_metadata.update(metadata)
                
                logger.info(f"Connection {self.connection_id} transitioned: {old_state} -> {new_state} (reason: {reason})")
                
                # Notify callbacks
                self._notify_state_change_callbacks(transition_info)
                
                # Reset failure count on successful transition
                self._transition_failures = 0
                
                return True
                
            except Exception as e:
                logger.error(f"State transition failed for {self.connection_id}: {old_state} -> {new_state}: {e}")
                self._metrics["failed_transitions"] += 1
                self._transition_failures += 1
                
                # Rollback on critical errors
                try:
                    self._current_state = old_state
                    logger.info(f"Rolled back state for {self.connection_id} to {old_state}")
                except Exception as rollback_error:
                    logger.critical(f"State rollback failed for {self.connection_id}: {rollback_error}")
                    self._current_state = ApplicationConnectionState.FAILED
                
                return False
    
    def _is_valid_transition(self, from_state: ApplicationConnectionState, 
                           to_state: ApplicationConnectionState) -> bool:
        """Validate if state transition is allowed."""
        
        # Terminal states can't transition (except FAILED can go to CONNECTING for retry)
        if ApplicationConnectionState.is_terminal(from_state) and to_state != ApplicationConnectionState.CONNECTING:
            return False
        
        # Define valid transitions
        valid_transitions = {
            ApplicationConnectionState.CONNECTING: {
                ApplicationConnectionState.ACCEPTED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.ACCEPTED: {
                ApplicationConnectionState.AUTHENTICATED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.AUTHENTICATED: {
                ApplicationConnectionState.SERVICES_READY,
                ApplicationConnectionState.DEGRADED,  # If services aren't available
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.SERVICES_READY: {
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,  # If partial services
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.PROCESSING_READY: {
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.PROCESSING: {
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.IDLE: {
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.DEGRADED: {
                ApplicationConnectionState.PROCESSING_READY,  # Recovery
                ApplicationConnectionState.PROCESSING,
                ApplicationConnectionState.IDLE,
                ApplicationConnectionState.RECONNECTING,
                ApplicationConnectionState.CLOSING,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.RECONNECTING: {
                ApplicationConnectionState.SERVICES_READY,
                ApplicationConnectionState.PROCESSING_READY,
                ApplicationConnectionState.DEGRADED,
                ApplicationConnectionState.FAILED,
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.CLOSING: {
                ApplicationConnectionState.CLOSED
            },
            ApplicationConnectionState.CLOSED: {},  # Terminal
            ApplicationConnectionState.FAILED: {
                ApplicationConnectionState.CONNECTING  # Allow retry
            }
        }
        
        return to_state in valid_transitions.get(from_state, set())
    
    def _notify_state_change_callbacks(self, transition_info: StateTransitionInfo):
        """Notify all registered callbacks about state change."""
        for callback in self.state_change_callbacks.copy():  # Copy to avoid modification during iteration
            try:
                callback(transition_info)
            except Exception as e:
                logger.error(f"State change callback failed for {self.connection_id}: {e}")
    
    def get_state_history(self) -> list[StateTransitionInfo]:
        """Get state transition history."""
        with self._lock:
            return self._state_history.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get connection state metrics."""
        with self._lock:
            return {
                **self._metrics,
                "current_state": self._current_state.value,
                "setup_phases_completed": [state.value for state in self._setup_phases_completed],
                "transition_failures": self._transition_failures,
                "is_operational": self.is_operational,
                "is_ready_for_messages": self.is_ready_for_messages,
                "setup_duration": self.setup_duration
            }
    
    def force_failed_state(self, reason: str):
        """Force connection to failed state (emergency use only)."""
        with self._lock:
            logger.error(f"Forcing FAILED state for {self.connection_id}: {reason}")
            self._current_state = ApplicationConnectionState.FAILED
            self._transition_failures = self._max_transition_failures
            
            # Record emergency transition
            transition_info = StateTransitionInfo(
                from_state=self._current_state,
                to_state=ApplicationConnectionState.FAILED,
                timestamp=datetime.now(timezone.utc),
                reason=f"EMERGENCY: {reason}",
                metadata={"emergency_transition": True}
            )
            self._state_history.append(transition_info)
            self._notify_state_change_callbacks(transition_info)
    
    def can_process_messages(self) -> bool:
        """
        Enhanced version of is_ready_for_messages with additional validation.
        
        This provides the enhanced readiness check that integrates with the existing
        is_websocket_connected_and_ready() function in utils.py.
        """
        with self._lock:
            # Basic state check
            if not self.is_ready_for_messages:
                return False
            
            # Additional validation for degraded mode
            if self._current_state == ApplicationConnectionState.DEGRADED:
                # In degraded mode, check if we have minimum required functionality
                setup_phases = len(self._setup_phases_completed)
                if setup_phases < 2:  # Need at least ACCEPTED and AUTHENTICATED
                    return False
            
            # Check for excessive failures
            if self._transition_failures >= self._max_transition_failures - 1:
                return False
            
            return True
    
    def get_current_state(self) -> ApplicationConnectionState:
        """
        Get the current connection state.
        
        This method provides compatibility with the test interface while
        delegating to the existing current_state property.
        
        Returns:
            Current ApplicationConnectionState
        """
        return self.current_state
    
    def execute_transition(self, transition: ConnectionStateTransition) -> bool:
        """
        Execute a state transition using a ConnectionStateTransition object.
        
        This method provides compatibility with the test interface while
        delegating to the existing transition_to method.
        
        Args:
            transition: ConnectionStateTransition object describing the transition
            
        Returns:
            True if transition succeeded, False otherwise
        """
        # Validate the transition first
        try:
            ConnectionStateValidator.validate_transition(transition)
        except StateTransitionError as e:
            logger.warning(f"Transition validation failed: {e}")
            return False
        
        # Verify the from_state matches current state
        if transition.from_state != self.current_state:
            logger.warning(
                f"Transition from_state {transition.from_state} does not match "
                f"current state {self.current_state} for connection {self.connection_id}"
            )
            return False
        
        # Execute the transition
        return self.transition_to(
            new_state=transition.to_state,
            reason=transition.reason,
            metadata=transition.metadata
        )
    
    def _validate_transition(self, from_state: ApplicationConnectionState, to_state: ApplicationConnectionState) -> bool:
        """
        Validate transition for compatibility with test interface.
        
        This method provides compatibility while delegating to the existing
        _is_valid_transition method.
        
        Args:
            from_state: Starting state
            to_state: Target state
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        is_valid = self._is_valid_transition(from_state, to_state)
        if not is_valid:
            raise StateTransitionError(
                f"Invalid transition: {from_state} -> {to_state}",
                connection_id=self.connection_id,
                from_state=from_state.value,
                to_state=to_state.value
            )
        return is_valid
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        with self._lock:
            return (f"ConnectionStateMachine(connection_id='{self.connection_id}', "
                   f"user_id='{self.user_id}', state='{self._current_state.value}', "
                   f"operational={self.is_operational}, ready={self.is_ready_for_messages})")


class ConnectionStateMachineRegistry:
    """
    Registry for managing connection state machines.
    
    Provides centralized access to connection state machines for integration
    with existing WebSocket utilities and the message loop.
    """
    
    def __init__(self):
        self._machines: Dict[str, ConnectionStateMachine] = {}
        self._lock = threading.RLock()
        
        logger.info("ConnectionStateMachineRegistry initialized")
    
    def register_connection(self, connection_id: ConnectionID, user_id: UserID,
                          state_change_callbacks: Optional[Set[Callable]] = None) -> ConnectionStateMachine:
        """Register a new connection state machine."""
        with self._lock:
            connection_key = str(connection_id)
            
            if connection_key in self._machines:
                existing_machine = self._machines[connection_key]
                logger.critical(f"DUPLICATE CONNECTION REGISTRATION DETECTED: Connection {connection_key} already registered. "
                               f"Existing state: {existing_machine.current_state}, User: {existing_machine.user_id}, "
                               f"Requested User: {user_id}. This indicates a race condition in connection setup. "
                               f"Returning existing machine to prevent state corruption.")
                return existing_machine
            
            machine = ConnectionStateMachine(connection_id, user_id, state_change_callbacks)
            self._machines[connection_key] = machine
            
            logger.info(f"Registered connection state machine for {connection_key}")
            return machine
    
    def get_connection_state_machine(self, connection_id: ConnectionID) -> Optional[ConnectionStateMachine]:
        """Get connection state machine by ID."""
        with self._lock:
            return self._machines.get(str(connection_id))
    
    def unregister_connection(self, connection_id: ConnectionID) -> bool:
        """Unregister connection state machine."""
        with self._lock:
            connection_key = str(connection_id)
            if connection_key in self._machines:
                del self._machines[connection_key]
                logger.info(f"Unregistered connection state machine for {connection_key}")
                return True
            return False
    
    def get_all_operational_connections(self) -> Dict[str, ConnectionStateMachine]:
        """Get all operational connection state machines."""
        with self._lock:
            return {
                conn_id: machine for conn_id, machine in self._machines.items()
                if machine.is_operational
            }
    
    def get_connections_by_state(self, state: ApplicationConnectionState) -> Dict[str, ConnectionStateMachine]:
        """Get connections in specific state."""
        with self._lock:
            return {
                conn_id: machine for conn_id, machine in self._machines.items()
                if machine.current_state == state
            }
    
    def cleanup_closed_connections(self) -> int:
        """Remove closed/failed connections from registry."""
        with self._lock:
            to_remove = []
            for conn_id, machine in self._machines.items():
                if ApplicationConnectionState.is_terminal(machine.current_state):
                    to_remove.append(conn_id)
            
            for conn_id in to_remove:
                del self._machines[conn_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} closed connections")
            
            return len(to_remove)
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with self._lock:
            state_counts = {}
            total_machines = len(self._machines)
            operational_count = 0
            
            for machine in self._machines.values():
                state = machine.current_state
                state_counts[state.value] = state_counts.get(state.value, 0) + 1
                if machine.is_operational:
                    operational_count += 1
            
            return {
                "total_connections": total_machines,
                "operational_connections": operational_count,
                "state_distribution": state_counts,
                "registry_size": len(self._machines)
            }


# Global registry instance for integration with existing code
_connection_state_registry: Optional[ConnectionStateMachineRegistry] = None


def get_connection_state_registry() -> ConnectionStateMachineRegistry:
    """Get global connection state registry."""
    global _connection_state_registry
    if _connection_state_registry is None:
        _connection_state_registry = ConnectionStateMachineRegistry()
    return _connection_state_registry


def get_connection_state_machine(connection_id: ConnectionID) -> Optional[ConnectionStateMachine]:
    """Convenience function to get connection state machine."""
    registry = get_connection_state_registry()
    return registry.get_connection_state_machine(connection_id)


def is_connection_ready_for_messages(connection_id: ConnectionID) -> bool:
    """
    Integration function for existing is_websocket_connected_and_ready().
    
    This function provides the enhanced readiness check that considers
    application-level state in addition to WebSocket transport state.
    
    PHASE 1 SAFETY FIX: Non-existent connections now return False instead of True
    to prevent race conditions where messages are sent before state machine setup.
    """
    machine = get_connection_state_machine(connection_id)
    if machine is None:
        # SAFETY FIX: Return False for non-existent connections to prevent race conditions
        logger.warning(f"No state machine found for connection {connection_id}, returning False for safety")
        return False
    
    return machine.can_process_messages()


# Compatibility alias for integration tests
WebSocketConnectionStateMachine = ConnectionStateMachine
# Compatibility alias for tests expecting ApplicationConnectionStateMachine
ApplicationConnectionStateMachine = ConnectionStateMachine
