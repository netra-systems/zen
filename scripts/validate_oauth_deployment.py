#!/usr/bin/env python3
"""
Pre-deployment OAuth Validation Script
Validates OAuth configuration before deployment to prevent broken authentication.

This script ensures OAuth credentials are properly configured for the target environment
and will FAIL LOUD if any critical OAuth configuration is missing or invalid.

Usage:
    python scripts/validate_oauth_deployment.py --environment staging
    python scripts/validate_oauth_deployment.py --environment production
    python scripts/validate_oauth_deployment.py --environment development
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.isolated_environment import get_env

try:
    # Google Cloud Secret Manager (optional)
    from google.cloud import secretmanager
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    

class OAuthValidationError(Exception):
    """Critical OAuth validation error that should fail deployment."""
    pass


class OAuthDeploymentValidator:
    """Validates OAuth configuration for deployment environments."""
    
    def __init__(self, environment: str, deployment_context: bool = False):
        self.environment = environment.lower()
        self.deployment_context = deployment_context  # True when validating for actual deployment
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.project_id = get_env().get("GCP_PROJECT_ID") or "netra-staging"
        
        print(f"OAuth Deployment Validator")
        print(f"Environment: {self.environment}")
        print(f"GCP Project: {self.project_id}")
        print(f"Context: {'Deployment' if deployment_context else 'Development'}")
        print("=" * 60)
    
    def validate_environment_variables(self) -> Dict[str, Optional[str]]:
        """Validate OAuth environment variables."""
        print("\nValidating Environment Variables...")
        
        # Environment-specific variables to check
        env_vars_to_check = {
            "GOOGLE_CLIENT_ID": get_env().get("GOOGLE_CLIENT_ID"),
            "GOOGLE_CLIENT_SECRET": get_env().get("GOOGLE_CLIENT_SECRET"),
            "GOOGLE_OAUTH_CLIENT_ID_STAGING": get_env().get("GOOGLE_OAUTH_CLIENT_ID_STAGING"),
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": get_env().get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING"),
            "GOOGLE_OAUTH_CLIENT_ID_PRODUCTION": get_env().get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION"),
            "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION": get_env().get("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"),
        }
        
        # Required variables for each environment
        if self.environment == "staging":
            required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
            preferred_vars = ["GOOGLE_OAUTH_CLIENT_ID_STAGING", "GOOGLE_OAUTH_CLIENT_SECRET_STAGING"]
        elif self.environment == "production":
            required_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
            preferred_vars = ["GOOGLE_OAUTH_CLIENT_ID_PRODUCTION", "GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION"]
        else:  # development
            required_vars = []
            preferred_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        
        print(f"Environment Variables Status:")
        for var_name, var_value in env_vars_to_check.items():
            if var_value:
                if "SECRET" in var_name:
                    print(f"  [OK] {var_name}: [SET - {len(var_value)} chars]")
                else:
                    print(f"  [OK] {var_name}: {var_value[:50]}{'...' if len(var_value) > 50 else ''}")
            else:
                print(f"  [MISSING] {var_name}: [NOT SET]")
        
        # Check required variables for staging/production
        if self.environment in ["staging", "production"]:
            missing_required = [var for var in required_vars if not env_vars_to_check.get(var)]
            missing_preferred = [var for var in preferred_vars if not env_vars_to_check.get(var)]
            
            # In deployment context, environment variables are optional if Secret Manager has them
            if not self.deployment_context and missing_required:
                self.validation_errors.extend([f"{var} is required for {self.environment} (non-deployment context)" for var in missing_required])
            elif self.deployment_context and missing_required:
                self.validation_warnings.extend([f"{var} missing locally - will validate via Secret Manager" for var in missing_required])
            
            if missing_preferred:
                self.validation_warnings.extend([f"{var} is preferred for {self.environment}" for var in missing_preferred])
        
        return env_vars_to_check
    
    def validate_google_secret_manager(self) -> Dict[str, Optional[str]]:
        """Validate OAuth secrets in Google Secret Manager."""
        print(f"\n[SECURE] Validating Google Secret Manager ({self.project_id})...")
        
        if not GOOGLE_CLOUD_AVAILABLE:
            print("  [WARNING]  Google Cloud SDK not available - skipping GSM validation")
            return {}
        
        # Secrets to check based on environment
        if self.environment == "staging":
            secrets_to_check = [
                "google-oauth-client-id-staging",
                "google-oauth-client-secret-staging"
            ]
        elif self.environment == "production":
            secrets_to_check = [
                "google-client-id-production", 
                "google-client-secret-production"
            ]
        else:
            secrets_to_check = []
        
        gsm_secrets = {}
        
        if not secrets_to_check:
            print(f"  [INFO]  No GSM secrets to check for {self.environment}")
            return gsm_secrets
        
        try:
            client = secretmanager.SecretManagerServiceClient()
            
            for secret_name in secrets_to_check:
                try:
                    name = f"projects/{self.project_id}/secrets/{secret_name}/versions/latest"
                    response = client.access_secret_version(request={"name": name})
                    secret_value = response.payload.data.decode("UTF-8")
                    gsm_secrets[secret_name] = secret_value
                    
                    if "secret" in secret_name:
                        print(f"  [OK] {secret_name}: [FOUND - {len(secret_value)} chars]")
                    else:
                        print(f"  [OK] {secret_name}: {secret_value[:50]}{'...' if len(secret_value) > 50 else ''}")
                        
                except Exception as e:
                    print(f"  [FAIL] {secret_name}: {str(e)}")
                    gsm_secrets[secret_name] = None
                    self.validation_errors.append(f"GSM secret '{secret_name}' not accessible: {str(e)}")
                    
        except Exception as e:
            print(f"  [FAIL] Could not connect to Google Secret Manager: {e}")
            self.validation_errors.append(f"Google Secret Manager not accessible: {str(e)}")
        
        return gsm_secrets
    
    def validate_oauth_credentials(self, env_vars: Dict[str, Optional[str]], gsm_secrets: Dict[str, Optional[str]]) -> None:
        """Validate the actual OAuth credential values."""
        print(f"\n[CHECK] Validating OAuth Credential Values...")
        
        # Determine which credentials to use
        if self.environment == "staging":
            client_id = (gsm_secrets.get("google-oauth-client-id-staging") or 
                        env_vars.get("GOOGLE_OAUTH_CLIENT_ID_STAGING") or 
                        env_vars.get("GOOGLE_CLIENT_ID"))
            client_secret = (gsm_secrets.get("google-oauth-client-secret-staging") or
                           env_vars.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING") or 
                           env_vars.get("GOOGLE_CLIENT_SECRET"))
        elif self.environment == "production":
            client_id = (gsm_secrets.get("google-client-id-production") or
                        env_vars.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION") or 
                        env_vars.get("GOOGLE_CLIENT_ID"))
            client_secret = (gsm_secrets.get("google-client-secret-production") or
                           env_vars.get("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION") or 
                           env_vars.get("GOOGLE_CLIENT_SECRET"))
        else:  # development
            client_id = env_vars.get("GOOGLE_CLIENT_ID")
            client_secret = env_vars.get("GOOGLE_CLIENT_SECRET")
        
        # Validate Google Client ID
        if not client_id:
            self.validation_errors.append(f"No Google Client ID available for {self.environment}")
            print("  [FAIL] Google Client ID: NOT FOUND")
        elif client_id.startswith("REPLACE_"):
            self.validation_errors.append("Google Client ID appears to be a placeholder")
            print(f"  [FAIL] Google Client ID: PLACEHOLDER ({client_id[:30]}...)")
        elif len(client_id) < 50:
            self.validation_errors.append(f"Google Client ID too short ({len(client_id)} chars)")
            print(f"  [FAIL] Google Client ID: TOO SHORT ({len(client_id)} chars)")
        elif not client_id.endswith(".apps.googleusercontent.com"):
            self.validation_warnings.append("Google Client ID doesn't end with .apps.googleusercontent.com")
            print(f"  [WARNING]  Google Client ID: UNUSUAL FORMAT ({client_id[:30]}...)")
        else:
            print(f"  [OK] Google Client ID: VALID ({client_id[:30]}...)")
        
        # Validate Google Client Secret
        if not client_secret:
            self.validation_errors.append(f"No Google Client Secret available for {self.environment}")
            print("  [FAIL] Google Client Secret: NOT FOUND")
        elif client_secret.startswith("REPLACE_"):
            self.validation_errors.append("Google Client Secret appears to be a placeholder")
            print("  [FAIL] Google Client Secret: PLACEHOLDER")
        elif len(client_secret) < 20:
            self.validation_errors.append(f"Google Client Secret too short ({len(client_secret)} chars)")
            print(f"  [FAIL] Google Client Secret: TOO SHORT ({len(client_secret)} chars)")
        else:
            print(f"  [OK] Google Client Secret: VALID ({len(client_secret)} chars)")
    
    def validate_oauth_redirect_uris(self) -> None:
        """Validate OAuth redirect URIs are properly configured."""
        print(f"\n[WEB] Validating OAuth Redirect URIs...")
        
        # Expected redirect URIs for each environment
        if self.environment == "staging":
            expected_domains = [
                "https://netra-frontend-staging-latest-w3h46qmr6q-uc.a.run.app",
                "https://staging.netrasystems.ai",
            ]
        elif self.environment == "production":
            expected_domains = [
                "https://netra-frontend-production-latest-w3h46qmr6q-uc.a.run.app",
                "https://app.netrasystems.ai",
                "https://netrasystems.ai"
            ]
        else:  # development
            expected_domains = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:8080"
            ]
        
        # Check if redirect URIs config file exists
        redirect_config_path = Path(__file__).parent.parent / "config" / "oauth_redirect_uris.json"
        if redirect_config_path.exists():
            try:
                with open(redirect_config_path) as f:
                    redirect_config = json.load(f)
                
                env_config = redirect_config.get(self.environment, {})
                authorized_origins = env_config.get("authorized_javascript_origins", [])
                redirect_uris = env_config.get("authorized_redirect_uris", [])
                
                print(f"  [LIST] Authorized Origins: {len(authorized_origins)}")
                for origin in authorized_origins:
                    print(f"    [U+2022] {origin}")
                
                print(f"  [LIST] Redirect URIs: {len(redirect_uris)}")
                for uri in redirect_uris:
                    print(f"    [U+2022] {uri}")
                
                # Check if expected domains are covered
                missing_domains = []
                for domain in expected_domains:
                    if not any(domain in origin or domain in uri for origin in authorized_origins for uri in redirect_uris):
                        missing_domains.append(domain)
                
                if missing_domains:
                    self.validation_warnings.extend([f"Missing redirect URI for {domain}" for domain in missing_domains])
                    print(f"  [WARNING]  Missing domains: {missing_domains}")
                else:
                    print(f"  [OK] All expected domains covered")
                    
            except Exception as e:
                self.validation_warnings.append(f"Could not read redirect URIs config: {str(e)}")
                print(f"  [WARNING]  Could not read config: {e}")
        else:
            self.validation_warnings.append("OAuth redirect URIs config file not found")
            print(f"  [WARNING]  Config file not found: {redirect_config_path}")
    
    def generate_deployment_report(self) -> str:
        """Generate detailed deployment validation report."""
        report_lines = [
            f"OAuth Deployment Validation Report",
            f"Environment: {self.environment}",
            f"Generated: {os.popen('date').read().strip()}",
            "=" * 60,
        ]
        
        if self.validation_errors:
            report_lines.extend([
                "",
                "[CRITICAL] CRITICAL ERRORS (Deployment MUST NOT Proceed):",
                "-" * 40
            ])
            for i, error in enumerate(self.validation_errors, 1):
                report_lines.append(f"{i}. {error}")
        
        if self.validation_warnings:
            report_lines.extend([
                "",
                "[WARNING]  WARNINGS (Deployment may proceed with caution):",
                "-" * 40
            ])
            for i, warning in enumerate(self.validation_warnings, 1):
                report_lines.append(f"{i}. {warning}")
        
        if not self.validation_errors and not self.validation_warnings:
            report_lines.extend([
                "",
                "[OK] ALL VALIDATIONS PASSED",
                "OAuth configuration is ready for deployment.",
            ])
        
        report_lines.extend([
            "",
            "=" * 60,
            "End of Report"
        ])
        
        return "\n".join(report_lines)
    
    def validate_all(self) -> Tuple[bool, str]:
        """Run all OAuth validations and return success status with report."""
        print(f"[DEPLOY] Starting OAuth Deployment Validation for {self.environment}...")
        
        try:
            # Validate environment variables
            env_vars = self.validate_environment_variables()
            
            # Validate Google Secret Manager (if available)
            gsm_secrets = self.validate_google_secret_manager()
            
            # Validate actual OAuth credentials
            self.validate_oauth_credentials(env_vars, gsm_secrets)
            
            # Validate redirect URIs
            self.validate_oauth_redirect_uris()
            
            # Generate report
            report = self.generate_deployment_report()
            
            # Determine success
            success = len(self.validation_errors) == 0
            
            return success, report
            
        except Exception as e:
            error_report = f"""
[CRITICAL][CRITICAL][CRITICAL] FATAL OAUTH VALIDATION ERROR [CRITICAL][CRITICAL][CRITICAL]

Environment: {self.environment}
Error: {str(e)}

This is a critical error that prevents OAuth validation.
Deployment MUST NOT proceed.

Stack trace available in logs.
[CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL][CRITICAL]
"""
            return False, error_report


def main():
    """Main OAuth deployment validation entry point."""
    parser = argparse.ArgumentParser(description="Validate OAuth configuration before deployment")
    parser.add_argument(
        "--environment", 
        choices=["development", "staging", "production"],
        required=True,
        help="Target deployment environment"
    )
    parser.add_argument(
        "--output-file",
        help="File to write validation report (optional)"
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Treat warnings as errors (fail deployment)"
    )
    parser.add_argument(
        "--deployment-context",
        action="store_true",
        help="Run in deployment context (relaxed validation for missing env vars)"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = OAuthDeploymentValidator(args.environment, deployment_context=args.deployment_context)
    success, report = validator.validate_all()
    
    # Print report
    print("\n" + report)
    
    # Write report to file if requested
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(report)
        print(f"\n[FILE] Report saved to: {args.output_file}")
    
    # Determine exit code
    if not success:
        print("\n[CRITICAL][CRITICAL][CRITICAL] OAUTH DEPLOYMENT VALIDATION FAILED [CRITICAL][CRITICAL][CRITICAL]")
        print("DEPLOYMENT MUST NOT PROCEED - OAuth authentication will be broken!")
        sys.exit(1)
    elif args.fail_on_warnings and validator.validation_warnings:
        print("\n[WARNING]  OAUTH DEPLOYMENT VALIDATION FAILED (Warnings treated as errors)")
        print("Deployment blocked due to --fail-on-warnings flag")
        sys.exit(1)
    else:
        print("\n[OK] OAuth deployment validation PASSED")
        print("Deployment may proceed safely.")
        sys.exit(0)


if __name__ == "__main__":
    main()
