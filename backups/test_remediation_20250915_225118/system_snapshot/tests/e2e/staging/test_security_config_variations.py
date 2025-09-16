from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""Additional security and configuration test variations for staging issues.

These tests provide additional test cases for security and configuration 
issues, testing edge cases and related scenarios for the core problems.
"""

import pytest
import os
import hashlib
import secrets
from typing import Dict, List, Optional
from test_framework.environment_markers import staging_only, env_requires

from shared.isolated_environment import get_env


env = get_env()
class SecurityConfigVariationsTests:
    """Additional test variations for security and configuration issues."""

    @staging_only
    @pytest.mark.e2e
    def test_multiple_secret_keys_all_too_short(self):
        """Test that multiple secret/key environment variables are all too short.
        
        Additional test case: comprehensive check of all secret-related env vars.
        This test should FAIL with multiple short secret keys.
        """
        # All secret/key environment variables that should meet length requirements
        secret_env_vars = {
            "SECRET_KEY": 32,
            "JWT_SECRET": 32,
            "JWT_SECRET_KEY": 32,
            "SESSION_SECRET": 32,
            "AUTH_SECRET": 32,
            "OAUTH_SECRET": 32,
            "ENCRYPTION_KEY": 32,
            "API_SECRET_KEY": 32,
            "SIGNING_KEY": 24,  # Might be shorter
            "CSRF_SECRET": 32
        }
        
        short_secret_failures = []
        missing_secrets = []
        
        for var_name, min_length in secret_env_vars.items():
            
            if not secret_value:
                missing_secrets.append({
                    "variable": var_name,
                    "required_length": min_length,
                    "status": "MISSING"
                })
            elif len(secret_value) < min_length:
                short_secret_failures.append({
                    "variable": var_name,
                    "actual_length": len(secret_value),
                    "required_length": min_length,
                    "deficit": min_length - len(secret_value),
                    "status": "TOO_SHORT"
                })
        
        total_secret_issues = len(short_secret_failures) + len(missing_secrets)
        
        # This test should FAIL - expecting multiple secret configuration issues
        assert total_secret_issues >= 3, (
            f"Expected at least 3 secret/key configuration issues in staging, "
            f"but only found {total_secret_issues}. "
            f"Short secrets: {len(short_secret_failures)}, "
            f"Missing secrets: {len(missing_secrets)}. "
            f"Details - Short: {short_secret_failures}, Missing: {missing_secrets}"
        )
        
        # Verify SECRET_KEY specifically is among the failures
        secret_key_issue = any(
            failure["variable"] == "SECRET_KEY" 
            for failure in short_secret_failures + missing_secrets
        )
        
        assert secret_key_issue, (
            f"Expected SECRET_KEY to be among the configuration issues "
            f"(matching staging audit findings), but SECRET_KEY appears properly configured. "
            f"All issues: {short_secret_failures + missing_secrets}"
        )

    @staging_only
    @pytest.mark.e2e
    def test_secret_key_entropy_quality_insufficient(self):
        """Test secret key entropy quality is insufficient for security.
        
        Additional test case: analyze secret quality beyond just length.
        This test should identify weak secret generation patterns.
        """
        secret_keys_to_test = {
        }
        
        entropy_quality_issues = []
        
        for var_name, secret_value in secret_keys_to_test.items():
            if not secret_value:
                continue  # Skip missing secrets (tested elsewhere)
            
            quality_issues = []
            
            # Test 1: Character diversity
            unique_chars = len(set(secret_value))
            if unique_chars < len(secret_value) * 0.6:  # Less than 60% unique
                quality_issues.append(f"Low character diversity: {unique_chars}/{len(secret_value)}")
            
            # Test 2: Predictable patterns
            if secret_value.lower() in ["secretkey", "mysecretkey", "changeme", "default", "test"]:
                quality_issues.append("Uses predictable default value")
            
            # Test 3: Sequential characters
            sequential_count = 0
            for i in range(len(secret_value) - 2):
                if (ord(secret_value[i]) + 1 == ord(secret_value[i+1]) and 
                    ord(secret_value[i+1]) + 1 == ord(secret_value[i+2])):
                    sequential_count += 1
            
            if sequential_count > 2:
                quality_issues.append(f"Contains sequential patterns: {sequential_count} sequences")
            
            # Test 4: Repeated substrings  
            if len(secret_value) >= 8:
                substring_length = 4
                substrings = {}
                for i in range(len(secret_value) - substring_length + 1):
                    substr = secret_value[i:i+substring_length]
                    substrings[substr] = substrings.get(substr, 0) + 1
                
                repeated_substrings = {k: v for k, v in substrings.items() if v > 1}
                if repeated_substrings:
                    quality_issues.append(f"Repeated substrings: {list(repeated_substrings.keys())}")
            
            if quality_issues:
                entropy_quality_issues.append({
                    "variable": var_name,
                    "length": len(secret_value),
                    "quality_issues": quality_issues,
                    "security_risk": "Weak secret generation"
                })
        
        # This test should FAIL - expecting entropy quality issues
        assert len(entropy_quality_issues) >= 1, (
            f"Expected secret key entropy quality issues in staging "
            f"(explaining weak security configuration), but all secrets appear "
            f"to have good entropy quality. Tested secrets: {list(secret_keys_to_test.keys())}. "
            f"This suggests secret generation has been properly implemented."
        )

    @staging_only
    @pytest.mark.e2e
    def test_oauth_credential_format_validation_failures(self):
        """Test OAuth credentials have incorrect formats or are malformed.
        
        Additional test case: OAuth credential format validation beyond just presence.
        This test should identify malformed OAuth credentials.
        """
        oauth_credentials = {
            "GOOGLE_CLIENT_ID": {
                "pattern": ".apps.googleusercontent.com",
                "min_length": 50,
                "description": "Google OAuth Client ID"
            },
            "GOOGLE_CLIENT_SECRET": {
                "min_length": 24,
                "max_length": 100,
                "description": "Google OAuth Client Secret"
            },
            "GOOGLE_OAUTH_REDIRECT_URI": {
                "pattern": "http",
                "required_content": ["/auth/", "/callback"],
                "description": "OAuth Redirect URI"
            }
        }
        
        credential_format_failures = []
        
        for var_name, requirements in oauth_credentials.items():
            
            if not credential_value:
                credential_format_failures.append({
                    "variable": var_name,
                    "issue": "OAuth credential not set",
                    "description": requirements["description"],
                    "impact": "OAuth authentication will fail"
                })
                continue
            
            # Format validation
            if "pattern" in requirements:
                if requirements["pattern"] not in credential_value:
                    credential_format_failures.append({
                        "variable": var_name,
                        "issue": f"Missing required pattern: {requirements['pattern']}",
                        "value_preview": credential_value[:20] + "...",
                        "impact": "OAuth credential format invalid"
                    })
            
            if "min_length" in requirements:
                if len(credential_value) < requirements["min_length"]:
                    credential_format_failures.append({
                        "variable": var_name,
                        "issue": f"Credential too short: {len(credential_value)} < {requirements['min_length']}",
                        "impact": "OAuth credential likely invalid"
                    })
            
            if "required_content" in requirements:
                for content in requirements["required_content"]:
                    if content not in credential_value:
                        credential_format_failures.append({
                            "variable": var_name,
                            "issue": f"Missing required content: {content}",
                            "value": credential_value,
                            "impact": "OAuth flow configuration error"
                        })
        
        # This test should FAIL - expecting OAuth credential format issues
        assert len(credential_format_failures) >= 2, (
            f"Expected OAuth credential format validation failures in staging "
            f"(explaining OAuth authentication issues), but only {len(credential_format_failures)} "
            f"format issues found. Failures: {credential_format_failures}. "
            f"OAuth credential format issues are common in staging environments."
        )
        
        # Verify missing credentials are among the issues
        missing_credential_issues = [
            failure for failure in credential_format_failures
            if "not set" in failure.get("issue", "")
        ]
        
        assert len(missing_credential_issues) >= 1, (
            f"Expected missing OAuth credentials (primary staging OAuth issue), "
            f"but got other format validation failures: {credential_format_failures}. "
            f"Missing credentials are the fundamental OAuth configuration problem."
        )

    @staging_only 
    @pytest.mark.e2e
    def test_environment_configuration_cross_validation_failures(self):
        """Test environment configuration cross-validation failures.
        
        Additional test case: configuration variables that are inconsistent with each other.
        This test should identify configuration conflicts.
        """
        # Configuration cross-validation rules
        cross_validation_rules = [
            {
                "name": "Environment consistency",
                "primary_var": "ENVIRONMENT",
                "related_vars": ["STAGING", "DEBUG", "PRODUCTION"],
                "rule": "If ENVIRONMENT=staging, STAGING should be true and PRODUCTION false"
            },
            {
                "name": "Database URL consistency", 
                "primary_var": "DATABASE_URL",
                "related_vars": ["STAGING_DATABASE_URL", "DB_HOST"],
                "rule": "Database URLs should reference staging resources"
            },
            {
                "name": "Service URL consistency",
                "primary_var": "BACKEND_URL", 
                "related_vars": ["AUTH_SERVICE_URL", "FRONTEND_URL"],
                "rule": "All service URLs should use same environment domain"
            }
        ]
        
        cross_validation_failures = []
        
        for rule in cross_validation_rules:
            
            if not primary_value:
                cross_validation_failures.append({
                    "rule": rule["name"],
                    "issue": f"Primary variable {rule['primary_var']} not set",
                    "impact": "Cannot validate configuration consistency"
                })
                continue
            
            # Rule-specific validation
            if rule["name"] == "Environment consistency":
                
                if primary_value.lower() == "staging":
                    if staging_var not in ["true", "1", "yes"]:
                        cross_validation_failures.append({
                            "rule": rule["name"],
                            "issue": "ENVIRONMENT=staging but STAGING not set to true",
                            "primary": f"ENVIRONMENT={primary_value}",
                            "related": f"STAGING={staging_var}"
                        })
                    
                    if production_var in ["true", "1", "yes"]:
                        cross_validation_failures.append({
                            "rule": rule["name"],
                            "issue": "ENVIRONMENT=staging but PRODUCTION is true",
                            "primary": f"ENVIRONMENT={primary_value}",
                            "related": f"PRODUCTION={production_var}"
                        })
            
            elif rule["name"] == "Service URL consistency":
                backend_url = primary_value
                
                if backend_url and auth_url:
                    backend_staging = "staging" in backend_url.lower()
                    auth_staging = "staging" in auth_url.lower()
                    
                    if backend_staging != auth_staging:
                        cross_validation_failures.append({
                            "rule": rule["name"],
                            "issue": "Backend and Auth URLs reference different environments",
                            "backend_staging": backend_staging,
                            "auth_staging": auth_staging,
                            "backend_url": backend_url,
                            "auth_url": auth_url
                        })
        
        # This test should FAIL - expecting configuration cross-validation issues
        assert len(cross_validation_failures) >= 1, (
            f"Expected configuration cross-validation failures in staging "
            f"(showing configuration inconsistencies), but all configuration "
            f"appears consistent. Cross-validation rules passed: "
            f"{len(cross_validation_rules) - len(cross_validation_failures)}/{len(cross_validation_rules)}. "
            f"This suggests configuration consistency has been achieved."
        )

    @staging_only
    @pytest.mark.e2e
    def test_security_headers_configuration_missing(self):
        """Test security headers configuration is missing or incorrect.
        
        Additional test case: security-related configuration for HTTP headers.
        This test should identify missing security configurations.
        """
        # Security-related configuration variables
        security_config_vars = {
            "CORS_ORIGINS": {
                "should_contain": ["staging.netrasystems.ai"],
                "should_not_contain": ["*", "localhost"]
            },
            "ALLOWED_HOSTS": {
                "should_contain": ["staging.netrasystems.ai"],
                "should_not_contain": ["*"]
            },
            "SECURE_SSL_REDIRECT": {
                "expected": "true",
                "description": "Should enforce HTTPS in staging"
            },
            "SESSION_COOKIE_SECURE": {
                "expected": "true", 
                "description": "Secure cookies in staging"
            }
        }
        
        security_config_failures = []
        
        for var_name, requirements in security_config_vars.items():
            
            if not config_value:
                security_config_failures.append({
                    "variable": var_name,
                    "issue": "Security configuration variable not set",
                    "description": requirements.get("description", "Security setting"),
                    "impact": "Security vulnerability in staging"
                })
                continue
            
            # Content validation
            if "should_contain" in requirements:
                for required_content in requirements["should_contain"]:
                    if required_content not in config_value:
                        security_config_failures.append({
                            "variable": var_name,
                            "issue": f"Missing required security content: {required_content}",
                            "value": config_value,
                            "impact": "Security configuration incomplete"
                        })
            
            if "should_not_contain" in requirements:
                for forbidden_content in requirements["should_not_contain"]:
                    if forbidden_content in config_value:
                        security_config_failures.append({
                            "variable": var_name,
                            "issue": f"Contains forbidden security content: {forbidden_content}",
                            "value": config_value,
                            "impact": "Security configuration too permissive"
                        })
            
            if "expected" in requirements:
                if config_value.lower() != requirements["expected"]:
                    security_config_failures.append({
                        "variable": var_name,
                        "issue": f"Security setting incorrect",
                        "expected": requirements["expected"],
                        "actual": config_value,
                        "impact": "Security not properly enforced"
                    })
        
        # This test should FAIL - expecting security configuration issues
        assert len(security_config_failures) >= 2, (
            f"Expected security configuration issues in staging "
            f"(showing incomplete security setup), but only {len(security_config_failures)} "
            f"security issues found. Failures: {security_config_failures}. "
            f"Security configuration gaps are common in staging environments."
        )
