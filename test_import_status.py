"""Test import status of the codebase"""

import sys
import os
from pathlib import Path
import importlib
import traceback

# Add project to path
sys.path.insert(0, r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
os.chdir(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')

def test_imports():
    """Test importing key modules"""
    
    modules_to_test = [
        # Core modules
        'netra_backend.app.core.unified_logging',
        'netra_backend.app.core.configuration.base',
        'netra_backend.app.core.health.checks',
        
        # WebSocket modules - testing the reported circular import
        'netra_backend.app.ws_manager',
        'netra_backend.app.services.websocket.ws_manager',
        
        # Services
        'netra_backend.app.services.synthetic_data.core_service',
        'netra_backend.app.services.quality_monitoring.service',
        'netra_backend.app.services.corpus.corpus_manager',
        
        # Agents
        'netra_backend.app.agents.base_agent',
        'netra_backend.app.agents.agent_lifecycle',
        
        # Auth
        'auth_service.auth_core.core.jwt_handler',
        'auth_service.main',
    ]
    
    success_count = 0
    failure_count = 0
    failures = []
    
    print("=" * 60)
    print("IMPORT STATUS TEST")
    print("=" * 60)
    
    for module_name in modules_to_test:
        try:
            importlib.import_module(module_name)
            print(f"[PASS] {module_name}")
            success_count += 1
        except Exception as e:
            print(f"[FAIL] {module_name}: {e.__class__.__name__}")
            failure_count += 1
            failures.append({
                'module': module_name,
                'error': str(e),
                'type': e.__class__.__name__
            })
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {success_count} passed, {failure_count} failed")
    print("=" * 60)
    
    if failures:
        print("\nFAILED IMPORTS:")
        for fail in failures:
            print(f"\n{fail['module']}:")
            print(f"  Error Type: {fail['type']}")
            print(f"  Message: {fail['error'][:200]}")
    
    # Test for circular imports between ws_manager modules
    print("\n" + "=" * 60)
    print("CIRCULAR IMPORT TEST: ws_manager <-> websocket.unified")
    print("=" * 60)
    
    try:
        # Clear any cached imports
        if 'netra_backend.app.ws_manager' in sys.modules:
            del sys.modules['netra_backend.app.ws_manager']
        if 'netra_backend.app.services.websocket' in sys.modules:
            del sys.modules['netra_backend.app.services.websocket']
            
        # Try importing both
        import netra_backend.app.ws_manager
        print("[PASS] Imported app.ws_manager")
        
        # Check if websocket.unified exists
        try:
            from netra_backend.app.services.websocket import unified
            print("[PASS] websocket.unified exists and imports successfully")
        except ImportError:
            print("[INFO] websocket.unified does not exist (no circular import possible)")
            
    except Exception as e:
        print(f"[FAIL] Circular import detected: {e}")
        traceback.print_exc()
    
    return success_count, failure_count

if __name__ == "__main__":
    success, failures = test_imports()
    sys.exit(0 if failures == 0 else 1)