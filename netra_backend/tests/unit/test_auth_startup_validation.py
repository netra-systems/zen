"""
Test auth startup validation to ensure SSOT auth checks work correctly.
"""

import pytest
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from unittest.mock import patch, MagicMock
from netra_backend.app.core.auth_startup_validator import (
    AuthStartupValidator,
    AuthValidationError,
    AuthComponent
)
from shared.jwt_secret_manager import get_jwt_secret_manager


@pytest.mark.asyncio
async def test_auth_startup_validator_with_missing_jwt_secret():
    """Test that missing JWT secret causes validation failure."""
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    # Use isolated environment to truly clear variables
    from shared.isolated_environment import get_env
    env = get_env()
    env.enable_isolation()
    
    # Clear all JWT-related variables and set minimal environment
    env.set('ENVIRONMENT', 'development', 'test')
    env.delete('JWT_SECRET')
    env.delete('JWT_SECRET_KEY')
    env.delete('JWT_SECRET_STAGING')
    env.delete('AUTH_SERVICE_URL')  # Also clear this to avoid other critical failures
    
    try:
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail without JWT secret
        assert not success
        
        # Find JWT secret validation result
        jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
        assert jwt_result is not None
        assert not jwt_result.valid
        assert "No JWT secret configured" in jwt_result.error
        
    finally:
        env.disable_isolation()
        get_jwt_secret_manager().clear_cache()


@pytest.mark.asyncio
async def test_auth_startup_validator_with_valid_config():
    """Test that valid auth configuration passes validation."""
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    # Use isolated environment to properly set values
    from shared.isolated_environment import get_env
    env = get_env()
    env.enable_isolation()
    
    # Set valid configuration
    test_vars = {
        'JWT_SECRET_KEY': 'a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab',
        'SERVICE_ID': 'netra-backend',
        'SERVICE_SECRET': '9f8e7d6c5b4a3210fedcba9876543210fedcba9876543210fedcba9876543210ab',
        'AUTH_SERVICE_URL': 'http://localhost:8001',
        'GOOGLE_CLIENT_ID': 'test-google-id',
        'GOOGLE_CLIENT_SECRET': 'test-google-secret',
        'CORS_ALLOWED_ORIGINS': 'http://localhost:3000',
        'FRONTEND_URL': 'http://localhost:3000',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
        'REFRESH_TOKEN_EXPIRE_DAYS': '7',
        'AUTH_CIRCUIT_FAILURE_THRESHOLD': '3',
        'AUTH_CIRCUIT_TIMEOUT': '30',
        'AUTH_CACHE_TTL': '300',
        'AUTH_CACHE_ENABLED': 'true',
        'ENVIRONMENT': 'development'
    }
    
    # Clear any existing JWT keys that might interfere  
    env.delete('JWT_SECRET_KEY')
    env.delete('JWT_SECRET_DEVELOPMENT')
    env.delete('JWT_SECRET_STAGING')
    
    for key, value in test_vars.items():
        env.set(key, value, 'test')
    
    try:
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should succeed with valid config
        assert success, f"Validation failed with results: {[(r.component.value, r.error) for r in results if not r.valid]}"
        
        # All critical components should be valid
        critical_components = [
            AuthComponent.JWT_SECRET,
            AuthComponent.AUTH_SERVICE_URL,
            AuthComponent.CORS_ORIGINS
        ]
        
        for component in critical_components:
            result = next((r for r in results if r.component == component), None)
            assert result is not None
            assert result.valid, f"{component.value} should be valid but got error: {result.error if result else 'Not found'}"
            
    finally:
        env.disable_isolation()
        get_jwt_secret_manager().clear_cache()


@pytest.mark.asyncio
async def test_auth_startup_validator_production_requirements():
    """Test that production environment has stricter requirements."""
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    # Use isolated environment to properly set values
    from shared.isolated_environment import get_env
    env = get_env()
    env.enable_isolation()
    
    # Set production configuration with violations
    test_vars = {
        'JWT_SECRET_KEY': 'a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab',
        'SERVICE_ID': 'netra-backend',
        'SERVICE_SECRET': '9f8e7d6c5b4a3210fedcba9876543210fedcba9876543210fedcba9876543210ab',
        'AUTH_SERVICE_URL': 'http://localhost:8001',  # HTTP in production should fail
        'FRONTEND_URL': 'http://localhost:3000',  # HTTP in production should fail
        'CORS_ALLOWED_ORIGINS': '*',  # Wildcard in production should fail
        'ENVIRONMENT': 'production'
    }
    
    # Clear testing flags to force production environment detection
    env.delete('TESTING')
    env.delete('PYTEST_CURRENT_TEST')
    
    for key, value in test_vars.items():
        env.set(key, value, 'test')
    
    try:
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail due to production requirements
        assert not success, f"Production validation should fail but passed with results: {[(r.component.value, r.valid, r.error) for r in results]}"
        
        # Check specific production failures - look for HTTPS requirement failures
        failed_results = [r for r in results if not r.valid]
        
        # Should have HTTPS validation failures
        https_failures = [r for r in failed_results if r.error and "HTTPS" in r.error]
        assert len(https_failures) > 0, f"Expected HTTPS validation failures but got: {[(r.component.value, r.error) for r in failed_results]}"
        
        # Check CORS failure (could be wildcard or frontend URL mismatch in production)
        cors_result = next((r for r in results if r.component == AuthComponent.CORS_ORIGINS), None)
        assert cors_result is not None
        assert not cors_result.valid
        assert cors_result.error in ["CORS wildcard (*) not allowed in production", "FRONTEND_URL not in CORS_ALLOWED_ORIGINS"]
        
    finally:
        env.disable_isolation()
        get_jwt_secret_manager().clear_cache()


@pytest.mark.asyncio
async def test_validate_auth_at_startup_raises_on_failure():
    """Test that validate_auth_at_startup raises AuthValidationError on critical failures."""
    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
    
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'TESTING': '', 'PYTEST_CURRENT_TEST': ''}, clear=True):  # Minimal environment
        with pytest.raises(AuthValidationError) as exc_info:
            await validate_auth_at_startup()
        
        assert "Critical auth validation failures" in str(exc_info.value)


@pytest.mark.asyncio 
async def test_auth_startup_validator_oauth_validation():
    """Test OAuth configuration validation."""
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    test_env = {
        'JWT_SECRET_KEY': 'a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab',
        'ENVIRONMENT': 'development',
        'TESTING': '',
        'PYTEST_CURRENT_TEST': ''
    }
    
    with patch.dict(os.environ, test_env):
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should have warning about no OAuth providers
        oauth_result = next((r for r in results if r.component == AuthComponent.OAUTH_CREDENTIALS), None)
        assert oauth_result is not None
        assert not oauth_result.valid
        assert "No OAuth providers configured" in oauth_result.error
        
        # In development, this should not be critical
        assert not oauth_result.is_critical


@pytest.mark.asyncio
async def test_auth_startup_validator_token_expiry():
    """Test token expiry configuration validation."""
    # Clear JWT secret manager cache before test
    get_jwt_secret_manager().clear_cache()
    
    # Use isolated environment to properly set values
    from shared.isolated_environment import get_env
    env = get_env()
    env.enable_isolation()
    
    # Set configuration with invalid token expiry
    test_vars = {
        'JWT_SECRET_KEY': 'a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '2',  # Too short
        'REFRESH_TOKEN_EXPIRE_DAYS': '365',  # Too long
        'ENVIRONMENT': 'development'
    }
    
    # Clear any existing JWT keys that might interfere  
    env.delete('JWT_SECRET_KEY')
    env.delete('JWT_SECRET_DEVELOPMENT')
    env.delete('JWT_SECRET_STAGING')
    
    for key, value in test_vars.items():
        env.set(key, value, 'test')
    
    try:
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail due to invalid token expiry
        token_result = next((r for r in results if r.component == AuthComponent.TOKEN_EXPIRY), None)
        assert token_result is not None
        assert not token_result.valid, f"Token expiry should be invalid but got: {token_result.error}"
        assert "too short" in token_result.error.lower()
        
    finally:
        env.disable_isolation()
        get_jwt_secret_manager().clear_cache()


if __name__ == "__main__":
    import asyncio
    
    # Quick test to verify validator works
    async def main():
        print("Testing auth startup validator...")
        
        # Test with minimal config
        test_env = {
            'JWT_SECRET_KEY': 'a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab',
            'ENVIRONMENT': 'development'
        }
        
        with patch.dict(os.environ, test_env):
            validator = AuthStartupValidator()
            success, results = await validator.validate_all()
            
            print(f"\nValidation {'PASSED' if success else 'FAILED'}")
            print(f"Total checks: {len(results)}")
            print(f"Passed: {len([r for r in results if r.valid])}")
            print(f"Failed: {len([r for r in results if not r.valid])}")
            
            if not success:
                print("\nCritical failures:")
                for r in results:
                    if not r.valid and r.is_critical:
                        print(f"  - {r.component.value}: {r.error}")
    
    asyncio.run(main())