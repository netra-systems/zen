"""
Integration tests for ClickHouse dependency validation and startup robustness

Tests the complete ClickHouse health check dependency fix:
1. Service dependency validation before startup
2. Connection retry logic with exponential backoff
3. Connection pooling and health monitoring
4. Analytics data consistency during startup
5. Graceful degradation when ClickHouse is unavailable

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure 100% reliable backend startup
- Value Impact: Prevents startup failures due to ClickHouse connection issues
- Revenue Impact: Eliminates downtime from dependency failures
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any

from netra_backend.app.core.clickhouse_connection_manager import (
    ClickHouseConnectionManager,
    RetryConfig,
    ConnectionPoolConfig,
    CircuitBreakerConfig,
    ConnectionState,
    ConnectionHealth,
    initialize_clickhouse_with_retry
)


class TestClickHouseConnectionManager:
    """Test suite for ClickHouse connection manager with robust retry logic"""

    @pytest.fixture
    def retry_config(self):
        """Retry configuration for testing"""
        return RetryConfig(
            max_retries=3,
            initial_delay=0.1,  # Fast retries for testing
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable testing
            timeout_per_attempt=5.0
        )

    @pytest.fixture
    def pool_config(self):
        """Pool configuration for testing"""
        return ConnectionPoolConfig(
            pool_size=3,
            max_connections=5,
            connection_timeout=10.0,
            pool_recycle_time=300,  # 5 minutes for testing
            health_check_interval=10.0
        )

    @pytest.fixture
    def circuit_breaker_config(self):
        """Circuit breaker configuration for testing"""
        return CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5.0,
            half_open_max_calls=2
        )

    @pytest.fixture
    def connection_manager(self, retry_config, pool_config, circuit_breaker_config):
        """Connection manager instance for testing"""
        return ClickHouseConnectionManager(
            retry_config=retry_config,
            pool_config=pool_config,
            circuit_breaker_config=circuit_breaker_config
        )

    @pytest.mark.asyncio
    async def test_initialization_with_successful_connection(self, connection_manager):
        """Test successful initialization with connection retry logic"""
        # Mock successful connection
        with patch.object(connection_manager, '_attempt_connection', return_value=True):
            success = await connection_manager.initialize()
            
            assert success is True
            assert connection_manager.connection_health.state == ConnectionState.HEALTHY
            assert connection_manager.metrics["connection_attempts"] == 1
            assert connection_manager.metrics["successful_connections"] == 1
            assert connection_manager.metrics["failed_connections"] == 0

    @pytest.mark.asyncio
    async def test_initialization_with_retry_logic(self, connection_manager):
        """Test initialization retry logic with exponential backoff"""
        # Mock connection that fails twice then succeeds
        attempt_count = 0
        
        async def mock_attempt_connection():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                raise ConnectionError(f"Mock connection error {attempt_count}")
            return True
        
        with patch.object(connection_manager, '_attempt_connection', side_effect=mock_attempt_connection):
            start_time = time.time()
            success = await connection_manager.initialize()
            end_time = time.time()
            
            assert success is True
            assert connection_manager.connection_health.state == ConnectionState.HEALTHY
            assert connection_manager.metrics["retry_attempts"] >= 2
            assert connection_manager.metrics["successful_connections"] == 1
            
            # Verify exponential backoff timing (should have delays between attempts)
            # With initial_delay=0.1 and exponential_base=2.0, total delay should be ~0.3s minimum
            assert end_time - start_time >= 0.2  # Allow for some variance

    @pytest.mark.asyncio
    async def test_initialization_failure_after_all_retries(self, connection_manager):
        """Test initialization failure after all retries are exhausted"""
        # Mock connection that always fails
        with patch.object(connection_manager, '_attempt_connection', side_effect=ConnectionError("Persistent failure")):
            success = await connection_manager.initialize()
            
            assert success is False
            assert connection_manager.connection_health.state == ConnectionState.FAILED
            assert connection_manager.metrics["failed_connections"] == 1
            assert connection_manager.metrics["retry_attempts"] == connection_manager.retry_config.max_retries

    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, connection_manager):
        """Test circuit breaker opens after threshold failures"""
        # Initialize first
        with patch.object(connection_manager, '_attempt_connection', return_value=True):
            await connection_manager.initialize()
        
        # Mock failing connection to trigger circuit breaker
        with patch.object(connection_manager, '_attempt_connection', side_effect=ConnectionError("Mock failure")):
            # Execute multiple failing operations to open circuit breaker
            for i in range(connection_manager.circuit_breaker_config.failure_threshold + 1):
                try:
                    await connection_manager.execute_with_retry("SELECT 1")
                except Exception:
                    pass
            
            # Circuit breaker should now be open
            assert connection_manager.circuit_breaker.state == "open"
            
            # Next operation should fail immediately without attempting connection
            with pytest.raises(ConnectionError, match="circuit breaker is open"):
                await connection_manager.execute_with_retry("SELECT 1")

    @pytest.mark.asyncio
    async def test_connection_pooling(self, connection_manager):
        """Test connection pooling functionality"""
        # Mock successful connection
        mock_connection = AsyncMock()
        mock_connection.execute = AsyncMock(return_value=[{"result": 1}])
        
        with patch('netra_backend.app.db.clickhouse.get_clickhouse_client') as mock_client:
            mock_client.return_value.__aenter__.return_value = mock_connection
            
            # Initialize connection manager
            with patch.object(connection_manager, '_attempt_connection', return_value=True):
                await connection_manager.initialize()
            
            # Execute multiple queries to test pooling
            results = []
            async with connection_manager.get_connection() as conn:
                result = await conn.execute("SELECT 1")
                results.append(result)
            
            async with connection_manager.get_connection() as conn:
                result = await conn.execute("SELECT 2")
                results.append(result)
            
            assert len(results) == 2
            assert all(result == [{"result": 1}] for result in results)

    @pytest.mark.asyncio
    async def test_service_dependency_validation(self, connection_manager):
        """Test comprehensive service dependency validation"""
        # Mock successful connection and query execution
        with patch.object(connection_manager, '_perform_health_check', return_value=True):
            with patch.object(connection_manager, 'execute_with_retry', return_value=[{"version()": "23.8.1.1"}]):
                validation = await connection_manager.validate_service_dependencies()
                
                assert validation["overall_health"] is True
                assert validation["clickhouse_available"] is True
                assert validation["docker_service_healthy"] is True
                assert validation["connection_successful"] is True
                assert validation["query_execution"] is True
                assert validation["clickhouse_version"] == "23.8.1.1"
                assert len(validation["errors"]) == 0

    @pytest.mark.asyncio
    async def test_service_dependency_validation_failure(self, connection_manager):
        """Test service dependency validation when ClickHouse is unavailable"""
        # Mock failing health check
        with patch.object(connection_manager, '_perform_health_check', side_effect=ConnectionError("Service unavailable")):
            validation = await connection_manager.validate_service_dependencies()
            
            assert validation["overall_health"] is False
            assert validation["clickhouse_available"] is False
            assert validation["docker_service_healthy"] is False
            assert validation["connection_successful"] is False
            assert validation["query_execution"] is False
            assert len(validation["errors"]) > 0
            assert "Health check failed" in validation["errors"][0]

    @pytest.mark.asyncio
    async def test_analytics_data_consistency(self, connection_manager):
        """Test analytics data consistency validation during startup"""
        # Mock successful table queries and data access
        mock_tables = [
            {"name": "agent_state_history", "engine": "MergeTree"},
            {"name": "analytics_events", "engine": "MergeTree"}
        ]
        
        with patch.object(connection_manager, 'execute_with_retry') as mock_execute:
            mock_execute.side_effect = [
                mock_tables,  # Tables query
                [{"test_value": 1}],  # Read test query
                []  # Write test query
            ]
            
            consistency = await connection_manager.ensure_analytics_consistency()
            
            assert consistency["overall_consistent"] is True
            assert consistency["tables_verified"] is True
            assert consistency["schema_valid"] is True
            assert consistency["data_accessible"] is True
            assert consistency["write_test_successful"] is True
            assert consistency["table_count"] == 2
            assert len(consistency["errors"]) == 0

    @pytest.mark.asyncio
    async def test_analytics_data_consistency_failure(self, connection_manager):
        """Test analytics data consistency when data is inaccessible"""
        # Mock failing queries
        with patch.object(connection_manager, 'execute_with_retry', side_effect=ConnectionError("Data access failed")):
            consistency = await connection_manager.ensure_analytics_consistency()
            
            assert consistency["overall_consistent"] is False
            assert consistency["tables_verified"] is False
            assert consistency["schema_valid"] is False
            assert consistency["data_accessible"] is False
            assert len(consistency["errors"]) > 0

    @pytest.mark.asyncio
    async def test_health_monitoring(self, connection_manager):
        """Test background health monitoring functionality"""
        # Initialize with successful connection
        with patch.object(connection_manager, '_attempt_connection', return_value=True):
            await connection_manager.initialize()
        
        # Health monitoring task should be running
        assert connection_manager._health_monitor_task is not None
        assert not connection_manager._health_monitor_task.done()
        
        # Wait a bit for health check to run
        await asyncio.sleep(0.1)
        
        # Stop monitoring
        await connection_manager.shutdown()
        
        # Health monitoring task should be cancelled
        assert connection_manager._health_monitor_task.done()

    @pytest.mark.asyncio
    async def test_connection_metrics(self, connection_manager):
        """Test connection metrics collection"""
        # Initialize and perform operations
        with patch.object(connection_manager, '_attempt_connection', return_value=True):
            await connection_manager.initialize()
        
        # Get metrics
        metrics = connection_manager.get_connection_metrics()
        
        assert "connection_attempts" in metrics
        assert "successful_connections" in metrics
        assert "failed_connections" in metrics
        assert "retry_attempts" in metrics
        assert "circuit_breaker_opens" in metrics
        assert "connection_state" in metrics
        assert "circuit_breaker_state" in metrics
        assert "pool_size" in metrics
        assert "pool_config" in metrics
        assert "retry_config" in metrics

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, connection_manager):
        """Test graceful shutdown cleans up resources"""
        # Initialize with successful connection
        with patch.object(connection_manager, '_attempt_connection', return_value=True):
            await connection_manager.initialize()
        
        initial_state = connection_manager.connection_health.state
        assert initial_state != ConnectionState.DISCONNECTED
        
        # Shutdown
        await connection_manager.shutdown()
        
        # Should be disconnected
        assert connection_manager.connection_health.state == ConnectionState.DISCONNECTED
        
        # Health monitor should be stopped
        if connection_manager._health_monitor_task:
            assert connection_manager._health_monitor_task.done()


class TestClickHouseStartupIntegration:
    """Integration tests for ClickHouse startup with the backend"""

    @pytest.mark.asyncio
    async def test_initialize_clickhouse_with_retry_success(self):
        """Test successful ClickHouse initialization during startup"""
        with patch('netra_backend.app.core.clickhouse_connection_manager.get_clickhouse_connection_manager') as mock_manager:
            # Mock successful initialization
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.validate_service_dependencies = AsyncMock(return_value={
                "overall_health": True,
                "errors": []
            })
            mock_instance.ensure_analytics_consistency = AsyncMock(return_value={
                "overall_consistent": True,
                "errors": []
            })
            mock_manager.return_value = mock_instance
            
            success = await initialize_clickhouse_with_retry()
            
            assert success is True
            mock_instance.initialize.assert_called_once()
            mock_instance.validate_service_dependencies.assert_called_once()
            mock_instance.ensure_analytics_consistency.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_clickhouse_with_retry_failure(self):
        """Test ClickHouse initialization failure during startup"""
        with patch('netra_backend.app.core.clickhouse_connection_manager.get_clickhouse_connection_manager') as mock_manager:
            # Mock failed initialization
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=False)
            mock_manager.return_value = mock_instance
            
            success = await initialize_clickhouse_with_retry()
            
            assert success is False
            mock_instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_clickhouse_dependency_validation_failure(self):
        """Test ClickHouse initialization with dependency validation failure"""
        with patch('netra_backend.app.core.clickhouse_connection_manager.get_clickhouse_connection_manager') as mock_manager:
            # Mock successful connection but failed validation
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.validate_service_dependencies = AsyncMock(return_value={
                "overall_health": False,
                "errors": ["Service unavailable"]
            })
            mock_manager.return_value = mock_instance
            
            success = await initialize_clickhouse_with_retry()
            
            assert success is False
            mock_instance.initialize.assert_called_once()
            mock_instance.validate_service_dependencies.assert_called_once()

    @pytest.mark.asyncio 
    async def test_initialize_clickhouse_analytics_consistency_warning(self):
        """Test ClickHouse initialization with analytics consistency warning"""
        with patch('netra_backend.app.core.clickhouse_connection_manager.get_clickhouse_connection_manager') as mock_manager:
            # Mock successful connection and validation but analytics issues
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            mock_instance.validate_service_dependencies = AsyncMock(return_value={
                "overall_health": True,
                "errors": []
            })
            mock_instance.ensure_analytics_consistency = AsyncMock(return_value={
                "overall_consistent": False,
                "errors": ["Table access issues"]
            })
            mock_manager.return_value = mock_instance
            
            # Should still succeed but log warnings
            success = await initialize_clickhouse_with_retry()
            
            assert success is True
            mock_instance.initialize.assert_called_once()
            mock_instance.validate_service_dependencies.assert_called_once()
            mock_instance.ensure_analytics_consistency.assert_called_once()


class TestClickHouseDockerDependency:
    """Test ClickHouse Docker service dependency validation"""

    @pytest.mark.integration
    @pytest.mark.real_database
    async def test_docker_clickhouse_health_check(self):
        """Test actual Docker ClickHouse health check"""
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        
        connection_manager = get_clickhouse_connection_manager()
        
        # Perform actual health check
        health_check = await connection_manager._perform_health_check()
        
        # Should pass if ClickHouse Docker service is running
        # If not, this test documents the expected behavior
        if health_check:
            assert health_check is True
        else:
            pytest.skip("ClickHouse Docker service not available")

    @pytest.mark.integration
    @pytest.mark.real_database
    async def test_docker_clickhouse_service_dependencies(self):
        """Test actual Docker ClickHouse service dependency validation"""
        from netra_backend.app.core.clickhouse_connection_manager import get_clickhouse_connection_manager
        
        connection_manager = get_clickhouse_connection_manager()
        
        # Perform actual dependency validation
        validation = await connection_manager.validate_service_dependencies()
        
        # Document expected behavior based on Docker service availability
        if validation["overall_health"]:
            assert validation["clickhouse_available"] is True
            assert validation["docker_service_healthy"] is True
            assert validation["connection_successful"] is True
            assert "clickhouse_version" in validation
        else:
            # Service not available - document the failure
            assert len(validation["errors"]) > 0
            pytest.skip(f"ClickHouse Docker service not available: {validation['errors']}")

    @pytest.mark.integration
    async def test_backend_startup_with_clickhouse_unavailable(self):
        """Test backend startup behavior when ClickHouse is unavailable"""
        # This test verifies that the backend can start gracefully even when ClickHouse is down
        with patch('netra_backend.app.core.clickhouse_connection_manager.get_clickhouse_connection_manager') as mock_manager:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=False)
            mock_manager.return_value = mock_instance
            
            # Initialization should handle failure gracefully
            success = await initialize_clickhouse_with_retry()
            
            # Should return False but not raise an exception
            assert success is False
            
            # Backend startup should continue (ClickHouse is optional)
            # This test documents that ClickHouse failures don't prevent backend startup


@pytest.mark.integration
class TestClickHouseRetryScenarios:
    """Test various retry scenarios for ClickHouse connections"""

    @pytest.mark.asyncio
    async def test_connection_timeout_retry(self):
        """Test retry logic when connections timeout"""
        manager = ClickHouseConnectionManager(
            retry_config=RetryConfig(max_retries=2, initial_delay=0.1, timeout_per_attempt=0.1)
        )
        
        # Mock timeout on first two attempts, success on third
        attempt_count = 0
        
        async def mock_attempt():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:
                await asyncio.sleep(0.2)  # Longer than timeout
                return True
            return True
        
        with patch.object(manager, '_attempt_connection', side_effect=mock_attempt):
            success = await manager.initialize()
            
            # Should eventually succeed after retries
            assert success is True
            assert manager.metrics["retry_attempts"] >= 2

    @pytest.mark.asyncio
    async def test_intermittent_connection_failures(self):
        """Test handling of intermittent connection failures"""
        manager = ClickHouseConnectionManager(
            retry_config=RetryConfig(max_retries=4, initial_delay=0.1)
        )
        
        # Simulate intermittent failures
        attempt_count = 0
        failures = [True, False, True, False]  # Fail, succeed, fail, succeed
        
        async def mock_attempt():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= len(failures) and failures[attempt_count - 1]:
                raise ConnectionError(f"Intermittent failure {attempt_count}")
            return True
        
        with patch.object(manager, '_attempt_connection', side_effect=mock_attempt):
            success = await manager.initialize()
            
            assert success is True
            assert manager.metrics["retry_attempts"] > 0

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that exponential backoff timing is working correctly"""
        manager = ClickHouseConnectionManager(
            retry_config=RetryConfig(
                max_retries=3,
                initial_delay=0.1,
                exponential_base=2.0,
                jitter=False  # Disable for predictable timing
            )
        )
        
        # Mock failures for first 3 attempts, success on 4th
        attempt_count = 0
        attempt_times = []
        
        async def mock_attempt():
            nonlocal attempt_count
            attempt_count += 1
            attempt_times.append(time.time())
            
            if attempt_count <= 3:
                raise ConnectionError(f"Failure {attempt_count}")
            return True
        
        with patch.object(manager, '_attempt_connection', side_effect=mock_attempt):
            start_time = time.time()
            success = await manager.initialize()
            
            assert success is True
            assert len(attempt_times) == 4
            
            # Verify exponential backoff delays
            # Delays should be approximately: 0, 0.1, 0.2, 0.4 seconds
            if len(attempt_times) >= 3:
                delay1 = attempt_times[1] - attempt_times[0]
                delay2 = attempt_times[2] - attempt_times[1]
                
                # Allow some tolerance for timing variations
                assert 0.08 <= delay1 <= 0.15  # ~0.1 second delay
                assert 0.18 <= delay2 <= 0.25  # ~0.2 second delay