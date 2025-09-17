#!/usr/bin/env python
"""
Test script to verify the xfailed parameter fix for SSotBaseTestCase.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
    
    # Test instantiation with xfailed parameter
    print("Testing SSotBaseTestCase instantiation with xfailed parameter...")
    
    test1 = SSotBaseTestCase(xfailed=True)
    print("✅ SUCCESS: SSotBaseTestCase accepts xfailed=True")
    
    test2 = SSotBaseTestCase(xfailed=False, xpassed=True)  
    print("✅ SUCCESS: SSotBaseTestCase accepts multiple pytest parameters")
    
    test3 = SSotBaseTestCase()
    print("✅ SUCCESS: SSotBaseTestCase works without parameters")
    
    print("\n🎉 ALL TESTS PASSED: xfailed parameter issue is FIXED!")
    
except Exception as e:
    print(f"❌ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)