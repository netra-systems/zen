"""Dead Letter Queue for handling failed messages"""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


class DeadLetterQueue:
    """Handles messages that failed processing"""
    
    def __init__(self, max_size: int = 1000):
        self.failed_messages: List[Dict[str, Any]] = []
        self.max_size = max_size
    
    async def add_failed_message(self, message: Dict[str, Any], error: str) -> None:
        """Add a failed message to the dead letter queue"""
        failed_msg = {
            **message,
            "error": error,
            "failed_at": datetime.now(UTC).isoformat(),
            "original_id": message.get("id")
        }
        
        self.failed_messages.append(failed_msg)
        
        # Keep queue size under limit
        if len(self.failed_messages) > self.max_size:
            self.failed_messages.pop(0)
    
    async def get_failed_messages(self) -> List[Dict[str, Any]]:
        """Get all failed messages"""
        return self.failed_messages.copy()
    
    async def retry_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Remove and return a failed message for retry"""
        for i, message in enumerate(self.failed_messages):
            if message.get("original_id") == message_id:
                return self.failed_messages.pop(i)
        return None
    
    async def clear_old_messages(self, hours: int = 24) -> int:
        """Clear messages older than specified hours"""
        cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
        initial_count = len(self.failed_messages)
        
        self.failed_messages = [
            msg for msg in self.failed_messages
            if datetime.fromisoformat(msg["failed_at"]).timestamp() > cutoff
        ]
        
        return initial_count - len(self.failed_messages)
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """Get statistics about failed messages"""
        if not self.failed_messages:
            return {"total_failed": 0, "errors": {}}
        
        error_counts = {}
        for message in self.failed_messages:
            error = message.get("error", "unknown")
            error_counts[error] = error_counts.get(error, 0) + 1
        
        return {
            "total_failed": len(self.failed_messages),
            "errors": error_counts,
            "oldest_failure": self.failed_messages[0]["failed_at"] if self.failed_messages else None,
            "newest_failure": self.failed_messages[-1]["failed_at"] if self.failed_messages else None
        }