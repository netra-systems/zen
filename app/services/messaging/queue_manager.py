"""Queue Manager for orchestrating message queues"""

from typing import Dict, Any, Optional, List
import asyncio
from .message_queue import MessageQueue


class QueueManager:
    """Manages multiple message queues and routing"""
    
    def __init__(self):
        self.queues: Dict[str, MessageQueue] = {}
        self._default_queue = MessageQueue()
        self.queues["default"] = self._default_queue
    
    def create_queue(self, name: str) -> MessageQueue:
        """Create a new message queue"""
        queue = MessageQueue()
        self.queues[name] = queue
        return queue
    
    def get_queue(self, name: str) -> Optional[MessageQueue]:
        """Get queue by name"""
        return self.queues.get(name)
    
    async def route_message(self, queue_name: str, message: Dict[str, Any]) -> bool:
        """Route message to specific queue"""
        queue = self.get_queue(queue_name)
        if queue:
            return await queue.enqueue(message)
        return False
    
    async def process_all_queues(self) -> None:
        """Process messages in all queues"""
        tasks = []
        for queue in self.queues.values():
            tasks.append(queue.process_messages())
        await asyncio.gather(*tasks)
    
    def get_queue_stats(self) -> Dict[str, int]:
        """Get statistics for all queues"""
        return {name: queue.get_queue_size() for name, queue in self.queues.items()}
    
    async def shutdown(self) -> None:
        """Shutdown all queues"""
        await self.process_all_queues()
        self.queues.clear()