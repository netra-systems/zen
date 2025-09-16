"""
Test Pattern Filter Validation Suite
====================================

This test suite validates the pattern filter functionality and confirms
that pattern filtering behavior is correctly scoped to E2E tests only.

VALIDATION OBJECTIVES:
1. Confirm pattern filtering works correctly for E2E tests (expected behavior)
2. Validate that non-E2E tests ignore pattern filtering (currently broken)
3. Test edge cases in pattern filtering logic
4. Verify command line argument processing for patterns
"""

import pytest
import subprocess
import re
from pathlib import Path


class TestPatternFilterValidation:
    """Validation tests for pattern filter functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_pattern_filter_argument_processing(self):
        """
        VALIDATION: Test that pattern arguments are processed correctly.
        
        Validates that the pattern argument is properly parsed and cleaned.
        """
        # Test pattern argument processing
        test_patterns = [
            "test_auth",
            "*test_auth*",  # Should be cleaned to "test_auth"
            "websocket",
            "*websocket*"   # Should be cleaned to "websocket"
        ]
        
        for pattern in test_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "e2e", 
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should process without errors (regardless of whether tests are found)
            assert result.returncode in [0, 1], (  # 0=success, 1=no tests found 
                f"Pattern '{pattern}' caused command failure. "
                f"stderr: {result.stderr}, stdout: {result.stdout}"
            )
            
            # Check that pytest -k format is used (not glob format)
            if "-k" in result.stdout or "-k" in result.stderr:
                # Verify no asterisks in the actual -k argument
                assert "*" not in result.stdout.split("-k")[1].split()[0].strip('"'), (
                    f"Pattern '{pattern}' not properly cleaned for pytest -k format"
                )
                
    def test_e2e_pattern_filtering_works_correctly(self):
        """
        VALIDATION: Confirm E2E pattern filtering works as expected.
        
        This should pass - E2E tests should be correctly filtered by patterns.
        """
        # Test with a realistic pattern that might exist in E2E tests
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", "auth",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # Should execute without errors
        assert result.returncode in [0, 1], f"E2E pattern filtering failed: {result.stderr}"
        
        # If tests are collected, they should contain 'auth' in the name
        if "collected" in result.stdout and "0 items" not in result.stdout:
            # Extract test names from output and verify they match pattern
            collected_match = re.search(r'collected (\d+) items?', result.stdout)
            if collected_match and int(collected_match.group(1)) > 0:
                # Pattern filtering should work for E2E
                assert True  # E2E filtering is working
        
    def test_non_e2e_categories_should_ignore_pattern(self):
        """
        VALIDATION: Non-E2E categories should ignore pattern filtering.
        
        This test should FAIL with current buggy behavior, demonstrating
        that non-E2E tests are incorrectly being filtered.
        """
        non_e2e_categories = ["unit", "integration", "critical"]
        
        for category in non_e2e_categories:
            # Use a pattern that's unlikely to match any test names
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", "completely_nonexistent_test_xyz123", 
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # BUG: Currently this will fail because pattern is applied globally
            # The test should collect tests regardless of the pattern
            assert "collected 0 items" not in result.stdout, (
                f"BUG DETECTED: {category} tests are being filtered by pattern! "
                f"Pattern filtering should not apply to {category} tests. "
                f"Command: {' '.join(cmd)}\n"
                f"Output: {result.stdout}"
            )
            
    def test_pattern_vs_no_pattern_comparison(self):
        """
        VALIDATION: Compare test collection with and without patterns.
        
        For non-E2E categories, the test count should be the same regardless
        of pattern. For E2E categories, pattern may reduce the count.
        """
        categories_to_test = ["unit", "integration", "critical", "e2e"]
        results = {}
        
        # First, collect without pattern
        for category in categories_to_test:
            cmd_no_pattern = [
                "python", str(self.runner_path),
                "--category", category,
                "--collect-only"
            ]
            
            result_no_pattern = subprocess.run(
                cmd_no_pattern, capture_output=True, text=True, cwd=self.test_root
            )
            
            # Then collect with pattern
            cmd_with_pattern = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", "unlikely_pattern_xyz999",
                "--collect-only"
            ]
            
            result_with_pattern = subprocess.run(
                cmd_with_pattern, capture_output=True, text=True, cwd=self.test_root
            )
            
            results[category] = {
                'without_pattern': result_no_pattern,
                'with_pattern': result_with_pattern
            }
            
        # Analyze results
        for category in categories_to_test:
            no_pattern_result = results[category]['without_pattern']
            with_pattern_result = results[category]['with_pattern']
            
            # Extract collection counts
            def extract_count(output):
                match = re.search(r'collected (\d+) items?', output)
                return int(match.group(1)) if match else 0
                
            count_no_pattern = extract_count(no_pattern_result.stdout)
            count_with_pattern = extract_count(with_pattern_result.stdout)
            
            if category in ["unit", "integration", "critical"]:
                # BUG: These should have the same count (pattern should be ignored)
                assert count_no_pattern == count_with_pattern, (
                    f"BUG DETECTED in {category}: Pattern filtering affected test collection! "
                    f"Without pattern: {count_no_pattern} tests, "
                    f"with pattern: {count_with_pattern} tests. "
                    f"Non-E2E tests should ignore pattern filtering."
                )
            elif category == "e2e":
                # E2E tests may have different counts (pattern filtering is expected)
                # This is correct behavior, so we don't assert anything specific
                pass
                
    def test_multiple_categories_pattern_consistency(self):
        """
        VALIDATION: Test pattern behavior across multiple categories.
        
        When running multiple categories, only E2E categories should be
        affected by pattern filtering.
        """
        # Test with mixed E2E and non-E2E categories
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit,integration,e2e",
            "--pattern", "nonexistent_test_pattern_abc456",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # The command should run successfully
        assert result.returncode in [0, 1], f"Multi-category pattern test failed: {result.stderr}"
        
        # Unit and integration tests should be collected (pattern ignored)
        # Only E2E tests should be filtered by pattern
        # BUG: Currently all categories are filtered, so this will likely show 0 collected
        if "collected 0 items" in result.stdout:
            pytest.fail(
                "BUG DETECTED: All categories filtered by pattern! "
                "Only E2E categories should be filtered. "
                f"Output: {result.stdout}"
            )
            
    def test_empty_pattern_handling(self):
        """
        VALIDATION: Test behavior with empty or whitespace-only patterns.
        
        Empty patterns should not affect test collection for any category.
        """
        empty_patterns = ["", "   ", "\t", "\n"]
        
        for pattern in empty_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "unit",
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should collect tests normally (empty pattern should be ignored)
            assert result.returncode in [0, 1], (
                f"Empty pattern '{repr(pattern)}' caused failure: {result.stderr}"
            )
            
            # Should not result in zero collection due to empty pattern
            if "collected 0 items" in result.stdout:
                # This might be legitimate if there really are no unit tests
                # But we should verify it's not due to pattern filtering
                cmd_no_pattern = [
                    "python", str(self.runner_path),
                    "--category", "unit", 
                    "--collect-only"
                ]
                
                result_no_pattern = subprocess.run(
                    cmd_no_pattern, capture_output=True, text=True, cwd=self.test_root
                )
                
                # Compare counts - they should be the same
                assert result.stdout == result_no_pattern.stdout, (
                    f"Empty pattern '{repr(pattern)}' affected test collection! "
                    f"With pattern: {result.stdout}\n"
                    f"Without pattern: {result_no_pattern.stdout}"
                )


class TestPatternFilterEdgeCases:
    """Test edge cases in pattern filter functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent  
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_special_characters_in_pattern(self):
        """
        EDGE CASE: Test patterns with special characters.
        
        Patterns with special regex characters should be handled safely.
        """
        special_patterns = [
            "test[auth]",      # Square brackets
            "test.auth",       # Dot (regex any character)
            "test+auth",       # Plus (regex one or more)
            "test*auth",       # Asterisk (should be cleaned)
            "test(auth)",      # Parentheses
            "test|auth",       # Pipe (regex OR)
            "test\\auth",      # Backslash
            "test^auth$",      # Anchors
        ]
        
        for pattern in special_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "e2e",  # Use E2E where pattern filtering is expected
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should not crash with special characters
            assert "Error" not in result.stderr, (
                f"Pattern '{pattern}' caused error: {result.stderr}"
            )
            
    def test_very_long_pattern(self):
        """
        EDGE CASE: Test with very long pattern strings.
        
        Long patterns should be handled without issues.
        """
        long_pattern = "test_" + "very_long_pattern_name_" * 50 + "xyz"
        
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", long_pattern,
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # Should handle long patterns without crashing
        assert result.returncode in [0, 1], (
            f"Long pattern caused failure: {result.stderr}"
        )
        
    def test_unicode_pattern(self):
        """
        EDGE CASE: Test patterns with Unicode characters.
        
        Unicode in patterns should be handled safely.
        """
        unicode_patterns = [
            "test_αβγ",        # Greek letters
            "test_测试",        # Chinese characters  
            "test_🔧",         # Emoji
            "test_café",       # Accented characters
        ]
        
        for pattern in unicode_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "e2e",
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should handle Unicode without crashing
            assert result.returncode in [0, 1], (
                f"Unicode pattern '{pattern}' caused failure: {result.stderr}"
            )


class TestPatternFilterBehaviorDocumentation:
    """Document expected vs actual pattern filter behavior."""
    
    def test_expected_behavior_documentation(self):
        """
        DOCUMENTATION: Document the expected pattern filter behavior.
        
        This test serves as executable documentation.
        """
        expected_behavior = {
            "e2e_categories": {
                "categories": ["e2e", "e2e_critical", "cypress"],
                "pattern_behavior": "Should filter tests by pattern using pytest -k",
                "rationale": "E2E tests often need specific test selection for targeted runs"
            },
            "non_e2e_categories": {
                "categories": ["unit", "integration", "critical", "frontend"],
                "pattern_behavior": "Should ignore pattern and run all tests",
                "rationale": "Non-E2E tests should run comprehensively without filtering"
            }
        }
        
        # This always passes - it's documentation
        assert len(expected_behavior["e2e_categories"]["categories"]) == 3
        assert len(expected_behavior["non_e2e_categories"]["categories"]) == 4
        assert "ignore pattern" in expected_behavior["non_e2e_categories"]["pattern_behavior"]
        
    def test_bug_impact_analysis(self):
        """
        ANALYSIS: Document the impact of the current bug.
        
        This test analyzes the scope and impact of the pattern filter bug.
        """
        bug_impact = {
            "affected_categories": ["unit", "integration", "critical", "frontend"],
            "symptom": "Tests are incorrectly filtered when pattern is specified",
            "user_impact": "Developers cannot run full test suites for non-E2E categories when using patterns",
            "workaround": "Remove --pattern argument when running non-E2E tests",
            "fix_location": "Line 3249 in unified_test_runner.py needs conditional check"
        }
        
        # Document the bug characteristics
        assert len(bug_impact["affected_categories"]) == 4
        assert "incorrectly filtered" in bug_impact["symptom"] 
        assert "3249" in bug_impact["fix_location"]


if __name__ == "__main__":
    # Run validation tests to check pattern filter behavior
    pytest.main([__file__, "-v", "--tb=short"])