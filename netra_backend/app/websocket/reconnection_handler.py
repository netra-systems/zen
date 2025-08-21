"""WebSocket Reconnection Handler for Agent Startup

Handles connection state preservation across WebSocket reconnections,
ensuring agent context and conversation state remain intact.

Business Value: Preserves agent session continuity worth $200K+ MRR.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket.connection_info import ConnectionInfo, ConnectionState
from netra_backend.app.agents.base.reliability_manager import ReliabilityManager
from netra_backend.app.agents.base.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.schemas.shared_types import RetryConfig

logger = central_logger.get_logger(__name__)


@dataclass
class ReconnectionContext:
    """Context for WebSocket reconnection attempts."""
    user_id: str
    original_connection_id: str
    session_data: Dict[str, Any]
    agent_state: Optional[Dict[str, Any]] = None
    conversation_history: List[Dict[str, Any]] = None
    last_activity: datetime = None
    reconnection_attempts: int = 0


class WebSocketReconnectionHandler:
    """Handles WebSocket reconnections with state preservation."""
    
    def __init__(self):
        self.reconnection_contexts: Dict[str, ReconnectionContext] = {}
        self.reliability_manager = self._create_reliability_manager()
        self.max_reconnection_window = 300  # 5 minutes
        self.max_reconnection_attempts = 5
        
    def _create_reliability_manager(self) -> ReliabilityManager:
        """Create reliability manager for reconnection attempts."""
        circuit_config = CircuitBreakerConfig(
            name="websocket_reconnection",
            failure_threshold=3,
            recovery_timeout=60
        )
        retry_config = RetryConfig(
            max_retries=2,
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0
        )
        return ReliabilityManager(circuit_config, retry_config)
        
    async def prepare_for_reconnection(self, conn_info: ConnectionInfo,
                                     agent_state: Optional[Dict[str, Any]] = None) -> str:
        """Prepare connection context for potential reconnection."""
        reconnection_token = f"reconnect_{conn_info.connection_id}_{int(time.time())}"
        
        context = ReconnectionContext(
            user_id=conn_info.user_id,
            original_connection_id=conn_info.connection_id,
            session_data=self._extract_session_data(conn_info),
            agent_state=agent_state,
            last_activity=datetime.now(timezone.utc)
        )
        
        self.reconnection_contexts[reconnection_token] = context
        logger.info(f"Prepared reconnection context for {conn_info.user_id}: {reconnection_token}")
        return reconnection_token
        
    def _extract_session_data(self, conn_info: ConnectionInfo) -> Dict[str, Any]:
        """Extract essential session data for preservation."""
        return {
            "connected_at": conn_info.connected_at,
            "message_count": conn_info.message_count,
            "last_ping": conn_info.last_ping,
            "last_message_time": conn_info.last_message_time,
            "rate_limit_count": conn_info.rate_limit_count,
            "rate_limit_window_start": conn_info.rate_limit_window_start
        }
        
    async def attempt_reconnection(self, reconnection_token: str,
                                 new_websocket) -> Optional[ConnectionInfo]:
        """Attempt to reconnect with preserved state."""
        context = self.reconnection_contexts.get(reconnection_token)
        if not context:
            logger.warning(f"Reconnection context not found: {reconnection_token}")
            return None
            
        if not self._is_reconnection_valid(context):
            logger.info(f"Reconnection window expired for {context.user_id}")
            self._cleanup_context(reconnection_token)
            return None
            
        context.reconnection_attempts += 1
        logger.info(f"Attempting reconnection for {context.user_id} (attempt {context.reconnection_attempts})")
        
        try:
            return await self._execute_reconnection(context, new_websocket)
        except Exception as e:
            logger.error(f"Reconnection failed for {context.user_id}: {e}")
            if context.reconnection_attempts >= self.max_reconnection_attempts:
                self._cleanup_context(reconnection_token)
            return None
            
    def _is_reconnection_valid(self, context: ReconnectionContext) -> bool:
        """Check if reconnection is still valid within time window."""
        if not context.last_activity:
            return False
            
        time_elapsed = (datetime.now(timezone.utc) - context.last_activity).total_seconds()
        return time_elapsed <= self.max_reconnection_window
        
    async def _execute_reconnection(self, context: ReconnectionContext,
                                  new_websocket) -> ConnectionInfo:
        """Execute the reconnection with state restoration."""
        # Create new connection info with preserved data
        conn_info = ConnectionInfo(
            websocket=new_websocket,
            user_id=context.user_id,
            connected_at=datetime.now(timezone.utc),
            message_count=context.session_data.get("message_count", 0),
            last_ping=datetime.now(timezone.utc),
            rate_limit_count=context.session_data.get("rate_limit_count", 0),
            rate_limit_window_start=context.session_data.get("rate_limit_window_start", datetime.now(timezone.utc))
        )
        
        logger.info(f"Reconnected {context.user_id} with preserved state: {context.session_data}")
        return conn_info
        
    def get_preserved_agent_state(self, reconnection_token: str) -> Optional[Dict[str, Any]]:
        """Get preserved agent state for reconnection."""
        context = self.reconnection_contexts.get(reconnection_token)
        return context.agent_state if context else None
        
    def update_conversation_history(self, reconnection_token: str,
                                  history: List[Dict[str, Any]]) -> None:
        """Update conversation history for reconnection context."""
        context = self.reconnection_contexts.get(reconnection_token)
        if context:
            context.conversation_history = history
            logger.debug(f"Updated conversation history for {context.user_id}")
            
    def _cleanup_context(self, reconnection_token: str) -> None:
        """Clean up expired or completed reconnection context."""
        context = self.reconnection_contexts.pop(reconnection_token, None)
        if context:
            logger.info(f"Cleaned up reconnection context for {context.user_id}")
            
    async def cleanup_expired_contexts(self) -> int:
        """Clean up expired reconnection contexts."""
        current_time = datetime.now(timezone.utc)
        expired_tokens = []
        
        for token, context in self.reconnection_contexts.items():
            if not context.last_activity:
                expired_tokens.append(token)
                continue
                
            time_elapsed = (current_time - context.last_activity).total_seconds()
            if time_elapsed > self.max_reconnection_window:
                expired_tokens.append(token)
                
        for token in expired_tokens:
            self._cleanup_context(token)
            
        logger.info(f"Cleaned up {len(expired_tokens)} expired reconnection contexts")
        return len(expired_tokens)
        
    def get_reconnection_stats(self) -> Dict[str, Any]:
        """Get reconnection statistics."""
        active_contexts = len(self.reconnection_contexts)
        
        attempt_counts = [ctx.reconnection_attempts for ctx in self.reconnection_contexts.values()]
        avg_attempts = sum(attempt_counts) / len(attempt_counts) if attempt_counts else 0
        
        return {
            "active_reconnection_contexts": active_contexts,
            "average_reconnection_attempts": avg_attempts,
            "max_attempts_allowed": self.max_reconnection_attempts,
            "reconnection_window_seconds": self.max_reconnection_window,
            "reliability_health": self.reliability_manager.get_health_status()
        }


# Global instance for WebSocket reconnection handling
_reconnection_handler: Optional[WebSocketReconnectionHandler] = None


def get_reconnection_handler() -> WebSocketReconnectionHandler:
    """Get global reconnection handler instance."""
    global _reconnection_handler
    if _reconnection_handler is None:
        _reconnection_handler = WebSocketReconnectionHandler()
    return _reconnection_handler