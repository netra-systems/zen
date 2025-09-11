#!/usr/bin/env python3
"""
DEPRECATED TEST RUNNER - LEGACY COMPATIBILITY ONLY
=====================================================
This script is DEPRECATED and will be removed in a future version.
Please use the unified test runner instead:

    python tests/unified_test_runner.py [your args]

The integrated test runner functionality has been consolidated into the
unified test runner which supports all orchestration features.

SSOT CONSOLIDATION: This file was part of Issue #299 remediation.
All test runner functionality has been consolidated into unified_test_runner.py
"""

import sys
import subprocess
from pathlib import Path

def show_deprecation_warning():
    """Show deprecation warning."""
    print("="*80)
    print("[DEPRECATION WARNING] This script is deprecated!")
    print("="*80)
    print("The integrated_test_runner_ORIGINAL.py script has been consolidated into unified_test_runner.py")
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

def main():
    """Main entry point - redirect to unified test runner."""
    show_deprecation_warning()
    
    # Get project root
    project_root = Path(__file__).parent.parent.absolute()
    unified_runner = project_root / "tests" / "unified_test_runner.py"
    
    # Build command to run unified test runner with all original args
    cmd = [sys.executable, str(unified_runner)] + sys.argv[1:]
    
    print(f"Redirecting to: {' '.join(cmd)}")
    print()
    
    # Execute unified test runner
    try:
        result = subprocess.run(cmd, cwd=project_root)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running unified test runner: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()