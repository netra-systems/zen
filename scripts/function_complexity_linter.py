#!/usr/bin/env python3
"""
Function Complexity Linter Core
Core linting logic for enforcing the 8-line maximum function rule.

This module contains the main FunctionComplexityLinter class and core analysis logic.
"""

import ast
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import asdict

from function_complexity_types import FunctionComplexityViolation

class FunctionComplexityLinter:
    """Linter for enforcing function complexity rules"""
    
    def __init__(self, max_lines: int = 8, root_path: str = "."):
        self.max_lines = max_lines
        self.root_path = Path(root_path)
        self.violations: List[FunctionComplexityViolation] = []
    
    def _count_function_lines(self, node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        start_idx = self._get_code_start_index(node)
        if start_idx >= len(node.body):
            return 0
        return self._calculate_line_count(node, start_idx)
    
    def _get_code_start_index(self, node: ast.FunctionDef) -> int:
        """Get the index where actual code starts (skip docstring)"""
        if not node.body:
            return 0
        if self._has_docstring(node.body[0]):
            return 1
        return 0
    
    def _has_docstring(self, stmt: ast.stmt) -> bool:
        """Check if statement is a docstring"""
        return (isinstance(stmt, ast.Expr) and 
                isinstance(stmt.value, ast.Constant) and 
                isinstance(stmt.value.value, str))
    
    def _calculate_line_count(self, node: ast.FunctionDef, start_idx: int) -> int:
        """Calculate line count from start index to end"""
        first_line = node.body[start_idx].lineno
        last_stmt = node.body[-1]
        last_line = getattr(last_stmt, 'end_lineno', last_stmt.lineno)
        return last_line - first_line + 1
    
    def _should_skip_function(self, function_name: str, file_path: str) -> bool:
        """Check if function should be skipped from linting"""
        return (self._is_special_function(function_name) or 
                self._is_test_file(file_path))
    
    def _is_special_function(self, function_name: str) -> bool:
        """Check if function is a special method or test function"""
        skip_patterns = [
            "__init__", "__str__", "__repr__", "__eq__",
            "test_", "setUp", "tearDown"
        ]
        return any(pattern in function_name for pattern in skip_patterns)
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file should be skipped (test/example files)"""
        skip_files = [
            "test_", "example_", "demo_", "sample_",
            "__init__.py", "conftest.py"
        ]
        return any(pattern in file_path for pattern in skip_files)
    
    def lint_file(self, file_path: Path) -> List[FunctionComplexityViolation]:
        """Lint a single Python file for function complexity"""
        try:
            tree = self._parse_file_content(file_path)
            return self._analyze_ast_tree(tree, file_path)
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return []
    
    def _parse_file_content(self, file_path: Path) -> ast.AST:
        """Parse Python file content into AST"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return ast.parse(content)
    
    def _analyze_ast_tree(self, tree: ast.AST, file_path: Path) -> List[FunctionComplexityViolation]:
        """Analyze AST tree for function complexity violations"""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                violation = self._check_function_node(node, file_path)
                if violation:
                    violations.append(violation)
        return violations
    
    def _check_function_node(self, node: ast.FunctionDef, file_path: Path) -> Optional[FunctionComplexityViolation]:
        """Check a single function node for violations"""
        if self._should_skip_function(node.name, str(file_path)):
            return None
        lines = self._count_function_lines(node)
        if lines <= self.max_lines:
            return None
        return self._create_violation(node, lines, file_path)
    
    def _create_violation(self, node: ast.FunctionDef, lines: int, file_path: Path) -> FunctionComplexityViolation:
        """Create a function complexity violation object"""
        rel_path = str(file_path.relative_to(self.root_path))
        return FunctionComplexityViolation(
            file_path=rel_path, function_name=node.name, line_number=node.lineno,
            actual_lines=lines, max_lines=self.max_lines,
            message=f"Function '{node.name}' has {lines} lines (max: {self.max_lines})"
        )
    
    def lint_directory(self, patterns: List[str] = None) -> None:
        """Lint all Python files in directory or single file"""
        root_path = Path(self.root_path)
        if root_path.is_file():
            self._lint_single_file(root_path)
            return
        self._lint_directory_files(patterns)
    
    def _lint_single_file(self, file_path: Path) -> None:
        """Lint a single Python file"""
        if not self._should_skip_file(file_path):
            file_violations = self.lint_file(file_path)
            self.violations.extend(file_violations)
    
    def _lint_directory_files(self, patterns: List[str] = None) -> None:
        """Lint all Python files in directory using patterns"""
        if patterns is None:
            patterns = ["**/*.py"]
        for pattern in patterns:
            for file_path in self.root_path.rglob(pattern):
                if self._should_skip_file(file_path):
                    continue
                file_violations = self.lint_file(file_path)
                self.violations.extend(file_violations)
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        return (self._has_skip_directory(file_path) or 
                self._is_third_party_file(file_path))
    
    def _has_skip_directory(self, file_path: Path) -> bool:
        """Check if file path contains directories to skip"""
        skip_dirs = {
            "__pycache__", ".git", "node_modules", 
            ".pytest_cache", "migrations", "venv", 
            ".venv", "env", ".env"
        }
        return any(part in skip_dirs for part in file_path.parts)
    
    def _is_third_party_file(self, file_path: Path) -> bool:
        """Check if file is a third-party or generated file"""
        return "site-packages" in str(file_path)
    
    def generate_report(self) -> Dict:
        """Generate linting report"""
        return {
            "total_violations": len(self.violations),
            "max_lines_allowed": self.max_lines,
            "violations": [asdict(v) for v in self.violations],
            "files_with_violations": self._count_files_with_violations(),
            "worst_violations": self._get_worst_violations_dict()
        }
    
    def _count_files_with_violations(self) -> int:
        """Count unique files with violations"""
        return len(set(v.file_path for v in self.violations))
    
    def _get_worst_violations_dict(self) -> List[Dict]:
        """Get worst violations as dictionary list"""
        violation_dicts = [asdict(v) for v in self.violations]
        sorted_violations = sorted(violation_dicts, 
                                 key=lambda x: x["actual_lines"], 
                                 reverse=True)
        return sorted_violations[:10]
    
    def print_report(self) -> None:
        """Print human-readable report"""
        self._print_report_header()
        if self.violations:
            self._print_violations_summary()
        else:
            print("\nNo function complexity violations found!")
    
    def _print_report_header(self) -> None:
        """Print report header with basic statistics"""
        print(f"\nFunction Complexity Linter Report")
        print("=" * 50)
        print(f"Maximum lines allowed: {self.max_lines}")
        print(f"Total violations: {len(self.violations)}")
        print(f"Files with violations: {len(set(v.file_path for v in self.violations))}")
    
    def _print_violations_summary(self) -> None:
        """Print summary of worst violations"""
        print(f"\nWorst violations:")
        sorted_violations = self._get_sorted_violations()
        self._print_top_violations(sorted_violations)
        self._print_remaining_count(sorted_violations)
    
    def _get_sorted_violations(self) -> List[FunctionComplexityViolation]:
        """Get violations sorted by line count (descending)"""
        return sorted(self.violations, key=lambda x: x.actual_lines, reverse=True)
    
    def _print_top_violations(self, sorted_violations: List[FunctionComplexityViolation]) -> None:
        """Print top 10 violations"""
        for i, violation in enumerate(sorted_violations[:10], 1):
            print(f"  {i}. {violation.function_name}() - {violation.actual_lines} lines")
            print(f"     {violation.file_path}:{violation.line_number}")
    
    def _print_remaining_count(self, sorted_violations: List[FunctionComplexityViolation]) -> None:
        """Print count of remaining violations if more than 10"""
        if len(sorted_violations) > 10:
            remaining = len(sorted_violations) - 10
            print(f"     ... and {remaining} more violations")


    def handle_output_generation(self, use_json: bool) -> None:
        """Generate and display linting output"""
        if use_json:
            print(json.dumps(self.generate_report(), indent=2))
        else:
            self.print_report()

if __name__ == "__main__":
    from function_complexity_cli import main
    main()