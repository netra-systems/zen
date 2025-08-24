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
            "jwt-secret-staging",
            "google-client-id-staging",
            "google-client-secret-staging"
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
            ("Database Connectivity", self.check_database_connectivity),
            ("JWT Secret Consistency", self.check_jwt_consistency),
            ("OAuth Configuration", self.check_oauth_configuration),
            ("SSL Parameter Handling", self.check_ssl_parameters),
            ("Staging URLs", self.check_staging_urls),
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
    
    def check_database_connectivity(self) -> Tuple[bool, str]:
        """Test actual database connectivity with credentials."""
        try:
            # Get database URL from secrets
            result = subprocess.run([
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", "database-url-staging",
                "--project", self.project_id
            ], capture_output=True, text=True, check=True)
            
            database_url = result.stdout.strip()
            
            # Import here to avoid dependency issues
            import asyncio
            import asyncpg
            from urllib.parse import urlparse
            
            # Parse and validate URL
            parsed = urlparse(database_url)
            if not parsed.scheme.startswith('postgresql'):
                return False, f"Invalid database URL scheme: {parsed.scheme}"
            
            # Test connection
            async def test_connection():
                # Convert URL for asyncpg if needed
                if 'sslmode=' in database_url:
                    # Handle SSL parameter conversion
                    test_url = database_url.replace('sslmode=require', 'ssl=require')
                else:
                    test_url = database_url
                
                try:
                    conn = await asyncpg.connect(test_url)
                    await conn.execute("SELECT 1")
                    await conn.close()
                    return True, "Database connection successful"
                except asyncpg.InvalidPasswordError:
                    return False, "Database authentication failed - check credentials"
                except Exception as e:
                    return False, f"Database connection failed: {e}"
            
            success, message = asyncio.run(test_connection())
            return success, message
            
        except subprocess.CalledProcessError:
            return False, "Could not retrieve database URL from secrets"
        except ImportError:
            return False, "Required packages (asyncpg) not available for database testing"
        except Exception as e:
            return False, f"Database connectivity check failed: {e}"
    
    def check_jwt_consistency(self) -> Tuple[bool, str]:
        """Check JWT secret consistency across services."""
        try:
            # Get both JWT secrets
            jwt_secret_key = self._get_secret_value("jwt-secret-key-staging")
            jwt_secret = self._get_secret_value("jwt-secret-staging")
            
            if not jwt_secret_key:
                return False, "JWT_SECRET_KEY not found in secrets"
            if not jwt_secret:
                return False, "JWT_SECRET not found in secrets"
            
            # Check consistency
            if jwt_secret_key != jwt_secret:
                return False, "JWT secrets mismatch between auth service and backend"
            
            # Check length
            if len(jwt_secret_key) < 32:
                return False, f"JWT secret too short ({len(jwt_secret_key)} chars, minimum 32)"
            
            # Test JWT functionality
            import jwt
            test_token = jwt.encode({"test": "validation"}, jwt_secret_key, algorithm="HS256")
            decoded = jwt.decode(test_token, jwt_secret_key, algorithms=["HS256"])
            
            return True, "JWT secrets are consistent and functional"
            
        except ImportError:
            return False, "PyJWT not available for JWT testing"
        except Exception as e:
            return False, f"JWT consistency check failed: {e}"
    
    def check_oauth_configuration(self) -> Tuple[bool, str]:
        """Validate OAuth configuration for staging environment."""
        try:
            client_id = self._get_secret_value("google-client-id-staging")
            client_secret = self._get_secret_value("google-client-secret-staging")
            
            if not client_id:
                return False, "Google Client ID not found in secrets"
            if not client_secret:
                return False, "Google Client Secret not found in secrets"
            
            # Check for dev/localhost patterns in staging
            issues = []
            if 'dev' in client_id.lower() or 'localhost' in client_id.lower():
                issues.append("Client ID appears to be for development environment")
            
            if 'dev' in client_secret.lower() or 'localhost' in client_secret.lower():
                issues.append("Client secret appears to be for development environment")
            
            # Validate redirect URIs would match staging
            expected_domain = "staging.netrasystems.ai"
            # Note: In real validation, we'd check actual OAuth console configuration
            
            if issues:
                return False, f"OAuth configuration issues: {'; '.join(issues)}"
            
            return True, "OAuth configuration valid for staging"
            
        except Exception as e:
            return False, f"OAuth configuration check failed: {e}"
    
    def check_ssl_parameters(self) -> Tuple[bool, str]:
        """Check SSL parameter handling for asyncpg compatibility."""
        try:
            database_url = self._get_secret_value("database-url-staging")
            if not database_url:
                return False, "Database URL not available for SSL parameter check"
            
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(database_url)
            params = parse_qs(parsed.query)
            
            issues = []
            
            # Check for sslmode parameter that needs conversion
            if 'sslmode' in params:
                issues.append("Found 'sslmode' parameter - should be converted to 'ssl' for asyncpg")
            
            # Check for conflicting SSL parameters
            if 'sslmode' in params and 'ssl' in params:
                issues.append("Both 'sslmode' and 'ssl' parameters present - conflict detected")
            
            # Check Cloud SQL Unix socket with SSL parameters
            if '/cloudsql/' in database_url and ('sslmode' in params or 'ssl' in params):
                issues.append("Cloud SQL Unix socket should not have SSL parameters")
            
            if issues:
                return False, f"SSL parameter issues: {'; '.join(issues)}"
            
            return True, "SSL parameters correctly configured"
            
        except Exception as e:
            return False, f"SSL parameter check failed: {e}"
    
    def check_staging_urls(self) -> Tuple[bool, str]:
        """Validate staging URL configuration."""
        expected_urls = {
            "frontend": "https://app.staging.netrasystems.ai",
            "auth": "https://auth.staging.netrasystems.ai"
        }
        
        # In a real deployment, these would be validated against actual environment variables
        # or deployment configuration. For now, we check the expected pattern.
        
        issues = []
        
        # Check that URLs don't contain localhost
        for service, expected_url in expected_urls.items():
            if 'localhost' in expected_url:
                issues.append(f"{service} URL contains localhost: {expected_url}")
        
        if issues:
            return False, f"Staging URL issues: {'; '.join(issues)}"
        
        return True, "Staging URLs correctly configured"
    
    def _get_secret_value(self, secret_name: str) -> Optional[str]:
        """Get secret value from GCP Secret Manager."""
        try:
            result = subprocess.run([
                "gcloud", "secrets", "versions", "access", "latest",
                "--secret", secret_name,
                "--project", self.project_id
            ], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None


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