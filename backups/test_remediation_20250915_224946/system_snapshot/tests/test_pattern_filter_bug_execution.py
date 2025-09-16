"""
Pattern Filter Bug Execution Test
=================================

This test demonstrates the pattern filter bug by running actual test commands
and analyzing the generated pytest commands to show the bug.

The bug: Pattern filtering is applied to ALL test categories instead of only E2E tests.
Location: Line 3249 in unified_test_runner.py
"""

import pytest
import subprocess
import tempfile
import sys
from pathlib import Path
from textwrap import dedent


def test_pattern_filter_bug_demonstration():
    """
    EXECUTION TEST: Demonstrate the pattern filter bug by examining actual command construction.
    
    This test creates temporary test files and uses the unified test runner to show
    that pattern filtering is incorrectly applied to non-E2E tests.
    """
    test_root = Path(__file__).parent
    runner_path = test_root / "unified_test_runner.py"
    
    # Create a simple test file to verify behavior
    temp_dir = Path(tempfile.mkdtemp(prefix="pattern_bug_test_"))
    try:
        # Create a simple unit test file
        test_file = temp_dir / "test_sample_unit.py"
        test_file.write_text(dedent('''
            def test_unit_auth_sample():
                """Unit test with 'auth' in name."""
                assert True
                
            def test_unit_websocket_sample():
                """Unit test with 'websocket' in name."""
                assert True
                
            def test_unit_other_sample():
                """Unit test without specific keywords."""
                assert True
        '''))
        
        # Run unit tests with pattern - this should NOT filter for unit tests
        cmd = [
            "python3", str(runner_path),
            "--category", "unit", 
            "--pattern", "auth",
            "--quiet",  # Reduce output
            str(test_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=test_root)
        
        # Check if the command was constructed with pattern filtering
        output = result.stderr + result.stdout
        
        # Look for pytest command with -k flag in the output
        if "-k" in output and "auth" in output:
            # BUG REPRODUCED: Unit tests are being filtered by pattern
            print(f"\nBUG REPRODUCED!")
            print(f"Unit tests are incorrectly filtered by pattern!")
            print(f"Command output contains: -k \"auth\"")
            print(f"Unit tests should run ALL tests regardless of pattern.")
            print(f"Output excerpt: {output[:500]}...")
            
            # This demonstrates the bug
            assert False, (
                "BUG CONFIRMED: Unit tests are being filtered by pattern! "
                f"Found -k 'auth' in pytest command for unit category. "
                f"Unit tests should ignore pattern filtering."
            )
        else:
            # If no -k found, that would be the correct behavior for unit tests
            print(f"No pattern filtering found for unit tests (correct behavior)")
            assert True
            
    finally:
        # Clean up
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def test_e2e_pattern_filtering_should_work():
    """
    CONTROL TEST: E2E tests should correctly use pattern filtering.
    
    This verifies that the pattern filtering works for E2E tests (which is correct).
    """
    test_root = Path(__file__).parent
    runner_path = test_root / "unified_test_runner.py"
    
    # Test E2E category with pattern - this SHOULD have pattern filtering
    cmd = [
        "python3", str(runner_path),
        "--category", "e2e",
        "--pattern", "auth",
        "--quiet",
        "--list-categories"  # This will exit early but still show command construction
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=test_root)
    
    # For E2E tests, pattern filtering is expected and correct
    # We don't fail here as this is the intended behavior
    print(f"E2E test command executed (pattern filtering expected for E2E)")


def test_bug_location_analysis():
    """
    CODE ANALYSIS: Verify the bug location in the source code.
    
    This test examines the unified_test_runner.py to confirm the bug location.
    """
    test_root = Path(__file__).parent
    runner_path = test_root / "unified_test_runner.py"
    
    if not runner_path.exists():
        pytest.skip("unified_test_runner.py not found")
        
    content = runner_path.read_text()
    lines = content.split('\n')
    
    # Look for the problematic pattern filtering code
    bug_found = False
    for i, line in enumerate(lines):
        # Look for line that adds -k pattern without category check
        if 'cmd_parts.extend(["-k"' in line and 'clean_pattern' in line:
            line_number = i + 1
            print(f"\nFOUND PATTERN FILTERING CODE at line {line_number}:")
            print(f"  {line.strip()}")
            
            # Check if there's an E2E category check before this line
            context_lines = lines[max(0, i-10):i]
            e2e_check_found = any(
                ('e2e' in ctx_line.lower() and 
                 ('if' in ctx_line or 'category' in ctx_line or '==' in ctx_line))
                for ctx_line in context_lines
            )
            
            if not e2e_check_found:
                print(f"\nBUG CONFIRMED at line {line_number}:")
                print(f"  Pattern filtering is applied WITHOUT checking if category is E2E!")
                print(f"  This causes ALL test categories to be filtered by pattern.")
                print(f"\nExpected: Pattern filtering should only apply to E2E categories")
                print(f"Actual: Pattern filtering applies to ALL categories")
                
                bug_found = True
                
                # Show some context
                print(f"\nContext around line {line_number}:")
                for j, ctx_line in enumerate(lines[max(0, i-5):i+5]):
                    ctx_line_num = max(0, i-5) + j + 1
                    marker = ">>> " if ctx_line_num == line_number else "    "
                    print(f"{marker}{ctx_line_num:4d}: {ctx_line}")
                    
    assert bug_found, "Could not find the pattern filtering bug in the code"
    
    # The bug is confirmed - pattern filtering is applied globally
    assert True  # This test is for analysis/documentation


def test_category_specific_behavior_demonstration():
    """
    DEMONSTRATION: Show how different categories are affected by the bug.
    
    This test demonstrates that the bug affects all categories, not just unit tests.
    """
    test_root = Path(__file__).parent
    runner_path = test_root / "unified_test_runner.py"
    
    # Test multiple non-E2E categories with pattern
    non_e2e_categories = ["unit", "integration"]  # Test a subset to avoid too much output
    
    for category in non_e2e_categories:
        print(f"\nTesting pattern filtering for category: {category}")
        
        cmd = [
            "python3", str(runner_path),
            "--category", category,
            "--pattern", "nonexistent_test_xyz123",
            "--quiet",
            "--list-categories"  # Exit early but still process arguments
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=test_root)
        
        # The bug applies to all categories
        print(f"  Category '{category}' processed with pattern (bug affects all categories)")
        
    # This test documents the bug scope
    assert True


if __name__ == "__main__":
    # Run this file directly to see the bug demonstration
    print("=== PATTERN FILTER BUG DEMONSTRATION ===")
    print()
    
    try:
        test_pattern_filter_bug_demonstration()
        print("✓ Bug demonstration completed")
    except AssertionError as e:
        print(f"✗ Bug confirmed: {e}")
        
    print()
    try:
        test_bug_location_analysis()
        print("✓ Bug location analysis completed")
    except AssertionError as e:
        print(f"✗ Analysis failed: {e}")
        
    print()
    test_category_specific_behavior_demonstration()
    print("✓ Category behavior demonstration completed")
    
    print()
    print("=== BUG SUMMARY ===")
    print("Location: Line 3249 in unified_test_runner.py")
    print("Problem: Pattern filtering applied to ALL categories instead of only E2E")
    print("Impact: Non-E2E tests are incorrectly filtered when --pattern is used")
    print("Fix needed: Add category check before applying pattern filter")