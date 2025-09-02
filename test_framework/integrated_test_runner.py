#!/usr/bin/env python3
"""
DEPRECATED TEST RUNNER - LEGACY COMPATIBILITY ONLY
=====================================================
This script is DEPRECATED and will be removed in a future version.
Please use the unified test runner instead:

    python tests/unified_test_runner.py [your args]

The integrated test runner functionality has been consolidated into the
unified test runner which supports all orchestration features.
"""

import sys
import subprocess
from pathlib import Path

def show_deprecation_warning():
    """Show deprecation warning."""
    print("="*80)
    print("[DEPRECATION WARNING] This script is deprecated!")
    print("="*80)
    print("The integrated_test_runner.py script has been consolidated into unified_test_runner.py")
    print("Please update your scripts and CI/CD to use:")
    print()
    print("    python tests/unified_test_runner.py [your args]")
    print()
    print("The unified test runner now includes all Docker orchestration,")
    print("Alpine isolation, and service refresh capabilities.")
    print()
    print("This legacy wrapper will be removed in a future version.")
    print("="*80)
    print()

def convert_args_to_unified(args):
    """Convert legacy integrated test runner args to unified test runner args."""
    unified_args = ["python", "tests/unified_test_runner.py"]
    
    # Skip the script name
    args = args[1:]
    
    # Convert specific integrated test runner args
    i = 0
    while i < len(args):
        arg = args[i]
        
        # Convert mode arguments to orchestration arguments
        if arg == "--mode":
            if i + 1 < len(args):
                mode = args[i + 1]
                if mode == "isolated":
                    unified_args.extend(["--docker-dedicated"])
                elif mode == "parallel":
                    unified_args.extend(["--parallel"])
                elif mode == "refresh":
                    unified_args.extend(["--docker-force-restart"])
                elif mode == "ci":
                    unified_args.extend(["--execution-mode", "nightly"])
                i += 1  # Skip the mode value
            
        # Convert suites to categories
        elif arg == "--suites":
            if i + 1 < len(args):
                suites = args[i + 1].split()
                unified_args.extend(["--categories"] + suites)
                i += 1  # Skip the suites value
                
        # Pass through other arguments
        else:
            unified_args.append(arg)
            
        i += 1
    
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