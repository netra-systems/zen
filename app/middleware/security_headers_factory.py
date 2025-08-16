"""
Security headers factory and utilities.
Provides factory functions and CSP violation handling.
"""

from typing import Optional, Dict, Any
from fastapi import Request

from app.config import settings
from app.logging_config import central_logger
from .security_headers_middleware import SecurityHeadersMiddleware

logger = central_logger.get_logger(__name__)


def create_security_headers_middleware(environment: Optional[str] = None) -> SecurityHeadersMiddleware:
    """Factory function to create security headers middleware."""
    if not environment:
        environment = getattr(settings, 'environment', 'development')
    return SecurityHeadersMiddleware(None, environment)


async def handle_csp_violation_report(request: Request, middleware: SecurityHeadersMiddleware) -> Dict[str, str]:
    """Handle CSP violation reports."""
    try:
        violation_data = await request.json()
        csp_report = violation_data.get("csp-report", {})
        middleware.handle_csp_violation(csp_report)
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error handling CSP violation report: {e}")
        return {"status": "error", "message": str(e)}


# Global instance (to be initialized by app factory)
security_headers_middleware = None