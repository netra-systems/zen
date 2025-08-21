"""Supervisor Agent Lifecycle Manager.

Manages agent lifecycle transitions according to unified spec requirements.
Business Value: Ensures proper agent state transitions and error handling.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from app.logging_config import central_logger
from app.agents.state import DeepAgentState
from app.agents.base.interface import ExecutionContext, ExecutionResult
from app.schemas.core_enums import ExecutionStatus
from app.agents.base.errors import ValidationError

logger = central_logger.get_logger(__name__)


class SupervisorLifecycleManager:
    """Manages supervisor agent lifecycle according to unified spec."""
    
    def __init__(self):
        self._active_contexts: Dict[str, ExecutionContext] = {}
        self._lifecycle_hooks: Dict[str, list] = {
            "pre_execution": [],
            "post_execution": [],
            "on_error": [],
            "on_success": []
        }
    
    async def validate_entry_conditions(self, context: ExecutionContext) -> bool:
        """Validate entry conditions per unified spec requirements."""
        await self._validate_user_request_present(context.state)
        await self._validate_authentication_verified(context)
        await self._validate_thread_context_established(context)
        return True
    
    async def _validate_user_request_present(self, state: DeepAgentState) -> None:
        """Validate user request is present."""
        if not hasattr(state, 'user_request') or not state.user_request:
            raise ValidationError("Missing required user_request in state")
    
    async def _validate_authentication_verified(self, context: ExecutionContext) -> None:
        """Validate authentication is verified."""
        if not context.user_id:
            raise ValidationError("Authentication not verified - missing user_id")
    
    async def _validate_thread_context_established(self, context: ExecutionContext) -> None:
        """Validate thread context is established."""
        if not context.thread_id:
            raise ValidationError("Thread context not established - missing thread_id")
    
    async def check_exit_conditions(self, context: ExecutionContext, 
                                   result: ExecutionResult) -> bool:
        """Check exit conditions per unified spec."""
        return await self._should_exit_workflow(context, result)
    
    async def _should_exit_workflow(self, context: ExecutionContext, 
                                   result: ExecutionResult) -> bool:
        """Determine if workflow should exit."""
        exit_conditions = [
            result.status == ExecutionStatus.COMPLETED,
            result.status == ExecutionStatus.FAILED,
            self._error_threshold_exceeded(context)
        ]
        return any(exit_conditions)
    
    def _error_threshold_exceeded(self, context: ExecutionContext) -> bool:
        """Check if error threshold is exceeded."""
        return context.retry_count >= context.max_retries
    
    def register_lifecycle_hook(self, event: str, handler) -> None:
        """Register lifecycle event hook."""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].append(handler)
    
    async def execute_lifecycle_hooks(self, event: str, 
                                     context: ExecutionContext, 
                                     **kwargs) -> None:
        """Execute registered lifecycle hooks."""
        hooks = self._lifecycle_hooks.get(event, [])
        for hook in hooks:
            try:
                await hook(context, **kwargs)
            except Exception as e:
                logger.warning(f"Lifecycle hook {event} failed: {e}")
    
    def track_active_context(self, context: ExecutionContext) -> None:
        """Track active execution context."""
        self._active_contexts[context.run_id] = context
    
    def clear_active_context(self, run_id: str) -> None:
        """Clear active execution context."""
        self._active_contexts.pop(run_id, None)
    
    def get_active_contexts(self) -> Dict[str, ExecutionContext]:
        """Get all active execution contexts."""
        return self._active_contexts.copy()
