"""SSOT WebSocket Bridge Factory - Standard interface for all WebSocket bridge adapters.

This module consolidates multiple WebSocketBridgeAdapter implementations into a unified
interface, eliminating duplicate code and providing standardized WebSocket event handling.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: SSOT Compliance & WebSocket Event Reliability
- Value Impact: Ensures consistent WebSocket event delivery across all tool dispatchers and agents
- Strategic Impact: Protects $500K+ ARR chat functionality through reliable event infrastructure

Key Consolidation Goals:
- Single WebSocket bridge interface for all adapters
- Standardized event handling across RequestScopedToolDispatcher, UnifiedToolDispatcher, agents
- Eliminates duplicate WebSocketBridgeAdapter implementations
- Maintains all 5 critical WebSocket events with enhanced reliability
- Provides backward compatibility for existing bridge interfaces

Replaces:
- Multiple WebSocketBridgeAdapter classes in various modules
- Inconsistent bridge adapter patterns
- Duplicate event validation and error handling logic
- Scattered WebSocket bridge creation patterns

The StandardWebSocketBridge ensures reliable delivery of all critical WebSocket events
while providing a unified interface for all components that need WebSocket functionality.
"""

import asyncio
import time
import warnings
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Protocol
from datetime import datetime, timezone
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
    from netra_backend.app.websocket_core import WebSocketEventEmitter

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


# ===================== STANDARD WEBSOCKET BRIDGE INTERFACE =====================

class WebSocketBridgeProtocol(Protocol):
    """Standard protocol for all WebSocket bridge implementations.
    
    This protocol defines the required interface that all WebSocket bridges
    must implement to ensure consistent event delivery across the platform.
    """
    
    async def notify_agent_started(
        self,
        run_id: str,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that an agent has started."""
        ...
    
    async def notify_agent_thinking(
        self,
        run_id: str,
        agent_name: str,
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """Notify that an agent is thinking."""
        ...
    
    async def notify_tool_executing(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that a tool is executing."""
        ...
    
    async def notify_tool_completed(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that a tool has completed."""
        ...
    
    async def notify_agent_completed(
        self,
        run_id: str,
        agent_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that an agent has completed."""
        ...


class StandardWebSocketBridge:
    """SSOT WebSocket bridge providing standard interface for all adapter patterns.
    
    This class consolidates all WebSocket bridge adapter implementations into a
    unified interface that can work with any underlying WebSocket system:
    - AgentWebSocketBridge (legacy agent bridge)
    - WebSocketEventEmitter (new unified emitter)
    - UnifiedWebSocketManager (direct manager access)
    
    Key Features:
    - Automatic adapter pattern detection and delegation
    - All 5 critical WebSocket events guaranteed
    - Enhanced error handling and validation
    - User context isolation and security
    - Performance monitoring and metrics
    - Backward compatibility with all existing bridges
    
    Business Value:
    - Protects $500K+ ARR chat functionality through reliable events
    - Eliminates WebSocket bridge duplication and inconsistencies  
    - Provides single point of WebSocket event reliability
    - Simplifies maintenance and reduces bug surface area
    """
    
    def __init__(self, user_context: 'UserExecutionContext'):
        """Initialize the standard WebSocket bridge.
        
        Args:
            user_context: User execution context for event correlation and security
        """
        self.user_context = user_context
        self.bridge_id = f"std_bridge_{user_context.user_id}_{user_context.run_id}_{int(time.time()*1000)}"
        self.created_at = datetime.now(timezone.utc)
        
        # Bridge adapters (only one will be active)
        self._agent_bridge: Optional['AgentWebSocketBridge'] = None
        self._websocket_emitter: Optional['WebSocketEventEmitter'] = None
        self._websocket_manager: Optional['WebSocketManager'] = None
        
        # Active adapter type for metrics and debugging
        self._active_adapter_type: Optional[str] = None
        
        # Event delivery metrics
        self._metrics = {
            'events_sent': 0,
            'events_failed': 0,
            'agent_started_events': 0,
            'agent_thinking_events': 0,
            'tool_executing_events': 0,
            'tool_completed_events': 0,
            'agent_completed_events': 0,
            'total_execution_time_ms': 0,
            'adapter_switches': 0,
            'last_event_time': None
        }
        
        logger.info(f"[U+1F309] Created StandardWebSocketBridge {self.bridge_id} for user {user_context.user_id}")
    
    # ===================== ADAPTER CONFIGURATION METHODS =====================
    
    def set_agent_bridge(self, agent_bridge: 'AgentWebSocketBridge') -> None:
        """Configure with AgentWebSocketBridge (legacy agent bridge pattern).
        
        Args:
            agent_bridge: The AgentWebSocketBridge to use for event delivery
        """
        if self._has_active_adapter():
            self._metrics['adapter_switches'] += 1
            logger.warning(
                f" CYCLE:  Switching adapter types in {self.bridge_id}: "
                f"{self._active_adapter_type}  ->  AgentWebSocketBridge"
            )
        
        self._agent_bridge = agent_bridge
        self._websocket_emitter = None
        self._websocket_manager = None
        self._active_adapter_type = "AgentWebSocketBridge"
        
        logger.info(f"[U+1F50C] StandardWebSocketBridge configured with AgentWebSocketBridge for {self.user_context.get_correlation_id()}")
    
    def set_websocket_emitter(self, websocket_emitter: 'WebSocketEventEmitter') -> None:
        """Configure with WebSocketEventEmitter (new unified emitter pattern).
        
        Args:
            websocket_emitter: The WebSocketEventEmitter to use for event delivery
        """
        if self._has_active_adapter():
            self._metrics['adapter_switches'] += 1
            logger.warning(
                f" CYCLE:  Switching adapter types in {self.bridge_id}: "
                f"{self._active_adapter_type}  ->  WebSocketEventEmitter"
            )
        
        self._websocket_emitter = websocket_emitter
        self._agent_bridge = None
        self._websocket_manager = None
        self._active_adapter_type = "WebSocketEventEmitter"
        
        logger.info(f"[U+1F50C] StandardWebSocketBridge configured with WebSocketEventEmitter for {self.user_context.get_correlation_id()}")
    
    def set_websocket_manager(self, websocket_manager: 'WebSocketManager') -> None:
        """Configure with UnifiedWebSocketManager (direct manager access pattern).
        
        Args:
            websocket_manager: The UnifiedWebSocketManager to use for event delivery
        """
        if self._has_active_adapter():
            self._metrics['adapter_switches'] += 1
            logger.warning(
                f" CYCLE:  Switching adapter types in {self.bridge_id}: "
                f"{self._active_adapter_type}  ->  UnifiedWebSocketManager"
            )
        
        self._websocket_manager = websocket_manager
        self._agent_bridge = None
        self._websocket_emitter = None
        self._active_adapter_type = "UnifiedWebSocketManager"
        
        logger.info(f"[U+1F50C] StandardWebSocketBridge configured with UnifiedWebSocketManager for {self.user_context.get_correlation_id()}")
    
    def _has_active_adapter(self) -> bool:
        """Check if any adapter is currently configured."""
        return (
            self._agent_bridge is not None or
            self._websocket_emitter is not None or
            self._websocket_manager is not None
        )
    
    def get_active_adapter_type(self) -> Optional[str]:
        """Get the type of currently active adapter."""
        return self._active_adapter_type
    
    # ===================== STANDARD WEBSOCKET EVENT METHODS =====================
    
    async def notify_agent_started(
        self,
        run_id: str,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that an agent has started - CRITICAL EVENT #1.
        
        This event signals to users that their AI request is being processed.
        Essential for chat UX and user confidence in the system.
        
        Args:
            run_id: Execution run ID (must match user context)
            agent_name: Name of the agent that started
            context: Optional context data for the event
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        if not self._validate_run_id(run_id):
            return False
        
        start_time = time.time()
        
        try:
            success = False
            
            if self._agent_bridge:
                success = await self._agent_bridge.notify_agent_started(run_id, agent_name, context)
            elif self._websocket_emitter:
                success = await self._websocket_emitter.notify_agent_started(run_id, agent_name, context)
            elif self._websocket_manager:
                success = await self._send_via_manager("agent_started", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "context": context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.critical(
                    f" ALERT:  CRITICAL: No WebSocket adapter configured in {self.bridge_id} - "
                    f"agent_started event LOST for {agent_name}! User will not see AI working."
                )
                self._metrics['events_failed'] += 1
                return False
            
            # Update metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(success, execution_time_ms, 'agent_started')
            
            if success:
                logger.debug(f" PASS:  agent_started: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            else:
                logger.error(f" FAIL:  agent_started FAILED: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            
            return success
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(False, execution_time_ms, 'agent_started')
            
            logger.critical(
                f" ALERT:  CRITICAL: agent_started event failed for {agent_name} in {self.bridge_id}: {e}. "
                f"User will not see AI working!"
            )
            return False
    
    async def notify_agent_thinking(
        self,
        run_id: str,
        agent_name: str,
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None
    ) -> bool:
        """Notify that an agent is thinking - CRITICAL EVENT #2.
        
        This event provides real-time reasoning visibility to users.
        Essential for user engagement and trust in AI reasoning process.
        
        Args:
            run_id: Execution run ID (must match user context)
            agent_name: Name of the thinking agent
            reasoning: The agent's current reasoning/thought process
            step_number: Optional step number in the reasoning process
            progress_percentage: Optional progress percentage
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        if not self._validate_run_id(run_id):
            return False
        
        start_time = time.time()
        
        try:
            success = False
            
            if self._agent_bridge:
                success = await self._agent_bridge.notify_agent_thinking(
                    run_id, agent_name, reasoning, step_number, progress_percentage
                )
            elif self._websocket_emitter:
                success = await self._websocket_emitter.notify_agent_thinking(
                    run_id, agent_name, reasoning, step_number, progress_percentage
                )
            elif self._websocket_manager:
                success = await self._send_via_manager("agent_thinking", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "reasoning": reasoning,
                    "step_number": step_number,
                    "progress_percentage": progress_percentage,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.warning(
                    f" WARNING: [U+FE0F] No WebSocket adapter configured in {self.bridge_id} - "
                    f"agent_thinking event LOST for {agent_name}! User will not see real-time reasoning."
                )
                self._metrics['events_failed'] += 1
                return False
            
            # Update metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(success, execution_time_ms, 'agent_thinking')
            
            if success:
                logger.debug(f"[U+1F4AD] agent_thinking: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            else:
                logger.warning(f" WARNING: [U+FE0F] agent_thinking FAILED: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            
            return success
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(False, execution_time_ms, 'agent_thinking')
            
            logger.warning(
                f" WARNING: [U+FE0F] agent_thinking event failed for {agent_name} in {self.bridge_id}: {e}. "
                f"User will not see real-time reasoning."
            )
            return False
    
    async def notify_tool_executing(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify that a tool is executing - CRITICAL EVENT #3.
        
        This event provides tool usage transparency to users.
        Essential for user understanding of AI problem-solving process.
        
        Args:
            run_id: Execution run ID (must match user context)
            agent_name: Name of the agent executing the tool
            tool_name: Name of the tool being executed
            parameters: Optional tool parameters
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        if not self._validate_run_id(run_id):
            return False
        
        start_time = time.time()
        
        try:
            success = False
            
            if self._agent_bridge:
                success = await self._agent_bridge.notify_tool_executing(
                    run_id, agent_name, tool_name, parameters
                )
            elif self._websocket_emitter:
                success = await self._websocket_emitter.notify_tool_executing(
                    run_id, agent_name, tool_name, parameters
                )
            elif self._websocket_manager:
                success = await self._send_via_manager("tool_executing", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.error(
                    f" FAIL:  No WebSocket adapter configured in {self.bridge_id} - "
                    f"tool_executing event LOST for {tool_name}! User will not see tool usage transparency."
                )
                self._metrics['events_failed'] += 1
                return False
            
            # Update metrics
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(success, execution_time_ms, 'tool_executing')
            
            if success:
                logger.debug(f"[U+1F527] tool_executing: {tool_name} by {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            else:
                logger.error(f" FAIL:  tool_executing FAILED: {tool_name} by {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            
            return success
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(False, execution_time_ms, 'tool_executing')
            
            logger.error(
                f" FAIL:  tool_executing event failed for {tool_name} by {agent_name} in {self.bridge_id}: {e}. "
                f"User will not see tool usage transparency."
            )
            return False
    
    async def notify_tool_completed(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that a tool has completed - CRITICAL EVENT #4.
        
        This event shows users the results of tool execution.
        Essential for user understanding of AI problem-solving results.
        
        Args:
            run_id: Execution run ID (must match user context)
            agent_name: Name of the agent that executed the tool
            tool_name: Name of the tool that completed
            result: Optional tool execution result
            execution_time_ms: Optional execution time in milliseconds
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        if not self._validate_run_id(run_id):
            return False
        
        start_time = time.time()
        
        try:
            success = False
            
            if self._agent_bridge:
                success = await self._agent_bridge.notify_tool_completed(
                    run_id, agent_name, tool_name, result, execution_time_ms
                )
            elif self._websocket_emitter:
                success = await self._websocket_emitter.notify_tool_completed(
                    run_id, agent_name, tool_name, result, execution_time_ms
                )
            elif self._websocket_manager:
                success = await self._send_via_manager("tool_completed", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "tool_name": tool_name,
                    "result": result,
                    "execution_time_ms": execution_time_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.error(
                    f" FAIL:  No WebSocket adapter configured in {self.bridge_id} - "
                    f"tool_completed event LOST for {tool_name}! User will not see tool results."
                )
                self._metrics['events_failed'] += 1
                return False
            
            # Update metrics
            event_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(success, event_time_ms, 'tool_completed')
            
            if success:
                logger.debug(f" PASS:  tool_completed: {tool_name} by {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            else:
                logger.error(f" FAIL:  tool_completed FAILED: {tool_name} by {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            
            return success
            
        except Exception as e:
            event_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(False, event_time_ms, 'tool_completed')
            
            logger.error(
                f" FAIL:  tool_completed event failed for {tool_name} by {agent_name} in {self.bridge_id}: {e}. "
                f"User will not see tool results."
            )
            return False
    
    async def notify_agent_completed(
        self,
        run_id: str,
        agent_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None
    ) -> bool:
        """Notify that an agent has completed - CRITICAL EVENT #5.
        
        This event signals to users that their AI response is ready.
        Essential for chat UX and user awareness of completion.
        
        Args:
            run_id: Execution run ID (must match user context)
            agent_name: Name of the agent that completed
            result: Optional agent execution result
            execution_time_ms: Optional execution time in milliseconds
            
        Returns:
            bool: True if event was sent successfully, False otherwise
        """
        if not self._validate_run_id(run_id):
            return False
        
        start_time = time.time()
        
        try:
            success = False
            
            if self._agent_bridge:
                success = await self._agent_bridge.notify_agent_completed(
                    run_id, agent_name, result, execution_time_ms
                )
            elif self._websocket_emitter:
                success = await self._websocket_emitter.notify_agent_completed(
                    run_id, agent_name, result, execution_time_ms
                )
            elif self._websocket_manager:
                success = await self._send_via_manager("agent_completed", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "result": result,
                    "execution_time_ms": execution_time_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                logger.critical(
                    f" ALERT:  CRITICAL: No WebSocket adapter configured in {self.bridge_id} - "
                    f"agent_completed event LOST for {agent_name}! User will not know response is ready."
                )
                self._metrics['events_failed'] += 1
                return False
            
            # Update metrics
            event_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(success, event_time_ms, 'agent_completed')
            
            if success:
                logger.info(f" CELEBRATION:  agent_completed: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            else:
                logger.critical(f" ALERT:  agent_completed FAILED: {agent_name}  ->  user {self.user_context.user_id} via {self._active_adapter_type}")
            
            return success
            
        except Exception as e:
            event_time_ms = (time.time() - start_time) * 1000
            self._update_event_metrics(False, event_time_ms, 'agent_completed')
            
            logger.critical(
                f" ALERT:  CRITICAL: agent_completed event failed for {agent_name} in {self.bridge_id}: {e}. "
                f"User will not know response is ready!"
            )
            return False
    
    # ===================== ADDITIONAL EVENT METHODS =====================
    
    async def notify_agent_error(
        self,
        run_id: str,
        agent_name: str,
        error: str,
        error_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Notify of an agent error."""
        if not self._validate_run_id(run_id):
            return False
        
        try:
            if self._agent_bridge:
                return await self._agent_bridge.notify_agent_error(run_id, agent_name, error, error_context)
            elif self._websocket_emitter:
                return await self._websocket_emitter.notify_agent_error(run_id, agent_name, error, error_context)
            elif self._websocket_manager:
                return await self._send_via_manager("agent_error", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "error": error,
                    "error_context": error_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            return False
        except Exception as e:
            logger.error(f" FAIL:  Failed to send agent_error event: {e}")
            return False
    
    async def notify_progress_update(
        self,
        run_id: str,
        agent_name: str,
        progress: Dict[str, Any]
    ) -> bool:
        """Notify of a progress update."""
        if not self._validate_run_id(run_id):
            return False
        
        try:
            if self._agent_bridge:
                return await self._agent_bridge.notify_progress_update(run_id, agent_name, progress)
            elif self._websocket_emitter:
                return await self._websocket_emitter.notify_progress_update(run_id, agent_name, progress)
            elif self._websocket_manager:
                return await self._send_via_manager("progress_update", {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "progress": progress,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            return False
        except Exception as e:
            logger.debug(f"Failed to send progress_update event: {e}")
            return False
    
    async def notify_custom(
        self,
        run_id: str,
        agent_name: str,
        notification_type: str,
        data: Dict[str, Any]
    ) -> bool:
        """Send custom notification."""
        if not self._validate_run_id(run_id):
            return False
        
        try:
            if self._agent_bridge:
                return await self._agent_bridge.notify_custom(run_id, agent_name, notification_type, data)
            elif self._websocket_emitter:
                return await self._websocket_emitter.notify_custom(run_id, agent_name, notification_type, data)
            elif self._websocket_manager:
                return await self._send_via_manager(notification_type, {
                    "run_id": run_id,
                    "agent_name": agent_name,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            return False
        except Exception as e:
            logger.debug(f"Failed to send custom notification {notification_type}: {e}")
            return False
    
    # ===================== INTERNAL HELPER METHODS =====================
    
    def _validate_run_id(self, run_id: str) -> bool:
        """Validate that the run_id matches the user context for security."""
        if run_id != self.user_context.run_id:
            logger.warning(
                f" WARNING: [U+FE0F] SECURITY: Run ID mismatch in {self.bridge_id}. "
                f"Expected: {self.user_context.run_id}, Got: {run_id}. "
                f"Event rejected for security."
            )
            return False
        return True
    
    async def _send_via_manager(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """Send event via WebSocketManager (direct manager access)."""
        try:
            if hasattr(self._websocket_manager, 'send_event'):
                await self._websocket_manager.send_event(event_type, event_data)
                return True
            else:
                logger.error(f" FAIL:  WebSocketManager missing send_event method in {self.bridge_id}")
                return False
        except Exception as e:
            logger.error(f" FAIL:  Failed to send {event_type} via manager: {e}")
            return False
    
    def _update_event_metrics(self, success: bool, execution_time_ms: float, event_type: str) -> None:
        """Update event delivery metrics."""
        if success:
            self._metrics['events_sent'] += 1
        else:
            self._metrics['events_failed'] += 1
        
        self._metrics['total_execution_time_ms'] += execution_time_ms
        self._metrics['last_event_time'] = datetime.now(timezone.utc)
        
        # Track specific event types
        event_key = f"{event_type}_events"
        if event_key in self._metrics:
            self._metrics[event_key] += 1
    
    # ===================== METRICS AND DIAGNOSTICS =====================
    
    def get_bridge_metrics(self) -> Dict[str, Any]:
        """Get bridge metrics for monitoring and debugging."""
        uptime_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        total_events = self._metrics['events_sent'] + self._metrics['events_failed']
        success_rate = (self._metrics['events_sent'] / max(1, total_events))
        avg_execution_time = (self._metrics['total_execution_time_ms'] / max(1, total_events))
        
        return {
            **self._metrics,
            'bridge_id': self.bridge_id,
            'user_id': self.user_context.user_id,
            'run_id': self.user_context.run_id,
            'active_adapter_type': self._active_adapter_type,
            'has_active_adapter': self._has_active_adapter(),
            'uptime_seconds': uptime_seconds,
            'success_rate': success_rate,
            'avg_execution_time_ms': avg_execution_time,
            'created_at': self.created_at.isoformat()
        }
    
    def diagnose_bridge_health(self) -> Dict[str, Any]:
        """Diagnose bridge health for debugging."""
        health = {
            'status': 'healthy',
            'issues': [],
            'adapters': {
                'agent_bridge': self._agent_bridge is not None,
                'websocket_emitter': self._websocket_emitter is not None,
                'websocket_manager': self._websocket_manager is not None
            },
            'active_adapter': self._active_adapter_type,
            'metrics': self.get_bridge_metrics()
        }
        
        # Check for issues
        if not self._has_active_adapter():
            health['status'] = 'critical'
            health['issues'].append("No WebSocket adapter configured - all events will fail")
        
        if self._metrics['events_failed'] > 0:
            failure_rate = self._metrics['events_failed'] / max(1, self._metrics['events_sent'] + self._metrics['events_failed'])
            if failure_rate > 0.1:  # More than 10% failure rate
                health['status'] = 'degraded' if health['status'] == 'healthy' else health['status']
                health['issues'].append(f"High event failure rate: {failure_rate:.1%}")
        
        if self._metrics['adapter_switches'] > 5:
            health['status'] = 'degraded' if health['status'] == 'healthy' else health['status']
            health['issues'].append(f"Frequent adapter switches: {self._metrics['adapter_switches']}")
        
        return health


# ===================== FACTORY FUNCTIONS FOR WEBSOCKET BRIDGES =====================

def create_standard_websocket_bridge(user_context: 'UserExecutionContext') -> StandardWebSocketBridge:
    """Create a standard WebSocket bridge for the given user context.
    
    Args:
        user_context: User execution context for event correlation
        
    Returns:
        StandardWebSocketBridge: Configured bridge ready for adapter assignment
    """
    return StandardWebSocketBridge(user_context)


def create_agent_bridge_adapter(
    agent_bridge: 'AgentWebSocketBridge',
    user_context: 'UserExecutionContext'
) -> StandardWebSocketBridge:
    """Create standard bridge configured with AgentWebSocketBridge.
    
    Args:
        agent_bridge: The AgentWebSocketBridge to wrap
        user_context: User execution context
        
    Returns:
        StandardWebSocketBridge: Bridge configured with agent bridge adapter
    """
    bridge = StandardWebSocketBridge(user_context)
    bridge.set_agent_bridge(agent_bridge)
    return bridge


def create_emitter_bridge_adapter(
    websocket_emitter: 'WebSocketEventEmitter',
    user_context: 'UserExecutionContext'
) -> StandardWebSocketBridge:
    """Create standard bridge configured with WebSocketEventEmitter.
    
    Args:
        websocket_emitter: The WebSocketEventEmitter to wrap
        user_context: User execution context
        
    Returns:
        StandardWebSocketBridge: Bridge configured with emitter adapter
    """
    bridge = StandardWebSocketBridge(user_context)
    bridge.set_websocket_emitter(websocket_emitter)
    return bridge


def create_manager_bridge_adapter(
    websocket_manager: 'WebSocketManager',
    user_context: 'UserExecutionContext'
) -> StandardWebSocketBridge:
    """Create standard bridge configured with UnifiedWebSocketManager.
    
    Args:
        websocket_manager: The UnifiedWebSocketManager to wrap
        user_context: User execution context
        
    Returns:
        StandardWebSocketBridge: Bridge configured with manager adapter
    """
    bridge = StandardWebSocketBridge(user_context)
    bridge.set_websocket_manager(websocket_manager)
    return bridge


# ===================== BACKWARD COMPATIBILITY ADAPTERS =====================

class WebSocketBridgeAdapter(StandardWebSocketBridge):
    """DEPRECATED: Backward compatibility adapter for existing WebSocketBridgeAdapter usage.
    
    This class provides backward compatibility for code that expects the old
    WebSocketBridgeAdapter interface while redirecting to the new StandardWebSocketBridge.
    """
    
    def __init__(self, websocket_emitter: 'WebSocketEventEmitter', user_context: 'UserExecutionContext'):
        """Initialize backward compatibility adapter.
        
        Args:
            websocket_emitter: WebSocketEventEmitter to wrap
            user_context: User execution context
        """
        warnings.warn(
            "WebSocketBridgeAdapter is deprecated. "
            "Use StandardWebSocketBridge or create_emitter_bridge_adapter() for SSOT compliance.",
            DeprecationWarning,
            stacklevel=2
        )
        
        super().__init__(user_context)
        self.set_websocket_emitter(websocket_emitter)
        
        # Legacy compatibility attributes
        self.websocket_emitter = websocket_emitter
        self.user_context = user_context
        
        logger.warning(
            f" CYCLE:  DEPRECATED: WebSocketBridgeAdapter created for {user_context.get_correlation_id()}. "
            f"Use StandardWebSocketBridge for SSOT compliance."
        )


__all__ = [
    # Standard SSOT Interface
    'WebSocketBridgeProtocol',
    'StandardWebSocketBridge',
    
    # Factory Functions
    'create_standard_websocket_bridge',
    'create_agent_bridge_adapter',
    'create_emitter_bridge_adapter',
    'create_manager_bridge_adapter',
    
    # Backward Compatibility (DEPRECATED)
    'WebSocketBridgeAdapter',
]