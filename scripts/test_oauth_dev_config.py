from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Test OAuth credential loading for development environment.
Verifies that the auth service correctly loads development-specific OAuth credentials.
"""
import os
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env = get_env()
def test_oauth_credential_loading():
    """Test that OAuth credentials are loaded correctly for each environment."""
    print("Testing OAuth credential loading for development environment...")
    print("-" * 60)
    
    # Test different environment configurations
    test_cases = [
        {
            "env": "development",
            "vars": {
                "ENVIRONMENT": "development",
                "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "dev-client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT": "dev-client-secret-123456",
                "GOOGLE_CLIENT_ID": "fallback-client-id",
                "GOOGLE_CLIENT_SECRET": "fallback-secret"
            },
            "expected_id_log": "Using GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT from environment",
            "expected_secret_log": "Using GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT from environment",
            "expected_id": "dev-client-id.apps.googleusercontent.com",
            "expected_secret": "dev-client-secret-123456"
        },
        {
            "env": "development with fallback",
            "vars": {
                "ENVIRONMENT": "development",
                "GOOGLE_CLIENT_ID": "fallback-client-id.apps.googleusercontent.com",
                "GOOGLE_CLIENT_SECRET": "fallback-secret-789012"
            },
            "expected_id_log": "Using GOOGLE_CLIENT_ID from environment",
            "expected_secret_log": "Using GOOGLE_CLIENT_SECRET from environment",
            "expected_id": "fallback-client-id.apps.googleusercontent.com",
            "expected_secret": "fallback-secret-789012"
        },
        {
            "env": "staging",
            "vars": {
                "ENVIRONMENT": "staging",
                "GOOGLE_OAUTH_CLIENT_ID_STAGING": "staging-client-id.apps.googleusercontent.com",
                "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "staging-secret-345678",
                "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT": "dev-client-id",
                "GOOGLE_CLIENT_ID": "fallback-client-id"
            },
            "expected_id_log": "Using GOOGLE_OAUTH_CLIENT_ID_STAGING from environment",
            "expected_secret_log": "Using GOOGLE_OAUTH_CLIENT_SECRET_STAGING from environment",
            "expected_id": "staging-client-id.apps.googleusercontent.com",
            "expected_secret": "staging-secret-345678"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['env']}")
        print("-" * 40)
        
        # Save original environment
        original_env = env.get_all()
        
        try:
            # Clear relevant environment variables
            for key in ["ENVIRONMENT", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
                       "GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT", "GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT",
                       "GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
                       "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"]:
                os.environ.pop(key, None)
            
            # Set test environment variables
            for key, value in test_case["vars"].items():
                os.environ[key] = value
            
            # Import after setting environment to ensure fresh load
            from auth_service.auth_core.secret_loader import AuthSecretLoader
            
            # Test client ID loading
            client_id = AuthSecretLoader.get_google_client_id()
            print(f"  Client ID: {client_id[:30]}..." if len(client_id) > 30 else f"  Client ID: {client_id}")
            assert client_id == test_case["expected_id"], f"Expected {test_case['expected_id']}, got {client_id}"
            print(f"  [OK] Client ID loaded correctly")
            
            # Test client secret loading
            client_secret = AuthSecretLoader.get_google_client_secret()
            print(f"  Client Secret: {'*' * 10} (hidden)")
            assert client_secret == test_case["expected_secret"], f"Expected {test_case['expected_secret']}, got {client_secret}"
            print(f"  [OK] Client Secret loaded correctly")
            
        except Exception as e:
            print(f"  [FAIL] Test failed: {e}")
            return False
        finally:
            # Restore original environment
            env.clear()
            env.update(original_env, "test")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] All OAuth credential loading tests passed!")
    print("=" * 60)
    print("\nTo use development-specific OAuth credentials:")
    print("1. Create a Google OAuth client for local development")
    print("2. Set authorized redirect URI to: http://localhost:3000/auth/callback")
    print("3. Add to your .env file:")
    print("   GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT=your-dev-client-id.apps.googleusercontent.com")
    print("   GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT=your-dev-client-secret")
    
    return True

if __name__ == "__main__":
    success = test_oauth_credential_loading()
    sys.exit(0 if success else 1)