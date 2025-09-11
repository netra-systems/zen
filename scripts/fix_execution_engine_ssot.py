#!/usr/bin/env python3
"""
Critical SSOT Fix Script for ExecutionEngine Consolidation

This script safely removes deprecated ExecutionEngine implementations and 
updates imports to use UserExecutionEngine as the single source of truth.

CRITICAL SECURITY FIX: This addresses WebSocket user isolation vulnerabilities
caused by multiple competing ExecutionEngine implementations.
"""

import os
import re
import shutil
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Get the project root
PROJECT_ROOT = Path(__file__).parent.parent
NETRA_BACKEND = PROJECT_ROOT / "netra_backend"

# Critical ExecutionEngine files to deprecate/remove
DEPRECATED_FILES = [
    "netra_backend/app/agents/supervisor/execution_engine.py",
    "netra_backend/app/agents/execution_engine_consolidated.py", 
    "netra_backend/app/agents/supervisor/request_scoped_execution_engine.py",
]

# Import patterns to replace
IMPORT_REPLACEMENTS = [
    # Pattern 1: Direct ExecutionEngine import
    (
        r"from\s+netra_backend\.app\.agents\.supervisor\.execution_engine\s+import\s+ExecutionEngine",
        "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine"
    ),
    # Pattern 2: Consolidated ExecutionEngine import
    (
        r"from\s+netra_backend\.app\.agents\.execution_engine_consolidated\s+import\s+.*ExecutionEngine",
        "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine"
    ),
    # Pattern 3: RequestScoped ExecutionEngine import
    (
        r"from\s+netra_backend\.app\.agents\.supervisor\.request_scoped_execution_engine\s+import\s+.*ExecutionEngine",
        "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine"
    ),
]

def backup_file(file_path: Path) -> None:
    """Create backup of file before modification."""
    backup_path = file_path.with_suffix(f".backup_{int(time.time())}")
    shutil.copy2(file_path, backup_path)
    print(f"BACKED UP {file_path} to {backup_path}")

def deprecate_file(file_path: Path) -> None:
    """Mark file as deprecated and add migration notice."""
    if not file_path.exists():
        print(f"WARNING: File {file_path} does not exist, skipping")
        return
    
    backup_file(file_path)
    
    # Read current content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add deprecation notice at the top
    deprecation_notice = '''"""
🚨 CRITICAL SSOT MIGRATION - FILE DEPRECATED 🚨

This file has been DEPRECATED as part of ExecutionEngine SSOT consolidation.

MIGRATION REQUIRED:
- Use UserExecutionEngine from netra_backend.app.agents.supervisor.user_execution_engine
- This file will be REMOVED in the next release

SECURITY FIX: Multiple ExecutionEngine implementations caused WebSocket user 
isolation vulnerabilities. UserExecutionEngine is now the SINGLE SOURCE OF TRUTH.
"""

'''
    
    # Prepend deprecation notice
    new_content = deprecation_notice + content
    
    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"DEPRECATED {file_path}")

def update_imports_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Update imports in a single file. Returns (changed, errors)."""
    if not file_path.exists():
        return False, [f"File {file_path} does not exist"]
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Apply import replacements
        for pattern, replacement in IMPORT_REPLACEMENTS:
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced pattern: {pattern}")
        
        # Write updated content if changes were made
        if content != original_content:
            backup_file(file_path)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"UPDATED imports in {file_path}")
            return True, changes
        
        return False, []
        
    except Exception as e:
        error_msg = f"Error updating {file_path}: {e}"
        print(f"ERROR: {error_msg}")
        return False, [error_msg]

def find_files_with_deprecated_imports() -> List[Path]:
    """Find all Python files that import deprecated ExecutionEngine."""
    python_files = []
    
    # Search in netra_backend directory
    for root, dirs, files in os.walk(NETRA_BACKEND):
        # Skip test directories for now (handle separately)
        if 'test' in str(root).lower():
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for deprecated import patterns
                    for pattern, _ in IMPORT_REPLACEMENTS:
                        if re.search(pattern, content):
                            python_files.append(file_path)
                            break
                            
                except Exception as e:
                    print(f"WARNING: Error reading {file_path}: {e}")
    
    return python_files

def main():
    """Main execution function."""
    import time
    print("CRITICAL SSOT FIX: ExecutionEngine Consolidation")
    print("=" * 60)
    
    # Step 1: Deprecate old ExecutionEngine files
    print("\nStep 1: Deprecating old ExecutionEngine files...")
    for file_path_str in DEPRECATED_FILES:
        file_path = PROJECT_ROOT / file_path_str
        deprecate_file(file_path)
    
    # Step 2: Find files with deprecated imports
    print("\nStep 2: Finding files with deprecated imports...")
    files_to_update = find_files_with_deprecated_imports()
    print(f"Found {len(files_to_update)} files with deprecated imports")
    
    # Step 3: Update imports in core files (non-test first)
    print("\nStep 3: Updating imports in core files...")
    updated_count = 0
    error_count = 0
    
    for file_path in files_to_update:
        changed, errors = update_imports_in_file(file_path)
        if changed:
            updated_count += 1
        if errors:
            error_count += len(errors)
            for error in errors:
                print(f"ERROR: {error}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SSOT CONSOLIDATION SUMMARY")
    print(f"Files deprecated: {len(DEPRECATED_FILES)}")
    print(f"Imports updated: {updated_count}")
    print(f"Errors encountered: {error_count}")
    
    if error_count == 0:
        print("\nSUCCESS: ExecutionEngine SSOT consolidation completed!")
        print("   UserExecutionEngine is now the single source of truth.")
        print("   WebSocket user isolation vulnerability should be resolved.")
    else:
        print(f"\nPARTIAL SUCCESS: {error_count} errors need manual review")
    
    print("\nNEXT STEPS:")
    print("1. Run tests to validate the changes")
    print("2. Test WebSocket user isolation specifically")
    print("3. Remove deprecated files after validation")

if __name__ == "__main__":
    main()