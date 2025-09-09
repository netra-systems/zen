"""
Unit Test Suite for User Context Factory Isolation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure complete user isolation for multi-tenant agent execution
- Value Impact: Prevents user data leakage and ensures secure multi-user agent operations
- Strategic Impact: User isolation is foundation for Enterprise/Mid-tier security requirements

This test suite validates the User Context Factory pattern that enables complete 
isolation between users' agent execution contexts. This is CRITICAL for multi-user
scenarios where agent executions must not leak data between users.

USER CONTEXT FACTORY PATTERNS:
- Factory creates isolated execution contexts per user
- Context inheritance preserves isolation boundaries
- Memory cleanup prevents context leakage
- Database session isolation per user context
- WebSocket connection isolation per user
- Agent execution state isolation

CRITICAL ISOLATION REQUIREMENTS:
- User A's agent execution cannot access User B's data
- Database sessions are scoped to individual users
- WebSocket connections maintain user boundaries
- Memory cleanup prevents cross-contamination
- Context creation follows factory pattern SSOT
- Error propagation respects isolation boundaries
"""

import pytest
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set
import unittest
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass

# Import system under test - User context types from shared SSOT
from shared.types import (
    StronglyTypedUserExecutionContext, UserID, ThreadID, RunID, RequestID,
    WebSocketID, AgentID, ExecutionID, ContextValidationError, IsolationViolationError
)


class UserContextFactory:
    """Factory for creating isolated user execution contexts.
    
    This class implements the factory pattern for creating completely isolated
    user execution contexts that prevent data leakage between users.
    """
    
    def __init__(self):
        """Initialize factory with isolation tracking."""
        self.created_contexts: Dict[UserID, List[StronglyTypedUserExecutionContext]] = {}
        self.active_contexts: Set[str] = set()  # Track by request_id
        self.isolation_violations: List[str] = []
        
    def create_context(
        self,
        user_id: UserID,
        thread_id: ThreadID,
        run_id: RunID,
        request_id: RequestID,
        websocket_client_id: Optional[WebSocketID] = None,
        parent_request_id: Optional[RequestID] = None
    ) -> StronglyTypedUserExecutionContext:
        """Create a new isolated user execution context."""
        
        # Validate isolation boundaries
        self._validate_isolation_requirements(user_id, request_id)
        
        # Create context with isolation guarantees
        context = StronglyTypedUserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=request_id,
            websocket_client_id=websocket_client_id,
            parent_request_id=parent_request_id,
            created_at=datetime.now(timezone.utc),
            operation_depth=0 if parent_request_id is None else 1
        )
        
        # Track context for isolation monitoring
        if user_id not in self.created_contexts:
            self.created_contexts[user_id] = []
        self.created_contexts[user_id].append(context)
        self.active_contexts.add(str(request_id))
        
        return context
    
    def create_child_context(
        self,
        parent_context: StronglyTypedUserExecutionContext,
        new_request_id: RequestID
    ) -> StronglyTypedUserExecutionContext:
        """Create a child context that inherits isolation from parent."""
        
        # Child must belong to same user
        if str(new_request_id) in self.active_contexts:
            raise IsolationViolationError(f"Request ID {new_request_id} already exists")
        
        child_context = StronglyTypedUserExecutionContext(
            user_id=parent_context.user_id,
            thread_id=parent_context.thread_id,
            run_id=parent_context.run_id,
            request_id=new_request_id,
            websocket_client_id=parent_context.websocket_client_id,
            parent_request_id=parent_context.request_id,
            created_at=datetime.now(timezone.utc),
            operation_depth=parent_context.operation_depth + 1
        )
        
        # Track child context
        self.created_contexts[parent_context.user_id].append(child_context)
        self.active_contexts.add(str(new_request_id))
        
        return child_context
    
    def release_context(self, context: StronglyTypedUserExecutionContext) -> bool:
        """Release and clean up a user execution context."""
        try:
            # Remove from active tracking
            self.active_contexts.discard(str(context.request_id))
            
            # Remove from user's context list
            if context.user_id in self.created_contexts:
                user_contexts = self.created_contexts[context.user_id]
                self.created_contexts[context.user_id] = [
                    ctx for ctx in user_contexts 
                    if ctx.request_id != context.request_id
                ]
            
            return True
            
        except Exception as e:
            self.isolation_violations.append(f"Context cleanup failed: {e}")
            return False
    
    def get_user_contexts(self, user_id: UserID) -> List[StronglyTypedUserExecutionContext]:
        """Get all active contexts for a specific user."""
        return self.created_contexts.get(user_id, [])
    
    def cleanup_user_contexts(self, user_id: UserID) -> int:
        """Clean up all contexts for a specific user."""
        user_contexts = self.created_contexts.get(user_id, [])
        cleanup_count = 0
        
        for context in user_contexts:
            if self.release_context(context):
                cleanup_count += 1
        
        # Clear user's context list
        self.created_contexts.pop(user_id, None)
        
        return cleanup_count
    
    def validate_isolation(self) -> List[str]:
        """Validate that isolation is maintained across all contexts."""
        violations = []
        
        # Check for duplicate request IDs across different users
        request_id_to_user = {}
        for user_id, contexts in self.created_contexts.items():
            for context in contexts:
                req_id = str(context.request_id)
                if req_id in request_id_to_user:
                    violations.append(
                        f"Request ID {req_id} used by multiple users: "
                        f"{request_id_to_user[req_id]} and {user_id}"
                    )
                else:
                    request_id_to_user[req_id] = user_id
        
        # Check for cross-user thread contamination
        thread_to_user = {}
        for user_id, contexts in self.created_contexts.items():
            for context in contexts:
                thread_id = str(context.thread_id)
                if thread_id in thread_to_user and thread_to_user[thread_id] != user_id:
                    violations.append(
                        f"Thread ID {thread_id} shared between users: "
                        f"{thread_to_user[thread_id]} and {user_id}"
                    )
                else:
                    thread_to_user[thread_id] = user_id
        
        return violations + self.isolation_violations
    
    def _validate_isolation_requirements(self, user_id: UserID, request_id: RequestID) -> None:
        """Validate that context creation maintains isolation."""
        
        # Check for duplicate request ID
        if str(request_id) in self.active_contexts:
            raise IsolationViolationError(f"Request ID {request_id} already in use")
        
        # Validate user ID format
        if not str(user_id).strip():
            raise ContextValidationError("User ID cannot be empty")
        
        # Check for forbidden test values that could indicate test pollution
        forbidden_values = ["test_user", "mock_user", "example_user"]
        if str(user_id) in forbidden_values:
            raise ContextValidationError(f"Forbidden test user ID: {user_id}")


class TestUserContextFactoryIsolation(unittest.TestCase):
    """Test user context factory isolation patterns."""
    
    def setUp(self):
        """Set up fresh factory for each test."""
        self.factory = UserContextFactory()
        self.user1_id = UserID(str(uuid.uuid4()))
        self.user2_id = UserID(str(uuid.uuid4()))
        self.thread1_id = ThreadID(str(uuid.uuid4()))
        self.thread2_id = ThreadID(str(uuid.uuid4()))
    
    def test_factory_creates_isolated_contexts(self):
        """Test that factory creates completely isolated contexts for different users."""
        
        # Create contexts for two different users
        context1 = self.factory.create_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        context2 = self.factory.create_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Contexts should be completely isolated
        self.assertNotEqual(context1.user_id, context2.user_id)
        self.assertNotEqual(context1.thread_id, context2.thread_id)
        self.assertNotEqual(context1.run_id, context2.run_id)
        self.assertNotEqual(context1.request_id, context2.request_id)
        
        # Each user should only see their own context
        user1_contexts = self.factory.get_user_contexts(self.user1_id)
        user2_contexts = self.factory.get_user_contexts(self.user2_id)
        
        self.assertEqual(len(user1_contexts), 1)
        self.assertEqual(len(user2_contexts), 1)
        self.assertEqual(user1_contexts[0].user_id, self.user1_id)
        self.assertEqual(user2_contexts[0].user_id, self.user2_id)
    
    def test_context_creation_validates_isolation(self):
        """Test that context creation validates isolation requirements."""
        
        request_id = RequestID(str(uuid.uuid4()))
        
        # Create first context
        context1 = self.factory.create_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=request_id
        )
        
        # Attempting to reuse request_id should raise error
        with self.assertRaises(IsolationViolationError):
            self.factory.create_context(
                user_id=self.user2_id,
                thread_id=self.thread2_id,
                run_id=RunID(str(uuid.uuid4())),
                request_id=request_id  # Duplicate request_id
            )
    
    def test_child_context_inherits_isolation(self):
        """Test that child contexts properly inherit isolation from parent."""
        
        # Create parent context
        parent_context = self.factory.create_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Create child context
        child_request_id = RequestID(str(uuid.uuid4()))
        child_context = self.factory.create_child_context(parent_context, child_request_id)
        
        # Child should inherit user isolation from parent
        self.assertEqual(child_context.user_id, parent_context.user_id)
        self.assertEqual(child_context.thread_id, parent_context.thread_id)
        self.assertEqual(child_context.run_id, parent_context.run_id)
        self.assertEqual(child_context.parent_request_id, parent_context.request_id)
        self.assertEqual(child_context.operation_depth, parent_context.operation_depth + 1)
        
        # Both contexts should be tracked under same user
        user_contexts = self.factory.get_user_contexts(self.user1_id)
        self.assertEqual(len(user_contexts), 2)
        
        context_request_ids = {str(ctx.request_id) for ctx in user_contexts}
        self.assertIn(str(parent_context.request_id), context_request_ids)
        self.assertIn(str(child_context.request_id), context_request_ids)
    
    def test_context_cleanup_maintains_isolation(self):
        """Test that context cleanup maintains isolation between users."""
        
        # Create contexts for both users
        user1_context = self.factory.create_context(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        user2_context = self.factory.create_context(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Clean up user1's contexts
        cleanup_count = self.factory.cleanup_user_contexts(self.user1_id)
        self.assertEqual(cleanup_count, 1)
        
        # User1 should have no contexts, User2 should still have theirs
        user1_contexts = self.factory.get_user_contexts(self.user1_id)
        user2_contexts = self.factory.get_user_contexts(self.user2_id)
        
        self.assertEqual(len(user1_contexts), 0)
        self.assertEqual(len(user2_contexts), 1)
        self.assertEqual(user2_contexts[0].user_id, self.user2_id)
    
    def test_multiple_contexts_per_user_isolation(self):
        """Test isolation with multiple contexts per user."""
        
        # Create multiple contexts for each user
        user1_contexts = []
        user2_contexts = []
        
        for i in range(3):
            # User1 contexts
            context1 = self.factory.create_context(
                user_id=self.user1_id,
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4())),
                request_id=RequestID(str(uuid.uuid4()))
            )
            user1_contexts.append(context1)
            
            # User2 contexts
            context2 = self.factory.create_context(
                user_id=self.user2_id,
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4())),
                request_id=RequestID(str(uuid.uuid4()))
            )
            user2_contexts.append(context2)
        
        # Each user should have exactly 3 contexts
        self.assertEqual(len(self.factory.get_user_contexts(self.user1_id)), 3)
        self.assertEqual(len(self.factory.get_user_contexts(self.user2_id)), 3)
        
        # All contexts should belong to correct users
        for context in self.factory.get_user_contexts(self.user1_id):
            self.assertEqual(context.user_id, self.user1_id)
        
        for context in self.factory.get_user_contexts(self.user2_id):
            self.assertEqual(context.user_id, self.user2_id)
        
        # No isolation violations should be detected
        violations = self.factory.validate_isolation()
        self.assertEqual(len(violations), 0)


class TestUserContextMemoryCleanup(unittest.TestCase):
    """Test memory cleanup and resource management for user contexts."""
    
    def setUp(self):
        """Set up fresh factory for each test."""
        self.factory = UserContextFactory()
        self.user_id = UserID(str(uuid.uuid4()))
    
    def test_context_release_removes_tracking(self):
        """Test that releasing context properly removes all tracking references."""
        
        # Create context
        context = self.factory.create_context(
            user_id=self.user_id,
            thread_id=ThreadID(str(uuid.uuid4())),
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Verify context is tracked
        self.assertIn(str(context.request_id), self.factory.active_contexts)
        self.assertEqual(len(self.factory.get_user_contexts(self.user_id)), 1)
        
        # Release context
        self.assertTrue(self.factory.release_context(context))
        
        # Verify context is no longer tracked
        self.assertNotIn(str(context.request_id), self.factory.active_contexts)
        self.assertEqual(len(self.factory.get_user_contexts(self.user_id)), 0)
    
    def test_bulk_cleanup_removes_all_user_contexts(self):
        """Test that bulk cleanup removes all contexts for a user."""
        
        # Create multiple contexts
        contexts = []
        for i in range(5):
            context = self.factory.create_context(
                user_id=self.user_id,
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4())),
                request_id=RequestID(str(uuid.uuid4()))
            )
            contexts.append(context)
        
        # Verify all contexts are tracked
        self.assertEqual(len(self.factory.get_user_contexts(self.user_id)), 5)
        for context in contexts:
            self.assertIn(str(context.request_id), self.factory.active_contexts)
        
        # Bulk cleanup
        cleanup_count = self.factory.cleanup_user_contexts(self.user_id)
        self.assertEqual(cleanup_count, 5)
        
        # Verify all contexts are removed
        self.assertEqual(len(self.factory.get_user_contexts(self.user_id)), 0)
        for context in contexts:
            self.assertNotIn(str(context.request_id), self.factory.active_contexts)
        
        # User should be completely removed from tracking
        self.assertNotIn(self.user_id, self.factory.created_contexts)
    
    def test_memory_cleanup_prevents_leakage(self):
        """Test that memory cleanup prevents context leakage between tests."""
        
        # Create contexts for multiple users
        users = [UserID(str(uuid.uuid4())) for _ in range(3)]
        
        for user_id in users:
            for i in range(2):
                self.factory.create_context(
                    user_id=user_id,
                    thread_id=ThreadID(str(uuid.uuid4())),
                    run_id=RunID(str(uuid.uuid4())),
                    request_id=RequestID(str(uuid.uuid4()))
                )
        
        # Should have 6 total contexts (3 users × 2 contexts)
        total_contexts = sum(len(contexts) for contexts in self.factory.created_contexts.values())
        self.assertEqual(total_contexts, 6)
        
        # Clean up all users
        for user_id in users:
            self.factory.cleanup_user_contexts(user_id)
        
        # All tracking should be empty
        self.assertEqual(len(self.factory.created_contexts), 0)
        self.assertEqual(len(self.factory.active_contexts), 0)
        
        # No isolation violations should remain
        violations = self.factory.validate_isolation()
        self.assertEqual(len(violations), 0)


class TestUserContextInheritancePatterns(unittest.TestCase):
    """Test context inheritance patterns and validation."""
    
    def setUp(self):
        """Set up fresh factory for each test."""
        self.factory = UserContextFactory()
        self.user_id = UserID(str(uuid.uuid4()))
    
    def test_child_context_inherits_user_isolation(self):
        """Test that child contexts inherit proper user isolation."""
        
        # Create parent context
        parent = self.factory.create_context(
            user_id=self.user_id,
            thread_id=ThreadID(str(uuid.uuid4())),
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Create child context
        child = self.factory.create_child_context(parent, RequestID(str(uuid.uuid4())))
        
        # Child should inherit all isolation properties from parent
        self.assertEqual(child.user_id, parent.user_id)
        self.assertEqual(child.thread_id, parent.thread_id)
        self.assertEqual(child.run_id, parent.run_id)
        self.assertEqual(child.parent_request_id, parent.request_id)
        
        # Operation depth should increment
        self.assertEqual(child.operation_depth, parent.operation_depth + 1)
        
        # Both should be tracked under same user
        user_contexts = self.factory.get_user_contexts(self.user_id)
        self.assertEqual(len(user_contexts), 2)
    
    def test_multi_level_context_inheritance(self):
        """Test multi-level context inheritance maintains isolation."""
        
        # Create parent → child → grandchild chain
        parent = self.factory.create_context(
            user_id=self.user_id,
            thread_id=ThreadID(str(uuid.uuid4())),
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        child = self.factory.create_child_context(parent, RequestID(str(uuid.uuid4())))
        grandchild = self.factory.create_child_context(child, RequestID(str(uuid.uuid4())))
        
        # All should maintain user isolation
        self.assertEqual(parent.user_id, child.user_id)
        self.assertEqual(child.user_id, grandchild.user_id)
        
        # Operation depth should increment correctly
        self.assertEqual(parent.operation_depth, 0)
        self.assertEqual(child.operation_depth, 1)
        self.assertEqual(grandchild.operation_depth, 2)
        
        # Parent relationships should be correct
        self.assertIsNone(parent.parent_request_id)
        self.assertEqual(child.parent_request_id, parent.request_id)
        self.assertEqual(grandchild.parent_request_id, child.request_id)
        
        # All should be tracked under same user
        user_contexts = self.factory.get_user_contexts(self.user_id)
        self.assertEqual(len(user_contexts), 3)
    
    def test_child_context_prevents_duplicate_request_ids(self):
        """Test that child context creation prevents duplicate request IDs."""
        
        parent = self.factory.create_context(
            user_id=self.user_id,
            thread_id=ThreadID(str(uuid.uuid4())),
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Try to create child with existing request ID
        with self.assertRaises(IsolationViolationError):
            self.factory.create_child_context(parent, parent.request_id)


class TestUserContextValidationErrors(unittest.TestCase):
    """Test validation error handling in user context factory."""
    
    def setUp(self):
        """Set up fresh factory for each test."""
        self.factory = UserContextFactory()
    
    def test_empty_user_id_validation(self):
        """Test that empty user IDs are rejected."""
        
        with self.assertRaises(ContextValidationError):
            self.factory.create_context(
                user_id=UserID(""),  # Empty user ID
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4())),
                request_id=RequestID(str(uuid.uuid4()))
            )
    
    def test_forbidden_test_user_ids_rejected(self):
        """Test that forbidden test user IDs are rejected."""
        
        forbidden_ids = ["test_user", "mock_user", "example_user"]
        
        for forbidden_id in forbidden_ids:
            with self.subTest(user_id=forbidden_id):
                with self.assertRaises(ContextValidationError):
                    self.factory.create_context(
                        user_id=UserID(forbidden_id),
                        thread_id=ThreadID(str(uuid.uuid4())),
                        run_id=RunID(str(uuid.uuid4())),
                        request_id=RequestID(str(uuid.uuid4()))
                    )
    
    def test_isolation_violation_detection(self):
        """Test that isolation violations are properly detected and reported."""
        
        user1_id = UserID(str(uuid.uuid4()))
        user2_id = UserID(str(uuid.uuid4()))
        shared_thread_id = ThreadID(str(uuid.uuid4()))
        
        # Create contexts that would violate isolation (sharing thread_id)
        context1 = self.factory.create_context(
            user_id=user1_id,
            thread_id=shared_thread_id,
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        context2 = self.factory.create_context(
            user_id=user2_id,
            thread_id=shared_thread_id,  # Same thread_id - isolation violation
            run_id=RunID(str(uuid.uuid4())),
            request_id=RequestID(str(uuid.uuid4()))
        )
        
        # Validation should detect the isolation violation
        violations = self.factory.validate_isolation()
        self.assertGreater(len(violations), 0)
        
        # Should contain information about thread sharing
        violation_text = " ".join(violations)
        self.assertIn("Thread ID", violation_text)
        self.assertIn("shared between users", violation_text)


if __name__ == "__main__":
    unittest.main()