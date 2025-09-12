#!/usr/bin/env python3
"""
Fix testcontainers import issues in L3 integration tests.

This script corrects the import statements for testcontainers modules
and ensures they follow the correct syntax.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def fix_testcontainers_imports(file_path: Path) -> bool:
    """
    Fix testcontainers import statements in a Python file.
    
    Args:
        file_path: Path to the Python file to fix
        
    Returns:
        True if any changes were made, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix redis container imports
        content = re.sub(
            r'import testcontainers\.redis as redis_container',
            'from testcontainers.redis import RedisContainer',
            content
        )
        
        # Fix postgres container imports  
        content = re.sub(
            r'import testcontainers\.postgres as postgres_container',
            'from testcontainers.postgres import PostgresContainer',
            content
        )
        
        # Fix usage patterns - redis_container.RedisContainer -> RedisContainer
        content = re.sub(
            r'redis_container\.RedisContainer',
            'RedisContainer',
            content
        )
        
        # Fix usage patterns - postgres_container.PostgresContainer -> PostgresContainer
        content = re.sub(
            r'postgres_container\.PostgresContainer',
            'PostgresContainer',
            content
        )
        
        # Check if any changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in: {file_path}")
            return True
        else:
            print(f"No changes needed in: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def find_files_with_testcontainers_imports(search_dir: Path) -> List[Path]:
    """
    Find all Python files that import testcontainers incorrectly.
    
    Args:
        search_dir: Directory to search in
        
    Returns:
        List of file paths with testcontainers imports
    """
    files_with_imports = []
    
    # Search for Python files with testcontainers imports
    for file_path in search_dir.rglob("*.py"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for the problematic import patterns
            if (re.search(r'import testcontainers\.redis as redis_container', content) or
                re.search(r'import testcontainers\.postgres as postgres_container', content)):
                files_with_imports.append(file_path)
                
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return files_with_imports


def main():
    """Main function to fix testcontainers imports."""
    print("Fixing testcontainers import issues in L3 integration tests...")
    
    # Define the search directory
    project_root = Path(__file__).parent.parent
    search_dir = project_root / "app" / "tests"
    
    print(f"Searching for files with testcontainers imports in: {search_dir}")
    
    # Find files with testcontainers imports
    files_to_fix = find_files_with_testcontainers_imports(search_dir)
    
    if not files_to_fix:
        print("No files found with testcontainers import issues.")
        return
    
    print(f"Found {len(files_to_fix)} files with testcontainers import issues:")
    for file_path in files_to_fix:
        print(f"  - {file_path}")
    
    # Fix the imports
    fixed_count = 0
    for file_path in files_to_fix:
        if fix_testcontainers_imports(file_path):
            fixed_count += 1
    
    print(f"\nFixed imports in {fixed_count} files.")
    
    if fixed_count > 0:
        print("\nTestcontainers import issues have been resolved!")
        print("The following changes were made:")
        print("  - import testcontainers.redis as redis_container  ->  from testcontainers.redis import RedisContainer")
        print("  - import testcontainers.postgres as postgres_container  ->  from testcontainers.postgres import PostgresContainer")
        print("  - redis_container.RedisContainer  ->  RedisContainer")
        print("  - postgres_container.PostgresContainer  ->  PostgresContainer")
    else:
        print("No changes were needed.")


if __name__ == "__main__":
    main()