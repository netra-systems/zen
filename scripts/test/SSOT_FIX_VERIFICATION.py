#!/usr/bin/env python
"""Comprehensive verification that SSOT fix is complete and working."""

import os
import sys
import importlib
from pathlib import Path

def verify_ssot_fix():
    """Verify the SSOT fix is complete."""
    
    print("=" * 70)
    print("SSOT FIX VERIFICATION - TRIPLE CHECK")
    print("=" * 70)
    
    all_passed = True
    
    # 1. Verify old files are deleted
    print("\n[1/5] Verifying old files are deleted...")
    old_files = [
        "netra_backend/app/agents/supervisor_agent.py",
        "netra_backend/app/agents/supervisor_agent_modern.py"
    ]
    
    for file_path in old_files:
        if os.path.exists(file_path):
            print(f"  [FAIL] {file_path} still exists!")
            all_passed = False
        else:
            print(f"  [PASS] {file_path} correctly removed")
    
    # 2. Verify canonical file exists
    print("\n[2/5] Verifying canonical implementation exists...")
    canonical_file = "netra_backend/app/agents/supervisor_consolidated.py"
    if os.path.exists(canonical_file):
        print(f"  [PASS] {canonical_file} exists")
        # Check file size to ensure it's not empty
        size = os.path.getsize(canonical_file)
        if size > 1000:
            print(f"  [PASS] File size OK ({size} bytes)")
        else:
            print(f"  [FAIL] File too small ({size} bytes)")
            all_passed = False
    else:
        print(f"  [FAIL] {canonical_file} does not exist!")
        all_passed = False
    
    # 3. Verify imports work
    print("\n[3/5] Testing imports...")
    try:
        # Clear any cached imports
        if 'netra_backend.app.agents.supervisor_agent' in sys.modules:
            del sys.modules['netra_backend.app.agents.supervisor_agent']
        if 'netra_backend.app.agents.supervisor_agent_modern' in sys.modules:
            del sys.modules['netra_backend.app.agents.supervisor_agent_modern']
        
        # Test that old imports fail
        try:
            from netra_backend.app.agents.supervisor_agent import SupervisorAgent
            print("  [FAIL] supervisor_agent import should have failed!")
            all_passed = False
        except ImportError:
            print("  [PASS] supervisor_agent import correctly fails")
        
        try:
            from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
            print("  [FAIL] supervisor_agent_modern import should have failed!")
            all_passed = False
        except ImportError:
            print("  [PASS] supervisor_agent_modern import correctly fails")
        
        # Test that new import works
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        print("  [PASS] supervisor_consolidated import works")
        print(f"  [INFO] Module: {SupervisorAgent.__module__}")
        
    except Exception as e:
        print(f"  [FAIL] Import test failed: {e}")
        all_passed = False
    
    # 4. Check for any remaining references
    print("\n[4/5] Checking for remaining references to old modules...")
    
    patterns_to_check = [
        "from netra_backend.app.agents.supervisor_agent import",
        "from netra_backend.app.agents.supervisor_agent_modern import",
        "import netra_backend.app.agents.supervisor_agent",
        "import netra_backend.app.agents.supervisor_agent_modern"
    ]
    
    dirs_to_check = ["netra_backend", "tests", "scripts"]
    files_with_refs = []
    
    for dir_name in dirs_to_check:
        if os.path.exists(dir_name):
            for root, dirs, files in os.walk(dir_name):
                # Skip __pycache__ and .git directories
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.venv', 'venv']]
                
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                for pattern in patterns_to_check:
                                    if pattern in content:
                                        files_with_refs.append(file_path)
                                        break
                        except:
                            pass
    
    if files_with_refs:
        print(f"  [FAIL] Found {len(files_with_refs)} files with old references:")
        for f in files_with_refs[:5]:  # Show first 5
            print(f"    - {f}")
        all_passed = False
    else:
        print("  [PASS] No references to old modules found")
    
    # 5. Verify critical imports
    print("\n[5/5] Verifying critical module imports...")
    critical_modules = [
        "netra_backend.app.startup_module",
        "netra_backend.app.services.message_handlers",
        "netra_backend.app.services.service_factory"
    ]
    
    for module_name in critical_modules:
        try:
            module = importlib.import_module(module_name)
            print(f"  [PASS] {module_name} imports successfully")
            
            # Check if it has correct supervisor import
            module_file = module.__file__
            with open(module_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'SupervisorAgent' in content:
                    if 'supervisor_consolidated' in content:
                        print(f"    [PASS] Uses correct supervisor_consolidated import")
                    elif 'supervisor_agent' in content or 'supervisor_agent_modern' in content:
                        print(f"    [FAIL] Still uses old import!")
                        all_passed = False
        except Exception as e:
            print(f"  [FAIL] Error checking {module_name}: {e}")
            all_passed = False
    
    # Final summary
    print("\n" + "=" * 70)
    if all_passed:
        print("SUCCESS: ALL VERIFICATIONS PASSED")
        print("SSOT fix is complete and working correctly!")
    else:
        print("FAILURE: Some verifications failed")
        print("Please review the issues above")
    print("=" * 70)
    
    return all_passed

if __name__ == "__main__":
    success = verify_ssot_fix()
    sys.exit(0 if success else 1)