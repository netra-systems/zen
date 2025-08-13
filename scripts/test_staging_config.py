#!/usr/bin/env python3
"""Test configuration loading for staging environment."""

import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_staging_config():
    """Test configuration loading with staging environment variables."""
    
    print("=" * 80)
    print("Staging Configuration Test")
    print("=" * 80)
    
    # Set staging environment variables
    print("\n[SETUP] Setting staging environment variables...")
    os.environ["ENVIRONMENT"] = "staging"
    os.environ["LOAD_SECRETS"] = "true"
    os.environ["K_SERVICE"] = "backend-staging-pr-123"
    os.environ["GCP_PROJECT_ID_NUMERICAL_STAGING"] = "123456789"  # Simulated numerical ID
    os.environ["SECRET_MANAGER_PROJECT_ID"] = "netra-staging"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Optional: Set some test secrets in env vars to simulate fallback
    os.environ["GEMINI_API_KEY"] = "test-gemini-key-from-env"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-key-from-env"
    os.environ["FERNET_KEY"] = "ZmVybmV0LXRlc3Qta2V5LXBsYWNlaG9sZGVyLTEyMw=="
    
    print("[SETUP] Environment variables set:")
    for key in ["ENVIRONMENT", "LOAD_SECRETS", "K_SERVICE", "GCP_PROJECT_ID_NUMERICAL_STAGING"]:
        print(f"  {key}: {os.environ.get(key)}")
    
    print("\n" + "=" * 80)
    print("Loading configuration...")
    print("=" * 80 + "\n")
    
    try:
        # Clear any cached config first
        if 'app.config' in sys.modules:
            del sys.modules['app.config']
        if 'app.core.secret_manager' in sys.modules:
            del sys.modules['app.core.secret_manager']
        
        # Import config (this will trigger the loading process)
        from app.config import get_config
        
        # Get the config
        config = get_config()
        
        print("\n[SUCCESS] Configuration loaded successfully!")
        
        # Check critical configurations
        print("\n[CRITICAL] Configuration Status:")
        
        # Check environment
        print(f"\n  Environment: {config.environment if hasattr(config, 'environment') else 'Unknown'}")
        
        # Check LLM configs
        if hasattr(config, 'llm_configs'):
            print("\n  LLM Configurations:")
            for name, llm_config in config.llm_configs.items():
                if llm_config and hasattr(llm_config, 'api_key'):
                    has_key = bool(llm_config.api_key)
                    if has_key:
                        # Check if it's from env or would be from Secret Manager
                        key_source = "env vars" if llm_config.api_key == "test-gemini-key-from-env" else "Secret Manager"
                        print(f"    {name}: OK - API key configured (from {key_source})")
                    else:
                        print(f"    {name}: MISSING - No API key")
        
        # Check auth configs
        print("\n  Authentication:")
        jwt_configured = bool(getattr(config, 'jwt_secret_key', None))
        fernet_configured = bool(getattr(config, 'fernet_key', None))
        
        if jwt_configured:
            jwt_source = "env vars" if config.jwt_secret_key == "test-jwt-key-from-env" else "Secret Manager"
            print(f"    JWT Secret: OK - Configured (from {jwt_source})")
        else:
            print(f"    JWT Secret: MISSING")
            
        if fernet_configured:
            fernet_source = "env vars" if config.fernet_key == "ZmVybmV0LXRlc3Qta2V5LXBsYWNlaG9sZGVyLTEyMw==" else "Secret Manager"
            print(f"    Fernet Key: OK - Configured (from {fernet_source})")
        else:
            print(f"    Fernet Key: MISSING")
        
        print("\n" + "=" * 80)
        print("[SUCCESS] Staging configuration test completed")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Configuration loading failed: {e}")
        print("\n[DEBUG] Full error details:")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_staging_config()
    sys.exit(0 if success else 1)