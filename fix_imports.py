#!/usr/bin/env python3
"""
Script to update all relative imports to absolute imports following the new namespace convention:
- netra_backend.app for main backend
- netra_backend.tests for tests
- {service_name}.app for microservices
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

def get_namespace_for_file(filepath: str) -> str:
    """Determine the correct namespace prefix for a file."""
    path_parts = Path(filepath).parts
    
    if 'auth_service' in path_parts:
        if 'tests' in path_parts:
            return 'auth_service.tests'
        return 'auth_service.app'
    elif 'frontend' in path_parts:
        # Frontend doesn't use Python imports
        return None
    elif 'app' in path_parts:
        if 'tests' in path_parts:
            return 'netra_backend.tests'
        return 'netra_backend.app'
    return None

def fix_imports_in_file(filepath: str) -> bool:
    """Fix imports in a single Python file."""
    namespace = get_namespace_for_file(filepath)
    if not namespace:
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False
    
    original_content = content
    
    # Pattern 1: Fix relative imports starting with dot
    # from .module import Something -> from netra_backend.app.module import Something
    content = re.sub(
        r'^from \.([\w\.]+) import',
        lambda m: f'from {namespace}.{m.group(1)} import',
        content,
        flags=re.MULTILINE
    )
    
    # Pattern 2: Fix imports without dots that should be absolute
    # These are imports from root modules that should be prefixed
    modules_to_fix = [
        'agents', 'api', 'config', 'core', 'db', 'logging_config',
        'models', 'schemas', 'services', 'utils', 'websocket',
        'middleware', 'metrics', 'telemetry'
    ]
    
    for module in modules_to_fix:
        # Handle: from module import ...
        pattern = rf'^from {module}(\.|$)'
        if 'tests' in namespace:
            # In test files, imports from app modules should use netra_backend.app
            replacement = f'from netra_backend.app.{module}\\1'
        else:
            replacement = f'from {namespace}.{module}\\1'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Handle: import module
        pattern = rf'^import {module}(\.|$)'
        if 'tests' in namespace:
            replacement = f'import netra_backend.app.{module}\\1'
        else:
            replacement = f'import {namespace}.{module}\\1'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Special handling for test fixtures and helpers
    if 'tests' in filepath:
        # Fix test-specific imports
        test_modules = ['conftest', 'fixtures', 'helpers', 'test_helpers']
        for module in test_modules:
            pattern = rf'^from {module} import'
            replacement = f'from netra_backend.tests.{module} import'
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False
    
    return False

def find_python_files(directory: str) -> List[str]:
    """Find all Python files in directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.pytest_cache']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def main():
    """Main function to fix all imports."""
    directories_to_fix = ['app', 'auth_service']
    
    total_fixed = 0
    total_files = 0
    
    for directory in directories_to_fix:
        if not os.path.exists(directory):
            print(f"Directory {directory} not found, skipping...")
            continue
            
        print(f"\nProcessing {directory}...")
        python_files = find_python_files(directory)
        
        for filepath in python_files:
            total_files += 1
            if fix_imports_in_file(filepath):
                total_fixed += 1
                print(f"  Fixed: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"Total files processed: {total_files}")
    print(f"Total files fixed: {total_fixed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()