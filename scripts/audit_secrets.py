#!/usr/bin/env python3
"""
Automated Secrets Audit Script
Comprehensive audit of secrets across all environments and services.

This script performs a full audit of the secrets management system including:
- Secret existence and validity
- Environment variable mappings
- Cloud Run configurations
- Code references
- Security compliance

Run this regularly (e.g., in CI/CD) to ensure secrets remain properly configured.
"""

import subprocess
import json
import os
import re
import argparse
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, field
import hashlib


@dataclass
class SecretAuditResult:
    """Results from a secret audit."""
    secret_name: str
    environment: str
    exists_in_secret_manager: bool = False
    has_valid_value: bool = False
    mapped_in_deployment: bool = False
    mapped_in_cloud_run: bool = False
    referenced_in_code: bool = False
    last_rotation_date: Optional[str] = None
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def is_healthy(self) -> bool:
        """Check if secret is fully healthy."""
        return (
            self.exists_in_secret_manager and
            self.has_valid_value and
            self.mapped_in_deployment and
            self.mapped_in_cloud_run and
            not self.issues
        )


class SecretsAuditor:
    """Comprehensive secrets auditing system."""
    
    def __init__(self, project: str, environment: str = "staging"):
        """Initialize auditor."""
        self.project = project
        self.environment = environment
        self.results: Dict[str, SecretAuditResult] = {}
        self.code_base = Path(".")
        
    def run_full_audit(self) -> Tuple[bool, Dict[str, SecretAuditResult]]:
        """Run complete audit of all secrets."""
        print(f"\n{'='*80}")
        print(f"SECRETS AUDIT REPORT - {datetime.now().isoformat()}")
        print(f"Project: {self.project} | Environment: {self.environment}")
        print(f"{'='*80}")
        
        # Phase 1: Discover all secrets
        print("\n[Phase 1] Discovering secrets...")
        all_secrets = self.discover_all_secrets()
        print(f"  Found {len(all_secrets)} unique secrets")
        
        # Phase 2: Audit Secret Manager
        print("\n[Phase 2] Auditing Secret Manager...")
        self.audit_secret_manager(all_secrets)
        
        # Phase 3: Audit deployment scripts
        print("\n[Phase 3] Auditing deployment scripts...")
        self.audit_deployment_scripts(all_secrets)
        
        # Phase 4: Audit Cloud Run services
        print("\n[Phase 4] Auditing Cloud Run services...")
        self.audit_cloud_run_services(all_secrets)
        
        # Phase 5: Audit code references
        print("\n[Phase 5] Auditing code references...")
        self.audit_code_references(all_secrets)
        
        # Phase 6: Security compliance
        print("\n[Phase 6] Checking security compliance...")
        self.check_security_compliance(all_secrets)
        
        # Generate report
        return self.generate_report()
    
    def discover_all_secrets(self) -> Set[str]:
        """Discover all secrets referenced anywhere in the system."""
        secrets = set()
        
        # From canonical specification
        canonical_secrets = [
            "postgres-host", "postgres-port", "postgres-db", "postgres-user", "postgres-password",
            "redis-url", "redis-password",
            "jwt-secret-key", "jwt-secret", "secret-key", "session-secret-key",
            "google-oauth-client-id", "google-oauth-client-secret", "oauth-hmac-secret",
            "service-secret", "service-id", "fernet-key",
            "openai-api-key", "anthropic-api-key", "gemini-api-key",
            "clickhouse-host", "clickhouse-port", "clickhouse-db", 
            "clickhouse-user", "clickhouse-password", "clickhouse-url"
        ]
        
        for secret in canonical_secrets:
            secret_name = f"{secret}-{self.environment}" if self.environment != "development" else secret
            secrets.add(secret_name)
            self.results[secret_name] = SecretAuditResult(
                secret_name=secret_name,
                environment=self.environment
            )
        
        # From Secret Manager
        try:
            result = subprocess.run(
                ["gcloud", "secrets", "list", f"--project={self.project}", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            gcp_secrets = json.loads(result.stdout)
            for secret in gcp_secrets:
                name = secret["name"].split("/")[-1]
                if name not in self.results:
                    self.results[name] = SecretAuditResult(
                        secret_name=name,
                        environment=self.environment
                    )
                secrets.add(name)
        except Exception as e:
            print(f"  Warning: Could not list GCP secrets: {e}")
        
        # From code (environment variable references)
        env_pattern = re.compile(r'(?:get|getenv|environ\.get|env\.get)\(["\']([A-Z_]+)["\']')
        for py_file in self.code_base.rglob("*.py"):
            try:
                content = py_file.read_text()
                for match in env_pattern.findall(content):
                    # Convert to secret name format
                    if match.startswith(("POSTGRES_", "REDIS_", "JWT_", "OAUTH_", 
                                       "CLICKHOUSE_", "SERVICE_", "OPENAI_", 
                                       "ANTHROPIC_", "GEMINI_", "FERNET_")):
                        secret_name = match.lower().replace("_", "-")
                        if self.environment != "development":
                            secret_name = f"{secret_name}-{self.environment}"
                        if secret_name not in self.results:
                            self.results[secret_name] = SecretAuditResult(
                                secret_name=secret_name,
                                environment=self.environment,
                                referenced_in_code=True
                            )
                        secrets.add(secret_name)
            except Exception:
                continue
        
        return secrets
    
    def audit_secret_manager(self, secrets: Set[str]) -> None:
        """Audit secrets in GCP Secret Manager."""
        for secret_name in secrets:
            result = self.results[secret_name]
            
            # Check if secret exists
            try:
                describe_result = subprocess.run(
                    ["gcloud", "secrets", "describe", secret_name, f"--project={self.project}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                result.exists_in_secret_manager = True
                
                # Get creation/update time
                metadata = describe_result.stdout
                if "createTime" in metadata:
                    import re
                    match = re.search(r'createTime:\s*["\']?([^"\'\n]+)', metadata)
                    if match:
                        result.last_rotation_date = match.group(1)
                
                # Check secret value
                value_result = subprocess.run(
                    ["gcloud", "secrets", "versions", "access", "latest",
                     f"--secret={secret_name}", f"--project={self.project}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                value = value_result.stdout.strip()
                
                # Validate value
                if self.validate_secret_value(secret_name, value):
                    result.has_valid_value = True
                else:
                    result.issues.append("Contains placeholder or weak value")
                    
            except subprocess.CalledProcessError:
                result.exists_in_secret_manager = False
                result.issues.append("Secret does not exist in Secret Manager")
    
    def audit_deployment_scripts(self, secrets: Set[str]) -> None:
        """Audit secret mappings in deployment scripts."""
        deploy_script = self.code_base / "scripts" / "deploy_to_gcp.py"
        
        if not deploy_script.exists():
            for result in self.results.values():
                result.warnings.append("Deployment script not found")
            return
        
        content = deploy_script.read_text()
        
        for secret_name in secrets:
            result = self.results[secret_name]
            
            # Check if secret is mapped
            env_var = secret_name.replace(f"-{self.environment}", "").upper().replace("-", "_")
            mapping = f"{env_var}={secret_name}:latest"
            
            if mapping in content:
                result.mapped_in_deployment = True
            else:
                # Check if it's supposed to be mapped
                if any(keyword in secret_name for keyword in 
                       ["postgres", "redis", "jwt", "oauth", "clickhouse", "service"]):
                    result.issues.append(f"Not mapped in deployment script as {mapping}")
    
    def audit_cloud_run_services(self, secrets: Set[str]) -> None:
        """Audit secret configurations in Cloud Run services."""
        services = ["netra-backend-staging", "netra-auth-service", "netra-frontend-staging"]
        
        for service in services:
            try:
                result = subprocess.run(
                    ["gcloud", "run", "services", "describe", service,
                     f"--region=us-central1", f"--project={self.project}", "--format=json"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                config = json.loads(result.stdout)
                
                # Extract environment variables
                containers = config.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                if containers:
                    env_vars = containers[0].get("env", [])
                    
                    for secret_name in secrets:
                        audit_result = self.results[secret_name]
                        env_var = secret_name.replace(f"-{self.environment}", "").upper().replace("-", "_")
                        
                        # Check if this secret should be in this service
                        if self.should_secret_be_in_service(secret_name, service):
                            found = False
                            for env in env_vars:
                                if env.get("name") == env_var:
                                    found = True
                                    # Check if properly configured
                                    if "valueFrom" in env:
                                        secret_ref = env["valueFrom"].get("secretKeyRef", {})
                                        if secret_ref.get("name") == secret_name:
                                            audit_result.mapped_in_cloud_run = True
                                        else:
                                            audit_result.issues.append(
                                                f"Incorrect secret reference in {service}: "
                                                f"expected {secret_name}, got {secret_ref.get('name')}"
                                            )
                                    break
                            
                            if not found and audit_result.exists_in_secret_manager:
                                audit_result.warnings.append(f"Not configured in {service}")
                                
            except subprocess.CalledProcessError:
                pass
    
    def audit_code_references(self, secrets: Set[str]) -> None:
        """Audit how secrets are referenced in code."""
        for secret_name in secrets:
            result = self.results[secret_name]
            env_var = secret_name.replace(f"-{self.environment}", "").upper().replace("-", "_")
            
            # Search for references
            found_references = False
            for py_file in self.code_base.rglob("*.py"):
                try:
                    if env_var in py_file.read_text():
                        found_references = True
                        result.referenced_in_code = True
                        break
                except Exception:
                    continue
            
            # Some secrets may not be directly referenced
            if not found_references and result.exists_in_secret_manager:
                if not any(skip in secret_name for skip in ["clickhouse-url", "session-secret"]):
                    result.warnings.append("No code references found")
    
    def check_security_compliance(self, secrets: Set[str]) -> None:
        """Check security compliance of secrets."""
        for secret_name in secrets:
            result = self.results[secret_name]
            
            # Check rotation age
            if result.last_rotation_date:
                try:
                    from datetime import datetime
                    created = datetime.fromisoformat(result.last_rotation_date.replace("Z", "+00:00"))
                    age_days = (datetime.now(created.tzinfo) - created).days
                    
                    if age_days > 90:
                        result.warnings.append(f"Secret not rotated in {age_days} days (>90 days)")
                    elif age_days > 30 and "api-key" not in secret_name:
                        result.warnings.append(f"Consider rotating (age: {age_days} days)")
                except Exception:
                    pass
            
            # Check for hardcoded values
            if result.referenced_in_code:
                self.check_for_hardcoded_values(secret_name, result)
    
    def check_for_hardcoded_values(self, secret_name: str, result: SecretAuditResult) -> None:
        """Check if secret values are hardcoded in code."""
        # This is a simplified check - in production, use more sophisticated scanning
        patterns = [
            r'["\'][a-zA-Z0-9]{32,}["\']',  # Long strings that might be keys
            r'password\s*=\s*["\'][^"\']+["\']',  # Hardcoded passwords
        ]
        
        for py_file in self.code_base.rglob("*.py"):
            try:
                content = py_file.read_text()
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        # Don't report on test files
                        if "test" not in str(py_file).lower():
                            result.warnings.append(f"Possible hardcoded secret in {py_file.name}")
                            break
            except Exception:
                continue
    
    def validate_secret_value(self, secret_name: str, value: str) -> bool:
        """Validate a secret value is not a placeholder."""
        if not value:
            return False
        
        placeholders = [
            "REPLACE_WITH", "TODO", "CHANGEME", "placeholder",
            "development", "test_", "password", "123456", "admin"
        ]
        
        for placeholder in placeholders:
            if placeholder.lower() in value.lower():
                return False
        
        # Check minimum length for different secret types
        if "password" in secret_name and len(value) < 8:
            return False
        if "api-key" in secret_name and len(value) < 20:
            return False
        
        return True
    
    def should_secret_be_in_service(self, secret_name: str, service: str) -> bool:
        """Determine if a secret should be in a specific service."""
        # Backend needs most secrets
        if "backend" in service:
            return True
        
        # Auth service needs specific secrets
        if "auth" in service:
            auth_secrets = ["postgres", "redis", "jwt", "oauth", "service"]
            return any(keyword in secret_name for keyword in auth_secrets)
        
        # Frontend needs minimal secrets
        if "frontend" in service:
            frontend_secrets = ["gtm", "next-public"]
            return any(keyword in secret_name for keyword in frontend_secrets)
        
        return False
    
    def generate_report(self) -> Tuple[bool, Dict[str, SecretAuditResult]]:
        """Generate audit report."""
        print(f"\n{'='*80}")
        print("AUDIT RESULTS")
        print(f"{'='*80}")
        
        healthy = []
        warnings = []
        critical = []
        
        for secret_name, result in sorted(self.results.items()):
            if result.issues:
                critical.append((secret_name, result))
            elif result.warnings:
                warnings.append((secret_name, result))
            elif result.is_healthy:
                healthy.append((secret_name, result))
            else:
                warnings.append((secret_name, result))
        
        # Print healthy secrets
        if healthy:
            print(f"\n PASS:  HEALTHY SECRETS ({len(healthy)}):")
            for name, _ in healthy:
                print(f"  [U+2713] {name}")
        
        # Print warnings
        if warnings:
            print(f"\n WARNING: [U+FE0F]  WARNINGS ({len(warnings)}):")
            for name, result in warnings:
                print(f"\n  {name}:")
                for warning in result.warnings:
                    print(f"    - {warning}")
        
        # Print critical issues
        if critical:
            print(f"\n FAIL:  CRITICAL ISSUES ({len(critical)}):")
            for name, result in critical:
                print(f"\n  {name}:")
                for issue in result.issues:
                    print(f"    - {issue}")
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total Secrets: {len(self.results)}")
        print(f"Healthy: {len(healthy)}")
        print(f"Warnings: {len(warnings)}")
        print(f"Critical: {len(critical)}")
        
        # Generate JSON report
        report_file = f"secrets_audit_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "environment": self.environment,
                    "project": self.project,
                    "summary": {
                        "total": len(self.results),
                        "healthy": len(healthy),
                        "warnings": len(warnings),
                        "critical": len(critical)
                    },
                    "results": {
                        name: {
                            "healthy": result.is_healthy,
                            "exists": result.exists_in_secret_manager,
                            "valid": result.has_valid_value,
                            "deployed": result.mapped_in_deployment,
                            "cloud_run": result.mapped_in_cloud_run,
                            "referenced": result.referenced_in_code,
                            "issues": result.issues,
                            "warnings": result.warnings
                        }
                        for name, result in self.results.items()
                    }
                },
                f,
                indent=2
            )
        print(f"\n[U+1F4C4] Detailed report saved to: {report_file}")
        
        return len(critical) == 0, self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Audit secrets configuration")
    parser.add_argument(
        "--project",
        default="netra-staging",
        help="GCP project ID"
    )
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="staging",
        help="Environment to audit"
    )
    parser.add_argument(
        "--output",
        choices=["console", "json", "both"],
        default="both",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    auditor = SecretsAuditor(project=args.project, environment=args.environment)
    success, results = auditor.run_full_audit()
    
    if not success:
        print("\n FAIL:  Audit failed - critical issues found")
        exit(1)
    else:
        print("\n PASS:  Audit passed")
        exit(0)


if __name__ == "__main__":
    main()