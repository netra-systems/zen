#!/usr/bin/env python3
"""Fix supervisor agent import issues.

Business Value Justification (BVJ):
- Segment: Platform
- Business Goal: Development Velocity  
- Value Impact: Fixes critical import blocking tests
- Revenue Impact: Enables CI/CD pipeline success
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Add project root to path


def fix_supervisor_imports(file_path: Path) -> bool:
    """Fix supervisor agent imports in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # Fix supervisor.agent import to supervisor_consolidated
        replacements = [
            ('from netra_backend.app.agents.supervisor.agent import SupervisorAgent',
             'from netra_backend.app.agents.supervisor_ssot import SupervisorAgent'),
            ('from netra_backend.app.agents.supervisor.agent import',
             'from netra_backend.app.agents.supervisor_ssot import'),
            # Fix PerformanceMetric imports
            ('from netra_backend.app.monitoring.models import PerformanceMetric',
             'from netra_backend.app.schemas.monitoring import PerformanceMetric'),
        ]
        
        for old_text, new_text in replacements:
            if old_text in content:
                content = content.replace(old_text, new_text)
                print(f"  - Replaced: {old_text[:50]}...")
        
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            print(f"[OK] Fixed imports in {file_path}")
            return True
        return False
    except Exception as e:
        print(f"[ERROR] Error fixing {file_path}: {e}")
        return False


def find_files_with_bad_imports() -> List[Path]:
    """Find all Python files with problematic imports."""
    files = []
    
    # Search patterns
    patterns = [
        'from netra_backend.app.agents.supervisor.agent',
        'from netra_backend.app.monitoring.models import PerformanceMetric'
    ]
    
    # Search in key directories
    dirs_to_search = [
        PROJECT_ROOT / 'netra_backend',
        PROJECT_ROOT / 'tests',
    ]
    
    for dir_path in dirs_to_search:
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                for pattern in patterns:
                    if pattern in content:
                        files.append(py_file)
                        break
            except Exception:
                pass
    
    return files


def main():
    """Main execution."""
    print("=" * 60)
    print("FIXING SUPERVISOR AND MONITORING IMPORTS")
    print("=" * 60)
    
    # Find files with bad imports
    files = find_files_with_bad_imports()
    print(f"\nFound {len(files)} files with problematic imports")
    
    # Fix imports
    fixed_count = 0
    for file_path in files:
        if fix_supervisor_imports(file_path):
            fixed_count += 1
    
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: Fixed {fixed_count} files")
    print("=" * 60)
    
    return 0 if fixed_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())