#!/usr/bin/env python3
"""Test configuration loading with detailed logging for debugging staging issues."""

import os
import sys
import json
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_config_loading():
    """Test configuration loading with detailed output."""
    _print_test_header()
    _print_environment_variables()
    _print_loading_header()
    try:
        config = _load_and_reload_config()
        _check_all_configurations(config)
        _print_success_footer()
        return True
    except Exception as e:
        _handle_configuration_error(e)
        return False

def _print_test_header():
    """Print test header"""
    print("=" * 80)
    print("Configuration Loading Test")
    print("=" * 80)

def _print_environment_variables():
    """Print environment variable information"""
    print("\n[INFO] Environment Variables:")
    env_vars = ["ENVIRONMENT", "K_SERVICE", "K_REVISION", "GCP_PROJECT_ID", "GCP_PROJECT_ID_NUMERICAL_STAGING", "SECRET_MANAGER_PROJECT_ID", "LOAD_SECRETS", "PR_NUMBER", "GEMINI_API_KEY", "JWT_SECRET_KEY", "FERNET_KEY"]
    for var in env_vars:
        _print_environment_variable(var)

def _print_environment_variable(var):
    """Print single environment variable with masking"""
    value = os.environ.get(var)
    if value:
        display_value = _mask_sensitive_value(var, value)
        print(f"  {var}: {display_value}")
    else:
        print(f"  {var}: <not set>")

def _mask_sensitive_value(var, value):
    """Mask sensitive environment variable values"""
    if "KEY" in var or "SECRET" in var or "PASSWORD" in var:
        return f"{value[:5]}...{value[-5:]}" if len(value) > 10 else "***"
    return value

def _print_loading_header():
    """Print configuration loading header"""
    print("\n" + "=" * 80)
    print("Loading configuration...")
    print("=" * 80 + "\n")

def _load_and_reload_config():
    """Load and reload configuration modules"""
    from netra_backend.app.config import settings, get_config
    from netra_backend.app.config import reload_config
    reload_config()
    config = get_config()
    print("\n[SUCCESS] Configuration loaded successfully!")
    return config

def _check_all_configurations(config):
    """Check all critical configurations"""
    print("\n[CRITICAL] Configuration Status:")
    _check_llm_configurations(config)
    _check_auth_configurations(config)
    _check_oauth_configuration(config)
    _check_database_configuration(config)

def _check_llm_configurations(config):
    """Check LLM configurations"""
    if hasattr(config, 'llm_configs'):
        print("\n  LLM Configurations:")
        for name, llm_config in config.llm_configs.items():
            _check_single_llm_config(name, llm_config)

def _check_single_llm_config(name, llm_config):
    """Check single LLM configuration"""
    if llm_config and hasattr(llm_config, 'api_key'):
        has_key = bool(llm_config.api_key)
        status = "OK" if has_key else "MISSING"
        message = 'API key configured' if has_key else 'No API key'
        print(f"    {name}: {status} {message}")

def _check_auth_configurations(config):
    """Check authentication configurations"""
    print("\n  Authentication:")
    jwt_configured = bool(getattr(config, 'jwt_secret_key', None))
    fernet_configured = bool(getattr(config, 'fernet_key', None))
    print(f"    JWT Secret: {'OK - Configured' if jwt_configured else 'MISSING'}")
    print(f"    Fernet Key: {'OK - Configured' if fernet_configured else 'MISSING'}")

def _check_oauth_configuration(config):
    """Check OAuth configuration"""
    if hasattr(config, 'oauth_config'):
        oauth = config.oauth_config
        client_id = bool(getattr(oauth, 'client_id', None))
        client_secret = bool(getattr(oauth, 'client_secret', None))
        print(f"\n  OAuth Configuration:")
        print(f"    Client ID: {'OK - Configured' if client_id else 'MISSING'}")
        print(f"    Client Secret: {'OK - Configured' if client_secret else 'MISSING'}")

def _check_database_configuration(config):
    """Check database configuration"""
    if hasattr(config, 'database_url'):
        db_url = config.database_url
        if db_url:
            masked_url = _mask_database_url(db_url)
            print(f"\n  Database:")
            print(f"    URL: {masked_url}")

def _mask_database_url(db_url):
    """Mask sensitive parts of database URL"""
    if "@" in db_url:
        parts = db_url.split("@")
        return f"{parts[0].split('://')[0]}://***@{parts[1]}"
    return db_url

def _print_success_footer():
    """Print success footer"""
    print("\n" + "=" * 80)
    print("[SUCCESS] All configuration checks completed")
    print("=" * 80)

def _handle_configuration_error(e):
    """Handle configuration loading errors"""
    print(f"\n[ERROR] Configuration loading failed: {e}")
    print("\n[DEBUG] Full error details:")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    # Set some test environment variables if running locally
    if not os.environ.get("ENVIRONMENT"):
        print("[INFO] No ENVIRONMENT set, using test values for local testing")
        os.environ["ENVIRONMENT"] = "development"
        os.environ["LOG_LEVEL"] = "DEBUG"
    
    success = test_config_loading()
    sys.exit(0 if success else 1)