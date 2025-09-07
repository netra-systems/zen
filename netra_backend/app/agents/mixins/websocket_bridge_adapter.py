"""WebSocket Bridge Adapter for Agents

This adapter provides agents with a clean interface to AgentWebSocketBridge,
replacing the legacy WebSocketContextMixin pattern.

Business Value: SSOT for WebSocket event emission, eliminating duplicate code
BVJ: Platform/Internal | Stability | Single source of truth for agent-websocket coordination
"""

from typing import TYPE_CHECKING, Optional, Any, Dict
from netra_backend.app.logging_config import central_logger

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

logger = central_logger.get_logger(__name__)


class WebSocketBridgeAdapter:
    """Adapter providing agents with WebSocket event emission through AgentWebSocketBridge.
    
    This replaces the legacy WebSocketContextMixin pattern with the SSOT bridge approach.
    All WebSocket events go through the centralized AgentWebSocketBridge.
    
    Critical Events for Chat Functionality:
    1. agent_started - User sees agent began processing
    2. agent_thinking - Real-time reasoning visibility
    3. tool_executing - Tool usage transparency
    4. tool_completed - Tool results display
    5. agent_completed - User knows when done
    """
    
    def __init__(self):
        """Initialize the adapter."""
        self._bridge: Optional['AgentWebSocketBridge'] = None
        self._run_id: Optional[str] = None
        self._agent_name: Optional[str] = None
        
    def set_websocket_bridge(self, bridge: 'AgentWebSocketBridge', 
                            run_id: str, agent_name: str) -> None:
        """Set the WebSocket bridge for event emission.
        
        Args:
            bridge: The AgentWebSocketBridge instance
            run_id: The execution run ID
            agent_name: The name of the agent
        """
        if not bridge:
            logger.error(f"❌ CRITICAL: Attempting to set None bridge on WebSocketBridgeAdapter for {agent_name}!")
            logger.error(f"   This will cause ALL WebSocket events from {agent_name} to fail silently!")
        if not run_id:
            logger.error(f"❌ CRITICAL: Attempting to set None run_id on WebSocketBridgeAdapter for {agent_name}!")
            
        self._bridge = bridge
        self._run_id = run_id
        self._agent_name = agent_name
        
        if bridge and run_id:
            logger.info(f"✅ WebSocket bridge configured for {agent_name} (run_id: {run_id}, bridge_type: {type(bridge).__name__})")
        else:
            logger.error(f"❌ WebSocket bridge configuration FAILED for {agent_name} - bridge={bridge is not None}, run_id={run_id is not None}")
    
    def has_websocket_bridge(self) -> bool:
        """Check if WebSocket bridge is available."""
        return self._bridge is not None and self._run_id is not None
    
    async def emit_agent_started(self, message: Optional[str] = None) -> None:
        """Emit agent started event."""
        if not self.has_websocket_bridge():
            error_msg = (
                f"CRITICAL: Agent {self._agent_name} missing WebSocket bridge - "
                f"agent_started event will be lost! Users will not see AI working. "
                f"Bridge={self._bridge is not None}, Run_ID={self._run_id}"
            )
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: {error_msg}")
            
            # HARD FAILURE: Raise exception instead of silent return
            # Per CLAUDE.MD Section 6: WebSocket events are MISSION CRITICAL for chat value
            raise RuntimeError(
                f"Missing WebSocket bridge for agent_started event. "
                f"Agent: {self._agent_name}, Bridge: {self._bridge is not None}, Run_ID: {self._run_id}. "
                f"This violates SSOT requirement for mandatory WebSocket notifications."
            )
        
        try:
            context = {"message": message} if message else {}
            await self._bridge.notify_agent_started(
                self._run_id, 
                self._agent_name,
                context=context
            )
        except Exception as e:
            logger.debug(f"Failed to emit agent_started: {e}")
    
    async def emit_thinking(self, thought: str, step_number: Optional[int] = None) -> None:
        """Emit agent thinking event for real-time reasoning visibility."""
        if not self.has_websocket_bridge():
            error_msg = (
                f"CRITICAL: Agent {self._agent_name} missing WebSocket bridge - "
                f"agent_thinking event will be lost! Users will not see real-time reasoning. "
                f"Bridge={self._bridge is not None}, Run_ID={self._run_id}"
            )
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: {error_msg}")
            
            # HARD FAILURE: Raise exception instead of silent return
            # Per CLAUDE.MD Section 6: Real-time reasoning visibility is MISSION CRITICAL
            raise RuntimeError(
                f"Missing WebSocket bridge for agent_thinking event. "
                f"Agent: {self._agent_name}, Bridge: {self._bridge is not None}, Run_ID: {self._run_id}. "
                f"This violates SSOT requirement for mandatory WebSocket notifications."
            )
        
        try:
            await self._bridge.notify_agent_thinking(
                self._run_id,
                self._agent_name,
                thought,  # reasoning parameter
                step_number=step_number
            )
        except Exception as e:
            logger.debug(f"Failed to emit thinking: {e}")
    
    async def emit_tool_executing(self, tool_name: str, 
                                 parameters: Optional[Dict[str, Any]] = None) -> None:
        """Emit tool executing event."""
        if not self.has_websocket_bridge():
            return
        
        try:
            await self._bridge.notify_tool_executing(
                self._run_id,
                self._agent_name,
                tool_name,
                parameters=parameters
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool_executing: {e}")
    
    async def emit_tool_completed(self, tool_name: str, 
                                 result: Optional[Dict[str, Any]] = None) -> None:
        """Emit tool completed event."""
        if not self.has_websocket_bridge():
            return
        
        try:
            await self._bridge.notify_tool_completed(
                self._run_id,
                self._agent_name,
                tool_name,
                result=result
            )
        except Exception as e:
            logger.debug(f"Failed to emit tool_completed: {e}")
    
    async def emit_agent_completed(self, result: Optional[Dict[str, Any]] = None) -> None:
        """Emit agent completed event."""
        if not self.has_websocket_bridge():
            error_msg = (
                f"CRITICAL: Agent {self._agent_name} missing WebSocket bridge - "
                f"agent_completed event will be lost! Users will not know when valuable response is ready. "
                f"Bridge={self._bridge is not None}, Run_ID={self._run_id}"
            )
            logger.critical(f"🚨 BUSINESS VALUE FAILURE: {error_msg}")
            
            # HARD FAILURE: Raise exception instead of silent return
            # Per CLAUDE.MD Section 6: Users must know when valuable response is ready
            raise RuntimeError(
                f"Missing WebSocket bridge for agent_completed event. "
                f"Agent: {self._agent_name}, Bridge: {self._bridge is not None}, Run_ID: {self._run_id}. "
                f"This violates SSOT requirement for mandatory WebSocket notifications."
            )
        
        try:
            await self._bridge.notify_agent_completed(
                self._run_id,
                self._agent_name,
                result=result
            )
        except Exception as e:
            logger.debug(f"Failed to emit agent_completed: {e}")
    
    async def emit_progress(self, content: str, is_complete: bool = False) -> None:
        """Emit progress update."""
        if not self.has_websocket_bridge():
            return
        
        try:
            progress_data = {
                "content": content,
                "is_complete": is_complete
            }
            await self._bridge.notify_progress_update(
                self._run_id,
                self._agent_name,
                progress_data
            )
        except Exception as e:
            logger.debug(f"Failed to emit progress: {e}")
    
    async def emit_error(self, error_message: str, 
                        error_type: Optional[str] = None,
                        error_details: Optional[Dict[str, Any]] = None) -> None:
        """Emit error event."""
        if not self.has_websocket_bridge():
            return
        
        try:
            error_context = {
                "error_type": error_type or "general",
                "details": error_details
            } if error_type or error_details else None
            
            await self._bridge.notify_agent_error(
                self._run_id,
                self._agent_name,
                error_message,
                error_context=error_context
            )
        except Exception as e:
            logger.debug(f"Failed to emit error: {e}")
    
    # Backward compatibility methods for existing code
    async def emit_tool_started(self, tool_name: str, 
                               parameters: Optional[Dict[str, Any]] = None) -> None:
        """Backward compatibility: emit_tool_started maps to emit_tool_executing."""
        await self.emit_tool_executing(tool_name, parameters)
    
    async def emit_subagent_started(self, subagent_name: str, 
                                   subagent_id: Optional[str] = None) -> None:
        """Emit subagent started event (uses custom notification)."""
        if not self.has_websocket_bridge():
            return
        
        try:
            await self._bridge.notify_custom(
                self._run_id,
                self._agent_name,
                "subagent_started",
                {"subagent_name": subagent_name, "subagent_id": subagent_id}
            )
        except Exception as e:
            logger.debug(f"Failed to emit subagent_started: {e}")
    
    async def emit_subagent_completed(self, subagent_name: str,
                                     subagent_id: Optional[str] = None,
                                     result: Optional[Dict[str, Any]] = None,
                                     duration_ms: float = 0) -> None:
        """Emit subagent completed event (uses custom notification)."""
        if not self.has_websocket_bridge():
            return
        
        try:
            await self._bridge.notify_custom(
                self._run_id,
                self._agent_name,
                "subagent_completed",
                {
                    "subagent_name": subagent_name,
                    "subagent_id": subagent_id,
                    "result": result,
                    "duration_ms": duration_ms
                }
            )
        except Exception as e:
            logger.debug(f"Failed to emit subagent_completed: {e}")