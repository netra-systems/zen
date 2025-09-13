#!/usr/bin/env python3
"""
Configuration SSOT Test Runner - Issue #667

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Validate SSOT configuration consolidation process
- Value Impact: Ensures safe consolidation without breaking Golden Path
- Strategic Impact: Protects $500K+ ARR chat functionality during migration

This script runs the comprehensive test suite for Issue #667 configuration
manager SSOT consolidation, providing systematic validation of the consolidation
process.

Usage:
    python scripts/run_configuration_ssot_tests.py [--category <category>] [--verbose]

Categories:
    - unit: Unit tests for duplication detection
    - integration: Integration tests (non-docker)
    - compliance: SSOT enforcement compliance tests
    - all: All configuration SSOT tests (default)
"""

import argparse
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any


def setup_environment():
    """Set up the test environment."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def run_test_category(category: str, verbose: bool = False) -> Dict[str, Any]:
    """Run tests for a specific category."""
    project_root = Path(__file__).parent.parent

    test_paths = {
        'unit': 'tests/unit/configuration_ssot/',
        'integration': 'tests/integration/configuration_ssot/',
        'compliance': 'tests/compliance/configuration_ssot/',
    }

    if category not in test_paths:
        raise ValueError(f"Unknown test category: {category}")

    test_path = project_root / test_paths[category]

    if not test_path.exists():
        return {
            'category': category,
            'success': False,
            'error': f"Test path does not exist: {test_path}",
            'output': '',
            'duration': 0
        }

    # Use the unified test runner with SSOT patterns
    cmd = [
        sys.executable,
        'tests/unified_test_runner.py',
        '--category', 'unit' if category == 'unit' else 'integration',
        '--test-path', str(test_path),
        '--no-coverage',  # Skip coverage for this specific test run
    ]

    if verbose:
        cmd.append('--verbose')

    print(f"\nRunning {category.upper()} tests for Configuration SSOT...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Test path: {test_path}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per category
        )

        duration = time.time() - start_time

        return {
            'category': category,
            'success': result.returncode == 0,
            'returncode': result.returncode,
            'output': result.stdout,
            'error': result.stderr,
            'duration': duration
        }

    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return {
            'category': category,
            'success': False,
            'error': f"Test category {category} timed out after 5 minutes",
            'output': '',
            'duration': duration
        }

    except Exception as e:
        duration = time.time() - start_time
        return {
            'category': category,
            'success': False,
            'error': f"Failed to run {category} tests: {e}",
            'output': '',
            'duration': duration
        }


def run_individual_test_files(verbose: bool = False) -> List[Dict[str, Any]]:
    """Run individual test files directly using pytest as fallback."""
    project_root = Path(__file__).parent.parent

    test_files = [
        'tests/unit/configuration_ssot/test_configuration_manager_duplication_detection.py',
        'tests/integration/configuration_ssot/test_configuration_consolidation_integration.py',
        'tests/compliance/configuration_ssot/test_configuration_manager_enforcement.py'
    ]

    results = []

    for test_file in test_files:
        test_path = project_root / test_file

        if not test_path.exists():
            results.append({
                'test_file': test_file,
                'success': False,
                'error': f"Test file does not exist: {test_path}",
                'output': '',
                'duration': 0
            })
            continue

        # Run with pytest directly
        cmd = [sys.executable, '-m', 'pytest', str(test_path), '-v']

        if verbose:
            cmd.extend(['-s', '--tb=short'])

        print(f"\nRunning {test_file}...")
        print(f"Command: {' '.join(cmd)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=180  # 3 minute timeout per file
            )

            duration = time.time() - start_time

            results.append({
                'test_file': test_file,
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'output': result.stdout,
                'error': result.stderr,
                'duration': duration
            })

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            results.append({
                'test_file': test_file,
                'success': False,
                'error': f"Test file {test_file} timed out after 3 minutes",
                'output': '',
                'duration': duration
            })

        except Exception as e:
            duration = time.time() - start_time
            results.append({
                'test_file': test_file,
                'success': False,
                'error': f"Failed to run {test_file}: {e}",
                'output': '',
                'duration': duration
            })

    return results


def print_test_results(results: List[Dict[str, Any]]):
    """Print formatted test results."""
    print("\n" + "="*80)
    print("CONFIGURATION SSOT TEST RESULTS - Issue #667")
    print("="*80)

    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    failed_tests = total_tests - successful_tests

    print(f"\nSUMMARY:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Successful: {successful_tests}")
    print(f"  Failed: {failed_tests}")
    print(f"  Success Rate: {(successful_tests/total_tests)*100:.1f}%")

    print(f"\nDETAILED RESULTS:")

    for result in results:
        test_name = result.get('category') or result.get('test_file', 'Unknown')
        status = "PASS" if result['success'] else "FAIL"
        duration = result.get('duration', 0)

        print(f"\n  {status} {test_name} ({duration:.2f}s)")

        if not result['success']:
            error = result.get('error', 'Unknown error')
            print(f"    Error: {error}")

        # Print key output excerpts
        output = result.get('output', '')
        if output and 'CONFIGURATION MANAGERS' in output:
            # Extract configuration manager detection results
            lines = output.split('\n')
            for line in lines:
                if 'FOUND CONFIGURATION MANAGERS' in line or 'DETECTED DUPLICATE' in line:
                    print(f"    {line.strip()}")

    print(f"\nTEST INTERPRETATION:")
    print(f"  EXPECTED BEHAVIOR (Issue #667 Phase 1):")
    print(f"    - Duplication detection tests should FIND duplicates")
    print(f"    - SSOT enforcement tests should FAIL (proving violations exist)")
    print(f"    - Integration tests should show compatibility between managers")
    print(f"  AFTER CONSOLIDATION:")
    print(f"    - Duplication detection should find ONLY 1 manager")
    print(f"    - SSOT enforcement tests should PASS")
    print(f"    - Integration tests should show unified configuration")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run Configuration SSOT tests for Issue #667"
    )
    parser.add_argument(
        '--category',
        choices=['unit', 'integration', 'compliance', 'all'],
        default='all',
        help='Test category to run (default: all)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--individual',
        action='store_true',
        help='Run individual test files directly (fallback method)'
    )

    args = parser.parse_args()

    setup_environment()

    print("Configuration SSOT Test Suite - Issue #667")
    print("=" * 60)
    print("Purpose: Validate configuration manager SSOT consolidation")
    print("Expected: Tests should initially FAIL, proving duplication exists")
    print("After consolidation: Tests should PASS with single SSOT manager")

    results = []

    if args.individual:
        print("\nRunning individual test files (fallback method)...")
        results = run_individual_test_files(args.verbose)
    else:
        if args.category == 'all':
            categories = ['unit', 'integration', 'compliance']
        else:
            categories = [args.category]

        for category in categories:
            result = run_test_category(category, args.verbose)
            results.append(result)

    print_test_results(results)

    # Determine exit code
    if any(not r['success'] for r in results):
        print(f"\nSome tests failed - this may be EXPECTED during Phase 1")
        print(f"   Tests are designed to FAIL initially to prove duplication exists")
        sys.exit(1)
    else:
        print(f"\nAll tests passed - configuration SSOT consolidation complete!")
        sys.exit(0)


if __name__ == '__main__':
    main()