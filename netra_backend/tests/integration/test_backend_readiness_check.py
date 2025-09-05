"""
Integration test for backend readiness check failures during dev launcher startup.
Tests backend service health checks, database connectivity, and dependency readiness.
"""
import pytest
import requests
import asyncio
import time
from netra_backend.app.config import get_config
from shared.isolated_environment import IsolatedEnvironment


class TestBackendReadinessCheck:
    """Test backend readiness checks and identify failure points."""

    def test_backend_service_configuration(self):
        """Test backend service configuration for readiness checks."""
        config = get_config()
        
        # Check basic backend configuration
        assert hasattr(config, 'api_base_url'), "Backend API base URL missing"
        assert config.api_base_url, "Backend API base URL is empty"
        
        print(f"Backend API URL configured as: {config.api_base_url}")

    def test_backend_database_connectivity_check(self):
        """Test backend database connectivity for readiness."""
        config = get_config()
        
        # Check database URL configuration
        assert hasattr(config, 'database_url'), "Database URL missing from backend config"
        assert config.database_url, "Database URL is empty"
        
        db_url = config.database_url
        
        # Validate database URL format
        assert db_url.startswith(('postgresql://', 'postgres://', 'postgresql+asyncpg://')), \
            f"Invalid database URL format: {db_url[:30]}..."
        
        # Check for localhost (OK in development)
        if 'localhost' in db_url:
            assert config.environment == "development", \
                "Database URL contains localhost in non-development environment"
        
        print(f"Backend database URL: {db_url[:50]}...")

    def test_backend_health_endpoint_accessibility(self):
        """Test backend health endpoint for readiness checks."""
        config = get_config()
        base_url = config.api_base_url
        
        try:
            health_url = f"{base_url}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                print("Backend health endpoint is accessible")
                health_data = response.json()
                print(f"Health response: {health_data}")
                
                # Check health response format
                if isinstance(health_data, dict):
                    assert 'status' in health_data or 'health' in health_data, \
                        "Health response missing status field"
            else:
                pytest.fail(f"Backend health endpoint returned {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend service not running - expected during this test iteration")
        except requests.exceptions.Timeout:
            pytest.fail("Backend health endpoint timed out - indicates startup issues")

    def test_backend_readiness_endpoint_accessibility(self):
        """Test backend readiness endpoint specifically."""
        config = get_config()
        base_url = config.api_base_url
        
        try:
            readiness_url = f"{base_url}/ready"
            response = requests.get(readiness_url, timeout=5)
            
            if response.status_code == 200:
                print("Backend readiness endpoint is accessible")
                readiness_data = response.json()
                print(f"Readiness response: {readiness_data}")
            elif response.status_code == 503:
                # Service unavailable - backend is starting but not ready
                print("Backend is starting but not ready yet (503)")
                pytest.skip("Backend not ready - this is expected during startup")
            else:
                pytest.fail(f"Backend readiness endpoint returned {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend service not running")
        except requests.exceptions.Timeout:
            pytest.fail("Backend readiness endpoint timed out")

    def test_backend_dependency_checks(self):
        """Test backend dependency requirements for readiness."""
        config = get_config()
        
        dependencies = []
        
        # Database dependency
        if hasattr(config, 'database_url') and config.database_url:
            dependencies.append(('database', config.database_url))
        
        # Redis dependency (if configured)
        if hasattr(config, 'redis_url') and config.redis_url:
            dependencies.append(('redis', config.redis_url))
        
        # ClickHouse dependency (if enabled)
        if hasattr(config, 'clickhouse_url') and config.clickhouse_url:
            dependencies.append(('clickhouse', config.clickhouse_url))
        
        print(f"Backend dependencies configured: {[name for name, _ in dependencies]}")
        
        # At minimum should have database
        dependency_names = [name for name, _ in dependencies]
        assert 'database' in dependency_names, "Backend missing database dependency"

    def test_backend_startup_timeout_configuration(self):
        """Test backend startup timeout configuration."""
        config = get_config()
        
        # Check for startup-related configuration
        startup_config_fields = [
            'startup_max_retries',
            'startup_circuit_breaker_threshold', 
            'startup_recovery_timeout',
            'graceful_startup_mode',
            'allow_degraded_mode'
        ]
        
        startup_config = {}
        for field in startup_config_fields:
            if hasattr(config, field):
                startup_config[field] = getattr(config, field)
        
        print(f"Backend startup configuration: {startup_config}")
        
        # Should have some startup configuration
        assert startup_config, "No startup configuration found"

    def test_backend_port_availability(self):
        """Test that backend port is not blocked."""
        config = get_config()
        
        # Extract port from API base URL
        import urllib.parse
        parsed_url = urllib.parse.urlparse(config.api_base_url)
        port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 8000)
        host = parsed_url.hostname or 'localhost'
        
        print(f"Testing backend port availability: {host}:{port}")
        
        # Try to connect to the port
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                print(f"Port {port} is accessible")
                # Port is open - either backend is running or something else is using it
            else:
                print(f"Port {port} is not accessible (result: {result})")
                # This is expected if backend isn't started yet
        except socket.gaierror as e:
            pytest.fail(f"DNS resolution failed for {host}: {e}")
        finally:
            sock.close()

    def test_backend_environment_isolation_readiness(self):
        """Test backend environment isolation for readiness checks."""
        config = get_config()
        
        # Check environment-specific configuration
        if config.environment == "development":
            # Development should have debug enabled
            assert getattr(config, 'debug', False), "Debug should be enabled in development"
            
            # Development should have local-friendly URLs
            assert 'localhost' in config.api_base_url or '127.0.0.1' in config.api_base_url, \
                "Development should use localhost URLs"

    def test_backend_async_startup_issues(self):
        """Test for common async startup issues in backend."""
        # This test checks for configuration that might cause async startup issues
        config = get_config()
        
        # Check async-related configuration
        async_config = {}
        async_fields = [
            'log_async_checkout',
            'llm_cache_enabled',
            'llm_cache_ttl'
        ]
        
        for field in async_fields:
            if hasattr(config, field):
                async_config[field] = getattr(config, field)
        
        print(f"Backend async configuration: {async_config}")
        
        # Log async checkout can cause issues if enabled
        if async_config.get('log_async_checkout'):
            print("Warning: log_async_checkout is enabled - may cause verbose logging")


if __name__ == "__main__":
    # Run this test to check backend readiness issues
    pytest.main([__file__, "-v", "-s"])