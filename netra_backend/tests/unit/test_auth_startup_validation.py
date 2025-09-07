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


@pytest.mark.asyncio
async def test_auth_startup_validator_with_missing_jwt_secret():
    """Test that missing JWT secret causes validation failure."""
    with patch.dict(os.environ, {}, clear=True):
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail without JWT secret
        assert not success
        
        # Find JWT secret validation result
        jwt_result = next((r for r in results if r.component == AuthComponent.JWT_SECRET), None)
        assert jwt_result is not None
        assert not jwt_result.valid
        assert "No JWT secret configured" in jwt_result.error


@pytest.mark.asyncio
async def test_auth_startup_validator_with_valid_config():
    """Test that valid auth configuration passes validation."""
    test_env = {
        'JWT_SECRET': 'test-secret-key-that-is-long-enough-for-validation',
        'SERVICE_ID': 'netra-backend',
        'SERVICE_SECRET': 'test-service-secret-long-enough',
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
    
    with patch.dict(os.environ, test_env):
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should succeed with valid config
        assert success
        
        # All critical components should be valid
        critical_components = [
            AuthComponent.JWT_SECRET,
            AuthComponent.AUTH_SERVICE_URL,
            AuthComponent.CORS_ORIGINS
        ]
        
        for component in critical_components:
            result = next((r for r in results if r.component == component), None)
            assert result is not None
            assert result.valid, f"{component.value} should be valid"


@pytest.mark.asyncio
async def test_auth_startup_validator_production_requirements():
    """Test that production environment has stricter requirements."""
    test_env = {
        'JWT_SECRET': 'test-secret-key-that-is-long-enough-for-validation',
        'SERVICE_ID': 'netra-backend',
        'SERVICE_SECRET': 'test-service-secret-long-enough',
        'AUTH_SERVICE_URL': 'http://localhost:8001',  # HTTP in production should fail
        'FRONTEND_URL': 'http://localhost:3000',  # HTTP in production should fail
        'CORS_ALLOWED_ORIGINS': '*',  # Wildcard in production should fail
        'ENVIRONMENT': 'production'
    }
    
    with patch.dict(os.environ, test_env):
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail due to production requirements
        assert not success
        
        # Check specific production failures
        auth_url_result = next((r for r in results if r.component == AuthComponent.AUTH_SERVICE_URL), None)
        assert auth_url_result is not None
        assert not auth_url_result.valid
        assert "HTTPS" in auth_url_result.error
        
        cors_result = next((r for r in results if r.component == AuthComponent.CORS_ORIGINS), None)
        assert cors_result is not None
        assert not cors_result.valid
        assert "wildcard" in cors_result.error.lower()


@pytest.mark.asyncio
async def test_validate_auth_at_startup_raises_on_failure():
    """Test that validate_auth_at_startup raises AuthValidationError on critical failures."""
    from netra_backend.app.core.auth_startup_validator import validate_auth_at_startup
    
    with patch.dict(os.environ, {}, clear=True):  # Empty environment
        with pytest.raises(AuthValidationError) as exc_info:
            await validate_auth_at_startup()
        
        assert "Critical auth validation failures" in str(exc_info.value)


@pytest.mark.asyncio 
async def test_auth_startup_validator_oauth_validation():
    """Test OAuth configuration validation."""
    test_env = {
        'JWT_SECRET': 'test-secret-key-that-is-long-enough-for-validation',
        'ENVIRONMENT': 'development'
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
    test_env = {
        'JWT_SECRET': 'test-secret-key-that-is-long-enough-for-validation',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '2',  # Too short
        'REFRESH_TOKEN_EXPIRE_DAYS': '365',  # Too long
        'ENVIRONMENT': 'development'
    }
    
    with patch.dict(os.environ, test_env):
        validator = AuthStartupValidator()
        success, results = await validator.validate_all()
        
        # Should fail due to invalid token expiry
        token_result = next((r for r in results if r.component == AuthComponent.TOKEN_EXPIRY), None)
        assert token_result is not None
        assert not token_result.valid
        assert "too short" in token_result.error.lower()


if __name__ == "__main__":
    import asyncio
    
    # Quick test to verify validator works
    async def main():
        print("Testing auth startup validator...")
        
        # Test with minimal config
        test_env = {
            'JWT_SECRET': 'test-secret-key-that-is-long-enough-for-validation',
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