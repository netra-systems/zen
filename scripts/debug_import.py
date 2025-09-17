#!/usr/bin/env python3
import sys
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print(f"Python path setup: {project_root}")
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

def test_import(module_name, from_module=None):
    try:
        if from_module:
            exec(f"from {from_module} import {module_name}")
            print(f"✅ SUCCESS: from {from_module} import {module_name}")
        else:
            exec(f"import {module_name}")
            print(f"✅ SUCCESS: import {module_name}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {module_name} - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False

print("\n=== BASIC IMPORTS ===")
test_import("shared")
test_import("isolated_environment", "shared")

print("\n=== TEST FRAMEWORK IMPORTS ===")
test_import("test_framework")
test_import("test_framework.ssot")

print("\n=== SPECIFIC SSOT IMPORTS ===")
test_import("BaseTestCase", "test_framework.ssot")

print("\n=== UNIFIED DOCKER MANAGER ===")
test_import("unified_docker_manager", "test_framework")

print("\n=== TEST CONFIG ===")
test_import("test_config", "test_framework")

print("\n=== DONE ===")