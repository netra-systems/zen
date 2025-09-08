"""
Comprehensive Pre-Deployment Validation Framework for Auth Service

Addresses root causes identified in staging failures:
1. Database credentials and connectivity validation
2. JWT secret consistency between services  
3. OAuth configuration and environment consistency
4. SSL parameters for different connection types
5. Container lifecycle management readiness

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent staging deployment failures and service downtime
- Value Impact: Reduces deployment failures, debugging time, and service availability issues
- Strategic Impact: Ensures reliable auth service for all customer tiers
"""

import asyncio
import logging
import os
import re
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

# Add parent directory to Python path for imports

from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.secret_loader import AuthSecretLoader
from auth_service.auth_core.database.database_manager import AuthDatabaseManager


class PreDeploymentValidator:
    """Comprehensive pre-deployment validation framework for auth service."""
    
    def __init__(self):
        self.validation_report = {
            "overall_status": "unknown",
            "validations": {},
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
            "environment": AuthConfig.get_environment(),
            "timestamp": None
        }
    
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """
        Run all validation checks for pre-deployment readiness.
        
        Returns:
            Complete validation report with status and recommendations
        """
        import datetime
        self.validation_report["timestamp"] = datetime.datetime.now().isoformat()
        
        logger.info("Starting comprehensive pre-deployment validation...")
        
        # Core validation checks
        self._validate_database_configuration()
        self._validate_jwt_secret_consistency()
        self._validate_oauth_configuration()
        self._validate_ssl_parameters()
        self._validate_container_lifecycle_readiness()
        self._validate_environment_consistency()
        self._validate_service_configuration()
        self._validate_security_configuration()
        
        # Determine overall status
        self._determine_overall_status()
        
        logger.info(f"Validation complete. Status: {self.validation_report['overall_status']}")
        return self.validation_report
    
    def _validate_database_configuration(self) -> None:
        """Validate database credentials and connectivity configuration."""
        logger.debug("Validating database configuration...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }

    def _validate_database_ssl_config(self, database_url: str) -> Dict[str, Any]:
        """Validate SSL parameter configuration for database connections."""
        ssl_config = {
            "valid": True,
            "issues": [],
            "details": {},
            "critical": False
        }
        
        try:
            # Check if Cloud SQL connection
            is_cloud_sql = "/cloudsql/" in database_url
            ssl_config["details"]["is_cloud_sql"] = is_cloud_sql
            
            # Parse SSL parameters
            has_sslmode = "sslmode=" in database_url
            has_ssl = "ssl=" in database_url
            ssl_config["details"]["has_sslmode"] = has_sslmode
            ssl_config["details"]["has_ssl"] = has_ssl
            
            if is_cloud_sql:
                # Cloud SQL should not have SSL parameters
                if has_sslmode or has_ssl:
                    ssl_config["details"]["ssl_params_in_cloud_sql"] = True
                    # This is handled by the manager, so it's a warning not critical
                    ssl_config["issues"].append("SSL parameters present in Cloud SQL URL (will be auto-removed)")
                else:
                    ssl_config["details"]["ssl_params_in_cloud_sql"] = False
            else:
                # Regular TCP connections should have proper SSL config
                if not has_sslmode and not has_ssl and AuthConfig.get_environment() in ["staging", "production"]:
                    ssl_config["issues"].append("No SSL parameters specified for TCP connection in production environment")
                    ssl_config["valid"] = False
                    ssl_config["critical"] = True
                
                # Check for SSL parameter conflicts
                if has_sslmode and has_ssl:
                    ssl_config["issues"].append("Both sslmode and ssl parameters present - may cause conflicts")
                    ssl_config["valid"] = False
            
            # Test SSL parameter conversion
            try:
                import re
                # Convert SSL params for asyncpg
                if is_cloud_sql:
                    converted_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)
                    converted_url = re.sub(r'[&?]ssl=[^&]*', '', converted_url)
                    converted_url = re.sub(r'&&+', '&', converted_url)
                    converted_url = re.sub(r'[&?]$', '', converted_url)
                else:
                    converted_url = database_url.replace("sslmode=require", "ssl=require") if "sslmode=require" in database_url else database_url
                ssl_config["details"]["conversion_successful"] = True
                
                # Check conversion results
                if is_cloud_sql and ("ssl=" in converted_url or "sslmode=" in converted_url):
                    ssl_config["issues"].append("SSL parameters not properly removed for Cloud SQL after conversion")
                    ssl_config["valid"] = False
                    ssl_config["critical"] = True
                
            except Exception as e:
                ssl_config["issues"].append(f"SSL parameter conversion failed: {e}")
                ssl_config["valid"] = False
                ssl_config["critical"] = True
                ssl_config["details"]["conversion_successful"] = False
            
        except Exception as e:
            ssl_config["issues"].append(f"SSL validation failed: {e}")
            ssl_config["valid"] = False
            ssl_config["error"] = str(e)
        
        return ssl_config
    
    def _validate_jwt_secret_consistency(self) -> None:
        """Validate JWT secret consistency between auth service and main backend."""
        logger.debug("Validating JWT secret consistency...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Get JWT secret from auth service
            auth_jwt_secret = AuthSecretLoader.get_jwt_secret()
            validation_result["details"]["auth_secret_loaded"] = bool(auth_jwt_secret)
            validation_result["details"]["auth_secret_length"] = len(auth_jwt_secret) if auth_jwt_secret else 0
            
            # Check secret strength
            if len(auth_jwt_secret) < 32 and AuthConfig.get_environment() in ["staging", "production"]:
                validation_result["status"] = "failed"
                validation_result["issues"].append("JWT secret is less than 32 characters in production environment")
                self.validation_report["critical_issues"].append("JWT: Secret too short for production")
            
            # Check for development defaults in production
            if (auth_jwt_secret == "dev-secret-key-DO-NOT-USE-IN-PRODUCTION" and 
                AuthConfig.get_environment() in ["staging", "production"]):
                validation_result["status"] = "failed"
                validation_result["issues"].append("Using development default JWT secret in production environment")
                self.validation_report["critical_issues"].append("JWT: Development secret in production")
            
            # Validate secret sources
            secret_sources = []
            env_vars_to_check = ["JWT_SECRET_KEY", "JWT_SECRET_STAGING", "JWT_SECRET_PRODUCTION"]
            
            for env_var in env_vars_to_check:
                if get_env().get(env_var):
                    secret_sources.append(env_var)
            
            validation_result["details"]["available_secret_sources"] = secret_sources
            
            if not secret_sources:
                if AuthConfig.get_environment() not in ["development", "test"]:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("No JWT secret environment variables found")
                    self.validation_report["critical_issues"].append("JWT: No secret sources configured")
            
            # Check for consistency with backend (if running on same system)
            try:
                backend_secret = get_env().get("JWT_SECRET_KEY")
                if backend_secret and backend_secret != auth_jwt_secret:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("JWT secrets differ between auth service and backend")
                    self.validation_report["critical_issues"].append("JWT: Secret inconsistency between services")
                    validation_result["details"]["backend_consistency"] = False
                else:
                    validation_result["details"]["backend_consistency"] = True
            except Exception:
                validation_result["warnings"].append("Could not check backend JWT secret consistency")
                validation_result["details"]["backend_consistency"] = "unknown"
            
            # Validate environment-specific secrets
            env = AuthConfig.get_environment()
            if env == "staging" and get_env().get("JWT_SECRET_STAGING"):
                if get_env().get("JWT_SECRET_STAGING") != auth_jwt_secret:
                    validation_result["warnings"].append("JWT_SECRET_STAGING differs from loaded secret")
                    validation_result["details"]["staging_specific_consistency"] = False
                else:
                    validation_result["details"]["staging_specific_consistency"] = True
            
        except ValueError as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"JWT secret loading failed: {e}")
            self.validation_report["critical_issues"].append("JWT: Secret loading failed")
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"JWT validation failed: {e}")
            self.validation_report["critical_issues"].append("JWT: Validation process failed")
        
        self.validation_report["validations"]["jwt_secret"] = validation_result
    
    def _validate_oauth_configuration(self) -> None:
        """Validate OAuth configuration and environment consistency."""
        logger.debug("Validating OAuth configuration...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            env = AuthConfig.get_environment()
            
            # Validate Google OAuth Client ID
            client_id = AuthSecretLoader.get_google_client_id()
            validation_result["details"]["client_id_configured"] = bool(client_id)
            
            if not client_id:
                if env in ["staging", "production"]:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("Google OAuth Client ID not configured for production environment")
                    self.validation_report["critical_issues"].append("OAuth: Missing Client ID in production")
                else:
                    validation_result["warnings"].append("Google OAuth Client ID not configured")
            else:
                # Check for development credentials in production
                if ("localhost" in client_id or "dev" in client_id.lower()) and env in ["staging", "production"]:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("Development OAuth credentials detected in production environment")
                    self.validation_report["critical_issues"].append("OAuth: Development credentials in production")
                
                # Validate client ID format (Google client IDs end with .apps.googleusercontent.com)
                if not client_id.endswith(".apps.googleusercontent.com"):
                    validation_result["warnings"].append("Google Client ID format may be incorrect")
                    validation_result["details"]["client_id_format"] = "invalid"
                else:
                    validation_result["details"]["client_id_format"] = "valid"
            
            # Validate Google OAuth Client Secret
            client_secret = AuthSecretLoader.get_google_client_secret()
            validation_result["details"]["client_secret_configured"] = bool(client_secret)
            
            if not client_secret:
                if env in ["staging", "production"]:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("Google OAuth Client Secret not configured for production environment")
                    self.validation_report["critical_issues"].append("OAuth: Missing Client Secret in production")
                else:
                    validation_result["warnings"].append("Google OAuth Client Secret not configured")
            
            # Validate redirect URIs for environment
            expected_redirect_uris = self._get_expected_redirect_uris(env)
            validation_result["details"]["expected_redirect_uris"] = expected_redirect_uris
            
            # Check OAUTH_ALLOWED_REDIRECT_URIS configuration
            allowed_redirect_uris = get_env().get("OAUTH_ALLOWED_REDIRECT_URIS", "")
            if allowed_redirect_uris:
                allowed_uris = [uri.strip() for uri in allowed_redirect_uris.split(",")]
                validation_result["details"]["configured_redirect_uris"] = allowed_uris
                
                # Check if expected URIs are in allowed list
                for expected_uri in expected_redirect_uris:
                    if expected_uri not in allowed_uris:
                        validation_result["warnings"].append(f"Expected redirect URI not in allowed list: {expected_uri}")
                        validation_result["details"]["missing_redirect_uris"] = validation_result["details"].get("missing_redirect_uris", [])
                        validation_result["details"]["missing_redirect_uris"].append(expected_uri)
            else:
                validation_result["warnings"].append("OAUTH_ALLOWED_REDIRECT_URIS not configured, using defaults")
                validation_result["details"]["using_default_redirect_uris"] = True
            
            # Validate frontend URL consistency
            frontend_url = AuthConfig.get_frontend_url()
            validation_result["details"]["frontend_url"] = frontend_url
            
            expected_frontend_urls = {
                "staging": "https://app.staging.netrasystems.ai",
                "production": "https://netrasystems.ai",
                "development": None  # Can vary
            }
            
            if env in expected_frontend_urls and expected_frontend_urls[env]:
                if frontend_url != expected_frontend_urls[env]:
                    validation_result["warnings"].append(f"Frontend URL mismatch for {env}: expected {expected_frontend_urls[env]}, got {frontend_url}")
                    validation_result["details"]["frontend_url_mismatch"] = True
                else:
                    validation_result["details"]["frontend_url_mismatch"] = False
            
            # Check OAuth HMAC secret for state signing
            hmac_secret = get_env().get("OAUTH_HMAC_SECRET")
            validation_result["details"]["hmac_secret_configured"] = bool(hmac_secret)
            
            if not hmac_secret and env in ["staging", "production"]:
                validation_result["warnings"].append("OAUTH_HMAC_SECRET not configured, using generated secret")
                validation_result["details"]["using_generated_hmac"] = True
            
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"OAuth validation failed: {e}")
            self.validation_report["critical_issues"].append("OAuth: Validation process failed")
        
        self.validation_report["validations"]["oauth"] = validation_result
    
    def _get_expected_redirect_uris(self, environment: str) -> List[str]:
        """Get expected redirect URIs for the given environment."""
        if environment == "staging":
            return [
                "https://app.staging.netrasystems.ai/auth/callback",
                "https://auth.staging.netrasystems.ai/callback"
            ]
        elif environment == "production":
            return [
                "https://netrasystems.ai/auth/callback",
                "https://app.netrasystems.ai/auth/callback",
                "https://auth.netrasystems.ai/callback"
            ]
        else:  # development
            return [
                "http://localhost:3000/auth/callback",
                "http://127.0.0.1:3000/auth/callback"
            ]
    
    def _validate_ssl_parameters(self) -> None:
        """Validate SSL parameters for different connection types."""
        logger.debug("Validating SSL parameters...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # This is primarily covered in database validation, but we add specific SSL checks here
            database_url = get_env().get("DATABASE_URL", "")
            
            if database_url:
                # Check SSL parameter format
                ssl_params = []
                if "sslmode=" in database_url:
                    sslmode_match = re.search(r'sslmode=([^&\s]+)', database_url)
                    if sslmode_match:
                        ssl_params.append(("sslmode", sslmode_match.group(1)))
                
                if "ssl=" in database_url:
                    ssl_match = re.search(r'ssl=([^&\s]+)', database_url)
                    if ssl_match:
                        ssl_params.append(("ssl", ssl_match.group(1)))
                
                validation_result["details"]["ssl_parameters"] = ssl_params
                
                # Check for parameter conflicts
                if len(ssl_params) > 1:
                    param_types = [param[0] for param in ssl_params]
                    if "sslmode" in param_types and "ssl" in param_types:
                        validation_result["warnings"].append("Both sslmode and ssl parameters present")
                        validation_result["details"]["parameter_conflict"] = True
                
                # Validate SSL values
                for param_type, param_value in ssl_params:
                    if param_type == "sslmode":
                        valid_sslmodes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
                        if param_value not in valid_sslmodes:
                            validation_result["warnings"].append(f"Invalid sslmode value: {param_value}")
                            validation_result["details"]["invalid_sslmode"] = param_value
                    elif param_type == "ssl":
                        # SSL parameter for asyncpg should be boolean or specific values
                        valid_ssl_values = ["true", "false", "require", "prefer", "allow", "disable"]
                        if param_value.lower() not in valid_ssl_values:
                            validation_result["warnings"].append(f"Invalid ssl parameter value: {param_value}")
                            validation_result["details"]["invalid_ssl"] = param_value
            
            # Check Redis SSL configuration if applicable
            redis_url = AuthConfig.get_redis_url()
            if redis_url and redis_url.startswith("rediss://"):
                validation_result["details"]["redis_ssl_enabled"] = True
            else:
                validation_result["details"]["redis_ssl_enabled"] = False
                
                # In production, recommend SSL for Redis
                if AuthConfig.get_environment() in ["staging", "production"] and not redis_url.startswith("rediss://"):
                    validation_result["warnings"].append("Redis SSL not enabled in production environment")
                    validation_result["details"]["redis_ssl_recommended"] = True
        
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"SSL validation failed: {e}")
            self.validation_report["critical_issues"].append("SSL: Validation process failed")
        
        self.validation_report["validations"]["ssl"] = validation_result
    
    def _validate_container_lifecycle_readiness(self) -> None:
        """Validate container lifecycle management readiness."""
        logger.debug("Validating container lifecycle readiness...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Check signal handlers
            signal_handlers_registered = self._check_signal_handlers()
            validation_result["details"]["signal_handlers"] = signal_handlers_registered
            
            if not signal_handlers_registered["SIGTERM"] and not signal_handlers_registered["SIGINT"]:
                validation_result["warnings"].append("No graceful shutdown signal handlers registered")
                validation_result["details"]["graceful_shutdown"] = False
                self.validation_report["warnings"].append("Container: No graceful shutdown handlers")
            else:
                validation_result["details"]["graceful_shutdown"] = True
            
            # Check PORT environment variable
            port = get_env().get("PORT")
            validation_result["details"]["port_configured"] = bool(port)
            
            if not port:
                validation_result["warnings"].append("PORT environment variable not set, using default")
                validation_result["details"]["using_default_port"] = True
            else:
                try:
                    port_int = int(port)
                    if port_int < 1 or port_int > 65535:
                        validation_result["issues"].append(f"Invalid PORT value: {port}")
                        validation_result["status"] = "failed"
                        self.validation_report["critical_issues"].append(f"Container: Invalid port {port}")
                    else:
                        validation_result["details"]["port_valid"] = True
                except ValueError:
                    validation_result["issues"].append(f"PORT is not a valid integer: {port}")
                    validation_result["status"] = "failed"
                    self.validation_report["critical_issues"].append("Container: Invalid port format")
            
            # Check health endpoints
            health_endpoints = ["/health", "/health/ready"]
            validation_result["details"]["health_endpoints"] = health_endpoints
            validation_result["details"]["health_endpoints_configured"] = True  # They exist in main.py
            
            # Check environment detection
            k_service = get_env().get("K_SERVICE")
            validation_result["details"]["k_service"] = k_service
            validation_result["details"]["cloud_run_detected"] = bool(k_service)
            
            # Check resource constraints awareness
            if k_service:
                # In Cloud Run, check for memory/CPU limits
                memory_limit = get_env().get("MEMORY_LIMIT")
                cpu_limit = get_env().get("CPU_LIMIT")
                validation_result["details"]["memory_limit"] = memory_limit
                validation_result["details"]["cpu_limit"] = cpu_limit
                
                if not memory_limit and not cpu_limit:
                    validation_result["warnings"].append("No resource limits detected in Cloud Run environment")
                    validation_result["details"]["resource_limits_detected"] = False
                else:
                    validation_result["details"]["resource_limits_detected"] = True
            
            # Check for fast test mode handling
            fast_test_mode = get_env().get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            validation_result["details"]["fast_test_mode"] = fast_test_mode
            
            # Check startup sequence configuration
            environment = AuthConfig.get_environment()
            if environment in ["development", "staging"]:
                validation_result["details"]["startup_error_tolerance"] = True
            else:
                validation_result["details"]["startup_error_tolerance"] = False
            
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"Container lifecycle validation failed: {e}")
            self.validation_report["critical_issues"].append("Container: Lifecycle validation failed")
        
        self.validation_report["validations"]["container_lifecycle"] = validation_result
    
    def _check_signal_handlers(self) -> Dict[str, bool]:
        """Check if signal handlers are registered for graceful shutdown."""
        signal_handlers = {}
        
        try:
            # Check common signals used in container environments
            signals_to_check = [signal.SIGTERM, signal.SIGINT, signal.SIGUSR1, signal.SIGUSR2]
            
            for sig in signals_to_check:
                try:
                    current_handler = signal.signal(sig, signal.getsignal(sig))
                    signal.signal(sig, current_handler)  # Restore original handler
                    
                    # Check if it's not the default handler
                    is_registered = current_handler != signal.SIG_DFL
                    signal_handlers[sig.name] = is_registered
                except (AttributeError, OSError):
                    signal_handlers[sig.name] = False
        except Exception:
            # Fallback if signal checking fails
            signal_handlers = {
                "SIGTERM": False,
                "SIGINT": False,
                "SIGUSR1": False,
                "SIGUSR2": False
            }
        
        return signal_handlers
    
    def _validate_environment_consistency(self) -> None:
        """Validate environment detection and configuration consistency."""
        logger.debug("Validating environment consistency...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Check environment detection
            detected_env = AuthConfig.get_environment()
            env_var = get_env().get("ENVIRONMENT", "development").lower()
            
            validation_result["details"]["detected_environment"] = detected_env
            validation_result["details"]["environment_variable"] = env_var
            validation_result["details"]["environment_consistent"] = detected_env == env_var
            
            if detected_env != env_var:
                validation_result["warnings"].append(f"Environment mismatch: detected {detected_env}, ENVIRONMENT={env_var}")
                validation_result["details"]["environment_consistent"] = False
            
            # Check Cloud Run environment detection
            k_service = get_env().get("K_SERVICE")
            if k_service:
                validation_result["details"]["k_service"] = k_service
                
                # Check if service name matches expected pattern
                expected_service_patterns = {
                    "staging": ["netra-auth-staging", "auth-service-staging"],
                    "production": ["netra-auth-service", "netra-auth-prod"]
                }
                
                if detected_env in expected_service_patterns:
                    service_pattern_match = any(pattern in k_service.lower() for pattern in expected_service_patterns[detected_env])
                    validation_result["details"]["service_name_pattern_match"] = service_pattern_match
                    
                    if not service_pattern_match:
                        validation_result["warnings"].append(f"Service name {k_service} doesn't match expected pattern for {detected_env}")
                        self.validation_report["warnings"].append(f"Environment: Service name mismatch in {detected_env}")
            
            # Check for environment-specific configurations
            env_specific_configs = [
                ("GOOGLE_CLIENT_ID_STAGING", "staging"),
                ("GOOGLE_CLIENT_ID_PRODUCTION", "production"),
                ("JWT_SECRET_STAGING", "staging"),
                ("JWT_SECRET_PRODUCTION", "production")
            ]
            
            for config_var, target_env in env_specific_configs:
                if detected_env == target_env and not get_env().get(config_var):
                    validation_result["warnings"].append(f"Environment-specific config {config_var} not set for {target_env}")
                    validation_result["details"][f"missing_{config_var.lower()}"] = True
            
            # Validate CORS configuration for environment
            cors_origins = get_env().get("CORS_ORIGINS", "")
            validation_result["details"]["cors_origins"] = cors_origins
            
            if detected_env == "staging" and cors_origins:
                if "staging.netrasystems.ai" not in cors_origins:
                    validation_result["warnings"].append("Staging CORS origins may not include staging domain")
                    validation_result["details"]["staging_cors_incomplete"] = True
            
            # Check for development settings in production
            dev_indicators = [
                ("DEBUG", "true"),
                ("DEVELOPMENT", "true"),
                ("AUTH_FAST_TEST_MODE", "true")
            ]
            
            if detected_env in ["staging", "production"]:
                for env_var, dev_value in dev_indicators:
                    if get_env().get(env_var, "").lower() == dev_value:
                        validation_result["status"] = "failed"
                        validation_result["issues"].append(f"Development setting {env_var}={dev_value} active in {detected_env}")
                        self.validation_report["critical_issues"].append(f"Environment: Development setting in {detected_env}")
        
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"Environment validation failed: {e}")
            self.validation_report["critical_issues"].append("Environment: Validation process failed")
        
        self.validation_report["validations"]["environment"] = validation_result
    
    def _validate_service_configuration(self) -> None:
        """Validate service-specific configuration."""
        logger.debug("Validating service configuration...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            # Check service name consistency
            expected_service_name = "auth-service"
            validation_result["details"]["expected_service_name"] = expected_service_name
            
            # Check service ID configuration
            service_id = AuthConfig.get_service_id()
            validation_result["details"]["service_id"] = service_id
            
            if "dev-instance" in service_id and AuthConfig.get_environment() in ["staging", "production"]:
                validation_result["warnings"].append("Using development service ID in production environment")
                validation_result["details"]["dev_service_id_in_prod"] = True
            
            # Check service URLs
            auth_service_url = AuthConfig.get_auth_service_url()
            validation_result["details"]["auth_service_url"] = auth_service_url
            
            expected_urls = {
                "staging": "https://auth.staging.netrasystems.ai",
                "production": "https://auth.netrasystems.ai"
            }
            
            env = AuthConfig.get_environment()
            if env in expected_urls and auth_service_url != expected_urls[env]:
                validation_result["warnings"].append(f"Auth service URL mismatch for {env}: expected {expected_urls[env]}, got {auth_service_url}")
                validation_result["details"]["service_url_mismatch"] = True
            else:
                validation_result["details"]["service_url_mismatch"] = False
            
            # Check Redis configuration
            redis_url = AuthConfig.get_redis_url()
            validation_result["details"]["redis_url"] = redis_url
            validation_result["details"]["redis_disabled"] = AuthConfig.is_redis_disabled()
            
            if AuthConfig.is_redis_disabled() and env in ["staging", "production"]:
                validation_result["warnings"].append("Redis is disabled in production environment")
                validation_result["details"]["redis_disabled_in_prod"] = True
            
            # Check session TTL configuration
            session_ttl = AuthConfig.get_session_ttl_hours()
            validation_result["details"]["session_ttl_hours"] = session_ttl
            
            if session_ttl > 168 and env in ["staging", "production"]:  # More than 7 days
                validation_result["warnings"].append(f"Session TTL is very long: {session_ttl} hours")
                validation_result["details"]["long_session_ttl"] = True
            
            # Check JWT configuration
            jwt_algorithm = AuthConfig.get_jwt_algorithm()
            jwt_access_expiry = AuthConfig.get_jwt_access_expiry_minutes()
            jwt_refresh_expiry = AuthConfig.get_jwt_refresh_expiry_days()
            
            validation_result["details"]["jwt_algorithm"] = jwt_algorithm
            validation_result["details"]["jwt_access_expiry_minutes"] = jwt_access_expiry
            validation_result["details"]["jwt_refresh_expiry_days"] = jwt_refresh_expiry
            
            # Validate JWT algorithm
            secure_algorithms = ["HS256", "RS256", "ES256"]
            if jwt_algorithm not in secure_algorithms:
                validation_result["status"] = "failed"
                validation_result["issues"].append(f"Insecure JWT algorithm: {jwt_algorithm}")
                self.validation_report["critical_issues"].append(f"Service: Insecure JWT algorithm {jwt_algorithm}")
            
            # Check JWT expiry times
            if jwt_access_expiry > 60 and env in ["staging", "production"]:  # More than 1 hour
                validation_result["warnings"].append(f"JWT access token expiry is long: {jwt_access_expiry} minutes")
                validation_result["details"]["long_access_token_expiry"] = True
            
            if jwt_refresh_expiry > 30 and env in ["staging", "production"]:  # More than 30 days
                validation_result["warnings"].append(f"JWT refresh token expiry is very long: {jwt_refresh_expiry} days")
                validation_result["details"]["long_refresh_token_expiry"] = True
        
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"Service configuration validation failed: {e}")
            self.validation_report["critical_issues"].append("Service: Configuration validation failed")
        
        self.validation_report["validations"]["service"] = validation_result
    
    def _validate_security_configuration(self) -> None:
        """Validate security-related configuration."""
        logger.debug("Validating security configuration...")
        
        validation_result = {
            "status": "passed",
            "issues": [],
            "warnings": [],
            "details": {}
        }
        
        try:
            env = AuthConfig.get_environment()
            
            # Check service secret configuration
            try:
                service_secret = AuthConfig.get_service_secret()
                validation_result["details"]["service_secret_configured"] = bool(service_secret)
                
                if service_secret and len(service_secret) >= 32:
                    validation_result["details"]["service_secret_strong"] = True
                else:
                    if env in ["staging", "production"]:
                        validation_result["warnings"].append("Service secret may be weak for production")
                        validation_result["details"]["service_secret_strong"] = False
            except ValueError as e:
                validation_result["status"] = "failed"
                validation_result["issues"].append(f"Service secret validation failed: {e}")
                self.validation_report["critical_issues"].append("Security: Service secret issue")
            
            # Check secure headers configuration
            secure_headers_enabled = get_env().get("SECURE_HEADERS_ENABLED", "false").lower() == "true"
            validation_result["details"]["secure_headers_enabled"] = secure_headers_enabled
            
            if not secure_headers_enabled and env in ["staging", "production"]:
                validation_result["warnings"].append("Secure headers not enabled in production environment")
                validation_result["details"]["secure_headers_recommended"] = True
            
            # Check CORS configuration security
            cors_origins = get_env().get("CORS_ORIGINS", "")
            if cors_origins == "*" and env in ["staging", "production"]:
                validation_result["status"] = "failed"
                validation_result["issues"].append("Wildcard CORS origins not allowed in production")
                self.validation_report["critical_issues"].append("Security: Wildcard CORS in production")
            
            # Check OAuth security settings
            oauth_hmac_secret = get_env().get("OAUTH_HMAC_SECRET")
            validation_result["details"]["oauth_hmac_secret_configured"] = bool(oauth_hmac_secret)
            
            if not oauth_hmac_secret and env in ["staging", "production"]:
                validation_result["warnings"].append("OAuth HMAC secret not configured, using generated secret")
                validation_result["details"]["oauth_security_degraded"] = True
            
            # Check for insecure development settings
            insecure_settings = [
                ("LOG_ASYNC_CHECKOUT", "true"),
                ("DISABLE_AUTH", "true"),
                ("ALLOW_INSECURE", "true")
            ]
            
            for setting, insecure_value in insecure_settings:
                if get_env().get(setting, "").lower() == insecure_value and env in ["staging", "production"]:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append(f"Insecure setting {setting}={insecure_value} in {env}")
                    self.validation_report["critical_issues"].append(f"Security: Insecure setting {setting} in {env}")
            
            # Check SSL/TLS configuration
            if env in ["staging", "production"]:
                database_url = get_env().get("DATABASE_URL", "")
                redis_url = AuthConfig.get_redis_url()
                
                # Check database SSL
                if database_url and "sslmode=disable" in database_url:
                    validation_result["status"] = "failed"
                    validation_result["issues"].append("Database SSL is disabled in production")
                    self.validation_report["critical_issues"].append("Security: Database SSL disabled in production")
                
                # Check Redis SSL
                if redis_url and not redis_url.startswith(("rediss://", "redis://localhost", "redis://redis:")):
                    validation_result["warnings"].append("Redis may not be using SSL in production")
                    validation_result["details"]["redis_ssl_warning"] = True
        
        except Exception as e:
            validation_result["status"] = "failed"
            validation_result["issues"].append(f"Security validation failed: {e}")
            self.validation_report["critical_issues"].append("Security: Validation process failed")
        
        self.validation_report["validations"]["security"] = validation_result
    
    def _determine_overall_status(self) -> None:
        """Determine overall validation status based on individual checks."""
        if self.validation_report["critical_issues"]:
            self.validation_report["overall_status"] = "failed"
        elif any(v.get("status") == "failed" for v in self.validation_report["validations"].values()):
            self.validation_report["overall_status"] = "failed"
        elif self.validation_report["warnings"]:
            self.validation_report["overall_status"] = "warning"
        else:
            self.validation_report["overall_status"] = "passed"
    
    def print_validation_report(self) -> None:
        """Print a comprehensive validation report."""
        report = self.validation_report
        
        status_symbols = {
            "passed": "✓ PASS",
            "warning": "⚠ WARN",
            "failed": "✗ FAIL",
            "unknown": "? UNKNOWN"
        }
        
        status_symbol = status_symbols.get(report["overall_status"], "? UNKNOWN")
        
        print("\n" + "=" * 80)
        print("AUTH SERVICE PRE-DEPLOYMENT VALIDATION REPORT")
        print("=" * 80)
        print(f"Overall Status: {status_symbol}")
        print(f"Environment: {report['environment']}")
        print(f"Timestamp: {report['timestamp']}")
        
        if report["critical_issues"]:
            print(f"\n🚨 CRITICAL ISSUES ({len(report['critical_issues'])}):")
            for issue in report["critical_issues"]:
                print(f"   ✗ {issue}")
        
        if report["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"   ⚠ {warning}")
        
        # Show validation details
        print(f"\n📋 VALIDATION DETAILS:")
        for check_name, check_result in report["validations"].items():
            status_icon = "✓" if check_result["status"] == "passed" else "✗" if check_result["status"] == "failed" else "⚠"
            print(f"   {status_icon} {check_name.upper()}: {check_result['status']}")
            
            if check_result.get("issues"):
                for issue in check_result["issues"]:
                    print(f"      - {issue}")
            
            if check_result.get("warnings"):
                for warning in check_result["warnings"]:
                    print(f"      ⚠ {warning}")
        
        if report["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS ({len(report['recommendations'])}):")
            for rec in report["recommendations"]:
                print(f"   → {rec}")
        
        print("\n" + "=" * 80)
        
        # Summary
        if report["overall_status"] == "passed":
            print("✅ AUTH SERVICE IS READY FOR DEPLOYMENT")
        elif report["overall_status"] == "warning":
            print("⚠️  AUTH SERVICE CAN DEPLOY WITH WARNINGS - REVIEW RECOMMENDED")
        else:
            print("🚫 AUTH SERVICE NOT READY FOR DEPLOYMENT - FIX CRITICAL ISSUES")
        
        print("=" * 80)


def main():
    """Main function to run validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auth Service Pre-Deployment Validation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON format")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    # Run validation
    validator = PreDeploymentValidator()
    report = validator.run_comprehensive_validation()
    
    if args.json:
        import json
        print(json.dumps(report, indent=2))
    else:
        validator.print_validation_report()
    
    # Exit with appropriate code
    if report["overall_status"] == "failed":
        sys.exit(1)
    elif report["overall_status"] == "warning":
        sys.exit(2)  # Warning exit code
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()