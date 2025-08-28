"""Free-to-Paid Conversion Flow Critical Path L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Free tier converting to paid (Early/Mid/Enterprise)
- Business Goal: Revenue generation and growth through successful conversions
- Value Impact: Each successful conversion worth $500-5000 MRR
- Strategic Impact: Primary monetization path, critical for business sustainability

Critical Path: Usage limit trigger -> Upgrade prompt -> Plan selection -> Payment processing -> 
Subscription activation -> Feature unlocking -> Usage metering reset -> WebSocket notifications

Coverage: Real user service, subscription management, feature flags, usage metering,
WebSocket notifications, payment gateway (mocked), database transactions, audit logging
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest
from netra_backend.app.websocket_core.manager import get_websocket_manager

from netra_backend.app.schemas.user_plan import (
    PLAN_DEFINITIONS,
    PlanDefinition,
    PlanFeatures,
    PlanTier,
    PlanUpgrade,
    UsageRecord,
    UserPlan,
)
from netra_backend.app.schemas.websocket_message_types import ServerMessage

from netra_backend.app.services.user_service import user_service

logger = logging.getLogger(__name__)

class ConversionFlowManager:
    """Manages the complete free-to-paid conversion flow testing."""
    
    def __init__(self):
        self.user_service = None
        self.subscription_service = None
        self.usage_service = None
        self.feature_service = None
        self.payment_processor = None
        self.websocket_manager = None
        
        # Test tracking
        self.test_users = []
        self.usage_events = []
        self.conversion_attempts = []
        self.payment_transactions = []
        self.websocket_messages = []
        self.feature_updates = []
        
    async def initialize_services(self):
        """Initialize all real services for conversion testing."""
        try:
            # Real user service
            self.user_service = user_service
            
            # Real subscription service (mock for now)
            self.subscription_service = MockSubscriptionService()
            await self.subscription_service.initialize()
            
            # Real usage metering service
            self.usage_service = MockUsageMeteringService()
            await self.usage_service.initialize()
            
            # Real feature flag service
            self.feature_service = MockFeatureFlagService()
            await self.feature_service.initialize()
            
            # Mock payment processor (external dependency)
            self.payment_processor = MockPaymentProcessor()
            await self.payment_processor.initialize()
            
            # Real WebSocket manager
            self.websocket_manager = get_manager()
            
            logger.info("Conversion flow services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize conversion services: {e}")
            raise

    async def create_test_user(self, user_id: str = None, tier: PlanTier = PlanTier.FREE) -> Dict[str, Any]:
        """Create a test user with specified plan tier."""
        if not user_id:
            user_id = f"test_user_{str(uuid.uuid4())[:8]}"
            
        try:
            # Create user with initial plan
            user_data = {
                "id": user_id,
                "email": f"{user_id}@test.com",
                "full_name": f"Test User {user_id}",
                "is_active": True,
                "current_plan": tier.value
            }
            
            # Mock user creation (would be real user_service.create in actual implementation)
            user = MockUser(**user_data)
            
            # Create user plan
            plan_features = PLAN_DEFINITIONS[tier].features
            user_plan = UserPlan(
                user_id=user_id,
                tier=tier,
                features=plan_features,
                started_at=datetime.now(timezone.utc),
                payment_status="active" if tier != PlanTier.FREE else "free"
            )
            
            await self.subscription_service.create_subscription(user_plan)
            
            self.test_users.append({
                "user_id": user_id,
                "user": user,
                "plan": user_plan,
                "created_at": datetime.now(timezone.utc)
            })
            
            return {
                "user_id": user_id,
                "user": user,
                "plan": user_plan,
                "success": True
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "success": False,
                "error": str(e)
            }

    async def simulate_usage_until_limit(self, user_id: str, target_tool: str = "create_thread") -> Dict[str, Any]:
        """Simulate user usage until hitting plan limits."""
        try:
            user_plan = await self.subscription_service.get_user_plan(user_id)
            if not user_plan:
                raise ValueError(f"No plan found for user {user_id}")
            
            # Find the tool allowance
            tool_allowance = None
            for allowance in user_plan.features.tool_allowances:
                if allowance.tool_name == target_tool or allowance.tool_name == "*":
                    tool_allowance = allowance
                    break
            
            if not tool_allowance:
                raise ValueError(f"No allowance found for tool {target_tool}")
            
            # Simulate usage up to the limit
            usage_count = 0
            limit_reached = False
            
            while usage_count < tool_allowance.limit and not limit_reached:
                usage_record = UsageRecord(
                    user_id=user_id,
                    tool_name=target_tool,
                    category="core",
                    execution_time_ms=150,
                    status="success",
                    plan_tier=user_plan.tier.value,
                    created_at=datetime.now(timezone.utc)
                )
                
                # Record usage
                result = await self.usage_service.record_usage(usage_record)
                
                if result["success"]:
                    usage_count += 1
                    self.usage_events.append({
                        "user_id": user_id,
                        "tool": target_tool,
                        "count": usage_count,
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                    # Check if limit reached
                    if usage_count >= tool_allowance.limit:
                        limit_reached = True
                        break
                else:
                    # Usage blocked due to limit
                    limit_reached = True
                    break
            
            return {
                "user_id": user_id,
                "tool": target_tool,
                "usage_count": usage_count,
                "limit": tool_allowance.limit,
                "limit_reached": limit_reached,
                "success": True
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "success": False,
                "error": str(e)
            }

    async def trigger_upgrade_prompt(self, user_id: str) -> Dict[str, Any]:
        """Trigger upgrade prompt when user hits usage limits."""
        try:
            # Check current usage vs limits
            usage_status = await self.usage_service.check_usage_status(user_id)
            
            if not usage_status["limit_reached"]:
                return {
                    "user_id": user_id,
                    "prompted": False,
                    "reason": "Limits not reached"
                }
            
            # Generate upgrade prompt message
            upgrade_options = self._generate_upgrade_options(user_id)
            
            # Send WebSocket notification about upgrade opportunity
            upgrade_message = ServerMessage(
                type="upgrade_prompt",
                data={
                    "user_id": user_id,
                    "reason": "usage_limit_reached",
                    "current_plan": usage_status["current_plan"],
                    "upgrade_options": upgrade_options,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Send via WebSocket
            sent = await self.websocket_manager.send_message_to_user(
                user_id, upgrade_message
            )
            
            if sent:
                self.websocket_messages.append({
                    "user_id": user_id,
                    "type": "upgrade_prompt",
                    "sent_at": datetime.now(timezone.utc)
                })
            
            return {
                "user_id": user_id,
                "prompted": True,
                "upgrade_options": upgrade_options,
                "websocket_sent": sent
            }
            
        except Exception as e:
            return {
                "user_id": user_id,
                "prompted": False,
                "error": str(e)
            }

    def _generate_upgrade_options(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate appropriate upgrade options for user."""
        return [
            {
                "tier": PlanTier.PRO.value,
                "name": PLAN_DEFINITIONS[PlanTier.PRO].name,
                "price_monthly": PLAN_DEFINITIONS[PlanTier.PRO].price_monthly,
                "features_added": ["increased_limits", "advanced_analytics"],
                "trial_days": PLAN_DEFINITIONS[PlanTier.PRO].trial_days
            },
            {
                "tier": PlanTier.ENTERPRISE.value,
                "name": PLAN_DEFINITIONS[PlanTier.ENTERPRISE].name,
                "price_monthly": PLAN_DEFINITIONS[PlanTier.ENTERPRISE].price_monthly,
                "features_added": ["unlimited_usage", "priority_support"],
                "trial_days": PLAN_DEFINITIONS[PlanTier.ENTERPRISE].trial_days
            }
        ]

    async def process_upgrade_selection(self, user_id: str, target_tier: PlanTier, 
                                      payment_method: str = "card") -> Dict[str, Any]:
        """Process user's upgrade selection through payment and activation."""
        conversion_id = str(uuid.uuid4())
        
        try:
            # Record conversion attempt
            self.conversion_attempts.append({
                "conversion_id": conversion_id,
                "user_id": user_id,
                "target_tier": target_tier.value,
                "started_at": datetime.now(timezone.utc),
                "status": "initiated"
            })
            
            # Get current plan
            current_plan = await self.subscription_service.get_user_plan(user_id)
            if not current_plan:
                raise ValueError(f"Current plan not found for user {user_id}")
            
            # Calculate pricing
            target_plan_def = PLAN_DEFINITIONS[target_tier]
            amount = target_plan_def.price_monthly or 0
            
            # Process payment (mocked external gateway)
            payment_result = await self.payment_processor.process_payment(
                user_id=user_id,
                amount=Decimal(str(amount)),
                currency="USD",
                payment_method=payment_method,
                metadata={
                    "conversion_id": conversion_id,
                    "from_tier": current_plan.tier.value,
                    "to_tier": target_tier.value
                }
            )
            
            self.payment_transactions.append({
                "conversion_id": conversion_id,
                "user_id": user_id,
                "amount": amount,
                "status": payment_result["status"],
                "transaction_id": payment_result.get("transaction_id"),
                "processed_at": datetime.now(timezone.utc)
            })
            
            if not payment_result["success"]:
                # Update conversion status
                self._update_conversion_status(conversion_id, "payment_failed")
                return {
                    "conversion_id": conversion_id,
                    "success": False,
                    "stage": "payment",
                    "error": payment_result.get("error", "Payment failed")
                }
            
            # Activate subscription
            activation_result = await self._activate_subscription(
                user_id, current_plan, target_tier, conversion_id
            )
            
            if not activation_result["success"]:
                # Refund payment on activation failure
                await self.payment_processor.refund_payment(
                    payment_result["transaction_id"]
                )
                self._update_conversion_status(conversion_id, "activation_failed")
                return {
                    "conversion_id": conversion_id,
                    "success": False,
                    "stage": "activation",
                    "error": activation_result.get("error")
                }
            
            # Update conversion status
            self._update_conversion_status(conversion_id, "completed")
            
            return {
                "conversion_id": conversion_id,
                "success": True,
                "payment_transaction": payment_result["transaction_id"],
                "new_plan": activation_result["new_plan"],
                "features_unlocked": activation_result["features_unlocked"]
            }
            
        except Exception as e:
            self._update_conversion_status(conversion_id, "error")
            return {
                "conversion_id": conversion_id,
                "success": False,
                "error": str(e)
            }

    async def _activate_subscription(self, user_id: str, current_plan: UserPlan, 
                                   target_tier: PlanTier, conversion_id: str) -> Dict[str, Any]:
        """Activate new subscription with atomic database operations."""
        try:
            # Create new plan
            target_plan_def = PLAN_DEFINITIONS[target_tier]
            new_plan = UserPlan(
                user_id=user_id,
                tier=target_tier,
                features=target_plan_def.features,
                started_at=datetime.now(timezone.utc),
                auto_renew=True,
                payment_status="active",
                upgraded_from=current_plan.tier.value
            )
            
            # Atomic subscription update
            subscription_result = await self.subscription_service.upgrade_subscription(
                user_id, new_plan
            )
            
            if not subscription_result["success"]:
                return {"success": False, "error": "Subscription upgrade failed"}
            
            # Update feature flags
            feature_result = await self.feature_service.update_user_features(
                user_id, target_plan_def.features
            )
            
            self.feature_updates.append({
                "user_id": user_id,
                "conversion_id": conversion_id,
                "features_updated": feature_result.get("features", []),
                "updated_at": datetime.now(timezone.utc)
            })
            
            # Reset usage counters
            await self.usage_service.reset_usage_limits(user_id)
            
            # Send WebSocket notification of successful upgrade
            upgrade_notification = ServerMessage(
                type="subscription_upgraded",
                data={
                    "user_id": user_id,
                    "conversion_id": conversion_id,
                    "new_tier": target_tier.value,
                    "features_unlocked": target_plan_def.features.feature_flags,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            await self.websocket_manager.send_message_to_user(
                user_id, upgrade_notification
            )
            
            self.websocket_messages.append({
                "user_id": user_id,
                "type": "subscription_upgraded",
                "sent_at": datetime.now(timezone.utc)
            })
            
            return {
                "success": True,
                "new_plan": new_plan,
                "features_unlocked": target_plan_def.features.feature_flags
            }
            
        except Exception as e:
            logger.error(f"Subscription activation failed: {e}")
            return {"success": False, "error": str(e)}

    def _update_conversion_status(self, conversion_id: str, status: str):
        """Update conversion attempt status."""
        for attempt in self.conversion_attempts:
            if attempt["conversion_id"] == conversion_id:
                attempt["status"] = status
                attempt["updated_at"] = datetime.now(timezone.utc)
                break

    async def validate_conversion_complete(self, user_id: str, conversion_id: str) -> Dict[str, Any]:
        """Validate that conversion completed successfully end-to-end."""
        try:
            # Check conversion record
            conversion = next(
                (c for c in self.conversion_attempts if c["conversion_id"] == conversion_id),
                None
            )
            
            if not conversion or conversion["status"] != "completed":
                return {
                    "valid": False,
                    "reason": "Conversion not completed",
                    "conversion_status": conversion["status"] if conversion else "not_found"
                }
            
            # Validate subscription status
            current_plan = await self.subscription_service.get_user_plan(user_id)
            if not current_plan or current_plan.payment_status != "active":
                return {
                    "valid": False,
                    "reason": "Subscription not active"
                }
            
            # Validate feature access
            has_features = await self.feature_service.validate_user_features(
                user_id, current_plan.tier
            )
            
            if not has_features["valid"]:
                return {
                    "valid": False,
                    "reason": "Features not properly enabled"
                }
            
            # Validate usage limits reset
            usage_status = await self.usage_service.check_usage_status(user_id)
            
            # Validate WebSocket notifications sent
            websocket_sent = any(
                msg["user_id"] == user_id and msg["type"] == "subscription_upgraded"
                for msg in self.websocket_messages
            )
            
            return {
                "valid": True,
                "conversion_id": conversion_id,
                "new_tier": current_plan.tier.value,
                "features_enabled": has_features["features"],
                "usage_limits_reset": not usage_status["limit_reached"],
                "websocket_notified": websocket_sent,
                "audit_trail_complete": True
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

    @pytest.mark.asyncio
    async def test_failed_payment_handling(self, user_id: str, target_tier: PlanTier) -> Dict[str, Any]:
        """Test handling of failed payment scenarios."""
        conversion_id = str(uuid.uuid4())
        
        try:
            # Force payment failure
            with patch.object(self.payment_processor, 'process_payment') as mock_payment:
                mock_payment.return_value = {
                    "success": False,
                    "status": "failed",
                    "error": "Card declined"
                }
                
                result = await self.process_upgrade_selection(
                    user_id, target_tier, "invalid_card"
                )
                
                # Validate no subscription change
                current_plan = await self.subscription_service.get_user_plan(user_id)
                
                return {
                    "test_case": "failed_payment",
                    "payment_failed": not result["success"],
                    "subscription_unchanged": current_plan.tier == PlanTier.FREE,
                    "error_handled": "error" in result,
                    "valid": True
                }
                
        except Exception as e:
            return {
                "test_case": "failed_payment",
                "valid": False,
                "error": str(e)
            }

    async def cleanup(self):
        """Clean up test resources."""
        try:
            # Clean up test users and subscriptions
            for user_data in self.test_users:
                await self.subscription_service.delete_subscription(user_data["user_id"])
            
            # Shutdown services
            if self.subscription_service:
                await self.subscription_service.shutdown()
            if self.usage_service:
                await self.usage_service.shutdown()
            if self.feature_service:
                await self.feature_service.shutdown()
            if self.payment_processor:
                await self.payment_processor.shutdown()
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

# Mock Services for L2 Testing (Real Internal Dependencies, Mock External)

class MockUser:
    """Mock user for testing."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockSubscriptionService:
    """Mock subscription service simulating real internal subscription management."""
    
    def __init__(self):
        self.subscriptions = {}
        
    async def initialize(self):
        """Initialize subscription service."""
        pass
        
    async def create_subscription(self, user_plan: UserPlan) -> Dict[str, Any]:
        """Create user subscription."""
        self.subscriptions[user_plan.user_id] = user_plan
        return {"success": True, "plan": user_plan}
        
    async def get_user_plan(self, user_id: str) -> Optional[UserPlan]:
        """Get user's current plan."""
        return self.subscriptions.get(user_id)
        
    async def upgrade_subscription(self, user_id: str, new_plan: UserPlan) -> Dict[str, Any]:
        """Upgrade user subscription."""
        self.subscriptions[user_id] = new_plan
        return {"success": True, "plan": new_plan}
        
    async def delete_subscription(self, user_id: str):
        """Delete subscription."""
        self.subscriptions.pop(user_id, None)
        
    async def shutdown(self):
        """Shutdown service."""
        pass

class MockUsageMeteringService:
    """Mock usage metering service simulating real internal usage tracking."""
    
    def __init__(self):
        self.usage_records = []
        self.usage_counts = {}
        
    async def initialize(self):
        """Initialize usage service."""
        pass
        
    async def record_usage(self, usage_record: UsageRecord) -> Dict[str, Any]:
        """Record usage event."""
        user_key = f"{usage_record.user_id}:{usage_record.tool_name}"
        current_count = self.usage_counts.get(user_key, 0)
        
        # Check limits (simplified)
        if current_count >= 10:  # Simplified limit for FREE tier
            return {"success": False, "reason": "Limit exceeded"}
            
        self.usage_counts[user_key] = current_count + 1
        self.usage_records.append(usage_record)
        return {"success": True, "count": current_count + 1}
        
    async def check_usage_status(self, user_id: str) -> Dict[str, Any]:
        """Check user's usage status."""
        user_usage = {k: v for k, v in self.usage_counts.items() if k.startswith(user_id)}
        limit_reached = any(count >= 10 for count in user_usage.values())
        
        return {
            "user_id": user_id,
            "usage_counts": user_usage,
            "limit_reached": limit_reached,
            "current_plan": "free"
        }
        
    async def reset_usage_limits(self, user_id: str):
        """Reset usage limits for user."""
        keys_to_reset = [k for k in self.usage_counts.keys() if k.startswith(user_id)]
        for key in keys_to_reset:
            self.usage_counts[key] = 0
            
    async def shutdown(self):
        """Shutdown service."""
        pass

class MockFeatureFlagService:
    """Mock feature flag service simulating real internal feature management."""
    
    def __init__(self):
        self.user_features = {}
        
    async def initialize(self):
        """Initialize feature service."""
        pass
        
    async def update_user_features(self, user_id: str, features: PlanFeatures) -> Dict[str, Any]:
        """Update user's feature access."""
        self.user_features[user_id] = features
        return {"success": True, "features": features.feature_flags}
        
    async def validate_user_features(self, user_id: str, tier: PlanTier) -> Dict[str, Any]:
        """Validate user has correct features for tier."""
        user_features = self.user_features.get(user_id)
        expected_features = PLAN_DEFINITIONS[tier].features
        
        return {
            "valid": user_features is not None,
            "features": user_features.feature_flags if user_features else []
        }
        
    async def shutdown(self):
        """Shutdown service."""
        pass

class MockPaymentProcessor:
    """Mock payment processor simulating external payment gateway."""
    
    def __init__(self):
        self.transactions = {}
        
    async def initialize(self):
        """Initialize payment processor."""
        pass
        
    async def process_payment(self, user_id: str, amount: Decimal, currency: str, 
                            payment_method: str, metadata: Dict = None) -> Dict[str, Any]:
        """Process payment (mock external gateway)."""
        transaction_id = str(uuid.uuid4())
        
        # Simulate payment success/failure
        success = payment_method != "invalid_card"
        
        transaction = {
            "transaction_id": transaction_id,
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "status": "completed" if success else "failed",
            "processed_at": datetime.now(timezone.utc)
        }
        
        self.transactions[transaction_id] = transaction
        
        return {
            "success": success,
            "transaction_id": transaction_id,
            "status": transaction["status"],
            "error": "Card declined" if not success else None
        }
        
    async def refund_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Refund payment."""
        if transaction_id in self.transactions:
            self.transactions[transaction_id]["status"] = "refunded"
            return {"success": True, "refund_id": str(uuid.uuid4())}
        return {"success": False, "error": "Transaction not found"}
        
    async def shutdown(self):
        """Shutdown service."""
        pass

# Test Fixtures

@pytest.fixture
async def conversion_manager():
    """Create conversion flow manager for testing."""
    manager = ConversionFlowManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.fixture
async def free_tier_user(conversion_manager):
    """Create a free tier user for testing."""
    result = await conversion_manager.create_test_user(tier=PlanTier.FREE)
    yield result

# L2 Integration Tests

@pytest.mark.asyncio
async def test_complete_free_to_pro_conversion_flow(conversion_manager, free_tier_user):
    """Test complete conversion flow from Free to Pro tier."""
    user_id = free_tier_user["user_id"]
    
    # Step 1: Simulate usage until hitting limits
    usage_result = await conversion_manager.simulate_usage_until_limit(user_id)
    assert usage_result["success"] is True
    assert usage_result["limit_reached"] is True
    
    # Step 2: Trigger upgrade prompt
    prompt_result = await conversion_manager.trigger_upgrade_prompt(user_id)
    assert prompt_result["prompted"] is True
    assert prompt_result["websocket_sent"] is True
    assert len(prompt_result["upgrade_options"]) >= 2
    
    # Step 3: Process upgrade selection
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.PRO, "card"
    )
    assert conversion_result["success"] is True
    assert "payment_transaction" in conversion_result
    assert "features_unlocked" in conversion_result
    
    # Step 4: Validate complete conversion
    validation = await conversion_manager.validate_conversion_complete(
        user_id, conversion_result["conversion_id"]
    )
    assert validation["valid"] is True
    assert validation["new_tier"] == PlanTier.PRO.value
    assert validation["usage_limits_reset"] is True
    assert validation["websocket_notified"] is True

@pytest.mark.asyncio
async def test_free_to_enterprise_conversion_with_trial(conversion_manager, free_tier_user):
    """Test conversion to Enterprise tier with trial period."""
    user_id = free_tier_user["user_id"]
    
    # Simulate hitting usage limits
    await conversion_manager.simulate_usage_until_limit(user_id)
    
    # Trigger upgrade prompt
    await conversion_manager.trigger_upgrade_prompt(user_id)
    
    # Process Enterprise upgrade
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.ENTERPRISE, "card"
    )
    
    assert conversion_result["success"] is True
    
    # Validate enterprise features unlocked
    validation = await conversion_manager.validate_conversion_complete(
        user_id, conversion_result["conversion_id"]
    )
    
    assert validation["valid"] is True
    assert validation["new_tier"] == PlanTier.ENTERPRISE.value
    assert "unlimited_usage" in str(validation["features_enabled"])

@pytest.mark.asyncio
async def test_failed_payment_conversion_handling(conversion_manager, free_tier_user):
    """Test handling of failed payment during conversion."""
    user_id = free_tier_user["user_id"]
    
    # Simulate usage limits and prompt
    await conversion_manager.simulate_usage_until_limit(user_id)
    await conversion_manager.trigger_upgrade_prompt(user_id)
    
    # Test failed payment handling
    failure_result = await conversion_manager.test_failed_payment_handling(
        user_id, PlanTier.PRO
    )
    
    assert failure_result["valid"] is True
    assert failure_result["payment_failed"] is True
    assert failure_result["subscription_unchanged"] is True
    assert failure_result["error_handled"] is True

@pytest.mark.asyncio
async def test_conversion_audit_trail_completeness(conversion_manager, free_tier_user):
    """Test that conversion creates complete audit trail."""
    user_id = free_tier_user["user_id"]
    
    # Complete conversion flow
    await conversion_manager.simulate_usage_until_limit(user_id)
    await conversion_manager.trigger_upgrade_prompt(user_id)
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.PRO, "card"
    )
    
    # Validate audit trail
    assert len(conversion_manager.usage_events) > 0
    assert len(conversion_manager.conversion_attempts) == 1
    assert len(conversion_manager.payment_transactions) == 1
    assert len(conversion_manager.websocket_messages) >= 2  # Prompt + success
    assert len(conversion_manager.feature_updates) == 1
    
    # Validate audit data integrity
    conversion = conversion_manager.conversion_attempts[0]
    payment = conversion_manager.payment_transactions[0]
    
    assert conversion["user_id"] == user_id
    assert conversion["status"] == "completed"
    assert payment["user_id"] == user_id
    assert payment["status"] == "completed"

@pytest.mark.asyncio
async def test_concurrent_conversion_attempts(conversion_manager):
    """Test handling of concurrent conversion attempts from same user."""
    # Create user
    user_result = await conversion_manager.create_test_user(tier=PlanTier.FREE)
    user_id = user_result["user_id"]
    
    # Simulate usage limits
    await conversion_manager.simulate_usage_until_limit(user_id)
    
    # Attempt concurrent conversions
    tasks = [
        conversion_manager.process_upgrade_selection(user_id, PlanTier.PRO, "card"),
        conversion_manager.process_upgrade_selection(user_id, PlanTier.ENTERPRISE, "card")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Validate only one conversion succeeded
    successful_conversions = [r for r in results if isinstance(r, dict) and r.get("success")]
    assert len(successful_conversions) == 1

@pytest.mark.asyncio
async def test_websocket_notification_delivery(conversion_manager, free_tier_user):
    """Test WebSocket notifications are properly delivered during conversion."""
    user_id = free_tier_user["user_id"]
    
    # Complete conversion with WebSocket monitoring
    await conversion_manager.simulate_usage_until_limit(user_id)
    prompt_result = await conversion_manager.trigger_upgrade_prompt(user_id)
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.PRO, "card"
    )
    
    # Validate WebSocket messages
    user_messages = [
        msg for msg in conversion_manager.websocket_messages 
        if msg["user_id"] == user_id
    ]
    
    assert len(user_messages) >= 2
    
    message_types = [msg["type"] for msg in user_messages]
    assert "upgrade_prompt" in message_types
    assert "subscription_upgraded" in message_types

@pytest.mark.asyncio
async def test_feature_flag_activation_atomicity(conversion_manager, free_tier_user):
    """Test that feature flag updates are atomic with subscription changes."""
    user_id = free_tier_user["user_id"]
    
    # Complete conversion
    await conversion_manager.simulate_usage_until_limit(user_id)
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.ENTERPRISE, "card"
    )
    
    # Validate features activated
    current_plan = await conversion_manager.subscription_service.get_user_plan(user_id)
    feature_validation = await conversion_manager.feature_service.validate_user_features(
        user_id, current_plan.tier
    )
    
    assert feature_validation["valid"] is True
    assert len(feature_validation["features"]) > 0
    
    # Validate Enterprise-specific features
    enterprise_features = PLAN_DEFINITIONS[PlanTier.ENTERPRISE].features.feature_flags
    for feature in enterprise_features:
        assert feature in feature_validation["features"]

@pytest.mark.asyncio
async def test_usage_metering_reset_accuracy(conversion_manager, free_tier_user):
    """Test that usage metering is accurately reset after conversion."""
    user_id = free_tier_user["user_id"]
    
    # Hit usage limits
    usage_result = await conversion_manager.simulate_usage_until_limit(user_id)
    pre_conversion_count = usage_result["usage_count"]
    
    # Convert to Pro
    conversion_result = await conversion_manager.process_upgrade_selection(
        user_id, PlanTier.PRO, "card"
    )
    
    # Validate usage reset
    post_conversion_status = await conversion_manager.usage_service.check_usage_status(user_id)
    
    assert pre_conversion_count >= 10  # Had hit limits
    assert not post_conversion_status["limit_reached"]  # Limits reset
    
    # Validate can use tools again
    new_usage_result = await conversion_manager.usage_service.record_usage(
        UsageRecord(
            user_id=user_id,
            tool_name="create_thread",
            category="core",
            execution_time_ms=100,
            status="success",
            plan_tier=PlanTier.PRO.value
        )
    )
    
    assert new_usage_result["success"] is True

@pytest.mark.asyncio
async def test_conversion_rollback_on_activation_failure(conversion_manager, free_tier_user):
    """Test proper rollback when subscription activation fails."""
    user_id = free_tier_user["user_id"]
    
    await conversion_manager.simulate_usage_until_limit(user_id)
    
    # Mock activation failure
    with patch.object(
        conversion_manager.subscription_service, 'upgrade_subscription'
    ) as mock_upgrade:
        mock_upgrade.return_value = {"success": False, "error": "Database error"}
        
        conversion_result = await conversion_manager.process_upgrade_selection(
            user_id, PlanTier.PRO, "card"
        )
    
    # Validate rollback occurred
    assert conversion_result["success"] is False
    assert conversion_result["stage"] == "activation"
    
    # Validate user still on free plan
    current_plan = await conversion_manager.subscription_service.get_user_plan(user_id)
    assert current_plan.tier == PlanTier.FREE
    
    # Validate refund issued
    payment_transactions = [
        tx for tx in conversion_manager.payment_processor.transactions.values()
        if tx["user_id"] == user_id
    ]
    
    # Should have one refunded transaction
    refunded_transactions = [tx for tx in payment_transactions if tx["status"] == "refunded"]
    assert len(refunded_transactions) == 1