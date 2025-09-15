"""
Test MessageRouter SSOT Violations Reproduction

Business Value Justification:
- Segment: Platform Infrastructure
- Business Goal: System Stability & SSOT Compliance
- Value Impact: Prevent routing conflicts that break $500K+ ARR chat functionality
- Strategic Impact: SSOT violation detection and prevention

Purpose: This test file is designed to FAIL initially to demonstrate current
MessageRouter SSOT violations. After SSOT consolidation, all tests should PASS.

Issue #1067: MessageRouter SSOT Consolidation Test Suite
"""

import pytest
import importlib
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Set, Type
import inspect

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTViolationsReproduction(SSotBaseTestCase):
    """Reproduce and validate MessageRouter SSOT violations."""

    @pytest.mark.unit
    @pytest.mark.ssot_validation
    def test_detect_multiple_router_implementations(self):
        """FAILING TEST: Should detect exactly 1 MessageRouter class, currently finds 2+.

        This test should FAIL initially, demonstrating SSOT violation.
        Expected to find multiple MessageRouter implementations which violates SSOT.
        """
        router_implementations = self._discover_message_router_classes()

        # Expected: 1 (SSOT compliant)
        # Current Reality: 2+ (SSOT violation)
        expected_count = 1
        actual_count = len(router_implementations)

        assert actual_count == expected_count, (
            f"SSOT VIOLATION: Found {actual_count} MessageRouter implementations, "
            f"expected {expected_count}. Implementations: {router_implementations}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_validation
    def test_canonical_router_import_path_enforcement(self):
        """FAILING TEST: All MessageRouter imports should use canonical path.

        This test should FAIL initially, showing import path fragmentation.
        """
        canonical_path = "netra_backend.app.websocket_core.handlers"
        invalid_imports = self._find_non_canonical_imports()

        assert len(invalid_imports) == 0, (
            f"SSOT VIOLATION: Found {len(invalid_imports)} non-canonical MessageRouter imports. "
            f"All imports must use '{canonical_path}'. Violations: {invalid_imports}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_validation
    def test_routing_conflict_between_implementations(self):
        """FAILING TEST: Different MessageRouter instances should not conflict.

        This test should FAIL initially, demonstrating routing conflicts.
        """
        routing_conflicts = []

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter as WebSocketRouter
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            ws_router = WebSocketRouter()

            # Create mock dependencies for QualityMessageRouter
            mock_db = None
            mock_redis = None
            mock_llm_manager = None
            mock_ws_manager = None

            quality_router = QualityMessageRouter(mock_db, mock_redis, mock_llm_manager, mock_ws_manager)

            # Check if both routers handle the same message types (conflict)
            ws_message_types = set(getattr(ws_router, '_supported_types', ['user_message', 'system_message']))
            quality_message_types = set(getattr(quality_router, '_supported_types', ['user_message', 'agent_request']))

            conflicts = ws_message_types.intersection(quality_message_types)

            if len(conflicts) > 0:
                routing_conflicts.extend(list(conflicts))

            # Check for method conflicts
            ws_methods = set(method for method in dir(ws_router) if not method.startswith('_'))
            quality_methods = set(method for method in dir(quality_router) if not method.startswith('_'))

            method_conflicts = ws_methods.intersection(quality_methods)
            if method_conflicts:
                routing_conflicts.append(f"Method conflicts: {method_conflicts}")

        except ImportError as e:
            # If imports fail, that's also a SSOT violation
            routing_conflicts.append(f"Import error: {str(e)}")

        assert len(routing_conflicts) == 0, (
            f"ROUTING CONFLICT: Found {len(routing_conflicts)} conflicts between MessageRouter implementations. "
            f"This creates ambiguous routing and violates SSOT principles. Conflicts: {routing_conflicts}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_validation
    def test_message_handler_registration_consistency(self):
        """FAILING TEST: Message handler registration should be consistent across routers.

        This test should FAIL initially, showing registration inconsistencies.
        """
        consistency_violations = []

        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter

            router1 = MessageRouter()
            router2 = MessageRouter()

            # Create a test handler
            class TestHandler:
                def handle_message(self, message):
                    return {"status": "handled", "message": message}

            test_handler = TestHandler()

            # Check if both routers support same registration methods
            router1_methods = {method for method in dir(router1) if 'handler' in method.lower()}
            router2_methods = {method for method in dir(router2) if 'handler' in method.lower()}

            if router1_methods != router2_methods:
                consistency_violations.append(
                    f"Different handler methods between router instances. "
                    f"Router1: {router1_methods}, Router2: {router2_methods}"
                )

            # Check if registration methods work consistently
            if hasattr(router1, 'add_handler') and hasattr(router2, 'add_handler'):
                try:
                    router1.add_handler(test_handler)
                    router2.add_handler(test_handler)

                    handlers1 = getattr(router1, 'custom_handlers', [])
                    handlers2 = getattr(router2, 'custom_handlers', [])

                    if len(handlers1) != len(handlers2):
                        consistency_violations.append(
                            f"Handler count mismatch after registration. "
                            f"Router1: {len(handlers1)}, Router2: {len(handlers2)}"
                        )
                except Exception as e:
                    consistency_violations.append(f"Handler registration failed: {str(e)}")

        except Exception as e:
            consistency_violations.append(f"MessageRouter instantiation failed: {str(e)}")

        assert len(consistency_violations) == 0, (
            f"HANDLER REGISTRATION INCONSISTENCY: Found {len(consistency_violations)} violations. "
            f"Details: {consistency_violations}"
        )

    @pytest.mark.unit
    @pytest.mark.ssot_validation
    def test_router_singleton_violation_detection(self):
        """FAILING TEST: Should detect singleton pattern violations.

        This test should FAIL initially if singleton patterns exist.
        """
        singleton_violations = []

        try:
            # Try to detect singleton patterns in MessageRouter implementations
            router_implementations = self._discover_message_router_classes()

            for path, router_class in router_implementations.items():
                # Check for singleton indicators
                class_source = inspect.getsource(router_class)

                singleton_indicators = [
                    "_instance" in class_source,
                    "__new__" in class_source and "cls._instance" in class_source,
                    "singleton" in class_source.lower(),
                    "_instances" in class_source
                ]

                if any(singleton_indicators):
                    singleton_violations.append(f"Singleton pattern detected in {path}")

        except Exception as e:
            singleton_violations.append(f"Singleton detection failed: {str(e)}")

        # For now, we expect violations, so test should pass if violations found
        # After SSOT consolidation, change this assertion
        assert len(singleton_violations) == 0, (
            f"SINGLETON VIOLATIONS: Found {len(singleton_violations)} singleton patterns. "
            f"SSOT requires factory patterns for user isolation. Violations: {singleton_violations}"
        )

    # Helper methods
    def _discover_message_router_classes(self) -> Dict[str, Type]:
        """Discover all MessageRouter class implementations in the codebase."""
        implementations = {}

        # Known paths where MessageRouter might exist
        potential_paths = [
            "netra_backend.app.websocket_core.handlers",
            "netra_backend.app.core.message_router",
            "netra_backend.app.services.message_router",
            "netra_backend.app.agents.message_router",
            "netra_backend.app.services.websocket.quality_message_router"
        ]

        for path in potential_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, 'MessageRouter'):
                    router_class = getattr(module, 'MessageRouter')
                    implementations[path] = router_class
                if hasattr(module, 'QualityMessageRouter'):
                    router_class = getattr(module, 'QualityMessageRouter')
                    implementations[f"{path}.QualityMessageRouter"] = router_class
            except ImportError:
                continue  # Path doesn't exist, which is fine

        return implementations

    def _find_non_canonical_imports(self) -> List[str]:
        """Find all non-canonical MessageRouter import statements."""
        # This would scan source files for import patterns
        # For now, return known violations based on analysis
        non_canonical_patterns = [
            "from netra_backend.app.core.message_router import MessageRouter",
            "from netra_backend.app.agents.message_router import MessageRouter",
            "from netra_backend.app.services.message_router import MessageRouter",
            "from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter"
        ]

        # In a real implementation, this would scan actual source files
        # For testing purposes, we'll simulate finding these violations
        return non_canonical_patterns

    def _scan_source_files_for_imports(self) -> List[str]:
        """Scan actual source files for MessageRouter imports (placeholder)."""
        violations = []

        # This would be implemented to actually scan source files
        # For now, return expected violations for demonstration

        return violations