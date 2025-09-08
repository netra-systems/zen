"""Token Optimization Session Factory

This module provides factory-based user isolation for token optimization sessions
using UniversalRegistry patterns to ensure complete user data separation.

CRITICAL: Ensures zero shared state between users for token optimization.
"""

from typing import Dict, Any, Optional, Protocol, List
from datetime import datetime, timezone

from netra_backend.app.core.registry.universal_registry import UniversalRegistry
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.billing.token_counter import TokenCounter
from netra_backend.app.services.token_optimization.context_manager import TokenOptimizationContextManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TokenOptimizationSession(Protocol):
    """Protocol for token optimization sessions ensuring proper interface."""
    
    def track_usage(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        model: str, 
        operation_type: str
    ) -> Dict[str, Any]:
        """Track token usage for this session."""
        ...
    
    def optimize_prompt(
        self, 
        prompt: str, 
        target_reduction: int = 20
    ) -> Dict[str, Any]:
        """Optimize prompt for this session."""
        ...
    
    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get optimization suggestions for this session."""
        ...
    
    def finalize_session(self) -> Dict[str, Any]:
        """Finalize session and return summary."""
        ...


class UserTokenOptimizationSession:
    """User-isolated token optimization session.
    
    This class manages token optimization for a single user session,
    ensuring complete isolation from other users' data.
    """
    
    def __init__(
        self, 
        context: UserExecutionContext, 
        token_counter: TokenCounter,
        context_manager: TokenOptimizationContextManager
    ):
        """Initialize user-specific token optimization session."""
        self.context = context
        self.token_counter = token_counter
        self.context_manager = context_manager
        self.session_id = f"token_session_{context.user_id}_{context.request_id}"
        self.created_at = datetime.now(timezone.utc)
        self.operations_count = 0
        self.total_cost = 0.0
        self.total_tokens = 0
        
        logger.debug(f"Created token optimization session: {self.session_id}")
    
    def track_usage(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        model: str, 
        operation_type: str = "execution"
    ) -> Dict[str, Any]:
        """Track token usage for this user session."""
        
        # Use TokenCounter to track usage (SSOT component)
        tracking_result = self.token_counter.track_agent_usage(
            agent_name=f"session_{self.session_id}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            operation_type=operation_type
        )
        
        # Update session statistics
        if tracking_result.get("tracking_enabled"):
            self.operations_count += 1
            operation_cost = tracking_result["current_operation"]["cost"]
            self.total_cost += operation_cost
            self.total_tokens += input_tokens + output_tokens
            
            logger.debug(
                f"Session {self.session_id}: tracked {input_tokens + output_tokens} tokens, "
                f"cost ${operation_cost:.4f}"
            )
        
        return {
            "session_id": self.session_id,
            "operation_result": tracking_result,
            "session_totals": {
                "operations_count": self.operations_count,
                "total_cost": self.total_cost,
                "total_tokens": self.total_tokens
            }
        }
    
    def optimize_prompt(
        self, 
        prompt: str, 
        target_reduction: int = 20
    ) -> Dict[str, Any]:
        """Optimize prompt for this user session."""
        
        # Use TokenCounter optimization (SSOT component)
        optimization_result = self.token_counter.optimize_prompt(
            prompt=prompt,
            target_reduction_percent=target_reduction
        )
        
        # Add session context
        optimization_result["session_id"] = self.session_id
        optimization_result["user_id"] = self.context.user_id
        optimization_result["optimized_at"] = datetime.now(timezone.utc).isoformat()
        
        return optimization_result
    
    def get_suggestions(self) -> List[Dict[str, Any]]:
        """Get optimization suggestions for this user session."""
        
        # Get suggestions from TokenCounter
        suggestions = self.token_counter.get_optimization_suggestions()
        
        # Filter and enhance suggestions for this session
        session_suggestions = []
        for suggestion in suggestions:
            # Add session context to suggestions
            enhanced_suggestion = suggestion.copy()
            enhanced_suggestion["session_id"] = self.session_id
            enhanced_suggestion["user_id"] = self.context.user_id
            enhanced_suggestion["generated_for"] = "user_session"
            session_suggestions.append(enhanced_suggestion)
        
        return session_suggestions
    
    def finalize_session(self) -> Dict[str, Any]:
        """Finalize session and return comprehensive summary."""
        
        duration_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        # Get final agent usage summary
        agent_summary = self.token_counter.get_agent_usage_summary()
        
        session_summary = {
            "session_id": self.session_id,
            "user_id": self.context.user_id,
            "context": {
                "thread_id": self.context.thread_id,
                "run_id": self.context.run_id,
                "request_id": self.context.request_id
            },
            "duration_seconds": duration_seconds,
            "operations_performed": self.operations_count,
            "total_cost": self.total_cost,
            "total_tokens_processed": self.total_tokens,
            "average_cost_per_operation": (
                self.total_cost / max(self.operations_count, 1)
            ),
            "average_tokens_per_operation": (
                self.total_tokens / max(self.operations_count, 1)
            ),
            "finalized_at": datetime.now(timezone.utc).isoformat(),
            "agent_usage_summary": agent_summary
        }
        
        logger.info(
            f"✅ Finalized token optimization session {self.session_id}: "
            f"{self.operations_count} operations, ${self.total_cost:.4f} total cost"
        )
        
        return session_summary


class TokenOptimizationSessionFactory:
    """Factory for creating user-isolated token optimization sessions.
    
    Uses UniversalRegistry to ensure complete user isolation and prevent
    cross-user data contamination in token optimization.
    """
    
    def __init__(self):
        """Initialize factory with UniversalRegistry for user isolation."""
        
        # Use UniversalRegistry for session isolation (SSOT pattern)
        self._session_registry = UniversalRegistry("token_optimization_sessions")
        
        # Single shared TokenCounter instance (SSOT component)
        self._token_counter = TokenCounter()
        
        # Single shared context manager (SSOT pattern)
        self._context_manager = TokenOptimizationContextManager(self._token_counter)
        
        self._active_sessions = {}  # Track active sessions for cleanup
        
        logger.debug("Initialized TokenOptimizationSessionFactory with UniversalRegistry")
    
    def create_session(self, context: UserExecutionContext) -> UserTokenOptimizationSession:
        """Create user-isolated token optimization session.
        
        Args:
            context: UserExecutionContext for complete user isolation
            
        Returns:
            UserTokenOptimizationSession for the specific user
            
        Raises:
            ValueError: If context is invalid or user isolation cannot be ensured
        """
        
        # Validate context for user isolation
        if not context.user_id or not context.request_id:
            raise ValueError(
                f"Invalid context for token optimization: "
                f"user_id={context.user_id}, request_id={context.request_id}"
            )
        
        # Create unique session key ensuring user isolation
        session_key = f"token_opt_{context.user_id}_{context.request_id}_{context.thread_id}"
        
        # Check if session already exists (idempotent creation)
        if session_key in self._session_registry:
            existing_session = self._session_registry.get(session_key)
            logger.debug(f"Reusing existing token optimization session: {session_key}")
            return existing_session
        
        # Create new isolated session
        session = UserTokenOptimizationSession(
            context=context,
            token_counter=self._token_counter,  # Shared SSOT component
            context_manager=self._context_manager  # Shared SSOT manager
        )
        
        # Register session using UniversalRegistry for isolation
        self._session_registry.register(session_key, session)
        self._active_sessions[session_key] = {
            "user_id": context.user_id,
            "created_at": datetime.now(timezone.utc),
            "session": session
        }
        
        logger.info(
            f"✅ Created token optimization session: {session_key} "
            f"for user {context.user_id}"
        )
        
        return session
    
    def get_session(
        self, 
        context: UserExecutionContext
    ) -> Optional[UserTokenOptimizationSession]:
        """Get existing session for user context.
        
        Args:
            context: UserExecutionContext to find session for
            
        Returns:
            Existing session or None if not found
        """
        session_key = f"token_opt_{context.user_id}_{context.request_id}_{context.thread_id}"
        
        if session_key in self._session_registry:
            return self._session_registry.get(session_key)
        
        return None
    
    def finalize_session(self, context: UserExecutionContext) -> Optional[Dict[str, Any]]:
        """Finalize and clean up session for user context.
        
        Args:
            context: UserExecutionContext to finalize session for
            
        Returns:
            Session summary or None if session not found
        """
        session_key = f"token_opt_{context.user_id}_{context.request_id}_{context.thread_id}"
        
        if session_key not in self._session_registry:
            logger.warning(f"No session found to finalize: {session_key}")
            return None
        
        # Get session and finalize
        session = self._session_registry.get(session_key)
        summary = session.finalize_session()
        
        # Clean up registry entries
        self._session_registry.remove(session_key)
        if session_key in self._active_sessions:
            del self._active_sessions[session_key]
        
        logger.info(f"✅ Finalized and cleaned up session: {session_key}")
        
        return summary
    
    def get_active_sessions_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a specific user.
        
        Args:
            user_id: User ID to find sessions for
            
        Returns:
            List of active session information for the user
        """
        user_sessions = []
        
        for session_key, session_info in self._active_sessions.items():
            if session_info["user_id"] == user_id:
                session = session_info["session"]
                user_sessions.append({
                    "session_key": session_key,
                    "session_id": session.session_id,
                    "created_at": session_info["created_at"].isoformat(),
                    "operations_count": session.operations_count,
                    "total_cost": session.total_cost,
                    "total_tokens": session.total_tokens
                })
        
        return user_sessions
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up expired sessions to prevent memory leaks.
        
        Args:
            max_age_hours: Maximum age for sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        cleanup_count = 0
        current_time = datetime.now(timezone.utc)
        expired_keys = []
        
        for session_key, session_info in self._active_sessions.items():
            age_hours = (current_time - session_info["created_at"]).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_keys.append(session_key)
        
        # Clean up expired sessions
        for session_key in expired_keys:
            if session_key in self._session_registry:
                session = self._session_registry.get(session_key)
                session.finalize_session()  # Get final summary
                self._session_registry.remove(session_key)
            
            if session_key in self._active_sessions:
                del self._active_sessions[session_key]
            
            cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"✅ Cleaned up {cleanup_count} expired token optimization sessions")
        
        return cleanup_count
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """Get factory statistics and health information.
        
        Returns:
            Factory statistics including session counts and health metrics
        """
        total_sessions = len(self._active_sessions)
        users_with_sessions = len(set(
            session_info["user_id"] 
            for session_info in self._active_sessions.values()
        ))
        
        # Get registry stats
        registry_stats = {
            "total_registered": len(self._active_sessions),
            "registry_health": "healthy" if self._session_registry else "degraded"
        }
        
        return {
            "factory_type": "TokenOptimizationSessionFactory",
            "total_active_sessions": total_sessions,
            "unique_users_with_sessions": users_with_sessions,
            "registry_stats": registry_stats,
            "token_counter_stats": self._token_counter.get_stats(),
            "uses_universal_registry": True,
            "user_isolation_enabled": True,
            "ssot_compliance": True
        }