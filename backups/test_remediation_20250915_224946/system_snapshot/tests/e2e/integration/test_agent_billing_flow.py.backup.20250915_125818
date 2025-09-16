"""E2E Agent Billing Flow Test - Critical Usage-Based Billing Validation

CRITICAL E2E test for complete agent request  ->  processing  ->  billing flow.
Validates usage-based billing accuracy for all paid tiers.

Business Value Justification (BVJ):
1. Segment: ALL paid tiers (revenue tracking critical)
2. Business Goal: Ensure accurate usage-based billing for agent operations
3. Value Impact: Protects revenue integrity - billing errors = customer trust loss
4. Revenue Impact: Each billing error costs $100-1000/month per customer

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper imports)
- Function size: <8 lines each
- Real services (Auth, Backend, WebSocket) with mocked LLM API only
- <5 seconds per test execution for performance validation
- Multiple agent types with different cost structures

TECHNICAL DETAILS:
- Uses real WebSocket infrastructure from existing E2E patterns
- Mocks only LLM API calls (OpenAI/Anthropic) to ensure deterministic costs
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

from tests.e2e.agent_billing_test_helpers import (
    AgentBillingTestCore, AgentRequestSimulator, BillingFlowValidator, AgentBillingTestUtils,
    AgentBillingTestCore,
    AgentRequestSimulator,
    BillingFlowValidator,
    AgentBillingTestUtils
)
from netra_backend.app.schemas.user_plan import PlanTier
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

@pytest.mark.asyncio
@pytest.mark.e2e
class TestAgentBillingFlow:
    """Test #2: Agent Request  ->  Processing  ->  Response  ->  Billing Record Flow."""
    
    @pytest_asyncio.fixture
    @pytest.mark.e2e
    async def test_core(self):
        """Initialize billing test core."""
        core = AgentBillingTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
    
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
    async def test_complete_agent_billing_flow_triage(self, test_core, request_simulator,
                                                    billing_validator):
        """Test complete billing flow for triage agent."""
        # Setup authenticated session
        session = await test_core.establish_authenticated_user_session(PlanTier.PRO)
        
        try:
            # Create and send triage request
            request = request_simulator.create_triage_request(session["user_data"]["id"])
            
            # Test with mocked LLM for deterministic costs
            response = await self._execute_agent_request_with_mock(session, request)
            
            # Validate complete billing flow
            validation = await billing_validator.validate_agent_response_flow(
                session, request, response
            )
            
            # Assert all billing flow components
            self._assert_billing_flow_success(validation)
        
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multiple_agent_types_billing_accuracy(self, test_core, request_simulator,
                                                       billing_validator):
        """Test billing accuracy across different agent types."""
        session = await test_core.establish_authenticated_user_session(PlanTier.ENTERPRISE)
        
        try:
            billing_results = {}
            
            # Test each agent type
            for agent_type in request_simulator.get_agent_types():
                request = getattr(request_simulator, f"create_{agent_type}_request")(
                    session["user_data"]["id"]
                )
                
                response = await self._execute_agent_request_with_mock(session, request)
                validation = await billing_validator.validate_agent_response_flow(
                    session, request, response
                )
                
                billing_results[agent_type] = validation
            
            # Validate all agent types processed correctly
            self._assert_all_agent_types_success(billing_results)
        
        finally:
            await session["client"].close()
    
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
            response = await self._execute_agent_request_with_mock(session, request)
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
            
            # Test with simulated billing failure
            # Mock: ClickHouse database isolation for fast testing without external database dependency
            with patch('tests.e2e.clickhouse_billing_helper.MockClickHouseBillingClient.insert_billing_record') as mock_billing:
                mock_billing.side_effect = Exception("Billing service unavailable")
                
                # Should handle billing errors gracefully
                response = await self._execute_agent_request_with_mock(session, request)
                
                # Response should still be delivered
                assert response.get("status") in ["success", "error"], "Agent should handle billing errors"
                
        finally:
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
                response = await self._execute_agent_request_with_mock(session, request)
                
                validation = await billing_validator.validate_agent_response_flow(
                    session, request, response
                )
                
                # Validate tier-specific billing
                assert validation["flow_complete"], f"Billing flow failed for {tier.value} tier"
                assert validation["cost_accurate"], f"Cost calculation incorrect for {tier.value}"
                
            finally:
                await session["client"].close()
    
    async def _execute_agent_request_with_mock(self, session: Dict, request: Dict) -> Dict[str, Any]:
        """Execute agent request with mocked LLM response."""
        expected_tokens = request["expected_cost"]["tokens"]
        
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        with patch('netra_backend.app.llm.llm_manager.LLMManager.ask_llm_full') as mock_llm:
            mock_llm.return_value = AgentBillingTestUtils.create_mock_llm_response(expected_tokens)
            
            response = await AgentBillingTestUtils.send_agent_request(
                session["client"], request
            )
            
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
class TestAgentBillingPerformance:
    """Performance validation for agent billing operations."""
    
    @pytest_asyncio.fixture
    @pytest.mark.e2e
    async def test_core(self):
        """Initialize performance test core."""
        core = AgentBillingTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
    
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
