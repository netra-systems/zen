#!/usr/bin/env python3
"""
Test script to debug why Issue #1144 warning isn't being triggered.
"""
import warnings
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_warning_with_explicit_file():
    """Test warning detection with explicit file creation"""
    
    # Create a test file with problematic import
    test_file_content = '''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.simplefilter("always")

# This should trigger the warning
from netra_backend.app.websocket_core import WebSocketManager

print("Import completed")
'''
    
    with open("/tmp/test_problematic_import.py", "w") as f:
        f.write(test_file_content)
    
    print("Created test file with problematic import")
    print("Running it...")
    
    # Execute the test file
    import subprocess
    result = subprocess.run([sys.executable, "/tmp/test_problematic_import.py"], 
                          capture_output=True, text=True, cwd=os.getcwd())
    
    print(f"Exit code: {result.returncode}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    
    # Check if warning was in the output
    if "ISSUE #1144" in result.stderr:
        print("✅ Issue #1144 warning was correctly triggered!")
        return True
    else:
        print("❌ Issue #1144 warning was NOT triggered")
        return False

def test_direct_stack_inspection():
    """Test the warning detection logic directly"""
    
    # Import the warning function and test it
    from netra_backend.app.websocket_core import _check_import_pattern_and_warn
    
    print("Testing the warning function directly...")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Call the function directly
        _check_import_pattern_and_warn()
        
        print(f"Captured {len(w)} warnings")
        for warning in w:
            print(f"Warning: {warning.message}")
            if "ISSUE #1144" in str(warning.message):
                print("✅ Found Issue #1144 warning!")
                return True
    
    print("❌ No Issue #1144 warning found in direct test")
    return False

def main():
    print("Testing Issue #1144 warning detection...")
    print("=" * 50)
    
    print("\nTest 1: External file with problematic import")
    result1 = test_warning_with_explicit_file()
    
    print("\nTest 2: Direct stack inspection")
    result2 = test_direct_stack_inspection()
    
    print("\n" + "=" * 50)
    if result1:
        print("✅ Warning detection working correctly!")
        return 0
    else:
        print("❌ Warning detection has issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())