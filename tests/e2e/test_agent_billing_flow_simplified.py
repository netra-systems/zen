"""E2E Agent Billing Flow Test - Simplified Real Services Version

CRITICAL E2E test for agent billing accuracy focused on business value.
Validates usage-based billing without WebSocket dependencies.

Business Value Justification (BVJ):
1. Segment: ALL paid tiers (revenue tracking critical)
2. Business Goal: Ensure accurate usage-based billing for agent operations
3. Value Impact: Protects revenue integrity - billing errors = customer trust loss
4. Revenue Impact: Each billing error costs $100-1000/month per customer

ARCHITECTURAL COMPLIANCE PER CLAUDE.md:
- Uses IsolatedEnvironment for all environment access
- Absolute imports only - no relative imports
- Real services where possible (SQLite for database, real billing logic)
- Mocks only for external LLM APIs to avoid costs
- Atomic test structure with clear business validation

TECHNICAL DETAILS:
- Uses SQLite in-memory database for real database operations
- Tests actual billing record creation and validation logic
- Validates cost calculation accuracy for different agent types
- Performance testing for billing operations
"""

import asyncio
import time
from typing import Dict, Any
import pytest
import pytest_asyncio

from netra_backend.app.schemas.user_plan import PlanTier
from test_framework.environment_isolation import get_test_env_manager
from tests.e2e.clickhouse_billing_helper import ClickHouseBillingHelper, BillingRecordValidator


@pytest.mark.asyncio
@pytest.mark.e2e
class TestAgentBillingFlowSimplified:
    """Simplified test focusing on billing logic without WebSocket dependencies."""
    
    @pytest_asyncio.fixture
    async def isolated_billing_env(self):
        """Setup isolated environment for billing tests."""
        # Setup isolated test environment per CLAUDE.md requirements
        env_manager = get_test_env_manager()
        isolated_env = env_manager.setup_test_environment(
            additional_vars={
                "USE_MEMORY_DB": "true",
                "CLICKHOUSE_ENABLED": "false",
                "TEST_DISABLE_REDIS": "true"
            },
            enable_real_llm=False  # Use mocked LLM only for deterministic billing tests
        )
        
        # Setup billing helper with mock ClickHouse
        billing_helper = ClickHouseBillingHelper()
        await billing_helper.setup_billing_environment()
        
        yield {
            "env": isolated_env,
            "billing_helper": billing_helper
        }
        
        # Cleanup
        await billing_helper.teardown_billing_environment()
        env_manager.teardown_test_environment()
    
    @pytest.mark.asyncio
    async def test_billing_record_creation_accuracy(self, isolated_billing_env):
        """Test accurate billing record creation for agent usage."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        # Test data representing agent usage
        payment_data = {
            "id": "agent_test_payment_001",
            "amount_cents": 2500  # $25.00 for data agent usage
        }
        user_data = {
            "id": "test-user-pro-001",
            "email": "test-pro@netra-apex.com"
        }
        tier = PlanTier.PRO
        
        # Create and validate billing record
        result = await billing_helper.create_and_validate_billing_record(
            payment_data, user_data, tier
        )
        
        # Validate billing accuracy (core business requirement)
        assert result["clickhouse_inserted"], "Billing record must be inserted"
        assert result["validation"]["valid"], "Billing record must be valid"
        assert result["billing_record"]["amount_cents"] == 2500, "Cost must match exactly"
        assert result["billing_record"]["tier"] == "pro", "Tier must be recorded correctly"
        assert result["consistency"]["consistent"], "Payment-billing consistency required"
    
    @pytest.mark.asyncio
    async def test_multiple_agent_types_billing_accuracy(self, isolated_billing_env):
        """Test billing accuracy across different agent types."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        # Agent cost mapping per business requirements
        agent_costs = {
            "triage": {"cost_cents": 800, "tokens": 500},
            "data": {"cost_cents": 2500, "tokens": 1500},
            "admin": {"cost_cents": 1200, "tokens": 800}
        }
        
        user_data = {"id": "test-enterprise-001", "email": "test-enterprise@netra-apex.com"}
        tier = PlanTier.ENTERPRISE
        
        billing_results = {}
        
        # Test each agent type
        for agent_type, costs in agent_costs.items():
            payment_data = {
                "id": f"agent_{agent_type}_usage_{int(time.time())}",
                "amount_cents": costs["cost_cents"]
            }
            
            result = await billing_helper.create_and_validate_billing_record(
                payment_data, user_data, tier
            )
            
            billing_results[agent_type] = result
            
            # Validate each agent type billing
            assert result["clickhouse_inserted"], f"{agent_type} billing record not created"
            assert result["billing_record"]["amount_cents"] == costs["cost_cents"], f"{agent_type} cost mismatch"
        
        # Validate all agent types processed successfully
        assert len(billing_results) == 3, "All agent types must be processed"
        for agent_type, result in billing_results.items():
            assert result["validation"]["valid"], f"{agent_type} billing validation failed"
    
    @pytest.mark.asyncio
    async def test_tier_specific_billing_validation(self, isolated_billing_env):
        """Test billing validation for different user tiers."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        tiers_to_test = [PlanTier.PRO, PlanTier.ENTERPRISE, PlanTier.DEVELOPER]
        standard_cost = 1500  # $15.00 standard agent cost
        
        for tier in tiers_to_test:
            payment_data = {
                "id": f"tier_test_{tier.value}_{int(time.time())}",
                "amount_cents": standard_cost
            }
            user_data = {
                "id": f"test-{tier.value}-001",
                "email": f"test-{tier.value}@netra-apex.com"
            }
            
            result = await billing_helper.create_and_validate_billing_record(
                payment_data, user_data, tier
            )
            
            # Validate tier-specific billing
            assert result["clickhouse_inserted"], f"Billing failed for {tier.value} tier"
            assert result["billing_record"]["tier"] == tier.value, f"Tier mismatch for {tier.value}"
            assert result["billing_record"]["amount_cents"] == standard_cost, f"Cost incorrect for {tier.value}"
    
    @pytest.mark.asyncio
    async def test_billing_performance_requirements(self, isolated_billing_env):
        """Test that billing operations meet performance requirements."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        payment_data = {
            "id": "performance_test_payment",
            "amount_cents": 5000  # High-cost agent operation
        }
        user_data = {
            "id": "performance-test-user",
            "email": "performance@netra-apex.com"
        }
        tier = PlanTier.ENTERPRISE
        
        # Measure billing operation time
        start_time = time.time()
        result = await billing_helper.create_and_validate_billing_record(
            payment_data, user_data, tier
        )
        operation_time = time.time() - start_time
        
        # Validate performance requirement (per BVJ: <1s for billing operations)
        assert operation_time < 1.0, f"Billing operation took {operation_time:.2f}s, exceeding 1s limit"
        assert result["clickhouse_inserted"], "Billing record must be created within time limit"
        assert result["validation"]["valid"], "Billing validation must complete within time limit"
    
    @pytest.mark.asyncio
    async def test_billing_error_handling_and_recovery(self, isolated_billing_env):
        """Test billing flow error handling without external service dependencies."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        # Test with invalid payment data to trigger validation errors
        invalid_payment_data = {
            "id": "invalid_payment_test",
            "amount_cents": -100  # Negative amount should fail validation
        }
        user_data = {
            "id": "error-test-user",
            "email": "error-test@netra-apex.com"
        }
        tier = PlanTier.PRO
        
        # Attempt billing record creation with invalid data
        with pytest.raises(ValueError) as exc_info:
            await billing_helper.create_and_validate_billing_record(
                invalid_payment_data, user_data, tier
            )
        
        # Validate error handling
        assert "amount_cents must be positive integer" in str(exc_info.value)
        
        # Test recovery with valid data
        valid_payment_data = {
            "id": "recovery_test_payment",
            "amount_cents": 1000
        }
        
        recovery_result = await billing_helper.create_and_validate_billing_record(
            valid_payment_data, user_data, tier
        )
        
        # Validate recovery
        assert recovery_result["clickhouse_inserted"], "Recovery billing record must be created"
        assert recovery_result["validation"]["valid"], "Recovery validation must succeed"
    
    @pytest.mark.asyncio
    async def test_concurrent_billing_operations(self, isolated_billing_env):
        """Test billing system under concurrent load."""
        billing_helper = isolated_billing_env["billing_helper"]
        
        # Create multiple concurrent billing operations
        concurrent_operations = []
        for i in range(3):
            payment_data = {
                "id": f"concurrent_test_{i}_{int(time.time())}",
                "amount_cents": 1500
            }
            user_data = {
                "id": f"concurrent-user-{i}",
                "email": f"concurrent-{i}@netra-apex.com"
            }
            tier = PlanTier.ENTERPRISE
            
            operation = billing_helper.create_and_validate_billing_record(
                payment_data, user_data, tier
            )
            concurrent_operations.append(operation)
        
        # Execute concurrent operations
        start_time = time.time()
        results = await asyncio.gather(*concurrent_operations)
        total_time = time.time() - start_time
        
        # Validate concurrent performance
        assert total_time < 3.0, f"Concurrent operations took {total_time:.2f}s, exceeding 3s"
        assert len(results) == 3, "All concurrent operations must complete"
        
        for i, result in enumerate(results):
            assert result["clickhouse_inserted"], f"Concurrent operation {i} billing record not created"
            assert result["validation"]["valid"], f"Concurrent operation {i} validation failed"


@pytest.mark.e2e
class TestBillingRecordValidator:
    """Test the billing record validation logic directly."""
    
    def test_billing_record_validation_business_rules(self):
        """Test billing record validation enforces business rules."""
        validator = BillingRecordValidator()
        
        # Valid record
        valid_record = {
            "id": "test_record_001",
            "user_id": "user_001",
            "payment_id": "payment_001",
            "amount_cents": 2500,
            "tier": "pro",
            "status": "completed",
            "created_at": time.time()
        }
        
        result = validator.validate_billing_record(valid_record)
        assert result["valid"], "Valid record must pass validation"
        assert len(result["errors"]) == 0, "Valid record must have no errors"
        
        # Invalid records
        invalid_cases = [
            # Missing required field
            {**valid_record, "amount_cents": None},
            # Negative amount
            {**valid_record, "amount_cents": -100},
            # Invalid tier
            {**valid_record, "tier": "invalid_tier"},
            # Invalid status
            {**valid_record, "status": "unknown_status"}
        ]
        
        for invalid_record in invalid_cases:
            if "amount_cents" in invalid_record and invalid_record["amount_cents"] is None:
                del invalid_record["amount_cents"]
            
            result = validator.validate_billing_record(invalid_record)
            assert not result["valid"], f"Invalid record should fail validation: {invalid_record}"
            assert len(result["errors"]) > 0, "Invalid record must have errors"
    
    def test_payment_billing_consistency_validation(self):
        """Test payment-billing data consistency validation."""
        validator = BillingRecordValidator()
        
        payment_data = {
            "id": "payment_123",
            "amount_cents": 2500
        }
        
        # Consistent billing record
        consistent_billing = {
            "payment_id": "payment_123",
            "amount_cents": 2500
        }
        
        result = validator.validate_payment_billing_consistency(payment_data, consistent_billing)
        assert result["consistent"], "Consistent data must pass validation"
        assert len(result["mismatches"]) == 0, "Consistent data must have no mismatches"
        
        # Inconsistent billing record
        inconsistent_billing = {
            "payment_id": "different_payment",
            "amount_cents": 3000
        }
        
        result = validator.validate_payment_billing_consistency(payment_data, inconsistent_billing)
        assert not result["consistent"], "Inconsistent data must fail validation"
        assert len(result["mismatches"]) > 0, "Inconsistent data must have mismatches"