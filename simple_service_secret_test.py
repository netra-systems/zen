#!/usr/bin/env python3
"""
Simple test for SERVICE_SECRET validation.
"""

import os
from unittest.mock import patch

def test_service_secret_required():
    """Test that SERVICE_SECRET is required in staging."""
    
    # Base environment without SERVICE_SECRET
    env_without_service_secret = {
        "ENVIRONMENT": "staging",
        "DATABASE_URL": "postgresql://user:pass@host:5432/db",
        "REDIS_HOST": "redis-host",
        "REDIS_PASSWORD": "redis-pass-123456",
        "FERNET_KEY": "fernet-key-" + "x" * 22,  # 32+ chars
        "GEMINI_API_KEY": "gemini-key-123456",
        "GOOGLE_OAUTH_CLIENT_ID_STAGING": "oauth-id-staging",
        "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "oauth-secret-staging-123456",
        "JWT_SECRET_STAGING": "jwt-secret-staging-" + "x" * 14  # 33 chars
    }
    
    print("Testing SERVICE_SECRET requirement in staging environment...")
    
    try:
        with patch.dict(os.environ, env_without_service_secret, clear=True):
            from shared.configuration.central_config_validator import CentralConfigurationValidator
            validator = CentralConfigurationValidator()
            validator.validate_all_requirements()
            print("❌ FAIL: Missing SERVICE_SECRET should have failed validation")
            return False
    except ValueError as e:
        if "SERVICE_SECRET required" in str(e):
            print("✅ PASS: Missing SERVICE_SECRET correctly rejected")
            return True
        else:
            print(f"❌ FAIL: Wrong error for missing SERVICE_SECRET: {e}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_service_secret_required()
    exit(0 if success else 1)