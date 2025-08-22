"""Message Queue Service module"""

import asyncio
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class MessageQueueService:
    """Service for managing message queues"""
    
    def __init__(self):
        self.queues: Dict[str, List[Dict[str, Any]]] = {}
        self.handlers: Dict[str, Any] = {}
        self.is_running = False
    
    async def start(self) -> None:
        """Start the message queue service"""
        self.is_running = True
    
    async def stop(self) -> None:
        """Stop the message queue service"""
        self.is_running = False
    
    async def publish(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Publish message to queue"""
        if queue_name not in self.queues:
            self.queues[queue_name] = []
        
        enriched_message = {
            **message,
            "id": f"{queue_name}_{len(self.queues[queue_name])}",
            "timestamp": datetime.now(UTC).isoformat(),
            "queue": queue_name
        }
        
        self.queues[queue_name].append(enriched_message)
        return True
    
    async def consume(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Consume message from queue"""
        if queue_name in self.queues and self.queues[queue_name]:
            return self.queues[queue_name].pop(0)
        return None
    
    async def subscribe(self, queue_name: str, handler) -> None:
        """Subscribe handler to queue"""
        self.handlers[queue_name] = handler
    
    async def process_queue(self, queue_name: str) -> None:
        """Process all messages in a queue"""
        while queue_name in self.queues and self.queues[queue_name]:
            message = await self.consume(queue_name)
            if message and queue_name in self.handlers:
                try:
                    await self.handlers[queue_name](message)
                except Exception as e:
                    # Simple error handling - in real implementation would use dead letter queue
                    pass
    
    def get_queue_size(self, queue_name: str) -> int:
        """Get size of specific queue"""
        return len(self.queues.get(queue_name, []))
    
    def list_queues(self) -> List[str]:
        """List all queue names"""
        return list(self.queues.keys())
    
    async def purge_queue(self, queue_name: str) -> int:
        """Clear all messages from queue"""
        if queue_name in self.queues:
            count = len(self.queues[queue_name])
            self.queues[queue_name].clear()
            return count
        return 0