#!/usr/bin/env python
"""Fix all imports from deleted triage_sub_agent module to new unified_triage_agent.

This script updates all imports that reference the deleted triage_sub_agent module
to use the new consolidated unified_triage_agent module.
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from loguru import logger

# Define import mappings from old to new
IMPORT_MAPPINGS = {
    # Models imports
    r'from netra_backend\.app\.agents\.triage_sub_agent\.models import (.*)':
        'from netra_backend.app.agents.triage.unified_triage_agent import \\1',
    
    # Core imports
    r'from netra_backend\.app\.agents\.triage_sub_agent\.core import (.*)':
        'from netra_backend.app.agents.triage.unified_triage_agent import \\1',
    
    # Agent imports
    r'from netra_backend\.app\.agents\.triage_sub_agent\.agent import (.*)':
        'from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent',
    
    # Any other triage_sub_agent imports
    r'from netra_backend\.app\.agents\.triage_sub_agent import (.*)':
        'from netra_backend.app.agents.triage.unified_triage_agent import \\1',
    
    # Module-level imports
    r'import netra_backend\.app\.agents\.triage_sub_agent':
        'import netra_backend.app.agents.triage.unified_triage_agent',
}

# Files to skip (e.g., this script)
SKIP_FILES = {
    'fix_triage_imports.py',
    'unified_triage_agent.py'
}


def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file.
    
    Args:
        file_path: Path to the file to fix
        
    Returns:
        True if file was modified, False otherwise
    """
    # Skip certain files
    if file_path.name in SKIP_FILES:
        return False
    
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Apply all import mappings
        for pattern, replacement in IMPORT_MAPPINGS.items():
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Check if content changed
        if content != original_content:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            file_path.rename(backup_path)
            
            # Write updated content
            file_path.write_text(content, encoding='utf-8')
            
            # Remove backup if successful
            backup_path.unlink()
            
            logger.info(f"Fixed imports in: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False


def find_files_with_old_imports(root_dir: Path) -> List[Path]:
    """Find all Python files with old triage_sub_agent imports.
    
    Args:
        root_dir: Root directory to search
        
    Returns:
        List of file paths with old imports
    """
    files_with_imports = []
    
    # Search patterns
    search_pattern = 'triage_sub_agent'
    
    # Walk through all Python files
    for py_file in root_dir.rglob('*.py'):
        # Skip virtual environments and cache directories
        if any(part in py_file.parts for part in ['.venv', 'venv', '__pycache__', '.git']):
            continue
        
        # Skip files we should not modify
        if py_file.name in SKIP_FILES:
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8')
            if search_pattern in content:
                files_with_imports.append(py_file)
        except Exception as e:
            logger.warning(f"Could not read {py_file}: {e}")
    
    return files_with_imports


def main():
    """Main execution function."""
    logger.info("Starting triage import fix...")
    
    # Find project root
    root_dir = Path(project_root)
    
    # Find all files with old imports
    logger.info(f"Searching for files with old triage_sub_agent imports in: {root_dir}")
    files_to_fix = find_files_with_old_imports(root_dir)
    
    logger.info(f"Found {len(files_to_fix)} files with old imports")
    
    # Fix imports in each file
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_imports_in_file(file_path):
            fixed_count += 1
    
    # Report results
    logger.success(f"Import fix complete!")
    logger.info(f"Files processed: {len(files_to_fix)}")
    logger.info(f"Files fixed: {fixed_count}")
    
    # Verify no old imports remain
    logger.info("Verifying no old imports remain...")
    remaining = find_files_with_old_imports(root_dir)
    
    if remaining:
        logger.warning(f"Still {len(remaining)} files with old imports:")
        for file_path in remaining[:10]:  # Show first 10
            logger.warning(f"  - {file_path}")
    else:
        logger.success("All imports successfully fixed!")
    
    return 0 if not remaining else 1


if __name__ == "__main__":
    sys.exit(main())