"""Agent Communication Module

Handles WebSocket communication, error handling, and message updates for agents.
"""

import time
import asyncio
from typing import Dict, Any
from starlette.websockets import WebSocketDisconnect
from langchain_core.messages import SystemMessage

from app.schemas import SubAgentUpdate, SubAgentState
from app.schemas.registry import WebSocketMessage, WebSocketMessageType
from app.agents.error_handler import global_error_handler, ErrorContext, WebSocketError
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentCommunicationMixin:
    """Mixin providing agent communication functionality"""
    
    async def _send_update(self, run_id: str, data: Dict[str, Any]) -> None:
        """Send WebSocket update with proper error recovery."""
        if not self.websocket_manager:
            return
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                await self._attempt_websocket_update(run_id, data)
                return  # Success, exit retry loop
            except (WebSocketDisconnect, RuntimeError, ConnectionError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.warning(f"WebSocket update failed after {max_retries} attempts: {e}")
                    await self._handle_websocket_failure(run_id, data, e)
                    return
                
                # Exponential backoff for retries
                await asyncio.sleep(0.1 * (2 ** retry_count))
            except Exception as e:
                self.logger.error(f"Unexpected error in WebSocket update: {e}")
                return
                
    async def _attempt_websocket_update(self, run_id: str, data: Dict[str, Any]) -> None:
        """Attempt to send WebSocket update."""
        message_content = data.get("message", "")
        message = SystemMessage(content=message_content)
        
        sub_agent_state = SubAgentState(
            messages=[message],
            next_node="",
            lifecycle=self.get_state()
        )
        
        ws_user_id = self._get_websocket_user_id(run_id)
        
        update_payload = SubAgentUpdate(
            sub_agent_name=self.name,
            state=sub_agent_state
        )
        
        websocket_message = WebSocketMessage(
            type=WebSocketMessageType.SUB_AGENT_UPDATE,
            payload=update_payload.model_dump()
        )
        
        await self.websocket_manager.send_message(
            ws_user_id,
            websocket_message.model_dump()
        )
        
    def _get_websocket_user_id(self, run_id: str) -> str:
        """Get WebSocket user ID with fallback."""
        if hasattr(self, '_user_id'):
            return self._user_id
        if hasattr(self.websocket_manager, '_current_user_id'):
            return getattr(self.websocket_manager, '_current_user_id', run_id)
        # Extract user_id from run_id pattern if possible
        # run_id format: run_<uuid> vs user_id format: <uuid>
        if run_id.startswith('run_'):
            logger.warning(f"Using run_id {run_id} as fallback for user_id")
        return run_id
        
    async def _handle_websocket_failure(self, run_id: str, data: Dict[str, Any], error: Exception) -> None:
        """Handle WebSocket failure with graceful degradation and centralized error tracking."""
        # Create error context for centralized handling
        context = ErrorContext(
            agent_name=self.name,
            operation_name="websocket_update", 
            run_id=run_id,
            timestamp=time.time(),
            additional_data=data
        )
        
        # Use centralized error handler for consistent tracking
        websocket_error = WebSocketError(f"WebSocket update failed: {str(error)}", context)
        global_error_handler._store_error(websocket_error)
        global_error_handler._log_error(websocket_error)
        
        # Store failed update for potential retry later
        if not hasattr(self, '_failed_updates'):
            self._failed_updates = []
        
        self._failed_updates.append({
            "run_id": run_id,
            "data": data,
            "timestamp": time.time(),
            "error": str(error)
        })
        
        # Keep only recent failed updates (max 10)
        if len(self._failed_updates) > 10:
            self._failed_updates = self._failed_updates[-10:]

    async def run_in_background(self, state, run_id: str, stream_updates: bool) -> None:
        """Run agent in background task."""
        loop = asyncio.get_event_loop()
        loop.create_task(self.run(state, run_id, stream_updates))