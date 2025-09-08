"""
Security utilities for OAuth authentication and middleware
"""

# Canonical security middleware - SSOT for auth service security functionality
from auth_service.auth_core.security.middleware import (
    validate_request_size,
    add_service_headers,
    add_security_headers,
    create_security_middleware,
    MAX_JSON_PAYLOAD_SIZE
)

# Cross-service validation - SSOT for inter-service authentication
from auth_service.auth_core.security.cross_service_validator import (
    CrossServiceValidator,
    CrossServiceValidationResult
)

# Password policy validation - SSOT for password security validation
from auth_service.auth_core.security.password_policy_validator import (
    PasswordPolicyValidator,
    PasswordPolicyResult
)