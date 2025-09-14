"""
SSOT User Context Test Helpers - Simplified Testing Utilities

This module provides simplified utilities for creating valid UserExecutionContext
instances in tests, preventing duplication and ensuring SSOT compliance.

BUSINESS VALUE:
- Platform/Internal - Development Velocity & Test Reliability
- Eliminates user context creation duplication across test files
- Ensures consistent security isolation patterns in testing

SSOT COMPLIANCE:
- Single source of truth for user context creation in tests
- Integrates with unified test framework patterns
- Prevents user context setup code duplication

SECURITY FOCUS:
- All contexts are isolated by default
- No shared state between test contexts
- Validates proper user isolation patterns

Created for Issue #1066 - SSOT-regression-deprecated-websocket-factory-imports
Priority: P0 - Mission Critical
"""

import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio
from contextlib import contextmanager

# SSOT Import Registry - Verified canonical imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    UserContextManager,
    InvalidContextError,
    ContextIsolationError
)
from shared.types.core_types import UserID, ThreadID, RunID

# SSOT Mock Factory for creating test contexts
from test_framework.ssot.mock_factory import SSotMockFactory


@dataclass
class TestUserProfile:
    """Standard test user profile for consistent testing."""
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    description: str = ""


class UserContextTestHelper:
    """
    SSOT helper for creating and managing user contexts in tests.

    This class provides simplified, standardized methods for creating
    user contexts with proper isolation guarantees.
    """

    def __init__(self):
        """Initialize the test helper."""
        self._created_contexts: List[UserExecutionContext] = []
        self._context_counter = 0

    def create_test_user_context(
        self,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        description: str = "Test User Context"
    ) -> UserExecutionContext:
        """
        Create an isolated test user context with automatic ID generation.

        Args:
            user_id: Optional user ID (auto-generated if None)
            thread_id: Optional thread ID (auto-generated if None)
            run_id: Optional run ID (auto-generated if None)
            description: Description for debugging purposes

        Returns:
            UserExecutionContext: Isolated context for testing

        Example:
            ```python
            helper = UserContextTestHelper()
            context = helper.create_test_user_context(description="WebSocket test user")
            ```
        """
        self._context_counter += 1

        # Auto-generate IDs if not provided
        if user_id is None:
            user_id = f"test_user_{self._context_counter}_{uuid.uuid4().hex[:8]}"
        if thread_id is None:
            thread_id = f"test_thread_{self._context_counter}_{uuid.uuid4().hex[:8]}"
        if run_id is None:
            run_id = f"test_run_{self._context_counter}_{uuid.uuid4().hex[:8]}"

        # Create isolated context using SSOT mock factory (for testing)
        context = SSotMockFactory.create_isolated_execution_context(
            user_id=user_id,
            thread_id=thread_id
        )

        # Track for cleanup and validation
        self._created_contexts.append(context)

        return context

    def create_multiple_test_contexts(self, count: int) -> List[UserExecutionContext]:
        """
        Create multiple isolated test contexts for concurrent testing.

        Args:
            count: Number of contexts to create

        Returns:
            List[UserExecutionContext]: List of isolated contexts

        Example:
            ```python
            helper = UserContextTestHelper()
            contexts = helper.create_multiple_test_contexts(3)
            ```
        """
        return [
            self.create_test_user_context(description=f"Multi-user test context {i+1}")
            for i in range(count)
        ]

    def create_websocket_test_context(
        self,
        user_prefix: str = "websocket_user"
    ) -> UserExecutionContext:
        """
        Create a context specifically designed for WebSocket testing.

        Args:
            user_prefix: Prefix for generated user ID

        Returns:
            UserExecutionContext: Context optimized for WebSocket tests
        """
        return self.create_test_user_context(
            user_id=f"{user_prefix}_{uuid.uuid4().hex[:8]}",
            description="WebSocket-specific test context"
        )

    def create_agent_test_context(
        self,
        agent_type: str = "test_agent"
    ) -> UserExecutionContext:
        """
        Create a context specifically designed for agent testing.

        Args:
            agent_type: Type of agent being tested

        Returns:
            UserExecutionContext: Context optimized for agent tests
        """
        return self.create_test_user_context(
            user_id=f"agent_test_{agent_type}_{uuid.uuid4().hex[:8]}",
            description=f"Agent test context for {agent_type}"
        )

    @contextmanager
    def managed_test_context(self, **kwargs):
        """
        Context manager for automatic cleanup of test contexts.

        Args:
            **kwargs: Arguments passed to create_test_user_context

        Yields:
            UserExecutionContext: Managed context that will be cleaned up

        Example:
            ```python
            helper = UserContextTestHelper()
            with helper.managed_test_context() as context:
                # Use context in test
                pass
            # Context automatically cleaned up
            ```
        """
        context = self.create_test_user_context(**kwargs)
        try:
            yield context
        finally:
            # Perform any cleanup if needed
            pass

    def validate_context_isolation(self, contexts: List[UserExecutionContext]) -> bool:
        """
        Validate that multiple contexts are properly isolated.

        Args:
            contexts: List of contexts to validate

        Returns:
            bool: True if all contexts are properly isolated

        Raises:
            ContextIsolationError: If isolation validation fails
        """
        if len(contexts) < 2:
            return True  # Single context is always isolated

        # Check that all contexts have unique IDs
        user_ids = [ctx.user_id for ctx in contexts]
        thread_ids = [ctx.thread_id for ctx in contexts]
        run_ids = [ctx.run_id for ctx in contexts]

        if len(set(user_ids)) != len(user_ids):
            raise ContextIsolationError("User IDs are not unique across contexts")

        if len(set(thread_ids)) != len(thread_ids):
            raise ContextIsolationError("Thread IDs are not unique across contexts")

        if len(set(run_ids)) != len(run_ids):
            raise ContextIsolationError("Run IDs are not unique across contexts")

        return True

    def get_created_contexts(self) -> List[UserExecutionContext]:
        """
        Get all contexts created by this helper.

        Returns:
            List[UserExecutionContext]: All created contexts
        """
        return self._created_contexts.copy()

    def cleanup(self):
        """Clean up all created contexts."""
        self._created_contexts.clear()
        self._context_counter = 0


# Singleton instance for convenience (SSOT pattern)
_global_helper: Optional[UserContextTestHelper] = None


def get_user_context_test_helper() -> UserContextTestHelper:
    """
    Get the global SSOT user context test helper instance.

    Returns:
        UserContextTestHelper: Singleton test helper instance
    """
    global _global_helper
    if _global_helper is None:
        _global_helper = UserContextTestHelper()
    return _global_helper


# Convenience functions for common patterns
def create_test_user_context(
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    description: str = "Test User Context"
) -> UserExecutionContext:
    """
    Convenience function to create a test user context.

    This is a shorthand for getting the helper and creating a context.
    """
    return get_user_context_test_helper().create_test_user_context(
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        description=description
    )


def create_websocket_test_context(user_prefix: str = "websocket_user") -> UserExecutionContext:
    """
    Convenience function to create a WebSocket-specific test context.
    """
    return get_user_context_test_helper().create_websocket_test_context(user_prefix)


def create_agent_test_context(agent_type: str = "test_agent") -> UserExecutionContext:
    """
    Convenience function to create an agent-specific test context.
    """
    return get_user_context_test_helper().create_agent_test_context(agent_type)


def create_multiple_test_contexts(count: int) -> List[UserExecutionContext]:
    """
    Convenience function to create multiple isolated test contexts.
    """
    return get_user_context_test_helper().create_multiple_test_contexts(count)


def validate_context_isolation(contexts: List[UserExecutionContext]) -> bool:
    """
    Convenience function to validate context isolation.
    """
    return get_user_context_test_helper().validate_context_isolation(contexts)


# Test utility class for SSOT integration
class SSotUserContextTestMixin:
    """
    Mixin class that can be added to test cases for user context utilities.

    This provides consistent user context creation methods that integrate
    with the SSOT test framework.
    """

    def setUp(self):
        """Initialize user context test utilities."""
        super().setUp() if hasattr(super(), 'setUp') else None
        self.user_context_helper = UserContextTestHelper()

    def setup_method(self, method):
        """Initialize user context test utilities (pytest style)."""
        super().setup_method(method) if hasattr(super(), 'setup_method') else None
        self.user_context_helper = UserContextTestHelper()

    def create_test_user(self, **kwargs) -> UserExecutionContext:
        """Create a test user context with automatic cleanup tracking."""
        return self.user_context_helper.create_test_user_context(**kwargs)

    def create_websocket_test_user(self, user_prefix: str = "test_ws_user") -> UserExecutionContext:
        """Create a WebSocket-specific test user context."""
        return self.user_context_helper.create_websocket_test_context(user_prefix)

    def create_multiple_test_users(self, count: int) -> List[UserExecutionContext]:
        """Create multiple isolated test user contexts."""
        return self.user_context_helper.create_multiple_test_contexts(count)

    def tearDown(self):
        """Clean up user context test utilities."""
        if hasattr(self, 'user_context_helper'):
            self.user_context_helper.cleanup()
        super().tearDown() if hasattr(super(), 'tearDown') else None

    def teardown_method(self, method):
        """Clean up user context test utilities (pytest style)."""
        if hasattr(self, 'user_context_helper'):
            self.user_context_helper.cleanup()
        super().teardown_method(method) if hasattr(super(), 'teardown_method') else None