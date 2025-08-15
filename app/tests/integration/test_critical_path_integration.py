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
    
    @pytest.mark.asyncio
    async def test_agent_coordination_with_external_api_call(self):
        """Test complete flow: Agent -> Coordinator -> HTTP Client -> JSON Parsing."""
        # This simulates a typical critical path where an agent makes an external API call
        # through the coordinator with full reliability protection
        
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_reliability_wrapper, \
             patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Setup agent reliability
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_reliability_wrapper.return_value = mock_reliability
            
            # Setup coordinator
            mock_health_instance = Mock()
            mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
            mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
            mock_health_instance.record_success = AsyncMock()
            mock_health_instance.record_failure = AsyncMock()
            mock_health_instance.update_circuit_breaker_status = AsyncMock()
            mock_health_instance.update_system_health = AsyncMock()
            
            mock_emergency_instance = Mock()
            mock_health_monitor.return_value = mock_health_instance
            mock_emergency_manager.return_value = mock_emergency_instance
            
            coordinator = FallbackCoordinator()
            coordinator.health_monitor = mock_health_instance
            coordinator.emergency_manager = mock_emergency_instance
            
            # Setup HTTP client
            with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
                 patch('app.services.external_api_client.circuit_registry') as mock_registry, \
                 patch('app.services.external_api_client.ClientSession') as mock_session_class:
                
                mock_circuit = AsyncMock()
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                
                # Mock external API response
                api_response = {
                    "analysis_results": {
                        "tool_recommendations": [
                            {
                                "tool": "cost_optimizer",
                                "parameters": '{"target_reduction": 0.3, "preserve_sla": true}'
                            }
                        ],
                        "recommendations": '["Implement auto-scaling", "Use reserved instances"]'
                    },
                    "confidence": 0.85,
                    "execution_time": 1.2
                }
                
                mock_response.status = 200
                mock_response.json.return_value = api_response
                mock_session.request.return_value.__aenter__.return_value = mock_response
                mock_circuit.call = AsyncMock(side_effect=lambda func: func())
                
                mock_cb_class.return_value = mock_circuit
                mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
                mock_session_class.return_value = mock_session
                
                # Create components
                agent = MockReliableAgent("CriticalPathAgent")
                agent.reliability = mock_reliability
                client = ResilientHTTPClient(base_url="https://api.critical.com")
                
                # Register agent with coordinator
                with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                     patch('app.core.fallback_coordinator.CircuitBreaker'), \
                     patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                    
                    # Setup coordinator handler to actually call the HTTP operation
                    mock_handler = AsyncMock()
                    mock_handler_class.return_value = mock_handler
                    
                    def execute_with_fallback(operation, op_name, agent_name, fallback_type):
                        return operation()
                    
                    mock_handler.execute_with_fallback.side_effect = execute_with_fallback
                    
                    coordinator.register_agent("CriticalPathAgent")
                    
                    # Define the complete critical path operation
                    async def critical_path_operation():
                        # Step 1: Coordinator manages the operation
                        raw_result = await coordinator.execute_with_coordination(
                            "CriticalPathAgent",
                            # Step 2: HTTP client makes external API call
                            lambda: client.post("/optimize", "critical_api", json_data={
                                "workload": "production",
                                "constraints": {"budget": 10000, "sla": "99.9%"}
                            }),
                            "external_optimization_call"
                        )
                        
                        # Step 3: Parse and fix JSON response
                        return comprehensive_json_fix(raw_result)
                    
                    # Step 4: Execute with full reliability protection
                    async def async_execute_safely(op, name, **kwargs):
                        return await op()
                    mock_reliability.execute_safely.side_effect = async_execute_safely
                    
                    final_result = await agent.execute_with_reliability(
                        critical_path_operation,
                        "critical_path_operation",
                        timeout=30.0
                    )
                    
                    # Verify the complete integration
                    analysis = final_result["analysis_results"]
                    
                    # Verify JSON parsing worked
                    tool_params = analysis["tool_recommendations"][0]["parameters"]
                    assert tool_params == {"target_reduction": 0.3, "preserve_sla": True}
                    assert analysis["recommendations"] == ["Implement auto-scaling", "Use reserved instances"]
                    
                    # Verify confidence and timing are preserved
                    assert final_result["confidence"] == 0.85
                    assert final_result["execution_time"] == 1.2
                    
                    # Verify all components recorded success
                    assert len(agent.operation_times) == 1
                    assert len(agent.error_history) == 0
                    mock_health_instance.record_success.assert_called_once_with("CriticalPathAgent")
    
    @pytest.mark.asyncio
    async def test_critical_path_failure_recovery(self):
        """Test failure recovery in critical path integration."""
        # Test what happens when the external API fails but recovery strategies work
        
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_reliability_wrapper, \
             patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Setup components
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability_wrapper.return_value = mock_reliability
            
            mock_health_instance = Mock()
            mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
            mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
            mock_health_instance.record_success = AsyncMock()
            mock_health_instance.record_failure = AsyncMock()
            mock_health_instance.update_circuit_breaker_status = AsyncMock()
            mock_health_instance.update_system_health = AsyncMock()
            
            mock_emergency_instance = Mock()
            mock_health_monitor.return_value = mock_health_instance
            mock_emergency_manager.return_value = mock_emergency_instance
            
            coordinator = FallbackCoordinator()
            coordinator.health_monitor = mock_health_instance
            coordinator.emergency_manager = mock_emergency_instance
            
            agent = MockReliableAgent("RecoveryAgent")
            agent.reliability = mock_reliability
            
            # Setup a recovery strategy for API failures
            async def api_recovery_strategy(error, context):
                return {
                    "fallback_result": True,
                    "analysis_results": {
                        "tool_recommendations": [
                            {
                                "tool": "fallback_optimizer",
                                "parameters": {"mode": "conservative"}
                            }
                        ],
                        "recommendations": ["Use cached optimization", "Retry later"]
                    },
                    "confidence": 0.6,
                    "source": "fallback"
                }
            
            agent.register_recovery_strategy("critical_api_operation", api_recovery_strategy)
            
            # Setup HTTP client to fail
            with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
                 patch('app.services.external_api_client.circuit_registry') as mock_registry, \
                 patch('app.services.external_api_client.ClientSession') as mock_session_class:
                
                mock_circuit = AsyncMock()
                mock_session = AsyncMock()
                
                # Mock HTTP failure
                api_error = HTTPError(503, "Service Unavailable", {"retry_after": 60})
                mock_session.request.side_effect = api_error
                mock_circuit.call = AsyncMock(side_effect=lambda func: func())
                
                mock_cb_class.return_value = mock_circuit
                mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
                mock_session_class.return_value = mock_session
                
                client = ResilientHTTPClient(base_url="https://api.unreliable.com")
                
                # Register agent with coordinator
                with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                     patch('app.core.fallback_coordinator.CircuitBreaker'), \
                     patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                    
                    mock_handler = AsyncMock()
                    mock_handler_class.return_value = mock_handler
                    
                    # Coordinator will also fail, triggering agent recovery
                    mock_handler.execute_with_fallback.side_effect = api_error
                    
                    coordinator.register_agent("RecoveryAgent")
                    
                    # Setup agent to handle the failure and trigger recovery
                    async def failing_operation():
                        return await coordinator.execute_with_coordination(
                            "RecoveryAgent",
                            lambda: client.get("/optimize", "unreliable_api"),
                            "critical_api_operation"
                        )
                    
                    # Mock reliability to actually execute and handle the error
                    async def async_execute_safely_recovery(op, name, **kwargs):
                        return await op()
                    mock_reliability.execute_safely.side_effect = async_execute_safely_recovery
                    
                    # Execute - should recover despite failures
                    result = await agent.execute_with_reliability(
                        failing_operation,
                        "critical_api_operation",
                        timeout=10.0
                    )
                    
                    # Verify recovery worked
                    assert result["fallback_result"] is True
                    assert result["source"] == "fallback"
                    assert result["confidence"] == 0.6
                    
                    # Verify error was recorded but recovery succeeded
                    assert len(agent.error_history) == 1
                    error_record = agent.error_history[0]
                    assert error_record.recovery_attempted is True
                    assert error_record.recovery_successful is True
                    
                    # Verify coordinator recorded the failure
                    mock_health_instance.record_failure.assert_called_once()