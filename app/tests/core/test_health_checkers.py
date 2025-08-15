"""Tests for health checker functions."""

import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.core.health_checkers import (
    check_postgres_health, check_clickhouse_health, check_redis_health,
    check_websocket_health, check_system_resources,
    _create_success_result, _create_failed_result, _create_disabled_result
)
from app.core.health_types import HealthCheckResult


class TestHealthCheckerHelpers:
    """Test helper functions for health checkers."""
    
    def test_create_success_result(self):
        """Test creating successful health check result."""
        result = _create_success_result("test_component", 150.5)
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.response_time_ms == 150.5
        assert result.error_message == ""
    
    def test_create_failed_result(self):
        """Test creating failed health check result."""
        result = _create_failed_result("test_component", "Connection failed", 500.0)
        
        assert result.component_name == "test_component"
        assert result.success is False
        assert result.health_score == 0.0
        assert result.response_time_ms == 500.0
        assert result.error_message == "Connection failed"
    
    def test_create_failed_result_default_response_time(self):
        """Test creating failed result with default response time."""
        result = _create_failed_result("test", "Error")
        
        assert result.response_time_ms == 0.0
    
    def test_create_disabled_result(self):
        """Test creating disabled service result."""
        result = _create_disabled_result("disabled_service", "Service disabled in dev mode")
        
        assert result.component_name == "disabled_service"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.response_time_ms == 0.0
        assert result.metadata["status"] == "disabled"
        assert result.metadata["reason"] == "Service disabled in dev mode"


class TestPostgresHealthChecker:
    """Test PostgreSQL health checker."""
    
    @pytest.mark.asyncio
    async def test_postgres_health_success(self):
        """Test successful PostgreSQL health check."""
        mock_engine = Mock()
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch("app.core.health_checkers.async_engine", mock_engine):
            result = await check_postgres_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.component_name == "postgres"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.response_time_ms > 0
        mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_postgres_health_no_engine(self):
        """Test PostgreSQL health check with no engine."""
        with patch("app.core.health_checkers.async_engine", None):
            result = await check_postgres_health()
        
        assert result.component_name == "postgres"
        assert result.success is False
        assert result.health_score == 0.0
        assert "not initialized" in result.error_message
    
    @pytest.mark.asyncio
    async def test_postgres_health_connection_error(self):
        """Test PostgreSQL health check with connection error."""
        mock_engine = Mock()
        mock_engine.begin.side_effect = Exception("Connection failed")
        
        with patch("app.core.health_checkers.async_engine", mock_engine):
            result = await check_postgres_health()
        
        assert result.success is False
        assert result.health_score == 0.0
        assert "Connection failed" in result.error_message


class TestClickHouseHealthChecker:
    """Test ClickHouse health checker."""
    
    @pytest.mark.asyncio
    async def test_clickhouse_health_success(self):
        """Test successful ClickHouse health check."""
        mock_client = AsyncMock()
        mock_get_client = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client
        
        with patch("app.core.health_checkers.get_clickhouse_client", mock_get_client):
            result = await check_clickhouse_health()
        
        assert result.component_name == "clickhouse"
        assert result.success is True
        assert result.health_score == 1.0
        mock_client.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_clickhouse_health_error(self):
        """Test ClickHouse health check with error."""
        mock_get_client = AsyncMock()
        mock_get_client.side_effect = Exception("ClickHouse unavailable")
        
        with patch("app.core.health_checkers.get_clickhouse_client", mock_get_client):
            result = await check_clickhouse_health()
        
        assert result.success is False
        assert "ClickHouse unavailable" in result.error_message


class TestRedisHealthChecker:
    """Test Redis health checker."""
    
    @pytest.mark.asyncio
    async def test_redis_health_success(self):
        """Test successful Redis health check."""
        mock_redis_manager = Mock()
        mock_redis_manager.enabled = True
        mock_client = AsyncMock()
        mock_redis_manager.get_client.return_value = mock_client
        
        with patch("app.core.health_checkers.redis_manager", mock_redis_manager):
            result = await check_redis_health()
        
        assert result.component_name == "redis"
        assert result.success is True
        assert result.health_score == 1.0
        mock_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_redis_health_disabled(self):
        """Test Redis health check when disabled."""
        mock_redis_manager = Mock()
        mock_redis_manager.enabled = False
        
        with patch("app.core.health_checkers.redis_manager", mock_redis_manager):
            result = await check_redis_health()
        
        assert result.component_name == "redis"
        assert result.success is True
        assert result.health_score == 1.0
        assert result.metadata["status"] == "disabled"
    
    @pytest.mark.asyncio
    async def test_redis_health_no_client(self):
        """Test Redis health check with no client."""
        mock_redis_manager = Mock()
        mock_redis_manager.enabled = True
        mock_redis_manager.get_client.return_value = None
        
        with patch("app.core.health_checkers.redis_manager", mock_redis_manager):
            result = await check_redis_health()
        
        assert result.success is False
        assert "not available" in result.error_message
    
    @pytest.mark.asyncio
    async def test_redis_health_ping_error(self):
        """Test Redis health check with ping error."""
        mock_redis_manager = Mock()
        mock_redis_manager.enabled = True
        mock_client = AsyncMock()
        mock_client.ping.side_effect = Exception("Redis connection failed")
        mock_redis_manager.get_client.return_value = mock_client
        
        with patch("app.core.health_checkers.redis_manager", mock_redis_manager):
            result = await check_redis_health()
        
        assert result.success is False
        assert "Redis connection failed" in result.error_message


class TestWebSocketHealthChecker:
    """Test WebSocket health checker."""
    
    @pytest.mark.asyncio
    async def test_websocket_health_success(self):
        """Test successful WebSocket health check."""
        mock_connection_manager = Mock()
        mock_stats = {
            "active_connections": 50,
            "total_connections": 100,
            "active_users": 25
        }
        mock_connection_manager.get_stats.return_value = mock_stats
        
        with patch("app.core.health_checkers.connection_manager", mock_connection_manager):
            result = await check_websocket_health()
        
        assert result.component_name == "websocket"
        assert result.success is True
        assert result.health_score > 0.7  # Should be high with reasonable connection count
        assert result.metadata == mock_stats
    
    @pytest.mark.asyncio
    async def test_websocket_health_high_connections(self):
        """Test WebSocket health check with high connection count."""
        mock_connection_manager = Mock()
        mock_stats = {"active_connections": 800}  # High connection count
        mock_connection_manager.get_stats.return_value = mock_stats
        
        with patch("app.core.health_checkers.connection_manager", mock_connection_manager):
            result = await check_websocket_health()
        
        assert result.health_score < 1.0  # Should be lower due to high connections
    
    @pytest.mark.asyncio
    async def test_websocket_health_error(self):
        """Test WebSocket health check with error."""
        with patch("app.core.health_checkers.connection_manager") as mock_manager:
            mock_manager.get_stats.side_effect = Exception("WebSocket manager error")
            result = await check_websocket_health()
        
        assert result.success is False
        assert "WebSocket manager error" in result.error_message


class TestSystemResourcesChecker:
    """Test system resources health checker."""
    
    def test_system_resources_success(self):
        """Test successful system resources check."""
        mock_memory = Mock()
        mock_memory.percent = 60.0
        mock_memory.available = 4 * (1024**3)  # 4GB
        
        mock_disk = Mock()
        mock_disk.percent = 45.0
        mock_disk.free = 100 * (1024**3)  # 100GB
        
        with patch("app.core.health_checkers.psutil.cpu_percent", return_value=25.0), \
             patch("app.core.health_checkers.psutil.virtual_memory", return_value=mock_memory), \
             patch("app.core.health_checkers.psutil.disk_usage", return_value=mock_disk):
            
            result = check_system_resources()
        
        assert result.component_name == "system_resources"
        assert result.success is True
        assert result.health_score > 0.5  # Should be reasonable with moderate usage
        assert result.metadata["cpu_percent"] == 25.0
        assert result.metadata["memory_percent"] == 60.0
        assert result.metadata["disk_percent"] == 45.0
    
    def test_system_resources_high_usage(self):
        """Test system resources check with high usage."""
        mock_memory = Mock()
        mock_memory.percent = 95.0
        mock_memory.available = 0.5 * (1024**3)  # 0.5GB
        
        mock_disk = Mock()
        mock_disk.percent = 90.0
        mock_disk.free = 1 * (1024**3)  # 1GB
        
        with patch("app.core.health_checkers.psutil.cpu_percent", return_value=98.0), \
             patch("app.core.health_checkers.psutil.virtual_memory", return_value=mock_memory), \
             patch("app.core.health_checkers.psutil.disk_usage", return_value=mock_disk):
            
            result = check_system_resources()
        
        assert result.health_score < 0.3  # Should be low with high usage
    
    def test_system_resources_error(self):
        """Test system resources check with error."""
        with patch("app.core.health_checkers.psutil.cpu_percent", side_effect=Exception("psutil error")):
            result = check_system_resources()
        
        assert result.success is False
        assert "psutil error" in result.error_message
    
    def test_system_resources_response_time(self):
        """Test that response time is measured."""
        mock_memory = Mock()
        mock_memory.percent = 50.0
        mock_memory.available = 2 * (1024**3)
        
        mock_disk = Mock()
        mock_disk.percent = 50.0
        mock_disk.free = 50 * (1024**3)
        
        with patch("app.core.health_checkers.psutil.cpu_percent", return_value=50.0), \
             patch("app.core.health_checkers.psutil.virtual_memory", return_value=mock_memory), \
             patch("app.core.health_checkers.psutil.disk_usage", return_value=mock_disk):
            
            result = check_system_resources()
        
        assert result.response_time_ms > 0