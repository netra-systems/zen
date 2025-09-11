#!/usr/bin/env python3
"""
Environment URL Validation Script

PURPOSE: Validate service URLs match expected environment patterns
CONTEXT: CI/CD integration for pre-deployment validation
BUSINESS IMPACT: Prevents localhost URLs from being deployed to staging/production

This script is designed to be run as part of CI/CD pipeline before deployments
to catch environment configuration issues that could break Golden Path functionality.

Usage:
    python scripts/validate_environment_urls.py --environment staging
    python scripts/validate_environment_urls.py --environment production --strict
"""

import argparse
import sys
import os
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.app.core.service_dependencies.service_health_client import ServiceHealthClient
from netra_backend.app.core.service_dependencies.models import ServiceType, EnvironmentType
from netra_backend.app.core.environment_context.cloud_environment_detector import (
    CloudEnvironmentDetector,
    EnvironmentType as DetectorEnvironmentType
)


class ValidationResult(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass
class URLValidationIssue:
    """Represents a URL validation issue."""
    service: str
    url: str
    issue_type: str
    message: str
    severity: ValidationResult


@dataclass
class ValidationReport:
    """Complete validation report."""
    environment: str
    success: bool
    issues: List[URLValidationIssue]
    summary: str


class EnvironmentURLValidator:
    """Validates service URLs for specific environments."""
    
    # Expected URL patterns for each environment
    EXPECTED_URL_PATTERNS = {
        EnvironmentType.DEVELOPMENT: {
            ServiceType.AUTH_SERVICE: r"^http://localhost:8081/?$",
            ServiceType.BACKEND_SERVICE: r"^http://localhost:8000/?$"
        },
        EnvironmentType.STAGING: {
            ServiceType.AUTH_SERVICE: r"^https://auth\.staging\.netrasystems\.ai/?$",
            ServiceType.BACKEND_SERVICE: r"^https://api\.staging\.netrasystems\.ai/?$"
        },
        EnvironmentType.PRODUCTION: {
            ServiceType.AUTH_SERVICE: r"^https://auth\.netrasystems\.ai/?$",
            ServiceType.BACKEND_SERVICE: r"^https://api\.netrasystems\.ai/?$"
        }
    }
    
    # Critical validation rules
    CRITICAL_RULES = {
        "no_localhost_in_cloud": {
            "environments": [EnvironmentType.STAGING, EnvironmentType.PRODUCTION],
            "pattern": r"localhost",
            "message": "localhost URLs not allowed in cloud environments",
            "severity": ValidationResult.FAILURE
        },
        "https_required_cloud": {
            "environments": [EnvironmentType.STAGING, EnvironmentType.PRODUCTION],
            "pattern": r"^http://",
            "message": "HTTPS required for cloud environments",
            "severity": ValidationResult.FAILURE
        },
        "correct_domain_staging": {
            "environments": [EnvironmentType.STAGING],
            "pattern": r"staging\.netrasystems\.ai",
            "message": "staging.netrasystems.ai domain required for staging",
            "severity": ValidationResult.FAILURE,
            "positive_match": True
        },
        "correct_domain_production": {
            "environments": [EnvironmentType.PRODUCTION],
            "pattern": r"netrasystems\.ai",
            "message": "netrasystems.ai domain required for production",
            "severity": ValidationResult.FAILURE,
            "positive_match": True
        }
    }
    
    def __init__(self, environment: EnvironmentType, strict_mode: bool = False):
        """Initialize validator for specific environment.
        
        Args:
            environment: Target environment for validation
            strict_mode: If True, treat warnings as failures
        """
        self.environment = environment
        self.strict_mode = strict_mode
        self.issues: List[URLValidationIssue] = []
        
    def validate_service_urls(self, service_urls: Dict[ServiceType, str]) -> ValidationReport:
        """Validate all service URLs for the environment.
        
        Args:
            service_urls: Dictionary of service type to URL mappings
            
        Returns:
            ValidationReport with detailed results
        """
        self.issues = []
        
        # Validate each service URL
        for service_type, url in service_urls.items():
            self._validate_single_url(service_type, url)
            
        # Generate summary
        failure_count = len([i for i in self.issues if i.severity == ValidationResult.FAILURE])
        warning_count = len([i for i in self.issues if i.severity == ValidationResult.WARNING])
        
        success = failure_count == 0 and (not self.strict_mode or warning_count == 0)
        
        if success:
            summary = f"All service URLs valid for {self.environment.value}"
        else:
            summary = f"Validation failed: {failure_count} failures, {warning_count} warnings"
            
        return ValidationReport(
            environment=self.environment.value,
            success=success,
            issues=self.issues,
            summary=summary
        )
        
    def _validate_single_url(self, service_type: ServiceType, url: str) -> None:
        """Validate a single service URL.
        
        Args:
            service_type: Type of service being validated
            url: URL to validate
        """
        service_name = service_type.value
        
        # Check expected pattern
        expected_patterns = self.EXPECTED_URL_PATTERNS.get(self.environment, {})
        expected_pattern = expected_patterns.get(service_type)
        
        if expected_pattern and not re.match(expected_pattern, url):
            self.issues.append(URLValidationIssue(
                service=service_name,
                url=url,
                issue_type="pattern_mismatch",
                message=f"URL does not match expected pattern for {self.environment.value}",
                severity=ValidationResult.FAILURE
            ))
            
        # Check critical rules
        for rule_name, rule_config in self.CRITICAL_RULES.items():
            if self.environment in rule_config["environments"]:
                pattern = rule_config["pattern"]
                positive_match = rule_config.get("positive_match", False)
                
                if positive_match:
                    # Rule requires pattern to match (e.g., correct domain)
                    if not re.search(pattern, url):
                        self.issues.append(URLValidationIssue(
                            service=service_name,
                            url=url,
                            issue_type=rule_name,
                            message=rule_config["message"],
                            severity=rule_config["severity"]
                        ))
                else:
                    # Rule requires pattern NOT to match (e.g., no localhost)
                    if re.search(pattern, url):
                        self.issues.append(URLValidationIssue(
                            service=service_name,
                            url=url,
                            issue_type=rule_name,
                            message=rule_config["message"],
                            severity=rule_config["severity"]
                        ))


async def validate_environment_urls(environment_name: str, strict_mode: bool = False) -> ValidationReport:
    """Main validation function.
    
    Args:
        environment_name: Name of environment to validate (staging, production, etc.)
        strict_mode: If True, treat warnings as failures
        
    Returns:
        ValidationReport with detailed results
    """
    
    # Map environment name to enum
    environment_map = {
        "development": EnvironmentType.DEVELOPMENT,
        "staging": EnvironmentType.STAGING, 
        "production": EnvironmentType.PRODUCTION,
        "testing": EnvironmentType.TESTING
    }
    
    environment = environment_map.get(environment_name.lower())
    if not environment:
        raise ValueError(f"Unknown environment: {environment_name}")
        
    print(f"Validating service URLs for {environment.value} environment...")
    
    try:
        # Create mock environment context for testing
        from unittest.mock import Mock, patch
        
        # Map to detector environment type
        detector_env_map = {
            EnvironmentType.DEVELOPMENT: DetectorEnvironmentType.DEVELOPMENT,
            EnvironmentType.STAGING: DetectorEnvironmentType.STAGING,
            EnvironmentType.PRODUCTION: DetectorEnvironmentType.PRODUCTION,
            EnvironmentType.TESTING: DetectorEnvironmentType.TESTING
        }
        
        detector_environment = detector_env_map[environment]
        
        # Mock environment context service
        mock_context = Mock()
        mock_context.environment_type = detector_environment
        
        with patch('netra_backend.app.core.service_dependencies.service_health_client.get_environment_context_service') as mock_service:
            mock_service.return_value.is_initialized.return_value = True
            mock_service.return_value.get_environment_context.return_value = mock_context
            
            # Create ServiceHealthClient and get URLs
            service_client = ServiceHealthClient()
            service_urls = service_client.service_urls
            
            print(f"Service URLs for {environment.value}:")
            for service_type, url in service_urls.items():
                print(f"  {service_type.value}: {url}")
            
            # Validate URLs
            validator = EnvironmentURLValidator(environment, strict_mode)
            report = validator.validate_service_urls(service_urls)
            
            return report
            
    except Exception as e:
        # Create error report
        error_issue = URLValidationIssue(
            service="validator",
            url="",
            issue_type="validation_error", 
            message=f"Validation failed with error: {e}",
            severity=ValidationResult.FAILURE
        )
        
        return ValidationReport(
            environment=environment_name,
            success=False,
            issues=[error_issue],
            summary=f"Validation error: {e}"
        )


def print_validation_report(report: ValidationReport) -> None:
    """Print formatted validation report.
    
    Args:
        report: ValidationReport to print
    """
    
    print(f"\n{'='*60}")
    print(f"ENVIRONMENT URL VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"Environment: {report.environment.upper()}")
    print(f"Result: {'✅ PASS' if report.success else '❌ FAIL'}")
    print(f"Summary: {report.summary}")
    
    if report.issues:
        print(f"\nISSUES FOUND ({len(report.issues)}):")
        print("-" * 40)
        
        for i, issue in enumerate(report.issues, 1):
            severity_icon = {
                ValidationResult.SUCCESS: "✅",
                ValidationResult.WARNING: "⚠️", 
                ValidationResult.FAILURE: "❌"
            }[issue.severity]
            
            print(f"{i}. {severity_icon} {issue.severity.value.upper()}")
            print(f"   Service: {issue.service}")
            print(f"   URL: {issue.url}")
            print(f"   Issue: {issue.issue_type}")
            print(f"   Message: {issue.message}")
            print()
    else:
        print("\n✅ No issues found!")
        
    print(f"{'='*60}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Validate service URLs for specific environment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate staging environment
    python scripts/validate_environment_urls.py --environment staging
    
    # Validate production with strict mode (warnings fail)
    python scripts/validate_environment_urls.py --environment production --strict
    
    # Validate development environment
    python scripts/validate_environment_urls.py --environment development
    
This script is designed to catch environment configuration issues before deployment,
specifically preventing localhost URLs from being used in staging/production environments.
"""
    )
    
    parser.add_argument(
        "--environment",
        required=True,
        choices=["development", "staging", "production", "testing"],
        help="Environment to validate"
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: treat warnings as failures"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print summary, not detailed report"
    )
    
    args = parser.parse_args()
    
    try:
        # Run validation
        report = asyncio.run(validate_environment_urls(args.environment, args.strict))
        
        # Print report
        if not args.quiet:
            print_validation_report(report)
        else:
            print(f"{args.environment.upper()}: {'PASS' if report.success else 'FAIL'} - {report.summary}")
        
        # Exit with appropriate code
        sys.exit(0 if report.success else 1)
        
    except Exception as e:
        print(f"❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()