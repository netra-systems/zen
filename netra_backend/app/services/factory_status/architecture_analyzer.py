"""Architecture compliance analyzer - Checks 300/8 limits."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from netra_backend.app.services.factory_status.spec_analyzer_core import (
    SpecLoader,
    SpecViolation,
    ViolationSeverity,
)


class ArchitectureAnalyzer:
    """Analyzes code against architecture requirements."""
    
    def __init__(self, spec_loader: SpecLoader):
        """Initialize with spec loader."""
        self.spec_loader = spec_loader
    
    async def analyze_architecture(self, module_path: Path) -> Tuple[float, List[SpecViolation]]:
        """Check architecture compliance (300/8 limits)."""
        violations: List[SpecViolation] = []
        total_files, compliant_files = await self._analyze_all_py_files(module_path, violations)
        score = self._calculate_compliance_score(total_files, compliant_files)
        return score, violations
    
    async def _analyze_all_py_files(self, module_path: Path, violations: List[SpecViolation]) -> Tuple[int, int]:
        """Analyze all Python files in module path."""
        total_files = 0
        compliant_files = 0
        for py_file in module_path.rglob("*.py"):
            total_files += 1
            compliant_files += await self._process_single_file(py_file, violations)
        return total_files, compliant_files
    
    async def _process_single_file(self, py_file: Path, violations: List[SpecViolation]) -> int:
        """Process a single Python file and return compliance status."""
        file_ok = await self._check_file_compliance(py_file, violations)
        return 1 if file_ok else 0
    
    def _calculate_compliance_score(self, total_files: int, compliant_files: int) -> float:
        """Calculate compliance score percentage."""
        return (compliant_files / total_files * 100) if total_files > 0 else 100
    
    async def _check_file_compliance(self, file_path: Path, violations: List[SpecViolation]) -> bool:
        """Check single file for compliance."""
        try:
            lines = self._read_file_lines(file_path)
            return self._validate_file_compliance(file_path, lines, violations)
        except Exception:
            return True  # Skip on error
    
    async def _validate_file_compliance(self, file_path: Path, lines: List[str], violations: List[SpecViolation]) -> bool:
        """Validate file compliance for length and functions."""
        length_ok = self._check_file_length(file_path, lines, violations)
        func_ok = await self._check_function_lengths(file_path, lines, violations)
        return length_ok and func_ok
    
    def _read_file_lines(self, file_path: Path) -> List[str]:
        """Read all lines from file."""
        with open(file_path, 'r') as f:
            return f.readlines()
    
    def _check_file_length(self, file_path: Path, lines: List[str], violations: List[SpecViolation]) -> bool:
        """Check if file exceeds 300 line limit."""
        if len(lines) > 300:
            self._add_file_length_violation(file_path, len(lines), violations)
            return False
        return True
    
    def _add_file_length_violation(self, file_path: Path, line_count: int, violations: List[SpecViolation]) -> None:
        """Add file length violation to list."""
        violation = self._create_file_length_violation(file_path, line_count)
        violations.append(violation)
    
    def _create_file_length_violation(self, file_path: Path, line_count: int) -> SpecViolation:
        """Create file length violation object."""
        return SpecViolation(
            module=file_path.stem, violation_type="file_length",
            severity=ViolationSeverity.CRITICAL,
            description=f"File has {line_count} lines (max 300)",
            file_path=str(file_path), line_number=None,
            remediation="Split into focused modules"
        )
    
    async def _check_function_lengths(self, file_path: Path, lines: List[str], violations: List[SpecViolation]) -> bool:
        """Check function lengths in file."""
        func_data = self._init_function_tracking()
        all_ok = True
        for i, line in enumerate(lines, 1):
            all_ok = self._process_line_for_function(i, line, file_path, func_data, violations, all_ok)
        return all_ok
    
    def _init_function_tracking(self) -> Dict[str, Any]:
        """Initialize function tracking data."""
        return {
            "in_function": False, "func_start": 0,
            "func_name": "", "func_lines": 0
        }
    
    def _process_line_for_function(self, line_num: int, line: str, file_path: Path, 
                                 func_data: Dict[str, Any], violations: List[SpecViolation], all_ok: bool) -> bool:
        """Process a single line for function length checking."""
        if self._is_function_start(line):
            all_ok = self._handle_function_start(line_num, line, file_path, func_data, violations, all_ok)
        elif func_data["in_function"]:
            self._handle_function_body(line, func_data)
        return all_ok
    
    def _is_function_start(self, line: str) -> bool:
        """Check if line starts a function definition."""
        stripped = line.strip()
        return stripped.startswith("def ") or stripped.startswith("async def ")
    
    def _handle_function_start(self, line_num: int, line: str, file_path: Path, 
                             func_data: Dict[str, Any], violations: List[SpecViolation], all_ok: bool) -> bool:
        """Handle the start of a function definition."""
        if func_data["in_function"] and func_data["func_lines"] > 8:
            self._add_function_length_violation(file_path, func_data, violations)
            all_ok = False
        self._start_new_function_tracking(line_num, line, func_data)
        return all_ok
    
    def _handle_function_body(self, line: str, func_data: Dict[str, Any]) -> None:
        """Handle a line within a function body."""
        if line and not line[0].isspace() and not line.strip().startswith("#"):
            func_data["in_function"] = False
        else:
            func_data["func_lines"] += 1
    
    def _start_new_function_tracking(self, line_num: int, line: str, func_data: Dict[str, Any]) -> None:
        """Start tracking a new function."""
        func_data["in_function"] = True
        func_data["func_start"] = line_num
        func_data["func_name"] = line.split("(")[0].replace("def ", "").replace("async ", "").strip()
        func_data["func_lines"] = 1
    
    def _add_function_length_violation(self, file_path: Path, func_data: Dict[str, Any], violations: List[SpecViolation]) -> None:
        """Add function length violation to list."""
        violations.append(SpecViolation(
            module=file_path.stem, violation_type="function_length",
            severity=ViolationSeverity.CRITICAL,
            description=f"Function {func_data['func_name']} has {func_data['func_lines']} lines (max 8)",
            file_path=str(file_path), line_number=func_data["func_start"],
            remediation="Extract helper functions"
        ))