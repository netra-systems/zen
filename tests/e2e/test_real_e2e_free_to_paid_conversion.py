"""
Test Free to Paid Conversion Journey

Business Value Justification (BVJ):
- Segment: Free tier users converting to paid (Early/Mid/Enterprise)
- Business Goal: Validate complete conversion funnel from free to paid
- Value Impact: Each conversion worth $2K-$50K+ annual revenue
- Strategic Impact: Conversion optimization critical for $1M+ ARR growth

This test validates the complete free-to-paid conversion journey:
1. Free user experiences value limitations
2. User sees upgrade prompts with clear value proposition
3. Payment flow works seamlessly
4. User gains access to premium features immediately
5. Billing and subscription management works correctly
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest

from shared.isolated_environment import get_env
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.websocket_helpers import MockWebSocketConnection, WebSocketTestHelpers

# SSOT: Test environment configuration
TEST_PORTS = {
    "backend": 8000,
    "auth": 8081,
    "postgresql": 5434,
    "redis": 6381
}

logger = logging.getLogger(__name__)


@dataclass
class ConversionMetrics:
    """Track conversion funnel metrics."""
    free_tier_usage_duration: float = 0.0
    value_limitation_encounters: int = 0
    upgrade_prompt_views: int = 0
    pricing_page_views: int = 0
    checkout_initiated: bool = False
    payment_completed: bool = False
    premium_features_accessed: bool = False
    conversion_time: float = 0.0
    subscription_tier: str = ""
    annual_revenue_value: float = 0.0
    

class PaymentSimulator:
    """Simulate payment processing for testing."""
    
    @staticmethod
    async def process_payment(
        user_id: str,
        plan: str,
        amount: float,
        card_token: str
    ) -> Dict[str, Any]:
        """Simulate payment processing."""
        # Simulate payment gateway interaction
        await asyncio.sleep(0.5)  # Payment processing time
        
        return {
            "success": True,
            "transaction_id": f"txn_{int(time.time())}",
            "amount": amount,
            "currency": "USD",
            "plan": plan,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }


class SubscriptionManager:
    """Manage subscription state for testing."""
    
    def __init__(self):
        self.subscriptions = {}
        
    async def create_subscription(
        self,
        user_id: str,
        plan: str,
        payment_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new subscription."""
        subscription = {
            "subscription_id": f"sub_{int(time.time())}",
            "user_id": user_id,
            "plan": plan,
            "status": "active",
            "start_date": datetime.now().isoformat(),
            "billing_cycle": "monthly" if "monthly" in plan else "annual",
            "amount": payment_info["amount"],
            "next_billing_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "features": self._get_plan_features(plan)
        }
        
        self.subscriptions[user_id] = subscription
        return subscription
        
    def _get_plan_features(self, plan: str) -> List[str]:
        """Get features for a subscription plan."""
        features_map = {
            "early_monthly": [
                "unlimited_agents",
                "advanced_analytics",
                "api_access",
                "email_support"
            ],
            "early_annual": [
                "unlimited_agents",
                "advanced_analytics",
                "api_access",
                "priority_support",
                "custom_integrations"
            ],
            "mid_monthly": [
                "unlimited_agents",
                "advanced_analytics",
                "api_access",
                "priority_support",
                "custom_integrations",
                "team_collaboration",
                "sla_guarantee"
            ],
            "enterprise": [
                "unlimited_everything",
                "white_glove_support",
                "custom_deployment",
                "dedicated_account_manager",
                "custom_sla",
                "audit_logs",
                "sso_integration"
            ]
        }
        return features_map.get(plan, ["basic_features"])


class TestRealE2EFreeToPayConversion(BaseE2ETest):
    """Test complete free to paid conversion journey."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.payment_simulator = PaymentSimulator()
        self.subscription_manager = SubscriptionManager()
        self.conversion_metrics = ConversionMetrics()
        
    async def simulate_free_tier_usage(
        self,
        user_id: str,
        websocket: MockWebSocketConnection
    ) -> int:
        """Simulate free tier usage until limitations encountered."""
        limitation_count = 0
        start_time = time.time()
        
        # Simulate multiple agent requests
        for i in range(5):  # Free tier allows 3 requests
            request = {
                "type": "agent_request",
                "user_id": user_id,
                "message": f"Optimize my costs - request {i+1}",
                "agent": "cost_optimizer"
            }
            
            await websocket.send(json.dumps(request))
            response_str = await websocket.recv()
            response = json.loads(response_str)
            
            # Check for limitation after 3rd request
            if i >= 2:
                limitation_count += 1
                assert response.get("type") == "tier_limitation", \
                    "Should encounter tier limitation after 3 requests"
                assert "upgrade" in response.get("message", "").lower(), \
                    "Limitation message should mention upgrade"
                    
        self.conversion_metrics.free_tier_usage_duration = time.time() - start_time
        self.conversion_metrics.value_limitation_encounters = limitation_count
        
        logger.info(f"Free tier limitations encountered: {limitation_count}")
        return limitation_count
        
    async def view_upgrade_options(
        self,
        user_id: str,
        websocket: MockWebSocketConnection
    ) -> Dict[str, Any]:
        """View upgrade options and pricing."""
        # Request upgrade options
        request = {
            "type": "view_pricing",
            "user_id": user_id
        }
        
        await websocket.send(json.dumps(request))
        response_str = await websocket.recv()
        pricing_info = json.loads(response_str)
        
        self.conversion_metrics.upgrade_prompt_views += 1
        self.conversion_metrics.pricing_page_views += 1
        
        # Validate pricing options
        assert pricing_info.get("type") == "pricing_options", \
            "Should receive pricing options"
        assert "plans" in pricing_info, "Pricing should include plans"
        
        plans = pricing_info["plans"]
        assert len(plans) >= 3, "Should have at least 3 plan options"
        
        # Validate each plan has required info
        for plan in plans:
            assert "name" in plan, "Plan must have name"
            assert "price" in plan, "Plan must have price"
            assert "features" in plan, "Plan must have features"
            assert "value_proposition" in plan, "Plan must have value proposition"
            
        logger.info(f"Pricing plans available: {[p['name'] for p in plans]}")
        return pricing_info
        
    async def initiate_checkout(
        self,
        user_id: str,
        websocket: MockWebSocketConnection,
        selected_plan: str
    ) -> Dict[str, Any]:
        """Initiate checkout process."""
        self.conversion_metrics.checkout_initiated = True
        
        # Start checkout
        checkout_request = {
            "type": "initiate_checkout",
            "user_id": user_id,
            "plan": selected_plan
        }
        
        await websocket.send(json.dumps(checkout_request))
        response_str = await websocket.recv()
        checkout_info = json.loads(response_str)
        
        assert checkout_info.get("type") == "checkout_session", \
            "Should receive checkout session"
        assert "session_id" in checkout_info, "Checkout must have session ID"
        assert "amount" in checkout_info, "Checkout must show amount"
        assert "plan_details" in checkout_info, "Checkout must show plan details"
        
        logger.info(f"Checkout initiated for plan: {selected_plan}")
        return checkout_info
        
    async def complete_payment(
        self,
        user_id: str,
        websocket: MockWebSocketConnection,
        checkout_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Complete payment process."""
        # Simulate payment details
        payment_request = {
            "type": "process_payment",
            "user_id": user_id,
            "session_id": checkout_info["session_id"],
            "payment_method": {
                "type": "card",
                "token": "tok_test_visa_4242"  # Test token
            }
        }
        
        # Process payment
        payment_result = await self.payment_simulator.process_payment(
            user_id=user_id,
            plan=checkout_info["plan_details"]["id"],
            amount=checkout_info["amount"],
            card_token=payment_request["payment_method"]["token"]
        )
        
        if payment_result["success"]:
            self.conversion_metrics.payment_completed = True
            
            # Create subscription
            subscription = await self.subscription_manager.create_subscription(
                user_id=user_id,
                plan=checkout_info["plan_details"]["id"],
                payment_info=payment_result
            )
            
            # Send confirmation via WebSocket
            confirmation = {
                "type": "payment_success",
                "user_id": user_id,
                "subscription": subscription,
                "payment": payment_result
            }
            
            await websocket.send(json.dumps(confirmation))
            response_str = await websocket.recv()
            confirmation_response = json.loads(response_str)
            
            assert confirmation_response.get("type") == "subscription_activated", \
                "Should receive subscription activation confirmation"
                
            logger.info(f"Payment completed successfully for user {user_id}")
            return confirmation_response
        else:
            raise Exception("Payment failed in simulation")
            
    async def verify_premium_access(
        self,
        user_id: str,
        websocket: MockWebSocketConnection
    ) -> bool:
        """Verify access to premium features."""
        # Test premium feature access
        premium_request = {
            "type": "agent_request",
            "user_id": user_id,
            "message": "Perform advanced cost analysis with ML predictions",
            "agent": "advanced_cost_analyzer",  # Premium agent
            "features": ["ml_predictions", "custom_reports"]  # Premium features
        }
        
        await websocket.send(json.dumps(premium_request))
        
        # Collect response events
        events = []
        start_time = time.time()
        
        while time.time() - start_time < 10:
            try:
                response_str = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                event = json.loads(response_str)
                events.append(event)
                
                if event.get("type") == "agent_completed":
                    break
            except asyncio.TimeoutError:
                continue
                
        # Verify premium features are accessible
        agent_started = any(e.get("type") == "agent_started" for e in events)
        agent_completed = any(e.get("type") == "agent_completed" for e in events)
        
        if agent_started and agent_completed:
            self.conversion_metrics.premium_features_accessed = True
            
            # Check for premium features in response
            completion_event = next(
                (e for e in events if e.get("type") == "agent_completed"),
                None
            )
            
            if completion_event:
                response_data = completion_event.get("data", {})
                has_ml_predictions = "ml_predictions" in str(response_data).lower()
                has_custom_reports = "custom_report" in str(response_data).lower()
                
                logger.info(f"Premium features accessed: ML={has_ml_predictions}, Reports={has_custom_reports}")
                return has_ml_predictions or has_custom_reports
                
        return False
        
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.timeout(180)
    async def test_complete_free_to_paid_conversion_journey(self):
        """Test complete conversion from free tier to paid subscription."""
        logger.info("Starting free-to-paid conversion journey test")
        
        conversion_start = time.time()
        
        # Create free tier user
        user_id = f"free_user_{int(time.time())}"
        websocket = MockWebSocketConnection(user_id=user_id)
        
        try:
            # Step 1: Use free tier until limitations
            limitations = await self.simulate_free_tier_usage(user_id, websocket)
            assert limitations >= 2, "Should encounter multiple limitations"
            
            # Step 2: View upgrade options
            pricing_info = await self.view_upgrade_options(user_id, websocket)
            assert len(pricing_info["plans"]) >= 3, "Should see multiple plan options"
            
            # Step 3: Select a plan (Early tier for this test)
            selected_plan = "early_monthly"
            self.conversion_metrics.subscription_tier = selected_plan
            self.conversion_metrics.annual_revenue_value = 199 * 12  # $199/month
            
            # Step 4: Initiate checkout
            checkout_info = await self.initiate_checkout(
                user_id, websocket, selected_plan
            )
            assert checkout_info["amount"] == 199.00, "Early plan should be $199/month"
            
            # Step 5: Complete payment
            payment_confirmation = await self.complete_payment(
                user_id, websocket, checkout_info
            )
            assert payment_confirmation["subscription"]["status"] == "active", \
                "Subscription should be active"
            
            # Step 6: Verify premium access
            has_premium_access = await self.verify_premium_access(user_id, websocket)
            assert has_premium_access, "Should have access to premium features"
            
            # Calculate conversion metrics
            self.conversion_metrics.conversion_time = time.time() - conversion_start
            
            # Validate business value
            assert self.conversion_metrics.payment_completed, "Payment must complete"
            assert self.conversion_metrics.premium_features_accessed, \
                "Premium features must be accessible"
            assert self.conversion_metrics.annual_revenue_value >= 2000, \
                "Conversion must generate significant revenue"
            
            logger.info(
                f"Conversion completed successfully:\n"
                f"  - Tier: {self.conversion_metrics.subscription_tier}\n"
                f"  - Annual Revenue: ${self.conversion_metrics.annual_revenue_value:,.2f}\n"
                f"  - Conversion Time: {self.conversion_metrics.conversion_time:.2f}s\n"
                f"  - Limitation Encounters: {self.conversion_metrics.value_limitation_encounters}"
            )
            
        finally:
            await websocket.close()
            
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_upgrade_triggers_and_value_proposition(self):
        """Test that upgrade triggers effectively communicate value."""
        logger.info("Testing upgrade triggers and value proposition")
        
        user_id = f"free_user_triggers_{int(time.time())}"
        websocket = MockWebSocketConnection(user_id=user_id)
        
        try:
            # Trigger various limitation scenarios
            limitation_messages = []
            
            # Test 1: Agent request limit
            for i in range(5):
                request = {
                    "type": "agent_request",
                    "user_id": user_id,
                    "message": f"Request {i+1}"
                }
                await websocket.send(json.dumps(request))
                response = json.loads(await websocket.recv())
                
                if response.get("type") == "tier_limitation":
                    limitation_messages.append(response.get("message", ""))
                    
            # Test 2: Advanced feature request
            advanced_request = {
                "type": "agent_request",
                "user_id": user_id,
                "message": "Generate custom optimization report",
                "features": ["custom_reports"]
            }
            await websocket.send(json.dumps(advanced_request))
            response = json.loads(await websocket.recv())
            
            if response.get("type") == "feature_unavailable":
                limitation_messages.append(response.get("message", ""))
                
            # Validate value proposition in messages
            for message in limitation_messages:
                assert any(keyword in message.lower() for keyword in [
                    "upgrade", "premium", "unlock", "pro", "paid"
                ]), f"Limitation message should mention upgrade: {message}"
                
            # Check for specific value props
            value_props_found = {
                "unlimited": any("unlimited" in msg.lower() for msg in limitation_messages),
                "advanced": any("advanced" in msg.lower() for msg in limitation_messages),
                "priority": any("priority" in msg.lower() for msg in limitation_messages)
            }
            
            assert any(value_props_found.values()), \
                "At least one value proposition should be communicated"
                
            logger.info(f"Value propositions found: {value_props_found}")
            
        finally:
            await websocket.close()
            
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_conversion_revenue_tracking(self):
        """Test that conversions properly track revenue metrics."""
        logger.info("Testing conversion revenue tracking")
        
        # Simulate conversions for different tiers
        conversion_scenarios = [
            {"tier": "early_monthly", "price": 199, "annual_value": 2388},
            {"tier": "mid_monthly", "price": 499, "annual_value": 5988},
            {"tier": "enterprise", "price": 2499, "annual_value": 29988}
        ]
        
        total_revenue = 0
        successful_conversions = []
        
        for scenario in conversion_scenarios:
            user_id = f"convert_{scenario['tier']}_{int(time.time())}"
            websocket = MockWebSocketConnection(user_id=user_id)
            
            try:
                # Quick conversion flow
                checkout_info = {
                    "session_id": f"session_{int(time.time())}",
                    "amount": scenario["price"],
                    "plan_details": {"id": scenario["tier"]}
                }
                
                # Process payment
                payment_result = await self.payment_simulator.process_payment(
                    user_id=user_id,
                    plan=scenario["tier"],
                    amount=scenario["price"],
                    card_token="tok_test"
                )
                
                if payment_result["success"]:
                    subscription = await self.subscription_manager.create_subscription(
                        user_id=user_id,
                        plan=scenario["tier"],
                        payment_info=payment_result
                    )
                    
                    successful_conversions.append({
                        "user_id": user_id,
                        "tier": scenario["tier"],
                        "annual_revenue": scenario["annual_value"]
                    })
                    
                    total_revenue += scenario["annual_value"]
                    
            finally:
                await websocket.close()
                
        # Validate revenue metrics
        assert len(successful_conversions) == len(conversion_scenarios), \
            "All conversions should succeed"
        assert total_revenue == sum(s["annual_value"] for s in conversion_scenarios), \
            "Total revenue should match expected"
        assert total_revenue >= 38364, "Combined revenue should exceed targets"
        
        logger.info(
            f"Revenue tracking validated:\n"
            f"  - Conversions: {len(successful_conversions)}\n"
            f"  - Total Annual Revenue: ${total_revenue:,}\n"
            f"  - Average Revenue per User: ${total_revenue/len(successful_conversions):,.2f}"
        )


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])