"""
Unit tests for Issue #1318 - SSOT Import Validation

Tests to ensure netra_backend/app modules do NOT import from auth_service directly.
All auth imports should go through netra_backend.app.auth_integration layer.

Created: 2025-09-17
Issue: #1318 - SSOT violations in cross-service imports
"""

import os
import re
import unittest
from pathlib import Path
from typing import List, Tuple


class TestIssue1318ImportValidation(unittest.TestCase):
    """Test SSOT compliance for auth_service imports in netra_backend."""

    def setUp(self):
        """Set up test paths."""
        self.backend_app_path = Path(__file__).parent.parent.parent / "app"
        self.assertTrue(self.backend_app_path.exists(), f"Backend app path not found: {self.backend_app_path}")

    def test_no_direct_auth_service_imports(self):
        """
        Test that netra_backend/app modules do NOT import directly from auth_service.

        SSOT Pattern: Backend should only import auth via auth_integration layer.
        Expected: This test should PASS (no violations found).
        """
        violations = self._find_auth_service_imports()

        if violations:
            violation_details = "\n".join([
                f"  {file_path}:{line_num}: {line.strip()}"
                for file_path, line_num, line in violations
            ])
            self.fail(
                f"Found {len(violations)} SSOT violations - direct auth_service imports in backend:\n"
                f"{violation_details}\n\n"
                f"SOLUTION: Use 'from netra_backend.app.auth_integration.auth import ...' instead"
            )

    def test_sessionmanager_imports_are_internal(self):
        """
        Test that all SessionManager imports come from netra_backend, not auth_service.

        SSOT Pattern: SessionManager should be imported from internal database modules.
        Expected: This test should PASS (all imports are internal).
        """
        violations = self._find_external_sessionmanager_imports()

        if violations:
            violation_details = "\n".join([
                f"  {file_path}:{line_num}: {line.strip()}"
                for file_path, line_num, line in violations
            ])
            self.fail(
                f"Found {len(violations)} external SessionManager imports:\n"
                f"{violation_details}\n\n"
                f"SOLUTION: Import SessionManager from netra_backend.app.database.session_manager"
            )

    def _find_auth_service_imports(self) -> List[Tuple[str, int, str]]:
        """Find all direct auth_service imports in Python files."""
        violations = []

        for python_file in self.backend_app_path.rglob("*.py"):
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip comments and empty lines
                        stripped = line.strip()
                        if not stripped or stripped.startswith('#'):
                            continue

                        # Check for direct auth_service imports
                        if re.match(r'^\s*from\s+auth_service\b', line) or re.match(r'^\s*import\s+auth_service\b', line):
                            relative_path = os.path.relpath(python_file, self.backend_app_path.parent)
                            violations.append((relative_path, line_num, line))

            except (UnicodeDecodeError, PermissionError):
                # Skip binary files or files we can't read
                continue

        return violations

    def _find_external_sessionmanager_imports(self) -> List[Tuple[str, int, str]]:
        """Find SessionManager imports that come from outside netra_backend."""
        violations = []

        for python_file in self.backend_app_path.rglob("*.py"):
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        # Skip comments and empty lines
                        stripped = line.strip()
                        if not stripped or stripped.startswith('#'):
                            continue

                        # Check for external SessionManager imports
                        if ('SessionManager' in line and
                            re.match(r'^\s*from\s+', line) and
                            'auth_service' in line):
                            relative_path = os.path.relpath(python_file, self.backend_app_path.parent)
                            violations.append((relative_path, line_num, line))

            except (UnicodeDecodeError, PermissionError):
                # Skip binary files or files we can't read
                continue

        return violations


if __name__ == '__main__':
    unittest.main()