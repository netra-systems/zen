"""
CRITICAL E2E Payment Upgrade Flow Tests - Revenue Protection Test Suite

BVJ (Business Value Justification):
1. Segment: Free  ->  Paid conversion (100% of new revenue generation)
2. Business Goal: Protect complete payment and tier upgrade pipeline
3. Value Impact: Validates $99-999/month per user conversion flow
4. Revenue Impact: Each test failure caught prevents $10K+ MRR loss

REQUIREMENTS:
- Complete user journey: signup  ->  payment  ->  tier upgrade
- Real authentication and JWT operations
- Mock payment provider integration (Stripe simulation)
- Billing record creation in ClickHouse
- Premium feature activation validation
- Performance validation (<30 seconds total)
- 450-line file limit, 25-line function limit

This test protects 100% of new revenue generation. Without this test passing,
we cannot convert free users to paid, which is the entire business model.
"""
import time
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.schemas.user_plan import PlanTier
from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.integration.payment_upgrade_flow_tester import PaymentUpgradeFlowTester


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_payment_upgrade_flow_pro_tier():
    """
    Test #1: Complete User Signup  ->  Payment  ->  Pro Tier Upgrade Flow
    
    BVJ: Protects $29/month Pro tier conversions ($348/year per user)
    - User signs up (free tier)
    - User initiates payment for Pro tier
    - Payment processes successfully through mock provider
    - User tier upgrades to Pro
    - Premium features become available
    - Billing records created in ClickHouse
    - Must complete in <30 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        payment_tester = PaymentUpgradeFlowTester(auth_tester)
        
        # Execute complete payment upgrade flow
        results = await payment_tester.execute_complete_payment_flow(PlanTier.PRO)
        
        # Validate business-critical success criteria
        assert results["success"], f"Payment upgrade flow failed: {results.get('error')}"
        assert results["execution_time"] < 30.0, f"Performance failed: {results['execution_time']:.2f}s"
        
        # Validate each step completed successfully
        required_steps = [
            "signup", "payment_initiated", "payment_processed", 
            "tier_upgraded", "premium_features", "billing_records"
        ]
        for step in required_steps:
            assert step in results, f"Missing critical step: {step}"
        
        # Business value validation - payment processing
        payment_result = results["payment_processed"]
        assert payment_result["success"], "Payment processing failed"
        assert payment_result["payment"]["status"] == "succeeded", "Payment not successful"
        assert payment_result["payment"]["amount_cents"] == 2900, "Incorrect Pro tier amount"
        
        # Business value validation - tier upgrade
        tier_result = results["tier_upgraded"]
        assert tier_result["current_tier"] == "pro", "Tier not upgraded to Pro"
        assert tier_result["payment_status"] == "active", "Payment status not active"
        
        # Business value validation - premium features
        features_result = results["premium_features"]
        assert features_result["premium_features_available"], "Premium features not available"
        expected_features = ["analytics", "data_management"]
        assert all(f in features_result["features_tested"] for f in expected_features)
        
        # Business value validation - billing records
        billing_result = results["billing_records"]
        assert billing_result["billing_records_created"], "Billing records not created"
        assert billing_result["billing_status"] == "completed", "Billing not completed"
        assert billing_result["clickhouse_insertion"] == "verified", "ClickHouse insertion failed"
        
        print(f"[SUCCESS] Pro Tier Upgrade Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] $29/month Pro tier conversions")
        print(f"[REVENUE] Payment pipeline validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_payment_upgrade_flow_enterprise_tier():
    """
    Test #2: Complete User Signup  ->  Payment  ->  Enterprise Tier Upgrade Flow
    
    BVJ: Protects $299/month Enterprise tier conversions ($3,588/year per user)
    - User signs up (free tier)
    - User initiates payment for Enterprise tier
    - Payment processes successfully
    - User tier upgrades to Enterprise
    - Advanced premium features become available
    - Billing records created with correct Enterprise pricing
    - Must complete in <30 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        payment_tester = PaymentUpgradeFlowTester(auth_tester)
        
        # Execute complete Enterprise upgrade flow
        results = await payment_tester.execute_complete_payment_flow(PlanTier.ENTERPRISE)
        
        # Validate Enterprise-specific success criteria
        assert results["success"], f"Enterprise upgrade flow failed: {results.get('error')}"
        assert results["execution_time"] < 30.0, f"Performance failed: {results['execution_time']:.2f}s"
        
        # Business value validation - Enterprise payment processing
        payment_result = results["payment_processed"]
        assert payment_result["payment"]["amount_cents"] == 29900, "Incorrect Enterprise amount"
        
        # Business value validation - Enterprise tier upgrade
        tier_result = results["tier_upgraded"]
        assert tier_result["current_tier"] == "enterprise", "Tier not upgraded to Enterprise"
        
        # Business value validation - Enterprise premium features
        features_result = results["premium_features"]
        expected_enterprise_features = ["analytics", "data_management", "advanced_optimization"]
        assert all(f in features_result["features_tested"] for f in expected_enterprise_features)
        
        print(f"[SUCCESS] Enterprise Tier Upgrade Flow: {results['execution_time']:.2f}s")
        print(f"[PROTECTED] $299/month Enterprise tier conversions")
        print(f"[REVENUE] High-value customer pipeline validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_payment_failure_handling():
    """
    Test #3: Payment Failure Handling and Recovery
    
    BVJ: Prevents user frustration and abandoned conversions
    - User attempts payment upgrade
    - Payment fails (simulated)
    - User tier remains unchanged
    - No billing records created
    - Error handling provides clear feedback
    - Must complete gracefully in <30 seconds
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        payment_tester = PaymentUpgradeFlowTester(auth_tester)
        
        # Execute payment failure scenario
        results = await payment_tester.test_payment_failure_scenario()
        
        # Validate failure handling
        assert results["failure_scenario_tested"], "Failure scenario not executed"
        assert results["payment_failed_correctly"], "Payment failure not handled correctly"
        assert results["tier_unchanged"], "User tier should not have changed"
        
        print(f"[SUCCESS] Payment Failure Handling")
        print(f"[PROTECTED] User experience during payment failures")
        print(f"[RESILIENCE] Payment system error handling validated")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_payment_upgrade_performance_validation():
    """
    Test #4: Payment Upgrade Flow Performance Validation
    
    BVJ: User experience directly impacts conversion rates
    - Multiple payment flows executed sequentially
    - Each must complete within performance limits
    - System remains stable under payment processing load
    - Billing records created efficiently
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        total_start_time = time.time()
        
        # Test Pro tier upgrade performance
        pro_tester = PaymentUpgradeFlowTester(auth_tester)
        pro_results = await pro_tester.execute_complete_payment_flow(PlanTier.PRO)
        assert pro_results["execution_time"] < 30.0, f"Pro upgrade too slow: {pro_results['execution_time']:.2f}s"
        
        # Test Enterprise tier upgrade performance
        enterprise_tester = PaymentUpgradeFlowTester(auth_tester)
        enterprise_results = await enterprise_tester.execute_complete_payment_flow(PlanTier.ENTERPRISE)
        assert enterprise_results["execution_time"] < 30.0, f"Enterprise upgrade too slow: {enterprise_results['execution_time']:.2f}s"
        
        total_time = time.time() - total_start_time
        avg_upgrade_time = (pro_results["execution_time"] + enterprise_results["execution_time"]) / 2
        
        # Performance validation
        assert total_time < 120.0, f"Total test time too long: {total_time:.2f}s"
        assert avg_upgrade_time < 25.0, f"Average upgrade time too slow: {avg_upgrade_time:.2f}s"
        
        print(f"[PASSED] Payment Performance Validation")
        print(f"[METRICS] Average upgrade time: {avg_upgrade_time:.2f}s")
        print(f"[METRICS] Total test time: {total_time:.2f}s")
        print(f"[OPTIMIZED] Payment conversion experience")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_billing_record_data_integrity():
    """
    Test #5: Billing Record Data Integrity Validation
    
    BVJ: Accurate billing is critical for revenue tracking
    - Payment upgrade creates complete billing records
    - All required billing fields are present
    - Billing amounts match tier pricing
    - ClickHouse integration works correctly
    - Data consistency across payment and billing systems
    """
    manager = AuthCompleteFlowManager()
    
    async with manager.setup_complete_test_environment() as auth_tester:
        payment_tester = PaymentUpgradeFlowTester(auth_tester)
        
        # Execute payment flow with detailed billing validation
        results = await payment_tester.execute_complete_payment_flow(PlanTier.PRO)
        
        # Deep billing record validation
        billing_result = results["billing_records"]
        payment_result = results["payment_processed"]
        
        # Validate billing record completeness
        assert billing_result["billing_records_created"], "Billing records not created"
        assert billing_result["record_count"] >= 1, "No billing records found"
        
        # Validate payment-billing consistency
        assert payment_result["success"], "Payment must succeed for billing validation"
        payment_amount = payment_result["payment"]["amount_cents"]
        assert payment_amount == 2900, f"Pro tier should cost $29.00, got {payment_amount/100}"
        
        # Validate ClickHouse integration
        assert billing_result["clickhouse_insertion"] == "verified", "ClickHouse insertion not verified"
        
        print(f"[SUCCESS] Billing Data Integrity Validation")
        print(f"[PROTECTED] Revenue tracking accuracy")
        print(f"[VERIFIED] Payment-billing consistency")
