#!/usr/bin/env python3
"""
Test Framework Import Verification Script

This script verifies all test framework imports are working correctly
and identifies any missing components that could cause NameError issues.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_import(module_name, item_name=None):
    """Test importing a module or specific item from a module."""
    try:
        if item_name:
            module = __import__(module_name, fromlist=[item_name])
            getattr(module, item_name)
            print(f"OK: from {module_name} import {item_name}")
        else:
            __import__(module_name)
            print(f"OK: import {module_name}")
        return True
    except Exception as e:
        print(f"ERROR: {module_name}.{item_name or ''}: {e}")
        return False

def main():
    """Run comprehensive test framework import verification."""
    print("=" * 60)
    print("TEST FRAMEWORK IMPORT VERIFICATION")
    print("=" * 60)
    
    # Core test framework modules
    core_modules = [
        "test_framework.decorators",
        "test_framework.ssot.base_test_case", 
        "test_framework.ssot.database",
        "test_framework.ssot.mock_factory",
        "test_framework.unified_docker_manager",
        "test_framework.service_dependencies",
        "test_framework.resource_monitor"
    ]
    
    print("\n1. Core Module Imports:")
    print("-" * 30)
    core_success = 0
    for module in core_modules:
        if test_import(module):
            core_success += 1
    
    # Test framework decorators
    decorator_imports = [
        ("test_framework.decorators", "requires_real_database"),
        ("test_framework.decorators", "requires_real_redis"),
        ("test_framework.decorators", "requires_real_services"),
        ("test_framework.decorators", "requires_docker"),
        ("test_framework.decorators", "requires_websocket"),
        ("test_framework.decorators", "mission_critical"),
        ("test_framework.decorators", "race_condition_test"),
        ("test_framework.decorators", "experimental_test"),
        ("test_framework.decorators", "feature_flag"),
        ("test_framework.decorators", "requires_feature"),
        ("test_framework.decorators", "tdd_test"),
        ("test_framework.service_dependencies", "requires_services"),
    ]
    
    print("\n2. Decorator Imports:")
    print("-" * 30)
    decorator_success = 0
    for module, decorator in decorator_imports:
        if test_import(module, decorator):
            decorator_success += 1
    
    # SSOT imports
    ssot_imports = [
        ("test_framework.ssot.base_test_case", "SSotBaseTestCase"),
        ("test_framework.ssot.base_test_case", "SSotAsyncTestCase"),
        ("test_framework.ssot.database", "DatabaseTestHelper"),
        ("test_framework.ssot.mock_factory", "SSotMockFactory"),
    ]
    
    print("\n3. SSOT Component Imports:")
    print("-" * 30)
    ssot_success = 0
    for module, component in ssot_imports:
        if test_import(module, component):
            ssot_success += 1
    
    # Test the specific imports from the failing test file
    print("\n4. Race Condition Test File Imports:")
    print("-" * 30)
    race_test_imports = [
        ("test_framework.ssot.base_test_case", "SSotBaseTestCase"),
        ("test_framework.ssot.database", "DatabaseTestHelper"),
        ("test_framework.decorators", "requires_real_database"),
    ]
    
    race_success = 0
    for module, component in race_test_imports:
        if test_import(module, component):
            race_success += 1
    
    # Summary
    total_tests = len(core_modules) + len(decorator_imports) + len(ssot_imports) + len(race_test_imports)
    total_success = core_success + decorator_success + ssot_success + race_success
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Core Modules:     {core_success}/{len(core_modules)}")
    print(f"Decorators:       {decorator_success}/{len(decorator_imports)}")
    print(f"SSOT Components:  {ssot_success}/{len(ssot_imports)}")
    print(f"Race Test Imports: {race_success}/{len(race_test_imports)}")
    print(f"Overall:          {total_success}/{total_tests}")
    
    if total_success == total_tests:
        print("\nALL TEST FRAMEWORK IMPORTS WORKING")
        return 0
    else:
        print(f"\n{total_tests - total_success} IMPORT FAILURES DETECTED")
        return 1

if __name__ == "__main__":
    sys.exit(main())