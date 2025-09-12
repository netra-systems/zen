#!/usr/bin/env python3
"""
[U+1F534] BOUNDARY ENFORCER [U+1F534]
Modular Ultra Deep Thinking Approach to Growth Control

CRITICAL MISSION: Stop unhealthy system growth permanently
Enforces MANDATORY architectural boundaries from CLAUDE.md:
- File lines  <= 300 (HARD LIMIT)
- Function lines  <= 8 (HARD LIMIT)  
- Module count  <= 700 (SYSTEM LIMIT)
- Total LOC  <= 200,000 (CODEBASE LIMIT)
- Complexity score  <= 3 (MAINTAINABILITY LIMIT)

Refactored into focused modules for 300/8 compliance.
"""

from pathlib import Path
from typing import List

from boundary_enforcer_cli_handler import (
    CLIArgumentParser,
    CLIOrchestrator,
    HookInstaller,
    ViolationDisplayer,
)
from boundary_enforcer_core_types import (
    BoundaryReport,
    BoundaryViolation,
    SystemBoundaries,
)
from boundary_enforcer_file_checks import FileBoundaryChecker
from boundary_enforcer_function_checks import FunctionBoundaryChecker
from boundary_enforcer_report_generator import (
    BoundaryReportGenerator,
    ConsoleReportPrinter,
    PRCommentGenerator,
)
from boundary_enforcer_system_checks import SystemBoundaryChecker
from boundary_enforcer_type_checks import TypeBoundaryChecker


class BoundaryEnforcer:
    """Modular ultra thinking boundary enforcer for system growth control"""
    
    def __init__(self, root_path: str = ".", boundaries: SystemBoundaries = None):
        self.root_path = Path(root_path)
        self.boundaries = boundaries or SystemBoundaries()
        self.violations: List[BoundaryViolation] = []
        self.system_metrics = {}
        self._init_checkers()

    def _init_checkers(self) -> None:
        """Initialize all boundary checker modules"""
        self.file_checker = FileBoundaryChecker(self.root_path, self.boundaries)
        self.function_checker = FunctionBoundaryChecker(self.root_path, self.boundaries)
        self.system_checker = SystemBoundaryChecker(self.root_path, self.boundaries)
        self.type_checker = TypeBoundaryChecker(self.root_path, self.boundaries)
        
    def enforce_all_boundaries(self) -> BoundaryReport:
        """Enforce all system boundaries with ultra deep analysis"""
        self._collect_system_metrics()
        self._check_all_boundary_types()
        return self._generate_boundary_report()

    def _collect_system_metrics(self) -> None:
        """Collect comprehensive system metrics using system checker"""
        self.system_metrics = self.system_checker.collect_system_metrics()
    
    def _check_all_boundary_types(self) -> None:
        """Check all boundary types using specialized checkers"""
        self._check_file_boundaries()
        self._check_function_boundaries()
        self._check_system_boundaries()
        self._check_type_boundaries()

    def _check_file_boundaries(self) -> None:
        """Check file line boundaries using file checker"""
        violations = self.file_checker.check_file_boundaries()
        self.violations.extend(violations)

    def _check_function_boundaries(self) -> None:
        """Check function line boundaries using function checker"""
        violations = self.function_checker.check_function_boundaries()
        self.violations.extend(violations)

    def _check_system_boundaries(self) -> None:
        """Check system-wide boundaries using system checker"""
        violations = []
        module_violation = self.system_checker.check_module_count_boundary()
        if module_violation:
            violations.append(module_violation)
        loc_violation = self.system_checker.check_total_loc_boundary()
        if loc_violation:
            violations.append(loc_violation)
        complexity_violation = self.system_checker.check_complexity_boundary()
        if complexity_violation:
            violations.append(complexity_violation)
        self.violations.extend(violations)

    def _check_type_boundaries(self) -> None:
        """Check type and test stub boundaries using type checker"""
        duplicate_violations = self.type_checker.check_duplicate_type_boundaries()
        test_stub_violations = self.type_checker.check_test_stub_boundaries()
        self.violations.extend(duplicate_violations)
        self.violations.extend(test_stub_violations)

    def _generate_boundary_report(self) -> BoundaryReport:
        """Generate comprehensive boundary enforcement report using report generator"""
        report_generator = BoundaryReportGenerator(self.violations, self.system_metrics)
        return report_generator.generate_boundary_report()

    def generate_enforcement_report(self) -> str:
        """Generate human-readable enforcement report using console printer"""
        report = self.enforce_all_boundaries()
        return ConsoleReportPrinter.print_enforcement_report(report)
    def generate_pr_comment(self) -> str:
        """Generate PR comment with boundary status using PR comment generator"""
        report = self.enforce_all_boundaries()
        return PRCommentGenerator.generate_pr_comment(report)







































































def main():
    """Main CLI orchestrator for boundary enforcement"""
    parser = CLIArgumentParser.setup_argument_parser()
    args = parser.parse_args()
    if args.install_hooks:
        return HookInstaller.install_hooks()
    if args.pr_comment:
        enforcer = BoundaryEnforcer()
        comment = enforcer.generate_pr_comment()
        # Handle Unicode encoding for Windows console
        try:
            print(comment)
        except UnicodeEncodeError:
            print(comment.encode('utf-8', errors='ignore').decode('utf-8'))
        return
    enforcer = BoundaryEnforcer()
    violations = CLIOrchestrator.handle_specific_checks(args, enforcer)
    if violations is not None:
        return ViolationDisplayer.display_violation_results(violations, args.fail_on_critical)
    result_status = enforcer.generate_enforcement_report()
    CLIOrchestrator.handle_json_output(args, enforcer)
    CLIOrchestrator.handle_failure_checks(args, enforcer)

if __name__ == "__main__":
    main()