"""
Test-Driven Correction (TDC) Tests for Staging External Service Dependencies

Tests the specific ClickHouse and Redis connectivity issues found in staging audit.
These are FAILING tests designed to expose the exact issues preventing staging readiness.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Platform Stability - ensure external services are properly validated in staging
- Value Impact: Prevents service degradation by ensuring external dependencies are required not optional
- Strategic Impact: Critical for staging environment reliability and production readiness validation

Issues Found in Audit:
1. ClickHouse: Connection timeouts to clickhouse.staging.netrasystems.ai:8123 causing 503 on /health/ready
2. Redis: Connections fail but service falls back to no-Redis mode instead of failing fast

Expected Test Results:
- All tests in this file SHOULD FAIL initially to demonstrate the issues
- After fixes, these same tests should PASS to validate the solutions
"""

import pytest
import asyncio
import socket
import time
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, Optional

from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.config import get_config

# These imports may fail if services aren't properly configured - that's part of what we're testing
try:
    from netra_backend.app.db.clickhouse import ClickHouseService
    from netra_backend.app.redis_manager import RedisManager
except ImportError as e:
    ClickHouseService = None  
    RedisManager = None
    print(f"Warning: Could not import services for testing: {e}")


@pytest.mark.env("staging")
class TestStagingClickHouseConnectivity:
    """Test suite for ClickHouse connectivity issues in staging environment."""

    @pytest.mark.critical  
    @pytest.mark.asyncio
    async def test_clickhouse_host_dns_resolution_fails(self):
        """
        FAILING TEST: ClickHouse DNS resolution for staging host.
        
        Tests that clickhouse.staging.netrasystems.ai can be resolved.
        Expected failure: DNS resolution timeout or host not found.
        """
        staging_host = "clickhouse.staging.netrasystems.ai"
        
        try:
            # Test DNS resolution
            resolved_ip = socket.gethostbyname(staging_host)
            
            # If we get here, DNS works but connection might not
            assert resolved_ip != "127.0.0.1", f"ClickHouse host {staging_host} resolves to localhost, indicating DNS issues"
            
            # Test actual connectivity to the resolved IP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                result = sock.connect_ex((resolved_ip, 8123))
                if result != 0:
                    pytest.fail(f"ClickHouse port 8123 not accessible on {resolved_ip} (resolved from {staging_host})")
            finally:
                sock.close()
                
        except socket.gaierror as e:
            pytest.fail(f"ClickHouse DNS resolution failed for {staging_host}: {e}")
        except socket.timeout:
            pytest.fail(f"ClickHouse DNS resolution timeout for {staging_host}")

    @pytest.mark.critical
    @pytest.mark.asyncio  
    async def test_clickhouse_port_connectivity_fails(self):
        """
        FAILING TEST: Direct network connectivity to ClickHouse port 8123.
        
        Tests that port 8123 is accessible on the ClickHouse staging host.
        Expected failure: Connection refused or timeout.
        """
        config = get_config()
        
        # Try to get ClickHouse config
        try:
            ch_config = config.clickhouse_https
            host = getattr(ch_config, 'host', 'clickhouse.staging.netrasystems.ai')
            port = getattr(ch_config, 'port', 8123)
        except AttributeError:
            host = 'clickhouse.staging.netrasystems.ai'
            port = 8123
        
        # Test direct TCP connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        sock.settimeout(10)  # 10 second timeout
        
        try:
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()
            
            if result != 0:
                connect_time = end_time - start_time
                pytest.fail(f"ClickHouse connection failed to {host}:{port} after {connect_time:.2f}s - Connection refused or host unreachable")
                
        except socket.gaierror as e:
            pytest.fail(f"ClickHouse host resolution failed: {e}")
        except socket.timeout:
            pytest.fail(f"ClickHouse connection timeout to {host}:{port}")
        finally:
            sock.close()

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_service_initialization_fails(self):
        """
        FAILING TEST: ClickHouse service initialization with real staging config.
        
        Tests that ClickHouse service can initialize and connect with staging credentials.
        Expected failure: Connection timeout, authentication failure, or service unavailable.
        """
        if ClickHouseService is None:
            pytest.skip("ClickHouse service not available for testing")
        
        # Get real configuration
        config = get_config()
        
        # Ensure we're testing with real staging config, not fallbacks
        env = IsolatedEnvironment()
        environment = env.get("ENVIRONMENT", "development")
        
        if environment == "development":
            pytest.skip("Test requires staging environment configuration")
        
        try:
            # Attempt to create and initialize ClickHouse service
            clickhouse_service = ClickHouseService()
            
            # This should fail if ClickHouse isn't properly configured or accessible
            await clickhouse_service.ping()
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Categorize the failure to understand the root cause
            if 'timeout' in error_msg:
                pytest.fail(f"ClickHouse connection timeout - service unavailable: {e}")
            elif 'authentication' in error_msg or 'password' in error_msg:
                pytest.fail(f"ClickHouse authentication failure - check credentials: {e}")  
            elif 'connection' in error_msg or 'refused' in error_msg:
                pytest.fail(f"ClickHouse connection refused - service not running: {e}")
            elif 'dns' in error_msg or 'resolve' in error_msg:
                pytest.fail(f"ClickHouse DNS resolution failure - check hostname: {e}")
            else:
                pytest.fail(f"ClickHouse unexpected initialization failure: {e}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_health_endpoint_dependency_fails(self):
        """
        FAILING TEST: Health endpoint dependency on ClickHouse.
        
        Tests that /health/ready returns 503 when ClickHouse is unavailable.
        Expected failure: Health endpoint returns healthy when ClickHouse is down (inappropriate fallback).
        """
        from fastapi.testclient import TestClient
        from netra_backend.app.main import app
        
        # Mock ClickHouse to simulate connection failure
        with patch('netra_backend.app.db.clickhouse.ClickHouseService') as mock_ch:
            mock_instance = AsyncMock()
            mock_ch.return_value = mock_instance
            
            # Simulate ClickHouse connection timeout
            mock_instance.ping.side_effect = asyncio.TimeoutError("Connection to ClickHouse timed out")
            
            client = TestClient(app)
            
            # Health/ready should return 503 when ClickHouse is unavailable
            response = client.get("/health/ready")
            
            # This test SHOULD FAIL if health endpoint doesn't properly check ClickHouse
            if response.status_code == 200:
                response_data = response.json() 
                pytest.fail(f"Health endpoint reports ready when ClickHouse unavailable. Response: {response_data}")
            
            # Expected behavior: 503 status code when external dependencies fail
            assert response.status_code == 503, f"Expected 503 when ClickHouse unavailable, got {response.status_code}"

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_configuration_validation_fails(self):
        """
        FAILING TEST: ClickHouse configuration completeness in staging.
        
        Tests that all required ClickHouse configuration is present and valid.
        Expected failure: Missing or invalid configuration values.
        """
        config = get_config()
        env = IsolatedEnvironment()
        
        # Test required configuration exists
        assert hasattr(config, 'clickhouse_https'), "ClickHouse configuration section missing"
        
        ch_config = config.clickhouse_https
        
        # Test each required field (note: ClickHouse config uses 'user' not 'username')
        required_fields = ['host', 'port', 'user', 'password'] 
        for field in required_fields:
            assert hasattr(ch_config, field), f"ClickHouse {field} configuration missing"
            
            value = getattr(ch_config, field)
            if field in ['host', 'user']:  # These should never be empty
                assert value and str(value).strip(), f"ClickHouse {field} is empty or whitespace: '{value}'"
        
        # Test for staging-specific values (not localhost/development defaults)
        assert ch_config.host != "localhost", "ClickHouse still using localhost in staging"
        assert ch_config.host != "127.0.0.1", "ClickHouse still using 127.0.0.1 in staging"
        assert "staging" in ch_config.host or "netrasystems" in ch_config.host, f"ClickHouse host doesn't appear to be staging: {ch_config.host}"
        
        # Test port is reasonable
        assert isinstance(ch_config.port, (int, str)), f"ClickHouse port should be int or string, got {type(ch_config.port)}"
        port_num = int(ch_config.port)
        assert 1024 <= port_num <= 65535, f"ClickHouse port {port_num} outside valid range"

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_clickhouse_timeout_handling_fails(self):
        """
        FAILING TEST: ClickHouse timeout handling in staging environment.
        
        Tests that ClickHouse operations have appropriate timeout handling.
        Expected failure: Operations hang indefinitely or don't handle timeouts gracefully.
        """
        if ClickHouseService is None:
            pytest.skip("ClickHouse service not available for testing")
        
        # Test with artificial timeout to simulate staging connectivity issues
        with patch('netra_backend.app.db.clickhouse._create_real_client') as mock_client:
            async def mock_generator():
                mock_instance = AsyncMock()
                # Simulate long timeout that exceeds reasonable limits
                mock_instance.execute.side_effect = asyncio.TimeoutError("ClickHouse query timeout after 30s")
                yield mock_instance
            
            mock_client.return_value = mock_generator()
            
            clickhouse_service = ClickHouseService()
            
            start_time = time.time()
            try:
                # This should fail quickly with timeout, not hang
                await asyncio.wait_for(clickhouse_service.ping(), timeout=15.0)
                elapsed = time.time() - start_time
                
                # If we get here, the timeout wasn't handled properly
                pytest.fail(f"ClickHouse operation completed when timeout expected, took {elapsed:.2f}s")
                
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                # Timeout should happen reasonably quickly (< 15s)
                if elapsed > 20:
                    pytest.fail(f"ClickHouse timeout took too long: {elapsed:.2f}s (should be < 15s)")


@pytest.mark.env("staging") 
class TestStagingRedisConnectivity:
    """Test suite for Redis connectivity issues in staging environment."""

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_redis_service_not_provisioned_fails(self):
        """
        FAILING TEST: Redis service provisioning in staging.
        
        Tests that Redis service is actually provisioned and running in staging.
        Expected failure: Redis service not provisioned or not running.
        """
        # Get Redis configuration
        env = IsolatedEnvironment()
        redis_url = env.get("REDIS_URL")
        
        if not redis_url:
            pytest.fail("REDIS_URL not configured in staging environment")
        
        # Parse Redis URL to get host and port
        if redis_url.startswith("redis://"):
            # Extract host and port from redis://host:port format
            url_parts = redis_url[8:].split(":")
            if len(url_parts) >= 2:
                host = url_parts[0]
                try:
                    port = int(url_parts[1].split("/")[0])  # Handle /db suffix
                except (ValueError, IndexError):
                    port = 6379
            else:
                host = url_parts[0]
                port = 6379
        else:
            pytest.fail(f"Invalid Redis URL format: {redis_url}")
        
        # Test TCP connectivity to Redis
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        try:
            result = sock.connect_ex((host, port))
            if result != 0:
                pytest.fail(f"Redis service not accessible at {host}:{port} - service may not be provisioned")
        except socket.gaierror as e:
            pytest.fail(f"Redis host resolution failed for {host}: {e}")
        finally:
            sock.close()

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_redis_fallback_mode_inappropriately_enabled_fails(self):
        """
        FAILING TEST: Redis fallback to no-Redis mode in staging.
        
        Tests that Redis failures cause the service to fail fast, not fall back to no-Redis mode.
        Expected failure: Service falls back to no-Redis mode instead of failing.
        """
        if RedisManager is None:
            pytest.skip("Redis manager not available for testing")
        
        # Mock Redis to simulate connection failure
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_instance = AsyncMock()
            mock_redis_class.return_value = mock_redis_instance
            
            # Simulate Redis connection failure
            mock_redis_instance.ping.side_effect = ConnectionError("Redis service unavailable")
            
            redis_manager = RedisManager()
            
            # In staging, Redis failures should NOT be tolerated with fallback
            try:
                await redis_manager.connect()
                
                # If connection "succeeds" but Redis is unavailable, that's inappropriate fallback
                if hasattr(redis_manager, 'enabled') and not redis_manager.enabled:
                    pytest.fail("Redis manager enabled fallback mode instead of failing fast in staging")
                
                # Test that operations actually require Redis
                try:
                    await redis_manager.set("test_key", "test_value")
                    # If this succeeds when Redis is down, we have inappropriate fallback
                    pytest.fail("Redis operations succeeded when Redis unavailable - inappropriate fallback enabled")
                except Exception:
                    # This is expected - operations should fail when Redis is down
                    pass
                    
            except ConnectionError:
                # This is the expected behavior in staging - fail fast
                pass

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_redis_health_check_dependency_fails(self):
        """
        FAILING TEST: Health check dependency on Redis in staging.
        
        Tests that health endpoints properly reflect Redis unavailability.
        Expected failure: Health checks report healthy when Redis is unavailable.
        """
        from fastapi.testclient import TestClient
        from netra_backend.app.main import app
        
        # Mock Redis to simulate unavailability
        with patch('netra_backend.app.redis_manager.RedisManager') as mock_redis_manager:
            mock_instance = MagicMock()
            mock_redis_manager.return_value = mock_instance
            
            # Simulate Redis unavailable
            mock_instance.connect.side_effect = ConnectionError("Redis unavailable")
            mock_instance.enabled = False
            
            client = TestClient(app)
            
            # Health/ready should reflect Redis unavailability in staging
            response = client.get("/health/ready")
            
            # In staging, Redis unavailability should affect readiness
            if response.status_code == 200:
                response_data = response.json()
                
                # Check if Redis status is properly reported
                if 'components' in response_data:
                    redis_status = None
                    for component in response_data.get('components', []):
                        if 'redis' in component.get('name', '').lower():
                            redis_status = component.get('status')
                            break
                    
                    if redis_status == 'healthy':
                        pytest.fail("Health check reports Redis healthy when unavailable")
                else:
                    # If no component details, check overall status
                    pytest.fail(f"Health check may not be validating Redis dependency: {response_data}")

    @pytest.mark.critical 
    @pytest.mark.asyncio
    async def test_redis_authentication_failure_handling_fails(self):
        """
        FAILING TEST: Redis authentication in staging environment.
        
        Tests that Redis authentication is properly configured and handled.
        Expected failure: Authentication failures or missing credentials.
        """
        env = IsolatedEnvironment()
        redis_url = env.get("REDIS_URL", "")
        
        # Check if Redis URL includes authentication
        if "@" not in redis_url and "redis://" in redis_url:
            # No authentication in URL, check for separate auth config
            redis_password = env.get("REDIS_PASSWORD")
            if not redis_password:
                pytest.fail("Redis URL has no authentication and no REDIS_PASSWORD configured")
        
        if RedisManager is None:
            pytest.skip("Redis manager not available for testing")
        
        # Test with invalid credentials to verify auth is required
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_instance = AsyncMock()
            mock_redis_class.return_value = mock_redis_instance
            
            # Simulate authentication failure
            mock_redis_instance.ping.side_effect = ConnectionError("WRONGPASS invalid username-password pair")
            
            redis_manager = RedisManager()
            
            try:
                await redis_manager.connect()
                pytest.fail("Redis connection succeeded with invalid credentials - authentication not enforced")
            except ConnectionError as e:
                if "WRONGPASS" in str(e) or "authentication" in str(e).lower():
                    # This is expected - authentication is being enforced
                    pass
                else:
                    pytest.fail(f"Redis connection failed for unexpected reason: {e}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_redis_connection_timeout_staging_fails(self):
        """
        FAILING TEST: Redis connection timeout in staging environment.
        
        Tests that Redis connections have appropriate timeout handling.
        Expected failure: Connections hang or take too long to timeout.
        """
        if RedisManager is None:
            pytest.skip("Redis manager not available for testing")
        
        # Test with simulated network timeout
        with patch('redis.asyncio.Redis') as mock_redis_class:
            mock_redis_instance = AsyncMock() 
            mock_redis_class.return_value = mock_redis_instance
            
            # Simulate long connection timeout
            async def slow_ping():
                await asyncio.sleep(30)  # 30 second delay
                return True
                
            mock_redis_instance.ping.side_effect = slow_ping
            
            redis_manager = RedisManager()
            
            start_time = time.time()
            try:
                # Connection should timeout quickly, not wait 30 seconds
                await asyncio.wait_for(redis_manager.connect(), timeout=10.0)
                elapsed = time.time() - start_time
                
                if elapsed > 15:
                    pytest.fail(f"Redis connection took too long: {elapsed:.2f}s (should timeout < 10s)")
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                # Timeout should happen within reasonable time
                if elapsed > 15:
                    pytest.fail(f"Redis timeout took too long: {elapsed:.2f}s (should be < 10s)")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_redis_operations_require_connection_fails(self):
        """
        FAILING TEST: Redis operations when connection unavailable.
        
        Tests that Redis operations fail appropriately when connection is unavailable.
        Expected failure: Operations succeed with fallback when they should fail.
        """
        if RedisManager is None:
            pytest.skip("Redis manager not available for testing")
        
        redis_manager = RedisManager()
        
        # Don't connect Redis, ensure it's not available
        redis_manager.redis_client = None
        redis_manager.enabled = False
        
        # Operations should fail when Redis unavailable in staging
        operations_to_test = [
            ("get", ("test_key",)),
            ("set", ("test_key", "test_value")),
            ("delete", ("test_key",)),
            ("exists", ("test_key",)),
        ]
        
        for operation_name, args in operations_to_test:
            if hasattr(redis_manager, operation_name):
                operation = getattr(redis_manager, operation_name)
                
                try:
                    result = await operation(*args)
                    
                    # If operation succeeds when Redis unavailable, that's inappropriate fallback
                    if result is not None:
                        pytest.fail(f"Redis {operation_name} succeeded when connection unavailable - inappropriate fallback")
                        
                except Exception:
                    # This is expected - operations should fail when Redis unavailable
                    pass


@pytest.mark.env("staging")
class TestStagingExternalServiceIntegration:
    """Integration tests for external service dependencies in staging."""

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_external_services_required_not_optional_fails(self):
        """
        FAILING TEST: External services should be required in staging, not optional.
        
        Tests that both ClickHouse and Redis are treated as required dependencies.
        Expected failure: Services start in degraded mode when external services unavailable.
        """
        from fastapi.testclient import TestClient
        from netra_backend.app.main import app
        
        # Mock both external services as unavailable
        with patch('netra_backend.app.db.clickhouse.ClickHouseService') as mock_ch:
            with patch('netra_backend.app.redis_manager.RedisManager') as mock_redis:
                
                mock_ch_instance = AsyncMock()
                mock_ch.return_value = mock_ch_instance
                mock_ch_instance.ping.side_effect = ConnectionError("ClickHouse unavailable")
                
                mock_redis_instance = MagicMock()
                mock_redis.return_value = mock_redis_instance
                mock_redis_instance.connect.side_effect = ConnectionError("Redis unavailable")
                
                client = TestClient(app)
                
                # Application startup should fail or return degraded status
                response = client.get("/health/ready")
                
                # In staging, unavailable external services should prevent readiness
                if response.status_code == 200:
                    response_data = response.json()
                    pytest.fail(f"Service reports ready when external services unavailable: {response_data}")
                
                # Expected: 503 status when required external services unavailable
                assert response.status_code == 503, f"Expected 503 when external services unavailable, got {response.status_code}"

    @pytest.mark.critical
    @pytest.mark.asyncio 
    async def test_external_service_configuration_completeness_fails(self):
        """
        FAILING TEST: Complete external service configuration in staging.
        
        Tests that all external service configuration is present and valid.
        Expected failure: Missing or incomplete configuration for external services.
        """
        env = IsolatedEnvironment()
        config = get_config()
        
        # Required external service configurations
        required_configs = {
            'REDIS_URL': 'Redis connection URL',
            'CLICKHOUSE_HOST': 'ClickHouse host',
            'CLICKHOUSE_PORT': 'ClickHouse port',
            'CLICKHOUSE_USERNAME': 'ClickHouse username',
            'CLICKHOUSE_PASSWORD': 'ClickHouse password',
        }
        
        missing_configs = []
        invalid_configs = []
        
        for env_var, description in required_configs.items():
            value = env.get(env_var)
            
            if not value:
                missing_configs.append(f"{env_var} ({description})")
            elif isinstance(value, str) and not value.strip():
                invalid_configs.append(f"{env_var} is empty or whitespace")
            elif env_var.endswith('_HOST') and value.strip() in ['localhost', '127.0.0.1']:
                invalid_configs.append(f"{env_var} still using localhost: {value}")
        
        # Check ClickHouse config object if available
        if hasattr(config, 'clickhouse_https'):
            ch_config = config.clickhouse_https
            for field in ['host', 'port', 'user']:  # ClickHouse uses 'user' not 'username'
                if not hasattr(ch_config, field):
                    missing_configs.append(f"ClickHouse config missing {field}")
                else:
                    value = getattr(ch_config, field)
                    if not value or (isinstance(value, str) and not value.strip()):
                        invalid_configs.append(f"ClickHouse {field} is empty")
        
        # Report all configuration issues
        error_messages = []
        if missing_configs:
            error_messages.append(f"Missing configurations: {', '.join(missing_configs)}")
        if invalid_configs:
            error_messages.append(f"Invalid configurations: {', '.join(invalid_configs)}")
        
        if error_messages:
            pytest.fail(f"External service configuration incomplete: {'; '.join(error_messages)}")

    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_external_service_network_connectivity_fails(self):
        """
        FAILING TEST: Network connectivity to all external services.
        
        Tests that all external services are network accessible from staging environment.
        Expected failure: Network connectivity issues or services not provisioned.
        """
        env = IsolatedEnvironment()
        connectivity_tests = []
        
        # ClickHouse connectivity test
        clickhouse_host = env.get("CLICKHOUSE_HOST", "clickhouse.staging.netrasystems.ai")
        clickhouse_port = int(env.get("CLICKHOUSE_PORT", "8123"))
        
        connectivity_tests.append(("ClickHouse", clickhouse_host, clickhouse_port))
        
        # Redis connectivity test
        redis_url = env.get("REDIS_URL", "")
        if redis_url and "redis://" in redis_url:
            # Extract host/port from Redis URL
            try:
                url_part = redis_url.split("://")[1]
                if "@" in url_part:
                    url_part = url_part.split("@")[1]  # Remove auth
                
                if ":" in url_part:
                    host, port_part = url_part.split(":", 1)
                    port = int(port_part.split("/")[0])  # Remove DB suffix
                else:
                    host = url_part.split("/")[0]
                    port = 6379
                    
                connectivity_tests.append(("Redis", host, port))
            except (ValueError, IndexError) as e:
                connectivity_tests.append(("Redis", f"URL_PARSE_ERROR: {redis_url}", 0))
        
        # Test connectivity to each service
        failed_connections = []
        
        for service_name, host, port in connectivity_tests:
            if port == 0:  # URL parse error
                failed_connections.append(f"{service_name}: {host}")
                continue
                
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            try:
                result = sock.connect_ex((host, port))
                if result != 0:
                    failed_connections.append(f"{service_name}: {host}:{port} connection refused")
            except socket.gaierror as e:
                failed_connections.append(f"{service_name}: {host}:{port} DNS resolution failed: {e}")
            except Exception as e:
                failed_connections.append(f"{service_name}: {host}:{port} connection error: {e}")
            finally:
                sock.close()
        
        if failed_connections:
            pytest.fail(f"External service connectivity failures: {'; '.join(failed_connections)}")


if __name__ == "__main__":
    # Run the tests to validate external service connectivity issues
    pytest.main([__file__, "-v", "-s"])