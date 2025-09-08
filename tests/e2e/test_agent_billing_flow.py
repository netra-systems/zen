"""E2E Agent Billing Flow Test - Critical Usage-Based Billing Validation

CRITICAL E2E test for complete agent request → processing → billing flow.
Validates usage-based billing accuracy for all paid tiers.

Business Value Justification (BVJ):
1. Segment: ALL paid tiers (revenue tracking critical)
2. Business Goal: Ensure accurate usage-based billing for agent operations
3. Value Impact: Protects revenue integrity - billing errors = customer trust loss
4. Revenue Impact: Each billing error costs $100-1000/month per customer

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper imports)
- Function size: <8 lines each
- REAL services (Auth, Backend, WebSocket, LLM) per CLAUDE.md - NO MOCKS
- Performance validation for real-world conditions
- Multiple agent types with different cost structures

TECHNICAL DETAILS:
- Uses real WebSocket infrastructure from existing E2E patterns
- REAL LLM API calls per CLAUDE.md - NO MOCKS ALLOWED
- Validates ClickHouse usage tracking and billing record creation
- Tests Triage, Data, and Admin agent types with different pricing
- Includes performance assertions and billing calculation validation
"""

import asyncio
import time
from typing import Dict, Any
import pytest
import pytest_asyncio
from shared.isolated_environment import IsolatedEnvironment

# CLAUDE.md: E2E tests MUST use SSOT authentication patterns
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from test_framework.ssot.base_test_case import SSotBaseTestCase

from tests.e2e.agent_billing_test_helpers import (
    AgentBillingTestCore, 
    AgentRequestSimulator, 
    BillingFlowValidator, 
    AgentBillingTestUtils
)
from netra_backend.app.schemas.user_plan import PlanTier
from shared.isolated_environment import get_env
from test_framework.real_services import RealServicesManager
from test_framework.llm_config_manager import configure_llm_testing, LLMTestMode

@pytest.mark.asyncio
@pytest.mark.e2e
class TestAgentBillingFlow(SSotBaseTestCase):
    """Test #2: Agent Request → Processing → Response → Billing Record Flow.
    
    CLAUDE.md Compliance:
    - Uses SSOT authentication patterns (E2EAuthHelper)
    - NO mocks - real services only
    - Proper error handling - tests MUST raise errors
    - WebSocket authentication with E2E detection headers
    - Multi-user isolation testing
    """
    
    @pytest_asyncio.fixture
    async def auth_helper(self):
        """SSOT authentication helper for all tests."""
        return E2EAuthHelper(environment=self.get_test_environment())
        
    @pytest_asyncio.fixture
    async def websocket_auth_helper(self):
        """SSOT WebSocket authentication helper."""
        return E2EWebSocketAuthHelper(environment=self.get_test_environment())
    
    @pytest_asyncio.fixture
    async def test_core(self, auth_helper, websocket_auth_helper):
        """Initialize billing test core with isolated environment and SSOT patterns."""
        # Setup REAL services environment per CLAUDE.md requirements - NO MOCKS
        # Use proper environment management through shared.isolated_environment
        env = get_env()
        env.set("USE_REAL_SERVICES", "true", "e2e_test")
        env.set("CLICKHOUSE_ENABLED", "true", "e2e_test")
        env.set("TEST_DISABLE_REDIS", "false", "e2e_test")
        env.set("REAL_DATABASE_TESTING", "true", "e2e_test")
        env.set("LLM_TEST_MODE", "REAL", "e2e_test")  # CLAUDE.md: Use REAL LLM for e2e tests
        
        # Configure real LLM testing per CLAUDE.md standards
        configure_llm_testing(mode=LLMTestMode.REAL)
        
        # Create test core with SSOT auth integration
        core = AgentBillingTestCore()
        core.auth_helper = auth_helper
        core.websocket_auth_helper = websocket_auth_helper
        
        # CLAUDE.md: Execution time tracking to prevent 0.00s completion
        core.test_start_time = time.time()
        
        await core.setup_test_environment()
        yield core
        
        # CLAUDE.md: Validate execution time - E2E tests with 0.00s = HARD FAILURE
        execution_time = time.time() - core.test_start_time
        if execution_time < 0.1:  # Less than 100ms indicates test didn't really run
            raise AssertionError(f"E2E test completed in {execution_time:.3f}s - this indicates test was not executed properly (mocks/bypasses)")
        
        await core.teardown_test_environment()
        
        # Cleanup environment variables
        env = get_env()
        env.delete("USE_REAL_SERVICES", "e2e_test")
        env.delete("CLICKHOUSE_ENABLED", "e2e_test")
        env.delete("TEST_DISABLE_REDIS", "e2e_test")
        env.delete("REAL_DATABASE_TESTING", "e2e_test")
        env.delete("LLM_TEST_MODE", "e2e_test")
    
    @pytest.fixture
    def request_simulator(self):
        """Initialize agent request simulator."""
        return AgentRequestSimulator()
    
    @pytest.fixture
    def billing_validator(self):
        """Initialize billing flow validator."""
        # Create a new billing helper for validation
        from tests.e2e.clickhouse_billing_helper import ClickHouseBillingHelper
        billing_helper = ClickHouseBillingHelper()
        return BillingFlowValidator(billing_helper)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_agent_billing_flow_triage(self, test_core, auth_helper, websocket_auth_helper, 
                                                    request_simulator, billing_validator):
        """Test complete billing flow for triage agent with SSOT authentication."""
        # CLAUDE.md: E2E tests MUST authenticate - create real authenticated user
        token, user_data = await create_authenticated_user(
            environment=self.get_test_environment(),
            permissions=["read", "write", "billing"]
        )
        
        # CLAUDE.md: Use SSOT WebSocket authentication
        websocket_client = await websocket_auth_helper.connect_authenticated_websocket()
        
        test_start_time = time.time()
        
        # CLAUDE.md: NO exception swallowing - tests must raise errors
        # Create and send triage request
        request = request_simulator.create_triage_request(user_data["id"])
        
        # Test with REAL LLM per CLAUDE.md requirements - NO MOCKS
        response = await self._execute_real_agent_request(
            websocket_client, request, token, user_data
        )
        
        # Validate complete billing flow
        validation = await billing_validator.validate_agent_response_flow(
            {"user_data": user_data, "tier": PlanTier.PRO, "token": token}, 
            request, response
        )
        
        # CLAUDE.md: Tests must raise errors - NO try/except hiding failures
        self._assert_billing_flow_success(validation)
        
        # CLAUDE.md: Validate execution time to prevent 0.00s fake tests
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"Test completed too quickly ({execution_time:.3f}s) - indicates mocking/bypassing"
        
        await websocket_client.close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_agent_types_billing_accuracy(self, test_core, auth_helper, websocket_auth_helper,
                                                       request_simulator, billing_validator):
        """Test billing accuracy across different agent types with multi-user isolation."""
        # CLAUDE.md: Multi-user isolation testing - create separate users for each agent type
        test_users = []
        websocket_clients = []
        test_start_time = time.time()
        
        # CLAUDE.md: NO exception swallowing - tests must raise errors
        billing_results = {}
        
        # Test each agent type with separate authenticated users for isolation
        for agent_type in request_simulator.get_agent_types():
            # Create isolated authenticated user for this agent type
            token, user_data = await create_authenticated_user(
                environment=self.get_test_environment(),
                permissions=["read", "write", "billing", f"agent_{agent_type}"]
            )
            test_users.append((token, user_data))
            
            # Create authenticated WebSocket connection
            ws_client = await websocket_auth_helper.connect_authenticated_websocket()
            websocket_clients.append(ws_client)
            
            # Create request for this agent type
            request = getattr(request_simulator, f"create_{agent_type}_request")(user_data["id"])
            
            # Execute with REAL services - NO MOCKS
            response = await self._execute_real_agent_request(
                ws_client, request, token, user_data
            )
            
            validation = await billing_validator.validate_agent_response_flow(
                {"user_data": user_data, "tier": PlanTier.ENTERPRISE, "token": token},
                request, response
            )
            
            billing_results[agent_type] = validation
        
        # Clean up WebSocket connections
        for ws_client in websocket_clients:
            await ws_client.close()
        
        # CLAUDE.md: Tests must raise errors - validate all agent types
        self._assert_all_agent_types_success(billing_results)
        
        # CLAUDE.md: Validate execution time to prevent fake tests
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.5, f"Multi-agent test completed too quickly ({execution_time:.3f}s) - indicates mocking"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_billing_performance_requirements(self, test_core, request_simulator,
                                                  billing_validator):
        """Test that billing operations meet performance requirements."""
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            # Test high-cost request for performance validation
            request = request_simulator.create_high_cost_request(session["user_data"]["id"])
            
            # Measure total response time
            start_time = time.time()
            response = await self._execute_real_agent_request(session, request)
            response_time = time.time() - start_time
            
            # Validate performance requirement
            assert response_time < 5.0, f"Response took {response_time:.2f}s, exceeding 5s limit"
            
            # Validate billing still accurate under performance pressure
            validation = await billing_validator.validate_agent_response_flow(
                session, request, response
            )
            self._assert_billing_flow_success(validation)
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_billing_error_handling(self, test_core, request_simulator):
        """Test billing flow error handling and recovery."""
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            request = request_simulator.create_triage_request(session["user_data"]["id"])
            
            # Test billing error handling directly without WebSocket dependency
            billing_helper = test_core.billing_helper
            
            # Test with invalid billing data to trigger validation errors
            invalid_payment_data = {
                "id": "invalid_billing_test",
                "amount_cents": -100  # Negative amount should fail validation
            }
            user_data = session["user_data"]
            tier = session["tier"]
            
            # Attempt billing record creation with invalid data
            try:
                await billing_helper.create_and_validate_billing_record(
                    invalid_payment_data, user_data, tier
                )
                assert False, "Invalid billing data should raise exception"
            except ValueError:
                # Expected error handling
                pass
            
            # Test recovery with valid data
            valid_payment_data = {
                "id": "recovery_billing_test", 
                "amount_cents": 1500
            }
            
            recovery_result = await billing_helper.create_and_validate_billing_record(
                valid_payment_data, user_data, tier
            )
            
            # Validate recovery
            assert recovery_result["clickhouse_inserted"], "Recovery billing record must be created"
            assert recovery_result["validation"]["valid"], "Recovery validation must succeed"
            
        finally:
            if hasattr(session["client"], "close"):
                await session["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_tier_specific_billing_validation(self, test_core, request_simulator,
                                                  billing_validator):
        """Test billing validation for different user tiers."""
        tiers_to_test = [PlanTier.PRO, PlanTier.ENTERPRISE, PlanTier.DEVELOPER]
        
        for tier in tiers_to_test:
            session = await test_core.establish_authenticated_user_session(tier)
            
            try:
                request = request_simulator.create_data_request(session["user_data"]["id"])
                response = await self._execute_real_agent_request(session, request)
                
                validation = await billing_validator.validate_agent_response_flow(
                    session, request, response
                )
                
                # Validate tier-specific billing
                assert validation["flow_complete"], f"Billing flow failed for {tier.value} tier"
                assert validation["cost_accurate"], f"Cost calculation incorrect for {tier.value}"
                
            finally:
                await session["client"].close()
    
    async def _execute_real_agent_request(self, websocket_client, request: Dict, 
                                        token: str, user_data: Dict) -> Dict[str, Any]:
        """Execute agent request with REAL LLM per CLAUDE.md requirements - NO MOCKS."""
        # CLAUDE.md: Real Everything (LLM, Services) E2E > E2E > Integration > Unit
        # Add authentication context to request
        authenticated_request = {
            **request,
            "auth_token": token,
            "user_context": user_data,
            "test_environment": self.get_test_environment()
        }
        
        # Send actual agent request through real WebSocket to real backend with real LLM
        response = await AgentBillingTestUtils.send_agent_request(
            websocket_client, authenticated_request
        )
        
        # CLAUDE.md: Validate response is real (not mocked)
        if not response or response.get("mocked", False):
            raise AssertionError("Response appears to be mocked - E2E tests must use real services")
        
        return response
    
    def _assert_billing_flow_success(self, validation: Dict[str, Any]) -> None:
        """Assert billing flow validation success."""
        assert validation["response_valid"], "Agent response structure invalid"
        assert validation["usage_tracked"], "Usage not tracked in ClickHouse"
        assert validation["billing_recorded"], "Billing record not created"
        assert validation["cost_accurate"], "Billing cost calculation incorrect"
        assert validation["flow_complete"], "Complete billing flow validation failed"
    
    def _assert_all_agent_types_success(self, billing_results: Dict[str, Any]) -> None:
        """Assert billing success for all agent types."""
        for agent_type, result in billing_results.items():
            assert result["flow_complete"], f"{agent_type} agent billing flow failed"
            assert result["cost_accurate"], f"{agent_type} agent cost calculation incorrect"

@pytest.mark.asyncio 
@pytest.mark.e2e
class TestAgentBillingPerformance(SSotBaseTestCase):
    """Performance validation for agent billing operations with SSOT patterns."""
    
    @pytest_asyncio.fixture
    async def auth_helper(self):
        """SSOT authentication helper for performance tests."""
        return E2EAuthHelper(environment=self.get_test_environment())
        
    @pytest_asyncio.fixture
    async def websocket_auth_helper(self):
        """SSOT WebSocket authentication helper for performance tests."""
        return E2EWebSocketAuthHelper(environment=self.get_test_environment())
    
    @pytest_asyncio.fixture
    async def test_core(self, auth_helper, websocket_auth_helper):
        """Initialize performance test core with REAL services and SSOT patterns."""
        # Setup REAL services environment - NO MOCKS
        # Use proper environment management through shared.isolated_environment
        env = get_env()
        env.set("USE_REAL_SERVICES", "true", "e2e_perf_test")
        env.set("CLICKHOUSE_ENABLED", "true", "e2e_perf_test")
        env.set("TEST_DISABLE_REDIS", "false", "e2e_perf_test")
        env.set("REAL_DATABASE_TESTING", "true", "e2e_perf_test")
        env.set("LLM_TEST_MODE", "REAL", "e2e_perf_test")  # CLAUDE.md: Use REAL LLM for e2e tests
        
        # Configure real LLM testing per CLAUDE.md standards
        configure_llm_testing(mode=LLMTestMode.REAL)
        
        core = AgentBillingTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
        
        # Cleanup environment variables
        env = get_env()
        env.delete("USE_REAL_SERVICES", "e2e_perf_test")
        env.delete("CLICKHOUSE_ENABLED", "e2e_perf_test")
        env.delete("TEST_DISABLE_REDIS", "e2e_perf_test")
        env.delete("REAL_DATABASE_TESTING", "e2e_perf_test")
        env.delete("LLM_TEST_MODE", "e2e_perf_test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_billing_record_creation_performance(self, test_core):
        """Test that billing record creation meets performance requirements."""
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            # Measure billing record creation time
            start_time = time.time()
            
            payment_data = {"id": "test_payment", "amount_cents": 2500}
            user_data = session["user_data"]
            
            result = await test_core.billing_helper.create_and_validate_billing_record(
                payment_data, user_data, session["tier"]
            )
            
            creation_time = time.time() - start_time
            
            # Validate performance requirement
            assert creation_time < 1.0, f"Billing creation took {creation_time:.2f}s, exceeding 1s"
            assert result["clickhouse_inserted"], "Billing record not inserted"
            assert result["validation"]["valid"], "Billing record validation failed"
        
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_concurrent_billing_operations(self, test_core):
        """Test billing system under concurrent load."""
        sessions = []
        
        try:
            # Create multiple concurrent sessions
            for _ in range(3):
                session = await test_core.establish_authenticated_user_session(PlanTier.ENTERPRISE)
                sessions.append(session)
            
            # Execute concurrent billing operations
            start_time = time.time()
            
            tasks = []
            for session in sessions:
                payment_data = {"id": f"concurrent_test_{session['user_data']['id']}", "amount_cents": 1500}
                task = test_core.billing_helper.create_and_validate_billing_record(
                    payment_data, session["user_data"], session["tier"]
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Validate concurrent performance
            assert total_time < 3.0, f"Concurrent operations took {total_time:.2f}s, exceeding 3s"
            assert all(result["clickhouse_inserted"] for result in results), "Some billing records failed"
            
        finally:
            for session in sessions:
                await session["client"].close()
