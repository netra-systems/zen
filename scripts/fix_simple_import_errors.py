#!/usr/bin/env python3
"""
Simple script to fix the specific import syntax error pattern we're seeing:
from module import item1, item2
    item1, item2
)
"""

import os
import ast
import re


def fix_simple_import_error(filepath):
    """Fix simple import syntax errors."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.split('\n')
        fixed_lines = []
        i = 0
        changes_made = False
        
        while i < len(lines):
            line = lines[i]
            
            # Look for pattern: import line followed by indented items and closing paren
            if ('from ' in line and ' import ' in line and i + 2 < len(lines)):
                next_line = lines[i + 1].strip()
                third_line = lines[i + 2].strip()
                
                # Check if this matches our problematic pattern
                if (next_line and not next_line.startswith('from ') and 
                    not next_line.startswith('#') and third_line == ')'):
                    
                    # Extract the base import and items
                    base_import = line.strip()
                    items = next_line.strip()
                    
                    # Reconstruct as proper import
                    if '(' not in base_import:
                        # Convert to multi-line import
                        fixed_lines.append(base_import.replace(' import ', ' import ('))
                        fixed_lines.append(f'    {items}')
                        fixed_lines.append(')')
                    else:
                        # Already has opening paren
                        fixed_lines.append(base_import)
                        fixed_lines.append(f'    {items}')
                        fixed_lines.append(')')
                    
                    changes_made = True
                    i += 3  # Skip the processed lines
                    continue
            
            fixed_lines.append(line)
            i += 1
        
        if changes_made:
            new_content = '\n'.join(fixed_lines)
            
            # Test if the fix works
            try:
                ast.parse(new_content)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True, "Fixed"
            except SyntaxError as e:
                return False, f"Still has error: {e}"
        
        return False, "No changes needed"
        
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Fix import syntax errors."""
    fixed_files = []
    
    # Get list of files with syntax errors
    error_files = [
        "tests/e2e/agent_isolation/test_file_system_isolation.py",
        "tests/e2e/agent_isolation/test_memory_isolation.py", 
        "tests/e2e/fixtures/__init__.py",
        "tests/e2e/resource_isolation/test_infrastructure.py",
        "tests/e2e/resource_isolation/test_suite.py",
        "tests/e2e/resource_isolation/infrastructure/__init__.py",
        "tests/e2e/resource_isolation/suite/test_suite_core.py",
        "tests/e2e/test_helpers/throughput_helpers.py",
        "tests/e2e/test_helpers/__init__.py",
        "tests/e2e/websocket_resilience/test_2_midstream_disconnection_recovery_websocket.py",
        "tests/e2e/websocket_resilience/test_websocket_connection_concurrent.py",
        "tests/e2e/websocket_resilience/test_websocket_security_attacks.py",
        "tests/e2e/websocket_resilience/test_websocket_security_audit.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_advanced.py",
        "tests/e2e/websocket_resilience/test_websocket_token_refresh_flow.py",
    ]
    
    for file_path in error_files:
        if os.path.exists(file_path):
            success, message = fix_simple_import_error(file_path)
            if success:
                print(f"Fixed: {file_path}")
                fixed_files.append(file_path)
            else:
                print(f"Could not fix {file_path}: {message}")
    
    print(f"\nFixed {len(fixed_files)} files")
    return fixed_files


if __name__ == "__main__":
    main()