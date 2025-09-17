#!/usr/bin/env python3
"""Script to fix common syntax errors in test files"""

import ast
import os
import re
import argparse
import logging
from pathlib import Path
from typing import List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_unclosed_parenthesis(content: str) -> str:
    """Fix unclosed parenthesis in import statements"""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for import statements with unclosed parentheses
        if ('from ' in line and '(' in line) or ('import ' in line and '(' in line):
            paren_count = line.count('(') - line.count(')')
            
            if paren_count > 0:
                # Found unclosed parenthesis - look for the end or close it
                import_lines = [line]
                j = i + 1
                
                while j < len(lines) and paren_count > 0:
                    next_line = lines[j]
                    paren_count += next_line.count('(') - next_line.count(')')
                    import_lines.append(next_line)
                    j += 1
                
                # If we still have unclosed parentheses, close them
                if paren_count > 0:
                    import_lines[-1] = import_lines[-1].rstrip() + ')'
                
                fixed_lines.extend(import_lines)
                i = j
                continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)

def fix_orphaned_methods(content: str) -> str:
    """Fix methods without class definitions"""
    lines = content.split('\n')
    
    # Look for orphaned methods (functions at wrong indentation)
    orphaned_method_found = False
    first_orphan_line = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Look for methods that start with spaces but no class above them
        if line.startswith('    def ') or (stripped.startswith('def ') and line.startswith('    ')):
            # Check if there's a class definition above this line
            has_class_above = False
            for j in range(i-1, -1, -1):
                prev_line = lines[j].strip()
                if prev_line.startswith('class '):
                    has_class_above = True
                    break
                elif prev_line.startswith('def ') and not lines[j].startswith('    '):
                    break
            
            if not has_class_above:
                orphaned_method_found = True
                if first_orphan_line == -1:
                    first_orphan_line = i
                break
    
    if orphaned_method_found:
        # Find where to insert the class (after imports/docstrings)
        insert_pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('#') and 
                not stripped.startswith('"""') and
                not stripped.startswith("'''") and
                not stripped.startswith('import ') and 
                not stripped.startswith('from ') and
                not line.startswith('"""') and
                not line.startswith("'''")):
                insert_pos = i
                break
        
        # Insert a test class before the orphaned methods
        lines.insert(insert_pos, '')
        lines.insert(insert_pos + 1, 'class TestSyntaxFix:')
        lines.insert(insert_pos + 2, '    """Test class for orphaned methods"""')
        lines.insert(insert_pos + 3, '')
    
    return '\n'.join(lines)

def fix_incomplete_imports(content: str) -> str:
    """Fix incomplete import statements"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix common incomplete import patterns
        if line.strip().startswith('from ') and line.strip().endswith('('):
            # Line ends with open paren but no closing paren
            if i + 1 < len(lines) and not lines[i + 1].strip():
                # Next line is empty, close the import
                line = line.rstrip() + ')'
        elif line.strip() == 'from' or line.strip().endswith('from'):
            # Incomplete 'from' statement
            line = '# ' + line + ' # Incomplete import statement'
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_unexpected_indent(content: str) -> str:
    """Fix unexpected indentation issues"""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # If line starts with spaces but previous meaningful line doesn't establish context
        if line.startswith('    ') and line.strip():
            # Check if this could be an orphaned method/function definition
            if i > 0:
                # Look back to find the last non-empty line
                prev_meaningful = None
                for j in range(i-1, -1, -1):
                    if lines[j].strip():
                        prev_meaningful = lines[j]
                        break
                
                # If previous line doesn't establish indentation context, this might be orphaned
                if (prev_meaningful and 
                    not prev_meaningful.strip().endswith(':') and
                    not prev_meaningful.startswith('    ') and
                    not prev_meaningful.strip().startswith('class ') and
                    not prev_meaningful.strip().startswith('def ') and
                    line.strip().startswith('def ')):
                    
                    # This looks like an orphaned method - it will be caught by fix_orphaned_methods
                    pass
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

def fix_invalid_syntax(content: str) -> str:
    """Fix various invalid syntax issues"""
    lines = content.split('\n')
    fixed_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        original_line = line

        # CRITICAL FIX: Pattern found in 808 errors - unterminated docstrings
        # Pattern: "Real WebSocket connection for testing instead of mocks.""
        if '"Real WebSocket connection for testing instead of mocks.""' in line:
            line = line.replace(
                '"Real WebSocket connection for testing instead of mocks.""',
                '"""Real WebSocket connection for testing instead of mocks."""'
            )

        # Fix other common unterminated string patterns
        if '"Test suite for ' in line and line.count('"') == 3 and line.endswith('""'):
            # Pattern: "Test suite for backend login endpoint 500 error fixes.""
            line = re.sub(r'^(\s*)"(.+)""$', r'\1"""\2"""', line)

        # Fix unterminated string literals at line start
        if line.strip().startswith('"') and not line.strip().startswith('"""'):
            # Check if it's a single quote at start and ends with ""
            if line.strip().endswith('""') and line.count('"') == 3:
                line = re.sub(r'^(\s*)"(.+)""$', r'\1"""\2"""', line)

        # Fix f-string unterminated literals
        if 'logger.warning(f"' in line and line.count('"') == 1:
            line = line.rstrip() + '")'
        if 'print(f"' in line and line.count('"') == 1:
            line = line.rstrip() + '")'

        # Fix incomplete import statements that end abruptly
        if ('from ' in line and
            ('import (' in line or line.strip().endswith('(')) and
            i + 1 < len(lines)):

            # Look for the pattern where import statement is cut off
            next_line = lines[i + 1] if i + 1 < len(lines) else ""

            # If next line starts with a new statement, close the import
            if (next_line.strip().startswith('from ') or
                next_line.strip().startswith('import ') or
                next_line.strip().startswith('class ') or
                next_line.strip().startswith('def ') or
                not next_line.strip()):

                if not line.strip().endswith(')'):
                    line = line.rstrip() + ')'

        # Fix unmatched brackets patterns
        if '{ )' in line:
            line = line.replace('{ )', '{ }')
        if '[ )' in line:
            line = line.replace('[ )', '[ ]')
        if '( }' in line:
            line = line.replace('( }', '( )')

        # Fix unterminated print statements
        if 'print(" )' in line:
            line = line.replace('print(" )', 'print("")')
        if "print(' )" in line:
            line = line.replace("print(' )", "print('')")

        # Fix Magic class declarations
        if re.match(r'\s*(\w+)\s*=\s*Magic\s*$', line):
            line = re.sub(r'(\s*)(\w+)\s*=\s*Magic\s*$', r'\1\2 = MagicMock()', line)
        if 'Magic        mock_' in line:
            line = line.replace('Magic        mock_', 'MagicMock(); mock_')
        if 'mock_services_config = Magic mock_log' in line:
            line = line.replace('mock_services_config = Magic mock_log', 'mock_services_config = MagicMock(); mock_log')

        # Fix AsyncMock syntax issues
        if 'AsyncMock( )' in line and 'status_code=' in line:
            line = line.replace('AsyncMock( )', 'AsyncMock(')
        if 'AsyncNone' in line:
            line = line.replace('AsyncNone', 'MagicMock()')
        if 'AuthManager()' in line and 'mock_' in line:
            line = line.replace('AuthManager()', 'MagicMock()')

        # Fix malformed function calls
        if 'response = client.get( )' in line:
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if '"formatted_string"' in next_line:
                line = 'response = client.get("formatted_string")'
                i += 1  # Skip the next line as we merged it

        # Fix malformed dict syntax in return values
        if 'return_value = { )' in line:
            line = line.replace('return_value = { )', 'return_value = {')

        # Fix specific variable assignments
        if 'mock_user_response = mock_user_response_instance' in line:
            line = line.replace('mock_user_response = mock_user_response_instance', 'mock_user_response = MagicMock()')
        if 'mock_repo = mock_repo_instance' in line:
            line = line.replace('mock_repo = mock_repo_instance', 'mock_repo = MagicMock()')
        if 'mock_user = mock_user_instance' in line:
            line = line.replace('mock_user = mock_user_instance', 'mock_user = MagicMock()')

        # Fix string formatting issues
        if '"formatted_string"' in line and not ('get(' in line or 'format(' in line):
            line = line.replace('"formatted_string"', '""')

        # Fix unterminated string concatenations
        if '" + "' in line and line.count('"') % 2 != 0:
            line = line.replace('" + "', ' + ')

        # Fix malformed print statements with broken concatenation
        if 'print("")' in line and 'print("' in lines[i-1] if i > 0 else False:
            prev_line = lines[i-1] if i > 0 else ""
            if 'print("' in prev_line and not prev_line.strip().endswith(')'):
                # Merge broken print statement
                merged_print = prev_line.strip().rstrip('"') + '")'
                fixed_lines[-1] = merged_print  # Replace previous line
                continue  # Skip current line

        # Fix broken list/dict definitions
        if line.strip() == '}' and i > 0:
            prev_line = lines[i-1] if i > 0 else ""
            if prev_line.strip().endswith(','):
                # This might be a continuation
                pass

        # Fix indentation for print statements
        if line.startswith('print("') and not line.startswith('    '):
            # Check if this should be indented based on context
            if i > 0:
                prev_line = lines[i-1] if i > 0 else ""
                if (prev_line.strip().endswith(':') or
                    prev_line.startswith('    ') or
                    'try:' in prev_line or 'except' in prev_line):
                    line = '    ' + line

        # Fix malformed list definitions
        if 'files_to_check = [ ]' in line:
            line = line.replace('files_to_check = [ ]', 'files_to_check = [')
        if 'test_files = [ ]' in line:
            line = line.replace('test_files = [ ]', 'test_files = [')
        if 'coverage_areas = { }' in line:
            line = line.replace('coverage_areas = { }', 'coverage_areas = {')

        # Fix malformed string concatenation in print statements
        if '[Test' in line and ']:' in line and line.count('"') == 1:
            line = line.replace('[Test', '"[Test').replace(']:', ']:"')
        if '[RUNNING' in line and line.count('"') == 0:
            line = '"' + line + '")'

        # Comment out misplaced pytest fixture decorators
        if '@pytest.fixture' in line and i + 1 < len(lines):
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if 'def test_' in next_line and not next_line.strip().startswith('def test_'):
                line = line.replace('@pytest.fixture', '# @pytest.fixture')

        fixed_lines.append(line)
        i += 1

    return '\n'.join(fixed_lines)

def check_syntax(filepath: Path) -> List[str]:
    """Check if file has syntax errors"""
    errors = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"{filepath}: {e.msg} at line {e.lineno}")
    except Exception as e:
        errors.append(f"{filepath}: {str(e)}")
    return errors

def fix_file(filepath: Path) -> bool:
    """Fix common syntax errors in a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes in order of complexity
        content = fix_incomplete_imports(content)
        content = fix_unclosed_parenthesis(content)
        content = fix_invalid_syntax(content)
        content = fix_unexpected_indent(content)
        content = fix_orphaned_methods(content)
        
        # Only write if changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False

def main():
    """Main function to fix syntax errors in test files"""
    parser = argparse.ArgumentParser(description='Fix syntax errors in Python test files')
    parser.add_argument('--file', help='Fix a specific file')
    parser.add_argument('--directory', help='Fix all test files in directory')
    parser.add_argument('--priority-files', action='store_true', help='Fix priority files first')
    parser.add_argument('--validate-only', action='store_true', help='Only validate syntax, don\'t fix')

    args = parser.parse_args()

    if args.file:
        filepath = Path(args.file)
        if args.validate_only:
            errors = check_syntax(filepath)
            if errors:
                print(f"INVALID: {filepath}")
                for error in errors:
                    print(f"  {error}")
            else:
                print(f"VALID: {filepath}")
        else:
            if fix_file(filepath):
                print(f"Fixed: {filepath}")
                # Re-check
                errors = check_syntax(filepath)
                if not errors:
                    print(f"✓ Syntax validated: {filepath}")
                else:
                    print(f"⚠ Still has errors: {filepath}")
            else:
                print(f"No changes needed: {filepath}")
        return

    if args.directory:
        test_dir = Path(args.directory)
        test_files = list(test_dir.glob('**/*.py'))
    elif args.priority_files:
        # Priority files identified in the analysis
        priority_files = [
            'auth_service/tests/test_oauth_state_validation.py',
            'tests/run_refresh_tests.py',
            'tests/test_critical_dev_launcher_issues.py',
            'auth_service/tests/test_redis_staging_connectivity_fixes.py',
            'tests/integration_test_docker_rate_limiter.py'
        ]
        test_files = [Path(f) for f in priority_files if Path(f).exists()]
        print(f"Priority files to fix: {len(test_files)}")
    else:
        # Default behavior - search all test directories
        test_dirs = [
            Path('netra_backend/tests'),
            Path('tests'),
            Path('auth_service/tests'),
            Path('integration_tests'),
            Path('test_framework'),
            Path('frontend/tests')
        ]

        test_files = []
        for test_dir in test_dirs:
            if test_dir.exists():
                test_files.extend(test_dir.glob('**/*.py'))

    print(f"Found {len(test_files)} test files")

    # Check for syntax errors
    files_with_errors = []
    for filepath in test_files:
        errors = check_syntax(filepath)
        if errors:
            files_with_errors.append((filepath, errors))

    print(f"Found {len(files_with_errors)} files with syntax errors")

    if args.validate_only:
        for filepath, errors in files_with_errors:
            print(f"INVALID: {filepath}")
            for error in errors:
                print(f"  {error}")
        return

    # Fix errors
    fixed_count = 0
    for filepath, errors in files_with_errors:
        logger.info(f"Fixing {filepath}")
        if fix_file(filepath):
            fixed_count += 1
            print(f"Fixed: {filepath}")

    print(f"\nFixed {fixed_count} files")

    # Re-check for remaining errors
    remaining_errors = []
    for filepath, _ in files_with_errors:
        errors = check_syntax(filepath)
        if errors:
            remaining_errors.extend(errors)

    if remaining_errors:
        print(f"\n{len(remaining_errors)} syntax errors remain:")
        for error in remaining_errors[:20]:  # Show first 20
            print(f"  - {error}")
        if len(remaining_errors) > 20:
            print(f"  ... and {len(remaining_errors) - 20} more")
    else:
        print("\nAll syntax errors fixed!")

if __name__ == '__main__':
    main()