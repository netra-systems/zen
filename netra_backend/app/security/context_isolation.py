"""Context Isolation Security Module

Business Value Justification (BVJ):
- Segment: Enterprise (security and compliance)
- Business Goal: Ensure strict tenant/context isolation
- Value Impact: Critical for multi-tenant security compliance
- Strategic Impact: Essential for enterprise security requirements

Provides context isolation management for agents and services.
"""

import asyncio
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class IsolationContext:
    """Represents an isolated execution context."""
    context_id: str
    tenant_id: str
    user_id: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate context after initialization."""
        if not self.context_id or not self.tenant_id:
            raise NetraException("Context ID and Tenant ID are required")


@dataclass
class IsolationViolation:
    """Represents a context isolation violation."""
    violation_id: str
    context_id: str
    violation_type: str
    description: str
    severity: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextIsolationManager:
    """Manages context isolation for multi-tenant security."""
    
    def __init__(self):
        """Initialize the context isolation manager."""
        self._active_contexts: Dict[str, IsolationContext] = {}
        self._context_boundaries: Dict[str, Set[str]] = {}
        self._violation_log: List[IsolationViolation] = []
        self._lock = asyncio.Lock()
    
    async def create_context(self, tenant_id: str, user_id: Optional[str] = None, 
                           permissions: Optional[Set[str]] = None) -> IsolationContext:
        """Create a new isolated context."""
        async with self._lock:
            context_id = self._generate_context_id()
            context = IsolationContext(
                context_id=context_id,
                tenant_id=tenant_id,
                user_id=user_id,
                permissions=permissions or set()
            )
            self._active_contexts[context_id] = context
            self._context_boundaries[context_id] = {tenant_id}
            logger.info(f"Created isolation context {context_id} for tenant {tenant_id}")
            return context
    
    async def destroy_context(self, context_id: str) -> None:
        """Destroy an isolated context."""
        async with self._lock:
            if context_id in self._active_contexts:
                del self._active_contexts[context_id]
                self._context_boundaries.pop(context_id, None)
                logger.info(f"Destroyed isolation context {context_id}")
    
    async def validate_access(self, context_id: str, resource_tenant_id: str) -> bool:
        """Validate that a context can access a resource."""
        async with self._lock:
            context = self._active_contexts.get(context_id)
            if not context:
                await self._log_violation(context_id, "INVALID_CONTEXT", 
                                        f"Context {context_id} not found", "HIGH")
                return False
            
            if resource_tenant_id not in self._context_boundaries.get(context_id, set()):
                await self._log_violation(context_id, "CROSS_TENANT_ACCESS",
                                        f"Context {context_id} attempted access to tenant {resource_tenant_id}", 
                                        "CRITICAL")
                return False
            
            return True
    
    async def get_context(self, context_id: str) -> Optional[IsolationContext]:
        """Get an active context by ID."""
        async with self._lock:
            return self._active_contexts.get(context_id)
    
    async def get_violations(self, limit: int = 100) -> List[IsolationViolation]:
        """Get recent isolation violations."""
        async with self._lock:
            return self._violation_log[-limit:]
    
    @asynccontextmanager
    async def isolated_execution(self, tenant_id: str, user_id: Optional[str] = None):
        """Context manager for isolated execution."""
        context = await self.create_context(tenant_id, user_id)
        try:
            yield context
        finally:
            await self.destroy_context(context.context_id)
    
    def _generate_context_id(self) -> str:
        """Generate a unique context ID."""
        return f"ctx_{uuid.uuid4().hex[:16]}"
    
    async def _log_violation(self, context_id: str, violation_type: str, 
                           description: str, severity: str) -> None:
        """Log an isolation violation."""
        violation = IsolationViolation(
            violation_id=f"viol_{uuid.uuid4().hex[:16]}",
            context_id=context_id,
            violation_type=violation_type,
            description=description,
            severity=severity
        )
        self._violation_log.append(violation)
        logger.error(f"Context isolation violation: {description}")
    
    async def get_active_contexts_count(self) -> int:
        """Get count of active contexts."""
        async with self._lock:
            return len(self._active_contexts)
    
    async def cleanup_expired_contexts(self, max_age_hours: int = 24) -> int:
        """Clean up expired contexts."""
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            expired_contexts = [
                ctx_id for ctx_id, ctx in self._active_contexts.items()
                if (current_time - ctx.created_at).total_seconds() > max_age_hours * 3600
            ]
            
            for ctx_id in expired_contexts:
                del self._active_contexts[ctx_id]
                self._context_boundaries.pop(ctx_id, None)
            
            logger.info(f"Cleaned up {len(expired_contexts)} expired contexts")
            return len(expired_contexts)


# Global instance for application use
context_isolation_manager = ContextIsolationManager()