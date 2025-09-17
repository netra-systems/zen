from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
JWT Secret Synchronization Test

CRITICAL: This test ensures that both auth service and backend service
use the EXACT same JWT secret. This is REQUIRED for authentication to work.
'''
import os
import sys
import pytest
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


env = get_env()
def test_jwt_secrets_are_synchronized():
'''
CRITICAL: Ensure both services use EXACT same JWT secret.

This test validates that the shared JWT secret manager is working
correctly and both services get the same secret.
'''
pass
    # Import both service configurations
from auth_service.auth_core.config import AuthConfig
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager

    Get JWT secrets from both services
auth_secret = AuthConfig.get_jwt_secret()

    # Create backend secret manager instance
backend_manager = UnifiedSecretManager()
backend_secret = backend_manager.get_jwt_secret()

    # CRITICAL: Secrets MUST be identical
assert auth_secret == backend_secret, ( )
""
    

    # Ensure secret meets minimum security requirements
assert len(auth_secret) >= 32, ""

    # Ensure no whitespace issues
assert auth_secret == auth_secret.strip(), "JWT secret has whitespace"

print("")


def test_shared_jwt_manager_consistency():
'''
Test that SharedJWTSecretManager returns consistent results.
'''
pass
from shared.jwt_secret_manager import SharedJWTSecretManager

    # Get secret multiple times
secret1 = SharedJWTSecretManager.get_jwt_secret()
secret2 = SharedJWTSecretManager.get_jwt_secret()
secret3 = SharedJWTSecretManager.get_jwt_secret()

    # All calls should return the same secret
assert secret1 == secret2 == secret3, "SharedJWTSecretManager returns inconsistent secrets"

    # Clear cache and verify we still get the same secret
SharedJWTSecretManager.clear_cache()
secret4 = SharedJWTSecretManager.get_jwt_secret()

assert secret1 == secret4, "Secret changed after cache clear"


def test_jwt_secret_environment_specific():
'''
Test that environment-specific JWT secrets are loaded correctly.
'''
pass
from shared.jwt_secret_manager import SharedJWTSecretManager

    # Clear cache before each test
SharedJWTSecretManager.clear_cache()

    # Test staging environment
with patch.dict(os.environ, { })
"ENVIRONMENT": "staging",
"JWT_SECRET_STAGING": "staging-secret-with-32-characters-minimum",
"JWT_SECRET_KEY": "generic-secret"
}):
SharedJWTSecretManager.clear_cache()
secret = SharedJWTSecretManager.get_jwt_secret()
assert secret == "staging-secret-with-32-characters-minimum"

        # Test production environment
with patch.dict(os.environ, { })
"ENVIRONMENT": "production",
"JWT_SECRET_PRODUCTION": "production-secret-with-32-characters-min",
"JWT_SECRET_KEY": "generic-secret"
}):
SharedJWTSecretManager.clear_cache()
secret = SharedJWTSecretManager.get_jwt_secret()
assert secret == "production-secret-with-32-characters-min"

            # Test fallback to JWT_SECRET_KEY
with patch.dict(os.environ, { })
"ENVIRONMENT": "staging",
"JWT_SECRET_KEY": "generic-secret-with-32-characters-minimum"
}, clear=True):
SharedJWTSecretManager.clear_cache()
secret = SharedJWTSecretManager.get_jwt_secret()
assert secret == "generic-secret-with-32-characters-minimum"


def test_jwt_secret_validation():
'''
Test that JWT secret validation works correctly.
'''
pass
from shared.jwt_secret_manager import SharedJWTSecretManager

    # Test that short secrets fail in production
with patch.dict(os.environ, { })
"ENVIRONMENT": "production",
"JWT_SECRET_KEY": "too-short"
}, clear=True):
SharedJWTSecretManager.clear_cache()
with pytest.raises(ValueError, match="at least 32 characters"):
SharedJWTSecretManager.get_jwt_secret()

            # Test that missing secrets fail in production
with patch.dict(os.environ, { })
"ENVIRONMENT": "production"
}, clear=True):
SharedJWTSecretManager.clear_cache()
with pytest.raises(ValueError, match="JWT secret is REQUIRED"):
SharedJWTSecretManager.get_jwt_secret()

                    # Test whitespace validation
with patch.dict(os.environ, { })
"ENVIRONMENT": "staging",
"JWT_SECRET_KEY": "  secret-with-whitespace-32-chars-minimum  "
}, clear=True):
SharedJWTSecretManager.clear_cache()
secret = SharedJWTSecretManager.get_jwt_secret()
                        # Should be stripped
assert secret == "secret-with-whitespace-32-chars-minimum"


def test_jwt_synchronization_validation():
'''
Test the deployment validation function.
'''
pass
from shared.jwt_secret_manager import validate_jwt_configuration

    # Set up a valid configuration
with patch.dict(os.environ, { })
"ENVIRONMENT": "staging",
"JWT_SECRET_KEY": "valid-staging-secret-with-32-characters-min"
}):
from shared.jwt_secret_manager import SharedJWTSecretManager
SharedJWTSecretManager.clear_cache()

        # Validation should pass
assert validate_jwt_configuration() == True

        # Test that development secrets fail in production
with patch.dict(os.environ, { })
"ENVIRONMENT": "production",
"JWT_SECRET_KEY": "development-jwt-secret-minimum-32-characters-long"
}):
SharedJWTSecretManager.clear_cache()

with pytest.raises(ValueError, match="Development secret used in production"):
validate_jwt_configuration()


if __name__ == "__main__":
                    # Run tests
    print("Running JWT Secret Synchronization Tests...")

                    # Set up test environment
env.set("ENVIRONMENT", "test", "test")
env.set("JWT_SECRET_KEY", "test-jwt-secret-32-character-minimum-length", "test")

try:
test_jwt_secrets_are_synchronized()
print(" PASS:  JWT synchronization test passed")

test_shared_jwt_manager_consistency()
print(" PASS:  Shared manager consistency test passed")

test_jwt_secret_environment_specific()
print(" PASS:  Environment-specific secret test passed")

test_jwt_secret_validation()
print(" PASS:  Secret validation test passed")

test_jwt_synchronization_validation()
print(" PASS:  Deployment validation test passed")

print("")
CELEBRATION:  All JWT synchronization tests PASSED!")

except AssertionError as e:
    print("")
sys.exit(1)
except Exception as e:
    print("")
sys.exit(1)
