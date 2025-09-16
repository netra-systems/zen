#!/usr/bin/env python3
"""
Test script to check if real-world imports are getting unexpected warnings.
"""
import warnings
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_real_world_imports():
    """Test real-world imports to see if they get unexpected warnings"""
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        
        print("Testing real-world imports...")
        
        # Test import from routes/websocket_ssot.py which was showing warnings
        try:
            from netra_backend.app.routes import websocket_ssot
            print("✓ routes.websocket_ssot import successful")
        except Exception as e:
            print(f"❌ routes.websocket_ssot import failed: {e}")
        
        # Test specific imports from known good files
        try:
            from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
            print("✓ Direct websocket_manager import successful")
        except Exception as e:
            print(f"❌ Direct websocket_manager import failed: {e}")
        
        # Check for Issue #1144 warnings
        issue_1144_warnings = [warning for warning in w if 'ISSUE #1144' in str(warning.message)]
        
        print(f'\nTotal warnings captured: {len(w)}')
        print(f'Issue #1144 warnings: {len(issue_1144_warnings)}')
        
        for warning in issue_1144_warnings:
            print(f'\nIssue #1144 Warning detected:')
            print(f'  Message: {warning.message}')
            print(f'  File: {warning.filename}:{warning.lineno}')
            
        # Look for any deprecation warnings about specific imports
        other_deprecation_warnings = [warning for warning in w 
                                    if issubclass(warning.category, DeprecationWarning) 
                                    and 'ISSUE #1144' not in str(warning.message)]
        
        print(f'Other deprecation warnings: {len(other_deprecation_warnings)}')
        for warning in other_deprecation_warnings[:3]:  # Show first 3
            print(f'  - {warning.message}')
            
        return len(issue_1144_warnings) == 0  # Should be 0 for legitimate imports

if __name__ == "__main__":
    if test_real_world_imports():
        print("\n✅ No unexpected Issue #1144 warnings detected")
        sys.exit(0)
    else:
        print("\n❌ Unexpected Issue #1144 warnings detected")
        sys.exit(1)