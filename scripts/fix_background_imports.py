#!/usr/bin/env python3
"""Fix all BackgroundTaskManager imports."""

import os
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    original_content = content
    
    # Fix the import
    content = content.replace(
        'from netra_backend.app.background import BackgroundTaskManager',
        'from netra_backend.app.services.background_task_manager import BackgroundTaskManager'
    )
    
    # Also fix any corrupted imports
    content = content.replace(
        'from C import BackgroundTaskManager',
        'from netra_backend.app.services.background_task_manager import BackgroundTaskManager'
    )
    
    if content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path.name}")
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False
    
    return False

def main():
    """Main execution function."""
    root_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1')
    
    files_to_fix = [
        'netra_backend/tests/agents/test_supply_researcher_scheduler.py',
        'netra_backend/tests/services/test_supply_research_scheduler_jobs.py',
        'netra_backend/tests/services/test_scheduler_retry_logic.py',
        'netra_backend/tests/services/test_scheduler_jobs_core.py',
        'netra_backend/app/services/supply_research_scheduler.py',
        'tests/e2e/test_startup_initialization.py',
    ]
    
    print("Fixing BackgroundTaskManager imports...")
    print("=" * 40)
    
    fixed_count = 0
    for file_path in files_to_fix:
        full_path = root_dir / file_path
        if full_path.exists():
            if fix_file(full_path):
                fixed_count += 1
        else:
            print(f"Not found: {file_path}")
    
    print("=" * 40)
    print(f"Fixed {fixed_count} files")
    
    return 0

if __name__ == "__main__":
    exit(main())