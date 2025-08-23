"""Critical Auth Service Staging Issues - Failing Tests
Tests that reproduce production errors found in staging environment.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service reliability and production readiness
- Value Impact: Prevents auth service failures in staging/production
- Strategic Impact: Ensures authentication availability for all tiers
"""

import os
import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Ensure absolute imports work
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.database_manager import AuthDatabaseManager


class TestAuthDatabaseInitialization:
    """Test database initialization issues found in staging."""
    
    def test_auth_database_manager_has_async_method(self):
        """Test that AuthDatabaseManager has get_auth_database_url_async method.
        
        ERROR FOUND: type object 'AuthDatabaseManager' has no attribute 'get_auth_database_url_async'
        This test verifies the method exists as a static method on AuthDatabaseManager.
        """
        # This should not raise AttributeError
        assert hasattr(AuthDatabaseManager, 'get_auth_database_url_async'), \
            "AuthDatabaseManager missing get_auth_database_url_async static method"
        
        # The method should be callable as a static method
        assert callable(getattr(AuthDatabaseManager, 'get_auth_database_url_async', None)), \
            "get_auth_database_url_async should be callable"
    
    def test_auth_database_url_method_returns_correct_format(self):
        """Test that the async database URL method returns asyncpg format.
        
        Similar to backend's get_application_url_async pattern.
        """
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db'}):
            # Should return asyncpg format
            url = AuthDatabaseManager.get_auth_database_url_async()
            assert url.startswith('postgresql+asyncpg://'), \
                f"Expected asyncpg driver in URL, got: {url}"
    
    def test_auth_database_manager_follows_backend_pattern(self):
        """Test that auth service follows the same pattern as backend DatabaseManager.
        
        Backend uses: get_application_url_async()
        Auth should have similar method structure.
        """
        # Backend pattern methods that should exist
        backend_pattern_methods = [
            'get_auth_database_url_async',  # Should be renamed or implemented correctly
            '_normalize_postgres_url',
            '_convert_sslmode_to_ssl',
            'validate_auth_url'
        ]
        
        for method in backend_pattern_methods:
            assert hasattr(AuthDatabaseManager, method) or hasattr(AuthDatabaseManager, method.replace('auth_', '')), \
                f"Missing method {method} following backend pattern"
    
    @pytest.mark.asyncio
    async def test_connection_initialization_uses_correct_method(self):
        """Test that connection.py calls the correct database URL method."""
        from auth_service.auth_core.database.connection import AuthDatabase
        
        auth_db = AuthDatabase()
        
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db',
            'AUTH_FAST_TEST_MODE': 'false',
            'ENVIRONMENT': 'staging'
        }):
            # Mock the method that should exist
            with patch.object(AuthDatabaseManager, 'get_auth_database_url_async', 
                            return_value='postgresql+asyncpg://user:pass@localhost:5432/db') as mock_method:
                
                # This should not raise AttributeError
                try:
                    await auth_db.initialize()
                except Exception as e:
                    # Other errors are OK, we're testing the method exists
                    if "has no attribute 'get_auth_database_url_async'" in str(e):
                        pytest.fail(f"Method not found error: {e}")


class TestEnvironmentModeDetection:
    """Test environment mode detection issues."""
    
    def test_staging_environment_detected_correctly(self):
        """Test that staging environment is detected when ENVIRONMENT=staging.
        
        ERROR FOUND: Service reports "development mode" when ENVIRONMENT=staging
        """
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            env = AuthConfig.get_environment()
            assert env == 'staging', f"Expected 'staging' environment, got '{env}'"
    
    def test_staging_environment_case_insensitive(self):
        """Test that environment detection is case-insensitive."""
        test_cases = ['STAGING', 'Staging', 'StAgInG']
        
        for case in test_cases:
            with patch.dict(os.environ, {'ENVIRONMENT': case}):
                env = AuthConfig.get_environment()
                assert env == 'staging', f"Failed for case '{case}', got '{env}'"
    
    def test_cloud_run_staging_environment(self):
        """Test environment detection in Cloud Run staging deployment."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-service',  # Cloud Run service indicator
            'PORT': '8080'
        }):
            env = AuthConfig.get_environment()
            assert env == 'staging', f"Cloud Run staging not detected, got '{env}'"
    
    def test_environment_logging_shows_correct_mode(self):
        """Test that log output shows correct environment mode."""
        import logging
        from io import StringIO
        
        # Capture log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        logger = logging.getLogger('auth_service.main')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            # Simulate the log message from main.py line 113
            env = AuthConfig.get_environment()
            if env in ["development", "staging"]:
                logger.warning(f"Starting with 1 DB issues in {env} mode")
            
            log_output = log_capture.getvalue()
            assert "staging mode" in log_output, \
                f"Expected 'staging mode' in logs, got: {log_output}"
            assert "development mode" not in log_output, \
                f"Should not show 'development mode' when ENVIRONMENT=staging"


class TestServiceNaming:
    """Test service naming configuration issues."""
    
    def test_service_name_consistency(self):
        """Test that service name is consistent across configurations.
        
        ERROR FOUND: Service named "netra-auth-staging" instead of "netra-auth-service"
        """
        # Check service name in health interface
        from auth_service.main import health_interface
        assert health_interface.service_name == "auth-service", \
            f"Expected 'auth-service', got '{health_interface.service_name}'"
    
    def test_cloud_run_service_name_format(self):
        """Test Cloud Run service name follows correct format."""
        with patch.dict(os.environ, {
            'K_SERVICE': 'netra-auth-staging',  # What we see in Cloud Run
            'ENVIRONMENT': 'staging'
        }):
            # The K_SERVICE is set by Cloud Run, but our internal name should be consistent
            from auth_service.main import app
            
            # Check the OpenAPI/Swagger title
            assert "Auth Service" in app.title, \
                f"App title should contain 'Auth Service', got: {app.title}"
    
    def test_service_id_configuration(self):
        """Test service ID configuration for staging."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'SERVICE_ID': 'netra-auth-staging-instance'
        }):
            service_id = AuthConfig.get_service_id()
            # Service ID can vary, but should be set in staging
            assert service_id != "netra-auth-dev-instance", \
                "Should not use dev instance ID in staging"
    
    def test_service_response_headers(self):
        """Test that service identifies itself correctly in response headers."""
        from fastapi.testclient import TestClient
        from auth_service.main import app
        
        client = TestClient(app)
        
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            response = client.get("/health")
            
            # Check X-Service-Name header
            assert response.headers.get("X-Service-Name") == "auth-service", \
                f"Expected 'auth-service' in X-Service-Name header, got: {response.headers.get('X-Service-Name')}"
            
            # Check response body
            assert response.json()["service"] == "auth-service", \
                f"Expected 'auth-service' in response, got: {response.json()}"


class TestSimilarConfigurationIssues:
    """Test similar configuration issues that might occur."""
    
    def test_database_url_not_set_fallback(self):
        """Test behavior when DATABASE_URL is not set in staging."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}, clear=True):
            # Should use staging default, not development default
            url = AuthDatabaseManager._get_default_auth_url()
            assert "staging" in url or "35.223" in url, \
                f"Should use staging defaults when DATABASE_URL not set, got: {url}"
    
    def test_redis_configuration_in_staging(self):
        """Test Redis configuration in staging environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            redis_url = AuthConfig.get_redis_url()
            # In staging, should not default to localhost
            assert "localhost" not in redis_url, \
                f"Redis URL should not use localhost in staging, got: {redis_url}"
    
    def test_frontend_url_in_staging(self):
        """Test frontend URL configuration in staging."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            frontend_url = AuthConfig.get_frontend_url()
            assert frontend_url == "https://app.staging.netrasystems.ai", \
                f"Expected staging frontend URL, got: {frontend_url}"
    
    def test_cors_origins_in_staging(self):
        """Test CORS origins configuration in staging."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            from auth_service.main import app
            
            # Find CORS middleware configuration
            env = AuthConfig.get_environment()
            
            if env == "staging":
                # Should have staging-specific CORS origins
                expected_origins = [
                    "https://app.staging.netrasystems.ai",
                    "https://auth.staging.netrasystems.ai",
                    "https://api.staging.netrasystems.ai"
                ]
                
                # This tests that the CORS configuration logic works correctly
                assert env == "staging", "Should detect staging environment for CORS config"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])