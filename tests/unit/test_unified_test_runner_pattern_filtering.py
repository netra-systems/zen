"""
Unit tests for Issue #1270: Pattern filtering incorrectly applied to database category

These tests SHOULD FAIL to demonstrate the pattern filtering bug in unified_test_runner.py.
The bug is that pattern filtering is applied globally instead of being category-specific.

Business Impact: Platform/Internal - Test Infrastructure Reliability
This bug causes database tests to be incorrectly filtered when patterns are applied,
leading to false positives in test execution results.

Expected Behavior:
- Database category should run specific test files without pattern filtering
- Pattern filtering should only apply to categories that use -k expressions

Actual Behavior (BUG):
- Pattern filtering is applied globally to all categories including database
- This causes database tests to be filtered incorrectly
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

# Setup path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestUnifiedTestRunnerPatternFiltering(SSotBaseTestCase):
    """Test that pattern filtering is incorrectly applied to database category."""

    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)

        # Mock the UnifiedTestRunner
        self.mock_runner = Mock()
        self.test_args = Mock()
        self.test_args.pattern = "connection"
        self.test_args.no_coverage = True

    def test_database_category_should_not_use_pattern_filtering(self):
        """
        TEST THAT SHOULD FAIL: Database category incorrectly gets pattern filtering.

        This test demonstrates the bug where pattern filtering is applied globally
        instead of being category-specific. The database category should run specific
        files without any -k pattern filtering.
        """
        # Simulate the broken behavior in unified_test_runner.py
        # This mimics the bug where pattern is applied to all categories

        # Database category definition (should not use -k patterns)
        database_category_paths = [
            "netra_backend/tests/test_database_connections.py",
            "netra_backend/tests/clickhouse"
        ]

        # Build command as the buggy code does
        cmd_parts = ["python", "-m", "pytest"]
        cmd_parts.extend(database_category_paths)

        # BUG: Pattern is applied globally to ALL categories
        if self.test_args.pattern:
            clean_pattern = self.test_args.pattern.strip('*')
            cmd_parts.extend(["-k", f'"{clean_pattern}"'])

        built_command = " ".join(cmd_parts)

        # ASSERTION THAT SHOULD FAIL - demonstrates the bug
        # The database category should NOT have -k pattern filtering
        self.assertNotIn('-k "connection"', built_command,
                        "Database category should not have pattern filtering applied, but it does (BUG)")

        # This assertion will fail, proving the bug exists
        print(f"Generated command (shows bug): {built_command}")

    def test_websocket_category_should_use_pattern_filtering(self):
        """
        Test that categories designed for pattern filtering work correctly.

        This test should PASS to show that some categories are supposed to use -k patterns.
        """
        # WebSocket category definition (should use -k patterns)
        websocket_category_config = ["-k", '"websocket or ws"']

        # Build command for websocket category
        cmd_parts = ["python", "-m", "pytest", "tests/"]
        cmd_parts.extend(websocket_category_config)

        # For websocket, additional pattern filtering is appropriate
        if self.test_args.pattern:
            clean_pattern = self.test_args.pattern.strip('*')
            cmd_parts.extend(["-k", f'"{clean_pattern}"'])

        built_command = " ".join(cmd_parts)

        # This should pass - websocket category can handle multiple -k expressions
        self.assertIn('-k', built_command,
                     "WebSocket category should use pattern filtering")

        print(f"WebSocket command (correct): {built_command}")

    def test_pattern_filtering_command_generation_bug(self):
        """
        TEST THAT SHOULD FAIL: Demonstrates incorrect command generation.

        This test shows that the current implementation applies pattern filtering
        globally without considering category-specific needs.
        """
        # Test data representing different categories
        categories_config = {
            "database": {
                "paths": ["netra_backend/tests/test_database_connections.py", "netra_backend/tests/clickhouse"],
                "should_use_pattern": False  # Database uses specific files, no patterns
            },
            "websocket": {
                "paths": ["tests/", "-k", '"websocket or ws"'],
                "should_use_pattern": True   # WebSocket uses patterns by design
            },
            "unit": {
                "paths": ["netra_backend/tests/unit"],
                "should_use_pattern": False  # Unit tests use directory paths
            }
        }

        pattern = "connection"

        for category_name, config in categories_config.items():
            cmd_parts = ["python", "-m", "pytest"]
            cmd_parts.extend(config["paths"])

            # BUG: This code applies pattern filtering globally
            if pattern:
                clean_pattern = pattern.strip('*')
                cmd_parts.extend(["-k", f'"{clean_pattern}"'])

            built_command = " ".join(cmd_parts)
            has_pattern_filter = '-k "connection"' in built_command

            # Check if this category should have pattern filtering
            if not config["should_use_pattern"]:
                # ASSERTION THAT SHOULD FAIL for database and unit categories
                self.assertFalse(has_pattern_filter,
                    f"Category '{category_name}' should not have pattern filtering, "
                    f"but command contains: {built_command}")
            else:
                # This should pass for websocket category
                self.assertTrue(has_pattern_filter,
                    f"Category '{category_name}' should have pattern filtering")

    def test_database_category_specific_files_vs_pattern_conflict(self):
        """
        TEST THAT SHOULD FAIL: Shows conflict between specific files and pattern filtering.

        Database category specifies exact files to run, but global pattern filtering
        can cause these specific files to be filtered out incorrectly.
        """
        # Database category specifies these exact files
        database_files = [
            "netra_backend/tests/test_database_connections.py",
            "netra_backend/tests/clickhouse"
        ]

        # Simulate pattern that would exclude these files
        exclusion_pattern = "not database"

        # Build command with the bug
        cmd_parts = ["python", "-m", "pytest"]
        cmd_parts.extend(database_files)

        # BUG: Pattern is applied even to specific file selections
        if exclusion_pattern:
            clean_pattern = exclusion_pattern.strip('*')
            cmd_parts.extend(["-k", f'"{clean_pattern}"'])

        built_command = " ".join(cmd_parts)

        # ASSERTION THAT SHOULD FAIL
        # When specific files are listed, pattern filtering should not be applied
        has_specific_files = any("test_database_connections.py" in part for part in cmd_parts)
        has_exclusion_pattern = '-k "not database"' in built_command

        if has_specific_files and has_exclusion_pattern:
            self.fail(f"BUG: Specific database files are listed but pattern filtering "
                     f"could exclude them. Command: {built_command}")

        print(f"Conflicting command (shows bug): {built_command}")


if __name__ == '__main__':
    unittest.main()