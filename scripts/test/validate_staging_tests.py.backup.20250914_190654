from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Validate and run staging tests with proper environment setup
"""

import os
import sys
import subprocess

# Set environment BEFORE any imports that might check it
os.environ["ENVIRONMENT"] = "staging"
os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
os.environ["E2E_OAUTH_SIMULATION_KEY"] = "25006a4abd79f48e8e7a62c2b1b87245a449348ac0a01ac69a18521c7e140444"
os.environ["API_BASE_URL"] = "https://api.staging.netrasystems.ai"
os.environ["AUTH_SERVICE_URL"] = "https://auth.staging.netrasystems.ai"
os.environ["FRONTEND_URL"] = "https://app.staging.netrasystems.ai"
os.environ["WS_BASE_URL"] = "wss://api.staging.netrasystems.ai/ws"
os.environ["REDIS_REQUIRED"] = "false"
os.environ["REDIS_FALLBACK_ENABLED"] = "true"
os.environ["REDIS_PASSWORD"] = ""
os.environ["PYTHONIOENCODING"] = "utf-8"

print("Environment configured:")
print(f"  ENVIRONMENT={os.environ['ENVIRONMENT']}")
print(f"  E2E_OAUTH_SIMULATION_KEY=...configured")
print(f"  API_BASE_URL={os.environ['API_BASE_URL']}")

# Now import pytest AFTER setting environment
import pytest

# Run the test
test_path = sys.argv[1] if len(sys.argv) > 1 else "tests/e2e/test_staging_e2e_comprehensive.py"
print(f"\nRunning test: {test_path}")

# Run pytest directly in the same process
exit_code = pytest.main([test_path, "-v", "--tb=short"])

print(f"\nTest execution completed with exit code: {exit_code}")
sys.exit(exit_code)
