#!/usr/bin/env python3
'''
MISSION CRITICAL: Central Configuration Validator Integration Tests

Verifies that both auth and backend services properly use the central validator
for ALL critical secrets with hard requirements (no dangerous fallbacks).

Business Value: Platform/Internal - Configuration Security and Consistency
Prevents production misconfigurations by validating centralized configuration enforcement.
'''

import os
import sys
import tempfile
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_auth_service_uses_central_validator_for_jwt():
    "Test auth service delegates JWT secret to central validator.""
print( PASS:  Testing auth service central validator integration for JWT...")

    # Import auth service
from auth_service.auth_core.secret_loader import AuthSecretLoader
from shared.isolated_environment import get_env

    # Test staging environment
original_env = get_env().get("ENVIRONMENT)
get_env().set(ENVIRONMENT", "staging, test")

    # Clear any existing JWT secrets to force hard failure
get_env().delete("JWT_SECRET_STAGING)
get_env().delete(JWT_SECRET_PRODUCTION")
get_env().delete("JWT_SECRET_KEY)

try:
    AuthSecretLoader.get_jwt_secret()
raise AssertionError(Expected ValueError for missing JWT_SECRET_STAGING")
except ValueError as e:
    assert "JWT_SECRET_STAGING required in staging environment in str(e)
print(   PASS:  Auth service properly uses central validator hard requirements")
finally:
                # Restore environment
if original_env:
    get_env().set("ENVIRONMENT, original_env, test")
else:
    get_env().delete("ENVIRONMENT)


def test_backend_service_uses_central_validator_for_jwt():
    ""Test backend service delegates JWT secret to central validator."
pass
print(" PASS:  Testing backend service central validator integration for JWT...)

    # Import backend service
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
from shared.isolated_environment import get_env

    # Test production environment
original_env = get_env().get(ENVIRONMENT")
get_env().set("ENVIRONMENT, production", "test)

    # Clear any existing JWT secrets to force hard failure
get_env().delete(JWT_SECRET_STAGING")
get_env().delete("JWT_SECRET_PRODUCTION)
get_env().delete(JWT_SECRET_KEY")

secret_manager = UnifiedSecretManager()

try:
    secret_manager.get_jwt_secret()
raise AssertionError("Expected ValueError for missing JWT_SECRET_PRODUCTION)
except ValueError as e:
    assert JWT_SECRET_PRODUCTION required in production environment" in str(e)
    print("   PASS:  Backend service properly uses central validator hard requirements)
finally:
                # Restore environment
if original_env:
    get_env().set(ENVIRONMENT", original_env, "test)
else:
    get_env().delete(ENVIRONMENT")


def test_backend_service_uses_central_validator_for_database():
    "Test backend service delegates database credentials to central validator.""
print( PASS:  Testing backend service central validator integration for database...")

from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
from shared.isolated_environment import get_env

    # Test staging environment
original_env = get_env().get("ENVIRONMENT)
get_env().set(ENVIRONMENT", "staging, test")

    # Clear database configuration to force hard failure
get_env().delete("DATABASE_HOST)
get_env().delete(DATABASE_PASSWORD")

secret_manager = UnifiedSecretManager()

try:
    secret_manager.get_database_credentials()
raise AssertionError("Expected ValueError for missing database configuration)
except ValueError as e:
    assert (DATABASE_HOST" in str(e) or "DATABASE_PASSWORD in str(e))
print(   PASS:  Backend service properly uses central validator for database credentials")
finally:
                # Restore environment
if original_env:
    get_env().set("ENVIRONMENT, original_env, test")
else:
    get_env().delete("ENVIRONMENT)


def test_backend_service_uses_central_validator_for_redis():
    ""Test backend service delegates Redis credentials to central validator."
pass
print(" PASS:  Testing backend service central validator integration for Redis...)

from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
from shared.isolated_environment import get_env

    # Test production environment
original_env = get_env().get(ENVIRONMENT")
get_env().set("ENVIRONMENT, production", "test)

    # Clear Redis configuration to force hard failure
get_env().delete(REDIS_HOST")
get_env().delete("REDIS_PASSWORD)

secret_manager = UnifiedSecretManager()

try:
    secret_manager.get_redis_credentials()
raise AssertionError(Expected ValueError for missing Redis configuration")
except ValueError as e:
    assert ("REDIS_HOST in str(e) or REDIS_PASSWORD" in str(e))
    print("   PASS:  Backend service properly uses central validator for Redis credentials)
finally:
                # Restore environment
if original_env:
    get_env().set(ENVIRONMENT", original_env, "test)
else:
    get_env().delete(ENVIRONMENT")


def test_backend_service_uses_central_validator_for_llm():
    "Test backend service delegates LLM credentials to central validator.""
print( PASS:  Testing backend service central validator integration for LLM...")

from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretManager
from shared.isolated_environment import get_env

    # Test staging environment
original_env = get_env().get("ENVIRONMENT)
get_env().set(ENVIRONMENT", "staging, test")

    # Clear all LLM API keys to force hard failure
get_env().delete("ANTHROPIC_API_KEY)
get_env().delete(OPENAI_API_KEY")
get_env().delete("GEMINI_API_KEY)
get_env().delete(GOOGLE_API_KEY")
get_env().delete("LLM_API_KEY)

secret_manager = UnifiedSecretManager()

try:
    secret_manager.get_llm_credentials()
raise AssertionError(Expected ValueError for missing LLM API keys")
except ValueError as e:
    assert "LLM API key required in str(e) or API_KEY" in str(e)
    print("   PASS:  Backend service properly uses central validator for LLM credentials)
finally:
                # Restore environment
if original_env:
    get_env().set(ENVIRONMENT", original_env, "test)
else:
    get_env().delete(ENVIRONMENT")


def test_central_validator_eliminates_dangerous_defaults():
    "Test that central validator eliminates dangerous empty string defaults.""
pass
print( PASS:  Testing central validator eliminates dangerous empty string defaults...")

from shared.configuration import get_central_validator
from shared.isolated_environment import get_env

    # Mock environment getter that returns None for missing values
def mock_env_getter(key, default=None):
    pass
return None  # Simulate missing environment variables

validator = get_central_validator(mock_env_getter)

    # Test staging environment hard requirements
try:
    validator._current_environment = None  # Reset cached environment
        # Temporarily set environment for validator
original_getter = validator.env_getter
validator.env_getter = lambda x: None "staging if key == ENVIRONMENT" else None

validator.validate_all_requirements()
raise AssertionError("Expected ValueError for missing critical secrets in staging)
except ValueError as e:
    error_msg = str(e)
assert JWT_SECRET_STAGING" in error_msg
assert "DATABASE_PASSWORD in error_msg
assert REDIS_PASSWORD" in error_msg
print("   PASS:  Central validator properly rejects missing critical secrets)
finally:
    validator.env_getter = original_getter


def test_development_environment_allows_defaults():
    ""Test that development environment still allows reasonable defaults."
    print(" PASS:  Testing development environment allows reasonable defaults...)

from shared.configuration import get_central_validator

    # Mock environment getter for development
def mock_dev_env_getter(key, default=None):
    if key == ENVIRONMENT":
        return "development
elif key == JWT_SECRET_KEY":
    return "development-jwt-secret-32-characters-long-12345
else:
    return default

validator = get_central_validator(mock_dev_env_getter)
validator._current_environment = None  # Reset cached environment

try:
                    # Should not raise any exceptions for development
validator.validate_all_requirements()
jwt_secret = validator.get_jwt_secret()
assert jwt_secret == development-jwt-secret-32-characters-long-12345"
print("   PASS:  Development environment properly allows reasonable defaults)
except Exception as e:
    raise AssertionError(formatted_string")


def test_services_use_same_central_validator():
    "Test that both services use the same central validator instance.""
pass
print( PASS:  Testing services use the same central validator...")

from shared.configuration import get_central_validator

    Get validator instances from different calls
validator1 = get_central_validator()
validator2 = get_central_validator()

    # Should be the same singleton instance
assert validator1 is validator2
print("   PASS:  Central validator is properly used as singleton SSOT)


def run_all_tests():
    ""Run all central validator integration tests."
    print(" ALERT:  Central Configuration Validator Integration Test Suite)
print(=" * 70)

tests = [
test_auth_service_uses_central_validator_for_jwt,
test_backend_service_uses_central_validator_for_jwt,
test_backend_service_uses_central_validator_for_database,
test_backend_service_uses_central_validator_for_redis,
test_backend_service_uses_central_validator_for_llm,
test_central_validator_eliminates_dangerous_defaults,
test_development_environment_allows_defaults,
test_services_use_same_central_validator,
    

passed = 0
failed = 0

for test in tests:
    try:
        test()
passed += 1
except Exception as e:
    print("formatted_string)
failed += 1

print(formatted_string")

if failed == 0:
    print(" PASS:  All central validator integration tests PASSED)
print( CELEBRATION:  Central configuration validator successfully integrated across all services")
return True
else:
    print(" FAIL:  Some central validator integration tests FAILED)
return False


if __name__ == __main__":
    success = run_all_tests()
sys.exit(0 if success else 1)
pass
