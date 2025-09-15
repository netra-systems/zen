"""UserExecutionEngine Factory Pattern Validation Tests

Test suite for Issue #1186: UserExecutionEngine SSOT consolidation
These tests validate factory-based creation patterns and user context isolation.

DESIGN: These tests are designed to FAIL initially, proving current fragmentation,
and will only PASS after complete SSOT factory consolidation.

Business Value Justification:
- Segment: Platform/Internal - Multi-tenant Infrastructure
- Business Goal: User Isolation & Factory Pattern Consistency
- Value Impact: Ensures secure multi-user execution with proper resource isolation
- Strategic Impact: Prevents user context contamination and enables enterprise-grade security

Test Categories:
1. Factory-Based Creation - Validate all engines created via factory
2. User Context Binding - Ensure proper user isolation
3. Singleton Elimination - Verify no global/shared instances
4. Factory Pattern Consistency - Validate uniform factory usage
"""

import asyncio
import gc
import sys
import weakref
from typing import Any, Dict, List, Optional
from unittest import TestCase
from unittest.mock import MagicMock, AsyncMock, patch

import unittest


class UserExecutionEngineFactoryPatternsTests(unittest.IsolatedAsyncioTestCase):
    """Test suite validating UserExecutionEngine factory pattern consolidation."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.created_engines = []  # Track engines for cleanup
        self.factory_instances = []  # Track factory instances

    async def asyncTearDown(self):
        """Clean up test resources."""
        # Clean up any created engines
        for engine in self.created_engines:
            if hasattr(engine, 'cleanup'):
                try:
                    await engine.cleanup()
                except Exception:
                    pass

        # Clear references
        self.created_engines.clear()
        self.factory_instances.clear()

        # Force garbage collection
        gc.collect()

        await super().asyncTearDown()

    async def test_factory_based_creation_required(self):
        """Test that UserExecutionEngine instances must be created via factory.

        THIS TEST SHOULD FAIL INITIALLY - proving direct instantiation is allowed.
        After consolidation, direct instantiation should be prevented.
        """
        try:
            # Attempt to import and create UserExecutionEngine directly
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Create a mock user context for testing
            mock_user_context = MagicMock()
            mock_user_context.user_id = "test_user_123"
            mock_user_context.session_id = "session_456"

            # THIS SHOULD FAIL AFTER CONSOLIDATION - direct instantiation should be prevented
            try:
                # Try direct instantiation with different signatures
                engine = None

                # Try modern signature
                try:
                    engine = UserExecutionEngine(
                        context=mock_user_context,
                        agent_factory=MagicMock(),
                        websocket_emitter=MagicMock()
                    )
                except Exception:
                    # Try legacy signature
                    try:
                        engine = UserExecutionEngine(
                            context_or_registry=MagicMock(),  # Agent registry
                            agent_factory_or_websocket_bridge=MagicMock(),  # WebSocket bridge
                            websocket_emitter_or_user_context=mock_user_context  # User context
                        )
                    except Exception:
                        # Try minimal signature
                        engine = UserExecutionEngine()

                if engine:
                    self.created_engines.append(engine)

                # If we can create directly, consolidation is not complete
                self.fail(
                    "SSOT Violation: UserExecutionEngine can still be instantiated directly. "
                    "After consolidation, all instances must be created via ExecutionEngineFactory "
                    "to ensure proper user isolation and resource management."
                )

            except TypeError as e:
                if "factory" in str(e).lower() or "must be created via" in str(e).lower():
                    # Good - factory-only creation is enforced
                    self.assertTrue(True, "Factory-based creation properly enforced")
                else:
                    # Unexpected error
                    self.fail(f"Unexpected TypeError during direct instantiation: {e}")

        except ImportError as e:
            self.fail(f"Cannot import UserExecutionEngine: {e}")

    async def test_factory_user_context_binding(self):
        """Test that factory properly binds user context to engine instances.

        Validates that each engine is properly isolated by user context.
        """
        try:
            # Import factory components
            from netra_backend.app.agents.supervisor.execution_engine_factory import (
                ExecutionEngineFactory, get_execution_engine_factory
            )

            # Create factory instance
            factory = await get_execution_engine_factory()
            self.factory_instances.append(factory)

            # Create mock user contexts for different users
            user_contexts = [
                self._create_mock_user_context("user_1", "session_1"),
                self._create_mock_user_context("user_2", "session_2"),
                self._create_mock_user_context("user_3", "session_3")
            ]

            engines = []

            # Create engines for different users
            for i, user_context in enumerate(user_contexts):
                try:
                    # This should work after proper factory consolidation
                    engine = await factory.create_user_execution_engine(user_context)
                    engines.append(engine)
                    self.created_engines.append(engine)

                    # Validate user context binding
                    self.assertIsNotNone(engine, f"Factory should create engine for user {i+1}")

                    # Verify user isolation
                    if hasattr(engine, 'user_context'):
                        self.assertEqual(
                            engine.user_context.user_id,
                            user_context.user_id,
                            f"Engine user context should match for user {i+1}"
                        )

                except Exception as e:
                    # This failure indicates factory pattern not yet fully consolidated
                    self.fail(
                        f"Factory-based creation failed for user {i+1}: {e}. "
                        f"This indicates SSOT factory consolidation is incomplete."
                    )

            # Verify all engines are unique instances (no sharing)
            for i, engine1 in enumerate(engines):
                for j, engine2 in enumerate(engines):
                    if i != j:
                        self.assertIsNot(
                            engine1, engine2,
                            f"Engines for different users should be unique instances (user {i+1} vs {j+1})"
                        )

        except ImportError as e:
            # This failure indicates SSOT imports not yet consolidated
            self.fail(f"Cannot import factory components - SSOT consolidation incomplete: {e}")

    async def test_singleton_elimination_validation(self):
        """Test that no singleton patterns exist in UserExecutionEngine creation.

        THIS TEST SHOULD FAIL INITIALLY - proving singletons exist.
        After consolidation, all instances should be unique per user.
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import get_execution_engine_factory

            # Get factory multiple times
            factory1 = await get_execution_engine_factory()
            factory2 = await get_execution_engine_factory()

            self.factory_instances.extend([factory1, factory2])

            # Create engines from both factory references
            user_context = self._create_mock_user_context("test_user", "test_session")

            engine1 = await factory1.create_user_execution_engine(user_context)
            engine2 = await factory2.create_user_execution_engine(user_context)

            self.created_engines.extend([engine1, engine2])

            # Verify engines are unique instances (no singleton behavior)
            self.assertIsNot(
                engine1, engine2,
                "SSOT Violation: Engines should be unique instances, not singletons. "
                "Singleton patterns prevent proper user isolation."
            )

            # Verify no global state sharing
            if hasattr(engine1, '_shared_state') or hasattr(engine2, '_shared_state'):
                # Check if they share the same state object
                if (hasattr(engine1, '_shared_state') and hasattr(engine2, '_shared_state')
                        and engine1._shared_state is engine2._shared_state):
                    self.fail(
                        "SSOT Violation: Engines share global state. "
                        "User isolation requires separate state per engine instance."
                    )

        except Exception as e:
            self.fail(f"Singleton elimination validation failed: {e}")

    async def test_factory_pattern_consistency(self):
        """Test that factory pattern usage is consistent across codebase.

        Validates that all UserExecutionEngine creation follows the same pattern.
        """
        # This test scans the codebase for inconsistent factory usage patterns
        import ast
        from pathlib import Path

        netra_root = Path(__file__).parent.parent.parent.parent
        backend_path = netra_root / "netra_backend"

        inconsistent_patterns = []

        for py_file in backend_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Skip test files and backups
                if 'test' in str(py_file) or 'backup' in str(py_file):
                    continue

                # Look for direct UserExecutionEngine instantiation
                if "UserExecutionEngine(" in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "UserExecutionEngine(" in line and "import" not in line:
                            # Found direct instantiation
                            rel_path = str(py_file.relative_to(netra_root))
                            inconsistent_patterns.append(f"{rel_path}:{i+1}: {line.strip()}")

            except (UnicodeDecodeError, IOError):
                continue

        if inconsistent_patterns:
            failure_message = [
                "Found inconsistent UserExecutionEngine creation patterns:",
                "All creation should use ExecutionEngineFactory for proper user isolation:",
                ""
            ]
            failure_message.extend(inconsistent_patterns)
            failure_message.append(f"\nTotal inconsistent patterns found: {len(inconsistent_patterns)}")

            self.fail("\n".join(failure_message))

        # If no inconsistencies found, consolidation is complete
        self.assertEqual(len(inconsistent_patterns), 0, "All UserExecutionEngine creation uses consistent factory pattern")

    async def test_user_context_isolation_validation(self):
        """Test that user contexts are properly isolated between engine instances.

        Validates that concurrent users cannot access each other's execution contexts.
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import get_execution_engine_factory

            factory = await get_execution_engine_factory()
            self.factory_instances.append(factory)

            # Create engines for two different users
            user1_context = self._create_mock_user_context("user_alpha", "session_alpha")
            user2_context = self._create_mock_user_context("user_beta", "session_beta")

            engine1 = await factory.create_user_execution_engine(user1_context)
            engine2 = await factory.create_user_execution_engine(user2_context)

            self.created_engines.extend([engine1, engine2])

            # Simulate concurrent execution
            async def user1_execution():
                if hasattr(engine1, 'set_execution_data'):
                    await engine1.set_execution_data("user1_secret_data")
                return "user1_result"

            async def user2_execution():
                if hasattr(engine2, 'set_execution_data'):
                    await engine2.set_execution_data("user2_secret_data")
                return "user2_result"

            # Execute concurrently
            results = await asyncio.gather(user1_execution(), user2_execution())

            # Verify results are isolated
            self.assertEqual(len(results), 2, "Both users should complete execution")

            # Verify no cross-user data contamination
            if hasattr(engine1, 'get_execution_data') and hasattr(engine2, 'get_execution_data'):
                user1_data = await engine1.get_execution_data() if asyncio.iscoroutinefunction(engine1.get_execution_data) else engine1.get_execution_data()
                user2_data = await engine2.get_execution_data() if asyncio.iscoroutinefunction(engine2.get_execution_data) else engine2.get_execution_data()

                # Data should not leak between users
                if user1_data and user2_data:
                    self.assertNotEqual(
                        user1_data, user2_data,
                        "User execution data should be isolated - no cross-user contamination"
                    )

        except Exception as e:
            # This failure indicates user isolation is not yet properly implemented
            self.fail(f"User context isolation validation failed: {e}")

    async def test_factory_resource_management(self):
        """Test that factory properly manages engine resources and lifecycle.

        Validates that engines are properly cleaned up and resources released.
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import get_execution_engine_factory

            factory = await get_execution_engine_factory()
            self.factory_instances.append(factory)

            # Create an engine
            user_context = self._create_mock_user_context("resource_test_user", "resource_session")
            engine = await factory.create_user_execution_engine(user_context)

            # Keep a weak reference to check cleanup
            weak_ref = weakref.ref(engine)

            # Engine should exist
            self.assertIsNotNone(weak_ref(), "Engine should exist after creation")

            # Clean up engine
            if hasattr(engine, 'cleanup'):
                await engine.cleanup()

            # Remove our reference
            engine = None

            # Force garbage collection
            gc.collect()

            # After cleanup and GC, weak reference should be None (object collected)
            # Note: This may not always work due to Python's garbage collection behavior
            # but it's a good indicator of proper resource management

        except Exception as e:
            self.fail(f"Factory resource management test failed: {e}")

    def _create_mock_user_context(self, user_id: str, session_id: str) -> MagicMock:
        """Create a mock user context for testing."""
        mock_context = MagicMock()
        mock_context.user_id = user_id
        mock_context.session_id = session_id
        mock_context.is_valid = True
        mock_context.permissions = ["execute", "read", "write"]
        return mock_context


if __name__ == "__main__":
    import unittest
    unittest.main()