#!/usr/bin/env python
"""Fix test_framework.redis imports after directory rename."""

import os
import re

def fix_redis_imports(root_dir="."):
    """Replace test_framework.redis with test_framework.redis_test_utils in all Python files."""
    
    pattern = re.compile(r'from test_framework\.redis')
    replacement = 'from test_framework.redis_test_utils_test_utils'
    
    files_updated = 0
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip hidden directories and __pycache__
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if pattern.search(content):
                        new_content = pattern.sub(replacement, content)
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        files_updated += 1
                        print(f"Updated: {filepath}")
                        
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
    
    print(f"\nTotal files updated: {files_updated}")

if __name__ == "__main__":
    fix_redis_imports()