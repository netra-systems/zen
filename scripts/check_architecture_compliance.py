#!/usr/bin/env python3
"""
Architecture Compliance Checker
Enforces CLAUDE.md architectural rules:
- 300-line file limit
- 8-line function limit  
- No duplicate types
- No test stubs in production
"""

import ast
import glob
import os
import sys
import re
from collections import defaultdict
from typing import List, Tuple, Dict
from pathlib import Path

class ArchitectureEnforcer:
    """Enforces architectural rules from CLAUDE.md"""
    
    MAX_FILE_LINES = 300
    MAX_FUNCTION_LINES = 8
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.violations = []
        
    def check_file_size(self) -> List[Tuple[str, int]]:
        """Check for files exceeding 300 lines"""
        violations = []
        patterns = ['app/**/*.py', 'frontend/**/*.tsx', 'frontend/**/*.ts']
        
        for pattern in patterns:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if self._should_skip(filepath):
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        if lines > self.MAX_FILE_LINES:
                            violations.append((filepath, lines))
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
                    
        return sorted(violations, key=lambda x: x[1], reverse=True)
    
    def check_function_complexity(self) -> List[Tuple[str, str, int]]:
        """Check for functions exceeding 8 lines"""
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                    
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        lines = self._count_function_lines(node)
                        if lines > self.MAX_FUNCTION_LINES:
                            violations.append((filepath, node.name, lines))
            except Exception as e:
                print(f"Error parsing {filepath}: {e}")
                
        return sorted(violations, key=lambda x: x[2], reverse=True)
    
    def check_duplicate_types(self) -> Dict[str, List[str]]:
        """Find duplicate type definitions"""
        type_definitions = defaultdict(list)
        
        # Check Python files
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if self._should_skip(filepath):
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for match in re.finditer(r'^class\s+(\w+)', content, re.MULTILINE):
                        type_name = match.group(1)
                        type_definitions[type_name].append(filepath)
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
        
        # Check TypeScript files
        for pattern in ['frontend/**/*.ts', 'frontend/**/*.tsx']:
            for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
                if 'node_modules' in filepath:
                    continue
                    
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for match in re.finditer(r'(?:interface|type)\s+(\w+)', content):
                            type_name = match.group(1)
                            type_definitions[type_name].append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
        
        # Return only duplicates
        return {k: v for k, v in type_definitions.items() if len(v) > 1}
    
    def check_test_stubs(self) -> List[Tuple[str, str]]:
        """Check for test stubs in production code"""
        suspicious_patterns = [
            (r'# Mock implementation', 'Mock implementation comment'),
            (r'# Test stub', 'Test stub comment'),
            (r'""".*test implementation.*"""', 'Test implementation docstring'),
            (r'""".*for testing.*"""', 'For testing docstring'),
            (r'return \[{"id": "1"', 'Hardcoded test data'),
            (r'return {"test": "data"}', 'Test data return'),
            (r'return {"status": "ok"}', 'Static status return'),
            (r'def \w+\(\*args, \*\*kwargs\).*return {', 'Args/kwargs with static return'),
        ]
        
        violations = []
        
        for filepath in glob.glob(str(self.root_path / 'app/**/*.py'), recursive=True):
            if '__pycache__' in filepath or 'app/tests' in filepath:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for pattern, description in suspicious_patterns:
                        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                            violations.append((filepath, description))
                            break
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                
        return violations
    
    def _should_skip(self, filepath: str) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            '__pycache__',
            'node_modules',
            '.git',
            'migrations',
            'test_reports',
            'docs',
            '.pytest_cache'
        ]
        return any(pattern in filepath for pattern in skip_patterns)
    
    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        
        # Skip docstring if present
        start_idx = 0
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            start_idx = 1
        
        if start_idx >= len(node.body):
            return 0
            
        # Count lines from first real statement to last
        first_line = node.body[start_idx].lineno
        last_line = node.body[-1].end_lineno if hasattr(node.body[-1], 'end_lineno') else node.body[-1].lineno
        return last_line - first_line + 1
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        print("\n" + "="*80)
        print("ARCHITECTURE COMPLIANCE REPORT")
        print("="*80)
        
        # File size violations
        print("\n[FILE SIZE VIOLATIONS] (>300 lines)")
        print("-" * 40)
        file_violations = self.check_file_size()
        if file_violations:
            for filepath, lines in file_violations[:10]:
                print(f"  {lines:4d} lines: {filepath}")
            if len(file_violations) > 10:
                print(f"  ... and {len(file_violations)-10} more files")
            print(f"\n  Total violations: {len(file_violations)}")
        else:
            print("  [PASS] No violations found")
        
        # Function complexity violations
        print("\n[FUNCTION COMPLEXITY VIOLATIONS] (>8 lines)")
        print("-" * 40)
        func_violations = self.check_function_complexity()
        if func_violations:
            for filepath, func_name, lines in func_violations[:10]:
                print(f"  {lines:3d} lines: {func_name}() in {filepath}")
            if len(func_violations) > 10:
                print(f"  ... and {len(func_violations)-10} more functions")
            print(f"\n  Total violations: {len(func_violations)}")
        else:
            print("  [PASS] No violations found")
        
        # Duplicate types
        print("\n[DUPLICATE TYPE DEFINITIONS]")
        print("-" * 40)
        duplicates = self.check_duplicate_types()
        if duplicates:
            for type_name, files in sorted(duplicates.items())[:10]:
                print(f"  {type_name} ({len(files)} definitions):")
                for f in files[:3]:
                    print(f"    - {f}")
                if len(files) > 3:
                    print(f"    ... and {len(files)-3} more")
            if len(duplicates) > 10:
                print(f"\n  ... and {len(duplicates)-10} more duplicate types")
            print(f"\n  Total duplicate types: {len(duplicates)}")
        else:
            print("  [PASS] No duplicates found")
        
        # Test stubs
        print("\n[TEST STUBS IN PRODUCTION]")
        print("-" * 40)
        test_stubs = self.check_test_stubs()
        if test_stubs:
            for filepath, issue in test_stubs[:10]:
                print(f"  {filepath}: {issue}")
            if len(test_stubs) > 10:
                print(f"  ... and {len(test_stubs)-10} more files")
            print(f"\n  Total suspicious files: {len(test_stubs)}")
        else:
            print("  [PASS] No test stubs found")
        
        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        total_violations = (len(file_violations) + len(func_violations) + 
                          len(duplicates) + len(test_stubs))
        
        if total_violations == 0:
            print("[PASS] FULL COMPLIANCE - All architectural rules satisfied!")
            return "PASS"
        else:
            print(f"[FAIL] VIOLATIONS FOUND: {total_violations} total issues")
            print("\nRequired Actions:")
            if file_violations:
                print(f"  - Split {len(file_violations)} oversized files")
            if func_violations:
                print(f"  - Refactor {len(func_violations)} complex functions")
            if duplicates:
                print(f"  - Deduplicate {len(duplicates)} type definitions")
            if test_stubs:
                print(f"  - Remove {len(test_stubs)} test stubs from production")
            
            print("\nRefer to ALIGNMENT_ACTION_PLAN.md for remediation steps")
            return "FAIL"

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check architecture compliance')
    parser.add_argument('--path', default='.', help='Root path to check')
    parser.add_argument('--fail-on-violation', action='store_true', 
                       help='Exit with non-zero code on violations')
    
    args = parser.parse_args()
    
    enforcer = ArchitectureEnforcer(args.path)
    result = enforcer.generate_report()
    
    if args.fail_on_violation and result == "FAIL":
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main()