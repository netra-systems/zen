from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
ClickHouse SSOT Compliance Test Runner

Simple script to run the ClickHouse SSOT violation tests and provide
a clear summary of compliance status.

Usage:
    python3 run_ssot_compliance_tests.py [--verbose]
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run SSOT compliance tests and provide summary."""
    
    # Set up environment
    project_root = Path(__file__).parent.parent
    analytics_service_path = Path(__file__).parent
    
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{project_root}:{analytics_service_path}"
    
    # Determine verbosity
    verbose = '--verbose' in sys.argv
    
    print("=" * 60)
    print("CLICKHOUSE SSOT COMPLIANCE TEST RUNNER")
    print("=" * 60)
    print(f"Analytics Service Path: {analytics_service_path}")
    print(f"Project Root: {project_root}")
    print("")
    
    # Run the compliance tests
    test_file = analytics_service_path / "tests/compliance/test_clickhouse_ssot_violations.py"
    
    cmd = [
        sys.executable, "-m", "pytest", 
        str(test_file),
        "-v" if verbose else "--tb=no",
        "--disable-warnings"
    ]
    
    if verbose:
        print("Running command:", " ".join(cmd))
        print("")
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=not verbose,
            text=True,
            cwd=project_root
        )
        
        if verbose:
            return_code = result.returncode
        else:
            print("Test Output:")
            print("-" * 40)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("ERRORS:")
                print(result.stderr)
            return_code = result.returncode
        
        print("")
        print("=" * 60)
        if return_code == 0:
            print(" CELEBRATION:  SSOT COMPLIANCE: PASSED")
            print("All ClickHouse SSOT requirements are met!")
        else:
            print(" FAIL:  SSOT COMPLIANCE: FAILED")
            print("ClickHouse SSOT violations detected.")
            print("")
            print("NEXT STEPS:")
            print("1. Remove duplicate ClickHouse implementations")
            print("2. Update imports to use clickhouse_manager")
            print("3. Complete service initialization in main.py")
            print("4. Replace deprecated model usage")
            print("5. Re-run tests to verify compliance")
        print("=" * 60)
        
        return return_code
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
