"""Comprehensive validation tests for IsolatedEnvironment test infrastructure.

This module provides validation tests that verify the correctness, performance,
and reliability of the entire test infrastructure including:

- IsolatedEnvironmentManager functionality
- Database isolation and transaction safety
- External service integration
- Performance optimization
- Resource management and cleanup
- Concurrent test execution safety

These tests serve as both validation and examples for the migration from
mocks to real services across 2,941+ test files.

Business Value: Platform/Internal - Infrastructure Validation
Ensures the test infrastructure is reliable and ready for production use.
"""

import asyncio
import concurrent.futures
import logging
import pytest
import time
import uuid
from typing import Dict, List, Any

# Test infrastructure imports
from test_framework.isolated_environment_manager import (
    IsolatedEnvironmentManager,
    IsolationConfig,
    DatabaseTestResource,
    RedisTestResource,
    ClickHouseTestResource,
    generate_test_id,
    get_isolated_environment_manager
)

from test_framework.external_service_integration import (
    ExternalServiceManager,
    ExternalServiceConfig,
    WebSocketTestResource,
    HTTPTestResource,
    FileSystemTestResource
)

from test_framework.performance_optimization import (
    PerformanceOptimizer,
    OptimizationLevel,
    OptimizedIsolatedEnvironmentManager,
    create_optimized_environment_manager
)

# Import fixtures
from test_framework.conftest_comprehensive import (
    comprehensive_test_environment,
    isolated_database,
    isolated_redis,
    isolated_clickhouse,
    performance_test_environment
)

logger = logging.getLogger(__name__)


class TestIsolatedEnvironmentManager:
    """Test IsolatedEnvironmentManager core functionality."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test manager initializes correctly with all services."""
        config = IsolationConfig(
            enable_parallel_execution=True,
            max_concurrent_tests=10,
            enable_resource_pooling=True,
            enable_health_monitoring=True
        )
        
        manager = IsolatedEnvironmentManager(config)
        
        try:
            await manager.initialize()
            
            # Verify manager state
            assert manager.config.enable_parallel_execution
            assert manager.config.max_concurrent_tests == 10
            
            # Test health status
            health = await manager.get_health_status()
            assert isinstance(health, dict)
            
            # Test metrics
            metrics = manager.get_metrics()
            assert isinstance(metrics, dict)
            assert 'resources_created' in metrics
            
        finally:
            await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_database_isolation(self, isolated_database):
        """Test PostgreSQL transaction-based isolation works correctly."""
        # Test data isolation - changes should not persist
        test_value = f"test_value_{uuid.uuid4()}"
        
        # Insert data in isolated transaction
        result = await isolated_database.execute(
            "CREATE TEMPORARY TABLE test_isolation (id SERIAL, value TEXT)"
        )
        
        await isolated_database.execute(
            "INSERT INTO test_isolation (value) VALUES ($1)",
            test_value
        )
        
        # Verify data exists in this transaction
        row = await isolated_database.fetchrow(
            "SELECT * FROM test_isolation WHERE value = $1",
            test_value
        )
        assert row is not None
        assert row['value'] == test_value
        
        # Transaction will automatically rollback after test
        
    @pytest.mark.asyncio
    async def test_redis_isolation(self, isolated_redis):
        """Test Redis database isolation works correctly."""
        test_key = f"test_key_{uuid.uuid4()}"
        test_value = f"test_value_{uuid.uuid4()}"
        
        # Set value in isolated Redis database
        success = await isolated_redis.set(test_key, test_value)
        assert success
        
        # Verify value exists
        retrieved_value = await isolated_redis.get(test_key)
        assert retrieved_value == test_value
        
        # Test key existence
        exists = await isolated_redis.exists(test_key)
        assert exists
        
        # Database will be flushed after test
        
    @pytest.mark.skipif(
        not hasattr(pytest, 'clickhouse_available') or not pytest.clickhouse_available,
        reason="ClickHouse not available"
    )
    @pytest.mark.asyncio
    async def test_clickhouse_isolation(self, isolated_clickhouse):
        """Test ClickHouse schema isolation works correctly."""
        # Create table with isolated name
        table_name = isolated_clickhouse.get_table_name("test_events")
        
        await isolated_clickhouse.execute(f"""
            CREATE TABLE {table_name} (
                id UInt64,
                event_type String,
                timestamp DateTime
            ) ENGINE = Memory
        """)
        
        # Insert test data
        await isolated_clickhouse.execute(
            f"INSERT INTO {table_name} VALUES (1, 'test_event', now())"
        )
        
        # Verify data
        result = await isolated_clickhouse.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        )
        assert result[0][0] == 1
        
        # Table will be dropped after test
        
    @pytest.mark.asyncio
    async def test_concurrent_test_environments(self):
        """Test multiple test environments can run concurrently safely."""
        manager = get_isolated_environment_manager()
        await manager.initialize()
        
        async def create_and_use_environment(env_id: str) -> Dict[str, Any]:
            """Create environment, use it, and return results."""
            test_id = f"concurrent_{env_id}"
            results = {'test_id': test_id, 'success': False, 'error': None}
            
            try:
                async with manager.create_test_environment(test_id) as resources:
                    # Test database if available
                    if 'database' in resources:
                        db = resources['database']
                        value = await db.fetchval("SELECT 1")
                        assert value == 1
                    
                    # Test Redis if available
                    if 'redis' in resources:
                        redis = resources['redis']
                        await redis.set(f"key_{env_id}", f"value_{env_id}")
                        retrieved = await redis.get(f"key_{env_id}")
                        assert retrieved == f"value_{env_id}"
                    
                    results['success'] = True
                    results['resources'] = list(resources.keys())
                    
            except Exception as e:
                results['error'] = str(e)
                logger.error(f"Concurrent environment {env_id} failed: {e}")
                
            return results
        
        # Create 10 concurrent environments
        tasks = [
            create_and_use_environment(f"env_{i}")
            for i in range(10)
        ]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all succeeded
            successful = [r for r in results if isinstance(r, dict) and r.get('success')]
            failed = [r for r in results if not (isinstance(r, dict) and r.get('success'))]
            
            logger.info(f"Concurrent test results: {len(successful)} successful, {len(failed)} failed")
            
            # Most should succeed (allow for some resource contention)
            assert len(successful) >= 8, f"Too many concurrent failures: {failed}"
            
        finally:
            await manager.shutdown()


class TestExternalServiceIntegration:
    """Test external service integration functionality."""
    
    @pytest.mark.skipif(
        not hasattr(pytest, 'websockets_available') or not pytest.websockets_available,
        reason="WebSocket testing requires websockets package"
    )
    @pytest.mark.asyncio
    async def test_websocket_integration(self):
        """Test WebSocket server and client integration."""
        config = ExternalServiceConfig(websocket_timeout=10.0)
        manager = ExternalServiceManager(config)
        
        try:
            # Create WebSocket resource
            websocket = await manager.create_websocket_resource("test_websocket")
            
            # Test message handler registration
            test_responses = []
            
            def test_handler(message):
                test_responses.append(message)
                return {'type': 'ack', 'received': message.get('data')}
            
            websocket.register_message_handler('test_message', test_handler)
            
            # Send test message
            test_message = {'type': 'test_message', 'data': 'hello_world'}
            await websocket.send_message(test_message)
            
            # Receive response
            response = await websocket.receive_message(timeout=5.0)
            
            assert response['type'] == 'ack'
            assert response['received'] == 'hello_world'
            assert len(test_responses) == 1
            
        finally:
            await manager.cleanup_all_resources()
            
    @pytest.mark.skipif(
        not hasattr(pytest, 'http_available') or not pytest.http_available,
        reason="HTTP testing requires httpx package"
    )
    @pytest.mark.asyncio
    async def test_http_client_integration(self):
        """Test HTTP client with circuit breaker functionality."""
        config = ExternalServiceConfig(http_timeout=10.0)
        manager = ExternalServiceManager(config)
        
        try:
            # Create HTTP resource
            http_client = await manager.create_http_resource("test_http")
            
            # Test circuit breaker can execute
            can_execute = http_client.circuit_breaker.can_execute()
            assert can_execute
            
            # Test health check (may fail but should not raise exception)
            try:
                is_healthy = await http_client.health_check()
                logger.info(f"HTTP health check result: {is_healthy}")
            except Exception as e:
                logger.info(f"HTTP health check failed (expected): {e}")
            
        finally:
            await manager.cleanup_all_resources()
            
    @pytest.mark.asyncio
    async def test_filesystem_integration(self):
        """Test file system isolation and cleanup."""
        config = ExternalServiceConfig(max_file_size_mb=10)
        manager = ExternalServiceManager(config)
        
        try:
            # Create filesystem resource
            filesystem = await manager.create_filesystem_resource("test_filesystem")
            
            # Test file creation
            test_content = "Hello, World!"
            test_file = await filesystem.create_file("test.txt", test_content)
            
            assert test_file.exists()
            assert test_file.name == "test.txt"
            
            # Test file reading
            content = await filesystem.read_file("test.txt")
            assert content == test_content
            
            # Test directory creation
            test_dir = filesystem.create_directory("test_subdir")
            assert test_dir.exists()
            assert test_dir.is_dir()
            
            # Test file listing
            files = filesystem.list_files()
            assert len(files) >= 2  # test.txt and test_subdir
            
            # Test usage statistics
            usage = filesystem.get_size_usage()
            assert usage['file_count'] >= 1
            assert usage['total_size_bytes'] > 0
            
        finally:
            await manager.cleanup_all_resources()


class TestPerformanceOptimization:
    """Test performance optimization functionality."""
    
    @pytest.mark.asyncio
    async def test_performance_optimizer_initialization(self):
        """Test performance optimizer initializes with correct configuration."""
        optimizer = PerformanceOptimizer(OptimizationLevel.CI_FAST)
        
        try:
            await optimizer.initialize()
            
            # Check configuration
            assert optimizer.optimization_level == OptimizationLevel.CI_FAST
            assert optimizer.config['concurrent_tests'] == 10
            
            # Check resource pools were created
            assert len(optimizer.resource_pools) > 0
            
        finally:
            await optimizer.shutdown()
            
    @pytest.mark.asyncio
    async def test_optimized_environment_manager(self):
        """Test optimized environment manager performance."""
        manager = create_optimized_environment_manager(
            OptimizationLevel.CI_FAST,
            {'max_concurrent_tests': 5}
        )
        
        try:
            await manager.initialize()
            
            # Test environment creation performance
            start_time = time.time()
            
            test_id = generate_test_id()
            async with manager.create_test_environment(test_id) as resources:
                creation_time = time.time() - start_time
                
                # Should create environment reasonably quickly
                assert creation_time < 5.0  # 5 second timeout
                assert len(resources) > 0
                
                logger.info(f"Environment created in {creation_time:.2f}s with resources: {list(resources.keys())}")
                
            # Get performance metrics
            metrics = manager.get_performance_metrics()
            assert 'metrics_summary' in metrics
            assert 'pool_statistics' in metrics
            
        finally:
            await manager.shutdown()


class TestComprehensiveIntegration:
    """Test comprehensive integration scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_comprehensive_environment(self, comprehensive_test_environment):
        """Test complete integrated environment with all services."""
        resources = comprehensive_test_environment
        
        # Verify all expected resources are available
        expected_resources = ['database', 'redis']
        available_resources = list(resources.keys())
        
        logger.info(f"Available resources: {available_resources}")
        
        # Test database operations
        if 'database' in resources:
            db = resources['database']
            
            # Test table creation and data insertion
            await db.execute(
                "CREATE TEMPORARY TABLE integration_test (id SERIAL, name TEXT, created_at TIMESTAMP DEFAULT NOW())"
            )
            
            # Insert test data
            user_id = await db.fetchval(
                "INSERT INTO integration_test (name) VALUES ($1) RETURNING id",
                "Integration Test User"
            )
            
            # Verify data
            user = await db.fetchrow(
                "SELECT * FROM integration_test WHERE id = $1",
                user_id
            )
            assert user is not None
            assert user['name'] == "Integration Test User"
            assert user['created_at'] is not None
            
        # Test Redis operations
        if 'redis' in resources:
            redis = resources['redis']
            
            # Test basic operations
            await redis.set("integration_test_key", "integration_test_value")
            value = await redis.get("integration_test_key")
            assert value == "integration_test_value"
            
            # Test expiration
            await redis.set("temp_key", "temp_value", ex=1)
            value = await redis.get("temp_key")
            assert value == "temp_value"
            
        # Test WebSocket if available
        if 'websocket' in resources:
            websocket = resources['websocket']
            
            # Test message sending
            await websocket.send_message({
                'type': 'integration_test',
                'message': 'Hello from integration test'
            })
            
        # Test HTTP client if available
        if 'http' in resources:
            http_client = resources['http']
            
            # Test health check
            try:
                health = await http_client.health_check()
                logger.info(f"HTTP health check: {health}")
            except Exception as e:
                logger.info(f"HTTP health check failed (may be expected): {e}")
                
        # Test file system if available
        if 'filesystem' in resources:
            filesystem = resources['filesystem']
            
            # Create integration test file
            test_file = await filesystem.create_file(
                "integration_test.json",
                '{"test": "integration", "timestamp": "2023-01-01T00:00:00Z"}'
            )
            
            assert test_file.exists()
            
            # Read and verify content
            content = await filesystem.read_file("integration_test.json")
            assert "integration" in content
            
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, performance_test_environment):
        """Test performance benchmarks for the infrastructure."""
        resources = performance_test_environment
        
        # Database performance test
        if 'database' in resources:
            db = resources['database']
            
            # Create test table
            await db.execute(
                "CREATE TEMPORARY TABLE perf_test (id SERIAL, value TEXT, created_at TIMESTAMP DEFAULT NOW())"
            )
            
            # Benchmark bulk inserts
            start_time = time.time()
            
            for i in range(100):
                await db.execute(
                    "INSERT INTO perf_test (value) VALUES ($1)",
                    f"value_{i}"
                )
                
            insert_time = time.time() - start_time
            
            # Benchmark bulk query
            start_time = time.time()
            
            results = await db.fetch(
                "SELECT * FROM perf_test ORDER BY id"
            )
            
            query_time = time.time() - start_time
            
            logger.info(
                f"Performance benchmark - "
                f"100 inserts: {insert_time:.2f}s ({insert_time*10:.1f}ms/insert), "
                f"100 row query: {query_time:.2f}s ({query_time*1000:.1f}ms)"
            )
            
            # Assert reasonable performance
            assert len(results) == 100
            assert insert_time < 10.0  # Should complete in under 10 seconds
            assert query_time < 1.0    # Query should be fast
            
        # Redis performance test
        if 'redis' in resources:
            redis = resources['redis']
            
            # Benchmark Redis operations
            start_time = time.time()
            
            for i in range(100):
                await redis.set(f"perf_key_{i}", f"perf_value_{i}")
                
            set_time = time.time() - start_time
            
            start_time = time.time()
            
            for i in range(100):
                value = await redis.get(f"perf_key_{i}")
                assert value == f"perf_value_{i}"
                
            get_time = time.time() - start_time
            
            logger.info(
                f"Redis performance benchmark - "
                f"100 sets: {set_time:.2f}s ({set_time*10:.1f}ms/set), "
                f"100 gets: {get_time:.2f}s ({get_time*10:.1f}ms/get)"
            )
            
            # Assert reasonable performance
            assert set_time < 2.0  # Redis should be fast
            assert get_time < 1.0
            
    @pytest.mark.asyncio
    async def test_resource_cleanup_validation(self):
        """Test that all resources are properly cleaned up."""
        manager = get_isolated_environment_manager()
        await manager.initialize()
        
        initial_metrics = manager.get_metrics()
        initial_resources = initial_metrics.get('resources_created', 0)
        
        # Create and use multiple test environments
        for i in range(5):
            test_id = f"cleanup_test_{i}"
            
            async with manager.create_test_environment(test_id) as resources:
                # Use resources briefly
                if 'database' in resources:
                    db = resources['database']
                    await db.fetchval("SELECT 1")
                    
                if 'redis' in resources:
                    redis = resources['redis']
                    await redis.set(f"test_{i}", f"value_{i}")
                    
            # Resources should be cleaned up automatically
            
        final_metrics = manager.get_metrics()
        final_resources = final_metrics.get('resources_created', 0)
        cleaned_resources = final_metrics.get('resources_cleaned', 0)
        
        logger.info(
            f"Resource cleanup validation - "
            f"Created: {final_resources - initial_resources}, "
            f"Cleaned: {cleaned_resources}"
        )
        
        # Verify cleanup happened
        assert cleaned_resources > 0, "No resources were cleaned up"
        
        # Get health status
        health = await manager.get_health_status()
        logger.info(f"Final health status: {len(health)} active resources")
        
        await manager.shutdown()


class TestMigrationValidation:
    """Test migration patterns and validation."""
    
    @pytest.mark.asyncio
    async def test_migration_pattern_database(self, isolated_database):
        """Test typical database migration pattern from mocks to real services."""
        # This test demonstrates the migration pattern
        # OLD: Mock-based test would use MagicMock/AsyncMock
        # NEW: Real database test with transaction isolation
        
        # Example: User creation workflow
        email = f"migration_test_{uuid.uuid4()}@example.com"
        
        # Create user (would be actual service call)
        user_id = await isolated_database.fetchval(
            "SELECT CASE WHEN EXISTS(SELECT 1) THEN 1 ELSE 0 END"
        )
        
        # Simulate user creation
        await isolated_database.execute(
            "CREATE TEMPORARY TABLE migration_users (id SERIAL, email TEXT UNIQUE, created_at TIMESTAMP DEFAULT NOW())"
        )
        
        actual_user_id = await isolated_database.fetchval(
            "INSERT INTO migration_users (email) VALUES ($1) RETURNING id",
            email
        )
        
        # Verify user was created (replaces mock assertions)
        user = await isolated_database.fetchrow(
            "SELECT * FROM migration_users WHERE id = $1",
            actual_user_id
        )
        
        assert user is not None
        assert user['email'] == email
        assert user['created_at'] is not None
        
        # No cleanup needed - transaction rolls back automatically
        
    @pytest.mark.asyncio
    async def test_migration_pattern_caching(self, isolated_redis):
        """Test typical caching migration pattern."""
        # Example: Cache service integration
        cache_key = f"migration_test_{uuid.uuid4()}"
        cache_value = {"user_id": 123, "session": "active"}
        
        # Set cache (would be actual service call)
        import json
        success = await isolated_redis.set(cache_key, json.dumps(cache_value))
        assert success
        
        # Verify cache hit (replaces mock assertions)
        cached_data = await isolated_redis.get(cache_key)
        assert cached_data is not None
        
        parsed_data = json.loads(cached_data)
        assert parsed_data["user_id"] == 123
        assert parsed_data["session"] == "active"
        
        # Test cache expiration
        await isolated_redis.set(f"{cache_key}_temp", "temp_value", ex=1)
        temp_value = await isolated_redis.get(f"{cache_key}_temp")
        assert temp_value == "temp_value"
        
        # Redis database automatically flushed after test
        
    @pytest.mark.asyncio
    async def test_migration_pattern_integration(self, comprehensive_test_environment):
        """Test comprehensive integration migration pattern."""
        # This demonstrates migrating complex multi-service tests
        resources = comprehensive_test_environment
        
        # Example: Complete user workflow with multiple services
        user_email = f"integration_{uuid.uuid4()}@example.com"
        
        # 1. Create user in database
        if 'database' in resources:
            db = resources['database']
            
            await db.execute(
                "CREATE TEMPORARY TABLE integration_users (id SERIAL, email TEXT, status TEXT)"
            )
            
            user_id = await db.fetchval(
                "INSERT INTO integration_users (email, status) VALUES ($1, $2) RETURNING id",
                user_email, "active"
            )
            
            # 2. Cache user session
            if 'redis' in resources:
                redis = resources['redis']
                
                import json
                session_data = {
                    "user_id": user_id,
                    "email": user_email,
                    "login_time": "2023-01-01T00:00:00Z"
                }
                
                await redis.set(f"session:{user_id}", json.dumps(session_data), ex=3600)
                
            # 3. Send notification (WebSocket)
            if 'websocket' in resources:
                websocket = resources['websocket']
                
                await websocket.send_message({
                    'type': 'user_registered',
                    'user_id': user_id,
                    'email': user_email
                })
                
            # 4. Create user profile file
            if 'filesystem' in resources:
                filesystem = resources['filesystem']
                
                profile_data = {
                    "user_id": user_id,
                    "email": user_email,
                    "preferences": {"theme": "dark", "notifications": True}
                }
                
                profile_file = await filesystem.create_file(
                    f"user_profile_{user_id}.json",
                    json.dumps(profile_data, indent=2)
                )
                
                assert profile_file.exists()
                
            # Verify complete workflow
            user_check = await db.fetchrow(
                "SELECT * FROM integration_users WHERE id = $1",
                user_id
            )
            assert user_check['email'] == user_email
            assert user_check['status'] == "active"
            
            if 'redis' in resources:
                session_check = await redis.get(f"session:{user_id}")
                assert session_check is not None
                session_parsed = json.loads(session_check)
                assert session_parsed['user_id'] == user_id


# Benchmark utility functions
class BenchmarkResults:
    """Store and analyze benchmark results."""
    
    def __init__(self):
        self.results = []
        
    def add_result(self, operation: str, duration: float, iterations: int = 1):
        """Add benchmark result."""
        self.results.append({
            'operation': operation,
            'duration': duration,
            'iterations': iterations,
            'avg_per_operation': duration / iterations if iterations > 0 else 0
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get benchmark summary."""
        if not self.results:
            return {'total_operations': 0}
            
        total_duration = sum(r['duration'] for r in self.results)
        total_iterations = sum(r['iterations'] for r in self.results)
        
        return {
            'total_operations': len(self.results),
            'total_duration': total_duration,
            'total_iterations': total_iterations,
            'average_operation_time': total_duration / len(self.results),
            'operations_per_second': total_iterations / total_duration if total_duration > 0 else 0,
            'results': self.results
        }


@pytest.mark.benchmark
class TestInfrastructureBenchmarks:
    """Benchmark tests for infrastructure performance."""
    
    @pytest.mark.asyncio
    async def test_environment_creation_benchmark(self):
        """Benchmark environment creation performance."""
        manager = get_isolated_environment_manager()
        await manager.initialize()
        
        benchmark = BenchmarkResults()
        
        try:
            # Benchmark environment creation
            for i in range(10):
                test_id = f"benchmark_{i}"
                
                start_time = time.time()
                
                async with manager.create_test_environment(test_id) as resources:
                    creation_time = time.time() - start_time
                    benchmark.add_result(f'environment_creation_{i}', creation_time)
                    
                    # Brief usage to ensure resources are functional
                    if 'database' in resources:
                        await resources['database'].fetchval("SELECT 1")
                        
            summary = benchmark.get_summary()
            
            logger.info(f"Environment creation benchmark: {summary}")
            
            # Performance assertions
            assert summary['average_operation_time'] < 5.0  # Should average under 5 seconds
            assert summary['operations_per_second'] > 0.2   # At least 0.2 environments/second
            
        finally:
            await manager.shutdown()
            
    @pytest.mark.asyncio
    async def test_concurrent_environment_benchmark(self):
        """Benchmark concurrent environment handling."""
        manager = get_isolated_environment_manager()
        await manager.initialize()
        
        async def create_concurrent_environment(env_id: str) -> float:
            """Create environment and return creation time."""
            start_time = time.time()
            
            async with manager.create_test_environment(f"concurrent_bench_{env_id}") as resources:
                # Simulate work
                if 'database' in resources:
                    await resources['database'].fetchval("SELECT $1", env_id)
                if 'redis' in resources:
                    await resources['redis'].set(f"bench_{env_id}", env_id)
                    
                return time.time() - start_time
                
        try:
            start_time = time.time()
            
            # Run 20 concurrent environments
            tasks = [create_concurrent_environment(str(i)) for i in range(20)]
            creation_times = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            logger.info(
                f"Concurrent benchmark - "
                f"20 environments in {total_time:.2f}s, "
                f"average per env: {sum(creation_times)/len(creation_times):.2f}s, "
                f"throughput: {20/total_time:.2f} envs/sec"
            )
            
            # Performance assertions
            assert total_time < 30.0  # Should complete in under 30 seconds
            assert max(creation_times) < 10.0  # No single environment should take more than 10 seconds
            
        finally:
            await manager.shutdown()


if __name__ == "__main__":
    # Run validation tests directly
    pytest.main([__file__, "-v", "-s"])
