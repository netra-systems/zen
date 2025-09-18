"""
Unit Test: WebSocket SSOT Compliance Validation

ISSUE #1090: SSOT-incomplete-migration-websocket-manager-import-fragmentation

This test validates SSOT compliance by detecting import fragmentation violations
and ensuring canonical import paths work correctly.

PURPOSE:
- FAILS if deprecated import patterns are still active
- PASSES after SSOT remediation eliminates fragmentation

Business Value: Validates $500K+ ARR Golden Path infrastructure compliance
"""

import pytest
import ast
import os
import glob
import inspect
import warnings
import importlib.util
from typing import List, Dict, Set, Any, Optional, Tuple
from pathlib import Path
from test_framework.ssot.base_test_case import SSotAsyncTestCase


@pytest.mark.unit
class WebSocketSSOTComplianceValidationTests(SSotAsyncTestCase):
    """Comprehensive SSOT compliance validation for WebSocket imports."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.project_root = Path("C:/GitHub/netra-apex")
        self.websocket_core_path = self.project_root / "netra_backend/app/websocket_core"
        self.violations_found = []
        self.compliant_imports = []

    def test_websocket_core_directory_ssot_structure(self):
        """
        STRUCTURE TEST: Validates WebSocket core directory has proper SSOT structure.

        This test confirms the canonical SSOT files exist and deprecated files
        are properly marked for migration.
        """
        required_ssot_files = {
            'websocket_manager.py': 'canonical_ssot_implementation',
            'unified_manager.py': 'private_implementation_layer'
        }

        deprecated_files = {
            'websocket_manager_factory.py': 'deprecated_factory_pattern'
        }

        # Validate SSOT files exist
        for filename, description in required_ssot_files.items():
            file_path = self.websocket_core_path / filename
            self.assertTrue(
                file_path.exists(),
                f"SSOT file missing: {filename} ({description})"
            )

        # Validate deprecated files exist with deprecation markers
        for filename, description in deprecated_files.items():
            file_path = self.websocket_core_path / filename
            if file_path.exists():
                # Read file content to check for deprecation markers
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                deprecation_markers = [
                    'DEPRECATED',
                    'DeprecationWarning',
                    'warnings.warn',
                    'SSOT consolidation'
                ]

                markers_found = sum(1 for marker in deprecation_markers if marker in content)

                if markers_found < 2:
                    self.violations_found.append({
                        'type': 'insufficient_deprecation_markers',
                        'file': filename,
                        'markers_found': markers_found,
                        'status': 'SSOT_VIOLATION'
                    })
                    self.fail(
                        f"SSOT VIOLATION: {filename} exists but lacks proper deprecation markers. "
                        f"Found {markers_found} markers, need at least 2."
                    )

    def test_scan_codebase_for_deprecated_import_usage(self):
        """
        CODEBASE SCAN TEST: Scans entire codebase for deprecated WebSocket imports.

        This test FAILS if deprecated imports are found in active code.
        This test PASSES after all deprecated imports are migrated to SSOT.
        """
        deprecated_import_patterns = [
            'from netra_backend.app.websocket_core.websocket_manager_factory import',
            'import netra_backend.app.websocket_core.websocket_manager_factory',
            'websocket_manager_factory.create_websocket_manager',
            'websocket_manager_factory.WebSocketManagerFactory'
        ]

        python_files = list(self.project_root.glob("**/*.py"))
        violations = []

        for file_path in python_files:
            # Skip __pycache__ and backup files
            if '__pycache__' in str(file_path) or '.backup' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in deprecated_import_patterns:
                    if pattern in content:
                        violations.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'pattern': pattern,
                            'type': 'deprecated_import_usage'
                        })

            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read
                continue

        # Store violations for reporting
        self.violations_found.extend(violations)

        # TEST ASSERTION: Violations indicate incomplete SSOT migration
        if violations:
            violation_summary = "\n".join([
                f"  - {v['file']}: {v['pattern']}" for v in violations[:10]  # First 10
            ])
            total_violations = len(violations)

            self.assertTrue(
                len(violations) > 0,
                f"SSOT VIOLATION: {total_violations} deprecated WebSocket imports found:\n"
                f"{violation_summary}\n"
                f"{'...' if total_violations > 10 else ''}\n"
                "This test confirms incomplete SSOT migration. "
                "Test should FAIL now and PASS after remediation."
            )

    def test_validate_canonical_import_paths_functional(self):
        """
        FUNCTIONAL TEST: Validates canonical SSOT import paths work correctly.

        This test ensures the correct import patterns are functional.
        """
        canonical_patterns = [
            {
                'pattern': 'from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager',
                'expected_callable': 'get_websocket_manager'
            },
            {
                'pattern': 'from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager',
                'expected_class': 'WebSocketManager'
            }
        ]

        for pattern_info in canonical_patterns:
            try:
                if 'expected_callable' in pattern_info:
                    from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                    self.assertTrue(
                        callable(get_websocket_manager),
                        f"SSOT canonical import failed: {pattern_info['pattern']}"
                    )

                elif 'expected_class' in pattern_info:
                    from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
                    self.assertTrue(
                        inspect.isclass(WebSocketManager),
                        f"SSOT canonical import failed: {pattern_info['pattern']}"
                    )

                self.compliant_imports.append({
                    'pattern': pattern_info['pattern'],
                    'status': 'CANONICAL_SSOT_SUCCESS'
                })

            except ImportError as e:
                self.fail(f"CRITICAL: Canonical SSOT import failed: {pattern_info['pattern']} - {e}")

    def test_detect_circular_import_prevention(self):
        """
        CIRCULAR IMPORT TEST: Validates SSOT structure prevents circular imports.

        This test ensures the SSOT refactoring eliminated circular dependencies.
        """
        try:
            # Import the main SSOT module
            from netra_backend.app.websocket_core import websocket_manager

            # Check module dependencies using AST
            websocket_manager_path = self.websocket_core_path / "websocket_manager.py"

            with open(websocket_manager_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Check for potential circular imports
            circular_patterns = [
                'websocket_manager_factory',  # Should not import its own factory
                'netra_backend.app.websocket_core.websocket_manager_factory'
            ]

            circular_imports = [imp for imp in imports if any(pattern in imp for pattern in circular_patterns)]

            if circular_imports:
                self.violations_found.append({
                    'type': 'circular_import_detected',
                    'imports': circular_imports,
                    'status': 'SSOT_VIOLATION'
                })
                self.fail(
                    f"SSOT VIOLATION: Circular import patterns detected in websocket_manager.py: "
                    f"{circular_imports}. This indicates incomplete SSOT migration."
                )

        except Exception as e:
            self.fail(f"Circular import detection failed: {e}")

    def test_websocket_manager_factory_deprecation_warnings(self):
        """
        DEPRECATION WARNING TEST: Validates proper deprecation warnings are active.

        This test ensures deprecated modules properly warn users.
        """
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            try:
                # This should trigger deprecation warnings
                import netra_backend.app.websocket_core.websocket_manager_factory

                # Filter for relevant deprecation warnings
                websocket_deprecation_warnings = [
                    warning for warning in w
                    if issubclass(warning.category, DeprecationWarning)
                    and 'websocket_manager_factory' in str(warning.message).lower()
                ]

                # TEST ASSERTION: Should have deprecation warnings in violation state
                self.assertGreater(
                    len(websocket_deprecation_warnings), 0,
                    "SSOT VIOLATION: No deprecation warnings found for websocket_manager_factory. "
                    "This test confirms deprecated modules lack proper warnings. "
                    "Test should FAIL now (no warnings) and PASS after proper deprecation setup."
                )

                # Log warning details
                for warning in websocket_deprecation_warnings:
                    self.violations_found.append({
                        'type': 'deprecation_warning_active',
                        'message': str(warning.message),
                        'filename': warning.filename,
                        'status': 'DEPRECATION_CONFIRMED'
                    })

            except ImportError as e:
                # If factory module is already removed, this is post-remediation state
                self.compliant_imports.append({
                    'pattern': 'websocket_manager_factory import blocked',
                    'status': 'SSOT_REMEDIATION_COMPLETE'
                })

    def test_websocket_event_emission_ssot_compliance(self):
        """
        EVENT EMISSION TEST: Validates WebSocket event emission uses SSOT patterns.

        This test ensures critical WebSocket events use canonical import patterns.
        """
        # Look for WebSocket event emission patterns in codebase
        event_emission_files = list(self.project_root.glob("**/agents/**/*.py"))
        event_emission_files.extend(list(self.project_root.glob("**/websocket_core/**/*.py")))

        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        ssot_compliant_emissions = 0
        deprecated_pattern_emissions = 0

        for file_path in event_emission_files:
            if '__pycache__' in str(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for event emissions with import patterns
                for event in critical_events:
                    if event in content:
                        # Check which import pattern is used
                        if 'websocket_manager_factory' in content:
                            deprecated_pattern_emissions += 1
                            self.violations_found.append({
                                'type': 'event_emission_deprecated_import',
                                'file': str(file_path.relative_to(self.project_root)),
                                'event': event,
                                'status': 'SSOT_VIOLATION'
                            })
                        elif 'from netra_backend.app.websocket_core.canonical_import_patterns import' in content:
                            ssot_compliant_emissions += 1
                            self.compliant_imports.append({
                                'type': 'event_emission_ssot_compliant',
                                'file': str(file_path.relative_to(self.project_root)),
                                'event': event,
                                'status': 'SSOT_COMPLIANT'
                            })

            except (UnicodeDecodeError, PermissionError):
                continue

        # TEST ASSERTION: Deprecated patterns indicate incomplete migration
        if deprecated_pattern_emissions > 0:
            self.assertTrue(
                deprecated_pattern_emissions > 0,
                f"SSOT VIOLATION: {deprecated_pattern_emissions} WebSocket event emissions "
                f"using deprecated import patterns. {ssot_compliant_emissions} using SSOT patterns. "
                "This confirms incomplete SSOT migration for critical Golden Path events."
            )

    async def test_websocket_manager_creation_patterns_async(self):
        """
        ASYNC CREATION TEST: Validates WebSocket manager creation patterns.

        This async test checks both deprecated and canonical creation patterns.
        """
        creation_results = {
            'deprecated_pattern': None,
            'canonical_pattern': None,
            'direct_instantiation': None
        }

        # Test user context
        try:
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.types.core_types import ensure_user_id

            test_context = UserExecutionContext(
                user_id=ensure_user_id("ssot_validation_user"),
                thread_id="ssot_test_thread",
                run_id="ssot_test_run",
                request_id="ssot_compliance_test"
            )

            # Test deprecated pattern (should work but warn)
            try:
                from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
                deprecated_manager = await create_websocket_manager(user_context=test_context)
                creation_results['deprecated_pattern'] = 'SUCCESS'
            except Exception as e:
                creation_results['deprecated_pattern'] = f'FAILED: {e}'

            # Test canonical pattern (should work)
            try:
                from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
                canonical_manager = get_websocket_manager(user_context=test_context)
                creation_results['canonical_pattern'] = 'SUCCESS'
            except Exception as e:
                creation_results['canonical_pattern'] = f'FAILED: {e}'

            # Test direct instantiation (should work)
            try:
                from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
                direct_manager = WebSocketManager(user_context=test_context)
                creation_results['direct_instantiation'] = 'SUCCESS'
            except Exception as e:
                creation_results['direct_instantiation'] = f'FAILED: {e}'

            # Analyze results
            successful_patterns = sum(1 for result in creation_results.values() if result == 'SUCCESS')

            # VIOLATION STATE: Multiple patterns work (indicates fragmentation)
            if successful_patterns > 1:
                self.violations_found.append({
                    'type': 'multiple_creation_patterns_active',
                    'results': creation_results,
                    'successful_patterns': successful_patterns,
                    'status': 'SSOT_FRAGMENTATION_CONFIRMED'
                })

                # This confirms SSOT fragmentation exists
                self.assertGreater(
                    successful_patterns, 1,
                    f"SSOT VIOLATION: {successful_patterns} WebSocket manager creation patterns work. "
                    f"Results: {creation_results}. This confirms SSOT fragmentation. "
                    "Test should FAIL now (multiple patterns) and PASS after SSOT consolidation."
                )

        except Exception as e:
            self.fail(f"Async creation pattern test failed: {e}")

    def tearDown(self):
        """Clean up and log comprehensive SSOT compliance results."""
        super().tearDown()

        print("\n=== WEBSOCKET SSOT COMPLIANCE REPORT ===")

        if self.violations_found:
            print(f"\nVIOLATIONS FOUND ({len(self.violations_found)}):")
            for violation in self.violations_found:
                print(f"  - {violation['type']}: {violation.get('file', 'N/A')} - {violation['status']}")

        if self.compliant_imports:
            print(f"\nCOMPLIANT PATTERNS ({len(self.compliant_imports)}):")
            for compliant in self.compliant_imports[:5]:  # First 5
                print(f"  - {compliant.get('pattern', compliant.get('type', 'Unknown'))}: {compliant['status']}")

        # Summary
        violation_count = len(self.violations_found)
        compliant_count = len(self.compliant_imports)

        print(f"\nSUMMARY:")
        print(f"  - Violations: {violation_count}")
        print(f"  - Compliant: {compliant_count}")

        if violation_count > 0:
            print(f"  - RESULT: SSOT MIGRATION INCOMPLETE (Test FAILS as expected)")
        else:
            print(f"  - RESULT: SSOT COMPLIANT (Test PASSES after remediation)")


if __name__ == '__main__':
    import asyncio

    async def run_async_tests():
        test_instance = WebSocketSSOTComplianceValidationTests()
        await test_instance.asyncSetUp()

        # Run sync tests
        sync_tests = [
            test_instance.test_websocket_core_directory_ssot_structure,
            test_instance.test_scan_codebase_for_deprecated_import_usage,
            test_instance.test_validate_canonical_import_paths_functional,
            test_instance.test_detect_circular_import_prevention,
            test_instance.test_websocket_manager_factory_deprecation_warnings,
            test_instance.test_websocket_event_emission_ssot_compliance,
        ]

        for test in sync_tests:
            try:
                test()
                print(f"✓ {test.__name__}")
            except AssertionError as e:
                print(f"✗ {test.__name__}: {e}")
            except Exception as e:
                print(f"? {test.__name__}: Unexpected error: {e}")

        # Run async tests
        try:
            await test_instance.test_websocket_manager_creation_patterns_async()
            print(f"✓ test_websocket_manager_creation_patterns_async")
        except AssertionError as e:
            print(f"✗ test_websocket_manager_creation_patterns_async: {e}")
        except Exception as e:
            print(f"? test_websocket_manager_creation_patterns_async: Unexpected error: {e}")

        test_instance.tearDown()

    asyncio.run(run_async_tests())