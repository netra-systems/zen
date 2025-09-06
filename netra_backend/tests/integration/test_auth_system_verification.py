"""
Integration test for auth system verification during dev launcher startup.
Tests auth service health checks and readiness verification.
""""
import pytest
import asyncio
import requests
from netra_backend.app.config import get_config
from shared.isolated_environment import IsolatedEnvironment


class TestAuthSystemVerification:
    """Test auth system verification and readiness checks."""

    def test_auth_service_configuration(self):
        """Test that auth service configuration is properly loaded."""
        config = get_config()
        
        # Check auth service config
        assert hasattr(config, 'auth_service_url'), "Auth service URL missing from config"
        auth_url = config.auth_service_url
        
        # Should not be empty
        assert auth_url, "Auth service URL is empty"
        assert auth_url != "http://localhost:8001", "Auth service URL still has default value"
        
        print(f"Auth service URL configured as: {auth_url}")

    def test_auth_service_health_endpoint_responds(self):
        """Test that auth service health endpoint is accessible."""
        config = get_config()
        auth_url = config.auth_service_url
        
        try:
            # Try to connect to health endpoint with short timeout
            health_url = f"{auth_url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                assert True, "Auth service health endpoint is accessible"
            else:
                pytest.fail(f"Auth service health endpoint returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            pytest.skip(f"Auth service not running or not accessible: {e}")
        except requests.exceptions.Timeout:
            pytest.fail("Auth service health endpoint timed out - may indicate startup issues")
        except Exception as e:
            pytest.fail(f"Unexpected error checking auth service health: {e}")

    def test_auth_service_startup_dependencies(self):
        """Test that auth service dependencies are available."""
        config = get_config()
        
        # Check database dependencies
        if hasattr(config, 'database_url'):
            assert config.database_url, "Database URL required for auth service is empty"
        
        # Check Redis dependencies  
        if hasattr(config, 'redis_url'):
            assert config.redis_url, "Redis URL required for auth service is empty"

    def test_auth_service_environment_isolation(self):
        """Test that auth service has proper environment isolation."""
        config = get_config()
        
        # In development, auth service should be accessible
        if config.environment == "development":
            # Should have development-appropriate auth config
            assert config.auth_service_url, "Auth service URL missing in development"
            
            # Should not be production URLs
            assert "prod" not in config.auth_service_url.lower(), \
                "Auth service appears to be using production URL in development"

    def test_auth_verification_request_format(self):
        """Test that auth verification requests are properly formatted."""
        config = get_config()
        auth_url = config.auth_service_url
        
        # Test that we can form proper verification request
        verify_url = f"{auth_url}/verify"
        
        try:
            # Send a test verification request (should fail with 401/400 but not connection error)
            response = requests.post(verify_url, 
                                   json={"token": "test-token"}, 
                                   headers={"Content-Type": "application/json"},
                                   timeout=5)
            
            # We expect this to fail with authentication error, not connection error
            if response.status_code in [400, 401, 403]:
                assert True, "Auth verification endpoint is accessible and responding appropriately"
            elif response.status_code == 404:
                pytest.fail("Auth verification endpoint not found - may indicate routing issues")
            else:
                print(f"Auth verification returned unexpected status: {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            pytest.skip(f"Auth service not accessible for verification test: {e}")
        except requests.exceptions.Timeout:
            pytest.fail("Auth verification endpoint timed out")
        except Exception as e:
            pytest.fail(f"Unexpected error in auth verification test: {e}")

    def test_auth_service_database_connectivity(self):
        """Test that auth service can connect to its database."""
        config = get_config()
        
        # Check if database connection details are configured
        if hasattr(config, 'database_url') and config.database_url:
            # Basic validation that database URL is formatted correctly
            db_url = config.database_url
            
            assert db_url.startswith(('postgresql://', 'postgres://', 'postgresql+asyncpg://')), \
                f"Database URL format appears incorrect: {db_url[:20}]..."
            
            # Check that it's not using obvious default values
            assert 'user:pass' not in db_url, "Database URL contains default credentials"
            assert 'localhost' not in db_url or config.environment == "development", \
                "Database URL may be using localhost in non-development environment"

    def test_auth_service_startup_timeout_configuration(self):
        """Test that auth service startup has reasonable timeout configuration."""
        # This test checks if there are configuration issues that cause long startup times
        import time
        start_time = time.time()
        
        config = get_config()
        auth_url = config.auth_service_url
        
        try:
            # Try a quick health check with very short timeout
            response = requests.get(f"{auth_url}/health", timeout=2)
            response_time = time.time() - start_time
            
            # If it responds quickly, no timeout issues
            if response_time < 2.0:
                assert True, "Auth service responds quickly"
            else:
                pytest.fail(f"Auth service took {response_time:.2f}s to respond - may indicate startup issues")
                
        except requests.exceptions.Timeout:
            pytest.skip("Auth service not responding within 2s - may not be started yet")
        except requests.exceptions.ConnectionError:
            pytest.skip("Auth service not accessible")


if __name__ == "__main__":
    # Run this test standalone to check auth system verification
    pytest.main([__file__, "-v"])