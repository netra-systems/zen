#!/usr/bin/env python3
"""
DEPRECATED TEST RUNNER - LEGACY COMPATIBILITY ONLY
=====================================================
This script is DEPRECATED and will be removed in a future version.
Please use the unified test runner instead:

    python tests/unified_test_runner.py --service backend [your args]

This script now redirects to the unified test runner for backward compatibility.
"""

import sys
import subprocess
from pathlib import Path

def show_deprecation_warning():
    """Show deprecation warning."""
    print("="*80)
    print("[DEPRECATION WARNING] This script is deprecated!")
    print("="*80)
    print("The test_backend.py script has been consolidated into unified_test_runner.py")
    print("Please update your scripts and CI/CD to use:")
    print()
    print("    python tests/unified_test_runner.py --service backend [your args]")
    print()
    print("This legacy wrapper will be removed in a future version.")
    print("="*80)
    print()

def convert_args_to_unified(args):
    """Convert legacy backend args to unified test runner args."""
    unified_args = ["python", "tests/unified_test_runner.py", "--service", "backend"]
    
    # Skip the script name
    args = args[1:]
    
    # Add all remaining arguments as-is since we added compatibility to unified runner
    unified_args.extend(args)
    
    return unified_args

def main():
    """Main entry point - redirect to unified test runner."""
    show_deprecation_warning()
    
    # Convert arguments
    unified_command = convert_args_to_unified(sys.argv)
    
    # Show what we're running
    print("Redirecting to:", " ".join(unified_command))
    print("-" * 80)
    
    # Execute the unified test runner
    try:
        exit_code = subprocess.run(unified_command, cwd=Path(__file__).parent.parent).returncode
        sys.exit(exit_code)
    except Exception as e:
        print(f"Failed to run unified test runner: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()