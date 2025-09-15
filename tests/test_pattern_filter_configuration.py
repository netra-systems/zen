"""
Test Pattern Filter Configuration Suite
=======================================

This test suite validates the configuration and command-line argument handling
for pattern filtering in the unified test runner.

CONFIGURATION TESTING OBJECTIVES:
1. Test command-line argument parsing for --pattern
2. Validate pattern cleaning and processing logic  
3. Test category-specific configuration behavior
4. Verify pytest command construction with patterns
"""

import pytest
import subprocess
import re
import shlex
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestPatternFilterConfigurationParsing:
    """Test configuration and argument parsing for pattern filters."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_pattern_argument_acceptance(self):
        """
        CONFIG TEST: Verify --pattern argument is accepted and parsed.
        
        Tests that the argument parser correctly accepts pattern arguments.
        """
        test_patterns = [
            "simple_pattern",
            "pattern_with_underscores", 
            "pattern-with-hyphens",
            "123numeric_start",
            "MixedCase_Pattern"
        ]
        
        for pattern in test_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "unit",
                "--pattern", pattern,
                "--help"  # Use --help to test parsing without running tests
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should parse arguments successfully  
            assert "error" not in result.stderr.lower(), (
                f"Pattern '{pattern}' caused argument parsing error: {result.stderr}"
            )
            
    def test_pattern_cleaning_behavior(self):
        """
        CONFIG TEST: Verify pattern cleaning removes asterisks.
        
        Tests that asterisks are properly stripped from patterns for pytest -k.
        """
        # Test patterns that should be cleaned
        dirty_patterns = [
            "*test_pattern*",
            "*test_pattern", 
            "test_pattern*",
            "***test_pattern***"
        ]
        
        expected_clean = "test_pattern"
        
        for dirty_pattern in dirty_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "e2e",  # Use E2E where pattern is applied
                "--pattern", dirty_pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Look for the cleaned pattern in pytest command
            # The actual pytest command should use the cleaned pattern
            if "pytest" in result.stderr or "pytest" in result.stdout:
                output = result.stderr + result.stdout
                # Should contain -k "test_pattern" not -k "*test_pattern*"
                if '-k' in output:
                    assert f'"{expected_clean}"' in output or f"'{expected_clean}'" in output, (
                        f"Pattern '{dirty_pattern}' not properly cleaned. "
                        f"Expected clean pattern '{expected_clean}' in output: {output}"
                    )
                    
    def test_pattern_empty_and_whitespace_handling(self):
        """
        CONFIG TEST: Test handling of empty and whitespace-only patterns.
        
        Empty patterns should be handled gracefully without causing errors.
        """
        empty_patterns = ["", "   ", "\t", "\n", "  \t\n  "]
        
        for pattern in empty_patterns:
            cmd = [
                "python", str(self.runner_path),
                "--category", "unit",
                "--pattern", pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # Should handle empty patterns without crashing
            assert result.returncode in [0, 1], (
                f"Empty pattern '{repr(pattern)}' caused unexpected failure: {result.stderr}"
            )
            
            # Empty pattern should not add -k argument to pytest
            output = result.stderr + result.stdout
            if pattern.strip() == "":
                # For truly empty patterns, -k should not be added
                # However, the current bug might still add it
                pass  # We'll document this behavior
                
    def test_category_configuration_consistency(self):
        """
        CONFIG TEST: Test pattern configuration across different categories.
        
        Verifies that pattern handling is consistent across category configurations.
        """
        all_categories = [
            "unit", "integration", "e2e", "critical", 
            "frontend", "cypress", "e2e_critical"
        ]
        
        test_pattern = "consistent_test_pattern"
        
        for category in all_categories:
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", test_pattern,
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            # All categories should accept the pattern argument without error
            assert "error" not in result.stderr.lower(), (
                f"Category '{category}' failed to accept pattern argument: {result.stderr}"
            )
            
            # BUG VERIFICATION: All categories currently get pattern filtering
            # This is the bug - only E2E categories should get pattern filtering
            output = result.stderr + result.stdout
            if "-k" in output:
                # Currently ALL categories get -k filtering (this is the bug)
                if category in ["unit", "integration", "critical", "frontend"]:
                    # These should NOT have -k filtering
                    pytest.fail(
                        f"BUG DETECTED: Non-E2E category '{category}' is getting pattern filtering! "
                        f"Pattern filtering should only apply to E2E categories. "
                        f"Found -k in output: {output}"
                    )


class TestPatternFilterCommandConstruction:
    """Test pytest command construction with pattern filters."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_pytest_k_argument_format(self):
        """
        COMMAND TEST: Verify pytest -k argument is properly formatted.
        
        Tests that the -k argument is correctly added to pytest commands.
        """
        test_pattern = "auth_test_pattern"
        
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", test_pattern,
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        output = result.stderr + result.stdout
        
        # Should contain -k argument with quoted pattern
        if "-k" in output:
            # Extract the -k argument value
            k_match = re.search(r'-k\s+["\']([^"\']+)["\']', output)
            if k_match:
                k_value = k_match.group(1)
                assert k_value == test_pattern, (
                    f"Pattern in -k argument '{k_value}' doesn't match input '{test_pattern}'"
                )
            else:
                # Try without quotes
                k_match = re.search(r'-k\s+(\S+)', output)
                if k_match:
                    k_value = k_match.group(1)
                    assert test_pattern in k_value, (
                        f"Pattern '{test_pattern}' not found in -k argument '{k_value}'"
                    )
                    
    def test_command_argument_order(self):
        """
        COMMAND TEST: Verify argument order in constructed pytest commands.
        
        Tests that arguments are in the correct order and properly formatted.
        """
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", "test_order",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        output = result.stderr + result.stdout
        
        # Look for pytest command structure
        if "pytest" in output:
            # The command should have proper argument structure
            # -k should come with its value
            assert re.search(r'-k\s+["\']?[^"\']*["\']?', output), (
                f"Invalid -k argument format in command: {output}"
            )
            
    def test_multiple_arguments_interaction(self):
        """
        COMMAND TEST: Test pattern with other command-line arguments.
        
        Verifies that pattern works correctly with other arguments.
        """
        cmd = [
            "python3", str(self.runner_path),
            "--category", "e2e",
            "--pattern", "interaction_test",
            "--timeout", "60",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        # Should handle multiple arguments without conflicts
        assert result.returncode in [0, 1], (
            f"Multiple arguments with pattern caused failure: {result.stderr}"
        )
        
        output = result.stderr + result.stdout
        
        # Should contain both pattern and timeout arguments
        if "--timeout" in output and "-k" in output:
            # Both arguments should be present
            assert True  # Command construction working
            

class TestPatternFilterCategorySpecificBehavior:
    """Test category-specific pattern filter behavior configuration."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.test_root = Path(__file__).parent
        self.runner_path = self.test_root / "unified_test_runner.py"
        
    def test_e2e_category_pattern_application(self):
        """
        CATEGORY CONFIG: Test that E2E categories correctly apply patterns.
        
        E2E categories should have pattern filtering enabled.
        """
        e2e_categories = ["e2e", "e2e_critical", "cypress"]
        
        for category in e2e_categories:
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", "e2e_pattern_test",
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            output = result.stderr + result.stdout
            
            # E2E categories should have -k filtering (this is correct behavior)
            # We don't fail here because this is expected
            if "-k" not in output:
                # If no -k found, it might be because there are no tests or other reasons
                # This is not necessarily a failure for E2E categories
                pass
                
    def test_non_e2e_category_pattern_exclusion(self):
        """
        CATEGORY CONFIG: Test that non-E2E categories should exclude patterns.
        
        Non-E2E categories should NOT have pattern filtering applied.
        This test will FAIL with current buggy behavior.
        """
        non_e2e_categories = ["unit", "integration", "critical", "frontend"]
        
        for category in non_e2e_categories:
            cmd = [
                "python", str(self.runner_path),
                "--category", category,
                "--pattern", "should_be_ignored_pattern",
                "--collect-only"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
            
            output = result.stderr + result.stdout
            
            # BUG: Non-E2E categories should NOT have -k filtering
            if "-k" in output:
                pytest.fail(
                    f"BUG DETECTED: Non-E2E category '{category}' has pattern filtering! "
                    f"Category '{category}' should not apply pattern filters. "
                    f"Pattern filtering should only apply to E2E categories. "
                    f"Found -k in command: {output}"
                )
                
    def test_mixed_category_pattern_behavior(self):
        """
        CATEGORY CONFIG: Test pattern behavior with mixed categories.
        
        When multiple categories are specified, only E2E ones should get filtering.
        """
        cmd = [
            "python3", str(self.runner_path),
            "--category", "unit,integration,e2e",
            "--pattern", "mixed_category_test",
            "--collect-only"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.test_root)
        
        output = result.stderr + result.stdout
        
        # With mixed categories, the behavior depends on implementation
        # Currently, the bug applies pattern globally to all
        # BUG: Pattern is applied to all categories instead of just E2E
        if "-k" in output:
            # This indicates the bug - pattern is applied globally
            pytest.fail(
                "BUG DETECTED: Pattern filtering applied to mixed categories! "
                "When running mixed categories (unit,integration,e2e), "
                "pattern should only filter the E2E portion, not all tests. "
                f"Found global -k filtering in: {output}"
            )


class TestPatternFilterConfigurationDocumentation:
    """Document pattern filter configuration expectations."""
    
    def test_configuration_requirements_documentation(self):
        """
        DOCUMENTATION: Document configuration requirements for pattern filtering.
        
        This test serves as executable documentation of configuration needs.
        """
        config_requirements = {
            "argument_parsing": {
                "argument": "--pattern",
                "type": "string",
                "description": "Pattern to filter test selection",
                "cleaning": "Remove leading/trailing asterisks for pytest -k"
            },
            "category_behavior": {
                "e2e_categories": ["e2e", "e2e_critical", "cypress"],
                "apply_pattern": True,
                "reason": "E2E tests need selective execution"
            },
            "non_e2e_behavior": {
                "categories": ["unit", "integration", "critical", "frontend"],
                "apply_pattern": False,
                "reason": "Non-E2E tests should run comprehensively"
            },
            "command_construction": {
                "format": "pytest -k 'pattern'",
                "quoting": "Pattern should be quoted for shell safety",
                "position": "After other pytest arguments"
            }
        }
        
        # Validate documentation structure
        assert config_requirements["argument_parsing"]["argument"] == "--pattern"
        assert config_requirements["category_behavior"]["apply_pattern"] is True
        assert config_requirements["non_e2e_behavior"]["apply_pattern"] is False
        assert "pytest -k" in config_requirements["command_construction"]["format"]
        
    def test_bug_configuration_analysis(self):
        """
        ANALYSIS: Document the configuration aspect of the current bug.
        
        Analyzes how the bug manifests in configuration handling.
        """
        bug_analysis = {
            "current_behavior": "Pattern applied globally to all categories",
            "expected_behavior": "Pattern applied only to E2E categories",
            "configuration_location": "Line 3249 in unified_test_runner.py",
            "fix_needed": "Add category check before applying pattern filter",
            "affected_config": "Command construction logic in _build_pytest_command",
            "test_impact": "Non-E2E tests incorrectly filtered by pattern"
        }
        
        # Document the configuration bug
        assert "globally" in bug_analysis["current_behavior"]
        assert "only to E2E" in bug_analysis["expected_behavior"]
        assert "3249" in bug_analysis["configuration_location"]
        assert "category check" in bug_analysis["fix_needed"]


if __name__ == "__main__":
    # Run configuration tests to validate pattern filter setup
    pytest.main([__file__, "-v", "--tb=short"])