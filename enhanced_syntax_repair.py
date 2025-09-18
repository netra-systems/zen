#!/usr/bin/env python3
"""
Enhanced Syntax Repair Tool - Phase 2
Handles complex multiline syntax errors and function call corruptions.
"""

import re
import os
import ast
from pathlib import Path
from typing import List, Dict, Tuple
import shutil
import sys

class EnhancedSyntaxRepair:
    """Enhanced tool for complex syntax repair patterns."""
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'multiline_fixes': 0,
            'function_call_fixes': 0,
            'complex_bracket_fixes': 0,
            'docstring_fixes': 0,
            'files_fixed': 0
        }
    
    def fix_function_call_corruption(self, content: str) -> Tuple[str, int]:
        """Fix corrupted function calls like logging.basicConfig( ) with params on next lines."""
        fixes = 0
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Pattern: function( ) followed by parameters on next lines
            if re.search(r'\w+\.\w+\(\s*\)\s*$', line) and i + 1 < len(lines):
                next_line = lines[i + 1]
                
                # Check if next line looks like function parameters
                if re.match(r'\s*\w+\s*=', next_line):
                    # Collect all parameter lines
                    param_lines = []
                    j = i + 1
                    
                    while j < len(lines) and (re.match(r'\s*\w+\s*=', lines[j]) or lines[j].strip() == ''):
                        if lines[j].strip():
                            param_lines.append(lines[j].strip())
                        j += 1
                    
                    if param_lines:
                        # Reconstruct function call
                        func_match = re.search(r'(\w+\.\w+)\(\s*\)', line)
                        if func_match:
                            func_name = func_match.group(1)
                            params = ', '.join(param_lines)
                            new_line = line.replace(f'{func_name}( )', f'{func_name}({params})')
                            
                            # Replace the lines
                            lines[i] = new_line
                            del lines[i + 1:j]
                            fixes += 1
                            print(f"  Fixed function call: {func_name}")
            
            i += 1
        
        return '\n'.join(lines), fixes
    
    def fix_multiline_structures(self, content: str) -> Tuple[str, int]:
        """Fix multiline data structures split incorrectly."""
        fixes = 0
        
        # Pattern 1: Dict/list definition split across lines
        patterns = [
            # connection_params = { \n 'host': ... \n }
            (r'(\w+\s*=\s*{\s*)\n(\s*[\'"]?\w+[\'"]?\s*:\s*.*)', r'\1\n    \2'),
            # list_var = [ \n item1, \n item2 \n ]
            (r'(\w+\s*=\s*\[\s*)\n(\s*.*)', r'\1\n    \2'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                fixes += 1
        
        return content, fixes
    
    def fix_missing_colons_and_indentation(self, content: str) -> Tuple[str, int]:
        """Fix missing colons and indentation issues."""
        fixes = 0
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            # Fix async def without proper structure
            if re.match(r'^\s*async def \w+\(.*\)\s*$', line) and i + 1 < len(lines):
                next_line = lines[i + 1]
                if not next_line.strip().startswith('"""') and not next_line.strip() == '':
                    # Add colon if missing
                    if not line.rstrip().endswith(':'):
                        lines[i] = line.rstrip() + ':'
                        fixes += 1
                        print(f"  Added colon to async def: {line.strip()}")
            
            # Fix try/except without colons
            elif re.match(r'^\s*(try|except|finally|else)\s*$', line):
                if not line.rstrip().endswith(':'):
                    lines[i] = line.rstrip() + ':'
                    fixes += 1
                    print(f"  Added colon to {line.strip()}")
        
        return '\n'.join(lines), fixes
    
    def fix_docstring_corruption(self, content: str) -> Tuple[str, int]:
        """Fix corrupted docstrings and comments."""
        fixes = 0
        
        # Fix corrupted docstrings
        patterns = [
            # '''...\n''' -> proper docstring
            (r"'''([^']*)\n\s*'''", r'"""\1"""'),
            # Fix incomplete docstrings
            (r'"""([^"]*)\n\s*[^"]*$', r'"""\1"""'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, content, re.MULTILINE):
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                fixes += 1
        
        return content, fixes
    
    def fix_import_block_corruption(self, content: str) -> Tuple[str, int]:
        """Fix corrupted import blocks."""
        fixes = 0
        lines = content.split('\n')
        
        # Group imports together and fix indentation
        import_lines = []
        other_lines = []
        in_import_block = False
        
        for line in lines:
            if re.match(r'\s*(from|import)\s+', line):
                # Fix indentation for imports
                clean_line = line.lstrip()
                import_lines.append(clean_line)
                in_import_block = True
                if line != clean_line:
                    fixes += 1
            else:
                if in_import_block and import_lines:
                    other_lines.extend(import_lines)
                    import_lines = []
                    in_import_block = False
                other_lines.append(line)
        
        # Add any remaining imports
        if import_lines:
            other_lines.extend(import_lines)
        
        return '\n'.join(other_lines), fixes
    
    def fix_complex_bracket_patterns(self, content: str) -> Tuple[str, int]:
        """Fix complex bracket mismatch patterns not caught by basic tool."""
        fixes = 0
        
        # Pattern 1: Multiple closing brackets on wrong lines
        # json={ )) -> json={}
        content = re.sub(r'json=\{\s*\)\)', 'json={}', content)
        if 'json={}' in content:
            fixes += 1
        
        # Pattern 2: Function calls with bracket mismatches  
        # func(param={ ) -> func(param={})
        content = re.sub(r'(\w+\([^)]*=\{\s*)\)', r'\1})', content)
        
        # Pattern 3: List/dict definitions spanning lines incorrectly
        # var = { ) \n "key": "value" -> var = {"key": "value"}
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for pattern: var = { )
            if re.search(r'\w+\s*=\s*\{\s*\)', line) and i + 1 < len(lines):
                # Check if next lines have key-value pairs
                j = i + 1
                kvp_lines = []
                while j < len(lines) and (re.match(r'\s*[\'"]?\w+[\'"]?\s*:', lines[j]) or lines[j].strip() == ''):
                    if lines[j].strip():
                        kvp_lines.append(lines[j].strip())
                    j += 1
                
                if kvp_lines:
                    # Reconstruct the dict
                    var_part = re.search(r'(\w+\s*=\s*)\{\s*\)', line).group(1)
                    dict_content = ', '.join(kvp_lines)
                    new_line = f'{var_part}{{{dict_content}}}'
                    
                    lines[i] = new_line
                    del lines[i + 1:j]
                    fixes += 1
                    print(f"  Fixed complex dict pattern")
            
            i += 1
        
        return '\n'.join(lines), fixes
    
    def validate_and_repair_file(self, filepath: str) -> bool:
        """Apply all enhanced repair techniques to a file."""
        print(f"\n🔧 Enhanced repair: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create backup
            backup_path = f"{filepath}.backup"
            if not os.path.exists(backup_path):
                shutil.copy2(filepath, backup_path)
            
            total_fixes = 0
            
            # Apply all repair techniques
            content, fixes1 = self.fix_function_call_corruption(content)
            total_fixes += fixes1
            self.stats['function_call_fixes'] += fixes1
            
            content, fixes2 = self.fix_complex_bracket_patterns(content)
            total_fixes += fixes2
            self.stats['complex_bracket_fixes'] += fixes2
            
            content, fixes3 = self.fix_multiline_structures(content)
            total_fixes += fixes3
            self.stats['multiline_fixes'] += fixes3
            
            content, fixes4 = self.fix_missing_colons_and_indentation(content)
            total_fixes += fixes4
            
            content, fixes5 = self.fix_docstring_corruption(content)
            total_fixes += fixes5
            self.stats['docstring_fixes'] += fixes5
            
            content, fixes6 = self.fix_import_block_corruption(content)
            total_fixes += fixes6
            
            # Validate syntax
            try:
                ast.parse(content)
                # Write fixed content
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                if total_fixes > 0:
                    print(f"  ✅ Enhanced repair: {total_fixes} fixes, syntax valid")
                    self.stats['files_fixed'] += 1
                else:
                    print(f"  ✅ Already valid syntax")
                return True
                
            except SyntaxError as e:
                print(f"  ❌ Still invalid after {total_fixes} fixes: {e.msg}")
                # Keep the fixes anyway, they might help
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                return False
                
        except Exception as e:
            print(f"  ❌ Error during enhanced repair: {e}")
            return False
        
        finally:
            self.stats['files_processed'] += 1
    
    def repair_priority_files(self, error_files: List[str], max_files: int = 100) -> None:
        """Repair priority files that are critical for testing."""
        
        # Prioritize files by importance
        priority_patterns = [
            'mission_critical',
            'websocket',
            'auth',
            'agent',
            'test_',
            'integration',
            'unit'
        ]
        
        prioritized_files = []
        
        # Add files by priority
        for pattern in priority_patterns:
            matching_files = [f for f in error_files if pattern in f.lower()]
            prioritized_files.extend(matching_files[:20])  # Top 20 per category
        
        # Add remaining files
        remaining = [f for f in error_files if f not in prioritized_files]
        prioritized_files.extend(remaining[:max_files - len(prioritized_files)])
        
        print(f"🚀 Enhanced repair starting on {len(prioritized_files)} priority files")
        
        success_count = 0
        for i, filepath in enumerate(prioritized_files):
            if self.validate_and_repair_file(filepath):
                success_count += 1
            
            if (i + 1) % 20 == 0:
                print(f"\n📈 Progress: {i+1}/{len(prioritized_files)} files")
                print(f"   Success rate: {success_count}/{i+1} ({success_count/(i+1)*100:.1f}%)")
        
        print(f"\n🎉 ENHANCED REPAIR COMPLETED!")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files fixed: {self.stats['files_fixed']}")
        print(f"Function call fixes: {self.stats['function_call_fixes']}")
        print(f"Complex bracket fixes: {self.stats['complex_bracket_fixes']}")
        print(f"Multiline fixes: {self.stats['multiline_fixes']}")
        print(f"Docstring fixes: {self.stats['docstring_fixes']}")
        print(f"Success rate: {self.stats['files_fixed']/self.stats['files_processed']*100:.1f}%")

def extract_error_files_from_report(report_file: str) -> List[str]:
    """Extract file paths from syntax error report."""
    error_files = []
    with open(report_file, 'r') as f:
        for line in f:
            if line.startswith('./') and ':' in line:
                filepath = line.split(':')[0]
                if os.path.exists(filepath):
                    error_files.append(filepath)
    return list(set(error_files))

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 enhanced_syntax_repair.py <syntax_errors_report.txt>")
        sys.exit(1)
    
    report_file = sys.argv[1]
    if not os.path.exists(report_file):
        print(f"Error: Report file {report_file} not found")
        sys.exit(1)
    
    error_files = extract_error_files_from_report(report_file)
    print(f"Found {len(error_files)} files with syntax errors")
    
    repair_tool = EnhancedSyntaxRepair()
    repair_tool.repair_priority_files(error_files, max_files=150)

if __name__ == "__main__":
    main()