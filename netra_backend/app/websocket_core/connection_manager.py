"""
WebSocket Connection Manager - SSOT Alias

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Development Velocity & Backward Compatibility
- Value Impact: Prevents test failures from broken imports, maintains test reliability
- Strategic Impact: Critical for WebSocket thread routing tests to run properly

This module provides the SSOT alias for WebSocketConnectionManager imports that tests expect.
Following CLAUDE.md SSOT principles by creating proper aliases rather than duplicating code.
"""

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.logging_config import central_logger
from typing import Dict, Any, Optional
from datetime import datetime

logger = central_logger.get_logger(__name__)


class ConnectionInfo:
    """
    SSOT CONSOLIDATED: WebSocket connection information with unified constructor patterns.
    
    Business Value Justification:
    - Segment: Platform/Internal - SSOT compliance for Issue #441
    - Business Goal: Development Velocity & System Stability  
    - Value Impact: Eliminates SSOT violation, maintains test compatibility
    - Strategic Impact: Prevents duplicate class definitions causing confusion
    
    UNIFIED CONSTRUCTOR PATTERNS:
    - Parameterless: ConnectionInfo() - For test compatibility
    - Standard: ConnectionInfo('conn-123', 'user-456') - For business logic
    - With metadata: ConnectionInfo('conn-123', 'user-456', {'key': 'value'})
    
    DYNAMIC PROPERTIES: Supports test patterns like:
    - conn.websocket_id = 'ws-123'  
    - conn.state = ConnectionState.CONNECTED
    - conn.message_count = 10
    """
    
    def __init__(self, connection_id: str = None, user_id: str = None, metadata: Dict[str, Any] = None):
        import time
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        
        # Handle parameterless constructor for test compatibility
        if connection_id is None and user_id is None:
            # Generate test-friendly IDs
            self.connection_id = f"test_conn_{UnifiedIdGenerator.generate_base_id('conn', include_random=True, random_length=6)}"
            self.user_id = f"test_user_{UnifiedIdGenerator.generate_base_id('user', include_random=True, random_length=6)}"
        elif connection_id is None:
            # Generate connection_id from user_id
            self.connection_id = f"conn_{user_id}_{UnifiedIdGenerator.generate_base_id('auto', include_random=True, random_length=6)}"
            self.user_id = user_id
        elif user_id is None:
            # Extract or generate user_id
            self.connection_id = connection_id
            self.user_id = f"user_{UnifiedIdGenerator.generate_base_id('auto', include_random=True, random_length=6)}"
        else:
            # Standard constructor with both parameters
            self.connection_id = connection_id
            self.user_id = user_id
        
        # Core properties from both original implementations
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Compatibility properties from second implementation  
        self.connected_at = time.time()
        self.is_active = True
        
        # Initialize dynamic properties for test compatibility
        self._dynamic_properties = {}
    
    def __setattr__(self, name: str, value: Any) -> None:
        """Support dynamic property assignment for test compatibility."""
        # Allow normal attribute setting for known properties
        if name in ['connection_id', 'user_id', 'metadata', 'created_at', 'last_activity', 
                    'connected_at', 'is_active', '_dynamic_properties']:
            super().__setattr__(name, value)
        else:
            # Store dynamic properties in separate dict for test compatibility
            if not hasattr(self, '_dynamic_properties'):
                super().__setattr__('_dynamic_properties', {})
            self._dynamic_properties[name] = value
    
    def __getattr__(self, name: str) -> Any:
        """Support dynamic property access for test compatibility."""
        if hasattr(self, '_dynamic_properties') and name in self._dynamic_properties:
            return self._dynamic_properties[name]
        raise AttributeError(f"'ConnectionInfo' object has no attribute '{name}'")
    
    def update_activity(self):
        """Update last activity timestamp - merged from both implementations."""
        import time
        self.last_activity = datetime.utcnow()
        self.connected_at = time.time()  # Keep both time formats
    
    def disconnect(self):
        """Mark connection as disconnected - from second implementation."""
        self.is_active = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation - merged from both implementations."""
        result = {
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'connected_at': self.connected_at,
            'is_active': self.is_active
        }
        
        # Include dynamic properties for complete state representation
        if hasattr(self, '_dynamic_properties'):
            result.update(self._dynamic_properties)
            
        return result


# SSOT COMPLIANCE: Use direct alias instead of class inheritance
# DEPRECATED: WebSocketConnectionManager is now an alias to UnifiedWebSocketManager
# Use UnifiedWebSocketManager directly for new code
# This eliminates the duplicate class definition while maintaining backward compatibility
WebSocketConnectionManager = UnifiedWebSocketManager


# SSOT alias for backward compatibility
ConnectionManager = WebSocketConnectionManager


# Export for backward compatibility
__all__ = ['WebSocketConnectionManager', 'ConnectionManager', 'ConnectionInfo']