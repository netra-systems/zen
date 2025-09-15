#!/usr/bin/env python3
"""
Test script to verify that problematic imports (direct imports from websocket_core)
DO trigger deprecation warnings.
"""
import warnings
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    
    print("Testing problematic imports...")
    
    # This SHOULD trigger a warning (direct import from websocket_core)
    from netra_backend.app.websocket_core import WebSocketManager
    print("✓ Direct import from websocket_core: WARNING expected")
    
    # Check if deprecation warnings were triggered
    deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
    issue_1144_warnings = [warning for warning in deprecation_warnings if "ISSUE #1144" in str(warning.message)]
    
    if issue_1144_warnings:
        print(f"\n✅ SUCCESS: {len(issue_1144_warnings)} Issue #1144 deprecation warnings were triggered as expected:")
        for warning in issue_1144_warnings:
            print(f"  - {warning.message}")
        sys.exit(0)
    else:
        print(f"\n❌ FAILURE: Expected deprecation warning was not triggered")
        print(f"Total warnings captured: {len(w)}")
        print(f"Deprecation warnings: {len(deprecation_warnings)}")
        if deprecation_warnings:
            print("Deprecation warnings found:")
            for warning in deprecation_warnings:
                print(f"  - {warning.message}")
        sys.exit(1)