#!/usr/bin/env python3
"""
Deployment Configuration Validator
Ensures GCP deployments match the proven working configuration.

Usage:
    python scripts/validate_deployment_config.py --environment staging
    python scripts/validate_deployment_config.py --check-secrets
"""

import os
import sys
import yaml
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional
import argparse

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import io
    try:
        # Only wrap if not already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
    except:
        # If wrapping fails, continue with default encoding
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from deployment.secrets_config import SecretConfig


class DeploymentValidator:
    """Validates deployment configuration against known working setup."""
    
    # Known working configuration from netra-backend-staging-00035-fnj
    WORKING_CONFIG = {
        "environment_vars": {
            "ENVIRONMENT": "staging",
            "PYTHONUNBUFFERED": "1",
            "AUTH_SERVICE_URL": "https://auth.staging.netrasystems.ai",
            "AUTH_SERVICE_ENABLED": "true", 
            "FRONTEND_URL": "https://app.staging.netrasystems.ai",
            "FORCE_HTTPS": "true",
            "GCP_PROJECT_ID": "netra-staging",
            "CLICKHOUSE_HOST": "xedvrr4c3r.us-central1.gcp.clickhouse.cloud",
            "CLICKHOUSE_PORT": "8443",
            "CLICKHOUSE_USER": "default",
            "CLICKHOUSE_DB": "default",
            "CLICKHOUSE_SECURE": "true",
            "WEBSOCKET_CONNECTION_TIMEOUT": "900",
            "WEBSOCKET_HEARTBEAT_INTERVAL": "25",
            "WEBSOCKET_HEARTBEAT_TIMEOUT": "75",
            "WEBSOCKET_CLEANUP_INTERVAL": "180",
            "WEBSOCKET_STALE_TIMEOUT": "900"
        },
        "required_secrets": [
            "postgres-host-staging",
            "postgres-port-staging",
            "postgres-db-staging",
            "postgres-user-staging",
            "postgres-password-staging",
            "redis-host-staging",
            "redis-port-staging",
            "redis-url-staging",
            "redis-password-staging",
            "jwt-secret-staging",
            "jwt-secret-key-staging",
            "secret-key-staging",
            "service-secret-staging",
            "service-id-staging",
            "fernet-key-staging",
            "openai-api-key-staging",
            "anthropic-api-key-staging",
            "gemini-api-key-staging",
            "clickhouse-password-staging"
        ]
    }
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.config_file = self.project_root / "scripts" / "deployment" / f"{environment}_config.yaml"
        self.errors = []
        self.warnings = []
        
    def load_config(self) -> Optional[Dict]:
        """Load deployment configuration file."""
        if not self.config_file.exists():
            self.errors.append(f"Configuration file not found: {self.config_file}")
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load config: {e}")
            return None
            
    def validate_environment_vars(self, config: Dict) -> bool:
        """Validate environment variables match working configuration."""
        print("\n SEARCH:  Validating Environment Variables...")
        
        env_vars = config.get('env_vars', {})
        valid = True
        
        for key, expected_value in self.WORKING_CONFIG['environment_vars'].items():
            if key not in env_vars:
                self.errors.append(f"Missing required env var: {key}")
                valid = False
            elif env_vars[key] != expected_value:
                self.warnings.append(
                    f"Env var {key} differs from working config:\n"
                    f"  Expected: {expected_value}\n"
                    f"  Found: {env_vars[key]}"
                )
                
        # Check for extra env vars not in working config
        for key in env_vars:
            if key not in self.WORKING_CONFIG['environment_vars']:
                self.warnings.append(f"Extra env var not in working config: {key}")
                
        return valid
        
    def validate_secrets(self, config: Dict) -> bool:
        """Validate all required secrets are configured."""
        print("\n[U+1F510] Validating Secrets Configuration...")
        
        secrets = config.get('secrets', {})
        valid = True
        
        # Check each required secret
        for secret_name in self.WORKING_CONFIG['required_secrets']:
            # Convert secret name to env var format (e.g., postgres-host-staging -> POSTGRES_HOST)
            env_var = secret_name.replace('-staging', '').replace('-', '_').upper()
            
            if env_var not in secrets:
                self.errors.append(f"Missing secret mapping: {env_var} -> {secret_name}")
                valid = False
            else:
                expected_ref = f"{secret_name}:latest"
                actual_ref = secrets[env_var]
                if actual_ref != expected_ref:
                    self.warnings.append(
                        f"Secret reference differs:\n"
                        f"  Expected: {env_var} -> {expected_ref}\n"
                        f"  Found: {env_var} -> {actual_ref}"
                    )
                    
        return valid
        
    def check_gcp_secrets(self) -> bool:
        """Check if secrets actually exist in GCP Secret Manager."""
        print("\n[U+2601][U+FE0F] Checking GCP Secret Manager...")
        
        gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        
        try:
            # List all secrets in the project
            result = subprocess.run(
                [gcloud_cmd, "secrets", "list", "--format=json", 
                 "--project", "netra-staging"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                self.warnings.append("Could not list GCP secrets (may need authentication)")
                return True  # Don't fail, just warn
                
            existing_secrets = {s['name'].split('/')[-1] 
                              for s in json.loads(result.stdout)}
            
            # Check each required secret
            missing_secrets = []
            for secret_name in self.WORKING_CONFIG['required_secrets']:
                if secret_name not in existing_secrets:
                    missing_secrets.append(secret_name)
                    
            if missing_secrets:
                self.errors.append(
                    f"Missing secrets in GCP Secret Manager:\n  " + 
                    "\n  ".join(missing_secrets)
                )
                return False
                
            print(f" PASS:  All {len(self.WORKING_CONFIG['required_secrets'])} required secrets exist in GCP")
            return True
            
        except Exception as e:
            self.warnings.append(f"Could not check GCP secrets: {e}")
            return True  # Don't fail on check errors
            
    def validate_cloud_run_config(self, config: Dict) -> bool:
        """Validate Cloud Run configuration settings."""
        print("\n[U+1F680] Validating Cloud Run Configuration...")
        
        cloud_run = config.get('cloud_run', {})
        valid = True
        
        # Check critical settings
        if cloud_run.get('memory', '') not in ['4Gi', '512Mi']:
            self.warnings.append(f"Unusual memory setting: {cloud_run.get('memory')}")
            
        if cloud_run.get('min_instances', 0) < 1:
            self.warnings.append("min_instances < 1 may cause cold starts")
            
        if cloud_run.get('timeout', '') != '900s':
            self.warnings.append(f"Timeout differs from working config: {cloud_run.get('timeout')}")
            
        return valid
        
    def run_validation(self, check_secrets: bool = False) -> bool:
        """Run full validation suite."""
        print(f"\n{'='*60}")
        print(f"[U+1F527] Deployment Configuration Validator")
        print(f"Environment: {self.environment}")
        print(f"Config File: {self.config_file}")
        print(f"{'='*60}")
        
        # Load configuration
        config = self.load_config()
        if not config:
            self.print_results()
            return False
            
        # Run validations
        env_valid = self.validate_environment_vars(config)
        secrets_valid = self.validate_secrets(config)
        cloud_run_valid = self.validate_cloud_run_config(config)
        
        # Optionally check GCP secrets
        gcp_valid = True
        if check_secrets:
            gcp_valid = self.check_gcp_secrets()
            
        # Print results
        self.print_results()
        
        return env_valid and secrets_valid and cloud_run_valid and gcp_valid
        
    def print_results(self):
        """Print validation results."""
        print(f"\n{'='*60}")
        print(" CHART:  Validation Results")
        print(f"{'='*60}")
        
        if self.errors:
            print("\n FAIL:  ERRORS (must fix):")
            for error in self.errors:
                print(f"  [U+2022] {error}")
                
        if self.warnings:
            print("\n WARNING: [U+FE0F] WARNINGS (review):")
            for warning in self.warnings:
                print(f"  [U+2022] {warning}")
                
        if not self.errors and not self.warnings:
            print("\n PASS:  All validations passed!")
            print("Configuration matches the proven working setup.")
            
        print(f"\n{'='*60}")
        
        if self.errors:
            print(" FAIL:  VALIDATION FAILED - Fix errors before deploying")
        else:
            print(" PASS:  VALIDATION PASSED - Safe to deploy")
            
        print(f"{'='*60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate deployment configuration against proven working setup"
    )
    parser.add_argument(
        "--environment",
        default="staging",
        help="Environment to validate (default: staging)"
    )
    parser.add_argument(
        "--check-secrets",
        action="store_true",
        help="Also check if secrets exist in GCP Secret Manager"
    )
    
    args = parser.parse_args()
    
    validator = DeploymentValidator(args.environment)
    success = validator.run_validation(check_secrets=args.check_secrets)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()