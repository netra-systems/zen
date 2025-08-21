"""Message Queue implementation for messaging service"""

from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime, UTC


class MessageQueue:
    """Message queue for handling async message processing"""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self._handlers: Dict[str, Any] = {}
    
    async def enqueue(self, message: Dict[str, Any]) -> bool:
        """Add message to queue"""
        self.messages.append({
            **message,
            "id": str(len(self.messages)),
            "timestamp": datetime.now(UTC).isoformat()
        })
        return True
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Remove and return next message from queue"""
        return self.messages.pop(0) if self.messages else None
    
    async def process_messages(self) -> None:
        """Process all queued messages"""
        while self.messages:
            message = await self.dequeue()
            if message:
                await self._process_message(message)
    
    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message"""
        message_type = message.get("type", "default")
        handler = self._handlers.get(message_type)
        if handler:
            await handler(message)
    
    def register_handler(self, message_type: str, handler) -> None:
        """Register message handler"""
        self._handlers[message_type] = handler
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return len(self.messages)