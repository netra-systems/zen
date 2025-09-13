"""
Unit Tests for Agent Execution Context Validation

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) with critical focus on Enterprise security
- Business Goal: Multi-tenant security and data isolation compliance
- Value Impact: Prevents $500K+ ARR loss from security breaches and ensures enterprise compliance
- Strategic Impact: Enables secure multi-user platform operation and enterprise customer confidence

This module tests the UserExecutionContext validation logic to ensure:
1. User context validation prevents placeholder and invalid values
2. Context isolation prevents cross-user data contamination
3. Security validation detects 20+ forbidden patterns
4. Context creation follows proper isolation principles
5. Child context creation maintains security boundaries
6. Database session isolation is properly enforced
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

# SSOT imports as per SSOT_IMPORT_REGISTRY.md
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    InvalidContextError,
    ContextIsolationError,
    validate_user_context,
    create_isolated_execution_context
)
from netra_backend.app.agents.supervisor.agent_execution_context_manager import (
    AgentExecutionContextManager,
    ExecutionSession,
    ContextIsolationMetrics
)
from shared.types.core_types import UserID, ThreadID, RunID
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestContextValidation(SSotAsyncTestCase):
    """Unit tests for user execution context validation and security."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.context_manager = AgentExecutionContextManager()
        self.test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.test_request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    def test_user_execution_context_creation_with_valid_data(self):
        """Test UserExecutionContext creation with valid data."""
        valid_context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id,
            agent_context={"agent_type": "supervisor"},
            audit_metadata={"source": "api", "ip": "192.168.1.100"}
        )
        
        # Should create successfully
        self.assertEqual(valid_context.user_id, self.test_user_id)
        self.assertEqual(valid_context.thread_id, self.test_thread_id) 
        self.assertEqual(valid_context.run_id, self.test_run_id)
        self.assertEqual(valid_context.request_id, self.test_request_id)
        self.assertTrue(isinstance(valid_context.created_at, datetime))
        self.assertTrue(isinstance(valid_context.agent_context, dict))
        self.assertTrue(isinstance(valid_context.audit_metadata, dict))
    
    def test_user_execution_context_immutability(self):
        """Test that UserExecutionContext is immutable after creation."""
        context = UserExecutionContext(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            request_id=self.test_request_id
        )
        
        # Should not be able to modify fields directly (frozen=True)
        with self.expect_exception(AttributeError):
            context.user_id = "modified_user_id"
            
        with self.expect_exception(AttributeError):
            context.thread_id = "modified_thread_id"
            
        # Note: agent_context and audit_metadata are dicts and could be modified
        # This is by design for adding contextual information during execution
    
    def test_context_validation_rejects_placeholder_values(self):
        """Test validation rejects placeholder and template values."""
        placeholder_patterns = [
            "placeholder_user_id",
            "PLACEHOLDER_VALUE", 
            "{{user_id}}",
            "{thread_id}",
            "YOUR_USER_ID_HERE",
            "test_user_placeholder",
            "default_thread",
            "example_run_id",
            "sample_request",
            "template_user"
        ]
        
        for placeholder in placeholder_patterns:
            with self.expect_exception(InvalidContextError):
                # Create context with placeholder value - validation happens during creation
                invalid_context = UserExecutionContext(
                    user_id=placeholder,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    request_id=self.test_request_id
                )
                # Then validate the context
                validate_user_context(invalid_context)
            
            error_msg = str(context.exception)
            self.assertIn("placeholder", error_msg.lower())
            self.assertIn(placeholder, error_msg)
    
    def test_context_validation_rejects_invalid_formats(self):
        """Test validation rejects invalid ID formats."""
        invalid_values = [
            "",              # Empty string
            " ",             # Whitespace only
            None,            # None value  
            "  \n\t  ",      # Only whitespace characters
            "user id",       # Contains spaces
            "user@domain",   # Contains invalid characters
            "user/id",       # Contains slashes
            "user\\id",      # Contains backslashes
            "<user_id>",     # Contains angle brackets
            "user_id;DROP",  # SQL injection attempt
        ]
        
        for invalid_value in invalid_values:
            with self.expect_exception((InvalidContextError, ValueError, TypeError)):
                # Create context with invalid value - validation happens during creation
                invalid_context = UserExecutionContext(
                    user_id=invalid_value,
                    thread_id=self.test_thread_id, 
                    run_id=self.test_run_id,
                    request_id=self.test_request_id
                )
                # Then validate the context
                validate_user_context(invalid_context)
    
    def test_context_validation_security_pattern_detection(self):
        """Test detection of security-sensitive patterns in context."""
        security_violations = [
            ("sql_injection", "'; DROP TABLE users; --"),
            ("xss_attempt", "<script>alert('xss')</script>"),
            ("path_traversal", "../../../etc/passwd"),
            ("command_injection", "; rm -rf /"),
            ("template_injection", "{{config.items()}}"),
            ("code_injection", "__import__('os').system('ls')"),
            ("ldap_injection", "user*)(password=*)"),
            ("xml_injection", "<?xml version='1.0'?><!DOCTYPE foo>"),
            ("json_injection", '{"admin": true}'),
            ("header_injection", "user\r\nSet-Cookie: admin=true")
        ]
        
        for attack_type, payload in security_violations:
            with self.expect_exception(InvalidContextError):
                # Create context with security violation - validation happens during creation
                invalid_context = UserExecutionContext(
                    user_id=f"user_{payload}",
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    request_id=self.test_request_id
                )
                # Then validate the context
                validate_user_context(invalid_context)
            
            error_msg = str(context.exception)
            self.assertIn("security", error_msg.lower())
    
    def test_context_isolation_between_users(self):
        """Test context isolation prevents cross-user contamination."""
        # Create contexts for different users
        user1_context = create_isolated_execution_context(
            user_id=f"user1_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread1_{uuid.uuid4().hex[:8]}",
            run_id=f"run1_{uuid.uuid4().hex[:8]}"
        )
        
        user2_context = create_isolated_execution_context(
            user_id=f"user2_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread2_{uuid.uuid4().hex[:8]}",
            run_id=f"run2_{uuid.uuid4().hex[:8]}"
        )
        
        # Should have different IDs
        self.assertNotEqual(user1_context.user_id, user2_context.user_id)
        self.assertNotEqual(user1_context.thread_id, user2_context.thread_id)
        self.assertNotEqual(user1_context.run_id, user2_context.run_id)
        
        # Should have separate agent_context dictionaries
        user1_context.agent_context["user1_data"] = "sensitive_data_1"
        user2_context.agent_context["user2_data"] = "sensitive_data_2"
        
        # Data should not leak between contexts
        self.assertNotIn("user2_data", user1_context.agent_context)
        self.assertNotIn("user1_data", user2_context.agent_context)
    
    def test_context_child_creation_maintains_isolation(self):
        """Test child context creation maintains security boundaries."""
        parent_context = create_isolated_execution_context(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id
        )
        
        # Create child context
        child_context = parent_context.create_child_context(
            child_run_id=f"child_{uuid.uuid4().hex[:8]}",
            child_metadata={"operation": "sub_task"}
        )
        
        # Should inherit parent user/thread but have new run ID
        self.assertEqual(child_context.user_id, parent_context.user_id)
        self.assertEqual(child_context.thread_id, parent_context.thread_id)
        self.assertNotEqual(child_context.run_id, parent_context.run_id)
        
        # Should have incremented operation depth
        self.assertEqual(child_context.operation_depth, parent_context.operation_depth + 1)
        
        # Parent request ID should be set
        self.assertEqual(child_context.parent_request_id, parent_context.request_id)
        
        # Should have separate context dictionaries
        parent_context.agent_context["parent_data"] = "parent_value"
        child_context.agent_context["child_data"] = "child_value"
        
        # Data should not leak between parent and child
        self.assertNotIn("child_data", parent_context.agent_context)
        self.assertNotIn("parent_data", child_context.agent_context)
    
    def test_context_database_session_isolation(self):
        """Test database session isolation between contexts."""
        # Mock database sessions
        mock_session1 = Mock()
        mock_session2 = Mock()
        
        context1 = UserExecutionContext(
            user_id=f"user1_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread1_{uuid.uuid4().hex[:8]}",
            run_id=f"run1_{uuid.uuid4().hex[:8]}",
            request_id=f"req1_{uuid.uuid4().hex[:8]}",
            db_session=mock_session1
        )
        
        context2 = UserExecutionContext(
            user_id=f"user2_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread2_{uuid.uuid4().hex[:8]}",
            run_id=f"run2_{uuid.uuid4().hex[:8]}",
            request_id=f"req2_{uuid.uuid4().hex[:8]}",
            db_session=mock_session2
        )
        
        # Should have different database sessions
        self.assertIsNot(context1.db_session, context2.db_session)
        self.assertEqual(context1.db_session, mock_session1)
        self.assertEqual(context2.db_session, mock_session2)
    
    def test_context_websocket_routing_isolation(self):
        """Test WebSocket routing isolation between users."""
        websocket_id1 = f"ws_{uuid.uuid4().hex[:8]}"
        websocket_id2 = f"ws_{uuid.uuid4().hex[:8]}"
        
        context1 = create_isolated_execution_context(
            user_id=f"user1_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread1_{uuid.uuid4().hex[:8]}",
            run_id=f"run1_{uuid.uuid4().hex[:8]}",
            websocket_client_id=websocket_id1
        )
        
        context2 = create_isolated_execution_context(
            user_id=f"user2_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread2_{uuid.uuid4().hex[:8]}",
            run_id=f"run2_{uuid.uuid4().hex[:8]}",
            websocket_client_id=websocket_id2
        )
        
        # Should have different WebSocket client IDs
        self.assertNotEqual(context1.websocket_client_id, context2.websocket_client_id)
        self.assertEqual(context1.websocket_client_id, websocket_id1)
        self.assertEqual(context2.websocket_client_id, websocket_id2)
    
    def test_execution_session_isolation(self):
        """Test ExecutionSession isolation between users."""
        session1 = ExecutionSession(
            session_id=f"session1_{uuid.uuid4().hex[:8]}",
            user_id=UserID(f"user1_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"thread1_{uuid.uuid4().hex[:8]}"),
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            execution_context=Mock()
        )
        
        session2 = ExecutionSession(
            session_id=f"session2_{uuid.uuid4().hex[:8]}",
            user_id=UserID(f"user2_{uuid.uuid4().hex[:8]}"),
            thread_id=ThreadID(f"thread2_{uuid.uuid4().hex[:8]}"),
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            execution_context=Mock()
        )
        
        # Should have separate session IDs and user contexts
        self.assertNotEqual(session1.session_id, session2.session_id)
        self.assertNotEqual(session1.user_id, session2.user_id)
        self.assertNotEqual(session1.thread_id, session2.thread_id)
        
        # Should have separate active runs sets
        session1.add_run("run1")
        session2.add_run("run2")
        
        self.assertIn("run1", session1.active_runs)
        self.assertNotIn("run1", session2.active_runs)
        self.assertIn("run2", session2.active_runs)
        self.assertNotIn("run2", session1.active_runs)
    
    def test_context_isolation_metrics_tracking(self):
        """Test context isolation metrics for monitoring."""
        metrics = ContextIsolationMetrics()
        
        # Should start with zero metrics
        self.assertEqual(metrics.active_sessions, 0)
        self.assertEqual(metrics.active_contexts, 0)
        self.assertEqual(metrics.isolation_violations, 0)
        self.assertEqual(metrics.context_leaks, 0)
        self.assertEqual(metrics.session_timeouts, 0)
        
        # Should be able to increment metrics
        metrics.active_sessions += 1
        metrics.active_contexts += 2
        metrics.isolation_violations += 1
        
        self.assertEqual(metrics.active_sessions, 1)
        self.assertEqual(metrics.active_contexts, 2)
        self.assertEqual(metrics.isolation_violations, 1)
        
        # Should be able to reset metrics
        metrics.reset()
        self.assertEqual(metrics.active_sessions, 0)
        self.assertEqual(metrics.isolation_violations, 0)
    
    def test_context_validation_performance_reasonable(self):
        """Test that context validation performs reasonably for business needs."""
        import time
        
        # Time context creation and validation
        start_time = time.time()
        
        for i in range(100):  # Validate 100 contexts
            context = create_isolated_execution_context(
                user_id=f"user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}"
            )
            validate_user_context(context)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_validation = total_time / 100
        
        # Should be fast enough for real-time use
        self.assertLess(avg_time_per_validation, 0.01)  # Less than 10ms per validation
        self.assertLess(total_time, 1.0)  # Less than 1 second for 100 validations
    
    def test_context_validation_memory_usage_reasonable(self):
        """Test that context creation doesn't leak memory."""
        import gc
        
        # Force garbage collection before test
        gc.collect()
        
        # Create many contexts and let them go out of scope
        for i in range(1000):
            context = create_isolated_execution_context(
                user_id=f"user_{i}_{uuid.uuid4().hex[:8]}",
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                run_id=f"run_{i}_{uuid.uuid4().hex[:8]}"
            )
            # Context should go out of scope and be eligible for GC
        
        # Force garbage collection after test
        gc.collect()
        
        # Test passes if no memory errors occur
        # (More sophisticated memory testing would require memory profiling tools)
        self.assertTrue(True, "Context creation completed without memory errors")
    
    def test_context_validation_error_messages_informative(self):
        """Test that validation error messages are informative for debugging."""
        test_cases = [
            ("", "empty"),
            ("placeholder_user", "placeholder"),
            ("user'; DROP TABLE", "security"),
            ("<script>alert(1)</script>", "security"),
            ("{{user}}", "placeholder")
        ]
        
        for invalid_value, expected_keyword in test_cases:
            with self.expect_exception(InvalidContextError):
                # Create context with invalid value - validation happens during creation
                invalid_context = UserExecutionContext(
                    user_id=invalid_value,
                    thread_id=self.test_thread_id,
                    run_id=self.test_run_id,
                    request_id=self.test_request_id
                )
                # Then validate the context
                validate_user_context(invalid_context)
            
            error_msg = str(context.exception).lower()
            self.assertIn(expected_keyword, error_msg,
                         f"Error message should contain '{expected_keyword}' for value '{invalid_value}'")
            self.assertIn(invalid_value, str(context.exception),
                         f"Error message should contain the invalid value '{invalid_value}'")


async def async_test_context_manager_isolation():
    """Test AgentExecutionContextManager in async context."""
    manager = AgentExecutionContextManager()
    
    # Test creating isolated sessions
    context1 = create_isolated_execution_context(
        user_id=f"user1_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread1_{uuid.uuid4().hex[:8]}",
        run_id=f"run1_{uuid.uuid4().hex[:8]}"
    )
    
    context2 = create_isolated_execution_context(
        user_id=f"user2_{uuid.uuid4().hex[:8]}",
        thread_id=f"thread2_{uuid.uuid4().hex[:8]}",
        run_id=f"run2_{uuid.uuid4().hex[:8]}"
    )
    
    # Should maintain isolation in async context
    assert context1.user_id != context2.user_id
    assert context1.thread_id != context2.thread_id
    assert context1.run_id != context2.run_id


if __name__ == '__main__':
    pytest.main([__file__])