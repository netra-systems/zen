"""Integration tests for circuit breaker with services.

This module tests circuit breaker integration with:
- LLM client
- Database client  
- External API client
- Monitoring system
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from app.llm.client import ResilientLLMClient
from app.db.client import ResilientDatabaseClient
from app.services.external_api_client import ResilientHTTPClient
from app.services.circuit_breaker_monitor import CircuitBreakerMonitor, AlertSeverity, CircuitBreakerEvent
from app.core.circuit_breaker import CircuitBreakerOpenError, CircuitConfig


class TestLLMClientCircuitBreaker:
    """Test LLM client circuit breaker integration."""
    
    def setup_method(self):
        """Set up test LLM client."""
        # Clean up any existing circuit breakers to ensure test isolation
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
        
        self.mock_llm_manager = MagicMock()
        self.llm_client = ResilientLLMClient(self.mock_llm_manager)
    
    def teardown_method(self):
        """Clean up after test."""
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
    
    async def test_successful_llm_call(self):
        """Test successful LLM call through circuit breaker."""
        self.mock_llm_manager.ask_llm = AsyncMock(return_value="test response")
        
        result = await self.llm_client.ask_llm("test prompt", "test_config")
        
        assert result == "test response"
        self.mock_llm_manager.ask_llm.assert_called_once_with(
            "test prompt", "test_config", True
        )
    
    async def test_llm_circuit_breaker_opens(self):
        """Test LLM circuit breaker opens after failures."""
        self.mock_llm_manager.ask_llm = AsyncMock(side_effect=Exception("LLM error"))
        
        # Configure circuit with low threshold for testing
        circuit = await self.llm_client.core_client.circuit_manager.get_circuit("test_config")
        circuit.config.failure_threshold = 2
        circuit.adaptive_failure_threshold = 2
        
        # Check initial state
        assert circuit.state.value == "closed"
        assert circuit.failure_count == 0
        
        # First failure
        with pytest.raises(Exception, match="LLM error"):
            await self.llm_client.ask_llm("test prompt", "test_config")
        
        # Check state after first failure
        assert circuit.failure_count == 1
        assert circuit.state.value == "closed"
        
        # Second failure should open circuit
        with pytest.raises(Exception, match="LLM error"):
            await self.llm_client.ask_llm("test prompt", "test_config")
        
        # Check state after second failure - circuit should be open
        assert circuit.failure_count == 2
        assert circuit.state.value == "open"
        
        # Third call should be blocked by circuit breaker and return fallback
        result = await self.llm_client.ask_llm("test prompt", "test_config")
        
        # Should return fallback response
        assert "Service temporarily unavailable" in result
        assert "test_config" in result
    
    async def test_llm_structured_output_protection(self):
        """Test structured LLM output with circuit breaker."""
        from pydantic import BaseModel
        
        class TestSchema(BaseModel):
            message: str
        
        mock_response = TestSchema(message="test")
        self.mock_llm_manager.ask_structured_llm = AsyncMock(return_value=mock_response)
        
        result = await self.llm_client.ask_structured_llm(
            "test prompt", "test_config", TestSchema
        )
        
        assert result.message == "test"
    
    async def test_llm_health_check(self):
        """Test LLM client health check."""
        mock_health = MagicMock()
        mock_health.healthy = True
        self.mock_llm_manager.health_check = AsyncMock(return_value=mock_health)
        
        health = await self.llm_client.health_check("test_config")
        
        assert "llm_health" in health
        assert "circuit_status" in health
        assert "overall_health" in health


class TestDatabaseClientCircuitBreaker:
    """Test database client circuit breaker integration."""
    
    def setup_method(self):
        """Set up test database client."""
        # Clean up any existing circuit breakers to ensure test isolation
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
        
        self.db_client = ResilientDatabaseClient()
    
    def teardown_method(self):
        """Clean up after test."""
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
    
    @patch('app.db.client_postgres_session.TransactionHandler.get_session')
    async def test_successful_db_query(self, mock_get_session):
        """Test successful database query through circuit breaker."""
        mock_session = AsyncMock()
        
        # Create mock result with proper row structure
        mock_row = MagicMock()
        mock_row._mapping = {"id": 1, "name": "test"}
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock the session context manager to yield the mock session
        mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await self.db_client.execute_read_query("SELECT * FROM test")
        
        assert len(result) == 1
        assert result[0]["name"] == "test"
    
    @patch('app.db.client_postgres_session.TransactionHandler.get_session')
    async def test_db_circuit_breaker_fallback(self, mock_get_session):
        """Test database circuit breaker fallback behavior."""
        mock_get_session.side_effect = Exception("Database connection error")
        
        # Configure BOTH postgres and read circuits with low thresholds
        postgres_circuit = await self.db_client._get_postgres_circuit()
        read_circuit = await self.db_client._get_read_circuit()
        
        postgres_circuit.config.failure_threshold = 1
        read_circuit.config.failure_threshold = 1
        # For AdaptiveCircuitBreaker, also set the adaptive threshold
        postgres_circuit.adaptive_failure_threshold = 1
        read_circuit.adaptive_failure_threshold = 1
        
        # Verify initial state
        assert postgres_circuit.state.value == "closed"
        assert postgres_circuit.failure_count == 0
        
        # First call should fail with exception and record failure
        with pytest.raises(Exception, match="Database connection error"):
            await self.db_client.execute_read_query("SELECT * FROM test")
        
        # Verify postgres circuit recorded the failure and opened
        assert postgres_circuit.failure_count == 1
        assert postgres_circuit.state.value == "open"
        
        # Second call should be blocked by postgres circuit breaker and return empty result
        result = await self.db_client.execute_read_query("SELECT * FROM test")
        
        # Should return empty result as fallback
        assert result == []
    
    async def test_db_health_check(self):
        """Test database client health check."""
        with patch.object(self.db_client, '_test_connection') as mock_test:
            mock_test.return_value = {"status": "healthy", "test_query": True}
            
            health = await self.db_client.health_check()
            
            assert "connection" in health
            assert "circuits" in health
            assert "overall_health" in health


class TestHTTPClientCircuitBreaker:
    """Test HTTP client circuit breaker integration."""
    
    def setup_method(self):
        """Set up test HTTP client."""
        # Clean up any existing circuit breakers to ensure test isolation
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
        
        self.http_client = ResilientHTTPClient(base_url="https://api.example.com")
    
    def teardown_method(self):
        """Clean up after test."""
        from app.core.circuit_breaker import circuit_registry
        circuit_registry.cleanup_all()
    
    @patch('aiohttp.ClientSession.request')
    async def test_successful_http_request(self, mock_request):
        """Test successful HTTP request through circuit breaker."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"success": True})
        mock_request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_request.return_value.__aexit__ = AsyncMock(return_value=None)
        
        result = await self.http_client.get("/test", "test_api")
        
        assert result["success"] is True
    
    @patch('aiohttp.ClientSession.request')
    async def test_http_circuit_breaker_opens(self, mock_request):
        """Test HTTP circuit breaker opens after failures."""
        mock_request.side_effect = Exception("Network error")
        
        # Configure circuit with low threshold for testing
        circuit = await self.http_client._get_circuit("test_api")
        circuit.config.failure_threshold = 2
        circuit.adaptive_failure_threshold = 2
        
        # Check initial state
        assert circuit.state.value == "closed"
        assert circuit.failure_count == 0
        
        # First failure
        with pytest.raises(Exception, match="Network error"):
            await self.http_client.get("/test", "test_api")
        
        # Check state after first failure
        assert circuit.failure_count == 1
        assert circuit.state.value == "closed"
        
        # Second failure should open circuit
        with pytest.raises(Exception, match="Network error"):
            await self.http_client.get("/test", "test_api")
        
        # Check state after second failure - circuit should be open
        assert circuit.failure_count == 2
        assert circuit.state.value == "open"
        
        # Third call should return fallback response
        result = await self.http_client.get("/test", "test_api")
        
        assert result["fallback"] is True
        assert "service_unavailable" in result["error"]
    
    async def test_http_health_check(self):
        """Test HTTP client health check."""
        with patch.object(self.http_client, '_test_connectivity') as mock_test:
            mock_test.return_value = {"status": "healthy", "response_code": 200}
            
            health = await self.http_client.health_check("test_api")
            
            assert "api_name" in health
            assert "circuit" in health
            assert "connectivity" in health


class TestCircuitBreakerMonitoring:
    """Test circuit breaker monitoring system."""
    
    def setup_method(self):
        """Set up test monitor."""
        self.monitor = CircuitBreakerMonitor()
    
    async def test_monitoring_start_stop(self):
        """Test starting and stopping monitoring."""
        # Start monitoring
        await self.monitor.start_monitoring(interval_seconds=0.1)
        assert self.monitor._monitoring_active is True
        
        # Wait a short time for monitoring loop
        await asyncio.sleep(0.2)
        
        # Stop monitoring
        await self.monitor.stop_monitoring()
        assert self.monitor._monitoring_active is False
    
    async def test_alert_handler(self):
        """Test alert handler functionality."""
        alerts_received = []
        
        async def test_handler(alert):
            alerts_received.append(alert)
        
        self.monitor.add_alert_handler(test_handler)
        
        # Simulate creating an alert
        await self.monitor._create_alert(
            circuit_name="test_circuit",
            severity=AlertSeverity.HIGH,
            message="Test alert",
            state="open",
            metrics={}
        )
        
        assert len(alerts_received) == 1
        assert alerts_received[0].circuit_name == "test_circuit"
        assert alerts_received[0].message == "Test alert"
    
    def test_health_summary(self):
        """Test health summary generation."""
        # Simulate some circuit states
        self.monitor._last_states = {
            "circuit1": "closed",
            "circuit2": "open",
            "circuit3": "half_open"
        }
        
        summary = self.monitor.get_health_summary()
        
        assert summary["total_circuits"] == 3
        assert summary["healthy_circuits"] == 1
        assert summary["degraded_circuits"] == 1
        assert summary["unhealthy_circuits"] == 1
    
    def test_recent_events(self):
        """Test recent events tracking."""
        from datetime import datetime, UTC
        
        # Add test events
        event1 = CircuitBreakerEvent(
            circuit_name="test1",
            old_state="closed",
            new_state="open",
            timestamp=datetime.now(UTC),
            failure_count=3,
            success_rate=0.5
        )
        
        self.monitor._events.append(event1)
        
        recent = self.monitor.get_recent_events(limit=10)
        assert len(recent) == 1
        assert recent[0].circuit_name == "test1"


class TestCircuitBreakerEndpoints:
    """Test circuit breaker monitoring endpoints."""
    
    async def test_dashboard_endpoint_structure(self):
        """Test dashboard endpoint returns proper structure."""
        from app.routes.circuit_breaker_health import get_circuit_breaker_dashboard
        
        with patch('app.services.circuit_breaker_monitor.circuit_monitor') as mock_monitor:
            mock_monitor.get_health_summary.return_value = {
                "total_circuits": 5,
                "healthy_circuits": 3,
                "degraded_circuits": 1,
                "unhealthy_circuits": 1
            }
            mock_monitor.get_recent_events.return_value = []
            mock_monitor.get_recent_alerts.return_value = []
            
            with patch('app.services.circuit_breaker_monitor.metrics_collector') as mock_collector:
                mock_collector.get_aggregated_metrics.return_value = {}
                
                dashboard = await get_circuit_breaker_dashboard()
                
                assert "summary" in dashboard
                assert "recent_events" in dashboard
                assert "recent_alerts" in dashboard
                assert "metrics" in dashboard
class TestCircuitBreakerPerformance:
    """Test circuit breaker performance characteristics."""
    
    async def test_high_throughput_handling(self):
        """Test circuit breaker with high throughput."""
        from app.core.circuit_breaker import CircuitBreaker, CircuitConfig
        
        config = CircuitConfig(name="performance_test")
        circuit = CircuitBreaker(config)
        
        async def fast_func(value):
            return value * 2
        
        # Create many concurrent calls
        tasks = [
            circuit.call(lambda v=i: fast_func(v))
            for i in range(100)
        ]
        
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*tasks)
        end_time = asyncio.get_event_loop().time()
        
        # Should complete reasonably quickly
        assert end_time - start_time < 1.0
        assert len(results) == 100
        assert circuit.metrics.successful_calls == 100
    
    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively."""
        from app.core.circuit_breaker import CircuitBreaker, CircuitConfig
        
        config = CircuitConfig(name="memory_test")
        circuit = CircuitBreaker(config)
        
        async def test_func():
            return "test"
        
        # Perform many operations
        for _ in range(1000):
            await circuit.call(test_func)
        
        # Check metrics are reasonable
        assert circuit.metrics.total_calls == 1000
        assert circuit.metrics.successful_calls == 1000
        
        # Check status doesn't consume excessive memory
        status = circuit.get_status()
        assert len(str(status)) < 10000  # Reasonable serialized size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])