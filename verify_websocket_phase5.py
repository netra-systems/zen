#!/usr/bin/env python3
"""
Issue #186 Phase 5 Verification Script

This script verifies that the Phase 5 WebSocket SSOT consolidation fixes are working correctly:
1. Import consolidation is successful
2. No class name conflicts exist
3. Basic WebSocket manager functionality works
4. SSOT patterns are enforced
"""

import sys
import os
import traceback
from typing import Dict, Any

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_canonical_imports() -> Dict[str, Any]:
    """Test that canonical imports work correctly."""
    print("🔍 Testing canonical imports...")
    
    results = {
        'canonical_imports_success': False,
        'websocket_manager_creation': False,
        'ssot_validation': False,
        'errors': []
    }
    
    try:
        # Test canonical import path
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
        from netra_backend.app.websocket_core.canonical_imports import WebSocketManagerProtocol
        
        results['canonical_imports_success'] = True
        print("✅ Canonical imports successful")
        
        # Test WebSocket manager creation
        try:
            # Create a test user context
            from shared.types.core_types import UserID
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            
            user_context = UserExecutionContext(
                user_id="test_user_phase5",
                thread_id="test_thread_phase5",
                session_id="test_session_phase5"
            )
            
            # Create WebSocket manager using SSOT function
            manager = get_websocket_manager(user_context)
            
            if manager is not None:
                results['websocket_manager_creation'] = True
                print("✅ WebSocket manager creation successful")
                
                # Test basic manager functionality
                if hasattr(manager, 'user_context') and hasattr(manager, 'mode'):
                    print(f"✅ Manager has required attributes: user_context={manager.user_context}, mode={manager.mode}")
                else:
                    results['errors'].append("Manager missing required attributes")
                    
            else:
                results['errors'].append("Manager creation returned None")
                
        except Exception as manager_error:
            results['errors'].append(f"Manager creation failed: {manager_error}")
            print(f"❌ Manager creation failed: {manager_error}")
            
    except Exception as import_error:
        results['errors'].append(f"Import error: {import_error}")
        print(f"❌ Import error: {import_error}")
        
    return results

def test_ssot_compliance() -> Dict[str, Any]:
    """Test SSOT compliance and no duplicate classes."""
    print("\n🔍 Testing SSOT compliance...")
    
    results = {
        'no_duplicate_classes': False,
        'import_consolidation': False,
        'errors': []
    }
    
    try:
        # Test that imports are consolidated
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        
        # These should be the same class (aliases)
        if WebSocketManager == UnifiedWebSocketManager:
            results['import_consolidation'] = True
            print("✅ Import consolidation successful - aliases point to same class")
        else:
            results['errors'].append("WebSocketManager and UnifiedWebSocketManager are different classes")
            
        # Test that we don't have multiple WebSocketManager class definitions
        import inspect
        import netra_backend.app.websocket_core.websocket_manager as ws_module
        
        websocket_classes = []
        for name, obj in inspect.getmembers(ws_module):
            if (inspect.isclass(obj) and 
                'WebSocketManager' in name and 
                name not in ['WebSocketManagerProtocol', 'WebSocketManagerMode']):
                websocket_classes.append(name)
                
        if len(websocket_classes) <= 2:  # Allow WebSocketManager and WebSocketConnectionManager aliases
            results['no_duplicate_classes'] = True
            print(f"✅ No excessive WebSocket manager classes found: {websocket_classes}")
        else:
            results['errors'].append(f"Too many WebSocket manager classes: {websocket_classes}")
            
    except Exception as ssot_error:
        results['errors'].append(f"SSOT compliance test failed: {ssot_error}")
        print(f"❌ SSOT compliance test failed: {ssot_error}")
        
    return results

def test_phase5_specific_fixes() -> Dict[str, Any]:
    """Test Phase 5 specific fixes for Issue #186."""
    print("\n🔍 Testing Phase 5 specific fixes...")
    
    results = {
        'class_naming_fixed': False,
        'import_paths_consolidated': False,
        'errors': []
    }
    
    try:
        # Verify that the main implementation doesn't have "WebSocketManager" in its class name
        from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation
        
        # The implementation class should not contain "WebSocketManager" in its name
        if "WebSocketManager" not in _UnifiedWebSocketManagerImplementation.__name__:
            results['class_naming_fixed'] = True
            print(f"✅ Implementation class properly named: {_UnifiedWebSocketManagerImplementation.__name__}")
        else:
            results['errors'].append(f"Implementation class still contains 'WebSocketManager': {_UnifiedWebSocketManagerImplementation.__name__}")
            
        # Test that canonical imports module provides SSOT
        from netra_backend.app.websocket_core.canonical_imports import validate_canonical_import_usage
        
        validation_results = validate_canonical_import_usage()
        if validation_results.get('canonical_imports_available', False):
            results['import_paths_consolidated'] = True
            print("✅ Canonical import validation successful")
        else:
            results['errors'].append("Canonical import validation failed")
            
    except Exception as phase5_error:
        results['errors'].append(f"Phase 5 specific test failed: {phase5_error}")
        print(f"❌ Phase 5 specific test failed: {phase5_error}")
        traceback.print_exc()
        
    return results

def main():
    """Run all verification tests."""
    print("🚀 Starting Issue #186 Phase 5 Verification")
    print("=" * 60)
    
    all_results = {}
    
    # Test 1: Canonical imports
    all_results['canonical_imports'] = test_canonical_imports()
    
    # Test 2: SSOT compliance
    all_results['ssot_compliance'] = test_ssot_compliance()
    
    # Test 3: Phase 5 specific fixes
    all_results['phase5_fixes'] = test_phase5_specific_fixes()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    all_errors = []
    
    for test_name, test_results in all_results.items():
        print(f"\n{test_name.upper().replace('_', ' ')}:")
        for check_name, check_result in test_results.items():
            if check_name != 'errors' and isinstance(check_result, bool):
                total_tests += 1
                status = "✅ PASS" if check_result else "❌ FAIL"
                print(f"  {check_name}: {status}")
                if check_result:
                    passed_tests += 1
                    
        if test_results.get('errors'):
            all_errors.extend(test_results['errors'])
            
    print(f"\n🎯 OVERALL RESULT: {passed_tests}/{total_tests} tests passed")
    
    if all_errors:
        print(f"\n❌ ERRORS DETECTED ({len(all_errors)}):")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
    
    if passed_tests == total_tests and not all_errors:
        print("\n🎉 ALL TESTS PASSED - Phase 5 verification successful!")
        return True
    else:
        print(f"\n⚠️  VERIFICATION INCOMPLETE - {total_tests - passed_tests} failures, {len(all_errors)} errors")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)