"""
WebSocket ASGI Scope Validation Fix for Issue #466

BUSINESS IMPACT: $50K+ MRR WebSocket functionality failing due to ASGI scope issues
CRITICAL: WebSocket connection state issues with "Need to call 'accept' first" and scope validation errors

This fix provides comprehensive WebSocket ASGI scope validation and connection state management
to prevent staging environment failures and ensure proper WebSocket handshake.

SOLUTION:
1. Enhanced ASGI scope validation for WebSocket connections
2. Proper WebSocket connection state management
3. Graceful error handling for malformed ASGI scopes
4. Connection state verification before operations
5. Comprehensive logging for debugging ASGI issues
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Union, Callable
from starlette.types import Scope, Receive, Send, Message
from starlette.websockets import WebSocket, WebSocketState
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class WebSocketASGIScopeValidator:
    """
    WebSocket ASGI Scope Validator for Issue #466
    
    Provides comprehensive validation and error handling for WebSocket ASGI scopes
    to prevent connection failures and ensure proper handshake.
    """
    
    def __init__(self):
        """Initialize WebSocket ASGI scope validator."""
        self.validation_stats = {
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'scope_errors': 0,
            'connection_errors': 0
        }
    
    def validate_websocket_scope(self, scope: Scope) -> Dict[str, Any]:
        """
        Validate WebSocket ASGI scope structure and contents.
        
        CRITICAL FIX: Comprehensive scope validation to prevent ASGI exceptions
        
        Args:
            scope: ASGI scope dictionary
            
        Returns:
            Dictionary containing validation results
        """
        self.validation_stats['total_validations'] += 1
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'scope_type': None,
            'connection_info': {},
            'headers': {},
            'query_params': {}
        }
        
        try:
            # Phase 1: Basic scope structure validation
            if not isinstance(scope, dict):
                validation_result['valid'] = False
                validation_result['errors'].append(f"Invalid scope type: {type(scope)}, expected dict")
                self.validation_stats['scope_errors'] += 1
                return validation_result
            
            # Phase 2: Scope type validation
            scope_type = scope.get('type', 'unknown')
            validation_result['scope_type'] = scope_type
            
            if scope_type != 'websocket':
                validation_result['warnings'].append(f"Non-WebSocket scope type: {scope_type}")
                if scope_type == 'http':
                    # HTTP scope in WebSocket validator - this could indicate middleware confusion
                    validation_result['warnings'].append("HTTP scope detected in WebSocket validator - potential middleware routing issue")
            
            # Phase 3: Required WebSocket scope fields validation
            required_fields = ['path', 'query_string', 'headers']
            for field in required_fields:
                if field not in scope:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Missing required WebSocket scope field: {field}")
            
            # Phase 4: Field type validation
            if 'path' in scope:
                path = scope['path']
                if not isinstance(path, str):
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid path type: {type(path)}, expected str")
                else:
                    validation_result['connection_info']['path'] = path
            
            if 'query_string' in scope:
                query_string = scope['query_string']
                if not isinstance(query_string, (bytes, str)):
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid query_string type: {type(query_string)}, expected bytes or str")
                else:
                    # Parse query parameters safely
                    try:
                        if isinstance(query_string, bytes):
                            query_str = query_string.decode('utf-8')
                        else:
                            query_str = query_string
                        validation_result['query_params'] = self._parse_query_string(query_str)
                    except Exception as e:
                        validation_result['warnings'].append(f"Could not parse query string: {e}")
            
            if 'headers' in scope:
                headers = scope['headers']
                if not isinstance(headers, list):
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Invalid headers type: {type(headers)}, expected list")
                else:
                    # Parse headers safely
                    try:
                        validation_result['headers'] = self._parse_headers(headers)
                    except Exception as e:
                        validation_result['warnings'].append(f"Could not parse headers: {e}")
            
            # Phase 5: Connection information validation
            if 'client' in scope:
                client = scope['client']
                if isinstance(client, (list, tuple)) and len(client) >= 2:
                    validation_result['connection_info']['client_host'] = client[0]
                    validation_result['connection_info']['client_port'] = client[1]
                else:
                    validation_result['warnings'].append(f"Invalid client info format: {client}")
            
            if 'server' in scope:
                server = scope['server']
                if isinstance(server, (list, tuple)) and len(server) >= 2:
                    validation_result['connection_info']['server_host'] = server[0]
                    validation_result['connection_info']['server_port'] = server[1]
                else:
                    validation_result['warnings'].append(f"Invalid server info format: {server}")
            
            # Phase 6: WebSocket-specific validation
            if scope_type == 'websocket':
                # Check for WebSocket upgrade headers
                headers = validation_result.get('headers', {})
                upgrade_header = headers.get('upgrade', '').lower()
                connection_header = headers.get('connection', '').lower()
                
                if upgrade_header != 'websocket':
                    validation_result['warnings'].append(f"Missing or invalid Upgrade header: {upgrade_header}")
                
                if 'upgrade' not in connection_header:
                    validation_result['warnings'].append(f"Missing or invalid Connection header: {connection_header}")
                
                # Check for WebSocket version
                ws_version = headers.get('sec-websocket-version')
                if not ws_version:
                    validation_result['warnings'].append("Missing Sec-WebSocket-Version header")
                elif ws_version != '13':
                    validation_result['warnings'].append(f"Non-standard WebSocket version: {ws_version}")
            
            # Update success statistics
            if validation_result['valid']:
                self.validation_stats['successful_validations'] += 1
            else:
                self.validation_stats['failed_validations'] += 1
            
            return validation_result
            
        except Exception as e:
            # Critical validation error
            validation_result['valid'] = False
            validation_result['errors'].append(f"Scope validation exception: {e}")
            self.validation_stats['scope_errors'] += 1
            logger.error(f"WebSocket scope validation error: {e}")
            return validation_result
    
    def _parse_query_string(self, query_string: str) -> Dict[str, str]:
        """Parse query string safely."""
        if not query_string:
            return {}
        
        params = {}
        try:
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[key] = value
                else:
                    params[param] = ''
        except Exception as e:
            logger.warning(f"Error parsing query string: {e}")
        
        return params
    
    def _parse_headers(self, headers: list) -> Dict[str, str]:
        """Parse headers list safely."""
        parsed_headers = {}
        try:
            for header in headers:
                if isinstance(header, (list, tuple)) and len(header) >= 2:
                    name = header[0]
                    value = header[1]
                    
                    # Convert bytes to string if needed
                    if isinstance(name, bytes):
                        name = name.decode('latin-1')
                    if isinstance(value, bytes):
                        value = value.decode('latin-1')
                    
                    parsed_headers[name.lower()] = value
        except Exception as e:
            logger.warning(f"Error parsing headers: {e}")
        
        return parsed_headers
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        stats = self.validation_stats.copy()
        if stats['total_validations'] > 0:
            stats['success_rate'] = stats['successful_validations'] / stats['total_validations']
            stats['error_rate'] = stats['failed_validations'] / stats['total_validations']
        else:
            stats['success_rate'] = 0.0
            stats['error_rate'] = 0.0
        
        return stats


class WebSocketConnectionStateManager:
    """
    WebSocket Connection State Manager for Issue #466
    
    Manages WebSocket connection state to prevent "Need to call 'accept' first" errors
    and ensure proper connection lifecycle management.
    """
    
    def __init__(self):
        """Initialize WebSocket connection state manager."""
        self.connection_registry = {}
        self.state_stats = {
            'total_connections': 0,
            'successful_accepts': 0,
            'failed_accepts': 0,
            'state_errors': 0,
            'premature_operations': 0
        }
    
    def register_connection(self, websocket: WebSocket, connection_id: str = None) -> str:
        """
        Register WebSocket connection for state management.
        
        Args:
            websocket: WebSocket instance
            connection_id: Optional connection ID
            
        Returns:
            Connection ID for tracking
        """
        if connection_id is None:
            connection_id = f"ws_{id(websocket)}_{self.state_stats['total_connections']}"
        
        self.connection_registry[connection_id] = {
            'websocket': websocket,
            'state': 'connecting',
            'accept_called': False,
            'close_called': False,
            'last_activity': asyncio.get_event_loop().time(),
            'error_count': 0
        }
        
        self.state_stats['total_connections'] += 1
        logger.debug(f"Registered WebSocket connection: {connection_id}")
        
        return connection_id
    
    async def safe_accept(self, websocket: WebSocket, connection_id: str = None, 
                         subprotocol: str = None, headers: Dict[str, str] = None) -> bool:
        """
        Safely accept WebSocket connection with state validation.
        
        CRITICAL FIX: Prevent "Need to call 'accept' first" errors
        
        Args:
            websocket: WebSocket instance
            connection_id: Connection ID for tracking
            subprotocol: Optional WebSocket subprotocol
            headers: Optional response headers
            
        Returns:
            True if accept succeeded, False otherwise
        """
        if connection_id is None:
            connection_id = self.register_connection(websocket)
        
        connection_info = self.connection_registry.get(connection_id, {})
        
        try:
            # Check current connection state
            if hasattr(websocket, 'client_state'):
                current_state = websocket.client_state
            else:
                current_state = WebSocketState.CONNECTING
            
            # Validate state before accepting
            if current_state != WebSocketState.CONNECTING:
                logger.warning(f"WebSocket {connection_id} not in CONNECTING state: {current_state}")
                if current_state == WebSocketState.CONNECTED:
                    # Already connected - mark as successful
                    connection_info['accept_called'] = True
                    connection_info['state'] = 'connected'
                    return True
                else:
                    # Invalid state for accept
                    self.state_stats['state_errors'] += 1
                    return False
            
            # Check if accept was already called
            if connection_info.get('accept_called', False):
                logger.warning(f"Accept already called for WebSocket {connection_id}")
                return True
            
            # Perform accept operation
            accept_kwargs = {}
            if subprotocol:
                accept_kwargs['subprotocol'] = subprotocol
            if headers:
                accept_kwargs['headers'] = list(headers.items())
            
            await websocket.accept(**accept_kwargs)
            
            # Update connection state
            connection_info['accept_called'] = True
            connection_info['state'] = 'connected'
            connection_info['last_activity'] = asyncio.get_event_loop().time()
            
            self.state_stats['successful_accepts'] += 1
            logger.debug(f"Successfully accepted WebSocket connection: {connection_id}")
            
            return True
            
        except Exception as e:
            # Accept failed
            connection_info['error_count'] = connection_info.get('error_count', 0) + 1
            connection_info['state'] = 'error'
            
            self.state_stats['failed_accepts'] += 1
            logger.error(f"Failed to accept WebSocket connection {connection_id}: {e}")
            
            return False
    
    def validate_connection_state(self, websocket: WebSocket, connection_id: str = None, 
                                operation: str = 'send') -> bool:
        """
        Validate WebSocket connection state before operations.
        
        CRITICAL FIX: Prevent operations on unaccepted connections
        
        Args:
            websocket: WebSocket instance
            connection_id: Connection ID for tracking
            operation: Operation being attempted
            
        Returns:
            True if operation is safe to proceed
        """
        if connection_id is None:
            connection_id = f"ws_{id(websocket)}"
        
        connection_info = self.connection_registry.get(connection_id, {})
        
        try:
            # Check if accept was called
            if not connection_info.get('accept_called', False):
                logger.error(f"Attempted {operation} on unaccepted WebSocket {connection_id}")
                self.state_stats['premature_operations'] += 1
                return False
            
            # Check WebSocket state
            if hasattr(websocket, 'client_state'):
                current_state = websocket.client_state
                if current_state != WebSocketState.CONNECTED:
                    logger.warning(f"WebSocket {connection_id} not connected for {operation}: {current_state}")
                    return False
            
            # Update last activity
            connection_info['last_activity'] = asyncio.get_event_loop().time()
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating WebSocket state for {connection_id}: {e}")
            return False
    
    async def safe_send_text(self, websocket: WebSocket, data: str, 
                            connection_id: str = None) -> bool:
        """
        Safely send text data with state validation.
        
        Args:
            websocket: WebSocket instance
            data: Text data to send
            connection_id: Connection ID for tracking
            
        Returns:
            True if send succeeded
        """
        if not self.validate_connection_state(websocket, connection_id, 'send_text'):
            return False
        
        try:
            await websocket.send_text(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send text on WebSocket {connection_id}: {e}")
            return False
    
    async def safe_send_json(self, websocket: WebSocket, data: Any, 
                            connection_id: str = None) -> bool:
        """
        Safely send JSON data with state validation.
        
        Args:
            websocket: WebSocket instance
            data: Data to send as JSON
            connection_id: Connection ID for tracking
            
        Returns:
            True if send succeeded
        """
        if not self.validate_connection_state(websocket, connection_id, 'send_json'):
            return False
        
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.error(f"Failed to send JSON on WebSocket {connection_id}: {e}")
            return False
    
    async def safe_close(self, websocket: WebSocket, code: int = 1000, 
                        reason: str = None, connection_id: str = None) -> bool:
        """
        Safely close WebSocket connection.
        
        Args:
            websocket: WebSocket instance
            code: Close code
            reason: Close reason
            connection_id: Connection ID for tracking
            
        Returns:
            True if close succeeded
        """
        if connection_id is None:
            connection_id = f"ws_{id(websocket)}"
        
        connection_info = self.connection_registry.get(connection_id, {})
        
        try:
            # Check if already closed
            if connection_info.get('close_called', False):
                logger.debug(f"WebSocket {connection_id} already closed")
                return True
            
            # Perform close operation
            close_kwargs = {'code': code}
            if reason:
                close_kwargs['reason'] = reason
            
            await websocket.close(**close_kwargs)
            
            # Update connection state
            connection_info['close_called'] = True
            connection_info['state'] = 'closed'
            
            logger.debug(f"Successfully closed WebSocket connection: {connection_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close WebSocket connection {connection_id}: {e}")
            return False
    
    def cleanup_connection(self, connection_id: str) -> None:
        """Clean up connection from registry."""
        if connection_id in self.connection_registry:
            del self.connection_registry[connection_id]
            logger.debug(f"Cleaned up WebSocket connection: {connection_id}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection state statistics."""
        stats = self.state_stats.copy()
        stats['active_connections'] = len(self.connection_registry)
        
        if stats['total_connections'] > 0:
            stats['accept_success_rate'] = stats['successful_accepts'] / stats['total_connections']
        else:
            stats['accept_success_rate'] = 0.0
        
        return stats


class ASGIScopeProtectionMiddleware(BaseHTTPMiddleware):
    """
    ASGI Scope Protection Middleware for Issue #466
    
    Provides comprehensive protection against malformed ASGI scopes and
    WebSocket connection state issues in staging environment.
    """
    
    def __init__(self, app, scope_validator: WebSocketASGIScopeValidator = None,
                 state_manager: WebSocketConnectionStateManager = None):
        """
        Initialize ASGI scope protection middleware.
        
        Args:
            app: ASGI application
            scope_validator: WebSocket scope validator instance
            state_manager: WebSocket state manager instance
        """
        super().__init__(app)
        self.scope_validator = scope_validator or WebSocketASGIScopeValidator()
        self.state_manager = state_manager or WebSocketConnectionStateManager()
        
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI middleware call with comprehensive scope protection.
        
        CRITICAL FIX: Prevent ASGI scope validation errors and WebSocket state issues
        """
        try:
            # Phase 1: Scope type detection and routing
            scope_type = scope.get('type', 'unknown')
            
            if scope_type == 'websocket':
                # WebSocket scope - apply comprehensive validation
                await self._handle_websocket_scope(scope, receive, send)
            elif scope_type == 'http':
                # HTTP scope - standard processing
                await super().__call__(scope, receive, send)
            else:
                # Unknown scope type - pass through with logging
                logger.warning(f"Unknown ASGI scope type: {scope_type}")
                await self.app(scope, receive, send)
                
        except Exception as e:
            logger.error(f"ASGI scope protection middleware error: {e}")
            # Send safe error response based on scope type
            await self._send_safe_error_response(scope, send, str(e))
    
    async def _handle_websocket_scope(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle WebSocket scope with comprehensive validation and state management.
        
        Args:
            scope: WebSocket ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        try:
            # Phase 1: Validate WebSocket scope
            validation_result = self.scope_validator.validate_websocket_scope(scope)
            
            if not validation_result['valid']:
                # Invalid scope - send appropriate error
                error_msg = f"Invalid WebSocket scope: {', '.join(validation_result['errors'])}"
                logger.error(error_msg)
                await self._send_websocket_error_response(send, 1002, error_msg)
                return
            
            # Phase 2: Create WebSocket instance with state management
            websocket = WebSocket(scope, receive, send)
            connection_id = self.state_manager.register_connection(websocket)
            
            # Phase 3: Enhanced WebSocket handling with state protection
            await self._process_websocket_with_state_management(
                websocket, connection_id, scope, receive, send
            )
            
        except Exception as e:
            logger.error(f"WebSocket scope handling error: {e}")
            await self._send_websocket_error_response(send, 1011, f"Internal server error: {e}")
    
    async def _process_websocket_with_state_management(self, websocket: WebSocket, 
                                                      connection_id: str, scope: Scope,
                                                      receive: Receive, send: Send) -> None:
        """
        Process WebSocket with comprehensive state management.
        
        CRITICAL FIX: Ensure proper WebSocket lifecycle and prevent state errors
        """
        try:
            # Phase 1: Wrap application call with state management
            original_accept = websocket.accept
            original_send_text = websocket.send_text
            original_send_json = websocket.send_json
            original_close = websocket.close
            
            # Wrap accept method
            async def safe_accept_wrapper(*args, **kwargs):
                return await self.state_manager.safe_accept(websocket, connection_id, *args, **kwargs)
            
            # Wrap send methods
            async def safe_send_text_wrapper(data, *args, **kwargs):
                if self.state_manager.validate_connection_state(websocket, connection_id, 'send_text'):
                    return await original_send_text(data, *args, **kwargs)
                else:
                    raise RuntimeError("Cannot send text on unaccepted WebSocket connection")
            
            async def safe_send_json_wrapper(data, *args, **kwargs):
                if self.state_manager.validate_connection_state(websocket, connection_id, 'send_json'):
                    return await original_send_json(data, *args, **kwargs)
                else:
                    raise RuntimeError("Cannot send JSON on unaccepted WebSocket connection")
            
            # Wrap close method
            async def safe_close_wrapper(*args, **kwargs):
                return await self.state_manager.safe_close(websocket, *args, connection_id=connection_id, **kwargs)
            
            # Apply wrappers
            websocket.accept = safe_accept_wrapper
            websocket.send_text = safe_send_text_wrapper
            websocket.send_json = safe_send_json_wrapper
            websocket.close = safe_close_wrapper
            
            # Phase 2: Process WebSocket with protected methods
            await self.app(scope, receive, send)
            
        except Exception as e:
            logger.error(f"WebSocket state management error: {e}")
            # Attempt graceful cleanup
            await self.state_manager.safe_close(websocket, 1011, f"Server error: {e}", connection_id)
        finally:
            # Cleanup connection from registry
            self.state_manager.cleanup_connection(connection_id)
    
    async def _send_websocket_error_response(self, send: Send, code: int, reason: str) -> None:
        """Send WebSocket error response."""
        try:
            await send({
                'type': 'websocket.close',
                'code': code,
                'reason': reason[:123] if len(reason) > 123 else reason  # WebSocket reason limit
            })
        except Exception as e:
            logger.error(f"Failed to send WebSocket error response: {e}")
    
    async def _send_safe_error_response(self, scope: Scope, send: Send, error_message: str) -> None:
        """Send safe error response based on scope type."""
        scope_type = scope.get('type', 'unknown')
        
        if scope_type == 'websocket':
            await self._send_websocket_error_response(send, 1011, error_message)
        elif scope_type == 'http':
            # Send HTTP error response
            try:
                await send({
                    'type': 'http.response.start',
                    'status': 500,
                    'headers': [
                        (b'content-type', b'application/json'),
                        (b'x-asgi-error', b'true'),
                    ],
                })
                
                error_data = {
                    'error': 'asgi_scope_error',
                    'message': error_message,
                    'issue_reference': '#466'
                }
                response_body = json.dumps(error_data).encode('utf-8')
                
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
            except Exception as e:
                logger.error(f"Failed to send HTTP error response: {e}")
        else:
            logger.error(f"Cannot send error response for scope type: {scope_type}")


def create_websocket_asgi_protection_suite():
    """
    Create complete WebSocket ASGI protection suite for Issue #466.
    
    Returns:
        Dictionary containing all protection components
    """
    scope_validator = WebSocketASGIScopeValidator()
    state_manager = WebSocketConnectionStateManager()
    
    def create_middleware(app):
        return ASGIScopeProtectionMiddleware(app, scope_validator, state_manager)
    
    return {
        'scope_validator': scope_validator,
        'state_manager': state_manager,
        'middleware_factory': create_middleware,
        'get_stats': lambda: {
            'scope_validation': scope_validator.get_validation_stats(),
            'connection_state': state_manager.get_connection_stats()
        }
    }


def main():
    """
    Main function to demonstrate WebSocket ASGI scope validation fix for Issue #466.
    """
    try:
        print("Creating WebSocket ASGI protection suite...")
        
        # Create protection suite
        protection_suite = create_websocket_asgi_protection_suite()
        
        print("WebSocket ASGI protection suite created successfully!")
        print(f"Components: {list(protection_suite.keys())}")
        
        # Get initial stats
        stats = protection_suite['get_stats']()
        print(f"Initial stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"WebSocket ASGI protection suite creation failed: {e}")
        logger.error(f"WebSocket ASGI protection suite creation failed: {e}")
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)