#!/usr/bin/env python3
"""
Fix test_utils import errors in test files.

This script fixes the incorrect import:
    from netra_backend.tests.test_utils import setup_test_path
    
And removes it since it's not needed (tests should be run from proper context).
"""

import os
import re
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_test_utils_imports(file_path: Path) -> bool:
    """Fix test_utils import in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match the problematic import and its usage
        patterns = [
            # Remove the import line
            (r'from netra_backend\.tests\.test_utils import setup_test_path\n', ''),
            # Remove the setup_test_path() call
            (r'setup_test_path\(\)\n', ''),
            # Remove any empty comment lines that might be left
            (r'# Setup test path\n(?=\n)', ''),
            # Clean up multiple consecutive newlines
            (r'\n\n\n+', '\n\n'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # If content changed, write it back
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Fixed: {file_path}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix all test files."""
    # Get the base path
    base_path = Path(__file__).parent.parent
    test_dirs = [
        base_path / "netra_backend" / "tests",
        base_path / "tests"
    ]
    
    fixed_count = 0
    error_count = 0
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
            
        # Find all Python test files
        for file_path in test_dir.rglob("test_*.py"):
            # Check if file contains the problematic import
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if 'from netra_backend.tests.test_utils import setup_test_path' in f.read():
                        if fix_test_utils_imports(file_path):
                            fixed_count += 1
                        else:
                            error_count += 1
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
                error_count += 1
    
    logger.info(f"\n{'='*60}")
    logger.info("TEST_UTILS IMPORT FIX RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"Files fixed: {fixed_count}")
    logger.info(f"Errors: {error_count}")
    
    if fixed_count > 0:
        logger.info("\n PASS:  Successfully fixed test_utils imports!")
    
    return 0 if error_count == 0 else 1

if __name__ == "__main__":
    exit(main())