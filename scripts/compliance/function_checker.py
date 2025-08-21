#!/usr/bin/env python3
"""
Function complexity compliance checker.
Enforces CLAUDE.md function size guidelines (approx <25 lines).
Per CLAUDE.md 2.2: Exceeding guidelines signals need to reassess design for SRP adherence.
"""

import ast
import glob
from pathlib import Path
from typing import List, Optional

from .core import ComplianceConfig, Violation, ViolationBuilder


class FunctionChecker:
    """Checks functions for complexity compliance"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
    
    def check_function_complexity(self) -> List[Violation]:
        """Check all functions for complexity violations"""
        violations = []
        patterns = self.config.get_python_patterns()
        for pattern in patterns:
            violations.extend(self._check_pattern(pattern))
        return self._sort_violations(violations)
    
    def _check_pattern(self, pattern: str) -> List[Violation]:
        """Check functions in files matching pattern"""
        violations = []
        filepaths = self._get_matching_files(pattern)
        for filepath in filepaths:
            if not self.config.should_skip_file(filepath):
                violations.extend(self._check_functions_in_file(filepath))
        return violations
    
    def _get_matching_files(self, pattern: str) -> List[str]:
        """Get files matching pattern"""
        return glob.glob(str(self.config.root_path / pattern), recursive=True)
    
    def _check_functions_in_file(self, filepath: str) -> List[Violation]:
        """Check all functions in a single file"""
        try:
            tree = self._parse_file(filepath)
            rel_path = str(Path(filepath).relative_to(self.config.root_path))
            return self._extract_function_violations(tree, rel_path)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return []
    
    def _parse_file(self, filepath: str) -> ast.AST:
        """Parse Python file into AST"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return ast.parse(f.read())
    
    def _extract_function_violations(self, tree: ast.AST, rel_path: str) -> List[Violation]:
        """Extract function violations from AST"""
        violations = []
        is_example_file = self._is_example_file(rel_path)
        for node in ast.walk(tree):
            if self._is_function_node(node):
                violation = self._check_function_node(node, rel_path, is_example_file)
                if violation:
                    violations.append(violation)
        return violations
    
    def _is_function_node(self, node) -> bool:
        """Check if node is a function definition"""
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    
    def _is_example_file(self, rel_path: str) -> bool:
        """Check if file is an example/demo file"""
        example_patterns = ['example', 'demo', 'sample', 'test_', 'mock', 
                           'example_usage', 'corpus_metrics', 'audit/example']
        return any(x in rel_path.lower() for x in example_patterns)
    
    def _check_function_node(self, node, rel_path: str, is_example_file: bool) -> Optional[Violation]:
        """Check single function node for violations"""
        lines = self._count_function_lines(node)
        if lines <= self.config.max_function_lines:
            return None
        severity, prefix = self._get_violation_params(is_example_file)
        return ViolationBuilder.function_violation(
            node, rel_path, lines, self.config.max_function_lines, severity, prefix
        )
    
    def _get_violation_params(self, is_example_file: bool) -> tuple:
        """Get severity and prefix for violation"""
        if is_example_file:
            return "low", "[WARNING]"
        return "medium", "[VIOLATION]"
    
    def _count_function_lines(self, node) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        start_idx = self._get_code_start_index(node)
        if start_idx >= len(node.body):
            return 0
        return self._calculate_line_count(node, start_idx)
    
    def _get_code_start_index(self, node) -> int:
        """Get index where actual code starts (after docstring)"""
        if self._has_docstring(node):
            return 1
        return 0
    
    def _has_docstring(self, node) -> bool:
        """Check if function has docstring"""
        return (len(node.body) > 0 and isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant))
    
    def _calculate_line_count(self, node, start_idx: int) -> int:
        """Calculate line count from start index to end"""
        first_line = node.body[start_idx].lineno
        last_stmt = node.body[-1]
        last_line = getattr(last_stmt, 'end_lineno', last_stmt.lineno)
        return last_line - first_line + 1
    
    def _sort_violations(self, violations: List[Violation]) -> List[Violation]:
        """Sort violations by actual value descending"""
        return sorted(violations, key=lambda x: x.actual_value or 0, reverse=True)