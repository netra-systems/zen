#!/usr/bin/env python3
"""
Unauthorized Test Runner Detection Script for Pre-Commit Hooks

Business Value Justification (BVJ):
- Segment: Platform (All segments affected by test infrastructure chaos)
- Business Goal: Stability - Prevent deployment blocking from test chaos
- Value Impact: Protects $500K+ ARR from deployment delays and failures
- Revenue Impact: Prevents customer churn from unreliable system deployments

PURPOSE: Prevent new unauthorized test runners from being committed.
ISSUE: https://github.com/netra-systems/netra-apex/issues/1024

SSOT Requirement: ALL test execution must go through tests/unified_test_runner.py
"""

import sys
import re
import ast
from pathlib import Path
from typing import List, Tuple, Set

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Authorized test runner patterns (SSOT compliance)
AUTHORIZED_RUNNERS = {
    "tests/unified_test_runner.py",  # Primary SSOT test runner
    "test_framework/ssot/base_test_case.py",  # SSOT base classes
    "test_framework/unified_docker_manager.py",  # SSOT Docker management
}

# Unauthorized patterns that indicate test runner violations
UNAUTHORIZED_PATTERNS = [
    # Direct pytest execution
    r'pytest\.main\s*\(',
    r'subprocess\..*pytest',
    r'os\.system\s*\(.*pytest',
    r'run\s*\(.*pytest',

    # Unauthorized test orchestration
    r'if\s+__name__\s*==\s*["\']__main__["\'].*pytest',
    r'unittest\.main\s*\(',
    r'pytest\.cmdline\.main',

    # Test discovery bypasses
    r'pytest\.collect\.',
    r'pytest\.runner\.',

    # Direct test invocation
    r'\.run_tests\s*\(',
    r'execute_tests\s*\(',
    r'run_test_suite\s*\(',
]

def detect_unauthorized_test_runners(file_paths: List[str]) -> List[Tuple[str, int, str, str]]:
    """
    Detect unauthorized test runner patterns in files.

    Returns:
        List of (file_path, line_number, pattern, line_content) tuples
    """
    violations = []

    for file_path in file_paths:
        # Skip authorized runners
        if any(auth in file_path for auth in AUTHORIZED_RUNNERS):
            continue

        # Skip non-Python files
        if not file_path.endswith('.py'):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()

                # Skip comments and docstrings
                if line_stripped.startswith('#') or line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                    continue

                # Check each unauthorized pattern
                for pattern in UNAUTHORIZED_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        violations.append((file_path, line_num, pattern, line_stripped))

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            continue

    return violations

def analyze_main_block_violations(file_paths: List[str]) -> List[Tuple[str, str]]:
    """
    Analyze __main__ blocks that might contain unauthorized test execution.

    Returns:
        List of (file_path, violation_description) tuples
    """
    violations = []

    for file_path in file_paths:
        # Skip authorized runners
        if any(auth in file_path for auth in AUTHORIZED_RUNNERS):
            continue

        if not file_path.endswith('.py'):
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse AST to find __main__ blocks
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if (isinstance(node, ast.If) and
                        isinstance(node.test, ast.Compare) and
                        isinstance(node.test.left, ast.Name) and
                        node.test.left.id == '__name__'):

                        # Found __main__ block, check for test execution
                        main_block_code = ast.get_source_segment(content, node)
                        if main_block_code:
                            for pattern in UNAUTHORIZED_PATTERNS:
                                if re.search(pattern, main_block_code, re.IGNORECASE):
                                    violations.append((
                                        file_path,
                                        f"__main__ block contains unauthorized test execution: {pattern}"
                                    ))
                                    break

            except SyntaxError:
                # If AST parsing fails, fall back to regex
                if re.search(r'if\s+__name__\s*==\s*["\']__main__["\']', content):
                    for pattern in UNAUTHORIZED_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            violations.append((
                                file_path,
                                f"File contains unauthorized test execution in __main__ block"
                            ))
                            break

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            continue

    return violations

def main():
    """Main entry point for pre-commit hook."""
    if len(sys.argv) < 2:
        print("Usage: detect_unauthorized_test_runners.py <file1> <file2> ...")
        sys.exit(0)

    file_paths = sys.argv[1:]

    # Detect pattern violations
    pattern_violations = detect_unauthorized_test_runners(file_paths)

    # Detect __main__ block violations
    main_violations = analyze_main_block_violations(file_paths)

    total_violations = len(pattern_violations) + len(main_violations)

    if total_violations > 0:
        print(f"\n🚨 CRITICAL: {total_violations} UNAUTHORIZED TEST RUNNER VIOLATIONS DETECTED!")
        print("=" * 80)
        print("ISSUE #1024: SSOT Regression - Unauthorized Test Runners Blocking Golden Path")
        print("BUSINESS IMPACT: $500K+ ARR at risk from test infrastructure chaos")
        print("=" * 80)

        if pattern_violations:
            print("\n📍 PATTERN VIOLATIONS:")
            for file_path, line_num, pattern, line_content in pattern_violations:
                print(f"  ❌ {file_path}:{line_num}")
                print(f"     Pattern: {pattern}")
                print(f"     Line: {line_content}")
                print()

        if main_violations:
            print("\n📍 __main__ BLOCK VIOLATIONS:")
            for file_path, description in main_violations:
                print(f"  ❌ {file_path}")
                print(f"     Issue: {description}")
                print()

        print("🔧 REQUIRED ACTION:")
        print("1. Replace pytest.main() calls with tests/unified_test_runner.py")
        print("2. Remove __main__ blocks with direct test execution")
        print("3. Use SSOT pattern: python tests/unified_test_runner.py --category <category>")
        print()
        print("📚 DOCUMENTATION:")
        print("- SSOT Guide: reports/TEST_EXECUTION_GUIDE.md")
        print("- Issue #1024: https://github.com/netra-systems/netra-apex/issues/1024")
        print("- Unified Runner: tests/unified_test_runner.py")

        sys.exit(1)

    print("✅ No unauthorized test runner violations detected.")
    sys.exit(0)

if __name__ == "__main__":
    main()