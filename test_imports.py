#!/usr/bin/env python3
"""
Simple import test to diagnose Golden Path test issues.
"""

import os
import sys
from pathlib import Path

# Set up the project path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"Testing imports from: {PROJECT_ROOT}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

# Set basic environment
os.environ["ENVIRONMENT"] = "staging"
os.environ["TEST_MODE"] = "true"

print("\n=== Testing Basic Imports ===")

try:
    print("1. Testing test_framework imports...")
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
    print("   ✅ SSotAsyncTestCase imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import SSotAsyncTestCase: {e}")

try:
    print("2. Testing netra_backend imports...")
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    print("   ✅ UserExecutionContext imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import UserExecutionContext: {e}")

try:
    print("3. Testing agent imports...")
    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
    print("   ✅ SupervisorAgent imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import SupervisorAgent: {e}")

try:
    print("4. Testing websocket imports...")
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("   ✅ WebSocketManager imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import WebSocketManager: {e}")

try:
    print("5. Testing execution engine factory imports...")
    from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
    print("   ✅ ExecutionEngineFactory imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import ExecutionEngineFactory: {e}")

try:
    print("6. Testing auth integration imports...")
    from netra_backend.app.auth_integration.auth import get_auth_service
    print("   ✅ get_auth_service imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import get_auth_service: {e}")

print("\n=== Testing Golden Path Test Imports ===")

try:
    print("7. Testing simplified golden path test import...")
    from tests.e2e.golden_path.test_simplified_golden_path_e2e import SimplifiedGoldenPathE2ETests
    print("   ✅ SimplifiedGoldenPathE2ETests imported successfully")

    # Try to instantiate
    test_instance = SimplifiedGoldenPathE2ETests()
    print("   ✅ SimplifiedGoldenPathE2ETests instantiated successfully")

except Exception as e:
    print(f"   ❌ Failed to import or instantiate SimplifiedGoldenPathE2ETests: {e}")
    import traceback
    traceback.print_exc()

try:
    print("8. Testing staging validation test import...")
    from tests.e2e.staging.test_golden_path_end_to_end_staging_validation import GoldenPathEndToEndStagingValidationTests
    print("   ✅ GoldenPathEndToEndStagingValidationTests imported successfully")

    # Try to instantiate
    test_instance = GoldenPathEndToEndStagingValidationTests()
    print("   ✅ GoldenPathEndToEndStagingValidationTests instantiated successfully")

except Exception as e:
    print(f"   ❌ Failed to import or instantiate GoldenPathEndToEndStagingValidationTests: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Import Test Complete ===")
print("If all imports succeeded, the tests should be runnable.")