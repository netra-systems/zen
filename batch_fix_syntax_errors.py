#!/usr/bin/env python3
"""
Batch fix specific syntax error patterns found in the codebase.
"""

import ast
import re
import os
from pathlib import Path


class BatchSyntaxFixer:
    """Fix specific known syntax error patterns."""
    
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
    
    def fix_file(self, file_path: str) -> bool:
        """Fix syntax errors in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            if not original_content.strip():
                return True
            
            content = original_content
            
            # Apply specific fixes
            content = self._fix_import_statements(content)
            content = self._fix_indentation_issues(content)
            content = self._fix_empty_function_bodies(content)
            content = self._fix_unterminated_strings(content)
            content = self._fix_bracket_issues(content)
            content = self._fix_decorator_issues(content)
            
            # Verify the fix worked
            try:
                ast.parse(content)
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Fixed: {file_path}")
                    self.fixed_files.append(file_path)
                return True
            except SyntaxError as e:
                print(f"Still has syntax error: {file_path} - {e}")
                self.failed_files.append((file_path, str(e)))
                return False
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            self.failed_files.append((file_path, str(e)))
            return False
    
    def _fix_import_statements(self, content: str) -> str:
        """Fix common import statement issues."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix import statements inside other imports
            if 'from ' in line and 'import (' in line:
                # Look for the pattern: from x import (
                # from y import z  <- this should be outside
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('from '):
                    # Move the second import outside
                    next_line = lines[i + 1].strip()
                    fixed_lines.append(line)
                    # Skip the next line, we'll add it after the closing paren
                    i += 1
                    # Find the closing paren and add the import after it
                    j = i + 1
                    while j < len(lines) and ')' not in lines[j]:
                        fixed_lines.append(lines[j])
                        j += 1
                    if j < len(lines):
                        fixed_lines.append(lines[j])  # closing paren line
                        fixed_lines.append('')  # empty line
                        fixed_lines.append(next_line)  # moved import
                    continue
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_indentation_issues(self, content: str) -> str:
        """Fix common indentation problems."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix function definitions with wrong indentation
            if re.match(r'^\s*(def|class|@)', line.strip()):
                # Check if this is wrongly indented
                if line.startswith(' ') and not line.startswith('    '):
                    # Fix indentation to proper 4-space
                    stripped = line.lstrip()
                    if i > 0:
                        # Check previous line indentation
                        prev_line = lines[i-1] if i-1 >= 0 else ""
                        if prev_line.strip() and ':' in prev_line:
                            # This should be indented
                            line = '    ' + stripped
                        else:
                            # This should be at module level
                            line = stripped
            
            # Fix unindent issues
            if line.strip() and not line.startswith(' '):
                # Check if previous line suggests this should be indented
                if i > 0:
                    prev_line = lines[i-1] if i-1 >= 0 else ""
                    if prev_line.strip().endswith(':'):
                        # This line should be indented
                        line = '    ' + line
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_empty_function_bodies(self, content: str) -> str:
        """Add pass to empty function bodies."""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            fixed_lines.append(line)
            
            # Check if this is a function/class definition that needs a body
            if (line.strip().endswith(':') and 
                any(keyword in line for keyword in ['def ', 'class ', 'if ', 'else', 'elif ', 'for ', 'while ', 'try', 'except', 'finally'])):
                
                # Look ahead to see if there's a body
                j = i + 1
                has_body = False
                
                while j < len(lines):
                    next_line = lines[j]
                    if not next_line.strip():  # empty line
                        j += 1
                        continue
                    
                    # Check if indented properly
                    if next_line.startswith('    ') or next_line.startswith('\t'):
                        has_body = True
                        break
                    else:
                        # Not indented, no body
                        break
                
                if not has_body:
                    # Add pass with proper indentation
                    indent = len(line) - len(line.lstrip()) + 4
                    fixed_lines.append(' ' * indent + 'pass')
        
        return '\n'.join(fixed_lines)
    
    def _fix_unterminated_strings(self, content: str) -> str:
        """Fix unterminated string literals."""
        # This is tricky - let's be conservative and only fix obvious cases
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Count quotes, but be smart about it
            if '"""' in line:
                # Triple quote - check if it's complete
                if line.count('"""') == 1:
                    # Might be unterminated - but this is complex to fix safely
                    pass  # Skip for now
            elif line.count('"') % 2 == 1:
                # Odd number of quotes - might be unterminated
                if not line.rstrip().endswith('\\'):
                    # Not a line continuation, probably unterminated
                    line = line + '"'
            elif line.count("'") % 2 == 1:
                # Odd number of single quotes
                if not line.rstrip().endswith('\\'):
                    line = line + "'"
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_bracket_issues(self, content: str) -> str:
        """Fix bracket and parenthesis issues."""
        # Count brackets and balance them
        open_brackets = {'(': 0, '[': 0, '{': 0}
        close_brackets = {')': '(', ']': '[', '}': '{'}
        
        lines = content.split('\n')
        
        # Count all brackets first
        for line in lines:
            for char in line:
                if char in open_brackets:
                    open_brackets[char] += 1
                elif char in close_brackets:
                    corresponding_open = close_brackets[char]
                    if open_brackets[corresponding_open] > 0:
                        open_brackets[corresponding_open] -= 1
        
        # Add missing closing brackets at the end
        missing_closers = []
        for opener, count in open_brackets.items():
            if count > 0:
                if opener == '(':
                    missing_closers.extend([')'] * count)
                elif opener == '[':
                    missing_closers.extend([']'] * count)
                elif opener == '{':
                    missing_closers.extend(['}'] * count)
        
        if missing_closers:
            lines.append(''.join(missing_closers))
        
        return '\n'.join(lines)
    
    def _fix_decorator_issues(self, content: str) -> str:
        """Fix decorator syntax issues."""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Fix decorators that are not on their own line
            if '@' in line and not line.strip().startswith('@'):
                # Split decorator from other content
                at_pos = line.find('@')
                before = line[:at_pos].rstrip()
                after = line[at_pos:]
                
                if before:
                    fixed_lines.append(before)
                fixed_lines.append(after)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)


def main():
    """Main execution."""
    error_files = [
        "netra_backend/tests/test_agent_service_fixtures.py",
        "netra_backend/tests/test_business_value_fixtures.py", 
        "netra_backend/tests/test_chat_content_validation.py",
        "netra_backend/tests/test_chat_send_receive.py",
        "netra_backend/tests/test_clickhouse_client_comprehensive.py",
        "netra_backend/tests/test_clickhouse_factory.py",
        "netra_backend/tests/test_clickhouse_factory_simple.py",
        "netra_backend/tests/test_config_helpers.py",
        "netra_backend/tests/test_database_session_efficiency.py",
        "netra_backend/tests/test_data_sub_agent_coordination.py",
        "netra_backend/tests/test_dev_smoke_test.py",
        "netra_backend/tests/test_gcp_staging_api_endpoint_availability.py",
        "netra_backend/tests/test_gcp_staging_startup_sequence_robustness.py",
        "netra_backend/tests/test_goals_triage_ssot_violations.py",
        "netra_backend/tests/test_health_monitor_checks.py",
        "netra_backend/tests/test_mcp_integration_fixtures.py",
        "netra_backend/tests/test_redis_factory.py",
        "netra_backend/tests/test_thread_repository.py",
        "netra_backend/tests/test_websocket_critical.py",
    ]
    
    fixer = BatchSyntaxFixer()
    
    print("Fixing critical syntax error files...")
    print(f"Processing {len(error_files)} files")
    
    for file_path in error_files:
        if os.path.exists(file_path):
            fixer.fix_file(file_path)
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nResults:")
    print(f"Fixed: {len(fixer.fixed_files)}")
    print(f"Failed: {len(fixer.failed_files)}")
    
    if fixer.failed_files:
        print("\nFiles still with errors:")
        for file_path, error in fixer.failed_files:
            print(f"  {file_path}: {error}")


if __name__ == "__main__":
    main()