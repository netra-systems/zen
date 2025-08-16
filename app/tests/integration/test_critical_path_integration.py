"""Test critical system paths end-to-end."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.core.agent_reliability_mixin import AgentReliabilityMixin
from app.core.fallback_coordinator import FallbackCoordinator
from app.core.json_parsing_utils import comprehensive_json_fix
from app.services.external_api_client import ResilientHTTPClient, HTTPError


class MockReliableAgent(AgentReliabilityMixin):
    """Mock agent with reliability mixin for integration testing."""
    
    def __init__(self, name: str = "MockAgent"):
        self.name = name
        super().__init__()
    
    async def mock_operation(self, should_fail: bool = False, response_data: any = None):
        """Mock operation for testing."""
        if should_fail:
            raise ValueError("Mock operation failed")
        return response_data or {"success": True, "agent": self.name}


class TestCriticalPathIntegration:
    """Test critical system paths end-to-end."""
    async def test_agent_coordination_with_external_api_call(self):
        """Test complete flow: Agent -> Coordinator -> HTTP Client -> JSON Parsing."""
        # This simulates a typical critical path where an agent makes an external API call
        # through the coordinator with full reliability protection
        mock_patches = self._setup_coordination_test_patches()
        coordinator, agent, client = self._create_coordination_test_components(mock_patches)
        critical_path_operation = self._define_critical_path_operation(coordinator, client)
        final_result = await self._execute_coordination_test(agent, critical_path_operation, mock_patches)
        self._verify_coordination_test_results(final_result, agent, mock_patches)

    def _setup_coordination_test_patches(self):
        """Setup all required patches for coordination test"""
        patches = {}
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_reliability_wrapper, \
             patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            patches.update(self._setup_reliability_mocks(mock_reliability_wrapper))
            patches.update(self._setup_coordinator_mocks(mock_health_monitor, mock_emergency_manager))
            return patches

    def _setup_reliability_mocks(self, mock_reliability_wrapper):
        """Setup agent reliability mocks"""
        mock_reliability = Mock()
        mock_reliability.execute_safely = AsyncMock()
        mock_reliability.circuit_breaker = Mock()
        mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
        mock_reliability_wrapper.return_value = mock_reliability
        return {"mock_reliability": mock_reliability}

    def _setup_coordinator_mocks(self, mock_health_monitor, mock_emergency_manager):
        """Setup coordinator health and emergency mocks"""
        mock_health_instance = Mock()
        for method in ["is_emergency_mode_active", "should_prevent_cascade", "record_success", "record_failure", "update_circuit_breaker_status", "update_system_health"]:
            setattr(mock_health_instance, method, AsyncMock(return_value=False if "active" in method or "prevent" in method else None))
        mock_health_monitor.return_value = mock_health_instance
        mock_emergency_manager.return_value = Mock()
        return {"mock_health_instance": mock_health_instance}

    def _create_coordination_test_components(self, mock_patches):
        """Create coordinator, agent, and HTTP client for testing"""
        coordinator = FallbackCoordinator()
        coordinator.health_monitor = mock_patches["mock_health_instance"]
        coordinator.emergency_manager = Mock()
        agent = MockReliableAgent("CriticalPathAgent")
        agent.reliability = mock_patches["mock_reliability"]
        return coordinator, agent, self._setup_http_client_mocks()

    def _setup_http_client_mocks(self):
        """Setup HTTP client with mocked responses"""
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            self._configure_http_mocks(mock_cb_class, mock_registry, mock_session_class)
            return ResilientHTTPClient(base_url="https://api.critical.com")

    def _configure_http_mocks(self, mock_cb_class, mock_registry, mock_session_class):
        """Configure HTTP client mocks with API response"""
        api_response = {"analysis_results": {"tool_recommendations": [{"tool": "cost_optimizer", "parameters": '{"target_reduction": 0.3, "preserve_sla": true}'}], "recommendations": '["Implement auto-scaling", "Use reserved instances"]'}, "confidence": 0.85, "execution_time": 1.2}
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = api_response
        mock_session = AsyncMock()
        mock_session.request.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session

    def _define_critical_path_operation(self, coordinator, client):
        """Define the complete critical path operation"""
        async def critical_path_operation():
            raw_result = await coordinator.execute_with_coordination("CriticalPathAgent", lambda: client.post("/optimize", "critical_api", json_data={"workload": "production", "constraints": {"budget": 10000, "sla": "99.9%"}}), "external_optimization_call")
            return comprehensive_json_fix(raw_result)
        return critical_path_operation

    async def _execute_coordination_test(self, agent, critical_path_operation, mock_patches):
        """Execute the coordination test with reliability protection"""
        async def async_execute_safely(op, name, **kwargs):
            return await op()
        mock_patches["mock_reliability"].execute_safely.side_effect = async_execute_safely
        with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, patch('app.core.fallback_coordinator.CircuitBreaker'), patch('app.core.fallback_coordinator.AgentFallbackStatus'):
            self._setup_fallback_handler(mock_handler_class)
            return await agent.execute_with_reliability(critical_path_operation, "critical_path_operation", timeout=30.0)

    def _setup_fallback_handler(self, mock_handler_class):
        """Setup fallback handler mock"""
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.side_effect = lambda operation, op_name, agent_name, fallback_type: operation()
        mock_handler_class.return_value = mock_handler

    def _verify_coordination_test_results(self, final_result, agent, mock_patches):
        """Verify all coordination test results"""
        analysis = final_result["analysis_results"]
        tool_params = analysis["tool_recommendations"][0]["parameters"]
        assert tool_params == {"target_reduction": 0.3, "preserve_sla": True}
        assert analysis["recommendations"] == ["Implement auto-scaling", "Use reserved instances"]
        assert final_result["confidence"] == 0.85 and final_result["execution_time"] == 1.2
        assert len(agent.operation_times) == 1 and len(agent.error_history) == 0
    async def test_critical_path_failure_recovery(self):
        """Test failure recovery in critical path integration."""
        # Test what happens when the external API fails but recovery strategies work
        mock_patches = self._setup_failure_recovery_test_patches()
        coordinator, agent = self._create_failure_recovery_components(mock_patches)
        self._setup_recovery_strategy(agent)
        client = self._setup_failing_http_client()
        failing_operation = self._define_failing_operation(coordinator, client)
        result = await self._execute_failure_recovery_test(agent, failing_operation, mock_patches)
        self._verify_failure_recovery_results(result, agent, mock_patches)

    def _setup_failure_recovery_test_patches(self):
        """Setup patches for failure recovery test"""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_reliability_wrapper, \
             patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability_wrapper.return_value = mock_reliability
            return self._setup_health_mocks(mock_health_monitor, mock_emergency_manager, mock_reliability)

    def _setup_health_mocks(self, mock_health_monitor, mock_emergency_manager, mock_reliability):
        """Setup health monitor and emergency manager mocks"""
        mock_health_instance = Mock()
        for method in ["is_emergency_mode_active", "should_prevent_cascade", "record_success", "record_failure", "update_circuit_breaker_status", "update_system_health"]:
            setattr(mock_health_instance, method, AsyncMock(return_value=False if "active" in method or "prevent" in method else None))
        mock_health_monitor.return_value = mock_health_instance
        mock_emergency_manager.return_value = Mock()
        return {"mock_reliability": mock_reliability, "mock_health_instance": mock_health_instance}

    def _create_failure_recovery_components(self, mock_patches):
        """Create coordinator and agent for failure recovery test"""
        coordinator = FallbackCoordinator()
        coordinator.health_monitor = mock_patches["mock_health_instance"]
        coordinator.emergency_manager = Mock()
        agent = MockReliableAgent("RecoveryAgent")
        agent.reliability = mock_patches["mock_reliability"]
        return coordinator, agent

    def _setup_recovery_strategy(self, agent):
        """Setup recovery strategy for API failures"""
        async def api_recovery_strategy(error, context):
            return {"fallback_result": True, "analysis_results": {"tool_recommendations": [{"tool": "fallback_optimizer", "parameters": {"mode": "conservative"}}], "recommendations": ["Use cached optimization", "Retry later"]}, "confidence": 0.6, "source": "fallback"}
        agent.register_recovery_strategy("critical_api_operation", api_recovery_strategy)

    def _setup_failing_http_client(self):
        """Setup HTTP client that fails with 503 error"""
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            api_error = HTTPError(503, "Service Unavailable", {"retry_after": 60})
            mock_session = AsyncMock()
            mock_session.request.side_effect = api_error
            mock_session_class.return_value = mock_session
            return ResilientHTTPClient(base_url="https://api.unreliable.com")

    def _define_failing_operation(self, coordinator, client):
        """Define operation that will fail and trigger recovery"""
        async def failing_operation():
            return await coordinator.execute_with_coordination("RecoveryAgent", lambda: client.get("/optimize", "unreliable_api"), "critical_api_operation")
        return failing_operation

    async def _execute_failure_recovery_test(self, agent, failing_operation, mock_patches):
        """Execute failure recovery test with proper mocking"""
        async def async_execute_safely_recovery(op, name, **kwargs):
            return await op()
        mock_patches["mock_reliability"].execute_safely.side_effect = async_execute_safely_recovery
        with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, patch('app.core.fallback_coordinator.CircuitBreaker'), patch('app.core.fallback_coordinator.AgentFallbackStatus'):
            mock_handler = AsyncMock()
            mock_handler.execute_with_fallback.side_effect = HTTPError(503, "Service Unavailable", {"retry_after": 60})
            mock_handler_class.return_value = mock_handler
            return await agent.execute_with_reliability(failing_operation, "critical_api_operation", timeout=10.0)

    def _verify_failure_recovery_results(self, result, agent, mock_patches):
        """Verify failure recovery worked correctly"""
        assert result["fallback_result"] is True and result["source"] == "fallback" and result["confidence"] == 0.6
        assert len(agent.error_history) == 1
        error_record = agent.error_history[0]
        assert error_record.recovery_attempted is True and error_record.recovery_successful is True
        mock_patches["mock_health_instance"].record_failure.assert_called_once()