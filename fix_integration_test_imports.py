#!/usr/bin/env python3
"""Fix import issues in integration tests."""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single test file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix monitoring imports
    content = re.sub(
        r'from monitoring\.(.+?) import',
        r'from netra_backend.app.monitoring.\1 import',
        content
    )
    
    # Fix netra_backend.tests imports
    content = re.sub(
        r'from netra_backend\.tests\.integration\.helpers\.critical_integration_helpers import',
        r'from tests.integration.helpers.user_flow_helpers import',
        content
    )
    
    # Fix auth_integration imports
    content = re.sub(
        r'from auth_integration\.auth import',
        r'from app.auth_integration.auth import',
        content
    )
    
    # Fix services imports
    content = re.sub(
        r'from services\.(.+?) import',
        r'from app.services.\1 import',
        content
    )
    
    # Fix core imports without app prefix
    content = re.sub(
        r'from core\.(.+?) import',
        r'from app.core.\1 import',
        content
    )
    
    # Fix database imports without app prefix
    content = re.sub(
        r'from database\.(.+?) import',
        r'from netra_backend.app.database.\1 import',
        content
    )
    
    # Fix routes imports without app prefix
    content = re.sub(
        r'from routes\.(.+?) import',
        r'from app.routes.\1 import',
        content
    )
    
    # Fix utils imports without app prefix
    content = re.sub(
        r'from utils\.(.+?) import',
        r'from app.utils.\1 import',
        content
    )
    
    # Fix agents imports without app prefix
    content = re.sub(
        r'from agents\.(.+?) import',
        r'from app.agents.\1 import',
        content
    )
    
    # Check if we have project root setup
        # Already has path setup
        pass
    elif 'from netra_backend.app' not in content and 'from app.' in content:
        # Needs path setup
        lines = content.split('\n')
        
        # Find the first import statement
        import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                import_idx = i
                break
        
        if import_idx > 0:
            # Check if docstring ends before imports
            docstring_end = -1
            in_docstring = False
            quote_type = None
            
            for i, line in enumerate(lines):
                if i < import_idx:
                    if not in_docstring:
                        if '"""' in line or "'''" in line:
                            quote_type = '"""' if '"""' in line else "'''"
                            if line.count(quote_type) == 2:
                                # Single line docstring
                                docstring_end = i
                            else:
                                in_docstring = True
                    else:
                        if quote_type in line:
                            in_docstring = False
                            docstring_end = i
            
            # Insert path setup after docstring
            insert_idx = docstring_end + 1 if docstring_end >= 0 else 0
            
            path_setup = [
                "",
                "# Add project root to path",
                "import sys",
                "from pathlib import Path",
                ""
            ]
            
            # Only add if not already present
            if 'PROJECT_ROOT = Path(__file__)' not in content:
                lines[insert_idx:insert_idx] = path_setup
                content = '\n'.join(lines)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    """Fix imports in all integration test files."""
    test_dir = Path('netra_backend/tests/integration')
    
    fixed_count = 0
    total_count = 0
    
    for test_file in test_dir.rglob('test_*.py'):
        total_count += 1
        if fix_imports_in_file(test_file):
            fixed_count += 1
            print(f"Fixed: {test_file}")
    
    print(f"\nFixed {fixed_count} out of {total_count} test files")


if __name__ == '__main__':
    main()