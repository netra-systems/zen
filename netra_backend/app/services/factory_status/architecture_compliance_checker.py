"""Architecture compliance checking module.

Checks compliance against 300/8 line limits.
Follows 450-line limit with 25-line function limit.
"""

import re
import subprocess
from typing import Any, Dict, List

from netra_backend.app.services.factory_status.quality_models import (
    ArchitectureCompliance,
    ComplianceStatus,
)


class ArchitectureComplianceChecker:
    """Checker for architecture compliance."""
    
    MAX_LINES_PER_FILE = 300
    MAX_LINES_PER_FUNCTION = 8
    
    def __init__(self, repo_path: str = "."):
        """Initialize compliance checker."""
        self.repo_path = repo_path
    
    def check_compliance(self) -> ArchitectureCompliance:
        """Check architecture compliance against limits."""
        violations_data = self._collect_all_violations()
        compliance_metrics = self._calculate_compliance_metrics(violations_data)
        return self._build_compliance_result(violations_data, compliance_metrics)
    
    def _calculate_compliance_score(self, line_violations: int,
                                   function_violations: int,
                                   module_violations: List[str]) -> float:
        """Calculate compliance score."""
        total_violations = line_violations + function_violations + len(module_violations)
        return max(0, 100 - (total_violations * 5))
    
    def _collect_all_violations(self) -> Dict[str, Any]:
        """Collect all types of violations."""
        line_violations = self._check_file_line_limits()
        function_violations = self._check_function_line_limits()
        module_violations = self._check_module_violations()
        return {'line': line_violations, 'function': function_violations, 'module': module_violations}
    
    def _calculate_compliance_metrics(self, violations_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compliance score and status from violations."""
        compliance_score = self._calculate_compliance_score(
            violations_data['line'], violations_data['function'], violations_data['module']
        )
        status = self._determine_status(compliance_score)
        return {'score': compliance_score, 'status': status}
    
    def _build_compliance_result(self, violations_data: Dict[str, Any], 
                                compliance_metrics: Dict[str, Any]) -> ArchitectureCompliance:
        """Build final compliance result object."""
        return ArchitectureCompliance(
            line_limit_violations=violations_data['line'],
            function_limit_violations=violations_data['function'],
            module_violations=violations_data['module'],
            compliance_score=compliance_metrics['score'],
            compliance_status=compliance_metrics['status'],
            violation_details=self._build_violation_details(violations_data)
        )
    
    def _build_violation_details(self, violations_data: Dict[str, Any]) -> Dict[str, int]:
        """Build violation details dictionary."""
        return {
            "file_line_limit": violations_data['line'],
            "function_line_limit": violations_data['function'],
            "module_structure": len(violations_data['module'])
        }
    
    def _check_file_line_limits(self) -> int:
        """Check files exceeding 450-line limit."""
        violations = 0
        files = self._get_source_files()
        for file_path in files:
            if file_path and self._file_exceeds_limit(file_path):
                violations += 1
        return violations
    
    def _get_source_files(self) -> List[str]:
        """Get all source files."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    
    def _file_exceeds_limit(self, file_path: str) -> bool:
        """Check if file exceeds line limit."""
        line_count = self._count_file_lines(file_path)
        return line_count > self.MAX_LINES_PER_FILE
    
    def _count_file_lines(self, file_path: str) -> int:
        """Count lines in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_function_line_limits(self) -> int:
        """Check functions exceeding 25-line limit."""
        violations = 0
        python_files = self._get_python_files()
        for file_path in python_files:
            if file_path:
                violations += self._count_function_violations(file_path)
        return violations
    
    def _get_python_files(self) -> List[str]:
        """Get all Python files."""
        cmd = ["find", ".", "-name", "*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout else []
    
    def _count_function_violations(self, file_path: str) -> int:
        """Count function violations in file."""
        try:
            content = self._read_file_content(file_path)
            functions = self._extract_functions(content)
            return self._count_oversized_functions(functions)
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content safely."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function definitions from content."""
        pattern = r'def\s+\w+\([^)]*\):[^:]*?(?=\n\s*def|\n\s*class|\n\s*$|\Z)'
        return re.findall(pattern, content, re.DOTALL)
    
    def _count_oversized_functions(self, functions: List[str]) -> int:
        """Count functions exceeding line limit."""
        violations = 0
        for func in functions:
            if self._function_exceeds_limit(func):
                violations += 1
        return violations
    
    def _function_exceeds_limit(self, func: str) -> bool:
        """Check if function exceeds line limit."""
        lines = [line for line in func.split('\n') if line.strip()]
        return len(lines) > self.MAX_LINES_PER_FUNCTION
    
    def _check_module_violations(self) -> List[str]:
        """Check for module structure violations."""
        violations = []
        deep_dirs = self._find_deep_directories()
        violations.extend(deep_dirs)
        return violations
    
    def _find_deep_directories(self) -> List[str]:
        """Find overly deep directory structures."""
        cmd = ["find", ".", "-type", "d", "-path", "./*/*/*/*/*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            return result.stdout.strip().split("\n")
        return []
    
    def _determine_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score."""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.MINOR_VIOLATIONS
        elif score >= 60:
            return ComplianceStatus.MAJOR_VIOLATIONS
        return ComplianceStatus.NON_COMPLIANT
