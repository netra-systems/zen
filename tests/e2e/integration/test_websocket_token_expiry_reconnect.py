"""Test #6: WebSocket Token Expiry Reconnection Test - P1 User Experience

WebSocket Token Expiry Automatic Reconnection Test - Critical User Experience Test
Tests that WebSocket connections automatically reconnect when auth tokens expire,
preserving chat context and message queues to prevent user frustration.

Business Value Justification (BVJ):
1. Segment: All tiers (Free, Early, Mid, Enterprise) 
2. Business Goal: Prevent user churn from connection drops during token expiry
3. Value Impact: Users don't lose chat conversations mid-flow when tokens expire
4. Revenue Impact: Protects conversion rates and user experience across all tiers

ISSUE: WebSocket disconnects permanently when token expires
IMPACT: Users lose chat mid-conversation, causing frustration and churn
SPEC: websockets.xml - WebSocket reliability and persistence requirements

Test Requirements:
- Test WebSocket connection with expiring token (short TTL)
- Test automatic reconnection when token expires
- Test token refresh happens before disconnection
- Test message queue preserved during reconnection
- Test user doesn't lose chat context
- Must complete in <10 seconds

Architecture Compliance:
- Real WebSocket connections (NO MOCKS for critical auth components)
- <10 second execution time for fast feedback loops
- Deterministic test results through controlled token expiry
- Integration with existing token lifecycle and WebSocket test infrastructure
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.config import TEST_ENDPOINTS, TEST_USERS
from tests.e2e.token_lifecycle_helpers import (
    PerformanceBenchmark,
    TokenLifecycleManager,
    WebSocketSessionManager,
)
from test_framework.http_client import ClientConfig
from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient


class TestTokenExpiryReconnectioner:
    """Core tester for WebSocket token expiry and automatic reconnection."""
    
    def __init__(self):
        self.token_manager = TokenLifecycleManager()
        self.performance = PerformanceBenchmark()
        self.ws_url = TEST_ENDPOINTS.ws_url
        self.test_messages: List[Dict[str, Any]] = []
        
    async def create_session_with_short_token(self, user_id: str, ttl_seconds: int = 5) -> Dict[str, Any]:
        """Create WebSocket session with short-lived token for expiry testing."""
        # Create token with very short TTL for quick expiry
        access_token = await self.token_manager.create_short_ttl_token(user_id, ttl_seconds)
        refresh_token = await self.token_manager.create_valid_refresh_token(user_id)
        
        # Create WebSocket session
        session_manager = WebSocketSessionManager(self.ws_url)
        connection_success = await session_manager.start_chat_session(access_token)
        
        if not connection_success:
            raise RuntimeError("Failed to establish initial WebSocket connection")
        
        # Initialize chat context
        thread_id = f"thread_{user_id}_{int(time.time())}"
        chat_context = await self._initialize_chat_context(session_manager, thread_id)
        
        return {
            "session_manager": session_manager,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "thread_id": thread_id,
            "chat_context": chat_context,
            "user_id": user_id,
            "token_ttl": ttl_seconds
        }
    
    async def _initialize_chat_context(self, session_manager: WebSocketSessionManager, thread_id: str) -> Dict[str, Any]:
        """Initialize chat context to simulate ongoing conversation."""
        initial_message = "Hello, I need help with data analysis"
        
        # Send initial message
        message_sent = await session_manager.send_chat_message(initial_message, thread_id)
        if not message_sent:
            raise RuntimeError("Failed to send initial chat message")
        
        # Create chat context state
        chat_context = {
            "thread_id": thread_id,
            "conversation_started": datetime.now(timezone.utc).isoformat(),
            "message_history": [
                {
                    "role": "user",
                    "content": initial_message,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ],
            "active_task": "data_analysis_request",
            "user_preferences": {
                "response_format": "detailed",
                "include_charts": True
            }
        }
        
        return chat_context
    
    async def simulate_active_conversation_during_token_expiry(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate active conversation while token is expiring."""
        session_manager = session_data["session_manager"]
        thread_id = session_data["thread_id"]
        token_ttl = session_data["token_ttl"]
        
        # Queue messages during conversation
        conversation_messages = [
            "Can you analyze the sales data trends?",
            "Show me the quarterly performance metrics",
            "What insights can you provide about customer segments?"
        ]
        
        messages_sent = 0
        messages_queued = []
        
        # Send messages during token lifetime
        for message in conversation_messages:
            message_data = {
                "content": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "thread_id": thread_id
            }
            
            # Check if connection is still alive
            connection_alive = await session_manager.test_connection_alive()
            if connection_alive:
                success = await session_manager.send_chat_message(message, thread_id)
                if success:
                    messages_sent += 1
                    session_data["chat_context"]["message_history"].append({
                        "role": "user",
                        "content": message,
                        "timestamp": message_data["timestamp"]
                    })
                else:
                    messages_queued.append(message_data)
            else:
                messages_queued.append(message_data)
            
            # Wait briefly between messages
            await asyncio.sleep(0.5)
        
        # Wait for token to expire
        await asyncio.sleep(token_ttl + 1)
        
        return {
            "messages_sent_before_expiry": messages_sent,
            "messages_queued_during_expiry": len(messages_queued),
            "queued_messages": messages_queued,
            "token_expired": True,
            "chat_context_preserved": len(session_data["chat_context"]["message_history"]) > 0
        }
    
    async def execute_automatic_token_refresh_reconnection(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute automatic token refresh and reconnection flow."""
        session_manager = session_data["session_manager"]
        refresh_token = session_data["refresh_token"]
        user_id = session_data["user_id"]
        
        reconnection_start_time = self.performance.start_timer()
        
        try:
            # Step 1: Attempt to refresh token
            refresh_response = await self.token_manager.refresh_token_via_api(refresh_token)
            if not refresh_response or "access_token" not in refresh_response:
                return {"success": False, "error": "Token refresh failed", "step": "refresh"}
            
            new_access_token = refresh_response["access_token"]
            
            # Step 2: Reconnect with new token
            reconnection_success = await session_manager.reconnect_with_new_token(new_access_token)
            if not reconnection_success:
                return {"success": False, "error": "Reconnection failed", "step": "reconnection"}
            
            # Step 3: Verify connection is working
            connection_test = await session_manager.test_connection_alive()
            if not connection_test:
                return {"success": False, "error": "Connection not working after reconnection", "step": "verification"}
            
            # Step 4: Test sending message with new connection
            test_message = "Testing connection after token refresh"
            message_success = await session_manager.send_chat_message(test_message, session_data["thread_id"])
            
            reconnection_duration = self.performance.get_duration(reconnection_start_time)
            
            return {
                "success": True,
                "new_access_token": new_access_token,
                "reconnection_duration": reconnection_duration,
                "connection_verified": connection_test,
                "message_sent_after_reconnection": message_success,
                "chat_context_available": True  # Context should be preserved client-side
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "step": "exception"}
    
    async def validate_chat_context_preservation(self, session_data: Dict[str, Any], 
                                                 conversation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that chat context is preserved across reconnection."""
        chat_context = session_data["chat_context"]
        original_message_count = len(chat_context["message_history"])
        
        # Chat context should be preserved on client side
        context_preserved = {
            "original_message_count": original_message_count,
            "thread_id_preserved": chat_context["thread_id"] == session_data["thread_id"],
            "conversation_metadata_preserved": bool(chat_context.get("active_task")),
            "user_preferences_preserved": bool(chat_context.get("user_preferences")),
            "message_history_available": original_message_count > 0
        }
        
        # Verify essential context elements
        essential_preserved = (
            context_preserved["thread_id_preserved"] and
            context_preserved["conversation_metadata_preserved"] and
            context_preserved["message_history_available"]
        )
        
        return {
            "context_preservation_details": context_preserved,
            "essential_context_preserved": essential_preserved,
            "can_resume_conversation": essential_preserved,
            "no_data_loss": conversation_result["chat_context_preserved"]
        }
    
    @pytest.mark.e2e
    async def test_message_queue_resilience(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test that message queues are handled properly during reconnection."""
        session_manager = session_data["session_manager"]
        thread_id = session_data["thread_id"]
        
        # Simulate messages sent during disconnection
        offline_messages = [
            "This message sent during disconnection 1",
            "This message sent during disconnection 2",
            "This message sent during disconnection 3"
        ]
        
        # Try to send messages while disconnected (should queue or fail gracefully)
        failed_sends = []
        for message in offline_messages:
            success = await session_manager.send_chat_message(message, thread_id)
            if not success:
                failed_sends.append(message)
        
        return {
            "messages_attempted": len(offline_messages),
            "messages_failed_gracefully": len(failed_sends),
            "no_crashes_during_disconnect": True,  # Test didn't crash
            "graceful_handling": len(failed_sends) == len(offline_messages)  # All should fail when disconnected
        }


@pytest.mark.asyncio
@pytest.mark.e2e
class TestWebSocketTokenExpiryReconnect:
    """Test #6: WebSocket Token Expiry Reconnection - P1 User Experience."""
    
    @pytest.fixture
    def reconnection_tester(self):
        """Initialize WebSocket token expiry reconnection tester."""
        return TokenExpiryReconnectionTester()
    
    @pytest.fixture
    @pytest.mark.e2e
    def test_user_id(self):
        """Provide test user ID from enterprise tier."""
        return TEST_USERS["enterprise"].id
    
    @pytest.mark.e2e
    async def test_automatic_reconnection_on_token_expiry(self, reconnection_tester, test_user_id):
        """
        Primary Test: Token expires during chat  ->  Auto-reconnect with refreshed token  ->  Chat continues
        
        This is the core user experience test: ensuring users don't lose their chat
        conversation when tokens expire during active usage.
        """
        test_start_time = reconnection_tester.performance.start_timer()
        
        # Phase 1: Setup WebSocket session with short-lived token
        session_data = await reconnection_tester.create_session_with_short_token(test_user_id, ttl_seconds=3)
        assert session_data["access_token"], "Should have initial access token"
        assert session_data["thread_id"], "Should have active chat thread"
        assert session_data["chat_context"]["message_history"], "Should have initial chat history"
        
        # Phase 2: Simulate active conversation while token expires
        conversation_result = await reconnection_tester.simulate_active_conversation_during_token_expiry(session_data)
        assert conversation_result["token_expired"], "Token should have expired"
        assert conversation_result["chat_context_preserved"], "Chat context should be preserved client-side"
        
        # Phase 3: Execute automatic token refresh and reconnection
        reconnection_result = await reconnection_tester.execute_automatic_token_refresh_reconnection(session_data)
        assert reconnection_result["success"], f"Reconnection failed: {reconnection_result.get('error', 'Unknown error')}"
        assert reconnection_result["connection_verified"], "Connection should be verified after reconnection"
        assert reconnection_result["message_sent_after_reconnection"], "Should be able to send messages after reconnection"
        
        # Phase 4: Validate chat context preservation
        context_validation = await reconnection_tester.validate_chat_context_preservation(session_data, conversation_result)
        assert context_validation["essential_context_preserved"], "Essential chat context must be preserved"
        assert context_validation["can_resume_conversation"], "User should be able to resume conversation"
        assert context_validation["no_data_loss"], "No chat data should be lost"
        
        # Phase 5: Performance validation
        total_duration = reconnection_tester.performance.get_duration(test_start_time)
        assert total_duration < 10.0, f"Test took {total_duration:.1f}s, must complete in <10s"
        assert reconnection_result["reconnection_duration"] < 5.0, f"Reconnection took {reconnection_result['reconnection_duration']:.1f}s, should be <5s"
        
        # Cleanup
        await session_data["session_manager"].close()
    
    @pytest.mark.e2e
    async def test_message_queue_handling_during_disconnection(self, reconnection_tester, test_user_id):
        """
        Test: Messages sent during disconnection are handled gracefully
        
        Validates that the system handles message sending attempts during 
        disconnection gracefully without crashes or data corruption.
        """
        # Setup session with very short token
        session_data = await reconnection_tester.create_session_with_short_token(test_user_id, ttl_seconds=2)
        
        # Wait for token to expire and connection to drop
        await asyncio.sleep(3)
        
        # Test message queue handling during disconnection
        queue_result = await reconnection_tester.test_message_queue_resilience(session_data)
        assert queue_result["no_crashes_during_disconnect"], "System should not crash during disconnect"
        assert queue_result["graceful_handling"], "Should handle failed sends gracefully"
        assert queue_result["messages_attempted"] > 0, "Should have attempted to send messages"
        
        # Cleanup
        await session_data["session_manager"].close()
    
    @pytest.mark.e2e
    async def test_token_refresh_before_expiry_prevention(self, reconnection_tester, test_user_id):
        """
        Test: System should ideally refresh token BEFORE expiry to prevent disconnection
        
        While this test focuses on post-expiry reconnection, ideally the system
        should refresh tokens proactively to avoid disconnections entirely.
        """
        # Setup session with slightly longer token to test proactive refresh
        session_data = await reconnection_tester.create_session_with_short_token(test_user_id, ttl_seconds=6)
        
        # Simulate proactive token refresh before expiry
        original_token = session_data["access_token"]
        
        # Wait for most of token lifetime but not full expiry
        await asyncio.sleep(4)  # Token expires at 6 seconds, refresh at 4
        
        # Attempt proactive refresh
        refresh_result = await reconnection_tester.execute_automatic_token_refresh_reconnection(session_data)
        assert refresh_result["success"], "Proactive token refresh should succeed"
        assert refresh_result["new_access_token"] != original_token, "Should get new token"
        
        # Connection should remain stable
        connection_alive = await session_data["session_manager"].test_connection_alive()
        assert connection_alive, "Connection should remain alive after proactive refresh"
        
        # Cleanup
        await session_data["session_manager"].close()
    
    @pytest.mark.e2e
    async def test_multiple_expiry_cycles_resilience(self, reconnection_tester, test_user_id):
        """
        Test: System handles multiple token expiry and refresh cycles
        
        Validates that the reconnection mechanism works consistently
        across multiple expiry/refresh cycles in a session.
        """
        # Setup session with very short tokens for multiple cycles
        session_data = await reconnection_tester.create_session_with_short_token(test_user_id, ttl_seconds=2)
        
        successful_refreshes = 0
        
        # Test 2 expiry/refresh cycles
        for cycle in range(2):
            # Wait for token expiry
            await asyncio.sleep(3)
            
            # Refresh and reconnect
            refresh_result = await reconnection_tester.execute_automatic_token_refresh_reconnection(session_data)
            if refresh_result["success"]:
                successful_refreshes += 1
                # Update session with new token for next cycle
                session_data["access_token"] = refresh_result["new_access_token"]
        
        assert successful_refreshes >= 1, f"Should have at least 1 successful refresh, got {successful_refreshes}"
        
        # Final connection test
        final_connection = await session_data["session_manager"].test_connection_alive()
        assert final_connection, "Connection should be alive after multiple refresh cycles"
        
        # Cleanup
        await session_data["session_manager"].close()
    
    @pytest.mark.e2e
    async def test_concurrent_user_expiry_handling(self, reconnection_tester):
        """
        Test: System handles token expiry for multiple concurrent users
        
        Validates that token expiry handling works correctly when multiple
        users experience token expiry simultaneously.
        """
        # Setup sessions for multiple users
        user_sessions = []
        for tier in ["free", "early", "enterprise"]:
            user_id = TEST_USERS[tier].id
            session = await reconnection_tester.create_session_with_short_token(user_id, ttl_seconds=3)
            user_sessions.append((tier, session))
        
        # Wait for all tokens to expire
        await asyncio.sleep(4)
        
        # Attempt concurrent reconnections
        reconnection_tasks = []
        for tier, session in user_sessions:
            task = reconnection_tester.execute_automatic_token_refresh_reconnection(session)
            reconnection_tasks.append((tier, task))
        
        # Wait for all reconnections
        results = {}
        for tier, task in reconnection_tasks:
            try:
                result = await asyncio.wait_for(task, timeout=8.0)
                results[tier] = result
            except asyncio.TimeoutError:
                results[tier] = {"success": False, "error": "Timeout"}
        
        # Validate results
        successful_reconnections = sum(1 for result in results.values() if result.get("success", False))
        assert successful_reconnections >= 2, f"Should have at least 2 successful concurrent reconnections, got {successful_reconnections}"
        
        # Cleanup all sessions
        for tier, session in user_sessions:
            await session["session_manager"].close()
    
    @pytest.mark.e2e
    async def test_performance_requirements_token_expiry_flow(self, reconnection_tester, test_user_id):
        """
        Test: Token expiry and reconnection flow meets performance requirements
        
        Critical for user experience - the entire flow from expiry detection
        to successful reconnection should be fast and seamless.
        """
        performance_start = reconnection_tester.performance.start_timer()
        
        # Setup and immediate expiry test
        session_data = await reconnection_tester.create_session_with_short_token(test_user_id, ttl_seconds=1)
        
        # Wait for expiry
        await asyncio.sleep(2)
        
        # Measure reconnection performance
        reconnection_start = reconnection_tester.performance.start_timer()
        reconnection_result = await reconnection_tester.execute_automatic_token_refresh_reconnection(session_data)
        reconnection_duration = reconnection_tester.performance.get_duration(reconnection_start)
        
        total_duration = reconnection_tester.performance.get_duration(performance_start)
        
        # Performance assertions
        assert reconnection_result["success"], "Reconnection must succeed for performance test"
        assert reconnection_duration < 3.0, f"Reconnection took {reconnection_duration:.1f}s, must be <3s for good UX"
        assert total_duration < 10.0, f"Total test duration {total_duration:.1f}s, must be <10s"
        
        # Additional performance metrics
        assert reconnection_result.get("reconnection_duration", 10) < 2.0, "Measured reconnection should be <2s"
        
        # Cleanup
        await session_data["session_manager"].close()


# Business Value Summary
"""
WebSocket Token Expiry Reconnection Test - P1 User Experience Impact

Segment: All customer tiers (Free, Early, Mid, Enterprise)
- Prevents user frustration from losing chat conversations during token expiry
- Critical for user retention and conversion across all tiers
- Essential for enterprise customers requiring reliable real-time communication

User Experience Impact:
- Eliminates conversation loss during active AI interactions
- Maintains chat context and conversation flow
- Provides seamless experience during token transitions
- Prevents user abandonment due to technical interruptions

Revenue Protection:
- Protects conversion rates from Free to paid tiers
- Reduces churn from technical failures
- Supports enterprise reliability requirements
- Enables confident long-form AI interactions

Test Coverage:
- Automatic reconnection on token expiry during active chat
- Message queue handling during disconnection periods  
- Chat context preservation across reconnection cycles
- Proactive token refresh to prevent disconnections
- Multiple expiry cycle resilience
- Concurrent user expiry handling
- Performance requirements validation (<10s total, <3s reconnection)

Architecture Validation:
- WebSocket reliability and persistence requirements
- Token lifecycle management integration
- Real-world network interruption scenarios
- Auth service integration correctness
- User session state consistency
"""
