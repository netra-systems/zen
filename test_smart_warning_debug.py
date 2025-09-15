#!/usr/bin/env python3
"""
Debug the smart warning logic to understand why it's not working as expected.
"""

import warnings
import sys
import tempfile
import os

def test_warning_with_file():
    """Test by creating a temporary file with the import statement"""
    
    # Test 1: Specific module import (should NOT warn)
    print("=== Test 1: Specific module import (should NOT warn) ===")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator\n")
        temp_file1 = f.name
    
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Import the module by executing the file
            with open(temp_file1, 'r') as f:
                code = f.read()
            exec(code)
            
            websocket_warnings = [warning for warning in w 
                                if issubclass(warning.category, DeprecationWarning) 
                                and 'websocket_core' in str(warning.message)]
            
            if websocket_warnings:
                print(f"❌ FALSE POSITIVE: Got {len(websocket_warnings)} deprecation warning(s)")
                for warning in websocket_warnings:
                    print(f"    Warning: {warning.message}")
            else:
                print("✅ CORRECT: No deprecation warnings")
                
    finally:
        os.unlink(temp_file1)
    
    print()
    
    # Test 2: Broad import (should warn)
    print("=== Test 2: Broad import (should warn) ===")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("from netra_backend.app.websocket_core import WebSocketManager\n")
        temp_file2 = f.name
    
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Import the module by executing the file
            with open(temp_file2, 'r') as f:
                code = f.read()
            exec(code)
            
            websocket_warnings = [warning for warning in w 
                                if issubclass(warning.category, DeprecationWarning) 
                                and 'websocket_core' in str(warning.message)]
            
            if websocket_warnings:
                print(f"✅ CORRECT: Got {len(websocket_warnings)} deprecation warning(s)")
                for warning in websocket_warnings:
                    print(f"    Warning: {warning.message}")
            else:
                print("❌ MISSING: Expected deprecation warning but got none")
                
    finally:
        os.unlink(temp_file2)

def test_direct_import():
    """Test direct imports to see current behavior"""
    print("=== Direct Import Test ===")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # First test - this should NOT warn according to the issue
        from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        
        websocket_warnings = [warning for warning in w 
                            if issubclass(warning.category, DeprecationWarning) 
                            and 'websocket_core' in str(warning.message)]
        
        print(f"Direct specific import warnings: {len(websocket_warnings)}")
        for warning in websocket_warnings:
            print(f"    Warning: {warning.message}")
    
    # Clear warnings for next test
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Second test - this SHOULD warn
        from netra_backend.app.websocket_core import create_websocket_manager
        
        websocket_warnings = [warning for warning in w 
                            if issubclass(warning.category, DeprecationWarning) 
                            and 'websocket_core' in str(warning.message)]
        
        print(f"Direct broad import warnings: {len(websocket_warnings)}")
        for warning in websocket_warnings:
            print(f"    Warning: {warning.message}")

if __name__ == "__main__":
    test_warning_with_file()
    print()
    test_direct_import()