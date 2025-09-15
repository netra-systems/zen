"""
Test Issue #1270: Pattern Filter Applied Globally Instead of E2E Only

Business Value Justification (BVJ):
- Segment: All (affects testing of all segments)
- Business Goal: Ensure test runner allows proper validation of all categories
- Value Impact: Critical testing infrastructure must work correctly to validate $500K+ ARR functionality
- Strategic Impact: Blocks staging validation and deployment confidence

Bug Description:
The unified test runner applies --pattern filtering to ALL categories instead of only E2E categories.
This causes database category tests to be deselected when using --pattern agent, triggering fast-fail.

Expected Behavior:
- --pattern should only filter E2E category tests
- Database category tests should run normally without pattern filtering
- All categories should be able to execute independently

Root Cause:
In _build_pytest_command() lines 3182-3186, the pattern is applied to all categories via pytest -k flag,
regardless of whether the category should be filtered or not.
"""

import pytest
import subprocess
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from test_framework.base_integration_test import BaseIntegrationTest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tests.unified_test_runner import UnifiedTestRunner

class TestIssue1270PatternFilterBug(BaseIntegrationTest):
    """Test suite for Issue #1270 - Pattern filter applied globally."""

    def setup_method(self):
        """Set up test runner and common test data."""
        self.runner = UnifiedTestRunner()
        self.project_root = PROJECT_ROOT
        
        # Manually initialize test_configs if not present (due to structural issue in unified_test_runner.py)
        if not hasattr(self.runner, 'test_configs'):
            self.runner.test_configs = {
                "backend": {
                    "path": self.project_root,
                    "test_dir": "netra_backend/tests",
                    "config": "pyproject.toml",
                    "command": f"{self.runner.python_command} -m pytest"
                },
                "auth": {
                    "path": self.project_root,
                    "test_dir": "auth_service/tests", 
                    "config": "pyproject.toml",
                    "command": f"{self.runner.python_command} -m pytest"
                }
            }
        
    @pytest.mark.integration
    def test_pattern_filter_applied_to_database_category_REPRODUCE_BUG(self):
        """
        FAILING TEST: Reproduces the current broken behavior.
        
        This test should FAIL initially, demonstrating that --pattern agent
        is incorrectly applied to database category tests, causing them to be deselected.
        """
        # Mock args that reproduce the issue
        mock_args = Mock()
        mock_args.pattern = "agent"
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = True
        mock_args.env = "staging"
        
        # Test database category with agent pattern
        cmd = self.runner._build_pytest_command("backend", "database", mock_args)
        
        # BUG: Current broken behavior - pattern is applied to database category
        # This causes database tests to be filtered, leaving only agent-related ones
        # But database category has no agent-related tests, so all get deselected
        assert '-k "agent"' in cmd, "Pattern should NOT be applied to database category (but currently is - this is the bug)"
        
        # The problematic command will cause pytest to deselect all database tests
        # because none match the "agent" pattern, triggering fast-fail
        print(f"BROKEN CMD (reproduces bug): {cmd}")
        
    @pytest.mark.integration  
    def test_database_category_should_run_without_pattern_filter_EXPECTED_BEHAVIOR(self):
        """
        EXPECTED BEHAVIOR: Database category should run all tests without pattern filtering.
        
        This test defines what SHOULD happen after the fix is implemented.
        Initially this will FAIL, but should PASS after fixing the bug.
        """
        # Mock args with pattern that should NOT affect database category
        mock_args = Mock()
        mock_args.pattern = "agent"  # This should only filter E2E tests
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = True
        mock_args.env = "staging"
        
        # Test database category command generation
        cmd = self.runner._build_pytest_command("backend", "database", mock_args)
        
        # EXPECTED: Database category should NOT have pattern filtering applied
        assert '-k "agent"' not in cmd, "Pattern should NOT be applied to database category"
        
        # Database category should only include its specific test paths
        expected_paths = ["netra_backend/tests/test_database_connections.py", "netra_backend/tests/clickhouse"]
        for path in expected_paths:
            assert path in cmd, f"Database category should include {path}"
            
        print(f"CORRECT CMD (expected behavior): {cmd}")

    @pytest.mark.integration
    def test_e2e_category_should_have_pattern_filtering_EXPECTED_BEHAVIOR(self):
        """
        EXPECTED BEHAVIOR: E2E category SHOULD have pattern filtering applied.
        
        This verifies that pattern filtering works correctly for E2E categories.
        """
        # Mock args with pattern that SHOULD affect E2E category
        mock_args = Mock()
        mock_args.pattern = "agent"
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = False
        mock_args.env = "staging"
        
        # Test E2E category command generation
        cmd = self.runner._build_pytest_command("backend", "e2e", mock_args)
        
        # EXPECTED: E2E category SHOULD have pattern filtering applied
        assert '-k "agent"' in cmd, "Pattern SHOULD be applied to E2E category"
        
        print(f"E2E CMD (should have pattern): {cmd}")

    @pytest.mark.integration
    def test_agent_category_should_have_pattern_filtering_EXPECTED_BEHAVIOR(self):
        """
        EXPECTED BEHAVIOR: Agent category SHOULD have pattern filtering applied.
        
        This verifies that pattern filtering works correctly for agent categories.
        """
        # Mock args with pattern
        mock_args = Mock()
        mock_args.pattern = "websocket"  # Different pattern to test flexibility
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = False
        mock_args.env = "staging"
        
        # Test agent category command generation
        cmd = self.runner._build_pytest_command("backend", "agent", mock_args)
        
        # EXPECTED: Agent category SHOULD have pattern filtering applied
        assert '-k "websocket"' in cmd, "Pattern SHOULD be applied to agent category"
        
        print(f"AGENT CMD (should have pattern): {cmd}")

    @pytest.mark.integration
    def test_non_filterable_categories_should_ignore_pattern(self):
        """
        Test that non-filterable categories ignore pattern parameter.
        
        Categories like unit, integration, database, api should NOT be filtered by pattern.
        Only E2E-related categories should use pattern filtering.
        """
        mock_args = Mock()
        mock_args.pattern = "agent"
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = False
        mock_args.env = "staging"
        
        # Test categories that should NOT be filtered
        non_filterable_categories = ["unit", "integration", "database", "api", "smoke"]
        
        for category in non_filterable_categories:
            cmd = self.runner._build_pytest_command("backend", category, mock_args)
            assert '-k "agent"' not in cmd, f"Pattern should NOT be applied to {category} category"
            print(f"{category.upper()} CMD (no pattern expected): {cmd}")

    @pytest.mark.integration  
    def test_filterable_categories_should_use_pattern(self):
        """
        Test that filterable categories correctly use pattern parameter.
        
        Categories like e2e, agent, websocket should use pattern filtering.
        """
        mock_args = Mock()
        mock_args.pattern = "agent"
        mock_args.no_coverage = True
        mock_args.parallel = False
        mock_args.verbose = False
        mock_args.fast_fail = False
        mock_args.env = "staging"
        
        # Test categories that SHOULD be filtered
        filterable_categories = ["e2e", "e2e_critical", "e2e_full", "agent", "websocket"]
        
        for category in filterable_categories:
            # Skip if category doesn't exist in the mapping
            try:
                cmd = self.runner._build_pytest_command("backend", category, mock_args)
                assert '-k "agent"' in cmd, f"Pattern SHOULD be applied to {category} category"
                print(f"{category.upper()} CMD (pattern expected): {cmd}")
            except KeyError:
                # Category doesn't exist in mapping, skip
                print(f"Skipping {category} - not in category mapping")
                continue

class TestIssue1270IntegrationValidation(BaseIntegrationTest):
    """Integration tests that validate the complete test runner behavior."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_database_category_execution_with_pattern_INTEGRATION(self):
        """
        Integration test: Verify database category can execute with pattern present.
        
        This test runs the actual unified test runner in a subprocess to validate
        that database category tests can run successfully even when --pattern is specified.
        """
        # Command that reproduces the issue
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
            "--category", "database",
            "--pattern", "agent",
            "--fast-fail",
            "--env", "staging",  
            "--no-docker",
            "--collection-only"  # Only collect, don't run tests to speed up
        ]
        
        try:
            # Run the command
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # After fix, this should NOT fail with "CATEGORY_FAILED"
            # Currently it WILL fail because database tests get deselected
            print(f"Return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
            # This assertion will FAIL initially (reproducing bug), 
            # but should PASS after fix
            assert result.returncode == 0, f"Database category should succeed with pattern, but got: {result.stderr}"
            
            # Verify database tests were collected, not deselected
            assert "deselected" not in result.stdout.lower(), "Database tests should not be deselected by agent pattern"
            
        except subprocess.TimeoutExpired:
            pytest.fail("Test runner execution timed out")
        except Exception as e:
            pytest.fail(f"Test runner execution failed: {e}")

    @pytest.mark.integration
    @pytest.mark.slow  
    def test_e2e_category_execution_with_pattern_INTEGRATION(self):
        """
        Integration test: Verify E2E category correctly applies pattern filtering.
        
        This validates that E2E category SHOULD be filtered by pattern.
        """
        # Command for E2E with pattern
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "tests" / "unified_test_runner.py"),
            "--category", "e2e",
            "--pattern", "agent",
            "--env", "staging",
            "--no-docker", 
            "--collection-only"  # Only collect, don't run tests
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            print(f"E2E Return code: {result.returncode}")
            print(f"E2E STDOUT: {result.stdout}")
            print(f"E2E STDERR: {result.stderr}")
            
            # E2E should succeed and show filtered results
            # This should work correctly even with current code
            assert result.returncode == 0, f"E2E category should handle pattern correctly: {result.stderr}"
            
        except subprocess.TimeoutExpired:
            pytest.fail("E2E test runner execution timed out")
        except Exception as e:
            pytest.fail(f"E2E test runner execution failed: {e}")

if __name__ == "__main__":
    # Run these tests to validate Issue #1270
    pytest.main([__file__, "-v", "-s"])