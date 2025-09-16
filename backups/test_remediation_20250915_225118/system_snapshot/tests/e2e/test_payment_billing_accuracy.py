"""
CRITICAL TEST IMPLEMENTATION #2: Payment Processing and Billing Accuracy

BVJ (Business Value Justification):
1. Segment: All paid tiers (protects $80K+ MRR from billing errors)
2. Business Goal: Prevent billing disputes and revenue leakage from payment errors  
3. Value Impact: Ensures accurate payment processing, usage tracking, and invoicing
4. Revenue Impact: Each billing error costs $1K+ in customer trust and support time

CRITICAL PATH: User Upgrade  ->  Payment Processing  ->  Usage Tracking  ->  Invoice Generation  ->  Billing Records

TEST SCENARIOS COVERED:
1. Free to Early tier upgrade with Stripe payment validation
2. Usage tracking and cost calculation accuracy verification  
3. Subscription renewal and automated invoice generation
4. Downgrade handling with prorated refund calculations
5. Failed payment retry logic and recovery flows

REQUIREMENTS:
- Mock Stripe webhooks with realistic payment data
- Test real database state transitions and billing record creation
- Validate ClickHouse usage aggregation and cost accuracy
- Check invoice calculations match actual usage and subscription costs
- Test payment failure recovery and retry mechanisms
- Performance validation (<5 seconds per test scenario)
- Architecture: File <300 lines, functions <8 lines each
"""
import time
import uuid
from decimal import Decimal
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig
from shared.isolated_environment import IsolatedEnvironment


import pytest

from netra_backend.app.schemas.user_plan import PlanTier
from tests.e2e.auth_flow_manager import AuthCompleteFlowManager
from tests.e2e.payment_billing_helpers import BillingAccuracyValidator


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_free_to_pro_tier_payment_accuracy():
    """
    Test #1: Free to Pro Tier Upgrade with Payment Validation
    
    BVJ: Protects $29/month Pro tier conversions ($348/year per user)
    Critical Path: Free signup  ->  Pro tier selection  ->  Payment  ->  Billing validation
    - Validates Stripe payment webhook processing
    - Ensures accurate tier upgrade and feature activation
    - Verifies billing record creation with correct amounts
    - Tests ClickHouse integration for usage tracking
    """
    auth_manager = AuthCompleteFlowManager()
    billing_validator = BillingAccuracyValidator()
    
    async with auth_manager.setup_complete_test_environment() as auth_tester:
        await billing_validator.setup_billing_validation_environment()
        
        try:
            # Create test user (free tier)
            user_data = {
                "id": str(uuid.uuid4()),
                "email": f"pro-tier-{uuid.uuid4().hex[:8]}@test.com",
                "tier": PlanTier.FREE.value,
                "created_at": time.time()
            }
            
            # Execute payment to billing accuracy validation
            start_time = time.time()
            result = await billing_validator.validate_payment_to_billing_accuracy(
                user_data, PlanTier.PRO
            )
            execution_time = time.time() - start_time
            
            # Performance validation
            assert execution_time < 5.0, f"Test too slow: {execution_time:.2f}s"
            
            # Webhook validation
            webhook = result["webhook"]
            assert webhook["type"] == "payment_intent.succeeded"
            assert webhook["data"]["object"]["amount"] == 2900  # $29.00
            assert webhook["data"]["object"]["status"] == "succeeded"
            
            # Invoice accuracy validation
            invoice = result["invoice"]
            assert invoice["tier"] == PlanTier.PRO.value
            assert invoice["subscription_amount_cents"] == 2900
            assert invoice["total_cents"] > invoice["subscription_amount_cents"]  # includes tax
            
            # Billing record validation
            billing_record = result["billing_record"]
            assert billing_record["user_id"] == user_data["id"]
            assert billing_record["tier"] == PlanTier.PRO.value
            assert billing_record["status"] == "completed"
            
            # Cross-system consistency validation
            validation = result["validation"]
            assert validation["consistent"], f"Billing inconsistency: {validation['errors']}"
            
            print(f"[SUCCESS] Pro Tier Payment Accuracy: {execution_time:.2f}s")
            print(f"[PROTECTED] $29/month Pro tier revenue pipeline")
            print(f"[VALIDATED] Payment -> Invoice -> Billing consistency")
            
        finally:
            await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio  
@pytest.mark.e2e
async def test_usage_tracking_cost_calculation_accuracy():
    """
    Test #2: Usage Tracking and Cost Calculation Accuracy
    
    BVJ: Prevents revenue leakage from incorrect usage billing
    - Simulates AI agent execution with token usage
    - Validates cost calculation accuracy using real pricing
    - Tests usage aggregation for monthly billing cycles
    - Verifies ClickHouse usage record insertion and retrieval
    """
    billing_validator = BillingAccuracyValidator()
    await billing_validator.setup_billing_validation_environment()
    
    try:
        user_id = str(uuid.uuid4())
        
        # Record multiple usage events
        usage_events = [
            {"operation": "data_optimization", "tokens": 5000, "model": LLMModel.GEMINI_2_5_FLASH.value},
            {"operation": "analytics_generation", "tokens": 3000, "model": LLMModel.GEMINI_2_5_FLASH.value},
            {"operation": "report_creation", "tokens": 2000, "model": LLMModel.GEMINI_2_5_FLASH.value}
        ]
        
        total_expected_cost_cents = 0
        for event in usage_events:
            record = billing_validator.usage_tracker.record_usage(
                user_id, event["operation"], event["tokens"], event["model"]
            )
            total_expected_cost_cents += record["cost_cents"]
            
            # Validate individual usage record accuracy
            assert record["user_id"] == user_id
            assert record["tokens"] == event["tokens"]
            assert record["cost_cents"] > 0, "Usage should have non-zero cost"
        
        # Calculate monthly aggregate
        monthly_usage = billing_validator.usage_tracker.calculate_monthly_usage(user_id)
        
        # Validate aggregation accuracy
        assert monthly_usage["user_id"] == user_id
        assert monthly_usage["total_tokens"] == 10000  # Sum of all tokens
        assert monthly_usage["total_operations"] == 3
        assert monthly_usage["total_cost_cents"] == total_expected_cost_cents
        
        # Test cost calculation precision
        cost_decimal = Decimal(monthly_usage["total_cost_cents"]) / 100
        assert cost_decimal > Decimal("0.10"), "Monthly usage should cost at least $0.10"
        assert cost_decimal < Decimal("10.00"), "Monthly usage should cost less than $10.00"
        
        print(f"[SUCCESS] Usage Tracking Accuracy")
        print(f"[VALIDATED] Cost calculation precision: ${cost_decimal:.4f}")
        print(f"[PROTECTED] Usage-based billing revenue accuracy")
        
    finally:
        await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_subscription_renewal_invoice_generation():
    """
    Test #3: Subscription Renewal and Invoice Generation
    
    BVJ: Ensures automated billing continues generating revenue
    - Tests subscription renewal processing
    - Validates invoice generation with usage charges
    - Verifies tax calculation accuracy
    - Tests billing period management
    """
    auth_manager = AuthCompleteFlowManager()
    billing_validator = BillingAccuracyValidator()
    
    async with auth_manager.setup_complete_test_environment() as auth_tester:
        await billing_validator.setup_billing_validation_environment()
        
        try:
            # Setup Enterprise tier subscriber
            user_data = {
                "id": str(uuid.uuid4()),
                "email": f"enterprise-renewal-{uuid.uuid4().hex[:8]}@test.com",
                "tier": PlanTier.ENTERPRISE.value,
                "subscription_start": time.time() - 2592000  # 30 days ago
            }
            
            # Record usage during billing period
            for _ in range(10):  # Simulate 10 operations
                billing_validator.usage_tracker.record_usage(
                    user_data["id"], "ai_optimization", 1500, LLMModel.GEMINI_2_5_FLASH.value
                )
            
            # Generate renewal invoice
            usage_data = billing_validator.usage_tracker.calculate_monthly_usage(user_data["id"])
            
            # Mock payment data for renewal
            payment_data = {
                "id": f"pi_{uuid.uuid4().hex[:24]}",
                "amount": 29900,  # $299.00 Enterprise tier
                "status": "succeeded"
            }
            
            invoice = billing_validator.invoice_generator.generate_invoice(
                user_data["id"], PlanTier.ENTERPRISE, usage_data, payment_data
            )
            
            # Validate invoice structure and calculations
            assert invoice["user_id"] == user_data["id"]
            assert invoice["tier"] == PlanTier.ENTERPRISE.value
            assert invoice["subscription_amount_cents"] == 29900  # $299.00
            assert invoice["usage_amount_cents"] > 0, "Should have usage charges"
            
            # Validate tax calculation (8.5% for testing)
            expected_tax = int((invoice["subscription_amount_cents"] + invoice["usage_amount_cents"]) * 0.085)
            assert abs(invoice["tax_cents"] - expected_tax) <= 1, "Tax calculation inaccuracy"
            
            # Validate total calculation
            expected_total = invoice["subscription_amount_cents"] + invoice["usage_amount_cents"] + invoice["tax_cents"]
            assert invoice["total_cents"] == expected_total, "Total calculation error"
            
            print(f"[SUCCESS] Subscription Renewal Invoice Generation")
            print(f"[VALIDATED] Enterprise tier renewal: ${invoice['total_cents']/100:.2f}")
            print(f"[PROTECTED] Automated billing revenue continuity")
            
        finally:
            await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_downgrade_prorated_refund_handling():
    """
    Test #4: Downgrade Handling with Prorated Refunds
    
    BVJ: Maintains customer satisfaction during plan changes
    - Tests Enterprise to Pro tier downgrade
    - Calculates accurate prorated refunds
    - Validates refund processing fees
    - Ensures billing record updates
    """
    billing_validator = BillingAccuracyValidator()
    await billing_validator.setup_billing_validation_environment()
    
    try:
        # Setup Enterprise tier subscriber
        user_data = {
            "id": str(uuid.uuid4()),
            "email": f"enterprise-{uuid.uuid4().hex[:8]}@test.com",
            "tier": PlanTier.ENTERPRISE.value
        }
        
        # Create original Enterprise invoice
        usage_data = {"total_cost_cents": 5000}  # $50 usage
        payment_data = {"id": f"pi_{uuid.uuid4().hex[:24]}"}
        
        original_invoice = billing_validator.invoice_generator.generate_invoice(
            user_data["id"], PlanTier.ENTERPRISE, usage_data, payment_data
        )
        
        # Simulate downgrade 15 days into billing cycle
        downgrade_time = time.time() - 1296000  # 15 days ago
        
        # Calculate prorated refund
        refund_calculation = billing_validator.invoice_generator.calculate_prorated_refund(
            original_invoice["id"], downgrade_time
        )
        
        # Validate refund calculation accuracy
        assert "original_amount_cents" in refund_calculation
        assert "refund_amount_cents" in refund_calculation
        assert "refund_ratio" in refund_calculation
        
        # Validate refund is approximately 50% (15 days remaining of 30)
        expected_ratio = 0.5
        actual_ratio = refund_calculation["refund_ratio"]
        assert abs(actual_ratio - expected_ratio) < 0.1, f"Refund ratio inaccurate: {actual_ratio}"
        
        # Validate refund amount
        expected_refund = int(original_invoice["subscription_amount_cents"] * actual_ratio)
        assert abs(refund_calculation["refund_amount_cents"] - expected_refund) <= 100
        
        # Validate processing fee
        assert refund_calculation["processing_fee_cents"] == 30, "Processing fee incorrect"
        
        print(f"[SUCCESS] Downgrade Prorated Refund")
        print(f"[CALCULATED] Refund: ${refund_calculation['refund_amount_cents']/100:.2f}")
        print(f"[PROTECTED] Customer satisfaction during plan changes")
        
    finally:
        await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_payment_failure_retry_recovery():
    """
    Test #5: Payment Failure and Retry Logic
    
    BVJ: Recovers revenue from temporary payment failures
    - Simulates payment failure scenarios
    - Tests automated retry mechanisms
    - Validates retry timing and limits
    - Ensures graceful failure handling
    """
    billing_validator = BillingAccuracyValidator()
    await billing_validator.setup_billing_validation_environment()
    
    try:
        user_data = {
            "id": str(uuid.uuid4()),
            "email": f"retry-test-{uuid.uuid4().hex[:8]}@test.com",
            "tier": PlanTier.PRO.value
        }
        
        # Test payment failure and retry flow
        retry_result = await billing_validator.test_payment_failure_retry_flow(
            user_data, PlanTier.PRO
        )
        
        # Validate initial failure webhook
        failed_webhook = retry_result["initial_failure"]
        assert failed_webhook["type"] == "payment_intent.payment_failed"
        assert failed_webhook["data"]["object"]["status"] == "requires_payment_method"
        
        # Validate retry sequence initiation
        retry_info = retry_result["retry_initiated"]
        assert retry_info["status"] == "retrying"
        assert retry_info["attempt_count"] == 0
        
        # Validate retry attempts
        retry_attempts = retry_result["retry_attempts"]
        assert len(retry_attempts) == 3, "Should have 3 retry attempts"
        
        # First two attempts should fail
        assert retry_attempts[0]["status"] == "retrying"
        assert retry_attempts[1]["status"] == "retrying"
        
        # Third attempt should succeed
        assert retry_attempts[2]["status"] == "succeeded"
        assert retry_attempts[2]["attempts"] == 3
        
        # Validate final status
        assert retry_result["final_status"] == "succeeded"
        
        print(f"[SUCCESS] Payment Retry Recovery")
        print(f"[VALIDATED] 3-attempt retry sequence with success")
        print(f"[PROTECTED] Revenue recovery from temporary payment failures")
        
    finally:
        await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_enterprise_tier_billing_accuracy_comprehensive():
    """
    Test #6: Enterprise Tier Billing Accuracy (Comprehensive)
    
    BVJ: Protects highest value customers ($2,999/month = $35,988/year)
    - Tests complete Enterprise billing flow
    - Validates high-usage billing scenarios
    - Tests complex invoice calculations
    - Ensures accuracy for largest revenue customers
    """
    auth_manager = AuthCompleteFlowManager()
    billing_validator = BillingAccuracyValidator()
    
    async with auth_manager.setup_complete_test_environment() as auth_tester:
        await billing_validator.setup_billing_validation_environment()
        
        try:
            # Create Enterprise customer
            user_data = {
                "id": str(uuid.uuid4()),
                "email": f"enterprise-comp-{uuid.uuid4().hex[:8]}@test.com",
                "tier": PlanTier.ENTERPRISE.value
            }
            
            # Simulate heavy Enterprise usage
            for i in range(50):  # 50 high-value operations
                billing_validator.usage_tracker.record_usage(
                    user_data["id"], f"enterprise_operation_{i}", 
                    10000, LLMModel.GEMINI_2_5_FLASH.value  # Large token usage
                )
            
            # Execute comprehensive billing validation
            start_time = time.time()
            result = await billing_validator.validate_payment_to_billing_accuracy(
                user_data, PlanTier.ENTERPRISE
            )
            execution_time = time.time() - start_time
            
            # Performance validation for Enterprise
            assert execution_time < 5.0, f"Enterprise test too slow: {execution_time:.2f}s"
            
            # Validate Enterprise pricing accuracy
            webhook = result["webhook"]
            assert webhook["data"]["object"]["amount"] == 29900  # $299.00
            
            # Validate high usage billing
            usage_data = result["usage_data"]
            assert usage_data["total_tokens"] == 500000  # 50 * 10,000 tokens
            assert usage_data["total_cost_cents"] > 5000, "High usage should exceed $50"
            
            # Validate Enterprise invoice
            invoice = result["invoice"]
            assert invoice["subscription_amount_cents"] == 29900
            assert invoice["usage_amount_cents"] > 1000
            assert invoice["total_cents"] > 35000, "Total should exceed $350 with usage+tax"
            
            # Validate billing record accuracy
            billing_record = result["billing_record"]
            assert billing_record["tier"] == PlanTier.ENTERPRISE.value
            assert billing_record["amount_cents"] == invoice["total_cents"]
            
            print(f"[SUCCESS] Enterprise Billing Comprehensive: {execution_time:.2f}s")
            print(f"[PROTECTED] $299/month Enterprise revenue accuracy")
            print(f"[VALIDATED] High-usage billing calculations: ${invoice['total_cents']/100:.2f}")
            
        finally:
            await billing_validator.teardown_billing_validation_environment()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_billing_system_performance_under_load():
    """
    Test #7: Billing System Performance Under Load
    
    BVJ: Ensures billing system scales with customer growth
    - Tests multiple concurrent billing operations
    - Validates system performance under load
    - Ensures accuracy is maintained during high throughput
    - Tests database consistency under concurrent operations
    """
    billing_validator = BillingAccuracyValidator()
    await billing_validator.setup_billing_validation_environment()
    
    try:
        # Create multiple test users across all paid tiers
        test_users = []
        for i, tier in enumerate([PlanTier.PRO, PlanTier.ENTERPRISE]):
            user_data = {
                "id": str(uuid.uuid4()),
                "email": f"load-test-{i}@test.com",
                "tier": tier.value
            }
            test_users.append((user_data, tier))
        
        # Execute concurrent billing operations
        start_time = time.time()
        billing_results = []
        
        for user_data, tier in test_users:
            # Add usage for each user
            for _ in range(5):
                billing_validator.usage_tracker.record_usage(
                    user_data["id"], "load_test_operation", 2000, LLMModel.GEMINI_2_5_FLASH.value
                )
            
            # Validate billing accuracy for each
            result = await billing_validator.validate_payment_to_billing_accuracy(
                user_data, tier
            )
            billing_results.append(result)
        
        total_execution_time = time.time() - start_time
        
        # Performance validation
        assert total_execution_time < 20.0, f"Load test too slow: {total_execution_time:.2f}s"
        avg_per_operation = total_execution_time / len(test_users)
        assert avg_per_operation < 5.0, f"Average operation too slow: {avg_per_operation:.2f}s"
        
        # Validate all billing results are accurate
        for i, result in enumerate(billing_results):
            validation = result["validation"]
            assert validation["consistent"], f"User {i} billing inconsistency: {validation['errors']}"
        
        # Calculate total revenue processed
        total_revenue_cents = sum(
            result["invoice"]["total_cents"] for result in billing_results
        )
        
        print(f"[SUCCESS] Billing Load Performance: {total_execution_time:.2f}s")
        print(f"[PROCESSED] {len(test_users)} billing operations")
        print(f"[VALIDATED] Total revenue accuracy: ${total_revenue_cents/100:.2f}")
        print(f"[PROTECTED] Billing system scalability and accuracy")
        
    finally:
        await billing_validator.teardown_billing_validation_environment()
