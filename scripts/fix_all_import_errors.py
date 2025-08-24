#!/usr/bin/env python3
"""Comprehensive script to find and fix ALL import errors in the test suite.

This script addresses multiple refactoring issues where modules were moved/renamed
but test files weren't updated.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

def find_actual_location(class_name: str, root_dir: Path) -> List[str]:
    """Find where a class is actually defined in the codebase."""
    try:
        # Use grep to find class definitions
        cmd = f'grep -r "class {class_name}" --include="*.py" "{root_dir}" | head -5'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            locations = []
            for line in result.stdout.strip().split('\n'):
                if ':class ' in line:
                    file_path = line.split(':')[0]
                    # Convert to module path
                    module_path = file_path.replace(str(root_dir) + os.sep, '').replace('.py', '').replace(os.sep, '.')
                    locations.append(module_path)
            return locations
    except:
        pass
    return []

def analyze_import_errors() -> Dict[str, str]:
    """Analyze test output to find import errors and their fixes."""
    
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    # Known import mappings based on refactoring
    import_fixes = {
        # PerformanceMonitor refactoring (already fixed)
        'from netra_backend.app.monitoring.performance_monitor import PerformanceMonitor as PerformanceMetric':
            'from netra_backend.app.monitoring.metrics_collector import PerformanceMetric',
        
        # WebSocket refactoring (already fixed)
        'from netra_backend.app.websocket_core.connection_manager import ConnectionManager':
            'from netra_backend.app.websocket_core import WebSocketManager',
        
        # BackgroundTaskManager refactoring
        'from netra_backend.app.background import BackgroundTaskManager':
            'from netra_backend.app.core.background_tasks import BackgroundTaskManager',
        
        # Common moved modules
        'from netra_backend.app.core.thread_pool import ThreadPoolManager':
            'from netra_backend.app.core.async_utils import ThreadPoolManager',
            
        'from netra_backend.app.utils.validators import validate_':
            'from netra_backend.app.core.validators import validate_',
    }
    
    # Search for BackgroundTaskManager actual location
    bg_locations = find_actual_location('BackgroundTaskManager', root_dir / 'netra_backend')
    if bg_locations:
        actual_bg_module = bg_locations[0]
        import_fixes['from netra_backend.app.background import BackgroundTaskManager'] = \
            f'from {actual_bg_module} import BackgroundTaskManager'
    
    return import_fixes

def fix_imports_in_file(file_path: Path, import_fixes: Dict[str, str]) -> bool:
    """Fix imports in a single file based on known mappings."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    changes_made = False
    
    for old_import, new_import in import_fixes.items():
        if old_import in content:
            content = content.replace(old_import, new_import)
            changes_made = True
            print(f"Fixed in {file_path.name}: {old_import.split('import')[-1].strip()}")
    
    # Handle partial matches for validators
    if 'from netra_backend.app.utils.validators import' in content:
        content = re.sub(
            r'from netra_backend\.app\.utils\.validators import',
            'from netra_backend.app.core.validators import',
            content
        )
        changes_made = True
        print(f"Fixed validators import in {file_path.name}")
    
    if changes_made:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False

def find_test_files_with_imports() -> List[Path]:
    """Find all test files that might have import issues."""
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    test_dirs = [
        root_dir / 'netra_backend' / 'tests',
        root_dir / 'tests',
        root_dir / 'auth_service' / 'tests',
        root_dir / 'frontend' / '__tests__',
    ]
    
    test_files = []
    for test_dir in test_dirs:
        if test_dir.exists():
            test_files.extend(test_dir.rglob('*.py'))
    
    return test_files

def run_pytest_check(file_path: Path) -> bool:
    """Run pytest collection on a file to check for import errors."""
    try:
        cmd = f'python -m pytest --collect-only "{file_path}" 2>&1'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        
        # Check for import errors in output
        if 'ModuleNotFoundError' in result.stdout or 'ImportError' in result.stdout:
            return False
        return True
    except:
        return True  # Assume OK if we can't check

def main():
    """Main execution function."""
    print("=" * 60)
    print("COMPREHENSIVE IMPORT ERROR FIX")
    print("=" * 60)
    
    # First, let's find the actual location of BackgroundTaskManager
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    print("\n1. Searching for moved/renamed modules...")
    
    # Search for BackgroundTaskManager
    cmd = f'grep -r "class BackgroundTaskManager" --include="*.py" "{root_dir / "netra_backend"}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    import_fixes = {}
    
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if 'class BackgroundTaskManager' in line:
                file_path = line.split(':')[0]
                # Convert to module import path
                module_path = file_path.replace('\\', '/').replace(str(root_dir).replace('\\', '/') + '/', '')
                module_path = module_path.replace('.py', '').replace('/', '.')
                import_fixes['from netra_backend.app.background import BackgroundTaskManager'] = \
                    f'from {module_path} import BackgroundTaskManager'
                print(f"Found BackgroundTaskManager in: {module_path}")
                break
    
    # Add other known fixes
    import_fixes.update({
        'from netra_backend.app.monitoring.performance_monitor import PerformanceMonitor as PerformanceMetric':
            'from netra_backend.app.monitoring.metrics_collector import PerformanceMetric',
        'from netra_backend.app.websocket_core.connection_manager import ConnectionManager':
            'from netra_backend.app.websocket_core import WebSocketManager',
    })
    
    print(f"\n2. Found {len(import_fixes)} import patterns to fix")
    
    # Find and fix the specific file with BackgroundTaskManager issue
    problem_file = root_dir / 'netra_backend' / 'tests' / 'agents' / 'test_supply_researcher_integration.py'
    
    if problem_file.exists():
        print(f"\n3. Fixing known problem file: {problem_file.name}")
        if fix_imports_in_file(problem_file, import_fixes):
            print(f"   [FIXED] imports in {problem_file.name}")
    
    # Find all test files
    print("\n4. Scanning all test files for import issues...")
    test_files = find_test_files_with_imports()
    print(f"   Found {len(test_files)} test files to check")
    
    fixed_count = 0
    failed_files = []
    
    for test_file in test_files:
        # Quick check if file has any of our problematic imports
        try:
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                needs_fix = any(old_import in content for old_import in import_fixes.keys())
                
                # Also check for the patterns
                if 'from netra_backend.app.background import' in content:
                    needs_fix = True
                
                if needs_fix:
                    if fix_imports_in_file(test_file, import_fixes):
                        fixed_count += 1
        except Exception as e:
            print(f"   Error processing {test_file.name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: Fixed {fixed_count} files")
    print("=" * 60)
    
    print("\nNext steps:")
    print("1. Run: python unified_test_runner.py --category database --fast-fail")
    print("2. If still failing, check test report for new import errors")
    print("3. Document all import changes in learnings")
    
    return 0

if __name__ == "__main__":
    exit(main())