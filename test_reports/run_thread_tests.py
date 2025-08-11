"""Helper script to run threads_route tests with coverage"""
import subprocess
import sys

result = subprocess.run([
    sys.executable, "-m", "pytest",
    "../app/tests/unit/test_threads_route.py",
    "--cov=app.routes.threads_route",
    "--cov-report=term-missing",
    "--tb=short",
    "-q"
], capture_output=True, text=True)

print(result.stdout)
print(result.stderr)

# Extract coverage info
lines = result.stdout.split('\n')
for line in lines:
    if 'threads_route.py' in line or 'TOTAL' in line:
        print(f"COVERAGE: {line}")

sys.exit(result.returncode)