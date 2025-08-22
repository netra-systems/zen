#!/usr/bin/env python3
"""
Fix store tests by replacing the hookResult.result.current pattern
"""

import re

def fix_test_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Replace const result = ChatStoreTestUtils.initializeStore();
    # with const hookResult = ChatStoreTestUtils.initializeStore(); const store = hookResult.result.current;
    pattern1 = r'const result = ChatStoreTestUtils\.initializeStore\(\);'
    replacement1 = 'const hookResult = ChatStoreTestUtils.initializeStore();\n      const store = hookResult.result.current;'
    
    content = re.sub(pattern1, replacement1, content)
    
    # Pattern 2: Replace result.current. with store.
    pattern2 = r'result\.current\.'
    replacement2 = 'store.'
    
    content = re.sub(pattern2, replacement2, content)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_test_file("__tests__/store/undo-redo-history.test.ts")