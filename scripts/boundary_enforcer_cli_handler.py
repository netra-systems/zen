#!/usr/bin/env python3
"""
CLI handling module for boundary enforcement system.
Handles argument parsing and command orchestration.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from boundary_enforcer_core_types import BoundaryViolation

class CLIArgumentParser:
    """Handles command line argument parsing"""
    
    @staticmethod
    def setup_argument_parser() -> argparse.ArgumentParser:
        """Setup and configure argument parser"""
        parser = argparse.ArgumentParser(
            description='BOUNDARY ENFORCER - Stop unhealthy system growth',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""Examples: python boundary_enforcer.py --enforce""")
        return CLIArgumentParser._configure_parser_arguments(parser)

    @staticmethod
    def _configure_parser_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Configure all parser arguments"""
        parser.add_argument('--enforce', action='store_true', help='Run full boundary enforcement')
        parser.add_argument('--check-file-boundaries', action='store_true', help='Check only file size boundaries')
        parser.add_argument('--check-function-boundaries', action='store_true', help='Check only function size boundaries')
        parser.add_argument('--fail-on-critical', action='store_true', help='Exit with error code on critical violations')
        parser.add_argument('--fail-on-emergency', action='store_true', help='Exit with error code on emergency actions')
        CLIArgumentParser._add_remaining_arguments(parser)
        return parser

    @staticmethod
    def _add_remaining_arguments(parser: argparse.ArgumentParser) -> None:
        """Add remaining parser arguments"""
        parser.add_argument('--json-output', help='Save JSON report to file')
        parser.add_argument('--emergency-only', action='store_true', help='Show only emergency-level violations')
        parser.add_argument('--install-hooks', action='store_true', help='Install pre-commit hooks')
        parser.add_argument('--pr-comment', action='store_true', help='Generate PR comment with boundary status')

class HookInstaller:
    """Handles installation of pre-commit hooks and CI workflow"""
    
    @staticmethod
    def install_hooks() -> None:
        """Handle installation of pre-commit hooks and CI workflow"""
        pre_commit_config = Path('.pre-commit-config.yaml')
        pre_commit_config.write_text(HookInstaller._create_pre_commit_config())
        workflow_config = Path('.github/workflows/boundary-enforcement.yml')
        workflow_config.parent.mkdir(exist_ok=True)
        workflow_config.write_text(HookInstaller._create_ci_workflow_config())
        print("[OK] Boundary enforcement hooks and CI workflow installed")

    @staticmethod
    def _create_pre_commit_config() -> str:
        """Create pre-commit configuration for boundary enforcement"""
        return """# Boundary Enforcement Pre-commit Configuration
repos:
  - repo: local
    hooks:
      - id: boundary-enforcer
        name: System Boundary Enforcer
        entry: python scripts/boundary_enforcer.py --enforce --fail-on-critical
        language: system
        files: '^(app|frontend|scripts)/'
        stages: [commit]
        
      - id: file-size-check
        name: File Size Boundary Check
        entry: python scripts/boundary_enforcer.py --check-file-boundaries
        language: system
        files: '\\.(py|ts|tsx)$'
        stages: [commit]
        
      - id: function-complexity-check
        name: Function Complexity Boundary Check
        entry: python scripts/boundary_enforcer.py --check-function-boundaries
        language: system
        files: '\\.py$'
        stages: [commit]
"""

    @staticmethod
    def _create_ci_workflow_config() -> str:
        """Create CI workflow for boundary enforcement"""
        return """name: Boundary Enforcement

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  boundary-enforcement:
    runs-on: warp-custom-default
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install radon
      
      - name: Run Boundary Enforcer
        run: |
          python scripts/boundary_enforcer.py --enforce --json-output boundary-report.json
      
      - name: Check Critical Violations
        run: |
          python scripts/boundary_enforcer.py --fail-on-emergency
      
      - name: Upload Boundary Report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: boundary-report
          path: boundary-report.json
      
      - name: Comment PR with Report
        if: github.event_name == 'pull_request'
        run: |
          python scripts/boundary_enforcer.py --pr-comment
"""

class JSONOutputHandler:
    """Handles JSON output operations"""
    
    @staticmethod
    def save_json_report(json_path: str, report_data: dict) -> None:
        """Save JSON report to file"""
        with open(json_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        print(f"\n[INFO] JSON report saved to: {json_path}")

class FailureHandler:
    """Handles failure condition checking and exits"""
    
    @staticmethod
    def check_emergency_failures(emergency_actions: List[str]) -> None:
        """Handle emergency failure conditions"""
        if emergency_actions:
            print("\n[CRITICAL] EMERGENCY ACTIONS REQUIRED - Build failing")
            sys.exit(1)

    @staticmethod
    def check_critical_failures(violations: List[BoundaryViolation]) -> None:
        """Handle critical failure conditions"""
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            print(f"\n[FAIL] {len(critical_violations)} critical violations - Build failing")
            sys.exit(1)

class ViolationDisplayer:
    """Handles violation result display"""
    
    @staticmethod
    def display_violation_results(violations: List[BoundaryViolation], 
                                fail_on_critical: bool) -> None:
        """Display results for specific boundary check violations"""
        if violations:
            print(f"\n[FAIL] Found {len(violations)} boundary violations")
            for v in violations[:10]:
                print(f"  - {v.description} in {v.file_path}")
            ViolationDisplayer._check_critical_exit(fail_on_critical)
        else:
            print("[PASS] No boundary violations found")

    @staticmethod
    def _check_critical_exit(fail_on_critical: bool) -> None:
        """Exit if fail on critical is enabled"""
        if fail_on_critical:
            sys.exit(1)

class CLIOrchestrator:
    """Orchestrates CLI command execution"""
    
    @staticmethod
    def handle_specific_checks(args, enforcer) -> Optional[List[BoundaryViolation]]:
        """Run specific boundary checks based on arguments"""
        if args.check_file_boundaries:
            from boundary_enforcer_file_checks import FileBoundaryChecker
            checker = FileBoundaryChecker(enforcer.root_path, enforcer.boundaries)
            return checker.check_file_boundaries()
        elif args.check_function_boundaries:
            from boundary_enforcer_function_checks import FunctionBoundaryChecker
            checker = FunctionBoundaryChecker(enforcer.root_path, enforcer.boundaries)
            return checker.check_function_boundaries()
        return None

    @staticmethod
    def handle_json_output(args, enforcer) -> None:
        """Handle JSON output if requested"""
        if args.json_output:
            from dataclasses import asdict
            report = enforcer.enforce_all_boundaries()
            JSONOutputHandler.save_json_report(args.json_output, asdict(report))

    @staticmethod
    def handle_failure_checks(args, enforcer) -> None:
        """Handle all failure condition checks"""
        if args.fail_on_emergency:
            report = enforcer.enforce_all_boundaries()
            FailureHandler.check_emergency_failures(report.emergency_actions)
        if args.fail_on_critical:
            FailureHandler.check_critical_failures(enforcer.violations)