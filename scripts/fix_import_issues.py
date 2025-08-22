#!/usr/bin/env python3
"""
Fix Import Issues Across E2E Test Files

This script fixes common import issues found in the codebase:
1. validate_token -> validate_token_jwt
2. websockets module -> mcp.main module for websocket_endpoint
3. ConnectionManager -> ConnectionManager (where applicable)
"""

import glob
import os
import re
from pathlib import Path


def fix_validate_token_imports(file_path: str) -> bool:
    """Fix validate_token imports to use validate_token_jwt."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the import statement
        content = re.sub(
            r'from app\.auth_integration\.auth import([^,\n]*,\s*)?validate_token([^_\w])',
            r'from netra_backend.app.auth_integration.auth import\1validate_token_jwt\2',
            content
        )
        
        # Fix any function calls (though we found none in e2e tests)
        content = re.sub(
            r'validate_token\(',
            r'validate_token_jwt(',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def fix_websockets_import(file_path: str) -> bool:
    """Fix websockets module imports to use mcp.main."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix the import statement
        content = re.sub(
            r'from app\.routes\.websockets import websocket_endpoint',
            r'from netra_backend.app.routes.mcp.main import websocket_endpoint',
            content
        )
        
        # Remove duplicate imports (common issue found)
        lines = content.split('\n')
        seen_imports = set()
        filtered_lines = []
        
        for line in lines:
            if line.strip().startswith('from netra_backend.app.routes.mcp.main import websocket_endpoint'):
                if line not in seen_imports:
                    seen_imports.add(line)
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        
        content = '\n'.join(filtered_lines)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def fix_connection_manager_specs(file_path: str) -> bool:
    """Fix ConnectionManager mock specs to use ConnectionManager."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Only fix if importing from connection_manager module (not connection module)
        if 'from netra_backend.app.websocket.connection_manager import' in content:
            content = re.sub(
                r'spec=ConnectionManager',
                r'spec=ConnectionManager',
                content
            )
            
            content = re.sub(
                r'ConnectionManager\(\)',
                r'get_connection_manager()',
                content
            )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

def main():
    """Main function to fix import issues."""
    print("Fixing import issues across e2e test files...")
    
    base_dir = Path(__file__).parent.parent
    
    # Files to process for validate_token fixes
    validate_token_patterns = [
        "app/tests/**/*test*.py",
        "tests/**/*test*.py",
        "auth_service/tests/**/*test*.py",
        "SPEC/*.xml"
    ]
    
    # Files to process for websocket endpoint fixes  
    websocket_patterns = [
        "app/tests/**/*test*.py",
        "tests/**/*test*.py",
        "tests/conftest.py"
    ]
    
    # Files to process for connection manager fixes
    connection_patterns = [
        "app/tests/**/*test*.py",
        "tests/**/*test*.py"
    ]
    
    fixed_files = []
    
    print("\n1. Fixing validate_token imports...")
    for pattern in validate_token_patterns:
        for file_path in glob.glob(str(base_dir / pattern), recursive=True):
            if os.path.isfile(file_path):
                if fix_validate_token_imports(file_path):
                    fixed_files.append(f"validate_token: {file_path}")
                    print(f"  Fixed: {file_path}")
    
    print("\n2. Fixing websocket endpoint imports...")
    for pattern in websocket_patterns:
        for file_path in glob.glob(str(base_dir / pattern), recursive=True):
            if os.path.isfile(file_path):
                if fix_websockets_import(file_path):
                    fixed_files.append(f"websocket_endpoint: {file_path}")
                    print(f"  Fixed: {file_path}")
    
    print("\n3. Fixing ConnectionManager mock specs...")
    for pattern in connection_patterns:
        for file_path in glob.glob(str(base_dir / pattern), recursive=True):
            if os.path.isfile(file_path):
                if fix_connection_manager_specs(file_path):
                    fixed_files.append(f"ConnectionManager spec: {file_path}")
                    print(f"  Fixed: {file_path}")
    
    print(f"\nImport fixes completed!")
    print(f"   Total files fixed: {len(fixed_files)}")
    
    if fixed_files:
        print("\nSummary of fixes:")
        for fix in fixed_files:
            print(f"  - {fix}")
    else:
        print("\nNo files needed fixing - all imports are already correct!")

if __name__ == "__main__":
    main()