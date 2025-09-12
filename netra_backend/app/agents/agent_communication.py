"""Agent Communication Module

Handles WebSocket communication, error handling, and message updates for agents.
"""

import asyncio
import time
from typing import Dict, Optional

from langchain_core.messages import SystemMessage
from starlette.websockets import WebSocketDisconnect

# Import error types from canonical sources to maintain SSOT compliance
from netra_backend.app.core.exceptions_database import DatabaseError
from netra_backend.app.core.exceptions_websocket import WebSocketError
from netra_backend.app.schemas.shared_types import ErrorContext, NestedJsonDict
from netra_backend.app.agents.base.timing_decorators import time_operation, TimingCategory
from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.agent import SubAgentState, SubAgentUpdate
from netra_backend.app.schemas.registry import WebSocketMessage, WebSocketMessageType
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = central_logger.get_logger(__name__)


class AgentCommunicationMixin:
    """Mixin providing agent communication functionality"""
    
    @time_operation("send_websocket_update", TimingCategory.NETWORK)
    async def _send_update(self, run_id: str, data: NestedJsonDict) -> None:
        """Send WebSocket update with proper error recovery."""
        # Use unified emit methods from BaseAgent's WebSocketBridgeAdapter
        await self._execute_websocket_update_with_retry(run_id, data)
    
    async def _execute_websocket_update_with_retry(self, run_id: str, data: NestedJsonDict) -> None:
        """Execute WebSocket update with retry logic."""
        max_retries, retry_count = 3, 0
        while retry_count < max_retries:
            success = await self._attempt_single_update(run_id, data, retry_count, max_retries)
            if success:
                return
            retry_count += 1
    
    async def _handle_retry_or_failure(self, run_id: str, data: NestedJsonDict, 
                                      error: Exception, retry_count: int, max_retries: int) -> None:
        """Handle retry logic or final failure."""
        if retry_count >= max_retries:
            self.logger.warning(f"WebSocket update failed after {max_retries} attempts: {error}")
            await self._handle_websocket_failure(run_id, data, error)
            return
        await self._apply_exponential_backoff(retry_count)
    
    async def _apply_exponential_backoff(self, retry_count: int) -> None:
        """Apply exponential backoff delay."""
        await asyncio.sleep(0.1 * (2 ** retry_count))
                
    async def _attempt_websocket_update(self, run_id: str, data: NestedJsonDict) -> None:
        """Attempt to send WebSocket update using unified emit methods."""
        # Use emit methods from BaseAgent's WebSocketBridgeAdapter
        status = data.get("status", "")
        message = data.get("message", "")
        
        if status == "starting":
            await self.emit_agent_started(message)
        elif status == "completed":
            await self.emit_agent_completed({"status": status, "message": message})
        elif status == "failed":
            await self.emit_error(message, "execution_failure")
        elif status == "error":
            await self.emit_error(message)
        else:
            # Default to thinking notification for updates
            await self.emit_thinking(message)
    
    def _create_sub_agent_state(self, data: NestedJsonDict) -> SubAgentState:
        """Create SubAgentState from data."""
        message = self._build_system_message(data)
        return self._construct_sub_agent_state(message)
    
    def _build_system_message(self, data: NestedJsonDict) -> SystemMessage:
        """Build SystemMessage from data."""
        message_content = data.get("message", "")
        return SystemMessage(content=message_content)
    
    def _construct_sub_agent_state(self, message: SystemMessage) -> SubAgentState:
        """Construct SubAgentState with message."""
        return SubAgentState(
            messages=[message],
            next_node="",
            lifecycle=self.get_state()
        )
    
    def _create_update_payload(self, sub_agent_state: SubAgentState) -> SubAgentUpdate:
        """Create update payload from state."""
        return SubAgentUpdate(
            sub_agent_name=self.name,
            state=sub_agent_state
        )
    
    def _create_websocket_message(self, update_payload: SubAgentUpdate) -> WebSocketMessage:
        """Create WebSocket message from payload."""
        return WebSocketMessage(
            type=WebSocketMessageType.SUB_AGENT_UPDATE,
            payload=update_payload.model_dump()
        )
        
    def _get_websocket_user_id(self, run_id: str) -> str:
        """Get WebSocket user ID with fallback."""
        if hasattr(self, '_user_id'):
            return self._user_id
        manager_id = self._get_manager_user_id(run_id)
        if manager_id:
            return manager_id
        return self._handle_fallback_user_id(run_id)
        
    async def _handle_websocket_failure(self, run_id: str, data: NestedJsonDict, error: Exception) -> None:
        """Handle WebSocket failure with graceful degradation and centralized error tracking."""
        context = self._create_error_context(run_id, data)
        websocket_error = WebSocketError(
            f"WebSocket update failed: {str(error)}", 
            context=context.model_dump()
        )
        self._process_websocket_error(websocket_error)
        self._store_failed_update(run_id, data, error)
    
    def _create_error_context(self, run_id: str, data: NestedJsonDict) -> ErrorContext:
        """Create error context for centralized handling."""
        context_params = self._build_error_context_params(run_id, data)
        # Ensure required fields for canonical ErrorContext
        context_params['trace_id'] = context_params.get('trace_id', f"agent_comm_{run_id}")
        context_params['operation'] = context_params.get('operation', 'websocket_update')
        return ErrorContext(**context_params)
    
    def _build_error_context_params(self, run_id: str, data: NestedJsonDict) -> NestedJsonDict:
        """Build error context parameters."""
        basic_params = self._get_basic_context_params(run_id)
        extended_params = self._get_extended_context_params(data)
        # Map to canonical ErrorContext field names
        params = {**basic_params, **extended_params}
        return {
            'trace_id': params.get('trace_id', f"agent_comm_{run_id}"),
            'operation': params.get('operation_name', 'websocket_update'),
            'agent_name': params.get('agent_name'),
            'run_id': params.get('run_id'),
            'additional_data': params.get('additional_data', {})
        }
    
    def _get_basic_context_params(self, run_id: str) -> NestedJsonDict:
        """Get basic context parameters."""
        return {
            "agent_name": self.name,
            "operation_name": "websocket_update",
            "run_id": run_id,
            "trace_id": f"agent_comm_{run_id}",
            "timestamp": time.time()
        }
    
    def _get_extended_context_params(self, data: NestedJsonDict) -> NestedJsonDict:
        """Get extended context parameters."""
        return {"additional_data": data}
    
    def _process_websocket_error(self, websocket_error: WebSocketError) -> None:
        """Process WebSocket error through centralized handler."""
        # Log error directly instead of using global_error_handler to avoid circular import
        agent_id = getattr(self, 'agent_id', getattr(self, 'name', 'unknown'))
        logger.error(f"WebSocket error for agent {agent_id}: {websocket_error}")
    
    def _store_failed_update(self, run_id: str, data: NestedJsonDict, error: Exception) -> None:
        """Store failed update for potential retry later."""
        self._ensure_failed_updates_list()
        failed_update = self._create_failed_update_record(run_id, data, error)
        self._failed_updates.append(failed_update)
        self._limit_failed_updates_storage()
    
    def _limit_failed_updates_storage(self) -> None:
        """Limit failed updates storage to recent entries."""
        if len(self._failed_updates) > 10:
            self._failed_updates = self._failed_updates[-10:]

    async def run_in_background(self, user_context: UserExecutionContext, run_id: str, stream_updates: bool) -> None:
        """Run agent in background task."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.run(user_context, run_id, stream_updates))
    
    async def _attempt_single_update(self, run_id: str, data: NestedJsonDict, retry_count: int, max_retries: int) -> bool:
        """Attempt single WebSocket update with error handling."""
        try:
            await self._attempt_websocket_update(run_id, data)
            return True
        except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
            return await self._handle_websocket_exception(run_id, data, e, retry_count + 1, max_retries)
        except Exception:
            return self._handle_unexpected_websocket_error_fallback()
    
    async def _handle_websocket_exception(self, run_id: str, data: NestedJsonDict, 
                                        error: Exception, retry_count: int, max_retries: int) -> bool:
        """Handle WebSocket connection exceptions."""
        await self._handle_retry_or_failure(run_id, data, error, retry_count, max_retries)
        return False
    
    def _handle_unexpected_websocket_error(self, error: Exception) -> bool:
        """Handle unexpected WebSocket errors."""
        self.logger.error(f"Unexpected error in WebSocket update: {error}")
        return False
    
    def _handle_unexpected_websocket_error_fallback(self) -> bool:
        """Handle unexpected WebSocket errors with fallback."""
        self.logger.error("Unexpected error in WebSocket update")
        return False
    
    def _build_websocket_message(self, run_id: str, data: NestedJsonDict) -> WebSocketMessage:
        """Build complete WebSocket message."""
        sub_agent_state = self._create_sub_agent_state(data)
        update_payload = self._create_update_payload(sub_agent_state)
        return self._create_websocket_message(update_payload)
    
    def _get_manager_user_id(self, run_id: str) -> Optional[str]:
        """Get user ID from legacy context (deprecated)."""
        # Legacy method - user_id is now handled by WebSocketBridgeAdapter
        return None
    
    def _handle_fallback_user_id(self, run_id: str) -> str:
        """Handle fallback user ID logic."""
        if run_id.startswith('run_'):
            logger.warning(f"Using run_id {run_id} as fallback for user_id")
        return run_id
    
    def _ensure_failed_updates_list(self) -> None:
        """Ensure failed updates list exists."""
        if not hasattr(self, '_failed_updates'):
            self._failed_updates = []
    
    def _create_failed_update_record(self, run_id: str, data: NestedJsonDict, error: Exception) -> NestedJsonDict:
        """Create failed update record."""
        return {
            "run_id": run_id,
            "data": data,
            "timestamp": time.time(),
            "error": str(error)
        }
    
            
    
    
    
