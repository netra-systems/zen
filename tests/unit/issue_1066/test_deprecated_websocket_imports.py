"""
Test Deprecated WebSocket Factory Import Detection - Issue #1066

Business Value Justification (BVJ):
- Segment: ALL (Free -> Enterprise)
- Business Goal: Ensure SSOT compliance eliminates legacy WebSocket factory patterns
- Value Impact: Prevent multi-user data contamination and improve system security
- Revenue Impact: Protects $500K+ ARR by ensuring user isolation compliance

CRITICAL: These tests should FAIL with current deprecated code and PASS after SSOT migration.
Tests validate the specific files mentioned in Issue #1066 for SSOT compliance.

Test Strategy: Failing-first methodology to detect deprecated import patterns.
"""

import ast
import warnings
import pytest
import sys
from pathlib import Path
from typing import List, Set, Dict, Optional
from unittest.mock import patch, MagicMock
import importlib.util

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

class TestDeprecatedWebSocketImports:
    """Test that deprecated WebSocket factory imports are detected and eliminated."""

    def setup_method(self):
        """Setup for each test method."""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.deprecated_patterns = [
            "create_websocket_manager",
            "WebSocketManagerFactory",
            "get_websocket_manager_factory",
            "IsolatedWebSocketManager"
        ]

        # Files that should NOT contain deprecated patterns after migration
        self.target_files = [
            "netra_backend/app/websocket_core/__init__.py",
            "netra_backend/app/websocket_core/websocket_manager.py",
            "netra_backend/app/websocket_core/unified_manager.py",
            "netra_backend/app/routes/websocket.py",
            "netra_backend/app/agents/supervisor_agent_modern.py"
        ]

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_detect_deprecated_create_websocket_manager_imports(self):
        """
        Test that deprecated create_websocket_manager imports are detected.

        CRITICAL: This test should FAIL with current code that contains deprecated imports.
        After SSOT migration, this test should PASS (no deprecated imports found).
        """
        deprecated_import_files = []

        for file_path in self.target_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for deprecated import patterns
                if "create_websocket_manager" in content:
                    # Parse AST to find actual import statements (not just comments)
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.Import, ast.ImportFrom)):
                                if hasattr(node, 'names'):
                                    for alias in node.names:
                                        if alias.name == "create_websocket_manager":
                                            deprecated_import_files.append(str(file_path))
                                            break
                    except SyntaxError:
                        # If AST parsing fails, do text search
                        if "from" in content and "import" in content and "create_websocket_manager" in content:
                            deprecated_import_files.append(str(file_path))

            except Exception as e:
                pytest.fail(f"Failed to read file {file_path}: {e}")

        # CRITICAL: This assertion should FAIL with current deprecated code
        # After SSOT migration, no files should contain deprecated imports
        if deprecated_import_files:
            pytest.fail(
                f"DEPRECATED IMPORT DETECTED: Files still contain 'create_websocket_manager' imports: "
                f"{deprecated_import_files}. Issue #1066 SSOT migration incomplete. "
                f"These imports must be replaced with direct WebSocketManager instantiation."
            )

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_detect_deprecated_factory_patterns(self):
        """
        Test that deprecated WebSocket factory patterns are eliminated.

        CRITICAL: This test should FAIL with current code that contains factory patterns.
        After SSOT migration, factory patterns should be eliminated.
        """
        factory_pattern_violations = {}

        for file_path in self.target_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                violations = []
                for pattern in self.deprecated_patterns:
                    if pattern in content:
                        # More precise detection - check if it's actually used (not just in comments)
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if pattern in line and not line.strip().startswith('#'):
                                # Skip docstrings and comments
                                if '"""' not in line and "'''" not in line:
                                    violations.append(f"Line {i}: {line.strip()}")

                if violations:
                    factory_pattern_violations[str(file_path)] = violations

            except Exception as e:
                pytest.fail(f"Failed to read file {file_path}: {e}")

        # CRITICAL: This assertion should FAIL with current deprecated code
        if factory_pattern_violations:
            violation_summary = []
            for file_path, violations in factory_pattern_violations.items():
                violation_summary.append(f"\n{file_path}:")
                for violation in violations:
                    violation_summary.append(f"  - {violation}")

            pytest.fail(
                f"DEPRECATED FACTORY PATTERNS DETECTED: Issue #1066 SSOT migration incomplete. "
                f"Found deprecated WebSocket factory patterns:{''.join(violation_summary)}\n\n"
                f"These patterns must be replaced with direct WebSocketManager(user_context=...) instantiation."
            )

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_websocket_manager_direct_instantiation_required(self):
        """
        Test that WebSocketManager should be instantiated directly, not through factories.

        CRITICAL: Validates the target SSOT pattern that should exist after migration.
        This test should PASS and demonstrate the correct pattern.
        """
        # Test direct instantiation pattern
        try:
            # Import the SSOT WebSocketManager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            from netra_backend.app.core.user_context.factory import UserExecutionContextFactory

            # Create test user context
            user_context = UserExecutionContextFactory.create_test_context()

            # CORRECT PATTERN: Direct instantiation with user context
            manager = WebSocketManager(user_context=user_context)

            # Verify manager is created correctly
            assert manager is not None
            assert hasattr(manager, 'user_context')
            assert manager.user_context == user_context

        except ImportError as e:
            pytest.fail(f"SSOT WebSocketManager import failed: {e}. SSOT migration may be incomplete.")
        except Exception as e:
            pytest.fail(f"Direct WebSocketManager instantiation failed: {e}. Check SSOT implementation.")

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_deprecated_import_warnings_emitted(self):
        """
        Test that deprecated imports emit proper warnings.

        This test verifies the transition period behavior where deprecated imports
        should emit warnings before being completely removed.
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            try:
                # Try importing deprecated function (should emit warning)
                from netra_backend.app.websocket_core import create_websocket_manager

                # Check if deprecation warning was emitted
                deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]

                assert len(deprecation_warnings) > 0, (
                    "Expected DeprecationWarning for create_websocket_manager import, but none found. "
                    "Deprecated imports should emit warnings during transition period."
                )

                # Verify warning message mentions the deprecation
                warning_messages = [str(w.message) for w in deprecation_warnings]
                assert any("deprecated" in msg.lower() for msg in warning_messages), (
                    f"DeprecationWarning should mention 'deprecated'. Found messages: {warning_messages}"
                )

            except ImportError:
                # If import fails, the deprecated function may already be removed
                # This is actually the desired end state after migration
                pass

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_websocket_init_deprecation_warnings(self):
        """
        Test that __init__.py imports emit deprecation warnings.

        Validates Issue #1144 SSOT consolidation Phase 1 behavior.
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            try:
                # This import should trigger deprecation warning per Issue #1144
                from netra_backend.app.websocket_core import WebSocketManager

                # Check for deprecation warning about __init__.py imports
                deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]

                if deprecation_warnings:
                    # Verify warning mentions Issue #1144 or specific module imports
                    warning_messages = [str(w.message) for w in deprecation_warnings]
                    assert any("1144" in msg or "specific module" in msg for msg in warning_messages), (
                        f"Expected Issue #1144 deprecation warning. Found: {warning_messages}"
                    )

            except ImportError as e:
                pytest.fail(f"WebSocketManager import from __init__.py failed: {e}")

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_user_context_required_for_websocket_creation(self):
        """
        Test that WebSocket manager creation requires UserExecutionContext.

        CRITICAL: Validates user isolation requirements from User Context Architecture.
        Import-time initialization should be prohibited.
        """
        try:
            from netra_backend.app.websocket_core import create_websocket_manager

            # Test 1: create_websocket_manager without user_context should fail
            with pytest.raises((ValueError, RuntimeError)) as exc_info:
                create_websocket_manager(user_context=None)

            assert "UserExecutionContext" in str(exc_info.value), (
                "Expected error message to mention UserExecutionContext requirement"
            )

            # Test 2: Import-time initialization should be prohibited
            error_message = str(exc_info.value)
            assert any(phrase in error_message for phrase in [
                "Import-time initialization",
                "prohibited",
                "request-scoped"
            ]), f"Expected error about import-time initialization. Got: {error_message}"

        except ImportError:
            # If create_websocket_manager is removed, this is the desired end state
            # Test that direct WebSocketManager requires user_context
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

            with pytest.raises((ValueError, TypeError)) as exc_info:
                WebSocketManager(user_context=None)

            # Should require user_context parameter
            assert "user_context" in str(exc_info.value).lower()


class TestSSotWebSocketPatternCompliance:
    """Test compliance with SSOT WebSocket patterns after migration."""

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_canonical_websocket_manager_import_path(self):
        """
        Test that canonical WebSocket manager import path works.

        This validates the target SSOT import pattern that should work after migration.
        """
        try:
            # CANONICAL IMPORT: Direct from websocket_manager module
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

            # Verify the class is importable and functional
            assert WebSocketManager is not None
            assert hasattr(WebSocketManager, '__init__')

            # Verify it follows SSOT pattern (requires user_context)
            import inspect
            sig = inspect.signature(WebSocketManager.__init__)
            assert 'user_context' in sig.parameters, (
                "WebSocketManager should require user_context parameter for SSOT compliance"
            )

        except ImportError as e:
            pytest.fail(f"Canonical WebSocketManager import failed: {e}. SSOT pattern not implemented.")

    @pytest.mark.unit
    @pytest.mark.ssot_compliance
    def test_unified_manager_ssot_compliance(self):
        """
        Test that unified manager follows SSOT patterns.

        Validates the underlying SSOT implementation.
        """
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

            # Verify SSOT implementation exists
            assert UnifiedWebSocketManager is not None

            # Check for user context requirement in implementation
            import inspect
            sig = inspect.signature(UnifiedWebSocketManager.__init__)
            assert 'user_context' in sig.parameters, (
                "Unified implementation should require user_context for user isolation"
            )

        except ImportError as e:
            pytest.fail(f"Unified WebSocket manager implementation import failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])