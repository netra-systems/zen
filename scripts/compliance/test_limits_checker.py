#!/usr/bin/env python3
"""
Test file and function limits compliance checker.
Enforces SPEC/testing.xml rules: test files MUST follow same 450-line limit as production code,
test functions MUST follow same 25-line limit as production code.
"""

import ast
import glob
from pathlib import Path
from typing import Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

from scripts.compliance.core import ComplianceConfig, Violation, ViolationBuilder


class TestLimitsChecker:
    """Checks test files for size and function length compliance"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        # Override production limits with test-specific limits
        self.max_test_file_lines = 300  # From SPEC/testing.xml
        self.max_test_function_lines = 8  # From SPEC/testing.xml
    
    def check_test_limits(self) -> List[Violation]:
        """Check all test files for size and function violations"""
        violations = []
        test_files = self._find_test_files()
        
        for filepath in test_files:
            if not self.config.should_skip_file(filepath):
                violations.extend(self._check_test_file(filepath))
                violations.extend(self._check_test_functions(filepath))
        
        return self._sort_violations(violations)
    
    def generate_splitting_suggestions(self, violations: List[Violation]) -> Dict[str, List[str]]:
        """Generate automated splitting suggestions for violations"""
        suggestions = {}
        
        for violation in violations:
            if violation.violation_type == "test_file_size":
                suggestions[violation.file_path] = self._suggest_file_split(violation)
            elif violation.violation_type == "test_function_complexity":
                key = f"{violation.file_path}:{violation.function_name}"
                suggestions[key] = self._suggest_function_split(violation)
        
        return suggestions
    
    def _find_test_files(self) -> List[str]:
        """Find all test files in the project"""
        test_files = []
        patterns = [
            "app/tests/**/*.py",
            "tests/**/*.py", 
            "test_*.py",
            "**/test_*.py",
            "**/*_test.py",
            "tests/**/*_test.py"
        ]
        
        for pattern in patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                # Double-check it's actually a test file
                if self.config.is_test_file(filepath):
                    test_files.append(filepath)
        
        return list(set(test_files))  # Remove duplicates
    
    def _check_test_file(self, filepath: str) -> List[Violation]:
        """Check single test file for size violation"""
        try:
            line_count = self._count_file_lines(filepath)
            return self._create_file_violation_if_needed(filepath, line_count)
        except Exception as e:
            print(f"Error reading test file {filepath}: {e}")
            return []
    
    def _check_test_functions(self, filepath: str) -> List[Violation]:
        """Check all test functions in a single file"""
        try:
            tree = self._parse_file(filepath)
            rel_path = str(Path(filepath).relative_to(self.config.root_path))
            return self._extract_test_function_violations(tree, rel_path)
        except Exception as e:
            print(f"Error parsing test file {filepath}: {e}")
            return []
    
    def _count_file_lines(self, filepath: str) -> int:
        """Count lines in file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    
    def _parse_file(self, filepath: str) -> ast.AST:
        """Parse Python file into AST"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return ast.parse(f.read())
    
    def _create_file_violation_if_needed(self, filepath: str, lines: int) -> List[Violation]:
        """Create file size violation if needed"""
        if lines <= self.max_test_file_lines:
            return []
        
        rel_path = str(Path(filepath).relative_to(self.config.root_path))
        violation = Violation(
            file_path=rel_path,
            violation_type="test_file_size",
            severity="high",
            actual_value=lines,
            expected_value=self.max_test_file_lines,
            description=f"Test file exceeds {self.max_test_file_lines} line limit (SPEC/testing.xml)",
            fix_suggestion=f"Split into {(lines // self.max_test_file_lines) + 1} focused test modules"
        )
        return [violation]
    
    def _extract_test_function_violations(self, tree: ast.AST, rel_path: str) -> List[Violation]:
        """Extract test function violations from AST"""
        violations = []
        for node in ast.walk(tree):
            if self._is_test_function_node(node):
                violation = self._check_test_function_node(node, rel_path)
                if violation:
                    violations.append(violation)
        return violations
    
    def _is_test_function_node(self, node) -> bool:
        """Check if node is a test function definition"""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        # Test functions typically start with "test_" or are inside test classes
        return (node.name.startswith('test_') or 
                node.name.startswith('pytest_') or
                self._is_in_test_class(node))
    
    def _is_in_test_class(self, node) -> bool:
        """Check if function is inside a test class"""
        # This is a simplified check - in practice, AST traversal would need more context
        # For now, we'll focus on function names starting with test_
        return False
    
    def _check_test_function_node(self, node, rel_path: str) -> Optional[Violation]:
        """Check single test function node for violations"""
        lines = self._count_test_function_lines(node)
        if lines <= self.max_test_function_lines:
            return None
        
        return Violation(
            file_path=rel_path,
            violation_type="test_function_complexity",
            severity="high",
            line_number=node.lineno,
            function_name=node.name,
            actual_value=lines,
            expected_value=self.max_test_function_lines,
            description=f"Test function '{node.name}' has {lines} lines (max: {self.max_test_function_lines}, SPEC/testing.xml)",
            fix_suggestion=f"Split into {(lines // self.max_test_function_lines) + 1} focused test functions or use helper methods"
        )
    
    def _count_test_function_lines(self, node) -> int:
        """Count actual code lines in test function (excluding docstrings)"""
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
        return (len(node.body) > 0 and 
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant))
    
    def _calculate_line_count(self, node, start_idx: int) -> int:
        """Calculate line count from start index to end"""
        first_line = node.body[start_idx].lineno
        last_stmt = node.body[-1]
        last_line = getattr(last_stmt, 'end_lineno', last_stmt.lineno)
        return last_line - first_line + 1
    
    def _suggest_file_split(self, violation: Violation) -> List[str]:
        """Suggest how to split a large test file"""
        suggestions = [
            f"Current size: {violation.actual_value} lines (limit: {violation.expected_value})",
            "Suggested splitting strategies:",
            "1. Split by test categories (unit/integration/e2e)",
            "2. Split by functionality being tested",
            "3. Split by test class if using class-based tests",
            "4. Move helper functions to separate test utilities module",
            "Example split:",
            f"  - {violation.file_path.replace('.py', '_unit.py')} (unit tests)",
            f"  - {violation.file_path.replace('.py', '_integration.py')} (integration tests)",
            f"  - {violation.file_path.replace('.py', '_helpers.py')} (shared utilities)"
        ]
        return suggestions
    
    def _suggest_function_split(self, violation: Violation) -> List[str]:
        """Suggest how to split a large test function"""
        suggestions = [
            f"Function '{violation.function_name}' has {violation.actual_value} lines (limit: {violation.expected_value})",
            "Suggested refactoring strategies:",
            "1. Extract setup logic into fixture or helper method",
            "2. Split into multiple focused test cases",
            "3. Extract assertion logic into helper methods",
            "4. Use parameterized tests for multiple scenarios",
            "Example refactoring:",
            f"  - {violation.function_name}_setup() - Test setup logic",
            f"  - {violation.function_name}_scenario_1() - First test case", 
            f"  - {violation.function_name}_scenario_2() - Second test case",
            f"  - {violation.function_name}_assertions() - Common assertions"
        ]
        return suggestions
    
    def _sort_violations(self, violations: List[Violation]) -> List[Violation]:
        """Sort violations by severity and actual value"""
        return sorted(violations, key=lambda x: (
            x.severity == "high",  # High severity first
            x.actual_value or 0    # Then by size descending
        ), reverse=True)