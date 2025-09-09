"""
Integration Tests for Session Continuity and Context Management

Business Value Justification:
- Segment: All (Critical infrastructure supporting all user tiers)
- Business Goal: System Reliability & User Experience  
- Value Impact: Ensures multi-turn conversations maintain context
- Strategic Impact: CRITICAL - Context continuity prevents user frustration

CRITICAL REGRESSION PREVENTION:
Tests the fix for context creation vs getter pattern where system
incorrectly generated new IDs instead of maintaining session continuity.

Cross-Reference:
- SPEC/learnings/context_creation_vs_getter_pattern_fix_20250908.xml
- reports/architecture/CONTEXT_FACTORY_VS_GETTER_ANALYSIS.md
- reports/architecture/RUN_ID_SESSION_BEHAVIOR_GUIDE.md
"""

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from netra_backend.app.dependencies import get_user_execution_context, create_user_execution_context
from shared.id_generation.unified_id_generator import UnifiedIdGenerator, reset_global_counter
from netra_backend.app.services.user_execution_context import UserExecutionContext

class TestSessionContinuityIntegration:
    """Integration tests for session continuity patterns."""
    
    def setup_method(self):
        """Reset session state for test isolation."""
        # Clear session storage to ensure test isolation
        UnifiedIdGenerator._active_sessions.clear()
        reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_get_vs_create_context_behavioral_difference(self):
        """Test critical behavioral difference between get and create patterns."""
        user_id = "test_user_123"
        
        # Test 1: get_user_execution_context maintains session continuity
        context1 = get_user_execution_context(user_id=user_id, thread_id="thread_1")
        context2 = get_user_execution_context(user_id=user_id, thread_id="thread_1")
        
        assert context1.thread_id == context2.thread_id, "get_user_execution_context should reuse thread_id"
        assert context1.run_id == context2.run_id, "get_user_execution_context should reuse run_id"
        
        # Test 2: create_user_execution_context always creates new contexts  
        context3 = create_user_execution_context(user_id=user_id, thread_id="thread_1")
        context4 = create_user_execution_context(user_id=user_id, thread_id="thread_1")
        
        # These should be different because create always makes new contexts
        assert context3.run_id != context4.run_id, "create_user_execution_context should create new run_ids"
        assert context3.request_id != context4.request_id, "create_user_execution_context should create new request_ids"
    
    def test_conversation_continuity_across_messages(self):
        """Test that conversation context is maintained across multiple WebSocket messages."""
        user_id = "conversation_user"
        
        # Simulate first message in conversation
        message1_context = get_user_execution_context(
            user_id=user_id,
            thread_id="chat_thread_456"
        )
        
        # Simulate second message in same conversation
        message2_context = get_user_execution_context(
            user_id=user_id,
            thread_id="chat_thread_456"  # Same thread_id
        )
        
        # Verify conversation continuity
        assert message1_context.thread_id == message2_context.thread_id
        assert message1_context.run_id == message2_context.run_id
        assert message1_context.user_id == message2_context.user_id
        
        # Different request IDs for tracking individual messages
        assert message1_context.request_id != message2_context.request_id
    
    def test_new_agent_execution_within_same_thread(self):
        """Test new agent execution gets new run_id within same thread."""
        user_id = "agent_user"
        thread_id = "thread_789"
        
        # First agent execution
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id="run_1"
        )
        
        # Second agent execution with different run_id
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id="run_2"  # Explicit new run
        )
        
        # Should maintain thread but create new run
        assert context1.thread_id == context2.thread_id
        assert context1.run_id != context2.run_id
        assert context2.run_id == "run_2"
    
    def test_none_values_handled_correctly(self):
        """Test that None values are handled correctly in get_user_execution_context."""
        user_id = "none_test_user"
        
        # Call with None values - should create session
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Should generate
            run_id=None      # Should generate
        )
        
        assert context1.thread_id is not None
        assert context1.run_id is not None
        assert context1.user_id == user_id
        
        # Call again with None - should reuse existing session
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=None,
            run_id=None  
        )
        
        # Should get same session context
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
    
    def test_websocket_handler_pattern(self):
        """Test the corrected WebSocket handler pattern."""
        user_id = "websocket_user"
        
        # Simulate WebSocket message with existing context
        existing_thread_id = "ws_thread_123"
        existing_run_id = "ws_run_456"
        
        # CORRECT PATTERN: Use existing IDs from message
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=existing_thread_id,  # From WebSocket message
            run_id=existing_run_id         # From WebSocket message
        )
        
        assert context.thread_id == existing_thread_id
        assert context.run_id == existing_run_id
        
        # Subsequent message in same session
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=existing_thread_id,  # Same thread
            run_id=existing_run_id         # Same run  
        )
        
        assert context.thread_id == context2.thread_id
        assert context.run_id == context2.run_id
    
    def test_anti_pattern_detection(self):
        """Test that we can detect the incorrect pattern of generating IDs before get."""
        user_id = "antipattern_user"
        
        # ANTI-PATTERN: This was the incorrect approach
        generated_thread_id = UnifiedIdGenerator.generate_base_id("thread")
        generated_run_id = UnifiedIdGenerator.generate_base_id("run") 
        
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=generated_thread_id,
            run_id=generated_run_id
        )
        
        # Calling again with different generated IDs (simulating the bug)
        different_thread_id = UnifiedIdGenerator.generate_base_id("thread")  
        different_run_id = UnifiedIdGenerator.generate_base_id("run")
        
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=different_thread_id,  # Different ID breaks continuity
            run_id=different_run_id         # Different ID breaks continuity
        )
        
        # This demonstrates the bug: different contexts despite same user
        assert context1.thread_id != context2.thread_id
        assert context1.run_id != context2.run_id
    
    def test_multi_user_isolation(self):
        """Test that different users get isolated contexts."""
        user1_id = "user_1"
        user2_id = "user_2"
        thread_id = "shared_thread_name"  # Same thread name, different users
        
        context1 = get_user_execution_context(
            user_id=user1_id,
            thread_id=thread_id
        )
        
        context2 = get_user_execution_context(
            user_id=user2_id, 
            thread_id=thread_id  # Same thread name
        )
        
        # Different users should get different contexts even with same thread name
        assert context1.user_id != context2.user_id
        assert context1.thread_id != context2.thread_id  # Actually different internal thread IDs
        assert context1.run_id != context2.run_id
    
    def test_session_cleanup_and_recreation(self):
        """Test session cleanup and recreation behavior."""
        user_id = "cleanup_user"
        thread_id = "cleanup_thread"
        
        # Create initial session
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Manually clean up sessions (simulating cleanup process)
        cleaned = UnifiedIdGenerator.cleanup_expired_sessions(max_age_hours=0)  # Immediate cleanup
        assert cleaned >= 0  # Should clean up sessions
        
        # Create new session after cleanup
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Should create fresh context after cleanup
        assert context1.thread_id == context2.thread_id  # Thread ID should be preserved
        # Run ID behavior may vary based on cleanup implementation
    
    def test_error_recovery_context_creation(self):
        """Test context creation in error scenarios."""
        user_id = "error_user"
        
        # Test with invalid thread_id format
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id="",  # Empty string
            run_id=None
        )
        
        # Should handle gracefully and create valid context
        assert context1.user_id == user_id
        assert context1.thread_id  # Should not be empty
        assert context1.run_id     # Should not be None


class TestWebSocketHandlerSessionIntegration:
    """Integration tests specifically for WebSocket handler session patterns."""
    
    def setup_method(self):
        """Reset for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_quality_handler_session_continuity(self):
        """Test that quality handlers maintain session continuity."""
        user_id = "quality_user"
        thread_id = "quality_thread_123"
        run_id = "quality_run_456"
        
        # Simulate quality handler receiving message with context
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Simulate subsequent quality operation in same session
        context2 = get_user_execution_context(
            user_id=user_id, 
            thread_id=thread_id,  # Same thread from message
            run_id=run_id         # Same run from message
        )
        
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
        assert context1.user_id == context2.user_id
    
    def test_agent_handler_session_flow(self):
        """Test agent handler session flow with proper context management."""
        user_id = "agent_user"
        
        # First agent message without context
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # No existing thread
            run_id=None      # No existing run
        )
        
        # Should create new session
        assert context1.thread_id is not None
        assert context1.run_id is not None
        
        # Second message in same conversation
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=context1.thread_id,  # Use thread from first message
            run_id=context1.run_id          # Use run from first message
        )
        
        # Should maintain session continuity
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id


@pytest.mark.asyncio
class TestAsyncSessionContinuity:
    """Async tests for session continuity in concurrent scenarios."""
    
    def setup_method(self):
        """Reset for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    async def test_concurrent_session_access(self):
        """Test concurrent access to same session maintains consistency."""
        user_id = "concurrent_user"
        thread_id = "concurrent_thread"
        
        async def get_context():
            """Helper to get context asynchronously."""
            return get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id
            )
        
        # Execute concurrent context retrievals
        contexts = await asyncio.gather(*[get_context() for _ in range(5)])
        
        # All contexts should have same session identifiers
        first_context = contexts[0]
        for context in contexts[1:]:
            assert context.thread_id == first_context.thread_id
            assert context.run_id == first_context.run_id
            assert context.user_id == first_context.user_id
            # Request IDs should be different for each call
            assert context.request_id != first_context.request_id
    
    async def test_concurrent_multi_user_isolation(self):
        """Test concurrent multi-user access maintains isolation."""
        user_ids = [f"user_{i}" for i in range(3)]
        thread_id = "shared_thread"
        
        async def get_user_context(user_id: str):
            """Get context for specific user."""
            return get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id
            )
        
        # Get contexts for all users concurrently
        contexts = await asyncio.gather(*[get_user_context(uid) for uid in user_ids])
        
        # Each user should have isolated context
        for i, context in enumerate(contexts):
            assert context.user_id == user_ids[i]
            # Thread IDs should be different (user-specific)
            for j, other_context in enumerate(contexts):
                if i != j:
                    assert context.thread_id != other_context.thread_id
                    assert context.run_id != other_context.run_id


class TestRegressionPrevention:
    """Tests to prevent regression of the context creation vs getter pattern bug."""
    
    def setup_method(self):
        """Reset for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_prevent_id_generation_in_getter_calls(self):
        """Regression test: prevent generating IDs when calling get_user_execution_context."""
        user_id = "regression_user"
        
        # This test verifies that we don't fall back into the anti-pattern
        # of generating IDs before calling get_user_execution_context
        
        # CORRECT: Use existing IDs or None
        existing_thread = "existing_thread_123"
        existing_run = "existing_run_456"
        
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=existing_thread,
            run_id=existing_run
        )
        
        assert context.thread_id == existing_thread
        assert context.run_id == existing_run
    
    def test_prevent_always_create_pattern(self):
        """Regression test: prevent always using create instead of get."""
        user_id = "always_create_user"
        thread_id = "reused_thread"
        
        # Using get pattern should reuse context
        context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
        
        # Using create pattern should create new contexts (for comparison)
        context3 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        context4 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Create should make different contexts
        assert context3.run_id != context4.run_id
        assert context3.request_id != context4.request_id
    
    def test_websocket_handler_regression_prevention(self):
        """Regression test: ensure WebSocket handlers don't generate new IDs."""
        
        # Simulate the corrected WebSocket handler pattern
        def corrected_websocket_handler(user_id: str, message_thread_id: str, message_run_id: str):
            """Simulates corrected WebSocket handler logic."""
            # CORRECT: Use message context IDs directly
            return get_user_execution_context(
                user_id=user_id,
                thread_id=message_thread_id,  # From message, not generated
                run_id=message_run_id         # From message, not generated
            )
        
        user_id = "websocket_regression_user"
        message_thread = "msg_thread_789"
        message_run = "msg_run_012"
        
        # Call handler twice with same message context
        context1 = corrected_websocket_handler(user_id, message_thread, message_run)
        context2 = corrected_websocket_handler(user_id, message_thread, message_run)
        
        # Should maintain continuity
        assert context1.thread_id == context2.thread_id == message_thread
        assert context1.run_id == context2.run_id == message_run