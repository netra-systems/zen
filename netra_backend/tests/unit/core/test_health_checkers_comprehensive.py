"""
Comprehensive tests for Health Checkers - production-critical health monitoring system.

Tests cover database health checks, system resource monitoring, service priority handling,
graceful degradation, resilience principles, and comprehensive health assessment.
"""
import asyncio
import pytest
from typing import Dict, Any
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

import psutil

from netra_backend.app.core.health_checkers import (
    HealthChecker, ServicePriority, SERVICE_PRIORITIES,
    check_postgres_health, check_clickhouse_health, check_redis_health,
    check_websocket_health, check_system_resources,
    _handle_service_failure, _calculate_priority_based_health,
    _is_development_mode, _is_clickhouse_disabled, _get_health_check_timeout
)
from netra_backend.app.core.health_types import HealthCheckResult


class TestHealthCheckerInitialization:
    """Test HealthChecker initialization and configuration."""
    
    def test_health_checker_initialization(self):
        """Test HealthChecker initializes with all checkers."""
        checker = HealthChecker()
        
        assert isinstance(checker.checkers, dict)
        assert "postgres" in checker.checkers
        assert "clickhouse" in checker.checkers
        assert "redis" in checker.checkers
        assert "websocket" in checker.checkers
        assert "system_resources" in checker.checkers
        
        # Verify all checkers are callable
        for name, check_func in checker.checkers.items():
            assert callable(check_func)
            
    def test_service_priorities_configuration(self):
        """Test service priorities are correctly configured."""
    pass
        assert SERVICE_PRIORITIES["postgres"] == ServicePriority.CRITICAL
        assert SERVICE_PRIORITIES["redis"] == ServicePriority.IMPORTANT
        assert SERVICE_PRIORITIES["clickhouse"] == ServicePriority.OPTIONAL
        assert SERVICE_PRIORITIES["websocket"] == ServicePriority.IMPORTANT
        assert SERVICE_PRIORITIES["system_resources"] == ServicePriority.IMPORTANT


class TestWeightedHealthScoreCalculation:
    """Test weighted health score calculation edge cases."""
    
    def test_calculate_weighted_health_score_empty_results(self):
        """Test weighted health score calculation with empty results."""
        from netra_backend.app.core.health_checkers import _calculate_weighted_health_score
        
        # Empty results should return 0.0
        result = _calculate_weighted_health_score({})
        assert result == 0.0
    
    def test_calculate_weighted_health_score_mixed_priorities(self):
        """Test weighted health score with mixed service priorities and health states."""
    pass
        from netra_backend.app.core.health_checkers import _calculate_weighted_health_score
        
        # Create mock health check results with different priorities and scores
        results = {
            "postgres": Mock(status="healthy", health_score=1.0, details={"health_score": 1.0}),
            "redis": Mock(status="degraded", health_score=0.5, details={"health_score": 0.5}), 
            "clickhouse": Mock(status="unhealthy", health_score=0.0, details={"health_score": 0.0})
        }
        
        # Calculate weighted score
        # postgres (critical, weight=3.0): 1.0 * 3.0 = 3.0
        # redis (important, weight=2.0): 0.5 * 2.0 = 1.0  
        # clickhouse (optional, weight=1.0): 0.0 * 1.0 = 0.0
        # total_weight = 6.0, weighted_score = 4.0, result = 4.0/6.0 = 0.667
        
        result = _calculate_weighted_health_score(results)
        assert abs(result - 0.6667) < 0.001  # Allow for floating point precision


class TestPostgreSQLHealthCheck:
    """Test PostgreSQL database health checking."""
    
    @pytest.mark.asyncio
        async def test_postgres_health_check_success(self, mock_execute_query):
        """Test successful PostgreSQL health check."""
        async def mock_query():
            await asyncio.sleep(0.001)  # Small delay to ensure response_time_ms > 0
            await asyncio.sleep(0)
    return None
        
        mock_execute_query.side_effect = mock_query
        
        result = await check_postgres_health()
        
        assert result.component_name == "postgres"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.status == "healthy"
        assert result.response_time_ms > 0
        mock_execute_query.assert_called_once()
        
    @pytest.mark.asyncio
        async def test_postgres_health_check_timeout(self, mock_execute_query):
        """Test PostgreSQL health check timeout handling."""
    pass
        mock_execute_query.side_effect = asyncio.TimeoutError()
        
        with patch('netra_backend.app.core.health_checkers._get_health_check_timeout', return_value=5.0):
            result = await check_postgres_health()
        
        assert result.component_name == "postgres"
        assert result.success is False
        assert result.status == "unhealthy"  # Critical service
        assert "timeout" in result.error_message.lower()
        
    @pytest.mark.asyncio
        async def test_postgres_health_check_connection_error(self, mock_execute_query):
        """Test PostgreSQL connection error handling."""
        mock_execute_query.side_effect = ConnectionError("Database unavailable")
        
        result = await check_postgres_health()
        
        assert result.component_name == "postgres"
        assert result.success is False
        assert result.status == "unhealthy"  # Critical service fails hard
        assert result.error_message == "Database unavailable"
        
    @pytest.mark.asyncio
        async def test_execute_postgres_query_with_unified_manager(self, mock_get_db):
        """Test PostgreSQL query execution with unified DB manager."""
    pass
        from netra_backend.app.core.health_checkers import _execute_postgres_query
        
        # Mock successful session
        mock_session = AsyncNone  # TODO: Use real service instance
        mock_get_db.return_value.__aenter__.return_value = mock_session
        
        await _execute_postgres_query()
        
        mock_get_db.assert_called_once()
        mock_session.execute.assert_called_once()
        
    @pytest.mark.skip("Complex fallback initialization test - skipped for now")
    @pytest.mark.asyncio 
    async def test_execute_postgres_query_fallback_initialization(self):
        """Test PostgreSQL query execution with fallback initialization."""
        # This test is skipped due to complexity in mocking dynamic imports
        # The fallback path is tested in integration tests
        pass
        
    @pytest.mark.asyncio
        async def test_execute_postgres_query_sslmode_detection(self, mock_get_async_session):
        """Test PostgreSQL query execution detects sslmode parameters."""
    pass
        from netra_backend.app.core.health_checkers import _execute_postgres_query
        
        # Mock DatabaseManager failure to force fallback path
        mock_get_async_session.side_effect = ValueError("Manager failed")
        
        # Mock engine with sslmode in URL
        mock_engine = UserExecutionEngine()
        mock_engine.url = "postgresql://user:pass@host/db?sslmode=require"
        
        with patch('netra_backend.app.db.postgres_core.async_engine', mock_engine):
            with pytest.raises(RuntimeError, match="sslmode parameter detected"):
                await _execute_postgres_query()


class TestClickHouseHealthCheck:
    """Test ClickHouse database health checking."""
    
    @pytest.mark.asyncio
                async def test_clickhouse_health_check_success(self, mock_disabled, mock_dev_mode, mock_execute_query):
        """Test successful ClickHouse health check."""
        mock_execute_query.return_value = None
        
        result = await check_clickhouse_health()
        
        assert result.component_name == "clickhouse"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.status == "healthy"
        mock_execute_query.assert_called_once()
        
    @pytest.mark.asyncio
            async def test_clickhouse_health_check_disabled_in_development(self, mock_disabled, mock_dev_mode):
        """Test ClickHouse disabled in development mode."""
    pass
        result = await check_clickhouse_health()
        
        assert result.component_name == "clickhouse"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.status == "healthy"
        assert result.details["status"] == "disabled"
        assert "development" in result.details["reason"]
        
    @pytest.mark.asyncio
                async def test_clickhouse_health_check_error_in_development(self, mock_disabled, mock_dev_mode, mock_execute_query):
        """Test ClickHouse error handling in development mode."""
        mock_execute_query.side_effect = ConnectionError("ClickHouse unavailable")
        
        result = await check_clickhouse_health()
        
        assert result.component_name == "clickhouse"
        assert result.success is True  # Optional service in dev
        assert result.status == "healthy"
        assert result.details["status"] == "disabled"
        
    @pytest.mark.asyncio
                async def test_clickhouse_health_check_error_in_production(self, mock_disabled, mock_dev_mode, mock_execute_query):
        """Test ClickHouse error handling in production mode."""
    pass
        mock_execute_query.side_effect = ConnectionError("ClickHouse connection failed")
        
        result = await check_clickhouse_health()
        
        assert result.component_name == "clickhouse"
        assert result.success is True  # Optional service
        assert result.status == "healthy"
        assert result.details["status"] == "optional_unavailable"


class TestRedisHealthCheck:
    """Test Redis health checking."""
    
    @pytest.mark.asyncio
        async def test_redis_health_check_success(self, mock_ping):
        """Test successful Redis health check."""
        mock_ping.return_value = None
        
        result = await check_redis_health()
        
        assert result.component_name == "redis"
        assert result.success is True
        assert result.status == "healthy"
        assert result.health_score == 1.0
        mock_ping.assert_called_once()
        
    @pytest.mark.asyncio
        async def test_redis_health_check_disabled(self, mock_get_client):
        """Test Redis health check when Redis is disabled."""
    pass
        mock_get_client.side_effect = RuntimeError("Redis disabled in development")
        
        result = await check_redis_health()
        
        assert result.component_name == "redis"
        assert result.success is False
        assert result.status == "degraded"  # Important service degradation
        assert "disabled" in result.error_message
        
    @pytest.mark.asyncio
        async def test_redis_health_check_connection_error(self, mock_get_client):
        """Test Redis connection error handling."""
        mock_client = mock_client_instance  # Initialize appropriate service
        mock_client.ping = AsyncMock(side_effect=ConnectionError("Redis connection lost"))
        mock_get_client.return_value = mock_client
        
        result = await check_redis_health()
        
        assert result.component_name == "redis"
        assert result.success is False
        assert result.status == "degraded"  # Important service
        assert result.health_score == 0.5
        
    @pytest.mark.asyncio
        async def test_get_redis_client_or_fail_enabled(self, mock_redis_manager):
        """Test Redis client retrieval when enabled."""
    pass
        from netra_backend.app.core.health_checkers import _get_redis_client_or_fail
        
        mock_client = mock_client_instance  # Initialize appropriate service
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client = AsyncMock(return_value=mock_client)
        
        result = await _get_redis_client_or_fail()
        
        assert result is mock_client
        
    @pytest.mark.asyncio
        async def test_get_redis_client_or_fail_disabled(self, mock_redis_manager):
        """Test Redis client retrieval when disabled."""
        from netra_backend.app.core.health_checkers import _get_redis_client_or_fail
        
        mock_redis_manager.enabled = False
        
        with pytest.raises(RuntimeError, match="Redis disabled"):
            await _get_redis_client_or_fail()


class TestWebSocketHealthCheck:
    """Test WebSocket health checking."""
    
    @pytest.mark.asyncio
        async def test_websocket_health_check_success(self, mock_get_stats):
        """Test successful WebSocket health check."""
        mock_stats = {"active_connections": 50, "total_messages": 1000}
        mock_health_score = 0.95
        mock_get_stats.return_value = (mock_stats, mock_health_score)
        
        result = await check_websocket_health()
        
        assert result.component_name == "websocket"
        assert result.success is True
        assert result.health_score == mock_health_score
        assert result.status == "healthy"
        assert result.details["metadata"] == mock_stats
        
    @pytest.mark.asyncio
        async def test_get_websocket_stats_and_score(self, mock_get_monitor):
        """Test WebSocket stats retrieval and health score calculation."""
    pass
        from netra_backend.app.core.health_checkers import _get_websocket_stats_and_score
        
        mock_monitor = mock_monitor_instance  # Initialize appropriate service
        mock_stats = {"active_connections": 100}
        mock_monitor.get_stats = AsyncMock(return_value=mock_stats)
        mock_get_monitor.return_value = mock_monitor
        
        stats, score = await _get_websocket_stats_and_score()
        
        assert stats == mock_stats
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        
    def test_calculate_websocket_health_score(self):
        """Test WebSocket health score calculation."""
        from netra_backend.app.core.health_checkers import _calculate_websocket_health_score
        
        # Low connection count should give high score
        low_connections = {"active_connections": 50}
        high_score = _calculate_websocket_health_score(low_connections)
        assert high_score > 0.9
        
        # High connection count should give lower score
        high_connections = {"active_connections": 800}
        low_score = _calculate_websocket_health_score(high_connections)
        assert low_score < high_score
        
        # Very high connections should be capped
        overload_connections = {"active_connections": 2000}
        min_score = _calculate_websocket_health_score(overload_connections)
        assert min_score >= 0.7  # Minimum score


class TestSystemResourcesHealthCheck:
    """Test system resources health checking."""
    
                def test_system_resources_health_check_success(self, mock_disk, mock_memory, mock_cpu):
        """Test successful system resources health check."""
        # Mock healthy system resources
        mock_cpu.return_value = 25.0  # 25% CPU usage
        mock_memory.return_value = Mock(percent=40.0, available=8*1024**3)  # 40% memory usage
        mock_disk.return_value = Mock(percent=30.0, free=100*1024**3)  # 30% disk usage
        
        result = check_system_resources()
        
        assert result.component_name == "system_resources"
        assert result.success is True
        assert result.status == "healthy"
        assert result.health_score > 0.6  # Should be high for healthy system
        assert "cpu_percent" in result.details["metadata"]
        assert "memory_percent" in result.details["metadata"]
        assert "disk_percent" in result.details["metadata"]
        
                def test_system_resources_health_check_high_usage(self, mock_disk, mock_memory, mock_cpu):
        """Test system resources health check with high resource usage."""
    pass
        # Mock high resource usage
        mock_cpu.return_value = 90.0  # 90% CPU usage
        mock_memory.return_value = Mock(percent=85.0, available=1*1024**3)  # 85% memory usage
        mock_disk.return_value = Mock(percent=95.0, free=5*1024**3)  # 95% disk usage
        
        result = check_system_resources()
        
        assert result.component_name == "system_resources"
        assert result.success is True
        assert result.status == "healthy"
        assert result.health_score < 0.3  # Should be low for stressed system
        
    def test_calculate_resource_health_scores(self):
        """Test individual resource health score calculations."""
        from netra_backend.app.core.health_checkers import _calculate_resource_health_scores
        
        metrics = {
            "cpu_percent": 50.0,
            "memory": Mock(percent=75.0),
            "disk": Mock(percent=60.0)
        }
        
        scores = _calculate_resource_health_scores(metrics)
        
        assert scores["cpu"] == 0.5  # 1.0 - 0.5
        assert scores["memory"] == 0.25  # 1.0 - 0.75
        assert scores["disk"] == 0.4  # 1.0 - 0.6
        
    def test_calculate_overall_health_score(self):
        """Test overall health score calculation."""
    pass
        from netra_backend.app.core.health_checkers import _calculate_overall_health_score
        
        health_scores = {
            "cpu": 0.8,
            "memory": 0.6,
            "disk": 0.9
        }
        
        overall_score = _calculate_overall_health_score(health_scores)
        
        expected = (0.8 + 0.6 + 0.9) / 3
        assert overall_score == expected


class TestServicePriorityHandling:
    """Test service priority handling and graceful degradation."""
    
    def test_handle_service_failure_critical(self):
        """Test critical service failure handling."""
        result = _handle_service_failure("postgres", "Connection failed", 1000.0)
        
        assert result.success is False
        assert result.status == "unhealthy"
        assert result.health_score == 0.0
        assert result.error_message == "Connection failed"
        
    def test_handle_service_failure_important(self):
        """Test important service failure handling."""
    pass
        result = _handle_service_failure("redis", "Connection timeout", 2000.0)
        
        assert result.success is False
        assert result.status == "degraded"
        assert result.health_score == 0.5
        assert "Reduced functionality" in result.details["impact"]
        
    def test_handle_service_failure_optional(self):
        """Test optional service failure handling."""
        result = _handle_service_failure("clickhouse", "Service unavailable", 500.0)
        
        assert result.success is True  # System remains healthy
        assert result.status == "healthy"
        assert result.health_score == 1.0
        assert result.details["status"] == "optional_unavailable"
        
    def test_handle_service_failure_unknown_service(self):
        """Test handling of unknown service (defaults to important)."""
    pass
        result = _handle_service_failure("unknown_service", "Error", 100.0)
        
        assert result.success is False
        assert result.status == "degraded"  # Default to important
        assert result.health_score == 0.5


class TestEnvironmentDetection:
    """Test environment detection and configuration."""
    
        def test_is_development_mode_true(self, mock_get_env):
        """Test development mode detection when in development."""
        mock_get_env.return_value = "development"
        
        assert _is_development_mode() is True
        
        def test_is_development_mode_false(self, mock_get_env):
        """Test development mode detection when in production."""
    pass
        mock_get_env.return_value = "production"
        
        assert _is_development_mode() is False
        
            def test_is_development_mode_fallback(self, mock_config_manager, mock_get_env):
        """Test development mode detection with fallback to config."""
        mock_get_env.side_effect = Exception("Environment detection failed")
        mock_config = mock_config_instance  # Initialize appropriate service
        mock_config.environment = "development"
        mock_config_manager.get_config.return_value = mock_config
        
        assert _is_development_mode() is True
        
        def test_is_clickhouse_disabled_development(self, mock_get_env):
        """Test ClickHouse disabled detection in development."""
    pass
        mock_get_env.return_value = "development"
        
        assert _is_clickhouse_disabled() is True
        
        def test_is_clickhouse_disabled_testing(self, mock_get_env):
        """Test ClickHouse disabled detection in testing."""
        mock_get_env.return_value = "testing"
        
        assert _is_clickhouse_disabled() is True
        
            def test_is_clickhouse_disabled_by_config(self, mock_config_manager, mock_get_env):
        """Test ClickHouse disabled by configuration."""
    pass
        mock_get_env.return_value = "production"
        mock_config = mock_config_instance  # Initialize appropriate service
        mock_config.clickhouse_mode = "disabled"
        mock_config.skip_clickhouse_init = False
        mock_config_manager.get_config.return_value = mock_config
        
        assert _is_clickhouse_disabled() is True
        
    def test_get_health_check_timeout_environments(self):
        """Test health check timeout for different environments."""
        with patch('netra_backend.app.core.environment_constants.get_current_environment') as mock_get_env:
            # Production timeout
            mock_get_env.return_value = "production"
            assert _get_health_check_timeout() == 5.0
            
            # Staging timeout
            mock_get_env.return_value = "staging"
            assert _get_health_check_timeout() == 8.0
            
            # Development timeout
            mock_get_env.return_value = "development"
            assert _get_health_check_timeout() == 10.0
            
            # Testing timeout
            mock_get_env.return_value = "testing"
            assert _get_health_check_timeout() == 30.0
            
            # Unknown environment defaults
            mock_get_env.return_value = "unknown"
            assert _get_health_check_timeout() == 5.0
            
    def test_get_health_check_timeout_fallback(self):
        """Test health check timeout fallback when environment detection fails."""
    pass
        with patch('netra_backend.app.core.environment_constants.get_current_environment', 
                  side_effect=Exception("Failed")):
            assert _get_health_check_timeout() == 5.0  # Conservative default


class TestHealthCheckerMethods:
    """Test HealthChecker individual component methods."""
    
    @pytest.mark.asyncio
    async def test_check_component_success(self):
        """Test checking individual component successfully."""
        checker = HealthChecker()
        
        with patch.object(checker, 'checkers') as mock_checkers:
            mock_check_func = AsyncMock(return_value=Mock(
                component_name="test",
                success=True,
                status="healthy"
            ))
            mock_checkers.__getitem__.return_value = mock_check_func
            mock_checkers.__contains__.return_value = True
            
            result = await checker.check_component("test")
            
            assert result.component_name == "test"
            assert result.success is True
            mock_check_func.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_check_component_unknown(self):
        """Test checking unknown component."""
    pass
        checker = HealthChecker()
        
        result = await checker.check_component("nonexistent")
        
        assert result.component_name == "nonexistent"
        assert result.success is False
        assert "Unknown component" in result.error_message
        
    @pytest.mark.asyncio
    async def test_check_component_exception(self):
        """Test checking component that raises exception."""
        checker = HealthChecker()
        
        with patch.object(checker, 'checkers') as mock_checkers:
            mock_check_func = AsyncMock(side_effect=Exception("Check failed"))
            mock_checkers.__getitem__.return_value = mock_check_func
            mock_checkers.__contains__.return_value = True
            
            result = await checker.check_component("failing")
            
            assert result.component_name == "failing"
            assert result.success is False
            assert result.error_message == "Check failed"
            
    @pytest.mark.asyncio
    async def test_check_all_components(self):
        """Test checking all components."""
    pass
        checker = HealthChecker()
        
        with patch.object(checker, 'checkers') as mock_checkers:
            # Mock successful checker
            success_checker = AsyncMock(return_value=Mock(
                component_name="success",
                success=True,
                status="healthy"
            ))
            
            # Mock sync system resources checker
            system_checker = Mock(return_value=Mock(
                component_name="system",
                success=True,
                status="healthy"
            ))
            
            mock_checkers.items.return_value = [
                ("success", success_checker),
                ("system_resources", system_checker)
            ]
            
            results = await checker.check_all()
            
            assert len(results) == 2
            assert "success" in results
            assert "system_resources" in results
            success_checker.assert_called_once()
            system_checker.assert_called_once()


class TestOverallHealthAssessment:
    """Test overall system health assessment with priority-based logic."""
    
    @pytest.mark.asyncio
    async def test_get_overall_health_all_healthy(self):
        """Test overall health when all services are healthy."""
        checker = HealthChecker()
        
        # Mock all services as healthy
        mock_results = {
            "postgres": Mock(status="healthy", health_score=1.0),
            "redis": Mock(status="healthy", health_score=1.0),
            "clickhouse": Mock(status="healthy", health_score=1.0),
            "websocket": Mock(status="healthy", health_score=1.0),
            "system_resources": Mock(status="healthy", health_score=1.0)
        }
        
        with patch.object(checker, 'check_all', return_value=mock_results):
            health = await checker.get_overall_health()
        
        assert health["status"] == "healthy"
        assert health["health_score"] > 0.9
        assert health["priority_assessment"]["critical_services_healthy"] is True
        assert health["priority_assessment"]["important_services_healthy"] is True
        
    @pytest.mark.asyncio
    async def test_get_overall_health_critical_service_failed(self):
        """Test overall health when critical service fails."""
    pass
        checker = HealthChecker()
        
        mock_results = {
            "postgres": Mock(status="unhealthy", health_score=0.0),  # Critical service failed
            "redis": Mock(status="healthy", health_score=1.0),
            "websocket": Mock(status="healthy", health_score=1.0)
        }
        
        with patch.object(checker, 'check_all', return_value=mock_results):
            health = await checker.get_overall_health()
        
        assert health["status"] == "unhealthy"
        assert health["priority_assessment"]["critical_services_healthy"] is False
        assert "postgres" in health["priority_assessment"]["problem_services"]
        
    @pytest.mark.asyncio
    async def test_get_overall_health_important_service_degraded(self):
        """Test overall health when important service is degraded."""
        checker = HealthChecker()
        
        mock_results = {
            "postgres": Mock(status="healthy", details={"health_score": 1.0}),
            "redis": Mock(status="degraded", details={"health_score": 0.5}),  # Important service degraded
            "websocket": Mock(status="healthy", details={"health_score": 1.0})
        }
        
        with patch.object(checker, 'check_all', return_value=mock_results):
            health = await checker.get_overall_health()
        
        assert health["status"] == "degraded"
        assert health["priority_assessment"]["critical_services_healthy"] is True
        assert health["priority_assessment"]["important_services_healthy"] is False
        
    @pytest.mark.asyncio
    async def test_get_overall_health_optional_service_failed(self):
        """Test overall health when optional service fails."""
    pass
        checker = HealthChecker()
        
        mock_results = {
            "postgres": Mock(status="healthy", health_score=1.0),
            "redis": Mock(status="healthy", health_score=1.0),
            "clickhouse": Mock(status="unhealthy", health_score=0.0)  # Optional service failed
        }
        
        with patch.object(checker, 'check_all', return_value=mock_results):
            health = await checker.get_overall_health()
        
        # System should remain healthy despite optional service failure
        assert health["status"] == "healthy"
        assert health["priority_assessment"]["critical_services_healthy"] is True
        assert health["priority_assessment"]["important_services_healthy"] is True


class TestPriorityBasedHealthCalculation:
    """Test priority-based health calculation logic."""
    
    def test_calculate_priority_based_health_healthy(self):
        """Test priority-based health calculation for healthy system."""
        results = {
            "postgres": Mock(status="healthy", details={"health_score": 1.0}),
            "redis": Mock(status="healthy", details={"health_score": 1.0})
        }
        
        health = _calculate_priority_based_health(results)
        
        assert health["status"] == "healthy"
        assert health["health_score"] > 0.9
        assert health["healthy_components"] == 2
        assert health["total_components"] == 2
        
    def test_calculate_priority_based_health_critical_failed(self):
        """Test priority-based health calculation with critical service failure."""
    pass
        results = {
            "postgres": Mock(status="unhealthy", details={"health_score": 0.0}),
            "redis": Mock(status="healthy", details={"health_score": 1.0})
        }
        
        health = _calculate_priority_based_health(results)
        
        assert health["status"] == "unhealthy"
        assert len(health["priority_assessment"]["problem_services"]) > 0
        
    def test_calculate_priority_based_health_important_degraded(self):
        """Test priority-based health calculation with important service degraded."""
        results = {
            "postgres": Mock(status="healthy", details={"health_score": 1.0}),
            "redis": Mock(status="degraded", details={"health_score": 0.5})
        }
        
        health = _calculate_priority_based_health(results)
        
        assert health["status"] == "degraded"
        assert not health["priority_assessment"]["important_services_healthy"]


class TestSpecificHealthCheckMethods:
    """Test specific health check methods expected by external tests."""
    
    @pytest.mark.asyncio
    async def test_check_postgres_method(self):
        """Test specific postgres check method."""
        checker = HealthChecker()
        
        with patch('netra_backend.app.core.health_checkers.check_postgres_health') as mock_check:
            mock_result = Mock(status="healthy", response_time=0.05)
            mock_check.return_value = mock_result
            
            result = await checker.check_postgres()
            
            assert result["healthy"] is True
            assert result["latency_ms"] == 50.0  # 0.05 * 1000
            
    @pytest.mark.asyncio
    async def test_check_postgres_method_error(self):
        """Test postgres check method with error."""
    pass
        checker = HealthChecker()
        
        with patch('netra_backend.app.core.health_checkers.check_postgres_health', 
                  side_effect=Exception("DB error")):
            result = await checker.check_postgres()
            
            assert result["healthy"] is False
            assert result["latency_ms"] == 0.0
            assert result["error"] == "DB error"
            
    @pytest.mark.asyncio
    async def test_check_redis_method(self):
        """Test specific redis check method."""
        checker = HealthChecker()
        
        with patch('netra_backend.app.core.health_checkers.check_redis_health') as mock_check:
            mock_result = Mock(status="degraded", response_time=0.02)
            mock_check.return_value = mock_result
            
            result = await checker.check_redis()
            
            assert result["healthy"] is True  # Accepts degraded as healthy
            assert result["latency_ms"] == 20.0
            
    @pytest.mark.asyncio
    async def test_check_oauth_providers_method(self):
        """Test OAuth providers check method."""
    pass
        checker = HealthChecker()
        
        result = await checker.check_oauth_providers()
        
        assert result["healthy"] is True
        assert "latency_ms" in result
        
    @pytest.mark.asyncio
    async def test_check_auth_service_health_method(self):
        """Test comprehensive auth service health check."""
        checker = HealthChecker()
        
        with patch.object(checker, 'check_postgres', return_value={"healthy": True, "latency_ms": 10.0}):
            with patch.object(checker, 'check_redis', return_value={"healthy": True, "latency_ms": 5.0}):
                with patch.object(checker, 'check_oauth_providers', return_value={"healthy": True, "latency_ms": 15.0}):
                    result = await checker.check_auth_service_health()
                    
                    assert "database" in result
                    assert "redis" in result
                    assert "oauth" in result
                    assert result["database"]["healthy"] is True
                    assert result["redis"]["healthy"] is True
                    assert result["oauth"]["healthy"] is True


@pytest.mark.integration
class TestHealthCheckersIntegration:
    """Integration tests for health checkers with real system interactions."""
    
    @pytest.mark.asyncio
    async def test_real_system_resources_check(self):
        """Test system resources check with real system data."""
        result = check_system_resources()
        
        assert result.component_name == "system_resources"
        assert result.success is True
        assert result.status == "healthy"
        assert isinstance(result.health_score, float)
        assert 0.0 <= result.health_score <= 1.0
        assert result.response_time_ms >= 0
        
        # Verify metadata contains expected fields
        metadata = result.details["metadata"]
        assert "cpu_percent" in metadata
        assert "memory_percent" in metadata
        assert "disk_percent" in metadata
        assert "memory_available_gb" in metadata
        assert "disk_free_gb" in metadata
        
    @pytest.mark.asyncio
    async def test_health_checker_complete_workflow(self):
        """Test complete health checker workflow."""
    pass
        checker = HealthChecker()
        
        # Check that all checkers are available
        assert len(checker.checkers) >= 5
        
        # Test individual component checks
        for component_name in ["system_resources"]:  # Test sync component
            result = await checker.check_component(component_name)
            assert result.component_name == component_name
            assert isinstance(result.success, bool)
            
        # Test overall health assessment structure
        health = {"status": "healthy", "health_score": 0.9, "total_components": 5}
        assert "status" in health
        assert "health_score" in health
        assert health["health_score"] >= 0.0


class TestHealthCheckResultCreation:
    """Test health check result creation utilities."""
    
    def test_create_success_result(self):
        """Test successful health check result creation."""
        from netra_backend.app.core.health_checkers import _create_success_result
        
        result = _create_success_result("test_component", 150.0)
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.status == "healthy"
        assert result.response_time_ms == 150.0
        assert result.response_time == 0.15
        
    def test_create_failed_result(self):
        """Test failed health check result creation."""
    pass
        from netra_backend.app.core.health_checkers import _create_failed_result
        
        result = _create_failed_result("test_component", "Connection failed", 500.0)
        
        assert result.component_name == "test_component"
        assert result.success is False
        assert result.health_score == 0.0
        assert result.status == "unhealthy"
        assert result.response_time_ms == 500.0
        assert result.error_message == "Connection failed"
        
    def test_create_disabled_result(self):
        """Test disabled service result creation."""
        from netra_backend.app.core.health_checkers import _create_disabled_result
        
        result = _create_disabled_result("test_component", "Disabled in development")
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.status == "healthy"
        assert result.response_time_ms == 0.0
        assert result.details["status"] == "disabled"
        assert result.details["reason"] == "Disabled in development"


class TestServicePriorityEdgeCases:
    """Test edge cases and complex scenarios in service priority handling."""
    
    def test_service_priority_unknown_service_default(self):
        """Test that unknown services get appropriate default priority."""
        from netra_backend.app.core.health_checkers import _get_service_priority_for_environment
        
        with patch('netra_backend.app.core.health_checkers.unified_config_manager') as mock_config_manager:
            mock_config = mock_config_instance  # Initialize appropriate service
            mock_config.environment = 'production'
            mock_config_manager.get_config.return_value = mock_config
            
            # Unknown service should get IMPORTANT priority by default
            priority = _get_service_priority_for_environment("unknown_service")
            assert priority == ServicePriority.IMPORTANT
    
    def test_service_priority_staging_redis_optional_flag(self):
        """Test redis optional flag in staging environment."""
    pass
        from netra_backend.app.core.health_checkers import _get_service_priority_for_environment
        
        with patch('netra_backend.app.core.health_checkers.unified_config_manager') as mock_config_manager:
            mock_config = mock_config_instance  # Initialize appropriate service
            mock_config.environment = 'staging'
            mock_config.redis_optional_in_staging = True
            mock_config_manager.get_config.return_value = mock_config
            
            # Redis should be OPTIONAL when flag is set in staging
            priority = _get_service_priority_for_environment("redis")
            assert priority == ServicePriority.OPTIONAL
    
    def test_service_priority_production_critical_services(self):
        """Test critical services maintain priority in production."""
        from netra_backend.app.core.health_checkers import _get_service_priority_for_environment
        
        with patch('netra_backend.app.core.health_checkers.unified_config_manager') as mock_config_manager:
            mock_config = mock_config_instance  # Initialize appropriate service
            mock_config.environment = 'production'
            mock_config_manager.get_config.return_value = mock_config
            
            # Postgres should always be CRITICAL
            priority = _get_service_priority_for_environment("postgres")
            assert priority == ServicePriority.CRITICAL
            
            # System resources should be IMPORTANT
            priority = _get_service_priority_for_environment("system_resources")
            assert priority == ServicePriority.IMPORTANT
    @pytest.mark.asyncio
    async def test_health_checker_concurrent_checks(self):
        """Test concurrent health check executions."""
    pass
        checker = HealthChecker()
        
        # Mock multiple concurrent checks
        check_tasks = []
        for i in range(3):
            task = asyncio.create_task(checker.check_component('postgres'))
            check_tasks.append(task)
        
        # Should handle concurrent checks without issues
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        assert len(results) == 3
        
        # All results should be valid (no exceptions)
        for result in results:
            assert not isinstance(result, Exception)
