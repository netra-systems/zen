#!/usr/bin/env python3
"""
Test script to verify that legitimate imports (specific module imports) 
do NOT trigger deprecation warnings.
"""
import warnings
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    
    # These should NOT trigger warnings (legitimate imports)
    print("Testing legitimate imports...")
    
    # Specific module imports - these should be SAFE
    from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
    print("✓ Import from websocket_manager: NO WARNING expected")
    
    from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
    print("✓ Import from unified_emitter: NO WARNING expected")
    
    from netra_backend.app.websocket_core.handlers import MessageRouter
    print("✓ Import from handlers: NO WARNING expected")
    
    # Check specifically for Issue #1144 warnings (ignore other deprecation warnings)
    issue_1144_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning) and "ISSUE #1144" in str(warning.message)]
    
    if issue_1144_warnings:
        print(f"\n❌ FAILURE: {len(issue_1144_warnings)} Issue #1144 deprecation warnings were triggered when they shouldn't be:")
        for warning in issue_1144_warnings:
            print(f"  - {warning.message}")
        sys.exit(1)
    else:
        print(f"\n✅ SUCCESS: No Issue #1144 deprecation warnings triggered for legitimate imports")
        print(f"Total warnings captured: {len(w)}")
        total_deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        print(f"Total deprecation warnings (other): {len(total_deprecation_warnings)}")
        sys.exit(0)