'''Core unit tests for health checker functions.

Tests system health monitoring for SLA compliance.
SLA CRITICAL - Maintains system uptime for enterprise contracts.

Business Value: Ensures reliable health monitoring preventing SLA violations
that could result in enterprise contract penalties and customer churn.
'''

import sys
from pathlib import Path
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.core.health_checkers import (
    check_clickhouse_health,
    check_postgres_health,
    check_redis_health,
    check_system_resources,
    check_websocket_health
)
from netra_backend.app.schemas.core_models import HealthCheckResult

class TestHealthCheckersCore:
    """Core test suite for database and service health checkers."""

    @pytest.fixture
    def mock_postgres_engine(self):
        """Create mock PostgreSQL async engine."""
        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        return mock_engine

    @pytest.fixture
    def mock_clickhouse_client(self):
        """Create mock ClickHouse client."""
        mock_client = AsyncMock()
        mock_client.execute = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        return mock_client

    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager."""
        mock_manager = Mock()
        mock_manager.enabled = True
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_manager.get_client = AsyncMock(return_value=mock_client)
        return mock_manager, mock_client

    @pytest.mark.asyncio
    async def test_check_postgres_health_success(self):
        """Test successful PostgreSQL health check."""
        with patch('netra_backend.app.core.health_checkers._execute_postgres_query') as mock_execute:
            mock_execute.return_value = None  # Successful query
            
            result = await check_postgres_health()
            
            assert isinstance(result, HealthCheckResult)
            assert result.status == "healthy"
            assert result.response_time_ms >= 0
            assert result.details["component_name"] == "postgres"
            assert result.details["success"] is True

    @pytest.mark.asyncio
    async def test_check_postgres_health_connection_error(self):
        """Test PostgreSQL health check with connection error."""
        with patch('netra_backend.app.core.health_checkers._execute_postgres_query') as mock_execute:
            mock_execute.side_effect = Exception("Connection failed")
            
            result = await check_postgres_health()
            
            assert result.status == "unhealthy"
            assert result.details["success"] is False
            assert "Connection failed" in result.details["error_message"]

    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, mock_redis_manager):
        """Test successful Redis health check."""
        redis_manager, redis_client = mock_redis_manager
        
        with patch('netra_backend.app.core.health_checkers.redis_manager', redis_manager):
            result = await check_redis_health()
            
            assert result.status == "healthy"
            assert result.details["component_name"] == "redis"
            assert result.details["success"] is True
            redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_clickhouse_health_success(self, mock_clickhouse_client):
        """Test successful ClickHouse health check."""
        with patch('netra_backend.app.core.health_checkers._is_development_mode', return_value=False), \
             patch('netra_backend.app.core.health_checkers._is_clickhouse_disabled_in_dev', return_value=False), \
             patch('netra_backend.app.core.health_checkers._get_clickhouse_client', return_value=mock_clickhouse_client):
            
            result = await check_clickhouse_health()
            
            assert result.status == "healthy"
            assert result.details["component_name"] == "clickhouse"
            assert result.details["success"] is True
            mock_clickhouse_client.execute.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_check_websocket_health_success(self):
        """Test successful WebSocket health check."""
        mock_manager = Mock()
        mock_manager.get_stats = AsyncMock(return_value={
            "active_connections": 10,
            "total_connections": 50
        })
        
        with patch('netra_backend.app.core.health_checkers._get_websocket_manager', return_value=mock_manager):
            result = await check_websocket_health()
            
            assert result.status == "healthy"
            assert result.details["component_name"] == "websocket"
            assert result.details["success"] is True
            assert "metadata" in result.details

    @pytest.mark.asyncio
    async def test_check_system_resources_success(self):
        """Test successful system resources health check."""
        with patch('netra_backend.app.core.health_checkers._get_system_metrics') as mock_metrics:
            mock_metrics.return_value = {
                "cpu_usage": 45.0,
                "memory_usage": 60.0,
                "disk_usage": 30.0
            }
            
            result = await check_system_resources()
            
            assert result.status == "healthy"
            assert result.details["component_name"] == "system_resources"
            assert result.details["success"] is True
            assert "cpu_usage" in result.details
            assert "memory_usage" in result.details
            assert "disk_usage" in result.details

    def test_health_check_result_structure(self):
        """Test HealthCheckResult structure."""
        result = HealthCheckResult(
            component_name="test",
            success=True,
            health_score=1.0,
            response_time_ms=50.0,
            status="healthy",
            response_time=0.05,
            details={"component_name": "test", "success": True}
        )
        
        assert result.status == "healthy"
        assert result.response_time == 0.05
        assert result.details["success"] is True
        assert isinstance(result.details, dict)
        assert "component_name" in result.details

