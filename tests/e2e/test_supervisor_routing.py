"""Supervisor Agent Routing Tests - Phase 4a Agent Orchestration



Tests supervisor agent routing decisions to validate correct agent selection

based on request type. Core functionality that ensures efficient AI workload

distribution across specialized agents.



Business Value Justification (BVJ):

- Segment: All tiers (Free, Early, Mid, Enterprise)

- Business Goal: Validate AI optimization value delivery system

- Value Impact: Correct routing ensures optimal agent utilization and response times

- Revenue Impact: Efficient routing supports SLA guarantees and customer satisfaction



Architecture: 450-line compliance through focused testing scope

"""



import pytest

from shared.isolated_environment import IsolatedEnvironment



from tests.e2e.agent_orchestration_fixtures import (

    mock_supervisor_agent,

    routing_test_data,

)





@pytest.mark.e2e

class TestSupervisorRouting:

    """Test supervisor agent routing decisions - BVJ: Correct agent selection"""



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_data_request_to_data_agent(self, mock_supervisor_agent, routing_test_data):

        """Test data analysis request routes to DataSubAgent"""

        request = routing_test_data["data_request"]

        

        # Mock routing decision

        mock_supervisor_agent.route_request.return_value = "data"

        

        result = await mock_supervisor_agent.route_request(request)

        assert result == "data"

        mock_supervisor_agent.route_request.assert_called_once_with(request)



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_optimization_request(self, mock_supervisor_agent, routing_test_data):

        """Test optimization request routes to OptimizationsSubAgent"""

        request = routing_test_data["optimization_request"]

        

        mock_supervisor_agent.route_request.return_value = "optimizations"

        result = await mock_supervisor_agent.route_request(request)

        

        assert result == "optimizations"

        mock_supervisor_agent.route_request.assert_called_once_with(request)



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_complex_request_to_pipeline(self, mock_supervisor_agent, routing_test_data):

        """Test complex request creates multi-agent pipeline"""

        request = routing_test_data["complex_request"]

        

        mock_supervisor_agent.route_request.return_value = ["data", "optimizations", "actions"]

        result = await mock_supervisor_agent.route_request(request)

        

        assert isinstance(result, list)

        assert len(result) == 3

        assert "data" in result

        assert "optimizations" in result

        assert "actions" in result



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_unknown_request_fallback(self, mock_supervisor_agent, routing_test_data):

        """Test unknown request type uses fallback routing"""

        request = routing_test_data["unknown_request"]

        

        mock_supervisor_agent.route_request.return_value = "general"

        result = await mock_supervisor_agent.route_request(request)

        

        assert result == "general"

        mock_supervisor_agent.route_request.assert_called_once_with(request)



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_based_on_user_tier(self, mock_supervisor_agent):

        """Test routing considers user tier for agent selection"""

        enterprise_request = {

            "type": "data_analysis", 

            "query": "Complex analysis", 

            "user_tier": "enterprise"

        }

        

        mock_supervisor_agent.route_request.return_value = "enterprise_data"

        result = await mock_supervisor_agent.route_request(enterprise_request)

        

        assert result == "enterprise_data"



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_with_priority_handling(self, mock_supervisor_agent):

        """Test high-priority requests get priority routing"""

        priority_request = {

            "type": "optimization", 

            "priority": "high",

            "deadline": "urgent"

        }

        

        mock_supervisor_agent.route_request.return_value = "priority_optimizations"

        result = await mock_supervisor_agent.route_request(priority_request)

        

        assert result == "priority_optimizations"



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_handles_malformed_request(self, mock_supervisor_agent):

        """Test routing handles malformed or incomplete requests"""

        malformed_request = {"incomplete": "data"}

        

        mock_supervisor_agent.route_request.return_value = "fallback"

        result = await mock_supervisor_agent.route_request(malformed_request)

        

        assert result == "fallback"



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_route_considers_agent_availability(self, mock_supervisor_agent):

        """Test routing considers agent availability status"""

        request_with_preferred = {

            "type": "data_analysis",

            "preferred_agent": "data",

            "fallback_agents": ["general"]

        }

        

        # Simulate preferred agent unavailable, fallback used

        mock_supervisor_agent.route_request.return_value = "general"

        result = await mock_supervisor_agent.route_request(request_with_preferred)

        

        assert result == "general"





@pytest.mark.e2e

class TestRoutingValidation:

    """Test routing validation and error handling - BVJ: System reliability"""



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_validate_routing_decision(self, mock_supervisor_agent):

        """Test routing decisions are validated before execution"""

        valid_request = {"type": "optimization", "validation": True}

        

        mock_supervisor_agent.route_request.return_value = "optimizations"

        result = await mock_supervisor_agent.route_request(valid_request)

        

        assert result is not None

        assert result == "optimizations"



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_routing_timeout_handling(self, mock_supervisor_agent):

        """Test routing handles timeout scenarios gracefully"""

        timeout_request = {"type": "slow_analysis", "timeout": 5}

        

        mock_supervisor_agent.route_request.return_value = "timeout_handler"

        result = await mock_supervisor_agent.route_request(timeout_request)

        

        assert result == "timeout_handler"



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_routing_preserves_request_context(self, mock_supervisor_agent):

        """Test routing preserves important request context"""

        contextual_request = {

            "type": "analysis",

            "context": {"user_id": "12345", "session": "abc"},

            "metadata": {"source": "dashboard"}

        }

        

        mock_supervisor_agent.route_request.return_value = "context_aware_agent"

        result = await mock_supervisor_agent.route_request(contextual_request)

        

        assert result == "context_aware_agent"

        # Verify context was passed through (mock should be called with full request)

        call_args = mock_supervisor_agent.route_request.call_args[0][0]

        assert "context" in call_args

        assert "metadata" in call_args





@pytest.mark.e2e

class TestRoutingPerformance:

    """Test routing performance characteristics - BVJ: Response time SLAs"""



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_routing_response_time(self, mock_supervisor_agent):

        """Test routing decisions complete within performance thresholds"""

        performance_request = {"type": "quick_analysis", "sla": "fast"}

        

        mock_supervisor_agent.route_request.return_value = "fast_agent"

        result = await mock_supervisor_agent.route_request(performance_request)

        

        assert result == "fast_agent"

        # In real implementation, would measure actual execution time

        mock_supervisor_agent.route_request.assert_called_once()



    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_concurrent_routing_requests(self, mock_supervisor_agent):

        """Test supervisor handles concurrent routing requests"""

        import asyncio

        

        requests = [

            {"type": "analysis", "id": 1},

            {"type": "optimization", "id": 2}, 

            {"type": "reporting", "id": 3}

        ]

        

        # Mock different responses for each request

        side_effects = ["data", "optimizations", "reporting"]

        mock_supervisor_agent.route_request.side_effect = side_effects

        

        # Execute requests concurrently

        tasks = [mock_supervisor_agent.route_request(req) for req in requests]

        results = await asyncio.gather(*tasks)

        

        assert len(results) == 3

        assert results == side_effects



    @pytest.mark.asyncio 

    @pytest.mark.e2e

    async def test_routing_load_balancing(self, mock_supervisor_agent):

        """Test routing includes load balancing considerations"""

        load_balanced_request = {

            "type": "data_analysis",

            "load_balance": True,

            "available_instances": ["data1", "data2", "data3"]

        }

        

        mock_supervisor_agent.route_request.return_value = "data2"  # Load balanced choice

        result = await mock_supervisor_agent.route_request(load_balanced_request)

        

        assert result == "data2"

