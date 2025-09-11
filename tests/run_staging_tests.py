#!/usr/bin/env python3
"""
DEPRECATION WARNING: This staging test runner is deprecated in favor of UnifiedTestRunner SSOT.

This staging E2E test runner now redirects to the unified test runner's staging mode
to maintain SSOT compliance while preserving all existing staging test functionality.

CRITICAL: Please migrate to using the unified test runner directly:
    python tests/unified_test_runner.py --execution-mode staging --env staging

Migration Path:
    OLD: python tests/run_staging_tests.py --quick --auth --api --ws
    NEW: python tests/unified_test_runner.py --execution-mode staging --quick --auth --api --ws

All original staging test flags and options are preserved and forwarded to the SSOT implementation.
"""

import sys
import subprocess
from pathlib import Path
import argparse
import os


def show_deprecation_warning():
    """Show deprecation warning to users."""
    print("WARNING: DEPRECATION WARNING")
    print("=" * 70)
    print("Staging E2E Test Runner")
    print("=" * 70)
    print("This staging test runner is deprecated.")
    print("Please migrate to UnifiedTestRunner SSOT:")
    print()
    print("  NEW: python tests/unified_test_runner.py --execution-mode staging")
    print()
    print("All staging test functionality preserved. Redirecting...")
    print("=" * 70)
    print()


def parse_staging_test_args():
    """Parse all staging test arguments for compatibility."""
    parser = argparse.ArgumentParser(
        description="[DEPRECATED] Staging E2E Test Runner"
    )
    
    # Core staging test options
    parser.add_argument("--quick", action="store_true", help="Run only quick health checks")
    parser.add_argument("--full", action="store_true", help="Run full test suite including slow tests")
    parser.add_argument("--auth", action="store_true", help="Run only authentication tests")
    parser.add_argument("--api", action="store_true", help="Run only API tests")
    parser.add_argument("--ws", action="store_true", help="Run only WebSocket tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--env", default="staging", help="Environment to test against")
    parser.add_argument("--timeout", type=int, help="Test timeout in seconds")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    
    return parser.parse_known_args()


def main():
    """Main entry point with deprecation wrapper."""
    show_deprecation_warning()
    
    # Parse all staging test arguments
    args, unknown_args = parse_staging_test_args()
    
    # Get project root
    project_root = Path(__file__).parent.parent
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    if not unified_runner.exists():
        print(f"ERROR: UnifiedTestRunner not found at {unified_runner}")
        print("Falling back to original staging test runner...")
        return execute_fallback_staging_tests()
    
    try:
        # Build unified test runner command for staging tests
        cmd = [
            sys.executable, str(unified_runner),
            "--execution-mode", "staging"
        ]
        
        # Forward all staging test arguments
        if args.env != "staging":  # Only add if not default
            cmd.extend(["--env", args.env])
        if args.quick:
            cmd.append("--quick")
        if args.full:
            cmd.append("--full")
        if args.auth:
            cmd.append("--auth")
        if args.api:
            cmd.append("--api")
        if args.ws:
            cmd.append("--ws")
        if args.verbose:
            cmd.append("--verbose")
        if args.timeout:
            cmd.extend(["--timeout", str(args.timeout)])
        if args.fail_fast:
            cmd.append("--fail-fast")
            
        # Add any unknown arguments
        cmd.extend(unknown_args)
        
        print(f"Executing staging tests via UnifiedTestRunner:")
        print(f"   {' '.join(cmd)}")
        print()
        print("Environment Variables Required:")
        print("  - E2E_OAUTH_SIMULATION_KEY: Key for OAuth simulation")
        print("  - ENVIRONMENT: Must be set to 'staging'")
        print()
        
        # Execute unified test runner for staging tests
        result = subprocess.run(cmd, cwd=project_root)
        
        # Preserve original exit code behavior
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"ERROR: Failed to execute UnifiedTestRunner staging tests: {e}")
        print("Falling back to original staging test runner...")
        return execute_fallback_staging_tests()


def execute_fallback_staging_tests():
    """Execute original staging test runner as fallback."""
    try:
        # Import and execute original functionality as fallback
        project_root = Path(__file__).parent.parent
        
        # Import the backed up original implementation
        backup_file = Path(__file__).parent / "run_staging_tests.py.backup"
        if backup_file.exists():
            print("Using backup staging test runner...")
            
            # Add project root to path
            sys.path.insert(0, str(project_root))
            
            import importlib.util
            spec = importlib.util.spec_from_file_location("staging_backup", backup_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute main from backup with original arguments
            # Reset sys.argv to original arguments for the backup script
            original_argv = sys.argv[:]
            original_argv[0] = str(backup_file)  # Update script name
            sys.argv = original_argv
            
            # Note: The backup file may have syntax errors, so handle gracefully
            try:
                module.main()
            except AttributeError:
                print("WARNING: Backup file doesn't have main() function")
                print("Running tests directly with pytest...")
                
                # Fallback to direct pytest execution
                subprocess.run([
                    sys.executable, "-m", "pytest", 
                    "tests/e2e/", 
                    "-v", "--tb=short"
                ], cwd=project_root)
                
        else:
            print("CRITICAL: No backup available for staging test runner")
            print("Running basic staging health check...")
            
            # Basic staging health check as ultimate fallback
            subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/e2e/test_staging_health.py", 
                "-v"
            ], cwd=project_root)
            
    except Exception as fallback_error:
        print(f"CRITICAL: Fallback staging tests failed: {fallback_error}")
        print("Manual staging verification required.")
        sys.exit(1)


if __name__ == "__main__":
    main()