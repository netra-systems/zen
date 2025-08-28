#!/usr/bin/env python3
"""
CRITICAL Error Handler Import Consolidation Script
Fixes ALL imports to use the canonical UnifiedErrorHandler after SSOT consolidation.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Base directory
BASE_DIR = Path("C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1")
NETRA_BACKEND_DIR = BASE_DIR / "netra_backend"

# Import replacement mappings
IMPORT_REPLACEMENTS = [
    # ExecutionErrorHandler imports
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\.agents\.execution_error_handler\s+import\s+ExecutionErrorHandler',
        'from netra_backend.app.core.unified_error_handler import agent_error_handler as ExecutionErrorHandler'
    ),
    
    # AgentErrorHandler imports
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\.agents\.agent_error_handler\s+import\s+AgentErrorHandler',
        'from netra_backend.app.core.unified_error_handler import agent_error_handler as AgentErrorHandler'
    ),
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\.agents\.agent_error_handler\s+import\s+global_agent_error_handler',
        'from netra_backend.app.core.unified_error_handler import agent_error_handler as global_agent_error_handler'
    ),
    
    # ApiErrorHandler imports
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\.api\.api_error_handler\s+import\s+ApiErrorHandler',
        'from netra_backend.app.core.unified_error_handler import api_error_handler as ApiErrorHandler'
    ),
    
    # Generic error_handlers imports
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\s+import\s+ApiErrorHandler',
        'from netra_backend.app.core.unified_error_handler import api_error_handler as ApiErrorHandler'
    ),
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\s+import\s+get_http_status_code,\s*handle_exception',
        'from netra_backend.app.core.unified_error_handler import get_http_status_code, handle_exception'
    ),
    (
        r'from\s+netra_backend\.app\.core\.error_handlers\s+import\s+ErrorRecoveryStrategy',
        'from netra_backend.app.core.error_recovery import ErrorRecoveryStrategy'
    ),
]

# Files to exclude from processing
EXCLUDED_FILES = [
    "unified_error_handler.py",
    "error_recovery.py", 
    "error_types.py",
    "error_codes.py",
    "error_response.py"
]

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and file not in EXCLUDED_FILES:
                python_files.append(Path(root) / file)
    return python_files

def fix_imports_in_file(file_path: Path) -> Tuple[bool, List[str]]:
    """Fix imports in a single file. Returns (was_modified, changes)."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Apply all import replacements
        for pattern, replacement in IMPORT_REPLACEMENTS:
            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, replacement, content)
                changes.append(f"Replaced: {pattern[:50]}... -> {replacement[:50]}...")
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes
        
        return False, []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, []

def main():
    """Main execution function."""
    print("CRITICAL: Starting Error Handler Import Consolidation...")
    print(f"Processing directory: {NETRA_BACKEND_DIR}")
    
    # Find all Python files
    python_files = find_python_files(NETRA_BACKEND_DIR)
    print(f"Found {len(python_files)} Python files to process")
    
    # Process each file
    total_modified = 0
    all_changes = []
    
    for file_path in python_files:
        was_modified, changes = fix_imports_in_file(file_path)
        
        if was_modified:
            total_modified += 1
            relative_path = file_path.relative_to(BASE_DIR)
            print(f"Fixed imports in: {relative_path}")
            
            for change in changes:
                print(f"   - {change}")
                all_changes.append(f"{relative_path}: {change}")
    
    print(f"\nCONSOLIDATION COMPLETE!")
    print(f"Statistics:")
    print(f"   - Files processed: {len(python_files)}")
    print(f"   - Files modified: {total_modified}")
    print(f"   - Total import fixes: {len(all_changes)}")
    
    print("\nError Handler SSOT Consolidation Complete!")

if __name__ == "__main__":
    main()