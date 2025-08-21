#!/usr/bin/env python
"""Fix all import issues after netra_backend.app migration."""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Define import mappings
IMPORT_FIXES = [
    # Base class imports
    (r'from netra_backend\.app\.base import Base', 'from netra_backend.app.db.base import Base'),
    (r'from netra_backend\.app\.base import', 'from netra_backend.app.db.base import'),
    
    # Schema imports that were moved
    (r'from netra_backend\.app\.([A-Z]\w+) import', r'from netra_backend.app.schemas.\1 import'),
    (r'from netra_backend\.app\.auth_types import', 'from netra_backend.app.schemas.auth_types import'),
    (r'from netra_backend\.app\.agent_models import', 'from netra_backend.app.schemas.agent_models import'),
    (r'from netra_backend\.app\.agent_state import', 'from netra_backend.app.schemas.agent_state import'),
    (r'from netra_backend\.app\.error_response_models import', 'from netra_backend.app.core.error_response_models import'),
    
    # Model imports that were moved to db
    (r'from netra_backend\.app\.models_(\w+) import', r'from netra_backend.app.db.models_\1 import'),
    
    # Logging imports that were moved
    (r'from netra_backend\.app\.logging_formatters import', 'from netra_backend.app.core.logging_formatters import'),
    (r'from netra_backend\.app\.logging_context import', 'from netra_backend.app.core.logging_context import'),
    
    # Core imports
    (r'from netra_backend\.app\.unified_logging import', 'from netra_backend.app.core.unified_logging import'),
    (r'from netra_backend\.app\.lifespan_manager import', 'from netra_backend.app.core.lifespan_manager import'),
    (r'from netra_backend\.app\.app_factory import', 'from netra_backend.app.core.app_factory import'),
    
    # Fix relative imports in schemas __init__.py
    (r'from netra_backend\.app\.schemas\.schemas\.', 'from netra_backend.app.schemas.'),
]

def fix_file(filepath: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False
    
    original_content = content
    
    # Apply all fixes
    for pattern, replacement in IMPORT_FIXES:
        content = re.sub(pattern, replacement, content)
    
    # Special case: Fix schema __init__.py double schemas
    if 'schemas/__init__.py' in str(filepath):
        content = re.sub(r'from netra_backend\.app\.schemas\.schemas\.', 'from netra_backend.app.schemas.', content)
    
    # Only write if changed
    if content != original_content:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False
    
    return False

def main():
    """Main function to fix all imports."""
    root_dir = Path('netra_backend')
    
    if not root_dir.exists():
        print("Error: netra_backend directory not found")
        return
    
    # Find all Python files
    python_files = list(root_dir.rglob('*.py'))
    
    print(f"Found {len(python_files)} Python files to check")
    
    fixed_files = []
    for filepath in python_files:
        if '__pycache__' in str(filepath):
            continue
        
        if fix_file(filepath):
            fixed_files.append(filepath)
    
    print(f"\nFixed {len(fixed_files)} files:")
    for filepath in fixed_files:
        print(f"  - {filepath}")
    
    # Also fix integration tests
    integration_tests = Path('integration_tests')
    if integration_tests.exists():
        test_files = list(integration_tests.rglob('*.py'))
        print(f"\nChecking {len(test_files)} integration test files")
        
        for filepath in test_files:
            if '__pycache__' in str(filepath):
                continue
            
            if fix_file(filepath):
                fixed_files.append(filepath)
                print(f"  Fixed: {filepath}")
    
    print(f"\nTotal files fixed: {len(fixed_files)}")

if __name__ == '__main__':
    main()
