#!/usr/bin/env python3
"""
Fix sample_state -> sample_user_context in test file
"""

import re

def fix_test_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix function signatures
    content = re.sub(
        r'(async def test_[^(]+\([^)]*), sample_state([^)]*\):)',
        r'\1, sample_user_context\2:)',
        content
    )
    
    content = re.sub(
        r'(def test_[^(]+\([^)]*), sample_state([^)]*\):)',
        r'\1, sample_user_context\2:)',
        content
    )
    
    # Fix all sample_state usages in function calls
    content = re.sub(
        r'sample_state(?![a-zA-Z_0-9])',
        'sample_user_context',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {file_path}")

if __name__ == "__main__":
    fix_test_file("/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_unit.py")