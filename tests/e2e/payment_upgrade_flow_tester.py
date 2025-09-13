"""
Payment Upgrade Flow Tester - E2E Revenue Protection Testing

BVJ (Business Value Justification):
1. Segment: Free  ->  Paid conversion (100% of new revenue)
2. Business Goal: Validate complete signup  ->  payment  ->  tier upgrade flow
3. Value Impact: Protects $99-999/month per user revenue pipeline
4. Revenue Impact: Each test failure caught saves $10K+ MRR from payment issues

REQUIREMENTS:
- Complete user journey: signup  ->  payment  ->  tier upgrade
- Real authentication and JWT validation
- Mock payment provider (Stripe simulation)
- Billing record creation in ClickHouse
- Premium feature validation
- Performance validation (<30 seconds)
- 450-line file limit, 25-line function limit
"""
import time
import uuid
from typing import Any, Dict

from netra_backend.app.schemas.user_plan import PlanTier
from tests.e2e.payment_flow_manager import PaymentFlowManager


class PaymentUpgradeFlowTester:
    """Test #1: Complete User Signup  ->  Payment  ->  Tier Upgrade Flow."""
    
    def __init__(self, auth_tester):
        self.auth_tester = auth_tester
        self.payment_manager = PaymentFlowManager()
        self.user_email = f"e2e-payment-{uuid.uuid4().hex[:8]}@netrasystems.ai"
        self.test_results: Dict[str, Any] = {}
        self.user_data = {}
    
    async def execute_complete_payment_flow(self, target_tier: PlanTier = PlanTier.PRO) -> Dict[str, Any]:
        """Execute complete payment upgrade flow in <30 seconds."""
        start_time = time.time()
        
        try:
            # Setup payment services
            await self.payment_manager.setup_payment_services()
            
            # Step 1: User signup (free tier)
            signup_result = await self._execute_user_signup()
            self._store_result("signup", signup_result)
            
            # Step 2: User initiates payment
            payment_init_result = await self._initiate_payment_process(target_tier)
            self._store_result("payment_initiated", payment_init_result)
            
            # Step 3: Payment processes successfully
            payment_result = await self._process_payment_with_upgrade(
                signup_result, target_tier
            )
            self._store_result("payment_processed", payment_result)
            
            # Step 4: Verify tier upgrade
            tier_verification = await self._verify_tier_upgrade(
                signup_result["user"]["id"], target_tier
            )
            self._store_result("tier_upgraded", tier_verification)
            
            # Step 5: Verify premium features available
            features_result = await self._verify_premium_features_available(
                signup_result["user"]["id"], target_tier
            )
            self._store_result("premium_features", features_result)
            
            # Step 6: Verify billing records created
            billing_result = await self._verify_billing_records_created(
                signup_result["user"]["id"]
            )
            self._store_result("billing_records", billing_result)
            
            execution_time = time.time() - start_time
            self.test_results["execution_time"] = execution_time
            self.test_results["success"] = True
            
            # CRITICAL: Must complete in <30 seconds for user experience
            assert execution_time < 30.0, f"Payment flow took {execution_time:.2f}s > 30s limit"
            
        except Exception as e:
            self.test_results["error"] = str(e)
            self.test_results["success"] = False
            raise
        finally:
            await self.payment_manager.cleanup_services()
        
        return self.test_results
    
    async def _execute_user_signup(self) -> Dict[str, Any]:
        """Execute user signup with free tier."""
        # Create real JWT payload for free user
        payload = self.auth_tester.jwt_helper.create_valid_payload()
        payload["email"] = self.user_email
        payload["tier"] = PlanTier.FREE.value
        
        # Generate real JWT tokens
        access_token = await self.auth_tester.jwt_helper.create_jwt_token(payload)
        refresh_token = await self.auth_tester.jwt_helper.create_jwt_token(
            self.auth_tester.jwt_helper.create_refresh_payload()
        )
        
        # Create user data
        self.user_data = {
            "id": payload["sub"],
            "email": self.user_email,
            "tier": PlanTier.FREE.value,
            "is_active": True,
            "created_at": time.time()
        }
        
        # Simulate user creation in auth database
        await self.auth_tester.mock_services["auth"].create_user(self.user_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": self.user_data,
            "token_type": "Bearer",
            "initial_tier": PlanTier.FREE.value
        }
    
    async def _initiate_payment_process(self, target_tier: PlanTier) -> Dict[str, Any]:
        """Initiate payment process for tier upgrade."""
        # Simulate user selecting upgrade plan
        payment_intent = {
            "target_tier": target_tier.value,
            "billing_cycle": "monthly",
            "user_id": self.user_data["id"],
            "email": self.user_data["email"],
            "initiated_at": time.time()
        }
        
        # Validate tier upgrade is allowed
        valid_upgrade = target_tier in [PlanTier.PRO, PlanTier.ENTERPRISE]
        assert valid_upgrade, f"Invalid upgrade tier: {target_tier.value}"
        
        return {
            "payment_intent": payment_intent,
            "upgrade_allowed": valid_upgrade,
            "payment_flow_started": True
        }
    
    async def _process_payment_with_upgrade(self, signup_data: Dict, 
                                          target_tier: PlanTier) -> Dict[str, Any]:
        """Process payment and execute tier upgrade."""
        # Execute complete payment flow through payment manager
        payment_flow_result = await self.payment_manager.execute_complete_payment_flow(
            signup_data["user"], target_tier
        )
        
        # Validate payment succeeded
        assert payment_flow_result["success"], "Payment processing failed"
        assert payment_flow_result["payment"]["status"] == "succeeded", "Payment not successful"
        
        return payment_flow_result
    
    async def _verify_tier_upgrade(self, user_id: str, 
                                 expected_tier: PlanTier) -> Dict[str, Any]:
        """Verify user tier was upgraded correctly."""
        # Get current user plan
        user_plan = self.payment_manager.tier_manager.get_user_plan(user_id)
        
        # Validate tier upgrade
        assert user_plan is not None, "User plan not found after upgrade"
        assert user_plan["tier"] == expected_tier.value, f"Tier not upgraded: {user_plan['tier']}"
        assert user_plan["payment_status"] == "active", "Payment status not active"
        
        return {
            "tier_upgraded": True,
            "current_tier": user_plan["tier"],
            "payment_status": user_plan["payment_status"],
            "upgrade_verified": True
        }
    
    async def _verify_premium_features_available(self, user_id: str, 
                                               tier: PlanTier) -> Dict[str, Any]:
        """Verify premium features are available after upgrade."""
        # Define premium features to test based on tier
        premium_features = {
            PlanTier.PRO: ["analytics", "data_management"],
            PlanTier.ENTERPRISE: ["analytics", "data_management", "advanced_optimization"]
        }
        
        required_features = premium_features.get(tier, [])
        
        # Verify features are available
        features_available = self.payment_manager.tier_manager.verify_premium_features(
            user_id, required_features
        )
        
        assert features_available, f"Premium features not available for {tier.value}"
        
        return {
            "premium_features_available": True,
            "features_tested": required_features,
            "tier": tier.value,
            "feature_validation": "passed"
        }
    
    async def _verify_billing_records_created(self, user_id: str) -> Dict[str, Any]:
        """Verify billing records were created in ClickHouse."""
        # Get billing records from tier manager
        billing_records = self.payment_manager.tier_manager.billing_records
        
        # Find billing record for this user
        user_billing_records = [
            record for record in billing_records.values() 
            if record["user_id"] == user_id
        ]
        
        assert len(user_billing_records) > 0, "No billing records found"
        
        # Validate billing record structure
        billing_record = user_billing_records[0]
        required_fields = ["id", "user_id", "amount_cents", "tier", "status"]
        
        for field in required_fields:
            assert field in billing_record, f"Missing billing field: {field}"
        
        assert billing_record["status"] == "completed", "Billing status not completed"
        
        # Verify ClickHouse insertion was called
        self.payment_manager.mock_services["clickhouse"].insert_billing_record.assert_called_once()
        
        return {
            "billing_records_created": True,
            "record_count": len(user_billing_records),
            "billing_status": billing_record["status"],
            "clickhouse_insertion": "verified"
        }
    
    async def test_payment_failure_scenario(self) -> Dict[str, Any]:
        """Test payment failure handling."""
        # Enable payment failure mode
        self.payment_manager.simulate_payment_failure()
        
        try:
            # Execute signup
            signup_result = await self._execute_user_signup()
            
            # Attempt payment (should fail)
            payment_result = await self.payment_manager.execute_complete_payment_flow(
                signup_result["user"], PlanTier.PRO
            )
            
            # Verify failure was handled correctly
            assert not payment_result["success"], "Payment should have failed"
            
            # Verify user tier remains unchanged
            user_plan = self.payment_manager.tier_manager.get_user_plan(signup_result["user"]["id"])
            assert user_plan is None, "User tier should not have been upgraded"
            
            return {
                "failure_scenario_tested": True,
                "payment_failed_correctly": True,
                "tier_unchanged": True
            }
        finally:
            # Reset payment system
            self.payment_manager.reset_payment_system()
            await self.payment_manager.cleanup_services()
    
    def _store_result(self, step: str, result: Any) -> None:
        """Store step result for analysis."""
        self.test_results[step] = result
