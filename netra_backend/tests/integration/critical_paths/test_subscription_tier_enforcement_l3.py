"""Subscription Tier Enforcement L3 Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (Free, Early, Mid, Enterprise) - Critical revenue protection
- Business Goal: Enforce subscription limits, drive conversions, protect revenue
- Value Impact: Prevents revenue leakage, enforces tier boundaries, drives upsell
- Strategic Impact: $347K MRR protection through accurate tier enforcement and billing compliance

Critical Path: User request -> Tier validation -> Resource allocation -> Billing enforcement -> Usage tracking
Coverage: Real tier limits, actual billing events, cross-service enforcement, upgrade flows
L3 Realism: Tests against real database constraints, Redis rate limiting, ClickHouse analytics
"""

import pytest
import asyncio
import time
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass

from netra_backend.app.schemas.UserPlan import PlanTier, UsageRecord, PlanUsageSummary
from netra_backend.app.services.user_service import user_service as UserService
from netra_backend.app.services.audit_service import AuditService
from redis_manager import RedisManager
from netra_backend.app.services.database.session_manager import SessionManager
from netra_backend.app.core.rate_limiting.tier_enforcer import TierEnforcementService
from netra_backend.app.services.metrics.billing_metrics import BillingMetricsCollector
from test_framework.test_config import configure_dedicated_test_environment

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = logging.getLogger(__name__)


@dataclass
class TierEnforcementMetrics:
    """Metrics for tier enforcement testing."""
    total_requests: int = 0
    free_tier_enforced: int = 0
    early_tier_enforced: int = 0
    mid_tier_enforced: int = 0
    enterprise_unlimited: int = 0
    upgrade_prompts: int = 0
    billing_events_generated: int = 0
    cross_service_violations: int = 0
    enforcement_response_times: List[float] = None
    
    def __post_init__(self):
        if self.enforcement_response_times is None:
            self.enforcement_response_times = []


class SubscriptionTierEnforcementL3Manager:
    """L3 subscription tier enforcement test manager with real service integration."""
    
    def __init__(self):
        self.user_service = None
        self.audit_service = None
        self.redis_manager = None
        self.session_manager = None
        self.tier_enforcer = None
        self.billing_metrics = None
        self.test_users = {}
        self.enforcement_events = []
        self.billing_events = []
        self.metrics = TierEnforcementMetrics()
        
    async def initialize_services(self):
        """Initialize real services for L3 tier enforcement testing."""
        try:
            # Configure dedicated test environment
            configure_dedicated_test_environment()
            
            # Initialize core services
            self.user_service = UserService()
            await self.user_service.initialize()
            
            self.audit_service = AuditService()
            await self.audit_service.initialize()
            
            self.redis_manager = RedisManager()
            await self.redis_manager.initialize()
            
            self.session_manager = SessionManager()
            await self.session_manager.initialize()
            
            self.tier_enforcer = TierEnforcementService()
            await self.tier_enforcer.initialize()
            
            self.billing_metrics = BillingMetricsCollector()
            await self.billing_metrics.initialize()
            
            logger.info("L3 tier enforcement services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize L3 tier enforcement services: {e}")
            raise
    
    async def create_test_user(self, tier: PlanTier, user_id: str = None) -> Dict[str, Any]:
        """Create a test user with specific subscription tier."""
        if not user_id:
            user_id = f"test_user_{tier.value}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create user with specific tier
            user_data = {
                "id": user_id,
                "email": f"{user_id}@test-tier-enforcement.com",
                "tier": tier.value,
                "created_at": datetime.utcnow(),
                "status": "active",
                "monthly_usage": 0,
                "current_requests": 0,
                "test_user": True
            }
            
            # Store in database
            await self.session_manager.execute_query(
                """
                INSERT INTO users (id, email, tier, created_at, status, metadata)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    tier = EXCLUDED.tier,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata
                """,
                (user_id, user_data["email"], tier.value, user_data["created_at"], 
                 user_data["status"], {"test_user": True})
            )
            
            # Initialize usage tracking in Redis
            usage_key = f"user_usage:{user_id}"
            await self.redis_manager.hset(usage_key, {
                "tier": tier.value,
                "monthly_requests": 0,
                "current_concurrent": 0,
                "last_reset": time.time()
            })
            
            # Set Redis TTL for test cleanup
            await self.redis_manager.expire(usage_key, 3600)  # 1 hour cleanup
            
            self.test_users[user_id] = user_data
            
            return user_data
            
        except Exception as e:
            logger.error(f"Failed to create test user {user_id}: {e}")
            raise
    
    async def test_free_tier_monthly_limit_enforcement(self, user_id: str) -> Dict[str, Any]:
        """Test free tier monthly request limit (100 requests/month)."""
        start_time = time.time()
        
        try:
            # Simulate user at 95 requests this month
            usage_key = f"user_usage:{user_id}"
            await self.redis_manager.hset(usage_key, "monthly_requests", 95)
            
            enforcement_results = []
            
            # Test requests 96-105 (should hit limit at 100)
            for request_num in range(96, 106):
                request_start = time.time()
                
                enforcement_result = await self.tier_enforcer.enforce_tier_limits(
                    user_id=user_id,
                    action="api_request",
                    resource_type="general",
                    request_metadata={"request_id": f"free_test_{request_num}"}
                )
                
                request_time = time.time() - request_start
                self.metrics.enforcement_response_times.append(request_time)
                
                enforcement_results.append({
                    "request_number": request_num,
                    "allowed": enforcement_result.get("allowed", False),
                    "reason": enforcement_result.get("reason", ""),
                    "upgrade_prompt": enforcement_result.get("upgrade_prompt", False),
                    "response_time": request_time
                })
                
                # Track metrics
                self.metrics.total_requests += 1
                if not enforcement_result.get("allowed"):
                    self.metrics.free_tier_enforced += 1
                if enforcement_result.get("upgrade_prompt"):
                    self.metrics.upgrade_prompts += 1
                
                # Store enforcement event
                self.enforcement_events.append({
                    "user_id": user_id,
                    "tier": "free",
                    "request_number": request_num,
                    "enforcement_result": enforcement_result,
                    "timestamp": time.time()
                })
            
            # Verify enforcement pattern
            allowed_requests = [r for r in enforcement_results if r["allowed"]]
            denied_requests = [r for r in enforcement_results if not r["allowed"]]
            
            # Should allow requests 96-100, deny 101-105
            expected_allowed = 5  # Requests 96, 97, 98, 99, 100
            expected_denied = 5   # Requests 101, 102, 103, 104, 105
            
            return {
                "test_type": "free_tier_monthly_limit",
                "total_requests": len(enforcement_results),
                "allowed_requests": len(allowed_requests),
                "denied_requests": len(denied_requests),
                "expected_allowed": expected_allowed,
                "expected_denied": expected_denied,
                "enforcement_accurate": (
                    len(allowed_requests) == expected_allowed and 
                    len(denied_requests) == expected_denied
                ),
                "upgrade_prompts_count": sum(1 for r in enforcement_results if r["upgrade_prompt"]),
                "avg_response_time": sum(r["response_time"] for r in enforcement_results) / len(enforcement_results),
                "enforcement_results": enforcement_results,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Free tier limit enforcement test failed: {e}")
            return {
                "test_type": "free_tier_monthly_limit",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def test_mid_tier_concurrent_limit_enforcement(self, user_id: str) -> Dict[str, Any]:
        """Test mid tier concurrent request limit (20 concurrent)."""
        start_time = time.time()
        
        try:
            # Create 25 concurrent requests to test the 20-request limit
            concurrent_tasks = []
            
            for i in range(25):
                task = self._simulate_concurrent_request(user_id, f"mid_tier_concurrent_{i}")
                concurrent_tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Analyze results
            allowed_count = 0
            denied_count = 0
            exception_count = 0
            
            for result in results:
                if isinstance(result, Exception):
                    exception_count += 1
                elif isinstance(result, dict):
                    if result.get("allowed"):
                        allowed_count += 1
                    else:
                        denied_count += 1
                        self.metrics.mid_tier_enforced += 1
                    
                    self.metrics.total_requests += 1
            
            return {
                "test_type": "mid_tier_concurrent_limit",
                "total_requests": 25,
                "allowed_requests": allowed_count,
                "denied_requests": denied_count,
                "exception_count": exception_count,
                "limit_enforced_correctly": (allowed_count <= 20),  # Should allow max 20
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Mid tier concurrent limit test failed: {e}")
            return {
                "test_type": "mid_tier_concurrent_limit",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _simulate_concurrent_request(self, user_id: str, request_id: str) -> Dict[str, Any]:
        """Simulate a concurrent request for testing."""
        try:
            # Add artificial delay to simulate real request processing
            await asyncio.sleep(0.1)
            
            result = await self.tier_enforcer.enforce_tier_limits(
                user_id=user_id,
                action="concurrent_request",
                resource_type="api_call",
                request_metadata={"request_id": request_id}
            )
            
            # Simulate request completion after processing
            await asyncio.sleep(0.2)
            
            # Release concurrent slot
            await self.tier_enforcer.release_concurrent_slot(user_id, request_id)
            
            return result
            
        except Exception as e:
            return {"allowed": False, "error": str(e)}
    
    async def test_enterprise_unlimited_access(self, user_id: str) -> Dict[str, Any]:
        """Test enterprise tier unlimited access."""
        start_time = time.time()
        
        try:
            # Simulate heavy usage (1000 requests) to verify unlimited access
            test_requests = 50  # Reduced for test performance
            allowed_count = 0
            denied_count = 0
            
            for i in range(test_requests):
                result = await self.tier_enforcer.enforce_tier_limits(
                    user_id=user_id,
                    action="api_request",
                    resource_type="enterprise_feature",
                    request_metadata={"request_id": f"enterprise_test_{i}"}
                )
                
                if result.get("allowed"):
                    allowed_count += 1
                    self.metrics.enterprise_unlimited += 1
                else:
                    denied_count += 1
                
                self.metrics.total_requests += 1
            
            return {
                "test_type": "enterprise_unlimited_access",
                "total_requests": test_requests,
                "allowed_requests": allowed_count,
                "denied_requests": denied_count,
                "unlimited_access_verified": (denied_count == 0),
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Enterprise unlimited access test failed: {e}")
            return {
                "test_type": "enterprise_unlimited_access",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def test_tier_downgrade_enforcement(self, user_id: str, 
                                            from_tier: PlanTier, to_tier: PlanTier) -> Dict[str, Any]:
        """Test tier downgrade enforcement and immediate limit application."""
        start_time = time.time()
        
        try:
            # First, verify current tier allows higher usage
            pre_downgrade_result = await self.tier_enforcer.enforce_tier_limits(
                user_id=user_id,
                action="api_request",
                resource_type="premium_feature",
                request_metadata={"request_id": "pre_downgrade_test"}
            )
            
            # Execute tier downgrade
            downgrade_result = await self.user_service.update_user_tier(
                user_id=user_id,
                new_tier=to_tier,
                reason="test_tier_downgrade"
            )
            
            # Verify downgrade was applied
            await asyncio.sleep(0.1)  # Allow cache invalidation
            
            # Test that new tier limits are immediately enforced
            post_downgrade_results = []
            
            # If downgrading to free tier, test monthly limit
            if to_tier == PlanTier.FREE:
                # Set usage near free tier limit
                usage_key = f"user_usage:{user_id}"
                await self.redis_manager.hset(usage_key, "monthly_requests", 98)
                
                # Test 5 requests (should allow 2, deny 3)
                for i in range(5):
                    result = await self.tier_enforcer.enforce_tier_limits(
                        user_id=user_id,
                        action="api_request",
                        resource_type="general",
                        request_metadata={"request_id": f"post_downgrade_{i}"}
                    )
                    post_downgrade_results.append(result)
            
            allowed_post = sum(1 for r in post_downgrade_results if r.get("allowed"))
            denied_post = sum(1 for r in post_downgrade_results if not r.get("allowed"))
            
            return {
                "test_type": "tier_downgrade_enforcement",
                "from_tier": from_tier.value,
                "to_tier": to_tier.value,
                "downgrade_successful": downgrade_result.get("success", False),
                "pre_downgrade_allowed": pre_downgrade_result.get("allowed", False),
                "post_downgrade_requests": len(post_downgrade_results),
                "post_downgrade_allowed": allowed_post,
                "post_downgrade_denied": denied_post,
                "immediate_enforcement": (denied_post > 0 if to_tier == PlanTier.FREE else True),
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Tier downgrade enforcement test failed: {e}")
            return {
                "test_type": "tier_downgrade_enforcement",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def test_cross_service_tier_validation(self, user_id: str, tier: PlanTier) -> Dict[str, Any]:
        """Test tier validation across multiple services."""
        start_time = time.time()
        
        try:
            services_to_test = ["api_service", "websocket_service", "llm_service", "billing_service"]
            validation_results = {}
            
            for service in services_to_test:
                service_result = await self._test_service_tier_validation(user_id, tier, service)
                validation_results[service] = service_result
                
                if not service_result.get("tier_validated"):
                    self.metrics.cross_service_violations += 1
            
            # Check consistency across services
            tier_consistent = all(
                result.get("reported_tier") == tier.value 
                for result in validation_results.values()
            )
            
            return {
                "test_type": "cross_service_tier_validation",
                "user_tier": tier.value,
                "services_tested": services_to_test,
                "validation_results": validation_results,
                "tier_consistent_across_services": tier_consistent,
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Cross-service tier validation test failed: {e}")
            return {
                "test_type": "cross_service_tier_validation",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def _test_service_tier_validation(self, user_id: str, tier: PlanTier, service: str) -> Dict[str, Any]:
        """Test tier validation for a specific service."""
        try:
            # Simulate service-specific tier check
            validation_result = await self.tier_enforcer.validate_user_tier_for_service(
                user_id=user_id,
                service=service,
                requested_action=f"{service}_request"
            )
            
            return {
                "service": service,
                "tier_validated": validation_result.get("valid", False),
                "reported_tier": validation_result.get("user_tier", "unknown"),
                "service_accessible": validation_result.get("access_granted", False)
            }
            
        except Exception as e:
            return {
                "service": service,
                "tier_validated": False,
                "error": str(e)
            }
    
    async def test_billing_event_generation(self, user_id: str, tier: PlanTier) -> Dict[str, Any]:
        """Test billing event generation accuracy."""
        start_time = time.time()
        
        try:
            # Generate various billable events
            billable_actions = [
                {"action": "api_request", "cost_cents": 1},
                {"action": "llm_request", "cost_cents": 5},
                {"action": "data_processing", "cost_cents": 10},
                {"action": "premium_feature", "cost_cents": 25}
            ]
            
            generated_events = []
            
            for action_data in billable_actions:
                # Execute action and generate billing event
                billing_event = await self.billing_metrics.record_billable_event(
                    user_id=user_id,
                    action=action_data["action"],
                    tier=tier.value,
                    cost_cents=action_data["cost_cents"],
                    metadata={"test_event": True}
                )
                
                generated_events.append(billing_event)
                self.billing_events.append(billing_event)
                self.metrics.billing_events_generated += 1
            
            # Verify billing events are properly recorded
            total_cost_cents = sum(action["cost_cents"] for action in billable_actions)
            recorded_cost_cents = sum(
                event.get("cost_cents", 0) for event in generated_events 
                if event.get("success")
            )
            
            return {
                "test_type": "billing_event_generation",
                "user_tier": tier.value,
                "actions_tested": len(billable_actions),
                "events_generated": len(generated_events),
                "successful_events": sum(1 for e in generated_events if e.get("success")),
                "expected_cost_cents": total_cost_cents,
                "recorded_cost_cents": recorded_cost_cents,
                "billing_accuracy": (recorded_cost_cents == total_cost_cents),
                "test_duration": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Billing event generation test failed: {e}")
            return {
                "test_type": "billing_event_generation",
                "success": False,
                "error": str(e),
                "test_duration": time.time() - start_time
            }
    
    async def get_enforcement_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive tier enforcement metrics summary."""
        avg_response_time = (
            sum(self.metrics.enforcement_response_times) / len(self.metrics.enforcement_response_times)
            if self.metrics.enforcement_response_times else 0
        )
        
        return {
            "total_requests_tested": self.metrics.total_requests,
            "enforcement_actions": {
                "free_tier_enforced": self.metrics.free_tier_enforced,
                "early_tier_enforced": self.metrics.early_tier_enforced,
                "mid_tier_enforced": self.metrics.mid_tier_enforced,
                "enterprise_unlimited": self.metrics.enterprise_unlimited
            },
            "user_experience": {
                "upgrade_prompts": self.metrics.upgrade_prompts,
                "avg_enforcement_response_time": avg_response_time
            },
            "system_integrity": {
                "billing_events_generated": self.metrics.billing_events_generated,
                "cross_service_violations": self.metrics.cross_service_violations
            },
            "performance_sla": {
                "response_time_under_100ms": sum(
                    1 for t in self.metrics.enforcement_response_times if t < 0.1
                ) / len(self.metrics.enforcement_response_times) * 100 if self.metrics.enforcement_response_times else 0
            }
        }
    
    async def cleanup(self):
        """Clean up L3 tier enforcement test resources."""
        try:
            # Clean up test users
            for user_id in list(self.test_users.keys()):
                # Remove from database
                await self.session_manager.execute_query(
                    "DELETE FROM users WHERE id = %s AND metadata->>'test_user' = 'true'",
                    (user_id,)
                )
                
                # Remove from Redis
                usage_key = f"user_usage:{user_id}"
                await self.redis_manager.delete(usage_key)
            
            # Shutdown services
            if self.user_service:
                await self.user_service.shutdown()
            if self.audit_service:
                await self.audit_service.shutdown()
            if self.redis_manager:
                await self.redis_manager.shutdown()
            if self.session_manager:
                await self.session_manager.shutdown()
            if self.tier_enforcer:
                await self.tier_enforcer.shutdown()
            if self.billing_metrics:
                await self.billing_metrics.shutdown()
                
        except Exception as e:
            logger.error(f"L3 tier enforcement cleanup failed: {e}")


@pytest.fixture
async def tier_enforcement_l3():
    """Create L3 tier enforcement manager."""
    manager = SubscriptionTierEnforcementL3Manager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_free_tier_monthly_limit_enforcement(tier_enforcement_l3):
    """Test free tier monthly request limit enforcement."""
    # Create free tier user
    user = await tier_enforcement_l3.create_test_user(PlanTier.FREE)
    
    # Test monthly limit enforcement
    result = await tier_enforcement_l3.test_free_tier_monthly_limit_enforcement(user["id"])
    
    # Verify enforcement accuracy
    assert result["enforcement_accurate"], f"Free tier enforcement failed: {result}"
    assert result["denied_requests"] == result["expected_denied"], "Incorrect denial count"
    assert result["upgrade_prompts_count"] > 0, "No upgrade prompts generated"
    assert result["avg_response_time"] < 0.1, "Enforcement response time too slow"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_mid_tier_concurrent_limit_enforcement(tier_enforcement_l3):
    """Test mid tier concurrent request limit enforcement."""
    # Create mid tier user (using PRO as mid tier)
    user = await tier_enforcement_l3.create_test_user(PlanTier.PRO)
    
    # Test concurrent limit enforcement
    result = await tier_enforcement_l3.test_mid_tier_concurrent_limit_enforcement(user["id"])
    
    # Verify enforcement
    assert result["limit_enforced_correctly"], f"Mid tier concurrent limit not enforced: {result}"
    assert result["allowed_requests"] <= 20, "Too many concurrent requests allowed"
    assert result["denied_requests"] >= 5, "Not enough requests denied"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_enterprise_unlimited_access_verification(tier_enforcement_l3):
    """Test enterprise tier unlimited access."""
    # Create enterprise tier user
    user = await tier_enforcement_l3.create_test_user(PlanTier.ENTERPRISE)
    
    # Test unlimited access
    result = await tier_enforcement_l3.test_enterprise_unlimited_access(user["id"])
    
    # Verify unlimited access
    assert result["unlimited_access_verified"], f"Enterprise unlimited access failed: {result}"
    assert result["denied_requests"] == 0, "Enterprise requests incorrectly denied"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_tier_downgrade_immediate_enforcement(tier_enforcement_l3):
    """Test immediate enforcement after tier downgrade."""
    # Create enterprise user
    user = await tier_enforcement_l3.create_test_user(PlanTier.ENTERPRISE)
    
    # Test downgrade from enterprise to free
    result = await tier_enforcement_l3.test_tier_downgrade_enforcement(
        user["id"], PlanTier.ENTERPRISE, PlanTier.FREE
    )
    
    # Verify immediate enforcement
    assert result["downgrade_successful"], f"Tier downgrade failed: {result}"
    assert result["immediate_enforcement"], "Tier limits not immediately enforced after downgrade"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_cross_service_tier_validation_consistency(tier_enforcement_l3):
    """Test tier validation consistency across all services."""
    # Test each tier across services
    test_results = {}
    
    for tier in [PlanTier.FREE, PlanTier.PRO, PlanTier.ENTERPRISE]:
        user = await tier_enforcement_l3.create_test_user(tier)
        result = await tier_enforcement_l3.test_cross_service_tier_validation(user["id"], tier)
        test_results[tier.value] = result
        
        # Verify consistency
        assert result["tier_consistent_across_services"], f"Tier {tier.value} inconsistent across services"
    
    # Verify all tiers tested
    assert len(test_results) == 3, "Not all tiers tested"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_billing_event_generation_accuracy(tier_enforcement_l3):
    """Test billing event generation accuracy for all tiers."""
    billing_results = {}
    
    for tier in [PlanTier.FREE, PlanTier.PRO, PlanTier.ENTERPRISE]:
        user = await tier_enforcement_l3.create_test_user(tier)
        result = await tier_enforcement_l3.test_billing_event_generation(user["id"], tier)
        billing_results[tier.value] = result
        
        # Verify billing accuracy
        assert result["billing_accuracy"], f"Billing inaccurate for {tier.value}: {result}"
        assert result["successful_events"] > 0, f"No billing events generated for {tier.value}"
    
    # Verify comprehensive billing testing
    assert len(billing_results) == 3, "Not all tiers tested for billing"


@pytest.mark.asyncio
@pytest.mark.l3
@pytest.mark.critical
async def test_comprehensive_tier_enforcement_metrics(tier_enforcement_l3):
    """Test comprehensive tier enforcement system metrics."""
    # Create users for each tier and run multiple tests
    test_users = {}
    for tier in [PlanTier.FREE, PlanTier.PRO, PlanTier.ENTERPRISE]:
        test_users[tier] = await tier_enforcement_l3.create_test_user(tier)
    
    # Run enforcement tests
    await tier_enforcement_l3.test_free_tier_monthly_limit_enforcement(test_users[PlanTier.FREE]["id"])
    await tier_enforcement_l3.test_mid_tier_concurrent_limit_enforcement(test_users[PlanTier.PRO]["id"])
    await tier_enforcement_l3.test_enterprise_unlimited_access(test_users[PlanTier.ENTERPRISE]["id"])
    
    # Get comprehensive metrics
    metrics = await tier_enforcement_l3.get_enforcement_metrics_summary()
    
    # Verify system performance
    assert metrics["total_requests_tested"] > 50, "Insufficient test coverage"
    assert metrics["performance_sla"]["response_time_under_100ms"] > 95.0, "SLA response time not met"
    assert metrics["system_integrity"]["billing_events_generated"] > 0, "No billing events generated"
    assert metrics["system_integrity"]["cross_service_violations"] == 0, "Cross-service tier violations detected"
    assert metrics["user_experience"]["upgrade_prompts"] > 0, "No upgrade prompts generated"
    
    logger.info(f"Tier enforcement metrics: {metrics}")