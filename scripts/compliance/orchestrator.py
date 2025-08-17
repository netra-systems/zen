#!/usr/bin/env python3
"""
Architecture compliance orchestrator.
Coordinates all compliance checking modules and aggregates results.
"""

from collections import defaultdict
from typing import List, Dict

from .core import (
    Violation, ComplianceConfig, ComplianceResults, 
    create_compliance_results
)
from .file_checker import FileChecker, count_total_files
from .function_checker import FunctionChecker
from .type_checker import TypeChecker
from .stub_checker import StubChecker
from .reporter import ComplianceReporter


class ArchitectureEnforcer:
    """Orchestrates architectural rule enforcement"""
    
    def __init__(self, root_path: str = ".", max_file_lines: int = 300, 
                 max_function_lines: int = 8, violation_limit: int = 10,
                 smart_limits: bool = True, use_emoji: bool = True):
        self.config = ComplianceConfig(root_path, max_file_lines, max_function_lines)
        self.file_checker = FileChecker(self.config)
        self.function_checker = FunctionChecker(self.config)
        self.type_checker = TypeChecker(self.config)
        self.stub_checker = StubChecker(self.config)
        self.reporter = ComplianceReporter(max_file_lines, max_function_lines,
                                          violation_limit, smart_limits, use_emoji)
    
    def run_all_checks(self) -> ComplianceResults:
        """Run all compliance checks and return structured results"""
        all_violations = self._collect_all_violations()
        violations_by_type = self._group_violations_by_type(all_violations)
        total_files = count_total_files(self.config)
        compliance_score = self._calculate_compliance_score(all_violations, total_files)
        return create_compliance_results(
            all_violations, total_files, compliance_score, violations_by_type,
            self.config.max_file_lines, self.config.max_function_lines
        )
    
    def _collect_all_violations(self) -> List[Violation]:
        """Collect violations from all checkers"""
        violations = []
        violations.extend(self.file_checker.check_file_sizes())
        violations.extend(self.function_checker.check_function_complexity())
        violations.extend(self.type_checker.check_duplicate_types())
        violations.extend(self.stub_checker.check_test_stubs())
        return violations
    
    def _group_violations_by_type(self, violations: List[Violation]) -> Dict[str, int]:
        """Group violations by type for summary"""
        violations_by_type = defaultdict(int)
        for violation in violations:
            violations_by_type[violation.violation_type] += 1
        return dict(violations_by_type)
    
    def _calculate_compliance_score(self, violations: List[Violation], total_files: int) -> float:
        """Calculate compliance score percentage"""
        if total_files == 0:
            return 100.0
        files_with_violations = len(set(v.file_path for v in violations))
        clean_files = total_files - files_with_violations
        return max(0.0, (clean_files / total_files) * 100)
    
    def generate_report(self) -> str:
        """Generate compliance report"""
        results = self.run_all_checks()
        return self.reporter.generate_report(results)