#!/usr/bin/env python3
"""
Batch Import Update Script: Update all supervisor UserExecutionContext imports to services SSOT
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict

def find_files_with_supervisor_imports(root_dir: str) -> List[str]:
    """Find all Python files with supervisor UserExecutionContext imports."""
    files_to_update = []
    pattern = re.compile(r'from netra_backend\.app\.agents\.supervisor\.user_execution_context import UserExecutionContext')
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories for efficiency
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if pattern.search(content):
                            files_to_update.append(filepath)
                except Exception as e:
                    print(f"Warning: Could not read {filepath}: {e}")
                    continue
    
    return files_to_update

def update_file_imports(filepath: str) -> bool:
    """Update supervisor imports to services imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Pattern to find and replace the supervisor import
        old_import = 'from netra_backend.app.services.user_execution_context import UserExecutionContext'
        new_import = 'from netra_backend.app.services.user_execution_context import UserExecutionContext'
        
        # Check if file contains the old import
        if old_import not in content:
            return False  # Nothing to update
        
        # Replace the import
        updated_content = content.replace(old_import, new_import)
        
        # Write back the updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print(f"Updated: {filepath}")
        return True
        
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

def batch_update_imports(root_dir: str) -> Dict[str, int]:
    """Batch update all supervisor imports to services imports."""
    print("Searching for files with supervisor UserExecutionContext imports...")
    
    files_to_update = find_files_with_supervisor_imports(root_dir)
    total_files = len(files_to_update)
    
    if total_files == 0:
        print("No files found with supervisor imports - all imports already updated!")
        return {'total': 0, 'updated': 0, 'failed': 0}
    
    print(f"Found {total_files} files to update")
    
    # Process files in batches
    updated_count = 0
    failed_count = 0
    
    for i, filepath in enumerate(files_to_update, 1):
        if i % 10 == 0:
            print(f"Processing {i}/{total_files}...")
        
        if update_file_imports(filepath):
            updated_count += 1
        else:
            failed_count += 1
    
    print(f"\nBatch update completed:")
    print(f"   Total files found: {total_files}")
    print(f"   Successfully updated: {updated_count}")
    print(f"   Failed to update: {failed_count}")
    
    return {
        'total': total_files,
        'updated': updated_count,
        'failed': failed_count
    }

def main():
    """Main function to execute the batch import update."""
    print("Starting batch import consolidation to services SSOT...")
    
    # Set working directory
    root_dir = os.getcwd()
    print(f"Working directory: {root_dir}")
    
    # Execute batch update
    results = batch_update_imports(root_dir)
    
    if results['updated'] > 0:
        print("\nIMPORT CONSOLIDATION COMPLETED!")
        print("All files now import UserExecutionContext from services SSOT")
    else:
        print("\nNo updates were needed - imports already consolidated")

if __name__ == "__main__":
    main()