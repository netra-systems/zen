"""
Event system for core application events and notifications.
Provides a simple event bus for decoupled component communication.
"""

from typing import Dict, List, Callable, Any, Optional
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

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
    
    def publish(self, event: Event) -> None:
        """Publish an event to all subscribers."""
        # Handle synchronous handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event.type}: {e}")
    
    async def publish_async(self, event: Event) -> None:
        """Publish an event to all async subscribers."""
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
        timestamp=datetime.utcnow(),
        source=source
    )