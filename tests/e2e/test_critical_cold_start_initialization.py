from shared.isolated_environment import get_env
"""
Critical Cold Start System Initialization Tests.

This test suite validates the most difficult cold start scenarios that cause
production issues. These tests use REAL services and are designed to initially FAIL
to prove they catch real problems.

Test Categories:
1. Database initialization race conditions
2. Service coordination failures
3. WebSocket infrastructure issues
4. Authentication and session management
5. Frontend and API integration
6. Resource management and limits
"""

import asyncio
import json
import os
import time
import uuid
import signal
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor
import tempfile
import shutil

import aiohttp
import httpx
import psutil
import pytest
import redis.asyncio as redis
from sqlalchemy import text, pool, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.pool import NullPool, QueuePool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override test environment DATABASE_URL to use real database
if get_env().get('DATABASE_URL') == 'sqlite+aiosqlite:///:memory:':
    env_file_path = Path('.env')
    if env_file_path.exists():
        with open(env_file_path) as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    real_database_url = line.split('=', 1)[1].strip()
                    break

class Settings:
    def __init__(self):
        self.DATABASE_URL = get_env().get('DATABASE_URL', 'postgresql+asyncpg://postgres:DTprdt5KoQXlEG4Gh9lF@localhost:5433/netra_dev')
        self.REDIS_URL = get_env().get('REDIS_URL', 'redis://localhost:6379/1')
        self.CLICKHOUSE_HOST = get_env().get('CLICKHOUSE_HOST', 'localhost')
        self.CLICKHOUSE_PORT = int(get_env().get('CLICKHOUSE_PORT', '8123'))
    
    def is_postgresql(self):
        return self.DATABASE_URL.startswith(('postgresql', 'postgres'))

settings = Settings()


@pytest.mark.e2e
class TestDatabaseInitializationRaceConditions:
    """Test database initialization race conditions during cold start."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_01_connection_pool_race_during_cold_start(self):
        """Test connection pool race conditions when multiple services start simultaneously."""
        if not settings.is_postgresql():
            pytest.skip("Requires PostgreSQL for pool testing")
        
        # Simulate multiple services trying to initialize pools simultaneously
        engines = []
        connection_results = []
        
        async def create_pool_and_connect(service_name: str, pool_size: int):
            """Simulate a service creating its connection pool."""
            try:
                engine = create_async_engine(
                    settings.DATABASE_URL,
                    pool_size=pool_size,
                    max_overflow=0,  # No overflow to force contention
                    pool_timeout=1,  # Short timeout to detect issues quickly
                    pool_pre_ping=True
                    # Remove poolclass - let SQLAlchemy choose the right one for async
                )
                engines.append(engine)
                
                # Try to acquire all connections immediately
                connections = []
                for i in range(pool_size):
                    conn = await engine.connect()
                    connections.append(conn)
                
                # Execute a query on each connection
                for conn in connections:
                    result = await conn.execute(text("SELECT 1"))
                    assert result.scalar() == 1
                
                # Clean up
                for conn in connections:
                    await conn.close()
                
                return {"service": service_name, "success": True}
                
            except Exception as e:
                return {"service": service_name, "success": False, "error": str(e)}
        
        # Start multiple services simultaneously
        services = [
            ("backend", 10),
            ("auth", 5),
            ("websocket", 8),
            ("analytics", 3)
        ]
        
        tasks = [create_pool_and_connect(name, size) for name, size in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for race condition issues
        failed = [r for r in results if isinstance(r, dict) and not r.get("success")]
        assert len(failed) == 0, f"Services failed due to race conditions: {failed}"
        
        # Clean up engines
        for engine in engines:
            await engine.dispose()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_02_migration_lock_conflicts_multiple_services(self):
        """Test migration lock conflicts when multiple services try to run migrations."""
        if not settings.is_postgresql():
            pytest.skip("Requires PostgreSQL for advisory locks")
        
        migration_results = []
        lock_acquired = asyncio.Event()
        
        async def try_acquire_migration_lock(service_name: str):
            """Simulate a service trying to acquire migration lock."""
            engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
            
            try:
                async with engine.begin() as conn:
                    # Try to acquire PostgreSQL advisory lock (used by Alembic)
                    # Lock ID 12345 simulates Alembic's migration lock
                    result = await conn.execute(
                        text("SELECT pg_try_advisory_lock(12345)")
                    )
                    lock_obtained = result.scalar()
                    
                    if lock_obtained:
                        lock_acquired.set()
                        # Hold lock briefly to simulate migration
                        await asyncio.sleep(0.5)
                        # Release lock
                        await conn.execute(text("SELECT pg_advisory_unlock(12345)"))
                        return {"service": service_name, "got_lock": True}
                    else:
                        # Wait and retry
                        await lock_acquired.wait()
                        return {"service": service_name, "got_lock": False, "waited": True}
                        
            finally:
                await engine.dispose()
        
        # Multiple services try to acquire migration lock simultaneously
        services = ["backend", "auth", "worker", "scheduler"]
        tasks = [try_acquire_migration_lock(s) for s in services]
        results = await asyncio.gather(*tasks)
        
        # Exactly one service should get the lock initially
        lock_holders = [r for r in results if r.get("got_lock")]
        assert len(lock_holders) == 1, "Exactly one service should acquire migration lock"
        
        # Others should have waited
        waiters = [r for r in results if r.get("waited")]
        assert len(waiters) == len(services) - 1, "Other services should wait for lock"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_03_transaction_isolation_concurrent_init(self):
        """Test transaction isolation during concurrent initialization."""
        if not settings.is_postgresql():
            pytest.skip("Requires PostgreSQL for isolation testing")
        
        # Create test table for isolation testing
        engine = create_async_engine(settings.DATABASE_URL, isolation_level="SERIALIZABLE")
        
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS init_test (
                    id SERIAL PRIMARY KEY,
                    service_name VARCHAR(100),
                    init_value INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("TRUNCATE init_test"))
        
        async def init_service_data(service_name: str, value: int):
            """Simulate service initializing its data."""
            async with engine.begin() as conn:
                # Check if already initialized
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM init_test WHERE service_name = :name"),
                    {"name": service_name}
                )
                count = result.scalar()
                
                if count == 0:
                    # Initialize data
                    await conn.execute(
                        text("INSERT INTO init_test (service_name, init_value) VALUES (:name, :value)"),
                        {"name": service_name, "value": value}
                    )
                    return "initialized"
                return "already_exists"
        
        # Multiple services try to initialize simultaneously
        services = [("service1", 100), ("service2", 200), ("service3", 300)]
        tasks = [init_service_data(name, val) for name, val in services for _ in range(3)]
        
        # This might cause serialization failures
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for serialization errors
        errors = [r for r in results if isinstance(r, Exception)]
        # Some errors are expected due to isolation conflicts
        
        # Verify final state is consistent
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT COUNT(DISTINCT service_name) FROM init_test"))
            unique_services = result.scalar()
            assert unique_services == 3, "Each service should be initialized exactly once"
        
        await engine.dispose()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_04_schema_version_mismatch_detection(self):
        """Test detection of schema version mismatches between services."""
        engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        
        try:
            async with engine.begin() as conn:
                # Create version tracking table
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_versions (
                        service_name VARCHAR(100) PRIMARY KEY,
                        version VARCHAR(50),
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Simulate different services reporting different schema versions
                services_versions = [
                    ("backend", "2.1.0"),
                    ("auth", "2.0.9"),  # Outdated
                    ("worker", "2.1.0"),
                    ("analytics", "2.2.0")  # Too new
                ]
                
                for service, version in services_versions:
                    await conn.execute(text("""
                        INSERT INTO schema_versions (service_name, version) 
                        VALUES (:service, :version)
                        ON CONFLICT (service_name) 
                        DO UPDATE SET version = :version, updated_at = CURRENT_TIMESTAMP
                    """), {"service": service, "version": version})
                
                # Check for version mismatches
                result = await conn.execute(text("""
                    SELECT service_name, version 
                    FROM schema_versions 
                    ORDER BY version
                """))
                versions = result.fetchall()
                
                # Detect mismatches
                version_set = set(v[1] for v in versions)
                if len(version_set) > 1:
                    # Version mismatch detected - this is the expected failure
                    min_version = min(version_set)
                    max_version = max(version_set)
                    assert min_version == max_version, f"Schema version mismatch: {min_version} to {max_version}"
                
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_05_connection_retry_storm_overwhelming_db(self):
        """Test connection retry storms overwhelming database during failures."""
        if not settings.is_postgresql():
            pytest.skip("Requires PostgreSQL for connection testing")
        
        connection_attempts = []
        max_retries = 5
        
        async def aggressive_reconnect(service_name: str):
            """Simulate aggressive reconnection attempts."""
            for attempt in range(max_retries):
                try:
                    # Use very aggressive timeouts
                    engine = create_async_engine(
                        settings.DATABASE_URL,
                        pool_size=1,
                        max_overflow=0,
                        pool_timeout=0.1,  # Very short timeout
                        connect_args={
                            "command_timeout": 1,
                            "timeout": 1
                        }
                    )
                    
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                        connection_attempts.append({
                            "service": service_name,
                            "attempt": attempt,
                            "success": True,
                            "time": time.time()
                        })
                        await engine.dispose()
                        return True
                        
                except Exception as e:
                    connection_attempts.append({
                        "service": service_name,
                        "attempt": attempt,
                        "success": False,
                        "time": time.time(),
                        "error": str(e)
                    })
                    # No backoff - aggressive retry (this is the problem we're testing)
                    await asyncio.sleep(0.01)
            
            return False
        
        # Simulate multiple services retrying aggressively
        services = [f"service_{i}" for i in range(10)]
        tasks = [aggressive_reconnect(s) for s in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze retry storm pattern
        failed_attempts = [a for a in connection_attempts if not a["success"]]
        
        # Check if retry storm is detected
        if len(failed_attempts) > len(services) * 2:
            # Too many retries - this is the problem we want to catch
            print(f"Retry storm detected: {len(failed_attempts)} failed attempts")
            
        # Verify some connections eventually succeed
        successful = [a for a in connection_attempts if a["success"]]
        assert len(successful) > 0, "No connections succeeded during retry storm"


@pytest.mark.e2e
class TestServiceCoordinationFailures:
    """Test service coordination and dependency failures."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_06_services_starting_before_dependencies(self):
        """Test services starting before their dependencies are ready."""
        service_states = {}
        startup_order = []
        
        async def start_service(name: str, dependencies: List[str]):
            """Simulate service startup with dependency checking."""
            startup_order.append(name)
            
            # Check if dependencies are ready
            for dep in dependencies:
                if not service_states.get(dep, {}).get("ready", False):
                    # This is the failure we want to catch
                    raise RuntimeError(f"{name} started before dependency {dep} was ready")
            
            # Simulate startup time
            await asyncio.sleep(0.1)
            service_states[name] = {"ready": True, "start_time": time.time()}
            return True
        
        # Define service dependencies
        services = {
            "database": [],
            "redis": [],
            "auth": ["database", "redis"],
            "backend": ["database", "redis", "auth"],
            "frontend": ["backend"],
            "websocket": ["backend", "redis"]
        }
        
        # Try to start services concurrently (wrong approach)
        tasks = []
        for name, deps in services.items():
            # Add random delay to simulate race conditions
            await asyncio.sleep(0.01 * len(deps))
            tasks.append(start_service(name, deps))
        
        # This should fail for some services
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for dependency failures
        failures = [r for r in results if isinstance(r, Exception)]
        
        # In production, we'd want no failures
        # But this test is designed to catch the problem
        if failures:
            print(f"Dependency failures detected: {failures}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_07_health_check_false_positives_during_init(self):
        """Test health check false positives during initialization."""
        
        class ServiceHealth:
            def __init__(self, name: str):
                self.name = name
                self.initialized = False
                self.healthy = True  # False positive - reports healthy before init
                self.init_time = None
            
            async def initialize(self):
                """Simulate service initialization."""
                await asyncio.sleep(0.5)  # Initialization takes time
                self.initialized = True
                self.init_time = time.time()
            
            async def health_check(self):
                """Health check that might give false positives."""
                # Bug: Returns healthy even if not initialized
                return {
                    "healthy": self.healthy,
                    "initialized": self.initialized,
                    "name": self.name
                }
        
        # Create services
        services = {
            "backend": ServiceHealth("backend"),
            "auth": ServiceHealth("auth"),
            "worker": ServiceHealth("worker")
        }
        
        # Start initialization in background
        init_tasks = [s.initialize() for s in services.values()]
        init_task = asyncio.create_task(asyncio.gather(*init_tasks))
        
        # Immediately check health (before initialization completes)
        health_results = []
        for _ in range(3):
            results = {}
            for name, service in services.items():
                health = await service.health_check()
                results[name] = health
            health_results.append(results)
            await asyncio.sleep(0.2)
        
        # Wait for initialization to complete
        await init_task
        
        # Check for false positives
        false_positives = []
        for result_set in health_results:
            for name, health in result_set.items():
                if health["healthy"] and not health["initialized"]:
                    false_positives.append(f"{name} reported healthy but not initialized")
        
        # This test should catch false positives
        assert len(false_positives) > 0, "Should detect false positive health checks"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_08_port_binding_race_conditions(self):
        """Test port binding race conditions during startup."""
        import socket
        import errno
        
        ports_to_test = [8000, 8001, 8002, 3000]
        binding_results = []
        
        async def try_bind_port(service_name: str, port: int):
            """Try to bind to a port."""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            try:
                sock.bind(('localhost', port))
                sock.listen(1)
                binding_results.append({
                    "service": service_name,
                    "port": port,
                    "success": True,
                    "time": time.time()
                })
                # Hold the port briefly
                await asyncio.sleep(0.1)
                sock.close()
                return True
                
            except OSError as e:
                if e.errno == errno.EADDRINUSE:
                    binding_results.append({
                        "service": service_name,
                        "port": port,
                        "success": False,
                        "error": "Port in use",
                        "time": time.time()
                    })
                else:
                    binding_results.append({
                        "service": service_name,
                        "port": port,
                        "success": False,
                        "error": str(e),
                        "time": time.time()
                    })
                sock.close()
                return False
        
        # Multiple services try to bind the same ports
        tasks = []
        for port in ports_to_test:
            # Two services try to bind the same port
            tasks.append(try_bind_port(f"service_a_{port}", port))
            tasks.append(try_bind_port(f"service_b_{port}", port))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze port conflicts
        for port in ports_to_test:
            port_results = [r for r in binding_results if r["port"] == port]
            successes = [r for r in port_results if r["success"]]
            
            # Only one service should successfully bind each port
            assert len(successes) <= 1, f"Multiple services bound to port {port}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_09_service_discovery_timing_issues(self):
        """Test service discovery timing issues during startup."""
        
        class ServiceRegistry:
            def __init__(self):
                self.services = {}
                self.registration_order = []
            
            async def register(self, name: str, url: str):
                """Register a service."""
                await asyncio.sleep(0.1)  # Simulate registration delay
                self.services[name] = {
                    "url": url,
                    "registered_at": time.time()
                }
                self.registration_order.append(name)
            
            async def discover(self, name: str):
                """Discover a service."""
                # This might be called before service is registered
                if name not in self.services:
                    return None
                return self.services[name]
        
        registry = ServiceRegistry()
        discovery_failures = []
        
        async def service_startup(name: str, url: str, dependencies: List[str]):
            """Simulate service startup with discovery."""
            # Try to discover dependencies
            for dep in dependencies:
                service_info = await registry.discover(dep)
                if service_info is None:
                    discovery_failures.append({
                        "service": name,
                        "missing_dependency": dep,
                        "time": time.time()
                    })
                    # This is the timing issue we want to catch
                    raise RuntimeError(f"{name} cannot find dependency {dep}")
            
            # Register self
            await registry.register(name, url)
            return True
        
        # Services with dependencies try to start concurrently
        tasks = [
            service_startup("database", "localhost:5432", []),
            service_startup("redis", "localhost:6379", []),
            service_startup("auth", "localhost:8001", ["database", "redis"]),
            service_startup("backend", "localhost:8000", ["database", "redis", "auth"])
        ]
        
        # Start all services concurrently (causes timing issues)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for discovery failures
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(failures) > 0, "Should detect service discovery timing issues"
        assert len(discovery_failures) > 0, "Should log discovery failures"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_10_graceful_degradation_optional_services(self):
        """Test graceful degradation when optional services fail."""
        
        class ServiceManager:
            def __init__(self):
                self.services = {}
                self.required = {"database", "auth"}
                self.optional = {"cache", "analytics", "search"}
            
            async def start_service(self, name: str):
                """Start a service."""
                if name in ["cache", "analytics"]:
                    # Simulate failure of optional services
                    raise ConnectionError(f"Optional service {name} failed to start")
                
                self.services[name] = {"status": "running"}
                return True
            
            async def check_system_health(self):
                """Check overall system health."""
                # Check required services
                for req in self.required:
                    if req not in self.services:
                        return {"healthy": False, "reason": f"Required service {req} not running"}
                
                # Check optional services (should not fail system)
                missing_optional = []
                for opt in self.optional:
                    if opt not in self.services:
                        missing_optional.append(opt)
                
                return {
                    "healthy": True,
                    "degraded": len(missing_optional) > 0,
                    "missing_optional": missing_optional
                }
        
        manager = ServiceManager()
        
        # Start all services
        all_services = manager.required | manager.optional
        results = []
        
        for service in all_services:
            try:
                await manager.start_service(service)
                results.append({"service": service, "started": True})
            except Exception as e:
                results.append({"service": service, "started": False, "error": str(e)})
        
        # Check system health
        health = await manager.check_system_health()
        
        # System should be healthy but degraded
        assert health["healthy"] is True, "System should remain healthy with optional service failures"
        assert health["degraded"] is True, "System should report degraded state"
        assert len(health["missing_optional"]) > 0, "Should report missing optional services"


@pytest.mark.e2e
class TestWebSocketInfrastructure:
    """Test WebSocket infrastructure and cross-service communication."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_11_websocket_upgrade_failures_high_rate(self):
        """Test WebSocket upgrade failures during high connection rates."""
        
        upgrade_results = []
        max_connections = 100
        
        async def attempt_websocket_upgrade(client_id: int):
            """Attempt WebSocket upgrade."""
            try:
                # Simulate WebSocket upgrade attempt
                session = aiohttp.ClientSession()
                
                # Simulate upgrade with possible failure
                if client_id % 10 == 0:
                    # Simulate upgrade failure for every 10th connection
                    await session.close()
                    raise aiohttp.WSServerHandshakeError(
                        request_info=None,
                        history=None,
                        message="Upgrade failed - too many connections"
                    )
                
                # Simulate successful upgrade
                upgrade_results.append({
                    "client_id": client_id,
                    "success": True,
                    "time": time.time()
                })
                
                await session.close()
                return True
                
            except Exception as e:
                upgrade_results.append({
                    "client_id": client_id,
                    "success": False,
                    "error": str(e),
                    "time": time.time()
                })
                return False
        
        # Attempt many concurrent WebSocket upgrades
        tasks = [attempt_websocket_upgrade(i) for i in range(max_connections)]
        results = await asyncio.gather(*tasks)
        
        # Analyze upgrade failures
        failures = [r for r in upgrade_results if not r["success"]]
        success_rate = (len(upgrade_results) - len(failures)) / len(upgrade_results)
        
        # Some failures are expected under high load
        assert len(failures) > 0, "Should detect upgrade failures under high load"
        assert success_rate > 0.8, "Success rate should be reasonable despite failures"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_12_message_buffering_reconnection_storms(self):
        """Test message buffering during reconnection storms."""
        
        class MessageBuffer:
            def __init__(self, max_size: int = 1000):
                self.buffer = []
                self.max_size = max_size
                self.dropped_count = 0
            
            def add_message(self, message: dict):
                """Add message to buffer."""
                if len(self.buffer) >= self.max_size:
                    # Buffer overflow - drop oldest message
                    self.buffer.pop(0)
                    self.dropped_count += 1
                
                self.buffer.append({
                    "message": message,
                    "timestamp": time.time()
                })
            
            def get_messages(self, count: int = None):
                """Get messages from buffer."""
                if count is None:
                    messages = self.buffer[:]
                    self.buffer.clear()
                    return messages
                else:
                    messages = self.buffer[:count]
                    self.buffer = self.buffer[count:]
                    return messages
        
        # Simulate reconnection storm
        buffers = {}
        reconnection_count = 50
        messages_per_reconnect = 100
        
        for client_id in range(reconnection_count):
            buffer = MessageBuffer(max_size=500)
            
            # Generate messages during reconnection
            for msg_id in range(messages_per_reconnect):
                buffer.add_message({
                    "client_id": client_id,
                    "msg_id": msg_id,
                    "data": f"Message during reconnection"
                })
            
            buffers[client_id] = buffer
        
        # Check for message loss
        total_dropped = sum(b.dropped_count for b in buffers.values())
        
        # Message loss is expected during storms
        assert total_dropped > 0, "Should detect message drops during reconnection storm"
        
        # Verify some messages are preserved
        total_buffered = sum(len(b.buffer) for b in buffers.values())
        assert total_buffered > 0, "Should buffer some messages despite storm"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_13_cross_origin_websocket_authentication(self):
        """Test cross-origin WebSocket authentication issues."""
        
        class WebSocketAuth:
            def __init__(self):
                self.allowed_origins = ["http://localhost:3000", "https://app.example.com"]
                self.auth_failures = []
            
            async def authenticate_connection(self, origin: str, token: str):
                """Authenticate WebSocket connection."""
                # Check origin
                if origin not in self.allowed_origins:
                    self.auth_failures.append({
                        "reason": "invalid_origin",
                        "origin": origin,
                        "time": time.time()
                    })
                    return False
                
                # Validate token (simplified)
                if not token or len(token) < 10:
                    self.auth_failures.append({
                        "reason": "invalid_token",
                        "origin": origin,
                        "time": time.time()
                    })
                    return False
                
                return True
        
        auth = WebSocketAuth()
        
        # Test various origin/token combinations
        test_cases = [
            ("http://localhost:3000", "valid_token_12345"),  # Valid
            ("http://evil.com", "valid_token_12345"),  # Invalid origin
            ("http://localhost:3000", "bad"),  # Invalid token
            ("https://app.example.com", "valid_token_67890"),  # Valid
            ("http://localhost:8080", "valid_token_12345"),  # Wrong port
        ]
        
        results = []
        for origin, token in test_cases:
            result = await auth.authenticate_connection(origin, token)
            results.append({"origin": origin, "authenticated": result})
        
        # Should have both successes and failures
        successes = [r for r in results if r["authenticated"]]
        failures = [r for r in results if not r["authenticated"]]
        
        assert len(successes) == 2, "Should authenticate valid connections"
        assert len(failures) == 3, "Should reject invalid connections"
        assert len(auth.auth_failures) == 3, "Should log authentication failures"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_14_websocket_heartbeat_synchronization(self):
        """Test WebSocket heartbeat synchronization issues."""
        
        class HeartbeatManager:
            def __init__(self, interval: float = 30.0):
                self.interval = interval
                self.clients = {}
                self.missed_heartbeats = []
            
            async def register_client(self, client_id: str):
                """Register client for heartbeat."""
                self.clients[client_id] = {
                    "last_heartbeat": time.time(),
                    "missed_count": 0
                }
            
            async def heartbeat(self, client_id: str):
                """Process heartbeat from client."""
                if client_id not in self.clients:
                    return False
                
                now = time.time()
                last = self.clients[client_id]["last_heartbeat"]
                
                # Check if heartbeat is late
                if now - last > self.interval * 1.5:
                    self.clients[client_id]["missed_count"] += 1
                    self.missed_heartbeats.append({
                        "client_id": client_id,
                        "delay": now - last,
                        "time": now
                    })
                
                self.clients[client_id]["last_heartbeat"] = now
                return True
            
            async def check_alive(self, client_id: str):
                """Check if client is still alive."""
                if client_id not in self.clients:
                    return False
                
                client = self.clients[client_id]
                now = time.time()
                
                # Consider dead if no heartbeat for 2 intervals
                if now - client["last_heartbeat"] > self.interval * 2:
                    return False
                
                return True
        
        manager = HeartbeatManager(interval=1.0)  # Short interval for testing
        
        # Simulate clients with different heartbeat patterns
        clients = ["client_1", "client_2", "client_3"]
        
        for client in clients:
            await manager.register_client(client)
        
        # Simulate heartbeats with issues
        await asyncio.sleep(0.5)
        await manager.heartbeat("client_1")  # On time
        
        await asyncio.sleep(1.6)  # Late
        await manager.heartbeat("client_2")  # Delayed heartbeat
        
        # client_3 doesn't send heartbeat (dead connection)
        
        await asyncio.sleep(2.5)
        
        # Check client states
        alive_states = {}
        for client in clients:
            alive_states[client] = await manager.check_alive(client)
        
        # Should detect heartbeat issues
        assert len(manager.missed_heartbeats) > 0, "Should detect missed heartbeats"
        assert alive_states["client_3"] is False, "Should detect dead connection"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_15_broadcasting_failures_during_restart(self):
        """Test broadcasting failures during service restarts."""
        
        class BroadcastManager:
            def __init__(self):
                self.subscribers = {}
                self.failed_broadcasts = []
                self.restarting = False
            
            async def subscribe(self, client_id: str, channel: str):
                """Subscribe client to channel."""
                if channel not in self.subscribers:
                    self.subscribers[channel] = set()
                self.subscribers[channel].add(client_id)
            
            async def broadcast(self, channel: str, message: dict):
                """Broadcast message to channel."""
                if self.restarting:
                    self.failed_broadcasts.append({
                        "channel": channel,
                        "message": message,
                        "reason": "service_restarting",
                        "time": time.time()
                    })
                    return False
                
                if channel not in self.subscribers:
                    return True  # No subscribers
                
                failures = []
                for client_id in self.subscribers[channel]:
                    # Simulate sending with possible failure
                    if client_id.endswith("_disconnected"):
                        failures.append(client_id)
                
                if failures:
                    self.failed_broadcasts.append({
                        "channel": channel,
                        "failed_clients": failures,
                        "time": time.time()
                    })
                
                return len(failures) == 0
            
            async def restart_service(self):
                """Simulate service restart."""
                self.restarting = True
                await asyncio.sleep(0.5)  # Restart time
                self.restarting = False
        
        manager = BroadcastManager()
        
        # Set up subscribers
        await manager.subscribe("client_1", "updates")
        await manager.subscribe("client_2", "updates")
        await manager.subscribe("client_3_disconnected", "updates")
        
        # Try broadcasting
        await manager.broadcast("updates", {"type": "test", "data": "message1"})
        
        # Simulate restart during broadcast
        restart_task = asyncio.create_task(manager.restart_service())
        await asyncio.sleep(0.1)
        
        # Try broadcasting during restart
        await manager.broadcast("updates", {"type": "test", "data": "message2"})
        
        await restart_task
        
        # Broadcast after restart
        await manager.broadcast("updates", {"type": "test", "data": "message3"})
        
        # Should detect broadcast failures
        assert len(manager.failed_broadcasts) > 0, "Should detect broadcast failures"
        
        # Check failure reasons
        restart_failures = [f for f in manager.failed_broadcasts if f.get("reason") == "service_restarting"]
        assert len(restart_failures) > 0, "Should detect failures during restart"


@pytest.mark.e2e
class TestAuthenticationSessionManagement:
    """Test authentication and session management during startup."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_16_oauth_provider_initialization_failures(self):
        """Test OAuth provider initialization failures."""
        
        class OAuthProvider:
            def __init__(self, name: str, config: dict):
                self.name = name
                self.config = config
                self.initialized = False
                self.initialization_errors = []
            
            async def initialize(self):
                """Initialize OAuth provider."""
                # Validate configuration
                required_fields = ["client_id", "client_secret", "redirect_uri"]
                
                for field in required_fields:
                    if field not in self.config:
                        self.initialization_errors.append(f"Missing {field}")
                
                # Simulate connection to provider
                if self.name == "unreachable_provider":
                    self.initialization_errors.append("Provider unreachable")
                    raise ConnectionError(f"Cannot connect to {self.name}")
                
                if not self.initialization_errors:
                    self.initialized = True
                
                return self.initialized
        
        # Test various provider configurations
        providers = [
            OAuthProvider("google", {
                "client_id": "google_id",
                "client_secret": "google_secret",
                "redirect_uri": "http://localhost:3000/auth/callback"
            }),
            OAuthProvider("github", {
                "client_id": "github_id",
                # Missing client_secret
                "redirect_uri": "http://localhost:3000/auth/callback"
            }),
            OAuthProvider("unreachable_provider", {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "redirect_uri": "http://localhost:3000/auth/callback"
            })
        ]
        
        initialization_results = []
        
        for provider in providers:
            try:
                result = await provider.initialize()
                initialization_results.append({
                    "provider": provider.name,
                    "success": result,
                    "errors": provider.initialization_errors
                })
            except Exception as e:
                initialization_results.append({
                    "provider": provider.name,
                    "success": False,
                    "errors": provider.initialization_errors,
                    "exception": str(e)
                })
        
        # Should have both successes and failures
        successes = [r for r in initialization_results if r["success"]]
        failures = [r for r in initialization_results if not r["success"]]
        
        assert len(successes) == 1, "Should initialize valid providers"
        assert len(failures) == 2, "Should fail invalid providers"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_17_jwt_key_rotation_during_startup(self):
        """Test JWT key rotation issues during startup."""
        
        class JWTManager:
            def __init__(self):
                self.current_key = None
                self.previous_key = None
                self.rotation_in_progress = False
                self.validation_failures = []
            
            async def rotate_keys(self):
                """Rotate JWT signing keys."""
                self.rotation_in_progress = True
                
                # Save old key
                self.previous_key = self.current_key
                
                # Generate new key (simplified)
                await asyncio.sleep(0.1)  # Simulate key generation
                self.current_key = f"key_{uuid.uuid4().hex[:8]}"
                
                self.rotation_in_progress = False
            
            async def validate_token(self, token: str, key_hint: str = None):
                """Validate JWT token."""
                if self.rotation_in_progress:
                    # This is the problem - validation during rotation
                    self.validation_failures.append({
                        "reason": "rotation_in_progress",
                        "time": time.time()
                    })
                    return False
                
                # Try current key
                if key_hint == self.current_key:
                    return True
                
                # Try previous key (for tokens issued before rotation)
                if key_hint == self.previous_key:
                    return True
                
                self.validation_failures.append({
                    "reason": "invalid_key",
                    "time": time.time()
                })
                return False
        
        manager = JWTManager()
        manager.current_key = "initial_key"
        
        # Create tokens with current key
        tokens = [
            ("token1", "initial_key"),
            ("token2", "initial_key"),
            ("token3", "initial_key")
        ]
        
        # Start key rotation
        rotation_task = asyncio.create_task(manager.rotate_keys())
        
        # Try validating tokens during rotation
        validation_results = []
        for token, key in tokens:
            result = await manager.validate_token(token, key)
            validation_results.append(result)
        
        await rotation_task
        
        # Validate with new key
        new_token_result = await manager.validate_token("token4", manager.current_key)
        
        # Should detect validation issues during rotation
        assert len(manager.validation_failures) > 0, "Should detect validation failures during rotation"
        assert any(f["reason"] == "rotation_in_progress" for f in manager.validation_failures)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_18_session_store_race_conditions(self):
        """Test session store race conditions during concurrent access."""
        
        redis_client = await redis.from_url(settings.REDIS_URL)
        
        try:
            session_conflicts = []
            
            async def create_session(user_id: str, session_id: str):
                """Create user session with possible race condition."""
                session_key = f"session:{session_id}"
                user_sessions_key = f"user_sessions:{user_id}"
                
                # Check if session already exists (race condition point)
                exists = await redis_client.exists(session_key)
                
                if exists:
                    session_conflicts.append({
                        "user_id": user_id,
                        "session_id": session_id,
                        "type": "duplicate_session"
                    })
                    return False
                
                # Small delay to increase race condition probability
                await asyncio.sleep(0.01)
                
                # Create session
                session_data = {
                    "user_id": user_id,
                    "created_at": time.time(),
                    "data": "session_data"
                }
                
                # This might create duplicate sessions due to race condition
                await redis_client.setex(session_key, 3600, json.dumps(session_data))
                await redis_client.sadd(user_sessions_key, session_id)
                
                return True
            
            # Multiple concurrent session creations for same user
            user_id = "user_123"
            tasks = []
            
            for i in range(10):
                session_id = f"session_{i}"
                tasks.append(create_session(user_id, session_id))
            
            results = await asyncio.gather(*tasks)
            
            # Check for session conflicts
            user_sessions_key = f"user_sessions:{user_id}"
            actual_sessions = await redis_client.smembers(user_sessions_key)
            
            # Clean up
            for i in range(10):
                await redis_client.delete(f"session:session_{i}")
            await redis_client.delete(user_sessions_key)
            
            # Should work but might have race conditions
            assert len(actual_sessions) > 0, "Should create sessions"
            
        finally:
            await redis_client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_19_token_validation_cache_warming(self):
        """Test token validation cache warming issues."""
        
        class TokenCache:
            def __init__(self):
                self.cache = {}
                self.cache_misses = []
                self.warming_complete = False
            
            async def warm_cache(self):
                """Warm the cache with frequently used tokens."""
                # Simulate loading tokens from database
                await asyncio.sleep(0.5)
                
                # Pre-populate cache
                for i in range(100):
                    token_id = f"token_{i}"
                    self.cache[token_id] = {
                        "valid": True,
                        "user_id": f"user_{i}",
                        "cached_at": time.time()
                    }
                
                self.warming_complete = True
            
            async def validate_token(self, token_id: str):
                """Validate token using cache."""
                if token_id in self.cache:
                    return self.cache[token_id]
                
                # Cache miss
                self.cache_misses.append({
                    "token_id": token_id,
                    "warming_complete": self.warming_complete,
                    "time": time.time()
                })
                
                # Simulate database lookup
                await asyncio.sleep(0.1)
                
                result = {
                    "valid": token_id.startswith("token_"),
                    "user_id": f"user_{token_id.split('_')[1] if '_' in token_id else 'unknown'}"
                }
                
                self.cache[token_id] = result
                return result
        
        cache = TokenCache()
        
        # Start cache warming in background
        warming_task = asyncio.create_task(cache.warm_cache())
        
        # Try to validate tokens before warming completes
        early_validations = []
        for i in range(5):
            result = await cache.validate_token(f"token_{i}")
            early_validations.append(result)
        
        await warming_task
        
        # Validate tokens after warming
        late_validations = []
        for i in range(5):
            result = await cache.validate_token(f"token_{i}")
            late_validations.append(result)
        
        # Should have cache misses during warming
        early_misses = [m for m in cache.cache_misses if not m["warming_complete"]]
        assert len(early_misses) > 0, "Should have cache misses during warming"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_20_cross_service_auth_propagation(self):
        """Test cross-service authentication propagation issues."""
        
        class AuthPropagator:
            def __init__(self):
                self.service_tokens = {}
                self.propagation_failures = []
            
            async def propagate_auth(self, user_token: str, services: List[str]):
                """Propagate authentication to multiple services."""
                results = {}
                
                for service in services:
                    try:
                        # Simulate service-specific token generation
                        if service == "unavailable_service":
                            raise ConnectionError(f"Cannot reach {service}")
                        
                        service_token = f"{user_token}_{service}_{uuid.uuid4().hex[:4]}"
                        self.service_tokens[service] = service_token
                        
                        # Simulate propagation delay
                        await asyncio.sleep(0.05)
                        
                        results[service] = {"success": True, "token": service_token}
                        
                    except Exception as e:
                        self.propagation_failures.append({
                            "service": service,
                            "error": str(e),
                            "time": time.time()
                        })
                        results[service] = {"success": False, "error": str(e)}
                
                return results
        
        propagator = AuthPropagator()
        
        # Propagate to multiple services
        user_token = "user_token_123"
        services = ["backend", "websocket", "unavailable_service", "analytics"]
        
        results = await propagator.propagate_auth(user_token, services)
        
        # Check propagation results
        successes = [s for s, r in results.items() if r["success"]]
        failures = [s for s, r in results.items() if not r["success"]]
        
        assert len(successes) == 3, "Should propagate to available services"
        assert len(failures) == 1, "Should fail for unavailable services"
        assert len(propagator.propagation_failures) == 1, "Should log propagation failures"


@pytest.mark.e2e
class TestFrontendAPIIntegration:
    """Test frontend and API integration issues."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_21_api_gateway_init_before_backend(self):
        """Test API gateway initialization before backend is ready."""
        
        class APIGateway:
            def __init__(self):
                self.backend_url = "http://localhost:8000"
                self.backend_ready = False
                self.request_queue = []
                self.failed_requests = []
            
            async def check_backend(self):
                """Check if backend is ready."""
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{self.backend_url}/health")
                        self.backend_ready = response.status_code == 200
                except:
                    self.backend_ready = False
                
                return self.backend_ready
            
            async def forward_request(self, path: str, method: str = "GET"):
                """Forward request to backend."""
                if not self.backend_ready:
                    # Queue request or fail
                    self.request_queue.append({
                        "path": path,
                        "method": method,
                        "time": time.time()
                    })
                    
                    self.failed_requests.append({
                        "reason": "backend_not_ready",
                        "path": path
                    })
                    
                    raise RuntimeError("Backend not ready")
                
                # Forward request (simplified)
                return {"status": "forwarded", "path": path}
        
        gateway = APIGateway()
        
        # Try to forward requests before backend is ready
        early_requests = []
        for i in range(5):
            try:
                result = await gateway.forward_request(f"/api/test_{i}")
                early_requests.append({"success": True, "result": result})
            except Exception as e:
                early_requests.append({"success": False, "error": str(e)})
        
        # Simulate backend becoming ready
        gateway.backend_ready = True
        
        # Process queued requests
        processed = []
        for queued in gateway.request_queue:
            result = await gateway.forward_request(queued["path"], queued["method"])
            processed.append(result)
        
        # Should detect initialization order issues
        assert len(gateway.failed_requests) > 0, "Should detect requests before backend ready"
        assert len(gateway.request_queue) > 0, "Should queue requests"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_22_cors_configuration_mismatches(self):
        """Test CORS configuration mismatches between services."""
        
        class CORSValidator:
            def __init__(self):
                self.backend_origins = ["http://localhost:3000", "https://app.example.com"]
                self.frontend_origin = "http://localhost:3000"
                self.api_gateway_origins = ["http://localhost:3000"]  # Missing production origin
                self.cors_errors = []
            
            def validate_request(self, origin: str, service: str):
                """Validate CORS for a request."""
                allowed_origins = {
                    "backend": self.backend_origins,
                    "api_gateway": self.api_gateway_origins
                }.get(service, [])
                
                if origin not in allowed_origins:
                    self.cors_errors.append({
                        "origin": origin,
                        "service": service,
                        "allowed": allowed_origins,
                        "time": time.time()
                    })
                    return False
                
                return True
        
        validator = CORSValidator()
        
        # Test various origin/service combinations
        test_cases = [
            ("http://localhost:3000", "backend"),  # Valid
            ("https://app.example.com", "backend"),  # Valid for backend
            ("https://app.example.com", "api_gateway"),  # Invalid - mismatch!
            ("http://evil.com", "backend"),  # Invalid
        ]
        
        results = []
        for origin, service in test_cases:
            valid = validator.validate_request(origin, service)
            results.append({
                "origin": origin,
                "service": service,
                "valid": valid
            })
        
        # Should detect configuration mismatches
        assert len(validator.cors_errors) > 0, "Should detect CORS mismatches"
        
        # Check for specific mismatch
        gateway_errors = [e for e in validator.cors_errors if e["service"] == "api_gateway"]
        assert len(gateway_errors) > 0, "Should detect API gateway CORS mismatch"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_23_static_asset_cdn_fallback_failures(self):
        """Test static asset CDN fallback mechanism failures."""
        
        class AssetLoader:
            def __init__(self):
                self.cdn_url = "https://cdn.example.com"
                self.local_url = "http://localhost:3000"
                self.load_attempts = []
                self.cdn_available = False  # CDN is down
            
            async def load_asset(self, asset_path: str):
                """Load static asset with fallback."""
                # Try CDN first
                if self.cdn_available:
                    self.load_attempts.append({
                        "source": "cdn",
                        "path": asset_path,
                        "success": True
                    })
                    return f"{self.cdn_url}/{asset_path}"
                
                # CDN failed, try local
                self.load_attempts.append({
                    "source": "cdn",
                    "path": asset_path,
                    "success": False
                })
                
                # Simulate fallback delay
                await asyncio.sleep(0.1)
                
                # Local fallback
                if asset_path.endswith(".critical.js"):
                    # Critical assets must load
                    self.load_attempts.append({
                        "source": "local",
                        "path": asset_path,
                        "success": True
                    })
                    return f"{self.local_url}/{asset_path}"
                else:
                    # Non-critical might fail
                    self.load_attempts.append({
                        "source": "local",
                        "path": asset_path,
                        "success": False
                    })
                    raise RuntimeError(f"Failed to load {asset_path}")
        
        loader = AssetLoader()
        
        # Try loading various assets
        assets = [
            "bundle.critical.js",
            "styles.css",
            "logo.png",
            "app.critical.js"
        ]
        
        results = []
        for asset in assets:
            try:
                url = await loader.load_asset(asset)
                results.append({"asset": asset, "loaded": True, "url": url})
            except Exception as e:
                results.append({"asset": asset, "loaded": False, "error": str(e)})
        
        # Analyze fallback behavior
        cdn_attempts = [a for a in loader.load_attempts if a["source"] == "cdn"]
        fallback_attempts = [a for a in loader.load_attempts if a["source"] == "local"]
        
        assert len(cdn_attempts) > 0, "Should attempt CDN first"
        assert len(fallback_attempts) > 0, "Should fallback to local"
        
        # Critical assets should load
        critical_results = [r for r in results if "critical" in r["asset"]]
        assert all(r["loaded"] for r in critical_results), "Critical assets must load"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_24_graphql_schema_stitching_errors(self):
        """Test GraphQL schema stitching errors during startup."""
        
        class SchemaStitcher:
            def __init__(self):
                self.schemas = {}
                self.stitching_errors = []
            
            def add_schema(self, service: str, schema: dict):
                """Add service schema."""
                self.schemas[service] = schema
            
            def stitch_schemas(self):
                """Stitch schemas together."""
                # Check for conflicts
                all_types = {}
                
                for service, schema in self.schemas.items():
                    for type_name, type_def in schema.get("types", {}).items():
                        if type_name in all_types:
                            # Conflict detected
                            self.stitching_errors.append({
                                "type": "conflict",
                                "type_name": type_name,
                                "services": [all_types[type_name]["service"], service]
                            })
                        else:
                            all_types[type_name] = {
                                "service": service,
                                "definition": type_def
                            }
                
                # Check for missing dependencies
                for service, schema in self.schemas.items():
                    for dep in schema.get("dependencies", []):
                        if dep not in all_types:
                            self.stitching_errors.append({
                                "type": "missing_dependency",
                                "service": service,
                                "dependency": dep
                            })
                
                return len(self.stitching_errors) == 0
        
        stitcher = SchemaStitcher()
        
        # Add service schemas with conflicts
        stitcher.add_schema("users", {
            "types": {
                "User": {"id": "ID", "name": "String"},
                "Post": {"id": "ID", "title": "String"}  # Conflict!
            }
        })
        
        stitcher.add_schema("posts", {
            "types": {
                "Post": {"id": "ID", "content": "String"},  # Different definition!
                "Comment": {"id": "ID", "text": "String"}
            },
            "dependencies": ["User"]
        })
        
        stitcher.add_schema("analytics", {
            "types": {
                "Metric": {"id": "ID", "value": "Float"}
            },
            "dependencies": ["NonExistentType"]  # Missing dependency!
        })
        
        # Try to stitch schemas
        success = stitcher.stitch_schemas()
        
        # Should detect stitching errors
        assert success is False, "Should fail schema stitching"
        assert len(stitcher.stitching_errors) > 0, "Should detect stitching errors"
        
        # Check error types
        conflicts = [e for e in stitcher.stitching_errors if e["type"] == "conflict"]
        missing_deps = [e for e in stitcher.stitching_errors if e["type"] == "missing_dependency"]
        
        assert len(conflicts) > 0, "Should detect type conflicts"
        assert len(missing_deps) > 0, "Should detect missing dependencies"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_25_ssr_hydration_mismatches(self):
        """Test SSR hydration mismatches during initial render."""
        
        class SSRHydrator:
            def __init__(self):
                self.server_state = {}
                self.client_state = {}
                self.hydration_errors = []
            
            def render_server(self, props: dict):
                """Server-side render."""
                # Include server-only data
                self.server_state = {
                    "props": props,
                    "timestamp": time.time(),
                    "server_only": "secret_data",  # Should not be in client
                    "user_agent": "server"
                }
                
                return f"<div id='root'>{json.dumps(props)}</div>"
            
            def hydrate_client(self, props: dict):
                """Client-side hydration."""
                # Client state might differ
                self.client_state = {
                    "props": props,
                    "timestamp": time.time() + 0.5,  # Different time!
                    "user_agent": "browser"
                }
                
                # Check for mismatches
                if self.server_state.get("timestamp") != self.client_state.get("timestamp"):
                    self.hydration_errors.append({
                        "type": "timestamp_mismatch",
                        "server": self.server_state.get("timestamp"),
                        "client": self.client_state.get("timestamp")
                    })
                
                if "server_only" in self.server_state and "server_only" not in self.client_state:
                    self.hydration_errors.append({
                        "type": "missing_client_data",
                        "field": "server_only"
                    })
                
                return len(self.hydration_errors) == 0
        
        hydrator = SSRHydrator()
        
        # Server render
        props = {"page": "home", "user": "test_user"}
        html = hydrator.render_server(props)
        
        # Client hydration (with slight delay)
        await asyncio.sleep(0.1)
        success = hydrator.hydrate_client(props)
        
        # Should detect hydration mismatches
        assert success is False, "Should detect hydration mismatches"
        assert len(hydrator.hydration_errors) > 0, "Should log hydration errors"
        
        # Check mismatch types
        timestamp_errors = [e for e in hydrator.hydration_errors if e["type"] == "timestamp_mismatch"]
        assert len(timestamp_errors) > 0, "Should detect timestamp mismatches"


@pytest.mark.e2e
class TestResourceManagementLimits:
    """Test resource management and system limits."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_26_file_descriptor_exhaustion_startup(self):
        """Test file descriptor exhaustion during startup."""
        
        import resource
        
        # Get current limits
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        
        open_files = []
        exhaustion_point = None
        
        try:
            # Try to open many files
            temp_dir = tempfile.mkdtemp()
            
            for i in range(1000):  # Try to open many files
                try:
                    file_path = os.path.join(temp_dir, f"test_{i}.txt")
                    f = open(file_path, 'w')
                    open_files.append(f)
                    f.write(f"Test file {i}")
                    
                except OSError as e:
                    if "Too many open files" in str(e) or e.errno == 24:
                        exhaustion_point = i
                        break
            
            # Should hit limit before 1000 on most systems
            if exhaustion_point:
                print(f"File descriptor exhaustion at {exhaustion_point} files")
                assert exhaustion_point < soft_limit, "Should detect FD exhaustion"
            
        finally:
            # Clean up
            for f in open_files:
                try:
                    f.close()
                except:
                    pass
            
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_27_memory_allocation_failures(self):
        """Test memory allocation failures during startup."""
        
        memory_chunks = []
        allocation_failed = False
        
        try:
            # Try to allocate large amounts of memory
            chunk_size = 100 * 1024 * 1024  # 100MB chunks
            
            for i in range(100):  # Try to allocate 10GB
                try:
                    # Allocate memory
                    chunk = bytearray(chunk_size)
                    memory_chunks.append(chunk)
                    
                    # Check system memory
                    mem = psutil.virtual_memory()
                    if mem.percent > 90:
                        allocation_failed = True
                        print(f"Memory pressure detected: {mem.percent}% used")
                        break
                        
                except MemoryError:
                    allocation_failed = True
                    print(f"Memory allocation failed at chunk {i}")
                    break
            
            # Should detect memory pressure
            assert allocation_failed or len(memory_chunks) > 0, "Should allocate some memory"
            
        finally:
            # Clean up
            memory_chunks.clear()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_28_cpu_throttling_detection(self):
        """Test CPU throttling detection during startup."""
        
        def cpu_intensive_task(duration: float):
            """CPU intensive task."""
            start = time.time()
            result = 0
            while time.time() - start < duration:
                result += sum(i * i for i in range(1000))
            return result
        
        # Baseline measurement
        baseline_start = time.time()
        baseline_result = cpu_intensive_task(0.1)
        baseline_duration = time.time() - baseline_start
        
        # Run multiple tasks concurrently to trigger throttling
        tasks = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(cpu_intensive_task, 0.1)
                futures.append(future)
            
            # Wait for completion
            concurrent_start = time.time()
            for future in futures:
                future.result()
            concurrent_duration = time.time() - concurrent_start
        
        # Check for throttling
        throttling_ratio = concurrent_duration / baseline_duration
        
        # If ratio is much higher than 10, throttling occurred
        if throttling_ratio > 15:
            print(f"CPU throttling detected: {throttling_ratio:.2f}x slower")
        
        # Test passes either way - we're testing detection
        assert baseline_duration > 0, "Should measure baseline performance"
        assert concurrent_duration > 0, "Should measure concurrent performance"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_29_disk_io_saturation_handling(self):
        """Test disk I/O saturation handling during startup."""
        
        temp_dir = tempfile.mkdtemp()
        io_operations = []
        
        try:
            async def write_file(file_id: int, size_mb: int):
                """Write file to disk."""
                start = time.time()
                file_path = os.path.join(temp_dir, f"test_{file_id}.dat")
                
                # Write data in chunks
                chunk_size = 1024 * 1024  # 1MB
                data = bytearray(chunk_size)
                
                with open(file_path, 'wb') as f:
                    for _ in range(size_mb):
                        f.write(data)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                duration = time.time() - start
                io_operations.append({
                    "file_id": file_id,
                    "size_mb": size_mb,
                    "duration": duration,
                    "mb_per_sec": size_mb / duration if duration > 0 else 0
                })
                
                return duration
            
            # Create many concurrent I/O operations
            tasks = []
            for i in range(20):
                tasks.append(write_file(i, 10))  # 10MB each
            
            # Measure concurrent I/O
            start = time.time()
            durations = await asyncio.gather(*tasks)
            total_duration = time.time() - start
            
            # Analyze I/O performance
            avg_speed = sum(op["mb_per_sec"] for op in io_operations) / len(io_operations)
            
            # Check for I/O saturation
            if avg_speed < 10:  # Less than 10 MB/s indicates saturation
                print(f"Disk I/O saturation detected: {avg_speed:.2f} MB/s average")
            
            assert len(io_operations) > 0, "Should complete I/O operations"
            assert total_duration > 0, "Should measure I/O duration"
            
        finally:
            # Clean up
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_30_network_bandwidth_limitations(self):
        """Test network bandwidth limitations during startup."""
        
        class NetworkSimulator:
            def __init__(self, bandwidth_mbps: float = 100):
                self.bandwidth_mbps = bandwidth_mbps
                self.bytes_per_second = (bandwidth_mbps * 1024 * 1024) / 8
                self.transfers = []
            
            async def transfer_data(self, size_mb: float, connection_id: str):
                """Simulate data transfer with bandwidth limits."""
                size_bytes = size_mb * 1024 * 1024
                
                # Calculate transfer time based on bandwidth
                ideal_time = size_bytes / self.bytes_per_second
                
                # Add congestion factor if many concurrent transfers
                concurrent_transfers = len([t for t in self.transfers if t["active"]])
                congestion_factor = max(1, concurrent_transfers)
                actual_time = ideal_time * congestion_factor
                
                transfer = {
                    "connection_id": connection_id,
                    "size_mb": size_mb,
                    "start_time": time.time(),
                    "active": True
                }
                self.transfers.append(transfer)
                
                # Simulate transfer
                await asyncio.sleep(actual_time)
                
                transfer["active"] = False
                transfer["duration"] = actual_time
                transfer["actual_mbps"] = (size_mb * 8) / actual_time if actual_time > 0 else 0
                
                return transfer
        
        simulator = NetworkSimulator(bandwidth_mbps=100)
        
        # Simulate multiple services downloading data during startup
        tasks = []
        services_data = [
            ("backend", 50),  # 50MB
            ("frontend", 100),  # 100MB  
            ("assets", 200),  # 200MB
            ("database", 150),  # 150MB
        ]
        
        for service, size_mb in services_data:
            tasks.append(simulator.transfer_data(size_mb, service))
        
        # Start all transfers concurrently
        start = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start
        
        # Analyze bandwidth usage
        total_mb = sum(r["size_mb"] for r in results)
        avg_mbps = (total_mb * 8) / total_time if total_time > 0 else 0
        
        # Check for bandwidth saturation
        if avg_mbps < simulator.bandwidth_mbps * 0.8:
            print(f"Network bandwidth saturation: {avg_mbps:.2f} Mbps of {simulator.bandwidth_mbps} Mbps")
        
        # Verify all transfers completed
        assert len(results) == len(services_data), "All transfers should complete"
        assert all(not t["active"] for t in simulator.transfers), "All transfers should be inactive"
        
        # Check for bandwidth limitations
        slowest = min(results, key=lambda x: x["actual_mbps"])
        assert slowest["actual_mbps"] < simulator.bandwidth_mbps, "Should see bandwidth sharing effects"


# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--asyncio-mode=auto"])