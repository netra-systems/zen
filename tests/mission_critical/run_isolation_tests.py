#!/usr/bin/env python3
"""
DEPRECATION WARNING: This mission critical test runner is deprecated in favor of UnifiedTestRunner SSOT.

This isolation security test runner now redirects to the unified test runner's mission critical mode
to maintain SSOT compliance while preserving all existing test functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --category mission_critical --test-pattern "*isolation*"

Migration Path:
    OLD: python tests/mission_critical/run_isolation_tests.py --real-services --concurrent-load 20
    NEW: python tests/unified_test_runner.py --category mission_critical --real-services --concurrent-load 20

All original test execution flags and options are preserved and forwarded to the SSOT implementation.
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPRECATION WARNING")
    print("=" * 80)
    print("MISSION CRITICAL: Data Layer Isolation Security Tests")
    print("=" * 80)
    print("This mission critical test runner is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --category mission_critical")
    print()
    print("All isolation test functionality preserved. Redirecting...")
    print("=" * 80)
    print()


def parse_isolation_test_args():
    """Parse all isolation test arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Mission Critical Data Layer Isolation Test Runner"
    )
    
    # Core isolation test options
    parser.add_argument("--real-services", action="store_true", help="Use real services instead of mocks")
    parser.add_argument("--concurrent-load", type=int, default=10, help="Number of concurrent users to simulate")
    parser.add_argument("--test-duration", type=int, help="Test duration in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    parser.add_argument("--isolation-level", choices=["user", "session", "request"], default="user", help="Isolation level to test")
    parser.add_argument("--data-contamination-check", action="store_true", help="Check for data contamination")
    parser.add_argument("--cache-isolation-check", action="store_true", help="Check cache isolation")
    parser.add_argument("--session-isolation-check", action="store_true", help="Check session isolation")
    
    return parser.parse_known_args()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse all isolation test arguments
    args, unknown_args = parse_isolation_test_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent.parent
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Falling back to original isolation test runner...")
        return execute_fallback_isolation_tests()
    
    try:
        # Build unified test runner command for mission critical tests
        cmd = [
            sys.executable, str(unified_runner),
            "--category", "mission_critical",
            "--test-pattern", "*isolation*"
        ]
        
        # Forward all isolation test arguments
        if args.real_services:
            cmd.append("--real-services")
        if args.concurrent_load != 10:  # Only add if not default
            cmd.extend(["--concurrent-load", str(args.concurrent_load)])
        if args.test_duration:
            cmd.extend(["--test-duration", str(args.test_duration)])
        if args.verbose:
            cmd.append("--verbose")
        if args.fail_fast:
            cmd.append("--fail-fast")
        if args.isolation_level != "user":  # Only add if not default
            cmd.extend(["--isolation-level", args.isolation_level])
        if args.data_contamination_check:
            cmd.append("--data-contamination-check")
        if args.cache_isolation_check:
            cmd.append("--cache-isolation-check")
        if args.session_isolation_check:
            cmd.append("--session-isolation-check")
            
        # Add any unknown arguments
        cmd.extend(unknown_args)
        
        print(f"Executing isolation tests via UnifiedTestRunner:")
        print(f"   {' '.join(cmd)}")
        print()
        print("WARNING: These tests are EXPECTED TO FAIL initially!")
        print("   They are designed to expose critical security vulnerabilities:")
        print("   1. ClickHouse cache contamination between users")
        print("   2. Redis key collision between users")
        print("   3. Missing user context propagation")
        print("   4. Session isolation failures")
        print()
        
        # Execute unified test runner for mission critical isolation tests
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute UnifiedTestRunner isolation tests: {e}")
        print("Falling back to original isolation test runner...")
        return execute_fallback_isolation_tests()


def execute_fallback_isolation_tests():
    """Execute original isolation test runner as fallback."""
    try:
        # Import and execute original functionality as fallback
        project_root = Path(__file__).parent.parent.parent
        
        # Import the backed up original implementation
        backup_file = Path(__file__).parent / "run_isolation_tests.py.backup"
        if backup_file.exists():
            print("Using backup isolation test runner...")
            
            # Add project root to path
            sys.path.insert(0, str(project_root))
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("isolation_backup", backup_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute main from backup with original arguments
            # Reset sys.argv to original arguments for the backup script
            original_argv = sys.argv[:]
            original_argv[0] = str(backup_file)  # Update script name
            sys.argv = original_argv
            
            module.main()
        else:
            print("CRITICAL: No backup available for isolation test runner")
            print("Please restore original run_isolation_tests.py")
            sys.exit(1)
            
    except Exception as fallback_error:
        print(f"CRITICAL: Fallback isolation tests failed: {fallback_error}")
        print("Manual isolation testing required.")
        sys.exit(1)


if __name__ == "__main__":
    main()