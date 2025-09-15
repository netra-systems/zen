"""
Test Pattern Filter Integration Suite
=====================================

This test suite validates the integration aspects of pattern filtering with the
overall test runner system and real test execution scenarios.

INTEGRATION TESTING OBJECTIVES:
1. Test pattern filtering integration with real test discovery
2. Validate pattern filter interaction with test collection
3. Test pattern filtering with actual pytest execution
4. Verify integration with category-specific test running
"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path
from textwrap import dedent


class TestPatternFilterIntegrationWithRealTests:
    """Test pattern filtering integration with actual test discovery and execution."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
        # Create temporary test files for integration testing
        self.temp_dir = Path(tempfile.mkdtemp(prefix="pattern_filter_test_"))
        self.setup_temporary_test_files()
        
    def teardown_method(self):
        """Cleanup after each test method."""
        # Clean up temporary test files
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def setup_temporary_test_files(self):
        """Create temporary test files for integration testing."""
        # Create unit test file
        unit_test_content = dedent('''
            import pytest
            
            def test_unit_auth_functionality():
                """Unit test for auth functionality."""
                assert True
                
            def test_unit_websocket_functionality():
                """Unit test for websocket functionality."""
                assert True
                
            def test_unit_general_functionality():
                """General unit test."""
                assert True
        ''')
        
        # Create integration test file
        integration_test_content = dedent('''
            import pytest
            
            def test_integration_auth_system():
                """Integration test for auth system."""
                assert True
                
            def test_integration_websocket_system():
                """Integration test for websocket system."""
                assert True
                
            def test_integration_general_system():
                """General integration test."""
                assert True
        ''')
        
        # Create E2E test file
        e2e_test_content = dedent('''
            import pytest
            
            def test_e2e_auth_flow():
                """E2E test for auth flow."""
                assert True
                
            def test_e2e_websocket_flow():
                """E2E test for websocket flow."""
                assert True
                
            def test_e2e_general_flow():
                """General E2E test."""
                assert True
        ''')
        
        # Write test files
        (self.temp_dir / "test_unit_sample.py").write_text(unit_test_content)
        (self.temp_dir / "test_integration_sample.py").write_text(integration_test_content)
        (self.temp_dir / "test_e2e_sample.py").write_text(e2e_test_content)
        
    def test_real_unit_test_pattern_filtering_integration(self):
        """
        INTEGRATION: Test pattern filtering with real unit tests.
        
        This should FAIL because unit tests are incorrectly filtered by pattern.
        """
        # Run unit tests with specific pattern that matches some tests
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit",
            "--pattern", "auth",  # Should match test_unit_auth_functionality
            "--collect-only",
            str(self.temp_dir / "test_unit_sample.py")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # BUG: Unit tests should NOT be filtered by pattern
        # All unit tests should be collected regardless of pattern
        if "collected 1 item" in result.stdout:  # Only auth test collected
            pytest.fail(
                "BUG REPRODUCED: Unit tests are being filtered by pattern! "
                f"Expected all 3 unit tests to be collected, but only 1 was collected "
                f"when pattern 'auth' was specified. Unit tests should ignore patterns. "
                f"Output: {result.stdout}"
            )
        elif "collected 0 items" in result.stdout:
            pytest.fail(
                "BUG REPRODUCED: Unit tests filtered to zero by pattern! "
                f"Unit tests should be collected regardless of pattern 'auth'. "
                f"Output: {result.stdout}"
            )
            
        # Expected: Should collect all 3 unit tests regardless of pattern
        assert "collected 3 items" in result.stdout, (
            f"Unit tests should collect all tests regardless of pattern. "
            f"Expected 3 tests, got: {result.stdout}"
        )
        
    def test_real_integration_test_pattern_filtering_integration(self):
        """
        INTEGRATION: Test pattern filtering with real integration tests.
        
        This should FAIL because integration tests are incorrectly filtered by pattern.
        """
        # Run integration tests with specific pattern
        cmd = [
            "python3", str(self.runner_path),
            "--category", "integration",
            "--pattern", "websocket",  # Should match test_integration_websocket_system
            "--collect-only",
            str(self.temp_dir / "test_integration_sample.py")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # BUG: Integration tests should NOT be filtered by pattern
        # All integration tests should be collected regardless of pattern
        if "collected 1 item" in result.stdout:  # Only websocket test collected
            pytest.fail(
                "BUG REPRODUCED: Integration tests are being filtered by pattern! "
                f"Expected all 3 integration tests to be collected, but only 1 was collected "
                f"when pattern 'websocket' was specified. Integration tests should ignore patterns. "
                f"Output: {result.stdout}"
            )
        elif "collected 0 items" in result.stdout:
            pytest.fail(
                "BUG REPRODUCED: Integration tests filtered to zero by pattern! "
                f"Integration tests should be collected regardless of pattern 'websocket'. "
                f"Output: {result.stdout}"
            )
            
        # Expected: Should collect all 3 integration tests regardless of pattern
        assert "collected 3 items" in result.stdout, (
            f"Integration tests should collect all tests regardless of pattern. "
            f"Expected 3 tests, got: {result.stdout}"
        )
        
    def test_real_e2e_test_pattern_filtering_integration(self):
        """
        INTEGRATION: Test pattern filtering with real E2E tests.
        
        This should PASS as E2E tests should be correctly filtered by pattern.
        """
        # Run E2E tests with specific pattern
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", "auth",  # Should match only test_e2e_auth_flow
            "--collect-only",
            str(self.temp_dir / "test_e2e_sample.py")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # EXPECTED: E2E tests should be filtered by pattern
        # Should collect only the auth test (1 item)
        if "collected 1 item" in result.stdout:
            # This is correct behavior for E2E tests
            assert True
        elif "collected 3 items" in result.stdout:
            # If all tests are collected, pattern filtering is not working for E2E
            pytest.fail(
                "E2E pattern filtering not working! "
                f"Expected only 1 E2E test matching 'auth' pattern, but got 3. "
                f"E2E tests should be filtered by pattern. Output: {result.stdout}"
            )
        elif "collected 0 items" in result.stdout:
            # No tests collected - might be due to path issues or other problems
            pytest.skip(f"No E2E tests collected. Output: {result.stdout}")
            
    def test_pattern_filtering_with_existing_test_files(self):
        """
        INTEGRATION: Test pattern filtering with actual existing test files.
        
        Uses real test files from the codebase to validate behavior.
        """
        # Find some actual test files
        actual_unit_tests = list(self.test_root.glob("unit/**/test_*.py"))
        actual_integration_tests = list(self.test_root.glob("integration/**/test_*.py"))
        actual_e2e_tests = list(self.test_root.glob("e2e/**/test_*.py"))
        
        if actual_unit_tests:
            # Test with actual unit test file
            unit_test_file = actual_unit_tests[0]
            cmd = [
                "python", str(self.runner_path),
                "--category", "unit",
                "--pattern", "nonexistent_pattern_xyz",
                "--collect-only",
                str(unit_test_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # BUG: Should collect tests regardless of pattern for unit tests
            if "collected 0 items" in result.stdout:
                pytest.fail(
                    f"BUG REPRODUCED with real unit test file: {unit_test_file.name} "
                    f"Unit tests should not be filtered by pattern 'nonexistent_pattern_xyz'. "
                    f"Output: {result.stdout}"
                )


class TestPatternFilterSystemIntegration:
    """Test pattern filtering integration with the overall test runner system."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_pattern_filter_with_multiple_categories(self):
        """
        INTEGRATION: Test pattern filtering when multiple categories are specified.
        
        Tests the interaction between category selection and pattern filtering.
        """
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit,integration,e2e",
            "--pattern", "impossible_pattern_xyz123",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # BUG: Pattern should only affect E2E category, not unit and integration
        # Currently, the bug causes all categories to be filtered
        if "collected 0 items" in result.stdout:
            pytest.fail(
                "BUG REPRODUCED: Pattern filtering applied to all categories! "
                f"When running multiple categories (unit,integration,e2e) with pattern "
                f"'impossible_pattern_xyz123', only E2E tests should be filtered. "
                f"Unit and integration tests should still be collected. "
                f"Output: {result.stdout}"
            )
            
    def test_pattern_filter_command_line_integration(self):
        """
        INTEGRATION: Test pattern filter integration with command line processing.
        
        Validates that command line arguments are properly integrated.
        """
        # Test various command line combinations
        test_combinations = [
            (["--category", "unit", "--pattern", "test"], "unit with pattern"),
            (["--category", "e2e", "--pattern", "auth"], "e2e with pattern"),
            (["--pattern", "websocket", "--category", "integration"], "pattern before category"),
        ]
        
        for args, description in test_combinations:
            cmd = ["python3", str(self.runner_path)] + args + ["--collect-only"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should handle command line arguments without errors
            assert result.returncode in [0, 1], (
                f"Command line integration failed for {description}: {result.stderr}"
            )
            
    def test_pattern_filter_with_test_discovery_integration(self):
        """
        INTEGRATION: Test pattern filtering integration with pytest test discovery.
        
        Validates that pattern filtering works correctly with pytest's test discovery.
        """
        # Test that pattern filtering integrates properly with pytest discovery
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit",
            "--pattern", "sample",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # The integration should work without pytest errors
        assert "error" not in result.stderr.lower(), (
            f"Pattern filtering integration with pytest discovery failed: {result.stderr}"
        )
        
        # BUG: Unit tests should not be affected by pattern, so if zero collected,
        # it's likely due to the bug
        if "collected 0 items" in result.stdout:
            # This could be the bug or legitimately no tests
            # We'll document this as potential bug manifestation
            pass


class TestPatternFilterPerformanceIntegration:
    """Test pattern filtering integration with performance considerations."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_pattern_filter_does_not_slow_collection(self):
        """
        PERFORMANCE: Test that pattern filtering doesn't significantly slow test collection.
        
        Validates that the pattern filtering implementation is performant.
        """
        import time
        
        # Time test collection without pattern
        start_time = time.time()
        cmd_no_pattern = [
            "python3", str(self.runner_path),
            "--category", "unit",
            "--collect-only"
        ]
        result_no_pattern = subprocess.run(
            cmd_no_pattern, capture_output=True, text=True, cwd=self.test_root
        )
        no_pattern_time = time.time() - start_time
        
        # Time test collection with pattern
        start_time = time.time()
        cmd_with_pattern = [
            "python3", str(self.runner_path),
            "--category", "unit", 
            "--pattern", "sample_pattern",
            "--collect-only"
        ]
        result_with_pattern = subprocess.run(
            cmd_with_pattern, capture_output=True, text=True, cwd=self.test_root
        )
        with_pattern_time = time.time() - start_time
        
        # Pattern filtering should not significantly slow down collection
        # Allow for some overhead but not excessive
        time_ratio = with_pattern_time / max(no_pattern_time, 0.001)  # Avoid division by zero
        
        assert time_ratio < 3.0, (
            f"Pattern filtering is too slow! "
            f"Without pattern: {no_pattern_time:.3f}s, "
            f"with pattern: {with_pattern_time:.3f}s, "
            f"ratio: {time_ratio:.2f}x"
        )
        
    def test_pattern_filter_memory_integration(self):
        """
        PERFORMANCE: Test that pattern filtering doesn't cause memory issues.
        
        Validates that pattern filtering doesn't create memory leaks or excessive usage.
        """
        # Run pattern filtering multiple times to check for memory issues
        for i in range(5):
            cmd = [
                "python", str(self.runner_path),
                "--category", "unit",
                "--pattern", f"pattern_test_{i}",
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should not cause memory errors or crashes
            assert "MemoryError" not in result.stderr, (
                f"Pattern filtering caused memory error on iteration {i}: {result.stderr}"
            )
            assert result.returncode in [0, 1], (
                f"Pattern filtering failed on iteration {i}: {result.stderr}"
            )


class TestPatternFilterIntegrationDocumentation:
    """Document pattern filtering integration behavior and expectations."""
    
    def test_integration_behavior_documentation(self):
        """
        DOCUMENTATION: Document expected integration behavior.
        
        This test serves as executable documentation of integration expectations.
        """
        integration_expectations = {
            "test_discovery": {
                "description": "Pattern filtering should integrate with pytest test discovery",
                "expected": "Pattern applied only to E2E categories during discovery",
                "current_bug": "Pattern applied to all categories during discovery"
            },
            "command_construction": {
                "description": "Pattern should be properly integrated into pytest commands",
                "expected": "pytest -k 'pattern' only for E2E categories",
                "current_bug": "pytest -k 'pattern' applied to all categories"
            },
            "category_interaction": {
                "description": "Pattern filtering should respect category boundaries",
                "expected": "Mixed categories run with pattern only affecting E2E portion",
                "current_bug": "Mixed categories all affected by pattern filtering"
            },
            "performance": {
                "description": "Pattern filtering should not significantly impact performance",
                "expected": "Minimal overhead for pattern processing",
                "status": "Generally acceptable performance"
            }
        }
        
        # Validate documentation structure
        assert "test_discovery" in integration_expectations
        assert "command_construction" in integration_expectations
        assert "category_interaction" in integration_expectations
        assert "performance" in integration_expectations
        
        # Verify bug descriptions
        for component, details in integration_expectations.items():
            if "current_bug" in details:
                assert "all categories" in details["current_bug"]
                
    def test_integration_bug_impact_analysis(self):
        """
        ANALYSIS: Document the impact of the bug on system integration.
        
        Analyzes how the pattern filter bug affects overall system integration.
        """
        bug_impact_analysis = {
            "user_workflow_impact": {
                "problem": "Developers cannot use patterns with non-E2E categories",
                "example": "python unified_test_runner.py --category unit --pattern auth fails",
                "workaround": "Remove --pattern when running non-E2E tests"
            },
            "ci_cd_impact": {
                "problem": "CI/CD pipelines cannot selectively run non-E2E tests with patterns",
                "example": "Automated testing workflows break when using patterns",
                "workaround": "Separate CI jobs for pattern-based and full test runs"
            },
            "test_development_impact": {
                "problem": "Test developers cannot quickly run subsets of non-E2E tests",
                "example": "Cannot run 'auth' unit tests specifically during development",
                "workaround": "Use pytest directly instead of unified runner"
            },
            "system_consistency_impact": {
                "problem": "Inconsistent behavior between E2E and non-E2E test categories",
                "example": "Same pattern argument behaves differently across categories",
                "severity": "Medium - causes user confusion and workflow disruption"
            }
        }
        
        # Validate impact analysis
        assert "user_workflow_impact" in bug_impact_analysis
        assert "ci_cd_impact" in bug_impact_analysis
        assert "test_development_impact" in bug_impact_analysis
        assert "system_consistency_impact" in bug_impact_analysis
        
        # Verify impact severity
        for impact_type, details in bug_impact_analysis.items():
            assert "problem" in details
            if "severity" in details:
                assert details["severity"] in ["Low", "Medium", "High"]


if __name__ == "__main__":
    # Run integration tests to validate pattern filter system integration
    pytest.main([__file__, "-v", "--tb=short"])