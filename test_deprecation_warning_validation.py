#!/usr/bin/env python3
"""
Direct validation of Issue #1236 - WebSocket Import Deprecation Warning False Positives

This script tests the exact issue reported: specific module imports from websocket_core
triggering false positive deprecation warnings.

Test Scenarios:
1. Specific module imports (should NOT warn) - FALSE POSITIVE ISSUE
2. Broad __init__.py imports (should warn) - CORRECT BEHAVIOR
3. Edge cases and boundary conditions
"""

import warnings
import sys
import os
from pathlib import Path

def test_specific_module_imports_should_not_warn():
    """Test that specific module imports do NOT trigger deprecation warnings (Issue #1236)"""
    print("=" * 80)
    print("TEST 1: Specific Module Imports (Should NOT warn)")
    print("=" * 80)
    
    test_imports = [
        "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator",
        "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager", 
        "from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol",
        "from netra_backend.app.websocket_core.unified_emitter import UnifiedEmitter"
    ]
    
    results = {}
    
    for import_statement in test_imports:
        print(f"\nTesting: {import_statement}")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                exec(import_statement)
                
                # Filter for websocket_core deprecation warnings
                websocket_warnings = [
                    warning for warning in w 
                    if (issubclass(warning.category, DeprecationWarning) and 
                        'websocket_core' in str(warning.message))
                ]
                
                if websocket_warnings:
                    print(f"  ❌ FALSE POSITIVE: Got {len(websocket_warnings)} deprecation warning(s)")
                    for warning in websocket_warnings:
                        print(f"     Warning: {warning.message}")
                        print(f"     File: {warning.filename}:{warning.lineno}")
                    results[import_statement] = {"warnings": len(websocket_warnings), "status": "FALSE_POSITIVE"}
                else:
                    print(f"  ✅ CORRECT: No deprecation warnings")
                    results[import_statement] = {"warnings": 0, "status": "CORRECT"}
                    
            except ImportError as e:
                print(f"  ⚠️  Import failed: {e}")
                results[import_statement] = {"warnings": 0, "status": "IMPORT_FAILED", "error": str(e)}
    
    return results

def test_broad_init_imports_should_warn():
    """Test that broad __init__.py imports DO trigger deprecation warnings (correct behavior)"""
    print("\n" + "=" * 80)
    print("TEST 2: Broad __init__.py Imports (Should warn)")
    print("=" * 80)
    
    test_imports = [
        "from netra_backend.app.websocket_core import WebSocketManager",
        "from netra_backend.app.websocket_core import create_websocket_manager",
        "from netra_backend.app.websocket_core import UnifiedEventValidator"
    ]
    
    results = {}
    
    for import_statement in test_imports:
        print(f"\nTesting: {import_statement}")
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                exec(import_statement)
                
                # Filter for websocket_core deprecation warnings
                websocket_warnings = [
                    warning for warning in w 
                    if (issubclass(warning.category, DeprecationWarning) and 
                        'websocket_core' in str(warning.message))
                ]
                
                if websocket_warnings:
                    print(f"  ✅ CORRECT: Got {len(websocket_warnings)} deprecation warning(s)")
                    for warning in websocket_warnings:
                        print(f"     Warning: {warning.message}")
                    results[import_statement] = {"warnings": len(websocket_warnings), "status": "CORRECT"}
                else:
                    print(f"  ❌ MISSING: Expected deprecation warning but got none")
                    results[import_statement] = {"warnings": 0, "status": "MISSING_WARNING"}
                    
            except ImportError as e:
                print(f"  ⚠️  Import failed: {e}")
                results[import_statement] = {"warnings": 0, "status": "IMPORT_FAILED", "error": str(e)}
    
    return results

def test_websocket_error_validator_issue():
    """Test the exact issue from websocket_error_validator.py line 32"""
    print("\n" + "=" * 80)
    print("TEST 3: websocket_error_validator.py Issue (Line 32)")
    print("=" * 80)
    
    # This is the exact import causing the false positive
    import_statement = "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator"
    
    print(f"Testing problematic import: {import_statement}")
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        try:
            exec(import_statement)
            
            # Filter for websocket_core deprecation warnings
            websocket_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            print(f"\nResults:")
            print(f"  Total warnings captured: {len(w)}")
            print(f"  WebSocket core warnings: {len(websocket_warnings)}")
            
            if websocket_warnings:
                print(f"  ❌ ISSUE CONFIRMED: False positive deprecation warning triggered")
                print(f"  This is the exact issue described in #1236")
                for warning in websocket_warnings:
                    print(f"     Warning: {warning.message}")
                    print(f"     File: {warning.filename}:{warning.lineno}")
                return {"status": "ISSUE_CONFIRMED", "warnings": len(websocket_warnings)}
            else:
                print(f"  ✅ Issue not reproduced (no warnings)")
                return {"status": "ISSUE_NOT_REPRODUCED", "warnings": 0}
                
        except ImportError as e:
            print(f"  ⚠️  Import failed: {e}")
            return {"status": "IMPORT_FAILED", "error": str(e)}

def analyze_warning_source():
    """Analyze where the deprecation warning is being triggered from"""
    print("\n" + "=" * 80)
    print("TEST 4: Warning Source Analysis")
    print("=" * 80)
    
    import_statement = "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator"
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        try:
            exec(import_statement)
            
            # Filter for websocket_core deprecation warnings
            websocket_warnings = [
                warning for warning in w 
                if (issubclass(warning.category, DeprecationWarning) and 
                    'websocket_core' in str(warning.message))
            ]
            
            print("Warning Source Analysis:")
            for i, warning in enumerate(websocket_warnings):
                print(f"  Warning {i+1}:")
                print(f"    Message: {warning.message}")
                print(f"    File: {warning.filename}")
                print(f"    Line: {warning.lineno}")
                print(f"    Category: {warning.category}")
                
                # Try to identify if warning is coming from __init__.py
                if '__init__.py' in warning.filename:
                    print(f"    ❌ Source: __init__.py (likely cause of false positive)")
                else:
                    print(f"    ℹ️  Source: {Path(warning.filename).name}")
            
            return {"warning_count": len(websocket_warnings), "warnings": websocket_warnings}
            
        except ImportError as e:
            print(f"Import failed: {e}")
            return {"error": str(e)}

def main():
    """Execute all validation tests and provide comprehensive results"""
    print("Issue #1236 - WebSocket Import Deprecation Warning Validation")
    print("Testing for false positive deprecation warnings on specific module imports")
    
    # Execute all test scenarios
    specific_results = test_specific_module_imports_should_not_warn()
    broad_results = test_broad_init_imports_should_warn()
    validator_issue = test_websocket_error_validator_issue()
    warning_analysis = analyze_warning_source()
    
    # Summary analysis
    print("\n" + "=" * 80)
    print("SUMMARY ANALYSIS")
    print("=" * 80)
    
    false_positives = sum(1 for r in specific_results.values() if r.get("status") == "FALSE_POSITIVE")
    missing_warnings = sum(1 for r in broad_results.values() if r.get("status") == "MISSING_WARNING")
    
    print(f"Specific Module Import Tests: {len(specific_results)} total")
    print(f"  False Positives (Issues): {false_positives}")
    print(f"  Correct Behavior: {len(specific_results) - false_positives}")
    
    print(f"\nBroad Import Tests: {len(broad_results)} total")
    print(f"  Missing Expected Warnings: {missing_warnings}")
    print(f"  Correct Warnings: {len(broad_results) - missing_warnings}")
    
    print(f"\nwebsocket_error_validator.py Issue:")
    print(f"  Status: {validator_issue.get('status', 'unknown')}")
    
    # Overall verdict
    print(f"\n" + "=" * 80)
    print("VERDICT")
    print("=" * 80)
    
    if false_positives > 0:
        print("❌ ISSUE #1236 CONFIRMED: False positive deprecation warnings detected")
        print(f"   {false_positives} specific module imports are incorrectly triggering warnings")
        print("   RECOMMENDATION: Proceed to remediation planning")
    else:
        print("✅ Issue #1236 NOT REPRODUCED: No false positive warnings detected")
        print("   RECOMMENDATION: Re-evaluate issue description or test approach")
    
    print(f"\nDetailed Results:")
    print(f"  Specific imports with false positives: {false_positives}")
    print(f"  Broad imports missing warnings: {missing_warnings}")
    print(f"  Total warnings analyzed: {warning_analysis.get('warning_count', 0)}")

if __name__ == "__main__":
    main()