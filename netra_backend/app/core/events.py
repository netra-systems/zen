"""
Event system for core application events and notifications.
Provides a simple event bus for decoupled component communication.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Base event class for all system events."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    source: Optional[str] = None


class EventBus:
    """
    Simple event bus for publishing and subscribing to events.
    Supports both synchronous and asynchronous event handlers.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._async_handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events of a specific type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler to event type: {event_type}")
    
    def subscribe_async(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Subscribe to events with an async handler."""
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
        logger.debug(f"Subscribed async handler to event type: {event_type}")
    
    async def publish(self, event_or_type, data=None) -> None:
        """Publish an event to all subscribers. Supports both Event objects and (type, data) format."""
        if isinstance(event_or_type, Event):
            event = event_or_type
        else:
            # Support legacy (type, data) format
            event = Event(
                type=event_or_type,
                data=data or {},
                timestamp=datetime.now(timezone.utc)
            )
        
        # Handle synchronous handlers first
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}")
        
        # Handle async handlers
        async_handlers = self._async_handlers.get(event.type, [])
        if async_handlers:
            tasks = []
            for handler in async_handlers:
                try:
                    tasks.append(asyncio.create_task(handler(event)))
                except Exception as e:
                    logger.error(f"Error creating task for async handler for {event.type}: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def publish_sync(self, event_or_type, data=None) -> None:
        """Publish an event to synchronous subscribers only. Supports both Event objects and (type, data) format."""
        if isinstance(event_or_type, Event):
            event = event_or_type
        else:
            # Support legacy (type, data) format
            event = Event(
                type=event_or_type,
                data=data or {},
                timestamp=datetime.now(timezone.utc)
            )
        
        # Handle synchronous handlers only
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}")
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Remove a handler from event subscriptions."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass
        
        if event_type in self._async_handlers:
            try:
                self._async_handlers[event_type].remove(handler)
            except ValueError:
                pass


# Global event bus instance
event_bus = EventBus()


def create_event(event_type: str, data: Dict[str, Any], source: Optional[str] = None) -> Event:
    """Helper function to create an event."""
    return Event(
        type=event_type,
        data=data,
        timestamp=datetime.now(timezone.utc),
        source=source
    )