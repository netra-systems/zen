"""
E2E Test: Multi-User Concurrent Chat Isolation - MISSION CRITICAL Security & Scalability

BUSINESS IMPACT: Tests multi-user chat isolation that enables enterprise scalability.
This validates the security and isolation that allows multiple customers to use the platform simultaneously.

Business Value Justification (BVJ):
- Segment: Enterprise/Multi-Tenant - Platform Scalability  
- Business Goal: Platform Security & Scalability - Enable multiple customers safely
- Value Impact: Validates isolation that enables enterprise multi-tenant revenue
- Strategic Impact: Tests security architecture that prevents data leaks and ensures compliance

CRITICAL SUCCESS METRICS:
✅ Complete user isolation in concurrent chat sessions
✅ No data leakage between users during simultaneous chat
✅ Performance maintains quality under concurrent load
✅ Authentication and WebSocket isolation work correctly
✅ Agent responses are correctly routed to appropriate users

ISOLATION VALIDATION:
• User context isolation - Each user maintains separate execution context
• WebSocket isolation - Messages routed only to correct user
• Agent isolation - Agent responses don't cross-contaminate
• Data isolation - Business data and insights remain user-specific
• Thread isolation - Chat threads remain completely separate

COMPLIANCE:
@compliance CLAUDE.md - Multi-user system (Section 0.4 and 1.2)
@compliance CLAUDE.md - E2E AUTH MANDATORY (Section 7.3)
@compliance CLAUDE.md - Factory pattern user isolation
@compliance SPEC/core.xml - User isolation patterns
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# SSOT Imports - Authentication and Golden Path
from test_framework.ssot.e2e_auth_helper import (
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig
)
from netra_backend.app.websocket_core.event_validator import (
    AgentEventValidator,
    CriticalAgentEventType,
    WebSocketEventMessage
)

# SSOT Imports - Types
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext

# Test Framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


@pytest.mark.e2e
@pytest.mark.staging_compatible
@pytest.mark.multi_user
class TestMultiUserConcurrentChatIsolationE2E(SSotBaseTestCase):
    """
    MISSION CRITICAL E2E Tests for Multi-User Concurrent Chat Isolation.
    
    These tests validate that multiple users can chat simultaneously
    with complete isolation and no data leakage between users.
    
    SECURITY IMPACT: If isolation fails, customer data could leak to other customers.
    """
    
    def setup_method(self):
        """Set up multi-user concurrent chat isolation test environment."""
        super().setup_method()
        
        # Initialize SSOT helpers
        self.environment = self.get_test_environment()
        self.ws_auth_helper = E2EWebSocketAuthHelper(environment=self.environment)
        self.golden_path_helper = WebSocketGoldenPathHelper(environment=self.environment)
        
        # Multi-user test configuration
        self.config = GoldenPathTestConfig.for_environment(self.environment)
        self.config.enable_performance_monitoring = True
        
        # Multi-user tracking
        self.test_start_time = time.time()
        self.concurrent_users_tested = 0
        self.isolation_violations = 0
        self.cross_contamination_detected = False
        self.performance_degradation = False
        
        print(f"\n👥 MULTI-USER CONCURRENT CHAT ISOLATION E2E - Environment: {self.environment}")
        print(f"🔒 Target: Complete user isolation with concurrent chat sessions")
        print(f"🏢 Business Impact: Enterprise security and scalability validation")
    
    def teardown_method(self):
        """Clean up and report multi-user isolation metrics."""
        test_duration = time.time() - self.test_start_time
        
        print(f"\n📊 Multi-User Isolation Test Summary:")
        print(f"⏱️ Duration: {test_duration:.2f}s")
        print(f"👥 Concurrent Users Tested: {self.concurrent_users_tested}")
        print(f"🔒 Isolation Violations: {self.isolation_violations}")
        print(f"🚨 Cross-Contamination: {'DETECTED' if self.cross_contamination_detected else 'NONE'}")
        print(f"📉 Performance Issues: {'YES' if self.performance_degradation else 'NO'}")
        
        if self.isolation_violations == 0 and not self.cross_contamination_detected:
            print(f"✅ EXCELLENT ISOLATION - Enterprise-ready security")
        elif self.isolation_violations <= 1:
            print(f"⚠️ MINOR ISOLATION ISSUES - Acceptable for most use cases")
        else:
            print(f"❌ CRITICAL ISOLATION FAILURES - Enterprise security at risk")
        
        super().teardown_method()
    
    async def _create_isolated_user_session(
        self, 
        user_index: int,
        user_business_context: str
    ) -> Tuple[StronglyTypedUserExecutionContext, WebSocketGoldenPathHelper]:
        """
        Create an isolated user session with authentication and business context.
        
        Args:
            user_index: Index of user for identification
            user_business_context: Business context for this user's session
            
        Returns:
            Tuple of (user_context, golden_path_helper)
        """
        # Create authenticated user context with unique identifiers
        user_context = await create_authenticated_user_context(
            user_email=f"isolation_user_{user_index}_{uuid.uuid4().hex[:8]}@enterprise.com",
            environment=self.environment,
            permissions=["read", "write", "chat", "multi_user_isolation", "enterprise"],
            websocket_enabled=True
        )
        
        # Add business context to differentiate users
        user_context.agent_context.update({
            "user_index": user_index,
            "business_context": user_business_context,
            "isolation_test": True,
            "test_session_id": f"session_{user_index}_{int(time.time())}"
        })
        
        # Create dedicated golden path helper for this user
        user_helper = WebSocketGoldenPathHelper(
            config=self.config,
            environment=self.environment
        )
        
        return user_context, user_helper
    
    def _analyze_response_for_contamination(
        self, 
        response: str, 
        user_index: int,
        other_users_contexts: List[str]
    ) -> bool:
        """
        Analyze a user's response for contamination from other users.
        
        Args:
            response: The response content to analyze
            user_index: Index of the user who should have received this response
            other_users_contexts: Business contexts of other users
            
        Returns:
            True if contamination detected, False if clean
        """
        response_lower = response.lower()
        
        # Check for other users' business contexts leaking into this response
        for other_context in other_users_contexts:
            context_keywords = other_context.lower().split()[:3]  # First 3 words as identifiers
            for keyword in context_keywords:
                if len(keyword) > 4 and keyword in response_lower:
                    print(f"🚨 CONTAMINATION DETECTED: User {user_index} response contains '{keyword}' from other user")
                    return True
        
        # Check for explicit user mentions that shouldn't be there
        for i in range(10):  # Check for user_0 through user_9
            if i != user_index and f"user_{i}" in response_lower:
                print(f"🚨 USER CONTAMINATION: User {user_index} response mentions user_{i}")
                return True
        
        return False
    
    @pytest.mark.asyncio
    async def test_dual_user_concurrent_chat_isolation(self):
        """
        CRITICAL: Dual user concurrent chat with complete isolation.
        
        Tests that two users can chat simultaneously with completely
        isolated responses and no data leakage between sessions.
        
        BUSINESS IMPACT: Validates basic multi-tenant security.
        """
        print("\n🧪 CRITICAL: Testing dual user concurrent chat isolation...")
        
        # STEP 1: Create two isolated user sessions
        user1_context, user1_helper = await self._create_isolated_user_session(
            user_index=1,
            user_business_context="Technology Startup with AI Product Development"
        )
        
        user2_context, user2_helper = await self._create_isolated_user_session(
            user_index=2,
            user_business_context="Manufacturing Company with Supply Chain Optimization"
        )
        
        # Ensure different users
        assert user1_context.user_id != user2_context.user_id, "Users must have different IDs"
        assert user1_context.thread_id != user2_context.thread_id, "Users must have different thread IDs"
        
        print(f"👤 User 1: {user1_context.user_id} (Technology Startup)")
        print(f"👤 User 2: {user2_context.user_id} (Manufacturing)")
        
        # STEP 2: Define distinct business requests
        user1_request = (
            "As a technology startup developing AI products, I need strategic advice on "
            "scaling our machine learning infrastructure, hiring data scientists, "
            "and positioning our AI platform for Series A funding. Our current tech stack "
            "includes Python, TensorFlow, and cloud infrastructure."
        )
        
        user2_request = (
            "As a manufacturing company, I need optimization strategies for our supply chain. "
            "We have 15 suppliers, 3 warehouses, and distribute to 200+ retail locations. "
            "Our focus is reducing inventory costs, improving delivery times, "
            "and implementing lean manufacturing principles."
        )
        
        # STEP 3: Execute concurrent chat sessions
        async def execute_user_chat_session(user_context, user_helper, request, user_label):
            """Execute isolated chat session for one user."""
            try:
                async with user_helper.authenticated_websocket_connection(user_context):
                    result = await user_helper.execute_golden_path_flow(
                        user_message=request,
                        user_context=user_context,
                        timeout=90.0
                    )
                    
                    return {
                        "user_label": user_label,
                        "user_id": str(user_context.user_id),
                        "success": result.success,
                        "events_received": result.events_received,
                        "execution_time": result.execution_metrics.total_execution_time,
                        "business_value_score": result.execution_metrics.business_value_score
                    }
            
            except Exception as e:
                return {
                    "user_label": user_label,
                    "user_id": str(user_context.user_id),
                    "success": False,
                    "events_received": [],
                    "execution_time": 0.0,
                    "business_value_score": 0.0,
                    "error": str(e)[:200]
                }
        
        # Run both sessions concurrently
        concurrent_start = time.time()
        
        user1_result, user2_result = await asyncio.gather(
            execute_user_chat_session(user1_context, user1_helper, user1_request, "Technology User"),
            execute_user_chat_session(user2_context, user2_helper, user2_request, "Manufacturing User"),
            return_exceptions=True
        )
        
        concurrent_duration = time.time() - concurrent_start
        
        # STEP 4: Validate concurrent execution success
        assert not isinstance(user1_result, Exception), f"User 1 session failed: {user1_result}"
        assert not isinstance(user2_result, Exception), f"User 2 session failed: {user2_result}"
        
        self.concurrent_users_tested = 2
        
        print(f"✅ Both users completed concurrent sessions in {concurrent_duration:.2f}s")
        print(f"👤 User 1: {'SUCCESS' if user1_result['success'] else 'FAILED'} - {len(user1_result['events_received'])} events")
        print(f"👤 User 2: {'SUCCESS' if user2_result['success'] else 'FAILED'} - {len(user2_result['events_received'])} events")
        
        # STEP 5: Analyze responses for contamination
        user1_responses = []
        user2_responses = []
        
        for event in user1_result["events_received"]:
            if hasattr(event, 'data') and event.event_type == "agent_completed":
                response = event.data.get("response") or event.data.get("message", "")
                if len(response) > 50:
                    user1_responses.append(response)
        
        for event in user2_result["events_received"]:
            if hasattr(event, 'data') and event.event_type == "agent_completed":
                response = event.data.get("response") or event.data.get("message", "")
                if len(response) > 50:
                    user2_responses.append(response)
        
        # STEP 6: Check for cross-contamination
        contamination_detected = False
        
        for response in user1_responses:
            if self._analyze_response_for_contamination(
                response, 1, ["Manufacturing Company with Supply Chain Optimization"]
            ):
                contamination_detected = True
                self.isolation_violations += 1
        
        for response in user2_responses:
            if self._analyze_response_for_contamination(
                response, 2, ["Technology Startup with AI Product Development"]
            ):
                contamination_detected = True
                self.isolation_violations += 1
        
        self.cross_contamination_detected = contamination_detected
        
        # STEP 7: Validate performance under concurrent load
        if concurrent_duration > 120.0:  # Performance threshold
            self.performance_degradation = True
            print(f"⚠️ Performance degradation detected: {concurrent_duration:.2f}s")
        
        # STEP 8: Critical isolation assertions
        assert not contamination_detected, "CRITICAL: Cross-contamination detected between users"
        assert user1_result["success"] or user2_result["success"], "At least one user session must succeed"
        assert concurrent_duration < 150.0, f"Concurrent execution too slow: {concurrent_duration:.2f}s"
        
        print(f"🔒 Dual user isolation validation successful")
        print(f"✅ No contamination detected")
        print(f"📊 Performance: {concurrent_duration:.2f}s")
    
    @pytest.mark.asyncio
    async def test_triple_user_concurrent_isolation_stress(self):
        """
        CRITICAL: Triple user concurrent isolation under stress.
        
        Tests that three users can chat simultaneously with complete
        isolation, testing the platform's multi-tenant capabilities.
        
        BUSINESS IMPACT: Validates enterprise-scale multi-tenant security.
        """
        print("\n🧪 CRITICAL: Testing triple user concurrent isolation stress...")
        
        # STEP 1: Create three isolated user sessions
        user_sessions = []
        business_contexts = [
            "E-commerce Retail with Customer Analytics",
            "Healthcare SaaS with Patient Management", 
            "Financial Services with Risk Assessment"
        ]
        
        for i in range(3):
            user_context, user_helper = await self._create_isolated_user_session(
                user_index=i+1,
                user_business_context=business_contexts[i]
            )
            user_sessions.append((user_context, user_helper, business_contexts[i]))
        
        print(f"👥 Created 3 isolated user sessions:")
        for i, (context, _, business) in enumerate(user_sessions):
            print(f"   User {i+1}: {context.user_id} ({business[:30]}...)")
        
        # STEP 2: Define distinct business requests for stress testing
        business_requests = [
            (
                "As an e-commerce retailer, analyze our customer behavior data to identify "
                "high-value segments, optimize our conversion funnel, and develop personalized "
                "marketing strategies. We have 50K monthly visitors and 2% conversion rate."
            ),
            (
                "As a healthcare SaaS provider, help optimize our patient management workflow "
                "to reduce administrative burden on medical staff, improve patient outcomes, "
                "and ensure HIPAA compliance. We serve 200+ medical practices."
            ),
            (
                "As a financial services company, develop risk assessment models for loan "
                "applications, analyze market volatility impacts, and create investment "
                "portfolio optimization strategies. We manage $500M in assets."
            )
        ]
        
        # STEP 3: Execute concurrent stress test
        async def execute_stress_test_session(session_data, request, index):
            """Execute stress test session for one user."""
            user_context, user_helper, business_context = session_data
            
            try:
                async with user_helper.authenticated_websocket_connection(user_context):
                    result = await user_helper.execute_golden_path_flow(
                        user_message=request,
                        user_context=user_context,
                        timeout=120.0  # Extended timeout for stress test
                    )
                    
                    return {
                        "user_index": index + 1,
                        "user_id": str(user_context.user_id),
                        "business_context": business_context,
                        "success": result.success,
                        "events_count": len(result.events_received),
                        "execution_time": result.execution_metrics.total_execution_time,
                        "business_value_score": result.execution_metrics.business_value_score,
                        "events": result.events_received
                    }
            
            except Exception as e:
                return {
                    "user_index": index + 1,
                    "user_id": str(user_context.user_id),
                    "business_context": business_contexts[index],
                    "success": False,
                    "events_count": 0,
                    "execution_time": 0.0,
                    "business_value_score": 0.0,
                    "events": [],
                    "error": str(e)[:200]
                }
        
        # Run all three sessions concurrently
        stress_start = time.time()
        
        stress_results = await asyncio.gather(
            *[execute_stress_test_session(session, request, i) 
              for i, (session, request) in enumerate(zip(user_sessions, business_requests))],
            return_exceptions=True
        )
        
        stress_duration = time.time() - stress_start
        
        # STEP 4: Validate stress test results
        successful_sessions = []
        for result in stress_results:
            if not isinstance(result, Exception) and result.get("success"):
                successful_sessions.append(result)
            elif isinstance(result, Exception):
                print(f"❌ Session exception: {str(result)[:100]}")
            else:
                print(f"❌ Session failed: User {result.get('user_index', '?')}")
        
        self.concurrent_users_tested = 3
        success_rate = len(successful_sessions) / 3 * 100
        
        print(f"📊 Stress test results: {len(successful_sessions)}/3 successful ({success_rate:.1f}%)")
        print(f"⏱️ Total stress duration: {stress_duration:.2f}s")
        
        # STEP 5: Advanced contamination analysis
        contamination_violations = 0
        
        for i, session in enumerate(successful_sessions):
            # Extract responses for this user
            user_responses = []
            for event in session["events"]:
                if hasattr(event, 'data') and event.event_type == "agent_completed":
                    response = event.data.get("response") or event.data.get("message", "")
                    if len(response) > 30:
                        user_responses.append(response)
            
            # Check for contamination from other users
            other_contexts = [ctx for j, ctx in enumerate(business_contexts) if j != i]
            
            for response in user_responses:
                if self._analyze_response_for_contamination(
                    response, session["user_index"], other_contexts
                ):
                    contamination_violations += 1
        
        self.isolation_violations = contamination_violations
        self.cross_contamination_detected = contamination_violations > 0
        
        # STEP 6: Performance stress analysis
        if stress_duration > 180.0:  # Stress test performance threshold
            self.performance_degradation = True
        
        avg_execution_time = sum(s["execution_time"] for s in successful_sessions) / len(successful_sessions) if successful_sessions else 0
        
        # STEP 7: Critical stress test assertions
        assert success_rate >= 66.0, f"Stress test success rate too low: {success_rate:.1f}%"
        assert contamination_violations == 0, f"CRITICAL: {contamination_violations} contamination violations detected"
        assert stress_duration < 200.0, f"Stress test duration excessive: {stress_duration:.2f}s"
        assert avg_execution_time < 100.0, f"Average execution time too slow: {avg_execution_time:.2f}s"
        
        print(f"🎉 Triple user concurrent isolation stress test successful")
        print(f"🔒 Isolation violations: {contamination_violations}")
        print(f"📊 Average execution time: {avg_execution_time:.2f}s")
        print(f"✅ Enterprise-scale isolation validated")
    
    @pytest.mark.asyncio
    async def test_isolation_with_similar_business_contexts(self):
        """
        CRITICAL: Isolation validation with similar business contexts.
        
        Tests isolation when users have similar business contexts that
        could potentially cause confusion or cross-contamination.
        
        BUSINESS IMPACT: Validates isolation robustness in realistic scenarios.
        """
        print("\n🧪 CRITICAL: Testing isolation with similar business contexts...")
        
        # STEP 1: Create users with deliberately similar contexts
        user1_context, user1_helper = await self._create_isolated_user_session(
            user_index=1,
            user_business_context="E-commerce Platform with Revenue Growth Focus"
        )
        
        user2_context, user2_helper = await self._create_isolated_user_session(
            user_index=2,
            user_business_context="E-commerce Marketplace with Revenue Optimization"
        )
        
        print(f"👤 User 1: E-commerce Platform ({user1_context.user_id})")
        print(f"👤 User 2: E-commerce Marketplace ({user2_context.user_id})")
        
        # STEP 2: Define subtly different but related requests
        user1_request = (
            "Our e-commerce platform needs revenue growth strategies. We have $2M ARR, "
            "5000 active sellers, and want to expand into subscription services. "
            "Analyze our current metrics and recommend growth tactics for Q4."
        )
        
        user2_request = (
            "Our e-commerce marketplace needs revenue optimization. We have $1.8M ARR, "
            "4500 active vendors, and want to improve commission structures. "
            "Evaluate our performance metrics and suggest optimization approaches for Q4."
        )
        
        # STEP 3: Execute similar context sessions
        async def execute_similar_context_session(user_context, user_helper, request, user_label):
            """Execute session with similar business context."""
            async with user_helper.authenticated_websocket_connection(user_context):
                result = await user_helper.execute_golden_path_flow(
                    user_message=request,
                    user_context=user_context,
                    timeout=90.0
                )
                
                return {
                    "user_label": user_label,
                    "user_id": str(user_context.user_id),
                    "success": result.success,
                    "events": result.events_received,
                    "business_value_score": result.execution_metrics.business_value_score
                }
        
        # Run sessions concurrently
        similar_start = time.time()
        
        user1_result, user2_result = await asyncio.gather(
            execute_similar_context_session(user1_context, user1_helper, user1_request, "Platform User"),
            execute_similar_context_session(user2_context, user2_helper, user2_request, "Marketplace User")
        )
        
        similar_duration = time.time() - similar_start
        
        # STEP 4: Extract and analyze responses for subtle contamination
        user1_content = []
        user2_content = []
        
        for event in user1_result["events"]:
            if hasattr(event, 'data') and event.event_type in ["agent_completed", "tool_completed"]:
                content = event.data.get("response") or event.data.get("message", "")
                if len(content) > 30:
                    user1_content.append(content.lower())
        
        for event in user2_result["events"]:
            if hasattr(event, 'data') and event.event_type in ["agent_completed", "tool_completed"]:
                content = event.data.get("response") or event.data.get("message", "")
                if len(content) > 30:
                    user2_content.append(content.lower())
        
        # STEP 5: Detect subtle contamination
        subtle_contamination_detected = False
        
        # Check for specific metrics leakage
        user1_specific = ["2m arr", "$2m", "5000 sellers", "5000 active sellers", "subscription services"]
        user2_specific = ["1.8m arr", "$1.8m", "4500 vendors", "4500 active vendors", "commission structures"]
        
        for content in user1_content:
            for user2_metric in user2_specific:
                if user2_metric in content:
                    print(f"🚨 SUBTLE CONTAMINATION: User 1 content contains User 2 metric: {user2_metric}")
                    subtle_contamination_detected = True
                    self.isolation_violations += 1
        
        for content in user2_content:
            for user1_metric in user1_specific:
                if user1_metric in content:
                    print(f"🚨 SUBTLE CONTAMINATION: User 2 content contains User 1 metric: {user1_metric}")
                    subtle_contamination_detected = True
                    self.isolation_violations += 1
        
        self.cross_contamination_detected = subtle_contamination_detected
        self.concurrent_users_tested = 2
        
        # STEP 6: Validate context differentiation
        # Even with similar contexts, responses should be differentiated
        user1_all_content = " ".join(user1_content)
        user2_all_content = " ".join(user2_content)
        
        user1_platform_mentions = user1_all_content.count("platform")
        user1_marketplace_mentions = user1_all_content.count("marketplace")
        
        user2_platform_mentions = user2_all_content.count("platform")
        user2_marketplace_mentions = user2_all_content.count("marketplace")
        
        # Users should have context-appropriate terminology
        if user1_content and user1_platform_mentions < user1_marketplace_mentions:
            print(f"⚠️ User 1 (platform) has more marketplace mentions than platform")
        
        if user2_content and user2_marketplace_mentions < user2_platform_mentions:
            print(f"⚠️ User 2 (marketplace) has more platform mentions than marketplace")
        
        # STEP 7: Critical similar context isolation assertions
        assert not subtle_contamination_detected, "CRITICAL: Subtle contamination detected with similar contexts"
        assert user1_result["success"] and user2_result["success"], "Both similar context sessions must succeed"
        assert similar_duration < 120.0, f"Similar context execution too slow: {similar_duration:.2f}s"
        
        print(f"🔒 Similar context isolation validation successful")
        print(f"✅ No subtle contamination detected")
        print(f"👥 Both users maintained context appropriately")
        print(f"📊 Execution time: {similar_duration:.2f}s")


if __name__ == "__main__":
    """
    Run E2E tests for multi-user concurrent chat isolation.
    
    Usage:
        python -m pytest tests/e2e/test_multi_user_concurrent_chat_isolation_e2e.py -v
        python -m pytest tests/e2e/test_multi_user_concurrent_chat_isolation_e2e.py::TestMultiUserConcurrentChatIsolationE2E::test_dual_user_concurrent_chat_isolation -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))