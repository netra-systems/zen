#!/usr/bin/env python3
"""
Script to automatically fix frontend test files that use WebSocketProvider without AuthContext.
"""

import os
import re
from pathlib import Path

def fix_test_file(filepath):
    """Fix a single test file to use TestProviders instead of WebSocketProvider directly."""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check if file uses WebSocketProvider
    if 'WebSocketProvider' not in content:
        return False
    
    # Check if already fixed
    if 'TestProviders' in content or 'test-utils/providers' in content:
        return False
    
    # Add import for TestProviders if not present
    if "import { TestProviders" not in content:
        # Find the last import statement
        import_pattern = r'(import[^;]+;[\s]*)+' 
        import_match = re.search(import_pattern, content)
        if import_match:
            # Add the new import after the last import
            last_import_end = import_match.end()
            content = (content[:last_import_end] + 
                      "\nimport { TestProviders } from '../test-utils/providers';" +
                      content[last_import_end:])
    
    # Replace WebSocketProvider import with TestProviders usage
    content = re.sub(
        r"import \{ WebSocketProvider \} from '@/providers/WebSocketProvider';",
        "",
        content
    )
    
    # Fix wrapper functions that use WebSocketProvider
    # Pattern 1: wrapper = ({ children }) => (<WebSocketProvider>{children}</WebSocketProvider>)
    content = re.sub(
        r'wrapper = \(\{ children \}[^)]*\) => \(\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\)',
        'wrapper = TestProviders',
        content
    )
    
    # Pattern 2: const wrapper = ({ children }: ...) => (<WebSocketProvider>{children}</WebSocketProvider>)
    content = re.sub(
        r'const wrapper = \(\{ children \}[^)]*\) => \(\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\)',
        'const wrapper = TestProviders',
        content
    )
    
    # Pattern 3: Multi-line wrapper definitions
    content = re.sub(
        r'wrapper = \(\{ children \}\) => \(\s*\n\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\n\s*\);',
        'wrapper = TestProviders;',
        content,
        flags=re.MULTILINE
    )
    
    # Pattern 4: Direct usage in renderHook
    content = re.sub(
        r'<WebSocketProvider>\{children\}</WebSocketProvider>',
        '<TestProviders>{children}</TestProviders>',
        content
    )
    
    # Also add mock for fetch if needed
    if 'global.fetch' not in content and 'WebSocket' in content:
        # Find beforeEach or the first test
        beforeEach_pattern = r'beforeEach\(\(\) => \{'
        match = re.search(beforeEach_pattern, content)
        if match:
            insert_pos = match.end()
            fetch_mock = """
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });
"""
            content = content[:insert_pos] + fetch_mock + content[insert_pos:]
    
    # Clean up any duplicate empty lines
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    """Fix all test files in the frontend __tests__ directory."""
    
    frontend_tests_dir = Path('frontend/__tests__')
    
    if not frontend_tests_dir.exists():
        print(f"Error: {frontend_tests_dir} does not exist")
        return
    
    fixed_files = []
    
    # Find all test files
    test_files = list(frontend_tests_dir.glob('**/*.test.tsx')) + \
                 list(frontend_tests_dir.glob('**/*.test.ts'))
    
    print(f"Found {len(test_files)} test files to check...")
    
    for test_file in test_files:
        if fix_test_file(test_file):
            fixed_files.append(test_file)
            print(f"Fixed: {test_file.relative_to(frontend_tests_dir.parent)}")
    
    print(f"\nFixed {len(fixed_files)} test files")
    
    if fixed_files:
        print("\nFiles fixed:")
        for f in fixed_files:
            print(f"  - {f.relative_to(frontend_tests_dir.parent)}")

if __name__ == '__main__':
    main()