#!/usr/bin/env python3
"""Test import checker for E2E critical tests"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"PROJECT_ROOT: {PROJECT_ROOT}")
print(f"Current working directory: {Path.cwd()}")
print(f"Python path (first 3): {sys.path[:3]}")

# Test imports one by one
imports_to_test = [
    "shared.isolated_environment",
    "tests.e2e.config", 
    "tests.e2e.real_services_manager",
    "tests.e2e.enforce_real_services",
    "tests.e2e.test_environment_config",
    "tests.e2e.critical.test_auth_jwt_critical",
    "tests.e2e.critical.test_service_health_critical"
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
print("Attempting to import and run test classes...")

try:
    from tests.e2e.critical.test_auth_jwt_critical import CriticalJWTAuthenticationTests
    print("✅ CriticalJWTAuthenticationTests imported successfully")
    
    # Try to create instance
    test_instance = CriticalJWTAuthenticationTests()
    print("✅ Test instance created successfully")
    
    # Try setup (this will likely fail due to services not running)
    try:
        test_instance.setup_method()
        print("✅ Setup method completed successfully")
    except Exception as e:
        print(f"⚠️  Setup method failed (expected if services not running): {e}")
        
except Exception as e:
    print(f"❌ Failed to import/instantiate test class: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50)
print("Attempting service health test...")

try:
    from tests.e2e.critical.test_service_health_critical import CriticalServiceHealthTests
    print("✅ CriticalServiceHealthTests imported successfully")
    
    test_instance = CriticalServiceHealthTests()
    print("✅ Service health test instance created successfully")
    
    try:
        test_instance.setup_method()
        print("✅ Service health setup completed successfully")
    except Exception as e:
        print(f"⚠️  Service health setup failed (expected if services not running): {e}")
        
except Exception as e:
    print(f"❌ Failed to import/instantiate service health test: {e}")
    import traceback
    traceback.print_exc()