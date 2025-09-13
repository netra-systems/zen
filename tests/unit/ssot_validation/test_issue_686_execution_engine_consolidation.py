"""Issue #686 ExecutionEngine SSOT Consolidation Validation Tests.

CRITICAL MISSION: Tests that FAIL when SSOT violations exist and PASS after consolidation.

This test file validates SSOT compliance for ExecutionEngine implementations and ensures
complete consolidation to UserExecutionEngine as the Single Source of Truth.

Business Value Protection: $500K+ ARR Golden Path functionality depends on proper
ExecutionEngine isolation and WebSocket event delivery.

Test Strategy:
1. Test FAILS with current codebase (proving violations exist)
2. Tests enforce single ExecutionEngine SSOT implementation
3. Tests validate deprecated execution_engine.py redirects work correctly
4. Tests ensure no import pollution or namespace conflicts
5. Tests PASS after proper ExecutionEngine consolidation

Created: 2025-09-12
Issue: #686 ExecutionEngine consolidation blocking Golden Path
"""

import ast
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
import unittest.mock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment


class TestIssue686ExecutionEngineConsolidation(SSotBaseTestCase):
    """Test ExecutionEngine SSOT consolidation compliance."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.env = IsolatedEnvironment()
        self.netra_backend_path = Path("netra_backend")
        self.execution_engine_files = self._find_execution_engine_files()

    def _find_execution_engine_files(self) -> List[Path]:
        """Find all files containing ExecutionEngine implementations."""
        execution_files = []

        # Search for files with ExecutionEngine in the name or content
        for root, dirs, files in os.walk(self.netra_backend_path):
            for file in files:
                if file.endswith('.py') and 'execution_engine' in file.lower():
                    execution_files.append(Path(root) / file)

        return execution_files

    def test_single_execution_engine_implementation_ssot_compliance(self):
        """TEST FAILS: Multiple ExecutionEngine classes violate SSOT principle.

        EXPECTED FAILURE: Current codebase has multiple ExecutionEngine implementations.
        PASSES AFTER: Only UserExecutionEngine should exist as SSOT implementation.
        """
        execution_engine_classes = self._find_execution_engine_classes()

        # SSOT VIOLATION CHECK: Should only have ONE canonical implementation
        canonical_implementation = "UserExecutionEngine"

        # Find actual implementations (not imports/aliases)
        actual_implementations = []
        for class_info in execution_engine_classes:
            if not class_info['is_alias'] and not class_info['is_import']:
                actual_implementations.append(class_info['name'])

        # TEST FAILS with current codebase - multiple implementations exist
        self.assertEqual(
            len(actual_implementations), 1,
            f"SSOT VIOLATION: Found {len(actual_implementations)} ExecutionEngine implementations: "
            f"{actual_implementations}. Only {canonical_implementation} should exist as SSOT. "
            f"Issue #686: Multiple ExecutionEngine implementations blocking Golden Path. "
            f"Details: {execution_engine_classes}"
        )

        # Validate the single implementation is the correct SSOT
        if actual_implementations:
            self.assertEqual(
                actual_implementations[0], canonical_implementation,
                f"SSOT VIOLATION: Wrong canonical implementation. Expected: {canonical_implementation}, "
                f"Found: {actual_implementations[0]}. Issue #686 requires UserExecutionEngine as SSOT."
            )

    def test_deprecated_execution_engine_redirect_compliance(self):
        """TEST FAILS: execution_engine.py must be deprecated redirect only.

        EXPECTED FAILURE: execution_engine.py should contain ONLY import redirects.
        PASSES AFTER: File contains only deprecation notice and redirect imports.
        """
        deprecated_file = self.netra_backend_path / "app" / "agents" / "supervisor" / "execution_engine.py"

        if not deprecated_file.exists():
            self.fail(f"SSOT VIOLATION: Deprecated redirect file missing: {deprecated_file}")

        # Read and analyze the deprecated file
        with open(deprecated_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST to analyze implementation
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.fail(f"SSOT VIOLATION: Syntax error in deprecated file {deprecated_file}: {e}")

        # Check for actual class definitions (not allowed in redirect)
        class_definitions = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

        # TEST FAILS if deprecated file has actual implementations
        self.assertEqual(
            len(class_definitions), 0,
            f"SSOT VIOLATION: Deprecated file {deprecated_file} contains class definitions: "
            f"{[cls.name for cls in class_definitions]}. Should only contain import redirects. "
            f"Issue #686: execution_engine.py must be redirect-only for SSOT compliance."
        )

        # Validate deprecation notice exists
        self.assertIn(
            "DEPRECATED", content,
            f"SSOT VIOLATION: Missing deprecation notice in {deprecated_file}. "
            f"Issue #686 requires clear deprecation warnings for migration."
        )

        # Validate redirect import exists
        self.assertIn(
            "UserExecutionEngine", content,
            f"SSOT VIOLATION: Missing UserExecutionEngine redirect in {deprecated_file}. "
            f"Issue #686 requires redirect to canonical SSOT implementation."
        )

    def test_no_execution_engine_import_pollution(self):
        """TEST FAILS: Import pollution violates SSOT principle.

        EXPECTED FAILURE: Multiple import paths for ExecutionEngine exist.
        PASSES AFTER: Only canonical UserExecutionEngine imports allowed.
        """
        import_violations = self._find_execution_engine_import_violations()

        # TEST FAILS if import pollution exists
        self.assertEqual(
            len(import_violations), 0,
            f"SSOT VIOLATION: Found {len(import_violations)} import pollution violations: "
            f"{import_violations}. Issue #686: Only canonical UserExecutionEngine imports allowed. "
            f"All other imports must go through deprecated redirect or be removed."
        )

    def test_user_execution_engine_canonical_import_path(self):
        """TEST FAILS: UserExecutionEngine not accessible via canonical path.

        EXPECTED FAILURE: Canonical import path broken or not SSOT compliant.
        PASSES AFTER: UserExecutionEngine importable via canonical SSOT path.
        """
        canonical_import_path = "netra_backend.app.agents.supervisor.user_execution_engine"

        try:
            # Test canonical import
            module = importlib.import_module(canonical_import_path)
            user_execution_engine = getattr(module, 'UserExecutionEngine')

            # Validate it's a proper class
            self.assertTrue(
                inspect.isclass(user_execution_engine),
                f"SSOT VIOLATION: UserExecutionEngine is not a class in canonical path {canonical_import_path}. "
                f"Issue #686 requires proper class implementation."
            )

            # Validate it has required methods for ExecutionEngine interface
            required_methods = ['execute_agent_with_websocket_events', 'create_from_legacy']
            missing_methods = []

            for method in required_methods:
                if not hasattr(user_execution_engine, method):
                    missing_methods.append(method)

            # TEST FAILS if required interface methods missing
            self.assertEqual(
                len(missing_methods), 0,
                f"SSOT VIOLATION: UserExecutionEngine missing required methods: {missing_methods}. "
                f"Issue #686: SSOT implementation must have complete ExecutionEngine interface."
            )

        except ImportError as e:
            self.fail(
                f"SSOT VIOLATION: Cannot import UserExecutionEngine from canonical path "
                f"{canonical_import_path}: {e}. Issue #686 requires working canonical import."
            )

    def test_execution_engine_factory_ssot_compliance(self):
        """TEST FAILS: ExecutionEngine factory patterns violate SSOT.

        EXPECTED FAILURE: Multiple factory implementations exist.
        PASSES AFTER: Single factory pattern for UserExecutionEngine creation.
        """
        factory_violations = self._find_execution_engine_factory_violations()

        # TEST FAILS if multiple factory patterns exist
        self.assertEqual(
            len(factory_violations), 0,
            f"SSOT VIOLATION: Found {len(factory_violations)} factory pattern violations: "
            f"{factory_violations}. Issue #686: Only UserExecutionEngine factory methods allowed."
        )

    def test_websocket_bridge_isolation_ssot_compliance(self):
        """TEST FAILS: WebSocket bridge not properly isolated per user.

        EXPECTED FAILURE: Shared WebSocket state between users exists.
        PASSES AFTER: Complete per-user WebSocket isolation in UserExecutionEngine.
        """
        # This test validates the core business value: proper user isolation
        try:
            from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

            # Create two user contexts to test isolation
            mock_context1 = unittest.mock.Mock()
            mock_context1.user_id = "user_1"
            mock_context1.session_id = "session_1"

            mock_context2 = unittest.mock.Mock()
            mock_context2.user_id = "user_2"
            mock_context2.session_id = "session_2"

            # Test factory method creates isolated instances
            try:
                engine1 = UserExecutionEngine.create_from_legacy(mock_context1)
                engine2 = UserExecutionEngine.create_from_legacy(mock_context2)

                # TEST FAILS if instances are the same (shared state violation)
                self.assertIsNot(
                    engine1, engine2,
                    f"SSOT VIOLATION: UserExecutionEngine factory returns same instance for different users. "
                    f"Issue #686: Shared state violates user isolation principle. "
                    f"Golden Path requires complete user isolation for $500K+ ARR protection."
                )

                # Validate different user contexts
                if hasattr(engine1, 'user_context') and hasattr(engine2, 'user_context'):
                    self.assertNotEqual(
                        engine1.user_context.user_id, engine2.user_context.user_id,
                        f"SSOT VIOLATION: UserExecutionEngine instances share user context. "
                        f"Issue #686: User isolation broken - critical security vulnerability."
                    )

            except Exception as e:
                self.fail(
                    f"SSOT VIOLATION: UserExecutionEngine factory method failed: {e}. "
                    f"Issue #686: Factory pattern must work for SSOT compliance."
                )

        except ImportError as e:
            self.fail(
                f"SSOT VIOLATION: Cannot import UserExecutionEngine for isolation testing: {e}. "
                f"Issue #686: SSOT implementation must be importable."
            )

    def _find_execution_engine_classes(self) -> List[Dict[str, Any]]:
        """Find all ExecutionEngine class definitions and imports."""
        classes = []

        for file_path in self.execution_engine_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                # Find class definitions
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and 'ExecutionEngine' in node.name:
                        classes.append({
                            'name': node.name,
                            'file': str(file_path),
                            'is_alias': False,
                            'is_import': False
                        })
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            if 'ExecutionEngine' in alias.name:
                                classes.append({
                                    'name': alias.name,
                                    'file': str(file_path),
                                    'is_alias': bool(alias.asname),
                                    'is_import': True,
                                    'module': node.module
                                })
                    elif isinstance(node, ast.Assign):
                        # Check for alias assignments like ExecutionEngine = UserExecutionEngine
                        for target in node.targets:
                            if isinstance(target, ast.Name) and 'ExecutionEngine' in target.id:
                                classes.append({
                                    'name': target.id,
                                    'file': str(file_path),
                                    'is_alias': True,
                                    'is_import': False
                                })

            except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
                continue

        return classes

    def _find_execution_engine_import_violations(self) -> List[Dict[str, str]]:
        """Find import pollution violations."""
        violations = []
        canonical_path = "netra_backend.app.agents.supervisor.user_execution_engine"

        # Search for non-canonical imports
        for root, dirs, files in os.walk(self.netra_backend_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        tree = ast.parse(content)

                        for node in ast.walk(tree):
                            if isinstance(node, ast.ImportFrom):
                                if (node.module and 'execution_engine' in node.module and
                                    node.module != canonical_path and
                                    'user_execution_engine' not in node.module):

                                    # Allow deprecated redirect imports
                                    if 'supervisor.execution_engine' in node.module:
                                        continue

                                    violations.append({
                                        'file': str(file_path),
                                        'import': f"from {node.module} import {[n.name for n in node.names]}",
                                        'line': getattr(node, 'lineno', 'unknown')
                                    })

                    except (SyntaxError, FileNotFoundError, UnicodeDecodeError):
                        continue

        return violations

    def _find_execution_engine_factory_violations(self) -> List[Dict[str, str]]:
        """Find ExecutionEngine factory pattern violations."""
        violations = []
        allowed_factories = {
            'UserExecutionEngine.create_from_legacy',
            'create_request_scoped_engine'  # Allowed in deprecated redirect
        }

        for root, dirs, files in os.walk(self.netra_backend_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for factory function definitions
                        if 'def create_' in content and 'execution_engine' in content.lower():
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if 'def create_' in line and 'execution' in line.lower():
                                    # Extract function name
                                    func_name = line.strip().split('def ')[1].split('(')[0]
                                    full_name = f"{file_path.stem}.{func_name}"

                                    if full_name not in allowed_factories:
                                        violations.append({
                                            'file': str(file_path),
                                            'function': func_name,
                                            'line': i + 1
                                        })

                    except (FileNotFoundError, UnicodeDecodeError):
                        continue

        return violations


if __name__ == '__main__':
    # Run this test to validate Issue #686 SSOT compliance
    # Expected: Tests FAIL with current codebase (proving violations exist)
    # Expected: Tests PASS after ExecutionEngine consolidation complete
    import unittest
    unittest.main(verbosity=2)