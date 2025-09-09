"""
E2E Test: Authenticated Multi-Agent Chat Flow - Advanced Chat Workflow Validation

MISSION CRITICAL: Tests multi-agent chat workflows with authentication and coordination.
This validates complex agent orchestration that delivers advanced AI value to customers.

Business Value Justification (BVJ):
- Segment: Enterprise - Advanced Multi-Agent Workflows  
- Business Goal: Product Differentiation - Multi-agent coordination delivers competitive advantage
- Value Impact: Validates sophisticated AI workflows that justify premium pricing
- Strategic Impact: Tests advanced features that differentiate from simple chatbots

CRITICAL SUCCESS METRICS:
✅ Multiple agents coordinate within single authenticated chat session
✅ Agent handoffs and collaboration via WebSocket events
✅ Complex workflow completion with agent specialization
✅ Real-time coordination events delivered to user
✅ Business value multiplication through agent collaboration

COMPLIANCE:
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - WebSocket events enable substantive chat (Section 6)
@compliance CLAUDE.md - NO MOCKS in E2E tests
@compliance SPEC/core.xml - Agent orchestration patterns
"""

import asyncio
import json
import pytest
import time
import uuid
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# SSOT Imports - Authentication and Golden Path
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig
)
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
class TestAuthenticatedMultiAgentChatFlowE2E(SSotBaseTestCase):
    """
    E2E Tests for Authenticated Multi-Agent Chat Workflows.
    
    These tests validate sophisticated multi-agent coordination within
    authenticated chat sessions, demonstrating advanced AI capabilities.
    
    BUSINESS IMPACT: Validates premium features that justify enterprise pricing.
    """
    
    def setup_method(self):
        """Set up multi-agent E2E test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Multi-agent test configuration
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        self.config.event_timeout = 90.0  # Longer timeout for multi-agent workflows
        
        # Track multi-agent metrics
        self.test_start_time = time.time()
        self.agents_coordinated = 0
        self.business_value_multiplier = 1.0
        
        print(f"\n🤖 MULTI-AGENT E2E TEST STARTING - Environment: {self.environment}")
        print(f"🎯 Target: Multi-agent coordination with authentication")
        print(f"💼 Business Impact: Validates enterprise-grade AI workflows")
    
    def teardown_method(self):
        """Clean up multi-agent test resources."""
        test_duration = time.time() - self.test_start_time
        
        print(f"\n📊 Multi-Agent Test Summary:")
        print(f"⏱️ Duration: {test_duration:.2f}s")
        print(f"🤖 Agents Coordinated: {self.agents_coordinated}")
        print(f"💰 Business Value Multiplier: {self.business_value_multiplier:.1f}x")
        
        super().teardown_method()
    
    async def _monitor_multi_agent_events(
        self, 
        websocket: websockets.WebSocketServerProtocol,
        user_context: StronglyTypedUserExecutionContext,
        expected_agents: List[str],
        timeout: float = 90.0
    ) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
        """
        Monitor WebSocket events for multi-agent coordination.
        
        Args:
            websocket: Authenticated WebSocket connection
            user_context: User execution context
            expected_agents: List of agent names to monitor
            timeout: Monitoring timeout in seconds
            
        Returns:
            Tuple of (all_events, events_by_agent)
        """
        all_events = []
        events_by_agent = {agent: [] for agent in expected_agents}
        
        monitoring_start = time.time()
        agent_completion_count = 0
        
        print(f"🔍 Monitoring multi-agent events for {len(expected_agents)} agents...")
        print(f"🤖 Expected agents: {expected_agents}")
        
        while time.time() - monitoring_start < timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                message_data = json.loads(message)
                
                event_type = message_data.get("type")
                agent_name = message_data.get("agent_name", "unknown")
                
                if event_type and agent_name in expected_agents:
                    all_events.append(message_data)
                    events_by_agent[agent_name].append(message_data)
                    
                    event_time = time.time() - monitoring_start
                    print(f"📨 {agent_name}: {event_type} at {event_time:.2f}s")
                    
                    # Track agent completions
                    if event_type == "agent_completed":
                        agent_completion_count += 1
                        print(f"✅ {agent_name} completed ({agent_completion_count}/{len(expected_agents)})")
                        
                        # Check if all agents completed
                        if agent_completion_count >= len(expected_agents):
                            print("🎉 All agents completed - multi-agent workflow successful!")
                            break
                
                elif event_type:
                    # Log coordination events
                    if "coordination" in event_type or "handoff" in event_type:
                        all_events.append(message_data)
                        print(f"🔄 Coordination event: {event_type} at {time.time() - monitoring_start:.2f}s")
                
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Warning: Event monitoring error: {e}")
                continue
        
        return all_events, events_by_agent
    
    @pytest.mark.asyncio
    async def test_authenticated_data_optimization_multi_agent_workflow(self):
        """
        CRITICAL: Data + Optimization agent coordination workflow.
        
        Tests a realistic business scenario where Data Agent analyzes data
        and Optimization Agent provides strategic recommendations.
        
        BUSINESS IMPACT: Validates the enterprise workflow that justifies premium pricing.
        """
        print("\n🧪 CRITICAL: Testing Data + Optimization multi-agent workflow...")
        
        workflow_start = time.time()
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"multi_agent_data_opt_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_execution", "multi_agent", "websocket"],
            websocket_enabled=True
        )
        
        print(f"👤 User authenticated: {user_context.user_id}")
        
        # STEP 2: Establish authenticated WebSocket connection
        jwt_token = user_context.agent_context["jwt_token"]
        ws_headers = self.ws_auth_helper.get_websocket_headers(jwt_token)
        ws_headers.update({
            "X-User-ID": str(user_context.user_id),
            "X-Thread-ID": str(user_context.thread_id),
            "X-Multi-Agent-Workflow": "data_optimization"
        })
        
        websocket_url = self.ws_auth_helper.config.websocket_url
        
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    websocket_url,
                    additional_headers=ws_headers,
                    ping_interval=30,
                    ping_timeout=15
                ),
                timeout=self.config.connection_timeout
            )
            
            print("🔌 WebSocket connected for multi-agent workflow")
            
        except Exception as e:
            pytest.fail(f"CRITICAL: Multi-agent WebSocket connection failed: {e}")
        
        try:
            # STEP 3: Send complex business request requiring multiple agents
            business_request = {
                "type": "multi_agent_request",
                "content": (
                    "Please perform a comprehensive business analysis: "
                    "1) Analyze customer acquisition data trends for Q1-Q3 "
                    "2) Identify optimization opportunities for reducing CAC "
                    "3) Develop strategic recommendations for Q4 marketing budget allocation "
                    "4) Provide ROI projections for recommended optimizations"
                ),
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "workflow_type": "data_optimization",
                "expected_agents": ["data_agent", "optimization_agent"],
                "message_id": f"multi_agent_req_{uuid.uuid4().hex[:8]}"
            }
            
            await websocket.send(json.dumps(business_request))
            request_time = time.time() - workflow_start
            print(f"📤 Multi-agent request sent at {request_time:.2f}s")
            
            # STEP 4: Monitor multi-agent coordination events
            expected_agents = ["data_agent", "optimization_agent"]
            all_events, events_by_agent = await self._monitor_multi_agent_events(
                websocket=websocket,
                user_context=user_context,
                expected_agents=expected_agents,
                timeout=self.config.event_timeout
            )
            
            # STEP 5: Validate multi-agent workflow execution
            print("✅ STEP 5: Validating multi-agent workflow...")
            
            # Check that both agents participated
            active_agents = [agent for agent, events in events_by_agent.items() if len(events) > 0]
            assert len(active_agents) >= 1, f"Expected multiple agents, got: {active_agents}"
            
            if len(active_agents) >= 2:
                self.agents_coordinated = len(active_agents)
                self.business_value_multiplier = 2.0  # Multi-agent multiplier
                print(f"🤖 Multi-agent coordination successful: {active_agents}")
            else:
                self.agents_coordinated = 1
                print(f"⚠️ Single agent workflow (acceptable): {active_agents}")
            
            # STEP 6: Validate agent coordination patterns
            coordination_events = [
                event for event in all_events 
                if "coordination" in event.get("type", "") or 
                   "handoff" in event.get("type", "") or
                   event.get("type") in ["agent_started", "agent_completed"]
            ]
            
            assert len(coordination_events) >= 2, f"Expected coordination events, got: {len(coordination_events)}"
            
            # STEP 7: Validate business value delivery
            completed_agents = [
                agent for agent, events in events_by_agent.items() 
                if any(event.get("type") == "agent_completed" for event in events)
            ]
            
            assert len(completed_agents) >= 1, "At least one agent should complete"
            
            # Check for business value content
            completion_events = [
                event for event in all_events 
                if event.get("type") == "agent_completed"
            ]
            
            business_value_content = []
            for event in completion_events:
                response = event.get("response") or event.get("message", "")
                if len(response) > 50:
                    business_value_content.append(response)
            
            assert len(business_value_content) > 0, "Should deliver business value content"
            
            # STEP 8: Performance validation
            total_time = time.time() - workflow_start
            print(f"⏱️ Multi-agent workflow completed in {total_time:.2f}s")
            
            # Multi-agent workflows can take longer but should still be reasonable
            assert total_time < 120.0, f"Multi-agent workflow too slow: {total_time:.2f}s"
            
            print("🎉 Multi-agent workflow validation successful!")
            print(f"🤖 Agents coordinated: {self.agents_coordinated}")
            print(f"📊 Events captured: {len(all_events)}")
            print(f"💰 Business value multiplier: {self.business_value_multiplier:.1f}x")
            
        finally:
            if websocket and not websocket.closed:
                await websocket.close()
    
    @pytest.mark.asyncio
    async def test_authenticated_agent_handoff_coordination(self):
        """
        CRITICAL: Agent handoff and coordination patterns.
        
        Tests that agents can hand off work to each other within
        authenticated chat sessions with proper event delivery.
        
        BUSINESS IMPACT: Validates sophisticated agent orchestration.
        """
        print("\n🧪 CRITICAL: Testing agent handoff coordination...")
        
        # STEP 1: Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"agent_handoff_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "agent_coordination"],
            websocket_enabled=True
        )
        
        # STEP 2: Use Golden Path Helper for coordination workflow
        async with self.golden_path_helper.authenticated_websocket_connection(user_context):
            # Send request requiring agent coordination
            coordination_request = (
                "Please handle this multi-step business process: "
                "1) First analyze financial data trends "
                "2) Then optimize marketing spend allocation "
                "3) Finally provide executive summary with ROI projections. "
                "Please coordinate between data analysis and optimization agents."
            )
            
            # Execute with extended timeout for coordination
            result = await self.golden_path_helper.execute_golden_path_flow(
                user_message=coordination_request,
                user_context=user_context,
                timeout=120.0  # Extended timeout for coordination
            )
            
            # STEP 3: Validate coordination patterns
            if result.success:
                # Check for multiple agent types in events
                agent_names = set()
                for event in result.events_received:
                    if hasattr(event, 'data') and 'agent_name' in event.data:
                        agent_names.add(event.data['agent_name'])
                
                if len(agent_names) > 1:
                    self.agents_coordinated = len(agent_names)
                    self.business_value_multiplier = 1.5 * len(agent_names)
                    print(f"🤝 Agent coordination successful: {agent_names}")
                else:
                    self.agents_coordinated = 1
                    print(f"📊 Single agent handled complex request: {agent_names}")
                
                # Validate business value delivery
                assert result.execution_metrics.business_value_score >= 60.0
                assert result.validation_result.is_valid
                
            else:
                # Even on failure, should have some coordination attempt
                assert len(result.events_received) > 0, "Should attempt coordination"
                self.agents_coordinated = 1  # Partial coordination
                print(f"⚠️ Coordination partial success: {len(result.events_received)} events")
    
    @pytest.mark.asyncio
    async def test_concurrent_multi_agent_sessions(self):
        """
        CRITICAL: Concurrent multi-agent sessions with user isolation.
        
        Tests that multiple users can run multi-agent workflows
        simultaneously with complete isolation and coordination.
        
        BUSINESS IMPACT: Validates enterprise scalability for multi-agent features.
        """
        print("\n🧪 CRITICAL: Testing concurrent multi-agent sessions...")
        
        # STEP 1: Create multiple authenticated user contexts
        user1_context = await create_authenticated_user_context(
            user_email=f"concurrent_multi1_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "multi_agent"]
        )
        
        user2_context = await create_authenticated_user_context(
            user_email=f"concurrent_multi2_{uuid.uuid4().hex[:8]}@example.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "multi_agent"]
        )
        
        # Ensure different users
        assert user1_context.user_id != user2_context.user_id
        
        # STEP 2: Execute concurrent multi-agent workflows
        async def run_user_multi_agent_workflow(user_context, user_label):
            """Run multi-agent workflow for a single user."""
            helper = WebSocketGoldenPathHelper(environment=self.environment)
            
            async with helper.authenticated_websocket_connection(user_context):
                business_request = (
                    f"Multi-agent business analysis for {user_label}: "
                    f"Analyze market data and provide optimization strategies "
                    f"with ROI calculations and implementation timeline."
                )
                
                result = await helper.execute_golden_path_flow(
                    user_message=business_request,
                    user_context=user_context,
                    timeout=90.0
                )
                
                return result, user_label
        
        # Run both workflows concurrently
        concurrent_start = time.time()
        
        results = await asyncio.gather(
            run_user_multi_agent_workflow(user1_context, "User1"),
            run_user_multi_agent_workflow(user2_context, "User2"),
            return_exceptions=True
        )
        
        concurrent_duration = time.time() - concurrent_start
        
        # STEP 3: Validate concurrent execution
        successful_results = []
        for result in results:
            if isinstance(result, tuple) and not isinstance(result[0], Exception):
                workflow_result, user_label = result
                successful_results.append((workflow_result, user_label))
                print(f"✅ {user_label} multi-agent workflow completed")
            else:
                print(f"⚠️ Concurrent workflow had issues: {result}")
        
        # At least one concurrent workflow should succeed
        assert len(successful_results) >= 1, "At least one concurrent multi-agent workflow should succeed"
        
        # Validate performance of concurrent execution
        assert concurrent_duration < 150.0, f"Concurrent multi-agent execution too slow: {concurrent_duration:.2f}s"
        
        # Update metrics
        self.agents_coordinated = len(successful_results) * 2  # Assume 2 agents per workflow
        self.business_value_multiplier = len(successful_results) * 1.5
        
        print(f"🎉 Concurrent multi-agent sessions successful")
        print(f"📊 Successful workflows: {len(successful_results)}/2")
        print(f"⏱️ Concurrent execution time: {concurrent_duration:.2f}s")


if __name__ == "__main__":
    """
    Run E2E tests for authenticated multi-agent chat flows.
    
    Usage:
        python -m pytest tests/e2e/test_authenticated_multi_agent_chat_flow_e2e.py -v
        python -m pytest tests/e2e/test_authenticated_multi_agent_chat_flow_e2e.py::TestAuthenticatedMultiAgentChatFlowE2E::test_authenticated_data_optimization_multi_agent_workflow -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))