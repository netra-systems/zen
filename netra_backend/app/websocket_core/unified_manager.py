"""Unified WebSocket Manager - SSOT for WebSocket connection management.

This module is the single source of truth for WebSocket connection management.
"""

import asyncio
import json
from enum import Enum
from typing import Dict, Optional, Set, Any, List, Union
from dataclasses import dataclass
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from shared.types.core_types import (
    UserID, ThreadID, ConnectionID, WebSocketID, RequestID,
    ensure_user_id, ensure_thread_id, ensure_websocket_id
)
# Import UnifiedIDManager for SSOT ID generation
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

# Import the protocol after it's defined to avoid circular imports
logger = central_logger.get_logger(__name__)


class WebSocketManagerMode(Enum):
    """Operational modes for WebSocket manager."""
    UNIFIED = "unified"        # Default full-featured mode
    ISOLATED = "isolated"      # User-isolated mode with private state
    EMERGENCY = "emergency"    # Emergency fallback with minimal features
    DEGRADED = "degraded"      # Degraded service mode for last resort


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
    - Enum objects (WebSocketState, etc.) → converted to string values
    - Pydantic models → model_dump(mode='json') for datetime handling  
    - Complex objects with to_dict() method
    - Datetime objects → ISO string format
    - Dataclasses → converted to dict
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
            return message.name.lower()  # CONNECTED → "connected"
    except (ImportError, AttributeError) as e:
        logger.debug(f"Starlette WebSocketState import failed (non-critical): {e}")
    
    try:
        from fastapi.websockets import WebSocketState as FastAPIWebSocketState  
        if isinstance(message, FastAPIWebSocketState):
            return message.name.lower()  # CONNECTED → "connected"
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
    
    # Handle objects with to_dict method (DeepAgentState, etc.)
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
    """Compatibility registry for legacy tests."""
    
    def __init__(self, manager):
        self.manager = manager
    
    async def register_connection(self, user_id: str, connection_info):
        """Register a connection for test compatibility."""
        # Convert ConnectionInfo to WebSocketConnection format for the unified manager
        websocket_conn = WebSocketConnection(
            connection_id=connection_info.connection_id,
            user_id=user_id,
            websocket=connection_info.websocket,
            connected_at=connection_info.connected_at,
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
    
    🚨 FIVE WHYS ROOT CAUSE PREVENTION: This class implements the same interface
    as WebSocketManagerProtocol to ensure consistency with IsolatedWebSocketManager.
    
    While this class predates the protocol, it provides all required methods to
    maintain interface compatibility and prevent the root cause identified in
    Five Whys analysis: "lack of formal interface contracts."
    
    ENHANCED: Eliminates race conditions by providing connection-level isolation:
    - Per-user connection locks prevent race conditions during concurrent operations
    - Thread-safe connection management with user-specific isolation
    - Connection state validation prevents silent failures
    """
    
    def __init__(self, mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED, user_context: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize UnifiedWebSocketManager with operational mode support.
        
        Args:
            mode: Operational mode for the manager (unified, isolated, emergency, degraded)
            user_context: User execution context for isolated mode
            config: Configuration dictionary for emergency/degraded modes
        """
        self.mode = mode
        self.user_context = user_context
        self.config = config or {}
        
        # Core connection management
        self._connections: Dict[str, WebSocketConnection] = {}
        self._user_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        
        # RACE CONDITION FIX: Add per-user connection locks
        self._user_connection_locks: Dict[str, asyncio.Lock] = {}
        self._connection_lock_creation_lock = asyncio.Lock()
        
        # Mode-specific initialization
        if mode == WebSocketManagerMode.ISOLATED:
            if user_context is None:
                raise ValueError("user_context is required for ISOLATED mode")
            self._initialize_isolated_mode(user_context)
        elif mode == WebSocketManagerMode.EMERGENCY:
            self._initialize_emergency_mode(config or {})
        elif mode == WebSocketManagerMode.DEGRADED:
            self._initialize_degraded_mode(config or {})
        else:  # UNIFIED mode
            self._initialize_unified_mode()
        
        # Add compatibility registry for legacy tests
        self.registry = RegistryCompat(self)
        
        # Add compatibility for legacy tests expecting connection_manager
        self._connection_manager = self
        self.connection_manager = self
        self.active_connections = {}  # Compatibility mapping
        self.connection_registry = {}  # Registry for connection objects
        
        logger.info(f"UnifiedWebSocketManager initialized in {mode.value} mode")
    
    def _initialize_unified_mode(self):
        """Initialize unified mode with full feature set."""
        # Enhanced error handling and recovery system
        self._message_recovery_queue: Dict[str, List[Dict]] = {}  # user_id -> [messages]
        self._connection_error_count: Dict[str, int] = {}  # user_id -> error_count
        self._last_error_time: Dict[str, datetime] = {}  # user_id -> last_error_timestamp
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
        # Validate connection before adding
        if not connection.user_id:
            raise ValueError("Connection must have a valid user_id")
        if not connection.connection_id:
            raise ValueError("Connection must have a valid connection_id")
            
        # Use user-specific lock for connection operations
        user_lock = await self._get_user_connection_lock(connection.user_id)
        
        async with user_lock:
            async with self._lock:
                self._connections[connection.connection_id] = connection
                if connection.user_id not in self._user_connections:
                    self._user_connections[connection.user_id] = set()
                self._user_connections[connection.user_id].add(connection.connection_id)
                
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
                logger.info(f"Processing {len(queued_messages)} queued messages for user {connection.user_id}")
                # HANG FIX: Await the processing to ensure messages are sent before method returns
                # This prevents test hanging where the test expects messages but they're still processing
                try:
                    await asyncio.wait_for(
                        self._process_queued_messages(connection.user_id), 
                        timeout=5.0  # Reasonable timeout to prevent infinite hang
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Timeout processing queued messages for user {connection.user_id}")
                except Exception as e:
                    logger.error(f"Error processing queued messages for user {connection.user_id}: {e}")
    
    async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None:
        """Remove a WebSocket connection with thread safety and type validation."""
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
                    if connection.user_id in self._user_connections:
                        self._user_connections[connection.user_id].discard(connection_id)
                        if not self._user_connections[connection.user_id]:
                            del self._user_connections[connection.user_id]
                    
                    # Update compatibility mapping
                    if connection.user_id in self.active_connections:
                        self.active_connections[connection.user_id] = [
                            c for c in self.active_connections[connection.user_id]
                            if c.connection_id != connection_id
                        ]
                        if not self.active_connections[connection.user_id]:
                            del self.active_connections[connection.user_id]
                    
                    logger.info(f"Removed connection {connection_id} (thread-safe)")
    
    def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]:
        """Get a specific connection with type validation."""
        validated_connection_id = str(connection_id)
        return self._connections.get(validated_connection_id)
    
    def get_user_connections(self, user_id: Union[str, UserID]) -> Set[str]:
        """Get all connections for a user with type validation."""
        validated_user_id = ensure_user_id(user_id)
        return self._user_connections.get(validated_user_id, set()).copy()
    
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
        # Handle mode-specific behavior
        if self.mode == WebSocketManagerMode.EMERGENCY:
            return await self._send_emergency_message(user_id, message)
        elif self.mode == WebSocketManagerMode.DEGRADED:
            return await self._send_degraded_message(user_id, message)
        elif self.mode == WebSocketManagerMode.ISOLATED:
            return await self._send_isolated_message(user_id, message)
        
        # Unified mode (default) handling
        # Validate user_id
        validated_user_id = ensure_user_id(user_id)
        
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
                logger.info("🔍 GCP staging environment auto-detected - adjusting WebSocket retry configuration")
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
                    'metadata': connection.metadata or {}
                })
        
        return {
            'user_id': validated_user_id,
            'total_connections': total_connections,
            'active_connections': active_connections,
            'has_active_connections': active_connections > 0,
            'connections': connection_details
        }
    
    async def connect_user(self, user_id: str, websocket: Any, connection_id: str = None) -> Any:
        """Legacy compatibility method for connecting a user.
        
        Args:
            user_id: User identifier
            websocket: WebSocket connection
            connection_id: Optional preliminary connection ID to preserve state machine continuity
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
            connected_at=datetime.now()
        )
        await self.add_connection(connection)
        
        # Return a ConnectionInfo-like object for compatibility
        conn_info = type('ConnectionInfo', (), {
            'user_id': user_id,
            'connection_id': final_connection_id,
            'websocket': websocket
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
                jitter = base_backoff * 0.1 * (0.5 - random.random())  # ±5% jitter
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
                    f"{old_thread_id} → {validated_thread_id}"
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
        logger.info(f"🔗 SSOT INTERFACE: Handled connection for user {user_id[:8]}... → {connection_id}")
        return connection_id
    
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
        
        logger.info(f"🔌 SSOT INTERFACE: Handled disconnection for user {user_id[:8]}...")
    
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
        
        logger.info(f"🗑️ SSOT INTERFACE: Removed all connections for user {user_id[:8]}...")
    
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
# 🚨 SECURITY FIX: Singleton pattern completely removed to prevent multi-user data leakage
# Use create_websocket_manager(user_context) or WebSocketBridgeFactory instead

def get_websocket_manager() -> UnifiedWebSocketManager:
    """
    🚨 CRITICAL SECURITY ERROR: This function has been REMOVED.
    
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
    from netra_backend.app.logging_config import central_logger
    import inspect
    
    logger = central_logger.get_logger(__name__)
    
    # Get caller information for debugging
    frame = inspect.currentframe()
    caller_info = "unknown"
    if frame and frame.f_back:
        caller_info = f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
    
    error_message = (
        f"🚨 CRITICAL SECURITY ERROR: get_websocket_manager() has been REMOVED for security. "
        f"Called from: {caller_info}. "
        f"This function caused USER DATA LEAKAGE between different users. "
        f"Migrate to WebSocketBridgeFactory or create_websocket_manager(user_context)."
    )
    
    logger.critical(error_message)
    raise RuntimeError(error_message)