#!/usr/bin/env python3
"""Test import checker for Golden Path Tests"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"Current working directory: {Path.cwd()}")
print(f"Python path (first 3): {sys.path[:3]}")

# Test imports one by one - Golden Path focused
imports_to_test = [
    "shared.isolated_environment",
    "test_framework.ssot.base_test_case",
    "shared.id_generation.unified_id_generator",
    "netra_backend.app.websocket_core.types",
    "netra_backend.app.websocket_core.canonical_import_patterns",
    "netra_backend.app.websocket_core.unified_websocket_auth",
]

for import_name in imports_to_test:
    try:
        __import__(import_name)
        print(f"✅ SUCCESS: {import_name}")
    except ImportError as e:
        print(f"❌ IMPORT ERROR: {import_name} - {e}")
    except Exception as e:
        print(f"⚠️  EXECUTION ERROR: {import_name} - {e}")

print("\n" + "="*50)
print("Attempting to import Golden Path test classes...")

# Test golden path unit test import
try:
    from tests.unit.golden_path.test_golden_path_auth_coordination import GoldenPathAuthCoordinationTests
    print("✅ GoldenPathAuthCoordinationTests imported successfully")
    
    # Try to create instance
    test_instance = GoldenPathAuthCoordinationTests()
    print("✅ Golden Path unit test instance created successfully")
    
except Exception as e:
    print(f"❌ Failed to import Golden Path unit test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Attempting Golden Path integration test import...")

try:
    from tests.integration.goldenpath.test_websocket_auth_integration_no_docker import GoldenPathWebSocketAuthNonDockerTests
    print("✅ GoldenPathWebSocketAuthNonDockerTests imported successfully")
    
    test_instance = GoldenPathWebSocketAuthNonDockerTests()
    print("✅ Golden Path integration test instance created successfully")
    
except Exception as e:
    print(f"❌ Failed to import Golden Path integration test: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Golden Path import test complete!")