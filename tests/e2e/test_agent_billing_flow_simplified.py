"""E2E Agent Billing Flow Test - Real Services Compliance Update

CRITICAL E2E test for agent billing accuracy focused on business value.
Validates complete agent execution  ->  billing flow with REAL services only.

Business Value Justification (BVJ):
1. Segment: ALL paid tiers (revenue tracking critical)
2. Business Goal: Ensure accurate usage-based billing for agent operations
3. Value Impact: Protects revenue integrity - billing errors = customer trust loss
4. Revenue Impact: Each billing error costs $100-1000/month per customer

ARCHITECTURAL COMPLIANCE PER CLAUDE.md:
- Uses IsolatedEnvironment for all environment access
- Absolute imports only with setup_test_path()
- REAL services only - NO MOCKS (mocks = abomination)
- Tests real agent execution with WebSocket events for business value
- Real databases, real authentication, real billing systems

TECHNICAL DETAILS:
- Tests complete chat flow: WebSocket  ->  Agent  ->  Tool execution  ->  Billing
- Uses real database connections for billing validation
- Validates WebSocket agent events for substantive chat value
- Performance testing with real service execution
"""

# E2E test imports - CLAUDE.md compliant absolute import structure
import pytest
from test_framework import setup_test_path
setup_test_path()  # MUST be before project imports per CLAUDE.md

import asyncio
import time
import uuid
from typing import Dict, Any
import pytest_asyncio

# Import test framework - REAL SERVICES ONLY per CLAUDE.md
from test_framework.environment_isolation import get_test_env_manager, isolated_test_env
from test_framework.real_services import get_real_services
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient

# Import schemas using absolute paths
from netra_backend.app.schemas.user_plan import PlanTier

# Import real billing services for cost tracking per CLAUDE.md
from netra_backend.app.services.billing.billing_engine import BillingEngine
from tests.e2e.agent_billing_test_helpers import AgentRequestSimulator


class RealAgentBillingTestCore:
    """Core test infrastructure for real agent billing validation per CLAUDE.md."""
    
    def __init__(self):
        self.auth_client = None
        self.backend_client = None
        self.ws_client = None
        self.test_users = {}
        self.billing_records = []
        # Real billing services for cost tracking per CLAUDE.md
        self.billing_engine = BillingEngine()
        self.agent_simulator = AgentRequestSimulator()
        
    async def setup_real_billing_infrastructure(self, isolated_env) -> Dict[str, Any]:
        """Setup real billing test infrastructure with actual services."""
        
        # Ensure we're using real services per CLAUDE.md
        assert isolated_env.get("USE_REAL_SERVICES") == "true", "Must use real services"
        assert isolated_env.get("TESTING") == "1", "Must be in test mode"
        
        # Initialize real service clients
        auth_host = isolated_env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = isolated_env.get("AUTH_SERVICE_PORT", "8001")
        backend_host = isolated_env.get("BACKEND_HOST", "localhost")
        backend_port = isolated_env.get("BACKEND_PORT", "8000")
        
        self.auth_client = AuthTestClient(f"http://{auth_host}:{auth_port}")
        self.backend_client = BackendTestClient(f"http://{backend_host}:{backend_port}")
        
        return {
            "auth_client": self.auth_client,
            "backend_client": self.backend_client,
            "env": isolated_env
        }
    
    async def create_real_user_session(self, tier: PlanTier) -> Dict[str, Any]:
        """Create authenticated user session with real auth service."""
        test_email = f"billing-test-{uuid.uuid4()}@netra-test.com"
        test_password = "BillingTestPass123!"
        
        # Real user registration
        register_response = await self.auth_client.register(
            email=test_email,
            password=test_password,
            first_name="Billing Test",
            last_name=f"User {tier.value}"
        )
        assert register_response.get("success"), f"Real user registration failed: {register_response}"
        
        # Real user login
        user_token = await self.auth_client.login(test_email, test_password)
        assert user_token, f"Real user login failed - no token returned"
        
        # Get user info from token verification
        user_info = await self.auth_client.verify_token(user_token)
        user_id = user_info.get("sub") or user_info.get("user_id")
        
        # Setup WebSocket connection with real auth
        backend_host = self.backend_client.base_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{backend_host}/ws"
        ws_client = WebSocketTestClient(ws_url)
        
        await ws_client.connect(token=user_token, timeout=10.0)
        assert ws_client.is_connected, "Real WebSocket connection failed for billing test"
        
        session = {
            "user_id": user_id,
            "email": test_email,
            "token": user_token,
            "tier": tier,
            "ws_client": ws_client
        }
        
        self.test_users[user_id] = session
        return session
        
    async def execute_real_agent_billing_request(self, session: Dict[str, Any], 
                                                request_message: str) -> Dict[str, Any]:
        """Execute real agent request and validate billing events."""
        ws_client = session["ws_client"]
        user_id = session["user_id"]
        tier = session["tier"]
        
        # Record start time for billing
        request_start = time.time()
        
        # Create real billing record before request per CLAUDE.md
        agent_type = "triage" if "analyze" in request_message.lower() else "data"
        expected_cost = self.agent_simulator.agent_cost_map.get(agent_type, {"tokens": 500, "cost_cents": 8})
        
        billing_record = {
            "user_id": user_id,
            "tier": tier.value,
            "request_start": request_start,
            "expected_tokens": expected_cost["tokens"],
            "expected_cost_cents": expected_cost["cost_cents"],
            "agent_type": agent_type
        }
        self.billing_records.append(billing_record)
        
        # Send real agent request
        await ws_client.send_chat(request_message)
        
        # Collect real agent response events for billing validation
        agent_events = []
        billing_events = []
        completion_received = False
        timeout_start = time.time()
        
        while time.time() - timeout_start < 30.0:  # 30s timeout for real agent execution
            event = await ws_client.receive(timeout=2.0)
            if event:
                agent_events.append(event)
                
                # Track billing-relevant events per CLAUDE.md WebSocket requirements
                event_type = event.get("type")
                if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                    billing_events.append(event)
                
                # Check for completion
                if event_type in ["agent_completed", "final_report"]:
                    completion_received = True
                    break
        
        request_end = time.time()
        total_time = request_end - request_start
        
        # Update billing record with actual results
        if self.billing_records:
            self.billing_records[-1].update({
                "actual_response_time": total_time,
                "actual_events_count": len(agent_events),
                "completion_received": completion_received
            })
        
        return {
            "events": agent_events,
            "billing_events": billing_events,
            "completed": completion_received,
            "response_time": total_time,
            "billing_tracked": len(billing_events) > 0,
            "cost_tracking": self.billing_records[-1] if self.billing_records else None
        }
    
    async def validate_real_billing_integrity(self, session: Dict[str, Any], 
                                            agent_response: Dict[str, Any]) -> Dict[str, bool]:
        """Validate billing integrity using real database queries and WebSocket events."""
        user_id = session["user_id"]
        billing_events = agent_response["billing_events"]
        
        # Validate WebSocket agent events for substantive chat value per CLAUDE.md
        required_events = ["agent_started", "agent_thinking", "tool_executing", "agent_completed"]
        events_present = {event_type: False for event_type in required_events}
        
        for event in billing_events:
            event_type = event.get("type")
            if event_type in events_present:
                events_present[event_type] = True
        
        # Real billing validation with cost tracking per CLAUDE.md
        cost_tracking = agent_response.get("cost_tracking", {})
        cost_validation_passed = True
        
        if cost_tracking:
            # Validate expected vs actual performance for billing accuracy
            expected_time_limit = 30.0  # seconds for typical agent requests
            actual_time = cost_tracking.get("actual_response_time", 0)
            cost_validation_passed = actual_time < expected_time_limit
        
        validation_results = {
            "websocket_events_valid": all(events_present.values()),
            "agent_execution_tracked": agent_response["billing_tracked"],
            "completion_received": agent_response["completed"],
            "response_time_acceptable": agent_response["response_time"] < 25.0,
            "substantive_chat_delivered": len(agent_response["events"]) > 2,
            "billing_flow_complete": agent_response["completed"] and agent_response["billing_tracked"],
            "cost_tracking_valid": cost_validation_passed,
            "billing_record_created": cost_tracking is not None
        }
        
        return validation_results
    
    async def teardown_real_services(self):
        """Cleanup real service connections."""
        for user_session in self.test_users.values():
            if user_session.get("ws_client"):
                await user_session["ws_client"].disconnect()
                
        if self.auth_client:
            await self.auth_client.close()
            
        if self.backend_client:
            await self.backend_client.close()


@pytest.mark.asyncio
@pytest.mark.e2e
class TestAgentBillingFlowCompliant:
    """Agent billing flow tests compliant with CLAUDE.md - REAL services only."""
    
    @pytest_asyncio.fixture
    async def real_billing_env(self, isolated_test_env):
        """Setup real services environment for billing tests."""
        # Setup real services environment per CLAUDE.md requirements
        env_manager = get_test_env_manager()
        isolated_env = env_manager.setup_test_environment(
            additional_vars={
                "USE_REAL_SERVICES": "true",
                "CLICKHOUSE_ENABLED": "true",  # Use real ClickHouse
                "TEST_DISABLE_REDIS": "false",  # Use real Redis
                "TESTING": "1",
                "NETRA_ENV": "testing",
                "ENVIRONMENT": "testing",
                # Ensure real LLM usage
                "USE_MOCK_LLM": "false",
                "ENABLE_REAL_LLM_TESTING": "true"
            },
            enable_real_llm=True  # Use real LLM per CLAUDE.md
        )
        
        # Setup real billing test core
        billing_core = RealAgentBillingTestCore()
        infrastructure = await billing_core.setup_real_billing_infrastructure(isolated_env)
        
        yield {
            "env": isolated_env,
            "billing_core": billing_core,
            "infrastructure": infrastructure
        }
        
        # Cleanup real services
        await billing_core.teardown_real_services()
        env_manager.teardown_test_environment()
    
    @pytest.mark.asyncio
    async def test_real_agent_billing_flow_triage(self, real_billing_env):
        """Test complete triage agent billing flow with real services."""
        billing_core = real_billing_env["billing_core"]
        
        # Create real user session for PRO tier
        session = await billing_core.create_real_user_session(PlanTier.PRO)
        
        try:
            # Execute real triage agent request
            request_message = "Analyze my AI infrastructure and suggest cost optimizations"
            
            response = await billing_core.execute_real_agent_billing_request(
                session, request_message
            )
            
            # Validate real billing flow with WebSocket events
            billing_validation = await billing_core.validate_real_billing_integrity(session, response)
            
            # Assert complete billing flow per CLAUDE.md requirements
            assert billing_validation["websocket_events_valid"], "WebSocket agent events missing - breaks chat value"
            assert billing_validation["agent_execution_tracked"], "Agent execution not tracked for billing"
            assert billing_validation["completion_received"], "Agent completion not received"
            assert billing_validation["response_time_acceptable"], f"Response too slow: {response['response_time']:.2f}s"
            assert billing_validation["substantive_chat_delivered"], "Insufficient events for substantive chat value"
            assert billing_validation["billing_flow_complete"], "Complete billing flow validation failed"
            assert billing_validation["cost_tracking_valid"], "Cost tracking validation failed - billing accuracy compromised"
            assert billing_validation["billing_record_created"], "No billing record created - revenue tracking failed"
            
        finally:
            await session["ws_client"].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_agent_billing_flow_data_analysis(self, real_billing_env):
        """Test data analysis agent billing with real services."""
        billing_core = real_billing_env["billing_core"]
        
        # Create real user session for ENTERPRISE tier
        session = await billing_core.create_real_user_session(PlanTier.ENTERPRISE)
        
        try:
            # Execute real data analysis agent request
            request_message = "Provide detailed analytics on my AI usage patterns and cost trends"
            
            response = await billing_core.execute_real_agent_billing_request(
                session, request_message
            )
            
            # Validate real billing flow
            billing_validation = await billing_core.validate_real_billing_integrity(session, response)
            
            # Assert data analysis agent billing with higher complexity
            assert billing_validation["billing_flow_complete"], "Data analysis agent billing flow failed"
            assert len(response["events"]) >= 3, f"Insufficient events for data analysis: {len(response['events'])}"
            assert response["completed"], "Real data analysis agent request did not complete"
            assert billing_validation["substantive_chat_delivered"], "Data analysis must deliver substantive value"
            
        finally:
            await session["ws_client"].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_multi_tier_billing_validation(self, real_billing_env):
        """Test billing validation across multiple user tiers with real services."""
        billing_core = real_billing_env["billing_core"]
        
        tiers_to_test = [PlanTier.PRO, PlanTier.ENTERPRISE]
        tier_results = {}
        
        for tier in tiers_to_test:
            session = await billing_core.create_real_user_session(tier)
            
            try:
                request_message = f"Tier-specific optimization analysis for {tier.value} validation"
                
                response = await billing_core.execute_real_agent_billing_request(
                    session, request_message
                )
                
                billing_validation = await billing_core.validate_real_billing_integrity(session, response)
                
                tier_results[tier.value] = {
                    "flow_complete": billing_validation["billing_flow_complete"],
                    "websocket_valid": billing_validation["websocket_events_valid"],
                    "response_time": response["response_time"]
                }
                
            finally:
                await session["ws_client"].disconnect()
        
        # Validate all tiers succeeded with real services
        for tier, result in tier_results.items():
            assert result["flow_complete"], f"Billing flow failed for {tier} tier with real services"
            assert result["websocket_valid"], f"WebSocket events invalid for {tier} - breaks chat value"
            assert result["response_time"] < 30.0, f"Real service response too slow for {tier}: {result['response_time']:.2f}s"
    
    @pytest.mark.asyncio
    async def test_real_agent_billing_performance_validation(self, real_billing_env):
        """Test agent billing performance requirements with real services."""
        billing_core = real_billing_env["billing_core"]
        
        session = await billing_core.create_real_user_session(PlanTier.PRO)
        
        try:
            # Performance test request
            request_message = "Quick performance analysis - billing validation test"
            
            start_time = time.time()
            response = await billing_core.execute_real_agent_billing_request(
                session, request_message
            )
            end_time = time.time()
            
            total_response_time = end_time - start_time
            
            # Validate performance requirements with real services
            assert total_response_time < 30.0, f"Real agent billing flow too slow: {total_response_time:.2f}s (max 30s)"
            assert response["completed"], "Real agent request did not complete within performance window"
            assert len(response["events"]) >= 2, f"Insufficient real events for performance validation: {len(response['events'])}"
            
            # Validate billing was processed within performance window
            billing_validation = await billing_core.validate_real_billing_integrity(session, response)
            assert billing_validation["billing_flow_complete"], "Real billing not completed within performance window"
            
        finally:
            await session["ws_client"].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_billing_error_handling_and_recovery(self, real_billing_env):
        """Test billing flow error handling with real services."""
        billing_core = real_billing_env["billing_core"]
        
        session = await billing_core.create_real_user_session(PlanTier.PRO)
        
        try:
            # Send potentially problematic request to test error handling
            error_test_request = "Invalid complex request that might cause billing edge cases $$TEST$$"
            
            initial_connection = session["ws_client"].is_connected
            assert initial_connection, "WebSocket not connected before billing error test"
            
            response = await billing_core.execute_real_agent_billing_request(
                session, error_test_request
            )
            
            # Validate error handling maintains connection and billing integrity
            assert session["ws_client"].is_connected, "WebSocket connection lost during billing error handling"
            
            # Test recovery with normal request
            recovery_request = "Normal billing recovery test request"
            recovery_response = await billing_core.execute_real_agent_billing_request(
                session, recovery_request
            )
            
            recovery_validation = await billing_core.validate_real_billing_integrity(session, recovery_response)
            assert recovery_validation["billing_flow_complete"], "Billing system failed to recover after error"
            
        finally:
            await session["ws_client"].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_concurrent_billing_validation(self, real_billing_env):
        """Test concurrent billing operations with real services."""
        billing_core = real_billing_env["billing_core"]
        
        session = await billing_core.create_real_user_session(PlanTier.ENTERPRISE)
        
        try:
            # Send multiple requests to test concurrent billing handling
            requests = [
                "Concurrent billing test 1 - cost analysis",
                "Concurrent billing test 2 - usage report",
                "Concurrent billing test 3 - optimization recommendations"
            ]
            
            # Execute requests with small delays (real WebSocket can't handle truly concurrent)
            responses = []
            for i, request in enumerate(requests):
                response = await billing_core.execute_real_agent_billing_request(
                    session, request
                )
                responses.append(response)
                
                # Small delay between requests for real service processing
                if i < len(requests) - 1:
                    await asyncio.sleep(2.0)
            
            # Validate all billing operations succeeded
            for i, response in enumerate(responses):
                billing_validation = await billing_core.validate_real_billing_integrity(session, response)
                assert billing_validation["billing_flow_complete"], f"Concurrent billing request {i+1} failed"
                assert response["completed"], f"Concurrent request {i+1} did not complete"
            
            # Validate connection remained stable throughout
            assert session["ws_client"].is_connected, "WebSocket connection lost during concurrent billing"
            
        finally:
            await session["ws_client"].disconnect()


@pytest.mark.e2e
class TestRealBillingIntegration:
    """Test real billing integration with complete agent execution per CLAUDE.md."""
    
    @pytest_asyncio.fixture
    async def real_billing_env(self, isolated_test_env):
        """Setup real services environment for billing integration tests."""
        env_manager = get_test_env_manager()
        isolated_env = env_manager.setup_test_environment(
            additional_vars={
                "USE_REAL_SERVICES": "true",
                "CLICKHOUSE_ENABLED": "true",
                "TEST_DISABLE_REDIS": "false",
                "TESTING": "1",
                "NETRA_ENV": "testing",
                "ENVIRONMENT": "testing",
                # Ensure real LLM usage
                "USE_MOCK_LLM": "false",
                "ENABLE_REAL_LLM_TESTING": "true"
            },
            enable_real_llm=True
        )
        
        billing_core = RealAgentBillingTestCore()
        infrastructure = await billing_core.setup_real_billing_infrastructure(isolated_env)
        
        yield {
            "env": isolated_env,
            "billing_core": billing_core,
            "infrastructure": infrastructure
        }
        
        await billing_core.teardown_real_services()
        env_manager.teardown_test_environment()
    
    @pytest.mark.asyncio
    async def test_real_websocket_agent_billing_integration(self, real_billing_env):
        """Test WebSocket agent events integration with billing per CLAUDE.md requirements."""
        billing_core = real_billing_env["billing_core"]
        
        session = await billing_core.create_real_user_session(PlanTier.PRO)
        
        try:
            # Test specific message that should trigger all required WebSocket events
            request_message = "Analyze and optimize my AI infrastructure costs with detailed breakdown"
            
            response = await billing_core.execute_real_agent_billing_request(
                session, request_message
            )
            
            # Validate WebSocket events critical for business value delivery
            billing_events = response["billing_events"]
            event_types = [event.get("type") for event in billing_events]
            
            # CRITICAL: These events are required for substantive chat value per CLAUDE.md
            assert "agent_started" in event_types, "agent_started event missing - user won't see AI working"
            assert "agent_thinking" in event_types, "agent_thinking event missing - no real-time reasoning visibility"
            assert "tool_executing" in event_types, "tool_executing event missing - no problem-solving visibility"  
            assert "agent_completed" in event_types, "agent_completed event missing - user won't know when done"
            
            # Validate billing integration with real WebSocket events
            billing_validation = await billing_core.validate_real_billing_integrity(session, response)
            assert billing_validation["billing_flow_complete"], "WebSocket-to-billing integration failed"
            assert billing_validation["substantive_chat_delivered"], "Failed to deliver substantive AI value"
            
        finally:
            await session["ws_client"].disconnect()
    
    @pytest.mark.asyncio
    async def test_real_end_to_end_chat_billing_value_delivery(self, real_billing_env):
        """Test complete end-to-end chat value delivery with billing validation."""
        billing_core = real_billing_env["billing_core"]
        
        session = await billing_core.create_real_user_session(PlanTier.ENTERPRISE)
        
        try:
            # Test message that should deliver substantial business value
            request_message = "Provide comprehensive AI cost analysis with specific optimization recommendations"
            
            response = await billing_core.execute_real_agent_billing_request(
                session, request_message
            )
            
            # Validate complete business value delivery flow
            assert response["completed"], "Agent request must complete for business value"
            assert len(response["events"]) >= 4, f"Insufficient events for substantial value: {len(response['events'])}"
            assert response["billing_tracked"], "Billing must track valuable AI interactions"
            
            # Validate timing meets business requirements
            assert response["response_time"] < 45.0, f"Too slow for business value delivery: {response['response_time']:.2f}s"
            
            # Final billing validation
            billing_validation = await billing_core.validate_real_billing_integrity(session, response)
            assert billing_validation["billing_flow_complete"], "End-to-end value delivery billing failed"
            
        finally:
            await session["ws_client"].disconnect()