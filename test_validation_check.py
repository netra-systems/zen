#!/usr/bin/env python3
"""
Simple test validation to check if we can import test modules successfully.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def validate_basic_imports():
    """Check if basic test imports work."""
    results = []
    
    try:
        from tests.unified_test_runner import UnifiedTestRunner
        results.append(("✅", "UnifiedTestRunner import successful"))
    except Exception as e:
        results.append(("❌", f"UnifiedTestRunner import failed: {str(e)}"))
    
    try:
        from tests.staging.staging_config import StagingConfig
        results.append(("✅", "StagingConfig import successful"))
    except Exception as e:
        results.append(("❌", f"StagingConfig import failed: {str(e)}"))
    
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        results.append(("✅", "SSotAsyncTestCase import successful"))
    except Exception as e:
        results.append(("❌", f"SSotAsyncTestCase import failed: {str(e)}"))
        
    return results

def main():
    print("🧪 Netra Apex Test Validation Check")
    print("=" * 50)
    
    results = validate_basic_imports()
    
    for status, message in results:
        print(f"{status} {message}")
    
    success_count = sum(1 for status, _ in results if status == "✅")
    total_count = len(results)
    
    print(f"\n📊 Results: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("✅ All basic imports working - ready to run tests")
        return 0
    else:
        print("❌ Some imports failed - need to fix before running tests")
        return 1

if __name__ == "__main__":
    exit(main())