from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""Run supervisor tests with ClickHouse disabled."""

import os
import sys
import subprocess

# Set environment variables to disable ClickHouse
os.environ["TESTING"] = "true"
os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"
os.environ["CLICKHOUSE_ENABLED"] = "false"
os.environ["TEST_DISABLE_CLICKHOUSE"] = "true"
os.environ["SKIP_SERVICE_HEALTH_CHECK"] = "true"
os.environ["USE_REAL_SERVICES"] = "false"

# Run the tests
test_files = [
    "netra_backend/tests/agents/test_supervisor_bulletproof.py",
    "netra_backend/tests/integration/test_supervisor_agent_coordination.py"
]

for test_file in test_files:
    if os.path.exists(test_file):
        print(f"\n{'='*60}")
        print(f"Running: {test_file}")
        print('='*60)
        
        # Run the test with pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            test_file,
            "-v", "--tb=short", "-x",
            "--disable-warnings",
            "--timeout=10"  # Add timeout per test
        ], capture_output=False, text=True)
        
        if result.returncode != 0:
            print(f"Test failed: {test_file}")
        else:
            print(f"Test passed: {test_file}")
    else:
        print(f"Test file not found: {test_file}")

print("\n" + "="*60)
print("Test run complete")
