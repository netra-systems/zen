"""
Unified ID Manager Module

Provides centralized ID generation and management across the Netra platform.
Ensures unique, consistent ID generation for all system components.
"""

import logging
import uuid
import time
import threading
from typing import Dict, Optional, Any, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IDType(Enum):
    """Types of IDs managed by the system"""
    USER = "user"
    SESSION = "session"
    REQUEST = "request"
    AGENT = "agent"
    TOOL = "tool"
    TRANSACTION = "transaction"
    WEBSOCKET = "websocket"
    EXECUTION = "execution"
    TRACE = "trace"
    METRIC = "metric"


@dataclass
class IDMetadata:
    """Metadata associated with generated IDs"""
    id_value: str
    id_type: IDType
    created_at: float
    prefix: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class UnifiedIDManager:
    """
    Centralized ID management system.
    
    Provides consistent ID generation, tracking, and validation
    across all system components.
    """
    
    def __init__(self):
        self._id_registry: Dict[str, IDMetadata] = {}
        self._active_ids: Dict[IDType, Set[str]] = {id_type: set() for id_type in IDType}
        self._id_counters: Dict[IDType, int] = {id_type: 0 for id_type in IDType}
        self._lock = threading.RLock()
        logger.info("UnifiedIDManager initialized")
    
    def generate_id(self, 
                   id_type: IDType,
                   prefix: Optional[str] = None,
                   context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a new unique ID.
        
        Args:
            id_type: Type of ID to generate
            prefix: Optional prefix for the ID
            context: Additional context metadata
            
        Returns:
            Generated unique ID
        """
        with self._lock:
            # Generate base UUID
            base_uuid = str(uuid.uuid4())
            
            # Increment counter for this ID type
            self._id_counters[id_type] += 1
            counter = self._id_counters[id_type]
            
            # Construct ID with optional prefix
            if prefix:
                id_value = f"{prefix}_{id_type.value}_{counter}_{base_uuid[:8]}"
            else:
                id_value = f"{id_type.value}_{counter}_{base_uuid[:8]}"
            
            # Create metadata
            metadata = IDMetadata(
                id_value=id_value,
                id_type=id_type,
                created_at=time.time(),
                prefix=prefix,
                context=context or {}
            )
            
            # Register ID
            self._id_registry[id_value] = metadata
            self._active_ids[id_type].add(id_value)
            
            logger.debug(f"Generated {id_type.value} ID: {id_value}")
            return id_value
    
    def register_existing_id(self,
                           id_value: str,
                           id_type: IDType,
                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Register an existing ID with the manager.
        
        Args:
            id_value: Existing ID to register
            id_type: Type of the ID
            context: Additional context metadata
            
        Returns:
            True if registered successfully, False if already exists
        """
        with self._lock:
            if id_value in self._id_registry:
                return False
            
            metadata = IDMetadata(
                id_value=id_value,
                id_type=id_type,
                created_at=time.time(),
                context=context or {}
            )
            
            self._id_registry[id_value] = metadata
            self._active_ids[id_type].add(id_value)
            
            logger.debug(f"Registered existing {id_type.value} ID: {id_value}")
            return True
    
    def get_id_metadata(self, id_value: str) -> Optional[IDMetadata]:
        """Get metadata for a specific ID"""
        return self._id_registry.get(id_value)
    
    def is_valid_id(self, id_value: str, id_type: Optional[IDType] = None) -> bool:
        """
        Check if an ID is valid and registered.
        
        Args:
            id_value: ID to validate
            id_type: Optional specific type to check against
            
        Returns:
            True if ID is valid
        """
        metadata = self.get_id_metadata(id_value)
        if not metadata:
            return False
        
        if id_type and metadata.id_type != id_type:
            return False
        
        return True
    
    def release_id(self, id_value: str) -> bool:
        """
        Release an ID from active use.
        
        Args:
            id_value: ID to release
            
        Returns:
            True if released successfully
        """
        with self._lock:
            metadata = self._id_registry.get(id_value)
            if not metadata:
                return False
            
            # Remove from active IDs
            self._active_ids[metadata.id_type].discard(id_value)
            
            # Keep in registry for tracking but mark as released
            metadata.context['released_at'] = time.time()
            
            logger.debug(f"Released {metadata.id_type.value} ID: {id_value}")
            return True
    
    def get_active_ids(self, id_type: IDType) -> Set[str]:
        """Get all active IDs of a specific type"""
        return self._active_ids[id_type].copy()
    
    def count_active_ids(self, id_type: IDType) -> int:
        """Count active IDs of a specific type"""
        return len(self._active_ids[id_type])
    
    def cleanup_released_ids(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old released IDs from registry.
        
        Args:
            max_age_seconds: Maximum age for released IDs
            
        Returns:
            Number of IDs cleaned up
        """
        current_time = time.time()
        cleanup_count = 0
        
        with self._lock:
            ids_to_remove = []
            
            for id_value, metadata in self._id_registry.items():
                released_at = metadata.context.get('released_at')
                if released_at and current_time - released_at > max_age_seconds:
                    ids_to_remove.append(id_value)
            
            for id_value in ids_to_remove:
                del self._id_registry[id_value]
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} released IDs")
        
        return cleanup_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ID manager statistics"""
        with self._lock:
            stats = {
                'total_registered': len(self._id_registry),
                'active_by_type': {},
                'counters_by_type': {},
                'total_active': 0
            }
            
            for id_type in IDType:
                active_count = len(self._active_ids[id_type])
                stats['active_by_type'][id_type.value] = active_count
                stats['counters_by_type'][id_type.value] = self._id_counters[id_type]
                stats['total_active'] += active_count
            
            return stats
    
    def reset_counters(self) -> None:
        """Reset all ID counters (use with caution)"""
        with self._lock:
            self._id_counters = {id_type: 0 for id_type in IDType}
            logger.warning("ID counters reset")
    
    def clear_all(self) -> None:
        """Clear all IDs and reset manager (use with caution)"""
        with self._lock:
            self._id_registry.clear()
            self._active_ids = {id_type: set() for id_type in IDType}
            self._id_counters = {id_type: 0 for id_type in IDType}
            logger.warning("UnifiedIDManager cleared")


# Global ID manager instance
_id_manager = None


def get_id_manager() -> UnifiedIDManager:
    """Get global unified ID manager"""
    global _id_manager
    if _id_manager is None:
        _id_manager = UnifiedIDManager()
    return _id_manager


def generate_id(id_type: IDType, **kwargs) -> str:
    """Convenience function to generate ID"""
    return get_id_manager().generate_id(id_type, **kwargs)


def generate_user_id() -> str:
    """Generate a user ID"""
    return generate_id(IDType.USER)


def generate_session_id() -> str:
    """Generate a session ID"""
    return generate_id(IDType.SESSION)


def generate_request_id() -> str:
    """Generate a request ID"""
    return generate_id(IDType.REQUEST)


def generate_agent_id() -> str:
    """Generate an agent ID"""
    return generate_id(IDType.AGENT)


def generate_websocket_id() -> str:
    """Generate a WebSocket connection ID"""
    return generate_id(IDType.WEBSOCKET)


def generate_execution_id() -> str:
    """Generate an execution context ID"""
    return generate_id(IDType.EXECUTION)


def is_valid_id(id_value: str, id_type: Optional[IDType] = None) -> bool:
    """Convenience function to validate ID"""
    return get_id_manager().is_valid_id(id_value, id_type)