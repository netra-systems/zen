#!/usr/bin/env python3
"""
CRITICAL: Syntax Validation Script
Validates all Python files for syntax errors using AST parser
"""

import ast
import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import traceback


class SyntaxValidationResult:
    def __init__(self):
        self.valid_files: List[str] = []
        self.invalid_files: Dict[str, str] = {}
        self.warnings: Dict[str, List[str]] = {}
        self.total_files = 0

    def add_valid_file(self, file_path: str):
        self.valid_files.append(file_path)
        self.total_files += 1

    def add_invalid_file(self, file_path: str, error: str):
        self.invalid_files[file_path] = error
        self.total_files += 1

    def add_warning(self, file_path: str, warning: str):
        if file_path not in self.warnings:
            self.warnings[file_path] = []
        self.warnings[file_path].append(warning)

    def is_valid(self) -> bool:
        return len(self.invalid_files) == 0

    def print_report(self):
        print("=" * 80)
        print("SYNTAX VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\nTOTAL FILES CHECKED: {self.total_files}")
        print(f"VALID FILES: {len(self.valid_files)}")
        print(f"INVALID FILES: {len(self.invalid_files)}")
        print(f"FILES WITH WARNINGS: {len(self.warnings)}")
        
        if self.invalid_files:
            print("\n" + "="*50)
            print("SYNTAX ERRORS FOUND:")
            print("="*50)
            for file_path, error in self.invalid_files.items():
                print(f"\nFILE: {file_path}")
                print(f"ERROR: {error}")
        
        if self.warnings:
            print("\n" + "="*50)
            print("WARNINGS:")
            print("="*50)
            for file_path, warnings in self.warnings.items():
                print(f"\nFILE: {file_path}")
                for warning in warnings:
                    print(f"  WARNING: {warning}")
        
        if self.invalid_files:
            print(f"\n{'='*80}")
            print("CRITICAL: SYNTAX ERRORS MUST BE FIXED BEFORE DEPLOYMENT")
            print("="*80)
        else:
            print(f"\n{'='*80}")
            print("SUCCESS: ALL FILES HAVE VALID SYNTAX")
            print("="*80)


def check_file_syntax(file_path: Path) -> Tuple[bool, Optional[str], List[str]]:
    """
    Check syntax of a single Python file using AST parser.
    Returns: (is_valid, error_message, warnings)
    """
    warnings = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common issues before AST parsing
        lines = content.split('\n')
        
        # Check for shebang line placement
        if len(lines) > 1:
            if lines[0].strip() and not lines[0].startswith('#'):
                if any(line.strip().startswith('#!/') for line in lines[1:3]):
                    warnings.append("Shebang line should be first line in file")
        
        # Check for continuation character issues
        for i, line in enumerate(lines, 1):
            if line.rstrip().endswith('\\'):
                if i < len(lines):
                    next_line = lines[i-1] if i-1 < len(lines) else ""
                    if not next_line.strip():
                        warnings.append(f"Line {i}: Backslash continuation followed by empty line")
        
        # Check for string formatting issues
        import re
        for i, line in enumerate(lines, 1):
            # Check for incomplete f-strings
            if 'f"' in line and line.count('"') % 2 != 0:
                warnings.append(f"Line {i}: Potential incomplete f-string")
            if "f'" in line and line.count("'") % 2 != 0:
                warnings.append(f"Line {i}: Potential incomplete f-string")
        
        # Parse with AST
        try:
            ast.parse(content, filename=str(file_path))
            return True, None, warnings
        except SyntaxError as e:
            error_msg = f"Syntax Error at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\n  Code: {e.text.strip()}"
            return False, error_msg, warnings
        except Exception as e:
            return False, f"Parse Error: {str(e)}", warnings
            
    except UnicodeDecodeError as e:
        return False, f"Unicode Decode Error: {str(e)}", warnings
    except IOError as e:
        return False, f"File Read Error: {str(e)}", warnings
    except Exception as e:
        return False, f"Unexpected Error: {str(e)}\n{traceback.format_exc()}", warnings


def validate_directory(directory: Path, pattern: str = "*.py") -> SyntaxValidationResult:
    """
    Validate all Python files in a directory.
    """
    result = SyntaxValidationResult()
    
    python_files = list(directory.rglob(pattern))
    
    if not python_files:
        print(f"No Python files found in {directory}")
        return result
    
    print(f"Validating {len(python_files)} Python files in {directory}")
    
    for file_path in python_files:
        print(f"Checking: {file_path.relative_to(directory)}")
        
        is_valid, error, warnings = check_file_syntax(file_path)
        
        if is_valid:
            result.add_valid_file(str(file_path))
            if warnings:
                for warning in warnings:
                    result.add_warning(str(file_path), warning)
        else:
            result.add_invalid_file(str(file_path), error)
            if warnings:
                for warning in warnings:
                    result.add_warning(str(file_path), warning)
    
    return result


def main():
    """Main validation function"""
    if len(sys.argv) > 1:
        directory = Path(sys.argv[1])
    else:
        # Default to tests/mission_critical
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        directory = project_root / "tests" / "mission_critical"
    
    if not directory.exists():
        print(f"ERROR: Directory {directory} does not exist")
        sys.exit(1)
    
    print(f"CRITICAL: Validating Python syntax in {directory}")
    print("="*80)
    
    result = validate_directory(directory)
    result.print_report()
    
    # Return exit code based on validation results
    if result.is_valid():
        print("\nSUCCESS: All files have valid syntax")
        sys.exit(0)
    else:
        print(f"\nFAILURE: {len(result.invalid_files)} files have syntax errors")
        sys.exit(1)


if __name__ == "__main__":
    main()