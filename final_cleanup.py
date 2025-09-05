#!/usr/bin/env python3
"""
Final cleanup script to fix remaining automation artifacts in test files.
"""

import os
import re
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix remaining automation artifacts in a single file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Fix the \1 = TestWebSocketConnection() pattern
        content = re.sub(r'\\1 = TestWebSocketConnection\(\)', 'websocket = TestWebSocketConnection()', content)
        content = re.sub(r'websocket\.\\1 = TestWebSocketConnection\(\)', '# websocket setup complete', content)
        
        # Fix websocket=\1 patterns
        content = re.sub(r'websocket=\\1,', 'websocket=websocket,', content)
        content = re.sub(r'websocket=\\1\)', 'websocket=websocket)', content)
        
        # Fix variable declaration issues
        content = re.sub(r'\\1 = TestWebSocketConnection\(\)  # Real WebSocket implementation', 'websocket = TestWebSocketConnection()', content)
        
        # Fix other \1 patterns
        content = re.sub(r'\\1', 'websocket', content)
        
        # Fix duplicate TestWebSocketConnection at start of files
        lines = content.split('\n')
        if lines[0].strip() == '' and 'class TestWebSocketConnection:' in lines[1:5]:
            # Remove empty line at start
            lines = lines[1:]
        
        content = '\n'.join(lines)
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
            
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main entry point."""
    test_dir = Path(__file__).parent / "tests"
    
    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return
    
    test_files = list(test_dir.rglob("*.py"))
    fixed_count = 0
    
    print(f"Processing {len(test_files)} test files...")
    
    for file_path in test_files:
        if fix_file(file_path):
            fixed_count += 1
            print(f"Fixed: {file_path.relative_to(test_dir)}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()