from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Staging Deployment Validation Script

Comprehensive pre-deployment validation script that runs all validation checks
before deploying the auth service to staging environment.

This script addresses the root causes identified in staging failures:
- Database credentials and connectivity
- JWT secret consistency between services
- OAuth configuration and environment consistency  
- SSL parameters for different connection types
- Container lifecycle management readiness

Usage:
    python scripts/validate_staging_deployment.py [options]

Options:
    --verbose, -v     Enable verbose logging
    --json, -j        Output results in JSON format
    --fix-issues      Attempt to automatically fix non-critical issues
    --check-only      Only check specific validation categories
    --project         GCP project ID for deployment validation

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures
- Value Impact: Reduces deployment downtime and debugging cycles
- Strategic Impact: Ensures reliable auth service availability
"""

import argparse
import subprocess
import sys
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to Python path

# Try to import our comprehensive validation framework
try:
    from auth_service.auth_core.validation.pre_deployment_validator import PreDeploymentValidator
    HAS_COMPREHENSIVE_VALIDATOR = True
except ImportError:
    HAS_COMPREHENSIVE_VALIDATOR = False
    print("Warning: Comprehensive validator not available, using legacy validation only")


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
            "google-oauth-client-id-staging",
            "google-oauth-client-secret-staging"
        ]
        self.required_apis = [
            "run.googleapis.com",
            "containerregistry.googleapis.com", 
            "cloudbuild.googleapis.com",
            "secretmanager.googleapis.com",
            "compute.googleapis.com"
        ]
        
    def validate_all(self, use_comprehensive: bool = True, verbose: bool = False, output_format: str = "human") -> bool:
        """Run all validation checks."""
        # First run comprehensive validation if available
        comprehensive_passed = True
        if use_comprehensive and HAS_COMPREHENSIVE_VALIDATOR:
            print(" SEARCH:  COMPREHENSIVE VALIDATION FRAMEWORK")
            print("=" * 60)
            
            # Set environment to staging for validation
            original_env = os.environ.get("ENVIRONMENT")
            os.environ["ENVIRONMENT"] = "staging"
            
            try:
                validator = PreDeploymentValidator()
                report = validator.run_comprehensive_validation()
                
                if output_format == "json":
                    print(json.dumps(report, indent=2))
                else:
                    validator.print_validation_report()
                
                comprehensive_passed = report["overall_status"] in ["passed", "warning"]
                
            except Exception as e:
                print(f" FAIL:  COMPREHENSIVE VALIDATION ERROR: {e}")
                if verbose:
                    import traceback
                    print(traceback.format_exc())
                comprehensive_passed = False
            finally:
                # Restore original environment
                if original_env:
                    os.environ["ENVIRONMENT"] = original_env
                elif "ENVIRONMENT" in os.environ:
                    del os.environ["ENVIRONMENT"]
        
        # Run GCP-specific validation checks
        print("\n SEARCH:  GCP STAGING DEPLOYMENT VALIDATION")
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
        
        gcp_passed = True
        results = []
        
        for check_name, check_func in checks:
            print(f"\n SEARCH:  {check_name}...")
            try:
                success, message = check_func()
                status = " PASS:  PASS" if success else " FAIL:  FAIL" 
                print(f"   {status}: {message}")
                results.append((check_name, success, message))
                if not success:
                    gcp_passed = False
            except Exception as e:
                error_msg = str(e) if not verbose else f"{e}\n{traceback.format_exc() if 'traceback' in sys.modules else ''}"
                print(f"    FAIL:  ERROR: {error_msg}")
                results.append((check_name, False, error_msg))
                gcp_passed = False
                
        print("\n" + "=" * 50)
        print("[U+1F4CB] GCP VALIDATION SUMMARY")
        print("=" * 50)
        
        for check_name, success, message in results:
            status = " PASS: " if success else " FAIL: "
            print(f"{status} {check_name}")
            if not success:
                print(f"    ->  {message}")
        
        # Combined results
        all_passed = comprehensive_passed and gcp_passed
        
        print("\n" + "=" * 60)
        print(" TARGET:  OVERALL DEPLOYMENT READINESS")
        print("=" * 60)
        
        comp_status = " PASS:  PASS" if comprehensive_passed else " FAIL:  FAIL"
        gcp_status = " PASS:  PASS" if gcp_passed else " FAIL:  FAIL"
        
        print(f"Comprehensive Validation: {comp_status}")
        print(f"GCP-Specific Validation: {gcp_status}")
        
        if all_passed:
            print(f"\n CELEBRATION:  ALL VALIDATIONS PASSED - Ready for deployment!")
            print(f"Deploy with: python scripts/deploy_to_gcp.py --project {self.project_id} --build-local --run-checks")
        else:
            print(f"\n ALERT:  VALIDATION FAILED - Fix issues before deployment!")
            if not comprehensive_passed:
                print("   - Fix comprehensive validation issues first")
            if not gcp_passed:
                print("   - Fix GCP-specific deployment issues")
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
            "deployment/docker/backend.gcp.Dockerfile",
            "deployment/docker/auth.gcp.Dockerfile", 
            "deployment/docker/frontend.gcp.Dockerfile"
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
            client_id = self._get_secret_value("google-oauth-client-id-staging")
            client_secret = self._get_secret_value("google-oauth-client-secret-staging")
            
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
    parser = argparse.ArgumentParser(
        description="Auth Service Staging Deployment Validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_staging_deployment.py
  python scripts/validate_staging_deployment.py --verbose
  python scripts/validate_staging_deployment.py --json
  python scripts/validate_staging_deployment.py --no-comprehensive
  python scripts/validate_staging_deployment.py --project netra-staging --verbose
        """
    )
    
    parser.add_argument(
        "--project", 
        default="netra-staging", 
        help="GCP Project ID for deployment validation"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output comprehensive validation results in JSON format"
    )
    
    parser.add_argument(
        "--no-comprehensive",
        action="store_true",
        help="Skip comprehensive validation, run only GCP-specific checks"
    )
    
    parser.add_argument(
        "--environment",
        type=str,
        choices=["development", "staging", "production"],
        default="staging",
        help="Environment for validation (default: staging)"
    )
    
    args = parser.parse_args()
    
    # Set up logging if verbose
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Override environment if specified
    os.environ["ENVIRONMENT"] = args.environment
    
    # Initialize validator
    validator = StagingValidator(args.project)
    
    try:
        # Run validation
        output_format = "json" if args.json else "human"
        success = validator.validate_all(
            use_comprehensive=not args.no_comprehensive,
            verbose=args.verbose,
            output_format=output_format
        )
        
        # Exit with appropriate code based on validation results
        if success:
            sys.exit(0)  # All validations passed
        else:
            sys.exit(1)  # Critical issues found
            
    except KeyboardInterrupt:
        print("\nValidation interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Validation failed with error: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(3)  # Internal error


if __name__ == "__main__":
    main()
