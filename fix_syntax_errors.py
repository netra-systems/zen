#!/usr/bin/env python3
"""
Batch fix script for common syntax errors in test files.

Fixes patterns identified in 331 test files:
1. Unmatched parentheses: { ) -> }
2. Unmatched brackets: [ ) -> ]
3. Unterminated string literals
4. Basic indentation issues
"""

import os
import re
import sys
from pathlib import Path

def fix_unmatched_braces(content):
    """Fix { ) patterns to proper }"""
    # Pattern: { ) -> }
    content = re.sub(r'\{\s*\)', '}', content)

    # Pattern: json=}) -> json={
    content = re.sub(r'json=\}\)', 'json={', content)
    return content

def fix_unmatched_brackets(content):
    """Fix [ ) patterns to proper ]"""
    # Pattern: [ ) -> ]
    content = re.sub(r'\[\s*\)', ']', content)
    return content

def fix_unterminated_strings(content):
    """Fix basic unterminated string patterns"""
    lines = content.split('\n')
    fixed_lines = []

    for line in lines:
        # Look for unterminated string patterns like print(" without closing
        if 'print(' in line and line.count('"') % 2 == 1 and not line.strip().endswith('"'):
            # Try to close the string if it's clearly a print statement
            if line.strip().endswith(' )'):
                line = line.replace(' )', '")')
            elif not line.strip().endswith('"'):
                line = line + '"'

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)

def fix_json_structures(content):
    """Fix json={ patterns that need proper closing"""
    lines = content.split('\n')
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for json={ pattern
        if 'json={' in line and not '}' in line:
            # This line starts a JSON structure
            json_content_lines = [line]
            i += 1

            # Collect subsequent lines that look like JSON content
            while i < len(lines):
                next_line = lines[i]
                # If line has content that looks like JSON properties
                if ('"' in next_line and ':' in next_line) or ('"' in next_line and ',' in next_line) or next_line.strip() == '':
                    json_content_lines.append(next_line)
                    i += 1
                else:
                    # This line doesn't look like JSON content, stop collecting
                    break

            # Add closing } and ) if needed
            if len(json_content_lines) > 1:
                # Remove empty lines at the end
                while json_content_lines and json_content_lines[-1].strip() == '':
                    json_content_lines.pop()

                # Add the closing brace and parenthesis
                if json_content_lines:
                    json_content_lines.append('        })')

                fixed_lines.extend(json_content_lines)
            else:
                # Single line, just add it
                fixed_lines.append(line)

            # Don't increment i again since we already processed multiple lines
            continue
        else:
            fixed_lines.append(line)
            i += 1

    return '\n'.join(fixed_lines)

def fix_file(file_path):
    """Fix a single file and return success status"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        content = original_content

        # Apply fixes in order
        content = fix_unmatched_braces(content)
        content = fix_unmatched_brackets(content)
        content = fix_unterminated_strings(content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed"
        else:
            return True, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main function to fix syntax errors"""
    if len(sys.argv) > 1:
        # Fix specific files
        files_to_fix = sys.argv[1:]
    else:
        # Get all Python files with syntax errors from the top priority ones
        error_files = [
            "auth_service/tests/test_oauth_state_validation.py",
            "auth_service/tests/integration/test_auth_endpoint_regression_prevention_integration.py",
            "auth_service/tests/integration/test_backend_auth_service_communication.py",
            "auth_service/tests/unit/test_auth_endpoint_routing_regression_prevention.py",
            "auth_service/tests/unit/test_auth_environment_urls.py",
            "tests/run_refresh_tests.py",
            "tests/test_alpine_container_selection.py",
            "tests/test_cors_middleware_fix_verified.py",
            "tests/integration_test_docker_rate_limiter.py",
            "tests/run_agent_orchestration_tests.py",
            "tests/run_all_refresh_tests.py"
        ]
        files_to_fix = error_files

    fixed_count = 0
    error_count = 0

    for file_path in files_to_fix:
        if os.path.exists(file_path):
            success, message = fix_file(file_path)
            if success:
                fixed_count += 1
                print(f"[OK] {file_path}: {message}")
            else:
                error_count += 1
                print(f"[ERR] {file_path}: {message}")
        else:
            print(f"[WARN] {file_path}: File not found")

    print(f"\nSummary: {fixed_count} files processed, {error_count} errors")
    return error_count == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)