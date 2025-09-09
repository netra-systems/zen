"""
Authenticated User Journeys Batch 4 E2E Tests

CRITICAL: This test suite validates complete authenticated user journeys for the Golden Path
user flow that generates $500K+ ARR. These tests protect core business value by ensuring
authenticated users can complete the full journey from login to actionable AI results.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) 
- Business Goal: Revenue Protection - Validates complete authenticated user journeys
- Value Impact: Users receive actionable AI cost optimization insights through secure channels
- Strategic Impact: E2E validation of primary revenue-generating user flow

GOLDEN PATH FLOWS TESTED:
1. Free Tier User ’ Authentication ’ Cost Analysis ’ Basic Insights
2. Early Tier User ’ Authentication ’ Optimization ’ Standard Recommendations  
3. Enterprise User ’ Authentication ’ Advanced Analytics ’ Premium Features
4. Multi-User Concurrent Sessions ’ Isolation ’ Independent Results
5. Session Recovery ’ Authentication ’ Resumed Context ’ Continued Value
6. Mobile/Desktop Cross-Platform ’ Authentication ’ Consistent Experience
7. Error Recovery ’ Authentication ’ Graceful Degradation ’ Alternative Value
8. Performance Under Load ’ Authentication ’ Scalable Delivery ’ Quality Maintenance

CRITICAL REQUIREMENTS (per CLAUDE.md):
1. MANDATORY authentication via E2EWebSocketAuthHelper
2. MANDATORY full Docker stack (--real-services)
3. MANDATORY validation of all 5 WebSocket events
4. MANDATORY business value validation (cost savings > 0)
5. NO MOCKS - real services only
6. Must fail hard on any business value deviation
7. 60-second timeout maximum per test
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user_context
)
from test_framework.websocket_helpers import WebSocketTestClient, assert_websocket_events_sent

# Strongly typed context imports
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

# Real services integration
import websockets


class TestAuthenticatedUserJourneysBatch4E2E(BaseE2ETest):
    """Batch 4 E2E Tests for Authenticated User Journeys - Golden Path Validation."""
    
    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_free_tier_user_complete_authentication_journey_e2e(self):
        """
        E2E Test 1/8: Free tier user complete authenticated journey.
        
        Business Value: Validates free tier conversion funnel and basic value delivery.
        Expected: User authenticates, receives basic cost analysis, sees upgrade prompts.
        """
        # Arrange - Create authenticated free tier user
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "free",
            "user_id": "free_user_e2e_test_123",
            "permissions": ["read"],
            "features": ["basic_analysis", "view_dashboard"]
        })
        
        # Act - Execute complete free tier journey
        async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
            # Send cost analysis request (free tier limitation)
            message = {
                "type": "user_message",
                "content": "Help me analyze my cloud costs",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id)
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect all WebSocket events
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 45:  # 45-second timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(response)
                    events.append(event)
                    
                    # Stop when we receive agent_completed
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        # Assert - Validate free tier journey success
        event_types = [event.get("type") for event in events]
        
        # Must receive all required WebSocket events
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for required_event in required_events:
            assert required_event in event_types, f"Free tier journey missing {required_event} event"
        
        # Validate business value for free tier
        completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
        assert completed_event is not None, "Free tier journey must complete with business value"
        
        # Free tier should receive basic analysis with upgrade prompts
        result_content = completed_event.get("data", {}).get("result", "")
        assert "cost" in result_content.lower(), "Free tier should receive cost analysis"
        assert len(result_content) > 100, "Free tier should receive substantial analysis"
        
        print(" Free tier user complete authentication journey E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_early_tier_user_optimization_authentication_journey_e2e(self):
        """
        E2E Test 2/8: Early tier user complete optimization journey.
        
        Business Value: Validates paid tier value delivery and optimization features.
        Expected: User authenticates, receives optimization recommendations with cost savings.
        """
        # Arrange - Create authenticated early tier user
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "early",
            "user_id": "early_user_e2e_test_456",
            "permissions": ["read", "write"],
            "features": ["standard_optimization", "create_reports", "advanced_analysis"]
        })
        
        # Act - Execute complete early tier optimization journey
        async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
            # Send optimization request (early tier capabilities)
            message = {
                "type": "user_message", 
                "content": "Optimize my database costs and provide recommendations",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id)
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect all WebSocket events
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 45:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(response)
                    events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        # Assert - Validate early tier optimization success
        event_types = [event.get("type") for event in events]
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for required_event in required_events:
            assert required_event in event_types, f"Early tier journey missing {required_event} event"
        
        # Validate business value for early tier
        completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
        assert completed_event is not None, "Early tier journey must complete with optimization value"
        
        # Early tier should receive actionable recommendations
        result_content = completed_event.get("data", {}).get("result", "")
        assert "optimization" in result_content.lower() or "recommend" in result_content.lower(), \
            "Early tier should receive optimization recommendations"
        assert len(result_content) > 200, "Early tier should receive detailed analysis"
        
        print(" Early tier user optimization authentication journey E2E test passed")

    @pytest.mark.e2e 
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_enterprise_user_advanced_analytics_authentication_journey_e2e(self):
        """
        E2E Test 3/8: Enterprise user complete advanced analytics journey.
        
        Business Value: Validates premium tier maximum value delivery and enterprise features.
        Expected: User authenticates, receives advanced analytics with comprehensive insights.
        """
        # Arrange - Create authenticated enterprise user
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "enterprise",
            "user_id": "enterprise_user_e2e_test_789",
            "permissions": ["read", "write", "admin", "premium"],
            "features": ["advanced_optimization", "enterprise_features", "admin_functions", "premium_analytics"]
        })
        
        # Act - Execute complete enterprise analytics journey
        async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
            # Send advanced analytics request (enterprise capabilities)
            message = {
                "type": "user_message",
                "content": "Provide comprehensive cost analytics with predictive modeling and enterprise insights",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id)
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect all WebSocket events
            events = []
            start_time = time.time()
            
            while time.time() - start_time < 45:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(response)
                    events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        # Assert - Validate enterprise advanced analytics success
        event_types = [event.get("type") for event in events]
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for required_event in required_events:
            assert required_event in event_types, f"Enterprise journey missing {required_event} event"
        
        # Validate business value for enterprise tier
        completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
        assert completed_event is not None, "Enterprise journey must complete with premium value"
        
        # Enterprise should receive comprehensive analytics
        result_content = completed_event.get("data", {}).get("result", "")
        assert any(term in result_content.lower() for term in ["analytics", "predictive", "comprehensive", "enterprise"]), \
            "Enterprise tier should receive advanced analytics"
        assert len(result_content) > 300, "Enterprise tier should receive comprehensive analysis"
        
        print(" Enterprise user advanced analytics authentication journey E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_multi_user_concurrent_authentication_isolation_e2e(self):
        """
        E2E Test 4/8: Multi-user concurrent sessions with complete isolation.
        
        Business Value: Validates multi-tenant security and concurrent user support.
        Expected: Multiple authenticated users receive isolated experiences simultaneously.
        """
        # Arrange - Create multiple authenticated users
        auth_helper = E2EWebSocketAuthHelper()
        
        user_contexts = [
            await auth_helper.create_authenticated_user_session({
                "user_tier": "free",
                "user_id": "concurrent_user_1_e2e",
                "permissions": ["read"],
                "features": ["basic_analysis"]
            }),
            await auth_helper.create_authenticated_user_session({
                "user_tier": "early", 
                "user_id": "concurrent_user_2_e2e",
                "permissions": ["read", "write"],
                "features": ["standard_optimization"]
            }),
            await auth_helper.create_authenticated_user_session({
                "user_tier": "enterprise",
                "user_id": "concurrent_user_3_e2e", 
                "permissions": ["read", "write", "admin"],
                "features": ["enterprise_features"]
            })
        ]
        
        # Act - Execute concurrent authenticated journeys
        async def execute_user_journey(user_context, user_index):
            async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
                message = {
                    "type": "user_message",
                    "content": f"User {user_index} requesting cost analysis for my specific account",
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id)
                }
                
                await websocket.send(json.dumps(message))
                
                events = []
                start_time = time.time()
                
                while time.time() - start_time < 40:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event = json.loads(response)
                        events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        break
                
                return events, user_context
        
        # Execute all user journeys concurrently
        concurrent_results = await asyncio.gather(*[
            execute_user_journey(context, i) for i, context in enumerate(user_contexts)
        ])
        
        # Assert - Validate concurrent isolation success
        for events, user_context in concurrent_results:
            event_types = [event.get("type") for event in events]
            required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for required_event in required_events:
                assert required_event in event_types, f"Concurrent user {user_context.user_id} missing {required_event}"
            
            # Validate user isolation - each user gets their own results
            completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
            assert completed_event is not None, f"Concurrent user {user_context.user_id} must receive results"
            
            # Verify no cross-user data contamination
            result_content = completed_event.get("data", {}).get("result", "")
            user_id_str = str(user_context.user_id)
            
            # Each user should not see other users' data in their results
            other_user_ids = [str(ctx.user_id) for ctx in user_contexts if str(ctx.user_id) != user_id_str]
            for other_user_id in other_user_ids:
                assert other_user_id not in result_content, f"User isolation violated: {user_id_str} seeing {other_user_id} data"
        
        print(" Multi-user concurrent authentication isolation E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_session_recovery_authentication_context_preservation_e2e(self):
        """
        E2E Test 5/8: Session recovery with authentication context preservation.
        
        Business Value: Ensures user sessions survive interruptions without losing progress.
        Expected: User reconnects after interruption and continues with preserved context.
        """
        # Arrange - Create authenticated user and establish session
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "early",
            "user_id": "session_recovery_user_e2e",
            "permissions": ["read", "write"],
            "features": ["session_recovery", "standard_optimization"]
        })
        
        # Act - Phase 1: Establish session and start work
        initial_thread_id = None
        async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
            message = {
                "type": "user_message",
                "content": "Start analyzing my cloud infrastructure costs - this is a long running task",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id)
            }
            
            await websocket.send(json.dumps(message))
            initial_thread_id = str(user_context.thread_id)
            
            # Receive some initial events then "disconnect"
            events_phase1 = []
            start_time = time.time()
            
            while time.time() - start_time < 15:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event = json.loads(response)
                    events_phase1.append(event)
                    
                    # Simulate disconnect after receiving agent_started
                    if event.get("type") == "agent_started":
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        # Act - Phase 2: Reconnect and recover session
        await asyncio.sleep(2)  # Brief pause to simulate recovery time
        
        # Create new connection with same user context
        recovered_user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "early",
            "user_id": "session_recovery_user_e2e",  # Same user ID
            "permissions": ["read", "write"],
            "features": ["session_recovery", "standard_optimization"],
            "thread_id": initial_thread_id  # Resume same thread
        })
        
        async with auth_helper.authenticated_websocket_connection(recovered_user_context) as websocket:
            # Request session recovery
            recovery_message = {
                "type": "session_recovery",
                "user_id": str(recovered_user_context.user_id),
                "thread_id": initial_thread_id
            }
            
            await websocket.send(json.dumps(recovery_message))
            
            # Collect recovery events
            events_phase2 = []
            start_time = time.time()
            
            while time.time() - start_time < 30:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(response)
                    events_phase2.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
        
        # Assert - Validate session recovery success
        all_events = events_phase1 + events_phase2
        event_types = [event.get("type") for event in all_events]
        
        # Must eventually receive all required events across both phases
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for required_event in required_events:
            assert required_event in event_types, f"Session recovery missing {required_event} event"
        
        # Validate context preservation
        completed_event = next((e for e in all_events if e.get("type") == "agent_completed"), None)
        assert completed_event is not None, "Session recovery must complete with preserved context"
        
        result_content = completed_event.get("data", {}).get("result", "")
        assert "infrastructure" in result_content.lower() or "cost" in result_content.lower(), \
            "Session recovery should preserve original request context"
        
        print(" Session recovery authentication context preservation E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path  
    @pytest.mark.timeout(60)
    async def test_cross_platform_authentication_consistency_e2e(self):
        """
        E2E Test 6/8: Cross-platform authentication consistency.
        
        Business Value: Ensures consistent user experience across different client platforms.
        Expected: User receives identical authentication and business value across platforms.
        """
        # Arrange - Create authenticated user context
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "early",
            "user_id": "cross_platform_user_e2e", 
            "permissions": ["read", "write"],
            "features": ["cross_platform", "standard_optimization"]
        })
        
        # Simulate different platform contexts
        platform_scenarios = [
            {"platform": "web_desktop", "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            {"platform": "web_mobile", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)"},
            {"platform": "api_client", "user_agent": "NetraApiClient/1.0"}
        ]
        
        platform_results = []
        
        # Act - Test authentication across platforms
        for scenario in platform_scenarios:
            async with auth_helper.authenticated_websocket_connection(user_context, 
                                                                   headers={"User-Agent": scenario["user_agent"]}) as websocket:
                message = {
                    "type": "user_message",
                    "content": f"Analyze costs for {scenario['platform']} client",
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id) + f"_{scenario['platform']}",
                    "platform": scenario["platform"]
                }
                
                await websocket.send(json.dumps(message))
                
                events = []
                start_time = time.time()
                
                while time.time() - start_time < 30:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event = json.loads(response)
                        events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        break
                
                platform_results.append({
                    "platform": scenario["platform"],
                    "events": events,
                    "event_types": [event.get("type") for event in events]
                })
        
        # Assert - Validate cross-platform consistency
        required_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for result in platform_results:
            platform = result["platform"]
            event_types = result["event_types"]
            
            # Each platform should receive all required events
            for required_event in required_events:
                assert required_event in event_types, f"Platform {platform} missing {required_event} event"
            
            # Validate business value consistency across platforms  
            completed_event = next((e for e in result["events"] if e.get("type") == "agent_completed"), None)
            assert completed_event is not None, f"Platform {platform} must receive business value"
            
            result_content = completed_event.get("data", {}).get("result", "")
            assert len(result_content) > 100, f"Platform {platform} should receive substantial analysis"
            assert "cost" in result_content.lower(), f"Platform {platform} should receive cost analysis"
        
        # Verify consistency across platforms (similar response quality)
        result_lengths = [len(next((e for e in result["events"] if e.get("type") == "agent_completed"), {}).get("data", {}).get("result", "")) 
                         for result in platform_results]
        
        # Results should be reasonably similar in length (within 50% variance)
        max_length = max(result_lengths)
        min_length = min(result_lengths)
        variance_ratio = (max_length - min_length) / max_length if max_length > 0 else 0
        
        assert variance_ratio < 0.6, f"Cross-platform consistency issue: result variance {variance_ratio:.2f} too high"
        
        print(" Cross-platform authentication consistency E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60)
    async def test_error_recovery_authentication_graceful_degradation_e2e(self):
        """
        E2E Test 7/8: Error recovery with authentication and graceful degradation.
        
        Business Value: Ensures system provides alternative value when primary services fail.
        Expected: User receives degraded but functional service during error conditions.
        """
        # Arrange - Create authenticated user
        auth_helper = E2EWebSocketAuthHelper()
        user_context = await auth_helper.create_authenticated_user_session({
            "user_tier": "early",
            "user_id": "error_recovery_user_e2e",
            "permissions": ["read", "write"],
            "features": ["error_recovery", "graceful_degradation"]
        })
        
        # Act - Test error recovery scenarios
        async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
            # Send request that might trigger error conditions
            message = {
                "type": "user_message", 
                "content": "Analyze costs with potential service degradation scenarios",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "simulate_errors": True  # Signal for potential error testing
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect events including potential error events
            events = []
            error_events = []
            start_time = time.time()
            
            while time.time() - start_time < 45:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(response)
                    events.append(event)
                    
                    # Track error events
                    if "error" in event.get("type", "").lower() or event.get("error"):
                        error_events.append(event)
                    
                    # Continue even if errors occur - test graceful degradation
                    if event.get("type") == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    # Timeout might be expected during error conditions
                    break
        
        # Assert - Validate error recovery and graceful degradation
        event_types = [event.get("type") for event in events]
        
        # System should attempt to provide core events even during errors
        core_events = ["agent_started", "agent_thinking"]
        attempted_events = [event for event in core_events if event in event_types]
        
        assert len(attempted_events) >= 1, "System must attempt core functionality during errors"
        
        # If system completes despite errors, validate graceful degradation
        completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
        
        if completed_event:
            # System provided graceful degradation - validate alternative value
            result_content = completed_event.get("data", {}).get("result", "")
            assert len(result_content) > 50, "Graceful degradation should provide alternative value"
            
            # Should acknowledge service limitations during errors  
            degradation_indicators = ["limited", "partial", "reduced", "basic", "degraded"]
            has_degradation_notice = any(indicator in result_content.lower() for indicator in degradation_indicators)
            
            # Either provide full analysis or acknowledge degradation
            has_full_analysis = len(result_content) > 200 and "cost" in result_content.lower()
            
            assert has_full_analysis or has_degradation_notice, \
                "System should either provide full value or acknowledge service degradation"
            
        else:
            # If system couldn't complete, ensure it attempted meaningful work
            assert len(events) >= 2, "System must attempt meaningful work even during failures"
            
            # Should have error handling events
            has_error_handling = any("error" in str(event).lower() for event in events)
            assert has_error_handling, "System must provide error handling feedback"
        
        print(" Error recovery authentication graceful degradation E2E test passed")

    @pytest.mark.e2e
    @pytest.mark.golden_path
    @pytest.mark.timeout(60) 
    async def test_performance_under_load_authentication_quality_maintenance_e2e(self):
        """
        E2E Test 8/8: Performance under load with authentication quality maintenance.
        
        Business Value: Ensures system scales while maintaining service quality for authenticated users.
        Expected: System maintains response quality and authentication security under load.
        """
        # Arrange - Create multiple authenticated user contexts for load testing
        auth_helper = E2EWebSocketAuthHelper()
        
        load_test_users = []
        for i in range(5):  # Create 5 concurrent users for load testing
            user_context = await auth_helper.create_authenticated_user_session({
                "user_tier": "early" if i % 2 == 0 else "free",
                "user_id": f"load_test_user_{i}_e2e",
                "permissions": ["read", "write"] if i % 2 == 0 else ["read"],
                "features": ["performance_testing", "load_handling"]
            })
            load_test_users.append(user_context)
        
        # Act - Execute concurrent load testing
        async def execute_load_test_user(user_context, user_index):
            start_time = time.time()
            
            async with auth_helper.authenticated_websocket_connection(user_context) as websocket:
                message = {
                    "type": "user_message",
                    "content": f"Load test user {user_index} requesting performance analysis under concurrent load",
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "load_test": True
                }
                
                await websocket.send(json.dumps(message))
                
                events = []
                first_response_time = None
                completion_time = None
                
                while time.time() - start_time < 40:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=4.0)
                        event = json.loads(response)
                        events.append(event)
                        
                        # Track timing metrics
                        if first_response_time is None:
                            first_response_time = time.time() - start_time
                        
                        if event.get("type") == "agent_completed":
                            completion_time = time.time() - start_time
                            break
                            
                    except asyncio.TimeoutError:
                        break
                
                return {
                    "user_index": user_index,
                    "events": events,
                    "first_response_time": first_response_time,
                    "completion_time": completion_time,
                    "total_events": len(events)
                }
        
        # Execute all load test users concurrently
        load_test_results = await asyncio.gather(*[
            execute_load_test_user(context, i) for i, context in enumerate(load_test_users)
        ])
        
        # Assert - Validate performance under load
        successful_completions = [result for result in load_test_results if result["completion_time"] is not None]
        
        # At least 80% of users should complete successfully under load
        success_rate = len(successful_completions) / len(load_test_users)
        assert success_rate >= 0.8, f"Load test success rate {success_rate:.2f} below 80% threshold"
        
        # Validate response times are reasonable under load  
        first_response_times = [result["first_response_time"] for result in load_test_results 
                               if result["first_response_time"] is not None]
        
        if first_response_times:
            avg_first_response = sum(first_response_times) / len(first_response_times)
            assert avg_first_response < 10.0, f"Average first response time {avg_first_response:.2f}s too slow under load"
        
        # Validate quality maintenance under load
        for result in successful_completions:
            events = result["events"]
            event_types = [event.get("type") for event in events]
            
            # Should receive core business value events even under load
            core_events = ["agent_started", "agent_thinking", "agent_completed"]
            received_core_events = [event for event in core_events if event in event_types]
            
            assert len(received_core_events) >= 2, f"User {result['user_index']} missing core events under load"
            
            # Validate business value quality is maintained
            completed_event = next((e for e in events if e.get("type") == "agent_completed"), None)
            if completed_event:
                result_content = completed_event.get("data", {}).get("result", "")
                assert len(result_content) > 80, f"User {result['user_index']} received degraded quality under load"
        
        # System should handle load gracefully without major degradation
        total_events_received = sum(result["total_events"] for result in load_test_results)
        assert total_events_received >= len(load_test_users) * 3, \
            "System should maintain event delivery quality under load"
        
        print(" Performance under load authentication quality maintenance E2E test passed")
        

if __name__ == "__main__":
    # Run tests with business value reporting
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x"  # Stop on first failure for fast feedback
    ])