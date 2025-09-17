#!/usr/bin/env python3
"""
Automated Syntax Repair Tool for Test Files
Fixes the 4 main corruption patterns identified in 1,383 test files.
"""

import re
import os
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
import sys

class SyntaxRepairTool:
    """Tool to automatically fix syntax errors in Python test files."""
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'bracket_fixes': 0,
            'indentation_fixes': 0,
            'quote_fixes': 0,
            'other_fixes': 0,
            'files_fixed': 0,
            'backup_count': 0
        }
    
    def backup_file(self, filepath: str) -> str:
        """Create backup of file before modification."""
        backup_path = f"{filepath}.backup"
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)
            self.stats['backup_count'] += 1
        return backup_path
    
    def fix_bracket_mismatches(self, content: str) -> Tuple[str, int]:
        """Fix bracket/parentheses mismatches: { opened but ) used to close."""
        fixes = 0
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Pattern 1: { ) - dict opened with { but closed with )
            if re.search(r'\{\s*\)', line):
                lines[i] = re.sub(r'\{\s*\)', '{}', line)
                fixes += 1
                print(f"  Fixed {{}} pattern: {line.strip()}")
            
            # Pattern 2: { )) - dict opened with { but closed with ))
            elif re.search(r'\{\s*\)\)', line):
                lines[i] = re.sub(r'\{\s*\)\)', '})', line)
                fixes += 1
                print(f"  Fixed {{)}} pattern: {line.strip()}")
            
            # Pattern 3: [ ) - list opened with [ but closed with )
            elif re.search(r'\[\s*\)', line):
                lines[i] = re.sub(r'\[\s*\)', '[]', line)
                fixes += 1
                print(f"  Fixed [] pattern: {line.strip()}")
            
            # Pattern 4: Multiple function calls with { ) pattern
            elif 'json={' in line and ')' in line and not '}' in line:
                # Find the json={ and replace the ) with }
                if re.search(r'json=\{\s*\)', line):
                    lines[i] = re.sub(r'json=\{\s*\)', 'json={}', line)
                    fixes += 1
                    print(f"  Fixed json={{}} pattern: {line.strip()}")
        
        return '\n'.join(lines), fixes
    
    def fix_indentation_errors(self, content: str) -> Tuple[str, int]:
        """Fix indentation errors - missing blocks after if statements."""
        fixes = 0
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Pattern 1: if statement followed by unindented code
            if re.match(r'^(\s*)if\s+.*:\s*$', line):
                indent_level = len(re.match(r'^(\s*)', line).group(1))
                
                # Check if next line is properly indented
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.strip() and not next_line.startswith(' ' * (indent_level + 4)):
                        # Add pass statement with proper indentation
                        lines.insert(i + 1, ' ' * (indent_level + 4) + 'pass')
                        fixes += 1
                        print(f"  Added pass after if: {line.strip()}")
            
            # Pattern 2: Unexpected unindent - fix by adding proper indentation
            elif line.strip().startswith('def ') and i > 0:
                prev_line = lines[i - 1].strip()
                if prev_line and not prev_line.endswith(':'):
                    # Previous line needs a colon or this def needs proper spacing
                    if not prev_line.endswith(':') and prev_line:
                        lines[i] = '\n' + line
                        fixes += 1
                        print(f"  Added newline before def: {line.strip()}")
            
            # Pattern 3: Unexpected indent - fix import statements
            elif line.strip().startswith('from ') or line.strip().startswith('import '):
                if line.startswith('    ') or line.startswith('\t'):
                    lines[i] = line.lstrip()
                    fixes += 1
                    print(f"  Fixed import indentation: {line.strip()}")
        
        return '\n'.join(lines), fixes
    
    def fix_quote_issues(self, content: str) -> Tuple[str, int]:
        """Fix unterminated string literals."""
        fixes = 0
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Pattern 1: print(" ) - unterminated string in print
            if re.search(r'print\(\s*"\s*\)', line):
                lines[i] = re.sub(r'print\(\s*"\s*\)', 'print("")', line)
                fixes += 1
                print(f"  Fixed print quote: {line.strip()}")
            
            # Pattern 2: Other unterminated strings
            elif line.count('"') % 2 != 0 and not line.strip().endswith('\\'):
                # Count quotes and try to balance
                if line.strip().endswith(' )'):
                    lines[i] = line.rstrip(' )') + '")'
                    fixes += 1
                    print(f"  Fixed unterminated string: {line.strip()}")
        
        return '\n'.join(lines), fixes
    
    def fix_other_syntax_errors(self, content: str) -> Tuple[str, int]:
        """Fix other common syntax issues."""
        fixes = 0
        
        # Fix logging.basicConfig syntax
        if 'logging.basicConfig( )' in content:
            content = content.replace('logging.basicConfig( )', 'logging.basicConfig()')
            fixes += 1
            print("  Fixed logging.basicConfig syntax")
        
        # Fix incomplete function calls
        content = re.sub(r'(\w+)\(\s*\)\s*\n(\s*)(\w+)=', r'\1(\n\2\3=', content)
        
        return content, fixes
    
    def validate_syntax(self, content: str) -> bool:
        """Validate if the content has valid Python syntax."""
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    
    def repair_file(self, filepath: str) -> bool:
        """Repair syntax errors in a single file."""
        print(f"\n🔧 Repairing: {filepath}")
        
        try:
            # Read original content
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create backup
            self.backup_file(filepath)
            
            # Apply fixes in order
            content = original_content
            total_fixes = 0
            
            # 1. Fix bracket mismatches
            content, bracket_fixes = self.fix_bracket_mismatches(content)
            total_fixes += bracket_fixes
            self.stats['bracket_fixes'] += bracket_fixes
            
            # 2. Fix indentation errors
            content, indent_fixes = self.fix_indentation_errors(content)
            total_fixes += indent_fixes
            self.stats['indentation_fixes'] += indent_fixes
            
            # 3. Fix quote issues
            content, quote_fixes = self.fix_quote_issues(content)
            total_fixes += quote_fixes
            self.stats['quote_fixes'] += quote_fixes
            
            # 4. Fix other issues
            content, other_fixes = self.fix_other_syntax_errors(content)
            total_fixes += other_fixes
            self.stats['other_fixes'] += other_fixes
            
            # Validate syntax
            if self.validate_syntax(content):
                # Write fixed content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                if total_fixes > 0:
                    print(f"  ✅ Fixed {total_fixes} issues - syntax valid")
                    self.stats['files_fixed'] += 1
                    return True
                else:
                    print(f"  ✅ No fixes needed - syntax already valid")
                    return True
            else:
                print(f"  ❌ Fixes applied but syntax still invalid")
                # Restore backup
                shutil.copy2(f"{filepath}.backup", filepath)
                return False
        
        except Exception as e:
            print(f"  ❌ Error repairing file: {e}")
            return False
        
        finally:
            self.stats['files_processed'] += 1
    
    def repair_from_report(self, report_file: str) -> None:
        """Repair files listed in the syntax error report."""
        print("🚀 Starting systematic syntax repair...")
        
        # Read error report
        with open(report_file, 'r') as f:
            content = f.read()
        
        # Extract file paths
        error_files = []
        for line in content.split('\n'):
            if line.startswith('./') and ':' in line:
                filepath = line.split(':')[0]
                if os.path.exists(filepath):
                    error_files.append(filepath)
        
        print(f"Found {len(error_files)} files to repair")
        
        # Process files by type for better success rate
        bracket_files = []
        indent_files = []
        quote_files = []
        other_files = []
        
        # Categorize files by error type
        current_file = None
        current_type = None
        
        for line in content.split('\n'):
            if line.startswith('./') and ':' in line:
                current_file = line.split(':')[0]
            elif line.strip().startswith('Type:'):
                current_type = line.split(':')[1].strip()
                if current_file and os.path.exists(current_file):
                    if current_type == 'brackets':
                        bracket_files.append(current_file)
                    elif current_type == 'indentation':
                        indent_files.append(current_file)
                    elif current_type == 'quotes':
                        quote_files.append(current_file)
                    else:
                        other_files.append(current_file)
        
        # Process in order of success likelihood
        all_files = []
        all_files.extend(bracket_files[:50])  # Start with 50 of each type
        all_files.extend(quote_files[:50])
        all_files.extend(other_files[:50])
        all_files.extend(indent_files[:50])
        
        print(f"\n📊 Processing priority files:")
        print(f"  Bracket files: {len(bracket_files)} (processing first 50)")
        print(f"  Quote files: {len(quote_files)} (processing first 50)")
        print(f"  Other files: {len(other_files)} (processing first 50)")
        print(f"  Indent files: {len(indent_files)} (processing first 50)")
        
        # Process files
        success_count = 0
        for i, filepath in enumerate(all_files[:200]):  # Process first 200 files
            print(f"\n[{i+1}/{min(200, len(all_files))}] Processing {filepath}")
            
            if self.repair_file(filepath):
                success_count += 1
            
            # Progress update every 25 files
            if (i + 1) % 25 == 0:
                print(f"\n📈 Progress: {i+1}/{min(200, len(all_files))} files processed")
                print(f"   Success rate: {success_count}/{i+1} ({success_count/(i+1)*100:.1f}%)")
        
        # Final report
        print(f"\n🎉 REPAIR COMPLETED!")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files successfully fixed: {self.stats['files_fixed']}")
        print(f"Success rate: {self.stats['files_fixed']/self.stats['files_processed']*100:.1f}%")
        print(f"Bracket fixes: {self.stats['bracket_fixes']}")
        print(f"Indentation fixes: {self.stats['indentation_fixes']}")
        print(f"Quote fixes: {self.stats['quote_fixes']}")
        print(f"Other fixes: {self.stats['other_fixes']}")
        print(f"Backups created: {self.stats['backup_count']}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 syntax_repair_tool.py <syntax_errors_report.txt>")
        sys.exit(1)
    
    report_file = sys.argv[1]
    if not os.path.exists(report_file):
        print(f"Error: Report file {report_file} not found")
        sys.exit(1)
    
    repair_tool = SyntaxRepairTool()
    repair_tool.repair_from_report(report_file)

if __name__ == "__main__":
    main()