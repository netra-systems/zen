#!/usr/bin/env python3
"""Fix WebSocket test import syntax errors."""

import os
import re
from pathlib import Path

def fix_import_syntax(file_path):
    """Fix import * from statements to proper import * as statements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match: import * from '@/__tests__/helpers/something';
        pattern = r"import \* from ('@/__tests__/helpers/[^']+');"
        
        def replace_import(match):
            import_path = match.group(1)
            # Extract module name from path
            module_name = import_path.split('/')[-1].replace("'", "")
            # Convert kebab-case to PascalCase
            if 'websocket-test-manager' in module_name:
                alias = 'WebSocketTestManager'
            elif 'test-setup-helpers' in module_name:
                alias = 'TestSetupHelpers'
            elif 'websocket-test-utilities' in module_name:
                alias = 'WebSocketTestUtilities'
            elif 'streaming-test-utilities' in module_name:
                alias = 'StreamingTestUtilities'
            elif 'first-load-mock-setup' in module_name:
                alias = 'FirstLoadMockSetup'
            elif 'initial-state-storage-helpers' in module_name:
                alias = 'InitialStateStorageHelpers'
            elif 'initial-state-mock-components' in module_name:
                alias = 'InitialStateMockComponents'
            else:
                # Default: capitalize and remove dashes
                alias = ''.join(word.capitalize() for word in module_name.replace('-', '_').split('_'))
            
            return f"import * as {alias} from {import_path};"
        
        # Apply the fix
        new_content = re.sub(pattern, replace_import, content)
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Fixed imports in {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Fix all TypeScript test files in frontend/__tests__."""
    frontend_tests_dir = Path("frontend/__tests__")
    fixed_count = 0
    
    if not frontend_tests_dir.exists():
        print("frontend/__tests__ directory not found")
        return
    
    # Find all .tsx files
    for file_path in frontend_tests_dir.rglob("*.tsx"):
        if fix_import_syntax(file_path):
            fixed_count += 1
    
    print(f"Fixed import syntax in {fixed_count} files")

if __name__ == "__main__":
    main()