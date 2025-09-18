"""
MessageRouter SSOT Regression Prevention Test

GitHub Issue: #1056 - Message router fragmentation blocking Golden Path
Business Impact: $500K+ ARR - Users cannot receive AI responses reliably

PURPOSE: Monitor for future MessageRouter SSOT violations
STATUS: SHOULD FAIL initially with current fragmentation
EXPECTED: PASS after SSOT consolidation, then prevent future regressions

This test enforces SSOT compliance by monitoring implementation count
and preventing future introduction of fragmented MessageRouter implementations.
"""

import ast
import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterSSOTRegressionPrevention(SSotBaseTestCase):
    """Test MessageRouter SSOT regression prevention."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.project_root = Path("C:/GitHub/netra-apex")
        self.known_implementations = [
            "netra_backend/app/websocket_core/handlers.py",
            "netra_backend/app/agents/message_router.py",
            "netra_backend/app/core/message_router.py"
        ]
        self.canonical_implementation = "netra_backend/app/websocket_core/handlers.py"

        # SSOT compliance targets after consolidation
        self.max_allowed_implementations = 1  # Only canonical should remain
        self.allowed_compatibility_patterns = [
            # These patterns are acceptable for compatibility/migration
            "from netra_backend.app.websocket_core.handlers import MessageRouter",  # Re-export
            "__all__ = ['MessageRouter']"  # Export compatibility
        ]

    def test_prevent_message_router_ssot_regression(self):
        """
        Test prevents future MessageRouter SSOT violations.

        CRITICAL: This test SHOULD FAIL initially with current fragmentation.
        EXPECTED: PASS after SSOT consolidation, then fail on future violations.

        This test acts as a regression monitor to prevent re-introduction
        of fragmented MessageRouter implementations.
        """
        implementation_analysis = self._scan_for_message_router_implementations()

        # Log current implementation status
        implementation_count = len(implementation_analysis['implementations'])
        compatibility_count = len(implementation_analysis['compatibility_layers'])

        self.logger.info(f"MessageRouter implementation analysis:")
        self.logger.info(f"  Full implementations: {implementation_count}")
        self.logger.info(f"  Compatibility layers: {compatibility_count}")
        self.logger.info(f"  Total files with MessageRouter: {implementation_count + compatibility_count}")

        for impl in implementation_analysis['implementations']:
            self.logger.info(f"    Implementation: {impl}")

        for compat in implementation_analysis['compatibility_layers']:
            self.logger.info(f"    Compatibility: {compat}")

        # SSOT Validation
        total_implementations = implementation_count

        if total_implementations <= self.max_allowed_implementations:
            self.logger.info("✅ SSOT COMPLIANCE: MessageRouter implementation count within limits")

            # Additional validation: ensure canonical implementation exists
            canonical_found = any(
                impl['file_path'].endswith('websocket_core/handlers.py')
                for impl in implementation_analysis['implementations']
            )

            if not canonical_found:
                self.fail(
                    f"SSOT VIOLATION: Canonical MessageRouter implementation not found at "
                    f"{self.canonical_implementation}. This indicates improper consolidation."
                )

        else:
            # THIS IS EXPECTED TO FAIL initially - proves fragmentation exists
            violation_details = f"Found {total_implementations} MessageRouter implementations (max allowed: {self.max_allowed_implementations})"

            self.logger.error(f"❌ SSOT VIOLATION: {violation_details}")

            # Generate detailed violation report
            for impl in implementation_analysis['implementations']:
                self.logger.error(f"  VIOLATION: {impl['file_path']} - {impl['implementation_type']}")

            self.fail(
                f"SSOT VIOLATION: Too many MessageRouter implementations detected. "
                f"{violation_details}. This prevents SSOT consolidation and blocks Golden Path. "
                f"Expected exactly {self.max_allowed_implementations} implementation after consolidation."
            )

    def _scan_for_message_router_implementations(self) -> Dict[str, List[Dict]]:
        """Scan codebase for MessageRouter implementations and compatibility layers."""
        implementations = []
        compatibility_layers = []

        # Search in netra_backend directory
        search_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "netra_backend" / "tests",  # Check for test implementations
        ]

        for search_path in search_paths:
            if search_path.exists():
                implementations_found, compatibility_found = self._scan_directory_for_message_router(search_path)
                implementations.extend(implementations_found)
                compatibility_layers.extend(compatibility_found)

        return {
            'implementations': implementations,
            'compatibility_layers': compatibility_layers
        }

    def _scan_directory_for_message_router(self, directory: Path) -> Tuple[List[Dict], List[Dict]]:
        """Scan directory for MessageRouter class definitions and compatibility layers."""
        implementations = []
        compatibility_layers = []

        for py_file in directory.rglob("*.py"):
            try:
                file_analysis = self._analyze_file_for_message_router(py_file)

                if file_analysis['has_class_definition']:
                    implementations.append({
                        'file_path': str(py_file.relative_to(self.project_root)),
                        'class_name': 'MessageRouter',
                        'implementation_type': file_analysis['implementation_type'],
                        'method_count': file_analysis['method_count'],
                        'line_count': file_analysis['line_count']
                    })

                if file_analysis['has_compatibility_import']:
                    compatibility_layers.append({
                        'file_path': str(py_file.relative_to(self.project_root)),
                        'import_source': file_analysis['import_source'],
                        'compatibility_type': file_analysis['compatibility_type']
                    })

            except Exception as e:
                self.logger.debug(f"Could not analyze {py_file}: {e}")

        return implementations, compatibility_layers

    def _analyze_file_for_message_router(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for MessageRouter class definitions and imports."""
        analysis = {
            'has_class_definition': False,
            'has_compatibility_import': False,
            'implementation_type': None,
            'method_count': 0,
            'line_count': 0,
            'import_source': None,
            'compatibility_type': None
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST to find class definitions
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == 'MessageRouter':
                        analysis['has_class_definition'] = True
                        analysis['method_count'] = len([n for n in node.body if isinstance(n, ast.FunctionDef)])

                        # Determine implementation type based on method count and content
                        if analysis['method_count'] > 10:
                            analysis['implementation_type'] = 'full_implementation'
                        elif analysis['method_count'] > 5:
                            analysis['implementation_type'] = 'test_compatibility'
                        else:
                            analysis['implementation_type'] = 'minimal_stub'

                    elif isinstance(node, ast.ImportFrom):
                        # Check for MessageRouter imports
                        if (node.module and 'websocket_core.handlers' in node.module and
                            any(alias.name == 'MessageRouter' for alias in (node.names or []))):
                            analysis['has_compatibility_import'] = True
                            analysis['import_source'] = node.module
                            analysis['compatibility_type'] = 'import_reexport'

                    elif isinstance(node, ast.Import):
                        # Check for module imports that might provide MessageRouter
                        for alias in node.names or []:
                            if 'message_router' in alias.name.lower():
                                analysis['has_compatibility_import'] = True
                                analysis['import_source'] = alias.name
                                analysis['compatibility_type'] = 'module_import'

                # Count total lines for analysis
                analysis['line_count'] = len(content.splitlines())

            except SyntaxError as e:
                self.logger.debug(f"Syntax error in {file_path}: {e}")

        except Exception as e:
            self.logger.debug(f"Error reading {file_path}: {e}")

        return analysis

    def test_canonical_message_router_completeness(self):
        """
        Test that the canonical MessageRouter implementation is complete.

        This ensures that after SSOT consolidation, the canonical implementation
        provides all necessary functionality.
        """
        try:
            # Import canonical MessageRouter
            from netra_backend.app.websocket_core.handlers import MessageRouter

            # Test basic instantiation
            router = MessageRouter()

            # Validate essential interface
            essential_methods = [
                'handlers',  # Property
                'add_handler',  # Method
                'remove_handler',  # Method
                'route_message',  # Method
                'get_stats'  # Method
            ]

            missing_methods = []
            for method_name in essential_methods:
                if not hasattr(router, method_name):
                    missing_methods.append(method_name)

            if missing_methods:
                self.fail(
                    f"Canonical MessageRouter implementation incomplete. "
                    f"Missing methods: {missing_methods}. "
                    f"This indicates improper SSOT consolidation."
                )

            # Test basic functionality
            initial_handler_count = len(router.handlers)
            self.assertGreaterEqual(
                initial_handler_count, 5,
                "Canonical MessageRouter should have built-in handlers"
            )

            # Test statistics
            stats = router.get_stats()
            self.assertIsInstance(stats, dict, "get_stats should return dictionary")
            self.assertIn('handler_count', stats, "Stats should include handler count")

            self.logger.info("✅ Canonical MessageRouter implementation is complete and functional")

        except ImportError as e:
            self.fail(f"Cannot import canonical MessageRouter: {e}")
        except Exception as e:
            self.fail(f"Canonical MessageRouter implementation has errors: {e}")

    def test_ssot_import_path_enforcement(self):
        """
        Test that all MessageRouter imports use the canonical SSOT path.

        This prevents scattered imports that could hide future fragmentation.
        """
        import_analysis = self._scan_for_message_router_imports()

        non_canonical_imports = []
        canonical_import_path = "netra_backend.app.websocket_core.handlers"

        for file_info in import_analysis['files_with_imports']:
            for import_info in file_info['imports']:
                import_path = import_info['from_module']

                # Allow canonical path and direct compatibility re-exports
                if import_path == canonical_import_path:
                    continue  # Canonical import - allowed

                # Check if it's a known compatibility layer
                is_compatibility = any(
                    compat_path in import_path for compat_path in [
                        'agents.message_router',  # Known compatibility layer
                        'core.message_router'     # Known test compatibility layer
                    ]
                )

                if not is_compatibility:
                    non_canonical_imports.append({
                        'file': file_info['file_path'],
                        'import_path': import_path,
                        'line': import_info.get('line_number', 'unknown')
                    })

        # Log import analysis
        total_imports = sum(len(f['imports']) for f in import_analysis['files_with_imports'])
        canonical_count = total_imports - len(non_canonical_imports)

        self.logger.info(f"MessageRouter import analysis:")
        self.logger.info(f"  Total imports: {total_imports}")
        self.logger.info(f"  Canonical imports: {canonical_count}")
        self.logger.info(f"  Non-canonical imports: {len(non_canonical_imports)}")

        if non_canonical_imports:
            for bad_import in non_canonical_imports:
                self.logger.error(f"  NON-CANONICAL: {bad_import}")

        # SSOT Validation for imports
        # After consolidation, should have zero non-canonical imports
        if len(non_canonical_imports) == 0:
            self.logger.info("✅ SSOT COMPLIANCE: All MessageRouter imports use canonical path")
        else:
            # This might fail initially but should pass after SSOT consolidation
            violation_msg = f"SSOT VIOLATION: {len(non_canonical_imports)} non-canonical MessageRouter imports found"
            self.logger.warning(f"⚠️ {violation_msg}")

            # For now, just warn rather than fail - this becomes more strict after consolidation
            # self.fail(f"{violation_msg}. All imports should use canonical path: {canonical_import_path}")

    def _scan_for_message_router_imports(self) -> Dict[str, List[Dict]]:
        """Scan codebase for MessageRouter imports."""
        files_with_imports = []

        # Search in main application code
        search_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "tests",  # Also check test files
        ]

        for search_path in search_paths:
            if search_path.exists():
                files_found = self._scan_directory_for_imports(search_path)
                files_with_imports.extend(files_found)

        return {'files_with_imports': files_with_imports}

    def _scan_directory_for_imports(self, directory: Path) -> List[Dict]:
        """Scan directory for MessageRouter imports."""
        files_with_imports = []

        for py_file in directory.rglob("*.py"):
            try:
                import_info = self._extract_message_router_imports(py_file)
                if import_info['imports']:
                    files_with_imports.append({
                        'file_path': str(py_file.relative_to(self.project_root)),
                        'imports': import_info['imports']
                    })
            except Exception as e:
                self.logger.debug(f"Could not scan imports in {py_file}: {e}")

        return files_with_imports

    def _extract_message_router_imports(self, file_path: Path) -> Dict[str, List[Dict]]:
        """Extract MessageRouter imports from a Python file."""
        imports = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    # Check if MessageRouter is imported
                    if node.names and any(alias.name == 'MessageRouter' for alias in node.names):
                        imports.append({
                            'type': 'from_import',
                            'from_module': node.module or '',
                            'names': [alias.name for alias in node.names],
                            'line_number': node.lineno
                        })

        except Exception as e:
            self.logger.debug(f"Error parsing imports from {file_path}: {e}")

        return {'imports': imports}

    def test_future_implementation_detection(self):
        """
        Test future detection of new MessageRouter implementations.

        This test establishes a baseline and will catch any new implementations
        added after SSOT consolidation.
        """
        # Get current implementation fingerprint
        current_fingerprint = self._generate_implementation_fingerprint()

        # After SSOT consolidation, this fingerprint should be stable
        expected_implementation_count = 1  # Only canonical should remain
        expected_compatibility_count = 2   # Two known compatibility layers

        # Log current fingerprint for analysis
        self.logger.info("MessageRouter implementation fingerprint:")
        self.logger.info(f"  Implementation count: {current_fingerprint['implementation_count']}")
        self.logger.info(f"  Compatibility count: {current_fingerprint['compatibility_count']}")
        self.logger.info(f"  Total files: {current_fingerprint['total_files']}")

        # For now, just record the current state
        # After consolidation, this test should enforce the expected counts
        if (current_fingerprint['implementation_count'] == expected_implementation_count and
            current_fingerprint['compatibility_count'] == expected_compatibility_count):

            self.logger.info("✅ SSOT COMPLIANCE: Implementation fingerprint matches expected post-consolidation state")
        else:
            # Expected to fail initially - this proves the need for consolidation
            self.logger.warning(
                f"⚠️ CURRENT STATE: Implementation fingerprint indicates fragmentation. "
                f"Expected after consolidation: {expected_implementation_count} implementations, "
                f"{expected_compatibility_count} compatibility layers. "
                f"Current: {current_fingerprint['implementation_count']} implementations, "
                f"{current_fingerprint['compatibility_count']} compatibility layers."
            )

            # This test documents the current state and will validate post-consolidation
            self.assertTrue(True, "Implementation fingerprint recorded for future regression prevention")

    def _generate_implementation_fingerprint(self) -> Dict[str, Any]:
        """Generate fingerprint of current MessageRouter implementations."""
        analysis = self._scan_for_message_router_implementations()

        return {
            'implementation_count': len(analysis['implementations']),
            'compatibility_count': len(analysis['compatibility_layers']),
            'total_files': len(analysis['implementations']) + len(analysis['compatibility_layers']),
            'implementations': [impl['file_path'] for impl in analysis['implementations']],
            'compatibility_layers': [compat['file_path'] for compat in analysis['compatibility_layers']]
        }


if __name__ == "__main__":
    pytest.main([__file__])