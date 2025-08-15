#!/usr/bin/env python3
"""
File boundary checking module for boundary enforcement system.
Handles file size validation and split suggestions.
"""

import ast
import glob
from pathlib import Path
from typing import List, Optional, Tuple

from boundary_enforcer_core_types import (
    BoundaryViolation, SystemBoundaries, should_skip_file, get_file_patterns
)

class FileBoundaryChecker:
    """Handles file size boundary validation"""
    
    def __init__(self, root_path: Path, boundaries: SystemBoundaries):
        self.root_path = root_path
        self.boundaries = boundaries
        self.violations: List[BoundaryViolation] = []

    def check_file_boundaries(self) -> List[BoundaryViolation]:
        """Check file line boundaries with split suggestions"""
        self.violations.clear()
        patterns = get_file_patterns()
        for pattern in patterns:
            self._check_pattern_boundaries(pattern)
        return self.violations.copy()

    def _check_pattern_boundaries(self, pattern: str) -> None:
        """Check file boundaries for a specific glob pattern"""
        for filepath in glob.glob(str(self.root_path / pattern), recursive=True):
            if should_skip_file(filepath):
                continue
            self._validate_file_boundary(filepath)

    def _validate_file_boundary(self, filepath: str) -> None:
        """Validate boundary for a single file"""
        lines = self._get_file_line_count(filepath)
        if lines is None or lines <= self.boundaries.max_file_lines:
            return
        self._create_file_violation(filepath, lines)

    def _get_file_line_count(self, filepath: str) -> Optional[int]:
        """Get line count for file, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return None

    def _create_file_violation(self, filepath: str, lines: int) -> None:
        """Create a file boundary violation entry"""
        rel_path = str(Path(filepath).relative_to(self.root_path))
        split_suggestion = self._generate_split_suggestion(filepath, lines)
        violation = self._build_violation_object(rel_path, lines, split_suggestion)
        self.violations.append(violation)

    def _build_violation_object(self, rel_path: str, lines: int, suggestion: str) -> BoundaryViolation:
        """Build file boundary violation object"""
        return BoundaryViolation(
            file_path=rel_path, violation_type="file_line_boundary", severity="critical",
            boundary_name="FILE_SIZE_LIMIT", actual_value=lines, 
            expected_value=self.boundaries.max_file_lines,
            description=f"File exceeds {self.boundaries.max_file_lines} line HARD LIMIT",
            fix_suggestion=f"MANDATORY: Split into {(lines // self.boundaries.max_file_lines) + 1} modules",
            auto_split_suggestion=suggestion, impact_score=min(10, lines // 100)
        )

    def _generate_split_suggestion(self, filepath: str, lines: int) -> str:
        """Generate intelligent file split suggestions"""
        tree = self._parse_file_ast(filepath)
        if tree is None:
            return "Unable to analyze - manual split required"
        classes, functions = self._extract_ast_nodes(tree)
        suggestions = self._build_suggestions(classes, functions)
        return " | ".join(suggestions) if suggestions else "Consider splitting by logical boundaries"

class ASTAnalyzer:
    """Handles AST analysis for split suggestions"""
    
    @staticmethod
    def parse_file_ast(filepath: str) -> Optional[ast.AST]:
        """Parse file to AST, return None on error"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return ast.parse(f.read())
        except Exception:
            return None

    @staticmethod
    def extract_ast_nodes(tree: ast.AST) -> Tuple[List[str], List[str]]:
        """Extract classes and functions from AST"""
        classes, functions = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(f"class {node.name} (line {node.lineno})")
            elif isinstance(node, ast.FunctionDef):
                functions.append(f"function {node.name} (line {node.lineno})")
        return classes, functions

    @staticmethod
    def build_suggestions(classes: List[str], functions: List[str]) -> List[str]:
        """Build split suggestions from extracted nodes"""
        suggestions = []
        if classes:
            suggestions.append(f"Split by classes: {', '.join(classes[:3])}")
        if functions:
            suggestions.append(f"Split by functions: {', '.join(functions[:3])}")
        return suggestions

# Integration methods for FileBoundaryChecker
def _parse_file_ast(self, filepath: str) -> Optional[ast.AST]:
    """Parse file to AST using analyzer"""
    return ASTAnalyzer.parse_file_ast(filepath)

def _extract_ast_nodes(self, tree: ast.AST) -> Tuple[List[str], List[str]]:
    """Extract AST nodes using analyzer"""
    return ASTAnalyzer.extract_ast_nodes(tree)

def _build_suggestions(self, classes: List[str], functions: List[str]) -> List[str]:
    """Build suggestions using analyzer"""
    return ASTAnalyzer.build_suggestions(classes, functions)

# Bind methods to FileBoundaryChecker
FileBoundaryChecker._parse_file_ast = _parse_file_ast
FileBoundaryChecker._extract_ast_nodes = _extract_ast_nodes
FileBoundaryChecker._build_suggestions = _build_suggestions