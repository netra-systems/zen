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
