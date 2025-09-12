"""Tool Event Bus - Centralized event notification system for tool execution.

This module provides a unified event bus system for tool execution events,
separating event concerns from tool dispatch and execution logic.

Key Features:
- Centralized event routing and notification
- Support for multiple event types (tool, agent, progress, custom)
- Event filtering and subscription patterns
- Reliable delivery with fallback mechanisms
- Comprehensive logging and error handling
- Event history and replay capabilities
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

if TYPE_CHECKING:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter as WebSocketEventEmitter

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EventType(Enum):
    """Enumeration of event types."""
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    TOOL_PROGRESS = "tool_progress"
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    PROGRESS_UPDATE = "progress_update"
    CUSTOM = "custom"


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class ToolEvent:
    """Tool event data structure."""
    event_type: EventType
    event_id: str
    timestamp: datetime
    run_id: str
    agent_name: str
    priority: EventPriority = EventPriority.NORMAL
    
    # Event-specific data
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[float] = None
    progress_percentage: Optional[float] = None
    reasoning: Optional[str] = None
    step_number: Optional[int] = None
    custom_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'run_id': self.run_id,
            'agent_name': self.agent_name,
            'priority': self.priority.value,
            'tool_name': self.tool_name,
            'parameters': self.parameters,
            'result': self.result,
            'error': self.error,
            'execution_time_ms': self.execution_time_ms,
            'progress_percentage': self.progress_percentage,
            'reasoning': self.reasoning,
            'step_number': self.step_number,
            'custom_data': self.custom_data,
            'user_id': self.user_id,
            'thread_id': self.thread_id,
            'correlation_id': self.correlation_id,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolEvent':
        """Create event from dictionary."""
        return cls(
            event_type=EventType(data['event_type']),
            event_id=data['event_id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            run_id=data['run_id'],
            agent_name=data['agent_name'],
            priority=EventPriority(data.get('priority', EventPriority.NORMAL.value)),
            tool_name=data.get('tool_name'),
            parameters=data.get('parameters'),
            result=data.get('result'),
            error=data.get('error'),
            execution_time_ms=data.get('execution_time_ms'),
            progress_percentage=data.get('progress_percentage'),
            reasoning=data.get('reasoning'),
            step_number=data.get('step_number'),
            custom_data=data.get('custom_data'),
            user_id=data.get('user_id'),
            thread_id=data.get('thread_id'),
            correlation_id=data.get('correlation_id'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )


class EventSubscription:
    """Event subscription configuration."""
    
    def __init__(
        self,
        subscription_id: str,
        event_types: Set[EventType],
        handler: Callable[[ToolEvent], None],
        filter_func: Optional[Callable[[ToolEvent], bool]] = None,
        priority_threshold: EventPriority = EventPriority.LOW
    ):
        self.subscription_id = subscription_id
        self.event_types = event_types
        self.handler = handler
        self.filter_func = filter_func
        self.priority_threshold = priority_threshold
        self.created_at = datetime.now(timezone.utc)
        self.events_processed = 0
        self.last_event_time = None
        self.active = True
    
    def matches(self, event: ToolEvent) -> bool:
        """Check if event matches subscription criteria."""
        if not self.active:
            return False
        
        # Check event type
        if event.event_type not in self.event_types:
            return False
        
        # Check priority threshold
        if event.priority.value < self.priority_threshold.value:
            return False
        
        # Apply custom filter
        if self.filter_func and not self.filter_func(event):
            return False
        
        return True
    
    async def process_event(self, event: ToolEvent) -> bool:
        """Process event through subscription handler."""
        try:
            if asyncio.iscoroutinefunction(self.handler):
                await self.handler(event)
            else:
                self.handler(event)
            
            self.events_processed += 1
            self.last_event_time = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.error(f"Event handler error in subscription {self.subscription_id}: {e}")
            return False


class ToolEventBus:
    """Centralized event bus for tool execution events.
    
    This event bus provides:
    - Centralized event routing and delivery
    - Multiple delivery mechanisms (WebSocket, callbacks, logging)
    - Event filtering and subscription patterns
    - Reliable delivery with retry logic
    - Event history and replay capabilities
    - Performance monitoring and metrics
    """
    
    def __init__(self, bus_id: Optional[str] = None):
        """Initialize the tool event bus.
        
        Args:
            bus_id: Optional identifier for this bus instance
        """
        self.bus_id = bus_id or f"eventbus_{int(time.time() * 1000)}"
        self.created_at = datetime.now(timezone.utc)
        
        # Event routing
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._websocket_bridges: List['AgentWebSocketBridge'] = []
        self._websocket_emitters: List['WebSocketEventEmitter'] = []
        self._event_history: List[ToolEvent] = []
        self._failed_events: List[ToolEvent] = []
        
        # Configuration
        self.max_history_size = 1000
        self.max_failed_events = 100
        self.enable_history = True
        self.retry_failed_events = True
        
        # Metrics
        self._metrics = {
            'events_published': 0,
            'events_delivered': 0,
            'events_failed': 0,
            'subscriptions_active': 0,
            'websocket_deliveries': 0,
            'callback_deliveries': 0,
            'retry_attempts': 0,
            'last_event_time': None
        }
        
        # Background tasks
        self._retry_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f" PASS:  Created ToolEventBus {self.bus_id}")
    
    # ===================== LIFECYCLE MANAGEMENT =====================
    
    async def start(self) -> None:
        """Start the event bus background tasks."""
        if self._running:
            return
        
        self._running = True
        
        # Start background tasks
        if self.retry_failed_events:
            self._retry_task = asyncio.create_task(self._retry_failed_events_loop())
        
        self._cleanup_task = asyncio.create_task(self._cleanup_history_loop())
        
        logger.info(f"[U+1F680] Started ToolEventBus {self.bus_id}")
    
    async def stop(self) -> None:
        """Stop the event bus and cleanup resources."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel background tasks
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear subscriptions and emitters
        self._subscriptions.clear()
        self._websocket_bridges.clear()
        self._websocket_emitters.clear()
        
        logger.info(f"[U+1F6D1] Stopped ToolEventBus {self.bus_id}")
    
    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager for automatic lifecycle management."""
        try:
            await self.start()
            yield self
        finally:
            await self.stop()
    
    # ===================== EVENT PUBLISHING =====================
    
    async def publish_tool_executing(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish tool executing event."""
        event = ToolEvent(
            event_type=EventType.TOOL_EXECUTING,
            event_id=f"tool_exec_{run_id}_{tool_name}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            parameters=parameters,
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_tool_completed(
        self,
        run_id: str,
        agent_name: str,
        tool_name: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish tool completed event."""
        event = ToolEvent(
            event_type=EventType.TOOL_COMPLETED,
            event_id=f"tool_comp_{run_id}_{tool_name}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            result=result,
            execution_time_ms=execution_time_ms,
            error=error,
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH if error else EventPriority.NORMAL
        )
        
        return await self.publish_event(event)
    
    async def publish_agent_started(
        self,
        run_id: str,
        agent_name: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish agent started event."""
        event = ToolEvent(
            event_type=EventType.AGENT_STARTED,
            event_id=f"agent_start_{run_id}_{agent_name}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            custom_data=context,
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id,
            priority=EventPriority.HIGH
        )
        
        return await self.publish_event(event)
    
    async def publish_agent_thinking(
        self,
        run_id: str,
        agent_name: str,
        reasoning: str,
        step_number: Optional[int] = None,
        progress_percentage: Optional[float] = None,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish agent thinking event."""
        event = ToolEvent(
            event_type=EventType.AGENT_THINKING,
            event_id=f"agent_think_{run_id}_{agent_name}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            reasoning=reasoning,
            step_number=step_number,
            progress_percentage=progress_percentage,
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_progress_update(
        self,
        run_id: str,
        agent_name: str,
        progress: Dict[str, Any],
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish progress update event."""
        event = ToolEvent(
            event_type=EventType.PROGRESS_UPDATE,
            event_id=f"progress_{run_id}_{agent_name}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            custom_data=progress,
            progress_percentage=progress.get('percentage'),
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_custom_event(
        self,
        run_id: str,
        agent_name: str,
        notification_type: str,
        data: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """Publish custom event."""
        event = ToolEvent(
            event_type=EventType.CUSTOM,
            event_id=f"custom_{run_id}_{notification_type}_{int(time.time() * 1000)}",
            timestamp=datetime.now(timezone.utc),
            run_id=run_id,
            agent_name=agent_name,
            custom_data={
                'notification_type': notification_type,
                **data
            },
            priority=priority,
            user_id=user_id,
            thread_id=thread_id,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event)
    
    async def publish_event(self, event: ToolEvent) -> bool:
        """Publish event to all subscribed handlers and delivery mechanisms."""
        if not self._running:
            logger.warning(f"Event bus {self.bus_id} not running - event {event.event_id} dropped")
            return False
        
        self._metrics['events_published'] += 1
        self._metrics['last_event_time'] = datetime.now(timezone.utc)
        
        # Add to history if enabled
        if self.enable_history:
            self._event_history.append(event)
            if len(self._event_history) > self.max_history_size:
                self._event_history.pop(0)
        
        success_count = 0
        total_deliveries = 0
        
        try:
            # Deliver to subscriptions
            for subscription in self._subscriptions.values():
                if subscription.matches(event):
                    total_deliveries += 1
                    if await subscription.process_event(event):
                        success_count += 1
                        self._metrics['callback_deliveries'] += 1
            
            # Deliver to WebSocket bridges
            for bridge in self._websocket_bridges:
                total_deliveries += 1
                if await self._deliver_to_websocket_bridge(event, bridge):
                    success_count += 1
                    self._metrics['websocket_deliveries'] += 1
            
            # Deliver to WebSocket emitters
            for emitter in self._websocket_emitters:
                total_deliveries += 1
                if await self._deliver_to_websocket_emitter(event, emitter):
                    success_count += 1
                    self._metrics['websocket_deliveries'] += 1
            
            # Update metrics
            if success_count == total_deliveries:
                self._metrics['events_delivered'] += 1
                logger.debug(f" PASS:  Event {event.event_id} delivered to {success_count}/{total_deliveries} handlers")
                return True
            else:
                self._metrics['events_failed'] += 1
                logger.warning(f" WARNING: [U+FE0F] Event {event.event_id} partially delivered: {success_count}/{total_deliveries}")
                
                # Add to failed events for retry
                if event.retry_count < event.max_retries:
                    event.retry_count += 1
                    self._failed_events.append(event)
                    if len(self._failed_events) > self.max_failed_events:
                        self._failed_events.pop(0)
                
                return False
            
        except Exception as e:
            self._metrics['events_failed'] += 1
            logger.error(f" ALERT:  Event publication failed for {event.event_id}: {e}")
            return False
    
    # ===================== DELIVERY MECHANISMS =====================
    
    async def _deliver_to_websocket_bridge(self, event: ToolEvent, bridge: 'AgentWebSocketBridge') -> bool:
        """Deliver event to WebSocket bridge."""
        try:
            if event.event_type == EventType.TOOL_EXECUTING:
                return await bridge.notify_tool_executing(
                    event.run_id, event.agent_name, event.tool_name, event.parameters
                )
            elif event.event_type == EventType.TOOL_COMPLETED:
                return await bridge.notify_tool_completed(
                    event.run_id, event.agent_name, event.tool_name, 
                    event.result, event.execution_time_ms
                )
            elif event.event_type == EventType.AGENT_STARTED:
                return await bridge.notify_agent_started(
                    event.run_id, event.agent_name, event.custom_data
                )
            elif event.event_type == EventType.AGENT_THINKING:
                return await bridge.notify_agent_thinking(
                    event.run_id, event.agent_name, event.reasoning,
                    event.step_number, event.progress_percentage
                )
            elif event.event_type == EventType.AGENT_COMPLETED:
                return await bridge.notify_agent_completed(
                    event.run_id, event.agent_name, event.result, event.execution_time_ms
                )
            elif event.event_type == EventType.AGENT_ERROR:
                return await bridge.notify_agent_error(
                    event.run_id, event.agent_name, event.error, event.custom_data
                )
            elif event.event_type == EventType.PROGRESS_UPDATE:
                return await bridge.notify_progress_update(
                    event.run_id, event.agent_name, event.custom_data or {}
                )
            elif event.event_type == EventType.CUSTOM:
                notification_type = event.custom_data.get('notification_type', 'custom')
                data = {k: v for k, v in event.custom_data.items() if k != 'notification_type'}
                return await bridge.notify_custom(
                    event.run_id, event.agent_name, notification_type, data
                )
            
            return False
            
        except Exception as e:
            logger.error(f"WebSocket bridge delivery error: {e}")
            return False
    
    async def _deliver_to_websocket_emitter(self, event: ToolEvent, emitter: 'WebSocketEventEmitter') -> bool:
        """Deliver event to WebSocket emitter."""
        try:
            if event.event_type == EventType.TOOL_EXECUTING:
                return await emitter.notify_tool_executing(
                    event.run_id, event.agent_name, event.tool_name, event.parameters
                )
            elif event.event_type == EventType.TOOL_COMPLETED:
                return await emitter.notify_tool_completed(
                    event.run_id, event.agent_name, event.tool_name, 
                    event.result, event.execution_time_ms
                )
            elif event.event_type == EventType.AGENT_STARTED:
                return await emitter.notify_agent_started(
                    event.run_id, event.agent_name, event.custom_data
                )
            elif event.event_type == EventType.AGENT_THINKING:
                return await emitter.notify_agent_thinking(
                    event.run_id, event.agent_name, event.reasoning,
                    event.step_number, event.progress_percentage
                )
            elif event.event_type == EventType.AGENT_COMPLETED:
                return await emitter.notify_agent_completed(
                    event.run_id, event.agent_name, event.result, event.execution_time_ms
                )
            elif event.event_type == EventType.AGENT_ERROR:
                return await emitter.notify_agent_error(
                    event.run_id, event.agent_name, event.error, event.custom_data
                )
            elif event.event_type == EventType.PROGRESS_UPDATE:
                return await emitter.notify_progress_update(
                    event.run_id, event.agent_name, event.custom_data or {}
                )
            elif event.event_type == EventType.CUSTOM:
                notification_type = event.custom_data.get('notification_type', 'custom')
                data = {k: v for k, v in event.custom_data.items() if k != 'notification_type'}
                return await emitter.notify_custom(
                    event.run_id, event.agent_name, notification_type, data
                )
            
            return False
            
        except Exception as e:
            logger.error(f"WebSocket emitter delivery error: {e}")
            return False
    
    # ===================== SUBSCRIPTION MANAGEMENT =====================
    
    def subscribe(
        self,
        subscription_id: str,
        event_types: Set[EventType],
        handler: Callable[[ToolEvent], None],
        filter_func: Optional[Callable[[ToolEvent], bool]] = None,
        priority_threshold: EventPriority = EventPriority.LOW
    ) -> bool:
        """Subscribe to events with handler."""
        if subscription_id in self._subscriptions:
            logger.warning(f"Subscription {subscription_id} already exists")
            return False
        
        subscription = EventSubscription(
            subscription_id, event_types, handler, filter_func, priority_threshold
        )
        
        self._subscriptions[subscription_id] = subscription
        self._metrics['subscriptions_active'] += 1
        
        logger.info(f" PASS:  Added subscription {subscription_id} for events: {[e.value for e in event_types]}")
        return True
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription."""
        if subscription_id not in self._subscriptions:
            return False
        
        del self._subscriptions[subscription_id]
        self._metrics['subscriptions_active'] -= 1
        
        logger.info(f"[U+1F5D1][U+FE0F] Removed subscription {subscription_id}")
        return True
    
    def add_websocket_bridge(self, bridge: 'AgentWebSocketBridge') -> None:
        """Add WebSocket bridge for event delivery."""
        if bridge not in self._websocket_bridges:
            self._websocket_bridges.append(bridge)
            logger.debug(f"Added WebSocket bridge to event bus {self.bus_id}")
    
    def remove_websocket_bridge(self, bridge: 'AgentWebSocketBridge') -> bool:
        """Remove WebSocket bridge."""
        try:
            self._websocket_bridges.remove(bridge)
            logger.debug(f"Removed WebSocket bridge from event bus {self.bus_id}")
            return True
        except ValueError:
            return False
    
    def add_websocket_emitter(self, emitter: 'WebSocketEventEmitter') -> None:
        """Add WebSocket emitter for event delivery."""
        if emitter not in self._websocket_emitters:
            self._websocket_emitters.append(emitter)
            logger.debug(f"Added WebSocket emitter to event bus {self.bus_id}")
    
    def remove_websocket_emitter(self, emitter: 'WebSocketEventEmitter') -> bool:
        """Remove WebSocket emitter."""
        try:
            self._websocket_emitters.remove(emitter)
            logger.debug(f"Removed WebSocket emitter from event bus {self.bus_id}")
            return True
        except ValueError:
            return False
    
    # ===================== BACKGROUND TASKS =====================
    
    async def _retry_failed_events_loop(self) -> None:
        """Background task to retry failed events."""
        while self._running:
            try:
                if self._failed_events:
                    events_to_retry = self._failed_events.copy()
                    self._failed_events.clear()
                    
                    for event in events_to_retry:
                        self._metrics['retry_attempts'] += 1
                        logger.debug(f"Retrying event {event.event_id} (attempt {event.retry_count})")
                        
                        if not await self.publish_event(event):
                            logger.warning(f"Event {event.event_id} retry failed")
                
                await asyncio.sleep(5)  # Retry interval
                
            except Exception as e:
                logger.error(f"Error in retry loop: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_history_loop(self) -> None:
        """Background task to cleanup old history."""
        while self._running:
            try:
                # Clean up old events from history
                if len(self._event_history) > self.max_history_size:
                    excess_count = len(self._event_history) - self.max_history_size
                    self._event_history = self._event_history[excess_count:]
                    logger.debug(f"Cleaned up {excess_count} old events from history")
                
                # Clean up very old failed events
                cutoff_time = datetime.now(timezone.utc).timestamp() - 3600  # 1 hour ago
                old_failed_events = [
                    event for event in self._failed_events
                    if event.timestamp.timestamp() < cutoff_time
                ]
                
                for event in old_failed_events:
                    self._failed_events.remove(event)
                
                if old_failed_events:
                    logger.debug(f"Cleaned up {len(old_failed_events)} old failed events")
                
                await asyncio.sleep(300)  # Cleanup interval (5 minutes)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)
    
    # ===================== METRICS AND MONITORING =====================
    
    def get_event_bus_metrics(self) -> Dict[str, Any]:
        """Get comprehensive event bus metrics."""
        uptime_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        
        return {
            **self._metrics,
            'bus_id': self.bus_id,
            'uptime_seconds': uptime_seconds,
            'subscriptions_count': len(self._subscriptions),
            'websocket_bridges_count': len(self._websocket_bridges),
            'websocket_emitters_count': len(self._websocket_emitters),
            'history_size': len(self._event_history),
            'failed_events_pending': len(self._failed_events),
            'is_running': self._running,
            'created_at': self.created_at.isoformat(),
            'delivery_success_rate': (
                self._metrics['events_delivered'] / 
                max(1, self._metrics['events_published'])
            )
        }
    
    def get_event_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get event history."""
        events = self._event_history[-limit:] if limit else self._event_history
        return [event.to_dict() for event in events]
    
    def get_failed_events(self) -> List[Dict[str, Any]]:
        """Get failed events pending retry."""
        return [event.to_dict() for event in self._failed_events]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
        logger.info(f"Cleared event history for bus {self.bus_id}")
    
    def clear_failed_events(self) -> None:
        """Clear failed events queue."""
        self._failed_events.clear()
        logger.info(f"Cleared failed events for bus {self.bus_id}")


# ===================== GLOBAL EVENT BUS INSTANCE =====================

_global_event_bus: Optional[ToolEventBus] = None


async def get_global_event_bus() -> ToolEventBus:
    """Get or create global event bus instance."""
    global _global_event_bus
    
    if _global_event_bus is None:
        _global_event_bus = ToolEventBus("global")
        await _global_event_bus.start()
        logger.info("Created and started global ToolEventBus")
    
    return _global_event_bus


def create_request_scoped_event_bus(bus_id: Optional[str] = None) -> ToolEventBus:
    """Create new request-scoped event bus."""
    return ToolEventBus(bus_id)


# Export all public interfaces
__all__ = [
    'ToolEventBus',
    'ToolEvent',
    'EventType',
    'EventPriority',
    'EventSubscription',
    'get_global_event_bus',
    'create_request_scoped_event_bus'
]