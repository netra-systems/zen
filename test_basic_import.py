#!/usr/bin/env python3
"""Test basic test_framework imports."""

import sys
import traceback

print("Testing basic test_framework imports...")

try:
    import test_framework
    print("✅ SUCCESS: test_framework imported")
    print(f"   PROJECT_ROOT: {test_framework.PROJECT_ROOT}")
    print(f"   Version: {test_framework.__version__}")

    # Test if UnifiedDockerManager is available
    if hasattr(test_framework, 'UnifiedDockerManager') and test_framework.UnifiedDockerManager:
        print("✅ SUCCESS: UnifiedDockerManager available")
    else:
        print("⚠️  WARNING: UnifiedDockerManager not available")

    # Test if SSOT classes are available
    if hasattr(test_framework, 'SSotBaseTestCase') and test_framework.SSotBaseTestCase:
        print("✅ SUCCESS: SSotBaseTestCase available")
    else:
        print("⚠️  WARNING: SSotBaseTestCase not available")

except Exception as e:
    print(f"❌ FAILED: test_framework import - {e}")
    print(f"   Traceback: {traceback.format_exc()}")

try:
    from test_framework.ssot import BaseTestCase
    print("✅ SUCCESS: test_framework.ssot.BaseTestCase imported")
except Exception as e:
    print(f"❌ FAILED: test_framework.ssot.BaseTestCase - {e}")

try:
    from test_framework.unified_docker_manager import UnifiedDockerManager
    print("✅ SUCCESS: test_framework.unified_docker_manager.UnifiedDockerManager imported")
except Exception as e:
    print(f"❌ FAILED: test_framework.unified_docker_manager.UnifiedDockerManager - {e}")

print("Test complete.")