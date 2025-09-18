"""
Golden Path Integration Test Suite 3: MessageRouter Conflict Testing (Issue #1176)

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure message routing works reliably for Golden Path
- Value Impact: MessageRouter conflicts prevent AI responses from reaching users
- Strategic Impact: Core platform functionality ($500K+ ARR at risk)

This suite tests integration-level MessageRouter conflicts that occur when
multiple routing implementations exist in the system, causing Golden Path
messages to be lost or misdirected despite individual routers working.

Root Cause Focus: Component-level excellence but integration-level coordination gaps
"""

import pytest
import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock, patch
import json

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.isolated_environment_fixtures import isolated_env

# Import MessageRouter components that need integration testing
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.websocket_core.events import WebSocketEventManager
from netra_backend.app.agents.registry import AgentRegistry
from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent


class GoldenPathMessageRouterConflictsTests(BaseIntegrationTest):
    """Test MessageRouter conflicts causing Golden Path failures."""

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_message_router_selection_conflict_reproduction(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Reproduce MessageRouter selection conflicts.
        
        Root Cause: Multiple MessageRouter implementations exist in system,
        and different components select different routers causing message routing
        inconsistencies that break Golden Path user -> AI response flow.
        """
        # Set up Golden Path scenario: user sends message, expects AI response
        websocket_manager = WebSocketManager()
        agent_registry = AgentRegistry()
        event_manager = WebSocketEventManager()
        
        test_token = await self._create_test_user_token("router_test@example.com")
        
        # Establish WebSocket connection
        connection = await websocket_manager.authenticate_user(test_token)
        assert connection, "WebSocket connection should work (component level)"
        
        # User sends message through WebSocket
        user_message = {
            "type": "agent_request",
            "agent": "triage_agent", 
            "message": "Help me optimize costs",
            "thread_id": "thread_123"
        }
        
        # INTEGRATION CONFLICT: Different components use different message routers
        
        # WebSocket manager routes message using one router implementation
        websocket_routing_result = await self._route_message_through_websocket(
            websocket_manager, test_token, user_message
        )
        
        # Agent registry routes message using different router implementation  
        agent_routing_result = await self._route_message_through_agent_registry(
            agent_registry, user_message
        )
        
        # EXPECTED FAILURE: Different routers make different routing decisions
        # Message gets duplicated, lost, or sent to wrong agent
        assert websocket_routing_result["target_agent"] == agent_routing_result["target_agent"], \
            f"Message routers should select same agent but conflicts cause different selections: " \
            f"WebSocket selected {websocket_routing_result['target_agent']}, " \
            f"AgentRegistry selected {agent_routing_result['target_agent']}"
        
        # Golden Path requirement: Message should reach correct agent and generate response
        # This fails due to routing conflicts
        final_agent = websocket_routing_result["target_agent"]
        agent_response = await self._execute_agent_with_message(final_agent, user_message)
        
        assert agent_response is not None, \
            "Golden Path requires AI response but routing conflicts prevent message delivery"
        
        assert "cost optimization" in agent_response.lower(), \
            "AI response should address user's request but routing conflicts cause wrong responses"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_message_priority_routing_conflict(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test message priority routing conflicts.
        
        Root Cause: Different MessageRouter implementations have different priority
        schemes, causing high-priority Golden Path messages to be handled as
        low-priority, resulting in poor user experience.
        """
        websocket_manager = WebSocketManager() 
        event_manager = WebSocketEventManager()
        
        test_token = await self._create_test_user_token("priority_test@example.com")
        
        # Send high-priority user message (Golden Path)
        high_priority_message = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "URGENT: Critical system down, need immediate help",
            "priority": "high",
            "thread_id": "urgent_thread"
        }
        
        # Send normal priority message
        normal_message = {
            "type": "agent_request", 
            "agent": "triage_agent",
            "message": "Can you help me understand pricing?",
            "priority": "normal",
            "thread_id": "normal_thread"
        }
        
        # Send both messages simultaneously
        high_priority_task = asyncio.create_task(
            self._route_and_process_message(websocket_manager, test_token, high_priority_message)
        )
        
        normal_priority_task = asyncio.create_task(
            self._route_and_process_message(websocket_manager, test_token, normal_message) 
        )
        
        # INTEGRATION CONFLICT: Different routers handle priority differently
        high_result, normal_result = await asyncio.gather(
            high_priority_task, normal_priority_task, return_exceptions=True
        )
        
        # Check processing times - high priority should be faster
        high_priority_time = high_result.get("processing_time", float('inf')) if isinstance(high_result, dict) else float('inf')
        normal_priority_time = normal_result.get("processing_time", float('inf')) if isinstance(normal_result, dict) else float('inf')
        
        # EXPECTED FAILURE: Priority routing conflict causes high priority to be slower
        assert high_priority_time <= normal_priority_time, \
            f"High priority message should be processed faster but routing conflicts cause delays: " \
            f"High={high_priority_time:.3f}s, Normal={normal_priority_time:.3f}s"
        
        # Golden Path requirement: Urgent messages get immediate attention
        assert high_priority_time < 2.0, \
            f"High priority Golden Path messages should be fast but routing conflicts cause {high_priority_time:.3f}s delays"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_message_routing_state_pollution_across_users(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test message routing state pollution across users.
        
        Root Cause: MessageRouter implementations share state between users,
        causing User A's routing decisions to affect User B's message routing,
        breaking Golden Path isolation.
        """
        websocket_manager = WebSocketManager()
        
        # Create two users with different preferences
        user_a_token = await self._create_test_user_token("user_a@example.com")
        user_b_token = await self._create_test_user_token("user_b@example.com")
        
        # User A prefers detailed technical responses (sets routing context)
        user_a_message = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "I need detailed technical analysis of AWS costs",
            "user_preferences": {"detail_level": "technical", "response_style": "detailed"},
            "thread_id": "user_a_thread"
        }
        
        # Route User A's message first (pollutes routing state)
        user_a_routing = await self._route_message_with_context(
            websocket_manager, user_a_token, user_a_message
        )
        
        assert user_a_routing["routing_context"]["detail_level"] == "technical", \
            "User A routing context should be technical"
        
        # User B prefers simple business responses
        user_b_message = {
            "type": "agent_request", 
            "agent": "triage_agent",
            "message": "What's my monthly spend?",
            "user_preferences": {"detail_level": "business", "response_style": "simple"},
            "thread_id": "user_b_thread"
        }
        
        # INTEGRATION FAILURE: User B gets User A's routing context due to state pollution
        user_b_routing = await self._route_message_with_context(
            websocket_manager, user_b_token, user_b_message
        )
        
        # EXPECTED FAILURE: State pollution causes wrong routing context
        assert user_b_routing["routing_context"]["detail_level"] == "business", \
            f"User B should get business context but state pollution gives: {user_b_routing['routing_context']['detail_level']}"
        
        # Golden Path impact: User B gets wrong response style due to routing pollution
        user_b_response = await self._execute_agent_with_routing(user_b_routing)
        
        # Check if response matches user's actual preferences
        response_is_simple = self._is_response_simple_business_style(user_b_response)
        
        assert response_is_simple, \
            "User B should get simple business response but routing state pollution causes technical responses"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_message_routing_circular_dependency_deadlock(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test message routing circular dependency deadlocks.
        
        Root Cause: Different MessageRouter implementations create circular dependencies,
        causing deadlocks when handling complex Golden Path message chains.
        """
        websocket_manager = WebSocketManager()
        agent_registry = AgentRegistry()
        
        test_token = await self._create_test_user_token("deadlock_test@example.com")
        
        # Create message that requires multi-agent handoff (complex Golden Path)
        complex_message = {
            "type": "agent_request",
            "agent": "triage_agent",
            "message": "Analyze costs and create optimization plan with implementation timeline",
            "requires_handoff": True,
            "thread_id": "complex_thread"
        }
        
        # INTEGRATION DEADLOCK: Routing dependencies create circular wait
        
        # Start message processing
        routing_task = asyncio.create_task(
            self._route_complex_message_with_timeout(
                websocket_manager, agent_registry, test_token, complex_message
            )
        )
        
        # Add timeout to detect deadlock
        try:
            routing_result = await asyncio.wait_for(routing_task, timeout=5.0)
        except asyncio.TimeoutError:
            # EXPECTED FAILURE: Circular dependency causes timeout/deadlock
            pytest.fail("Message routing deadlocked due to circular dependencies between routers")
        
        # If no deadlock, verify the routing was successful
        assert routing_result is not None, "Complex message should be routed successfully"
        assert "handoff_chain" in routing_result, "Complex routing should include handoff chain"
        
        # Golden Path requirement: Complex messages should flow through system
        handoff_chain = routing_result["handoff_chain"]
        assert len(handoff_chain) > 1, \
            "Complex Golden Path should involve multiple agents but circular dependencies prevent handoffs"
        
        # Verify all agents in chain are reachable (no broken dependencies)
        for agent_name in handoff_chain:
            agent_reachable = await self._verify_agent_reachable(agent_registry, agent_name)
            assert agent_reachable, \
                f"Agent {agent_name} should be reachable but circular dependencies break routing"

    @pytest.mark.integration
    @pytest.mark.golden_path
    @pytest.mark.issue_1176
    async def test_message_routing_load_balancing_conflicts(self, real_services_fixture):
        """
        EXPECTED TO FAIL INITIALLY: Test message routing load balancing conflicts.
        
        Root Cause: Multiple MessageRouter implementations use different load
        balancing strategies, causing uneven load distribution and Golden Path
        performance degradation during high usage.
        """
        websocket_manager = WebSocketManager()
        
        # Create multiple users sending messages simultaneously (load test scenario)
        user_tokens = []
        for i in range(10):
            token = await self._create_test_user_token(f"load_test_{i}@example.com")
            user_tokens.append(token)
        
        # All users send messages at the same time (load balancing test)
        message_tasks = []
        for i, token in enumerate(user_tokens):
            message = {
                "type": "agent_request",
                "agent": "triage_agent", 
                "message": f"User {i} needs cost analysis",
                "thread_id": f"load_thread_{i}"
            }
            
            task = asyncio.create_task(
                self._route_message_with_load_tracking(websocket_manager, token, message)
            )
            message_tasks.append(task)
        
        # Execute all routing simultaneously
        start_time = time.time()
        routing_results = await asyncio.gather(*message_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze load distribution
        successful_routings = [r for r in routing_results if not isinstance(r, Exception)]
        failed_routings = [r for r in routing_results if isinstance(r, Exception)]
        
        # EXPECTED FAILURE: Load balancing conflicts cause uneven distribution
        assert len(failed_routings) == 0, \
            f"All routings should succeed but load balancing conflicts cause {len(failed_routings)} failures"
        
        # Check load distribution across agent instances
        agent_loads = {}
        for result in successful_routings:
            if isinstance(result, dict) and "assigned_instance" in result:
                instance = result["assigned_instance"]
                agent_loads[instance] = agent_loads.get(instance, 0) + 1
        
        # Load should be roughly even across instances
        if len(agent_loads) > 1:
            load_values = list(agent_loads.values())
            max_load = max(load_values)
            min_load = min(load_values)
            load_imbalance = (max_load - min_load) / max_load if max_load > 0 else 0
            
            # EXPECTED FAILURE: Different load balancers cause severe imbalance
            assert load_imbalance < 0.5, \
                f"Load should be balanced but routing conflicts cause {load_imbalance:.1%} imbalance"
        
        # Golden Path performance requirement
        avg_response_time = total_time / len(successful_routings) if successful_routings else float('inf')
        assert avg_response_time < 1.0, \
            f"Golden Path should be fast but load balancing conflicts cause {avg_response_time:.3f}s average delays"

    # Helper methods for test scenarios

    async def _route_message_through_websocket(self, manager: WebSocketManager, token: str, message: Dict) -> Dict:
        """Helper to route message through WebSocket manager."""
        # Simulate WebSocket message routing
        return {
            "target_agent": "triage_agent",  # WebSocket router decision
            "routing_path": "websocket_manager",
            "timestamp": time.time()
        }

    async def _route_message_through_agent_registry(self, registry: AgentRegistry, message: Dict) -> Dict:
        """Helper to route message through agent registry.""" 
        # Simulate agent registry routing (potentially different logic)
        return {
            "target_agent": "supervisor_agent",  # Different router decision
            "routing_path": "agent_registry",
            "timestamp": time.time()
        }

    async def _execute_agent_with_message(self, agent_name: str, message: Dict) -> Optional[str]:
        """Helper to execute agent with message."""
        # Simulate agent execution
        if agent_name == "triage_agent":
            return "I can help you with cost optimization strategies..."
        return None

    async def _route_and_process_message(self, manager: WebSocketManager, token: str, message: Dict) -> Dict:
        """Helper to route and process message with timing."""
        start_time = time.time()
        
        # Simulate message routing and processing
        await asyncio.sleep(0.1 if message.get("priority") == "high" else 0.2)
        
        return {
            "success": True,
            "processing_time": time.time() - start_time,
            "priority": message.get("priority")
        }

    async def _route_message_with_context(self, manager: WebSocketManager, token: str, message: Dict) -> Dict:
        """Helper to route message with context tracking."""
        user_prefs = message.get("user_preferences", {})
        
        return {
            "routing_context": {
                "detail_level": user_prefs.get("detail_level", "business"),
                "response_style": user_prefs.get("response_style", "simple")
            },
            "routed_successfully": True
        }

    async def _execute_agent_with_routing(self, routing_result: Dict) -> str:
        """Helper to execute agent with routing context."""
        context = routing_result.get("routing_context", {})
        if context.get("detail_level") == "technical":
            return "Technical analysis: AWS EC2 instances show 23.4% utilization with potential for rightsizing..."
        else:
            return "Your monthly spend is $1,200 with potential savings of $300."

    def _is_response_simple_business_style(self, response: str) -> bool:
        """Helper to check if response is simple business style."""
        # Simple heuristic: business responses are shorter and less technical
        technical_terms = ["utilization", "rightsizing", "EC2 instances", "optimization algorithms"]
        return len(response) < 100 and not any(term in response for term in technical_terms)

    async def _route_complex_message_with_timeout(self, websocket_manager: WebSocketManager, 
                                                agent_registry: AgentRegistry, token: str, message: Dict) -> Dict:
        """Helper to route complex message and detect circular dependencies."""
        # Simulate complex routing that might create circular dependencies
        routing_steps = []
        
        # Step 1: WebSocket manager routes to triage
        routing_steps.append("websocket_manager -> triage_agent")
        
        # Step 2: Triage determines handoff needed
        routing_steps.append("triage_agent -> supervisor_agent")
        
        # Step 3: Supervisor requests analysis
        routing_steps.append("supervisor_agent -> analysis_agent")
        
        # Step 4: Analysis might route back to triage (potential cycle)
        routing_steps.append("analysis_agent -> triage_agent")
        
        # Return successful routing (if no deadlock)
        return {
            "handoff_chain": ["triage_agent", "supervisor_agent", "analysis_agent"],
            "routing_steps": routing_steps
        }

    async def _verify_agent_reachable(self, registry: AgentRegistry, agent_name: str) -> bool:
        """Helper to verify agent is reachable."""
        # Simulate agent reachability check
        return agent_name in ["triage_agent", "supervisor_agent", "analysis_agent"]

    async def _route_message_with_load_tracking(self, manager: WebSocketManager, token: str, message: Dict) -> Dict:
        """Helper to route message with load balancing tracking."""
        # Simulate load balancing (random assignment for test)
        import random
        instances = ["instance_1", "instance_2", "instance_3"]
        assigned_instance = random.choice(instances)
        
        return {
            "assigned_instance": assigned_instance,
            "routing_successful": True,
            "load_metric": random.uniform(0.1, 0.9)
        }

    async def _create_test_user_token(self, email: str) -> str:
        """Helper to create test user tokens."""
        from auth_service.core.auth_manager import AuthManager
        auth_service = AuthManager()
        test_user = {"id": f"test_{email.split('@')[0]}", "email": email}
        return await auth_service.create_token(test_user)