"""Fix all ErrorContext instantiations missing required fields.

This script updates all ErrorContext instantiations to include:
1. trace_id field (using ErrorContext.generate_trace_id())
2. operation field (required field)
"""

import os
import re
from pathlib import Path

# Files that need fixing based on our search
FILES_TO_FIX = [
    "netra_backend/app/agents/triage_sub_agent/error_core.py",
    "netra_backend/app/agents/data_sub_agent/metrics_recovery.py",
    "netra_backend/app/agents/corpus_admin/corpus_validation_handlers.py",
    "netra_backend/app/agents/corpus_admin/corpus_upload_handlers.py",
    "netra_backend/app/agents/corpus_admin/corpus_indexing_handlers.py",
    "netra_backend/app/agents/data_sub_agent/data_fetching_recovery.py",
]

def fix_error_context_in_file(file_path):
    """Fix ErrorContext instantiations in a single file."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to find ErrorContext instantiations without trace_id
    # This pattern looks for ErrorContext( followed by fields that don't start with trace_id
    pattern = r'return ErrorContext\(\s*\n\s*(agent_name|operation_name|run_id)'
    
    # Check if file needs fixing
    if not re.search(pattern, content):
        return False
    
    # Fix the pattern - add trace_id and operation fields
    def replacement(match):
        # Extract the original indentation
        lines = match.group(0).split('\n')
        indent = '        '  # Default 8 spaces
        if len(lines) > 1:
            # Get indentation from the second line
            second_line = lines[1]
            indent = second_line[:len(second_line) - len(second_line.lstrip())]
        
        # Build the replacement with trace_id and operation
        result = f"return ErrorContext(\n"
        result += f"{indent}trace_id=ErrorContext.generate_trace_id(),\n"
        
        # Determine the operation value based on context
        if 'operation_name=' in match.group(0):
            # Extract operation_name value if present
            op_match = re.search(r'operation_name="([^"]+)"', match.group(0))
            if op_match:
                result += f'{indent}operation="{op_match.group(1)}",\n'
            else:
                result += f'{indent}operation="unknown_operation",\n'
        else:
            # Infer from agent_name if possible
            agent_match = re.search(r'agent_name="([^"]+)"', match.group(0))
            if agent_match:
                agent = agent_match.group(1).replace('_agent', '').replace('_sub', '')
                result += f'{indent}operation="{agent}_operation",\n'
            else:
                result += f'{indent}operation="unknown_operation",\n'
        
        # Add the rest of the original fields
        result += f"{indent}{match.group(1)}"
        
        return result
    
    # Apply the fix
    content = re.sub(pattern, replacement, content)
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False


def main():
    """Main function to fix all files."""
    print("Fixing ErrorContext instantiations missing required fields...")
    print("=" * 60)
    
    fixed_count = 0
    for file_path in FILES_TO_FIX:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
        
        if fix_error_context_in_file(file_path):
            print(f"✅ Fixed: {file_path}")
            fixed_count += 1
        else:
            print(f"⏭️  No changes needed: {file_path}")
    
    print("=" * 60)
    print(f"Fixed {fixed_count} files")
    
    # Also check for the simpler pattern where operation_name should be operation
    print("\nChecking for operation_name that should be operation field...")
    
    # Additional check for files that use operation_name but not operation
    for file_path in FILES_TO_FIX:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'operation_name=' in content and 'operation=' not in content:
            print(f"⚠️  {file_path} uses operation_name but not operation field")


if __name__ == "__main__":
    main()