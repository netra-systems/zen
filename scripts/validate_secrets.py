#!/usr/bin/env python3
"""
Validate Secrets Before Deployment
Ensures all required secrets exist and have non-placeholder values.

This script MUST be run before deploying to staging or production.
It implements the canonical secrets management process defined in SPEC/canonical_secrets_management.xml

Business Impact: Prevents deployment failures that cost $5K+ per incident in engineering time.
"""

import subprocess
import sys
import json
import argparse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

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


class Environment(Enum):
    """Deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class SecretDefinition:
    """Definition of a required secret."""
    name: str
    services: List[str]  # Which services need this secret
    required: bool
    allows_placeholder: bool = False
    
    def get_secret_name(self, environment: str) -> str:
        """Get the full secret name for an environment."""
        if environment == "development":
            return self.name  # Development doesn't use suffix
        return f"{self.name}-{environment}"


class SecretsValidator:
    """Validates secrets configuration for deployment."""
    
    # Placeholder values that indicate misconfiguration
    PLACEHOLDER_VALUES = {
        "REPLACE_WITH_ACTUAL_VALUE",
        "REPLACE_WITH_REDIS_PASSWORD",
        "REPLACE_WITH_POSTGRES_PASSWORD",
        "REPLACE_WITH_JWT_SECRET",
        "TODO",
        "CHANGEME",
        "placeholder",
        "development_password",
        "test_password",
        "password",
        "123456",
        "admin"
    }
    
    # Required secrets for each service
    REQUIRED_SECRETS = {
        "backend": [
            # Database
            SecretDefinition("postgres-host", ["backend", "auth"], required=True),
            SecretDefinition("postgres-port", ["backend", "auth"], required=True),
            SecretDefinition("postgres-db", ["backend", "auth"], required=True),
            SecretDefinition("postgres-user", ["backend", "auth"], required=True),
            SecretDefinition("postgres-password", ["backend", "auth"], required=True),
            
            # Redis
            SecretDefinition("redis-url", ["backend", "auth"], required=True),
            SecretDefinition("redis-password", ["backend", "auth"], required=True),
            
            # JWT/Auth
            SecretDefinition("jwt-secret-key", ["backend", "auth"], required=True),
            SecretDefinition("secret-key", ["backend"], required=True),
            SecretDefinition("fernet-key", ["backend"], required=True),
            
            # OAuth
            SecretDefinition("google-oauth-client-id", ["backend", "auth"], required=True),
            SecretDefinition("google-oauth-client-secret", ["backend", "auth"], required=True),
            
            # Service Communication
            SecretDefinition("service-secret", ["backend", "auth"], required=True),
            
            # External APIs
            SecretDefinition("openai-api-key", ["backend"], required=True),
            SecretDefinition("anthropic-api-key", ["backend"], required=True),
            SecretDefinition("gemini-api-key", ["backend"], required=False),
            
            # ClickHouse
            SecretDefinition("clickhouse-host", ["backend"], required=True),
            SecretDefinition("clickhouse-port", ["backend"], required=True),
            SecretDefinition("clickhouse-db", ["backend"], required=True),
            SecretDefinition("clickhouse-user", ["backend"], required=True),
            SecretDefinition("clickhouse-password", ["backend"], required=True),
        ],
        "auth": [
            # Database
            SecretDefinition("postgres-host", ["backend", "auth"], required=True),
            SecretDefinition("postgres-port", ["backend", "auth"], required=True),
            SecretDefinition("postgres-db", ["backend", "auth"], required=True),
            SecretDefinition("postgres-user", ["backend", "auth"], required=True),
            SecretDefinition("postgres-password", ["backend", "auth"], required=True),
            
            # Redis
            SecretDefinition("redis-url", ["backend", "auth"], required=True),
            SecretDefinition("redis-password", ["backend", "auth"], required=True),
            
            # JWT/Auth
            SecretDefinition("jwt-secret-key", ["backend", "auth"], required=True),
            SecretDefinition("jwt-secret", ["auth"], required=True),
            
            # OAuth
            SecretDefinition("google-oauth-client-id", ["backend", "auth"], required=True),
            SecretDefinition("google-oauth-client-secret", ["backend", "auth"], required=True),
            SecretDefinition("oauth-hmac-secret", ["auth"], required=True),
            
            # Service Communication
            SecretDefinition("service-secret", ["backend", "auth"], required=True),
            SecretDefinition("service-id", ["auth"], required=True),
        ]
    }
    
    def __init__(self, environment: Environment, project: str):
        """Initialize validator."""
        self.environment = environment
        self.project = project
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def get_secret_value(self, secret_name: str) -> Optional[str]:
        """Fetch a secret value from GCP Secret Manager."""
        try:
            # Use gcloud.cmd on Windows
            gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
            result = subprocess.run(
                [
                    gcloud_cmd, "secrets", "versions", "access", "latest",
                    f"--secret={secret_name}",
                    f"--project={self.project}"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in Secret Manager."""
        try:
            # Use gcloud.cmd on Windows
            gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
            subprocess.run(
                [
                    gcloud_cmd, "secrets", "describe", secret_name,
                    f"--project={self.project}"
                ],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def validate_secret_value(self, secret_name: str, value: str) -> Tuple[bool, Optional[str]]:
        """Validate a secret value is not a placeholder."""
        if not value:
            return False, "Secret is empty"
        
        # Check for placeholder values
        if value in self.PLACEHOLDER_VALUES:
            return False, f"Secret contains placeholder value: {value}"
        
        # Check for common weak patterns
        if value.lower() in self.PLACEHOLDER_VALUES:
            return False, f"Secret contains weak value: {value}"
        
        # Additional checks for specific secret types
        if "password" in secret_name.lower():
            if len(value) < 8:
                return False, "Password is too short (minimum 8 characters)"
        
        if "api-key" in secret_name.lower():
            if len(value) < 20:
                return False, "API key appears invalid (too short)"
        
        return True, None
    
    def validate_service_secrets(self, service: str) -> bool:
        """Validate all secrets for a service."""
        print(f"\n{'='*60}")
        print(f"Validating {service.upper()} secrets for {self.environment.value}")
        print(f"{'='*60}")
        
        secrets = self.REQUIRED_SECRETS.get(service, [])
        all_valid = True
        
        for secret_def in secrets:
            # Skip if not required for this service
            if service not in secret_def.services:
                continue
            
            secret_name = secret_def.get_secret_name(self.environment.value)
            
            # Check if secret exists
            if not self.check_secret_exists(secret_name):
                if secret_def.required:
                    self.errors.append(f"[{service}] Required secret missing: {secret_name}")
                    print(f" FAIL:  {secret_name}: MISSING (REQUIRED)")
                    all_valid = False
                else:
                    self.warnings.append(f"[{service}] Optional secret missing: {secret_name}")
                    print(f" WARNING: [U+FE0F]  {secret_name}: MISSING (optional)")
                continue
            
            # Get secret value
            value = self.get_secret_value(secret_name)
            if value is None:
                self.errors.append(f"[{service}] Could not read secret: {secret_name}")
                print(f" FAIL:  {secret_name}: UNREADABLE")
                all_valid = False
                continue
            
            # Validate value (don't validate in development)
            if self.environment != Environment.DEVELOPMENT:
                is_valid, error = self.validate_secret_value(secret_name, value)
                if not is_valid:
                    if secret_def.allows_placeholder:
                        self.warnings.append(f"[{service}] {secret_name}: {error}")
                        print(f" WARNING: [U+FE0F]  {secret_name}: {error}")
                    else:
                        self.errors.append(f"[{service}] {secret_name}: {error}")
                        print(f" FAIL:  {secret_name}: {error}")
                        all_valid = False
                else:
                    print(f" PASS:  {secret_name}: Valid")
            else:
                print(f" PASS:  {secret_name}: Exists (development mode)")
        
        return all_valid
    
    def check_deployment_script_mappings(self) -> bool:
        """Verify deployment script has all required mappings."""
        print(f"\n{'='*60}")
        print("Checking deployment script mappings")
        print(f"{'='*60}")
        
        try:
            with open("scripts/deploy_to_gcp.py", "r") as f:
                content = f.read()
            
            all_valid = True
            
            # Check backend mappings
            backend_secrets = set()
            for secret_def in self.REQUIRED_SECRETS["backend"]:
                if "backend" in secret_def.services:
                    env_var = secret_def.name.upper().replace("-", "_")
                    secret_ref = f"{env_var}={secret_def.get_secret_name(self.environment.value)}:latest"
                    
                    if secret_ref not in content:
                        self.errors.append(f"Deployment script missing backend mapping: {secret_ref}")
                        print(f" FAIL:  Backend missing: {env_var}")
                        all_valid = False
                    else:
                        print(f" PASS:  Backend has: {env_var}")
            
            # Check auth mappings
            for secret_def in self.REQUIRED_SECRETS["auth"]:
                if "auth" in secret_def.services:
                    env_var = secret_def.name.upper().replace("-", "_")
                    secret_ref = f"{env_var}={secret_def.get_secret_name(self.environment.value)}:latest"
                    
                    if secret_ref not in content:
                        self.errors.append(f"Deployment script missing auth mapping: {secret_ref}")
                        print(f" FAIL:  Auth missing: {env_var}")
                        all_valid = False
                    else:
                        print(f" PASS:  Auth has: {env_var}")
            
            return all_valid
            
        except FileNotFoundError:
            self.errors.append("Could not find scripts/deploy_to_gcp.py")
            return False
    
    def generate_fix_commands(self) -> List[str]:
        """Generate commands to fix missing or invalid secrets."""
        commands = []
        
        for error in self.errors:
            if "Required secret missing:" in error:
                secret_name = error.split("Required secret missing: ")[1]
                if "password" in secret_name.lower():
                    commands.append(
                        f'python -c "import secrets; print(secrets.token_urlsafe(32))" | '
                        f'gcloud secrets create {secret_name} --data-file=- --project={self.project}'
                    )
                elif "api-key" in secret_name.lower():
                    commands.append(
                        f'echo "REPLACE_WITH_ACTUAL_API_KEY" | '
                        f'gcloud secrets create {secret_name} --data-file=- --project={self.project}'
                    )
                else:
                    commands.append(
                        f'echo "REPLACE_WITH_ACTUAL_VALUE" | '
                        f'gcloud secrets create {secret_name} --data-file=- --project={self.project}'
                    )
            elif "placeholder value" in error or "weak value" in error:
                # Extract secret name from error
                import re
                match = re.search(r'\[.*?\] (.*?):', error)
                if match:
                    secret_name = match.group(1)
                    if "password" in secret_name.lower():
                        commands.append(
                            f'python -c "import secrets; print(secrets.token_urlsafe(32))" | '
                            f'gcloud secrets versions add {secret_name} --data-file=- --project={self.project}'
                        )
        
        return commands
    
    def run_validation(self) -> bool:
        """Run complete validation."""
        print(f"\n{'#'*60}")
        print(f"# SECRETS VALIDATION FOR {self.environment.value.upper()}")
        print(f"# Project: {self.project}")
        print(f"{'#'*60}")
        
        # Validate backend secrets
        backend_valid = self.validate_service_secrets("backend")
        
        # Validate auth secrets
        auth_valid = self.validate_service_secrets("auth")
        
        # Check deployment script mappings
        mappings_valid = self.check_deployment_script_mappings()
        
        # Summary
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        if self.errors:
            print(f"\n FAIL:  ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n WARNING: [U+FE0F]  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors:
            print("\n PASS:  All secrets are properly configured!")
            return True
        else:
            # Generate fix commands
            fix_commands = self.generate_fix_commands()
            if fix_commands:
                print(f"\n[U+1F4DD] FIX COMMANDS:")
                for cmd in fix_commands:
                    print(f"\n{cmd}")
            
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate secrets before deployment")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="staging",
        help="Target environment"
    )
    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix issues automatically"
    )
    
    args = parser.parse_args()
    
    # Create validator
    validator = SecretsValidator(
        environment=Environment(args.environment),
        project=args.project
    )
    
    # Run validation
    is_valid = validator.run_validation()
    
    if not is_valid:
        print("\n FAIL:  Validation failed! Fix the issues before deploying.")
        sys.exit(1)
    else:
        print("\n PASS:  Validation passed! Ready to deploy.")
        sys.exit(0)


if __name__ == "__main__":
    main()