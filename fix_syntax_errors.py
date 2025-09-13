#!/usr/bin/env python3
"""
Fix syntax errors introduced by regex replacement
"""

def fix_syntax_errors(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix double colon syntax errors
    content = content.replace('::):', '):')
    content = content.replace(')::):', '):')
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed syntax errors in {file_path}")

if __name__ == "__main__":
    fix_syntax_errors("/c/Users/antho/OneDrive/Desktop/Netra/netra-core-generation-1/netra_backend/tests/unit/agents/supervisor/test_agent_execution_core_unit.py")