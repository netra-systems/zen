"""E2E Test #6: Cost Tracking Accuracy E2E - Complete AI Operation Cost Validation

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: ALL paid tiers (revenue-critical cost accuracy)
2. Business Goal: Protect $40K+ MRR through accurate billing and cost tracking
3. Value Impact: Ensures 100% cost accuracy from AI operations → billing records
4. Revenue Impact: Each billing discrepancy = customer trust loss = $1K-$10K+ churn

CRITICAL E2E test for complete cost tracking flow:
Frontend → AI Operations → Backend Cost Calculation → Database Billing → Frontend Display

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (modular design with helper imports)
- Function size: <8 lines each
- Real services integration with mock LLM costs only for deterministic testing
- Performance: <5 seconds per test, <30 seconds total
- 100% cost accuracy validation across all operation types

TECHNICAL COVERAGE:
- User performs AI operations (Frontend WebSocket)
- Track token usage with real cost calculator service
- Calculate costs using production cost calculation logic
- Display costs in frontend with real-time updates
- Verify billing accuracy through ClickHouse database validation
- Test different operation types and cost tiers
"""

import asyncio
import time
from typing import Dict, Any
from decimal import Decimal
from unittest.mock import patch, AsyncMock
import pytest
import pytest_asyncio

from tests.e2e.integration.cost_tracking_helpers import (
    CostTrackingTestCore, AIOperationSimulator, CostCalculationValidator, BillingAccuracyValidator, FrontendCostDisplayValidator,
    CostTrackingTestCore,
    AIOperationSimulator,
    CostCalculationValidator,
    BillingAccuracyValidator,
    FrontendCostDisplayValidator
)
from netra_backend.app.schemas.UserPlan import PlanTier
from netra_backend.app.schemas.llm_base_types import LLMProvider, TokenUsage


@pytest.mark.asyncio
class TestCostTrackingAccuracyE2E:
    """Test #6: Complete cost tracking accuracy from operations to billing."""
    
    @pytest_asyncio.fixture
    async def test_core(self):
        """Initialize cost tracking test core."""
        core = CostTrackingTestCore()
        await core.setup_test_environment()
        yield core
        await core.teardown_test_environment()
    
    @pytest.fixture
    def ai_operation_simulator(self):
        """Initialize AI operation simulator."""
        return AIOperationSimulator()
    
    @pytest.fixture
    def cost_calculator_validator(self):
        """Initialize cost calculation validator."""
        return CostCalculationValidator()
    
    @pytest.fixture
    def billing_accuracy_validator(self):
        """Initialize billing accuracy validator."""
        return BillingAccuracyValidator()
    
    @pytest.fixture
    def frontend_cost_validator(self):
        """Initialize frontend cost display validator."""
        return FrontendCostDisplayValidator()
    
    @pytest.mark.asyncio
    async def test_complete_cost_tracking_flow_data_analysis(self, test_core, ai_operation_simulator,
                                                           cost_calculator_validator,
                                                           billing_accuracy_validator,
                                                           frontend_cost_validator):
        """Test complete cost tracking for data analysis operation."""
        # Establish authenticated user session
        session = await test_core.establish_user_session(PlanTier.PRO)
        
        try:
            # Simulate AI operation with known cost structure
            operation = ai_operation_simulator.create_data_analysis_operation(
                session["user_id"], expected_tokens=1200, expected_cost_cents=18
            )
            
            # Execute operation through frontend → backend → database flow
            result = await self._execute_full_cost_tracking_flow(
                session, operation, test_core, cost_calculator_validator,
                billing_accuracy_validator, frontend_cost_validator
            )
            
            # Validate complete cost accuracy
            self._assert_cost_tracking_accuracy(result, operation)
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_multiple_operations_cost_accuracy(self, test_core, ai_operation_simulator,
                                                   cost_calculator_validator,
                                                   billing_accuracy_validator):
        """Test cost accuracy across multiple operation types."""
        session = await test_core.establish_user_session(PlanTier.ENTERPRISE)
        
        try:
            operations_results = []
            
            # Test different operation types with varying costs
            operations = [
                ai_operation_simulator.create_optimization_operation(session["user_id"]),
                ai_operation_simulator.create_analysis_operation(session["user_id"]),
                ai_operation_simulator.create_report_generation_operation(session["user_id"])
            ]
            
            for operation in operations:
                result = await self._execute_cost_calculation_flow(
                    session, operation, test_core, cost_calculator_validator, billing_accuracy_validator
                )
                operations_results.append(result)
            
            # Validate total cost accuracy
            self._assert_multi_operation_cost_accuracy(operations_results, operations)
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_cost_tracking_performance_requirements(self, test_core, ai_operation_simulator,
                                                        cost_calculator_validator):
        """Test cost tracking meets performance requirements."""
        session = await test_core.establish_user_session(PlanTier.PRO)
        
        try:
            # High-cost operation for performance validation
            operation = ai_operation_simulator.create_high_cost_operation(session["user_id"])
            
            # Measure complete cost tracking time
            start_time = time.time()
            result = await self._execute_timed_cost_tracking(session, operation, test_core)
            tracking_time = time.time() - start_time
            
            # Validate performance requirements
            assert tracking_time < 5.0, f"Cost tracking took {tracking_time:.2f}s, exceeding 5s limit"
            
            # Validate accuracy under performance pressure
            cost_validation = await cost_calculator_validator.validate_operation_cost_accuracy(
                operation, result
            )
            assert cost_validation["accurate"], "Cost accuracy compromised under performance pressure"
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_frontend_cost_display_real_time_updates(self, test_core, ai_operation_simulator,
                                                         frontend_cost_validator):
        """Test frontend cost display updates in real-time."""
        session = await test_core.establish_user_session(PlanTier.PRO)
        
        try:
            operation = ai_operation_simulator.create_streaming_operation(session["user_id"])
            
            # Execute operation with frontend cost tracking
            display_result = await frontend_cost_validator.validate_real_time_cost_display(
                session, operation
            )
            
            # Validate frontend cost accuracy
            assert display_result["real_time_updates"], "Frontend not receiving real-time cost updates"
            assert display_result["cost_accuracy"], "Frontend displaying incorrect costs"
            assert display_result["update_latency"] < 1.0, "Cost updates too slow"
            
        finally:
            await session["client"].close()
    
    @pytest.mark.asyncio
    async def test_billing_database_consistency_validation(self, test_core, ai_operation_simulator,
                                                         billing_accuracy_validator):
        """Test billing database consistency and integrity."""
        session = await test_core.establish_user_session(PlanTier.ENTERPRISE)
        
        try:
            operation = ai_operation_simulator.create_complex_operation(session["user_id"])
            
            # Execute operation and validate database consistency
            billing_result = await billing_accuracy_validator.validate_complete_billing_consistency(
                session, operation
            )
            
            # Validate database integrity
            assert billing_result["usage_recorded"], "Usage not recorded in database"
            assert billing_result["cost_calculated"], "Cost not calculated correctly"
            assert billing_result["billing_created"], "Billing record not created"
            assert billing_result["data_consistent"], "Database records inconsistent"
            assert billing_result["audit_trail_complete"], "Audit trail incomplete"
            
        finally:
            await session["client"].close()
    
    
    async def _execute_full_cost_tracking_flow(self, session: Dict, operation: Dict,
                                             test_core, cost_validator, billing_validator,
                                             frontend_validator) -> Dict[str, Any]:
        """Execute complete cost tracking flow."""
        # Mock LLM for deterministic costs
        with patch('app.llm.llm_manager.LLMManager.call_llm') as mock_llm:
            mock_llm.return_value = self._create_mock_llm_response(operation["expected_tokens"])
            
            # Execute through all layers
            frontend_result = await frontend_validator.execute_operation_with_cost_tracking(
                session, operation
            )
            cost_result = await cost_validator.validate_operation_cost_calculation(operation)
            billing_result = await billing_validator.validate_billing_record_creation(
                session, operation
            )
            
            return {
                "frontend_result": frontend_result,
                "cost_result": cost_result,
                "billing_result": billing_result,
                "operation": operation
            }
    
    async def _execute_cost_calculation_flow(self, session: Dict, operation: Dict,
                                           test_core, cost_validator, billing_validator) -> Dict:
        """Execute cost calculation and billing flow."""
        with patch('app.llm.llm_manager.LLMManager.call_llm') as mock_llm:
            mock_llm.return_value = self._create_mock_llm_response(operation["expected_tokens"])
            
            cost_result = await cost_validator.validate_operation_cost_calculation(operation)
            billing_result = await billing_validator.validate_billing_record_creation(
                session, operation
            )
            
            return {"cost_result": cost_result, "billing_result": billing_result}
    
    async def _execute_timed_cost_tracking(self, session: Dict, operation: Dict, test_core) -> Dict:
        """Execute cost tracking with timing measurement."""
        with patch('app.llm.llm_manager.LLMManager.call_llm') as mock_llm:
            mock_llm.return_value = self._create_mock_llm_response(operation["expected_tokens"])
            
            return await test_core.execute_operation_with_cost_tracking(session, operation)
    
    
    def _create_mock_llm_response(self, expected_tokens: int) -> AsyncMock:
        """Create mock LLM response for deterministic testing."""
        return AsyncMock(return_value={
            "content": "Operation completed successfully",
            "tokens_used": expected_tokens,
            "model": "test-model",
            "provider": "test-provider"
        })
    
    def _assert_cost_tracking_accuracy(self, result: Dict, operation: Dict) -> None:
        """Assert complete cost tracking accuracy."""
        assert result["frontend_result"]["cost_displayed"], "Cost not displayed in frontend"
        assert result["cost_result"]["calculation_accurate"], "Cost calculation incorrect"
        assert result["billing_result"]["record_created"], "Billing record not created"
        
        # Validate cost consistency across all layers
        expected_cost = operation["expected_cost_cents"]
        assert result["cost_result"]["calculated_cost_cents"] == expected_cost, "Cost calculation mismatch"
        assert result["billing_result"]["billed_cost_cents"] == expected_cost, "Billing cost mismatch"
        assert result["frontend_result"]["displayed_cost_cents"] == expected_cost, "Frontend cost mismatch"
    
    def _assert_multi_operation_cost_accuracy(self, results: list, operations: list) -> None:
        """Assert cost accuracy across multiple operations."""
        total_expected_cost = sum(op["expected_cost_cents"] for op in operations)
        total_calculated_cost = sum(r["cost_result"]["calculated_cost_cents"] for r in results)
        total_billed_cost = sum(r["billing_result"]["billed_cost_cents"] for r in results)
        
        assert total_calculated_cost == total_expected_cost, "Multi-operation cost calculation incorrect"
        assert total_billed_cost == total_expected_cost, "Multi-operation billing incorrect"
    
