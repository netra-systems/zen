"""
Multi-User Business Operations Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure platform scales effectively for concurrent users
- Value Impact: Multi-tenant isolation, subscription tier differentiation, billing accuracy
- Strategic Impact: Platform scalability and revenue protection through proper user isolation

Tests multi-user scenarios critical for business operations:
1. Concurrent user isolation (prevent data leaks between customers)
2. Cross-tenant data protection (enterprise security requirements)
3. Enterprise user workflows (premium feature access)
4. Subscription tier differentiation (feature/performance tiers)
5. Usage tracking and billing (revenue integrity)

Uses real components with multi-user simulation but no Docker dependencies.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from netra_backend.tests.integration.business_value.enhanced_base_integration_test import EnhancedBaseIntegrationTest
from test_framework.ssot.websocket import WebSocketEventType


class TestMultiUserBusinessOperations(EnhancedBaseIntegrationTest):
    """
    Integration tests validating multi-user business operations at scale.
    
    Focus: User isolation, subscription tiers, billing, concurrent access
    """
    
    @pytest.mark.integration
    @pytest.mark.business_value
    @pytest.mark.multi_user
    async def test_concurrent_user_isolation_validation(self):
        """
        Test 1: Concurrent Users Get Isolated Experiences
        
        Business Value: Prevents data leaks, ensures user privacy
        Customer Segment: All (fundamental security requirement)
        Success Criteria: 5+ concurrent users with zero cross-contamination
        """
        # Setup: Multiple users from different tiers
        users = await self.simulate_multi_user_scenario(user_count=5)
        
        # Concurrent execution contexts for each user
        user_contexts = []
        for i, user in enumerate(users):
            request = f"Analyze my AI costs for user {user['id']} - confidential data {i}"
            context = await self.create_agent_execution_context(user, request)
            user_contexts.append({
                "user": user,
                "context": context,
                "expected_isolation_marker": f"confidential data {i}"
            })
        
        # Execute agents concurrently for all users
        concurrent_results = []
        
        async def execute_user_agent(user_ctx):
            """Execute agent for single user with isolation tracking."""
            async with self.websocket_business_context(user_ctx["user"]) as ws_context:
                result = await self.execute_agent_with_business_validation(
                    agent_name="triage_agent",
                    state=user_ctx["context"],
                    expected_business_outcomes=["user_request_addressed", "category_assigned"],
                    timeout=20.0,
                    ws_context=ws_context
                )
                
                return {
                    "user_id": user_ctx["user"]["id"],
                    "subscription_tier": user_ctx["user"]["subscription_tier"],
                    "result": result,
                    "websocket_events": ws_context["events"],
                    "isolation_marker": user_ctx["expected_isolation_marker"]
                }
        
        # Execute all users concurrently
        tasks = [execute_user_agent(ctx) for ctx in user_contexts]
        concurrent_results = await asyncio.gather(*tasks)
        
        # Isolation Validation
        self.assert_multi_user_isolation(concurrent_results)
        
        # Verify each user got their own isolated results
        user_ids_processed = set()
        for result in concurrent_results:
            user_id = result["user_id"]
            
            # No duplicate processing
            assert user_id not in user_ids_processed, f"User {user_id} processed multiple times"
            user_ids_processed.add(user_id)
            
            # Business value delivered per user
            self.assert_business_value_delivered(result["result"])
            
            # Verify user context isolation (no cross-contamination)
            user_request = result["result"]["state"].user_request
            isolation_marker = result["isolation_marker"]
            assert isolation_marker in user_request, \
                f"User isolation failed - wrong context for {user_id}"
                
            # WebSocket isolation (each user gets their own events)
            events = result["websocket_events"]
            assert len(events) > 0, f"User {user_id} should receive WebSocket events"
            
            # Verify no cross-user event contamination
            for event in events:
                event_data = event.get("data", {})
                if "user_id" in event_data:
                    assert event_data["user_id"] == user_id, \
                        f"WebSocket event contamination detected for {user_id}"
        
        # Performance validation - concurrent execution shouldn't degrade significantly
        execution_times = [r["result"]["execution_time"] for r in concurrent_results]
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        
        assert avg_execution_time <= 15.0, f"Concurrent execution too slow: {avg_execution_time:.2f}s"
        assert max_execution_time <= 25.0, f"Slowest user too slow: {max_execution_time:.2f}s"
        
        # Record business metrics
        self.business_metrics.record_business_outcome("concurrent_users_supported", len(users))
        self.business_metrics.record_business_outcome("isolation_violations", 0)
        self.business_metrics.record_business_outcome("avg_concurrent_performance", avg_execution_time)
    
    @pytest.mark.integration
    @pytest.mark.business_value
    @pytest.mark.enterprise
    async def test_cross_tenant_data_protection(self):
        """
        Test 2: Enterprise Tenants Have Complete Data Isolation
        
        Business Value: Enterprise security compliance, prevents data breaches
        Customer Segment: Enterprise (strict data isolation requirements)
        Success Criteria: Zero data leakage between enterprise tenants
        """
        # Setup: Two enterprise customers with sensitive data
        enterprise_user_1 = await self.create_test_user(subscription_tier="enterprise")
        enterprise_user_2 = await self.create_test_user(subscription_tier="enterprise")
        
        # Add sensitive enterprise context
        enterprise_user_1["company"] = "MegaCorp Industries"
        enterprise_user_1["confidential_data"] = "Project Alpha budget: $2.5M"
        
        enterprise_user_2["company"] = "Global Dynamics Corp"  
        enterprise_user_2["confidential_data"] = "Project Beta revenue: $4.1M"
        
        # Concurrent requests with confidential data
        request_1 = f"Analyze AI costs for {enterprise_user_1['company']}. {enterprise_user_1['confidential_data']}"
        request_2 = f"Analyze AI costs for {enterprise_user_2['company']}. {enterprise_user_2['confidential_data']}"
        
        state_1 = await self.create_agent_execution_context(enterprise_user_1, request_1)
        state_2 = await self.create_agent_execution_context(enterprise_user_2, request_2)
        
        # Add enterprise-specific context
        state_1.user_context.update({
            "enterprise_features": True,
            "data_classification": "confidential",
            "compliance_requirements": ["SOX", "GDPR", "CCPA"]
        })
        
        state_2.user_context.update({
            "enterprise_features": True, 
            "data_classification": "confidential",
            "compliance_requirements": ["HIPAA", "SOX", "PCI-DSS"]
        })
        
        # Execute both enterprise users simultaneously
        async def execute_enterprise_user(user, state, expected_company):
            async with self.websocket_business_context(user) as ws_context:
                result = await self.execute_agent_with_business_validation(
                    agent_name="enterprise_optimization_agent",
                    state=state,
                    expected_business_outcomes=[
                        "enterprise_analysis_completed",
                        "confidential_data_processed",
                        "compliance_verified"
                    ],
                    timeout=30.0,
                    ws_context=ws_context
                )
                
                return {
                    "user": user,
                    "result": result,
                    "expected_company": expected_company,
                    "websocket_events": ws_context["events"]
                }
        
        # Execute both enterprise users concurrently
        results = await asyncio.gather(
            execute_enterprise_user(enterprise_user_1, state_1, "MegaCorp Industries"),
            execute_enterprise_user(enterprise_user_2, state_2, "Global Dynamics Corp")
        )
        
        # Cross-tenant isolation validation
        result_1, result_2 = results
        
        # Verify each enterprise user got only their own data
        user_1_request = result_1["result"]["state"].user_request
        user_2_request = result_2["result"]["state"].user_request
        
        # No cross-contamination of company names
        assert "MegaCorp Industries" in user_1_request
        assert "Global Dynamics Corp" not in user_1_request, "Cross-tenant data leak detected!"
        
        assert "Global Dynamics Corp" in user_2_request  
        assert "MegaCorp Industries" not in user_2_request, "Cross-tenant data leak detected!"
        
        # No cross-contamination of confidential data
        assert "Project Alpha budget" in user_1_request
        assert "Project Beta revenue" not in user_1_request, "Confidential data leak!"
        
        assert "Project Beta revenue" in user_2_request
        assert "Project Alpha budget" not in user_2_request, "Confidential data leak!"
        
        # Enterprise-level business value validation
        for result in results:
            self.assert_enterprise_tier_value(result["user"], result["result"]["business_outcomes"])
            
            # Enterprise users should get premium WebSocket events
            events = result["websocket_events"]
            event_types = [e.get("type") for e in events]
            assert "agent_thinking" in event_types, "Enterprise users should see detailed progress"
        
        # Record data protection metrics
        self.business_metrics.record_business_outcome("enterprise_tenants_isolated", 2)
        self.business_metrics.record_business_outcome("data_protection_violations", 0)
        self.business_metrics.record_business_outcome("compliance_checks_passed", 2)
    
    @pytest.mark.integration
    @pytest.mark.business_value  
    async def test_enterprise_user_premium_workflows(self):
        """
        Test 3: Enterprise Users Access Premium Features and Workflows
        
        Business Value: Justifies enterprise pricing, drives upsells
        Customer Segment: Enterprise (premium feature differentiation)
        Success Criteria: Enterprise users get enhanced features vs. lower tiers
        """
        # Setup: Users from different subscription tiers
        free_user = await self.create_test_user(subscription_tier="free")
        early_user = await self.create_test_user(subscription_tier="early")  
        enterprise_user = await self.create_test_user(subscription_tier="enterprise")
        
        # Same complex request across tiers
        complex_request = (
            "Perform comprehensive AI infrastructure analysis including cost optimization, "
            "performance benchmarking, security assessment, compliance review, and "
            "strategic recommendations for scaling to 10x current usage."
        )
        
        # Execute same request for each tier
        async def execute_for_tier(user):
            state = await self.create_agent_execution_context(user, complex_request)
            
            async with self.websocket_business_context(user) as ws_context:
                result = await self.execute_agent_with_business_validation(
                    agent_name="comprehensive_analysis_agent",
                    state=state,
                    expected_business_outcomes=["analysis_completed", "recommendations_provided"],
                    timeout=40.0,
                    ws_context=ws_context
                )
                
                return {
                    "user": user,
                    "tier": user["subscription_tier"],
                    "result": result,
                    "websocket_events": ws_context["events"]
                }
        
        # Execute for all tiers
        tier_results = await asyncio.gather(
            execute_for_tier(free_user),
            execute_for_tier(early_user),
            execute_for_tier(enterprise_user)
        )
        
        # Tier Differentiation Validation
        free_result = next(r for r in tier_results if r["tier"] == "free")
        early_result = next(r for r in tier_results if r["tier"] == "early")
        enterprise_result = next(r for r in tier_results if r["tier"] == "enterprise")
        
        # Enterprise should get the most comprehensive analysis
        enterprise_outcomes = enterprise_result["result"]["business_outcomes"]
        early_outcomes = early_result["result"]["business_outcomes"] 
        free_outcomes = free_result["result"]["business_outcomes"]
        
        # Enterprise should have higher confidence scores
        enterprise_confidence = enterprise_outcomes.get("confidence_score", 0)
        early_confidence = early_outcomes.get("confidence_score", 0)
        free_confidence = free_outcomes.get("confidence_score", 0)
        
        assert enterprise_confidence >= early_confidence, "Enterprise should have higher confidence"
        assert early_confidence >= free_confidence, "Early should have higher confidence than free"
        assert enterprise_confidence >= 0.85, f"Enterprise confidence too low: {enterprise_confidence}"
        
        # Enterprise should get more detailed recommendations
        enterprise_recs = enterprise_outcomes.get("actionable_recommendations", 0)
        early_recs = early_outcomes.get("actionable_recommendations", 0)
        free_recs = free_outcomes.get("actionable_recommendations", 0)
        
        assert enterprise_recs >= early_recs, "Enterprise should get more recommendations"
        assert enterprise_recs >= 3, f"Enterprise should get at least 3 recommendations, got {enterprise_recs}"
        
        # WebSocket event differentiation
        enterprise_events = enterprise_result["websocket_events"]
        early_events = early_result["websocket_events"]
        free_events = free_result["websocket_events"]
        
        # Enterprise users should see more detailed progress
        enterprise_event_count = len(enterprise_events)
        early_event_count = len(early_events)
        free_event_count = len(free_events)
        
        assert enterprise_event_count >= early_event_count, "Enterprise should get more progress updates"
        assert enterprise_event_count >= 3, "Enterprise should see detailed progress"
        
        # Performance differentiation - enterprise should be fastest
        enterprise_time = enterprise_result["result"]["execution_time"] 
        early_time = early_result["result"]["execution_time"]
        free_time = free_result["result"]["execution_time"]
        
        # Enterprise should get priority processing
        assert enterprise_time <= 35.0, f"Enterprise processing too slow: {enterprise_time:.2f}s"
        
        # Record tier differentiation metrics
        self.business_metrics.record_business_outcome("tier_differentiation_verified", True)
        self.business_metrics.record_business_outcome("enterprise_premium_features", enterprise_recs)
        self.business_metrics.record_business_outcome("tier_performance_advantage", 
                                                     early_time - enterprise_time)
    
    @pytest.mark.integration
    @pytest.mark.business_value
    async def test_subscription_tier_feature_access_control(self):
        """
        Test 4: Subscription Tiers Control Feature Access Appropriately
        
        Business Value: Enforces billing boundaries, drives upgrades
        Customer Segment: All (subscription revenue protection)
        Success Criteria: Lower tiers blocked from premium features
        """
        # Setup: Users from each tier requesting premium features
        tiers_and_features = [
            ("free", "basic_analysis", True),          # Free gets basic
            ("free", "advanced_optimization", False),  # Free blocked from advanced
            ("early", "basic_analysis", True),         # Early gets basic
            ("early", "advanced_optimization", True),   # Early gets advanced
            ("early", "enterprise_compliance", False), # Early blocked from compliance
            ("mid", "advanced_optimization", True),    # Mid gets advanced
            ("mid", "enterprise_compliance", False),   # Mid blocked from compliance
            ("enterprise", "enterprise_compliance", True), # Enterprise gets all
        ]
        
        access_results = []
        
        for tier, feature, should_have_access in tiers_and_features:
            user = await self.create_test_user(subscription_tier=tier)
            
            # Request specific to the feature
            feature_requests = {
                "basic_analysis": "Analyze my basic AI usage patterns",
                "advanced_optimization": "Perform advanced cost optimization with ML recommendations",
                "enterprise_compliance": "Generate SOX compliance report with audit trail"
            }
            
            request = feature_requests[feature]
            state = await self.create_agent_execution_context(user, request)
            
            # Add feature context to test access control
            # Update the metadata custom_fields where user_context is stored
            if hasattr(state, 'metadata') and state.metadata and hasattr(state.metadata, 'custom_fields'):
                if 'user_context' not in state.metadata.custom_fields:
                    state.metadata.custom_fields['user_context'] = {}
                state.metadata.custom_fields['user_context'].update({
                    "requested_feature": feature,
                    "subscription_tier": tier
                })
            
            try:
                async with self.websocket_business_context(user) as ws_context:
                    result = await self.execute_agent_with_business_validation(
                        agent_name="feature_access_agent", 
                        state=state,
                        expected_business_outcomes=["feature_access_checked"],
                        timeout=15.0,
                        ws_context=ws_context
                    )
                    
                    access_granted = result["business_outcomes"].get("feature_access_granted", False)
                    access_results.append({
                        "tier": tier,
                        "feature": feature,
                        "should_have_access": should_have_access,
                        "access_granted": access_granted,
                        "execution_successful": True
                    })
                    
            except Exception as e:
                # Access denied should raise appropriate error
                access_results.append({
                    "tier": tier,
                    "feature": feature,
                    "should_have_access": should_have_access,
                    "access_granted": False,
                    "execution_successful": False,
                    "error": str(e)
                })
        
        # Validate access control enforcement
        access_violations = []
        upgrade_opportunities = []
        
        for result in access_results:
            tier = result["tier"]
            feature = result["feature"] 
            should_have = result["should_have_access"]
            actually_has = result["access_granted"]
            
            if should_have and not actually_has:
                # User should have access but was denied - problem
                access_violations.append(f"{tier} denied {feature}")
            elif not should_have and actually_has:
                # User shouldn't have access but was granted - security issue
                access_violations.append(f"{tier} granted {feature}")
            elif not should_have and not actually_has:
                # Correctly denied - upgrade opportunity
                upgrade_opportunities.append(f"{tier} blocked from {feature}")
                
        # Assert no access control violations
        assert len(access_violations) == 0, f"Access control violations: {access_violations}"
        
        # Should have upgrade opportunities (business value)
        assert len(upgrade_opportunities) > 0, "No upgrade opportunities identified"
        
        # Record subscription enforcement metrics
        self.business_metrics.record_business_outcome("access_control_violations", len(access_violations))
        self.business_metrics.record_business_outcome("upgrade_opportunities", len(upgrade_opportunities))
        self.business_metrics.record_business_outcome("tier_enforcement_working", True)
        
        # Verify upgrade prompts for blocked features
        blocked_results = [r for r in access_results if not r["should_have_access"] and not r["access_granted"]]
        for blocked in blocked_results:
            # These should generate upgrade suggestions (business value)
            self.business_metrics.add_warning(
                f"Upgrade opportunity: {blocked['tier']} user needs {blocked['feature']}"
            )
    
    @pytest.mark.integration
    @pytest.mark.business_value
    async def test_usage_tracking_and_billing_accuracy(self):
        """
        Test 5: Accurate Usage Tracking for Billing and Revenue Protection
        
        Business Value: Accurate billing, prevents revenue leakage
        Customer Segment: All (revenue integrity)
        Success Criteria: All usage tracked accurately with billing implications
        """
        # Setup: Users with different usage patterns (scaled down for performance)
        users_and_usage = [
            ("enterprise", 8, 15.0),   # Heavy usage, long operations (was 50)
            ("mid", 5, 8.0),           # Medium usage (was 20)
            ("early", 3, 3.0),         # Light usage (was 5)
            ("free", 2, 1.0)           # Minimal usage (unchanged)
        ]
        
        usage_tracking_results = []
        
        for tier, operation_count, avg_duration in users_and_usage:
            user = await self.create_test_user(subscription_tier=tier)
            
            # Track usage for this user
            user_usage = {
                "user_id": user["id"],
                "tier": tier,
                "operations": [],
                "total_compute_time": 0.0,
                "total_api_calls": 0,
                "billing_events": []
            }
            
            # Simulate multiple operations for usage tracking
            for i in range(operation_count):
                operation_start = datetime.now()
                
                request = f"Operation {i+1}: Analyze usage pattern for billing"
                state = await self.create_agent_execution_context(user, request)
                
                async with self.websocket_business_context(user) as ws_context:
                    result = await self.execute_agent_with_business_validation(
                        agent_name="usage_tracking_agent",
                        state=state,
                        expected_business_outcomes=["operation_tracked", "usage_recorded"],
                        timeout=10.0,
                        ws_context=ws_context
                    )
                    
                    operation_end = datetime.now()
                    operation_duration = (operation_end - operation_start).total_seconds()
                    
                    # Record operation details
                    operation_record = {
                        "operation_id": f"op_{uuid.uuid4().hex[:8]}",
                        "timestamp": operation_start.isoformat(),
                        "duration": operation_duration,
                        "compute_cost": operation_duration * 0.01,  # $0.01/second
                        "api_calls": len(ws_context["events"]),
                        "success": result["success"]
                    }
                    
                    user_usage["operations"].append(operation_record)
                    user_usage["total_compute_time"] += operation_duration
                    user_usage["total_api_calls"] += operation_record["api_calls"]
                    
                    # Generate billing event
                    if self.mock_db:
                        await self.mock_db.connection.execute(
                            """INSERT INTO agent_executions 
                               (id, user_id, agent_name, execution_time_ms, success, created_at)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (operation_record["operation_id"], user["id"], "usage_tracking_agent",
                             operation_duration * 1000, result["success"], operation_start.isoformat())
                        )
                        
                # Small delay between operations (reduced for performance)
                await asyncio.sleep(0.05)
                
            usage_tracking_results.append(user_usage)
        
        # Validate usage tracking accuracy
        for user_usage in usage_tracking_results:
            tier = user_usage["tier"]
            operations = user_usage["operations"]
            
            # All operations should be tracked (updated counts)
            expected_ops = {"enterprise": 8, "mid": 5, "early": 3, "free": 2}[tier]
            actual_ops = len(operations)
            assert actual_ops == expected_ops, f"Usage tracking error: {tier} expected {expected_ops}, got {actual_ops}"
            
            # Compute time should be reasonable
            total_time = user_usage["total_compute_time"]
            assert total_time > 0, f"No compute time tracked for {tier}"
            
            # API calls should be tracked
            total_calls = user_usage["total_api_calls"] 
            assert total_calls > 0, f"No API calls tracked for {tier}"
            
            # Calculate billing amounts
            tier_multipliers = {"enterprise": 1.0, "mid": 0.8, "early": 0.6, "free": 0.0}
            compute_cost = total_time * 0.01 * tier_multipliers[tier]
            api_cost = total_calls * 0.001 * tier_multipliers[tier]
            total_bill = compute_cost + api_cost
            
            # Record billing metrics
            self.business_metrics.record_business_outcome(f"{tier}_compute_cost", compute_cost)
            self.business_metrics.record_business_outcome(f"{tier}_api_cost", api_cost)
            self.business_metrics.record_business_outcome(f"{tier}_total_bill", total_bill)
            
            # Verify billing tiers are differentiated
            if tier == "enterprise":
                assert total_bill > 0, "Enterprise should have billing charges"
            elif tier == "free":
                # Free tier should have no charges (multiplier = 0.0)
                assert total_bill == 0, f"Free tier should have no charges, got ${total_bill:.4f}"
                
        # Cross-user billing validation
        enterprise_usage = next(u for u in usage_tracking_results if u["tier"] == "enterprise")
        free_usage = next(u for u in usage_tracking_results if u["tier"] == "free")
        
        # Enterprise should have much higher usage than free
        enterprise_time = enterprise_usage["total_compute_time"] 
        free_time = free_usage["total_compute_time"]
        
        assert enterprise_time > free_time * 2, "Enterprise usage should be significantly higher than free"
        
        # Revenue integrity check
        total_billable_time = sum(u["total_compute_time"] for u in usage_tracking_results if u["tier"] != "free")
        total_revenue_potential = total_billable_time * 0.01
        
        assert total_revenue_potential > 0, "Must have revenue potential from usage"
        
        self.business_metrics.record_business_outcome("total_billable_time", total_billable_time)
        self.business_metrics.record_business_outcome("revenue_integrity_verified", True)


if __name__ == "__main__":
    # Run multi-user tests with concurrency focus
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-m", "business_value",
        "--durations=10",
        "-x"  # Stop on first failure for debugging
    ])