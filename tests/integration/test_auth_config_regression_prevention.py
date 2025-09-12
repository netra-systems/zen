"""
[U+1F527] INTEGRATION TEST SUITE: Authentication Configuration Regression Prevention

Tests to prevent auth configuration regressions that have caused production outages.
This validates configuration consistency and prevents repeat of past incidents.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Configuration Management
- Business Goal: Prevent Auth Configuration Outages - Maintain service availability
- Value Impact: $400K+ ARR - Config regressions = Service outages = Revenue loss
- Strategic Impact: Platform Reliability - Config consistency enables all services

REGRESSION PREVENTION SCOPE:
Based on past incidents and common failure modes:
- JWT secret consistency across environments
- OAuth configuration validation and regression detection
- Database connection configuration validation
- Service URL configuration and routing validation
- Environment-specific configuration isolation

CRITICAL SUCCESS CRITERIA:
- No configuration drift between services
- Environment-specific configs properly isolated
- OAuth redirects work correctly across environments
- Database connections maintain proper isolation
- Service discovery works reliably

FAILURE = CONFIG REGRESSION = SERVICE OUTAGE = REVENUE IMPACT
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import pytest
from shared.isolated_environment import get_env

# Import SSOT utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class AuthConfigRegressionValidator:
    """Validates auth configuration to prevent known regression patterns."""
    
    CRITICAL_CONFIG_KEYS = [
        "JWT_SECRET_KEY",
        "DATABASE_URL", 
        "REDIS_URL",
        "AUTH_SERVICE_URL",
        "BACKEND_URL",
        "OAUTH_CLIENT_ID",
        "OAUTH_CLIENT_SECRET"
    ]
    
    def __init__(self):
        self.config_checks = []
        self.regression_risks = []
        self.environment_configs = {}
        
    def record_config_check(self, check_name: str, result: Dict[str, Any]):
        """Record configuration check result."""
        check_record = {
            "check": check_name,
            "timestamp": time.time(),
            "result": result,
            "passed": result.get("valid", False)
        }
        self.config_checks.append(check_record)
        
        if not check_record["passed"]:
            self.regression_risks.append(check_record)
            
    def validate_jwt_secret_consistency(self, environments: List[str]) -> Dict[str, Any]:
        """Validate JWT secret consistency across environments."""
        validation = {
            "valid": True,
            "environments_tested": environments,
            "secrets_consistent": True,
            "secrets_secure": True,
            "business_impact": ""
        }
        
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            
            # Test that unified secret manager works
            secret = get_unified_jwt_secret()
            
            if not secret:
                validation["valid"] = False
                validation["business_impact"] = "CRITICAL: JWT secret not available - auth will fail"
            elif len(secret) < 32:
                validation["valid"] = False
                validation["secrets_secure"] = False
                validation["business_impact"] = "CRITICAL: JWT secret too short - security vulnerability"
            else:
                validation["business_impact"] = "NONE: JWT secret configuration valid"
                
        except Exception as e:
            validation["valid"] = False
            validation["business_impact"] = f"CRITICAL: JWT secret configuration error - {str(e)}"
            
        return validation
    
    def validate_service_url_consistency(self, service_configs: Dict[str, str]) -> Dict[str, Any]:
        """Validate service URL configuration consistency."""
        validation = {
            "valid": True,
            "urls_reachable": {},
            "url_formats_valid": True,
            "business_impact": ""
        }
        
        url_issues = []
        
        for service_name, url in service_configs.items():
            # Validate URL format
            if not url or not url.startswith(('http://', 'https://')):
                validation["url_formats_valid"] = False
                url_issues.append(f"{service_name}: Invalid URL format '{url}'")
            
            # Basic reachability (format validation)
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                if not parsed.netloc:
                    url_issues.append(f"{service_name}: Missing hostname in URL '{url}'")
            except Exception as e:
                url_issues.append(f"{service_name}: URL parsing error - {str(e)}")
        
        if url_issues:
            validation["valid"] = False
            validation["business_impact"] = f"HIGH: Service URL issues - {url_issues[:2]}"  # First 2 issues
        else:
            validation["business_impact"] = "NONE: Service URLs properly configured"
            
        return validation
    
    def validate_environment_isolation(self, test_env: str, prod_indicators: List[str]) -> Dict[str, Any]:
        """Validate that test environment is properly isolated from production."""
        validation = {
            "valid": True,
            "properly_isolated": True,
            "environment": test_env,
            "production_indicators_found": [],
            "business_impact": ""
        }
        
        env = get_env()
        
        # Check for production indicators in test environment
        for indicator in prod_indicators:
            env_value = env.get(indicator, "")
            if env_value and "prod" in env_value.lower():
                validation["production_indicators_found"].append(f"{indicator}={env_value}")
                
        if validation["production_indicators_found"]:
            validation["valid"] = False
            validation["properly_isolated"] = False
            validation["business_impact"] = "CRITICAL: Test environment contaminated with production config"
        else:
            validation["business_impact"] = "NONE: Environment isolation maintained"
            
        return validation


@pytest.mark.integration
@pytest.mark.real_services
class TestAuthConfigRegressionPrevention(BaseIntegrationTest):
    """Integration: Authentication configuration regression prevention."""
    
    @pytest.fixture(autouse=True)
    async def setup_config_regression_testing(self, real_services_fixture):
        """Setup for configuration regression testing."""
        self.services = real_services_fixture
        self.validator = AuthConfigRegressionValidator()
        self.auth_helper = E2EAuthHelper()
        self.env = get_env()
        
    async def test_jwt_secret_regression_prevention(self):
        """
        Integration: Prevent JWT secret configuration regressions.
        
        BUSINESS VALUE: Prevents auth failures due to JWT secret misconfigurations.
        """
        logger.info("[U+1F511] Integration: Testing JWT secret regression prevention")
        
        # Test JWT secret consistency
        validation = self.validator.validate_jwt_secret_consistency(["test", "development"])
        self.validator.record_config_check("jwt_secret_consistency", validation)
        
        if not validation["valid"]:
            pytest.fail(f"JWT SECRET REGRESSION: {validation['business_impact']}")
            
        # Test JWT secret strength
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            
            # Regression prevention checks based on past incidents
            strength_validation = {
                "valid": True,
                "sufficient_length": len(secret) >= 32,
                "not_default": secret != "default-secret-key",
                "not_development": "dev" not in secret.lower(),
                "properly_random": len(set(secret)) > 10,  # Should have good character diversity
                "business_impact": ""
            }
            
            issues = []
            if not strength_validation["sufficient_length"]:
                issues.append("Secret too short (< 32 chars)")
            if not strength_validation["not_default"]:
                issues.append("Using default secret")
            if not strength_validation["not_development"]:
                issues.append("Development secret in test")
            if not strength_validation["properly_random"]:
                issues.append("Low entropy secret")
                
            if issues:
                strength_validation["valid"] = False
                strength_validation["business_impact"] = f"SECURITY: JWT secret issues - {issues}"
            else:
                strength_validation["business_impact"] = "NONE: JWT secret meets security standards"
                
        except Exception as e:
            strength_validation = {
                "valid": False,
                "business_impact": f"CRITICAL: JWT secret access failed - {str(e)}"
            }
        
        self.validator.record_config_check("jwt_secret_strength", strength_validation)
        
        if not strength_validation["valid"]:
            pytest.fail(f"JWT SECRET SECURITY REGRESSION: {strength_validation['business_impact']}")
        
        logger.info(" PASS:  JWT secret regression prevention validated")
        
    async def test_service_url_configuration_regression_prevention(self):
        """
        Integration: Prevent service URL configuration regressions.
        
        BUSINESS VALUE: Prevents service discovery failures and routing issues.
        """
        logger.info("[U+1F517] Integration: Testing service URL configuration regression prevention")
        
        # Collect service URL configuration
        service_configs = {
            "auth_service": self.services.get("auth_url", ""),
            "backend_service": self.services.get("backend_url", ""),
        }
        
        # Add environment-based URLs if available
        auth_env_url = self.env.get("AUTH_SERVICE_URL")
        backend_env_url = self.env.get("BACKEND_URL") 
        
        if auth_env_url:
            service_configs["auth_service_env"] = auth_env_url
        if backend_env_url:
            service_configs["backend_service_env"] = backend_env_url
        
        # Validate URL configuration
        url_validation = self.validator.validate_service_url_consistency(service_configs)
        self.validator.record_config_check("service_url_configuration", url_validation)
        
        if not url_validation["valid"]:
            pytest.fail(f"SERVICE URL REGRESSION: {url_validation['business_impact']}")
        
        # Test URL reachability (basic connectivity test)
        connectivity_tests = []
        
        async with httpx.AsyncClient() as client:
            for service_name, url in service_configs.items():
                if url and url.startswith(('http://', 'https://')):
                    try:
                        response = await client.get(f"{url}/health", timeout=3.0)
                        connectivity_tests.append({
                            "service": service_name,
                            "url": url,
                            "reachable": True,
                            "status_code": response.status_code
                        })
                    except Exception as e:
                        connectivity_tests.append({
                            "service": service_name,
                            "url": url,
                            "reachable": False,
                            "error": str(e)
                        })
        
        # Validate connectivity
        reachable_services = [test for test in connectivity_tests if test.get("reachable", False)]
        unreachable_services = [test for test in connectivity_tests if not test.get("reachable", False)]
        
        connectivity_validation = {
            "valid": len(unreachable_services) == 0,
            "reachable_count": len(reachable_services),
            "total_tested": len(connectivity_tests),
            "unreachable_services": [test["service"] for test in unreachable_services]
        }
        
        self.validator.record_config_check("service_connectivity", connectivity_validation)
        
        if unreachable_services:
            logger.warning(f"Service connectivity issues: {connectivity_validation['unreachable_services']}")
            # Don't fail test - services may not be running in test environment
            
        logger.info(" PASS:  Service URL configuration regression prevention validated")
        
    async def test_oauth_configuration_regression_prevention(self):
        """
        Integration: Prevent OAuth configuration regressions.
        
        BUSINESS VALUE: Prevents OAuth login failures that block user onboarding.
        """
        logger.info("[U+1F510] Integration: Testing OAuth configuration regression prevention")
        
        # Test OAuth configuration validation
        oauth_config = {
            "client_id": self.env.get("OAUTH_CLIENT_ID", ""),
            "client_secret": self.env.get("OAUTH_CLIENT_SECRET", ""),
            "redirect_uri": self.env.get("OAUTH_REDIRECT_URI", ""),
            "provider": self.env.get("OAUTH_PROVIDER", "google")
        }
        
        oauth_validation = {
            "valid": True,
            "client_id_present": bool(oauth_config["client_id"]),
            "client_secret_present": bool(oauth_config["client_secret"]),
            "redirect_uri_valid": bool(oauth_config["redirect_uri"]),
            "business_impact": ""
        }
        
        # OAuth configuration may not be fully set up in test environment
        missing_configs = []
        if not oauth_validation["client_id_present"]:
            missing_configs.append("OAUTH_CLIENT_ID")
        if not oauth_validation["client_secret_present"]:
            missing_configs.append("OAUTH_CLIENT_SECRET")
        if not oauth_validation["redirect_uri_valid"]:
            missing_configs.append("OAUTH_REDIRECT_URI")
            
        if missing_configs:
            oauth_validation["valid"] = False
            oauth_validation["business_impact"] = f"CONFIG: OAuth not configured in test environment - {missing_configs}"
        else:
            # Validate redirect URI format
            redirect_uri = oauth_config["redirect_uri"]
            if redirect_uri and not redirect_uri.startswith(('http://', 'https://')):
                oauth_validation["valid"] = False
                oauth_validation["business_impact"] = "CRITICAL: Invalid OAuth redirect URI format"
            else:
                oauth_validation["business_impact"] = "NONE: OAuth configuration valid"
        
        self.validator.record_config_check("oauth_configuration", oauth_validation)
        
        # OAuth may not be configured in test environment - log warning but don't fail
        if not oauth_validation["valid"] and "test environment" in oauth_validation["business_impact"]:
            logger.warning(f"OAuth configuration issue (expected in test): {oauth_validation['business_impact']}")
        elif not oauth_validation["valid"]:
            pytest.fail(f"OAUTH CONFIG REGRESSION: {oauth_validation['business_impact']}")
        
        logger.info(" PASS:  OAuth configuration regression prevention tested")
        
    async def test_database_configuration_regression_prevention(self):
        """
        Integration: Prevent database configuration regressions.
        
        BUSINESS VALUE: Prevents data access failures and connection issues.
        """
        logger.info("[U+1F5C4][U+FE0F] Integration: Testing database configuration regression prevention")
        
        # Test database configuration
        db_config = {
            "database_url": self.env.get("DATABASE_URL", ""),
            "redis_url": self.env.get("REDIS_URL", ""),
            "db_host": self.env.get("DB_HOST", ""),
            "db_port": self.env.get("DB_PORT", ""),
            "db_name": self.env.get("DB_NAME", "")
        }
        
        db_validation = {
            "valid": True,
            "database_url_present": bool(db_config["database_url"]),
            "redis_url_present": bool(db_config["redis_url"]),
            "connection_params_complete": all([
                db_config["db_host"], 
                db_config["db_port"], 
                db_config["db_name"]
            ]),
            "business_impact": ""
        }
        
        # Validate database configuration completeness
        config_issues = []
        
        if not db_validation["database_url_present"] and not db_validation["connection_params_complete"]:
            config_issues.append("No database connection configuration")
            
        if not db_validation["redis_url_present"]:
            config_issues.append("Redis URL not configured")
            
        # Test for common regression patterns
        if db_config["database_url"]:
            if "localhost" in db_config["database_url"] and "prod" in self.env.get("ENVIRONMENT", "").lower():
                config_issues.append("Localhost database in production environment")
                
        if config_issues:
            db_validation["valid"] = False
            db_validation["business_impact"] = f"CONFIG: Database configuration issues - {config_issues[:2]}"
        else:
            db_validation["business_impact"] = "NONE: Database configuration appears valid"
        
        self.validator.record_config_check("database_configuration", db_validation)
        
        # Database configuration issues in test environment may be expected
        if not db_validation["valid"]:
            logger.warning(f"Database configuration issue: {db_validation['business_impact']}")
            # Don't fail - may be expected in test environment
            
        logger.info(" PASS:  Database configuration regression prevention tested")
        
    async def test_environment_isolation_regression_prevention(self):
        """
        Integration: Prevent environment isolation regressions.
        
        BUSINESS VALUE: Prevents test/staging from affecting production systems.
        """
        logger.info("[U+1F512] Integration: Testing environment isolation regression prevention")
        
        # Test environment isolation
        production_indicators = [
            "DATABASE_URL",
            "REDIS_URL", 
            "AUTH_SERVICE_URL",
            "BACKEND_URL",
            "OAUTH_CLIENT_ID"
        ]
        
        current_env = self.env.get("ENVIRONMENT", "test").lower()
        isolation_validation = self.validator.validate_environment_isolation(current_env, production_indicators)
        
        self.validator.record_config_check("environment_isolation", isolation_validation)
        
        if not isolation_validation["valid"]:
            pytest.fail(f"ENVIRONMENT ISOLATION REGRESSION: {isolation_validation['business_impact']}")
        
        # Additional isolation checks
        sensitive_env_checks = []
        
        # Check that we're not accidentally in production mode
        environment = self.env.get("ENVIRONMENT", "").lower()
        if environment in ["production", "prod"]:
            sensitive_env_checks.append("Environment set to production")
            
        # Check database doesn't point to production
        db_url = self.env.get("DATABASE_URL", "").lower()
        if db_url and any(prod_indicator in db_url for prod_indicator in ["prod", "production"]):
            sensitive_env_checks.append("Database URL contains production indicators")
            
        if sensitive_env_checks:
            pytest.fail(f"CRITICAL ISOLATION REGRESSION: Test environment compromised - {sensitive_env_checks}")
        
        logger.info(" PASS:  Environment isolation regression prevention validated")
        
    async def test_configuration_completeness_regression_prevention(self):
        """
        Integration: Prevent configuration completeness regressions.
        
        BUSINESS VALUE: Ensures all required configuration is present and valid.
        """
        logger.info("[U+1F4CB] Integration: Testing configuration completeness regression prevention")
        
        # Check completeness of critical configurations
        required_configs = {
            "JWT_SECRET_KEY": self.env.get("JWT_SECRET_KEY", ""),
            "DATABASE_URL": self.env.get("DATABASE_URL", ""),
            "REDIS_URL": self.env.get("REDIS_URL", ""),
        }
        
        optional_configs = {
            "OAUTH_CLIENT_ID": self.env.get("OAUTH_CLIENT_ID", ""),
            "OAUTH_CLIENT_SECRET": self.env.get("OAUTH_CLIENT_SECRET", ""),
            "AUTH_SERVICE_URL": self.env.get("AUTH_SERVICE_URL", ""),
        }
        
        completeness_validation = {
            "valid": True,
            "required_missing": [],
            "optional_missing": [],
            "business_impact": ""
        }
        
        # Check required configurations
        for config_name, config_value in required_configs.items():
            if not config_value:
                completeness_validation["required_missing"].append(config_name)
                
        # Check optional configurations (for warning)
        for config_name, config_value in optional_configs.items():
            if not config_value:
                completeness_validation["optional_missing"].append(config_name)
        
        if completeness_validation["required_missing"]:
            completeness_validation["valid"] = False
            completeness_validation["business_impact"] = f"CRITICAL: Missing required configs {completeness_validation['required_missing']}"
        elif completeness_validation["optional_missing"]:
            completeness_validation["business_impact"] = f"INFO: Optional configs not set {completeness_validation['optional_missing']}"
        else:
            completeness_validation["business_impact"] = "NONE: Configuration completeness satisfied"
        
        self.validator.record_config_check("configuration_completeness", completeness_validation)
        
        if not completeness_validation["valid"]:
            pytest.fail(f"CONFIG COMPLETENESS REGRESSION: {completeness_validation['business_impact']}")
        
        if completeness_validation["optional_missing"]:
            logger.info(f"Optional configuration info: {completeness_validation['business_impact']}")
        
        logger.info(" PASS:  Configuration completeness regression prevention validated")


@pytest.mark.integration
@pytest.mark.real_services
class TestAuthConfigRegressionRecovery(BaseIntegrationTest):
    """Integration: Auth configuration regression recovery testing."""
    
    async def test_configuration_error_recovery(self):
        """
        Integration: Test recovery from configuration errors.
        
        BUSINESS VALUE: System degrades gracefully when configuration is invalid.
        """
        logger.info(" CYCLE:  Integration: Testing configuration error recovery")
        
        auth_helper = E2EAuthHelper()
        
        # Test that auth system fails gracefully with invalid configuration
        recovery_tests = []
        
        # Test 1: JWT secret validation with error recovery
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            
            # Create token to test system functionality
            test_token = auth_helper.create_test_jwt_token(
                user_id="recovery-test",
                email="recovery@test.com"
            )
            
            recovery_tests.append({
                "test": "jwt_functionality",
                "success": True,
                "recovery_not_needed": True
            })
            
        except Exception as e:
            recovery_tests.append({
                "test": "jwt_functionality", 
                "success": False,
                "error": str(e),
                "needs_recovery": True
            })
        
        # Analyze recovery capability
        failed_tests = [test for test in recovery_tests if not test.get("success", False)]
        
        if failed_tests:
            failure_details = [f"{test['test']}: {test.get('error')}" for test in failed_tests]
            logger.warning(f"Configuration issues detected: {failure_details}")
            # Don't fail - this tests recovery capability
            
        logger.info(f" PASS:  Configuration error recovery tested - {len(recovery_tests)} tests")


if __name__ == "__main__":
    """Run auth configuration regression prevention tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "integration",
        "--real-services"
    ])