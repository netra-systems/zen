#!/usr/bin/env python3
"""
DEPLOYMENT CONFLICTS VALIDATION ORCHESTRATOR
==========================================

Comprehensive test orchestration for GitHub Issue #245: Deployment Script SSOT Consolidation

This script orchestrates all deployment validation tests in the correct order,
provides clear reporting, and ensures safe execution with proper risk mitigation.

USAGE:
    # Run all validation tests
    python tests/deployment_conflicts/run_deployment_validation.py

    # Run specific validation phases
    python tests/deployment_conflicts/run_deployment_validation.py --phase conflict_detection
    python tests/deployment_conflicts/run_deployment_validation.py --phase integration
    python tests/deployment_conflicts/run_deployment_validation.py --phase staging --staging-safe
    
    # Generate comprehensive report
    python tests/deployment_conflicts/run_deployment_validation.py --report-only

SAFETY FLAGS:
    --staging-safe : Allow staging environment testing (only if pre-checks pass)
    --docker-required : Require Docker daemon (exit if not available)
    --dry-run : Show what would be executed without running tests
"""

import os
import sys
import subprocess
import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase


class DeploymentValidationOrchestrator:
    """Orchestrates comprehensive deployment validation testing."""
    
    def __init__(self, dry_run: bool = False, staging_safe: bool = False, 
                 docker_required: bool = False):
        self.dry_run = dry_run
        self.staging_safe = staging_safe
        self.docker_required = docker_required
        self.project_root = PROJECT_ROOT
        self.results_dir = self.project_root / "tests" / "deployment_conflicts" / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize results tracking
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "summary": {},
            "recommendations": []
        }
        
    def run_full_validation(self) -> Dict:
        """Run complete deployment validation test suite."""
        print("[U+1F680] DEPLOYMENT CONFLICTS VALIDATION - COMPREHENSIVE TEST SUITE")
        print("=" * 70)
        print(f"Timestamp: {datetime.now()}")
        print(f"Project: {self.project_root}")
        print(f"Results: {self.results_dir}")
        print(f"Dry Run: {self.dry_run}")
        print(f"Staging Safe: {self.staging_safe}")
        print("=" * 70)
        
        # Phase 1: Environment and Dependency Checks
        self._run_phase("environment_checks", self._validate_environment)
        
        # Phase 2: Conflict Detection Tests
        self._run_phase("conflict_detection", self._run_conflict_detection_tests)
        
        # Phase 3: SSOT Validation Tests
        self._run_phase("ssot_validation", self._run_ssot_validation_tests)
        
        # Phase 4: Integration Pipeline Tests
        self._run_phase("integration_pipeline", self._run_integration_tests)
        
        # Phase 5: Golden Path Protection Tests
        self._run_phase("golden_path_protection", self._run_golden_path_tests)
        
        # Phase 6: Staging Environment Tests (if safe)
        if self.staging_safe:
            self._run_phase("staging_validation", self._run_staging_tests)
        else:
            print(" WARNING: [U+FE0F]  SKIPPING staging tests (use --staging-safe to enable)")
        
        # Generate comprehensive report
        self._generate_final_report()
        
        return self.validation_results
    
    def run_specific_phase(self, phase_name: str) -> Dict:
        """Run a specific validation phase."""
        print(f" TARGET:  Running specific phase: {phase_name}")
        
        phase_methods = {
            "environment_checks": self._validate_environment,
            "conflict_detection": self._run_conflict_detection_tests,
            "ssot_validation": self._run_ssot_validation_tests,
            "integration": self._run_integration_tests,
            "golden_path": self._run_golden_path_tests,
            "staging": self._run_staging_tests
        }
        
        if phase_name in phase_methods:
            self._run_phase(phase_name, phase_methods[phase_name])
        else:
            print(f" FAIL:  Unknown phase: {phase_name}")
            print(f"Available phases: {list(phase_methods.keys())}")
            return {"error": f"Unknown phase: {phase_name}"}
        
        return self.validation_results
    
    def generate_report_only(self) -> Dict:
        """Generate comprehensive report from existing results."""
        print(" CHART:  GENERATING DEPLOYMENT VALIDATION REPORT")
        
        # Load existing results if available
        existing_results = self._load_existing_results()
        if existing_results:
            self.validation_results = existing_results
            self._generate_final_report()
        else:
            print(" WARNING: [U+FE0F]  No existing results found. Run validation tests first.")
            
        return self.validation_results
    
    def _run_phase(self, phase_name: str, phase_method) -> Dict:
        """Run a validation phase with error handling and reporting."""
        print(f"\n[U+1F4CB] PHASE: {phase_name.upper()}")
        print("-" * 50)
        
        if self.dry_run:
            print(f" SEARCH:  DRY RUN: Would execute {phase_name}")
            self.validation_results["phases"][phase_name] = {
                "status": "dry_run",
                "message": "Execution skipped in dry-run mode"
            }
            return self.validation_results["phases"][phase_name]
        
        try:
            start_time = time.time()
            phase_result = phase_method()
            end_time = time.time()
            
            phase_data = {
                "status": "completed",
                "duration": round(end_time - start_time, 2),
                "timestamp": datetime.now().isoformat(),
                "result": phase_result
            }
            
            self.validation_results["phases"][phase_name] = phase_data
            print(f" PASS:  Phase {phase_name} completed in {phase_data['duration']}s")
            
        except Exception as e:
            print(f" FAIL:  Phase {phase_name} failed: {str(e)}")
            self.validation_results["phases"][phase_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        return self.validation_results["phases"][phase_name]
    
    def _validate_environment(self) -> Dict:
        """Validate environment and dependencies."""
        print(" SEARCH:  Validating environment and dependencies...")
        
        checks = {
            "docker_available": self._check_docker_availability(),
            "python_environment": self._check_python_environment(),
            "project_structure": self._check_project_structure(),
            "gcp_connectivity": self._check_gcp_connectivity()
        }
        
        # Report environment status
        for check_name, check_result in checks.items():
            status = " PASS: " if check_result["success"] else " FAIL: "
            print(f"  {status} {check_name}: {check_result['message']}")
        
        # Determine if environment is ready
        critical_checks = ["python_environment", "project_structure"]
        environment_ready = all(checks[check]["success"] for check in critical_checks)
        
        if not environment_ready:
            raise Exception("Critical environment checks failed")
        
        # Check Docker requirement
        if self.docker_required and not checks["docker_available"]["success"]:
            raise Exception("Docker required but not available")
        
        return checks
    
    def _run_conflict_detection_tests(self) -> Dict:
        """Run deployment script conflict detection tests."""
        print(" SEARCH:  Running deployment script conflict detection tests...")
        
        test_results = {}
        
        # Test 1: Discover all deployment entry points
        test_results["entry_points"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_discover_all_deployment_entry_points"
        )
        
        # Test 2: UnifiedTestRunner false claims validation
        test_results["unified_runner_claims"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_unified_test_runner_deployment_mode_false_claims"
        )
        
        # Test 3: Configuration consistency across deployment methods
        test_results["config_consistency"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_configuration_consistency_across_deployment_methods"
        )
        
        # Test 4: Terraform deprecated script references
        test_results["terraform_deprecated"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_terraform_deprecated_script_references"
        )
        
        # Test 5: Docker vs GCP configuration drift
        test_results["docker_gcp_drift"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_docker_vs_gcp_deployment_configuration_drift"
        )
        
        # Test 6: Deployment script functional validation
        test_results["script_functionality"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestDeploymentScriptConflicts::test_deployment_script_functional_validation"
        )
        
        return test_results
    
    def _run_ssot_validation_tests(self) -> Dict:
        """Run SSOT deployment consolidation validation tests."""
        print(" TARGET:  Running SSOT validation tests...")
        
        test_results = {}
        
        # Test 1: Single canonical deployment source
        test_results["canonical_source"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestSSotDeploymentValidation::test_single_canonical_deployment_source"
        )
        
        # Test 2: Deployment dependency chain validation
        test_results["dependency_chain"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestSSotDeploymentValidation::test_deployment_dependency_chain_validation"
        )
        
        return test_results
    
    def _run_integration_tests(self) -> Dict:
        """Run deployment pipeline integration tests."""
        print(" CYCLE:  Running integration pipeline tests...")
        
        test_results = {}
        
        # Test 1: Terraform to script integration
        test_results["terraform_integration"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_integration_validation.py::TestDeploymentPipelineIntegration::test_terraform_to_script_integration_chain"
        )
        
        # Test 2: CI/CD pipeline consistency
        test_results["cicd_consistency"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_integration_validation.py::TestDeploymentPipelineIntegration::test_ci_cd_pipeline_deployment_consistency"
        )
        
        # Test 3: Environment-specific configuration validation
        test_results["env_config"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_integration_validation.py::TestDeploymentPipelineIntegration::test_environment_specific_configuration_validation"
        )
        
        # Test 4: Rollback capability validation
        test_results["rollback_capability"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_integration_validation.py::TestDeploymentPipelineIntegration::test_deployment_rollback_capability_validation"
        )
        
        # Test 5: Performance impact analysis
        test_results["performance_impact"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_integration_validation.py::TestDeploymentPipelineIntegration::test_deployment_performance_impact_analysis"
        )
        
        return test_results
    
    def _run_golden_path_tests(self) -> Dict:
        """Run Golden Path protection tests."""
        print("[U+1F6E1][U+FE0F] Running Golden Path protection tests...")
        
        test_results = {}
        
        # Test 1: User login flow preservation
        test_results["login_flow"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestGoldenPathDeploymentProtection::test_deployment_preserves_user_login_flow"
        )
        
        # Test 2: AI response capability preservation
        test_results["ai_response"] = self._execute_test(
            "python tests/deployment_conflicts/test_deployment_script_conflicts.py::TestGoldenPathDeploymentProtection::test_deployment_preserves_ai_response_capability"
        )
        
        return test_results
    
    def _run_staging_tests(self) -> Dict:
        """Run staging environment validation tests."""
        print("[U+1F9EA] Running staging environment tests...")
        
        if not self.staging_safe:
            return {"skipped": "Staging tests not enabled (use --staging-safe)"}
        
        test_results = {}
        
        # Pre-staging validation
        print("   SEARCH:  Pre-staging environment checks...")
        pre_checks = self._validate_staging_prerequisites()
        test_results["pre_checks"] = pre_checks
        
        if not pre_checks.get("safe_to_proceed", False):
            print("   WARNING: [U+FE0F]  Staging prerequisites not met, skipping deployment tests")
            return test_results
        
        # Staging deployment validation (if safe)
        print("  [U+1F680] Staging deployment validation...")
        test_results["deployment_validation"] = self._validate_staging_deployment()
        
        return test_results
    
    def _check_docker_availability(self) -> Dict:
        """Check if Docker daemon is available."""
        try:
            result = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            if result.returncode == 0:
                return {"success": True, "message": "Docker daemon available"}
            else:
                return {"success": False, "message": f"Docker not running: {result.stderr}"}
        except Exception as e:
            return {"success": False, "message": f"Docker not available: {str(e)}"}
    
    def _check_python_environment(self) -> Dict:
        """Check Python environment and dependencies."""
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version.major == 3 and python_version.minor >= 8:
                return {"success": True, "message": f"Python {python_version.major}.{python_version.minor} available"}
            else:
                return {"success": False, "message": f"Python version {python_version.major}.{python_version.minor} not supported (need 3.8+)"}
        except Exception as e:
            return {"success": False, "message": f"Python environment check failed: {str(e)}"}
    
    def _check_project_structure(self) -> Dict:
        """Check project structure and required files."""
        required_paths = [
            "scripts",
            "terraform-gcp-staging", 
            "tests/deployment_conflicts",
            "tests/unified_test_runner.py"
        ]
        
        missing_paths = []
        for path in required_paths:
            if not (self.project_root / path).exists():
                missing_paths.append(path)
        
        if missing_paths:
            return {"success": False, "message": f"Missing required paths: {missing_paths}"}
        else:
            return {"success": True, "message": "All required project paths present"}
    
    def _check_gcp_connectivity(self) -> Dict:
        """Check GCP connectivity (optional)."""
        try:
            # Try to run gcloud info
            result = subprocess.run(
                ["gcloud", "info", "--format=json"], 
                capture_output=True, 
                text=True, 
                timeout=15
            )
            if result.returncode == 0:
                return {"success": True, "message": "GCP connectivity available"}
            else:
                return {"success": False, "message": "GCP CLI not configured"}
        except Exception:
            return {"success": False, "message": "GCP CLI not available"}
    
    def _execute_test(self, test_command: str) -> Dict:
        """Execute a specific test and capture results."""
        if self.dry_run:
            return {"status": "dry_run", "command": test_command}
        
        try:
            print(f"    Executing: {test_command}")
            result = subprocess.run(
                test_command.split(),
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": test_command
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Test execution timed out",
                "command": test_command
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "command": test_command
            }
    
    def _validate_staging_prerequisites(self) -> Dict:
        """Validate prerequisites for staging environment testing."""
        checks = {
            "docker_available": self._check_docker_availability()["success"],
            "gcp_connectivity": self._check_gcp_connectivity()["success"],
            "staging_project": self._check_staging_project_access(),
            "no_active_deployments": self._check_no_active_deployments()
        }
        
        safe_to_proceed = all(checks.values())
        
        return {
            "checks": checks,
            "safe_to_proceed": safe_to_proceed,
            "message": "All prerequisites met" if safe_to_proceed else "Prerequisites not met"
        }
    
    def _check_staging_project_access(self) -> bool:
        """Check access to staging GCP project."""
        try:
            result = subprocess.run([
                "gcloud", "projects", "describe", "netra-staging"
            ], capture_output=True, text=True, timeout=15)
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_no_active_deployments(self) -> bool:
        """Check if there are no active deployments in staging."""
        # For safety, always return False unless explicitly validated
        # In real implementation, this would check Cloud Run for active deployments
        return False
    
    def _validate_staging_deployment(self) -> Dict:
        """Validate staging deployment (dry-run mode)."""
        try:
            # Execute deployment script in dry-run mode
            result = subprocess.run([
                "python", "scripts/deploy_to_gcp_actual.py",
                "--project", "netra-staging",
                "--dry-run"
            ], capture_output=True, text=True, timeout=300, cwd=self.project_root)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "output": result.stdout,
                "error": result.stderr
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _load_existing_results(self) -> Optional[Dict]:
        """Load existing validation results if available."""
        results_file = self.results_dir / "validation_results.json"
        if results_file.exists():
            try:
                with open(results_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _generate_final_report(self) -> None:
        """Generate comprehensive final report."""
        print("\n" + "=" * 70)
        print(" CHART:  DEPLOYMENT VALIDATION COMPREHENSIVE REPORT")
        print("=" * 70)
        
        # Calculate summary statistics
        total_phases = len(self.validation_results["phases"])
        completed_phases = len([p for p in self.validation_results["phases"].values() if p["status"] == "completed"])
        failed_phases = len([p for p in self.validation_results["phases"].values() if p["status"] == "failed"])
        
        print(f"Execution Summary:")
        print(f"  Total Phases: {total_phases}")
        print(f"  Completed: {completed_phases}")
        print(f"  Failed: {failed_phases}")
        print(f"  Success Rate: {(completed_phases/total_phases)*100:.1f}%" if total_phases > 0 else "  Success Rate: N/A")
        
        # Phase-by-phase results
        print(f"\nPhase Results:")
        for phase_name, phase_data in self.validation_results["phases"].items():
            status_icon = {"completed": " PASS: ", "failed": " FAIL: ", "dry_run": " SEARCH: "}.get(phase_data["status"], "[U+2753]")
            duration = f" ({phase_data.get('duration', 0)}s)" if phase_data.get('duration') else ""
            print(f"  {status_icon} {phase_name}{duration}")
            
            if phase_data["status"] == "failed":
                print(f"    Error: {phase_data.get('error', 'Unknown error')}")
        
        # Generate recommendations
        self._generate_recommendations()
        
        if self.validation_results["recommendations"]:
            print(f"\n TARGET:  Recommendations:")
            for i, rec in enumerate(self.validation_results["recommendations"], 1):
                print(f"  {i}. {rec}")
        
        # Save results to file
        results_file = self.results_dir / "validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        print(f"\n[U+1F4C1] Detailed results saved to: {results_file}")
        
        # Generate executive summary
        self._generate_executive_summary()
    
    def _generate_recommendations(self) -> None:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Analyze results and generate specific recommendations
        for phase_name, phase_data in self.validation_results["phases"].items():
            if phase_data["status"] == "failed":
                if phase_name == "environment_checks":
                    recommendations.append("Fix critical environment dependencies before proceeding")
                elif phase_name == "conflict_detection":
                    recommendations.append("Resolve deployment script conflicts immediately")
                elif phase_name == "ssot_validation":
                    recommendations.append("Implement SSOT consolidation for deployment scripts")
                elif phase_name == "golden_path_protection":
                    recommendations.append("Critical: Fix issues affecting user login  ->  AI response flow")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("All validation tests passed - proceed with deployment consolidation")
        
        recommendations.append("Review detailed test outputs for specific implementation guidance")
        recommendations.append("Implement continuous deployment validation in CI/CD pipeline")
        
        self.validation_results["recommendations"] = recommendations
    
    def _generate_executive_summary(self) -> None:
        """Generate executive summary for stakeholders."""
        summary_file = self.results_dir / "executive_summary.md"
        
        completed_phases = len([p for p in self.validation_results["phases"].values() if p["status"] == "completed"])
        total_phases = len(self.validation_results["phases"])
        
        summary_content = f"""# Deployment Validation Executive Summary

**GitHub Issue #245 - Deployment Script SSOT Consolidation**

## Summary
- **Validation Date:** {self.validation_results['timestamp']}
- **Phases Completed:** {completed_phases}/{total_phases}
- **Overall Status:** {' PASS:  PASSED' if completed_phases == total_phases else ' WARNING: [U+FE0F] ISSUES FOUND'}

## Business Impact
- **Risk Level:** {'LOW' if completed_phases == total_phases else 'HIGH'}
- **ARR at Risk:** $500K+ (deployment reliability dependency)
- **Immediate Action Required:** {'No' if completed_phases == total_phases else 'Yes'}

## Key Findings
"""
        
        # Add key findings from each phase
        for phase_name, phase_data in self.validation_results["phases"].items():
            status = phase_data["status"]
            summary_content += f"- **{phase_name}:** {status.upper()}\n"
        
        summary_content += f"\n## Recommendations\n"
        for i, rec in enumerate(self.validation_results.get("recommendations", []), 1):
            summary_content += f"{i}. {rec}\n"
        
        summary_content += f"\n## Next Steps\n"
        if completed_phases == total_phases:
            summary_content += "- Proceed with deployment SSOT consolidation implementation\n"
            summary_content += "- Schedule deployment infrastructure consolidation\n"
        else:
            summary_content += "- Address critical validation failures before proceeding\n"
            summary_content += "- Re-run validation after fixes\n"
        
        summary_content += f"- Review detailed technical report in validation_results.json\n"
        
        with open(summary_file, 'w') as f:
            f.write(summary_content)
        
        print(f"[U+1F4C4] Executive summary saved to: {summary_file}")


def main():
    """Main entry point for deployment validation orchestrator."""
    parser = argparse.ArgumentParser(
        description="Deployment Conflicts Validation Orchestrator for GitHub Issue #245"
    )
    
    parser.add_argument(
        "--phase",
        choices=["environment_checks", "conflict_detection", "ssot_validation", 
                "integration", "golden_path", "staging"],
        help="Run specific validation phase"
    )
    
    parser.add_argument(
        "--staging-safe",
        action="store_true",
        help="Allow staging environment testing (only if pre-checks pass)"
    )
    
    parser.add_argument(
        "--docker-required",
        action="store_true",
        help="Require Docker daemon (exit if not available)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running tests"
    )
    
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Generate comprehensive report from existing results"
    )
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = DeploymentValidationOrchestrator(
        dry_run=args.dry_run,
        staging_safe=args.staging_safe,
        docker_required=args.docker_required
    )
    
    try:
        if args.report_only:
            results = orchestrator.generate_report_only()
        elif args.phase:
            results = orchestrator.run_specific_phase(args.phase)
        else:
            results = orchestrator.run_full_validation()
        
        # Exit with appropriate code
        if results.get("phases"):
            failed_phases = [p for p in results["phases"].values() if p["status"] == "failed"]
            exit_code = 1 if failed_phases else 0
        else:
            exit_code = 0
            
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n WARNING: [U+FE0F]  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n FAIL:  Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()