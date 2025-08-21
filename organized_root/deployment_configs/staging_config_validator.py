#!/usr/bin/env python3
"""
Staging Configuration Validator and Alignment Tool
Ensures complete alignment between staging deployment and central config

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero-downtime deployments
- Value Impact: Prevents $15K MRR loss from misconfiguration-related outages
- Strategic Impact: Ensures staging accurately mirrors production for validation
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import subprocess

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from netra_backend.app.core.environment_constants import Environment, EnvironmentVariables
from netra_backend.app.schemas.config import SECRET_CONFIG
from staging_config_alignment import StagingConfigurationManager, StagingDeploymentConfig


class StagingConfigValidator:
    """Validates and aligns staging configuration with central config standards."""
    
    def __init__(self):
        """Initialize validator with configuration manager."""
        self.config_manager = StagingConfigurationManager()
        self.deployment_config = self.config_manager.deployment_config
        self.validation_results = []
        self.alignment_actions = []
        
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validation checks.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check environment constants alignment
        env_errors, env_warnings = self._validate_environment_constants()
        errors.extend(env_errors)
        warnings.extend(env_warnings)
        
        # Check secret configuration alignment
        secret_errors, secret_warnings = self._validate_secret_configuration()
        errors.extend(secret_errors)
        warnings.extend(secret_warnings)
        
        # Check service configuration alignment
        service_errors, service_warnings = self._validate_service_configuration()
        errors.extend(service_errors)
        warnings.extend(service_warnings)
        
        # Check deployment files consistency
        file_errors, file_warnings = self._validate_deployment_files()
        errors.extend(file_errors)
        warnings.extend(file_warnings)
        
        # Check GCP resource alignment
        gcp_errors, gcp_warnings = self._validate_gcp_resources()
        errors.extend(gcp_errors)
        warnings.extend(gcp_warnings)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_environment_constants(self) -> Tuple[List[str], List[str]]:
        """Validate environment constants are properly used."""
        errors = []
        warnings = []
        
        # Check all env vars use constants
        backend_env = self.config_manager.get_backend_env_vars()
        frontend_env = self.config_manager.get_frontend_env_vars()
        auth_env = self.config_manager.get_auth_env_vars()
        
        # Verify ENVIRONMENT value
        for service, env_vars in [("backend", backend_env), ("frontend", frontend_env), ("auth", auth_env)]:
            if env_vars.get("ENVIRONMENT") != Environment.STAGING.value:
                errors.append(f"{service}: ENVIRONMENT must be '{Environment.STAGING.value}'")
        
        # Check for hardcoded values that should use constants
        hardcoded_checks = {
            "staging": "Should use Environment.STAGING.value",
            "development": "Should use Environment.DEVELOPMENT.value",
            "production": "Should use Environment.PRODUCTION.value"
        }
        
        for service, env_vars in [("backend", backend_env), ("frontend", frontend_env), ("auth", auth_env)]:
            for value in env_vars.values():
                if isinstance(value, str):
                    for hardcoded, suggestion in hardcoded_checks.items():
                        if hardcoded in value.lower() and value != Environment.STAGING.value:
                            warnings.append(f"{service}: Value '{value}' contains hardcoded '{hardcoded}'. {suggestion}")
        
        return errors, warnings
    
    def _validate_secret_configuration(self) -> Tuple[List[str], List[str]]:
        """Validate secret configuration matches central config."""
        errors = []
        warnings = []
        
        # Get configured secrets
        backend_secrets = self.config_manager.get_backend_secrets()
        auth_secrets = self.config_manager.get_auth_secrets()
        
        # Parse secret references
        backend_secret_names = [s.split('=')[0] for s in backend_secrets]
        auth_secret_names = [s.split('=')[0] for s in auth_secrets]
        
        # Check required secrets from SECRET_CONFIG
        required_secret_mappings = {
            "JWT_SECRET_KEY": "jwt-secret-key",
            "FERNET_KEY": "fernet-key",
            "GEMINI_API_KEY": "gemini-api-key",
            "LANGFUSE_SECRET_KEY": "langfuse-secret-key",
            "LANGFUSE_PUBLIC_KEY": "langfuse-public-key",
            "GOOGLE_CLIENT_ID": "google-client-id",
            "GOOGLE_CLIENT_SECRET": "google-client-secret",
            "GITHUB_TOKEN": "github-token"
        }
        
        # Validate backend secrets
        for env_name, secret_base in required_secret_mappings.items():
            if env_name in ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]:
                # Auth-only secrets
                if env_name not in auth_secret_names:
                    errors.append(f"Auth service missing required secret: {env_name}")
            elif env_name in ["JWT_SECRET_KEY", "FERNET_KEY"]:
                # Both services need these
                if env_name not in backend_secret_names:
                    errors.append(f"Backend missing required secret: {env_name}")
                if env_name not in auth_secret_names:
                    errors.append(f"Auth service missing required secret: {env_name}")
            else:
                # Backend-only secrets
                if env_name not in backend_secret_names:
                    errors.append(f"Backend missing required secret: {env_name}")
        
        # Check staging suffix convention
        for secret in backend_secrets + auth_secrets:
            if "=latest" not in secret:
                warnings.append(f"Secret reference should use ':latest' version: {secret}")
            
            secret_name = secret.split('=')[1].split(':')[0] if '=' in secret else ""
            if secret_name and not secret_name.endswith("-staging"):
                warnings.append(f"Staging secret should have '-staging' suffix: {secret_name}")
        
        return errors, warnings
    
    def _validate_service_configuration(self) -> Tuple[List[str], List[str]]:
        """Validate service configuration consistency."""
        errors = []
        warnings = []
        
        # Check service names match expected pattern
        expected_services = {
            "backend": "netra-backend-staging",
            "frontend": "netra-frontend-staging",
            "auth": "netra-auth-service"
        }
        
        if self.deployment_config.backend_service != expected_services["backend"]:
            errors.append(f"Backend service name mismatch: {self.deployment_config.backend_service} != {expected_services['backend']}")
        
        if self.deployment_config.frontend_service != expected_services["frontend"]:
            errors.append(f"Frontend service name mismatch: {self.deployment_config.frontend_service} != {expected_services['frontend']}")
        
        if self.deployment_config.auth_service != expected_services["auth"]:
            errors.append(f"Auth service name mismatch: {self.deployment_config.auth_service} != {expected_services['auth']}")
        
        # Check URLs consistency
        if not self.deployment_config.api_url.startswith("https://api.staging."):
            errors.append(f"API URL doesn't follow staging pattern: {self.deployment_config.api_url}")
        
        if not self.deployment_config.frontend_url.startswith("https://app.staging."):
            errors.append(f"Frontend URL doesn't follow staging pattern: {self.deployment_config.frontend_url}")
        
        if not self.deployment_config.auth_url.startswith("https://auth.staging."):
            errors.append(f"Auth URL doesn't follow staging pattern: {self.deployment_config.auth_url}")
        
        # Check WebSocket URL
        if not self.deployment_config.ws_url.startswith("wss://"):
            errors.append(f"WebSocket URL must use WSS: {self.deployment_config.ws_url}")
        
        # Check CORS origins
        backend_env = self.config_manager.get_backend_env_vars()
        cors_origins = backend_env.get("CORS_ORIGINS", "").split(",")
        
        if self.deployment_config.frontend_url not in cors_origins:
            warnings.append(f"Frontend URL not in CORS origins: {self.deployment_config.frontend_url}")
        
        if self.deployment_config.api_url not in cors_origins:
            warnings.append(f"API URL not in CORS origins: {self.deployment_config.api_url}")
        
        return errors, warnings
    
    def _validate_deployment_files(self) -> Tuple[List[str], List[str]]:
        """Validate deployment file consistency."""
        errors = []
        warnings = []
        
        deployment_dir = Path(__file__).parent
        
        # Check staging_deployment_config.json
        config_file = deployment_dir / "staging_deployment_config.json"
        if config_file.exists():
            with open(config_file) as f:
                stored_config = json.load(f)
            
            # Validate stored config matches current
            if stored_config.get("deployment", {}).get("project_id") != self.deployment_config.project_id:
                warnings.append(f"staging_deployment_config.json has outdated project_id")
            
            if stored_config.get("deployment", {}).get("region") != self.deployment_config.region:
                warnings.append(f"staging_deployment_config.json has outdated region")
        else:
            warnings.append("staging_deployment_config.json not found - run export to create")
        
        # Check deploy_staging.py imports config manager
        deploy_script = deployment_dir / "deploy_staging.py"
        if deploy_script.exists():
            with open(deploy_script) as f:
                content = f.read()
            
            if "from staging_config_alignment import StagingConfigurationManager" not in content:
                warnings.append("deploy_staging.py should import StagingConfigurationManager for consistency")
        
        # Check for legacy configuration files
        legacy_files = [
            "config.staging.yaml",
            "staging.env",
            ".env.staging"
        ]
        
        for legacy_file in legacy_files:
            if (deployment_dir / legacy_file).exists():
                warnings.append(f"Legacy configuration file found: {legacy_file} - consider removing")
        
        return errors, warnings
    
    def _validate_gcp_resources(self) -> Tuple[List[str], List[str]]:
        """Validate GCP resource configuration."""
        errors = []
        warnings = []
        
        # Check project ID format
        if not self.deployment_config.project_id:
            errors.append("Project ID is not set")
        
        if not self.deployment_config.project_id_numerical:
            errors.append("Numerical project ID is not set")
        elif not self.deployment_config.project_id_numerical.isdigit():
            errors.append(f"Numerical project ID must be numeric: {self.deployment_config.project_id_numerical}")
        
        # Check region validity
        valid_regions = ["us-central1", "us-east1", "us-west1", "europe-west1", "asia-northeast1"]
        if self.deployment_config.region not in valid_regions:
            warnings.append(f"Unusual region '{self.deployment_config.region}' - common regions: {', '.join(valid_regions)}")
        
        # Check Cloud SQL instance format
        if not self.deployment_config.cloudsql_instance:
            errors.append("Cloud SQL instance is not configured")
        elif ":" not in self.deployment_config.cloudsql_instance:
            errors.append(f"Cloud SQL instance should be in format 'project:region:instance': {self.deployment_config.cloudsql_instance}")
        
        # Check resource limits
        if self.deployment_config.backend_min_instances > self.deployment_config.backend_max_instances:
            errors.append(f"Backend min instances ({self.deployment_config.backend_min_instances}) > max ({self.deployment_config.backend_max_instances})")
        
        if self.deployment_config.frontend_min_instances > self.deployment_config.frontend_max_instances:
            errors.append(f"Frontend min instances ({self.deployment_config.frontend_min_instances}) > max ({self.deployment_config.frontend_max_instances})")
        
        if self.deployment_config.auth_min_instances > self.deployment_config.auth_max_instances:
            errors.append(f"Auth min instances ({self.deployment_config.auth_min_instances}) > max ({self.deployment_config.auth_max_instances})")
        
        # Check auth service always has min 1 instance
        if self.deployment_config.auth_min_instances < 1:
            warnings.append("Auth service should have min_instances >= 1 for availability")
        
        return errors, warnings
    
    def generate_alignment_report(self) -> str:
        """Generate detailed alignment report."""
        is_valid, errors, warnings = self.validate_all()
        
        report = []
        report.append("=" * 60)
        report.append("STAGING CONFIGURATION ALIGNMENT REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 30)
        report.append(f"Status: {'✅ ALIGNED' if is_valid else '❌ MISALIGNED'}")
        report.append(f"Errors: {len(errors)}")
        report.append(f"Warnings: {len(warnings)}")
        report.append("")
        
        # Configuration Overview
        report.append("CONFIGURATION OVERVIEW")
        report.append("-" * 30)
        report.append(f"Project ID: {self.deployment_config.project_id}")
        report.append(f"Region: {self.deployment_config.region}")
        report.append(f"Backend Service: {self.deployment_config.backend_service}")
        report.append(f"Frontend Service: {self.deployment_config.frontend_service}")
        report.append(f"Auth Service: {self.deployment_config.auth_service}")
        report.append("")
        
        # Errors
        if errors:
            report.append("ERRORS (Must Fix)")
            report.append("-" * 30)
            for i, error in enumerate(errors, 1):
                report.append(f"{i}. {error}")
            report.append("")
        
        # Warnings
        if warnings:
            report.append("WARNINGS (Should Review)")
            report.append("-" * 30)
            for i, warning in enumerate(warnings, 1):
                report.append(f"{i}. {warning}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 30)
        
        if not is_valid:
            report.append("1. Fix all errors before deploying to staging")
            report.append("2. Run 'python staging_config_alignment.py' to export aligned config")
            report.append("3. Update deploy_staging.py to use StagingConfigurationManager")
        else:
            report.append("1. Configuration is aligned and ready for deployment")
            report.append("2. Consider addressing warnings for better maintainability")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def auto_align(self) -> bool:
        """Attempt to automatically align configuration.
        
        Returns:
            True if alignment was successful
        """
        print("Starting automatic configuration alignment...")
        
        # Export aligned configuration
        output_file = Path(__file__).parent / "staging_deployment_config.json"
        self.config_manager.export_configuration(output_file)
        print(f"✅ Exported aligned configuration to {output_file}")
        
        # Validate after alignment
        is_valid, errors, warnings = self.validate_all()
        
        if is_valid:
            print("✅ Configuration successfully aligned")
        else:
            print(f"⚠️ Configuration aligned but {len(errors)} errors remain")
        
        return is_valid


def main():
    """Main entry point for validator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate and align staging configuration")
    parser.add_argument("--auto-align", action="store_true", help="Automatically align configuration")
    parser.add_argument("--json", action="store_true", help="Output report as JSON")
    args = parser.parse_args()
    
    validator = StagingConfigValidator()
    
    if args.auto_align:
        success = validator.auto_align()
        sys.exit(0 if success else 1)
    
    # Generate report
    if args.json:
        is_valid, errors, warnings = validator.validate_all()
        result = {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "deployment_config": asdict(validator.deployment_config)
        }
        print(json.dumps(result, indent=2))
    else:
        report = validator.generate_alignment_report()
        print(report)
    
    # Exit with error code if not valid
    is_valid, _, _ = validator.validate_all()
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()