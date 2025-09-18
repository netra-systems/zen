from shared.isolated_environment import get_env
#!/usr/bin/env python3
'''Production Load Test Runner

env = get_env()
This script provides a convenient way to run production load tests
with appropriate configuration and reporting.

Usage:
python tests/load/run_load_tests.py [options]

Examples:
        # Run all load tests
python tests/load/run_load_tests.py

        # Run specific test
python tests/load/run_load_tests.py --test test_100_concurrent_agents_baseline

        # Run with custom report directory
python tests/load/run_load_tests.py --report-dir /path/to/reports

        # Quick smoke test (reduced load)
python tests/load/run_load_tests.py --quick
'''

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
parser = argparse.ArgumentParser(description="Run production load tests")

parser.add_argument( )
"--test",
help="Run specific test function (e.g., test_100_concurrent_agents_baseline)"
    

parser.add_argument( )
"--quick",
action="store_true",
help="Run quick smoke tests with reduced load"
    

parser.add_argument( )
"--report-dir",
default="test_reports/load",
help="Directory for test reports (default: test_reports/load)"
    

parser.add_argument( )
"--verbose", "-v",
action="store_true",
help="Verbose output"
    

parser.add_argument( )
"--parallel", "-p",
type=int,
default=1,
help="Number of parallel test workers (default: 1)"
    

args = parser.parse_args()

    # Ensure report directory exists
os.makedirs(args.report_dir, exist_ok=True)

    # Build pytest command
cmd = ["python", "-m", "pytest"]

    # Add test file/function
if args.test:
cmd.append("formatted_string")
else:
cmd.append("tests/load/")

            # Add pytest options
cmd.extend([ ))
"-m", "load",  # Only run load tests
"--asyncio-mode=auto",  # Enable asyncio support
"-x",  # Stop on first failure
"--tb=short",  # Short traceback format
            

if args.verbose:
cmd.append("-v")

if args.parallel > 1:
cmd.extend(["-n", str(args.parallel)])

                    # Set environment variables for load testing
env = env.get_all()
env["PYTEST_LOAD_TESTING"] = "1"
env["LOAD_TEST_REPORT_DIR"] = args.report_dir

if args.quick:
env["LOAD_TEST_QUICK_MODE"] = "1"
print("[U+1F3C3] Running in quick mode (reduced load)")

print(f"[U+1F680] Starting production load tests...")
print("formatted_string")
print("formatted_string")
print()

                        # Run the tests
start_time = time.time()

try:
result = subprocess.run(cmd, env=env, check=False)

end_time = time.time()
duration = end_time - start_time

print()
print("formatted_string")
print("formatted_string")

if result.returncode == 0:
print(" PASS:  All load tests passed!")
else:
print(" FAIL:  Some load tests failed!")

return result.returncode

except KeyboardInterrupt:
print(" )
[U+1F6D1] Load tests interrupted by user")
return 1
except Exception as e:
print("formatted_string")
return 1


if __name__ == "__main__":
sys.exit(main())
