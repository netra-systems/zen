#!/usr/bin/env python3
"""Fix database import errors in test files."""

import os
import re
from pathlib import Path

def fix_database_imports(file_path):
    """Fix database imports in a single file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Fix get_async_session -> get_db
    content = re.sub(
        r'from netra_backend\.app\.database import ([^)]*?)get_async_session([^)]*?)',
        r'from netra_backend.app.database import \1get_db\2',
        content
    )
    
    # Fix get_db_session -> get_db
    content = re.sub(
        r'from netra_backend\.app\.database import ([^)]*?)get_db_session([^)]*?)',
        r'from netra_backend.app.database import \1get_db\2',
        content
    )
    
    # Fix UnifiedDatabaseManager -> DatabaseManager
    content = re.sub(
        r'from netra_backend\.app\.database import ([^)]*?)UnifiedDatabaseManager([^)]*?)',
        r'from netra_backend.app.database import \1DatabaseManager\2',
        content
    )
    
    # Fix usage of get_async_session() -> get_db()
    content = re.sub(
        r'\bget_async_session\(\)',
        r'get_db()',
        content
    )
    
    # Fix usage of get_db_session() -> get_db()
    content = re.sub(
        r'\bget_db_session\(\)',
        r'get_db()',
        content
    )
    
    # Fix usage of UnifiedDatabaseManager -> DatabaseManager
    content = re.sub(
        r'\bUnifiedDatabaseManager\b',
        r'DatabaseManager',
        content
    )
    
    # Fix async context manager usage
    content = re.sub(
        r'async with get_async_session\(\) as',
        r'async with get_db() as',
        content
    )
    
    content = re.sub(
        r'async with get_db_session\(\) as',
        r'async with get_db() as',
        content
    )
    
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

def main():
    """Fix all database imports in test files."""
    project_root = Path(__file__).parent.parent
    test_dir = project_root / 'netra_backend' / 'tests'
    
    fixed_count = 0
    for root, dirs, files in os.walk(test_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                if fix_database_imports(file_path):
                    print(f"Fixed: {file_path}")
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()