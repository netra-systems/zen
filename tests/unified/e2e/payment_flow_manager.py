"""
Payment Flow Manager - E2E Payment and Tier Upgrade Testing

BVJ (Business Value Justification):
1. Segment: Free → Paid conversion (100% of new revenue)
2. Business Goal: Protect complete payment and tier upgrade flow
3. Value Impact: Validates $99-999/month per user conversion pipeline
4. Revenue Impact: Single payment failure = lost customer = $1K+ lifetime value

REQUIREMENTS:
- Mock payment provider integration (Stripe/similar)
- Real tier upgrade logic with database updates
- Billing record creation in ClickHouse
- Performance validation (<30 seconds total)
- 450-line file limit, 25-line function limit
"""
import time
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock

from netra_backend.app.schemas.UserPlan import PlanTier, PLAN_DEFINITIONS, UserPlan, PlanFeatures
from tests.unified.e2e.clickhouse_billing_helper import ClickHouseBillingHelper


class MockPaymentProvider:
    """Mock payment provider for testing (replaces Stripe)."""
    
    def __init__(self):
        self.payments = {}
        self.customers = {}
        self.failure_mode = False
    
    async def create_customer(self, user_data: Dict) -> Dict[str, Any]:
        """Create payment customer record."""
        customer_id = f"cust_{uuid.uuid4().hex[:16]}"
        self.customers[customer_id] = {
            "id": customer_id,
            "email": user_data["email"],
            "user_id": user_data["id"],
            "created": time.time()
        }
        return self.customers[customer_id]
    
    async def process_payment(self, customer_id: str, amount_cents: int, 
                            tier: PlanTier) -> Dict[str, Any]:
        """Process payment with success/failure simulation."""
        if self.failure_mode:
            return {"status": "failed", "error": "Payment declined"}
        
        payment_id = f"pay_{uuid.uuid4().hex[:16]}"
        payment_record = {
            "id": payment_id,
            "customer_id": customer_id,
            "amount_cents": amount_cents,
            "status": "succeeded",
            "tier": tier.value,
            "processed_at": time.time()
        }
        self.payments[payment_id] = payment_record
        return payment_record
    
    def set_failure_mode(self, enabled: bool) -> None:
        """Enable/disable payment failures for testing."""
        self.failure_mode = enabled


class TierUpgradeManager:
    """Manages user tier upgrades and feature activation."""
    
    def __init__(self):
        self.user_plans = {}
        self.billing_records = {}
    
    async def upgrade_user_tier(self, user_id: str, from_tier: PlanTier, 
                               to_tier: PlanTier, payment_data: Dict) -> Dict[str, Any]:
        """Upgrade user tier with feature activation."""
        plan_def = PLAN_DEFINITIONS[to_tier]
        
        # Create new user plan
        new_plan = UserPlan(
            user_id=user_id,
            tier=to_tier,
            features=plan_def.features,
            payment_status="active",
            upgraded_from=from_tier.value
        )
        
        # Store plan
        self.user_plans[user_id] = new_plan
        
        # Create billing record
        billing_record = await self._create_billing_record(
            user_id, payment_data, to_tier
        )
        
        return {
            "user_plan": new_plan.model_dump(),
            "billing_record": billing_record,
            "features_activated": plan_def.features.permissions,
            "tier_change": f"{from_tier.value} → {to_tier.value}"
        }
    
    async def _create_billing_record(self, user_id: str, payment_data: Dict, 
                                   tier: PlanTier) -> Dict[str, Any]:
        """Create billing record for ClickHouse."""
        record_id = str(uuid.uuid4())
        billing_record = {
            "id": record_id,
            "user_id": user_id,
            "payment_id": payment_data["id"],
            "amount_cents": payment_data["amount_cents"],
            "tier": tier.value,
            "status": "completed",
            "created_at": time.time(),
            "billing_period_start": time.time(),
            "billing_period_end": time.time() + (30 * 24 * 3600)  # 30 days
        }
        self.billing_records[record_id] = billing_record
        return billing_record
    
    def get_user_plan(self, user_id: str) -> Optional[Dict]:
        """Get current user plan."""
        plan = self.user_plans.get(user_id)
        return plan.model_dump() if plan else None
    
    def verify_premium_features(self, user_id: str, 
                              required_features: list) -> bool:
        """Verify user has premium features available."""
        plan = self.user_plans.get(user_id)
        if not plan:
            return False
        
        user_permissions = plan.features.permissions
        return all(feature in user_permissions for feature in required_features)


class PaymentFlowManager:
    """Orchestrates complete payment and tier upgrade flow."""
    
    def __init__(self):
        self.payment_provider = MockPaymentProvider()
        self.tier_manager = TierUpgradeManager()
        self.billing_helper = ClickHouseBillingHelper()
        self.mock_services = {}
    
    async def setup_payment_services(self) -> None:
        """Setup payment-related mock services."""
        await self.billing_helper.setup_billing_environment()
        await self._setup_clickhouse_mock()
        await self._setup_auth_service_mock()
        await self._setup_notification_mock()
    
    async def _setup_clickhouse_mock(self) -> None:
        """Setup ClickHouse mock for billing records."""
        self.mock_services["clickhouse"] = MagicMock()
        self.mock_services["clickhouse"].insert_billing_record = AsyncMock()
        self.mock_services["clickhouse"].query_user_billing = AsyncMock()
    
    async def _setup_auth_service_mock(self) -> None:
        """Setup auth service mock for tier updates."""
        self.mock_services["auth"] = MagicMock()
        self.mock_services["auth"].update_user_tier = AsyncMock()
        self.mock_services["auth"].get_user_plan = AsyncMock()
    
    async def _setup_notification_mock(self) -> None:
        """Setup notification service mock."""
        self.mock_services["notifications"] = MagicMock()
        self.mock_services["notifications"].send_upgrade_confirmation = AsyncMock()
    
    async def execute_complete_payment_flow(self, user_data: Dict, 
                                          target_tier: PlanTier) -> Dict[str, Any]:
        """Execute complete payment and upgrade flow."""
        start_time = time.time()
        
        # Step 1: Create payment customer
        customer = await self.payment_provider.create_customer(user_data)
        
        # Step 2: Calculate payment amount
        plan_def = PLAN_DEFINITIONS[target_tier]
        amount_cents = int(plan_def.price_monthly * 100) if plan_def.price_monthly else 0
        
        # Step 3: Process payment
        payment_result = await self.payment_provider.process_payment(
            customer["id"], amount_cents, target_tier
        )
        
        execution_time = time.time() - start_time
        
        # Early return if payment failed
        if payment_result["status"] != "succeeded":
            return {
                "success": False,
                "customer": customer,
                "payment": payment_result,
                "execution_time": execution_time,
                "error": payment_result.get("error", "Payment failed")
            }
        
        # Step 4: Upgrade user tier (only if payment succeeded)
        upgrade_result = await self.tier_manager.upgrade_user_tier(
            user_data["id"], PlanTier.FREE, target_tier, payment_result
        )
        
        # Step 5: Store billing record in ClickHouse with validation
        billing_validation = await self.billing_helper.create_and_validate_billing_record(
            payment_result, user_data, target_tier
        )
        
        await self.mock_services["clickhouse"].insert_billing_record(
            billing_validation["billing_record"]
        )
        
        # Step 6: Update auth service
        await self.mock_services["auth"].update_user_tier(
            user_data["id"], target_tier.value
        )
        
        # Step 7: Send confirmation notification
        await self.mock_services["notifications"].send_upgrade_confirmation(
            user_data["email"], target_tier.value
        )
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "customer": customer,
            "payment": payment_result,
            "upgrade": upgrade_result,
            "billing_validation": billing_validation,
            "execution_time": execution_time,
            "billing_stored": True,
            "notifications_sent": True
        }
    
    def simulate_payment_failure(self) -> None:
        """Enable payment failure simulation."""
        self.payment_provider.set_failure_mode(True)
    
    def reset_payment_system(self) -> None:
        """Reset payment system to success mode."""
        self.payment_provider.set_failure_mode(False)
    
    async def cleanup_services(self) -> None:
        """Cleanup payment services."""
        await self.billing_helper.teardown_billing_environment()
        self.mock_services.clear()
        self.payment_provider.payments.clear()
        self.payment_provider.customers.clear()
        self.tier_manager.user_plans.clear()
        self.tier_manager.billing_records.clear()
