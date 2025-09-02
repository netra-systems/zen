"""DatabaseSessionManager - Per-Request Session Management

This module provides comprehensive database session management for per-request isolation,
ensuring sessions are NEVER shared between users and preventing session leakage.

Business Value Justification (BVJ):
- Segment: Platform Security (all tiers)
- Business Goal: Prevent data corruption and cross-user session leakage
- Value Impact: Ensures user data privacy and transactional integrity
- Strategic Impact: Eliminates session-related security vulnerabilities
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, AsyncContextManager
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from netra_backend.app.logging_config import central_logger
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class SessionManagerError(Exception):
    """Base exception for session manager errors."""
    pass


class SessionIsolationError(SessionManagerError):
    """Raised when session isolation is violated."""
    pass


class SessionLifecycleError(SessionManagerError):
    """Raised when session lifecycle is invalid."""
    pass


class DatabaseSessionManager:
    """Per-request database session manager with strict isolation guarantees.
    
    This class ensures database sessions are:
    1. Created per-request only
    2. Never shared between users
    3. Properly isolated and validated
    4. Automatically cleaned up on errors
    5. Tagged with user context for verification
    
    CRITICAL: Sessions managed by this class are NEVER stored globally.
    """
    
    def __init__(self, context: UserExecutionContext):
        """Initialize session manager with user context.
        
        Args:
            context: User execution context containing session and user info
            
        Raises:
            SessionManagerError: If context is invalid or session is missing
        """
        if not isinstance(context, UserExecutionContext):
            raise SessionManagerError(f"Invalid context type: {type(context)}")
        
        if context.db_session is None:
            raise SessionManagerError("UserExecutionContext must contain a database session")
        
        self.context = context
        self.session = context.db_session
        self._session_id = f"{context.user_id}_{context.run_id}_{uuid.uuid4().hex[:8]}"
        self._is_active = True
        self._transaction_count = 0
        self._operation_count = 0
        
        # Tag session for validation
        self._tag_session()
        
        logger.debug(f"Created DatabaseSessionManager {self._session_id} for user {context.user_id}")
    
    def _tag_session(self) -> None:
        """Tag session with user context for validation."""
        if not hasattr(self.session, 'info'):
            # Create info dict if it doesn't exist
            self.session.info = {}
        
        self.session.info.update({
            'user_id': self.context.user_id,
            'run_id': self.context.run_id,
            'request_id': self.context.request_id,
            'session_manager_id': self._session_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'is_request_scoped': True
        })
        
        logger.debug(f"Tagged session {id(self.session)} with user context {self.context.user_id}")
    
    def _validate_session_ownership(self) -> None:
        """Ensure session belongs to current user context.
        
        Raises:
            SessionIsolationError: If session belongs to different user
        """
        if not self._is_active:
            raise SessionLifecycleError(f"Session manager {self._session_id} is closed")
        
        session_user_id = getattr(self.session, 'info', {}).get('user_id')
        if session_user_id and session_user_id != self.context.user_id:
            raise SessionIsolationError(
                f"Session belongs to user {session_user_id}, "
                f"but current context is for user {self.context.user_id}"
            )
        
        session_request_id = getattr(self.session, 'info', {}).get('request_id')
        if session_request_id and session_request_id != self.context.request_id:
            logger.warning(
                f"Session request_id {session_request_id} differs from "
                f"context request_id {self.context.request_id} - possible reuse"
            )
    
    async def execute(self, query: Any) -> Any:
        """Execute query with session validation.
        
        Args:
            query: SQLAlchemy query to execute
            
        Returns:
            Query result
            
        Raises:
            SessionLifecycleError: If session is closed
            SessionIsolationError: If session ownership is invalid
        """
        self._validate_session_ownership()
        self._operation_count += 1
        
        try:
            logger.debug(f"Executing query {self._operation_count} for session {self._session_id}")
            result = await self.session.execute(query)
            logger.debug(f"Query {self._operation_count} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Query {self._operation_count} failed for session {self._session_id}: {e}")
            raise
    
    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[AsyncSession]:
        """Provide transaction context for atomic operations.
        
        Yields:
            Database session within transaction scope
            
        Raises:
            SessionLifecycleError: If session is closed
            SessionIsolationError: If session ownership is invalid
        """
        self._validate_session_ownership()
        self._transaction_count += 1
        transaction_id = f"{self._session_id}_tx{self._transaction_count}"
        
        logger.debug(f"Starting transaction {transaction_id}")
        
        try:
            async with self.session.begin():
                logger.debug(f"Transaction {transaction_id} began")
                yield self.session
                logger.debug(f"Transaction {transaction_id} committed")
        except Exception as e:
            logger.error(f"Transaction {transaction_id} failed: {e}")
            # SQLAlchemy will automatically rollback on exception
            raise
        finally:
            logger.debug(f"Transaction {transaction_id} completed")
    
    async def commit(self) -> None:
        """Commit current transaction.
        
        Raises:
            SessionLifecycleError: If session is closed
        """
        self._validate_session_ownership()
        
        try:
            await self.session.commit()
            logger.debug(f"Session {self._session_id} committed")
        except Exception as e:
            logger.error(f"Session {self._session_id} commit failed: {e}")
            await self.rollback()
            raise
    
    async def rollback(self) -> None:
        """Rollback current transaction.
        
        Raises:
            SessionLifecycleError: If session is closed
        """
        self._validate_session_ownership()
        
        try:
            await self.session.rollback()
            logger.debug(f"Session {self._session_id} rolled back")
        except Exception as e:
            logger.error(f"Session {self._session_id} rollback failed: {e}")
            raise
    
    async def refresh(self, instance: Any) -> None:
        """Refresh instance from database.
        
        Args:
            instance: SQLAlchemy model instance to refresh
        """
        self._validate_session_ownership()
        await self.session.refresh(instance)
    
    async def close(self) -> None:
        """Close session and prevent further use.
        
        This method is idempotent and can be called multiple times safely.
        """
        if not self._is_active:
            logger.debug(f"Session manager {self._session_id} already closed")
            return
        
        try:
            logger.debug(f"Closing session manager {self._session_id}")
            await self.session.close()
            self._is_active = False
            logger.debug(f"Session manager {self._session_id} closed successfully")
        except Exception as e:
            logger.error(f"Error closing session manager {self._session_id}: {e}")
            self._is_active = False  # Mark as closed even if close() failed
            raise
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for debugging and monitoring.
        
        Returns:
            Dictionary with session information
        """
        return {
            'session_id': self._session_id,
            'user_id': self.context.user_id,
            'run_id': self.context.run_id,
            'request_id': self.context.request_id,
            'is_active': self._is_active,
            'transaction_count': self._transaction_count,
            'operation_count': self._operation_count,
            'session_python_id': id(self.session),
            'session_info': getattr(self.session, 'info', {})
        }
    
    def __str__(self) -> str:
        return f"DatabaseSessionManager({self._session_id}, user={self.context.user_id}, active={self._is_active})"
    
    def __repr__(self) -> str:
        return (f"DatabaseSessionManager(session_id='{self._session_id}', "
                f"user_id='{self.context.user_id}', active={self._is_active})")


class SessionScopeValidator:
    """Validates database sessions are properly scoped and isolated."""
    
    @staticmethod
    def validate_no_stored_sessions(obj: Any, obj_name: str = "object") -> bool:
        """Check object doesn't store AsyncSession instances.
        
        Args:
            obj: Object to validate
            obj_name: Name of object for error messages
            
        Returns:
            True if no sessions found
            
        Raises:
            SessionIsolationError: If stored sessions are detected
        """
        stored_sessions = []
        
        # Check direct attributes
        for attr_name in dir(obj):
            if attr_name.startswith('_'):
                continue
            
            try:
                attr = getattr(obj, attr_name)
                if isinstance(attr, AsyncSession):
                    stored_sessions.append(f"{obj_name}.{attr_name}")
            except (AttributeError, TypeError):
                # Some attributes might not be accessible
                continue
        
        if stored_sessions:
            raise SessionIsolationError(
                f"Object {obj_name} stores AsyncSession in: {', '.join(stored_sessions)}. "
                f"Sessions must be passed via context only."
            )
        
        logger.debug(f"Validated {obj_name} contains no stored sessions")
        return True
    
    @staticmethod
    def tag_session(session: AsyncSession, user_id: str, run_id: str, request_id: str) -> None:
        """Tag session with user context for validation.
        
        Args:
            session: Session to tag
            user_id: User identifier
            run_id: Run identifier  
            request_id: Request identifier
        """
        if not hasattr(session, 'info'):
            session.info = {}
        
        session.info.update({
            'user_id': user_id,
            'run_id': run_id,
            'request_id': request_id,
            'tagged_at': datetime.now(timezone.utc).isoformat(),
            'is_request_scoped': True
        })
        
        logger.debug(f"Tagged session {id(session)} with user {user_id}, run {run_id}")
    
    @staticmethod
    def validate_session_context(session: AsyncSession, context: UserExecutionContext) -> bool:
        """Ensure session matches user context.
        
        Args:
            session: Session to validate
            context: Expected user context
            
        Returns:
            True if session matches context
            
        Raises:
            SessionIsolationError: If session context doesn't match
        """
        session_info = getattr(session, 'info', {})
        
        session_user_id = session_info.get('user_id')
        if session_user_id and session_user_id != context.user_id:
            raise SessionIsolationError(
                f"Session user_id {session_user_id} != context user_id {context.user_id}"
            )
        
        session_run_id = session_info.get('run_id')
        if session_run_id and session_run_id != context.run_id:
            logger.warning(
                f"Session run_id {session_run_id} != context run_id {context.run_id} - "
                f"possible session reuse"
            )
        
        logger.debug(f"Validated session {id(session)} matches context {context.user_id}")
        return True
    
    @staticmethod
    def validate_request_scoped(session: AsyncSession) -> bool:
        """Validate session is marked as request-scoped.
        
        Args:
            session: Session to validate
            
        Returns:
            True if session is request-scoped
            
        Raises:
            SessionIsolationError: If session is not request-scoped
        """
        session_info = getattr(session, 'info', {})
        is_request_scoped = session_info.get('is_request_scoped', False)
        
        if not is_request_scoped:
            raise SessionIsolationError(
                f"Session {id(session)} is not marked as request-scoped. "
                f"All sessions must be created per-request."
            )
        
        logger.debug(f"Validated session {id(session)} is request-scoped")
        return True


# Utility functions for session lifecycle management

async def create_session_manager(context: UserExecutionContext) -> DatabaseSessionManager:
    """Create session manager from user context.
    
    Args:
        context: User execution context with database session
        
    Returns:
        Configured DatabaseSessionManager
        
    Raises:
        SessionManagerError: If context is invalid
    """
    return DatabaseSessionManager(context)


@asynccontextmanager
async def managed_session(context: UserExecutionContext) -> AsyncContextManager[DatabaseSessionManager]:
    """Context manager for database session with automatic cleanup.
    
    Args:
        context: User execution context with database session
        
    Yields:
        DatabaseSessionManager instance
        
    Raises:
        SessionManagerError: If session management fails
    """
    session_manager = None
    try:
        session_manager = DatabaseSessionManager(context)
        yield session_manager
    except Exception as e:
        logger.error(f"Session management error: {e}")
        raise
    finally:
        if session_manager and session_manager._is_active:
            try:
                await session_manager.close()
            except Exception as e:
                logger.error(f"Error during session cleanup: {e}")


def validate_agent_session_isolation(agent: Any) -> bool:
    """Validate agent doesn't store database sessions.
    
    Args:
        agent: Agent instance to validate
        
    Returns:
        True if agent is properly isolated
        
    Raises:
        SessionIsolationError: If agent stores sessions
    """
    return SessionScopeValidator.validate_no_stored_sessions(agent, f"Agent({agent.__class__.__name__})")