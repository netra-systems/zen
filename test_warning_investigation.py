#!/usr/bin/env python3
"""
Focused investigation of Issue #1236 - Why warnings are inconsistent

This script investigates why some imports trigger warnings and others don't,
focusing on the exact mechanism causing false positives.
"""

import warnings
import sys
import importlib
from pathlib import Path

def investigate_warning_inconsistency():
    """Investigate why warnings behave inconsistently"""
    print("=" * 80)
    print("INVESTIGATION: Warning Inconsistency Analysis")
    print("=" * 80)
    
    test_cases = [
        {
            "description": "FIRST TIME: event_validator import",
            "import": "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator",
            "expected": "Should NOT warn (specific module)"
        },
        {
            "description": "REPEAT: event_validator import (already imported)",
            "import": "from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator",
            "expected": "Should NOT warn (already imported)"
        },
        {
            "description": "NEW: websocket_manager import",
            "import": "from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager",
            "expected": "Should NOT warn (specific module)"
        },
        {
            "description": "BROAD: __init__.py import",
            "import": "from netra_backend.app.websocket_core import WebSocketManager",
            "expected": "SHOULD warn (broad import)"
        }
    ]
    
    results = {}
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest {i+1}: {test_case['description']}")
        print(f"Import: {test_case['import']}")
        print(f"Expected: {test_case['expected']}")
        
        # Clear any cached modules to test fresh imports
        if i == 0:  # Only clear on first test
            modules_to_clear = [m for m in sys.modules.keys() if 'websocket_core' in m]
            print(f"Clearing {len(modules_to_clear)} cached websocket_core modules")
            for mod in modules_to_clear:
                if mod in sys.modules:
                    del sys.modules[mod]
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            try:
                exec(test_case['import'])
                
                # Filter for websocket_core deprecation warnings
                websocket_warnings = [
                    warning for warning in w 
                    if (issubclass(warning.category, DeprecationWarning) and 
                        'websocket_core' in str(warning.message))
                ]
                
                result = {
                    "warnings_count": len(websocket_warnings),
                    "total_warnings": len(w),
                    "has_websocket_warning": len(websocket_warnings) > 0,
                    "warnings": [str(warning.message) for warning in websocket_warnings]
                }
                
                if websocket_warnings:
                    print(f"  ⚠️  Got {len(websocket_warnings)} websocket_core warnings")
                    for warning in websocket_warnings:
                        print(f"     {warning.message}")
                        print(f"     Location: {Path(warning.filename).name}:{warning.lineno}")
                else:
                    print(f"  ✅ No websocket_core warnings")
                
                print(f"  Total warnings: {len(w)}")
                results[f"test_{i+1}"] = result
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results[f"test_{i+1}"] = {"error": str(e)}
    
    return results

def check_init_py_deprecation_logic():
    """Check the actual deprecation logic in __init__.py"""
    print("\n" + "=" * 80)
    print("INVESTIGATION: __init__.py Deprecation Logic")
    print("=" * 80)
    
    init_py_path = Path("/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/__init__.py")
    
    if init_py_path.exists():
        print(f"Reading {init_py_path}")
        try:
            with open(init_py_path, 'r') as f:
                content = f.read()
            
            # Look for deprecation warning logic
            if 'warnings.warn' in content:
                print("✅ Found deprecation warning logic in __init__.py")
                
                # Extract warning-related lines
                lines = content.split('\n')
                warning_lines = []
                for i, line in enumerate(lines):
                    if 'warn' in line.lower() or 'deprecat' in line.lower():
                        # Include context around warning lines
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        for j in range(start, end):
                            warning_lines.append(f"{j+1:3}: {lines[j]}")
                        warning_lines.append("---")
                
                print("Warning-related code:")
                for line in warning_lines[:50]:  # Limit output
                    print(line)
                    
            else:
                print("❌ No deprecation warning logic found in __init__.py")
                
        except Exception as e:
            print(f"❌ Error reading __init__.py: {e}")
    else:
        print(f"❌ __init__.py not found at {init_py_path}")

def test_import_stacktrace():
    """Test where warnings are actually triggered from"""
    print("\n" + "=" * 80)
    print("INVESTIGATION: Import Stack Trace Analysis")
    print("=" * 80)
    
    import traceback
    
    def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
        print(f"WARNING CAPTURED:")
        print(f"  Message: {message}")
        print(f"  Category: {category}")
        print(f"  File: {filename}")
        print(f"  Line: {lineno}")
        print(f"  Stack trace:")
        for line in traceback.format_stack()[:-1]:
            print(f"    {line.strip()}")
        print()
    
    # Set custom warning handler
    original_showwarning = warnings.showwarning
    warnings.showwarning = custom_warning_handler
    
    try:
        print("Testing with stack trace capture...")
        from netra_backend.app.websocket_core.event_validator import UnifiedEventValidator
        print("Import completed")
    except Exception as e:
        print(f"Import failed: {e}")
    finally:
        # Restore original warning handler
        warnings.showwarning = original_showwarning

def main():
    """Run complete investigation"""
    print("Issue #1236 - Deep Investigation of Warning Inconsistency")
    
    # Run investigations
    consistency_results = investigate_warning_inconsistency()
    check_init_py_deprecation_logic()
    test_import_stacktrace()
    
    print("\n" + "=" * 80)
    print("INVESTIGATION SUMMARY")
    print("=" * 80)
    
    # Analyze results
    warning_counts = [r.get("warnings_count", 0) for r in consistency_results.values() if "warnings_count" in r]
    total_tests = len([r for r in consistency_results.values() if "warnings_count" in r])
    tests_with_warnings = len([c for c in warning_counts if c > 0])
    
    print(f"Total import tests: {total_tests}")
    print(f"Tests with warnings: {tests_with_warnings}")
    print(f"Tests without warnings: {total_tests - tests_with_warnings}")
    
    if tests_with_warnings > 0:
        print("❌ INCONSISTENT WARNING BEHAVIOR CONFIRMED")
        print("   Some specific module imports trigger warnings when they shouldn't")
    else:
        print("✅ No warnings detected in this run")
    
    print(f"\nNext steps:")
    print(f"1. Examine __init__.py deprecation logic")
    print(f"2. Identify why specific imports trigger broad import warnings")
    print(f"3. Fix warning condition to only target actual broad imports")

if __name__ == "__main__":
    main()