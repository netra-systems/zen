#!/usr/bin/env python3
"""Fix websocket unified import issues"""

import os
import re

def fix_unified_imports(directory):
    count = 0
    for root, dirs, files in os.walk(directory):
        # Skip .git and __pycache__ directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.pytest_cache'}]
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Replace the unified import pattern
                    new_content = re.sub(
                        r'from netra_backend\.app\.websocket_core\.unified import',
                        'from netra_backend.app.websocket_core import',
                        content
                    )
                    
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        count += 1
                        print(f'Fixed: {filepath}')
                except Exception as e:
                    print(f'Error processing {filepath}: {e}')
    
    return count

if __name__ == '__main__':
    # Fix all files in netra_backend
    os.chdir('netra_backend')
    count = fix_unified_imports('.')
    print(f'\nTotal files fixed: {count}')