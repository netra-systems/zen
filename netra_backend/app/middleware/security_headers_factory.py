"""
Security headers factory and utilities.
Provides factory functions and CSP violation handling.
"""

from typing import Any, Dict, Optional

from fastapi import Request

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.logging_config import central_logger
from netra_backend.app.middleware.security_headers_middleware import (
    SecurityHeadersMiddleware,
)

logger = central_logger.get_logger(__name__)


def create_security_headers_middleware(environment: Optional[str] = None) -> SecurityHeadersMiddleware:
    """Factory function to create security headers middleware."""
    if not environment:
        environment = getattr(settings, 'environment', 'development')
    return SecurityHeadersMiddleware(None, environment)


async def handle_csp_violation_report(request: Request, middleware: SecurityHeadersMiddleware) -> Dict[str, str]:
    """Handle CSP violation reports."""
    try:
        return await _process_csp_violation(request, middleware)
    except Exception as e:
        return _handle_csp_violation_error(e)

async def _process_csp_violation(request: Request, middleware: SecurityHeadersMiddleware) -> Dict[str, str]:
    """Process CSP violation report."""
    violation_data = await request.json()
    csp_report = violation_data.get("csp-report", {})
    middleware.handle_csp_violation(csp_report)
    return {"status": "received"}

def _handle_csp_violation_error(error: Exception) -> Dict[str, str]:
    """Handle CSP violation processing error."""
    logger.error(f"Error handling CSP violation report: {error}")
    return {"status": "error", "message": str(error)}


# Global instance (to be initialized by app factory)
security_headers_middleware = None