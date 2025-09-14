#!/usr/bin/env python3
"""
Script to set E2E environment variables for testing
"""
import os

# Set critical E2E testing environment variables
os.environ["E2E_OAUTH_SIMULATION_KEY"] = "staging-e2e-test-bypass-key-2025"
os.environ["ENVIRONMENT"] = "staging"
os.environ["TEST_ENV"] = "staging"

# Verify they are set
from shared.isolated_environment import get_env
env = get_env()

print("E2E Environment Variables Set:")
print(f"E2E_OAUTH_SIMULATION_KEY: {env.get('E2E_OAUTH_SIMULATION_KEY')}")
print(f"ENVIRONMENT: {env.get('ENVIRONMENT')}")
print(f"TEST_ENV: {env.get('TEST_ENV')}")

# Import auth helper to test if it can now get the bypass key
try:
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
    auth_helper = E2EAuthHelper(environment="staging")
    print(f"Auth Helper Environment: {auth_helper.environment}")
    print(f"Auth Helper Can Get Bypass Key: {bool(env.get('E2E_OAUTH_SIMULATION_KEY'))}")
except Exception as e:
    print(f"Error initializing auth helper: {e}")