#!/usr/bin/env python3
"""
Final analysis: Separate backup corruption from active test files
"""
import ast
import glob
from pathlib import Path
from collections import defaultdict

def analyze_active_vs_backup_errors():
    """Separate active test files from backup directories"""

    # Define active test directories (not backups)
    active_patterns = [
        "./tests/**/*.py",
        "./netra_backend/tests/**/*.py",
        "./auth_service/tests/**/*.py",
        "./frontend/tests/**/*.py",
        "./test_framework/**/*.py"
    ]

    # Define backup patterns
    backup_patterns = [
        "./backup*/**/*.py",
        "./backups/**/*.py"
    ]

    # Collect active files
    active_files = set()
    for pattern in active_patterns:
        active_files.update(glob.glob(pattern, recursive=True))

    # Collect backup files
    backup_files = set()
    for pattern in backup_patterns:
        backup_files.update(glob.glob(pattern, recursive=True))

    print(f"Active test files: {len(active_files)}")
    print(f"Backup test files: {len(backup_files)}")

    # Analyze syntax errors in active files only
    active_errors = defaultdict(list)
    active_clean = []

    for filepath in sorted(active_files):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                ast.parse(content)
                active_clean.append(filepath)
            except SyntaxError as e:
                error_type = "unknown"
                if "unterminated string literal" in str(e).lower():
                    error_type = "unterminated_string"
                elif "unterminated f-string" in str(e).lower():
                    error_type = "unterminated_fstring"
                elif "unexpected indent" in str(e).lower() or "unindent" in str(e).lower():
                    error_type = "indentation"
                elif "invalid syntax" in str(e).lower():
                    error_type = "invalid_syntax"
                else:
                    error_type = "other_syntax"

                active_errors[error_type].append((filepath, f"Line {e.lineno}: {e.msg}"))

        except Exception as e:
            active_errors["file_error"].append((filepath, str(e)))

    # Print active file analysis
    print(f"\n=== ACTIVE TEST FILES ANALYSIS ===")
    print(f"Clean active files: {len(active_clean)}")

    total_active_errors = sum(len(files) for files in active_errors.values())
    print(f"Active files with errors: {total_active_errors}")

    if total_active_errors > 0:
        print(f"\nActive error breakdown:")
        for error_type, files in sorted(active_errors.items()):
            if files:
                percentage = (len(files) / total_active_errors * 100)
                print(f"  {error_type}: {len(files)} files ({percentage:.1f}%)")

    # Categorize active errors by business priority
    business_categories = {
        'websocket': [],
        'agent': [],
        'auth': [],
        'mission_critical': [],
        'integration': [],
        'unit': []
    }

    for error_type, files in active_errors.items():
        for filepath, error_msg in files:
            filepath_lower = filepath.lower()

            # Categorize by business priority
            if any(term in filepath_lower for term in ['websocket', 'ws_', 'socket', 'events']):
                business_categories['websocket'].append((filepath, error_msg))
            elif any(term in filepath_lower for term in ['agent', 'supervisor', 'orchestrat', 'execution']):
                business_categories['agent'].append((filepath, error_msg))
            elif any(term in filepath_lower for term in ['auth', 'login', 'jwt', 'token', 'session']):
                business_categories['auth'].append((filepath, error_msg))
            elif 'mission_critical' in filepath_lower or 'critical' in filepath_lower:
                business_categories['mission_critical'].append((filepath, error_msg))
            elif any(term in filepath_lower for term in ['integration', 'e2e', 'end_to_end']):
                business_categories['integration'].append((filepath, error_msg))
            else:
                business_categories['unit'].append((filepath, error_msg))

    print(f"\n=== ACTIVE FILES BY BUSINESS PRIORITY ===")
    for category, files in sorted(business_categories.items()):
        if files:
            print(f"{category.upper()}: {len(files)} files with errors")
            for filepath, error_msg in files[:3]:  # Show first 3
                print(f"  {filepath}")
                print(f"    {error_msg}")
            if len(files) > 3:
                print(f"    ... and {len(files) - 3} more")

    return {
        'active_files': len(active_files),
        'backup_files': len(backup_files),
        'active_clean': len(active_clean),
        'active_errors': total_active_errors,
        'business_categories': business_categories
    }

if __name__ == "__main__":
    results = analyze_active_vs_backup_errors()