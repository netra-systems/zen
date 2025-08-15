#!/usr/bin/env python3
"""
Function boundary checking module for boundary enforcement system.
Handles function size validation and refactor suggestions.
"""

import ast
import glob
from pathlib import Path
from typing import List, Dict, Optional

from boundary_enforcer_core_types import (
    BoundaryViolation, SystemBoundaries, should_skip_file
)

class FunctionBoundaryChecker:
    """Handles function size boundary validation"""
    
    def __init__(self, root_path: Path, boundaries: SystemBoundaries):
        self.root_path = root_path
        self.boundaries = boundaries
        self.violations: List[BoundaryViolation] = []

    def check_function_boundaries(self) -> List[BoundaryViolation]:
        """Check function line boundaries with refactor suggestions"""
        self.violations.clear()
        patterns = ['app/**/*.py', 'scripts/**/*.py']
        for pattern in patterns:
            self._check_pattern_functions(pattern)
        return self.violations.copy()

    def _check_pattern_functions(self, pattern: str) -> None:
        """Check function boundaries for a specific glob pattern"""
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if should_skip_file(filepath):
                continue
            self._validate_file_functions(filepath)

    def _validate_file_functions(self, filepath: str) -> None:
        """Validate function boundaries for a single file"""
        tree = self._parse_file_ast(filepath)
        if tree is None:
            return
        rel_path = str(Path(filepath).relative_to(self.root_path))
        self._check_function_nodes(tree, rel_path)

    def _parse_file_ast(self, filepath: str) -> Optional[ast.AST]:
        """Parse file to AST, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return ast.parse(f.read())
        except Exception:
            return None

    def _check_function_nodes(self, tree: ast.AST, rel_path: str) -> None:
        """Check all function nodes in AST for boundary violations"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._validate_function_node(node, rel_path)

    def _validate_function_node(self, node: ast.FunctionDef, rel_path: str) -> None:
        """Validate boundary for a single function node"""
        lines = self._count_function_lines(node)
        if lines <= self.boundaries.max_function_lines:
            return
        self._create_function_violation(node, lines, rel_path)

    def _create_function_violation(self, node: ast.FunctionDef, lines: int, rel_path: str) -> None:
        """Create a function boundary violation entry"""
        suggestion = self._generate_refactor_suggestion(node, lines)
        violation = self._build_function_violation(node, lines, rel_path, suggestion)
        self.violations.append(violation)

    def _build_function_violation(self, node: ast.FunctionDef, lines: int, 
                                 rel_path: str, suggestion: str) -> BoundaryViolation:
        """Build function boundary violation object"""
        return BoundaryViolation(
            file_path=rel_path, violation_type="function_line_boundary", severity="critical",
            boundary_name="FUNCTION_SIZE_LIMIT", line_number=node.lineno, function_name=node.name,
            actual_value=lines, expected_value=self.boundaries.max_function_lines,
            description=f"Function exceeds {self.boundaries.max_function_lines} line HARD LIMIT",
            fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_function_lines) + 1} functions",
            auto_split_suggestion=suggestion, impact_score=min(10, lines // 2)
        )

class FunctionAnalyzer:
    """Analyzes function structure for refactor suggestions"""
    
    @staticmethod
    def count_function_lines(node: ast.FunctionDef) -> int:
        """Count actual code lines in function (excluding docstrings)"""
        if not node.body:
            return 0
        start_idx = FunctionAnalyzer._get_start_index(node)
        if start_idx >= len(node.body):
            return 0
        return FunctionAnalyzer._calculate_line_count(node, start_idx)

    @staticmethod
    def _get_start_index(node: ast.FunctionDef) -> int:
        """Get the starting index after docstring (if present)"""
        if (len(node.body) > 0 and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Constant, ast.Str))):
            return 1
        return 0

    @staticmethod
    def _calculate_line_count(node: ast.FunctionDef, start_idx: int) -> int:
        """Calculate line count from start index to last statement"""
        first_line = node.body[start_idx].lineno
        last_statement = node.body[-1]
        last_line = getattr(last_statement, 'end_lineno', last_statement.lineno)
        return last_line - first_line + 1

    @staticmethod
    def generate_refactor_suggestion(node: ast.FunctionDef, lines: int) -> str:
        """Generate intelligent function refactoring suggestions"""
        if not hasattr(node, 'body') or len(node.body) == 0:
            return "Requires manual refactoring"
        analysis = FunctionAnalyzer._analyze_structure(node)
        suggestions = FunctionAnalyzer._build_suggestions(analysis, lines)
        return " | ".join(suggestions) if suggestions else "Requires manual refactoring"

    @staticmethod
    def _analyze_structure(node: ast.FunctionDef) -> Dict[str, bool]:
        """Analyze function structure for refactoring suggestions"""
        return {
            "has_conditions": any(isinstance(n, (ast.If, ast.While, ast.For)) for n in ast.walk(node)),
            "has_try_except": any(isinstance(n, ast.Try) for n in ast.walk(node))
        }

    @staticmethod
    def _build_suggestions(analysis: Dict[str, bool], lines: int) -> List[str]:
        """Build refactoring suggestions based on analysis"""
        suggestions = []
        if analysis["has_conditions"]:
            suggestions.append("Extract conditional logic into helper functions")
        if analysis["has_try_except"]:
            suggestions.append("Extract error handling into separate function")
        suggestions.append(FunctionAnalyzer._get_size_suggestion(lines))
        return suggestions

    @staticmethod
    def _get_size_suggestion(lines: int) -> str:
        """Get refactoring suggestion based on function size"""
        if lines > 15:
            return "Break into validation + processing + result functions"
        return "Split into 2-3 smaller focused functions"

# Integration methods for FunctionBoundaryChecker
def _count_function_lines(self, node: ast.FunctionDef) -> int:
    """Count function lines using analyzer"""
    return FunctionAnalyzer.count_function_lines(node)

def _generate_refactor_suggestion(self, node: ast.FunctionDef, lines: int) -> str:
    """Generate refactor suggestion using analyzer"""
    return FunctionAnalyzer.generate_refactor_suggestion(node, lines)

# Bind methods to FunctionBoundaryChecker
FunctionBoundaryChecker._count_function_lines = _count_function_lines
FunctionBoundaryChecker._generate_refactor_suggestion = _generate_refactor_suggestion