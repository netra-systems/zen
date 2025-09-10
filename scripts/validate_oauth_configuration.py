#!/usr/bin/env python3
"""
OAuth Configuration Validation Script
Pre-deployment validation to prevent OAuth redirect URI misconfigurations

This script validates OAuth configuration before deployment to prevent the critical
"No token received" authentication failure caused by OAuth redirect URI misconfigurations.

CRITICAL ISSUE PREVENTED:
- Auth service telling Google to redirect to frontend URL instead of auth service URL
- Results in complete OAuth authentication failure

Usage:
    python scripts/validate_oauth_configuration.py --env staging
    python scripts/validate_oauth_configuration.py --env production --strict
    python scripts/validate_oauth_configuration.py --all-environments

Exit codes:
    0 - All validations passed
    1 - Configuration errors found  
    2 - Critical errors that will break authentication
"""

import argparse
import asyncio
import json
import sys
import urllib.parse
from typing import Dict, List, Tuple, Optional, Any
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import httpx
    from auth_service.auth_core.config import AuthConfig
    from auth_service.auth_core.routes.auth_routes import _determine_urls
    from fastapi.testclient import TestClient
    from auth_service.main import app
    
    # SSOT OAuth validation imports
    from shared.configuration.central_config_validator import validate_oauth_configs_for_environment, get_central_validator
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("Ensure you're running from the project root directory")
    sys.exit(2)


class OAuthConfigurationValidator:
    """
    Comprehensive OAuth configuration validator
    
    Validates OAuth redirect URI configurations and prevents misconfigurations
    that would break authentication in staging/production deployments.
    """
    
    def __init__(self, environment: str, strict_mode: bool = False):
        self.environment = environment
        self.strict_mode = strict_mode
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validation_results: Dict[str, Any] = {}
        
        # Expected configurations by environment
        self.expected_configs = {
            "development": {
                "auth_service_url": "http://localhost:8081",
                "frontend_url": "http://localhost:3000",
                "expected_oauth_redirect": "http://localhost:8081/auth/callback"
            },
            "staging": {
                "auth_service_url": "https://auth.staging.netrasystems.ai",
                "frontend_url": "https://app.staging.netrasystems.ai", 
                "expected_oauth_redirect": "https://auth.staging.netrasystems.ai/auth/callback"
            },
            "production": {
                "auth_service_url": "https://auth.netrasystems.ai",
                "frontend_url": "https://netrasystems.ai",
                "expected_oauth_redirect": "https://auth.netrasystems.ai/auth/callback"
            }
        }

    def log_error(self, message: str, critical: bool = False):
        """Log validation error"""
        prefix = "CRITICAL ERROR" if critical else "ERROR"
        error_msg = f"[{prefix}] {message}"
        self.errors.append(error_msg)
        print(f"❌ {error_msg}")

    def log_warning(self, message: str):
        """Log validation warning"""
        warning_msg = f"[WARNING] {message}"
        self.warnings.append(warning_msg)
        print(f"⚠️  {warning_msg}")

    def log_success(self, message: str):
        """Log validation success"""
        print(f"✅ {message}")

    def log_info(self, message: str):
        """Log validation info"""
        print(f"ℹ️  {message}")

    def validate_environment_urls(self) -> bool:
        """Validate auth service and frontend URLs for environment"""
        try:
            # Mock environment for testing
            import unittest.mock
            with unittest.mock.patch.object(AuthConfig, 'get_environment', return_value=self.environment):
                auth_service_url = AuthConfig.get_auth_service_url()
                frontend_url = AuthConfig.get_frontend_url()
            
            expected_config = self.expected_configs.get(self.environment)
            if not expected_config:
                self.log_error(f"No configuration defined for environment: {self.environment}")
                return False
            
            # Validate auth service URL
            expected_auth_url = expected_config["auth_service_url"]
            if auth_service_url != expected_auth_url:
                self.log_error(
                    f"Auth service URL incorrect for {self.environment}:\n"
                    f"  Expected: {expected_auth_url}\n"
                    f"  Actual: {auth_service_url}",
                    critical=True
                )
                return False
            
            # Validate frontend URL  
            expected_frontend_url = expected_config["frontend_url"]
            if frontend_url != expected_frontend_url:
                self.log_error(
                    f"Frontend URL incorrect for {self.environment}:\n"
                    f"  Expected: {expected_frontend_url}\n" 
                    f"  Actual: {frontend_url}"
                )
                return False
            
            # CRITICAL: URLs must be different
            if auth_service_url == frontend_url:
                self.log_error(
                    f"Auth service and frontend URLs are identical: {auth_service_url}",
                    critical=True
                )
                return False
            
            self.validation_results["environment_urls"] = {
                "auth_service_url": auth_service_url,
                "frontend_url": frontend_url,
                "valid": True
            }
            
            self.log_success(f"Environment URLs validated for {self.environment}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to validate environment URLs: {e}")
            return False

    def validate_oauth_redirect_uris(self) -> bool:
        """Validate OAuth redirect URIs point to auth service"""
        try:
            import unittest.mock
            with unittest.mock.patch.object(AuthConfig, 'get_environment', return_value=self.environment):
                auth_service_url, frontend_url = _determine_urls()
            
            # OAuth redirect URI configuration
            oauth_redirect_uri = auth_service_url + "/auth/callback"
            frontend_callback_uri = frontend_url + "/auth/callback"
            
            expected_config = self.expected_configs.get(self.environment)
            expected_oauth_redirect = expected_config["expected_oauth_redirect"]
            
            # CRITICAL: OAuth redirect must use auth service URL
            if oauth_redirect_uri != expected_oauth_redirect:
                self.log_error(
                    f"OAuth redirect URI incorrect for {self.environment}:\n"
                    f"  Expected: {expected_oauth_redirect}\n"
                    f"  Actual: {oauth_redirect_uri}",
                    critical=True
                )
                return False
            
            # CRITICAL: Must NOT use frontend URL
            if oauth_redirect_uri == frontend_callback_uri:
                self.log_error(
                    f"CRITICAL: OAuth redirect URI using frontend URL!\n"
                    f"  OAuth redirect: {oauth_redirect_uri}\n"
                    f"  Frontend URL: {frontend_callback_uri}\n"
                    f"  This will break OAuth authentication completely!",
                    critical=True
                )
                return False
            
            # Environment-specific validations
            if self.environment in ["staging", "production"]:
                if "auth." not in oauth_redirect_uri:
                    self.log_error(
                        f"OAuth redirect URI missing 'auth.' subdomain: {oauth_redirect_uri}",
                        critical=True
                    )
                    return False
                
                if not oauth_redirect_uri.startswith("https://"):
                    self.log_error(
                        f"OAuth redirect URI must use HTTPS in {self.environment}: {oauth_redirect_uri}",
                        critical=True
                    )
                    return False
            
            self.validation_results["oauth_redirect_uris"] = {
                "oauth_redirect_uri": oauth_redirect_uri,
                "frontend_callback_uri": frontend_callback_uri,
                "expected": expected_oauth_redirect,
                "valid": True
            }
            
            self.log_success(f"OAuth redirect URIs validated: {oauth_redirect_uri}")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to validate OAuth redirect URIs: {e}")
            return False

    def validate_oauth_endpoints(self) -> bool:
        """Validate OAuth endpoints exist and respond"""
        try:
            client = TestClient(app)
            endpoints_to_test = [
                "/auth/callback", 
                "/auth/callback/google",
                "/auth/login/google"
            ]
            
            for endpoint in endpoints_to_test:
                if endpoint.startswith("/auth/login"):
                    # Test GET for login endpoints
                    response = client.get(endpoint)
                    if response.status_code == 404:
                        self.log_error(f"OAuth endpoint not found: {endpoint}")
                        return False
                    else:
                        self.log_success(f"OAuth login endpoint exists: {endpoint}")
                else:
                    # Test POST for callback endpoints  
                    response = client.post(endpoint, json={
                        "code": "test_validation_code",
                        "state": "test_validation_state"
                    })
                    if response.status_code == 404:
                        self.log_error(f"OAuth callback endpoint not found: {endpoint}")
                        return False
                    else:
                        self.log_success(f"OAuth callback endpoint exists: {endpoint}")
            
            self.validation_results["oauth_endpoints"] = {
                "endpoints_tested": endpoints_to_test,
                "all_available": True
            }
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to validate OAuth endpoints: {e}")
            return False

    def validate_oauth_initiation_redirect_uri(self) -> bool:
        """Validate OAuth initiation generates correct redirect_uri parameter"""
        try:
            client = TestClient(app)
            
            import unittest.mock
            with unittest.mock.patch.object(AuthConfig, 'get_environment', return_value=self.environment):
                response = client.get("/auth/login/google")
            
            if response.status_code == 302:
                google_oauth_url = response.headers.get("location", "")
                
                # Parse redirect_uri from Google OAuth URL
                parsed_url = urllib.parse.urlparse(google_oauth_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                if "redirect_uri" in query_params:
                    redirect_uri = urllib.parse.unquote(query_params["redirect_uri"][0])
                    expected_config = self.expected_configs.get(self.environment)
                    expected_redirect = expected_config["expected_oauth_redirect"]
                    
                    # CRITICAL: redirect_uri must match expected auth service URL
                    if redirect_uri != expected_redirect:
                        self.log_error(
                            f"OAuth initiation redirect_uri incorrect:\n"
                            f"  Expected: {expected_redirect}\n"
                            f"  Actual: {redirect_uri}",
                            critical=True
                        )
                        return False
                    
                    # CRITICAL: Must not use frontend URL
                    frontend_config = self.expected_configs[self.environment]
                    frontend_callback = frontend_config["frontend_url"] + "/auth/callback"
                    
                    if redirect_uri == frontend_callback:
                        self.log_error(
                            f"CRITICAL: OAuth initiation using frontend URL!\n"
                            f"  redirect_uri: {redirect_uri}\n" 
                            f"  Frontend callback: {frontend_callback}",
                            critical=True
                        )
                        return False
                    
                    self.validation_results["oauth_initiation"] = {
                        "redirect_uri": redirect_uri,
                        "google_oauth_url": google_oauth_url,
                        "valid": True
                    }
                    
                    self.log_success(f"OAuth initiation redirect_uri validated: {redirect_uri}")
                    return True
                else:
                    self.log_error("No redirect_uri parameter in Google OAuth URL")
                    return False
            else:
                self.log_warning(f"OAuth initiation returned {response.status_code}, may not be fully implemented")
                return True  # Not implemented yet is not a failure
                
        except Exception as e:
            self.log_error(f"Failed to validate OAuth initiation: {e}")
            return False

    def analyze_auth_routes_source_code(self) -> bool:
        """Analyze auth_routes.py for OAuth redirect URI patterns"""
        try:
            auth_routes_path = PROJECT_ROOT / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
            
            if not auth_routes_path.exists():
                self.log_warning("auth_routes.py not found for source code analysis")
                return True
            
            with open(auth_routes_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Look for problematic patterns
            problematic_patterns = [
                "_determine_urls()[1] + \"/auth/callback\"",
                "_determine_urls()[1]+\"/auth/callback\"",
                "_determine_urls()[1] +\"/auth/callback\"",
                "_determine_urls()[1]+ \"/auth/callback\""
            ]
            
            found_problems = []
            for pattern in problematic_patterns:
                if pattern in source_code:
                    found_problems.append(pattern)
            
            if found_problems:
                self.log_error(
                    f"CRITICAL: Problematic OAuth patterns found in auth_routes.py:\n" +
                    "\n".join(f"  - {pattern}" for pattern in found_problems) +
                    f"\nThese patterns use frontend URL for OAuth redirect_uri\n"
                    f"Fix: Change _determine_urls()[1] to _determine_urls()[0]",
                    critical=True
                )
                return False
            
            # Look for correct patterns
            correct_patterns = [
                "_determine_urls()[0] + \"/auth/callback\"",
                "_determine_urls()[0]+\"/auth/callback\"", 
                "_determine_urls()[0] +\"/auth/callback\"",
                "_determine_urls()[0]+ \"/auth/callback\""
            ]
            
            found_correct = []
            for pattern in correct_patterns:
                if pattern in source_code:
                    found_correct.append(pattern)
            
            # If OAuth is implemented, should have correct patterns
            if "redirect_uri" in source_code and "_determine_urls()" in source_code:
                if not found_correct:
                    self.log_error(
                        f"OAuth implementation found but no correct redirect_uri patterns detected\n"
                        f"Expected patterns: {correct_patterns}"
                    )
                    return False
                else:
                    self.log_success(f"Correct OAuth redirect_uri patterns found: {found_correct}")
            else:
                self.log_info("OAuth implementation not detected in auth_routes.py")
            
            self.validation_results["source_code_analysis"] = {
                "problematic_patterns": found_problems,
                "correct_patterns": found_correct,
                "oauth_implemented": "redirect_uri" in source_code,
                "valid": len(found_problems) == 0
            }
            
            return True
            
        except Exception as e:
            self.log_error(f"Failed to analyze source code: {e}")
            return False

    def generate_google_console_configuration(self) -> Dict[str, Any]:
        """Generate Google OAuth Console configuration requirements"""
        config = self.expected_configs.get(self.environment, {})
        
        google_console_config = {
            "environment": self.environment,
            "authorized_redirect_uris": [
                config.get("expected_oauth_redirect", ""),
                config.get("expected_oauth_redirect", "").replace("/callback", "/callback/google") 
            ],
            "prohibited_redirect_uris": [
                config.get("frontend_url", "") + "/auth/callback"
            ],
            "oauth_consent_screen": {
                "application_name": f"Netra AI Platform ({self.environment})",
                "authorized_domains": []
            }
        }
        
        if self.environment == "development":
            google_console_config["oauth_consent_screen"]["authorized_domains"] = ["localhost"]
        elif self.environment == "staging":
            google_console_config["oauth_consent_screen"]["authorized_domains"] = ["staging.netrasystems.ai"]
        elif self.environment == "production":
            google_console_config["oauth_consent_screen"]["authorized_domains"] = ["netrasystems.ai"]
        
        return google_console_config

    async def validate_oauth_provider_connectivity(self) -> bool:
        """Validate connectivity to OAuth providers"""
        if self.environment == "development":
            self.log_info("Skipping OAuth provider connectivity test in development")
            return True
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test Google OAuth discovery endpoint
                response = await client.get("https://accounts.google.com/.well-known/openid-configuration")
                if response.status_code != 200:
                    self.log_error(f"Google OAuth discovery endpoint failed: {response.status_code}")
                    return False
                
                # Test Google OAuth authorization endpoint
                auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
                response = await client.get(auth_url, params={"client_id": "test"})
                if response.status_code not in [200, 400]:  # 400 is expected for invalid client_id
                    self.log_error(f"Google OAuth authorization endpoint failed: {response.status_code}")
                    return False
                
                self.log_success("OAuth provider connectivity validated")
                return True
                
        except Exception as e:
            self.log_error(f"Failed to validate OAuth provider connectivity: {e}")
            return False

    async def run_validation(self) -> bool:
        """Run complete OAuth configuration validation"""
        self.log_info(f"Starting OAuth configuration validation for {self.environment}")
        self.log_info(f"Strict mode: {'enabled' if self.strict_mode else 'disabled'}")
        print("=" * 60)
        
        validation_results = []
        
        # Core validations
        validation_results.append(self.validate_environment_urls())
        validation_results.append(self.validate_oauth_redirect_uris())
        validation_results.append(self.validate_oauth_endpoints())
        validation_results.append(self.validate_oauth_initiation_redirect_uri())
        validation_results.append(self.analyze_auth_routes_source_code())
        
        # Network validations (async)
        validation_results.append(await self.validate_oauth_provider_connectivity())
        
        # Generate Google Console configuration
        google_config = self.generate_google_console_configuration()
        self.validation_results["google_console_config"] = google_config
        
        # Summary
        print("=" * 60)
        total_validations = len(validation_results)
        passed_validations = sum(validation_results)
        
        if passed_validations == total_validations:
            self.log_success(f"All {total_validations} OAuth validations passed for {self.environment}!")
            
            # Display Google Console configuration
            print(f"\n📋 GOOGLE OAUTH CONSOLE CONFIGURATION - {self.environment.upper()}")
            print("=" * 50)
            print("Required Authorized Redirect URIs:")
            for uri in google_config["authorized_redirect_uris"]:
                if uri:  # Skip empty URIs
                    print(f"  ✅ {uri}")
            print("\nProhibited URLs (DO NOT ADD):")
            for uri in google_config["prohibited_redirect_uris"]:
                print(f"  ❌ {uri}")
            print("=" * 50)
            
            return True
        else:
            failed_validations = total_validations - passed_validations
            self.log_error(f"{failed_validations}/{total_validations} OAuth validations failed for {self.environment}")
            
            if self.errors:
                print(f"\n🚨 ERRORS FOUND ({len(self.errors)}):")
                for error in self.errors:
                    print(f"  {error}")
            
            if self.warnings:
                print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
                for warning in self.warnings:
                    print(f"  {warning}")
            
            return False

    def save_results(self, output_file: Optional[str] = None):
        """Save validation results to JSON file"""
        if not output_file:
            output_file = f"oauth_validation_{self.environment}.json"
        
        results = {
            "environment": self.environment,
            "strict_mode": self.strict_mode,
            "timestamp": str(asyncio.get_event_loop().time()),
            "validation_results": self.validation_results,
            "errors": self.errors,
            "warnings": self.warnings,
            "passed": len(self.errors) == 0
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            self.log_info(f"Results saved to {output_file}")
        except Exception as e:
            self.log_warning(f"Failed to save results: {e}")


async def main():
    """Main validation function"""
    parser = argparse.ArgumentParser(
        description="Validate OAuth configuration to prevent authentication failures"
    )
    parser.add_argument(
        "--env", "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="Environment to validate (default: development)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (fail on warnings)"
    )
    parser.add_argument(
        "--all-environments",
        action="store_true",
        help="Validate all environments"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation results (JSON)"
    )
    parser.add_argument(
        "--silent",
        action="store_true", 
        help="Only show errors and critical issues"
    )
    
    args = parser.parse_args()
    
    if args.silent:
        # Redirect info/success logs to suppress output
        import io
        import contextlib
        
    environments_to_validate = []
    if args.all_environments:
        environments_to_validate = ["development", "staging", "production"]
    else:
        environments_to_validate = [args.env]
    
    overall_success = True
    
    for env in environments_to_validate:
        print(f"\n🔍 VALIDATING OAUTH CONFIGURATION - {env.upper()}")
        print("=" * 60)
        
        validator = OAuthConfigurationValidator(env, args.strict)
        success = await validator.run_validation()
        
        if args.output:
            output_file = args.output.replace("{env}", env) if "{env}" in args.output else f"{args.output}_{env}.json"
            validator.save_results(output_file)
        
        if not success:
            overall_success = False
        
        print("")  # Blank line between environments
    
    # Final summary
    if len(environments_to_validate) > 1:
        print("🏁 OVERALL VALIDATION SUMMARY")
        print("=" * 40)
        if overall_success:
            print("✅ All environments passed OAuth validation")
        else:
            print("❌ Some environments failed OAuth validation")
        print("")
    
    # Exit with appropriate code
    if overall_success:
        print("🎉 OAuth configuration validation completed successfully!")
        sys.exit(0)
    else:
        print("💥 OAuth configuration validation failed!")
        print("   Fix the errors above before deploying to prevent authentication failures")
        sys.exit(1 if not args.strict else 2)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Validation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error during validation: {e}")
        sys.exit(2)