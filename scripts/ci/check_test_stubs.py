#!/usr/bin/env python3
"""
CI Check for Test Stubs in Production Code

This script runs as part of the CI/CD pipeline to detect test stubs in production code.
It fails the build if any test stubs are found according to SPEC/no_test_stubs.xml.

Usage:
    python scripts/ci/check_test_stubs.py          # Run check and exit with code
    python scripts/ci/check_test_stubs.py --quiet  # Minimal output for CI
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path for imports

from scripts.remove_test_stubs import TestStubDetector


class CITestStubChecker:
    """CI-specific test stub checker with build integration."""
    
    def __init__(self, project_root: str, quiet: bool = False):
        self.detector = TestStubDetector(project_root)
        self.quiet = quiet
        self.exit_code = 0
    
    def run_check(self) -> int:
        """Run the test stub check and return appropriate exit code."""
        if not self.quiet:
            print("Checking for test stubs in production code...")
        
        violations = self.detector.scan_all()
        
        if not violations:
            if not self.quiet:
                print("SUCCESS: No test stubs found in production code.")
            return 0
        
        # We found violations - this should fail the build
        self.exit_code = 1
        
        if self.quiet:
            # Just print essential info for CI logs (no emojis for Windows compatibility)
            print(f"FAIL: Found {len(violations)} test stubs in production code")
            for v in violations[:5]:  # Show first 5 violations
                print(f"  {v.file_path}:{v.line_number} - {v.violation_type}")
            if len(violations) > 5:
                print(f"  ... and {len(violations) - 5} more violations")
        else:
            # Detailed output for local development
            self._print_detailed_report(violations)
        
        return self.exit_code
    
    def _print_detailed_report(self, violations):
        """Print detailed violation report."""
        print(f" FAIL:  Found {len(violations)} test stubs in production code")
        print()
        
        # Group by severity
        high_violations = [v for v in violations if v.severity == "HIGH"]
        medium_violations = [v for v in violations if v.severity == "MEDIUM"]
        
        if high_violations:
            print(f" ALERT:  HIGH SEVERITY ({len(high_violations)} violations):")
            for v in high_violations:
                print(f"  [U+1F4C1] {v.file_path}")
                print(f"      PIN:  Line {v.line_number}: {v.description}")
                print(f"     [U+1F527] Action: {v.recommended_action}")
                print()
        
        if medium_violations:
            print(f" WARNING: [U+FE0F]  MEDIUM SEVERITY ({len(medium_violations)} violations):")
            for v in medium_violations:
                print(f"  [U+1F4C1] {v.file_path}")
                print(f"      PIN:  Line {v.line_number}: {v.description}")
                print(f"     [U+1F527] Action: {v.recommended_action}")
                print()
        
        print(" IDEA:  To fix these issues:")
        print("   1. Review SPEC/no_test_stubs.xml for guidelines")
        print("   2. Replace test stubs with real implementations")
        print("   3. Move test helpers to app/tests/ directory")
        print("   4. Run 'python scripts/remove_test_stubs.py --scan' locally")


def setup_github_actions_annotations(violations):
    """Set up GitHub Actions annotations for found violations."""
    for violation in violations:
        # Convert Windows path to forward slashes for GitHub Actions
        file_path = violation.file_path.replace('\\', '/')
        
        annotation_level = "error" if violation.severity == "HIGH" else "warning"
        
        # GitHub Actions annotation format
        print(f"::{annotation_level} file={file_path},line={violation.line_number}::"
              f"{violation.description} - {violation.recommended_action}")


def main():
    """Main entry point for CI test stub checking."""
    parser = argparse.ArgumentParser(description='CI Test Stub Checker')
    parser.add_argument('--quiet', action='store_true', 
                       help='Minimal output for CI logs')
    parser.add_argument('--github-actions', action='store_true',
                       help='Output GitHub Actions annotations')
    parser.add_argument('--project-root', default='.', 
                       help='Project root directory')
    
    args = parser.parse_args()
    
    checker = CITestStubChecker(args.project_root, args.quiet)
    
    try:
        exit_code = checker.run_check()
        
        # Add GitHub Actions annotations if requested
        if args.github_actions and checker.detector.violations:
            setup_github_actions_annotations(checker.detector.violations)
        
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"ERROR: Test stub check failed: {e}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(2)  # Different exit code for script errors


if __name__ == '__main__':
    main()