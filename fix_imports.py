#!/usr/bin/env python3
"""Fix incorrect import paths in test files."""

import os
import re
from pathlib import Path

def fix_user_execution_engine_imports():
    """Fix UserExecutionEngine imports from wrong path."""
    root_dir = Path(".")
    
    # Pattern to match the incorrect import
    old_pattern = r"from netra_backend\.app\.core\.user_execution_engine import UserExecutionEngine"
    new_replacement = "from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine"
    
    fixed_count = 0
    
    # Walk through all Python files
    for py_file in root_dir.rglob("*.py"):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if re.search(old_pattern, content):
                new_content = re.sub(old_pattern, new_replacement, content)
                
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"Fixed: {py_file}")
                fixed_count += 1
        
        except Exception as e:
            print(f"Error processing {py_file}: {e}")
    
    print(f"Total files fixed: {fixed_count}")

if __name__ == "__main__":
    fix_user_execution_engine_imports()