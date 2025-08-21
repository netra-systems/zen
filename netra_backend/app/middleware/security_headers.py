"""
Security headers middleware for comprehensive protection.
Backward compatibility module that re-exports from split modules.
"""

# Import all components from split modules
from netra_backend.app.middleware.security_headers_config import SecurityHeadersConfig
from netra_backend.app.middleware.nonce_generator import NonceGenerator
from netra_backend.app.middleware.security_headers_middleware import SecurityHeadersMiddleware
from netra_backend.app.middleware.security_headers_factory import (
    create_security_headers_middleware,
    handle_csp_violation_report,
    security_headers_middleware
)

# Re-export all classes and functions for backward compatibility
__all__ = [
    'SecurityHeadersConfig',
    'NonceGenerator', 
    'SecurityHeadersMiddleware',
    'create_security_headers_middleware',
    'handle_csp_violation_report',
    'security_headers_middleware'
]