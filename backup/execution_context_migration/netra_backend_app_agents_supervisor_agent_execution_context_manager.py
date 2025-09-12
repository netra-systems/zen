"""Agent Execution Context Manager - SSOT for agent execution context and isolation management.

This module provides context management for agent execution including user isolation,
session management, and execution state tracking. It ensures proper isolation between
users and maintains execution context throughout the agent lifecycle.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Multi-tenant Security and Reliability
- Value Impact: Ensures secure user isolation and prevents data leakage between users
- Strategic Impact: Enables reliable multi-user platform operation

SSOT Principle: This is the canonical implementation for agent execution context.
All agent executions must use this manager for proper isolation and context tracking.
"""

from typing import Dict, Any, Optional, List, Set
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, field

# SSOT Imports - Absolute imports as per CLAUDE.md
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, ensure_user_id
from shared.types.execution_types import StronglyTypedUserExecutionContext
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# =============================================================================
# Context Management Types
# =============================================================================

@dataclass
class ExecutionSession:
    """Represents an active agent execution session."""
    session_id: str
    user_id: UserID
    thread_id: ThreadID
    created_at: datetime
    last_activity: datetime
    execution_context: StronglyTypedUserExecutionContext
    active_runs: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)
    
    def add_run(self, run_id: str):
        """Add a run to this session."""
        self.active_runs.add(run_id)
        self.update_activity()
    
    def remove_run(self, run_id: str):
        """Remove a run from this session."""
        self.active_runs.discard(run_id)
        self.update_activity()
    
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session has expired."""
        if not self.active_runs:
            # Session with no active runs expires after timeout
            elapsed = datetime.now(timezone.utc) - self.last_activity
            return elapsed.total_seconds() > (timeout_minutes * 60)
        return False


@dataclass
class ContextIsolationMetrics:
    """Metrics for context isolation monitoring."""
    active_sessions: int = 0
    active_contexts: int = 0
    isolation_violations: int = 0
    context_leaks: int = 0
    session_timeouts: int = 0
    
    def reset(self):
        """Reset all metrics to zero."""
        self.__dict__.update((k, 0) for k in self.__dict__)


# =============================================================================
# Agent Execution Context Manager
# =============================================================================

class AgentExecutionContextManager:
    """Manages agent execution contexts with proper user isolation.
    
    This class provides:
    - User session isolation and management
    - Execution context creation and cleanup
    - Context lifecycle tracking
    - Multi-tenant security enforcement
    - Memory and resource management
    """
    
    def __init__(self):
        """Initialize context manager with isolation tracking."""
        self._sessions: Dict[str, ExecutionSession] = {}
        self._user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self._context_registry: Dict[str, StronglyTypedUserExecutionContext] = {}
        self._lock = threading.RLock()  # Re-entrant lock for thread safety
        self._metrics = ContextIsolationMetrics()
        
        logger.info("AgentExecutionContextManager initialized with isolation tracking")
    
    # =========================================================================
    # Session Management
    # =========================================================================
    
    def create_execution_session(self, user_id: UserID, thread_id: ThreadID, 
                                initial_context: Optional[Dict[str, Any]] = None) -> str:
        """Create new agent execution session with proper isolation.
        
        Args:
            user_id: Strongly typed user identifier
            thread_id: Thread/conversation identifier
            initial_context: Optional initial context data
            
        Returns:
            str: Unique session identifier
        """
        with self._lock:
            try:
                session_id = f"session_{uuid.uuid4().hex[:12]}"
                now = datetime.now(timezone.utc)
                
                # Create execution context with proper isolation
                execution_context = self._create_isolated_execution_context(
                    user_id=user_id,
                    thread_id=thread_id,
                    session_id=session_id,
                    initial_context=initial_context or {}
                )
                
                # Create session
                session = ExecutionSession(
                    session_id=session_id,
                    user_id=user_id,
                    thread_id=thread_id,
                    created_at=now,
                    last_activity=now,
                    execution_context=execution_context,
                    metadata={
                        "isolation_boundary": str(user_id),
                        "context_version": "1.0",
                        "security_context": "isolated"
                    }
                )
                
                # Register session
                self._sessions[session_id] = session
                
                # Track user sessions
                user_id_str = str(user_id)
                if user_id_str not in self._user_sessions:
                    self._user_sessions[user_id_str] = set()
                self._user_sessions[user_id_str].add(session_id)
                
                # Register context
                self._context_registry[session_id] = execution_context
                
                # Update metrics
                self._metrics.active_sessions += 1
                self._metrics.active_contexts += 1
                
                logger.info(f"Created execution session {session_id} for user {user_id}")
                return session_id
                
            except Exception as e:
                logger.error(f"Failed to create execution session for user {user_id}: {e}")
                raise
    
    def get_execution_session(self, session_id: str) -> Optional[ExecutionSession]:
        """Get execution session by ID with isolation validation.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[ExecutionSession]: Session if found and valid, None otherwise
        """
        with self._lock:
            try:
                session = self._sessions.get(session_id)
                if not session:
                    return None
                
                # Check if session is expired
                if session.is_expired():
                    logger.warning(f"Session {session_id} has expired, cleaning up")
                    self._cleanup_session(session_id)
                    return None
                
                # Update activity
                session.update_activity()
                return session
                
            except Exception as e:
                logger.error(f"Error retrieving execution session {session_id}: {e}")
                return None
    
    def get_user_sessions(self, user_id: UserID) -> List[ExecutionSession]:
        """Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List[ExecutionSession]: Active sessions for the user
        """
        with self._lock:
            try:
                user_id_str = str(user_id)
                session_ids = self._user_sessions.get(user_id_str, set())
                
                active_sessions = []
                expired_sessions = []
                
                for session_id in session_ids:
                    session = self._sessions.get(session_id)
                    if session and not session.is_expired():
                        active_sessions.append(session)
                    else:
                        expired_sessions.append(session_id)
                
                # Clean up expired sessions
                for session_id in expired_sessions:
                    self._cleanup_session(session_id)
                
                return active_sessions
                
            except Exception as e:
                logger.error(f"Error retrieving user sessions for {user_id}: {e}")
                return []
    
    def cleanup_session(self, session_id: str) -> bool:
        """Clean up execution session and associated resources.
        
        Args:
            session_id: Session identifier to cleanup
            
        Returns:
            bool: True if session was cleaned up successfully
        """
        with self._lock:
            return self._cleanup_session(session_id)
    
    def _cleanup_session(self, session_id: str) -> bool:
        """Internal session cleanup with proper isolation."""
        try:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            # Remove from user sessions tracking
            user_id_str = str(session.user_id)
            if user_id_str in self._user_sessions:
                self._user_sessions[user_id_str].discard(session_id)
                if not self._user_sessions[user_id_str]:
                    del self._user_sessions[user_id_str]
            
            # Remove from context registry
            self._context_registry.pop(session_id, None)
            
            # Remove session
            del self._sessions[session_id]
            
            # Update metrics
            self._metrics.active_sessions = max(0, self._metrics.active_sessions - 1)
            self._metrics.active_contexts = max(0, self._metrics.active_contexts - 1)
            
            logger.info(f"Cleaned up session {session_id} for user {session.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
            return False
    
    # =========================================================================
    # Context Management
    # =========================================================================
    
    def get_execution_context(self, session_id: str) -> Optional[StronglyTypedUserExecutionContext]:
        """Get execution context for session with isolation validation.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Optional[StronglyTypedUserExecutionContext]: Context if valid and isolated
        """
        with self._lock:
            try:
                session = self.get_execution_session(session_id)
                if not session:
                    return None
                
                context = self._context_registry.get(session_id)
                if not context:
                    logger.error(f"Context missing for session {session_id}")
                    self._metrics.context_leaks += 1
                    return None
                
                # Validate context isolation
                if not self._validate_context_isolation(context, session):
                    logger.error(f"Context isolation violation for session {session_id}")
                    self._metrics.isolation_violations += 1
                    return None
                
                return context
                
            except Exception as e:
                logger.error(f"Error retrieving execution context for session {session_id}: {e}")
                return None
    
    def update_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update execution context for session.
        
        Args:
            session_id: Session identifier
            context_updates: Context fields to update
            
        Returns:
            bool: True if update successful
        """
        with self._lock:
            try:
                session = self.get_execution_session(session_id)
                if not session:
                    return False
                
                context = self._context_registry.get(session_id)
                if not context:
                    return False
                
                # Validate updates don't violate isolation
                if not self._validate_context_updates(context_updates, session):
                    logger.error(f"Context update would violate isolation for session {session_id}")
                    self._metrics.isolation_violations += 1
                    return False
                
                # Apply updates to context
                if hasattr(context, 'agent_context') and context.agent_context:
                    context.agent_context.update(context_updates)
                else:
                    # Create agent_context if it doesn't exist
                    context.agent_context = context_updates.copy()
                
                session.update_activity()
                logger.debug(f"Updated context for session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating context for session {session_id}: {e}")
                return False
    
    # =========================================================================
    # Run Management
    # =========================================================================
    
    def register_run(self, session_id: str, run_id: str) -> bool:
        """Register a new run with the session.
        
        Args:
            session_id: Session identifier
            run_id: Run identifier to register
            
        Returns:
            bool: True if registration successful
        """
        with self._lock:
            try:
                session = self.get_execution_session(session_id)
                if not session:
                    return False
                
                session.add_run(run_id)
                logger.debug(f"Registered run {run_id} with session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error registering run {run_id} with session {session_id}: {e}")
                return False
    
    def unregister_run(self, session_id: str, run_id: str) -> bool:
        """Unregister a run from the session.
        
        Args:
            session_id: Session identifier
            run_id: Run identifier to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        with self._lock:
            try:
                session = self.get_execution_session(session_id)
                if not session:
                    return False
                
                session.remove_run(run_id)
                logger.debug(f"Unregistered run {run_id} from session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error unregistering run {run_id} from session {session_id}: {e}")
                return False
    
    # =========================================================================
    # Context Factory and Isolation
    # =========================================================================
    
    def _create_isolated_execution_context(self, user_id: UserID, thread_id: ThreadID,
                                         session_id: str, initial_context: Dict[str, Any]) -> StronglyTypedUserExecutionContext:
        """Create isolated execution context with proper boundaries."""
        try:
            # Generate unique identifiers for this context
            run_id = RunID(f"run_{uuid.uuid4().hex[:12]}")
            request_id = RequestID(f"req_{uuid.uuid4().hex[:12]}")
            
            # Create agent context with isolation boundary
            agent_context = initial_context.copy()
            agent_context.update({
                "isolation_boundary": str(user_id),
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "context_type": "isolated_agent_execution",
                "security_level": "multi_tenant"
            })
            
            # Create strongly typed context
            context = StronglyTypedUserExecutionContext(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_id=request_id,
                db_session=None,  # Will be injected by execution engine
                agent_context=agent_context
            )
            
            logger.debug(f"Created isolated execution context for user {user_id}, session {session_id}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create isolated execution context: {e}")
            raise
    
    def _validate_context_isolation(self, context: StronglyTypedUserExecutionContext, 
                                   session: ExecutionSession) -> bool:
        """Validate that context maintains proper isolation."""
        try:
            # Check user ID matches session
            if context.user_id != session.user_id:
                logger.error(f"Context user ID mismatch: {context.user_id} != {session.user_id}")
                return False
            
            # Check isolation boundary
            if hasattr(context, 'agent_context') and context.agent_context:
                isolation_boundary = context.agent_context.get("isolation_boundary")
                if isolation_boundary != str(session.user_id):
                    logger.error(f"Isolation boundary violation: {isolation_boundary} != {session.user_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Context isolation validation error: {e}")
            return False
    
    def _validate_context_updates(self, updates: Dict[str, Any], session: ExecutionSession) -> bool:
        """Validate that context updates don't violate isolation."""
        try:
            # Check for forbidden fields
            forbidden_fields = {"user_id", "isolation_boundary", "session_id"}
            if any(field in updates for field in forbidden_fields):
                logger.error("Attempt to update forbidden isolation fields")
                return False
            
            # Check for cross-user data
            user_id_str = str(session.user_id)
            for key, value in updates.items():
                if isinstance(value, str) and "user_" in value.lower():
                    # Simple check for user references that don't match current user
                    if user_id_str not in value:
                        logger.warning(f"Potential cross-user reference in context update: {key}={value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Context update validation error: {e}")
            return False
    
    # =========================================================================
    # Monitoring and Metrics
    # =========================================================================
    
    def get_isolation_metrics(self) -> ContextIsolationMetrics:
        """Get current isolation metrics."""
        with self._lock:
            return ContextIsolationMetrics(
                active_sessions=self._metrics.active_sessions,
                active_contexts=self._metrics.active_contexts,
                isolation_violations=self._metrics.isolation_violations,
                context_leaks=self._metrics.context_leaks,
                session_timeouts=self._metrics.session_timeouts
            )
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up all expired sessions and return count."""
        with self._lock:
            expired_sessions = []
            
            for session_id, session in self._sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)
            
            cleanup_count = 0
            for session_id in expired_sessions:
                if self._cleanup_session(session_id):
                    cleanup_count += 1
            
            if cleanup_count > 0:
                self._metrics.session_timeouts += cleanup_count
                logger.info(f"Cleaned up {cleanup_count} expired sessions")
            
            return cleanup_count
    
    @contextmanager
    def execution_session_context(self, user_id: UserID, thread_id: ThreadID, 
                                 initial_context: Optional[Dict[str, Any]] = None):
        """Context manager for automatic session lifecycle management.
        
        Usage:
            with context_manager.execution_session_context(user_id, thread_id) as session_id:
                # Use session_id for agent execution
                pass
        """
        session_id = None
        try:
            session_id = self.create_execution_session(user_id, thread_id, initial_context)
            yield session_id
        finally:
            if session_id:
                self.cleanup_session(session_id)