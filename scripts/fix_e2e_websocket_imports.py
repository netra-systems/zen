#!/usr/bin/env python3
"""
Fix websocket-related import errors in e2e tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Test Infrastructure Stability
- Value Impact: Enables e2e tests to run properly, ensuring system reliability
- Strategic Impact: Prevents test failures from blocking deployments

This script automatically fixes common websocket import issues in e2e test files:
1. Updates old websocket.unified.manager imports to websocket_core.manager
2. Updates old websocket.connection_manager imports to websocket_core.manager  
3. Replaces UnifiedWebSocketManager with WebSocketManager
4. Adds backward compatibility aliases where needed
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in the given directory and subdirectories."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def analyze_file_imports(file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
    """Analyze a file for problematic websocket imports."""
    issues = {
        'unified_manager_imports': [],
        'connection_manager_imports': [],
        'unified_websocket_manager_usage': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Check for old unified.manager imports
            if re.search(r'from netra_backend\.app\.websocket\.unified\.manager import', line):
                issues['unified_manager_imports'].append((line_num, line.strip()))
            
            # Check for old connection_manager imports
            if re.search(r'from netra_backend\.app\.websocket\.connection_manager import', line):
                issues['connection_manager_imports'].append((line_num, line.strip()))
            
            # Check for UnifiedWebSocketManager usage
            if 'UnifiedWebSocketManager' in line and 'import' not in line:
                issues['unified_websocket_manager_usage'].append((line_num, line.strip()))
                
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return {}
    
    return issues

def fix_file_imports(file_path: Path, dry_run: bool = False) -> bool:
    """Fix websocket import issues in a single file."""
    print(f"\n=== Processing {file_path} ===")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            original_content = content
            
        changes_made = False
        
        # Fix 1: Replace unified.manager imports
        old_unified_pattern = r'from netra_backend\.app\.websocket\.unified\.manager import ([^#\n]*)'
        if re.search(old_unified_pattern, content):
            print("  * Fixing unified.manager import")
            content = re.sub(
                old_unified_pattern,
                r'from netra_backend.app.websocket_core.manager import \1',
                content
            )
            changes_made = True
        
        # Fix 2: Replace connection_manager imports
        old_connection_pattern = r'from netra_backend\.app\.websocket\.connection_manager import ([^#\n]*)'
        if re.search(old_connection_pattern, content):
            print("  * Fixing connection_manager import")
            content = re.sub(
                old_connection_pattern,
                r'from netra_backend.app.websocket_core.manager import \1',
                content
            )
            changes_made = True
        
        # Fix 3: Replace UnifiedWebSocketManager with WebSocketManager
        if 'UnifiedWebSocketManager' in content:
            print("  * Replacing UnifiedWebSocketManager with WebSocketManager")
            content = content.replace('UnifiedWebSocketManager', 'WebSocketManager')
            changes_made = True
            
        # Fix 4: Add compatibility alias if needed (after imports, before first class/function)
        if changes_made and 'from netra_backend.app.websocket_core.manager import' in content:
            # Check if we need to add the alias (only if there were UnifiedWebSocketManager usages)
            if 'UnifiedWebSocketManager' in original_content and 'import' not in [line.strip() for line in original_content.split('\n') if 'UnifiedWebSocketManager' in line and 'import' in line]:
                # Find a good place to insert the alias (after imports, before first definition)
                lines = content.split('\n')
                insert_index = -1
                
                # Find the last import line
                for i, line in enumerate(lines):
                    if line.strip().startswith(('import ', 'from ')) and not line.strip().startswith('#'):
                        insert_index = i + 1
                
                if insert_index > 0:
                    # Insert alias after imports
                    while insert_index < len(lines) and (not lines[insert_index].strip() or lines[insert_index].strip().startswith('#')):
                        insert_index += 1
                    
                    alias_line = "\n# Backward compatibility alias\nUnifiedWebSocketManager = WebSocketManager\n"
                    lines.insert(insert_index, alias_line)
                    content = '\n'.join(lines)
                    print("  * Added backward compatibility alias")
        
        if changes_made:
            if not dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  [FIXED] {file_path}")
            else:
                print(f"  [WOULD FIX] {file_path}")
            return True
        else:
            print(f"  [NO CHANGES] {file_path}")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error fixing {file_path}: {e}")
        return False

def main():
    """Main function to fix all websocket import issues in e2e tests."""
    
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    e2e_tests_dir = project_root / "tests" / "e2e"
    
    if not e2e_tests_dir.exists():
        print(f"E2E tests directory not found: {e2e_tests_dir}")
        sys.exit(1)
    
    print(f"Scanning for websocket import issues in {e2e_tests_dir}")
    
    # Find all Python files in e2e tests
    python_files = find_python_files(str(e2e_tests_dir))
    
    if not python_files:
        print("No Python files found in e2e tests directory")
        sys.exit(1)
    
    print(f"Found {len(python_files)} Python files")
    
    # Analyze files for issues
    files_with_issues = []
    total_issues = 0
    
    for file_path in python_files:
        issues = analyze_file_imports(file_path)
        if any(issues.values()):
            files_with_issues.append((file_path, issues))
            issue_count = sum(len(issue_list) for issue_list in issues.values())
            total_issues += issue_count
    
    if not files_with_issues:
        print("No websocket import issues found!")
        return
    
    print(f"\nFound websocket import issues in {len(files_with_issues)} files:")
    print(f"   Total issues: {total_issues}")
    
    # Show summary of issues
    for file_path, issues in files_with_issues:
        rel_path = file_path.relative_to(project_root)
        print(f"\n  File: {rel_path}:")
        
        if issues['unified_manager_imports']:
            print(f"    [U+2022] {len(issues['unified_manager_imports'])} unified.manager import(s)")
        if issues['connection_manager_imports']:  
            print(f"    [U+2022] {len(issues['connection_manager_imports'])} connection_manager import(s)")
        if issues['unified_websocket_manager_usage']:
            print(f"    [U+2022] {len(issues['unified_websocket_manager_usage'])} UnifiedWebSocketManager usage(s)")
    
    # Ask for confirmation (or run directly if --auto flag is present)
    if '--auto' in sys.argv or '--dry-run' in sys.argv:
        auto_mode = True
    else:
        response = input(f"\nFix {total_issues} issues in {len(files_with_issues)} files? [y/N]: ")
        auto_mode = response.lower().startswith('y')
    
    if not auto_mode:
        print("Operation cancelled")
        return
    
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("\nDRY RUN MODE - No files will be modified")
    
    # Fix the issues
    print(f"\n{'Analyzing' if dry_run else 'Fixing'} websocket import issues...")
    
    fixed_count = 0
    for file_path, _ in files_with_issues:
        if fix_file_imports(file_path, dry_run):
            fixed_count += 1
    
    if dry_run:
        print(f"\nDRY RUN COMPLETE: Would fix {fixed_count} files")
        print("Run without --dry-run to apply changes")
    else:
        print(f"\nCOMPLETE: Fixed websocket imports in {fixed_count} files")
        print("You can now run pytest --collect-only to verify the fixes")

if __name__ == "__main__":
    main()