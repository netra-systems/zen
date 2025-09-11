#!/usr/bin/env python3
"""
Batch Execution Factory Import Update Script
"""

import os
import re

def update_execution_factory_imports(root_dir: str):
    """Update all execution_factory imports to services imports."""
    
    pattern = re.compile(r'from netra_backend\.app\.agents\.supervisor\.execution_factory import UserExecutionContext')
    old_import = 'from netra_backend.app.services.user_execution_context import UserExecutionContext'
    new_import = 'from netra_backend.app.services.user_execution_context import UserExecutionContext'
    
    updated_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', '.pytest_cache', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if old_import in content:
                        updated_content = content.replace(old_import, new_import)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(updated_content)
                        
                        print(f"Updated execution_factory import: {filepath}")
                        updated_count += 1
                        
                except Exception as e:
                    print(f"Error updating {filepath}: {e}")
    
    print(f"Updated {updated_count} files with execution_factory imports")
    return updated_count

if __name__ == "__main__":
    print("Updating execution_factory imports...")
    root_dir = os.getcwd()
    update_execution_factory_imports(root_dir)
    print("Done!")