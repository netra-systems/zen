#!/usr/bin/env python3
"""
Simple runner for WebSocket SSOT validation test
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Import the test
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "unit" / "websocket_ssot"))

# Set up basic environment
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "test"

# Run the test
if __name__ == "__main__":
    from test_websocket_manager_single_implementation_validation import TestWebSocketManagerSingleImplementationValidation
    
    # Create test instance
    test_instance = TestWebSocketManagerSingleImplementationValidation()
    
    # Run setup
    test_instance.setup_method()
    
    try:
        # Run the test method
        print("Running WebSocket SSOT validation test...")
        test_instance.test_websocket_manager_single_implementation_ssot_validation()
        print("✅ Test PASSED - No SSOT violations detected")
    except AssertionError as e:
        print(f"❌ Test FAILED (Expected) - SSOT violations detected:")
        print(f"   {e}")
        print("\nThis failure proves the SSOT violations exist and need to be fixed.")
        return_code = 1
    except Exception as e:
        print(f"💥 Test ERROR - Unexpected error:")
        print(f"   {e}")
        return_code = 2
    finally:
        # Run teardown
        test_instance.teardown_method()
    
    # Show metrics
    metrics = test_instance.get_all_metrics()
    print(f"\nTest Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    sys.exit(return_code if 'return_code' in locals() else 0)