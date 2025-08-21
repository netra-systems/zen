"""Architecture compliance metrics calculator.

Checks compliance with file and function size limits.
Follows 450-line limit with 25-line function limit.
"""

import re
import subprocess
from typing import Dict, List
from netra_backend.app.services.factory_status.metrics_quality_types import ArchitectureCompliance, ComplianceStatus


class ArchitectureComplianceCalculator:
    """Calculator for architecture compliance metrics."""
    
    MAX_LINES_PER_FILE = 300
    MAX_LINES_PER_FUNCTION = 8
    
    def __init__(self, repo_path: str = "."):
        """Initialize architecture compliance calculator."""
        self.repo_path = repo_path
    
    def check_architecture_compliance(self) -> ArchitectureCompliance:
        """Check architecture compliance metrics."""
        line_violations = self._check_file_line_limits()
        function_violations = self._check_function_line_limits()
        module_violations = self._check_module_violations()
        
        violation_details = self._build_violation_details(
            line_violations, function_violations, len(module_violations)
        )
        
        compliance_score = self._calculate_compliance_score(violation_details)
        compliance_status = self._determine_compliance_status(compliance_score)
        
        return ArchitectureCompliance(
            line_limit_violations=line_violations,
            function_limit_violations=function_violations,
            module_violations=module_violations,
            compliance_score=compliance_score,
            compliance_status=compliance_status,
            violation_details=violation_details
        )
    
    def _check_file_line_limits(self) -> int:
        """Check files exceeding 450-line limit."""
        violations = 0
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        for file_path in files:
            if file_path and self._file_exceeds_limit(file_path):
                violations += 1
        
        return violations
    
    def _file_exceeds_limit(self, file_path: str) -> bool:
        """Check if file exceeds line limit."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = sum(1 for _ in f)
            return lines > self.MAX_LINES_PER_FILE
        except (IOError, UnicodeDecodeError):
            return False
    
    def _check_function_line_limits(self) -> int:
        """Check functions exceeding 25-line limit."""
        violations = 0
        cmd = ["find", ".", "-name", "*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        for file_path in files:
            if file_path:
                violations += self._count_function_violations(file_path)
        
        return violations
    
    def _count_function_violations(self, file_path: str) -> int:
        """Count function violations in file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            functions = self._extract_functions(content)
            return self._count_oversized_functions(functions)
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function definitions from content."""
        function_pattern = r'def\s+\w+\([^)]*\):[^:]*?(?=\n\s*def|\n\s*class|\n\s*$|\Z)'
        return re.findall(function_pattern, content, re.DOTALL)
    
    def _count_oversized_functions(self, functions: List[str]) -> int:
        """Count functions exceeding line limit."""
        violations = 0
        for func in functions:
            lines = len([line for line in func.split('\n') if line.strip()])
            if lines > self.MAX_LINES_PER_FUNCTION:
                violations += 1
        return violations
    
    def _check_module_violations(self) -> List[str]:
        """Check for module structure violations."""
        violations = []
        
        # Check for overly deep nesting (simplified)
        cmd = ["find", ".", "-type", "d", "-path", "./*/*/*/*/*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            deep_dirs = result.stdout.strip().split("\n")
            violations.extend(deep_dirs)
        
        return violations
    
    def _build_violation_details(self, line_violations: int, 
                                function_violations: int, 
                                module_violations: int) -> Dict[str, int]:
        """Build violation details dictionary."""
        return {
            "file_line_violations": line_violations,
            "function_line_violations": function_violations,
            "module_violations": module_violations
        }
    
    def _calculate_compliance_score(self, violations: Dict[str, int]) -> float:
        """Calculate compliance score from violations."""
        total_violations = sum(violations.values())
        total_files = self._count_total_files()
        
        if total_files == 0:
            return 100.0
        
        violation_ratio = total_violations / total_files
        return max(0, 100 - (violation_ratio * 100))
    
    def _count_total_files(self) -> int:
        """Count total source files."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return len(result.stdout.strip().split("\n")) if result.stdout else 0
    
    def _determine_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score."""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.MINOR_VIOLATIONS
        elif score >= 60:
            return ComplianceStatus.MAJOR_VIOLATIONS
        return ComplianceStatus.NON_COMPLIANT