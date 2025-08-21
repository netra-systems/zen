"""Quality validation for architecture compliance and technical debt.

Handles architecture compliance checking and technical debt calculation.
Module follows 450-line limit with 25-line function limit.
"""

import re
import subprocess
from typing import List

from netra_backend.app.services.factory_status.git_commit_parser import GitCommitParser
from netra_backend.app.services.factory_status.quality_core import (
    ArchitectureCompliance,
    ComplianceStatus,
    DocumentationMetrics,
    QualityConstants,
    QualityLevel,
    QualityMetrics,
    TechnicalDebt,
    TestCoverageMetrics,
)
from netra_backend.app.services.factory_status.technical_debt_calculator import (
    TechnicalDebtCalculator,
)


class ArchitectureValidator:
    """Validator for architecture compliance."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize architecture validator."""
        self.repo_path = repo_path
    
    def check_compliance(self) -> ArchitectureCompliance:
        """Check architecture compliance against 300/8 limits."""
        violations_data = self._gather_violation_data()
        compliance_score = self._calculate_compliance_score(violations_data)
        status = self._determine_compliance_status(compliance_score)
        violation_details = self._build_violation_details(violations_data)
        return self._build_compliance_result(violations_data, compliance_score, status, violation_details)
    
    def _gather_violation_data(self) -> dict:
        """Gather all violation data."""
        line_violations = self._check_file_line_limits()
        function_violations = self._check_function_line_limits()
        module_violations = self._check_module_violations()
        return {
            "line": line_violations,
            "function": function_violations,
            "module": module_violations
        }
    
    def _calculate_compliance_score(self, violations_data: dict) -> float:
        """Calculate compliance score from violations."""
        total_violations = (
            violations_data["line"] + 
            violations_data["function"] + 
            len(violations_data["module"])
        )
        return max(0, 100 - (total_violations * 5))
    
    def _build_violation_details(self, violations_data: dict) -> dict:
        """Build violation details dictionary."""
        return {
            "file_line_limit": violations_data["line"],
            "function_line_limit": violations_data["function"],
            "module_structure": len(violations_data["module"])
        }
    
    def _build_compliance_result(self, violations_data: dict, compliance_score: float, 
                                status: ComplianceStatus, violation_details: dict) -> ArchitectureCompliance:
        """Build final compliance result."""
        return ArchitectureCompliance(
            line_limit_violations=violations_data["line"],
            function_limit_violations=violations_data["function"],
            module_violations=violations_data["module"],
            compliance_score=compliance_score,
            compliance_status=status,
            violation_details=violation_details
        )

    def _check_file_line_limits(self) -> int:
        """Check files exceeding 450-line limit."""
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        files = self._extract_file_list(result)
        return self._count_file_violations(files)
    
    def _extract_file_list(self, result: subprocess.CompletedProcess) -> List[str]:
        """Extract file list from subprocess result."""
        if not result.stdout:
            return []
        return result.stdout.strip().split("\n")
    
    def _count_file_violations(self, files: List[str]) -> int:
        """Count violations in file list."""
        violations = 0
        for file_path in files:
            if file_path and self._is_file_oversized(file_path):
                violations += 1
        return violations
    
    def _is_file_oversized(self, file_path: str) -> bool:
        """Check if file exceeds line limit."""
        line_count = self._count_file_lines(file_path)
        return line_count > QualityConstants.MAX_LINES_PER_FILE
    
    def _count_file_lines(self, file_path: str) -> int:
        """Count lines in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_function_line_limits(self) -> int:
        """Check functions exceeding 25-line limit."""
        cmd = ["find", ".", "-name", "*.py"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        files = self._extract_python_files(result)
        return self._sum_function_violations(files)
    
    def _extract_python_files(self, result: subprocess.CompletedProcess) -> List[str]:
        """Extract Python file list from subprocess result."""
        if not result.stdout:
            return []
        return result.stdout.strip().split("\n")
    
    def _sum_function_violations(self, files: List[str]) -> int:
        """Sum function violations across all files."""
        violations = 0
        for file_path in files:
            if file_path:
                violations += self._count_function_violations(file_path)
        return violations
    
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
        function_pattern = r'def\s+\w+\([^)]*\):[^:]*?(?=\n\s*def|\n\s*class|\n\s*$|\Z)'
        return re.findall(function_pattern, content, re.DOTALL)
    
    def _count_oversized_functions(self, functions: List[str]) -> int:
        """Count functions exceeding line limit."""
        violations = 0
        for func in functions:
            lines = len([line for line in func.split('\n') if line.strip()])
            if lines > QualityConstants.MAX_LINES_PER_FUNCTION:
                violations += 1
        return violations
    
    def _check_module_violations(self) -> List[str]:
        """Check for module structure violations."""
        cmd = ["find", ".", "-type", "d", "-path", "./*/*/*/*/*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return self._extract_deep_directories(result)
    
    def _extract_deep_directories(self, result: subprocess.CompletedProcess) -> List[str]:
        """Extract deeply nested directories from result."""
        if not result.stdout:
            return []
        return result.stdout.strip().split("\n")
    
    def _determine_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status from score."""
        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 80:
            return ComplianceStatus.MINOR_VIOLATIONS
        elif score >= 60:
            return ComplianceStatus.MAJOR_VIOLATIONS
        return ComplianceStatus.NON_COMPLIANT




class QualityCalculator:
    """Main calculator orchestrating all quality metrics."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize quality calculator."""
        self.repo_path = repo_path
        
    def calculate_quality_metrics(self) -> QualityMetrics:
        """Calculate comprehensive quality metrics."""
        calculators = self._initialize_calculators()
        metrics = self._gather_metrics(calculators)
        overall_score = self._calculate_overall_quality_score(*metrics)
        quality_level = self._determine_quality_level(overall_score)
        return self._build_quality_metrics(metrics, overall_score, quality_level)
    
    def _initialize_calculators(self) -> tuple:
        """Initialize all quality calculators."""
        from .quality_metrics import DocumentationCalculator, TestCoverageCalculator
        coverage_calc = TestCoverageCalculator(self.repo_path)
        doc_calc = DocumentationCalculator(self.repo_path)
        arch_validator = ArchitectureValidator(self.repo_path)
        debt_calc = TechnicalDebtCalculator(self.repo_path)
        return (coverage_calc, doc_calc, arch_validator, debt_calc)
    
    def _gather_metrics(self, calculators: tuple) -> tuple:
        """Gather all metrics from calculators."""
        coverage_calc, doc_calc, arch_validator, debt_calc = calculators
        coverage = coverage_calc.calculate()
        docs = doc_calc.calculate()
        architecture = arch_validator.check_compliance()
        debt = debt_calc.calculate_debt()
        return (coverage, docs, architecture, debt)
    
    def _build_quality_metrics(self, metrics: tuple, overall_score: float, 
                              quality_level: QualityLevel) -> QualityMetrics:
        """Build final quality metrics object."""
        coverage, docs, architecture, debt = metrics
        return QualityMetrics(
            test_coverage=coverage, documentation=docs,
            architecture=architecture, technical_debt=debt,
            overall_quality_score=overall_score, quality_level=quality_level
        )
    
    def _calculate_overall_quality_score(self, coverage: TestCoverageMetrics,
                                        docs: DocumentationMetrics,
                                        arch: ArchitectureCompliance,
                                        debt: TechnicalDebt) -> float:
        """Calculate overall quality score."""
        scores = self._extract_component_scores(coverage, docs, arch, debt)
        weights = [0.3, 0.2, 0.3, 0.2]
        return sum(w * s for w, s in zip(weights, scores))
    
    def _extract_component_scores(self, coverage: TestCoverageMetrics, docs: DocumentationMetrics,
                                 arch: ArchitectureCompliance, debt: TechnicalDebt) -> List[float]:
        """Extract individual component scores."""
        coverage_score = coverage.overall_coverage
        docs_score = 80 if docs.documentation_quality == QualityLevel.EXCELLENT else 60
        arch_score = arch.compliance_score
        debt_score = max(0, 100 - debt.debt_score * 10)
        return [coverage_score, docs_score, arch_score, debt_score]
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """Determine quality level from score."""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.NEEDS_IMPROVEMENT
        return QualityLevel.POOR
