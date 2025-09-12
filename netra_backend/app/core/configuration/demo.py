"""Demo mode configuration module.

This module provides demo mode configuration and validation for the backend service.
Follows SSOT compliance for environment variable access.
"""

from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment


def _get_bool(env: IsolatedEnvironment, key: str, default: bool = False) -> bool:
    """Helper function to convert environment variable to boolean.
    
    Args:
        env: IsolatedEnvironment instance
        key: Environment variable name
        default: Default boolean value
        
    Returns:
        Boolean value parsed from environment variable
    """
    value = env.get(key, str(default).lower())
    if isinstance(value, str):
        return value.lower() in ['true', '1', 'yes', 'on']
    return bool(value)


def get_backend_demo_config() -> Dict[str, Any]:
    """Get backend demo configuration.
    
    Returns:
        Dict containing demo configuration settings
    """
    env = IsolatedEnvironment()
    
    return {
        "enabled": _is_demo_mode(),
        "session_ttl": int(env.get("DEMO_SESSION_TTL", "3600")),
        "max_sessions": int(env.get("MAX_DEMO_SESSIONS", "100")),
        "refresh_interval": int(env.get("DEMO_DATA_REFRESH_INTERVAL", "300")),
        "auto_create_users": _get_bool(env, "DEMO_AUTO_CREATE_USERS", False),
        "permissive_auth": _get_bool(env, "DEMO_PERMISSIVE_AUTH", False)
    }


def is_demo_mode() -> bool:
    """Check if demo mode is enabled.
    
    Returns:
        True if demo mode is enabled, False otherwise
    """
    return _is_demo_mode()


def _is_demo_mode() -> bool:
    """Internal helper to check demo mode status."""
    env = IsolatedEnvironment()
    return _get_bool(env, "DEMO_MODE", False) or _get_bool(env, "ENABLE_DEMO_MODE", False)


def get_demo_config() -> Dict[str, Any]:
    """Get general demo configuration.
    
    Returns:
        Dict containing demo configuration
    """
    env = IsolatedEnvironment()
    
    return {
        "mode": "demo" if _is_demo_mode() else "production",
        "session_management": {
            "ttl": int(env.get("DEMO_SESSION_TTL", "3600")),
            "max_concurrent": int(env.get("MAX_DEMO_SESSIONS", "100"))
        },
        "data_generation": {
            "refresh_interval": int(env.get("DEMO_DATA_REFRESH_INTERVAL", "300")),
            "synthetic_data": _get_bool(env, "DEMO_SYNTHETIC_DATA", True)
        }
    }


def get_auth_config() -> Dict[str, Any]:
    """Get demo-specific authentication configuration.
    
    Returns:
        Dict containing auth configuration for demo mode
    """
    env = IsolatedEnvironment()
    
    return {
        "permissive_mode": _get_bool(env, "DEMO_PERMISSIVE_AUTH", False),
        "auto_create_users": _get_bool(env, "DEMO_AUTO_CREATE_USERS", False),
        "bypass_jwt_validation": _get_bool(env, "DEMO_BYPASS_JWT", False),
        "demo_user_prefix": env.get("DEMO_USER_PREFIX", "demo-user"),
        "demo_session_secret": env.get("DEMO_SESSION_SECRET", "demo-secret-key")
    }


def validate_demo_mode() -> Dict[str, Any]:
    """Validate demo mode configuration.
    
    Returns:
        Dict containing validation results
    """
    env = IsolatedEnvironment()
    is_demo = _is_demo_mode()
    
    validation_results = {
        "valid": True,
        "demo_mode_enabled": is_demo,
        "warnings": [],
        "errors": []
    }
    
    if is_demo:
        # Check required demo environment variables
        required_vars = ["DEMO_SESSION_TTL", "MAX_DEMO_SESSIONS"]
        for var in required_vars:
            if not env.get(var):
                validation_results["warnings"].append(f"Missing optional demo variable: {var}")
        
        # Check for production conflicts
        if env.get("ENVIRONMENT") == "production":
            validation_results["errors"].append("Demo mode should not be enabled in production")
            validation_results["valid"] = False
    
    return validation_results


def get_demo_feature_flags() -> Dict[str, bool]:
    """Get demo-specific feature flags.
    
    Returns:
        Dict containing feature flag states
    """
    env = IsolatedEnvironment()
    is_demo = _is_demo_mode()
    
    return {
        "synthetic_data_generation": is_demo and _get_bool(env, "DEMO_SYNTHETIC_DATA", True),
        "auto_user_creation": is_demo and _get_bool(env, "DEMO_AUTO_CREATE_USERS", False),
        "permissive_authentication": is_demo and _get_bool(env, "DEMO_PERMISSIVE_AUTH", False),
        "mock_external_services": is_demo and _get_bool(env, "DEMO_MOCK_SERVICES", True),
        "enhanced_logging": is_demo and _get_bool(env, "DEMO_ENHANCED_LOGGING", True),
        "rate_limit_bypass": is_demo and _get_bool(env, "DEMO_BYPASS_RATE_LIMITS", False)
    }