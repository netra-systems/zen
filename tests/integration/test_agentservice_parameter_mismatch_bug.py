"""
Test to reproduce the AgentService parameter mismatch bug.

This test reproduces the exact error seen in production logs:
"AgentService.get_agent_status() got an unexpected keyword argument 'agent_id'"
"""

import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent


class TestAgentServiceParameterMismatch:
    """Test class to reproduce and verify the AgentService parameter mismatch bug."""

    @pytest.fixture
    def mock_supervisor(self):
        """Create a mock supervisor for testing."""
        supervisor = Mock(spec=SupervisorAgent)
        supervisor.run = AsyncMock(return_value="test response")
        supervisor.registry = Mock()
        return supervisor

    @pytest.fixture
    def agent_service(self, mock_supervisor):
        """Create AgentService instance for testing."""
        return AgentService(supervisor=mock_supervisor)

    @pytest.mark.asyncio
    async def test_get_agent_status_with_agent_id_parameter_fails(self, agent_service):
        """
        Test that reproduces the exact error from production logs.
        
        The route tries to call get_agent_status(agent_id="some-id", user_id="user")
        but the method only accepts get_agent_status(user_id="user").
        """
        
        # This should reproduce the exact TypeError from production
        with pytest.raises(TypeError, match="unexpected keyword argument 'agent_id'"):
            await agent_service.get_agent_status(
                agent_id="test-agent-123",
                user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_stop_agent_with_agent_id_parameter_fails(self, agent_service):
        """
        Test that reproduces the stop_agent parameter mismatch error.
        
        The route tries to call stop_agent(agent_id="id", reason="reason", user_id="user")
        but the method only accepts stop_agent(user_id="user").
        """
        
        # This should reproduce the exact TypeError from production
        with pytest.raises(TypeError, match="unexpected keyword argument 'agent_id'"):
            await agent_service.stop_agent(
                agent_id="test-agent-123",
                reason="test stop",
                user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_start_agent_with_agent_id_parameter_fails(self, agent_service):
        """
        Test that reproduces the start_agent parameter mismatch error.
        
        The route tries to call start_agent with agent_id, agent_type, message, etc.
        but the method expects start_agent(request_model, run_id, stream_updates).
        """
        
        # This should reproduce the exact TypeError from production  
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            await agent_service.start_agent(
                agent_id="test-agent-123",
                agent_type="triage",
                message="test message",
                context={},
                user_id="test-user"
            )

    @pytest.mark.asyncio
    async def test_correct_get_agent_status_works(self, agent_service):
        """Test that the correct method signature works properly."""
        
        # This should work without errors
        result = await agent_service.get_agent_status(user_id="test-user")
        
        # Verify it returns the expected structure
        assert isinstance(result, dict)
        assert "user_id" in result
        assert result["user_id"] == "test-user"
        assert "status" in result

    @pytest.mark.asyncio
    async def test_correct_stop_agent_works(self, agent_service):
        """Test that the correct method signature works properly."""
        
        # This should work without errors
        result = await agent_service.stop_agent(user_id="test-user")
        
        # Verify it returns boolean
        assert isinstance(result, bool)

    def test_missing_methods_that_routes_expect(self, agent_service):
        """Test that routes expect methods that don't exist in AgentService."""
        
        # These methods are called by routes but don't exist
        assert not hasattr(agent_service, "cancel_agent")
        assert not hasattr(agent_service, "stream_agent_execution")

    @pytest.mark.asyncio
    async def test_route_parameter_pattern_simulation(self, agent_service):
        """
        Simulate how the route handlers currently call AgentService methods.
        
        This test documents the exact calling pattern that causes the errors.
        """
        
        # Simulate the route's calling pattern - this should fail
        route_calls = [
            # From get_agent_status route (line 540-543)
            {
                "method": "get_agent_status",
                "params": {
                    "agent_id": "test-agent-123",
                    "user_id": "test-user"
                }
            },
            # From stop_agent route (line 412-416) 
            {
                "method": "stop_agent",
                "params": {
                    "agent_id": "test-agent-123", 
                    "reason": "test reason",
                    "user_id": "test-user"
                }
            },
            # From start_agent route (line 356-362)
            {
                "method": "start_agent",
                "params": {
                    "agent_id": "test-agent-123",
                    "agent_type": "triage",
                    "message": "test message",
                    "context": {},
                    "user_id": "test-user"
                }
            }
        ]
        
        # Each of these calls should fail with TypeError
        for call in route_calls:
            method_name = call["method"]
            params = call["params"]
            
            method = getattr(agent_service, method_name)
            
            with pytest.raises(TypeError, match="unexpected keyword argument"):
                if method_name in ["get_agent_status", "stop_agent"]:
                    await method(**params)
                else:
                    await method(**params)

    def test_interface_vs_implementation_mismatch(self):
        """
        Test documents the mismatch between service interface and route expectations.
        
        This test serves as documentation for the architectural mismatch.
        """
        
        # Interface expectations (from service_interfaces.py)
        interface_signatures = {
            "start_agent": ["request_model", "run_id", "stream_updates"],
            "stop_agent": ["user_id"], 
            "get_agent_status": ["user_id"]
        }
        
        # Route expectations (from agents_execute.py)
        route_expectations = {
            "start_agent": ["agent_id", "agent_type", "message", "context", "user_id"],
            "stop_agent": ["agent_id", "reason", "user_id"],
            "get_agent_status": ["agent_id", "user_id"]
        }
        
        # Document the mismatches
        mismatches = {}
        for method in interface_signatures:
            interface_params = set(interface_signatures[method])
            route_params = set(route_expectations[method])
            
            missing_in_interface = route_params - interface_params
            extra_in_interface = interface_params - route_params
            
            if missing_in_interface or extra_in_interface:
                mismatches[method] = {
                    "missing_in_interface": list(missing_in_interface),
                    "extra_in_interface": list(extra_in_interface)
                }
        
        # All methods have mismatches - this is the core of the bug
        assert len(mismatches) == 3
        assert "agent_id" in mismatches["get_agent_status"]["missing_in_interface"]
        assert "agent_id" in mismatches["stop_agent"]["missing_in_interface"]  
        assert "agent_id" in mismatches["start_agent"]["missing_in_interface"]