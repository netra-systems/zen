#!/usr/bin/env python3
"""
Detailed error pattern analysis for systematic issues
"""
import ast
import re
from pathlib import Path
from collections import defaultdict

def analyze_error_patterns():
    """Analyze specific error patterns to identify systematic issues"""

    # Known files with syntax errors from our analysis
    error_files = [
        "./tests/mission_critical/test_docker_stability_suite.py",
        "./backups/issue_450_redis_migration/tests/chat_system/integration/test_orchestration_flow.py",
        "./tests/mission_critical/test_no_ssot_violations.py",
        "./tests/mission_critical/test_orchestration_integration.py"
    ]

    patterns = {
        'unterminated_f_string': [],
        'mismatched_braces': [],
        'unterminated_strings': [],
        'missing_quotes': [],
        'malformed_dict_return': []
    }

    for filepath in error_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            print(f"\n=== Analyzing {filepath} ===")

            # Check for f-string issues
            for i, line in enumerate(lines, 1):
                if 'f"' in line and not line.count('"') % 2 == 0:
                    patterns['unterminated_f_string'].append((filepath, i, line.strip()))
                    print(f"  Line {i}: Unterminated f-string: {line.strip()}")

                # Check for brace mismatches
                if '{' in line and '}' not in line and 'return' in line:
                    patterns['mismatched_braces'].append((filepath, i, line.strip()))
                    print(f"  Line {i}: Possible brace mismatch: {line.strip()}")

                # Check for malformed dict returns
                if re.search(r'return\s*{\s*\)', line):
                    patterns['malformed_dict_return'].append((filepath, i, line.strip()))
                    print(f"  Line {i}: Malformed dict return: {line.strip()}")

                # Check for specific patterns
                if 'allow_module_level=True)' in line and 'pytest.skip(' in line:
                    patterns['unterminated_f_string'].append((filepath, i, line.strip()))
                    print(f"  Line {i}: Missing quote in pytest.skip: {line.strip()}")

        except FileNotFoundError:
            print(f"File not found: {filepath}")
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")

    # Summary
    print(f"\n=== PATTERN SUMMARY ===")
    for pattern_name, occurrences in patterns.items():
        if occurrences:
            print(f"{pattern_name}: {len(occurrences)} occurrences")
            for filepath, line_num, line_content in occurrences:
                print(f"  {filepath}:{line_num} - {line_content}")

def analyze_backup_corruption():
    """Check if backup directories contain corrupted files"""
    backup_paths = [
        "./backups/issue_450_redis_migration/",
        "./backups/syntax_fix_*/",
        "./backup/url_migration/"
    ]

    print(f"\n=== BACKUP CORRUPTION ANALYSIS ===")

    # Check if most errors are in backup directories
    import glob

    backup_files = []
    for pattern in backup_paths:
        backup_files.extend(glob.glob(pattern + "**/*.py", recursive=True))

    print(f"Found {len(backup_files)} Python files in backup directories")

    # This suggests many corrupted files are in backups, not primary codebase
    return len(backup_files)

if __name__ == "__main__":
    analyze_error_patterns()
    analyze_backup_corruption()