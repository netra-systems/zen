import subprocess
import sys
import os

os.chdir("C:\\netra-apex")

def run_test(test_path, description):
    print(f"\n{'='*50}")
    print(f"Running: {description}")
    print(f"Path: {test_path}")
    print('='*50)

    try:
        # Run pytest with verbose output and short traceback
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            test_path,
            "-v", "--tb=short", "-x", "--no-header"
        ], capture_output=True, text=True, timeout=300)

        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        print("TEST TIMED OUT AFTER 5 MINUTES")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

# Run each test category
tests = [
    ("tests/integration/agent_golden_path/", "Agent Golden Path Integration Tests"),
    ("tests/integration/agents/test_issue_1142_golden_path_startup_contamination.py", "Issue 1142 Golden Path Startup"),
    ("tests/integration/config_ssot/test_config_golden_path_protection.py", "Config SSOT Golden Path Protection"),
    ("tests/integration/config_ssot/test_golden_path_auth_failure_reproduction.py", "Golden Path Auth Failure Reproduction")
]

results = []
for test_path, description in tests:
    success = run_test(test_path, description)
    results.append((description, success))

print(f"\n{'='*50}")
print("FINAL SUMMARY")
print('='*50)
for desc, success in results:
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"{status}: {desc}")