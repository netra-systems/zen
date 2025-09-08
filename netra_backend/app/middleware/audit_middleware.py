"""
Audit Middleware for comprehensive request/response logging.

Handles audit logging functionality including:
- Request/response logging with sensitive data masking
- Security event tracking
- Audit trail generation
- Performance metrics collection

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (Compliance and security requirements)
- Business Goal: SOC2/ISO27001 compliance enabling enterprise deals
- Value Impact: Prevents security breaches, enables audit compliance
- Strategic Impact: Foundation for enterprise security requirements
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.auth_types import RequestContext

logger = central_logger.get_logger(__name__)


class AuditMiddleware:
    """Audit middleware for request/response logging and security tracking."""
    
    def __init__(
        self,
        log_requests: bool = True,
        log_responses: bool = True,
        sensitive_fields: List[str] = None,
        max_body_size: int = 10240  # 10KB
    ):
        """Initialize audit middleware.
        
        Args:
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses  
            sensitive_fields: List of field names to mask in logs
            max_body_size: Maximum body size to log (bytes)
        """
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.sensitive_fields = set(sensitive_fields or [
            "password", "token", "secret", "api_key", "authorization",
            "cookie", "session", "csrf", "private_key"
        ])
        self.max_body_size = max_body_size
        self.log_event = self._default_log_event  # Can be overridden for testing
        logger.info("AuditMiddleware initialized")
    
    async def process(self, context: RequestContext, handler: Callable) -> Any:
        """Process request through audit middleware.
        
        Args:
            context: Request context
            handler: Next handler in the chain
            
        Returns:
            Handler result with audit logging applied
        """
        start_time = time.time()
        audit_id = self._generate_audit_id()
        
        # Log request
        if self.log_requests:
            await self._log_request(audit_id, context, start_time)
        
        try:
            # Execute handler
            result = await handler(context)
            
            # Log successful response
            if self.log_responses:
                await self._log_response(audit_id, context, result, start_time, True)
            
            return result
            
        except Exception as e:
            # Log error response
            if self.log_responses:
                await self._log_response(audit_id, context, {"error": str(e)}, start_time, False)
            raise
    
    async def _log_request(self, audit_id: str, context: RequestContext, start_time: float):
        """Log incoming request details."""
        event = {
            "audit_id": audit_id,
            "event_type": "request",
            "method": context.method,
            "path": context.path,
            "client_ip": context.client_ip,
            "user_id": context.user_id,
            "authenticated": context.authenticated,
            "headers": self._mask_sensitive_data(context.headers),
            "body": self._process_body(context.body),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "processing_start": start_time
        }
        
        await self.log_event(event)
    
    async def _log_response(
        self, 
        audit_id: str, 
        context: RequestContext, 
        result: Any, 
        start_time: float, 
        success: bool
    ):
        """Log outgoing response details."""
        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        event = {
            "audit_id": audit_id,
            "event_type": "response",
            "method": context.method,
            "path": context.path,
            "client_ip": context.client_ip,
            "user_id": context.user_id,
            "success": success,
            "processing_time_ms": processing_time,
            "response_data": self._process_response(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.log_event(event)
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive fields in data."""
        if not isinstance(data, dict):
            return data
        
        masked = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                masked[key] = "[REDACTED]"
            elif isinstance(value, dict):
                masked[key] = self._mask_sensitive_data(value)
            elif isinstance(value, list):
                masked[key] = [
                    self._mask_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                masked[key] = value
        
        return masked
    
    def _process_body(self, body: Any) -> Any:
        """Process request body for logging."""
        if body is None:
            return None
        
        # Convert to string if needed
        body_str = json.dumps(body) if not isinstance(body, str) else body
        
        # Truncate if too large
        if len(body_str) > self.max_body_size:
            body_str = body_str[:self.max_body_size] + "... [TRUNCATED]"
        
        # Try to parse as JSON for masking
        try:
            parsed = json.loads(body_str) if isinstance(body_str, str) else body
            return self._mask_sensitive_data(parsed) if isinstance(parsed, dict) else parsed
        except (json.JSONDecodeError, TypeError):
            return body_str
    
    def _process_response(self, response: Any) -> Any:
        """Process response data for logging."""
        if response is None:
            return None
        
        # Mask sensitive data in response
        if isinstance(response, dict):
            return self._mask_sensitive_data(response)
        elif isinstance(response, str):
            # Try to parse JSON responses
            try:
                parsed = json.loads(response)
                return self._mask_sensitive_data(parsed) if isinstance(parsed, dict) else parsed
            except (json.JSONDecodeError, TypeError):
                return response[:self.max_body_size] if len(response) > self.max_body_size else response
        
        return str(response)[:self.max_body_size] if len(str(response)) > self.max_body_size else str(response)
    
    def _generate_audit_id(self) -> str:
        """Generate unique audit ID for request/response correlation."""
        from shared.id_generation.unified_id_generator import UnifiedIdGenerator
        return UnifiedIdGenerator.generate_base_id("audit")
    
    async def _default_log_event(self, event: Dict[str, Any]):
        """Default event logging implementation."""
        logger.info(f"AUDIT: {json.dumps(event, default=str, separators=(',', ':'))}")
    
    def add_custom_field(self, context: RequestContext, key: str, value: Any):
        """Add custom field to audit context (for testing/extension)."""
        if not hasattr(context, '_audit_metadata'):
            context._audit_metadata = {}
        context._audit_metadata[key] = value