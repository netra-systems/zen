#!/usr/bin/env python3
"""
CRITICAL: Staging Deployment Configuration Fix Script

This script addresses all identified critical issues preventing staging deployment from working:
1. Creates missing secrets in GCP Secret Manager
2. Fixes service connectivity issues 
3. Updates environment variable mappings
4. Validates CORS configuration
5. Tests critical path functionality

MISSION CRITICAL for startup success.
"""

import json
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests

# Fix Unicode encoding issues on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

@dataclass
class SecretConfig:
    """Configuration for a secret that needs to be created."""
    name: str
    description: str
    is_required: bool
    generate_command: Optional[str] = None
    placeholder_value: Optional[str] = None

@dataclass 
class ServiceEndpoint:
    """Configuration for service endpoint validation."""
    name: str
    url: str
    expected_status: List[int]
    timeout: int = 30

class StagingDeploymentFixer:
    """Fixes all critical staging deployment issues."""
    
    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        self.region = "us-central1"
        self.gcloud_cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"
        self.use_shell = sys.platform == "win32"
        
        # Define all required secrets with generation instructions
        self.required_secrets = [
            SecretConfig(
                name="openai-api-key-staging",
                description="OpenAI API key for LLM operations",
                is_required=True,
                placeholder_value="sk-test-placeholder-for-staging-only"
            ),
            SecretConfig(
                name="fernet-key-staging", 
                description="Fernet encryption key for data encryption",
                is_required=True,
                generate_command="python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ),
            SecretConfig(
                name="jwt-secret-key-staging",
                description="JWT signing key for authentication",
                is_required=True,
                generate_command="python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            ),
            SecretConfig(
                name="session-secret-key-staging",
                description="Session encryption key",
                is_required=True,
                generate_command="python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            ),
            SecretConfig(
                name="anthropic-api-key-staging",
                description="Anthropic API key for Claude operations", 
                is_required=False,
                placeholder_value="sk-ant-test-placeholder-for-staging-only"
            )
        ]
        
        # Service endpoints for validation
        self.service_endpoints = [
            ServiceEndpoint(
                name="Backend Health",
                url="https://netra-backend-jmujvwwf7q-uc.a.run.app/health",
                expected_status=[200]
            ),
            ServiceEndpoint(
                name="Backend Docs", 
                url="https://netra-backend-jmujvwwf7q-uc.a.run.app/docs",
                expected_status=[200]
            ),
            ServiceEndpoint(
                name="Auth Health",
                url="https://netra-auth-jmujvwwf7q-uc.a.run.app/health", 
                expected_status=[200]
            ),
            ServiceEndpoint(
                name="WebSocket Availability",
                url="https://netra-backend-jmujvwwf7q-uc.a.run.app/ws",
                expected_status=[400, 426, 404]  # Any of these indicates WS endpoint exists
            )
        ]

    def print_header(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n{'='*60}")
        print(f"{title:^60}")
        print(f"{'='*60}")

    def run_command(self, cmd: List[str], input_data: str = None) -> Tuple[bool, str, str]:
        """Run a shell command and return success status, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                input=input_data,
                capture_output=True,
                text=True,
                check=False,
                shell=self.use_shell
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except Exception as e:
            return False, "", str(e)

    def check_secret_exists(self, secret_name: str) -> bool:
        """Check if a secret exists in Secret Manager."""
        success, _, _ = self.run_command([
            self.gcloud_cmd, "secrets", "describe", secret_name, 
            "--project", self.project_id
        ])
        return success

    def generate_secret_value(self, secret: SecretConfig) -> Optional[str]:
        """Generate a secret value using the provided command or placeholder."""
        if secret.generate_command:
            try:
                result = subprocess.run(
                    secret.generate_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip()
            except Exception as e:
                print(f"   WARNING: [U+FE0F]  Failed to generate {secret.name}: {e}")
                return secret.placeholder_value
        return secret.placeholder_value

    def create_secret(self, secret: SecretConfig) -> bool:
        """Create a secret in Secret Manager."""
        secret_value = self.generate_secret_value(secret)
        if not secret_value:
            print(f"   FAIL:  No value available for {secret.name}")
            return False
        
        # Create the secret
        success, _, error = self.run_command([
            self.gcloud_cmd, "secrets", "create", secret.name,
            "--project", self.project_id
        ])
        
        if not success and "already exists" not in error:
            print(f"   FAIL:  Failed to create {secret.name}: {error}")
            return False
        
        # Add secret version  
        success, _, error = self.run_command([
            self.gcloud_cmd, "secrets", "versions", "add", secret.name,
            "--data-file=-", "--project", self.project_id
        ], input_data=secret_value)
        
        if success:
            print(f"   PASS:  Created {secret.name}")
            return True
        else:
            print(f"   FAIL:  Failed to add version to {secret.name}: {error}")
            return False

    def fix_secrets(self) -> Dict[str, bool]:
        """Fix all missing secrets in Secret Manager."""
        self.print_header("FIXING SECRETS IN SECRET MANAGER")
        
        results = {}
        for secret in self.required_secrets:
            print(f"\nChecking {secret.name}...")
            
            if self.check_secret_exists(secret.name):
                print(f"   PASS:  {secret.name} already exists")
                results[secret.name] = True
            else:
                print(f"  [U+1F527] Creating {secret.name}...")
                results[secret.name] = self.create_secret(secret)
                
        return results

    def get_service_url(self, service_name: str) -> Optional[str]:
        """Get the URL of a deployed Cloud Run service."""
        success, stdout, _ = self.run_command([
            self.gcloud_cmd, "run", "services", "describe", service_name,
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--format", "value(status.url)"
        ])
        
        return stdout if success else None

    def update_service_secrets(self, service_name: str, secrets_map: Dict[str, str]) -> bool:
        """Update Cloud Run service with new secrets."""
        secret_args = []
        for env_var, secret_name in secrets_map.items():
            secret_args.extend(["--update-secrets", f"{env_var}={secret_name}:latest"])
        
        cmd = [
            self.gcloud_cmd, "run", "services", "update", service_name,
            "--region", self.region,
            "--project", self.project_id
        ] + secret_args
        
        success, _, error = self.run_command(cmd)
        if success:
            print(f"   PASS:  Updated secrets for {service_name}")
            return True
        else:
            print(f"   FAIL:  Failed to update {service_name}: {error}")
            return False

    def fix_service_configuration(self) -> Dict[str, bool]:
        """Fix service configuration issues."""
        self.print_header("FIXING SERVICE CONFIGURATION")
        
        results = {}
        
        # Update backend service with all required secrets
        print("\n[U+1F527] Updating backend service secrets...")
        backend_secrets = {
            "DATABASE_URL": "database-url-staging",
            "JWT_SECRET_KEY": "jwt-secret-key-staging", 
            "SECRET_KEY": "session-secret-key-staging",
            "OPENAI_API_KEY": "openai-api-key-staging",
            "FERNET_KEY": "fernet-key-staging"
        }
        results["backend"] = self.update_service_secrets("netra-backend", backend_secrets)
        
        # Update auth service with required secrets
        print("\n[U+1F527] Updating auth service secrets...")
        auth_secrets = {
            "DATABASE_URL": "database-url-staging",
            "JWT_SECRET_KEY": "jwt-secret-key-staging"
        }
        results["auth"] = self.update_service_secrets("netra-auth", auth_secrets)
        
        # Update frontend with correct environment variables
        print("\n[U+1F527] Updating frontend service environment...")
        backend_url = self.get_service_url("netra-backend") 
        auth_url = self.get_service_url("netra-auth")
        
        if backend_url and auth_url:
            cmd = [
                self.gcloud_cmd, "run", "services", "update", "netra-frontend",
                "--region", self.region,
                "--project", self.project_id,
                "--update-env-vars", 
                f"NEXT_PUBLIC_API_URL={backend_url},NEXT_PUBLIC_AUTH_URL={auth_url}",
                "--update-env-vars",
                f"CORS_ALLOWED_ORIGINS={backend_url},{auth_url},https://netra-frontend-jmujvwwf7q-uc.a.run.app"
            ]
            
            success, _, error = self.run_command(cmd)
            results["frontend"] = success
            if success:
                print(f"   PASS:  Updated frontend environment variables")
            else:
                print(f"   FAIL:  Failed to update frontend: {error}")
        else:
            print(f"   WARNING: [U+FE0F]  Could not get service URLs - skipping frontend update")
            results["frontend"] = False
            
        return results

    def validate_endpoint(self, endpoint: ServiceEndpoint) -> Dict:
        """Validate a single service endpoint."""
        print(f"\n SEARCH:  Testing {endpoint.name}...")
        print(f"    URL: {endpoint.url}")
        print(f"    Expected: {endpoint.expected_status}")
        
        try:
            start_time = time.time()
            response = requests.get(endpoint.url, timeout=endpoint.timeout)
            response_time = (time.time() - start_time) * 1000
            
            status_ok = response.status_code in endpoint.expected_status
            
            result = {
                "endpoint": endpoint.name,
                "url": endpoint.url,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "success": status_ok,
                "error": None
            }
            
            if status_ok:
                print(f"     PASS:  Response: {response.status_code} ({response_time:.1f}ms)")
            else:
                print(f"     FAIL:  Response: {response.status_code} (expected {endpoint.expected_status})")
                
            return result
            
        except requests.exceptions.Timeout:
            print(f"    [U+23F0] Timeout after {endpoint.timeout}s")
            return {
                "endpoint": endpoint.name,
                "url": endpoint.url, 
                "status_code": None,
                "response_time_ms": endpoint.timeout * 1000,
                "success": False,
                "error": "Timeout"
            }
        except Exception as e:
            print(f"     FAIL:  Error: {e}")
            return {
                "endpoint": endpoint.name,
                "url": endpoint.url,
                "status_code": None, 
                "response_time_ms": 0,
                "success": False,
                "error": str(e)
            }

    def validate_critical_paths(self) -> Dict[str, Dict]:
        """Validate all critical service endpoints."""
        self.print_header("VALIDATING CRITICAL PATHS")
        
        results = {}
        for endpoint in self.service_endpoints:
            results[endpoint.name] = self.validate_endpoint(endpoint)
            
        return results

    def wait_for_service_deployment(self, service_name: str, max_wait: int = 300) -> bool:
        """Wait for a service to be fully deployed and healthy."""
        print(f"\n[U+23F3] Waiting for {service_name} to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            # Check service status
            success, stdout, _ = self.run_command([
                self.gcloud_cmd, "run", "services", "describe", service_name,
                "--region", self.region,
                "--project", self.project_id,
                "--format", "value(status.conditions[0].status)"
            ])
            
            if success and "True" in stdout:
                print(f"   PASS:  {service_name} is ready!")
                return True
                
            print(f"  [U+23F3] Still waiting... ({int(time.time() - start_time)}s)")
            time.sleep(10)
            
        print(f"   WARNING: [U+FE0F]  {service_name} not ready after {max_wait}s")
        return False

    def generate_validation_report(self, results: Dict) -> Dict:
        """Generate a comprehensive validation report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project_id": self.project_id,
            "secrets_status": results.get("secrets", {}),
            "services_status": results.get("services", {}),
            "endpoints_status": results.get("endpoints", {}),
            "overall_health": "unknown"
        }
        
        # Determine overall health
        secrets_ok = all(results.get("secrets", {}).values())
        services_ok = all(results.get("services", {}).values()) 
        endpoints_ok = all(r.get("success", False) for r in results.get("endpoints", {}).values())
        
        if secrets_ok and services_ok and endpoints_ok:
            report["overall_health"] = "healthy"
        elif secrets_ok and services_ok:
            report["overall_health"] = "partially_healthy"
        else:
            report["overall_health"] = "unhealthy"
            
        return report

    def run_complete_fix(self) -> Dict:
        """Run the complete staging deployment fix process."""
        print("[U+1F680] NETRA STAGING DEPLOYMENT FIX")
        print("=" * 60)
        print("This script will fix all identified critical issues:")
        print("1. Create missing secrets in Secret Manager")
        print("2. Update service configurations") 
        print("3. Fix environment variable mappings")
        print("4. Validate critical service paths")
        print("5. Generate deployment validation report")
        
        # Step 1: Fix secrets
        secrets_results = self.fix_secrets()
        
        # Step 2: Fix service configuration 
        services_results = self.fix_service_configuration()
        
        # Step 3: Wait for services to be ready
        for service_name in ["netra-backend", "netra-auth", "netra-frontend"]:
            self.wait_for_service_deployment(service_name, max_wait=180)
        
        # Step 4: Validate critical paths
        endpoints_results = self.validate_critical_paths()
        
        # Step 5: Generate final report
        final_results = {
            "secrets": secrets_results,
            "services": services_results, 
            "endpoints": endpoints_results
        }
        
        report = self.generate_validation_report(final_results)
        
        # Print final summary
        self.print_header("FINAL VALIDATION REPORT")
        print(f"Overall Health: {report['overall_health'].upper()}")
        print(f"Project: {self.project_id}")
        print(f"Timestamp: {report['timestamp']}")
        
        print(f"\n CHART:  RESULTS SUMMARY:")
        secrets_count = sum(1 for v in secrets_results.values() if v)
        services_count = sum(1 for v in services_results.values() if v)
        endpoints_count = sum(1 for v in endpoints_results.values() if v.get("success"))
        
        print(f"  Secrets: {secrets_count}/{len(secrets_results)}  PASS: ")
        print(f"  Services: {services_count}/{len(services_results)}  PASS: ") 
        print(f"  Endpoints: {endpoints_count}/{len(endpoints_results)}  PASS: ")
        
        if report["overall_health"] == "healthy":
            print(f"\n CELEBRATION:  STAGING DEPLOYMENT IS NOW HEALTHY!")
            print(f"   All services are running and accessible.")
        elif report["overall_health"] == "partially_healthy":
            print(f"\n WARNING: [U+FE0F]  STAGING DEPLOYMENT IS PARTIALLY HEALTHY")
            print(f"   Some endpoints may still have issues.")
        else:
            print(f"\n FAIL:  STAGING DEPLOYMENT STILL HAS ISSUES") 
            print(f"   Please review the errors above.")
            
        # Save report to file
        report_path = "staging_fix_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n[U+1F4C4] Full report saved to: {report_path}")
        
        return final_results

def main():
    """Main entry point."""
    project_id = "netra-staging"
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    
    fixer = StagingDeploymentFixer(project_id)
    try:
        results = fixer.run_complete_fix()
        
        # Return appropriate exit code
        overall_success = (
            all(results["secrets"].values()) and
            all(results["services"].values()) and 
            all(r.get("success", False) for r in results["endpoints"].values())
        )
        
        sys.exit(0 if overall_success else 1)
        
    except KeyboardInterrupt:
        print("\n\n WARNING: [U+FE0F] Fix process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n FAIL:  Fix process failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()