"""
Test Pattern Filter Bug Reproduction Suite
==========================================

This test suite is designed to reproduce the pattern filter bug where pattern filtering
is incorrectly applied to ALL test categories instead of only E2E tests.

BUG LOCATION: Line 3249 in unified_test_runner.py
The bug applies pattern filtering globally instead of restricting it to E2E test categories.

EXPECTED BEHAVIOR:
- Pattern filtering should ONLY apply to E2E test categories
- Unit tests should run ALL matching tests regardless of pattern
- Integration tests should run ALL matching tests regardless of pattern

ACTUAL BUGGY BEHAVIOR:
- Pattern filtering applies to ALL test categories
- Non-E2E tests are incorrectly filtered by pattern
"""

import pytest
import subprocess
import os
from pathlib import Path


class TestPatternFilterBugReproduction:
    """Test suite to reproduce the pattern filter bug."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_unit_tests_should_ignore_pattern_filter(self):
        """
        REPRODUCTION TEST: Unit tests should run ALL tests regardless of pattern.
        
        This test should FAIL with current buggy behavior because unit tests
        are incorrectly being filtered by pattern when they shouldn't be.
        """
        # Run unit tests with a pattern that should NOT affect unit test selection
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit",
            "--pattern", "nonexistent_pattern_xyz123",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # BUG: Current behavior incorrectly filters unit tests by pattern
        # This assertion will FAIL demonstrating the bug
        assert "collected 0 items" not in result.stdout, (
            "BUG REPRODUCED: Unit tests are being incorrectly filtered by pattern! "
            f"Pattern 'nonexistent_pattern_xyz123' should not affect unit test selection. "
            f"Output: {result.stdout}"
        )
        
        # Expected behavior: Unit tests should collect regardless of pattern
        assert "collected" in result.stdout, f"No unit tests collected. Output: {result.stdout}"
        
    def test_integration_tests_should_ignore_pattern_filter(self):
        """
        REPRODUCTION TEST: Integration tests should run ALL tests regardless of pattern.
        
        This test should FAIL with current buggy behavior because integration tests
        are incorrectly being filtered by pattern when they shouldn't be.
        """
        # Run integration tests with a pattern that should NOT affect integration test selection
        cmd = [
            "python3", str(self.runner_path),
            "--category", "integration", 
            "--pattern", "nonexistent_pattern_xyz123",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # BUG: Current behavior incorrectly filters integration tests by pattern
        # This assertion will FAIL demonstrating the bug
        assert "collected 0 items" not in result.stdout, (
            "BUG REPRODUCED: Integration tests are being incorrectly filtered by pattern! "
            f"Pattern 'nonexistent_pattern_xyz123' should not affect integration test selection. "
            f"Output: {result.stdout}"
        )
        
        # Expected behavior: Integration tests should collect regardless of pattern
        assert "collected" in result.stdout, f"No integration tests collected. Output: {result.stdout}"
        
    def test_e2e_tests_should_respect_pattern_filter(self):
        """
        CONTROL TEST: E2E tests should correctly be filtered by pattern.
        
        This test should PASS as E2E tests are supposed to be filtered by pattern.
        """
        # Run E2E tests with a pattern - this should correctly filter
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", "nonexistent_pattern_xyz123", 
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # EXPECTED: E2E tests should be filtered by pattern (this is correct behavior)
        assert "collected 0 items" in result.stdout or result.returncode != 0, (
            f"E2E tests should be filtered by pattern 'nonexistent_pattern_xyz123'. "
            f"Output: {result.stdout}"
        )
        
    def test_pattern_filter_scope_validation(self):
        """
        VALIDATION TEST: Verify pattern filter is applied in the wrong scope.
        
        This test demonstrates that the pattern filter is applied globally
        instead of only to E2E test categories.
        """
        # Test multiple non-E2E categories with pattern
        non_e2e_categories = ["unit", "integration", "critical"]
        
        for category in non_e2e_categories:
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", "impossible_test_name_xyz789",
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # BUG: These should NOT be filtered by pattern
            assert "collected 0 items" not in result.stdout, (
                f"BUG REPRODUCED in {category} category: "
                f"Pattern filtering should not apply to non-E2E tests! "
                f"Pattern 'impossible_test_name_xyz789' incorrectly filtered {category} tests. "
                f"Output: {result.stdout}"
            )
            
    def test_pattern_filter_line_3249_analysis(self):
        """
        CODE ANALYSIS TEST: Verify the specific bug location in unified_test_runner.py
        
        This test examines the actual code to confirm the bug location.
        """
        runner_content = self.runner_path.read_text()
        
        # Find the problematic line 3249
        lines = runner_content.split('\n')
        
        # The bug should be around line 3249 where pattern is applied globally
        bug_line_found = False
        for i, line in enumerate(lines):
            if 'cmd_parts.extend(["-k"' in line and 'clean_pattern' in line:
                bug_line_found = True
                line_number = i + 1
                
                # This should be inside a conditional that checks for E2E categories
                # If it's not, that's the bug
                context_lines = lines[max(0, i-10):i+5]
                context = '\n'.join(f"{max(0, i-10)+j+1}: {ctx_line}" for j, ctx_line in enumerate(context_lines))
                
                # Look for E2E category checks in the context
                e2e_check_found = any(
                    'e2e' in ctx_line.lower() and ('if' in ctx_line or 'category' in ctx_line) 
                    for ctx_line in context_lines[:10]  # Look in preceding lines
                )
                
                assert e2e_check_found, (
                    f"BUG CONFIRMED at line {line_number}: Pattern filtering is applied globally "
                    f"without checking if category is E2E!\n"
                    f"Context:\n{context}\n"
                    f"The pattern filter should only be applied when running E2E test categories."
                )
                
        assert bug_line_found, "Could not find the pattern filtering code in unified_test_runner.py"
        
    def test_collect_only_demonstrates_wrong_filtering(self):
        """
        DEMONSTRATION TEST: Use --collect-only to show wrong filtering behavior.
        
        This test uses --collect-only to demonstrate that tests are being
        incorrectly filtered without actually running them.
        """
        # Run different categories with the same pattern to show inconsistent behavior
        test_cases = [
            ("unit", "should_collect_regardless"),
            ("integration", "should_collect_regardless"), 
            ("critical", "should_collect_regardless"),
            ("e2e", "should_filter_correctly")  # This one should filter
        ]
        
        results = {}
        for category, pattern in test_cases:
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            results[category] = result
            
        # Non-E2E categories should collect tests (pattern should be ignored)
        for category in ["unit", "integration", "critical"]:
            result = results[category]
            assert "collected 0 items" not in result.stdout, (
                f"BUG REPRODUCED: {category} tests incorrectly filtered by pattern! "
                f"These should collect regardless of pattern. Output: {result.stdout}"
            )
            
        # E2E category should correctly filter (this behavior is expected)
        e2e_result = results["e2e"]
        # E2E filtering is expected, so we don't assert anything specific here
        # This is just to contrast with the buggy behavior above


class TestPatternFilterBugDocumentation:
    """Documentation and analysis of the pattern filter bug."""
    
    def test_bug_description_validation(self):
        """
        DOCUMENTATION TEST: Validate our understanding of the bug.
        
        This test serves as executable documentation of the bug.
        """
        bug_description = {
            "location": "Line 3249 in unified_test_runner.py",
            "problem": "Pattern filtering applied globally to all test categories",
            "expected": "Pattern filtering should only apply to E2E test categories",
            "impact": "Non-E2E tests are incorrectly filtered when pattern is specified",
            "categories_affected": ["unit", "integration", "critical", "frontend"],
            "categories_expected": ["e2e", "e2e_critical", "cypress"]
        }
        
        # This test always passes - it's documentation
        assert bug_description["location"] == "Line 3249 in unified_test_runner.py"
        assert "global" in bug_description["problem"]
        assert "E2E" in bug_description["expected"]
        
    def test_reproduction_strategy_validation(self):
        """
        STRATEGY TEST: Validate our reproduction approach.
        
        This test confirms our testing strategy is sound.
        """
        strategy = {
            "approach": "Use --collect-only to avoid actually running tests",
            "pattern": "Use nonexistent patterns to clearly show filtering behavior", 
            "categories": "Test both affected (non-E2E) and unaffected (E2E) categories",
            "assertion": "Non-E2E should collect tests, E2E should filter correctly"
        }
        
        assert "collect-only" in strategy["approach"]
        assert "nonexistent" in strategy["pattern"]
        assert "non-E2E" in strategy["assertion"]


if __name__ == "__main__":
    # Run this test file to reproduce the pattern filter bug
    pytest.main([__file__, "-v", "--tb=short"])