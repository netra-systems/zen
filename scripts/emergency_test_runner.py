#!/usr/bin/env python
"""
Emergency Test Runner - Direct pytest execution bypass for infrastructure failures

PURPOSE: When unified_test_runner.py fails, this provides direct pytest access
         while maintaining basic categorization and SSOT compliance.

USAGE:
    python scripts/emergency_test_runner.py unit
    python scripts/emergency_test_runner.py mission_critical
    python scripts/emergency_test_runner.py smoke --no-cov
"""

import sys
import subprocess
from pathlib import Path
import argparse

# Setup project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Test category mapping - direct pytest paths
TEST_CATEGORIES = {
    'unit': [
        'netra_backend/tests/unit',
        'netra_backend/tests/core',
        'auth_service/tests -m unit'
    ],
    'mission_critical': [
        'tests/mission_critical'
    ],
    'smoke': [
        'netra_backend/tests -m smoke'
    ],
    'integration': [
        'netra_backend/tests/integration',
        'tests/integration'
    ],
    'api': [
        'netra_backend/tests/api',
        'tests/api'
    ],
    'websocket': [
        'netra_backend/tests/websocket',
        'tests/websocket'
    ]
}

def run_pytest_direct(category: str, no_coverage: bool = False, verbose: bool = False):
    """Run pytest directly for specified category."""

    if category not in TEST_CATEGORIES:
        print(f"❌ Unknown category: {category}")
        print(f"Available: {', '.join(TEST_CATEGORIES.keys())}")
        return False

    # Build pytest command
    base_cmd = ['python', '-m', 'pytest', '-c', 'pyproject.toml']

    # Add paths for category
    paths = TEST_CATEGORIES[category]
    for path in paths:
        base_cmd.extend(path.split())

    # Add coverage if requested
    if not no_coverage:
        base_cmd.extend([
            '--cov=.',
            '--cov-report=term-missing',
            '--cov-report=html'
        ])

    # Add verbosity
    if verbose:
        base_cmd.append('-v')

    # Add timeout protection
    base_cmd.extend(['--timeout=300', '--timeout-method=thread'])

    print(f"Running emergency test execution for category: {category}")
    print(f"Command: {' '.join(base_cmd)}")
    print("=" * 60)

    # Execute
    try:
        result = subprocess.run(
            base_cmd,
            cwd=PROJECT_ROOT,
            capture_output=False,  # Show real-time output
            text=True
        )

        if result.returncode == 0:
            print(f"SUCCESS: Category '{category}' PASSED")
            return True
        else:
            print(f"FAILED: Category '{category}' FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print(f"ERROR: Execution failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Emergency Test Runner - Direct pytest bypass')
    parser.add_argument('category', choices=list(TEST_CATEGORIES.keys()),
                       help='Test category to run')
    parser.add_argument('--no-cov', action='store_true',
                       help='Disable coverage reporting')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output')

    args = parser.parse_args()

    print("EMERGENCY TEST RUNNER - Bypassing unified_test_runner.py")
    print(f"Category: {args.category}")
    print(f"Working Directory: {PROJECT_ROOT}")
    print()

    success = run_pytest_direct(args.category, args.no_cov, args.verbose)

    if success:
        print("\nEMERGENCY TEST EXECUTION SUCCESSFUL")
        print("This proves the test system can work - investigate unified_test_runner.py issues")
    else:
        print("\nEMERGENCY TEST EXECUTION FAILED")
        print("This indicates deeper test infrastructure issues beyond the runner")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()