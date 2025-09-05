#!/usr/bin/env python
"""
Fast-fail import testing script for Netra Backend

This script provides quick import validation to catch import errors
early in the development cycle. It can be run standalone or integrated
into CI/CD pipelines.

Usage:
    python scripts/test_imports.py              # Test critical imports (fast-fail)
    python scripts/test_imports.py --all        # Test all imports
    python scripts/test_imports.py --module app.services  # Test specific module
"""

import os
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path

from test_framework.import_tester import ImportTester


def main():
    """Main entry point for import testing"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fast-fail import testing for Netra Backend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/test_imports.py                  # Quick critical import test
  python scripts/test_imports.py --all            # Comprehensive import test
  python scripts/test_imports.py --verbose        # Show detailed output
  python scripts/test_imports.py --json report.json  # Save JSON report
        """
    )
    
    parser.add_argument(
        '--all', action='store_true',
        help='Test all imports (comprehensive, slower)'
    )
    parser.add_argument(
        '--module', type=str,
        help='Specific module to test (e.g., netra_backend.app.services)'
    )
    parser.add_argument(
        '--verbose', action='store_true',
        help='Show detailed output for each import'
    )
    parser.add_argument(
        '--json', type=str,
        help='Save detailed JSON report to file'
    )
    parser.add_argument(
        '--no-fail-fast', action='store_true',
        help='Continue testing even after failures'
    )
    
    args = parser.parse_args()
    
    tester = ImportTester(root_path=PROJECT_ROOT, verbose=args.verbose)
    
    # Determine what to test
    if args.all:
        print("="*60)
        print("COMPREHENSIVE IMPORT TEST")
        print("="*60)
        print("\nTesting all modules in netra_backend.app...")
        report = tester.test_package('netra_backend.app', recursive=True)
        
    elif args.module:
        print("="*60)
        print(f"TESTING MODULE: {args.module}")
        print("="*60)
        report = tester.test_package(args.module, recursive=True)
        
    else:
        # Default: fast-fail critical import test
        print("="*60)
        print("CRITICAL IMPORT TEST (Fast-Fail Mode)")
        print("="*60)
        
        if args.no_fail_fast:
            # Test all critical imports
            report = tester.test_critical_imports()
        else:
            # Fast-fail mode
            success = tester.run_fast_fail_test()
            if not success:
                print("\nImport test failed. Please fix the import errors above.")
                sys.exit(1)
            else:
                print("\nAll critical imports successful!")
                sys.exit(0)
    
    # Print results for non-fast-fail modes
    print(report.get_summary())
    
    if report.failed_imports > 0:
        print(report.get_failures_report())
        
        # Provide actionable feedback
        print("\n" + "="*60)
        print("ACTION REQUIRED")
        print("="*60)
        print("\nTo fix import errors:")
        print("1. Check for missing dependencies: pip install -r requirements.txt")
        print("2. Look for circular imports in the error messages above")
        print("3. Verify all module files exist and have no syntax errors")
        print("4. Check that __init__.py files exist in all package directories")
        
    # Save JSON report if requested
    if args.json:
        report.save_json_report(args.json)
        print(f"\nDetailed report saved to: {args.json}")
    
    # Exit with appropriate code
    sys.exit(1 if report.failed_imports > 0 else 0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nImport test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)