"""
SSOT Configuration Import Validation - Issue #962

This test validates that all configuration imports follow the SSOT pattern:
- REQUIRED: from netra_backend.app.config import get_config
- FORBIDDEN: from netra_backend.app.core.configuration.base import [anything]

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure
- Business Goal: System Stability and Maintainability
- Value Impact: Eliminates configuration import violations that cause confusion
- Revenue Impact: Ensures consistent configuration access patterns protecting $500K+ ARR

CRITICAL SUCCESS CRITERIA:
1. No imports from netra_backend.app.core.configuration.base in production code
2. All configuration access uses netra_backend.app.config.get_config()
3. SSOT pattern consistently applied across all modules
4. Configuration manager accessed through config.py only
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Tuple

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase

class TestIssue962SSotConfigurationValidation(SSotBaseTestCase):
    """Test SSOT configuration import compliance for Issue #962."""

    def test_no_base_configuration_imports_in_netra_backend(self):
        """Verify no imports from netra_backend.app.core.configuration.base in production code."""
        violations = []

        # Get netra_backend root path
        netra_backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"

        # Scan all Python files in netra_backend
        for py_file in netra_backend_root.rglob("*.py"):
            # Skip test files, backup files, and migration files
            if any(skip in str(py_file) for skip in ["test_", "tests/", ".backup", "__pycache__", "migration"]):
                continue

            violations.extend(self._check_file_for_base_imports(py_file, netra_backend_root))

        if violations:
            violation_summary = "\n".join([f"  - {file}: {import_line}" for file, import_line in violations])
            pytest.fail(
                f"SSOT VIOLATION: Found {len(violations)} configuration base imports in production code:\n"
                f"{violation_summary}\n\n"
                f"REQUIRED PATTERN: from netra_backend.app.config import get_config\n"
                f"FORBIDDEN PATTERN: from netra_backend.app.core.configuration.base import [anything]"
            )

    def test_proper_ssot_configuration_imports(self):
        """Verify production code uses proper SSOT configuration imports."""
        missing_ssot_imports = []
        files_needing_config = []

        # Get netra_backend root path
        netra_backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"

        # Check files that likely need configuration access
        for py_file in netra_backend_root.rglob("*.py"):
            # Skip test files and non-production files
            if any(skip in str(py_file) for skip in ["test_", "tests/", ".backup", "__pycache__"]):
                continue

            # Check if file needs configuration but doesn't use SSOT import
            needs_config, has_ssot_import = self._analyze_config_usage(py_file)
            if needs_config and not has_ssot_import:
                files_needing_config.append(str(py_file.relative_to(netra_backend_root)))

        if files_needing_config:
            files_summary = "\n".join([f"  - {file}" for file in files_needing_config[:10]])  # Limit to first 10
            if len(files_needing_config) > 10:
                files_summary += f"\n  ... and {len(files_needing_config) - 10} more files"

            pytest.fail(
                f"POTENTIAL SSOT IMPROVEMENT: Found {len(files_needing_config)} files that may need proper SSOT config imports:\n"
                f"{files_summary}\n\n"
                f"Consider using: from netra_backend.app.config import get_config"
            )

    def test_config_py_is_primary_interface(self):
        """Verify that config.py serves as the primary configuration interface."""
        netra_backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"
        config_file = netra_backend_root / "app" / "config.py"

        self.assertTrue(config_file.exists(), "config.py must exist as SSOT interface")

        # Check that config.py contains key SSOT functions
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_functions = ["get_config", "config_manager", "UnifiedConfigManager"]
        missing_functions = []

        for func in required_functions:
            if func not in content:
                missing_functions.append(func)

        if missing_functions:
            pytest.fail(
                f"SSOT VIOLATION: config.py missing required SSOT functions: {missing_functions}\n"
                f"config.py must serve as the complete SSOT interface for configuration access"
            )

    def test_no_direct_base_config_manager_usage(self):
        """Verify no direct usage of base configuration manager."""
        violations = []

        netra_backend_root = Path(__file__).parent.parent.parent.parent / "netra_backend"

        for py_file in netra_backend_root.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["test_", "tests/", ".backup", "__pycache__"]):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for problematic patterns
                problematic_patterns = [
                    "from netra_backend.app.core.configuration.base import config_manager",
                    "from netra_backend.app.core.configuration.base import get_unified_config",
                    "from netra_backend.app.core.configuration.base import UnifiedConfigManager"
                ]

                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in problematic_patterns:
                        if pattern in line:
                            violations.append((str(py_file.relative_to(netra_backend_root)), line_num, line.strip()))

            except Exception as e:
                # Skip files that can't be read
                continue

        if violations:
            violation_summary = "\n".join([f"  - {file}:{line_num}: {line}" for file, line_num, line in violations])
            pytest.fail(
                f"SSOT VIOLATION: Found {len(violations)} direct base configuration imports:\n"
                f"{violation_summary}\n\n"
                f"REQUIRED: Import from netra_backend.app.config instead"
            )

    def test_config_functions_work_correctly(self):
        """Test that SSOT configuration functions work correctly."""
        try:
            from netra_backend.app.config import get_config, config_manager

            # Test get_config function
            config = get_config()
            self.assertIsNotNone(config, "get_config() must return a configuration object")

            # Test config_manager
            self.assertIsNotNone(config_manager, "config_manager must be available")

            # Test that both return same configuration
            config_from_manager = config_manager.get_config()
            self.assertEqual(type(config), type(config_from_manager),
                           "get_config() and config_manager.get_config() must return same type")

        except ImportError as e:
            pytest.fail(f"SSOT IMPORT FAILURE: Cannot import SSOT configuration: {e}")
        except Exception as e:
            pytest.fail(f"SSOT FUNCTIONALITY FAILURE: SSOT configuration not working: {e}")

    def _check_file_for_base_imports(self, file_path: Path, root_path: Path) -> List[Tuple[str, str]]:
        """Check a file for forbidden base configuration imports."""
        violations = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST to find imports
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if (node.module and
                            "netra_backend.app.core.configuration.base" in node.module):
                            # Found forbidden import
                            import_line = f"from {node.module} import {', '.join([alias.name for alias in node.names])}"
                            violations.append((str(file_path.relative_to(root_path)), import_line))

            except SyntaxError:
                # File has syntax errors, skip AST parsing and use string matching
                for line_num, line in enumerate(content.splitlines(), 1):
                    if "from netra_backend.app.core.configuration.base import" in line:
                        violations.append((str(file_path.relative_to(root_path)), line.strip()))

        except Exception:
            # Skip files that can't be read
            pass

        return violations

    def _analyze_config_usage(self, file_path: Path) -> Tuple[bool, bool]:
        """Analyze if a file needs configuration and if it uses SSOT imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Indicators that file might need configuration
            config_indicators = [
                "settings.", "config.", "get_config", "database_url", "redis_url",
                "jwt_secret", "service_secret", "environment", "_config"
            ]

            needs_config = any(indicator in content for indicator in config_indicators)

            # Check for proper SSOT import
            has_ssot_import = "from netra_backend.app.config import" in content

            return needs_config, has_ssot_import

        except Exception:
            return False, False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])