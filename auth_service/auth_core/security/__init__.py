"""
Security utilities for OAuth authentication and middleware
"""

# Canonical security middleware - SSOT for auth service security functionality
from .middleware import (
    validate_request_size,
    add_service_headers,
    add_security_headers,
    create_security_middleware,
    MAX_JSON_PAYLOAD_SIZE
)