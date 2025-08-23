#!/usr/bin/env python3
"""Test configuration loading for staging environment."""

import os
import sys
from pathlib import Path

# Add app directory to path

def test_staging_config():
    """Test configuration loading with staging environment variables."""
    _print_staging_header()
    _setup_staging_environment()
    _print_loading_header()
    try:
        config = _load_staging_config()
        _check_staging_configurations(config)
        _print_staging_success()
        return True
    except Exception as e:
        _handle_staging_error(e)
        return False

def _print_staging_header():
    """Print staging test header"""
    print("=" * 80)
    print("Staging Configuration Test")
    print("=" * 80)

def _setup_staging_environment():
    """Set up staging environment variables"""
    print("\n[SETUP] Setting staging environment variables...")
    _set_staging_env_vars()
    _set_test_secrets()
    _print_env_setup_status()

def _set_staging_env_vars():
    """Set core staging environment variables"""
    staging_vars = {
        "ENVIRONMENT": "staging",
        "LOAD_SECRETS": "true",
        "K_SERVICE": "backend-staging-pr-123",
        "GCP_PROJECT_ID_NUMERICAL_STAGING": "123456789",
        "SECRET_MANAGER_PROJECT_ID": "netra-staging",
        "LOG_LEVEL": "DEBUG"
    }
    for key, value in staging_vars.items():
        os.environ[key] = value

def _set_test_secrets():
    """Set test secrets to simulate fallback"""
    test_secrets = {
        "GEMINI_API_KEY": "test-gemini-key-from-env",
        "JWT_SECRET_KEY": "test-jwt-key-from-env",
        "FERNET_KEY": "ZmVybmV0LXRlc3Qta2V5LXBsYWNlaG9sZGVyLTEyMw=="
    }
    for key, value in test_secrets.items():
        os.environ[key] = value

def _print_env_setup_status():
    """Print environment setup status"""
    print("[SETUP] Environment variables set:")
    key_vars = ["ENVIRONMENT", "LOAD_SECRETS", "K_SERVICE", "GCP_PROJECT_ID_NUMERICAL_STAGING"]
    for key in key_vars:
        print(f"  {key}: {os.environ.get(key)}")

def _print_loading_header():
    """Print configuration loading header"""
    print("\n" + "=" * 80)
    print("Loading configuration...")
    print("=" * 80 + "\n")

def _load_staging_config():
    """Load staging configuration with cache clearing"""
    _clear_config_cache()
    from netra_backend.app.config import get_config
    config = get_config()
    print("\n[SUCCESS] Configuration loaded successfully!")
    return config

def _clear_config_cache():
    """Clear configuration module cache"""
    if 'app.config' in sys.modules:
        del sys.modules['app.config']
    if 'app.core.secret_manager' in sys.modules:
        del sys.modules['app.core.secret_manager']

def _check_staging_configurations(config):
    """Check all staging configurations"""
    print("\n[CRITICAL] Configuration Status:")
    _check_environment_config(config)
    _check_staging_llm_configs(config)
    _check_staging_auth_configs(config)

def _check_environment_config(config):
    """Check environment configuration"""
    environment = config.environment if hasattr(config, 'environment') else 'Unknown'
    print(f"\n  Environment: {environment}")

def _check_staging_llm_configs(config):
    """Check staging LLM configurations"""
    if hasattr(config, 'llm_configs'):
        print("\n  LLM Configurations:")
        for name, llm_config in config.llm_configs.items():
            _check_single_staging_llm_config(name, llm_config)

def _check_single_staging_llm_config(name, llm_config):
    """Check single staging LLM configuration"""
    if llm_config and hasattr(llm_config, 'api_key'):
        has_key = bool(llm_config.api_key)
        if has_key:
            key_source = "env vars" if llm_config.api_key == "test-gemini-key-from-env" else "Secret Manager"
            print(f"    {name}: OK - API key configured (from {key_source})")
        else:
            print(f"    {name}: MISSING - No API key")

def _check_staging_auth_configs(config):
    """Check staging authentication configurations"""
    print("\n  Authentication:")
    _check_jwt_config(config)
    _check_fernet_config(config)

def _check_jwt_config(config):
    """Check JWT configuration"""
    jwt_configured = bool(getattr(config, 'jwt_secret_key', None))
    if jwt_configured:
        jwt_source = "env vars" if config.jwt_secret_key == "test-jwt-key-from-env" else "Secret Manager"
        print(f"    JWT Secret: OK - Configured (from {jwt_source})")
    else:
        print(f"    JWT Secret: MISSING")

def _check_fernet_config(config):
    """Check Fernet key configuration"""
    fernet_configured = bool(getattr(config, 'fernet_key', None))
    if fernet_configured:
        fernet_source = "env vars" if config.fernet_key == "ZmVybmV0LXRlc3Qta2V5LXBsYWNlaG9sZGVyLTEyMw==" else "Secret Manager"
        print(f"    Fernet Key: OK - Configured (from {fernet_source})")
    else:
        print(f"    Fernet Key: MISSING")

def _print_staging_success():
    """Print staging test success message"""
    print("\n" + "=" * 80)
    print("[SUCCESS] Staging configuration test completed")
    print("=" * 80)

def _handle_staging_error(e):
    """Handle staging configuration errors"""
    print(f"\n[ERROR] Configuration loading failed: {e}")
    print("\n[DEBUG] Full error details:")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    success = test_staging_config()
    sys.exit(0 if success else 1)