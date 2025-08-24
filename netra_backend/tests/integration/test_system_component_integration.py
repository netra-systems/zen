"""Test integration between different system components."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin
from netra_backend.app.core.json_parsing_utils import comprehensive_json_fix
from netra_backend.app.services.external_api_client import ResilientHTTPClient

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
        # Mock: Generic component isolation for controlled unit testing
        mock_reliability = Mock()
        # Mock: Generic component isolation for controlled unit testing
        mock_reliability.execute_safely = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        mock_reliability.circuit_breaker = Mock()
        # Mock: Component isolation for controlled unit testing
        mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
        mock_wrapper.return_value = mock_reliability
        
        agent = MockReliableAgent("JSONAgent")
        agent.reliability = mock_reliability
        mock_reliability.execute_safely.return_value = malformed_response
        return agent
    @pytest.mark.asyncio
    async def test_http_client_with_json_parsing_integration(self):
        """Test HTTP client integration with JSON parsing."""
        # Mock: Component isolation for testing without external dependencies
        with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
             patch('app.services.external_api_client.circuit_registry') as mock_registry, \
             patch('app.services.external_api_client.ClientSession') as mock_session_class:
            
            # Setup mocks
            # Mock: Generic component isolation for controlled unit testing
            mock_circuit = AsyncMock()
            # Mock: Database session isolation for transaction testing without real database dependency
            mock_session = AsyncMock()
            # Mock: Generic component isolation for controlled unit testing
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
            # Mock: Async component isolation for testing without real async operations
            mock_circuit.call = AsyncMock(side_effect=lambda func: func())
            
            mock_cb_class.return_value = mock_circuit
            # Mock: Async component isolation for testing without real async operations
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
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            # Setup reliability wrapper
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability = Mock()
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability.execute_safely = AsyncMock()
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability.circuit_breaker = Mock()
            # Mock: Component isolation for controlled unit testing
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            # Create agent with reliability
            agent = MockReliableAgent("APIAgent")
            agent.reliability = mock_reliability
            
            # Mock HTTP client operations
            # Mock: Component isolation for testing without external dependencies
            with patch('app.services.external_api_client.CircuitBreaker') as mock_cb_class, \
                 patch('app.services.external_api_client.circuit_registry') as mock_registry, \
                 patch('app.services.external_api_client.ClientSession') as mock_session_class:
                
                # Mock: Generic component isolation for controlled unit testing
                mock_circuit = AsyncMock()
                # Mock: Database session isolation for transaction testing without real database dependency
                mock_session = AsyncMock()
                # Mock: Generic component isolation for controlled unit testing
                mock_response = AsyncMock()
                
                mock_response.status = 200
                mock_response.json.return_value = {"api_result": "success", "data": [1, 2, 3]}
                mock_session.request.return_value.__aenter__.return_value = mock_response
                # Mock: Async component isolation for testing without real async operations
                mock_circuit.call = AsyncMock(side_effect=lambda func: func())
                
                mock_cb_class.return_value = mock_circuit
                # Mock: Async component isolation for testing without real async operations
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
        # Mock: Component isolation for testing without external dependencies
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability = Mock()
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability.execute_safely = AsyncMock()
            # Mock: Generic component isolation for controlled unit testing
            mock_reliability.circuit_breaker = Mock()
            # Mock: Component isolation for controlled unit testing
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