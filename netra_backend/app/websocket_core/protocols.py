"""
WebSocket Manager Protocol Interface - Five Whys ROOT CAUSE Prevention

This module defines the formal WebSocketManagerProtocol interface that prevents 
the ROOT CAUSE identified in the Five Whys analysis: "lack of formal interface 
contracts causing implementation drift during migrations."

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) 
- Business Goal: Prevent critical system failures from interface drift
- Value Impact: Ensures consistent WebSocket communication across all implementations
- Revenue Impact: Prevents user-facing errors that destroy confidence and retention

Five Whys Context:
- WHY #5 (ROOT CAUSE): No formal WebSocket Manager interface contract exists
- SPECIFIC ISSUE: IsolatedWebSocketManager missing get_connection_id_by_websocket
- SYSTEMIC PROBLEM: Migrations focus on functionality but fail to maintain interface compatibility

This protocol ensures ALL WebSocket manager implementations provide the same interface,
preventing future AttributeError and method missing errors.
"""

import asyncio
from typing import Dict, Optional, Set, Any, List, Protocol, runtime_checkable
from datetime import datetime
from abc import abstractmethod

from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@runtime_checkable
class WebSocketManagerProtocol(Protocol):
    """
    CRITICAL INTERFACE CONTRACT: Formal protocol for all WebSocket manager implementations.
    
    This protocol defines the complete interface that ANY WebSocket manager implementation
    MUST provide. It prevents the root cause identified in Five Whys analysis by ensuring
    interface compatibility is maintained during migrations.
    
    ROOT CAUSE PREVENTION: Any implementation that claims to be a WebSocket manager
    MUST implement ALL these methods with the correct signatures, preventing
    AttributeError exceptions during runtime.
    
    INTERFACE VALIDATION: Use validate_manager_protocol() to check compliance.
    """
    
    # ===========================================================================
    # CONNECTION MANAGEMENT METHODS
    # ===========================================================================
    
    @abstractmethod
    async def add_connection(self, connection: WebSocketConnection) -> None:
        """
        Add a new WebSocket connection to the manager.
        
        Args:
            connection: WebSocketConnection instance to add
            
        Raises:
            ValueError: If connection is invalid or conflicts with existing connections
        """
        ...
    
    @abstractmethod
    async def remove_connection(self, connection_id: str) -> None:
        """
        Remove a WebSocket connection from the manager.
        
        Args:
            connection_id: ID of connection to remove
        """
        ...
    
    @abstractmethod
    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Retrieve a specific connection by ID.
        
        Args:
            connection_id: ID of connection to retrieve
            
        Returns:
            WebSocketConnection instance if found, None otherwise
        """
        ...
    
    @abstractmethod
    def get_user_connections(self, user_id: str) -> Set[str]:
        """
        Get all connection IDs for a specific user.
        
        Args:
            user_id: User ID to get connections for
            
        Returns:
            Set of connection IDs belonging to the user
        """
        ...
    
    @abstractmethod
    def is_connection_active(self, user_id: str) -> bool:
        """
        Check if a user has any active WebSocket connections.
        CRITICAL for authentication event validation.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user has at least one active connection, False otherwise
        """
        ...
    
    # ===========================================================================
    # WEBSOCKET LOOKUP METHODS (Five Whys Critical Methods)
    # ===========================================================================
    
    @abstractmethod
    def get_connection_id_by_websocket(self, websocket) -> Optional[str]:
        """
        FIVE WHYS CRITICAL METHOD: Get connection ID for a given WebSocket instance.
        
        This method was MISSING from IsolatedWebSocketManager, causing the error
        that triggered the Five Whys analysis. It MUST be implemented by all
        WebSocket managers to prevent AttributeError exceptions.
        
        Args:
            websocket: WebSocket instance to search for
            
        Returns:
            Connection ID if found, None otherwise
            
        Root Cause Prevention:
            This method prevents "AttributeError: 'IsolatedWebSocketManager' object 
            has no attribute 'get_connection_id_by_websocket'" errors during 
            agent execution and thread management operations.
        """
        ...
    
    @abstractmethod
    def update_connection_thread(self, connection_id: str, thread_id: str) -> bool:
        """
        FIVE WHYS CRITICAL METHOD: Update thread association for a connection.
        
        This method is called alongside get_connection_id_by_websocket in agent
        handler patterns. Both must exist for proper thread management.
        
        Args:
            connection_id: Connection ID to update
            thread_id: New thread ID to associate
            
        Returns:
            True if update successful, False if connection not found
        """
        ...
    
    # ===========================================================================
    # MESSAGE SENDING METHODS
    # ===========================================================================
    
    @abstractmethod
    async def send_to_user(self, user_id: str, message: Dict[str, Any]) -> None:
        """
        Send a message to all connections for a specific user.
        
        Args:
            user_id: Target user ID
            message: Message payload to send
            
        Raises:
            RuntimeError: If manager is not active or message delivery fails critically
        """
        ...
    
    @abstractmethod
    async def emit_critical_event(self, user_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Emit a critical event to a specific user with delivery tracking.
        
        This is the primary interface for WebSocket event notifications
        that power the user chat experience.
        
        Args:
            user_id: Target user ID
            event_type: Event type (e.g., 'agent_started', 'tool_executing')
            data: Event payload
            
        Raises:
            ValueError: If parameters are invalid
        """
        ...
    
    # ===========================================================================
    # HEALTH AND MONITORING METHODS
    # ===========================================================================
    
    @abstractmethod
    def get_connection_health(self, user_id: str) -> Dict[str, Any]:
        """
        Get detailed connection health information for a user.
        
        Args:
            user_id: User ID to check health for
            
        Returns:
            Dictionary containing health metrics and connection status
        """
        ...
    
    # ===========================================================================
    # COMPATIBILITY METHODS (for legacy interfaces)
    # ===========================================================================
    
    @abstractmethod
    async def send_to_thread(self, thread_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to a thread (compatibility method).
        
        Args:
            thread_id: Thread ID to send to
            message: Message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        ...


class WebSocketManagerProtocolValidator:
    """
    Validator for WebSocket Manager Protocol compliance.
    
    This class provides utilities to validate that WebSocket manager implementations
    properly implement the WebSocketManagerProtocol interface, preventing the
    root cause identified in the Five Whys analysis.
    """
    
    @staticmethod
    def validate_manager_protocol(manager: Any) -> Dict[str, Any]:
        """
        Validate that a manager implementation complies with WebSocketManagerProtocol.
        
        This prevents the root cause by ensuring all required methods exist
        before the manager is used in production code.
        
        Args:
            manager: WebSocket manager instance to validate
            
        Returns:
            Dictionary with validation results and compliance details
            
        Example:
            >>> from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
            >>> manager = create_websocket_manager(user_context)
            >>> result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
            >>> if not result['compliant']:
            ...     raise ValueError(f"Manager not protocol compliant: {result['missing_methods']}")
        """
        validation_result = {
            'compliant': False,
            'manager_type': type(manager).__name__,
            'manager_module': getattr(type(manager), '__module__', 'unknown'),
            'missing_methods': [],
            'invalid_signatures': [],
            'method_check_details': {},
            'protocol_version': '1.0.0',
            'validation_timestamp': datetime.utcnow().isoformat()
        }
        
        # Define required methods with their expected signatures
        required_methods = {
            # Connection Management
            'add_connection': {'async': True, 'params': ['connection'], 'returns': None},
            'remove_connection': {'async': True, 'params': ['connection_id'], 'returns': None},
            'get_connection': {'async': False, 'params': ['connection_id'], 'returns': 'Optional[WebSocketConnection]'},
            'get_user_connections': {'async': False, 'params': ['user_id'], 'returns': 'Set[str]'},
            'is_connection_active': {'async': False, 'params': ['user_id'], 'returns': bool},
            
            # Five Whys Critical Methods
            'get_connection_id_by_websocket': {'async': False, 'params': ['websocket'], 'returns': 'Optional[str]'},
            'update_connection_thread': {'async': False, 'params': ['connection_id', 'thread_id'], 'returns': bool},
            
            # Message Sending
            'send_to_user': {'async': True, 'params': ['user_id', 'message'], 'returns': None},
            'emit_critical_event': {'async': True, 'params': ['user_id', 'event_type', 'data'], 'returns': None},
            
            # Health and Monitoring  
            'get_connection_health': {'async': False, 'params': ['user_id'], 'returns': 'Dict[str, Any]'},
            
            # Compatibility
            'send_to_thread': {'async': True, 'params': ['thread_id', 'message'], 'returns': bool}
        }
        
        try:
            # Check if it's a runtime_checkable Protocol instance
            is_protocol_instance = isinstance(manager, WebSocketManagerProtocol)
            validation_result['is_protocol_instance'] = is_protocol_instance
            
            # Check each required method
            for method_name, expected_sig in required_methods.items():
                method_details = {
                    'exists': False,
                    'callable': False,
                    'async_correct': False,
                    'signature_info': None
                }
                
                # Check if method exists
                if hasattr(manager, method_name):
                    method_details['exists'] = True
                    method = getattr(manager, method_name)
                    
                    # Check if it's callable
                    if callable(method):
                        method_details['callable'] = True
                        
                        # Check async/sync correctness
                        is_async = asyncio.iscoroutinefunction(method)
                        method_details['async_correct'] = is_async == expected_sig['async']
                        method_details['is_async'] = is_async
                        method_details['expected_async'] = expected_sig['async']
                        
                        # Get signature information
                        import inspect
                        try:
                            sig = inspect.signature(method)
                            method_details['signature_info'] = {
                                'parameters': list(sig.parameters.keys()),
                                'parameter_count': len(sig.parameters),
                                'expected_params': expected_sig['params'],
                                'return_annotation': str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else 'None'
                            }
                        except Exception as e:
                            method_details['signature_error'] = str(e)
                    else:
                        validation_result['invalid_signatures'].append(f"{method_name}: not callable")
                else:
                    validation_result['missing_methods'].append(method_name)
                
                validation_result['method_check_details'][method_name] = method_details
            
            # Determine overall compliance
            validation_result['compliant'] = (
                len(validation_result['missing_methods']) == 0 and
                len(validation_result['invalid_signatures']) == 0 and
                all(
                    details['exists'] and details['callable'] and details['async_correct']
                    for details in validation_result['method_check_details'].values()
                )
            )
            
            # Add summary statistics
            validation_result['summary'] = {
                'total_methods_required': len(required_methods),
                'methods_present': sum(1 for d in validation_result['method_check_details'].values() if d['exists']),
                'methods_callable': sum(1 for d in validation_result['method_check_details'].values() if d['callable']),
                'methods_async_correct': sum(1 for d in validation_result['method_check_details'].values() if d['async_correct']),
                'compliance_percentage': round(
                    (sum(1 for d in validation_result['method_check_details'].values() 
                         if d['exists'] and d['callable'] and d['async_correct']) / len(required_methods)) * 100, 1
                )
            }
            
            # Log validation results
            if validation_result['compliant']:
                logger.info(
                    f"✅ WebSocket Manager Protocol validation PASSED for {validation_result['manager_type']} "
                    f"({validation_result['summary']['compliance_percentage']}% compliant)"
                )
            else:
                logger.error(
                    f"❌ WebSocket Manager Protocol validation FAILED for {validation_result['manager_type']} "
                    f"({validation_result['summary']['compliance_percentage']}% compliant). "
                    f"Missing methods: {validation_result['missing_methods']}, "
                    f"Invalid signatures: {validation_result['invalid_signatures']}"
                )
                
        except Exception as e:
            validation_result['validation_error'] = str(e)
            validation_result['compliant'] = False
            logger.error(f"Protocol validation failed with exception: {e}")
        
        return validation_result
    
    @staticmethod
    def require_protocol_compliance(manager: Any, error_context: str = "WebSocket Manager") -> None:
        """
        Require that a manager is protocol compliant, raising detailed error if not.
        
        This enforces the protocol compliance and prevents the Five Whys root cause
        by failing fast with detailed error information.
        
        Args:
            manager: Manager to validate
            error_context: Context string for error messages
            
        Raises:
            RuntimeError: If manager is not protocol compliant with detailed diagnostics
        """
        validation = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)
        
        if not validation['compliant']:
            error_details = []
            
            if validation['missing_methods']:
                error_details.append(f"Missing methods: {', '.join(validation['missing_methods'])}")
            
            if validation['invalid_signatures']:
                error_details.append(f"Invalid signatures: {', '.join(validation['invalid_signatures'])}")
            
            # Add specific diagnostics for Five Whys critical methods
            five_whys_methods = ['get_connection_id_by_websocket', 'update_connection_thread']
            five_whys_issues = []
            for method in five_whys_methods:
                if method in validation['missing_methods']:
                    five_whys_issues.append(f"FIVE WHYS CRITICAL: Missing {method} method")
            
            error_message = (
                f"🚨 PROTOCOL COMPLIANCE FAILURE: {error_context} does not implement WebSocketManagerProtocol. "
                f"Manager type: {validation['manager_type']} from {validation['manager_module']}. "
                f"Compliance: {validation['summary']['compliance_percentage']}%. "
                f"Issues: {'; '.join(error_details)}. "
            )
            
            if five_whys_issues:
                error_message += f"Five Whys Root Cause Prevention: {'; '.join(five_whys_issues)}. "
            
            error_message += (
                f"This prevents the root cause identified in Five Whys analysis: "
                f"'lack of formal interface contracts causing implementation drift'. "
                f"ALL WebSocket managers MUST implement the complete protocol interface."
            )
            
            logger.critical(error_message)
            raise RuntimeError(error_message)
        
        logger.info(f"✅ Protocol compliance verified for {error_context}: {validation['manager_type']}")


def get_protocol_documentation() -> str:
    """
    Get comprehensive documentation for the WebSocketManagerProtocol.
    
    Returns:
        Detailed documentation string explaining the protocol requirements
    """
    return """
WebSocketManagerProtocol Interface Documentation

PURPOSE:
This protocol prevents the root cause identified in Five Whys analysis:
"lack of formal interface contracts causing implementation drift during migrations."

CRITICAL CONTEXT:
The Five Whys analysis revealed that IsolatedWebSocketManager was missing the
get_connection_id_by_websocket method, causing AttributeError exceptions during
agent execution. This protocol ensures ALL implementations provide this method.

REQUIRED METHODS:

1. CONNECTION MANAGEMENT:
   - add_connection(connection) -> None (async)
   - remove_connection(connection_id) -> None (async) 
   - get_connection(connection_id) -> Optional[WebSocketConnection]
   - get_user_connections(user_id) -> Set[str]
   - is_connection_active(user_id) -> bool

2. FIVE WHYS CRITICAL METHODS:
   - get_connection_id_by_websocket(websocket) -> Optional[str]
   - update_connection_thread(connection_id, thread_id) -> bool

3. MESSAGE SENDING:
   - send_to_user(user_id, message) -> None (async)
   - emit_critical_event(user_id, event_type, data) -> None (async)

4. HEALTH MONITORING:
   - get_connection_health(user_id) -> Dict[str, Any]

5. COMPATIBILITY:
   - send_to_thread(thread_id, message) -> bool (async)

VALIDATION:
Use WebSocketManagerProtocolValidator.validate_manager_protocol() to check compliance.
Use WebSocketManagerProtocolValidator.require_protocol_compliance() to enforce compliance.

MIGRATION GUIDE:
1. Import the protocol: from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
2. Make your manager implement the protocol: class MyManager(WebSocketManagerProtocol)
3. Implement ALL required methods with correct signatures
4. Validate compliance before deployment

FIVE WHYS PREVENTION:
This protocol directly addresses WHY #5 from the Five Whys analysis by ensuring
formal interface contracts exist and are enforced for all WebSocket managers.
"""


class WebSocketProtocol:
    """Simple WebSocket protocol class for integration test compatibility."""
    
    def __init__(self, websocket=None, connection_id: str = None, user_id: str = None):
        self.websocket = websocket
        self.connection_id = connection_id
        self.user_id = user_id
        self.is_active = True
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message through websocket."""
        try:
            if self.websocket and hasattr(self.websocket, 'send_json'):
                await self.websocket.send_json(message)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def close(self) -> None:
        """Close websocket connection."""
        self.is_active = False
        if self.websocket and hasattr(self.websocket, 'close'):
            await self.websocket.close()


__all__ = [
    'WebSocketManagerProtocol',
    'WebSocketManagerProtocolValidator',
    'WebSocketProtocol',
    'get_protocol_documentation'
]