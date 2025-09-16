"""
Test WebSocket Manager Factory Import SSOT Violations - Issue #1098

CRITICAL: This test must FAIL initially to prove violations exist.
After SSOT migration, this test must PASS to prove success.

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: Eliminate 2,615 import violations across 655 files
- Value Impact: Ensures SSOT compliance for $500K+ ARR chat functionality
- Revenue Impact: Prevents import chaos from breaking critical WebSocket events

FAILING TEST STRATEGY:
1. Test initially FAILS proving violations exist
2. SSOT migration removes websocket_manager_factory.py
3. Test PASSES proving migration success
"""

import pytest
import ast
import glob
import os
from pathlib import Path
from typing import List, Tuple, Dict
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestFactoryImportViolations(SSotBaseTestCase):
    """
    Unit tests to detect WebSocket Manager Factory import violations.

    CRITICAL: These tests are designed to FAIL initially, proving SSOT violations exist.
    After remediation, they must PASS to prove migration success.
    """

    def setUp(self):
        """Set up test environment for factory import violation detection."""
        super().setUp()
        self.netra_apex_root = "/c/netra-apex"
        self.violation_patterns = [
            "from netra_backend.app.websocket_core.websocket_manager_factory",
            "import websocket_manager_factory",
            "websocket_manager_factory.",
            "WebSocketManagerFactory",
            "FactoryInitializationError",
            "factory_instance.create_manager",
            "get_websocket_manager_factory"
        ]
        self.expected_violation_count = 2615  # From audit
        self.expected_violation_files = 655   # From audit

    def test_websocket_manager_factory_imports_forbidden(self):
        """
        Test that NO files import from websocket_manager_factory.py

        CRITICAL: This test MUST FAIL initially with 2,615 violations
        """
        violation_files = []
        violation_count = 0
        violation_details = []

        # Scan all Python files in the project
        python_files = self._get_all_python_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            violations = self._scan_file_for_factory_imports(py_file)
            if violations:
                violation_files.append(py_file)
                violation_count += len(violations)
                violation_details.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert violation_count == 0, (
            f"SSOT VIOLATION DETECTED: Found {violation_count} factory import violations "
            f"in {len(violation_files)} files. Expected violations: {self.expected_violation_count}. "
            f"This proves SSOT violations exist and must be remediated.\n"
            f"Sample violations:\n{self._format_violation_sample(violation_details[:10])}"
        )

        assert len(violation_files) == 0, (
            f"Files still importing websocket_manager_factory: {len(violation_files)} files. "
            f"Expected violation files: {self.expected_violation_files}.\n"
            f"Sample files: {violation_files[:10]}"
        )

    def test_factory_class_instantiation_forbidden(self):
        """
        Test that WebSocketManagerFactory class is not instantiated anywhere

        CRITICAL: Must detect direct factory instantiation violations
        """
        instantiation_violations = []

        python_files = self._get_all_python_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            violations = self._scan_file_for_factory_instantiation(py_file)
            instantiation_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(instantiation_violations) == 0, (
            f"FACTORY INSTANTIATION VIOLATIONS: Found {len(instantiation_violations)} "
            f"direct factory instantiation violations.\n"
            f"Violations: {instantiation_violations[:5]}"
        )

    def test_factory_legacy_patterns_forbidden(self):
        """
        Test that legacy factory patterns are not used

        CRITICAL: Detects factory pattern usage that violates SSOT
        """
        legacy_pattern_violations = []

        legacy_patterns = [
            "factory.create_manager",
            "manager_factory.get_instance",
            "websocket_factory.initialize",
            "factory_instance =",
            "_factory_singleton",
            "FactoryInitializationError",
            "WebSocketComponentError"
        ]

        python_files = self._get_all_python_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            violations = self._scan_file_for_legacy_patterns(py_file, legacy_patterns)
            legacy_pattern_violations.extend(violations)

        # CRITICAL: This assertion MUST FAIL initially
        assert len(legacy_pattern_violations) == 0, (
            f"LEGACY PATTERN VIOLATIONS: Found {len(legacy_pattern_violations)} "
            f"legacy factory pattern violations.\n"
            f"Violations: {legacy_pattern_violations[:5]}"
        )

    def test_websocket_manager_factory_file_removed(self):
        """
        Test that websocket_manager_factory.py file has been removed

        CRITICAL: This test FAILS while factory file exists (1,001 lines)
        """
        factory_file_path = os.path.join(
            self.netra_apex_root,
            "netra_backend/app/websocket_core/websocket_manager_factory.py"
        )

        file_exists = os.path.exists(factory_file_path)

        # CRITICAL: This assertion MUST FAIL initially
        assert not file_exists, (
            f"LEGACY FILE EXISTS: websocket_manager_factory.py still exists at {factory_file_path}. "
            f"This 1,001-line legacy file must be removed as part of SSOT migration. "
            f"File size: {self._get_file_size(factory_file_path) if file_exists else 0} bytes"
        )

    def test_canonical_imports_used_instead(self):
        """
        Test that files use canonical SSOT imports instead of factory imports

        CRITICAL: Validates migration to proper SSOT patterns
        """
        files_missing_canonical_imports = []
        files_with_factory_imports = []

        # Define canonical import patterns
        canonical_patterns = [
            "from netra_backend.app.websocket_core.unified_manager import",
            "from netra_backend.app.websocket_core.canonical_imports import",
            "from netra_backend.app.services.user_execution_context import"
        ]

        python_files = self._get_websocket_related_files()

        for py_file in python_files:
            if self._should_skip_file(py_file):
                continue

            has_factory_imports = self._has_factory_imports(py_file)
            has_canonical_imports = self._has_canonical_imports(py_file, canonical_patterns)

            if has_factory_imports:
                files_with_factory_imports.append(py_file)

            if not has_canonical_imports and self._needs_websocket_imports(py_file):
                files_missing_canonical_imports.append(py_file)

        # CRITICAL: These assertions MUST FAIL initially
        assert len(files_with_factory_imports) == 0, (
            f"FILES STILL USING FACTORY IMPORTS: {len(files_with_factory_imports)} files "
            f"still use factory imports instead of canonical SSOT imports.\n"
            f"Files: {files_with_factory_imports[:5]}"
        )

        # This assertion may not fail initially if files don't import anything
        if files_missing_canonical_imports:
            assert len(files_missing_canonical_imports) == 0, (
                f"FILES MISSING CANONICAL IMPORTS: {len(files_missing_canonical_imports)} files "
                f"need WebSocket functionality but don't use canonical imports.\n"
                f"Files: {files_missing_canonical_imports[:5]}"
            )

    # Helper methods for violation detection

    def _get_all_python_files(self) -> List[str]:
        """Get all Python files in the project."""
        return glob.glob(f"{self.netra_apex_root}/**/*.py", recursive=True)

    def _get_websocket_related_files(self) -> List[str]:
        """Get files that likely need WebSocket functionality."""
        patterns = [
            f"{self.netra_apex_root}/**/websocket*.py",
            f"{self.netra_apex_root}/**/agent*.py",
            f"{self.netra_apex_root}/**/manager*.py",
            f"{self.netra_apex_root}/**/execution*.py"
        ]

        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern, recursive=True))

        return list(set(files))  # Remove duplicates

    def _should_skip_file(self, file_path: str) -> bool:
        """Determine if file should be skipped during scanning."""
        skip_patterns = [
            "backup", "__pycache__", ".git", ".pytest_cache",
            "test_factory_import_violations.py",  # Skip this test file
            "migration_report", "archive", ".pyc"
        ]

        return any(pattern in file_path for pattern in skip_patterns)

    def _scan_file_for_factory_imports(self, file_path: str) -> List[Dict]:
        """Scan file for factory import violations."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Check for import patterns
            for pattern in self.violation_patterns:
                if pattern in content:
                    violations.append({
                        'file': file_path,
                        'pattern': pattern,
                        'type': 'import_violation'
                    })

            # Parse AST for more detailed analysis
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        violation = self._check_ast_node_for_violations(node, file_path)
                        if violation:
                            violations.append(violation)

            except SyntaxError:
                # Skip files with syntax errors
                pass

        except Exception:
            # Skip files that can't be read
            pass

        return violations

    def _scan_file_for_factory_instantiation(self, file_path: str) -> List[Dict]:
        """Scan file for direct factory instantiation."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            instantiation_patterns = [
                "WebSocketManagerFactory(",
                "websocket_manager_factory.WebSocketManagerFactory",
                "factory = WebSocketManagerFactory",
                "factory_instance = ",
                "create_websocket_manager_factory"
            ]

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in instantiation_patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'instantiation_violation'
                        })

        except Exception:
            pass

        return violations

    def _scan_file_for_legacy_patterns(self, file_path: str, patterns: List[str]) -> List[Dict]:
        """Scan file for legacy factory patterns."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in patterns:
                    if pattern in line:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'pattern': pattern,
                            'content': line.strip(),
                            'type': 'legacy_pattern_violation'
                        })

        except Exception:
            pass

        return violations

    def _check_ast_node_for_violations(self, node, file_path: str) -> Dict:
        """Check AST node for factory import violations."""
        if isinstance(node, ast.ImportFrom):
            if node.module and 'websocket_manager_factory' in node.module:
                return {
                    'file': file_path,
                    'type': 'ast_import_violation',
                    'module': node.module,
                    'names': [alias.name for alias in node.names] if node.names else []
                }

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if 'websocket_manager_factory' in alias.name:
                    return {
                        'file': file_path,
                        'type': 'ast_import_violation',
                        'name': alias.name
                    }

        return None

    def _has_factory_imports(self, file_path: str) -> bool:
        """Check if file has factory imports."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return any(pattern in content for pattern in self.violation_patterns)

        except Exception:
            return False

    def _has_canonical_imports(self, file_path: str, canonical_patterns: List[str]) -> bool:
        """Check if file has canonical SSOT imports."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            return any(pattern in content for pattern in canonical_patterns)

        except Exception:
            return False

    def _needs_websocket_imports(self, file_path: str) -> bool:
        """Check if file likely needs WebSocket functionality."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            websocket_indicators = [
                "websocket", "WebSocket", "send_message", "agent_started",
                "agent_thinking", "tool_executing", "connection_id"
            ]

            return any(indicator in content for indicator in websocket_indicators)

        except Exception:
            return False

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    def _format_violation_sample(self, violations: List[Dict]) -> str:
        """Format violation sample for error message."""
        if not violations:
            return "No violations to display"

        formatted = []
        for violation in violations[:5]:  # Show first 5
            if 'file' in violation and 'pattern' in violation:
                file_short = violation['file'].split('/')[-1]
                formatted.append(f"  - {file_short}: {violation['pattern']}")

        return "\n".join(formatted)


if __name__ == "__main__":
    # Run this test independently to check for violations
    pytest.main([__file__, "-v"])