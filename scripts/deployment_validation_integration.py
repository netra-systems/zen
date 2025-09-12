#!/usr/bin/env python3
"""
Deployment Validation Integration

PURPOSE: Integrate environment validation into deployment process
CONTEXT: Process Improvement - Add pre-deployment validation hooks
BUSINESS IMPACT: Prevents environment configuration issues from reaching deployment

This module provides functions to integrate environment validation into existing
deployment scripts without requiring major refactoring.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ValidationResult(Enum):
    """Result of validation check."""
    SUCCESS = "success"
    WARNING = "warning"  
    FAILURE = "failure"


@dataclass
class ValidationCheck:
    """Represents a single validation check."""
    name: str
    command: List[str]
    required: bool = True
    timeout: int = 60
    description: str = ""


@dataclass  
class DeploymentValidationConfig:
    """Configuration for deployment validation."""
    environment: str
    checks: List[ValidationCheck]
    strict_mode: bool = False
    fail_fast: bool = True


class DeploymentValidator:
    """Handles pre-deployment validation checks."""
    
    def __init__(self, environment: str, strict_mode: bool = False):
        """Initialize deployment validator.
        
        Args:
            environment: Target deployment environment
            strict_mode: If True, treat warnings as failures
        """
        self.environment = environment
        self.strict_mode = strict_mode
        self.project_root = Path(__file__).parent.parent
        
    def get_validation_config(self) -> DeploymentValidationConfig:
        """Get validation configuration for the environment.
        
        Returns:
            DeploymentValidationConfig for the environment
        """
        
        # Base validation checks for all environments
        base_checks = [
            ValidationCheck(
                name="Environment URL Validation",
                command=[
                    sys.executable,
                    "scripts/validate_environment_urls.py",
                    "--environment", self.environment
                ],
                required=True,
                timeout=30,
                description=f"Validate service URLs for {self.environment} environment"
            ),
            ValidationCheck(
                name="Environment Detection Tests",
                command=[
                    sys.executable, "-m", "pytest",
                    "tests/pre_deployment/test_environment_url_validation.py",
                    "-v", "--tb=short",
                    "-m", "pre_deployment and environment_validation"
                ],
                required=True,
                timeout=120,
                description="Test environment detection reliability"
            ),
            ValidationCheck(
                name="Service Health URL Tests",
                command=[
                    sys.executable, "-m", "pytest",
                    "tests/pre_deployment/test_environment_url_validation.py::TestServiceHealthClientEnvironmentURLValidation",
                    "-v", "--tb=short"
                ],
                required=True,
                timeout=60,
                description="Test ServiceHealthClient URL mappings"
            )
        ]
        
        # Add environment-specific checks
        if self.environment in ["staging", "production"]:
            base_checks.extend([
                ValidationCheck(
                    name="Critical Configuration Validation",
                    command=[
                        sys.executable, "-m", "pytest",
                        "tests/pre_deployment/test_environment_url_validation.py",
                        "-v", "--tb=short",
                        "-m", "critical"
                    ],
                    required=True,
                    timeout=60,
                    description="Critical configuration checks (no localhost URLs)"
                ),
                ValidationCheck(
                    name="Golden Path Prerequisites",
                    command=[
                        sys.executable, "-m", "pytest", 
                        "tests/pre_deployment/test_environment_url_validation.py::TestGoldenPathEnvironmentIntegration",
                        "-v", "--tb=short"
                    ],
                    required=True,
                    timeout=90,
                    description="Golden Path environment integration tests"
                )
            ])
            
        # Add strict mode flag if enabled
        if self.strict_mode:
            for check in base_checks:
                if check.name == "Environment URL Validation":
                    check.command.append("--strict")
        
        return DeploymentValidationConfig(
            environment=self.environment,
            checks=base_checks,
            strict_mode=self.strict_mode,
            fail_fast=True
        )
    
    def run_validation_check(self, check: ValidationCheck) -> Tuple[bool, str, str]:
        """Run a single validation check.
        
        Args:
            check: ValidationCheck to run
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        
        print(f" SEARCH:  Running: {check.name}")
        if check.description:
            print(f"   {check.description}")
        
        start_time = time.time()
        
        try:
            # Run the validation command
            result = subprocess.run(
                check.command,
                capture_output=True,
                text=True,
                timeout=check.timeout,
                cwd=self.project_root
            )
            
            duration = time.time() - start_time
            success = result.returncode == 0
            
            if success:
                print(f" PASS:  {check.name} passed ({duration:.1f}s)")
            else:
                print(f" FAIL:  {check.name} failed ({duration:.1f}s)")
                
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"[U+23F0] {check.name} timed out after {duration:.1f}s")
            return False, "", f"Command timed out after {check.timeout}s"
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"[U+1F4A5] {check.name} error after {duration:.1f}s: {e}")
            return False, "", str(e)
    
    def run_all_validations(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Run all validation checks for the environment.
        
        Returns:
            Tuple of (all_passed, results_list)
        """
        
        config = self.get_validation_config()
        results = []
        all_passed = True
        
        print(f"\n{'='*60}")
        print(f"PRE-DEPLOYMENT VALIDATION: {self.environment.upper()}")
        print(f"{'='*60}")
        print(f"Running {len(config.checks)} validation checks...")
        if self.strict_mode:
            print(" WARNING: [U+FE0F]  STRICT MODE ENABLED: Warnings will fail deployment")
        print()
        
        for i, check in enumerate(config.checks, 1):
            print(f"[{i}/{len(config.checks)}] {check.name}")
            
            success, stdout, stderr = self.run_validation_check(check)
            
            result = {
                "check": check.name,
                "success": success,
                "required": check.required,
                "stdout": stdout,
                "stderr": stderr,
                "description": check.description
            }
            results.append(result)
            
            # Check if this failure should block deployment
            if not success and check.required:
                all_passed = False
                print(f"[U+1F4A5] REQUIRED check failed: {check.name}")
                
                if config.fail_fast:
                    print("\n ALERT:  FAIL FAST MODE: Stopping validation due to required check failure")
                    break
                    
            elif not success:
                print(f" WARNING: [U+FE0F]  Optional check failed: {check.name}")
                
            print()  # Add spacing between checks
        
        # Print summary
        print(f"{'='*60}")
        print(f"VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        passed_count = len([r for r in results if r["success"]])
        failed_count = len([r for r in results if not r["success"]])
        required_failures = len([r for r in results if not r["success"] and r["required"]])
        
        print(f"Environment: {self.environment.upper()}")
        print(f"Total Checks: {len(results)}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {failed_count}")
        print(f"Required Failures: {required_failures}")
        
        if all_passed:
            print("\n PASS:  ALL VALIDATIONS PASSED")
            print(f"Environment configuration is valid for deployment to {self.environment}")
        else:
            print(f"\n FAIL:  VALIDATION FAILED")
            print(f"Deployment to {self.environment} is BLOCKED due to validation failures")
            
        print(f"{'='*60}")
        
        return all_passed, results
    
    def print_failed_check_details(self, results: List[Dict[str, Any]]) -> None:
        """Print detailed information about failed checks.
        
        Args:
            results: List of validation results
        """
        
        failed_checks = [r for r in results if not r["success"]]
        
        if not failed_checks:
            return
            
        print("\n" + "="*60)
        print("FAILED CHECK DETAILS")
        print("="*60)
        
        for result in failed_checks:
            print(f"\n FAIL:  {result['check']}")
            print(f"   Required: {'Yes' if result['required'] else 'No'}")
            print(f"   Description: {result['description']}")
            
            if result["stderr"]:
                print(f"   Error Output:")
                for line in result["stderr"].split('\n'):
                    if line.strip():
                        print(f"     {line}")
                        
            if result["stdout"]:
                print(f"   Standard Output:")
                for line in result["stdout"].split('\n'):
                    if line.strip():
                        print(f"     {line}")


def run_pre_deployment_validation(environment: str, strict_mode: bool = False) -> bool:
    """Main function to run pre-deployment validation.
    
    Args:
        environment: Target deployment environment
        strict_mode: If True, treat warnings as failures
        
    Returns:
        True if all validations passed, False otherwise
    """
    
    validator = DeploymentValidator(environment, strict_mode)
    all_passed, results = validator.run_all_validations()
    
    if not all_passed:
        validator.print_failed_check_details(results)
        
    return all_passed


def integrate_with_deployment_script(environment: str, strict_mode: bool = False) -> bool:
    """Integration function for existing deployment scripts.
    
    This function can be called from existing deployment scripts like deploy_to_gcp.py
    to add pre-deployment validation without major refactoring.
    
    Args:
        environment: Target deployment environment  
        strict_mode: If True, treat warnings as failures
        
    Returns:
        True if validation passed and deployment should continue, False to abort
        
    Example:
        # In deploy_to_gcp.py
        from scripts.deployment_validation_integration import integrate_with_deployment_script
        
        def deploy(args):
            # Run pre-deployment validation
            if not integrate_with_deployment_script(args.environment, args.strict_validation):
                print("Deployment aborted due to validation failures")
                sys.exit(1)
                
            # Continue with normal deployment...
    """
    
    print("\n" + " SEARCH: " + " "*58 + " SEARCH: ")
    print("  PRE-DEPLOYMENT VALIDATION INTEGRATION")
    print(" SEARCH: " + " "*58 + " SEARCH: ")
    print()
    print("This validation prevents configuration issues like:")
    print("  [U+2022] localhost URLs in staging/production environments")
    print("  [U+2022] Environment detection failures in Cloud Run")
    print("  [U+2022] Service URL misconfigurations")
    print("  [U+2022] Golden Path prerequisite failures")
    print()
    print("These checks protect $500K+ ARR Golden Path functionality.")
    print()
    
    # Run validation
    validation_passed = run_pre_deployment_validation(environment, strict_mode)
    
    if validation_passed:
        print("\n[U+1F680] PRE-DEPLOYMENT VALIDATION PASSED")
        print("   Proceeding with deployment...")
        return True
    else:
        print("\n ALERT:  PRE-DEPLOYMENT VALIDATION FAILED")
        print("   Deployment BLOCKED to prevent environment configuration issues")
        print("\n   This protection prevents issues like:")
        print("     [U+2022] localhost:8081 being used in Cloud Run staging")  
        print("     [U+2022] Environment detection defaulting incorrectly")
        print("     [U+2022] Service health checks failing due to wrong URLs")
        print("     [U+2022] Golden Path validation failures")
        print("\n   Fix the validation issues above and retry deployment.")
        return False


if __name__ == "__main__":
    """CLI for running pre-deployment validation standalone."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run pre-deployment validation checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate staging environment
    python scripts/deployment_validation_integration.py --environment staging
    
    # Validate production with strict mode
    python scripts/deployment_validation_integration.py --environment production --strict
    
    # Integration in deployment scripts:
    from scripts.deployment_validation_integration import integrate_with_deployment_script
    
    if not integrate_with_deployment_script('staging'):
        sys.exit(1)
"""
    )
    
    parser.add_argument(
        "--environment",
        required=True,
        choices=["development", "staging", "production", "testing"],
        help="Target deployment environment"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: treat warnings as failures"
    )
    
    args = parser.parse_args()
    
    # Run validation
    success = run_pre_deployment_validation(args.environment, args.strict)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)