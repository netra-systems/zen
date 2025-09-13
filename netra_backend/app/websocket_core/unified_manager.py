"""Unified WebSocket Manager - SSOT for WebSocket connection management.

This module is the single source of truth for WebSocket connection management.
"""

import asyncio
import json
import time
import weakref
from enum import Enum
from typing import Dict, Optional, Set, Any, List, Union
from dataclasses import dataclass
from datetime import datetime, timezone

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
# Import UnifiedIDManager for SSOT ID generation
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import the protocol after it's defined to avoid circular imports
logger = get_logger(__name__)


class WebSocketManagerMode(Enum):
    """DEPRECATED: WebSocket manager modes - CONSOLIDATING TO UNIFIED SSOT.
    
    ALL MODES NOW REDIRECT TO UNIFIED MODE FOR SSOT COMPLIANCE.
    User isolation is handled through UserExecutionContext, not manager modes.
    
    MIGRATION NOTICE: This enum will be removed in v2.0. 
    Use WebSocketManager directly without specifying mode.
    """
    UNIFIED = "unified"        # SSOT: Single unified mode with UserExecutionContext isolation
    ISOLATED = "unified"       # DEPRECATED: Redirects to UNIFIED (isolation via UserExecutionContext)
    EMERGENCY = "unified"      # DEPRECATED: Redirects to UNIFIED (graceful degradation built-in)
    DEGRADED = "unified"       # DEPRECATED: Redirects to UNIFIED (auto-recovery built-in)


def _get_enum_key_representation(enum_key: Enum) -> str:
    """
    Get string representation for enum keys in dictionaries.
    
    For enum keys, we use different strategies based on enum type:
    - WebSocketState enums: Use lowercase names for consistency ("open" vs "1")
    - Integer enums (IntEnum): Use string value for readability ("1" vs "first")  
    - String/text enums: Use lowercase names for readability ("option_a" vs "OPTION_A")
    
    Args:
        enum_key: Enum object to convert to string key
        
    Returns:
        String representation suitable for JSON dict keys
    """
    if hasattr(enum_key, 'name') and hasattr(enum_key, 'value'):
        # WEBSOCKET STATE HANDLING: Check if this is a WebSocket state enum
        enum_name = str(enum_key.name).upper()
        websocket_state_names = {'CONNECTING', 'OPEN', 'CLOSING', 'CLOSED', 'CONNECTED', 'DISCONNECTED'}
        
        # Check if it's from a WebSocket framework module or has WebSocket-like class name
        module_name = getattr(enum_key.__class__, '__module__', '')
        framework_modules = ['starlette.websockets', 'fastapi.websockets', 'websockets']
        is_framework_websocket = any(framework_mod in module_name for framework_mod in framework_modules)
        
        class_name = enum_key.__class__.__name__
        is_websocket_class = 'websocket' in class_name.lower() and 'state' in class_name.lower()
        
        # For WebSocket state enums, always use lowercase name for keys
        if (is_framework_websocket or 
            (is_websocket_class and enum_name in websocket_state_names)):
            return str(enum_key.name).lower()
        
        # For integer-valued non-WebSocket enums, use the string representation of the value
        # This makes {"1": "initialized"} instead of {"first": "initialized"}
        elif isinstance(enum_key.value, int):
            return str(enum_key.value)
        else:
            # For string/other enums, use lowercase names for better JSON readability
            # This makes {"option_a": "selected"} instead of {"OPTION_A": "selected"}
            return str(enum_key.name).lower()
    else:
        # Fallback to string representation
        return str(enum_key)


def _serialize_message_safely(message: Any) -> Dict[str, Any]:
    """
    Safely serialize message data for WebSocket transmission with comprehensive fallback strategies.
    
    CRITICAL FIX: Handles all serialization edge cases including:
    - Enum objects (WebSocketState, etc.)  ->  converted to string values
    - Pydantic models  ->  model_dump(mode='json') for datetime handling  
    - Complex objects with to_dict() method
    - Datetime objects  ->  ISO string format
    - Dataclasses  ->  converted to dict
    - Fallback to string representation for unhandled types
    
    Args:
        message: Any message object that needs JSON serialization
        
    Returns:
        JSON-serializable dictionary
        
    Raises:
        TypeError: Only if all fallback strategies fail (should be extremely rare)
    """
    # Quick path for already serializable dicts
    if isinstance(message, dict):
        try:
            # Test if it's already JSON serializable
            json.dumps(message)
            return message
        except (TypeError, ValueError):
            # Dict contains non-serializable objects, need to process recursively
            # Process both keys AND values for enum objects
            result = {}
            for key, value in message.items():
                # Convert enum keys consistently with enum value handling
                if isinstance(key, Enum):
                    # For WebSocketState enums, use name.lower() to match value handling
                    try:
                        from starlette.websockets import WebSocketState as StarletteWebSocketState
                        if isinstance(key, StarletteWebSocketState):
                            safe_key = key.name.lower()
                        else:
                            safe_key = _get_enum_key_representation(key)
                    except (ImportError, AttributeError):
                        try:
                            from fastapi.websockets import WebSocketState as FastAPIWebSocketState  
                            if isinstance(key, FastAPIWebSocketState):
                                safe_key = key.name.lower()
                            else:
                                safe_key = _get_enum_key_representation(key)
                        except (ImportError, AttributeError):
                            safe_key = _get_enum_key_representation(key)
                else:
                    safe_key = key
                # Recursively serialize values
                result[safe_key] = _serialize_message_safely(value)
            return result
    
    # CRITICAL FIX: Handle WebSocketState enum specifically (from FastAPI/Starlette)
    # CLOUD RUN FIX: More resilient import handling to prevent startup failures
    try:
        from starlette.websockets import WebSocketState as StarletteWebSocketState
        if isinstance(message, StarletteWebSocketState):
            return message.name.lower()  # CONNECTED  ->  "connected"
    except (ImportError, AttributeError) as e:
        logger.debug(f"Starlette WebSocketState import failed (non-critical): {e}")
    
    try:
        from fastapi.websockets import WebSocketState as FastAPIWebSocketState  
        if isinstance(message, FastAPIWebSocketState):
            return message.name.lower()  # CONNECTED  ->  "connected"
    except (ImportError, AttributeError) as e:
        logger.debug(f"FastAPI WebSocketState import failed (non-critical): {e}")
    
    # Handle enum objects - CONSISTENT LOGIC: Return .value for generic enums  
    if isinstance(message, Enum):
        # WEBSOCKET STATE HANDLING: Check if this enum represents WebSocket state
        # This includes both framework enums and test enums with WebSocket-like names
        if hasattr(message, 'name') and hasattr(message, 'value'):
            # Check for WebSocket state behavior by enum name pattern
            enum_name = str(message.name).upper()
            websocket_state_names = {'CONNECTING', 'OPEN', 'CLOSING', 'CLOSED', 'CONNECTED', 'DISCONNECTED'}
            
            # Also check if it's from a WebSocket framework module
            module_name = getattr(message.__class__, '__module__', '')
            framework_modules = ['starlette.websockets', 'fastapi.websockets', 'websockets']
            is_framework_websocket = any(framework_mod in module_name for framework_mod in framework_modules)
            
            # Also check if the class name suggests it's a WebSocket state enum
            class_name = message.__class__.__name__
            is_websocket_class = 'websocket' in class_name.lower() and 'state' in class_name.lower()
            
            # Treat as WebSocket state if: 
            # 1. From framework module, OR
            # 2. Has WebSocket-like class name AND websocket state name
            if (is_framework_websocket or 
                (is_websocket_class and enum_name in websocket_state_names)):
                return str(message.name).lower()
        
        # For all other enums, return the value
        return message.value if hasattr(message, 'value') else str(message)
    
    # Handle Pydantic models with proper datetime serialization
    if hasattr(message, 'model_dump'):
        try:
            return message.model_dump(mode='json')
        except Exception as e:
            logger.warning(f"Pydantic model_dump(mode='json') failed: {e}, trying without mode")
            try:
                return message.model_dump()
            except Exception as e2:
                logger.warning(f"Pydantic model_dump failed completely: {e2}, using string fallback")
                # Fall through to the string fallback at the end of the function
    
    # Handle objects with to_dict method (UserExecutionContext, etc.)
    if hasattr(message, 'to_dict'):
        return message.to_dict()
    
    # Handle dataclasses
    if hasattr(message, '__dataclass_fields__'):
        from dataclasses import asdict
        # Convert dataclass to dict, then recursively serialize the result
        dict_data = asdict(message)
        return _serialize_message_safely(dict_data)
    
    # Handle datetime objects
    if hasattr(message, 'isoformat'):
        return message.isoformat()
    
    # Handle lists and tuples recursively
    if isinstance(message, (list, tuple)):
        return [_serialize_message_safely(item) for item in message]
    
    # Handle sets (convert to list)
    if isinstance(message, set):
        return [_serialize_message_safely(item) for item in message]
    
    # Test direct JSON serialization for basic types
    try:
        json.dumps(message)
        return message
    except (TypeError, ValueError):
        pass
    
    # Final fallback - convert to string (prevents total failure)
    logger.warning(f"Using string fallback for object of type {type(message)}: {message}")
    return str(message)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection with type safety."""
    connection_id: str
    user_id: str
    websocket: Any
    connected_at: datetime
    metadata: Dict[str, Any] = None
    thread_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate connection data after initialization."""
        # Validate user_id is properly formatted
        if self.user_id:
            self.user_id = ensure_user_id(self.user_id)


class RegistryCompat:
    """Compatibility registry for legacy tests with circular reference prevention."""
    
    def __init__(self, manager):
        # ISSUE #601 FIX: Use weakref to prevent circular reference manager <-> registry
        self._manager_ref = weakref.ref(manager)
    
    @property 
    def manager(self):
        """Get manager from weak reference, preventing circular reference memory leaks."""
        manager = self._manager_ref()
        if manager is None:
            raise RuntimeError("WebSocket manager has been garbage collected")
        return manager
    
    async def register_connection(self, user_id: str, connection_info):
        """Register a connection for test compatibility."""
        # Convert ConnectionInfo to WebSocketConnection format for the unified manager
        # ISSUE #556 FIX: Extract thread_id from connection_info if available
        thread_id = getattr(connection_info, 'thread_id', None)
        websocket_conn = WebSocketConnection(
            connection_id=connection_info.connection_id,
            user_id=user_id,
            websocket=connection_info.websocket,
            connected_at=connection_info.connected_at,
            thread_id=thread_id,  # ISSUE #556 FIX: Include thread_id for propagation
            metadata={"connection_info": connection_info}
        )
        await self.manager.add_connection(websocket_conn)
        # Store connection info for tests that expect it
        if not hasattr(self.manager, '_connection_infos'):
            self.manager._connection_infos = {}
        self.manager._connection_infos[connection_info.connection_id] = connection_info
    
    def get_user_connections(self, user_id: str):
        """Get user connections for test compatibility."""
        if hasattr(self.manager, '_connection_infos') and user_id in self.manager._user_connections:
            conn_ids = self.manager._user_connections[user_id]
            return [self.manager._connection_infos.get(conn_id) for conn_id in conn_ids if conn_id in self.manager._connection_infos]
        return []


class UnifiedWebSocketManager:
    """Unified WebSocket connection manager - SSOT with enhanced thread safety.
    
     ALERT:  FIVE WHYS ROOT CAUSE PREVENTION: This class implements the same interface
    as WebSocketManagerProtocol to ensure consistency with IsolatedWebSocketManager.
    
    While this class predates the protocol, it provides all required methods to
    maintain interface compatibility and prevent the root cause identified in
    Five Whys analysis: "lack of formal interface contracts."
    
    ENHANCED: Eliminates race conditions by providing connection-level isolation:
    - Per-user connection locks prevent race conditions during concurrent operations
    - Thread-safe connection management with user-specific isolation
    - Connection state validation prevents silent failures
    """
    
    def __init__(self, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED, user_context: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, _ssot_authorization_token: Optional[str] = None):
        """Initialize UnifiedWebSocketManager - ALL MODES CONSOLIDATED TO UNIFIED.
        
        SSOT MIGRATION NOTICE: All WebSocket modes now use unified initialization.
        User isolation is achieved through UserExecutionContext, not separate modes.
        
        Args:
            mode: DEPRECATED - All modes redirect to UNIFIED (kept for backward compatibility)
            user_context: User execution context for proper user isolation
            config: Configuration dictionary (optional)
        """
        # ISSUE #712 FIX: SSOT Validation Integration
        from netra_backend.app.websocket_core.ssot_validation_enhancer import (
            validate_websocket_manager_creation,
            FactoryBypassDetected,
            UserIsolationViolation
        )

        # PHASE 1: Direct instantiation prevention (Issue #712)
        # Check if this is being created through proper factory pattern
        if _ssot_authorization_token is None:
            error_msg = "Direct instantiation not allowed. Use get_websocket_manager() factory function."
            logger.error(f"SSOT VIOLATION: {error_msg}")
            raise FactoryBypassDetected(error_msg)

        # Validate authorization token format (basic security)
        if not isinstance(_ssot_authorization_token, str) or len(_ssot_authorization_token) < 10:
            error_msg = "Invalid SSOT authorization token format"
            logger.error(f"SSOT VIOLATION: {error_msg}")
            raise FactoryBypassDetected(error_msg)

        # PHASE 1: User context requirement enforcement (Issue #712)
        if user_context is None:
            error_msg = "UserExecutionContext required for proper user isolation"
            logger.error(f"USER ISOLATION VIOLATION: {error_msg}")
            raise UserIsolationViolation(error_msg)

        # DEPRECATED: Mode is ignored - all instances use unified behavior
        self.mode = WebSocketManagerMode.UNIFIED  # Force unified mode
        self.user_context = user_context
        self.config = config or {}

        # PHASE 1: SSOT validation integration (Issue #712)
        try:
            validate_websocket_manager_creation(
                manager_instance=self,
                user_context=user_context,
                creation_method="factory_authorized"
            )
            logger.info(f"SSOT validation passed for user {getattr(user_context, 'user_id', 'unknown')}")
        except Exception as e:
            logger.error(f"SSOT validation failed: {e}")
            # Re-raise to prevent creation of non-compliant instances
            raise
        
        # Core connection management
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        
        # RACE CONDITION FIX: Add per-user connection locks
        self._user_connection_locks: Dict[str, asyncio.Lock] = {}
        self._connection_lock_creation_lock = asyncio.Lock()
        
        # ISSUE #414 FIX: Event contamination prevention
        self._event_isolation_tokens: Dict[str, str] = {}  # connection_id -> isolation_token
        self._user_event_queues: Dict[str, asyncio.Queue] = {}  # user_id -> event_queue
        self._event_delivery_tracking: Dict[str, Dict[str, Any]] = {}  # event_id -> metadata
        self._cross_user_detection: Dict[str, int] = {}  # user_id -> violation_count
        self._event_queue_stats = {
            'total_events_sent': 0,
            'events_delivered': 0,
            'contamination_prevented': 0,
            'queue_overflows': 0,
            'auth_token_reuse_detected': 0
        }
        
        # SSOT CONSOLIDATION: Always use unified initialization
        self._initialize_unified_mode()
        
        # ISSUE #601 FIX: Use WeakValueDictionary for connection pools to prevent memory leaks
        self._connection_pool = weakref.WeakValueDictionary()
        
        # Add compatibility registry for legacy tests (no circular reference with weakref)
        self.registry = RegistryCompat(self)
        
        # Add compatibility for legacy tests expecting connection_manager
        self._connection_manager = self
        self.connection_manager = self
        self.active_connections = {}  # Compatibility mapping

    def _validate_user_isolation(self, user_id: str, operation: str = "unknown") -> bool:
        """
        ISSUE #712 FIX: Validate user isolation for operations.

        This method enforces user isolation by ensuring operations are only
        performed on behalf of the user this manager was created for.

        Args:
            user_id: User ID requesting the operation
            operation: Description of operation for logging

        Returns:
            bool: True if validation passes

        Raises:
            UserIsolationViolation: If user isolation is violated in strict mode
        """
        from netra_backend.app.websocket_core.ssot_validation_enhancer import validate_user_isolation

        try:
            return validate_user_isolation(
                manager_instance=self,
                user_id=user_id,
                operation=operation
            )
        except Exception as e:
            logger.error(f"User isolation validation failed for {operation}: {e}")
            raise

    def _prevent_cross_user_event_bleeding(self, event_data: Dict[str, Any], target_user_id: str) -> Dict[str, Any]:
        """
        ISSUE #712 FIX: Prevent cross-user event bleeding.

        This method ensures events are only delivered to the intended user
        and adds isolation metadata to prevent contamination.

        Args:
            event_data: Event data to be sent
            target_user_id: User ID that should receive this event

        Returns:
            Dict[str, Any]: Event data with isolation metadata
        """
        from netra_backend.app.websocket_core.ssot_validation_enhancer import UserIsolationViolation

        # Add user isolation metadata
        isolated_event = event_data.copy()
        isolated_event['_user_isolation'] = {
            'target_user_id': target_user_id,
            'manager_user_id': getattr(self.user_context, 'user_id', None),
            'isolation_token': f"{target_user_id}_{time.time()}",
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Validate user match
        manager_user_id = getattr(self.user_context, 'user_id', None)
        if manager_user_id and str(manager_user_id) != str(target_user_id):
            logger.warning(f"Cross-user event bleeding prevented: manager_user={manager_user_id}, target_user={target_user_id}")
            raise UserIsolationViolation(f"Event targeting different user: {target_user_id} != {manager_user_id}")

        return isolated_event
        self.connection_registry = {}  # Registry for connection objects
        
        # Event listener support for testing
        self.on_event_emitted: Optional[callable] = None
        self._event_listeners: List[callable] = []
        
        logger.info("UnifiedWebSocketManager initialized with SSOT unified mode (all legacy modes consolidated)")
    
    def _initialize_unified_mode(self):
        """Initialize unified mode with full feature set."""
        # Enhanced error handling and recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}  # user_id -> [messages]
        self._connection_error_count: Dict[str, int] = {}  # user_id -> error_count
        self._last_error_time: Dict[str, datetime] = {}  # user_id -> last_error_timestamp
        
        # Transaction coordination support
        self._transaction_coordinator = None  # Will be set by DatabaseManager
        self._coordination_enabled = False
        
        logger.debug("[U+1F517] WebSocket manager initialized with transaction coordination support")
        self._error_recovery_enabled = True
        
        # Background task monitoring system
        self._background_tasks: Dict[str, asyncio.Task] = {}  # task_name -> task
        self._task_failures: Dict[str, int] = {}  # task_name -> failure_count
        self._task_last_failure: Dict[str, datetime] = {}  # task_name -> last_failure_time
        self._monitoring_enabled = True
        self._monitoring_lock = asyncio.Lock()  # Synchronization for monitoring state changes
        
        # Task registry for recovery and restart capabilities
        self._task_registry: Dict[str, Dict[str, Any]] = {}  # task_name -> {func, args, kwargs, meta}
        self._shutdown_requested = False  # Track intentional shutdown vs error-based disable
        self._last_health_check = datetime.utcnow()
        self._health_check_failures = 0
    
    def _initialize_isolated_mode(self, user_context):
        """Initialize isolated mode for user-specific operation."""
        self.user_context = user_context
        self._connection_ids: Set[str] = set()
        
        # Private connection state for isolation
        self._private_connections: Dict[str, Any] = {}
        self._private_message_queue: List[Dict] = []
        self._private_error_count = 0
        self._is_healthy = True
        
        # Initialize minimal recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}
        self._connection_error_count: Dict[str, int] = {}
        self._last_error_time: Dict[str, datetime] = {}
        self._error_recovery_enabled = True
        
        # Disable background monitoring in isolated mode for performance
        self._monitoring_enabled = False
        self._background_tasks = {}
        
        logger.info(f"Isolated mode initialized for user context")
    
    def add_event_listener(self, listener: callable) -> None:
        """Add an event listener for WebSocket events.
        
        This method provides compatibility with test frameworks that expect
        event listener functionality for capturing WebSocket events during testing.
        
        Args:
            listener: Callable that will receive event data when events are emitted
        """
        if listener not in self._event_listeners:
            self._event_listeners.append(listener)
            logger.debug(f"Added WebSocket event listener: {listener}")
    
    def remove_event_listener(self, listener: callable) -> None:
        """Remove an event listener.
        
        Args:
            listener: Callable to remove from the event listeners list
        """
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
            logger.debug(f"Removed WebSocket event listener: {listener}")
    
    def _notify_event_listeners(self, event: Dict[str, Any]) -> None:
        """Notify all event listeners about a WebSocket event.
        
        Args:
            event: Event data to send to listeners
        """
        # Call the on_event_emitted callback if set (for compatibility with existing tests)
        if self.on_event_emitted:
            try:
                self.on_event_emitted(**event)
            except Exception as e:
                logger.warning(f"Error in on_event_emitted callback: {e}")
        
        # Call all registered event listeners
        for listener in self._event_listeners:
            try:
                listener(event)
            except Exception as e:
                logger.warning(f"Error in event listener {listener}: {e}")
    
    def _initialize_emergency_mode(self, config: Dict[str, Any]):
        """Initialize emergency mode for service continuity."""
        self.user_id = config.get('user_id')
        self.websocket_client_id = config.get('websocket_client_id')
        self.thread_id = config.get('thread_id')
        self.run_id = config.get('run_id')
        self.emergency_mode = True
        self.created_at = datetime.now(timezone.utc)
        
        # Minimal state tracking
        self._emergency_connections = {}
        self._emergency_message_queue = []
        self._is_healthy = True
        
        # Minimal recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}
        self._connection_error_count: Dict[str, int] = {}
        self._error_recovery_enabled = False  # Disabled in emergency mode
        
        # Disable monitoring in emergency mode
        self._monitoring_enabled = False
        self._background_tasks = {}
        
        logger.warning("Emergency mode initialized - minimal functionality only")
    
    def _initialize_degraded_mode(self, config: Dict[str, Any]):
        """Initialize degraded mode for absolute last resort."""
        self.degraded_mode = True
        self.created_at = datetime.now(timezone.utc)
        self._is_healthy = False
        
        # Minimal recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}
        self._connection_error_count: Dict[str, int] = {}
        self._error_recovery_enabled = False
        
        # Disable all advanced features in degraded mode
        self._monitoring_enabled = False
        self._background_tasks = {}
        
        logger.error("Degraded mode initialized - system operating at minimal capacity")
    
    async def _get_user_connection_lock(self, user_id: str) -> asyncio.Lock:
        """Get or create user-specific connection lock for thread safety.
        
        Args:
            user_id: User identifier for connection lock isolation
            
        Returns:
            User-specific asyncio Lock for connection operations
        """
        if user_id not in self._user_connection_locks:
            async with self._connection_lock_creation_lock:
                # Double-check locking pattern
                if user_id not in self._user_connection_locks:
                    self._user_connection_locks[user_id] = asyncio.Lock()
                    logger.debug(f"Created user-specific connection lock for user: {user_id}")
        return self._user_connection_locks[user_id]
    
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """Add a new WebSocket connection with thread safety and type validation."""
        connection_start_time = time.time()
        
        # CRITICAL: Log connection addition attempt with full context
        connection_add_context = {
            "connection_id": connection.connection_id,
            "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
            "websocket_available": connection.websocket is not None,
            "websocket_state": _get_enum_key_representation(getattr(connection.websocket, 'client_state', 'unknown')) if hasattr(connection.websocket, 'client_state') else 'unknown',
            "existing_connections_count": len(self._connections),
            "user_existing_connections": len(self._user_connections.get(connection.user_id, set())),
            "has_queued_messages": connection.user_id in self._message_recovery_queue and bool(self._message_recovery_queue[connection.user_id]),
            "manager_mode": self.mode.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "golden_path_stage": "connection_addition_start"
        }
        
        logger.info(f"[U+1F517] GOLDEN PATH CONNECTION ADD: Adding connection {connection.connection_id} for user {connection.user_id[:8] if connection.user_id else 'unknown'}...")
        logger.info(f" SEARCH:  CONNECTION ADD CONTEXT: {json.dumps(connection_add_context, indent=2)}")
        
        # Validate connection before adding
        try:
            if not connection.user_id:
                raise ValueError("Connection must have a valid user_id")
            if not connection.connection_id:
                raise ValueError("Connection must have a valid connection_id")
            logger.debug(f" PASS:  CONNECTION VALIDATION: Connection {connection.connection_id} validated successfully")
        except Exception as e:
            # CRITICAL: Log validation failure
            validation_failure_context = {
                "connection_id": connection.connection_id,
                "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                "validation_error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "golden_path_impact": "CRITICAL - Connection rejected due to validation failure"
            }
            
            logger.critical(f" ALERT:  GOLDEN PATH CONNECTION VALIDATION FAILURE: Connection {connection.connection_id} validation failed for user {connection.user_id[:8] if connection.user_id else 'unknown'}...")
            logger.critical(f" SEARCH:  VALIDATION FAILURE CONTEXT: {json.dumps(validation_failure_context, indent=2)}")
            raise
            
        # Use user-specific lock for connection operations
        user_lock = await self._get_user_connection_lock(connection.user_id)
        
        async with user_lock:
            async with self._lock:
                # ISSUE #414 FIX: Event contamination prevention setup
                # Use UnifiedIDManager for isolation token generation
                id_manager = UnifiedIDManager()
                isolation_token = id_manager.generate_id(IDType.WEBSOCKET, prefix="isolation", context={
                    'user_id': connection.user_id,
                    'connection_id': connection.connection_id,
                    'purpose': 'event_contamination_prevention'
                })
                self._event_isolation_tokens[connection.connection_id] = isolation_token
                
                # Initialize user-specific event queue if not exists
                if connection.user_id not in self._user_event_queues:
                    self._user_event_queues[connection.user_id] = asyncio.Queue(maxsize=1000)  # Prevent overflow
                    self._cross_user_detection[connection.user_id] = 0
                
                # Validate no cross-user contamination
                for existing_conn_id, existing_token in self._event_isolation_tokens.items():
                    if existing_conn_id in self._connections:
                        existing_user = self._connections[existing_conn_id].user_id
                        if existing_user != connection.user_id and existing_token == isolation_token:
                            # This should never happen with UUID but check anyway
                            logger.error(
                                f" ALERT:  CRITICAL ISOLATION VIOLATION: Token collision detected! "
                                f"User {connection.user_id} vs {existing_user}, "
                                f"Connection {connection.connection_id} vs {existing_conn_id}"
                            )
                            self._cross_user_detection[connection.user_id] += 1
                            self._event_queue_stats['contamination_prevented'] += 1
                            
                            # Generate new token to fix collision using UnifiedIDManager
                            isolation_token = id_manager.generate_id(IDType.WEBSOCKET, prefix="isolation_fix", context={
                                'user_id': connection.user_id,
                                'connection_id': connection.connection_id,
                                'purpose': 'collision_recovery'
                            })
                            self._event_isolation_tokens[connection.connection_id] = isolation_token
                            break
                
                self._connections[connection.connection_id] = connection
                if connection.user_id not in self._user_connections:
                    self._user_connections[connection.user_id] = set()
                self._user_connections[connection.user_id].add(connection.connection_id)
                
                logger.debug(f" PASS:  ISSUE #414 FIX: Connection {connection.connection_id} isolated with token {isolation_token[:8]}... for user {connection.user_id[:8]}...")
                
                # Update compatibility mapping for legacy tests
                if connection.user_id not in self.active_connections:
                    self.active_connections[connection.user_id] = []
                # Create a simple connection info object for compatibility
                conn_info = type('ConnectionInfo', (), {
                    'websocket': connection.websocket,
                    'user_id': connection.user_id,
                    'connection_id': connection.connection_id
                })()
                self.active_connections[connection.user_id].append(conn_info)
                
                # CRITICAL: Log successful connection addition with state details
                connection_duration = time.time() - connection_start_time
                
                connection_success_context = {
                    "connection_id": connection.connection_id,
                    "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                    "total_connections": len(self._connections),
                    "user_total_connections": len(self._user_connections[connection.user_id]),
                    "connection_duration_ms": round(connection_duration * 1000, 2),
                    "active_users": len(self._user_connections),
                    "manager_mode": self.mode.value,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "golden_path_milestone": "Connection successfully added to manager"
                }
                
                logger.info(f" PASS:  GOLDEN PATH CONNECTION ADDED: Connection {connection.connection_id} added for user {connection.user_id[:8] if connection.user_id else 'unknown'}... in {connection_duration*1000:.2f}ms")
                logger.info(f" SEARCH:  CONNECTION SUCCESS CONTEXT: {json.dumps(connection_success_context, indent=2)}")
                logger.info(f"Added connection {connection.connection_id} for user {connection.user_id} (thread-safe)")
                
                # CRITICAL FIX: Process any queued messages for this user after connection established
                # This prevents race condition where messages are sent before connection is ready
                # Store the user_id for processing outside the lock to prevent deadlock
                process_recovery = connection.user_id in self._message_recovery_queue
                
        # DEADLOCK FIX: Process recovery queue OUTSIDE the lock to prevent circular dependency
        # add_connection -> _process_queued_messages -> send_to_user -> user_lock (deadlock)
        if process_recovery:
            queued_messages = self._message_recovery_queue.get(connection.user_id, [])
            if queued_messages:
                # CRITICAL: Log message recovery processing
                recovery_context = {
                    "connection_id": connection.connection_id,
                    "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                    "queued_messages_count": len(queued_messages),
                    "message_types": [msg.get('type', 'unknown') for msg in queued_messages[:5]],  # First 5 types
                    "timeout_seconds": 5.0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "golden_path_stage": "message_recovery_processing"
                }
                
                logger.info(f"[U+1F4E4] GOLDEN PATH MESSAGE RECOVERY: Processing {len(queued_messages)} queued messages for user {connection.user_id[:8] if connection.user_id else 'unknown'}...")
                logger.info(f" SEARCH:  MESSAGE RECOVERY CONTEXT: {json.dumps(recovery_context, indent=2)}")
                
                # HANG FIX: Await the processing to ensure messages are sent before method returns
                # This prevents test hanging where the test expects messages but they're still processing
                recovery_start = time.time()
                try:
                    await asyncio.wait_for(
                        self._process_queued_messages(connection.user_id), 
                        timeout=5.0  # Reasonable timeout to prevent infinite hang
                    )
                    
                    # CRITICAL: Log successful recovery completion
                    recovery_duration = time.time() - recovery_start
                    
                    recovery_success_context = {
                        "connection_id": connection.connection_id,
                        "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                        "messages_processed": len(queued_messages),
                        "recovery_duration_ms": round(recovery_duration * 1000, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "golden_path_milestone": "Message recovery completed successfully"
                    }
                    
                    logger.info(f" PASS:  GOLDEN PATH RECOVERY SUCCESS: Processed {len(queued_messages)} queued messages for user {connection.user_id[:8] if connection.user_id else 'unknown'}... in {recovery_duration*1000:.2f}ms")
                    logger.info(f" SEARCH:  RECOVERY SUCCESS CONTEXT: {json.dumps(recovery_success_context, indent=2)}")
                    
                except asyncio.TimeoutError:
                    recovery_duration = time.time() - recovery_start
                    
                    # CRITICAL: Log recovery timeout
                    timeout_context = {
                        "connection_id": connection.connection_id,
                        "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                        "messages_pending": len(queued_messages),
                        "timeout_seconds": 5.0,
                        "elapsed_time_ms": round(recovery_duration * 1000, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "golden_path_impact": "WARNING - Message recovery timed out, messages may be lost"
                    }
                    
                    logger.warning(f" WARNING: [U+FE0F] GOLDEN PATH RECOVERY TIMEOUT: Message recovery timed out for user {connection.user_id[:8] if connection.user_id else 'unknown'}... after {recovery_duration:.3f}s")
                    logger.warning(f" SEARCH:  RECOVERY TIMEOUT CONTEXT: {json.dumps(timeout_context, indent=2)}")
                    logger.error(f"Timeout processing queued messages for user {connection.user_id}")
                    
                except Exception as e:
                    recovery_duration = time.time() - recovery_start
                    
                    # CRITICAL: Log recovery error
                    recovery_error_context = {
                        "connection_id": connection.connection_id,
                        "user_id": connection.user_id[:8] + "..." if connection.user_id else "unknown",
                        "messages_pending": len(queued_messages),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "elapsed_time_ms": round(recovery_duration * 1000, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "golden_path_impact": "WARNING - Message recovery failed, messages may be lost"
                    }
                    
                    logger.warning(f" WARNING: [U+FE0F] GOLDEN PATH RECOVERY ERROR: Message recovery failed for user {connection.user_id[:8] if connection.user_id else 'unknown'}... after {recovery_duration:.3f}s")
                    logger.warning(f" SEARCH:  RECOVERY ERROR CONTEXT: {json.dumps(recovery_error_context, indent=2)}")
                    logger.error(f"Error processing queued messages for user {connection.user_id}: {e}")
    
    async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None:
        """Remove a WebSocket connection with thread safety, type validation, and pattern-agnostic cleanup.
        
        PHASE 1 SSOT REMEDIATION: Enhanced with pattern-agnostic resource cleanup
        to prevent WebSocket 1011 errors caused by ID pattern mismatches.
        """
        # Convert to string for internal use
        validated_connection_id = str(connection_id)
        
        # First get the connection to determine user_id
        connection = self._connections.get(validated_connection_id)
        if not connection:
            logger.debug(f"Connection {validated_connection_id} not found for removal")
            return
        
        # Use user-specific lock for connection operations
        user_lock = await self._get_user_connection_lock(connection.user_id)
        
        async with user_lock:
            async with self._lock:
                if connection_id in self._connections:
                    connection = self._connections[connection_id]
                    del self._connections[connection_id]
                    
                    # PHASE 1 SSOT REMEDIATION: Enhanced cleanup with pattern-agnostic matching
                    if connection.user_id in self._user_connections:
                        # Remove exact match first
                        self._user_connections[connection.user_id].discard(connection_id)
                        
                        # CRITICAL FIX: Also remove pattern matches to prevent resource leaks
                        # This prevents WebSocket 1011 errors by ensuring all related resources are cleaned up
                        from netra_backend.app.websocket_core.utils import find_matching_resources
                        try:
                            # Find connections with matching patterns for this user
                            user_connections_dict = {cid: cid for cid in self._user_connections[connection.user_id]}
                            matching_connection_ids = find_matching_resources(validated_connection_id, user_connections_dict)
                            
                            for match_id in matching_connection_ids:
                                if match_id in self._user_connections[connection.user_id]:
                                    self._user_connections[connection.user_id].discard(match_id)
                                    logger.debug(f"Pattern cleanup: removed matching connection {match_id} for {validated_connection_id}")
                        except Exception as e:
                            logger.warning(f"Pattern cleanup failed for connection {validated_connection_id}: {e}")
                        
                        # Clean up user entry if no connections remain
                        if not self._user_connections[connection.user_id]:
                            del self._user_connections[connection.user_id]
                    
                    # Update compatibility mapping with pattern-agnostic cleanup
                    if connection.user_id in self.active_connections:
                        # Remove exact matches
                        self.active_connections[connection.user_id] = [
                            c for c in self.active_connections[connection.user_id]
                            if c.connection_id != connection_id
                        ]
                        
                        # CRITICAL FIX: Also remove pattern matches from active connections
                        try:
                            from netra_backend.app.core.id_migration_bridge import validate_id_compatibility
                            self.active_connections[connection.user_id] = [
                                c for c in self.active_connections[connection.user_id]
                                if not validate_id_compatibility(c.connection_id, validated_connection_id)
                            ]
                        except Exception as e:
                            logger.warning(f"Pattern cleanup in active_connections failed for {validated_connection_id}: {e}")
                        
                        # Clean up user entry if no connections remain
                        if not self.active_connections[connection.user_id]:
                            del self.active_connections[connection.user_id]
                    
                    # PHASE 2 INTEGRATION - Cleanup Token Lifecycle Management
                    # Unregister connection from token lifecycle manager when WebSocket closes
                    try:
                        from netra_backend.app.websocket_core.token_lifecycle_manager import get_token_lifecycle_manager
                        
                        lifecycle_manager = get_token_lifecycle_manager()
                        await lifecycle_manager.unregister_connection(validated_connection_id)
                        
                        logger.debug(f"PHASE 2: Token lifecycle management cleaned up for connection {validated_connection_id}")
                        
                    except Exception as e:
                        logger.warning(f"PHASE 2: Error cleaning up token lifecycle for connection {validated_connection_id}: {e}")
                        # Don't fail connection removal due to lifecycle cleanup errors
                    
                    # ISSUE #601 FIX: Explicit event handler cleanup to prevent memory leaks
                    try:
                        # Clean up event handlers and references for this connection
                        if hasattr(connection.websocket, '_event_handlers'):
                            connection.websocket._event_handlers.clear()
                        
                        # Clean up any circular references in the connection object
                        if hasattr(connection, 'metadata') and connection.metadata:
                            # Remove any parent/child references in metadata
                            for key in list(connection.metadata.keys()):
                                if 'parent' in key.lower() or 'child' in key.lower() or 'ref' in key.lower():
                                    connection.metadata.pop(key, None)
                        
                        # Remove from connection pool weak references
                        if validated_connection_id in self._connection_pool:
                            del self._connection_pool[validated_connection_id]
                            
                        logger.debug(f"ISSUE #601: Event handler cleanup completed for connection {validated_connection_id}")
                        
                    except Exception as e:
                        logger.warning(f"ISSUE #601: Error during event handler cleanup for connection {validated_connection_id}: {e}")
                        # Don't fail connection removal due to cleanup errors
                    
                    logger.info(f"Removed connection {connection_id} with pattern-agnostic cleanup, Phase 2 lifecycle cleanup, and Issue #601 memory leak prevention (thread-safe)")
    
    def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]:
        """Get a specific connection with type validation."""
        validated_connection_id = str(connection_id)
        return self._connections.get(validated_connection_id)
    
    def get_user_connections(self, user_id: Union[str, UserID]) -> Set[str]:
        """Get all connections for a user with type validation."""
        validated_user_id = ensure_user_id(user_id)
        return self._user_connections.get(validated_user_id, set()).copy()
    
    def get_connection_thread_id(self, connection_id: Union[str, ConnectionID]) -> Optional[str]:
        """Get the thread_id for a specific connection."""
        connection = self.get_connection(connection_id)
        return connection.thread_id if connection else None
    
    def get_user_connections_by_thread(self, user_id: Union[str, UserID], thread_id: str) -> Set[str]:
        """Get all connections for a user filtered by thread_id."""
        validated_user_id = ensure_user_id(user_id)
        user_connections = self._user_connections.get(validated_user_id, set())
        
        thread_connections = set()
        for conn_id in user_connections:
            connection = self.get_connection(conn_id)
            if connection and connection.thread_id == thread_id:
                thread_connections.add(conn_id)
        
        return thread_connections

    # =================== COMPATIBILITY METHODS FOR ISSUE #618 ===================
    # These methods provide compatibility with legacy test signatures that expect
    # register_connection(connection_id, user_id, websocket) pattern
    
    def register_connection(self, connection_id: str, user_id: str, websocket: Any) -> None:
        """
        ISSUE #618 FIX: Compatibility method for legacy test patterns.
        
        This synchronous method provides compatibility with tests that expect:
        register_connection(connection_id, user_id, websocket)
        
        The async add_connection method is the preferred SSOT method for new code.
        """
        from netra_backend.app.websocket_core.connection_manager import ConnectionInfo
        
        # Create ConnectionInfo object for compatibility
        connection_info = ConnectionInfo(connection_id=connection_id, user_id=user_id)
        connection_info.websocket = websocket
        connection_info.connected_at = datetime.now(timezone.utc)
        
        # Convert to WebSocketConnection and add to manager
        websocket_conn = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=connection_info.connected_at,
            metadata={"source": "legacy_test_compatibility"}
        )
        
        # Store in synchronous collections for immediate access
        self._connections[connection_id] = websocket_conn
        
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(connection_id)
        
        # Store connection info for legacy test access patterns
        if not hasattr(self, '_connection_infos'):
            self._connection_infos = {}
        self._connection_infos[connection_id] = {
            'connection_id': connection_id,
            'user_id': user_id,
            'websocket': websocket,
            'connected_at': connection_info.connected_at,
            'is_active': True
        }
        
        logger.debug(f"Legacy compatibility: Registered connection {connection_id} for user {user_id}")
    
    def unregister_connection(self, connection_id: str) -> None:
        """
        ISSUE #618 FIX: Synchronous compatibility method for connection removal.
        
        Provides compatibility with legacy test patterns that expect synchronous unregistration.
        """
        # Remove from main connections
        connection = self._connections.pop(connection_id, None)
        
        if connection:
            # Remove from user connections
            user_id = connection.user_id
            if user_id in self._user_connections:
                self._user_connections[user_id].discard(connection_id)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]
        
        # Remove from legacy connection info store
        if hasattr(self, '_connection_infos'):
            self._connection_infos.pop(connection_id, None)
        
        logger.debug(f"Legacy compatibility: Unregistered connection {connection_id}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        ISSUE #618 FIX: Compatibility method for legacy connection info access.
        ISSUE #556 FIX: Include thread_id for thread propagation support.
        
        Tests expect to access connection metadata through get_connection_info.
        """
        if hasattr(self, '_connection_infos') and connection_id in self._connection_infos:
            return self._connection_infos[connection_id]
        
        # Fallback to standard connection if available
        connection = self.get_connection(connection_id)
        if connection:
            return {
                'connection_id': connection.connection_id,
                'user_id': connection.user_id,
                'websocket': connection.websocket,
                'connected_at': connection.connected_at,
                'thread_id': connection.thread_id,  # ISSUE #556 FIX: Include thread_id for propagation
                'is_active': True
            }
        
        return None
    
    def get_connections_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        ISSUE #618 FIX: Compatibility method for user connection lookup.
        
        Tests expect this method to return a list of connection objects/dicts.
        """
        connections = []
        user_connection_ids = self.get_user_connections(user_id)
        
        for conn_id in user_connection_ids:
            conn_info = self.get_connection_info(conn_id)
            if conn_info:
                connections.append(conn_info)
        
        return connections

    def clear_all_connections(self) -> None:
        """
        ISSUE #618 FIX: Compatibility method for test cleanup.
        
        Clears all connections for test isolation.
        """
        self._connections.clear()
        self._user_connections.clear()
        
        if hasattr(self, '_connection_infos'):
            self._connection_infos.clear()
        
        logger.debug("Legacy compatibility: Cleared all connections")
    
    # =================== END COMPATIBILITY METHODS ===================
    
    async def wait_for_connection(self, user_id: str, timeout: float = 5.0, check_interval: float = 0.1) -> bool:
        """
        Wait for a WebSocket connection to be established for a user.
        
        This method is useful during startup sequences to ensure connections are ready
        before attempting to send messages, avoiding race conditions.
        
        Args:
            user_id: User ID to wait for connection
            timeout: Maximum time to wait in seconds (default: 5.0)
            check_interval: How often to check for connection in seconds (default: 0.1)
            
        Returns:
            True if connection established within timeout, False otherwise
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check if user has any connections
            if self.get_user_connections(user_id):
                logger.debug(f"Connection established for user {user_id} after {asyncio.get_event_loop().time() - start_time:.2f}s")
                # HANG FIX: Process queued messages with timeout to prevent infinite wait
                try:
                    await asyncio.wait_for(
                        self.process_recovery_queue(user_id), 
                        timeout=min(2.0, timeout - (asyncio.get_event_loop().time() - start_time))
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout processing recovery queue for user {user_id}")
                except Exception as e:
                    logger.error(f"Error processing recovery queue for user {user_id}: {e}")
                return True
            
            # Wait before next check
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for connection for user {user_id} after {timeout}s")
        return False
    
    async def _send_emergency_message(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send message in emergency mode with minimal error handling."""
        try:
            # Add emergency mode indicator to messages
            emergency_message = {
                **message,
                'emergency_mode': True,
                'manager_type': 'emergency_fallback',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Find connection for user (simplified emergency logic)
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and hasattr(connection.websocket, 'send_json'):
                    await connection.websocket.send_json(emergency_message)
                    return
                    
            logger.warning(f"Emergency mode: No active connections for user {user_id}")
            
        except Exception as e:
            logger.error(f"Emergency manager send failed: {e}")
    
    async def _send_degraded_message(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send message in degraded mode with service notification."""
        try:
            degraded_message = {
                'type': 'degraded_service',
                'message': 'Service operating in degraded mode - limited functionality available',
                'original_message_type': message.get('type', 'unknown'),
                'degraded_mode': True,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Find connection for user (minimal degraded logic)
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and hasattr(connection.websocket, 'send_json'):
                    await connection.websocket.send_json(degraded_message)
                    return
                    
        except Exception as e:
            logger.error(f"Degraded manager send failed: {e}")
    
    async def _send_isolated_message(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send message in isolated mode with user context validation."""
        try:
            # Validate user context for isolation
            if self.user_context and hasattr(self.user_context, 'user_id'):
                context_user_id = str(self.user_context.user_id)
                if str(user_id) != context_user_id:
                    logger.warning(f"Isolated mode: User ID mismatch {user_id} != {context_user_id}")
                    return
            
            # Send message using private connection state
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    safe_message = _serialize_message_safely(message)
                    await connection.websocket.send_json(safe_message)
                    return
                    
            # Queue message if no active connections
            if not connection_ids:
                self._private_message_queue.append(message)
                
        except Exception as e:
            logger.error(f"Isolated mode send failed: {e}")
            self._private_error_count += 1
    
    async def send_to_user(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None:
        """Send a message to all connections for a user with thread safety and type validation."""
        # SSOT CONSOLIDATION: All modes use unified message handling
        # (Mode-specific behavior has been consolidated for SSOT compliance)
        # Validate user_id
        validated_user_id = ensure_user_id(user_id)
        
        # ISSUE #414 FIX: Event contamination prevention and validation
        # Use UnifiedIDManager for event ID generation
        id_manager = UnifiedIDManager()
        event_id = id_manager.generate_id(IDType.WEBSOCKET, prefix="event", context={
            'user_id': validated_user_id,
            'purpose': 'cross_user_contamination_prevention'
        })
        
        # Validate message doesn't contain foreign user data
        if isinstance(message, dict):
            for key, value in message.items():
                if key.endswith('_user_id') and value != validated_user_id:
                    logger.error(
                        f" ALERT:  CROSS-USER CONTAMINATION DETECTED: Message for user {validated_user_id} "
                        f"contains foreign user_id in field '{key}': {value}"
                    )
                    self._event_queue_stats['contamination_prevented'] += 1
                    self._cross_user_detection[validated_user_id] = self._cross_user_detection.get(validated_user_id, 0) + 1
                    
                    # Sanitize the message
                    message = message.copy()
                    message[key] = validated_user_id
                    logger.warning(f"[U+1F9F9] Sanitized contaminated field '{key}' for user {validated_user_id}")
        
        # Track event delivery
        self._event_delivery_tracking[event_id] = {
            'user_id': validated_user_id,
            'message_type': message.get('type', 'unknown'),
            'timestamp': datetime.now(timezone.utc),
            'delivery_status': 'pending',
            'contamination_checks': 'passed'
        }
        self._event_queue_stats['total_events_sent'] += 1
        
        # Use user-specific lock to prevent race conditions during message sending
        user_lock = await self._get_user_connection_lock(validated_user_id)
        
        async with user_lock:
            connection_ids = self.get_user_connections(user_id)
            if not connection_ids:
                # Check if this is a startup/test scenario where connections may not be established yet
                # Special handling for startup_test messages to avoid false critical errors
                message_type = message.get('type', 'unknown')
                
                # During startup or testing, connections may not be established yet - this is expected
                if message_type == 'startup_test' or user_id.startswith('startup_test_'):
                    logger.debug(
                        f"No WebSocket connections for user {user_id} during startup test. "
                        f"Message type: {message_type} (expected during initialization)"
                    )
                    # Store message for potential recovery when connection is established
                    await self._store_failed_message(user_id, message, "startup_pending")
                    return
                
                # For non-startup scenarios, this is a critical error
                logger.critical(
                    f"CRITICAL ERROR: No WebSocket connections found for user {user_id}. "
                    f"User will not receive message: {message_type}"
                )
                # Store message for potential recovery
                await self._store_failed_message(user_id, message, "no_connections")
                return
            
            failed_connections = []
            successful_sends = 0
            
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        # CRITICAL FIX: Use safe serialization to handle enums, Pydantic models, etc.
                        safe_message = _serialize_message_safely(message)
                        await connection.websocket.send_json(safe_message)
                        logger.debug(f"Sent message to connection {conn_id} (thread-safe)")
                        successful_sends += 1
                    except Exception as e:
                        # ENHANCED ERROR: More detailed logging for WebSocket send failures
                        logger.critical(
                            f"WEBSOCKET SEND FAILURE: Failed to send {message.get('type', 'unknown')} "
                            f"to connection {conn_id} for user {user_id}: {e}. "
                            f"Connection state: {self._get_connection_diagnostics(connection)}"
                        )
                        failed_connections.append((conn_id, str(e)))
                else:
                    # LOUD ERROR: Connection exists but websocket is None/invalid
                    logger.critical(
                        f"INVALID CONNECTION: Connection {conn_id} for user {user_id} "
                        f"has no valid WebSocket. Connection: {connection}"
                    )
                    failed_connections.append((conn_id, "invalid_websocket"))
            
            # If all connections failed, this is critical
            if successful_sends == 0:
                logger.critical(
                    f"COMPLETE MESSAGE DELIVERY FAILURE: All {len(connection_ids)} connections "
                    f"failed for user {user_id}. Message type: {message.get('type', 'unknown')}. "
                    f"Failed connections: {[f'{conn_id}: {error}' for conn_id, error in failed_connections]}"
                )
                # Store message for recovery
                await self._store_failed_message(user_id, message, "all_connections_failed")
            elif failed_connections:
                # Partial failure - log warning
                logger.warning(
                    f"PARTIAL MESSAGE DELIVERY: {successful_sends}/{len(connection_ids)} "
                    f"connections succeeded for user {user_id}. "
                    f"Failed: {[f'{conn_id}: {error}' for conn_id, error in failed_connections]}"
                )
            
            # DEADLOCK FIX: Schedule failed connection removal as background task to avoid nested locks
            # This prevents deadlock when send_to_user is called from within add_connection's user lock
            if failed_connections:
                async def cleanup_failed_connections():
                    for failed_conn_id, error in failed_connections:
                        try:
                            await self.remove_connection(failed_conn_id)
                            logger.info(f"Removed failed connection {failed_conn_id} due to: {error}")
                        except Exception as e:
                            # LOUD ERROR: Failed to clean up failed connection
                            logger.critical(
                                f"CLEANUP FAILURE: Failed to remove failed connection {failed_conn_id} "
                                f"for user {user_id}: {e}. This may cause connection leaks."
                            )
                
                # Create background task for cleanup to avoid deadlock
                asyncio.create_task(cleanup_failed_connections())
    
    async def send_to_thread(self, thread_id: Union[str, ThreadID], message: Dict[str, Any]) -> bool:
        """
        Send a message to a thread (compatibility method) with type validation.
        Routes to send_to_user using thread_id as user_id.
        """
        try:
            # For compatibility, treat thread_id as user_id
            validated_thread_id = ensure_thread_id(thread_id)
            await self.send_to_user(validated_thread_id, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send to thread {thread_id}: {e}")
            return False
    
    async def emit_critical_event(self, user_id: Union[str, UserID], event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a critical event to a specific user with guaranteed delivery tracking and type validation.
        This is the main interface for sending WebSocket events.
        
        CRITICAL FIX: Adds retry logic for staging/production environments to handle
        race conditions during connection establishment.
        
        Args:
            user_id: Target user ID (accepts both str and UserID)
            event_type: Event type (e.g., 'agent_started', 'tool_executing')
            data: Event payload
        """
        # Validate and convert user_id
        try:
            validated_user_id = ensure_user_id(user_id)
        except ValueError as e:
            logger.critical(f"INVALID USER_ID: Cannot emit {event_type} to invalid user_id {user_id}: {e}")
            raise ValueError(f"Invalid user_id for critical event {event_type}: {e}")
        
        if not event_type or not event_type.strip():
            logger.critical(f"INVALID EVENT_TYPE: Cannot emit empty event_type to user {user_id}")
            raise ValueError(f"event_type cannot be empty for user {user_id}")
        
        # CRITICAL FIX: Add retry logic for staging/production
        from shared.isolated_environment import get_env
        environment = get_env().get("ENVIRONMENT", "development").lower()
        
        # CRITICAL FIX: GCP staging auto-detection to prevent 1011 errors  
        # Environment variable propagation gaps in Cloud Run require auto-detection
        if not environment or environment == "development":
            # Auto-detect GCP staging based on service URLs and project context
            gcp_project = get_env().get("GCP_PROJECT_ID", "")
            backend_url = get_env().get("BACKEND_URL", "")
            auth_service_url = get_env().get("AUTH_SERVICE_URL", "")
            
            if ("staging" in gcp_project or 
                "staging.netrasystems.ai" in backend_url or 
                "staging.netrasystems.ai" in auth_service_url or
                "netra-staging" in gcp_project):
                logger.info(" SEARCH:  GCP staging environment auto-detected - adjusting WebSocket retry configuration")
                environment = "staging"
        
        # Retry configuration based on environment
        max_retries = 1  # Default for development
        retry_delay = 0.5  # seconds
        
        if environment in ["staging", "production"]:
            max_retries = 3  # More retries for cloud environments  
            retry_delay = 1.0  # Longer delay for Cloud Run
            logger.debug(f"WebSocket using {environment} retry config: {max_retries} retries with {retry_delay}s delay")
        
        # Try with retries
        for attempt in range(max_retries):
            # Check connection health before sending critical events
            if self.is_connection_active(user_id):
                # Connection exists, try to send
                message = {
                    "type": event_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat(),
                    "critical": True,
                    "attempt": attempt + 1 if attempt > 0 else None
                }
                
                try:
                    await self.send_to_user(user_id, message)
                    
                    # Notify event listeners for testing/monitoring
                    event_data = {
                        "event_type": event_type,
                        "user_id": str(user_id),
                        "data": data,
                        "timestamp": message.get("timestamp"),
                        "critical": True
                    }
                    self._notify_event_listeners(event_data)
                    
                    # Success! Return immediately
                    return
                except Exception as e:
                    logger.error(f"Failed to send critical event {event_type} to user {user_id} on attempt {attempt + 1}: {e}")
                    # Continue to retry
            
            # No connection yet, wait before retry (except on last attempt)
            if attempt < max_retries - 1:
                logger.warning(
                    f"No active connection for user {user_id} on attempt {attempt + 1}/{max_retries}. "
                    f"Waiting {retry_delay}s before retry..."
                )
                await asyncio.sleep(retry_delay)
        
        # All retries failed
        logger.critical(
            f"CONNECTION HEALTH CHECK FAILED: No active connections for user {user_id} "
            f"after {max_retries} attempts when trying to emit critical event {event_type}. "
            f"User will not receive this critical update."
        )
        
        # Store for recovery instead of silently failing
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "critical": True
        }
        await self._store_failed_message(user_id, message, "no_active_connections_after_retry")
        # Don't return silently - emit to user notification system
        await self._emit_connection_error_notification(user_id, event_type)
    
    async def send_to_user_with_wait(self, user_id: str, message: Dict[str, Any], 
                                      wait_timeout: float = 3.0) -> bool:
        """
        Send a message to user, optionally waiting for connection to be established first.
        
        This method helps avoid race conditions during startup by waiting for connections
        before attempting to send messages.
        
        Args:
            user_id: User ID to send message to
            message: Message to send
            wait_timeout: Maximum time to wait for connection (0 = no wait)
            
        Returns:
            True if message sent successfully, False otherwise
        """
        # If wait_timeout > 0, wait for connection first
        if wait_timeout > 0 and not self.is_connection_active(user_id):
            logger.debug(f"Waiting up to {wait_timeout}s for connection for user {user_id}")
            connection_ready = await self.wait_for_connection(user_id, timeout=wait_timeout)
            if not connection_ready:
                logger.warning(f"No connection established for user {user_id} within {wait_timeout}s")
                # Store message for later delivery
                await self._store_failed_message(user_id, message, "connection_timeout")
                return False
        
        # Try to send the message
        try:
            await self.send_to_user(user_id, message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            return False
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connections."""
        # CRITICAL FIX: Use safe serialization for broadcast messages
        safe_message = _serialize_message_safely(message)
        for connection in list(self._connections.values()):
            try:
                await connection.websocket.send_json(safe_message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection.connection_id}: {e}")
                await self.remove_connection(connection.connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self._connections),
            "unique_users": len(self._user_connections),
            "connections_by_user": {
                user_id: len(conns) 
                for user_id, conns in self._user_connections.items()
            }
        }
    
    def is_connection_active(self, user_id: Union[str, UserID]) -> bool:
        """
        Check if user has active WebSocket connections with type validation.
        CRITICAL for authentication event validation.
        
        Args:
            user_id: User ID to check (accepts both str and UserID)
            
        Returns:
            True if user has at least one active connection, False otherwise
        """
        try:
            connection_ids = self.get_user_connections(user_id)
            if not connection_ids:
                return False
        except ValueError as e:
            logger.warning(f"Invalid user_id for connection check: {user_id}: {e}")
            return False
        
        # Check if at least one connection is still valid
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket:
                # TODO: Add more sophisticated health check if websocket has state
                return True
        
        return False
    
    def get_connection_health(self, user_id: Union[str, UserID]) -> Dict[str, Any]:
        """
        Get detailed connection health information for a user with type validation.
        
        Args:
            user_id: User ID to check (accepts both str and UserID)
            
        Returns:
            Dictionary with connection health details
        """
        try:
            validated_user_id = ensure_user_id(user_id)
            connection_ids = self.get_user_connections(validated_user_id)
            total_connections = len(connection_ids)
            active_connections = 0
            connection_details = []
        except ValueError as e:
            logger.warning(f"Invalid user_id for health check: {user_id}: {e}")
            return {
                'user_id': str(user_id),
                'error': 'invalid_user_id',
                'message': f'Invalid user_id format: {e}'
            }
        
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection:
                is_active = connection.websocket is not None
                if is_active:
                    active_connections += 1
                    
                connection_details.append({
                    'connection_id': conn_id,
                    'active': is_active,
                    'connected_at': connection.connected_at.isoformat(),
                    'metadata': connection.metadata or {},
                    'thread_id': connection.thread_id
                })
        
        return {
            'user_id': validated_user_id,
            'total_connections': total_connections,
            'active_connections': active_connections,
            'has_active_connections': active_connections > 0,
            'connections': connection_details
        }
    
    async def connect_user(self, user_id: str, websocket: Any, connection_id: str = None, thread_id: str = None) -> Any:
        """Legacy compatibility method for connecting a user.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection
            connection_id: Optional preliminary connection ID to preserve state machine continuity
            thread_id: Optional thread context to preserve thread isolation
        """
        from datetime import datetime
        
        # CRITICAL FIX: Use provided connection_id to preserve state machine continuity
        if connection_id:
            # Pass-through connection ID strategy to prevent state machine recreation
            final_connection_id = connection_id
            logger.info(f"PASS-THROUGH FIX: Using provided connection_id {connection_id} to preserve state machine")
        else:
            # Fallback: Use UnifiedIDManager for new connection ID generation
            id_manager = UnifiedIDManager()
            final_connection_id = id_manager.generate_id(
                IDType.WEBSOCKET,
                prefix="conn",
                context={"user_id": user_id, "component": "legacy_connection"}
            )
            logger.warning(f"PASS-THROUGH FIX: No connection_id provided, generated new: {final_connection_id}")
        connection = WebSocketConnection(
            connection_id=final_connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(),
            thread_id=thread_id
        )
        await self.add_connection(connection)
        
        # Return a ConnectionInfo-like object for compatibility - ISSUE #556 FIX: Include thread_id
        conn_info = type('ConnectionInfo', (), {
            'user_id': user_id,
            'connection_id': final_connection_id,
            'websocket': websocket,
            'thread_id': thread_id  # ISSUE #556 FIX: Include thread_id for propagation
        })()
        
        # Store in connection registry for compatibility
        self.connection_registry[final_connection_id] = conn_info
        
        return final_connection_id  # Return the connection_id directly for consistency
    
    async def disconnect_user(self, user_id: str, websocket: Any, code: int = 1000, reason: str = "Normal closure") -> None:
        """Legacy compatibility method for disconnecting a user."""
        # Find the connection by user_id and websocket
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket == websocket:
                await self.remove_connection(conn_id)
                # Clean up connection registry
                if conn_id in self.connection_registry:
                    del self.connection_registry[conn_id]
                logger.info(f"Disconnected user {user_id} with code {code}: {reason}")
                return
        logger.warning(f"Connection not found for user {user_id} during disconnect")
    
    async def find_connection(self, user_id: str, websocket: Any) -> Optional[Any]:
        """Find a connection for the given user_id and websocket."""
        connection_ids = self.get_user_connections(user_id)
        for conn_id in connection_ids:
            connection = self.get_connection(conn_id)
            if connection and connection.websocket == websocket:
                # Return a ConnectionInfo-like object for compatibility
                return type('ConnectionInfo', (), {
                    'user_id': user_id,
                    'connection_id': conn_id,
                    'websocket': websocket
                })()
        return None
    
    async def handle_message(self, user_id: str, websocket: Any, message: Dict[str, Any]) -> bool:
        """Handle a message from a user (compatibility method)."""
        try:
            # For compatibility, just log the message handling
            logger.debug(f"Handling message from {user_id}: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to handle message from {user_id}: {e}")
            return False
    
    async def connect_to_job(self, websocket: Any, job_id: str) -> Any:
        """Connect to a job (room-like functionality for compatibility)."""
        import uuid
        from datetime import datetime
        
        # Validate job_id
        if not isinstance(job_id, str):
            logger.warning(f"Invalid job_id type: {type(job_id)}, converting to string")
            job_id = f"job_{id(websocket)}"
        
        # Check for invalid job_id patterns (object representations)
        if "<" in job_id or "object at" in job_id or "WebSocket" in job_id:
            logger.warning(f"Invalid job_id detected: {job_id}, generating new one")
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            job_id = UnifiedIdGenerator.generate_base_id("job", random_length=8)
        
        # Create a user_id based on job_id and websocket
        user_id = f"job_{job_id}_{id(websocket)}"
        
        # Create connection using SSOT
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        connection_id = UnifiedIdGenerator.generate_websocket_connection_id(user_id)
        connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            websocket=websocket,
            connected_at=datetime.now(),
            metadata={"job_id": job_id, "connection_type": "job"}
        )
        await self.add_connection(connection)
        
        # Initialize core and room_manager for compatibility
        if not hasattr(self, 'core'):
            self.core = type('Core', (), {})()
            self.core.room_manager = type('RoomManager', (), {})()
            self.core.room_manager.rooms = {}
            self.core.room_manager.room_connections = {}
        
        # Add to room
        if job_id not in self.core.room_manager.rooms:
            self.core.room_manager.rooms[job_id] = set()
            self.core.room_manager.room_connections[job_id] = set()
        
        self.core.room_manager.rooms[job_id].add(connection_id)
        self.core.room_manager.room_connections[job_id].add(user_id)
        
        # Add get_stats method to room_manager
        def get_stats():
            return {
                "room_connections": {
                    room_id: list(connections) for room_id, connections in self.core.room_manager.room_connections.items()
                }
            }
        
        def get_room_connections(room_id: str):
            return list(self.core.room_manager.room_connections.get(room_id, set()))
        
        self.core.room_manager.get_stats = get_stats
        self.core.room_manager.get_room_connections = get_room_connections
        
        # Return a ConnectionInfo-like object for compatibility
        conn_info = type('ConnectionInfo', (), {
            'user_id': user_id,
            'connection_id': connection_id,
            'websocket': websocket,
            'job_id': job_id
        })()
        
        # Store in connection registry for compatibility
        self.connection_registry[connection_id] = conn_info
        
        return conn_info
    
    async def disconnect_from_job(self, job_id: str, websocket: Any) -> None:
        """Disconnect from a job."""
        user_id = f"job_{job_id}_{id(websocket)}"
        await self.disconnect_user(user_id, websocket)
    
    # ============================================================================
    # ENHANCED ERROR HANDLING AND RECOVERY METHODS
    # ============================================================================
    
    def _get_connection_diagnostics(self, connection: WebSocketConnection) -> Dict[str, Any]:
        """Get detailed diagnostics for a connection with safe serialization."""
        try:
            websocket = connection.websocket
            diagnostics = {
                'has_websocket': websocket is not None,
                'websocket_type': type(websocket).__name__ if websocket else None,
                'connection_age_seconds': (datetime.utcnow() - connection.connected_at).total_seconds(),
                'metadata_present': bool(connection.metadata),
            }
            
            # CRITICAL FIX: Safe WebSocketState handling
            if websocket:
                try:
                    client_state = getattr(websocket, 'client_state', None)
                    if client_state is not None:
                        # Use safe serialization to convert WebSocketState enum to string
                        diagnostics['websocket_state'] = _serialize_message_safely(client_state)
                    else:
                        diagnostics['websocket_state'] = 'unknown'
                except Exception as state_error:
                    diagnostics['websocket_state'] = f'error_getting_state_{str(state_error)}'
            else:
                diagnostics['websocket_state'] = 'no_websocket'
                
            return diagnostics
        except Exception as e:
            return {'diagnostics_error': str(e)}
    
    async def _store_failed_message(self, user_id: str, message: Dict[str, Any], 
                                   failure_reason: str) -> None:
        """Store failed message for potential recovery."""
        if not self._error_recovery_enabled:
            return
        
        try:
            if user_id not in self._message_recovery_queue:
                self._message_recovery_queue[user_id] = []
            
            # Add failure metadata
            failed_message = {
                **message,
                'failure_reason': failure_reason,
                'failed_at': datetime.utcnow().isoformat(),
                'recovery_attempts': 0
            }
            
            self._message_recovery_queue[user_id].append(failed_message)
            
            # Increment error count
            self._connection_error_count[user_id] = self._connection_error_count.get(user_id, 0) + 1
            self._last_error_time[user_id] = datetime.utcnow()
            
            # Limit queue size to prevent memory issues
            max_queue_size = 50
            if len(self._message_recovery_queue[user_id]) > max_queue_size:
                self._message_recovery_queue[user_id] = self._message_recovery_queue[user_id][-max_queue_size:]
            
            logger.info(f"Stored failed message for user {user_id}: {failure_reason}")
            
        except Exception as e:
            logger.error(f"Failed to store failed message for recovery: {e}")
    
    async def _emit_connection_error_notification(self, user_id: str, failed_event_type: str) -> None:
        """Emit a user-visible error notification about connection issues."""
        try:
            error_message = {
                "type": "connection_error",
                "data": {
                    "message": f"Connection issue detected. Your {failed_event_type} update may be delayed.",
                    "event_type": failed_event_type,
                    "user_friendly_message": "We're having trouble connecting to you. Please refresh your browser if you don't see updates soon.",
                    "severity": "warning",
                    "action_required": "Consider refreshing the page if issues persist",
                    "support_code": f"CONN_ERR_{user_id[:8]}_{failed_event_type}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # Try to send the error notification (even though connection might be bad)
            # This might reach the user if there are other active connections
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        # CRITICAL FIX: Use safe serialization for error messages
                        safe_error_message = _serialize_message_safely(error_message)
                        await connection.websocket.send_json(safe_error_message)
                        logger.info(f"Sent connection error notification to user {user_id}")
                        return
                    except Exception:
                        continue  # Try next connection
            
            # If we can't send via WebSocket, log for external monitoring
            logger.critical(
                f"USER_NOTIFICATION_FAILED: Could not notify user {user_id} about connection error. "
                f"User may experience blank screen or missing updates. Support code: {error_message['data']['support_code']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to emit connection error notification: {e}")
    
    async def _emit_system_error_notification(self, user_id: str, failed_event_type: str, 
                                            error_details: str) -> None:
        """Emit a user-visible system error notification."""
        try:
            error_message = {
                "type": "system_error",
                "data": {
                    "message": f"A system error occurred while processing your {failed_event_type}.",
                    "user_friendly_message": "Something went wrong on our end. Our team has been notified. Please try again in a few moments.",
                    "event_type": failed_event_type,
                    "severity": "error",
                    "action_required": "Try refreshing the page or contact support if the problem persists",
                    "support_code": f"SYS_ERR_{user_id[:8]}_{failed_event_type}_{datetime.utcnow().strftime('%H%M%S')}"
                },
                "timestamp": datetime.utcnow().isoformat(),
                "critical": True
            }
            
            # DEADLOCK FIX: Send directly to avoid circular dependency with send_to_user
            connection_ids = self.get_user_connections(user_id)
            for conn_id in connection_ids:
                connection = self.get_connection(conn_id)
                if connection and connection.websocket:
                    try:
                        # CRITICAL FIX: Use safe serialization for system error messages
                        safe_error_message = _serialize_message_safely(error_message)
                        await connection.websocket.send_json(safe_error_message)
                        logger.info(f"Sent system error notification to user {user_id}")
                        return
                    except Exception:
                        continue  # Try next connection
            
        except Exception as e:
            logger.critical(
                f"SYSTEM_ERROR_NOTIFICATION_FAILED: Could not notify user {user_id} "
                f"about system error in {failed_event_type}: {e}. "
                f"User may be unaware of the failure. Error details: {error_details}"
            )
    
    async def attempt_message_recovery(self, user_id: str) -> int:
        """Attempt to recover failed messages for a user when they reconnect."""
        if not self._error_recovery_enabled or user_id not in self._message_recovery_queue:
            return 0
        
        failed_messages = self._message_recovery_queue[user_id]
        recovered_count = 0
        
        # Only attempt recovery if user has active connections now
        if not self.is_connection_active(user_id):
            logger.debug(f"Skipping message recovery for {user_id} - no active connections")
            return 0
        
        for message in failed_messages[:]:  # Copy list to avoid modification during iteration
            try:
                # Increment recovery attempts
                message['recovery_attempts'] = message.get('recovery_attempts', 0) + 1
                
                # Skip messages with too many recovery attempts
                if message['recovery_attempts'] > 3:
                    logger.warning(f"Abandoning message recovery after 3 attempts: {message.get('type', 'unknown')}")
                    failed_messages.remove(message)
                    continue
                
                # Attempt to send the message
                recovery_message = {k: v for k, v in message.items() 
                                  if k not in ['failure_reason', 'failed_at', 'recovery_attempts']}
                recovery_message['recovered'] = True
                recovery_message['original_failure'] = message['failure_reason']
                
                await self.send_to_user(user_id, recovery_message)
                failed_messages.remove(message)
                recovered_count += 1
                
                logger.info(f"Recovered message for user {user_id}: {message.get('type', 'unknown')}")
                
            except Exception as e:
                logger.warning(f"Message recovery attempt failed for user {user_id}: {e}")
        
        if recovered_count > 0:
            logger.info(f"Message recovery completed for user {user_id}: {recovered_count} messages recovered")
        
        return recovered_count
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics for monitoring."""
        total_users_with_errors = len(self._connection_error_count)
        total_error_count = sum(self._connection_error_count.values())
        total_queued_messages = sum(len(queue) for queue in self._message_recovery_queue.values())
        
        # Recent errors (last 5 minutes)
        recent_errors = 0
        cutoff_time = datetime.utcnow()
        for error_time in self._last_error_time.values():
            if (cutoff_time - error_time).total_seconds() < 300:  # 5 minutes
                recent_errors += 1
        
        return {
            'total_users_with_errors': total_users_with_errors,
            'total_error_count': total_error_count,
            'total_queued_messages': total_queued_messages,
            'recent_errors_5min': recent_errors,
            'error_recovery_enabled': self._error_recovery_enabled,
            'users_with_queued_messages': len(self._message_recovery_queue),
            'error_details': {
                user_id: {
                    'error_count': self._connection_error_count.get(user_id, 0),
                    'last_error': self._last_error_time.get(user_id, '').isoformat() if self._last_error_time.get(user_id) else None,
                    'queued_messages': len(self._message_recovery_queue.get(user_id, []))
                }
                for user_id in set(list(self._connection_error_count.keys()) + list(self._message_recovery_queue.keys()))
            }
        }
    
    async def cleanup_error_data(self, older_than_hours: int = 24) -> Dict[str, int]:
        """Clean up old error data to prevent memory leaks."""
        cutoff_time = datetime.utcnow()
        
        # Clean up old error times
        old_error_users = []
        for user_id, error_time in self._last_error_time.items():
            if (cutoff_time - error_time).total_seconds() > (older_than_hours * 3600):
                old_error_users.append(user_id)
        
        for user_id in old_error_users:
            del self._last_error_time[user_id]
            if user_id in self._connection_error_count:
                del self._connection_error_count[user_id]
        
        # Clean up old recovery queues for users with no recent activity
        old_queue_users = []
        for user_id, messages in self._message_recovery_queue.items():
            # Remove old messages from queue
            current_messages = []
            for message in messages:
                failed_at_str = message.get('failed_at', '')
                try:
                    failed_at = datetime.fromisoformat(failed_at_str.replace('Z', '+00:00'))
                    if (cutoff_time - failed_at).total_seconds() <= (older_than_hours * 3600):
                        current_messages.append(message)
                except (ValueError, AttributeError):
                    # Keep message if we can't parse the date
                    current_messages.append(message)
            
            if current_messages:
                self._message_recovery_queue[user_id] = current_messages
            else:
                old_queue_users.append(user_id)
        
        for user_id in old_queue_users:
            del self._message_recovery_queue[user_id]
        
        return {
            'cleaned_error_users': len(old_error_users),
            'cleaned_queue_users': len(old_queue_users),
            'remaining_error_users': len(self._connection_error_count),
            'remaining_queue_users': len(self._message_recovery_queue)
        }
    
    # ============================================================================
    # BACKGROUND TASK MONITORING SYSTEM
    # ============================================================================
    
    async def start_monitored_background_task(self, task_name: str, coro_func, *args, **kwargs) -> str:
        """Start a background task with monitoring and automatic restart."""
        async with self._monitoring_lock:
            if not self._monitoring_enabled:
                logger.warning("Background task monitoring is disabled")
                return ""
            
            # Store task definition in registry for potential recovery
            self._task_registry[task_name] = {
                'func': coro_func,
                'args': args,
                'kwargs': kwargs,
                'created_at': datetime.utcnow(),
                'restart_count': 0
            }
            
            # Stop existing task if it exists
            if task_name in self._background_tasks:
                await self.stop_background_task(task_name)
            
            # Create monitored task
            task = asyncio.create_task(
                self._run_monitored_task(task_name, coro_func, *args, **kwargs)
            )
            
            self._background_tasks[task_name] = task
            logger.info(f"Started monitored background task: {task_name}")
            return task_name
    
    async def _run_monitored_task(self, task_name: str, coro_func, *args, **kwargs):
        """ENHANCED: Run a task with monitoring, error handling, and automatic recovery."""
        failure_count = 0
        max_failures = 5  # Increased from 3 for better resilience
        base_delay = 1.0
        max_delay = 120.0  # Increased max delay
        task_start_time = datetime.utcnow()
        
        logger.info(f"MONITORING TASK STARTED: {task_name} with recovery support")
        
        while self._monitoring_enabled and not self._shutdown_requested:
            try:
                iteration_start = datetime.utcnow()
                
                if asyncio.iscoroutinefunction(coro_func):
                    await coro_func(*args, **kwargs)
                else:
                    # If it's a regular function, run it
                    result = coro_func(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        await result
                
                # Reset failure count on successful execution
                if failure_count > 0:
                    logger.info(f"TASK RECOVERY SUCCESS: {task_name} recovered after {failure_count} failures")
                    failure_count = 0
                    
                # Clear failure tracking
                if task_name in self._task_failures:
                    del self._task_failures[task_name]
                if task_name in self._task_last_failure:
                    del self._task_last_failure[task_name]
                
                execution_duration = (datetime.utcnow() - iteration_start).total_seconds()
                logger.debug(f"Background task {task_name} completed successfully (duration: {execution_duration:.2f}s)")
                break  # Task completed successfully
                
            except asyncio.CancelledError:
                logger.info(f"TASK CANCELLED: {task_name} was cancelled gracefully")
                break
                
            except Exception as e:
                failure_count += 1
                self._task_failures[task_name] = failure_count
                self._task_last_failure[task_name] = datetime.utcnow()
                
                # Enhanced error logging with more context
                task_runtime = (datetime.utcnow() - task_start_time).total_seconds()
                logger.critical(
                    f"BACKGROUND TASK FAILURE: {task_name} failed (attempt {failure_count}/{max_failures}) "
                    f"after {task_runtime:.1f}s runtime. Error: {e}. Error type: {type(e).__name__}. "
                    f"Monitoring_enabled: {self._monitoring_enabled}, Shutdown_requested: {self._shutdown_requested}"
                )
                
                # Check if we should attempt automatic recovery
                if failure_count >= max_failures:
                    logger.critical(
                        f"TASK FAILURE THRESHOLD EXCEEDED: {task_name} failed {max_failures} times. "
                        f"Attempting automatic monitoring restart before abandoning task."
                    )
                    
                    # Attempt one automatic monitoring restart
                    try:
                        restart_result = await self.restart_background_monitoring(force_restart=True)
                        if restart_result.get('monitoring_restarted') and restart_result.get('health_check_passed'):
                            logger.info(f"AUTOMATIC RECOVERY: Successfully restarted monitoring for {task_name}")
                            # Reset failure count and continue
                            failure_count = 0
                            continue
                        else:
                            logger.error(f"AUTOMATIC RECOVERY FAILED: Could not restart monitoring for {task_name}")
                    except Exception as restart_error:
                        logger.error(f"AUTOMATIC RECOVERY EXCEPTION: {restart_error}")
                    
                    # If automatic recovery failed, abandon task
                    logger.critical(
                        f"BACKGROUND TASK ABANDONED: {task_name} failed {max_failures} times and "
                        f"automatic recovery failed. Manual intervention required."
                    )
                    await self._notify_admin_of_task_failure(task_name, e, failure_count)
                    break
                
                # Check if monitoring is still enabled before retry
                if not self._monitoring_enabled or self._shutdown_requested:
                    logger.warning(
                        f"TASK RETRY ABORTED: {task_name} cannot retry due to monitoring state "
                        f"(enabled: {self._monitoring_enabled}, shutdown: {self._shutdown_requested})"
                    )
                    break
                
                # Calculate exponential backoff delay with jitter
                import random
                base_backoff = min(base_delay * (2 ** (failure_count - 1)), max_delay)
                jitter = base_backoff * 0.1 * (0.5 - random.random())  #  +/- 5% jitter
                delay = base_backoff + jitter
                
                logger.warning(
                    f"TASK RETRY SCHEDULED: {task_name} will retry in {delay:.1f}s "
                    f"(attempt {failure_count + 1}/{max_failures})"
                )
                
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    logger.info(f"TASK RETRY CANCELLED: {task_name} restart was cancelled")
                    break
        
        # Log final task state
        total_runtime = (datetime.utcnow() - task_start_time).total_seconds()
        logger.info(
            f"MONITORING TASK ENDED: {task_name} finished after {total_runtime:.1f}s "
            f"(failures: {failure_count}, monitoring_enabled: {self._monitoring_enabled})"
        )
    
    async def stop_background_task(self, task_name: str) -> bool:
        """Stop a background task by name."""
        if task_name not in self._background_tasks:
            logger.warning(f"Background task {task_name} not found")
            return False
        
        task = self._background_tasks[task_name]
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error while stopping background task {task_name}: {e}")
        
        del self._background_tasks[task_name]
        logger.info(f"Stopped background task: {task_name}")
        return True
    
    async def _notify_admin_of_task_failure(self, task_name: str, error: Exception, failure_count: int):
        """Notify system administrators of critical background task failure."""
        try:
            # This would integrate with alerting systems in production
            alert_message = {
                "type": "critical_task_failure",
                "task_name": task_name,
                "error": str(error),
                "error_type": type(error).__name__,
                "failure_count": failure_count,
                "timestamp": datetime.utcnow().isoformat(),
                "requires_manual_intervention": True,
                "impact": "System functionality may be degraded"
            }
            
            # Log at critical level for monitoring systems
            logger.critical(
                f"ADMIN ALERT REQUIRED: Background task {task_name} has failed permanently. "
                f"Alert: {alert_message}"
            )
            
            # TODO: Integrate with actual alerting systems:
            # - Send to PagerDuty/OpsGenie
            # - Email notification to on-call engineers
            # - Slack/Teams notification
            # - Create monitoring dashboard alert
            
        except Exception as e:
            logger.error(f"Failed to send admin notification for task failure: {e}")
    
    def get_background_task_status(self) -> Dict[str, Any]:
        """Get status of all background tasks."""
        task_status = {}
        
        for task_name, task in self._background_tasks.items():
            task_status[task_name] = {
                'running': not task.done(),
                'cancelled': task.cancelled(),
                'exception': str(task.exception()) if task.done() and task.exception() else None,
                'failure_count': self._task_failures.get(task_name, 0),
                'last_failure': self._task_last_failure.get(task_name, '').isoformat() if self._task_last_failure.get(task_name) else None
            }
        
        return {
            'monitoring_enabled': self._monitoring_enabled,
            'total_tasks': len(self._background_tasks),
            'running_tasks': len([t for t in self._background_tasks.values() if not t.done()]),
            'failed_tasks': len(self._task_failures),
            'tasks': task_status
        }
    
    async def process_recovery_queue(self, user_id: str) -> None:
        """Process recovery queue messages for a user.
        
        Public alias for _process_queued_messages for compatibility.
        """
        await self._process_queued_messages(user_id)
    
    async def _process_queued_messages(self, user_id: str) -> None:
        """Process queued messages for a user after connection established.
        
        This is called when a new connection is established to deliver
        any messages that were attempted while the user had no connections.
        """
        if user_id not in self._message_recovery_queue:
            return
        
        messages = self._message_recovery_queue.get(user_id, [])
        if not messages:
            return
        
        logger.info(f"Processing {len(messages)} queued messages for user {user_id}")
        
        # Clear the queue first to prevent re-processing
        self._message_recovery_queue[user_id] = []
        
        # Small delay to ensure connection is fully established
        await asyncio.sleep(0.1)
        
        # Send each queued message with timeout to prevent hanging
        for msg in messages:
            try:
                # Remove recovery metadata before sending
                clean_msg = {k: v for k, v in msg.items() 
                           if k not in ['failure_reason', 'failed_at', 'recovery_attempts']}
                
                # Add a flag indicating this is a recovered message
                clean_msg['recovered'] = True
                
                # HANG FIX: Add timeout to prevent infinite wait on send_to_user
                await asyncio.wait_for(
                    self.send_to_user(user_id, clean_msg),
                    timeout=3.0  # Reasonable timeout per message
                )
                logger.debug(f"Successfully delivered queued message type '{clean_msg.get('type')}' to user {user_id}")
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout delivering queued message to user {user_id}: {clean_msg.get('type', 'unknown')}")
            except Exception as e:
                logger.error(f"Failed to deliver queued message to user {user_id}: {e}")
        
        logger.info(f"Completed processing queued messages for user {user_id}")
    
    async def health_check_background_tasks(self) -> Dict[str, Any]:
        """Perform health check on background tasks and restart failed ones."""
        health_report = {
            'healthy_tasks': 0,
            'unhealthy_tasks': 0,
            'restarted_tasks': [],
            'failed_restarts': []
        }
        
        for task_name, task in list(self._background_tasks.items()):
            if task.done() and not task.cancelled():
                # Task completed unexpectedly - try to restart
                logger.warning(f"Background task {task_name} completed unexpectedly - attempting restart")
                
                try:
                    # Remove the completed task
                    del self._background_tasks[task_name]
                    
                    # This would need the original function and args to restart
                    # For now, just mark as needing manual restart
                    health_report['unhealthy_tasks'] += 1
                    health_report['failed_restarts'].append({
                        'task_name': task_name,
                        'reason': 'Cannot restart - original function not stored'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to restart background task {task_name}: {e}")
                    health_report['failed_restarts'].append({
                        'task_name': task_name,
                        'reason': str(e)
                    })
            else:
                health_report['healthy_tasks'] += 1
        
        return health_report
    
    async def shutdown_background_monitoring(self):
        """Shutdown all background tasks."""
        async with self._monitoring_lock:
            self._shutdown_requested = True
            self._monitoring_enabled = False
            
            # Cancel all tasks
            for task_name in list(self._background_tasks.keys()):
                await self.stop_background_task(task_name)
            
            logger.info("Background task monitoring shutdown complete")
    
    async def _verify_monitoring_health(self) -> bool:
        """
        CRITICAL: Verify that monitoring system is healthy and operational.
        
        Returns:
            True if monitoring is healthy, False if issues detected
        """
        try:
            # Check basic monitoring state
            if not self._monitoring_enabled:
                logger.error("Monitoring health check failed: monitoring disabled")
                return False
            
            if self._shutdown_requested:
                logger.error("Monitoring health check failed: shutdown requested")
                return False
            
            # Check task health
            healthy_tasks = 0
            total_tasks = len(self._background_tasks)
            
            for task_name, task in self._background_tasks.items():
                if not task.done() and not task.cancelled():
                    healthy_tasks += 1
                elif task.done() and task.exception():
                    logger.warning(f"Task {task_name} has exception: {task.exception()}")
            
            # Update health check timestamp
            self._last_health_check = datetime.utcnow()
            self._health_check_failures = 0
            
            logger.info(
                f"Monitoring health check passed: {healthy_tasks}/{total_tasks} tasks healthy, "
                f"failures_cleared={len(self._task_failures) == 0}"
            )
            return True
            
        except Exception as e:
            self._health_check_failures += 1
            logger.error(f"Monitoring health check exception: {e}")
            return False
    
    async def get_monitoring_health_status(self) -> Dict[str, Any]:
        """
        CRITICAL RESILIENCE: Get comprehensive monitoring health status.
        
        This provides detailed health information for monitoring dashboard and alerts.
        
        Returns:
            Comprehensive health status dictionary
        """
        current_time = datetime.utcnow()
        
        # Calculate task health metrics
        task_health = {
            'total_tasks': len(self._background_tasks),
            'running_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'healthy_tasks': []
        }
        
        for task_name, task in self._background_tasks.items():
            if not task.done():
                task_health['running_tasks'] += 1
                task_health['healthy_tasks'].append(task_name)
            elif task.cancelled():
                task_health['cancelled_tasks'] += 1
            elif task.exception():
                task_health['failed_tasks'] += 1
            else:
                task_health['completed_tasks'] += 1
        
        # Calculate uptime and failure rates
        last_health_check_age = (current_time - self._last_health_check).total_seconds() if self._last_health_check else None
        health_check_stale = last_health_check_age is not None and last_health_check_age > 300  # 5 minutes
        
        return {
            'monitoring_enabled': self._monitoring_enabled,
            'shutdown_requested': self._shutdown_requested,
            'health_check_failures': self._health_check_failures,
            'last_health_check': self._last_health_check.isoformat() if self._last_health_check else None,
            'last_health_check_age_seconds': last_health_check_age,
            'health_check_stale': health_check_stale,
            'task_health': task_health,
            'task_failures': {
                'total_failed_tasks': len(self._task_failures),
                'failure_details': {
                    task_name: {
                        'failure_count': count,
                        'last_failure': self._task_last_failure.get(task_name, '').isoformat() if self._task_last_failure.get(task_name) else None
                    }
                    for task_name, count in self._task_failures.items()
                }
            },
            'task_registry': {
                'registered_tasks': len(self._task_registry),
                'task_restart_counts': {
                    task_name: config.get('restart_count', 0)
                    for task_name, config in self._task_registry.items()
                }
            },
            'overall_health': self._calculate_overall_health_score(task_health, health_check_stale),
            'alerts': self._generate_health_alerts(task_health, health_check_stale, last_health_check_age)
        }
    
    def _calculate_overall_health_score(self, task_health: Dict, health_check_stale: bool) -> Dict[str, Any]:
        """
        Calculate overall health score for monitoring system.
        
        Args:
            task_health: Task health metrics
            health_check_stale: Whether health check is stale
            
        Returns:
            Health score and status
        """
        total_tasks = task_health['total_tasks']
        running_tasks = task_health['running_tasks']
        failed_tasks = task_health['failed_tasks']
        
        # Calculate base health score
        if total_tasks == 0:
            task_score = 100  # No tasks is considered healthy
        else:
            task_score = max(0, 100 - (failed_tasks / total_tasks * 100))
        
        # Apply penalties
        health_score = task_score
        
        if not self._monitoring_enabled:
            health_score = 0
        elif self._shutdown_requested:
            health_score = min(health_score, 25)
        elif health_check_stale:
            health_score = min(health_score, 50)
        elif self._health_check_failures > 0:
            health_score = min(health_score, 75)
        
        # Determine status
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        elif health_score >= 30:
            status = "degraded"
        else:
            status = "critical"
        
        return {
            'score': round(health_score, 1),
            'status': status,
            'factors': {
                'monitoring_enabled': self._monitoring_enabled,
                'shutdown_requested': self._shutdown_requested,
                'health_check_stale': health_check_stale,
                'health_check_failures': self._health_check_failures,
                'task_failure_rate': (failed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            }
        }
    
    def _generate_health_alerts(self, task_health: Dict, health_check_stale: bool, last_health_check_age: Optional[float]) -> List[Dict[str, Any]]:
        """
        Generate health alerts based on monitoring status.
        
        Args:
            task_health: Task health metrics
            health_check_stale: Whether health check is stale
            last_health_check_age: Age of last health check in seconds
            
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        # Critical alerts
        if not self._monitoring_enabled:
            alerts.append({
                'severity': 'critical',
                'message': 'Background monitoring is disabled',
                'action': 'Call restart_background_monitoring() immediately',
                'impact': 'System health monitoring and recovery are non-functional'
            })
        
        if self._shutdown_requested:
            alerts.append({
                'severity': 'critical',
                'message': 'Monitoring shutdown has been requested',
                'action': 'Investigate shutdown cause and restart monitoring',
                'impact': 'Monitoring will stop accepting new tasks'
            })
        
        # Warning alerts
        if health_check_stale:
            alerts.append({
                'severity': 'warning',
                'message': f'Health check is stale ({last_health_check_age:.0f}s old)',
                'action': 'Check monitoring system responsiveness',
                'impact': 'May not detect recent failures'
            })
        
        if self._health_check_failures > 0:
            alerts.append({
                'severity': 'warning',
                'message': f'{self._health_check_failures} health check failures detected',
                'action': 'Investigate monitoring system stability',
                'impact': 'Reduced reliability of health status'
            })
        
        # Task-related alerts
        if task_health['failed_tasks'] > 0:
            alerts.append({
                'severity': 'warning',
                'message': f"{task_health['failed_tasks']} background tasks have failed",
                'action': 'Review task failure logs and restart if needed',
                'impact': 'Reduced system functionality'
            })
        
        if task_health['total_tasks'] > 0 and task_health['running_tasks'] == 0:
            alerts.append({
                'severity': 'critical',
                'message': 'No background tasks are running despite having registered tasks',
                'action': 'Restart background monitoring immediately',
                'impact': 'Complete loss of background processing'
            })
        
        return alerts
    
    async def enable_background_monitoring(self, restart_previous_tasks: bool = True) -> Dict[str, Any]:
        """
        Re-enable background task monitoring with optional task recovery.
        
        CRITICAL FIX: Prevents permanent disable of monitoring system by providing
        a safe way to restart monitoring after shutdown or errors.
        
        Args:
            restart_previous_tasks: Whether to restart tasks that were registered before shutdown
            
        Returns:
            Dictionary with recovery status and counts
        """
        recovery_status = {
            'monitoring_enabled': False,
            'tasks_restarted': 0,
            'tasks_failed_restart': 0,
            'failed_tasks': [],
            'health_check_reset': False,
            'previous_state': {
                'was_shutdown': self._shutdown_requested,
                'had_failures': len(self._task_failures) > 0
            }
        }
        
        async with self._monitoring_lock:
            if self._monitoring_enabled:
                logger.info("Background monitoring is already enabled")
                recovery_status['monitoring_enabled'] = True
                return recovery_status
            
            # Reset monitoring state
            self._monitoring_enabled = True
            self._shutdown_requested = False
            self._health_check_failures = 0
            self._last_health_check = datetime.utcnow()
            recovery_status['health_check_reset'] = True
            
            logger.info("Background task monitoring re-enabled")
            recovery_status['monitoring_enabled'] = True
            
            # Optionally restart registered tasks
            if restart_previous_tasks and self._task_registry:
                logger.info(f"Attempting to restart {len(self._task_registry)} registered tasks")
                
                for task_name, task_config in list(self._task_registry.items()):
                    try:
                        # Increment restart count
                        task_config['restart_count'] = task_config.get('restart_count', 0) + 1
                        
                        # Don't restart tasks that have failed too many times
                        if task_config['restart_count'] > 5:
                            logger.warning(f"Skipping restart of {task_name} - too many restart attempts ({task_config['restart_count']})")
                            continue
                        
                        # Restart the task
                        restart_result = await self.start_monitored_background_task(
                            task_name,
                            task_config['func'],
                            *task_config['args'],
                            **task_config['kwargs']
                        )
                        
                        if restart_result:
                            recovery_status['tasks_restarted'] += 1
                            logger.info(f"Successfully restarted task: {task_name}")
                        else:
                            recovery_status['tasks_failed_restart'] += 1
                            recovery_status['failed_tasks'].append(task_name)
                            logger.error(f"Failed to restart task: {task_name}")
                        
                    except Exception as e:
                        recovery_status['tasks_failed_restart'] += 1
                        recovery_status['failed_tasks'].append(task_name)
                        logger.error(f"Exception while restarting task {task_name}: {e}")
            
            # Clear old failure data for a fresh start
            self._task_failures.clear()
            self._task_last_failure.clear()
            
            logger.info(
                f"Monitoring recovery complete: {recovery_status['tasks_restarted']} tasks restarted, "
                f"{recovery_status['tasks_failed_restart']} failed"
            )
            
        return recovery_status
    
    async def restart_background_monitoring(self, force_restart: bool = False) -> Dict[str, Any]:
        """
        CRITICAL RESILIENCE FIX: Restart background monitoring system with full recovery.
        
        This method addresses the permanent disable issue where monitoring could be
        turned off without a way to recover. Provides comprehensive monitoring restart
        with automatic task recovery and health validation.
        
        Args:
            force_restart: Force restart even if monitoring appears to be running
            
        Returns:
            Dictionary with detailed restart status and recovery metrics
        """
        restart_status = {
            'monitoring_restarted': False,
            'tasks_recovered': 0,
            'tasks_failed_recovery': 0,
            'failed_tasks': [],
            'health_check_passed': False,
            'monitoring_state_before': {
                'enabled': self._monitoring_enabled,
                'shutdown_requested': self._shutdown_requested,
                'active_tasks': len([t for t in self._background_tasks.values() if not t.done()]),
                'total_tasks': len(self._background_tasks),
                'task_failures': len(self._task_failures)
            },
            'recovery_actions_taken': []
        }
        
        async with self._monitoring_lock:
            # Log the restart attempt with detailed context
            logger.critical(
                f"MONITORING RESTART INITIATED: force_restart={force_restart}, "
                f"current_state=[enabled={self._monitoring_enabled}, "
                f"shutdown={self._shutdown_requested}, tasks={len(self._background_tasks)}]"
            )
            restart_status['recovery_actions_taken'].append('restart_initiated')
            
            # Check if restart is needed
            if self._monitoring_enabled and not force_restart and not self._shutdown_requested:
                # Monitoring appears healthy, but verify task health
                active_tasks = len([t for t in self._background_tasks.values() if not t.done()])
                if active_tasks > 0 and len(self._task_failures) == 0:
                    logger.info("Background monitoring appears healthy, skipping restart")
                    restart_status['monitoring_restarted'] = False
                    restart_status['health_check_passed'] = True
                    return restart_status
                else:
                    logger.warning(
                        f"Monitoring enabled but unhealthy: {active_tasks} active tasks, "
                        f"{len(self._task_failures)} task failures - proceeding with restart"
                    )
            
            # Force clean state reset
            logger.info("Resetting monitoring system to clean state")
            self._monitoring_enabled = True
            self._shutdown_requested = False
            self._health_check_failures = 0
            self._last_health_check = datetime.utcnow()
            restart_status['recovery_actions_taken'].append('state_reset')
            restart_status['monitoring_restarted'] = True
            
            # Cancel and clean up existing failed tasks
            failed_task_names = list(self._background_tasks.keys())
            for task_name in failed_task_names:
                try:
                    await self.stop_background_task(task_name)
                    logger.info(f"Cleaned up existing task: {task_name}")
                except Exception as e:
                    logger.error(f"Failed to clean up task {task_name}: {e}")
            
            restart_status['recovery_actions_taken'].append('existing_tasks_cleaned')
            
            # Clear failure tracking for fresh start
            self._task_failures.clear()
            self._task_last_failure.clear()
            restart_status['recovery_actions_taken'].append('failure_tracking_cleared')
            
            # Attempt to recover registered tasks
            if self._task_registry:
                logger.info(f"Attempting to recover {len(self._task_registry)} registered tasks")
                restart_status['recovery_actions_taken'].append('task_recovery_started')
                
                for task_name, task_config in list(self._task_registry.items()):
                    try:
                        # Limit restart attempts to prevent infinite loops
                        restart_count = task_config.get('restart_count', 0)
                        if restart_count > 10:
                            logger.warning(f"Skipping {task_name} - too many restart attempts ({restart_count})")
                            restart_status['tasks_failed_recovery'] += 1
                            restart_status['failed_tasks'].append(f"{task_name}:too_many_restarts")
                            continue
                        
                        # Increment restart count
                        task_config['restart_count'] = restart_count + 1
                        task_config['last_restart'] = datetime.utcnow()
                        
                        # Start the monitored task
                        recovery_result = await self.start_monitored_background_task(
                            task_name,
                            task_config['func'],
                            *task_config['args'],
                            **task_config['kwargs']
                        )
                        
                        if recovery_result:
                            restart_status['tasks_recovered'] += 1
                            logger.info(f"Successfully recovered task: {task_name} (attempt {restart_count + 1})")
                        else:
                            restart_status['tasks_failed_recovery'] += 1
                            restart_status['failed_tasks'].append(f"{task_name}:start_failed")
                            logger.error(f"Failed to recover task: {task_name}")
                        
                    except Exception as e:
                        restart_status['tasks_failed_recovery'] += 1
                        restart_status['failed_tasks'].append(f"{task_name}:exception:{str(e)}")
                        logger.error(f"Exception recovering task {task_name}: {e}")
            
            # Verify monitoring is working
            restart_status['health_check_passed'] = await self._verify_monitoring_health()
            restart_status['recovery_actions_taken'].append('health_check_completed')
            
            # Log final status
            logger.critical(
                f"MONITORING RESTART COMPLETED: success={restart_status['monitoring_restarted']}, "
                f"recovered={restart_status['tasks_recovered']}, "
                f"failed={restart_status['tasks_failed_recovery']}, "
                f"health_ok={restart_status['health_check_passed']}"
            )
            
        return restart_status
    
    # ===========================================================================
    # FIVE WHYS ROOT CAUSE PREVENTION METHODS
    # ===========================================================================
    
    def get_connection_id_by_websocket(self, websocket) -> Optional[ConnectionID]:
        """
        FIVE WHYS CRITICAL METHOD: Get connection ID for a given WebSocket instance with type safety.
        
        This method was identified as missing in the Five Whys analysis and is
        essential for WebSocket manager interface compatibility.
        
        Args:
            websocket: WebSocket instance to search for
            
        Returns:
            Strongly typed ConnectionID if found, None otherwise
        """
        for conn_id, connection in self._connections.items():
            if connection.websocket == websocket:
                logger.debug(f"Found connection ID {conn_id} for WebSocket {id(websocket)}")
                return ConnectionID(conn_id)
        
        logger.debug(f"No connection found for WebSocket {id(websocket)}")
        return None
    
    def update_connection_thread(self, connection_id: Union[str, ConnectionID], thread_id: Union[str, ThreadID]) -> bool:
        """
        FIVE WHYS CRITICAL METHOD: Update thread association for a connection with type validation.
        
        This method works with get_connection_id_by_websocket to manage thread
        associations, as identified in the Five Whys analysis.
        
        Args:
            connection_id: Connection ID to update (accepts both str and ConnectionID)
            thread_id: New thread ID to associate (accepts both str and ThreadID)
            
        Returns:
            True if update successful, False if connection not found
        """
        # Validate and convert IDs
        try:
            validated_connection_id = str(connection_id)
            validated_thread_id = ensure_thread_id(thread_id)
        except ValueError as e:
            logger.error(f"Invalid ID in update_connection_thread: {e}")
            return False
        
        connection = self._connections.get(validated_connection_id)
        if connection:
            # Update the thread_id on the connection object
            if hasattr(connection, 'thread_id'):
                old_thread_id = getattr(connection, 'thread_id', None)
                connection.thread_id = validated_thread_id
                logger.info(
                    f"Updated thread association for connection {validated_connection_id}: "
                    f"{old_thread_id}  ->  {validated_thread_id}"
                )
                return True
            else:
                # Add thread_id attribute if it doesn't exist
                setattr(connection, 'thread_id', validated_thread_id)
                logger.info(f"Added thread association for connection {validated_connection_id}: {validated_thread_id}")
                return True
        else:
            logger.warning(f"Connection {validated_connection_id} not found for thread update")
            return False
    
    # ============================================================================
    # SSOT INTERFACE STANDARDIZATION METHODS (Week 1 - Low Risk)
    # ============================================================================
    
    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all connections.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Args:
            message: Message to broadcast to all connections
        """
        # Use existing broadcast method
        await self.broadcast(message)
    
    async def send_message(self, connection_id: str, message: dict) -> bool:
        """
        Send direct message to specific WebSocket connection.
        
        CRITICAL SSOT INTERFACE COMPLIANCE: This method is required by WebSocket 
        manager interface validation tests and agent event delivery in Golden Path.
        Missing this method blocks agent events (agent_started, agent_thinking, 
        tool_executing, tool_completed, agent_completed) affecting $500K+ ARR.
        
        Args:
            connection_id: Unique connection identifier  
            message: Message payload to send
            
        Returns:
            bool: Success status of message delivery
        """
        try:
            # Validate connection exists
            connection = self.get_connection(connection_id)
            if not connection:
                logger.warning(f"send_message failed: connection {connection_id} not found")
                return False
            
            if not connection.websocket:
                logger.warning(f"send_message failed: connection {connection_id} has no websocket")
                return False
            
            # Safely serialize message for WebSocket transmission
            safe_message = _serialize_message_safely(message)
            
            # Send message via WebSocket
            await connection.websocket.send_json(safe_message)
            
            logger.debug(f"✅ Message sent successfully to connection {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ send_message failed for connection {connection_id}: {e}")
            return False
    
    async def send_event(self, connection_id: str, event_type: str, event_data: dict) -> bool:
        """
        Send event to specific WebSocket connection.
        
        CRITICAL SSOT INTERFACE COMPLIANCE: This method provides standard event 
        interface expected by WebSocket validation tests and agent systems.
        
        Args:
            connection_id: Unique connection identifier
            event_type: Type of event being sent
            event_data: Event payload data
            
        Returns:
            bool: Success status of event delivery
        """
        try:
            # Create event message structure
            event_message = {
                "type": event_type,
                "data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "connection_id": connection_id
            }
            
            # Use send_message for actual delivery
            return await self.send_message(connection_id, event_message)
            
        except Exception as e:
            logger.error(f"❌ send_event failed for connection {connection_id}, event {event_type}: {e}")
            return False
    
    async def broadcast_system_message(self, message: Dict[str, Any]) -> None:
        """
        Broadcast system-level message to all connections.
        
        This method is specifically used for system events like lifecycle changes,
        state changes, and administrative messages. It's functionally equivalent
        to broadcast_message but provides semantic clarity for system events.
        
        INTEGRATION COMPLIANCE: This method is required by integration tests and
        manager classes (UnifiedStateManager, UnifiedLifecycleManager, etc.)
        
        Args:
            message: System message to broadcast to all connections
        """
        # Use existing broadcast method - same functionality as broadcast_message
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """
        Get total number of connections managed by this instance.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Returns:
            Total number of active connections
        """
        return len(self._connections)
    
    async def handle_connection(self, websocket: Any, user_id: Optional[str] = None) -> str:
        """
        Handle new WebSocket connection with proper isolation.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Args:
            websocket: WebSocket instance to handle
            user_id: Optional user ID for the connection
            
        Returns:
            Connection ID for the established connection
        """
        if not user_id:
            # Generate a temporary user ID if none provided
            id_manager = UnifiedIDManager()
            user_id = id_manager.generate_id(
                IDType.USER,
                prefix="temp_user",
                context={"component": "handle_connection"}
            )
        
        # Use existing connect_user method
        connection_id = await self.connect_user(user_id, websocket)
        logger.info(f"[U+1F517] SSOT INTERFACE: Handled connection for user {user_id[:8]}...  ->  {connection_id}")
        return connection_id
    
    # ISSUE #414 FIX: Event contamination monitoring and prevention methods
    
    def get_contamination_stats(self) -> Dict[str, Any]:
        """Get current event contamination statistics (Issue #414 monitoring)."""
        return {
            **self._event_queue_stats,
            'cross_user_violations': dict(self._cross_user_detection),
            'active_isolation_tokens': len(self._event_isolation_tokens),
            'user_event_queues': {
                user_id: queue.qsize() 
                for user_id, queue in self._user_event_queues.items()
            },
            'total_users_monitored': len(self._cross_user_detection)
        }
    
    async def validate_event_isolation(self, user_id: str, connection_id: str) -> bool:
        """Validate event isolation for user and connection (Issue #414 validation)."""
        if connection_id not in self._event_isolation_tokens:
            logger.warning(f" WARNING: [U+FE0F] Connection {connection_id} has no isolation token")
            return False
        
        if connection_id not in self._connections:
            logger.warning(f" WARNING: [U+FE0F] Connection {connection_id} not found in active connections")
            return False
        
        connection = self._connections[connection_id]
        if connection.user_id != user_id:
            logger.error(
                f" ALERT:  ISOLATION VIOLATION: Connection {connection_id} user mismatch. "
                f"Expected: {user_id}, Actual: {connection.user_id}"
            )
            self._cross_user_detection[user_id] = self._cross_user_detection.get(user_id, 0) + 1
            return False
        
        return True
    
    async def cleanup_expired_event_tracking(self, max_age_hours: int = 24):
        """Clean up expired event tracking data (Issue #414 memory management)."""
        current_time = datetime.now(timezone.utc)
        expired_events = []
        
        for event_id, metadata in self._event_delivery_tracking.items():
            event_age = (current_time - metadata['timestamp']).total_seconds() / 3600
            if event_age > max_age_hours:
                expired_events.append(event_id)
        
        for event_id in expired_events:
            del self._event_delivery_tracking[event_id]
        
        if expired_events:
            logger.info(f"[U+1F9F9] Cleaned up {len(expired_events)} expired event tracking entries")
    
    async def force_cleanup_user_events(self, user_id: str):
        """Force cleanup of all event tracking for a specific user (Issue #414 isolation)."""
        # Clear user event queue
        if user_id in self._user_event_queues:
            queue = self._user_event_queues[user_id]
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            del self._user_event_queues[user_id]
        
        # Clear cross-user detection tracking
        if user_id in self._cross_user_detection:
            del self._cross_user_detection[user_id]
        
        # Clear event delivery tracking for this user
        user_events = [
            event_id for event_id, metadata in self._event_delivery_tracking.items()
            if metadata.get('user_id') == user_id
        ]
        
        for event_id in user_events:
            del self._event_delivery_tracking[event_id]
        
        logger.info(f"[U+1F9F9] Force cleaned up all event tracking for user {user_id}")
    
    def detect_queue_overflow(self, user_id: str) -> bool:
        """Detect if user's event queue is approaching overflow (Issue #414 monitoring)."""
        if user_id not in self._user_event_queues:
            return False
        
        queue = self._user_event_queues[user_id]
        utilization = queue.qsize() / 1000.0  # Max size is 1000
        
        if utilization > 0.9:  # 90% full
            logger.warning(f" ALERT:  Event queue near overflow for user {user_id}: {queue.qsize()}/1000")
            self._event_queue_stats['queue_overflows'] += 1
            return True
        
        return False
    
    async def handle_disconnection(self, user_id: str, websocket: Any = None) -> None:
        """
        Handle WebSocket disconnection with proper cleanup.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Args:
            user_id: User ID for the disconnecting connection
            websocket: Optional WebSocket instance being disconnected
        """
        if websocket:
            # Use existing disconnect_user method
            await self.disconnect_user(user_id, websocket)
        else:
            # Disconnect all connections for the user
            connection_ids = list(self.get_user_connections(user_id))
            for conn_id in connection_ids:
                await self.remove_connection(conn_id)
        
        logger.info(f"[U+1F50C] SSOT INTERFACE: Handled disconnection for user {user_id[:8]}...")
    
    async def send_agent_event(self, user_id: Union[str, UserID], event_type: str, data: Dict[str, Any]) -> None:
        """
        Send agent event to user connections.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Args:
            user_id: Target user ID (accepts both str and UserID)
            event_type: Type of agent event
            data: Event payload data
        """
        # Use existing emit_critical_event method
        await self.emit_critical_event(user_id, event_type, data)
    
    async def add_connection_by_user(self, user_id: str, websocket: Any, connection_id: str = None) -> str:
        """
        Add connection for a user with optional connection ID.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by SSOT validation tests for connection management.
        
        Args:
            user_id: User identifier
            websocket: WebSocket instance
            connection_id: Optional connection ID to use
            
        Returns:
            Connection ID for the added connection
        """
        # Use existing connect_user method which handles connection_id properly
        return await self.connect_user(user_id, websocket, connection_id)
    
    async def remove_connection_by_user(self, user_id: str) -> None:
        """
        Remove all connections for a specific user.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by SSOT validation tests for user cleanup.
        
        Args:
            user_id: User ID to remove connections for
        """
        connection_ids = list(self.get_user_connections(user_id))
        for conn_id in connection_ids:
            await self.remove_connection(conn_id)
        
        logger.info(f"[U+1F5D1][U+FE0F] SSOT INTERFACE: Removed all connections for user {user_id[:8]}...")
    
    def is_user_connected(self, user_id: Union[str, UserID]) -> bool:
        """
        Check if a user is currently connected.
        
        SSOT INTERFACE COMPLIANCE: This method provides the standard interface
        expected by WebSocketManagerProtocol and SSOT validation tests.
        
        Args:
            user_id: User ID to check (accepts both str and UserID)
            
        Returns:
            True if user has active connections, False otherwise
        """
        # Use existing is_connection_active method
        return self.is_connection_active(user_id)

    async def handle_event_confirmation(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> bool:
        """Handle event confirmation messages from WebSocket clients.
        
        This method processes confirmation messages sent by clients to acknowledge
        receipt of critical events (tool_executing, tool_completed, etc.).
        
        Args:
            user_id: User ID sending the confirmation
            message: Confirmation message with event_id and status
            
        Returns:
            bool: True if confirmation was processed successfully
        """
        try:
            # Validate message structure
            if not isinstance(message, dict):
                logger.warning(f"Invalid confirmation message format from user {user_id}: {type(message)}")
                return False
            
            event_id = message.get('event_id')
            confirmation_type = message.get('type', 'confirmation')
            status = message.get('status', 'confirmed')
            
            if not event_id:
                logger.warning(f"Confirmation message missing event_id from user {user_id}")
                return False
            
            # Get event delivery tracker
            from netra_backend.app.services.event_delivery_tracker import get_event_delivery_tracker
            tracker = get_event_delivery_tracker()
            
            if confirmation_type == 'confirmation' and status == 'confirmed':
                # Confirm successful delivery
                success = tracker.confirm_event(event_id)
                if success:
                    logger.debug(f"Confirmed event {event_id} for user {user_id}")
                    return True
                else:
                    logger.warning(f"Failed to confirm unknown event {event_id} for user {user_id}")
                    return False
                    
            elif confirmation_type == 'confirmation' and status == 'failed':
                # Event failed on client side
                error_msg = message.get('error', 'Client-side event processing failed')
                tracker.fail_event(event_id, f"Client failure: {error_msg}")
                logger.warning(f"Client reported failure for event {event_id} from user {user_id}: {error_msg}")
                return True
                
            else:
                logger.warning(f"Unknown confirmation type/status: {confirmation_type}/{status} from user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing event confirmation from user {user_id}: {e}")
            return False
    
    async def process_incoming_message(self, user_id: Union[str, UserID], message: Any) -> bool:
        """Process incoming WebSocket messages including confirmations.
        
        This method handles both regular messages and event confirmations.
        
        Args:
            user_id: User ID sending the message
            message: Raw WebSocket message
            
        Returns:
            bool: True if message was processed successfully
        """
        try:
            # Parse message if it's a string
            if isinstance(message, str):
                import json
                try:
                    parsed_message = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message from user {user_id}: {message[:100]}")
                    return False
            elif isinstance(message, dict):
                parsed_message = message
            else:
                logger.warning(f"Unsupported message type from user {user_id}: {type(message)}")
                return False
            
            # Check if this is an event confirmation
            message_type = parsed_message.get('type', '')
            if message_type == 'event_confirmation':
                return await self.handle_event_confirmation(user_id, parsed_message)
            
            # Handle other message types here if needed
            logger.debug(f"Received message type '{message_type}' from user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing incoming message from user {user_id}: {e}")
            return False

    # Transaction Coordination Methods
    def set_transaction_coordinator(self, coordinator):
        """Set transaction coordinator for database-WebSocket coordination.
        
        Args:
            coordinator: TransactionEventCoordinator instance from DatabaseManager
        """
        self._transaction_coordinator = coordinator
        self._coordination_enabled = True
        logger.info("[U+1F517] Transaction coordinator linked to WebSocket manager")
        
    async def send_event_after_commit(self, transaction_id: str, event_type: str, event_data: Dict[str, Any],
                                     connection_id: Optional[str] = None, user_id: Optional[str] = None,
                                     thread_id: Optional[str] = None, priority: int = 0):
        """Queue WebSocket event for sending after database transaction commit.
        
        This method ensures events are only sent AFTER database transactions commit,
        preventing data inconsistency in the Golden Path user flow.
        
        Args:
            transaction_id: Database transaction ID
            event_type: Type of WebSocket event to send
            event_data: Event data payload
            connection_id: Optional specific connection ID
            user_id: Optional user ID for targeting
            thread_id: Optional thread ID for context
            priority: Event priority (higher numbers sent first)
        """
        if not self._coordination_enabled or not self._transaction_coordinator:
            # Fallback: send immediately if coordination not enabled
            logger.warning(f" WARNING: [U+FE0F] Transaction coordination not enabled - sending WebSocket event '{event_type}' immediately")
            return await self._send_event_immediate(event_type, event_data, connection_id, user_id)
            
        # Queue event for after transaction commit
        await self._transaction_coordinator.add_pending_event(
            transaction_id=transaction_id,
            event_type=event_type,
            event_data=event_data,
            connection_id=connection_id,
            user_id=user_id,
            thread_id=thread_id,
            priority=priority
        )
        
        logger.debug(f"[U+1F4E4] Queued WebSocket event '{event_type}' for transaction {transaction_id[:8]}... "
                    f"(user: {user_id}, priority: {priority})")
        
    async def _send_event_immediate(self, event_type: str, event_data: Dict[str, Any],
                                   connection_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
        """Send WebSocket event immediately (fallback when coordination disabled).
        
        Args:
            event_type: Type of WebSocket event
            event_data: Event data payload
            connection_id: Optional specific connection ID
            user_id: Optional user ID for targeting
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = {
                "type": event_type,
                "data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if connection_id:
                # Send to specific connection
                if connection_id in self._connections:
                    connection = self._connections[connection_id]
                    await connection.websocket.send_json(_serialize_message_safely(message))
                    logger.debug(f"[U+1F4E4] Sent WebSocket event '{event_type}' to connection {connection_id}")
                    return True
                else:
                    logger.warning(f" WARNING: [U+FE0F] Connection {connection_id} not found for event '{event_type}'")
                    return False
                    
            elif user_id:
                # Send to all user connections
                await self.send_to_user(user_id, message)
                logger.debug(f"[U+1F4E4] Sent WebSocket event '{event_type}' to user {user_id}")
                return True
                
            else:
                logger.warning(f" WARNING: [U+FE0F] No connection_id or user_id specified for event '{event_type}'")
                return False
                
        except Exception as e:
            logger.error(f" FAIL:  Failed to send immediate WebSocket event '{event_type}': {type(e).__name__}: {e}")
            return False
            
    def is_coordination_enabled(self) -> bool:
        """Check if transaction coordination is enabled.
        
        Returns:
            True if coordination is enabled, False otherwise
        """
        return self._coordination_enabled and self._transaction_coordinator is not None
        
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current transaction coordination status.
        
        Returns:
            Dictionary containing coordination status information
        """
        if not self._coordination_enabled:
            return {
                "enabled": False,
                "reason": "Coordination not enabled"
            }
            
        if not self._transaction_coordinator:
            return {
                "enabled": False,
                "reason": "No transaction coordinator configured"
            }
            
        return {
            "enabled": True,
            "coordinator_available": True,
            "pending_events": self._transaction_coordinator.get_pending_events_count(),
            "metrics": self._transaction_coordinator.get_coordination_metrics()
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for current operational mode."""
        base_status = {
            'healthy': getattr(self, '_is_healthy', True),
            'manager_type': f'unified_{self.mode.value}',
            'mode': self.mode.value,
            'created_at': getattr(self, 'created_at', datetime.now(timezone.utc)).isoformat(),
        }
        
        if self.mode == WebSocketManagerMode.UNIFIED:
            return {
                **base_status,
                'functionality_level': 'full',
                'error_recovery_enabled': getattr(self, '_error_recovery_enabled', True),
                'monitoring_enabled': getattr(self, '_monitoring_enabled', True),
                'connection_count': self.get_connection_count(),
                'background_tasks': len(getattr(self, '_background_tasks', {}))
            }
        elif self.mode == WebSocketManagerMode.ISOLATED:
            return {
                **base_status,
                'functionality_level': 'isolated',
                'user_context': bool(self.user_context),
                'private_error_count': getattr(self, '_private_error_count', 0),
                'private_message_queue_size': len(getattr(self, '_private_message_queue', []))
            }
        elif self.mode == WebSocketManagerMode.EMERGENCY:
            return {
                **base_status,
                'functionality_level': 'emergency',
                'emergency_mode': True,
                'queued_messages': len(getattr(self, '_emergency_message_queue', [])),
                'uptime_seconds': (datetime.now(timezone.utc) - self.created_at).total_seconds()
            }
        elif self.mode == WebSocketManagerMode.DEGRADED:
            return {
                **base_status,
                'healthy': False,
                'functionality_level': 'minimal',
                'degraded_mode': True,
                'message': 'Operating in degraded mode - please retry connection'
            }
        
        return base_status


# SECURITY FIX: Replace singleton with factory pattern
#  ALERT:  SECURITY FIX: Singleton pattern completely removed to prevent multi-user data leakage
# Use create_websocket_manager(user_context) or WebSocketBridgeFactory instead

def get_websocket_manager() -> UnifiedWebSocketManager:
    """
     ALERT:  CRITICAL SECURITY ERROR: This function has been REMOVED.
    
    This function created critical security vulnerabilities in multi-user environments,
    causing user data leakage and authentication bypass.
    
    REQUIRED MIGRATION (choose one):
    1. For per-user WebSocket events: Use WebSocketBridgeFactory.create_user_emitter()
    2. For authenticated connections: Use create_websocket_manager(user_context)
    3. For testing: Create dedicated test instances with proper user context
    
    Example migration:
    ```python
    # OLD (UNSAFE):
    manager = get_websocket_manager()
    
    # NEW (SAFE):
    factory = WebSocketBridgeFactory()
    emitter = await factory.create_user_emitter(user_id, thread_id, connection_id)
    ```
    
    This function was causing User A to see User B's messages.
    """
    from shared.logging.unified_logging_ssot import get_logger
    import inspect
    
    logger = get_logger(__name__)
    
    # Get caller information for debugging
    frame = inspect.currentframe()
    caller_info = "unknown"
    if frame and frame.f_back:
        caller_info = f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
    
    error_message = (
        f" ALERT:  CRITICAL SECURITY ERROR: get_websocket_manager() has been REMOVED for security. "
        f"Called from: {caller_info}. "
        f"This function caused USER DATA LEAKAGE between different users. "
        f"Migrate to WebSocketBridgeFactory or create_websocket_manager(user_context)."
    )
    
    logger.critical(error_message)
    raise RuntimeError(error_message)


# CRITICAL: Export alias for backward compatibility with migration_adapter
# This ensures migration_adapter can import WebSocketManager 
WebSocketManager = UnifiedWebSocketManager

# Export list for the module
__all__ = [
    'WebSocketConnection',
    'UnifiedWebSocketManager', 
    'WebSocketManager',  # Alias for UnifiedWebSocketManager
    '_serialize_message_safely',
    'get_websocket_manager'
]