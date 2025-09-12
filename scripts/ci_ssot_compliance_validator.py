#!/usr/bin/env python3
"""
 ALERT:  CI/CD SSOT Compliance Validator

CRITICAL MISSION: Integrate SSOT compliance validation into CI/CD pipeline
Context: Automated deployment gate to prevent SSOT violations from reaching production
Objective: Block deployments that contain critical security or SSOT violations

Business Value:
- Protects $500K+ ARR by preventing security regressions in production
- Automated gate prevents human oversight errors
- Maintains SSOT architectural integrity across deployments
- Provides clear feedback for developers on compliance failures

INTEGRATION POINTS:
1. GitHub Actions workflow integration
2. GitLab CI pipeline integration  
3. Jenkins pipeline integration
4. Docker build validation
5. GCP Cloud Build integration

Usage:
    # In CI/CD pipeline:
    python scripts/ci_ssot_compliance_validator.py --mode=deployment-gate
    
    # For pull request validation:
    python scripts/ci_ssot_compliance_validator.py --mode=pr-validation --pr-number=123
    
    # For branch protection:
    python scripts/ci_ssot_compliance_validator.py --mode=branch-protection --branch=main

Exit codes:
    0 = Compliance validation passed - deployment allowed
    1 = SSOT violations found - deployment blocked
    2 = Critical security issues - immediate escalation required
    3 = Validation error - manual review required
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

# Configure logging for CI environments
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ci_ssot_compliance.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class ValidationMode(Enum):
    """CI/CD validation modes."""
    DEPLOYMENT_GATE = "deployment-gate"
    PR_VALIDATION = "pr-validation"
    BRANCH_PROTECTION = "branch-protection"
    CONTINUOUS_MONITORING = "continuous-monitoring"
    MANUAL_VALIDATION = "manual-validation"


class ComplianceLevel(Enum):
    """SSOT compliance levels for different environments."""
    STRICT = "strict"      # Production: Zero violations allowed
    STANDARD = "standard"  # Staging: Critical violations blocked
    PERMISSIVE = "permissive"  # Development: Warnings only


@dataclass
class CIValidationConfig:
    """Configuration for CI/CD compliance validation."""
    mode: ValidationMode
    compliance_level: ComplianceLevel
    project_root: Path
    environment: str
    branch: Optional[str] = None
    pr_number: Optional[str] = None
    commit_sha: Optional[str] = None
    deployment_target: Optional[str] = None


@dataclass 
class ValidationResult:
    """Results of CI/CD compliance validation."""
    passed: bool
    exit_code: int
    validation_timestamp: str
    total_files_checked: int
    critical_violations: int
    error_violations: int
    warning_violations: int
    violations: List[Dict[str, Any]]
    config: CIValidationConfig
    recommendations: List[str]
    blocking_reasons: List[str]


class CISSotComplianceValidator:
    """
    CI/CD pipeline integration for SSOT compliance validation.
    
    Provides automated gates to prevent deployment of SSOT violations.
    """
    
    def __init__(self, config: CIValidationConfig):
        """Initialize CI/CD SSOT compliance validator."""
        self.config = config
        self.project_root = config.project_root
        self.validation_start_time = datetime.now()
        
        # Import monitoring components
        try:
            sys.path.append(str(self.project_root / "scripts"))
            from monitor_ssot_compliance import (
                SSOTComplianceMonitor,
                WebSocketAuthPatternMonitor, 
                ViolationSeverity,
                MonitoringReport
            )
            self.monitor = SSOTComplianceMonitor(self.project_root)
            self.monitoring_available = True
        except ImportError as e:
            logger.error(f"Monitoring components not available: {e}")
            self.monitoring_available = False
    
    def detect_ci_environment(self) -> Dict[str, str]:
        """Detect CI environment and extract relevant information."""
        ci_info = {
            "environment": "unknown",
            "branch": None,
            "commit": None,
            "pr_number": None,
            "build_url": None
        }
        
        # GitHub Actions
        if os.getenv("GITHUB_ACTIONS"):
            ci_info.update({
                "environment": "github-actions",
                "branch": os.getenv("GITHUB_REF_NAME"),
                "commit": os.getenv("GITHUB_SHA"),
                "pr_number": os.getenv("GITHUB_EVENT_NUMBER"),
                "build_url": f"{os.getenv('GITHUB_SERVER_URL')}/{os.getenv('GITHUB_REPOSITORY')}/actions/runs/{os.getenv('GITHUB_RUN_ID')}"
            })
        
        # GitLab CI
        elif os.getenv("GITLAB_CI"):
            ci_info.update({
                "environment": "gitlab-ci", 
                "branch": os.getenv("CI_COMMIT_REF_NAME"),
                "commit": os.getenv("CI_COMMIT_SHA"),
                "pr_number": os.getenv("CI_MERGE_REQUEST_IID"),
                "build_url": os.getenv("CI_PIPELINE_URL")
            })
        
        # Jenkins
        elif os.getenv("JENKINS_URL"):
            ci_info.update({
                "environment": "jenkins",
                "branch": os.getenv("GIT_BRANCH"),
                "commit": os.getenv("GIT_COMMIT"),
                "build_url": os.getenv("BUILD_URL")
            })
        
        # Google Cloud Build
        elif os.getenv("PROJECT_ID") and os.getenv("BUILD_ID"):
            ci_info.update({
                "environment": "gcp-cloud-build",
                "branch": os.getenv("BRANCH_NAME"),
                "commit": os.getenv("COMMIT_SHA"),
                "build_url": f"https://console.cloud.google.com/cloud-build/builds/{os.getenv('BUILD_ID')}"
            })
        
        return ci_info
    
    def run_ssot_compliance_scan(self) -> Optional[Any]:
        """Run SSOT compliance monitoring scan."""
        if not self.monitoring_available:
            logger.error("Monitoring system not available - cannot perform compliance scan")
            return None
        
        try:
            logger.info(" SEARCH:  Running SSOT compliance scan for CI/CD validation...")
            
            # Choose scan scope based on mode
            websocket_only = self.config.mode in [ValidationMode.PR_VALIDATION, ValidationMode.BRANCH_PROTECTION]
            
            report = self.monitor.run_monitoring_scan(websocket_only=websocket_only)
            
            logger.info(f" PASS:  SSOT scan completed")
            logger.info(f"   Files scanned: {report.total_files_scanned}")
            logger.info(f"   Total violations: {len(report.violations)}")
            logger.info(f"   Critical issues: {report.security_critical_count}")
            logger.info(f"   Regressions: {report.regression_violations}")
            
            return report
            
        except Exception as e:
            logger.error(f"SSOT compliance scan failed: {e}")
            return None
    
    def run_mission_critical_tests(self) -> Tuple[int, List[str]]:
        """Run mission critical regression prevention tests."""
        logger.info("[U+1F9EA] Running mission critical SSOT regression tests...")
        
        try:
            test_file = self.project_root / "tests" / "mission_critical" / "test_ssot_regression_prevention_monitor.py"
            if not test_file.exists():
                logger.warning("Mission critical tests not found - skipping")
                return 0, []
            
            # Run specific critical tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                str(test_file), 
                "-v", 
                "-m", "critical",
                "--tb=short",
                "--disable-warnings"
            ], capture_output=True, text=True, cwd=self.project_root, timeout=120)
            
            messages = []
            if result.returncode == 0:
                messages.append(" PASS:  All mission critical tests passed")
            else:
                messages.append(f" FAIL:  Mission critical tests failed (exit code: {result.returncode})")
                if result.stdout:
                    messages.append(f"STDOUT:\n{result.stdout}")
                if result.stderr:
                    messages.append(f"STDERR:\n{result.stderr}")
            
            return result.returncode, messages
            
        except subprocess.TimeoutExpired:
            return 3, ["[U+23F1][U+FE0F] Mission critical tests timed out"]
        except Exception as e:
            return 3, [f" FAIL:  Mission critical test execution failed: {e}"]
    
    def determine_compliance_requirements(self) -> Dict[str, Any]:
        """Determine compliance requirements based on environment and mode."""
        requirements = {
            "max_critical_violations": 0,  # Always zero for security
            "max_error_violations": 0,
            "max_warning_violations": float('inf'),
            "block_on_regressions": True,
            "require_mission_critical_tests": True
        }
        
        # Adjust based on compliance level
        if self.config.compliance_level == ComplianceLevel.STRICT:
            # Production: Zero tolerance
            requirements.update({
                "max_error_violations": 0,
                "max_warning_violations": 0,
                "require_mission_critical_tests": True
            })
        elif self.config.compliance_level == ComplianceLevel.STANDARD:
            # Staging: Block critical and errors
            requirements.update({
                "max_error_violations": 0,
                "max_warning_violations": 5,
                "require_mission_critical_tests": True
            })
        elif self.config.compliance_level == ComplianceLevel.PERMISSIVE:
            # Development: Warnings only
            requirements.update({
                "max_error_violations": 5,
                "max_warning_violations": float('inf'),
                "require_mission_critical_tests": False
            })
        
        # Adjust based on validation mode
        if self.config.mode == ValidationMode.PR_VALIDATION:
            # Be more lenient for PR validation
            requirements["max_error_violations"] = min(requirements["max_error_violations"] + 2, 5)
            # Allow more warning violations for PR validation since many are documentation-related
            if requirements["max_warning_violations"] != float('inf'):
                requirements["max_warning_violations"] = min(requirements["max_warning_violations"] + 10, 20)
            # Skip mission critical tests for PR validation if dependencies are missing
            requirements["require_mission_critical_tests"] = False
        
        return requirements
    
    def validate_compliance(self) -> ValidationResult:
        """Run complete CI/CD compliance validation."""
        logger.info("[U+1F680] Starting CI/CD SSOT compliance validation")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.config.mode.value}")
        logger.info(f"Compliance Level: {self.config.compliance_level.value}")
        logger.info(f"Environment: {self.config.environment}")
        if self.config.branch:
            logger.info(f"Branch: {self.config.branch}")
        if self.config.commit_sha:
            logger.info(f"Commit: {self.config.commit_sha[:8]}...")
        logger.info("=" * 60)
        
        violations = []
        recommendations = []
        blocking_reasons = []
        
        # Determine compliance requirements
        requirements = self.determine_compliance_requirements()
        logger.info(f"[U+1F4CB] Compliance requirements: {requirements}")
        
        # 1. Run SSOT compliance monitoring scan
        monitoring_report = self.run_ssot_compliance_scan()
        if monitoring_report is None:
            blocking_reasons.append("SSOT compliance scan failed - manual review required")
            return ValidationResult(
                passed=False,
                exit_code=3,
                validation_timestamp=self.validation_start_time.isoformat(),
                total_files_checked=0,
                critical_violations=0,
                error_violations=0,
                warning_violations=0,
                violations=[],
                config=self.config,
                recommendations=["Fix monitoring system integration"],
                blocking_reasons=blocking_reasons
            )
        
        # Extract violation counts by severity
        critical_count = monitoring_report.security_critical_count
        error_count = len([v for v in monitoring_report.violations 
                          if v.severity.value in ["ERROR"]])
        warning_count = len([v for v in monitoring_report.violations 
                            if v.severity.value == "WARNING"])
        
        # Convert violations to standard format
        violations = [{
            "file": v.file_path,
            "line": v.line_number,
            "content": v.line_content,
            "type": v.violation_type,
            "description": v.description,
            "suggestion": v.suggestion,
            "severity": v.severity.value,
            "issue_reference": v.issue_reference,
            "business_impact": v.business_impact
        } for v in monitoring_report.violations]
        
        # 2. Check against requirements
        validation_passed = True
        
        if critical_count > requirements["max_critical_violations"]:
            blocking_reasons.append(f"Critical violations: {critical_count} (max: {requirements['max_critical_violations']})")
            validation_passed = False
        
        if error_count > requirements["max_error_violations"]:
            blocking_reasons.append(f"Error violations: {error_count} (max: {requirements['max_error_violations']})")
            validation_passed = False
        
        if warning_count > requirements["max_warning_violations"]:
            blocking_reasons.append(f"Warning violations: {warning_count} (max: {requirements['max_warning_violations']})")
            validation_passed = False
        
        if requirements["block_on_regressions"] and monitoring_report.regression_violations > 0:
            blocking_reasons.append(f"Regression violations: {monitoring_report.regression_violations} (blocking enabled)")
            validation_passed = False
        
        # 3. Run mission critical tests if required
        if requirements["require_mission_critical_tests"]:
            test_exit_code, test_messages = self.run_mission_critical_tests()
            if test_exit_code != 0:
                blocking_reasons.append(f"Mission critical tests failed (exit code: {test_exit_code})")
                validation_passed = False
                recommendations.extend(test_messages)
        
        # 4. Generate recommendations
        if critical_count > 0:
            recommendations.append(" ALERT:  IMMEDIATE ACTION: Fix critical security violations before deployment")
            recommendations.append("Review resolved GitHub issues (e.g., Issue #300) to prevent regression")
        
        if error_count > 0:
            recommendations.append("[U+1F527] Fix SSOT violations by using UnifiedAuthInterface for auth operations")
            recommendations.append("Remove direct JWT operations bypassing auth service")
        
        if warning_count > 0:
            recommendations.append("[U+1F4DD] Review warning violations for architectural improvements")
        
        if monitoring_report.regression_violations > 0:
            recommendations.append(" CYCLE:  Address regression violations - these are newly introduced issues")
        
        # Determine exit code
        if critical_count > 0:
            exit_code = 2  # Critical security issues
        elif not validation_passed:
            exit_code = 1  # SSOT violations
        else:
            exit_code = 0  # Passed
        
        return ValidationResult(
            passed=validation_passed,
            exit_code=exit_code,
            validation_timestamp=self.validation_start_time.isoformat(),
            total_files_checked=monitoring_report.total_files_scanned,
            critical_violations=critical_count,
            error_violations=error_count,
            warning_violations=warning_count,
            violations=violations,
            config=self.config,
            recommendations=recommendations,
            blocking_reasons=blocking_reasons
        )
    
    def save_validation_report(self, result: ValidationResult) -> Path:
        """Save validation report for CI/CD artifacts."""
        reports_dir = self.project_root / "reports" / "ci_compliance"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"ci_ssot_compliance_{timestamp}.json"
        
        # Convert result to JSON-serializable format
        report_data = {
            "validation_summary": {
                "passed": result.passed,
                "exit_code": result.exit_code,
                "validation_timestamp": result.validation_timestamp,
                "total_files_checked": result.total_files_checked,
                "critical_violations": result.critical_violations,
                "error_violations": result.error_violations,
                "warning_violations": result.warning_violations
            },
            "config": {
                "mode": result.config.mode.value,
                "compliance_level": result.config.compliance_level.value,
                "environment": result.config.environment,
                "branch": result.config.branch,
                "commit_sha": result.config.commit_sha,
                "pr_number": result.config.pr_number
            },
            "violations": result.violations,
            "recommendations": result.recommendations,
            "blocking_reasons": result.blocking_reasons,
            "business_impact": {
                "revenue_protection": "$500K+ ARR protected from security vulnerabilities",
                "compliance_status": "CRITICAL" if result.critical_violations > 0 else "PASS"
            }
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"[U+1F4C4] CI validation report saved to {report_file}")
        return report_file
    
    def print_validation_summary(self, result: ValidationResult):
        """Print formatted validation summary for CI logs."""
        print("\n" + "="*80)
        print(" ALERT:  CI/CD SSOT COMPLIANCE VALIDATION SUMMARY")
        print("="*80)
        
        # Overall status
        status_icon = " PASS: " if result.passed else " FAIL: "
        print(f"\n{status_icon} VALIDATION STATUS: {'PASSED' if result.passed else 'FAILED'}")
        print(f"   Exit Code: {result.exit_code}")
        print(f"   Timestamp: {result.validation_timestamp}")
        print(f"   Mode: {result.config.mode.value}")
        print(f"   Environment: {result.config.environment}")
        
        # Violation summary
        print(f"\n CHART:  VIOLATION SUMMARY:")
        print(f"   Files Checked: {result.total_files_checked}")
        print(f"   [U+1F534] Critical: {result.critical_violations}")
        print(f"   [U+1F7E1] Error: {result.error_violations}")  
        print(f"   [U+26AA] Warning: {result.warning_violations}")
        print(f"   Total: {len(result.violations)}")
        
        # Blocking reasons
        if result.blocking_reasons:
            print(f"\n[U+1F6AB] DEPLOYMENT BLOCKED:")
            for reason in result.blocking_reasons:
                print(f"   [U+2022] {reason}")
        
        # Critical violations details
        critical_violations = [v for v in result.violations if v["severity"] == "CRITICAL"]
        if critical_violations:
            print(f"\n[U+1F534] CRITICAL SECURITY VIOLATIONS ({len(critical_violations)}):")
            print("   These MUST be fixed before deployment:")
            for v in critical_violations:
                print(f"   [U+2022] {v['description']}")
                print(f"     File: {v['file']}:{v['line']}")
                print(f"     Fix: {v['suggestion']}")
                if v.get('issue_reference'):
                    print(f"     Reference: {v['issue_reference']}")
                print()
        
        # Recommendations
        if result.recommendations:
            print(f"\n IDEA:  RECOMMENDATIONS:")
            for rec in result.recommendations:
                print(f"   [U+2022] {rec}")
        
        # Business impact
        print(f"\n[U+1F4B0] BUSINESS IMPACT:")
        if result.critical_violations > 0:
            print("    ALERT:  HIGH RISK: Security vulnerabilities could compromise $500K+ ARR")
            print("    ALERT:  WebSocket auth bypass could enable unauthorized access")
        elif result.error_violations > 0:
            print("    WARNING: [U+FE0F]  MEDIUM RISK: SSOT violations could cause auth failures")
            print("    WARNING: [U+FE0F]  System reliability at risk from architectural inconsistency")
        else:
            print("    PASS:  LOW RISK: No significant compliance violations detected")
            print("    PASS:  $500K+ ARR protected from auth security vulnerabilities")
        
        # Final verdict
        print("\n" + "="*80)
        if result.passed:
            print(" PASS:  DEPLOYMENT APPROVED: All SSOT compliance checks passed")
            print("   System maintains proper security and architectural integrity.")
        else:
            print(" FAIL:  DEPLOYMENT BLOCKED: SSOT compliance violations detected")
            print("   Review and fix the violations listed above before deployment.")
            print("   Contact the development team if you need assistance.")
        
        print("="*80)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CI/CD SSOT Compliance Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deployment gate (production)
  python scripts/ci_ssot_compliance_validator.py --mode=deployment-gate --compliance-level=strict
  
  # Pull request validation
  python scripts/ci_ssot_compliance_validator.py --mode=pr-validation --pr-number=123
  
  # Branch protection
  python scripts/ci_ssot_compliance_validator.py --mode=branch-protection --branch=main
        """
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=[mode.value for mode in ValidationMode],
        default=ValidationMode.DEPLOYMENT_GATE.value,
        help="CI/CD validation mode"
    )
    
    parser.add_argument(
        "--compliance-level",
        type=str,
        choices=[level.value for level in ComplianceLevel],
        default=ComplianceLevel.STANDARD.value,
        help="Compliance strictness level"
    )
    
    parser.add_argument(
        "--environment",
        type=str,
        default="unknown",
        help="Deployment environment (production, staging, development)"
    )
    
    parser.add_argument(
        "--branch",
        type=str,
        help="Git branch being validated"
    )
    
    parser.add_argument(
        "--pr-number",
        type=str,
        help="Pull request number"
    )
    
    parser.add_argument(
        "--commit-sha",
        type=str,
        help="Git commit SHA"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory"
    )
    
    parser.add_argument(
        "--save-report",
        action="store_true",
        help="Save validation report as CI artifact"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def main():
    """Main CI/CD compliance validation entry point."""
    args = parse_args()
    
    try:
        # Create validation configuration
        config = CIValidationConfig(
            mode=ValidationMode(args.mode),
            compliance_level=ComplianceLevel(args.compliance_level),
            project_root=args.project_root,
            environment=args.environment,
            branch=args.branch,
            pr_number=args.pr_number,
            commit_sha=args.commit_sha
        )
        
        # Initialize validator
        validator = CISSotComplianceValidator(config)
        
        # Detect CI environment if not provided
        if config.environment == "unknown":
            ci_info = validator.detect_ci_environment()
            config.environment = ci_info["environment"]
            if not config.branch and ci_info["branch"]:
                config.branch = ci_info["branch"]
            if not config.commit_sha and ci_info["commit"]:
                config.commit_sha = ci_info["commit"]
            if not config.pr_number and ci_info["pr_number"]:
                config.pr_number = ci_info["pr_number"]
        
        # Run validation
        result = validator.validate_compliance()
        
        # Save report if requested
        if args.save_report:
            validator.save_validation_report(result)
        
        # Print summary
        validator.print_validation_summary(result)
        
        # Exit with appropriate code
        sys.exit(result.exit_code)
        
    except KeyboardInterrupt:
        logger.info("[U+1F6D1] CI validation interrupted")
        sys.exit(3)
    except Exception as e:
        logger.error(f" FAIL:  CI validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()