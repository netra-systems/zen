"""
Context Creation vs Getter Regression Prevention Test

Business Value Justification (BVJ):
- Segment: All (Platform-critical functionality)
- Business Goal: Prevent conversation continuity breaks and memory leaks
- Value Impact: Ensures users maintain context across multi-turn conversations
- Strategic Impact: CRITICAL - Context reuse enables proper chat experiences

CRITICAL REGRESSION TEST: This test prevents regression of the architectural issue
identified in CONTEXT_CREATION_ARCHITECTURE_ANALYSIS.md where the system
creates new contexts for every message instead of reusing existing contexts
for the same thread_id.

This test validates:
1. get_user_execution_context() maintains session continuity (CORRECT)
2. create_user_execution_context() always creates new contexts (DEPRECATED)
3. Same thread_id should return same context instance across messages
4. Different thread_id should return different context instances
5. Context lifecycle management and memory efficiency

SSOT Compliance:
- Uses SSotBaseTestCase from test_framework/ssot/base_test_case.py
- Uses IsolatedEnvironment (no direct os.environ access)
- Uses UnifiedIdGenerator for consistent ID generation
- Follows proper absolute import patterns

Cross-Reference: 
- reports/architecture/CONTEXT_CREATION_ARCHITECTURE_ANALYSIS.md
- SPEC/learnings/context_creation_vs_getter_pattern_fix_20250908.xml
- netra_backend/app/dependencies.py (functions under test)
- shared/id_generation/unified_id_generator.py (session management)
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from typing import Optional, Dict, Any

# SSOT imports - absolute imports only
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.dependencies import get_user_execution_context, create_user_execution_context
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestContextCreationVsGetterRegression:
    """Unit tests to prevent context creation vs getter pattern regression."""
    
    def setup_method(self):
        """Reset state for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_get_user_execution_context_uses_session_manager(self):
        """Test that get_user_execution_context uses session manager for continuity."""
        user_id = "test_user"
        thread_id = "test_thread"
        run_id = "test_run"
        
        with patch.object(UnifiedIdGenerator, 'get_or_create_user_session') as mock_session:
            mock_session.return_value = {
                "thread_id": thread_id,
                "run_id": run_id,
                "request_id": "test_request"
            }
            
            result = get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Verify session manager was called with correct parameters
            mock_session.assert_called_once_with(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            assert isinstance(result, UserExecutionContext)
            assert result.user_id == user_id
    
    def test_create_user_execution_context_always_creates_new(self):
        """Test that create_user_execution_context always creates new contexts."""
        user_id = "test_user"
        thread_id = "test_thread" 
        
        # Create two contexts with same parameters
        context1 = create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        
        context2 = create_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Should be different instances with different IDs
        assert context1 is not context2
        assert context1.run_id != context2.run_id
        assert context1.request_id != context2.request_id
        assert context1.thread_id == context2.thread_id  # Thread ID should match input
    
    def test_get_context_with_none_values_handled_correctly(self):
        """Test that get_user_execution_context handles None values correctly."""
        user_id = "test_user"
        
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=None,  # Should be handled by session manager
            run_id=None      # Should be handled by session manager
        )
        
        assert context.user_id == user_id
        assert context.thread_id is not None  # Should be generated
        assert context.run_id is not None     # Should be generated
        assert context.request_id is not None # Should be generated
    
    def test_session_continuity_behavior(self):
        """Test that get_user_execution_context maintains session continuity."""
        user_id = "continuity_user"
        thread_id = "continuity_thread"
        
        # First call should create session
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Second call should reuse session
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )
        
        # Should have same thread and run IDs (session continuity)
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
        assert context1.user_id == context2.user_id
        
        # Different request IDs for tracking individual requests
        assert context1.request_id != context2.request_id
    
    def test_create_vs_get_pattern_distinction(self):
        """Test clear distinction between create and get patterns."""
        user_id = "pattern_test_user"
        thread_id = "pattern_thread"
        
        # Get pattern - should maintain session
        get_context1 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        get_context2 = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Create pattern - should always create new
        create_context1 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        create_context2 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Get pattern should reuse session
        assert get_context1.run_id == get_context2.run_id
        
        # Create pattern should make new contexts
        assert create_context1.run_id != create_context2.run_id
    
    def test_websocket_client_id_generation(self):
        """Test websocket_client_id generation in both patterns."""
        user_id = "websocket_user"
        
        with patch.object(UnifiedIdGenerator, 'generate_websocket_client_id') as mock_ws:
            mock_ws.return_value = "ws_client_test_123"
            
            # Test get pattern
            get_context = get_user_execution_context(user_id=user_id)
            
            # Test create pattern  
            create_context = create_user_execution_context(user_id=user_id, thread_id="test_thread")
            
            # Both should generate websocket client IDs
            mock_ws.assert_has_calls([call(user_id), call(user_id)])
            assert get_context.websocket_client_id == "ws_client_test_123"
            # Note: create_user_execution_context may handle websocket_client_id differently


class TestAntiPatternDetection:
    """Unit tests to detect and prevent anti-patterns."""
    
    def setup_method(self):
        """Reset state for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_detect_id_generation_before_get_call(self):
        """Test detection of anti-pattern: generating IDs before get_user_execution_context call."""
        user_id = "antipattern_user"
        
        # ANTI-PATTERN: Generating IDs before calling get function
        generated_thread = UnifiedIdGenerator.generate_base_id("thread")
        generated_run = UnifiedIdGenerator.generate_base_id("run")
        
        # This pattern breaks session continuity
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=generated_thread,
            run_id=generated_run
        )
        
        # If someone calls with different generated IDs, session breaks
        different_thread = UnifiedIdGenerator.generate_base_id("thread")
        different_run = UnifiedIdGenerator.generate_base_id("run")
        
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=different_thread,
            run_id=different_run
        )
        
        # This demonstrates the bug: contexts are different despite same user
        assert context1.thread_id != context2.thread_id
        assert context1.run_id != context2.run_id
        
        # This test documents the problematic behavior we want to avoid
    
    def test_correct_pattern_with_existing_ids(self):
        """Test correct pattern: using existing IDs from request context."""
        user_id = "correct_user"
        existing_thread = "existing_thread_123"
        existing_run = "existing_run_456"
        
        # CORRECT PATTERN: Use IDs from request/message context
        context1 = get_user_execution_context(
            user_id=user_id,
            thread_id=existing_thread,  # From WebSocket message
            run_id=existing_run         # From WebSocket message
        )
        
        context2 = get_user_execution_context(
            user_id=user_id,
            thread_id=existing_thread,  # Same from message
            run_id=existing_run         # Same from message
        )
        
        # Should maintain session continuity
        assert context1.thread_id == context2.thread_id == existing_thread
        assert context1.run_id == context2.run_id == existing_run
    
    def test_prevent_test_code_using_get_pattern(self):
        """Test that demonstrates why test code should use create, not get."""
        user_id = "test_isolation_user"
        thread_id = "test_thread"
        
        # In test code, using get can cause cross-test contamination
        # This test shows the problem:
        
        # First "test" creates session
        test1_context = get_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Second "test" might get contaminated state
        test2_context = get_user_execution_context(user_id=user_id, thread_id=thread_id) 
        
        # Same session = contamination risk
        assert test1_context.run_id == test2_context.run_id
        
        # Tests should use create for isolation
        isolated_context1 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        isolated_context2 = create_user_execution_context(user_id=user_id, thread_id=thread_id)
        
        # Different contexts = proper test isolation
        assert isolated_context1.run_id != isolated_context2.run_id


class TestWebSocketHandlerPatterns:
    """Unit tests for WebSocket handler patterns to prevent regression."""
    
    def setup_method(self):
        """Reset state for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_websocket_handler_correct_pattern(self):
        """Test correct WebSocket handler pattern with existing message context."""
        
        class MockWebSocketMessage:
            """Mock WebSocket message with context."""
            def __init__(self, user_id: str, thread_id: Optional[str] = None, run_id: Optional[str] = None):
                self.user_id = user_id
                self.thread_id = thread_id
                self.run_id = run_id
                self.payload = {
                    "thread_id": thread_id,
                    "run_id": run_id
                }
        
        def correct_handler_pattern(message: MockWebSocketMessage) -> UserExecutionContext:
            """Demonstrates correct handler pattern."""
            # CORRECT: Extract from message context, don't generate
            thread_id = message.payload.get("thread_id") or message.thread_id
            run_id = message.payload.get("run_id")
            
            # Use existing IDs for session continuity
            return get_user_execution_context(
                user_id=message.user_id,
                thread_id=thread_id,  # From message context
                run_id=run_id         # From message context
            )
        
        # Test with message containing context
        message1 = MockWebSocketMessage("user_123", "thread_456", "run_789")
        context1 = correct_handler_pattern(message1)
        
        # Test with same context
        message2 = MockWebSocketMessage("user_123", "thread_456", "run_789")
        context2 = correct_handler_pattern(message2)
        
        # Should maintain continuity
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id
    
    def test_quality_handler_pattern_regression_prevention(self):
        """Test quality handler pattern to prevent regression."""
        
        def corrected_quality_handler(user_id: str, message_context: dict) -> UserExecutionContext:
            """Demonstrates corrected quality handler pattern."""
            # CORRECT: Use context from message, not generated IDs
            return get_user_execution_context(
                user_id=user_id,
                thread_id=message_context.get("thread_id"),  # From message
                run_id=message_context.get("run_id")         # From message
            )
        
        user_id = "quality_user"
        message_context = {
            "thread_id": "quality_thread_123",
            "run_id": "quality_run_456"
        }
        
        # Multiple calls should maintain continuity
        context1 = corrected_quality_handler(user_id, message_context)
        context2 = corrected_quality_handler(user_id, message_context)
        
        assert context1.thread_id == context2.thread_id
        assert context1.run_id == context2.run_id


class TestSessionManagerIntegration:
    """Unit tests for session manager integration."""
    
    def setup_method(self):
        """Reset state for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_session_manager_called_correctly(self):
        """Test that get_user_execution_context calls session manager with correct parameters."""
        user_id = "session_test_user"
        thread_id = "session_thread"
        run_id = "session_run"
        
        with patch.object(UnifiedIdGenerator, 'get_or_create_user_session') as mock_session:
            mock_session.return_value = {
                "thread_id": thread_id,
                "run_id": run_id,
                "request_id": "session_request"
            }
            
            get_user_execution_context(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
            
            # Verify session manager called with exact parameters
            mock_session.assert_called_once_with(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id
            )
    
    def test_session_manager_return_values_used(self):
        """Test that get_user_execution_context uses session manager return values."""
        user_id = "return_test_user"
        
        session_data = {
            "thread_id": "session_managed_thread",
            "run_id": "session_managed_run", 
            "request_id": "session_managed_request"
        }
        
        with patch.object(UnifiedIdGenerator, 'get_or_create_user_session') as mock_session:
            mock_session.return_value = session_data
            
            context = get_user_execution_context(user_id=user_id)
            
            # Verify context uses session manager values
            assert context.thread_id == session_data["thread_id"]
            assert context.run_id == session_data["run_id"]
            assert context.request_id == session_data["request_id"]
    
    def test_websocket_client_id_generation_called(self):
        """Test that websocket client ID is generated correctly."""
        user_id = "websocket_id_user"
        
        with patch.object(UnifiedIdGenerator, 'generate_websocket_client_id') as mock_ws:
            mock_ws.return_value = "test_ws_client_id"
            
            context = get_user_execution_context(user_id=user_id)
            
            # Verify websocket client ID generated for user
            mock_ws.assert_called_once_with(user_id)
            assert context.websocket_client_id == "test_ws_client_id"


@pytest.mark.parametrize("thread_id,run_id,expected_behavior", [
    (None, None, "creates_new_session"),
    ("existing_thread", None, "continues_thread_new_run"), 
    (None, "existing_run", "creates_thread_uses_run"),
    ("existing_thread", "existing_run", "uses_both_existing"),
])
class TestParameterizedContextBehavior:
    """Parametrized tests for different context parameter combinations."""
    
    def setup_method(self):
        """Reset state for test isolation."""
        UnifiedIdGenerator._active_sessions.clear()
        UnifiedIdGenerator.reset_global_counter()
    
    def teardown_method(self):
        """Clean up after tests."""
        UnifiedIdGenerator._active_sessions.clear()
    
    def test_context_parameter_combinations(self, thread_id, run_id, expected_behavior):
        """Test different parameter combinations behave correctly."""
        user_id = "param_test_user"
        
        context = get_user_execution_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Basic assertions that apply to all cases
        assert context.user_id == user_id
        assert context.thread_id is not None
        assert context.run_id is not None
        assert context.request_id is not None
        assert context.websocket_client_id is not None
        
        # Specific behavior verification based on expected behavior
        if expected_behavior == "uses_both_existing" and thread_id and run_id:
            assert context.thread_id == thread_id
            assert context.run_id == run_id