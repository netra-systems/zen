#!/usr/bin/env python3
"""
Staging Deployment Validation Script
Validates all staging configuration before deployment to prevent deployment failures.
"""

import subprocess
import sys
import json
from typing import Dict, List, Tuple, Optional


class StagingValidator:
    """Validates staging deployment configuration."""
    
    def __init__(self, project_id: str = "netra-staging"):
        self.project_id = project_id
        self.region = "us-central1"
        self.required_secrets = [
            "database-url-staging",
            "jwt-secret-key-staging", 
            "session-secret-key-staging",
            "fernet-key-staging",
            "openai-api-key-staging",
            "jwt-secret-staging"
        ]
        self.required_apis = [
            "run.googleapis.com",
            "containerregistry.googleapis.com", 
            "cloudbuild.googleapis.com",
            "secretmanager.googleapis.com",
            "compute.googleapis.com"
        ]
        
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("🔍 STAGING DEPLOYMENT VALIDATION")
        print("=" * 50)
        
        checks = [
            ("GCP Authentication", self.check_gcp_auth),
            ("Required APIs", self.check_apis_enabled),
            ("Staging Secrets", self.check_secrets_exist),
            ("Secret Values", self.check_secret_values),
            ("Dockerfiles", self.check_dockerfiles),
            ("Configuration Files", self.check_config_files),
            ("Cloud SQL Instance", self.check_cloud_sql)
        ]
        
        all_passed = True
        results = []
        
        for check_name, check_func in checks:
            print(f"\n🔍 {check_name}...")
            try:
                success, message = check_func()
                status = "✅ PASS" if success else "❌ FAIL" 
                print(f"   {status}: {message}")
                results.append((check_name, success, message))
                if not success:
                    all_passed = False
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                results.append((check_name, False, str(e)))
                all_passed = False
                
        print("\n" + "=" * 50)
        print("📋 VALIDATION SUMMARY")
        print("=" * 50)
        
        for check_name, success, message in results:
            status = "✅" if success else "❌"
            print(f"{status} {check_name}")
            if not success:
                print(f"   → {message}")
                
        if all_passed:
            print(f"\n🎉 ALL CHECKS PASSED - Ready for deployment!")
            print(f"Deploy with: python scripts/deploy_to_gcp.py --project {self.project_id} --build-local --run-checks")
        else:
            print(f"\n🚨 VALIDATION FAILED - Fix issues before deployment!")
            print(f"See STAGING_DEPLOYMENT_CHECKLIST.md for fix instructions")
            
        return all_passed
        
    def check_gcp_auth(self) -> Tuple[bool, str]:
        """Check GCP authentication and project access."""
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True, text=True, check=False
            )
            current_project = result.stdout.strip()
            
            if current_project != self.project_id:
                return False, f"Wrong project: {current_project}, expected: {self.project_id}"
                
            # Test access to project
            result = subprocess.run(
                ["gcloud", "projects", "describe", self.project_id],
                capture_output=True, text=True, check=False
            )
            
            if result.returncode != 0:
                return False, f"Cannot access project {self.project_id}"
                
            return True, f"Authenticated for project {self.project_id}"
            
        except FileNotFoundError:
            return False, "gcloud CLI not installed"
            
    def check_apis_enabled(self) -> Tuple[bool, str]:
        """Check if required APIs are enabled."""
        try:
            result = subprocess.run(
                ["gcloud", "services", "list", "--enabled", "--format=value(name)"],
                capture_output=True, text=True, check=True
            )
            enabled_apis = set(result.stdout.strip().split('\n'))
            
            missing_apis = []
            for api in self.required_apis:
                if api not in enabled_apis:
                    missing_apis.append(api)
                    
            if missing_apis:
                return False, f"Missing APIs: {', '.join(missing_apis)}"
                
            return True, f"All {len(self.required_apis)} required APIs enabled"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check APIs: {e.stderr}"
            
    def check_secrets_exist(self) -> Tuple[bool, str]:
        """Check if all required secrets exist."""
        try:
            result = subprocess.run(
                ["gcloud", "secrets", "list", "--format=value(name)"],
                capture_output=True, text=True, check=True
            )
            existing_secrets = set(result.stdout.strip().split('\n'))
            
            missing_secrets = []
            for secret in self.required_secrets:
                if secret not in existing_secrets:
                    missing_secrets.append(secret)
                    
            if missing_secrets:
                return False, f"Missing secrets: {', '.join(missing_secrets)}"
                
            return True, f"All {len(self.required_secrets)} required secrets exist"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check secrets: {e.stderr}"
            
    def check_secret_values(self) -> Tuple[bool, str]:
        """Check if secret values are not placeholder values."""
        try:
            placeholder_secrets = []
            
            for secret in self.required_secrets:
                try:
                    result = subprocess.run(
                        ["gcloud", "secrets", "versions", "access", "latest", "--secret", secret],
                        capture_output=True, text=True, check=True
                    )
                    value = result.stdout.strip()
                    
                    # Check for placeholder values
                    placeholders = [
                        "REPLACE_WITH_REAL",
                        "your-secure-",
                        "sk-REPLACE",
                        "zRR9caaayrRraaaaaaa6EK"  # Old test password
                    ]
                    
                    if any(placeholder in value for placeholder in placeholders):
                        placeholder_secrets.append(secret)
                        
                except subprocess.CalledProcessError:
                    placeholder_secrets.append(f"{secret} (inaccessible)")
                    
            if placeholder_secrets:
                return False, f"Placeholder values in: {', '.join(placeholder_secrets)}"
                
            return True, "All secrets have real values"
            
        except Exception as e:
            return False, f"Failed to validate secret values: {e}"
            
    def check_dockerfiles(self) -> Tuple[bool, str]:
        """Check if required Dockerfiles exist."""
        import os
        
        required_dockerfiles = [
            "Dockerfile.backend",
            "Dockerfile.auth", 
            "Dockerfile.frontend"
        ]
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        missing_files = []
        
        for dockerfile in required_dockerfiles:
            if not os.path.exists(os.path.join(project_root, dockerfile)):
                missing_files.append(dockerfile)
                
        if missing_files:
            return False, f"Missing Dockerfiles: {', '.join(missing_files)}"
            
        return True, "All required Dockerfiles exist"
        
    def check_config_files(self) -> Tuple[bool, str]:
        """Check if staging configuration files exist."""
        import os
        
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_files = [
            "config/staging.env",
            "SPEC/staging_environment.xml",
            "SPEC/gcp_deployment.xml"
        ]
        
        missing_files = []
        for config_file in config_files:
            if not os.path.exists(os.path.join(project_root, config_file)):
                missing_files.append(config_file)
                
        if missing_files:
            return False, f"Missing config files: {', '.join(missing_files)}"
            
        return True, "All configuration files exist"
        
    def check_cloud_sql(self) -> Tuple[bool, str]:
        """Check Cloud SQL instance accessibility."""
        try:
            result = subprocess.run(
                ["gcloud", "sql", "instances", "list", "--format=value(name,state)"],
                capture_output=True, text=True, check=True
            )
            
            instances = result.stdout.strip().split('\n')
            postgres_running = False
            
            for instance_line in instances:
                if instance_line:
                    name, state = instance_line.split('\t')
                    if 'postgres' in name.lower() and state == 'RUNNABLE':
                        postgres_running = True
                        break
                        
            if not postgres_running:
                return False, "No running PostgreSQL Cloud SQL instance found"
                
            return True, "Cloud SQL PostgreSQL instance is running"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to check Cloud SQL: {e.stderr}"


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate staging deployment configuration")
    parser.add_argument("--project", default="netra-staging", help="GCP Project ID")
    args = parser.parse_args()
    
    validator = StagingValidator(args.project)
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()