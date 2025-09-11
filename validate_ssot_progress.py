#!/usr/bin/env python3
"""
SSOT Validation Progress Check - Week 1 Interface Standardization

This script validates the progress made in Week 1 of SSOT remediation,
specifically checking interface standardization improvements.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Validate SSOT remediation progress
- Value Impact: Ensure interface standardization prevents runtime failures
- Revenue Impact: Prevent $500K+ ARR disruptions from manager inconsistencies
"""

import sys
import importlib
from typing import Dict, Any, List
import inspect

def check_factory_interface_compliance() -> Dict[str, Any]:
    """Check WebSocketManagerFactory interface compliance."""
    results = {
        'factory_available': False,
        'required_methods_present': [],
        'missing_methods': [],
        'interface_score': 0
    }
    
    try:
        # Import factory
        from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
        results['factory_available'] = True
        
        # Check required methods that failing tests expect
        required_methods = [
            'create_isolated_manager',
            'cleanup_manager', 
            'get_manager_by_user',
            'get_active_connections_count'
        ]
        
        factory = WebSocketManagerFactory()
        
        for method_name in required_methods:
            if hasattr(factory, method_name) and callable(getattr(factory, method_name)):
                results['required_methods_present'].append(method_name)
            else:
                results['missing_methods'].append(method_name)
        
        # Calculate interface score
        results['interface_score'] = (len(results['required_methods_present']) / len(required_methods)) * 100
        
    except Exception as e:
        results['error'] = str(e)
    
    return results

def check_unified_manager_interface_compliance() -> Dict[str, Any]:
    """Check UnifiedWebSocketManager interface compliance."""
    results = {
        'manager_available': False,
        'required_methods_present': [],
        'missing_methods': [],
        'interface_score': 0
    }
    
    try:
        # Import manager
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        results['manager_available'] = True
        
        # Check required methods that failing tests expect
        required_methods = [
            'broadcast_message',
            'get_connection_count', 
            'handle_connection',
            'handle_disconnection',
            'send_agent_event',
            'is_user_connected'
        ]
        
        manager = UnifiedWebSocketManager()
        
        for method_name in required_methods:
            if hasattr(manager, method_name) and callable(getattr(manager, method_name)):
                results['required_methods_present'].append(method_name)
            else:
                results['missing_methods'].append(method_name)
        
        # Calculate interface score
        results['interface_score'] = (len(results['required_methods_present']) / len(required_methods)) * 100
        
    except Exception as e:
        results['error'] = str(e)
    
    return results

def check_canonical_import_availability() -> Dict[str, Any]:
    """Check canonical import standardization."""
    results = {
        'canonical_imports_available': False,
        'import_paths_tested': [],
        'import_errors': []
    }
    
    # Test canonical import paths
    import_tests = [
        ('netra_backend.app.websocket_core.canonical_imports', 'WebSocketManagerFactory'),
        ('netra_backend.app.websocket_core.canonical_imports', 'WebSocketManagerProtocol'),
        ('netra_backend.app.websocket_core.canonical_imports', 'UnifiedWebSocketManager'),
    ]
    
    successful_imports = 0
    
    for module_path, class_name in import_tests:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, class_name):
                results['import_paths_tested'].append(f"✅ {module_path}.{class_name}")
                successful_imports += 1
            else:
                results['import_paths_tested'].append(f"❌ {module_path}.{class_name} (class not found)")
        except ImportError as e:
            results['import_errors'].append(f"{module_path}: {e}")
            results['import_paths_tested'].append(f"❌ {module_path}.{class_name} (import error)")
    
    results['canonical_imports_available'] = successful_imports == len(import_tests)
    results['import_success_rate'] = (successful_imports / len(import_tests)) * 100
    
    return results

def validate_ssot_progress() -> Dict[str, Any]:
    """Main validation function for SSOT progress."""
    print("🔍 SSOT WebSocket Manager Interface Standardization - Progress Check")
    print("=" * 70)
    
    # Check factory interface compliance
    print("\n📦 WebSocket Manager Factory Interface Compliance:")
    factory_results = check_factory_interface_compliance()
    if factory_results['factory_available']:
        print(f"✅ Factory Available: {factory_results['factory_available']}")
        print(f"📊 Interface Score: {factory_results['interface_score']:.1f}%")
        if factory_results['required_methods_present']:
            print(f"✅ Methods Present: {', '.join(factory_results['required_methods_present'])}")
        if factory_results['missing_methods']:
            print(f"❌ Missing Methods: {', '.join(factory_results['missing_methods'])}")
    else:
        print(f"❌ Factory Import Error: {factory_results.get('error', 'Unknown error')}")
    
    # Check unified manager interface compliance  
    print("\n🎯 Unified WebSocket Manager Interface Compliance:")
    manager_results = check_unified_manager_interface_compliance()
    if manager_results['manager_available']:
        print(f"✅ Manager Available: {manager_results['manager_available']}")
        print(f"📊 Interface Score: {manager_results['interface_score']:.1f}%")
        if manager_results['required_methods_present']:
            print(f"✅ Methods Present: {', '.join(manager_results['required_methods_present'])}")
        if manager_results['missing_methods']:
            print(f"❌ Missing Methods: {', '.join(manager_results['missing_methods'])}")
    else:
        print(f"❌ Manager Import Error: {manager_results.get('error', 'Unknown error')}")
    
    # Check canonical imports
    print("\n📋 Canonical Import Standardization:")
    import_results = check_canonical_import_availability()
    print(f"✅ Canonical Imports Available: {import_results['canonical_imports_available']}")
    print(f"📊 Import Success Rate: {import_results['import_success_rate']:.1f}%")
    for import_test in import_results['import_paths_tested']:
        print(f"   {import_test}")
    if import_results['import_errors']:
        print("❌ Import Errors:")
        for error in import_results['import_errors']:
            print(f"   {error}")
    
    # Calculate overall progress
    factory_score = factory_results.get('interface_score', 0)
    manager_score = manager_results.get('interface_score', 0) 
    import_score = import_results.get('import_success_rate', 0)
    
    overall_score = (factory_score + manager_score + import_score) / 3
    
    print("\n📈 OVERALL SSOT INTERFACE STANDARDIZATION PROGRESS:")
    print(f"🎯 Overall Score: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("🎉 EXCELLENT: Interface standardization is nearly complete!")
    elif overall_score >= 70:
        print("✅ GOOD: Significant progress on interface standardization")
    elif overall_score >= 50:
        print("⚠️  MODERATE: Interface standardization in progress")
    else:
        print("❌ NEEDS WORK: Interface standardization requires more effort")
    
    # Recommendations
    print("\n🔧 RECOMMENDATIONS:")
    total_missing = len(factory_results.get('missing_methods', [])) + len(manager_results.get('missing_methods', []))
    if total_missing == 0:
        print("✅ All required interface methods are present")
        print("🎯 Ready to move to Week 2: Protocol Compliance Testing")
    else:
        print(f"⚠️  {total_missing} interface methods still missing")
        print("📋 Complete interface method implementation before proceeding")
    
    return {
        'factory_results': factory_results,
        'manager_results': manager_results,
        'import_results': import_results,
        'overall_score': overall_score,
        'ready_for_week_2': total_missing == 0 and overall_score >= 80
    }

if __name__ == "__main__":
    try:
        results = validate_ssot_progress()
        
        # Exit with appropriate code
        if results['ready_for_week_2']:
            print(f"\n🚀 SUCCESS: Ready for Week 2 of SSOT remediation!")
            sys.exit(0)
        else:
            print(f"\n⚠️  IN PROGRESS: Continue with Week 1 interface standardization")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ VALIDATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)