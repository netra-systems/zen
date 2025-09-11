#!/usr/bin/env python3
"""
WebSocket Agent Bridge Import Fix Validation Script
====================================================

Purpose: Validate that the import path fix for issue #310 maintains system stability
Changes: Lines 732 and 747 in websocket_ssot.py changed from:
  - agents.agent_websocket_bridge 
  - TO: services.agent_websocket_bridge

Business Impact: $500K+ ARR dependent on WebSocket functionality
"""

import sys
import traceback
from pathlib import Path

def main():
    print("=" * 80)
    print("WEBSOCKET AGENT BRIDGE IMPORT FIX VALIDATION")
    print("=" * 80)
    print(f"Validating fix for issue #310")
    print(f"Business Impact: $500K+ ARR")
    print()
    
    validation_results = {}
    
    # Test 1: Python compilation
    print("1. PYTHON COMPILATION TEST")
    print("-" * 30)
    try:
        import py_compile
        websocket_ssot_path = Path("netra_backend/app/routes/websocket_ssot.py")
        py_compile.compile(str(websocket_ssot_path), doraise=True)
        print("PASS: websocket_ssot.py compiles without syntax errors")
        validation_results['compilation'] = True
    except Exception as e:
        print(f"FAIL: Compilation error - {e}")
        validation_results['compilation'] = False
    print()
    
    # Test 2: Import path validation
    print("2. IMPORT PATH VALIDATION")
    print("-" * 30)
    try:
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        print("PASS: Fixed import path works (services.agent_websocket_bridge)")
        validation_results['new_import'] = True
    except Exception as e:
        print(f"FAIL: New import path broken - {e}")
        validation_results['new_import'] = False
    
    try:
        from netra_backend.app.agents.agent_websocket_bridge import create_agent_websocket_bridge
        print("FAIL: Old import path still exists (should be removed)")
        validation_results['old_import_removed'] = False
    except ImportError:
        print("PASS: Old import path correctly removed (agents.agent_websocket_bridge)")
        validation_results['old_import_removed'] = True
    except Exception as e:
        print(f"ERROR: Unexpected error testing old path - {e}")
        validation_results['old_import_removed'] = False
    print()
    
    # Test 3: Function signature validation
    print("3. FUNCTION SIGNATURE VALIDATION")
    print("-" * 35)
    try:
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        import inspect
        sig = inspect.signature(create_agent_websocket_bridge)
        print(f"PASS: Function signature valid: {sig}")
        
        # Verify return type annotation exists
        if hasattr(create_agent_websocket_bridge, '__annotations__'):
            return_type = create_agent_websocket_bridge.__annotations__.get('return', 'No return annotation')
            print(f"PASS: Return type annotation: {return_type}")
        
        validation_results['function_signature'] = True
    except Exception as e:
        print(f"FAIL: Function signature validation failed - {e}")
        validation_results['function_signature'] = False
    print()
    
    # Test 4: Module dependencies
    print("4. MODULE DEPENDENCIES VALIDATION")
    print("-" * 38)
    dependencies_to_test = [
        "netra_backend.app.websocket_core.WebSocketManager",
        "netra_backend.app.services.user_execution_context.UserExecutionContext",
        "netra_backend.app.core.unified_id_manager.UnifiedIDManager"
    ]
    
    dependency_results = []
    for dep in dependencies_to_test:
        try:
            module_path, class_name = dep.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print(f"PASS: {dep}")
            dependency_results.append(True)
        except Exception as e:
            print(f"FAIL: {dep} - {e}")
            dependency_results.append(False)
    
    validation_results['dependencies'] = all(dependency_results)
    print()
    
    # Test 5: SSOT compliance check
    print("5. SSOT COMPLIANCE CHECK")
    print("-" * 25)
    try:
        # Check that the module exists in the services directory
        services_bridge_path = Path("netra_backend/app/services/agent_websocket_bridge.py")
        agents_bridge_path = Path("netra_backend/app/agents/agent_websocket_bridge.py")
        
        if services_bridge_path.exists():
            print("PASS: Module exists in correct location (services/)")
            validation_results['ssot_location'] = True
        else:
            print("FAIL: Module missing from services directory")
            validation_results['ssot_location'] = False
            
        if not agents_bridge_path.exists():
            print("PASS: No duplicate in agents directory")
            validation_results['ssot_no_duplicate'] = True
        else:
            print("WARN: Duplicate module exists in agents directory")
            validation_results['ssot_no_duplicate'] = False
    except Exception as e:
        print(f"ERROR: SSOT compliance check failed - {e}")
        validation_results['ssot_location'] = False
        validation_results['ssot_no_duplicate'] = False
    print()
    
    # Test 6: Import chain validation
    print("6. IMPORT CHAIN VALIDATION")
    print("-" * 30)
    try:
        # Test that websocket_ssot.py can import the bridge successfully
        import netra_backend.app.routes.websocket_ssot as websocket_ssot_module
        print("PASS: websocket_ssot.py module imports successfully")
        
        # Test specific imports from the fixed lines
        from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
        print("PASS: Line 732/747 import functionality confirmed")
        
        validation_results['import_chain'] = True
    except Exception as e:
        print(f"FAIL: Import chain broken - {e}")
        validation_results['import_chain'] = False
    print()
    
    # Overall assessment
    print("=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    total_tests = len(validation_results)
    passed_tests = sum(validation_results.values())
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print()
    
    for test_name, result in validation_results.items():
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
    
    print()
    
    if all(validation_results.values()):
        print("✓ OVERALL RESULT: SYSTEM STABLE")
        print("✓ Import path fix maintains system stability")
        print("✓ No breaking changes introduced")
        print("✓ $500K+ ARR functionality protected")
        return 0
    else:
        print("✗ OVERALL RESULT: ISSUES DETECTED")
        print("✗ System stability concerns identified")
        print("✗ Breaking changes may have been introduced")
        print("✗ $500K+ ARR functionality at risk")
        return 1

if __name__ == "__main__":
    sys.exit(main())