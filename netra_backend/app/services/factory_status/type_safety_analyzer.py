"""Type safety compliance analyzer - Checks type annotations."""

import ast
from pathlib import Path
from typing import Dict, List, Tuple, Any

from netra_backend.app.services.factory_status.spec_analyzer_core import SpecLoader, SpecViolation, ViolationSeverity


class TypeSafetyAnalyzer:
    """Analyzes code for type safety compliance."""
    
    def __init__(self, spec_loader: SpecLoader):
        """Initialize with spec loader."""
        self.spec_loader = spec_loader
    
    async def analyze_type_safety(self, module_path: Path) -> Tuple[float, List[SpecViolation]]:
        """Check type safety compliance."""
        violations: List[SpecViolation] = []
        total_functions, typed_functions = await self._count_typed_functions(module_path, violations)
        score = self._calculate_type_safety_score(total_functions, typed_functions)
        return score, violations
    
    async def _count_typed_functions(self, module_path: Path, violations: List[SpecViolation]) -> Tuple[int, int]:
        """Count total and typed functions in module."""
        total_functions = 0
        typed_functions = 0
        for py_file in module_path.rglob("*.py"):
            total_functions, typed_functions = await self._process_file_types(py_file, violations, total_functions, typed_functions)
        return total_functions, typed_functions
    
    async def _process_file_types(self, py_file: Path, violations: List[SpecViolation], total: int, typed: int) -> Tuple[int, int]:
        """Process type annotations for a single file."""
        funcs, typed_count = await self._check_type_annotations(py_file, violations)
        return total + funcs, typed + typed_count
    
    def _calculate_type_safety_score(self, total_functions: int, typed_functions: int) -> float:
        """Calculate type safety score percentage."""
        return (typed_functions / total_functions * 100) if total_functions > 0 else 100
    
    async def _check_type_annotations(self, file_path: Path, violations: List[SpecViolation]) -> Tuple[int, int]:
        """Check type annotations in file."""
        try:
            content = self._read_file_content(file_path)
            tree = self._parse_ast(content)
            return self._analyze_function_types(tree, file_path, violations)
        except Exception:
            return 0, 0
    
    def _read_file_content(self, file_path: Path) -> str:
        """Read file content as string."""
        with open(file_path, 'r') as f:
            return f.read()
    
    def _parse_ast(self, content: str) -> Any:
        """Parse content into AST."""
        return ast.parse(content)
    
    def _analyze_function_types(self, tree: Any, file_path: Path, violations: List[SpecViolation]) -> Tuple[int, int]:
        """Analyze function type annotations in AST."""
        total = 0
        typed = 0
        for node in ast.walk(tree):
            if self._is_function_node(node):
                total += 1
                typed += self._check_single_function_types(node, file_path, violations)
        return total, typed
    
    def _is_function_node(self, node: Any) -> bool:
        """Check if AST node is a function definition."""
        return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    
    def _check_single_function_types(self, node: Any, file_path: Path, violations: List[SpecViolation]) -> int:
        """Check type annotations for a single function."""
        has_return = node.returns is not None
        has_args = all(arg.annotation for arg in node.args.args)
        if has_return and has_args:
            return 1
        self._add_type_violation(node, file_path, violations)
        return 0
    
    def _add_type_violation(self, node: Any, file_path: Path, violations: List[SpecViolation]) -> None:
        """Add type annotation violation."""
        violations.append(SpecViolation(
            module=file_path.stem, violation_type="missing_types",
            severity=ViolationSeverity.HIGH,
            description=f"Function {node.name} missing type annotations",
            file_path=str(file_path), line_number=node.lineno,
            remediation="Add type annotations"
        ))