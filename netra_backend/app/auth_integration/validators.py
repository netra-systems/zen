"""
Auth Validation Utilities - Single Source of Truth
Centralized validation logic for authentication models.

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Consistent validation across platform
- Value Impact: Reduce auth errors by 15-20%
- Revenue Impact: +$2K MRR from better UX

Architecture:
- 450-line module limit enforced
- 25-line function limit enforced
- Reusable validation functions
- Strong typing with proper error handling
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import ValidationError


def validate_email_format(email: str) -> bool:
    """Validate email format using email-validator"""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return {"valid": False, "error": "Password too short"}
    
    return _check_password_character_requirements(password)

def _check_password_character_requirements(password: str) -> Dict[str, Any]:
    """Check password character requirements."""
    if not re.search(r"[A-Z]", password):
        return {"valid": False, "error": "Missing uppercase letter"}
    if not re.search(r"[a-z]", password):
        return {"valid": False, "error": "Missing lowercase letter"}
    if not re.search(r"\d", password):
        return {"valid": False, "error": "Missing number"}
    return {"valid": True, "error": None}


def validate_token_format(token: str) -> bool:
    """Validate JWT token format"""
    if not token:
        return False
    if len(token.split('.')) != 3:
        return False
    return _check_token_length(token)

def _check_token_length(token: str) -> bool:
    """Check if token meets minimum length requirement."""
    return len(token) >= 20


def validate_service_id(service_id: str) -> bool:
    """Validate service ID format"""
    if not service_id:
        return False
    if not re.match(r"^[a-zA-Z0-9_-]+$", service_id):
        return False
    return _check_service_id_length(service_id)

def _check_service_id_length(service_id: str) -> bool:
    """Check service ID length is within valid range."""
    return 3 <= len(service_id) <= 50


def validate_permission_format(permission: str) -> bool:
    """Validate permission string format"""
    if not permission:
        return False
    if not re.match(r"^[a-zA-Z0-9_:.-]+$", permission):
        return False
    return _check_permission_length(permission)

def _check_permission_length(permission: str) -> bool:
    """Check permission string length."""
    return len(permission) <= 100


def validate_session_metadata(metadata: Dict[str, Any]) -> bool:
    """Validate session metadata structure"""
    if not isinstance(metadata, dict):
        return False
    if len(str(metadata)) > 1000:  # Prevent oversized metadata
        return False
    return True


def validate_ip_address(ip_address: str) -> bool:
    """Validate IP address format (IPv4 or IPv6)"""
    if not ip_address:
        return True  # Optional field
    
    return _validate_ip_format(ip_address)

def _validate_ip_format(ip_address: str) -> bool:
    """Validate IP address format."""
    if _is_valid_ipv4(ip_address):
        return True
    if _is_valid_ipv6(ip_address):
        return True
    return False

def _is_valid_ipv4(ip_address: str) -> bool:
    """Check if IP address is valid IPv4."""
    ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
    if re.match(ipv4_pattern, ip_address):
        parts = ip_address.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    return False

def _is_valid_ipv6(ip_address: str) -> bool:
    """Check if IP address is valid IPv6."""
    return ':' in ip_address and len(ip_address) <= 39


def validate_user_agent(user_agent: str) -> bool:
    """Validate user agent string"""
    if not user_agent:
        return True  # Optional field
    if len(user_agent) > 500:
        return False
    return True


def validate_audit_event_type(event_type: str) -> bool:
    """Validate audit event type"""
    valid_types = [
        "login", "logout", "token_refresh", "token_validate",
        "password_change", "profile_update", "permission_grant",
        "permission_revoke", "session_create", "session_destroy"
    ]
    return event_type in valid_types


def validate_auth_provider(provider: str) -> bool:
    """Validate authentication provider"""
    valid_providers = ["local", "google", "github", "api_key"]
    return provider in valid_providers


def validate_token_type(token_type: str) -> bool:
    """Validate token type"""
    valid_types = ["access", "refresh", "service"]
    return token_type in valid_types


def validate_expires_at(expires_at: datetime) -> bool:
    """Validate expiration timestamp"""
    if not expires_at:
        return False
    if expires_at <= datetime.now(timezone.utc):
        return False
    return _check_max_expiry(expires_at)

def _check_max_expiry(expires_at: datetime) -> bool:
    """Check if expiry is within maximum allowed timeframe."""
    max_expiry = datetime.now(timezone.utc) + timedelta(days=365)
    return expires_at <= max_expiry


def validate_oauth_token(oauth_token: str) -> bool:
    """
    DEPRECATED: Validate OAuth token format
    
    This function now delegates to SSOT OAuth validation.
    Use shared.configuration.central_config_validator.validate_oauth_token_comprehensive() instead.
    """
    try:
        # SSOT OAuth validation - this replaces duplicate implementation
        from shared.configuration.central_config_validator import validate_oauth_token_comprehensive
        
        # Use SSOT OAuth token validation
        return validate_oauth_token_comprehensive(oauth_token)
        
    except ImportError:
        # Fallback if SSOT not available
        if not oauth_token:
            return False
        return _check_oauth_token_length(oauth_token)

def _check_oauth_token_length(oauth_token: str) -> bool:
    """Check OAuth token length constraints."""
    return 10 <= len(oauth_token) <= 2000


def validate_error_code(error_code: str) -> bool:
    """Validate error code format"""
    if not error_code:
        return False
    if not re.match(r"^[A-Z_]+$", error_code):
        return False
    return _check_error_code_length(error_code)

def _check_error_code_length(error_code: str) -> bool:
    """Check error code length constraint."""
    return len(error_code) <= 50


def validate_endpoint_url(url: str) -> bool:
    """Validate endpoint URL format"""
    if not url:
        return False
    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if not re.match(url_pattern, url):
        return False
    return _check_url_length(url)

def _check_url_length(url: str) -> bool:
    """Check URL length constraint."""
    return len(url) <= 200


def validate_cors_origin(origin: str) -> bool:
    """Validate CORS origin format"""
    if origin == "*":
        return True
    if not origin:
        return False
    
    return _validate_origin_format(origin)

def _validate_origin_format(origin: str) -> bool:
    """Validate origin format (URL or domain)."""
    if origin.startswith("http://") or origin.startswith("https://"):
        return validate_endpoint_url(origin)
    
    return _is_valid_domain(origin)

def _is_valid_domain(domain: str) -> bool:
    """Check if domain format is valid."""
    domain_pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(domain_pattern, domain) is not None


def sanitize_user_input(input_str: str, max_length: int = 100) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not input_str:
        return ""
    
    return _process_sanitization(input_str, max_length)

def _process_sanitization(input_str: str, max_length: int) -> str:
    """Process input sanitization steps."""
    sanitized = re.sub(r'[<>"\';]', '', input_str)
    sanitized = sanitized[:max_length]
    return sanitized.strip()


def validate_permission_list(permissions: List[str]) -> bool:
    """Validate list of permissions"""
    if not isinstance(permissions, list):
        return False
    if len(permissions) > 50:  # Prevent excessive permissions
        return False
    return all(validate_permission_format(perm) for perm in permissions)


def validate_auth_request_timing(request_time: datetime) -> bool:
    """Validate auth request is within acceptable time window"""
    now = datetime.now(timezone.utc)
    time_diff = abs((now - request_time).total_seconds())
    
    # Allow requests within 5 minutes of current time
    return time_diff <= 300


def create_validation_error(field: str, message: str) -> Dict[str, Any]:
    """Create standardized validation error"""
    return {
        "field": field,
        "message": message,
        "code": "VALIDATION_ERROR",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class AuthValidationError(Exception):
    """Custom exception for auth validation errors"""
    
    def __init__(self, field: str, message: str, code: str = "VALIDATION_ERROR"):
        self.field = field
        self.message = message
        self.code = code
        super().__init__(f"{field}: {message}")


def validate_model_field(value: Any, field_name: str, validator_func) -> Any:
    """Generic model field validation wrapper"""
    try:
        if not validator_func(value):
            raise AuthValidationError(field_name, f"Invalid {field_name}")
        return value
    except Exception as e:
        raise AuthValidationError(field_name, str(e))