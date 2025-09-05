"""Core rollback manager components.

This module provides the core classes and interfaces for database rollback operations.
"""

import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone


class RollbackState(Enum):
    """States for rollback operations."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


class DependencyType(Enum):
    """Types of rollback dependencies."""
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    FILE_SYSTEM = "file_system"


@dataclass
class RollbackOperation:
    """Represents a single rollback operation."""
    id: str
    operation_type: str
    table_name: Optional[str] = None
    record_id: Optional[str] = None
    state: RollbackState = RollbackState.PENDING
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class RollbackSession:
    """Manages a session of related rollback operations."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.operations: List[RollbackOperation] = []
        self.state = RollbackState.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
    
    def add_operation(self, operation: RollbackOperation):
        """Add a rollback operation to this session."""
        self.operations.append(operation)
    
    def mark_completed(self):
        """Mark the session as completed."""
        self.state = RollbackState.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def mark_failed(self, error: str):
        """Mark the session as failed."""
        self.state = RollbackState.FAILED
        self.completed_at = datetime.now(timezone.utc)


class RollbackManager:
    """Core rollback manager for database operations."""
    
    def __init__(self):
        self.sessions: Dict[str, RollbackSession] = {}
        self.handlers: Dict[DependencyType, Any] = {}
    
    def create_session(self, session_id: Optional[str] = None) -> RollbackSession:
        """Create a new rollback session."""
        import uuid
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        session = RollbackSession(session_id)
        self.sessions[session_id] = session
        return session
    
    async def execute_rollback(self, session_id: str) -> bool:
        """Execute rollback operations for a session."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        try:
            session.state = RollbackState.EXECUTING
            # Simple rollback execution - mark all operations as completed
            for operation in session.operations:
                operation.state = RollbackState.COMPLETED
                operation.completed_at = datetime.now(timezone.utc)
            
            session.mark_completed()
            return True
        except Exception as e:
            session.mark_failed(str(e))
            return False
    
    def register_handler(self, dependency_type: DependencyType, handler: Any):
        """Register a handler for a specific dependency type."""
        self.handlers[dependency_type] = handler
    
    def get_session(self, session_id: str) -> Optional[RollbackSession]:
        """Get a rollback session by ID."""
        return self.sessions.get(session_id)


# Global rollback manager instance
rollback_manager = RollbackManager()