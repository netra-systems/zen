#!/usr/bin/env python3
"""
Atomic Change Validator - Comprehensive validation for atomic changes
Ensures all changes meet the ATOMIC SCOPE requirement from CLAUDE.md
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import argparse

# Add project root to path

@dataclass
class ValidationResult:
    """Result of a validation check"""
    phase: str
    task: str
    passed: bool
    message: str
    command: Optional[str] = None
    output: Optional[str] = None

@dataclass
class AtomicChangeReport:
    """Complete report of atomic change validation"""
    timestamp: str
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    critical_failures: List[ValidationResult] = field(default_factory=list)
    warnings: List[ValidationResult] = field(default_factory=list)
    all_results: List[ValidationResult] = field(default_factory=list)
    
    @property
    def is_atomic(self) -> bool:
        """Determine if change meets atomic requirements"""
        return self.failed_checks == 0 and len(self.critical_failures) == 0
    
    @property
    def compliance_score(self) -> float:
        """Calculate compliance percentage"""
        if self.total_checks == 0:
            return 0.0
        return (self.passed_checks / self.total_checks) * 100

class AtomicChangeValidator:
    """Validates that changes meet atomic scope requirements"""
    
    def __init__(self, verbose: bool = False, fix: bool = False):
        self.verbose = verbose
        self.fix = fix
        self.report = AtomicChangeReport(
            timestamp=datetime.now().isoformat()
        )
        
    def run_command(self, command: str, check: bool = True) -> Tuple[int, str, str]:
        """Execute a command and return result"""
        if self.verbose:
            print(f"  Running: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=60
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)
    
    def validate_phase_1_pre_change(self) -> List[ValidationResult]:
        """Phase 1: Pre-change analysis"""
        results = []
        
        # Check WIP status
        wip_file = PROJECT_ROOT / "MASTER_WIP_STATUS.md"
        result = ValidationResult(
            phase="Pre-Change Analysis",
            task="Review MASTER_WIP_STATUS.md",
            passed=wip_file.exists(),
            message="WIP status file exists" if wip_file.exists() else "WIP status file missing"
        )
        results.append(result)
        
        # Check learnings
        learnings_file = PROJECT_ROOT / "SPEC" / "learnings" / "index.xml"
        result = ValidationResult(
            phase="Pre-Change Analysis",
            task="Check learnings index",
            passed=learnings_file.exists(),
            message="Learnings index accessible" if learnings_file.exists() else "Learnings index missing"
        )
        results.append(result)
        
        # Validate string literals tool exists
        literals_script = PROJECT_ROOT / "scripts" / "query_string_literals.py"
        result = ValidationResult(
            phase="Pre-Change Analysis",
            task="String literals validator available",
            passed=literals_script.exists(),
            message="String literals validator ready" if literals_script.exists() else "String literals validator missing"
        )
        results.append(result)
        
        return results
    
    def validate_phase_2_scope(self) -> List[ValidationResult]:
        """Phase 2: Scope validation"""
        results = []
        
        # Check service independence
        services_spec = PROJECT_ROOT / "SPEC" / "independent_services.xml"
        result = ValidationResult(
            phase="Scope Validation",
            task="Service independence spec available",
            passed=services_spec.exists(),
            message="Service independence can be validated" if services_spec.exists() else "Cannot validate service independence"
        )
        results.append(result)
        
        return results
    
    def validate_phase_3_implementation(self) -> List[ValidationResult]:
        """Phase 3: Implementation completeness"""
        results = []
        
        # Check for absolute imports
        print("  Checking import health...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/comprehensive_import_scanner.py --json-output"
        )
        
        import_valid = returncode == 0
        if not import_valid and self.fix:
            print("  Attempting to fix imports...")
            self.run_command("python scripts/fix_all_import_issues.py --absolute-only")
            # Re-check
            returncode, stdout, stderr = self.run_command(
                "python scripts/comprehensive_import_scanner.py --json-output"
            )
            import_valid = returncode == 0
        
        result = ValidationResult(
            phase="Implementation Completeness",
            task="All imports are absolute",
            passed=import_valid,
            message="All imports use absolute paths" if import_valid else "Found relative imports",
            command="python scripts/comprehensive_import_scanner.py",
            output=stderr if not import_valid else None
        )
        results.append(result)
        
        # Check for test stubs
        print("  Checking for test stubs...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/compliance/stub_checker.py"
        )
        
        no_stubs = "no stub" in stdout.lower() or returncode == 0
        result = ValidationResult(
            phase="Implementation Completeness",
            task="No test stubs present",
            passed=no_stubs,
            message="No test stubs found" if no_stubs else "Test stubs detected",
            command="python scripts/compliance/stub_checker.py"
        )
        results.append(result)
        
        return results
    
    def validate_phase_4_legacy_cleanup(self) -> List[ValidationResult]:
        """Phase 4: Legacy cleanup"""
        results = []
        
        # Check for duplicate tests
        print("  Checking for duplicate tests...")
        if self.fix:
            self.run_command("python scripts/cleanup_duplicate_tests.py")
        
        # Check for numbered files
        print("  Checking for numbered files...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/prevent_numbered_files.py --check"
        )
        
        no_numbered = returncode == 0
        if not no_numbered and self.fix:
            self.run_command("python scripts/prevent_numbered_files.py --fix")
            returncode, stdout, stderr = self.run_command(
                "python scripts/prevent_numbered_files.py --check"
            )
            no_numbered = returncode == 0
        
        result = ValidationResult(
            phase="Legacy Cleanup",
            task="No numbered/versioned files",
            passed=no_numbered,
            message="No numbered files found" if no_numbered else "Found numbered/versioned files",
            command="python scripts/prevent_numbered_files.py --check"
        )
        results.append(result)
        
        # Check for duplicates
        print("  Checking for duplicate code...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/duplicate_detector.py --severity high --max-results 5"
        )
        
        no_critical_duplicates = "critical" not in stdout.lower()
        result = ValidationResult(
            phase="Legacy Cleanup",
            task="No critical duplicates",
            passed=no_critical_duplicates,
            message="No critical duplicates" if no_critical_duplicates else "Critical duplicates found",
            command="python scripts/duplicate_detector.py"
        )
        results.append(result)
        
        return results
    
    def validate_phase_5_validation_suite(self) -> List[ValidationResult]:
        """Phase 5: Full validation suite"""
        results = []
        
        # Architecture compliance
        print("  Checking architecture compliance...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/check_architecture_compliance.py --ci-mode"
        )
        
        compliant = returncode == 0
        result = ValidationResult(
            phase="Validation Suite",
            task="Architecture compliance",
            passed=compliant,
            message="Architecture compliant" if compliant else "Architecture violations found",
            command="python scripts/check_architecture_compliance.py",
            output=stdout if not compliant else None
        )
        results.append(result)
        
        # Boundary enforcement
        print("  Checking boundaries...")
        returncode, stdout, stderr = self.run_command(
            "python scripts/boundary_enforcer.py --check"
        )
        
        boundaries_ok = returncode == 0
        result = ValidationResult(
            phase="Validation Suite",
            task="Boundary limits (450/25 rule)",
            passed=boundaries_ok,
            message="All boundaries respected" if boundaries_ok else "Boundary violations found",
            command="python scripts/boundary_enforcer.py"
        )
        results.append(result)
        
        # Test suite (quick check)
        print("  Running quick test validation...")
        returncode, stdout, stderr = self.run_command(
            "python unified_test_runner.py --level unit --fast-fail --no-coverage"
        )
        
        tests_pass = returncode == 0
        result = ValidationResult(
            phase="Validation Suite",
            task="Unit tests passing",
            passed=tests_pass,
            message="Unit tests pass" if tests_pass else "Test failures detected",
            command="python unified_test_runner.py --level unit"
        )
        results.append(result)
        
        return results
    
    def validate_phase_6_documentation(self) -> List[ValidationResult]:
        """Phase 6: Documentation sync"""
        results = []
        
        # Check if specs are updated
        master_index = PROJECT_ROOT / "LLM_MASTER_INDEX.md"
        result = ValidationResult(
            phase="Documentation Sync",
            task="Master index exists",
            passed=master_index.exists(),
            message="Master index present" if master_index.exists() else "Master index missing"
        )
        results.append(result)
        
        # String literals index
        print("  Updating string literals index...")
        if self.fix:
            self.run_command("python scripts/scan_string_literals.py")
        
        return results
    
    def generate_report(self) -> str:
        """Generate a formatted report"""
        report_lines = [
            "=" * 80,
            "ATOMIC CHANGE VALIDATION REPORT",
            "=" * 80,
            f"Timestamp: {self.report.timestamp}",
            f"Total Checks: {self.report.total_checks}",
            f"Passed: {self.report.passed_checks}",
            f"Failed: {self.report.failed_checks}",
            f"Compliance Score: {self.report.compliance_score:.1f}%",
            "",
            f"**ATOMIC CHANGE STATUS: {'VALID' if self.report.is_atomic else 'INVALID'}**",
            ""
        ]
        
        if self.report.critical_failures:
            report_lines.append("CRITICAL FAILURES:")
            report_lines.append("-" * 40)
            for failure in self.report.critical_failures:
                report_lines.append(f"[X] [{failure.phase}] {failure.task}")
                report_lines.append(f"   {failure.message}")
                if failure.command:
                    report_lines.append(f"   Command: {failure.command}")
                if failure.output and self.verbose:
                    report_lines.append(f"   Output: {failure.output[:200]}...")
                report_lines.append("")
        
        if self.report.warnings:
            report_lines.append("WARNINGS:")
            report_lines.append("-" * 40)
            for warning in self.report.warnings:
                report_lines.append(f"[!] [{warning.phase}] {warning.task}")
                report_lines.append(f"   {warning.message}")
                report_lines.append("")
        
        # Summary by phase
        report_lines.append("PHASE SUMMARY:")
        report_lines.append("-" * 40)
        
        phases = {}
        for result in self.report.all_results:
            if result.phase not in phases:
                phases[result.phase] = {"passed": 0, "failed": 0}
            if result.passed:
                phases[result.phase]["passed"] += 1
            else:
                phases[result.phase]["failed"] += 1
        
        for phase, counts in phases.items():
            total = counts["passed"] + counts["failed"]
            status = "[OK]" if counts["failed"] == 0 else "[FAIL]"
            report_lines.append(f"{status} {phase}: {counts['passed']}/{total} passed")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        if not self.report.is_atomic:
            report_lines.append("")
            report_lines.append("ACTION REQUIRED:")
            report_lines.append("1. Fix all critical failures before proceeding")
            report_lines.append("2. Run with --fix flag to attempt automatic fixes")
            report_lines.append("3. Consult SPEC/atomic_change_specification.xml for guidance")
        
        return "\n".join(report_lines)
    
    def validate(self) -> bool:
        """Run complete validation"""
        print("Starting Atomic Change Validation...")
        print("-" * 40)
        
        all_phases = [
            ("Pre-Change Analysis", self.validate_phase_1_pre_change),
            ("Scope Validation", self.validate_phase_2_scope),
            ("Implementation Completeness", self.validate_phase_3_implementation),
            ("Legacy Cleanup", self.validate_phase_4_legacy_cleanup),
            ("Validation Suite", self.validate_phase_5_validation_suite),
            ("Documentation Sync", self.validate_phase_6_documentation)
        ]
        
        for phase_name, phase_validator in all_phases:
            print(f"\nValidating {phase_name}...")
            results = phase_validator()
            
            for result in results:
                self.report.all_results.append(result)
                self.report.total_checks += 1
                
                if result.passed:
                    self.report.passed_checks += 1
                    if self.verbose:
                        print(f"  [PASS] {result.task}")
                else:
                    self.report.failed_checks += 1
                    if "critical" in result.task.lower() or "Architecture" in result.phase:
                        self.report.critical_failures.append(result)
                    else:
                        self.report.warnings.append(result)
                    print(f"  [FAIL] {result.task}: {result.message}")
        
        print("\n" + "=" * 40)
        print(self.generate_report())
        
        # Save report
        report_dir = PROJECT_ROOT / "test_reports" / "atomic_validation"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"atomic_validation_{timestamp}.txt"
        
        with open(report_file, "w") as f:
            f.write(self.generate_report())
        
        print(f"\nReport saved to: {report_file}")
        
        return self.report.is_atomic

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate that changes meet ATOMIC SCOPE requirements"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix issues"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (skip slow tests)"
    )
    
    args = parser.parse_args()
    
    validator = AtomicChangeValidator(
        verbose=args.verbose,
        fix=args.fix
    )
    
    is_atomic = validator.validate()
    
    # Exit with appropriate code
    sys.exit(0 if is_atomic else 1)

if __name__ == "__main__":
    main()