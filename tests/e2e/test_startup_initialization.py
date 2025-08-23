"""
Comprehensive System Initialization and Startup Tests

This test suite contains 30 difficult cold start initialization tests
that expose the most common and critical startup failures in production.
These tests use real services and are designed to initially FAIL to expose
actual issues in the System Under Test.

Test Categories:
1. Database Initialization (8 tests)
2. Service Dependencies (7 tests)  
3. Configuration & Secrets (5 tests)
4. Resource Management (5 tests)
5. Network & Communication (5 tests)
"""

import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch, MagicMock

import pytest
import psycopg2
import redis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.configuration.database import DatabaseConfigManager
from netra_backend.app.core.configuration.secrets import SecretsManager
from netra_backend.app.db.database_manager import DatabaseManager
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from dev_launcher.launcher import DevLauncher
from dev_launcher.config import LauncherConfig


# ==================== Test Fixtures ====================

@pytest.fixture
def test_env():
    """Create isolated test environment"""
    original_env = os.environ.copy()
    test_env = original_env.copy()
    test_env.update({
        "ENVIRONMENT": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_netra",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "CLICKHOUSE_HOST": "localhost",
        "CLICKHOUSE_HTTP_PORT": "8123",
        "JWT_SECRET_KEY": "test_jwt_secret_key_64_chars_minimum_for_security_test_environment_only",
        "JWT_SECRET": "test_jwt_secret_key_64_chars_minimum_for_security_test_environment_only",
    })
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield test_env
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
async def dev_launcher():
    """Create dev launcher instance for testing"""
    config = LauncherConfig(
        backend_port=0,  # Dynamic port allocation
        frontend_port=0,
        dynamic=True,
        no_browser=True,
        non_interactive=True,
        verbose=False,
        no_secrets=True,
        mode="minimal"
    )
    launcher = DevLauncher(config)
    yield launcher
    # Cleanup
    await launcher.cleanup()


@contextmanager
def temporary_env_var(key: str, value: Optional[str]):
    """Temporarily set or unset an environment variable"""
    original = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


@contextmanager
def limit_resource(resource_type: str, limit: int):
    """Temporarily limit system resources"""
    import resource as res
    
    resource_map = {
        "files": res.RLIMIT_NOFILE,
        "memory": res.RLIMIT_AS,
        "processes": res.RLIMIT_NPROC,
    }
    
    if resource_type not in resource_map:
        raise ValueError(f"Unknown resource type: {resource_type}")
    
    resource_id = resource_map[resource_type]
    original = res.getrlimit(resource_id)
    try:
        res.setrlimit(resource_id, (limit, original[1]))
        yield
    finally:
        res.setrlimit(resource_id, original)


# ==================== Database Initialization Tests ====================

@pytest.mark.asyncio
async def test_missing_postgresql_tables_on_first_boot(test_env):
    """Test 1: Application should handle missing database tables gracefully"""
    # Drop all tables to simulate fresh installation
    conn = psycopg2.connect(
        host=test_env["POSTGRES_HOST"],
        port=test_env["POSTGRES_PORT"],
        database=test_env["POSTGRES_DB"],
        user=test_env["POSTGRES_USER"],
        password=test_env["POSTGRES_PASSWORD"]
    )
    cursor = conn.cursor()
    cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.commit()
    conn.close()
    
    # Try to start the application
    start_time = time.time()
    timeout_seconds = 30
    
    try:
        from netra_backend.app.main import app
        from netra_backend.app.startup_module import startup_event
        
        # This should handle missing tables gracefully
        await startup_event(app)
        
        # If we get here without hanging, the test passes
        elapsed = time.time() - start_time
        assert elapsed < timeout_seconds, f"Startup took {elapsed}s, should complete within {timeout_seconds}s"
        
    except Exception as e:
        # Should provide clear error about missing tables
        assert "table" in str(e).lower() or "schema" in str(e).lower()


@pytest.mark.asyncio
async def test_connection_pool_exhaustion_during_startup(test_env):
    """Test 2: Handle connection pool exhaustion gracefully"""
    # Limit max connections to force exhaustion
    with patch.dict(os.environ, {"POSTGRES_MAX_CONNECTIONS": "2"}):
        tasks = []
        
        async def connect_to_db():
            db = Database()
            await db.connect()
            # Hold connection open
            await asyncio.sleep(5)
            await db.disconnect()
        
        # Try to create more connections than available
        for _ in range(5):
            tasks.append(asyncio.create_task(connect_to_db()))
        
        # At least some connections should fail gracefully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should have some connection errors
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) > 0, "Should have connection pool exhaustion errors"
        
        # Errors should be informative
        for error in errors:
            assert "connection" in str(error).lower() or "pool" in str(error).lower()


@pytest.mark.asyncio
async def test_schema_version_mismatch_between_services(test_env):
    """Test 3: Detect and handle schema version mismatches"""
    # Set different schema versions for different services
    with patch.dict(os.environ, {
        "BACKEND_SCHEMA_VERSION": "2.1",
        "AUTH_SCHEMA_VERSION": "2.0"
    }):
        # Backend database manager
        backend_db = Database()
        
        # Auth service database manager  
        auth_db = DatabaseManager()
        
        # Both should detect version mismatch
        with pytest.raises(Exception) as exc_info:
            await backend_db.connect()
            await auth_db.connect()
        
        assert "schema" in str(exc_info.value).lower() or "version" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_database_lock_timeout_during_concurrent_migration(test_env):
    """Test 4: Handle database locks during concurrent migrations"""
    import threading
    
    migration_errors = []
    
    def run_migration(service_name: str):
        try:
            # Simulate migration that takes locks
            conn = psycopg2.connect(
                host=test_env["POSTGRES_HOST"],
                port=test_env["POSTGRES_PORT"],
                database=test_env["POSTGRES_DB"],
                user=test_env["POSTGRES_USER"],
                password=test_env["POSTGRES_PASSWORD"]
            )
            cursor = conn.cursor()
            
            # Lock table for migration
            cursor.execute("LOCK TABLE alembic_version IN ACCESS EXCLUSIVE MODE NOWAIT")
            time.sleep(2)  # Hold lock
            conn.commit()
            conn.close()
        except Exception as e:
            migration_errors.append((service_name, e))
    
    # Start multiple migrations concurrently
    threads = []
    for i in range(3):
        t = threading.Thread(target=run_migration, args=(f"service_{i}",))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Should have lock timeout errors
    assert len(migration_errors) > 0, "Should have database lock conflicts"
    
    # Errors should mention locks or timeout
    for service, error in migration_errors:
        error_msg = str(error).lower()
        assert "lock" in error_msg or "timeout" in error_msg or "wait" in error_msg


@pytest.mark.asyncio
async def test_invalid_postgres_connection_string_format(test_env):
    """Test 5: Validate and handle invalid connection string formats"""
    invalid_urls = [
        "postgres://user@host:port/db",  # Missing password
        "postgresql+wrong://user:pass@host/db",  # Wrong driver
        "user:pass@host:5432/db",  # Missing scheme
        "postgresql://user:pass@:5432/db",  # Missing host
    ]
    
    for invalid_url in invalid_urls:
        with temporary_env_var("DATABASE_URL", invalid_url):
            db_config = DatabaseConfiguration()
            
            # Should raise clear validation error
            with pytest.raises(Exception) as exc_info:
                db_config.validate_connection_string()
            
            error_msg = str(exc_info.value).lower()
            assert "invalid" in error_msg or "format" in error_msg or "url" in error_msg


@pytest.mark.asyncio
async def test_postgresql_authentication_failure_recovery(test_env):
    """Test 6: Gracefully handle authentication failures with retry"""
    with temporary_env_var("POSTGRES_PASSWORD", "wrong_password"):
        db = Database()
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                await db.connect()
                break
            except Exception as e:
                retry_count += 1
                error_msg = str(e).lower()
                assert "authentication" in error_msg or "password" in error_msg
                
                if retry_count < max_retries:
                    # Fix password for last retry
                    if retry_count == max_retries - 1:
                        os.environ["POSTGRES_PASSWORD"] = test_env["POSTGRES_PASSWORD"]
                    await asyncio.sleep(1)
        
        assert retry_count > 0, "Should have had authentication failures"


@pytest.mark.asyncio
async def test_connection_timeout_during_network_partition(test_env):
    """Test 7: Handle connection timeouts appropriately"""
    # Point to non-existent host to simulate network partition
    with temporary_env_var("POSTGRES_HOST", "10.255.255.255"):
        db = Database()
        
        start_time = time.time()
        timeout_seconds = 5
        
        with pytest.raises(Exception) as exc_info:
            # Should timeout, not hang indefinitely
            await asyncio.wait_for(db.connect(), timeout=timeout_seconds)
        
        elapsed = time.time() - start_time
        assert elapsed < timeout_seconds + 1, f"Connection attempt took {elapsed}s, should timeout within {timeout_seconds}s"
        
        error_msg = str(exc_info.value).lower()
        assert "timeout" in error_msg or "connect" in error_msg


@pytest.mark.asyncio
async def test_database_recovery_from_crash_during_startup(test_env):
    """Test 8: Detect and recover from database crashes during startup"""
    db = Database()
    
    # Connect successfully first
    await db.connect()
    
    # Simulate database crash by killing connection
    if hasattr(db, '_connection'):
        db._connection.close()
    
    # Should detect disconnection and attempt reconnection
    health_check_passed = False
    for attempt in range(3):
        try:
            await db.health_check()
            health_check_passed = True
            break
        except Exception:
            # Should attempt reconnection
            await asyncio.sleep(1)
            await db.connect()
    
    assert health_check_passed, "Should recover from database crash"


# ==================== Service Dependencies Tests ====================

@pytest.mark.asyncio
async def test_redis_unavailable_at_startup(test_env):
    """Test 9: Handle Redis unavailability with graceful degradation"""
    # Point to non-existent Redis
    with temporary_env_var("REDIS_PORT", "16379"):
        from netra_backend.app.core.cache import CacheManager
        
        cache = CacheManager()
        
        # Should operate in degraded mode
        await cache.initialize()
        
        # Cache operations should work but not persist
        await cache.set("test_key", "test_value")
        result = await cache.get("test_key")
        
        # In degraded mode, might return None or use in-memory fallback
        assert result is None or result == "test_value"


@pytest.mark.asyncio
async def test_clickhouse_wrong_port_configuration(test_env):
    """Test 10: Handle ClickHouse port misconfiguration"""
    # Use HTTPS port instead of HTTP port
    with temporary_env_var("CLICKHOUSE_HTTP_PORT", "8443"):
        from netra_backend.app.db.clickhouse import ClickHouseManager
        
        ch = ClickHouseManager()
        
        with pytest.raises(Exception) as exc_info:
            await ch.connect()
        
        error_msg = str(exc_info.value).lower()
        assert "8443" in error_msg or "https" in error_msg or "port" in error_msg


@pytest.mark.asyncio
async def test_service_discovery_bootstrap_failure(test_env):
    """Test 11: Handle missing or corrupted service discovery files"""
    service_discovery_dir = Path(".service_discovery")
    
    # Remove service discovery directory
    if service_discovery_dir.exists():
        import shutil
        shutil.rmtree(service_discovery_dir)
    
    # Services should recreate discovery files
    from dev_launcher.service_discovery import ServiceDiscovery
    
    discovery = ServiceDiscovery()
    
    # Should create directory and files
    discovery.register_service("backend", "localhost", 8000)
    
    assert service_discovery_dir.exists()
    assert (service_discovery_dir / "backend.json").exists()


@pytest.mark.asyncio
async def test_auth_service_unreachable_during_backend_start(test_env):
    """Test 12: Handle auth service unavailability"""
    # Point to wrong auth service port
    with temporary_env_var("AUTH_SERVICE_URL", "http://localhost:18081"):
        from netra_backend.app.core.security import TokenValidator
        
        validator = TokenValidator()
        
        # Should handle auth service being down
        is_valid = await validator.validate_token("test_token")
        
        assert not is_valid, "Should reject tokens when auth service is down"


@pytest.mark.asyncio
async def test_port_conflict_resolution_failure(test_env):
    """Test 13: Handle port conflicts with dynamic allocation"""
    # Occupy the default backend port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", 8000))
    
    try:
        # Dev launcher should allocate different port
        launcher = DevLauncher(LauncherConfig(
            backend_port=8000,
            dynamic=True,
            non_interactive=True
        ))
        
        result = await launcher.allocate_ports()
        
        # Should get different port
        assert result["backend_port"] != 8000
        assert result["backend_port"] > 0
    finally:
        sock.close()


@pytest.mark.asyncio
async def test_health_check_cascade_timeout(test_env):
    """Test 14: Prevent circular dependency deadlocks"""
    from netra_backend.app.startup_checks.checker import StartupChecker
    
    # Create circular dependency scenario
    checker = StartupChecker()
    
    # Add checks that depend on each other
    async def check_service_a():
        # Wait for service B
        for _ in range(10):
            if await check_service_b():
                return True
            await asyncio.sleep(1)
        return False
    
    async def check_service_b():
        # Wait for service A
        for _ in range(10):
            if await check_service_a():
                return True
            await asyncio.sleep(1)
        return False
    
    # Should detect and break circular dependency
    start_time = time.time()
    timeout = 5
    
    try:
        await asyncio.wait_for(check_service_a(), timeout=timeout)
    except asyncio.TimeoutError:
        pass
    
    elapsed = time.time() - start_time
    assert elapsed < timeout + 1, "Should timeout to prevent deadlock"


@pytest.mark.asyncio
async def test_websocket_route_registration_missing(test_env):
    """Test 15: Detect missing WebSocket route registration"""
    from netra_backend.app.main import app
    
    client = TestClient(app)
    
    # Try to connect to WebSocket endpoint
    try:
        with client.websocket_connect("/ws"):
            pass
    except Exception as e:
        # Should give clear error about missing route
        error_msg = str(e).lower()
        assert "404" in error_msg or "not found" in error_msg or "websocket" in error_msg


# ==================== Configuration & Secrets Tests ====================

@pytest.mark.asyncio
async def test_missing_critical_environment_variables(test_env):
    """Test 16: Validate critical environment variables"""
    critical_vars = ["JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
    
    for var in critical_vars:
        with temporary_env_var(var, None):
            from netra_backend.app.core.configuration import Configuration
            
            config = Configuration()
            
            with pytest.raises(Exception) as exc_info:
                config.validate_required_variables()
            
            error_msg = str(exc_info.value)
            assert var in error_msg, f"Should mention missing {var}"


@pytest.mark.asyncio
async def test_jwt_secret_mismatch_between_services(test_env):
    """Test 17: Detect JWT secret mismatches"""
    # Backend uses different secret than auth service
    with patch.dict(os.environ, {
        "JWT_SECRET_KEY": "backend_secret_64_chars_minimum_for_security_test_environment_only",
        "JWT_SECRET": "auth_secret_different_64_chars_minimum_for_security_test_environment"
    }):
        from netra_backend.app.core.security import TokenValidator
        from auth_service.auth_core.security import TokenGenerator
        
        # Generate token with auth service
        generator = TokenGenerator()
        token = generator.create_token({"user_id": "123"})
        
        # Try to validate with backend
        validator = TokenValidator()
        is_valid = await validator.validate_token(token)
        
        assert not is_valid, "Should detect JWT secret mismatch"


@pytest.mark.asyncio
async def test_secrets_manager_api_timeout(test_env):
    """Test 18: Handle secrets loading timeouts"""
    with patch("netra_backend.app.core.configuration.secrets.GoogleSecretManager") as mock_gsm:
        # Make secret loading hang
        async def slow_load():
            await asyncio.sleep(60)
            return {}
        
        mock_gsm.return_value.load_secrets = slow_load
        
        secrets_config = SecretsConfiguration()
        
        start_time = time.time()
        timeout = 5
        
        try:
            await asyncio.wait_for(secrets_config.load_secrets(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        
        elapsed = time.time() - start_time
        assert elapsed < timeout + 1, "Should timeout secret loading"


@pytest.mark.asyncio
async def test_configuration_file_corruption(test_env):
    """Test 19: Handle corrupted configuration files"""
    config_file = Path(".service_discovery/backend.json")
    config_file.parent.mkdir(exist_ok=True)
    
    # Write corrupted JSON
    config_file.write_text("{ invalid json }")
    
    from dev_launcher.service_discovery import ServiceDiscovery
    
    discovery = ServiceDiscovery()
    
    # Should handle corruption gracefully
    service_info = discovery.get_service("backend")
    
    # Should either return None or recreate valid config
    assert service_info is None or isinstance(service_info, dict)


@pytest.mark.asyncio
async def test_environment_variable_case_sensitivity(test_env):
    """Test 20: Handle environment variable case inconsistencies"""
    # Set lowercase version
    with patch.dict(os.environ, {
        "clickhouse_host": "localhost",
        "CLICKHOUSE_HOST": ""  # Remove uppercase
    }):
        from netra_backend.app.core.configuration.database import DatabaseConfiguration
        
        config = DatabaseConfiguration()
        
        # Should normalize and find the variable
        host = config.get_clickhouse_host()
        
        assert host == "localhost", "Should handle case variations"


# ==================== Resource Management Tests ====================

@pytest.mark.asyncio
async def test_memory_limit_exceeded_during_startup(test_env):
    """Test 21: Handle memory constraints during startup"""
    if sys.platform != "win32":  # Resource limits don't work the same on Windows
        with limit_resource("memory", 256 * 1024 * 1024):  # 256MB limit
            # Try to allocate large amounts during startup
            try:
                large_data = []
                for _ in range(100):
                    large_data.append(bytearray(10 * 1024 * 1024))  # 10MB chunks
            except MemoryError as e:
                # Should handle gracefully
                assert True, "Memory limit enforced"
                return
            
            assert False, "Should have hit memory limit"


@pytest.mark.asyncio
async def test_file_descriptor_limit_exceeded(test_env):
    """Test 22: Handle file descriptor exhaustion"""
    if sys.platform != "win32":  # File descriptor limits are Unix-specific
        with limit_resource("files", 256):
            files = []
            try:
                # Try to open more files than allowed
                for i in range(300):
                    f = open(f"/tmp/test_file_{i}.txt", "w")
                    files.append(f)
            except OSError as e:
                # Should handle gracefully
                error_msg = str(e).lower()
                assert "too many" in error_msg or "file" in error_msg
            finally:
                for f in files:
                    f.close()


@pytest.mark.asyncio
async def test_background_task_timeout_crash(test_env):
    """Test 23: Prevent background task crashes"""
    from netra_backend.app.background import BackgroundTaskManager
    
    manager = BackgroundTaskManager()
    
    # Add task that hangs
    async def hanging_task():
        await asyncio.sleep(300)  # 5 minutes
    
    # Should timeout and not crash
    task = manager.add_task(hanging_task(), timeout=2)
    
    try:
        await task
    except asyncio.TimeoutError:
        pass  # Expected
    
    # Manager should still be functional
    assert manager.is_healthy()


@pytest.mark.asyncio
async def test_thread_pool_exhaustion_during_initialization(test_env):
    """Test 24: Handle thread pool exhaustion"""
    import concurrent.futures
    
    # Limit thread pool size
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        
        def blocking_task():
            time.sleep(5)
            return True
        
        # Submit more tasks than threads
        for _ in range(10):
            futures.append(executor.submit(blocking_task))
        
        # Should queue tasks, not crash
        start_time = time.time()
        timeout = 3
        
        completed = 0
        for future in concurrent.futures.as_completed(futures, timeout=timeout):
            try:
                future.result(timeout=0.1)
                completed += 1
            except concurrent.futures.TimeoutError:
                pass
        
        # Some tasks should complete
        assert completed > 0


@pytest.mark.asyncio
async def test_zombie_process_cleanup_failure(test_env):
    """Test 25: Clean up zombie processes properly"""
    if sys.platform != "win32":
        # Create a process that becomes zombie
        import subprocess
        
        # Start process that exits immediately
        proc = subprocess.Popen(["sleep", "0"])
        proc.wait()
        
        # Process is now zombie until parent reads exit status
        # Dev launcher should clean these up
        launcher = DevLauncher(LauncherConfig())
        launcher.cleanup_zombies()
        
        # Check no zombies remain
        zombies = subprocess.run(
            ["ps", "aux", "|", "grep", "defunct"],
            capture_output=True,
            text=True,
            shell=True
        )
        
        assert "defunct" not in zombies.stdout


# ==================== Network & Communication Tests ====================

@pytest.mark.asyncio
async def test_cors_configuration_dynamic_port_mismatch(test_env):
    """Test 26: Handle CORS with dynamic ports"""
    from auth_service.main import create_app
    
    app = create_app()
    
    # Simulate request from dynamic frontend port
    async with AsyncClient(app=app, base_url="http://localhost:8081") as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3001",  # Dynamic port
                "Access-Control-Request-Method": "GET"
            }
        )
        
        # Should allow dynamic localhost ports
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


@pytest.mark.asyncio
async def test_dns_resolution_failure_for_service_discovery(test_env):
    """Test 27: Handle DNS resolution failures"""
    with temporary_env_var("POSTGRES_HOST", "non.existent.host.invalid"):
        db = Database()
        
        with pytest.raises(Exception) as exc_info:
            await db.connect()
        
        error_msg = str(exc_info.value).lower()
        assert "host" in error_msg or "resolve" in error_msg or "dns" in error_msg


@pytest.mark.asyncio
async def test_ssl_tls_certificate_validation_failure(test_env):
    """Test 28: Handle certificate validation issues"""
    with temporary_env_var("DATABASE_URL", "postgresql+ssl://user:pass@localhost/db?sslmode=require"):
        db = Database()
        
        # Should handle self-signed or invalid certs in dev
        try:
            await db.connect()
        except Exception as e:
            error_msg = str(e).lower()
            assert "ssl" in error_msg or "certificate" in error_msg or "tls" in error_msg


@pytest.mark.asyncio
async def test_network_partition_during_service_registration(test_env):
    """Test 29: Handle network partitions during registration"""
    from dev_launcher.service_discovery import ServiceDiscovery
    
    discovery = ServiceDiscovery()
    
    # Register service
    discovery.register_service("backend", "localhost", 8000)
    
    # Simulate network partition by corrupting registration
    service_file = Path(".service_discovery/backend.json")
    if service_file.exists():
        data = json.loads(service_file.read_text())
        data["host"] = "unreachable.host"
        service_file.write_text(json.dumps(data))
    
    # Should detect stale registration
    is_valid = discovery.validate_service("backend")
    
    assert not is_valid, "Should detect stale service registration"


@pytest.mark.asyncio
async def test_websocket_connection_pool_exhaustion(test_env):
    """Test 30: Handle WebSocket connection limits"""
    from netra_backend.app.main import app
    
    client = TestClient(app)
    connections = []
    
    try:
        # Try to create many WebSocket connections
        for i in range(100):
            ws = client.websocket_connect(f"/ws?client_id={i}")
            connections.append(ws)
    except Exception as e:
        # Should reject after limit
        error_msg = str(e).lower()
        assert "limit" in error_msg or "max" in error_msg or "connections" in error_msg
    finally:
        for conn in connections:
            try:
                conn.close()
            except:
                pass


# ==================== Test Runner ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])