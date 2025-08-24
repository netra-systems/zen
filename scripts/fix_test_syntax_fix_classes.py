"""Fix TestSyntaxFix classes that have __init__ constructors in test files.

Pytest doesn't allow test classes to have __init__ constructors.
This script converts them to use setup_method instead.
"""

import re
from pathlib import Path
from typing import List, Tuple

def fix_test_syntax_fix_class(content: str) -> str:
    """Fix TestSyntaxFix class by converting __init__ to setup_method."""
    
    # Pattern to find TestSyntaxFix class with __init__
    class_pattern = r'(class TestSyntaxFix.*?\n)(.*?)(?=\nclass |\Z)'
    
    def replace_init(match):
        class_def = match.group(1)
        class_body = match.group(2)
        
        # Replace __init__ with setup_method
        init_pattern = r'(\s+)def __init__\(self\):\s*\n(\s+)super\(\).__init__\(\)\s*\n'
        setup_replacement = r'\1def setup_method(self):\n\2"""Setup method for test class."""\n'
        
        modified_body = re.sub(init_pattern, setup_replacement, class_body)
        
        # If no replacement was made, return original
        if modified_body == class_body:
            return match.group(0)
            
        return class_def + modified_body
    
    # Apply the replacement
    modified_content = re.sub(class_pattern, replace_init, content, flags=re.DOTALL)
    
    return modified_content

def process_file(file_path: Path) -> bool:
    """Process a single file to fix TestSyntaxFix classes.
    
    Returns True if file was modified, False otherwise.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Check if file contains TestSyntaxFix with __init__
        if 'class TestSyntaxFix' not in content or 'def __init__(self):' not in content:
            return False
        
        # Fix the content
        modified_content = fix_test_syntax_fix_class(content)
        
        # Only write if content changed
        if modified_content != content:
            file_path.write_text(modified_content, encoding='utf-8')
            return True
            
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all TestSyntaxFix classes."""
    
    # Files identified with TestSyntaxFix __init__ issues
    test_files = [
        "netra_backend/tests/integration/test_message_flow_routing_helpers.py",
        "netra_backend/tests/integration/test_message_flow_routing_core.py",
        "netra_backend/tests/integration/test_message_flow_errors_helpers.py",
        "netra_backend/tests/integration/test_message_flow_errors_core.py",
        "netra_backend/tests/integration/test_unified_message_flow_helpers.py",
        "netra_backend/tests/integration/test_unified_message_flow_core.py",
        "netra_backend/tests/integration/test_message_flow_performance_helpers.py",
        "netra_backend/tests/integration/test_message_flow_performance_core.py",
        "netra_backend/tests/integration/test_message_flow_auth_core.py",
        "netra_backend/tests/integration/test_logging_audit_integration_helpers.py",
        "netra_backend/tests/integration/test_logging_audit_integration_core.py",
    ]
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    fixed_files = []
    for file_path_str in test_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            if process_file(file_path):
                fixed_files.append(file_path_str)
                print(f"[FIXED] {file_path_str}")
            else:
                print(f"[OK] No changes needed: {file_path_str}")
        else:
            print(f"[ERROR] File not found: {file_path_str}")
    
    print(f"\n{len(fixed_files)} files fixed:")
    for file in fixed_files:
        print(f"  - {file}")
    
    return len(fixed_files)

if __name__ == "__main__":
    import sys
    fixed_count = main()
    sys.exit(0 if fixed_count > 0 else 1)