"""Integration tests for critical system paths and component interactions."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime

# Import components for integration testing
from app.core.agent_reliability_mixin import AgentReliabilityMixin, AgentError, AgentHealthStatus
from app.core.fallback_coordinator import FallbackCoordinator
from app.core.json_parsing_utils import comprehensive_json_fix, safe_json_parse
from app.services.external_api_client import ResilientHTTPClient, HTTPError


class MockReliableAgent(AgentReliabilityMixin):
    """Mock agent with reliability mixin for integration testing."""
    
    def __init__(self, name: str = "MockAgent"):
        self.name = name
        super().__init__()
    
    async def mock_operation(self, should_fail: bool = False, response_data: Any = None):
        """Mock operation for testing."""
        if should_fail:
            raise ValueError("Mock operation failed")
        return response_data or {"success": True, "agent": self.name}


class TestAgentReliabilityIntegration:
    """Integration tests for agent reliability across system components."""
    
    @pytest.fixture
    def reliable_agent(self):
        """Create mock reliable agent."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            agent = MockReliableAgent("TestAgent")
            agent.reliability = mock_reliability
            return agent
    
    def _create_complex_json_test_data(self):
        """Create complex JSON response for testing."""
        return {
            "tool_recommendations": [
                {
                    "tool": "data_analyzer",
                    "parameters": '{"query": "SELECT * FROM metrics", "format": "json"}'
                }
            ],
            "recommendations": '["Optimize query performance", "Add caching layer"]',
            "nested_data": {
                "analysis": '{"findings": ["bottleneck1", "bottleneck2"]}'
            }
        }
    
    def _verify_json_parsing_integration(self, fixed_result):
        """Verify JSON parsing integration results."""
        assert fixed_result["tool_recommendations"][0]["parameters"] == {
            "query": "SELECT * FROM metrics", 
            "format": "json"
        }
        assert fixed_result["recommendations"] == ["Optimize query performance", "Add caching layer"]
    
    def _verify_reliability_tracking(self, reliable_agent):
        """Verify reliability metrics were updated correctly."""
        assert len(reliable_agent.operation_times) == 1
        assert len(reliable_agent.error_history) == 0
    
    @pytest.mark.asyncio
    async def test_agent_reliability_with_json_parsing(self, reliable_agent):
        """Test agent reliability with JSON parsing integration."""
        complex_response = self._create_complex_json_test_data()
        reliable_agent.reliability.execute_safely.return_value = complex_response
        
        result = await reliable_agent.execute_with_reliability(
            lambda: reliable_agent.mock_operation(response_data=complex_response),
            "json_processing_operation",
            timeout=10.0
        )
        
        fixed_result = comprehensive_json_fix(result)
        self._verify_json_parsing_integration(fixed_result)
        self._verify_reliability_tracking(reliable_agent)
    
    def _create_mock_health_instance(self):
        """Create mock health monitor instance."""
        mock_health_instance = Mock()
        mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
        mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
        mock_health_instance.record_success = AsyncMock()
        mock_health_instance.record_failure = AsyncMock()
        mock_health_instance.update_circuit_breaker_status = AsyncMock()
        mock_health_instance.update_system_health = AsyncMock()
        return mock_health_instance
    
    def _setup_fallback_coordinator_mocks(self, mock_health_monitor, mock_emergency_manager):
        """Setup fallback coordinator with mocks."""
        mock_health_instance = self._create_mock_health_instance()
        mock_emergency_instance = Mock()
        mock_health_monitor.return_value = mock_health_instance
        mock_emergency_manager.return_value = mock_emergency_instance
        
        coordinator = FallbackCoordinator()
        coordinator.health_monitor = mock_health_instance
        coordinator.emergency_manager = mock_emergency_instance
        return coordinator, mock_health_instance
    
    def _setup_coordination_handler_mocks(self, mock_handler_class):
        """Setup coordination handler mocks."""
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"coordinated": True, "agent": "TestAgent"}
        mock_handler_class.return_value = mock_handler
        return mock_handler
    
    def _verify_coordination_integration(self, result, mock_handler, mock_health_instance, reliable_agent):
        """Verify coordination integration results."""
        assert result == {"coordinated": True, "agent": "TestAgent"}
        mock_handler.execute_with_fallback.assert_called_once()
        mock_health_instance.record_success.assert_called_once_with("TestAgent")
        assert len(reliable_agent.operation_times) == 1
    
    async def _execute_coordinated_operation(self, coordinator, reliable_agent):
        """Execute coordinated operation through reliability and coordination."""
        async def coordinated_operation():
            return await coordinator.execute_with_coordination(
                "TestAgent",
                lambda: reliable_agent.mock_operation(response_data={"agent_result": "success"}),
                "integrated_operation"
            )
        
        return await reliable_agent.execute_with_reliability(
            coordinated_operation,
            "coordination_operation",
            timeout=15.0
        )
    
    @pytest.mark.asyncio
    async def test_agent_reliability_with_fallback_coordinator(self, reliable_agent):
        """Test agent reliability integration with fallback coordinator."""
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            coordinator, mock_health_instance = self._setup_fallback_coordinator_mocks(mock_health_monitor, mock_emergency_manager)
            
            with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                 patch('app.core.fallback_coordinator.CircuitBreaker'), \
                 patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                
                mock_handler = self._setup_coordination_handler_mocks(mock_handler_class)
                coordinator.register_agent("TestAgent")
                
                result = await self._execute_coordinated_operation(coordinator, reliable_agent)
                self._verify_coordination_integration(result, mock_handler, mock_health_instance, reliable_agent)
    
    @pytest.mark.asyncio
    async def test_agent_failure_propagation_through_system(self, reliable_agent):
        """Test how agent failures propagate through the integrated system."""
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Setup mocks for emergency scenario
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
            
            # Setup failure scenario
            test_error = RuntimeError("Critical system failure")
            
            with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
                 patch('app.core.fallback_coordinator.CircuitBreaker'), \
                 patch('app.core.fallback_coordinator.AgentFallbackStatus'):
                
                mock_handler = AsyncMock()
                mock_handler.execute_with_fallback.side_effect = test_error
                mock_handler_class.return_value = mock_handler
                
                coordinator.register_agent("TestAgent")
                
                # Setup agent to fail
                reliable_agent.reliability.execute_safely.side_effect = test_error
                
                # Execute operation and expect failure propagation
                with pytest.raises(RuntimeError, match="Critical system failure"):
                    await reliable_agent.execute_with_reliability(
                        lambda: coordinator.execute_with_coordination(
                            "TestAgent",
                            lambda: reliable_agent.mock_operation(should_fail=True),
                            "failing_operation"
                        ),
                        "coordinated_failure",
                        timeout=5.0
                    )
                
                # Verify failure was recorded in both systems
                assert len(reliable_agent.error_history) == 1
                error_record = reliable_agent.error_history[0]
                assert error_record.error_type == "RuntimeError"
                assert error_record.message == "Critical system failure"
                
                # Verify coordinator recorded the failure
                mock_health_instance.record_failure.assert_called_once_with("TestAgent", test_error)


class TestSystemComponentIntegration:
    """Test integration between different system components."""
    
    def _create_malformed_json_response(self):
        """Create malformed JSON response for error handling test."""
        return {
            "tool_recommendations": [
                {
                    "tool": "parser",
                    "parameters": '{"invalid": json malformed}'  # Invalid JSON
                }
            ],
            "recommendations": '["invalid json array"'  # Invalid JSON
        }
    
    def _setup_json_error_agent(self, mock_wrapper, malformed_response):
        """Setup agent for JSON error handling test."""
        mock_reliability = Mock()
        mock_reliability.execute_safely = AsyncMock()
        mock_reliability.circuit_breaker = Mock()
        mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
        mock_wrapper.return_value = mock_reliability
        
        agent = MockReliableAgent("JSONAgent")
        agent.reliability = mock_reliability
        mock_reliability.execute_safely.return_value = malformed_response
        return agent
    
    @pytest.mark.asyncio
    async def test_http_client_with_json_parsing_integration(self):
        """Test HTTP client integration with JSON parsing."""
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            # Setup mocks
            mock_circuit = AsyncMock()
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            
            # Mock response with complex JSON that needs parsing
            complex_api_response = {
                "tool_recommendations": [
                    {
                        "tool": "api_optimizer",
                        "parameters": '{"cache_ttl": 3600, "retry_attempts": 3}'
                    }
                ],
                "recommendations": '["Use connection pooling", "Implement circuit breakers"]',
                "metadata": {
                    "response_time": 150,
                    "cached": False
                }
            }
            
            mock_response.status = 200
            mock_response.json.return_value = complex_api_response
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_circuit.call = AsyncMock(side_effect=lambda func: func())
            
            mock_cb_class.return_value = mock_circuit
            mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
            mock_session_class.return_value = mock_session
            
            # Create HTTP client
            client = ResilientHTTPClient(base_url="https://api.external.com")
            
            # Make request
            raw_response = await client.get("/analyze", "external_api")
            
            # Parse and fix JSON response
            parsed_response = comprehensive_json_fix(raw_response)
            
            # Verify integration
            assert parsed_response["tool_recommendations"][0]["parameters"] == {
                "cache_ttl": 3600, 
                "retry_attempts": 3
            }
            assert parsed_response["recommendations"] == [
                "Use connection pooling", 
                "Implement circuit breakers"
            ]
            assert parsed_response["metadata"]["response_time"] == 150
    
    @pytest.mark.asyncio
    async def test_http_client_with_reliability_integration(self):
        """Test HTTP client integration with reliability components."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            # Setup reliability wrapper
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            # Create agent with reliability
            agent = MockReliableAgent("APIAgent")
            agent.reliability = mock_reliability
            
            # Mock HTTP client operations
            with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
                 patch('app.services.external_api_client.circuit_registry') as mock_registry, \
                 patch('app.services.external_api_client.ClientSession') as mock_session_class:
                
                mock_circuit = AsyncMock()
                mock_session = AsyncMock()
                mock_response = AsyncMock()
                
                mock_response.status = 200
                mock_response.json.return_value = {"api_result": "success", "data": [1, 2, 3]}
                mock_session.request.return_value.__aenter__.return_value = mock_response
                mock_circuit.call = AsyncMock(side_effect=lambda func: func())
                
                mock_cb_class.return_value = mock_circuit
                mock_registry.get_circuit = AsyncMock(return_value=mock_circuit)
                mock_session_class.return_value = mock_session
                
                client = ResilientHTTPClient(base_url="https://api.reliable.com")
                
                # Execute HTTP operation with reliability protection
                async def api_operation():
                    return await client.post("/process", "reliable_api", json_data={"input": "test"})
                
                # Mock the reliability execute_safely to actually call the operation
                async def async_execute_safely_api(op, name, **kwargs):
                    return await op()
                mock_reliability.execute_safely.side_effect = async_execute_safely_api
                
                result = await agent.execute_with_reliability(
                    api_operation,
                    "api_call_operation",
                    timeout=10.0
                )
                
                # Verify integration
                assert result == {"api_result": "success", "data": [1, 2, 3]}
                assert len(agent.operation_times) == 1
                assert len(agent.error_history) == 0
    
    @pytest.mark.asyncio
    async def test_json_parsing_error_handling_integration(self):
        """Test JSON parsing error handling integration with reliability."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_wrapper.return_value = mock_reliability
            
            agent = MockReliableAgent("JSONAgent")
            agent.reliability = mock_reliability
            
            # Simulate operation that returns malformed JSON
            malformed_response = {
                "tool_recommendations": [
                    {
                        "tool": "parser",
                        "parameters": '{"invalid": json malformed}'  # Invalid JSON
                    }
                ],
                "recommendations": '["invalid json array"'  # Invalid JSON
            }
            
            mock_reliability.execute_safely.return_value = malformed_response
            
            # Execute operation
            result = await agent.execute_with_reliability(
                lambda: agent.mock_operation(response_data=malformed_response),
                "json_parsing_operation"
            )
            
            # Apply JSON fixes (should handle errors gracefully)
            fixed_result = comprehensive_json_fix(result)
            
            # Verify error handling - malformed JSON should fall back to defaults
            assert fixed_result["tool_recommendations"][0]["parameters"] == {}  # Fallback to empty dict
            assert fixed_result["recommendations"] == ['["invalid json array"']  # Fallback to original string
            
            # Verify operation was still considered successful
            assert len(agent.operation_times) == 1
            assert len(agent.error_history) == 0


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


class TestSystemResilience:
    """Test system resilience under various failure conditions."""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_prevention(self):
        """Test system behavior under cascading failure conditions."""
        # Simulate scenario where multiple components are failing simultaneously
        
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Setup emergency scenario
            mock_health_instance = Mock()
            mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=True)  # Emergency mode!
            mock_health_instance.should_prevent_cascade = AsyncMock(return_value=True)   # Prevent cascade!
            mock_health_instance.record_success = AsyncMock()
            mock_health_instance.record_failure = AsyncMock()
            mock_health_instance.update_circuit_breaker_status = AsyncMock()
            mock_health_instance.update_system_health = AsyncMock()
            
            mock_emergency_instance = Mock()
            mock_emergency_instance.execute_emergency_fallback = AsyncMock(return_value={
                "emergency_response": True,
                "message": "System in emergency mode - using minimal functionality",
                "capabilities": ["basic_health_check", "status_report"]
            })
            
            mock_health_monitor.return_value = mock_health_instance
            mock_emergency_manager.return_value = mock_emergency_instance
            
            coordinator = FallbackCoordinator()
            coordinator.health_monitor = mock_health_instance
            coordinator.emergency_manager = mock_emergency_instance
            
            # Try to execute operation during emergency
            result = await coordinator.execute_with_coordination(
                "FailingAgent",
                lambda: {"normal": "operation"},
                "test_operation"
            )
            
            # Verify emergency protocols activated
            assert result["emergency_response"] is True
            assert "emergency mode" in result["message"]
            mock_emergency_instance.execute_emergency_fallback.assert_called_once_with(
                "FailingAgent", "test_operation", "general"
            )
    
    @pytest.mark.asyncio
    async def test_concurrent_component_failures(self):
        """Test system behavior when multiple components fail concurrently."""
        # Simulate multiple agents failing at the same time
        
        agents = []
        for i in range(3):
            with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
                mock_reliability = Mock()
                mock_reliability.execute_safely = AsyncMock()
                mock_reliability.circuit_breaker = Mock()
                mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "open"})  # All circuits open
                mock_reliability.circuit_breaker.reset = Mock()
                mock_wrapper.return_value = mock_reliability
                
                agent = MockReliableAgent(f"Agent{i}")
                agent.reliability = mock_reliability
                agents.append(agent)
        
        # Setup concurrent failures
        failure_error = RuntimeError("Concurrent system failure")
        for agent in agents:
            agent.reliability.execute_safely.side_effect = failure_error
        
        # Execute concurrent operations
        async def failing_operation(agent_name):
            agent = next(a for a in agents if a.name == agent_name)
            return await agent.execute_with_reliability(
                lambda: agent.mock_operation(should_fail=True),
                "concurrent_operation"
            )
        
        # All should fail
        tasks = [failing_operation(f"Agent{i}") for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all failed appropriately
        for result in results:
            assert isinstance(result, RuntimeError)
            assert str(result) == "Concurrent system failure"
        
        # Verify all agents recorded failures
        for agent in agents:
            assert len(agent.error_history) == 1
            assert agent.error_history[0].error_type == "RuntimeError"