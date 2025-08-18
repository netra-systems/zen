"""Quality validation for architecture compliance and technical debt.

Handles architecture compliance checking and technical debt calculation.
Module follows 300-line limit with 8-line function limit.
"""

import re
import subprocess
from typing import List

from .git_commit_parser import GitCommitParser
from .technical_debt_calculator import TechnicalDebtCalculator
from .quality_core import (
    ArchitectureCompliance, TechnicalDebt, ComplianceStatus, 
    QualityConstants, QualityMetrics, QualityLevel,
    TestCoverageMetrics, DocumentationMetrics
)


class ArchitectureValidator:
    """Validator for architecture compliance."""
    
    def __init__(self, repo_path: str = "."):
        """Initialize architecture validator."""
        self.repo_path = repo_path
    
    def check_compliance(self) -> ArchitectureCompliance:
        """Check architecture compliance against 300/8 limits."""
        line_violations = self._check_file_line_limits()
        function_violations = self._check_function_line_limits()
        module_violations = self._check_module_violations()
        
        total_violations = line_violations + function_violations + len(module_violations)
        compliance_score = max(0, 100 - (total_violations * 5))
        status = self._determine_compliance_status(compliance_score)
        
        violation_details = {
            "file_line_limit": line_violations,
            "function_line_limit": function_violations,
            "module_structure": len(module_violations)
        }
        
        return ArchitectureCompliance(
            line_limit_violations=line_violations,
            function_limit_violations=function_violations,
            module_violations=module_violations,
            compliance_score=compliance_score,
            compliance_status=status,
            violation_details=violation_details
        )
    
    def _check_file_line_limits(self) -> int:
        """Check files exceeding 300-line limit."""
        violations = 0
        cmd = ["find", ".", "-name", "*.py", "-o", "-name", "*.ts", "-o", "-name", "*.tsx"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        files = result.stdout.strip().split("\n") if result.stdout else []
        for file_path in files:
            if file_path:
                line_count = self._count_file_lines(file_path)
                if line_count > QualityConstants.MAX_LINES_PER_FILE:
                    violations += 1
        
        return violations
    
    def _count_file_lines(self, file_path: str) -> int:
        """Count lines in a specific file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_function_line_limits(self) -> int:
        """Check functions exceeding 8-line limit."""
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
            
            function_pattern = r'def\s+\w+\([^)]*\):[^:]*?(?=\n\s*def|\n\s*class|\n\s*$|\Z)'
            functions = re.findall(function_pattern, content, re.DOTALL)
            
            violations = 0
            for func in functions:
                lines = len([line for line in func.split('\n') if line.strip()])
                if lines > QualityConstants.MAX_LINES_PER_FUNCTION:
                    violations += 1
            
            return violations
        except (IOError, UnicodeDecodeError):
            return 0
    
    def _check_module_violations(self) -> List[str]:
        """Check for module structure violations."""
        violations = []
        
        cmd = ["find", ".", "-type", "d", "-path", "./*/*/*/*/*"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.stdout:
            deep_dirs = result.stdout.strip().split("\n")
            violations.extend(deep_dirs)
        
        return violations
    
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
        from .quality_metrics import TestCoverageCalculator, DocumentationCalculator
        
        coverage_calc = TestCoverageCalculator(self.repo_path)
        doc_calc = DocumentationCalculator(self.repo_path)
        arch_validator = ArchitectureValidator(self.repo_path)
        debt_calc = TechnicalDebtCalculator(self.repo_path)
        
        coverage = coverage_calc.calculate()
        docs = doc_calc.calculate()
        architecture = arch_validator.check_compliance()
        debt = debt_calc.calculate_debt()
        
        overall_score = self._calculate_overall_quality_score(
            coverage, docs, architecture, debt
        )
        quality_level = self._determine_quality_level(overall_score)
        
        return QualityMetrics(
            test_coverage=coverage,
            documentation=docs,
            architecture=architecture,
            technical_debt=debt,
            overall_quality_score=overall_score,
            quality_level=quality_level
        )
    
    def _calculate_overall_quality_score(self, coverage: TestCoverageMetrics,
                                        docs: DocumentationMetrics,
                                        arch: ArchitectureCompliance,
                                        debt: TechnicalDebt) -> float:
        """Calculate overall quality score."""
        coverage_score = coverage.overall_coverage
        docs_score = 80 if docs.documentation_quality == QualityLevel.EXCELLENT else 60
        arch_score = arch.compliance_score
        debt_score = max(0, 100 - debt.debt_score * 10)
        
        weights = [0.3, 0.2, 0.3, 0.2]
        scores = [coverage_score, docs_score, arch_score, debt_score]
        
        return sum(w * s for w, s in zip(weights, scores))
    
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