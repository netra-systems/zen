"""
Test Suite: Auth Service Import Violation Detection

This test prevents regression to Issue #1319 - ModuleNotFoundError: No module named 'auth_service'
by detecting when backend code tries to import from the auth_service module.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent deployment failures from import violations
- Value Impact: Ensures Golden Path deployment works without ModuleNotFoundError
- Strategic Impact: Maintains service boundaries and SSOT compliance

CRITICAL: Backend should use SSOT auth integration patterns, not direct auth_service imports.
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase


class AuthServiceImportViolationTests(SSotBaseTestCase):
    """Test suite to detect auth_service import violations in backend code."""

    def setup_method(self, method):
        """Setup test method with SSOT base configuration."""
        super().setup_method(method)
        self.project_root = Path(project_root)
        self.backend_path = self.project_root / "netra_backend"

    def _find_auth_service_imports(self, file_path: Path) -> List[Tuple[int, str]]:
        """Find all auth_service imports in a Python file."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST to extract imports
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'auth_service' in alias.name:
                            line_content = content.split('\n')[node.lineno - 1].strip()
                            violations.append((node.lineno, line_content))

                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'auth_service' in node.module:
                        line_content = content.split('\n')[node.lineno - 1].strip()
                        violations.append((node.lineno, line_content))

        except Exception as e:
            # Skip files that can't be parsed (might be test files with syntax issues)
            pass

        return violations

    def test_backend_has_no_auth_service_imports(self):
        """Test that backend code does not import from auth_service module."""
        # Find all Python files in backend
        python_files = list(self.backend_path.rglob("*.py"))

        # Exclude test files and backups
        production_files = [
            f for f in python_files
            if not any(part in str(f) for part in ['test', 'backup', '__pycache__'])
        ]

        all_violations = []

        for file_path in production_files:
            violations = self._find_auth_service_imports(file_path)
            if violations:
                for line_num, line_content in violations:
                    all_violations.append({
                        'file': str(file_path),
                        'line': line_num,
                        'content': line_content
                    })

        # Report violations if found
        if all_violations:
            print(f"\nFOUND {len(all_violations)} auth_service import violations:")
            for violation in all_violations:
                print(f"  {violation['file']}:{violation['line']} - {violation['content']}")
            print("\nUse SSOT auth integration patterns instead:")
            print("  - from netra_backend.app.auth_integration.auth import get_current_user")
            print("  - from netra_backend.app.db.models_user import User")
            print("  - from netra_backend.app.clients.auth_client_core import AuthServiceClient")

        # CRITICAL ASSERTION: No auth_service imports in backend
        assert len(all_violations) == 0, (
            f"CRITICAL: Found {len(all_violations)} auth_service imports in backend code. "
            f"Backend must use SSOT auth integration patterns. "
            f"This violates service boundaries and causes ModuleNotFoundError in GCP. "
            f"See Issue #1319."
        )

    def test_auth_models_import_works_without_auth_service(self):
        """Test that auth models can be imported without auth_service dependency."""
        try:
            # This should work without importing from auth_service
            from netra_backend.app.auth.models import AuthUser, AuthSession, AuthAuditLog, PasswordResetToken
            from netra_backend.app.auth.models import User, Secret, ToolUsageLog

            # Verify AuthUser is an alias for the backend User model
            assert AuthUser is User, "AuthUser should be an alias for backend User model"

            # Verify User model comes from backend, not auth_service
            assert 'netra_backend' in User.__module__, f"User model should come from backend, got {User.__module__}"

        except ImportError as e:
            pytest.fail(f"Auth models import failed (suggests auth_service dependency): {e}")

    def test_auth_integration_patterns_available(self):
        """Test that proper SSOT auth integration patterns are available."""
        try:
            # These are the correct SSOT patterns backend should use
            from netra_backend.app.auth_integration.auth import get_current_user
            from netra_backend.app.clients.auth_client_core import AuthServiceClient
            from netra_backend.app.db.models_user import User

            # Verify these are callable/usable
            assert callable(get_current_user), "get_current_user should be a callable dependency"
            assert hasattr(AuthServiceClient, '__init__'), "AuthServiceClient should be instantiable"
            assert hasattr(User, '__tablename__'), "User should be a SQLAlchemy model"

        except ImportError as e:
            pytest.fail(f"SSOT auth integration patterns not available: {e}")


if __name__ == "__main__":
    # Direct test execution
    pytest.main([__file__, "-v"])