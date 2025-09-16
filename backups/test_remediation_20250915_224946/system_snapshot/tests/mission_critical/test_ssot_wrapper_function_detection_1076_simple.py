"""
SSOT Wrapper Function Detection Tests for Issue #1076

Test Plan: Detect backward compatibility wrapper functions that create SSOT violations.
Should FAIL initially (detecting violations) and PASS after remediation.

Key violations to detect:
1. Remaining wrapper functions in auth integration
2. Backward compatibility functions that should be removed
3. Functions that delegate to legacy patterns instead of using SSOT directly

Related Issues: #1076 - SSOT compliance verification
Priority: CRITICAL - These tests protect against regression during SSOT migration
"""

import pytest
import ast
import os
from pathlib import Path
from typing import List, Dict, Set
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class SSotWrapperFunctionDetectionTests(SSotBaseTestCase):
    """Tests to detect SSOT wrapper function violations that need remediation."""

    @property
    def project_root(self):
        """Get project root path."""
        return Path(__file__).parent.parent.parent

    def test_auth_integration_wrapper_detection(self):
        """
        CRITICAL: Detect wrapper functions in auth integration that bypass SSOT.

        EXPECTED: Should FAIL initially - detects remaining wrapper functions
        REMEDIATION: Remove wrapper functions, use SSOT auth service directly
        """
        auth_integration_path = self.project_root / "netra_backend" / "app" / "auth_integration"

        if not auth_integration_path.exists():
            # Skip if path doesn't exist
            return

        wrapper_functions_found = []

        for py_file in auth_integration_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)

                # Look for function definitions that might be wrappers
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name

                        # Check for wrapper patterns
                        if self._is_wrapper_function(node, content):
                            wrapper_functions_found.append({
                                'file': str(py_file),
                                'function': func_name,
                                'line': node.lineno,
                                'reason': 'Wrapper function detected'
                            })

            except Exception as e:
                # Continue processing other files if one fails
                print(f"Warning: Could not parse {py_file}: {e}")
                continue

        # This test should FAIL initially if wrapper functions exist
        if wrapper_functions_found:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']} - {v['function']} ({v['reason']})"
                for v in wrapper_functions_found
            ])

            self.fail(
                f"SSOT VIOLATION: Found {len(wrapper_functions_found)} wrapper functions in auth integration:\n"
                f"{violation_details}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Remove wrapper functions\n"
                f"2. Update callers to use SSOT auth service directly\n"
                f"3. Ensure auth_service is the single source of truth for auth operations"
            )

    def test_function_delegation_pattern_detection(self):
        """
        CRITICAL: Detect functions that delegate to legacy patterns instead of SSOT.

        EXPECTED: Should FAIL initially - detects delegation violations
        REMEDIATION: Update functions to use SSOT directly
        """
        delegation_violations = []

        # Search for functions that import and delegate to legacy modules
        legacy_import_patterns = [
            "from netra_backend.app.logging_config import",
            "import netra_backend.app.logging_config"
        ]

        search_paths = [
            self.project_root / "netra_backend" / "app",
            self.project_root / "auth_service",
            self.project_root / "shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for legacy import patterns
                    for pattern in legacy_import_patterns:
                        if pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    delegation_violations.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'pattern': pattern,
                                        'content': line.strip(),
                                        'reason': 'Legacy import delegation'
                                    })

                except Exception as e:
                    continue

        # This test should FAIL initially if delegation violations exist
        if delegation_violations:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']} - {v['content']}"
                for v in delegation_violations[:10]  # Limit output
            ])

            self.fail(
                f"SSOT VIOLATION: Found {len(delegation_violations)} function delegation violations:\n"
                f"{violation_details}\n"
                f"{'... and more' if len(delegation_violations) > 10 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Replace legacy imports with SSOT imports\n"
                f"2. Update function implementations to use SSOT directly\n"
                f"3. Remove all delegation to legacy modules"
            )

    def test_deprecated_import_pattern_detection(self):
        """
        CRITICAL: Detect deprecated import patterns that should be updated.

        EXPECTED: Should FAIL initially - detects deprecated imports
        REMEDIATION: Update to SSOT import patterns
        """
        deprecated_imports = []

        # Deprecated import patterns to detect
        deprecated_patterns = [
            ("from netra_backend.app.logging_config import", "Use 'from shared.logging.unified_logging_ssot import get_logger'"),
            ("import netra_backend.app.logging_config", "Use 'from shared.logging.unified_logging_ssot import get_logger'"),
            ("from auth_service.legacy", "Use current auth_service modules"),
            ("from netra_backend.app.auth_integration import validate_jwt", "Use auth_service directly")
        ]

        search_paths = [
            self.project_root / "netra_backend",
            self.project_root / "auth_service",
            self.project_root / "shared"
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for py_file in search_path.rglob("*.py"):
                if py_file.name.startswith("__") or "test" in py_file.name:
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    for pattern, recommendation in deprecated_patterns:
                        if pattern in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if pattern in line:
                                    deprecated_imports.append({
                                        'file': str(py_file.relative_to(self.project_root)),
                                        'line': i,
                                        'pattern': pattern,
                                        'content': line.strip(),
                                        'recommendation': recommendation
                                    })

                except Exception as e:
                    continue

        # This test should FAIL initially if deprecated imports exist
        if deprecated_imports:
            violation_details = "\n".join([
                f"  - {v['file']}:{v['line']} - {v['content']}\n    Recommendation: {v['recommendation']}"
                for v in deprecated_imports[:15]  # Limit output
            ])

            self.fail(
                f"SSOT VIOLATION: Found {len(deprecated_imports)} deprecated import patterns:\n"
                f"{violation_details}\n"
                f"{'... and more' if len(deprecated_imports) > 15 else ''}\n\n"
                f"REMEDIATION REQUIRED:\n"
                f"1. Update all deprecated imports to SSOT patterns\n"
                f"2. Remove backward compatibility imports\n"
                f"3. Ensure all modules use current SSOT architecture"
            )

    def _is_wrapper_function(self, node: ast.FunctionDef, content: str) -> bool:
        """Check if a function appears to be a wrapper function."""
        # Get the function body as string
        func_lines = content.split('\n')[node.lineno-1:node.end_lineno if hasattr(node, 'end_lineno') else node.lineno+10]
        func_body = '\n'.join(func_lines)

        # Wrapper function indicators
        wrapper_indicators = [
            'return ' in func_body and len(node.body) <= 3,  # Simple wrapper with return
            'jwt.decode' in func_body and 'auth_service' not in func_body,  # JWT wrapper
            'validate_token' in node.name and len(node.body) <= 2,  # Token validation wrapper
            '_wrapper' in node.name.lower(),  # Explicitly named wrapper
            'def get_' in func_body and 'return config' in func_body  # Config getter wrapper
        ]

        return any(wrapper_indicators)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])