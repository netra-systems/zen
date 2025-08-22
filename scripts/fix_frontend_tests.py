#!/usr/bin/env python3
"""
Script to automatically fix frontend test files that use WebSocketProvider without AuthContext.
"""

import os
import re
from pathlib import Path
from typing import Optional


def _should_skip_file(content: str) -> bool:
    """Check if file should be skipped from processing."""
    if 'WebSocketProvider' not in content:
        return True
    if 'TestProviders' in content or 'test-utils/providers' in content:
        return True
    return False

def _add_test_providers_import(content: str) -> str:
    """Add TestProviders import if not present."""
    if "import { TestProviders" in content:
        return content
    import_pattern = r'(import[^;]+;[\s]*)+'
    import_match = re.search(import_pattern, content)
    if import_match:
        last_import_end = import_match.end()
        return (content[:last_import_end] + 
                "\nimport { TestProviders } from '@/__tests__/test-utils/providers';" +
                content[last_import_end:])
    return content

def _replace_websocket_imports(content: str) -> str:
    """Replace WebSocketProvider import with empty string."""
    return re.sub(
        r"import \{ WebSocketProvider \} from '@/providers/WebSocketProvider';",
        "",
        content
    )

def _fix_wrapper_patterns(content: str) -> str:
    """Fix all wrapper function patterns that use WebSocketProvider."""
    content = _fix_wrapper_pattern_1(content)
    content = _fix_wrapper_pattern_2(content)
    content = _fix_wrapper_pattern_3(content)
    content = _fix_wrapper_pattern_4(content)
    return content

def _fix_wrapper_pattern_1(content: str) -> str:
    """Fix Pattern 1: wrapper = ({ children }) => (<WebSocketProvider>{children}</WebSocketProvider>)."""
    return re.sub(
        r'wrapper = \(\{ children \}[^)]*\) => \(\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\)',
        'wrapper = TestProviders',
        content
    )

def _fix_wrapper_pattern_2(content: str) -> str:
    """Fix Pattern 2: const wrapper = ({ children }: ...) => (<WebSocketProvider>{children}</WebSocketProvider>)."""
    return re.sub(
        r'const wrapper = \(\{ children \}[^)]*\) => \(\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\)',
        'const wrapper = TestProviders',
        content
    )

def _fix_wrapper_pattern_3(content: str) -> str:
    """Fix Pattern 3: Multi-line wrapper definitions."""
    return re.sub(
        r'wrapper = \(\{ children \}\) => \(\s*\n\s*<WebSocketProvider>\{children\}</WebSocketProvider>\s*\n\s*\);',
        'wrapper = TestProviders;',
        content,
        flags=re.MULTILINE
    )

def _fix_wrapper_pattern_4(content: str) -> str:
    """Fix Pattern 4: Direct usage in renderHook."""
    return re.sub(
        r'<WebSocketProvider>\{children\}</WebSocketProvider>',
        '<TestProviders>{children}</TestProviders>',
        content
    )

def _add_fetch_mock_if_needed(content: str) -> str:
    """Add fetch mock for config if needed."""
    if 'global.fetch' in content or 'WebSocket' not in content:
        return content
    beforeEach_pattern = r'beforeEach\(\(\) => \{'
    match = re.search(beforeEach_pattern, content)
    if match:
        return _insert_fetch_mock(content, match.end())
    return content

def _insert_fetch_mock(content: str, insert_pos: int) -> str:
    """Insert fetch mock at specified position."""
    fetch_mock = """
    // Mock fetch for config
    global.fetch = jest.fn().mockResolvedValue({
      json: jest.fn().mockResolvedValue({
        ws_url: 'ws://localhost:8000/ws'
      })
    });
"""
    return content[:insert_pos] + fetch_mock + content[insert_pos:]

def _cleanup_and_write_file(filepath: Path, content: str, original_content: str) -> bool:
    """Clean up content and write file if changed."""
    content = re.sub(r'\n\n\n+', '\n\n', content)
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def fix_test_file(filepath: Path) -> bool:
    """Fix a single test file to use TestProviders instead of WebSocketProvider directly."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    original_content = content
    if _should_skip_file(content):
        return False
    content = _add_test_providers_import(content)
    content = _replace_websocket_imports(content)
    content = _fix_wrapper_patterns(content)
    content = _add_fetch_mock_if_needed(content)
    return _cleanup_and_write_file(filepath, content, original_content)

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