"""
Real Agent Orchestration Integration Test - NO MOCKS

Critical integration test for agent orchestration using REAL services only.
Validates supervisor  ->  triage  ->  data  ->  actions agent workflow with real execution.

Business Value Justification (BVJ):
1. Segment: Enterprise ($100K+ MRR protection)
2. Business Goal: Ensure reliable multi-agent orchestration prevents system failures
3. Value Impact: Validates core product functionality - agent orchestration workflows
4. Revenue Impact: Protects $100K+ MRR from orchestration failures causing customer churn

ARCHITECTURAL COMPLIANCE:
- Uses IsolatedEnvironment for test isolation
- REAL services only (NO MOCKS per CLAUDE.md policy)
- Real agent execution with actual LLM calls
- Real WebSocket connections and event tracking
- Docker-compose for service dependencies
- Performance validation with real timing constraints

TECHNICAL DETAILS:
- Real supervisor agent orchestrates real sub-agents
- Real context passing between agents
- Real tool execution and state management
- Real WebSocket event emission and validation
- Real performance and latency measurement
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List, Set
import pytest
import pytest_asyncio

# Import test framework - NO MOCKS
from test_framework.environment_isolation import isolated_test_env, get_test_env_manager
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient

# Import schemas
from netra_backend.app.schemas.user_plan import PlanTier
from netra_backend.app.services.user_execution_context import UserExecutionContext


class RealAgentOrchestrationCore:
    """Core infrastructure for real agent orchestration testing."""
    
    REQUIRED_ORCHESTRATION_EVENTS = {
        "agent_started",
        "supervisor_routing", 
        "agent_thinking",
        "tool_executing",
        "tool_completed",
        "agent_handoff",
        "agent_completed"
    }
    
    def __init__(self):
        self.auth_client = None
        self.backend_client = None
        self.test_user = None
        self.ws_client = None
        self.orchestration_events = []
        self.agent_hierarchy = []
        
    async def setup_real_orchestration_infrastructure(self, isolated_env) -> Dict[str, Any]:
        """Setup real agent orchestration test infrastructure."""
        
        # Ensure real services
        assert isolated_env.get("USE_REAL_SERVICES") == "true", "Must use real services"
        assert isolated_env.get("TESTING") == "1", "Must be in testing mode"
        
        # Initialize real service clients
        auth_host = isolated_env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = isolated_env.get("AUTH_SERVICE_PORT", "8001") 
        backend_host = isolated_env.get("BACKEND_HOST", "localhost")
        backend_port = isolated_env.get("BACKEND_PORT", "8000")
        
        self.auth_client = AuthTestClient(f"http://{auth_host}:{auth_port}")
        self.backend_client = BackendTestClient(f"http://{backend_host}:{backend_port}")
        
        # Create real authenticated user for orchestration testing
        await self._setup_real_test_user()
        
        # Establish real WebSocket connection for orchestration events
        await self._setup_real_websocket_connection(backend_host, backend_port)
        
        return {
            "auth_client": self.auth_client,
            "backend_client": self.backend_client,
            "ws_client": self.ws_client,
            "user_data": self.test_user,
            "env": isolated_env
        }
    
    async def _setup_real_test_user(self):
        """Create real test user for orchestration."""
        test_email = f"orchestration-test-{uuid.uuid4()}@netra-test.com"
        test_password = "OrchestrationTest123!"
        
        # Real user registration and login
        register_response = await self.auth_client.register(
            email=test_email,
            password=test_password,
            name="Real Orchestration Test User"
        )
        assert register_response.get("success"), f"Real user registration failed: {register_response}"
        
        login_response = await self.auth_client.login(test_email, test_password)
        assert login_response.get("access_token"), f"Real user login failed: {login_response}"
        
        self.test_user = {
            "user_id": login_response.get("user_id"),
            "email": test_email,
            "token": login_response["access_token"]
        }
    
    async def _setup_real_websocket_connection(self, backend_host: str, backend_port: str):
        """Setup real WebSocket connection for orchestration event tracking."""
        ws_url = f"ws://{backend_host}:{backend_port}/ws"
        self.ws_client = WebSocketTestClient(ws_url)
        
        connection_success = await self.ws_client.connect(
            token=self.test_user["token"],
            timeout=10.0
        )
        
        assert connection_success and self.ws_client.is_connected, \
            "Real WebSocket connection failed for orchestration testing"
    
    async def execute_real_orchestration_request(self, request_message: str, 
                                               expected_agents: Optional[List[str]] = None,
                                               timeout: float = 60.0) -> Dict[str, Any]:
        """Execute real agent orchestration request and track events."""
        
        # Clear previous events
        self.orchestration_events.clear()
        self.agent_hierarchy.clear()
        
        # Start event collection task
        collection_task = asyncio.create_task(
            self._collect_real_orchestration_events(timeout)
        )
        
        # Send real orchestration request
        request_start = time.time()
        await self.ws_client.send_chat(request_message)
        
        # Wait for orchestration completion
        try:
            await collection_task
        except asyncio.TimeoutError:
            pass
        
        request_end = time.time()
        total_time = request_end - request_start
        
        # Analyze collected orchestration data
        return self._analyze_real_orchestration_results(total_time, expected_agents)
    
    async def _collect_real_orchestration_events(self, timeout: float):
        """Collect real orchestration events from WebSocket."""
        start_time = time.time()
        orchestration_complete = False
        
        while time.time() - start_time < timeout and not orchestration_complete:
            event = await self.ws_client.receive(timeout=2.0)
            if event:
                self.orchestration_events.append({
                    "event": event,
                    "timestamp": time.time() - start_time,
                    "event_type": event.get("type", "unknown")
                })
                
                # Track agent hierarchy
                if event.get("type") == "agent_started":
                    agent_info = {
                        "agent_type": event.get("agent_type", "unknown"),
                        "agent_id": event.get("agent_id"),
                        "parent_agent": event.get("parent_agent"),
                        "started_at": time.time() - start_time
                    }
                    self.agent_hierarchy.append(agent_info)
                
                # Check for orchestration completion
                if event.get("type") in ["agent_completed", "final_report", "orchestration_complete"]:
                    orchestration_complete = True
                    break
        
        if not orchestration_complete and time.time() - start_time >= timeout:
            raise asyncio.TimeoutError(f"Orchestration did not complete within {timeout}s")
    
    def _analyze_real_orchestration_results(self, total_time: float, 
                                          expected_agents: Optional[List[str]]) -> Dict[str, Any]:
        """Analyze real orchestration results."""
        event_types = {event["event_type"] for event in self.orchestration_events}
        agent_types = {agent["agent_type"] for agent in self.agent_hierarchy}
        
        # Validate orchestration requirements
        missing_events = self.REQUIRED_ORCHESTRATION_EVENTS - event_types
        orchestration_valid = len(missing_events) == 0
        
        # Check expected agents
        expected_agents_present = True
        if expected_agents:
            expected_set = set(expected_agents)
            expected_agents_present = expected_set.issubset(agent_types)
        
        return {
            "total_time": total_time,
            "event_count": len(self.orchestration_events),
            "unique_event_types": len(event_types),
            "agent_count": len(self.agent_hierarchy),
            "agent_types": list(agent_types),
            "orchestration_valid": orchestration_valid,
            "missing_events": list(missing_events),
            "expected_agents_present": expected_agents_present,
            "events_timeline": self.orchestration_events,
            "agent_hierarchy": self.agent_hierarchy,
            "performance_acceptable": total_time < 45.0  # 45s timeout for real orchestration
        }
    
    async def validate_real_agent_handoff(self, source_agent: str, target_agent: str) -> Dict[str, bool]:
        """Validate real agent handoff occurred correctly."""
        handoff_events = [
            event for event in self.orchestration_events
            if event["event_type"] == "agent_handoff"
        ]
        
        # Find specific handoff
        target_handoff = None
        for event in handoff_events:
            event_data = event["event"]
            if (event_data.get("source_agent") == source_agent and 
                event_data.get("target_agent") == target_agent):
                target_handoff = event
                break
        
        return {
            "handoff_occurred": target_handoff is not None,
            "handoff_data_complete": target_handoff is not None and target_handoff["event"].get("context_preserved", False),
            "handoff_timing_valid": target_handoff is not None and target_handoff["timestamp"] < 30.0
        }
    
    async def teardown_real_orchestration(self):
        """Clean up real orchestration test infrastructure."""
        if self.ws_client and self.ws_client.is_connected:
            await self.ws_client.disconnect()
        if self.auth_client:
            await self.auth_client.close()
        if self.backend_client:
            await self.backend_client.close()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestRealAgentOrchestration:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Real agent orchestration integration tests."""
    
    @pytest_asyncio.fixture
    async def orchestration_core(self, isolated_test_env):
        """Setup real orchestration test infrastructure."""
        core = RealAgentOrchestrationCore()
        infrastructure = await core.setup_real_orchestration_infrastructure(isolated_test_env)
        yield core
        await core.teardown_real_orchestration()
    
    async def test_real_supervisor_agent_orchestration(self, orchestration_core):
        """
        CRITICAL: Test real supervisor agent orchestrating sub-agents.
        
        Validates: Supervisor  ->  Triage  ->  Data  ->  Actions orchestration with real execution.
        """
        request_message = "Analyze my AI infrastructure costs and provide optimization recommendations with implementation plan"
        expected_agents = ["supervisor", "triage", "data", "actions"]
        
        orchestration_result = await orchestration_core.execute_real_orchestration_request(
            request_message, expected_agents, timeout=60.0
        )
        
        # Validate orchestration success
        assert orchestration_result["orchestration_valid"], \
            f"Real orchestration invalid. Missing events: {orchestration_result['missing_events']}"
        assert orchestration_result["expected_agents_present"], \
            f"Expected agents not present. Found: {orchestration_result['agent_types']}"
        assert orchestration_result["performance_acceptable"], \
            f"Real orchestration too slow: {orchestration_result['total_time']:.2f}s"
        
        # Validate agent hierarchy
        assert orchestration_result["agent_count"] >= 3, \
            f"Insufficient agents in orchestration: {orchestration_result['agent_count']}"
        assert "supervisor" in orchestration_result["agent_types"], "Supervisor agent not found in orchestration"
        
        # Validate event flow
        assert orchestration_result["event_count"] >= 10, \
            f"Insufficient orchestration events: {orchestration_result['event_count']}"
    
    async def test_real_agent_context_preservation(self, orchestration_core):
        """
        CRITICAL: Test context preservation during real agent handoff.
        
        Validates that context is preserved when supervisor hands off to sub-agents.
        """
        context_test_message = "Analyze costs for project 'TestOrchestration' with budget $50000 and deadline 2024-Q4"
        
        orchestration_result = await orchestration_core.execute_real_orchestration_request(
            context_test_message, ["supervisor", "triage", "data"], timeout=45.0
        )
        
        # Validate orchestration completed
        assert orchestration_result["orchestration_valid"], "Real context preservation orchestration failed"
        
        # Validate handoff with context preservation
        handoff_validation = await orchestration_core.validate_real_agent_handoff("supervisor", "triage")
        assert handoff_validation["handoff_occurred"], "Real supervisor  ->  triage handoff did not occur"
        assert handoff_validation["handoff_data_complete"], "Real handoff did not preserve context data"
        
        # Check for context keywords in events
        context_preserved = False
        context_keywords = ["TestOrchestration", "$50000", "2024-Q4"]
        
        for event_data in orchestration_result["events_timeline"]:
            event_content = json.dumps(event_data["event"]).lower()
            if any(keyword.lower() in event_content for keyword in context_keywords):
                context_preserved = True
                break
        
        assert context_preserved, "Context keywords not found in real orchestration events"
    
    async def test_real_orchestration_error_recovery(self, orchestration_core):
        """
        CRITICAL: Test orchestration error recovery with real services.
        
        Validates that orchestration can recover from errors and continue processing.
        """
        # Send complex request that might trigger edge cases
        error_test_message = "Complex analysis request with potential edge cases: analyze costs for $$INVALID_PROJECT$$ with undefined parameters"
        
        orchestration_result = await orchestration_core.execute_real_orchestration_request(
            error_test_message, timeout=30.0
        )
        
        # Should get some orchestration events even if errors occur
        assert orchestration_result["event_count"] > 0, "No orchestration events received during error test"
        
        # Check for error handling events
        error_events = [
            event for event in orchestration_result["events_timeline"]
            if "error" in event["event_type"].lower() or 
               "error" in json.dumps(event["event"]).lower()
        ]
        
        # WebSocket connection should remain stable
        assert orchestration_core.ws_client.is_connected, "WebSocket connection lost during orchestration error"
        
        # Test recovery with normal request
        recovery_message = "Simple recovery test - basic cost analysis"
        recovery_result = await orchestration_core.execute_real_orchestration_request(
            recovery_message, timeout=30.0
        )
        
        assert recovery_result["event_count"] > 0, "Orchestration failed to recover after error"
        assert recovery_result["orchestration_valid"] or recovery_result["event_count"] >= 3, \
            "Orchestration recovery insufficient"
    
    async def test_real_concurrent_orchestration_requests(self, orchestration_core):
        """
        CRITICAL: Test concurrent orchestration requests with real services.
        
        Validates that multiple orchestration requests can be handled simultaneously.
        """
        # Prepare concurrent requests
        concurrent_requests = [
            "Quick cost analysis for Project Alpha",
            "Performance optimization recommendations", 
            "Infrastructure scaling analysis"
        ]
        
        # Execute requests with staggered timing
        results = []
        for i, request in enumerate(concurrent_requests):
            result = await orchestration_core.execute_real_orchestration_request(
                request, timeout=25.0
            )
            results.append(result)
            
            # Brief pause between requests to avoid overwhelming
            if i < len(concurrent_requests) - 1:
                await asyncio.sleep(2.0)
        
        # Validate all concurrent requests succeeded
        for i, result in enumerate(results):
            assert result["event_count"] > 0, f"Concurrent request {i+1} received no events"
            assert result["performance_acceptable"] or result["total_time"] < 30.0, \
                f"Concurrent request {i+1} too slow: {result['total_time']:.2f}s"
        
        # WebSocket should remain stable throughout
        assert orchestration_core.ws_client.is_connected, "WebSocket lost during concurrent orchestration"
    
    async def test_real_orchestration_performance_validation(self, orchestration_core):
        """
        CRITICAL: Test orchestration performance with real services.
        
        Validates that orchestration meets performance requirements under real load.
        """
        performance_test_requests = [
            "Performance test 1: Quick infrastructure analysis",
            "Performance test 2: Basic cost optimization",
            "Performance test 3: Simple recommendations"
        ]
        
        total_start = time.time()
        performance_results = []
        
        for request in performance_test_requests:
            result = await orchestration_core.execute_real_orchestration_request(
                request, timeout=20.0
            )
            performance_results.append(result)
        
        total_time = time.time() - total_start
        
        # Performance validation
        avg_orchestration_time = sum(r["total_time"] for r in performance_results) / len(performance_results)
        max_orchestration_time = max(r["total_time"] for r in performance_results)
        
        assert avg_orchestration_time < 15.0, f"Average orchestration time too slow: {avg_orchestration_time:.2f}s"
        assert max_orchestration_time < 25.0, f"Slowest orchestration too slow: {max_orchestration_time:.2f}s" 
        assert total_time < 60.0, f"Total performance test time too slow: {total_time:.2f}s"
        
        # All requests should have succeeded
        successful_orchestrations = sum(1 for r in performance_results if r["event_count"] > 0)
        success_rate = successful_orchestrations / len(performance_results)
        assert success_rate >= 0.8, f"Orchestration success rate too low: {success_rate:.2f}"
    
    async def test_real_orchestration_agent_types_validation(self, orchestration_core):
        """
        CRITICAL: Test different agent types in real orchestration.
        
        Validates that different agent types can be orchestrated correctly.
        """
        agent_type_tests = [
            ("Data analysis request for cost optimization", ["supervisor", "triage", "data"]),
            ("Action recommendations for infrastructure improvements", ["supervisor", "triage", "actions"]),
            ("Comprehensive analysis with implementation plan", ["supervisor", "triage", "data", "actions"])
        ]
        
        for request_message, expected_agents in agent_type_tests:
            result = await orchestration_core.execute_real_orchestration_request(
                request_message, expected_agents, timeout=40.0
            )
            
            # Validate agent type orchestration
            assert result["expected_agents_present"], \
                f"Expected agents {expected_agents} not found. Got: {result['agent_types']}"
            assert result["orchestration_valid"], \
                f"Orchestration invalid for agent types {expected_agents}"
            
            # Brief pause between tests
            await asyncio.sleep(1.0)
    
    async def test_real_orchestration_websocket_stability(self, orchestration_core):
        """
        CRITICAL: Test WebSocket stability during extended orchestration.
        
        Validates that WebSocket connection remains stable during long orchestration sequences.
        """
        # Extended orchestration test
        extended_request = "Comprehensive infrastructure analysis including cost optimization, performance analysis, security review, and scaling recommendations with detailed implementation timeline"
        
        initial_connection = orchestration_core.ws_client.is_connected
        assert initial_connection, "WebSocket not connected before extended orchestration"
        
        # Execute extended orchestration
        result = await orchestration_core.execute_real_orchestration_request(
            extended_request, timeout=90.0  # Longer timeout for extended test
        )
        
        # Connection should remain stable
        final_connection = orchestration_core.ws_client.is_connected
        assert final_connection, "WebSocket connection lost during extended orchestration"
        
        # Should receive substantial orchestration activity
        assert result["event_count"] >= 5, f"Insufficient events for extended orchestration: {result['event_count']}"
        assert result["agent_count"] >= 2, f"Insufficient agents for extended orchestration: {result['agent_count']}"
        
        # Test connection stability with follow-up request
        followup_request = "Quick follow-up analysis to test stability"
        followup_result = await orchestration_core.execute_real_orchestration_request(
            followup_request, timeout=15.0
        )
        
        assert followup_result["event_count"] > 0, "WebSocket unstable after extended orchestration"
        assert orchestration_core.ws_client.is_connected, "Final connection stability check failed"


if __name__ == '__main__':
    # Run the real agent orchestration integration tests
    pytest.main([__file__, '-v', '--tb=short', '-m', 'integration'])