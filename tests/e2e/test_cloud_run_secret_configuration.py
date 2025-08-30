"""
Test Cloud Run Secret Configuration
Validates that Cloud Run services have properly configured secrets.

This test prevents deployment failures due to missing secret name fields in secretKeyRef.
Issue discovered: 2025-08-29 - All secrets were missing the 'name' field causing startup failures.
"""
import subprocess
import json
import yaml
from typing import Dict, List, Tuple


class CloudRunSecretValidator:
    """Validates Cloud Run service secret configurations."""
    
    REQUIRED_BACKEND_SECRETS = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
        "POSTGRES_USER", "POSTGRES_PASSWORD",
        "JWT_SECRET_KEY", "SECRET_KEY", "OPENAI_API_KEY",
        "FERNET_KEY", "REDIS_URL"
    ]
    
    REQUIRED_AUTH_SECRETS = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
        "POSTGRES_USER", "POSTGRES_PASSWORD", 
        "JWT_SECRET_KEY", "JWT_SECRET",
        "SERVICE_SECRET", "SERVICE_ID"
    ]
    
    SERVICE_MAPPINGS = {
        "backend": "netra-backend-staging",
        "auth": "netra-auth-service",
        "frontend": "netra-frontend-staging"
    }
    
    def __init__(self, project: str = "netra-staging", region: str = "us-central1"):
        self.project = project
        self.region = region
        self.errors = []
    
    def get_service_config(self, service_name: str) -> Dict:
        """Fetch Cloud Run service configuration."""
        try:
            result = subprocess.run(
                f"gcloud run services describe {service_name} "
                f"--region={self.region} --project={self.project} --format=json",
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            self.errors.append(f"Failed to fetch {service_name}: {e}")
            return {}
    
    def validate_secret_refs(self, config: Dict, service_type: str) -> List[str]:
        """Validate secretKeyRef configurations have proper name fields."""
        issues = []
        
        # Navigate to container env vars
        try:
            containers = config["spec"]["template"]["spec"]["containers"]
            if not containers:
                issues.append(f"No containers found in {service_type} service")
                return issues
            
            env_vars = containers[0].get("env", [])
            
            # Check required secrets based on service type
            required_secrets = (
                self.REQUIRED_BACKEND_SECRETS if service_type == "backend"
                else self.REQUIRED_AUTH_SECRETS if service_type == "auth"
                else []
            )
            
            for required_secret in required_secrets:
                found = False
                for env_var in env_vars:
                    if env_var.get("name") == required_secret:
                        found = True
                        # Check if it has secretKeyRef
                        if "valueFrom" in env_var:
                            secret_ref = env_var["valueFrom"].get("secretKeyRef", {})
                            if not secret_ref.get("name"):
                                expected_name = f"{required_secret.lower().replace('_', '-')}-staging"
                                issues.append(
                                    f"{required_secret}: Missing 'name' field in secretKeyRef. "
                                    f"Expected: {expected_name}"
                                )
                            elif not secret_ref.get("key"):
                                issues.append(f"{required_secret}: Missing 'key' field in secretKeyRef")
                        break
                
                if not found:
                    issues.append(f"{required_secret}: Secret not configured")
        
        except KeyError as e:
            issues.append(f"Invalid service configuration structure: {e}")
        
        return issues
    
    def validate_all_services(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Validate all Cloud Run services."""
        all_issues = {}
        
        for service_type, cloud_run_name in self.SERVICE_MAPPINGS.items():
            print(f"\nValidating {service_type} service ({cloud_run_name})...")
            
            config = self.get_service_config(cloud_run_name)
            if not config:
                all_issues[service_type] = [f"Could not fetch service configuration"]
                continue
            
            issues = self.validate_secret_refs(config, service_type)
            if issues:
                all_issues[service_type] = issues
            else:
                print(f"[OK] {service_type}: All secrets properly configured")
        
        return len(all_issues) == 0, all_issues
    
    def generate_fix_commands(self, issues: Dict[str, List[str]]) -> List[str]:
        """Generate gcloud commands to fix the issues."""
        fix_commands = []
        
        for service_type, service_issues in issues.items():
            if not service_issues:
                continue
            
            cloud_run_name = self.SERVICE_MAPPINGS[service_type]
            secrets_to_fix = []
            
            for issue in service_issues:
                if "Missing 'name' field" in issue:
                    # Extract the secret name from the issue
                    secret_var = issue.split(":")[0]
                    secret_name = f"{secret_var.lower().replace('_', '-')}-staging"
                    secrets_to_fix.append(f"{secret_var}={secret_name}:latest")
            
            if secrets_to_fix:
                cmd = (
                    f"gcloud run services update {cloud_run_name} "
                    f"--region={self.region} --project={self.project} "
                    f"--set-secrets={','.join(secrets_to_fix)}"
                )
                fix_commands.append(cmd)
        
        return fix_commands


def test_cloud_run_secret_configuration():
    """Test that Cloud Run services have properly configured secrets."""
    validator = CloudRunSecretValidator()
    
    print("=" * 80)
    print("CLOUD RUN SECRET CONFIGURATION VALIDATION")
    print("=" * 80)
    
    is_valid, issues = validator.validate_all_services()
    
    if not is_valid:
        print("\n[X] VALIDATION FAILED - Issues found:")
        for service, service_issues in issues.items():
            print(f"\n{service.upper()} SERVICE:")
            for issue in service_issues:
                print(f"  - {issue}")
        
        # Generate fix commands
        fix_commands = validator.generate_fix_commands(issues)
        if fix_commands:
            print("\n[FIX] COMMANDS:")
            for cmd in fix_commands:
                print(f"\n{cmd}")
        
        # Fail the test
        assert False, f"Secret configuration issues found: {issues}"
    else:
        print("\n[OK] All services have properly configured secrets")
        return True


if __name__ == "__main__":
    # Run the validation
    try:
        test_cloud_run_secret_configuration()
        print("\n[OK] All validations passed!")
    except AssertionError as e:
        print(f"\n[X] Validation failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        exit(1)