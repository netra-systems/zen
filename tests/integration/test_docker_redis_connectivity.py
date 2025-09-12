"""
Docker Redis Connectivity Integration Tests - Five Whys Root Cause Prevention

CRITICAL: This addresses the specific Five Whys root cause:
"Integration tests didn't catch Redis port mapping mismatch"

These tests validate:
1. Real Redis connectivity within Docker Compose environment
2. Redis connection validation with test containers
3. Health checks and startup validation for Redis connectivity  
4. Environment variable propagation from Docker to application
5. Redis functionality testing across different environments

ROOT CAUSE ADDRESSED: WHY #4 - Missing comprehensive test coverage that should
have caught Redis connectivity issues during Docker integration testing.

Business Value: Platform/Internal - Redis Integration Reliability & Docker Testing
Prevents Redis connection failures by validating real connectivity in Docker environments.
"""
import pytest
import os
import subprocess
import time
from netra_backend.app.services.redis_client import get_redis_client, get_redis_service
import json
import socket
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.backend_environment import BackendEnvironment

logger = logging.getLogger(__name__)


class DockerRedisTestManager:
    """Manage Docker Redis services for testing."""
    
    def __init__(self):
        """Initialize Docker Redis test manager."""
        self.project_dir = Path(__file__).parent.parent.parent
        self.compose_file = self.project_dir / "docker-compose.yml"
    
    def is_docker_available(self) -> bool:
        """Check if Docker and Docker Compose are available."""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, timeout=5)
            subprocess.run(["docker", "compose", "--version"], capture_output=True, timeout=5)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def start_test_redis(self, timeout: int = 60) -> bool:
        """Start test Redis service using Docker Compose."""
        if not self.is_docker_available():
            return False
        
        try:
            # Start test-redis service
            cmd = [
                "docker", "compose", 
                "--profile", "test",
                "up", "-d", "test-redis"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start test-redis: {result.stderr}")
                return False
            
            # Wait for Redis to be healthy
            return self.wait_for_redis_health(timeout=30)
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.error(f"Error starting test Redis: {e}")
            return False
    
    def wait_for_redis_health(self, timeout: int = 30) -> bool:
        """Wait for Redis to become healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if container is running and healthy
                result = subprocess.run(
                    ["docker", "compose", "--profile", "test", "ps", "test-redis"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if "test-redis" in result.stdout and ("Up" in result.stdout or "running" in result.stdout):
                    # Also test actual Redis connectivity
                    import asyncio
                    if asyncio.get_event_loop().run_until_complete(self._test_redis_ping("localhost", 6381)):
                        logger.info("Redis is healthy and accessible")
                        return True
                
                time.sleep(2)
                
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                time.sleep(2)
                continue
        
        logger.error("Redis failed to become healthy within timeout")
        return False
    
    async def _test_redis_ping(self, host: str, port: int) -> bool:
        """Test Redis connectivity with ping."""
        try:
            # MIGRATION NEEDED: await get_redis_client()  # MIGRATED: was redis.Redis( -> await get_redis_client() - requires async context
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host=host, port=port, socket_timeout=5, socket_connect_timeout=5)
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception:
            return False
    
    def stop_test_redis(self):
        """Stop test Redis service."""
        try:
            subprocess.run(
                ["docker", "compose", "--profile", "test", "down", "test-redis"],
                cwd=self.project_dir,
                capture_output=True,
                timeout=30
            )
        except:
            pass  # Best effort cleanup
    
    def get_redis_logs(self) -> str:
        """Get Redis container logs for debugging."""
        try:
            result = subprocess.run(
                ["docker", "compose", "--profile", "test", "logs", "test-redis"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout
        except:
            return "Could not retrieve Redis logs"


class TestDockerRedisConnectivity:
    """Test Redis connectivity in Docker environment."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup clean environment for each test."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        self.docker_manager = DockerRedisTestManager()
        yield
        self.env.reset_to_original()
    
    @pytest.fixture(scope="class")
    def redis_service(self):
        """Ensure Redis test service is running for the test class."""
        manager = DockerRedisTestManager()
        
        if not manager.is_docker_available():
            pytest.skip("Docker not available")
        
        # Start Redis service
        if not manager.start_test_redis():
            pytest.skip("Failed to start test Redis service")
        
        yield
        
        # Cleanup
        manager.stop_test_redis()
    
    def test_redis_basic_connectivity(self, redis_service):
        """Test basic Redis connectivity through Docker."""
        # Configure for Docker test environment
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_HOST": "localhost",  # External Docker access
            "REDIS_PORT": "6381",      # External port from docker-compose.yml
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "docker_redis_connectivity_test")
        
        backend_env = BackendEnvironment()
        
        # Validate configuration
        assert backend_env.is_testing() is True
        assert backend_env.get_redis_host() == "localhost"
        assert backend_env.get_redis_port() == 6381
        
        # Test actual Redis connectivity
        redis_url = backend_env.get_redis_url()
        assert redis_url == "redis://localhost:6381/0"
        
        # Create Redis client and test connection
        try:
            redis_client = redis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
            
            # Test ping
            pong = await redis_client.ping()
            assert pong is True, "Redis ping should return True"
            
            # Test basic operations
            test_key = f"docker_connectivity_test_{int(time.time())}"
            
            # Set a value
            await redis_client.set(test_key, "docker_test_value", ex=60)
            
            # Get the value
            retrieved_value = await redis_client.get(test_key)
            assert retrieved_value is not None, "Should retrieve the set value"
            assert retrieved_value.decode() == "docker_test_value"
            
            # Test Redis info
            info = await redis_client.info()
            assert isinstance(info, dict), "Redis info should return a dictionary"
            assert "redis_version" in info, "Redis info should contain version"
            
            # Test database selection
            await redis_client.select(0)  # Ensure we're on database 0
            
            # Cleanup
            await redis_client.delete(test_key)
            await redis_client.close()
            
        except redis.ConnectionError as e:
            pytest.fail(f"Redis connection failed: {e}")
        except redis.TimeoutError as e:
            pytest.fail(f"Redis operation timed out: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected Redis error: {e}")
    
    def test_redis_connection_pool_management(self, redis_service):
        """Test Redis connection pool management in Docker environment."""
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "redis_pool_test")
        
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        
        # Test connection pooling
        try:
            # Create connection pool
            pool = redis.ConnectionPool.from_url(redis_url, max_connections=5)
            
            # Create multiple clients using the same pool
            clients = []
            for i in range(3):
                # MIGRATION NEEDED: await get_redis_client()  # MIGRATED: was redis.Redis( -> await get_redis_client() - requires async context
                client = await get_redis_client()  # MIGRATED: was redis.Redis(connection_pool=pool)
                clients.append(client)
            
            # Test that all clients can perform operations
            test_keys = []
            for i, client in enumerate(clients):
                test_key = f"pool_test_{i}_{int(time.time())}"
                test_keys.append(test_key)
                
                client.set(test_key, f"value_{i}", ex=60)
                retrieved = client.get(test_key)
                assert retrieved.decode() == f"value_{i}"
            
            # Test concurrent operations
            pipe = clients[0].pipeline()
            for key in test_keys:
                pipe.get(key)
            results = pipe.execute()
            
            assert len(results) == len(test_keys)
            for i, result in enumerate(results):
                assert result.decode() == f"value_{i}"
            
            # Cleanup
            for key in test_keys:
                clients[0].delete(key)
            
            for client in clients:
                client.close()
            
            pool.disconnect()
            
        except Exception as e:
            pytest.fail(f"Redis connection pool test failed: {e}")
    
    def test_redis_persistence_across_connections(self, redis_service):
        """Test Redis data persistence across connection sessions."""
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "redis_persistence_test")
        
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        
        persistent_key = f"persistence_test_{int(time.time())}"
        persistent_value = "should_persist_across_connections"
        
        try:
            # First connection - set data
            redis_client1 = redis.from_url(redis_url, socket_timeout=5)
            redis_client1.set(persistent_key, persistent_value, ex=120)  # 2 minute expiry
            redis_client1.close()
            
            # Second connection - retrieve data
            redis_client2 = redis.from_url(redis_url, socket_timeout=5)
            retrieved_value = redis_client2.get(persistent_key)
            
            assert retrieved_value is not None, "Data should persist across connections"
            assert retrieved_value.decode() == persistent_value
            
            # Test TTL
            ttl = redis_client2.ttl(persistent_key)
            assert ttl > 0, "TTL should be positive"
            assert ttl <= 120, "TTL should not exceed set value"
            
            # Cleanup
            redis_client2.delete(persistent_key)
            redis_client2.close()
            
        except Exception as e:
            pytest.fail(f"Redis persistence test failed: {e}")
    
    def test_redis_error_handling_and_recovery(self, redis_service):
        """Test Redis error handling and connection recovery."""
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "redis_error_handling_test")
        
        backend_env = BackendEnvironment()
        redis_url = backend_env.get_redis_url()
        
        try:
            redis_client = redis.from_url(redis_url, socket_timeout=5, retry_on_timeout=True)
            
            # Test normal operation
            await redis_client.set("error_test_key", "test_value", ex=60)
            assert await redis_client.get("error_test_key").decode() == "test_value"
            
            # Test invalid operations that should handle gracefully
            try:
                # Invalid command should raise an error
                await redis_client.execute_command("INVALID_COMMAND")
                pytest.fail("Invalid command should raise an error")
            except redis.ResponseError:
                pass  # Expected
            
            # Connection should still work after error
            await redis_client.set("recovery_test_key", "recovery_value", ex=60)
            assert await redis_client.get("recovery_test_key").decode() == "recovery_value"
            
            # Test connection timeout handling
            try:
                redis_client_short_timeout = redis.from_url(
                    redis_url, 
                    socket_timeout=0.001,  # Very short timeout
                    socket_connect_timeout=0.001
                )
                # This might timeout, which is expected
                redis_client_short_timeout.ping()
                redis_client_short_timeout.close()
            except (redis.TimeoutError, redis.ConnectionError):
                pass  # Expected with very short timeout
            
            # Original connection should still work
            await redis_client.ping()
            
            # Cleanup
            await redis_client.delete("error_test_key", "recovery_test_key")
            await redis_client.close()
            
        except Exception as e:
            pytest.fail(f"Redis error handling test failed: {e}")
    
    def test_redis_database_selection(self, redis_service):
        """Test Redis database selection and isolation."""
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381"
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "redis_db_selection_test")
        
        backend_env = BackendEnvironment()
        
        try:
            # Test different databases
            # MIGRATION NEEDED: await get_redis_client()  # MIGRATED: was redis.Redis( -> await get_redis_client() - requires async context
            redis_db0 = await get_redis_client()
            
            # MIGRATION NEEDED: await get_redis_client()  # MIGRATED: was redis.Redis( -> await get_redis_client() - requires async context
            redis_db1 = await get_redis_client()
            
            test_key = f"db_isolation_test_{int(time.time())}"
            
            # Set same key in different databases
            redis_db0.set(test_key, "value_in_db0", ex=60)
            redis_db1.set(test_key, "value_in_db1", ex=60)
            
            # Verify isolation
            value_db0 = redis_db0.get(test_key)
            value_db1 = redis_db1.get(test_key)
            
            assert value_db0.decode() == "value_in_db0"
            assert value_db1.decode() == "value_in_db1"
            assert value_db0 != value_db1, "Different databases should have isolated data"
            
            # Test that default URL uses database 0
            redis_url_client = redis.from_url(f"redis://localhost:6381/0")
            value_url = redis_url_client.get(test_key)
            assert value_url.decode() == "value_in_db0", "URL with /0 should access database 0"
            
            # Cleanup
            redis_db0.delete(test_key)
            redis_db1.delete(test_key)
            
            redis_db0.close()
            redis_db1.close()
            redis_url_client.close()
            
        except Exception as e:
            pytest.fail(f"Redis database selection test failed: {e}")


class TestRedisDockerHealthChecks:
    """Test Redis health checks in Docker environment."""
    
    @pytest.fixture(autouse=True)
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        self.docker_manager = DockerRedisTestManager()
        yield
        self.env.reset_to_original()
    
    def test_redis_container_health_status(self):
        """Test Redis container health check status."""
        if not self.docker_manager.is_docker_available():
            pytest.skip("Docker not available")
        
        # Start Redis if not running
        if not self.docker_manager.start_test_redis():
            pytest.skip("Failed to start test Redis")
        
        try:
            # Check container health status
            result = subprocess.run(
                ["docker", "compose", "--profile", "test", "ps", "--format", "json"],
                cwd=self.docker_manager.project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                pytest.fail(f"Failed to get container status: {result.stderr}")
            
            # Parse JSON output
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            
            # Find Redis container
            redis_container = None
            for container in containers:
                if 'test-redis' in container.get('Name', ''):
                    redis_container = container
                    break
            
            assert redis_container is not None, "Redis container should be running"
            
            # Check health status
            status = redis_container.get('State', '').lower()
            assert 'running' in status or 'up' in status, f"Redis container should be running, got: {status}"
            
            # If health check is available, verify it
            health = redis_container.get('Health', '')
            if health:
                assert 'healthy' in health.lower() or 'starting' in health.lower(), f"Redis should be healthy, got: {health}"
        
        finally:
            self.docker_manager.stop_test_redis()
    
    def test_redis_health_check_command_validation(self):
        """Test that Redis health check command works correctly."""
        if not self.docker_manager.is_docker_available():
            pytest.skip("Docker not available")
        
        if not self.docker_manager.start_test_redis():
            pytest.skip("Failed to start test Redis")
        
        try:
            # Wait a moment for Redis to fully start
            time.sleep(5)
            
            # Execute health check command inside container
            # From docker-compose.yml: test: ["CMD", "redis-cli", "ping"]
            result = subprocess.run([
                "docker", "compose", "--profile", "test", "exec", "-T", "test-redis", 
                "redis-cli", "ping"
            ], 
            cwd=self.docker_manager.project_dir,
            capture_output=True, 
            text=True,
            timeout=10
            )
            
            assert result.returncode == 0, f"Redis health check failed: {result.stderr}"
            assert "PONG" in result.stdout.upper(), f"Redis ping should return PONG, got: {result.stdout}"
            
        finally:
            self.docker_manager.stop_test_redis()
    
    def test_redis_startup_timing_validation(self):
        """Test Redis startup timing and readiness."""
        if not self.docker_manager.is_docker_available():
            pytest.skip("Docker not available")
        
        start_time = time.time()
        
        # Start Redis and measure startup time
        success = self.docker_manager.start_test_redis(timeout=60)
        startup_time = time.time() - start_time
        
        try:
            assert success, "Redis should start successfully"
            assert startup_time < 30, f"Redis should start within 30 seconds, took {startup_time:.2f}s"
            
            # Test that Redis is immediately usable after health check passes
            # MIGRATION NEEDED: await get_redis_client()  # MIGRATED: was redis.Redis( -> await get_redis_client() - requires async context
            redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host="localhost", port=6381, socket_timeout=5)
            
            operation_start = time.time()
            await redis_client.ping()
            await redis_client.set("startup_test", "ready", ex=30)
            retrieved = await redis_client.get("startup_test")
            operation_time = time.time() - operation_start
            
            assert retrieved.decode() == "ready"
            assert operation_time < 1, f"Redis operations should be fast after startup, took {operation_time:.2f}s"
            
            # Cleanup
            await redis_client.delete("startup_test")
            await redis_client.close()
            
        finally:
            self.docker_manager.stop_test_redis()


class TestRedisConfigurationEnvironmentIntegration:
    """Test Redis configuration integration across different environments."""
    
    @pytest.fixture(autouse=True) 
    def setup_environment(self):
        """Setup environment."""
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        yield
        self.env.reset_to_original()
    
    def test_development_redis_configuration_integration(self):
        """Test Redis configuration for development environment."""
        # Simulate Docker development environment
        dev_config = {
            "ENVIRONMENT": "development",
            "REDIS_HOST": "dev-redis",  # Internal Docker service name
            "REDIS_PORT": "6379",       # Internal port
            # No REDIS_URL set - should use host/port
        }
        
        for key, value in dev_config.items():
            self.env.set(key, value, "dev_redis_config_test")
        
        backend_env = BackendEnvironment()
        
        # Validate development configuration
        assert backend_env.is_development() is True
        assert backend_env.get_redis_host() == "dev-redis"
        assert backend_env.get_redis_port() == 6379
        
        # Redis URL should use default pattern
        redis_url = backend_env.get_redis_url()
        assert redis_url == "redis://localhost:6379/0"  # Uses env var REDIS_URL or default
        
        # This configuration would work within Docker network
        # (Cannot test actual connectivity without running dev services)
    
    def test_test_environment_redis_configuration_integration(self):
        """Test Redis configuration for test environment."""
        test_config = {
            "ENVIRONMENT": "test",
            "REDIS_HOST": "localhost",      # External access
            "REDIS_PORT": "6381",           # External port
            "REDIS_URL": "redis://localhost:6381/0"  # Full URL
        }
        
        for key, value in test_config.items():
            self.env.set(key, value, "test_redis_config_test")
        
        backend_env = BackendEnvironment()
        
        # Validate test configuration
        assert backend_env.is_testing() is True
        assert backend_env.get_redis_host() == "localhost"
        assert backend_env.get_redis_port() == 6381
        assert backend_env.get_redis_url() == "redis://localhost:6381/0"
        
        # This configuration should work for external Docker access
    
    def test_redis_url_precedence_over_components(self):
        """Test that REDIS_URL takes precedence over individual components."""
        config_with_precedence = {
            "ENVIRONMENT": "test",
            "REDIS_HOST": "component-host",
            "REDIS_PORT": "9999",
            "REDIS_URL": "redis://url-host:8888/1"  # Should take precedence
        }
        
        for key, value in config_with_precedence.items():
            self.env.set(key, value, "redis_precedence_test")
        
        backend_env = BackendEnvironment()
        
        # REDIS_URL should take precedence
        redis_url = backend_env.get_redis_url()
        assert redis_url == "redis://url-host:8888/1"
        
        # But individual component methods should return their values
        assert backend_env.get_redis_host() == "component-host"
        assert backend_env.get_redis_port() == 9999
    
    def test_redis_configuration_validation_integration(self):
        """Test Redis configuration validation integration."""
        # Test valid Redis configuration
        valid_config = {
            "ENVIRONMENT": "test",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6381",
            "REDIS_URL": "redis://localhost:6381/0"
        }
        
        for key, value in valid_config.items():
            self.env.set(key, value, "redis_validation_test")
        
        backend_env = BackendEnvironment()
        
        # Configuration should be valid
        redis_host = backend_env.get_redis_host()
        redis_port = backend_env.get_redis_port()
        redis_url = backend_env.get_redis_url()
        
        assert redis_host == "localhost"
        assert redis_port == 6381
        assert redis_url == "redis://localhost:6381/0"
        
        # Test invalid port handling
        self.env.set("REDIS_PORT", "invalid_port", "validation_test")
        
        # Should fallback to default
        invalid_port_backend_env = BackendEnvironment()
        fallback_port = invalid_port_backend_env.get_redis_port()
        assert fallback_port == 6379  # Default port
        
        # Test empty host handling
        self.env.set("REDIS_HOST", "", "validation_test")
        
        empty_host_backend_env = BackendEnvironment()
        fallback_host = empty_host_backend_env.get_redis_host()
        assert fallback_host == "localhost"  # Default host


@pytest.mark.integration
@pytest.mark.docker  
class TestRedisDockerIntegrationEnd2End:
    """End-to-end Redis Docker integration tests."""
    
    @pytest.fixture(scope="class")
    def docker_environment(self):
        """Set up complete Docker test environment."""
        manager = DockerRedisTestManager()
        
        if not manager.is_docker_available():
            pytest.skip("Docker not available")
        
        # Start Redis service  
        if not manager.start_test_redis():
            pytest.skip("Failed to start Redis test environment")
        
        yield manager
        
        # Cleanup
        manager.stop_test_redis()
    
    def test_end_to_end_redis_integration_workflow(self, docker_environment):
        """Test complete Redis integration workflow from config to operation."""
        env = get_env()
        env.enable_isolation(backup_original=True)
        
        try:
            # Step 1: Configure environment (as Docker would)
            docker_config = {
                "ENVIRONMENT": "test",
                "REDIS_HOST": "localhost",
                "REDIS_PORT": "6381",
                "REDIS_URL": "redis://localhost:6381/0"
            }
            
            for key, value in docker_config.items():
                env.set(key, value, "e2e_redis_test")
            
            # Step 2: Initialize backend environment
            backend_env = BackendEnvironment()
            
            # Step 3: Validate configuration
            assert backend_env.is_testing() is True
            redis_url = backend_env.get_redis_url()
            assert redis_url == "redis://localhost:6381/0"
            
            # Step 4: Test Redis operations (simulating application usage)
            redis_client = redis.from_url(redis_url, socket_timeout=5)
            
            # Basic connectivity
            await redis_client.ping()
            
            # Simulate application data operations
            session_key = f"session:{int(time.time())}"
            user_data = {"user_id": "test_user", "session_start": time.time()}
            
            # Store session data
            await redis_client.hset(session_key, mapping=user_data)
            await redis_client.expire(session_key, 300)  # 5 minute expiry
            
            # Retrieve session data
            stored_data = await redis_client.hgetall(session_key)
            assert stored_data[b'user_id'].decode() == "test_user"
            
            # Test cache operations
            cache_key = f"cache:test_data:{int(time.time())}"
            cache_data = json.dumps({"result": "success", "timestamp": time.time()})
            
            await redis_client.setex(cache_key, 60, cache_data)
            cached_result = await redis_client.get(cache_key)
            assert cached_result is not None
            
            parsed_cache = json.loads(cached_result.decode())
            assert parsed_cache["result"] == "success"
            
            # Test pub/sub (basic test)
            pubsub = await redis_client.pubsub()
            test_channel = f"test_channel_{int(time.time())}"
            pubsub.subscribe(test_channel)
            
            # Publish a message
            await redis_client.publish(test_channel, "test_message")
            
            # Check for message (with timeout)
            message = pubsub.get_message(timeout=5)
            if message and message['type'] == 'subscribe':
                # Get actual message
                message = pubsub.get_message(timeout=5)
            
            if message:
                assert message['type'] == 'message'
                assert message['data'].decode() == "test_message"
            
            # Cleanup
            await redis_client.delete(session_key, cache_key)
            pubsub.close()
            await redis_client.close()
            
        finally:
            env.reset_to_original()
    
    def test_redis_failure_recovery_integration(self, docker_environment):
        """Test Redis failure and recovery scenarios."""
        env = get_env()
        env.enable_isolation(backup_original=True)
        
        try:
            # Configure Redis connection
            config = {
                "ENVIRONMENT": "test",
                "REDIS_URL": "redis://localhost:6381/0"
            }
            
            for key, value in config.items():
                env.set(key, value, "redis_failure_test")
            
            backend_env = BackendEnvironment()
            redis_url = backend_env.get_redis_url()
            
            # Test connection with retry logic
            redis_client = redis.from_url(
                redis_url, 
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Establish connection
            await redis_client.ping()
            
            # Set persistent data
            persistence_key = f"persistence_test_{int(time.time())}"
            await redis_client.set(persistence_key, "should_survive", ex=300)
            
            # Simulate brief disconnection by creating new client
            await redis_client.close()
            
            # Reconnect (simulating recovery)
            redis_client_recovered = redis.from_url(redis_url, socket_timeout=5)
            
            # Verify data survived
            recovered_data = redis_client_recovered.get(persistence_key)
            assert recovered_data is not None
            assert recovered_data.decode() == "should_survive"
            
            # Cleanup
            redis_client_recovered.delete(persistence_key)
            redis_client_recovered.close()
            
        finally:
            env.reset_to_original()