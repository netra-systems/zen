"""WebSocket Connection Model - Minimal implementation for integration tests.

This module provides WebSocket connection models.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from shared.types import UserID, ConnectionID

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Minimal WebSocket connection model for integration tests."""
    
    def __init__(
        self,
        connection_id: ConnectionID,
        user_id: UserID,
        created_at: Optional[datetime] = None,
        **kwargs
    ):
        self.connection_id = connection_id
        self.user_id = user_id
        self.created_at = created_at or datetime.now()
        self.is_active = True
        self.metadata = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert connection to dictionary."""
        return {
            'connection_id': self.connection_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebSocketConnection':
        """Create connection from dictionary."""
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        
        conn = cls(
            connection_id=data['connection_id'],
            user_id=data['user_id'],
            created_at=created_at
        )
        conn.is_active = data.get('is_active', True)
        conn.metadata = data.get('metadata', {})
        return conn