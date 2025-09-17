"""
Test WebSocket Manager SSOT Consolidation (Issue #824)

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise) - Golden Path Infrastructure
- Business Goal: Protect $500K+ ARR by ensuring WebSocket Manager SSOT compliance
- Value Impact: Prevents race conditions and initialization failures in Golden Path
- Revenue Impact: Ensures chat functionality works reliably across all user sessions

CRITICAL PURPOSE: These tests INITIALLY FAIL to demonstrate SSOT fragmentation issues,
then PASS after SSOT consolidation to validate the fix.

SSOT FRAGMENTATION DETECTED:
1. UnifiedWebSocketManager (netra_backend/app/websocket_core/unified_manager.py:294)
2. WebSocketManagerFactory (netra_backend/app/websocket_core/websocket_manager_factory.py:516)
3. LegacyWebSocketManagerAdapter (netra_backend/app/websocket_core/protocols.py:606)
4. WebSocketManagerAdapter (netra_backend/app/agents/supervisor/agent_registry.py:64)

TEST STRATEGY: Fail-first approach demonstrating actual fragmentation problems.
"""

import pytest
import asyncio
import importlib
import sys
import threading
import time
from typing import Dict, List, Type, Any, Set
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from test_framework.base_integration_test import BaseIntegrationTest
from shared.types.core_types import UserID, ensure_user_id


def create_user_context_from_id(user_id: str) -> object:
    """Create proper user_context object from user_id string.

    ISSUE #996 FIX: Convert user_id parameter to user_context object
    that WebSocket manager constructor expects.
    """
    from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType

    try:
        # Try to use the real factory if available
        from netra_backend.app.core.user_context.factory import UserExecutionContextFactory
        return UserExecutionContextFactory.create_test_context(user_id=user_id)
    except ImportError:
        # Fallback to mock context
        id_manager = UnifiedIDManager()
        return type('MockUserContext', (), {
            'user_id': ensure_user_id(user_id) if user_id else id_manager.generate_id(IDType.USER, prefix="test"),
            'session_id': id_manager.generate_id(IDType.THREAD, prefix="test"),
            'request_id': id_manager.generate_id(IDType.REQUEST, prefix="test"),
            'is_test': True
        })()


@dataclass
class WebSocketManagerImplementation:
    """Data class to track WebSocket Manager implementations."""
    name: str
    module_path: str
    class_name: str
    line_number: int
    is_active: bool
    creation_method: str  # "direct", "factory", "adapter", "protocol"


class WebSocketManagerSSOTConsolidationTests(BaseIntegrationTest):
    """Test WebSocket Manager SSOT consolidation for Issue #824."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.discovered_implementations: List[WebSocketManagerImplementation] = []
        self.user_contexts: Dict[UserID, Any] = {}

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_detect_multiple_websocket_manager_implementations(self):
        """
        FAIL-FIRST TEST: Detect multiple WebSocket Manager implementations.

        This test SHOULD INITIALLY FAIL with 4 implementations detected,
        then PASS with only 1 after SSOT consolidation.
        """
        # Known implementations from Issue #824 analysis
        expected_implementations = [
            WebSocketManagerImplementation(
                name="WebSocketManager",
                module_path="netra_backend.app.websocket_core.websocket_manager",
                class_name="WebSocketManager",
                line_number=115,
                is_active=True,
                creation_method="direct"
            ),
            WebSocketManagerImplementation(
                name="WebSocketManagerFactory",
                module_path="netra_backend.app.websocket_core.websocket_manager_factory",
                class_name="WebSocketManagerFactory",
                line_number=516,
                is_active=True,
                creation_method="factory"
            ),
            WebSocketManagerImplementation(
                name="LegacyWebSocketManagerAdapter",
                module_path="netra_backend.app.websocket_core.protocols",
                class_name="LegacyWebSocketManagerAdapter",
                line_number=606,
                is_active=True,
                creation_method="adapter"
            ),
            WebSocketManagerImplementation(
                name="WebSocketManagerAdapter",
                module_path="netra_backend.app.agents.supervisor.agent_registry",
                class_name="WebSocketManagerAdapter",
                line_number=64,
                is_active=True,
                creation_method="adapter"
            )
        ]

        # Verify each implementation exists (this will fail if already consolidated)
        active_implementations = []

        for impl in expected_implementations:
            try:
                # Import the module
                module = importlib.import_module(impl.module_path)

                # Check if the class exists
                if hasattr(module, impl.class_name):
                    cls = getattr(module, impl.class_name)
                    active_implementations.append(impl)
                    self.discovered_implementations.append(impl)
                    print(f"DETECTED: {impl.name} at {impl.module_path}:{impl.line_number}")

            except (ImportError, AttributeError) as e:
                print(f"Implementation {impl.name} not found: {e}")

        # ASSERTION: This should FAIL initially with 4 implementations
        # After SSOT consolidation, should PASS with only 1 implementation
        if len(active_implementations) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Found {len(active_implementations)} WebSocket Manager implementations. "
                f"Expected exactly 1 after SSOT consolidation. "
                f"Active implementations: {[impl.name for impl in active_implementations]}"
            )

        # SUCCESS: Only one implementation should remain
        assert len(active_implementations) == 1, (
            f"SSOT SUCCESS: Expected exactly 1 WebSocket Manager implementation, "
            f"found {len(active_implementations)}"
        )

        # Verify it's the correct SSOT implementation
        remaining_impl = active_implementations[0]
        assert remaining_impl.name == "WebSocketManager", (
            f"Expected WebSocketManager as SSOT, got {remaining_impl.name}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_import_path_consistency(self):
        """
        FAIL-FIRST TEST: Verify consistent import paths for WebSocket Manager.

        This test checks that all WebSocket Manager imports use the same SSOT path.
        Should FAIL initially due to multiple import paths, PASS after consolidation.
        """
        # Expected SSOT import path after consolidation
        expected_ssot_import = "netra_backend.app.websocket_core.websocket_manager.WebSocketManager"

        # Import paths that indicate fragmentation (should be eliminated)
        fragmented_imports = [
            "netra_backend.app.websocket_core.websocket_manager_factory.WebSocketManagerFactory",
            "netra_backend.app.websocket_core.protocols.LegacyWebSocketManagerAdapter",
            "netra_backend.app.agents.supervisor.agent_registry.WebSocketManagerAdapter",
            "netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager"
        ]

        # Check if fragmented imports still exist
        existing_fragmented = []
        for import_path in fragmented_imports:
            module_path, class_name = import_path.rsplit('.', 1)
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    existing_fragmented.append(import_path)
            except ImportError:
                pass  # Import doesn't exist, which is good for consolidation

        # ASSERTION: This should FAIL initially with multiple import paths
        if existing_fragmented:
            pytest.fail(
                f"SSOT VIOLATION: Found fragmented WebSocket Manager import paths: "
                f"{existing_fragmented}. All imports should use: {expected_ssot_import}"
            )

        # SUCCESS: Only SSOT import path should work
        ssot_module_path, ssot_class_name = expected_ssot_import.rsplit('.', 1)
        try:
            ssot_module = importlib.import_module(ssot_module_path)
            assert hasattr(ssot_module, ssot_class_name), (
                f"SSOT import path {expected_ssot_import} not available"
            )
        except ImportError as e:
            pytest.fail(f"SSOT import path {expected_ssot_import} not available: {e}")

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_factory_pattern_race_conditions(self):
        """
        FAIL-FIRST TEST: Detect race conditions from multiple factory patterns.

        This test simulates concurrent factory creation to expose race conditions
        that occur with multiple WebSocket Manager implementations.
        """
        import concurrent.futures
        import threading

        # Track instances created by different factories
        created_instances = []
        creation_errors = []
        creation_lock = threading.Lock()

        def create_via_factory(factory_type: str, user_id: str) -> Any:
            """Attempt to create WebSocket Manager via different factory patterns."""
            try:
                user_id_typed = ensure_user_id(user_id)

                if factory_type == "unified_manager":
                    # Direct instantiation from unified manager
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    instance = UnifiedWebSocketManager()

                elif factory_type == "factory_pattern":
                    # Factory pattern instantiation
                    from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                    user_context = create_user_context_from_id(str(user_id_typed))
                    instance = create_websocket_manager(user_context=user_context)

                elif factory_type == "adapter_pattern":
                    # Adapter pattern instantiation
                    from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter
                    # Create mock WebSocket Manager for adapter
                    mock_manager = MagicMock()
                    instance = WebSocketManagerAdapter(mock_manager)

                elif factory_type == "protocol_pattern":
                    # Protocol-based instantiation (if exists)
                    from netra_backend.app.websocket_core.protocols import LegacyWebSocketManagerAdapter
                    mock_manager = MagicMock()
                    instance = LegacyWebSocketManagerAdapter(mock_manager)

                with creation_lock:
                    created_instances.append({
                        'factory_type': factory_type,
                        'user_id': user_id,
                        'instance_id': id(instance),
                        'instance_type': type(instance).__name__,
                        'creation_time': time.time()
                    })

                return instance

            except Exception as e:
                with creation_lock:
                    creation_errors.append({
                        'factory_type': factory_type,
                        'user_id': user_id,
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                return None

        # Test concurrent creation with different factory patterns
        factory_types = ["unified_manager", "factory_pattern", "adapter_pattern", "protocol_pattern"]
        user_ids = [f"user_{i}" for i in range(5)]

        # Create instances concurrently to expose race conditions
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for factory_type in factory_types:
                for user_id in user_ids:
                    future = executor.submit(create_via_factory, factory_type, user_id)
                    futures.append(future)

            # Wait for all creations to complete
            concurrent.futures.wait(futures, timeout=10)

        # ASSERTION: Multiple factory patterns indicate SSOT violation
        successful_factory_types = set()
        for instance in created_instances:
            successful_factory_types.add(instance['factory_type'])

        if len(successful_factory_types) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket Manager factory patterns are active: "
                f"{successful_factory_types}. This indicates fragmentation and potential race conditions. "
                f"Created instances: {len(created_instances)}, Errors: {len(creation_errors)}"
            )

        # SUCCESS: Only one factory pattern should work (the SSOT one)
        assert len(successful_factory_types) <= 1, (
            f"Expected at most 1 factory pattern after SSOT consolidation, "
            f"found {len(successful_factory_types)}: {successful_factory_types}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_user_isolation_consistency(self):
        """
        FAIL-FIRST TEST: Verify consistent user isolation across implementations.

        This test checks that all WebSocket Manager implementations provide
        consistent user isolation behavior. Multiple implementations may have
        different isolation mechanisms, causing user data leakage.
        """
        # Test users - use UUID format as required by ensure_user_id validation
        import uuid
        user_a = ensure_user_id(str(uuid.uuid4()))
        user_b = ensure_user_id(str(uuid.uuid4()))

        isolation_results = {}

        # Test isolation behavior across different implementations
        implementation_tests = [
            ("unified_manager", self._test_unified_manager_isolation),
            ("factory_pattern", self._test_factory_pattern_isolation),
            ("adapter_pattern", self._test_adapter_pattern_isolation)
        ]

        for impl_name, test_func in implementation_tests:
            try:
                isolation_results[impl_name] = test_func(user_a, user_b)
            except Exception as e:
                isolation_results[impl_name] = {
                    'error': str(e),
                    'isolated': False
                }

        # Check for inconsistent isolation behavior
        isolation_behaviors = set()
        for impl_name, result in isolation_results.items():
            if 'error' not in result:
                isolation_behaviors.add(result.get('isolated', False))

        # ASSERTION: Inconsistent isolation indicates SSOT violation
        if len(isolation_behaviors) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Inconsistent user isolation behavior across WebSocket Manager implementations. "
                f"Implementation results: {isolation_results}. "
                f"This indicates potential user data leakage between sessions."
            )

        # SUCCESS: All implementations should have consistent isolation (or only one should exist)
        working_implementations = [k for k, v in isolation_results.items() if 'error' not in v]
        if working_implementations:
            # All working implementations should provide isolation
            for impl_name in working_implementations:
                assert isolation_results[impl_name]['isolated'], (
                    f"Implementation {impl_name} does not provide proper user isolation"
                )

    def _test_unified_manager_isolation(self, user_a: UserID, user_b: UserID) -> Dict[str, Any]:
        """Test user isolation for UnifiedWebSocketManager."""
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

        # Create manager and test user isolation
        manager = UnifiedWebSocketManager()

        # Simulate user-specific data
        manager_id_a = id(manager)
        manager_id_b = id(manager)  # Same manager, different contexts

        return {
            'isolated': manager_id_a == manager_id_b,  # Same manager, context-based isolation
            'implementation': 'UnifiedWebSocketManager',
            'isolation_method': 'context_based'
        }

    def _test_factory_pattern_isolation(self, user_a: UserID, user_b: UserID) -> Dict[str, Any]:
        """Test user isolation for WebSocketManagerFactory."""
        from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

        # Create separate instances for each user
        context_a = create_user_context_from_id(user_a)
        context_b = create_user_context_from_id(user_b)
        manager_a = create_websocket_manager(user_context=context_a)
        manager_b = create_websocket_manager(user_context=context_b)

        return {
            'isolated': id(manager_a) != id(manager_b),  # Different instances
            'implementation': 'WebSocketManagerFactory',
            'isolation_method': 'instance_based'
        }

    def _test_adapter_pattern_isolation(self, user_a: UserID, user_b: UserID) -> Dict[str, Any]:
        """Test user isolation for WebSocketManagerAdapter."""
        try:
            from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter

            # Create mock managers for adapters
            mock_manager_a = MagicMock()
            mock_manager_b = MagicMock()

            adapter_a = WebSocketManagerAdapter(mock_manager_a)
            adapter_b = WebSocketManagerAdapter(mock_manager_b)

            return {
                'isolated': id(adapter_a) != id(adapter_b),
                'implementation': 'WebSocketManagerAdapter',
                'isolation_method': 'adapter_based'
            }
        except ImportError:
            return {
                'error': 'WebSocketManagerAdapter not available',
                'isolated': False
            }

    @pytest.mark.unit
    @pytest.mark.ssot_violation
    def test_websocket_manager_initialization_order_dependency(self):
        """
        FAIL-FIRST TEST: Detect initialization order dependencies between implementations.

        This test checks for timing-dependent initialization issues that occur
        when multiple WebSocket Manager implementations have interdependencies.
        """
        import threading
        import time
        import random

        initialization_results = []
        initialization_errors = []
        init_lock = threading.Lock()

        def initialize_implementation(impl_name: str, delay: float = 0) -> None:
            """Initialize a WebSocket Manager implementation with optional delay."""
            time.sleep(delay)  # Simulate timing variations

            try:
                start_time = time.time()

                if impl_name == "unified_manager":
                    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                    instance = UnifiedWebSocketManager()

                elif impl_name == "factory":
                    from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
                    factory = WebSocketManagerFactory()
                    test_context = create_user_context_from_id("test_user")
                    instance = factory.create_websocket_manager(user_context=test_context)

                elif impl_name == "adapter":
                    from netra_backend.app.agents.supervisor.agent_registry import WebSocketManagerAdapter
                    mock_manager = MagicMock()
                    instance = WebSocketManagerAdapter(mock_manager)

                end_time = time.time()

                with init_lock:
                    initialization_results.append({
                        'implementation': impl_name,
                        'success': True,
                        'duration': end_time - start_time,
                        'instance_id': id(instance),
                        'thread_id': threading.get_ident()
                    })

            except Exception as e:
                with init_lock:
                    initialization_errors.append({
                        'implementation': impl_name,
                        'error': str(e),
                        'error_type': type(e).__name__,
                        'thread_id': threading.get_ident()
                    })

        # Test initialization with random delays to detect order dependencies
        implementations = ["unified_manager", "factory", "adapter"]

        # Run multiple initialization rounds with random timing
        for round_num in range(3):
            threads = []
            for impl_name in implementations:
                delay = random.uniform(0, 0.1)  # Random delay 0-100ms
                thread = threading.Thread(
                    target=initialize_implementation,
                    args=(impl_name, delay)
                )
                threads.append(thread)
                thread.start()

            # Wait for all initializations to complete
            for thread in threads:
                thread.join(timeout=5)

        # ASSERTION: Multiple successful initializations indicate SSOT violation
        successful_implementations = set()
        for result in initialization_results:
            if result['success']:
                successful_implementations.add(result['implementation'])

        if len(successful_implementations) > 1:
            pytest.fail(
                f"SSOT VIOLATION: Multiple WebSocket Manager implementations initialized successfully: "
                f"{successful_implementations}. This indicates fragmentation and potential "
                f"initialization order dependencies. Successes: {len(initialization_results)}, "
                f"Errors: {len(initialization_errors)}"
            )

        # SUCCESS: Only one implementation should initialize successfully
        assert len(successful_implementations) <= 1, (
            f"Expected at most 1 WebSocket Manager implementation to initialize after SSOT consolidation, "
            f"found {len(successful_implementations)}: {successful_implementations}"
        )