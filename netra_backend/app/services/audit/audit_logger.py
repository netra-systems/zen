"""
Generic Audit Logger

Provides a generic audit logging interface for integration testing.
Wraps the CorpusAuditLogger for actual implementation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import asyncio

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AuditLogger:
    """Generic audit logger for integration testing purposes."""
    
    def __init__(self):
        self._initialized = False
        self._events = []
    
    async def initialize(self) -> None:
        """Initialize the audit logger."""
        self._initialized = True
        logger.info("AuditLogger initialized")
    
    async def log_event(
        self, 
        event_type: str, 
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an audit event."""
        if not self._initialized:
            await self.initialize()
        
        event = {
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "details": details or {}
        }
        
        self._events.append(event)
        logger.info(f"Logged audit event: {event_type} for tenant: {tenant_id}")
    
    async def get_events(self, tenant_id: Optional[str] = None) -> list:
        """Get logged events, optionally filtered by tenant."""
        if tenant_id:
            return [e for e in self._events if e.get("tenant_id") == tenant_id]
        return self._events.copy()
    
    async def clear_events(self) -> None:
        """Clear all logged events."""
        self._events.clear()
        logger.info("Cleared all audit events")
    
    async def shutdown(self) -> None:
        """Shutdown the audit logger."""
        self._initialized = False
        self._events.clear()
        logger.info("AuditLogger shutdown")