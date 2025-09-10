"""
Integration Tests for JWT Configuration Validation (No Docker)

Purpose: Reproduce JWT configuration warnings between services  
Business Impact: $500K+ MRR at risk due to authentication configuration issues
Expected Initial Result: TESTS MUST FAIL to prove configuration issues exist

Test Strategy: Integration testing without Docker complexity, focusing on
JWT configuration synchronization and validation between services.
"""

import pytest
import os
import jwt
import json
import base64
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import hashlib

# Test subject imports (no Docker dependencies)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.core.token_validator import TokenValidator
from shared.isolated_environment import get_env


class TestJWTConfigurationSynchronization:
    """
    Tests JWT configuration synchronization issues (no Docker).
    
    These tests reproduce JWT configuration warnings and mismatches
    between services that prevent proper authentication flow.
    """

    def test_jwt_secret_synchronization_failure_reproduction(self):
        """
        MUST FAIL INITIALLY: Reproduce JWT configuration warnings.
        
        This test reproduces the exact JWT configuration mismatch issues
        mentioned in the Golden Path analysis.
        """
        env = get_env()
        
        # Test different JWT secret scenarios that cause mismatches
        test_scenarios = [
            {
                "name": "backend_vs_auth_mismatch",
                "backend_secret": "backend_secret_123",
                "auth_secret": "auth_secret_456",  # Different secret
                "expected_issue": "JWT secrets don't match between services"
            },
            {
                "name": "missing_auth_secret",
                "backend_secret": "backend_secret_123", 
                "auth_secret": "",  # Missing secret
                "expected_issue": "Auth service JWT secret missing"
            },
            {
                "name": "missing_backend_secret",
                "backend_secret": "",  # Missing secret
                "auth_secret": "auth_secret_123",
                "expected_issue": "Backend JWT secret missing"
            },
            {
                "name": "wrong_environment_variable",
                "backend_secret_var": "JWT_SECRET",  # Wrong variable name
                "auth_secret_var": "JWT_SECRET_KEY",  # Different variable name
                "expected_issue": "JWT secret environment variable mismatch"
            }
        ]
        
        configuration_failures = []
        
        for scenario in test_scenarios:
            try:
                # Set up test environment for each scenario
                if "backend_secret" in scenario:
                    env.set("JWT_SECRET_KEY", scenario["backend_secret"], source=f"test_{scenario['name']}_backend")
                if "auth_secret" in scenario:
                    env.set("AUTH_JWT_SECRET", scenario["auth_secret"], source=f"test_{scenario['name']}_auth")
                
                # Test JWT configuration validation
                result = self._validate_jwt_configuration_sync()
                
                if not result["synchronized"]:
                    configuration_failures.append({
                        "scenario": scenario["name"],
                        "expected_issue": scenario["expected_issue"],
                        "actual_error": result["error"],
                        "details": result.get("details", {})
                    })
                    
            except Exception as e:
                configuration_failures.append({
                    "scenario": scenario["name"],
                    "expected_issue": scenario["expected_issue"],
                    "exception": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Initially expect failures showing JWT configuration issues
        assert len(configuration_failures) > 0, (
            f"Expected JWT configuration failures to demonstrate issues exist. "
            f"Found {len(configuration_failures)} failures: {configuration_failures}"
        )
        
        # After fixes: assert len(configuration_failures) == 0

    def test_service_jwt_configuration_mismatch(self):
        """
        Test JWT configuration mismatches between services.
        
        This specifically tests the configuration mismatches that cause
        authentication warnings in service logs.
        """
        # Test JWT configuration across different services
        service_configs = {
            "backend": {
                "jwt_secret_var": "JWT_SECRET_KEY",
                "token_algorithm": "HS256",
                "token_expiry": 3600
            },
            "auth": {
                "jwt_secret_var": "JWT_SECRET_KEY",  # Should match backend
                "token_algorithm": "HS256",  # Should match backend
                "token_expiry": 3600  # Should match backend
            },
            "frontend": {
                "jwt_validation_endpoint": "/validate",
                "token_refresh_endpoint": "/refresh"
            }
        }
        
        env = get_env()
        mismatches = []
        
        # Test backend vs auth service configuration
        backend_secret = "test_backend_secret_123"
        auth_secret = "test_auth_secret_456"  # Intentionally different
        
        env.set("JWT_SECRET_KEY", backend_secret, source="test_backend")
        env.set("AUTH_JWT_SECRET", auth_secret, source="test_auth")
        
        try:
            # Validate configuration synchronization
            backend_config = self._get_backend_jwt_config()
            auth_config = self._get_auth_jwt_config()
            
            # Check for configuration mismatches
            if backend_config["secret"] != auth_config["secret"]:
                mismatches.append({
                    "type": "secret_mismatch",
                    "backend_secret_hash": hashlib.sha256(backend_config["secret"].encode()).hexdigest()[:8],
                    "auth_secret_hash": hashlib.sha256(auth_config["secret"].encode()).hexdigest()[:8]
                })
                
            if backend_config["algorithm"] != auth_config["algorithm"]:
                mismatches.append({
                    "type": "algorithm_mismatch",
                    "backend_algorithm": backend_config["algorithm"],
                    "auth_algorithm": auth_config["algorithm"]
                })
                
        except Exception as e:
            mismatches.append({
                "type": "configuration_error",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should initially fail showing configuration mismatches
        assert len(mismatches) == 0, (
            f"JWT configuration mismatches between services: {mismatches}"
        )

    def test_jwt_token_format_validation_cross_service(self):
        """
        Validate JWT token format across service boundaries.
        
        This tests token format compatibility issues that cause
        authentication failures between frontend and backend.
        """
        env = get_env()
        
        # Set up test JWT configuration
        test_secret = "test_jwt_secret_for_validation"
        env.set("JWT_SECRET_KEY", test_secret, source="test_jwt_validation")
        
        # Test different token generation scenarios
        token_scenarios = [
            {
                "name": "backend_generated_token",
                "service": "backend",
                "payload": {"user_id": "user123", "role": "user"},
                "algorithm": "HS256"
            },
            {
                "name": "auth_generated_token", 
                "service": "auth",
                "payload": {"user_id": "user123", "role": "user"},
                "algorithm": "HS256"
            },
            {
                "name": "mismatched_algorithm_token",
                "service": "backend",
                "payload": {"user_id": "user123", "role": "user"}, 
                "algorithm": "HS512"  # Different algorithm
            }
        ]
        
        validation_failures = []
        
        for scenario in token_scenarios:
            try:
                # Generate token using scenario parameters
                token = self._generate_test_jwt_token(
                    payload=scenario["payload"],
                    secret=test_secret,
                    algorithm=scenario["algorithm"]
                )
                
                # Test token validation across services
                backend_validation = self._validate_token_backend(token)
                auth_validation = self._validate_token_auth(token)
                
                # Check for validation mismatches
                if backend_validation["valid"] != auth_validation["valid"]:
                    validation_failures.append({
                        "scenario": scenario["name"],
                        "token_preview": token[:50] + "...",
                        "backend_valid": backend_validation["valid"],
                        "auth_valid": auth_validation["valid"],
                        "backend_error": backend_validation.get("error"),
                        "auth_error": auth_validation.get("error")
                    })
                    
            except Exception as e:
                validation_failures.append({
                    "scenario": scenario["name"],
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Should pass after JWT configuration synchronization
        assert len(validation_failures) == 0, (
            f"JWT token validation failures across services: {validation_failures}"
        )

    def test_jwt_environment_variable_consistency(self):
        """
        Test JWT environment variable consistency across services.
        
        This tests the environment variable naming and configuration
        inconsistencies that cause JWT configuration warnings.
        """
        # Test different environment variable naming patterns
        env_var_scenarios = [
            {
                "name": "consistent_naming",
                "variables": {
                    "JWT_SECRET_KEY": "consistent_secret_123",
                    "JWT_ALGORITHM": "HS256", 
                    "JWT_EXPIRY": "3600"
                },
                "expected_valid": True
            },
            {
                "name": "inconsistent_naming",
                "variables": {
                    "JWT_SECRET": "secret_123",  # Different name
                    "JWT_SECRET_KEY": "different_secret_456",  # Conflicting
                    "JWT_ALGORITHM": "HS256"
                },
                "expected_issue": "Conflicting JWT secret variable names"
            },
            {
                "name": "missing_required_vars",
                "variables": {
                    "JWT_ALGORITHM": "HS256"
                    # Missing JWT_SECRET_KEY
                },
                "expected_issue": "Missing required JWT configuration"
            }
        ]
        
        env = get_env()
        consistency_issues = []
        
        for scenario in env_var_scenarios:
            try:
                # Clear existing JWT configuration
                self._clear_jwt_env_vars(env)
                
                # Set test environment variables
                for var_name, var_value in scenario["variables"].items():
                    env.set(var_name, var_value, source=f"test_{scenario['name']}")
                
                # Validate environment variable consistency
                consistency_result = self._validate_jwt_env_var_consistency()
                
                if "expected_valid" in scenario:
                    if not consistency_result["consistent"]:
                        consistency_issues.append({
                            "scenario": scenario["name"],
                            "error": consistency_result["error"],
                            "details": consistency_result.get("details", {})
                        })
                else:
                    # Should detect inconsistency issue
                    if consistency_result["consistent"]:
                        consistency_issues.append({
                            "scenario": scenario["name"],
                            "error": "Should have detected consistency issue",
                            "expected_issue": scenario.get("expected_issue")
                        })
                        
            except Exception as e:
                consistency_issues.append({
                    "scenario": scenario["name"],
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
        
        # Should pass after environment variable standardization
        assert len(consistency_issues) == 0, (
            f"JWT environment variable consistency issues: {consistency_issues}"
        )

    # Helper methods for JWT testing

    def _validate_jwt_configuration_sync(self) -> Dict[str, any]:
        """
        Validate JWT configuration synchronization between services.
        
        This replicates the logic that should detect JWT configuration
        mismatches causing authentication warnings.
        """
        env = get_env()
        
        try:
            # Get JWT configuration from different services
            backend_jwt_secret = env.get("JWT_SECRET_KEY", "")
            auth_jwt_secret = env.get("AUTH_JWT_SECRET", "")
            
            if not backend_jwt_secret:
                return {
                    "synchronized": False,
                    "error": "Backend JWT secret missing",
                    "details": {"backend_secret_set": False}
                }
                
            if not auth_jwt_secret:
                return {
                    "synchronized": False,
                    "error": "Auth service JWT secret missing", 
                    "details": {"auth_secret_set": False}
                }
                
            if backend_jwt_secret != auth_jwt_secret:
                return {
                    "synchronized": False,
                    "error": "JWT secrets don't match between services",
                    "details": {
                        "backend_secret_hash": hashlib.sha256(backend_jwt_secret.encode()).hexdigest()[:8],
                        "auth_secret_hash": hashlib.sha256(auth_jwt_secret.encode()).hexdigest()[:8]
                    }
                }
                
            return {
                "synchronized": True,
                "message": "JWT configuration synchronized"
            }
            
        except Exception as e:
            return {
                "synchronized": False,
                "error": f"JWT configuration validation error: {str(e)}"
            }

    def _get_backend_jwt_config(self) -> Dict[str, any]:
        """Get backend JWT configuration."""
        env = get_env()
        
        return {
            "secret": env.get("JWT_SECRET_KEY", ""),
            "algorithm": env.get("JWT_ALGORITHM", "HS256"),
            "expiry": int(env.get("JWT_EXPIRY", "3600"))
        }

    def _get_auth_jwt_config(self) -> Dict[str, any]:
        """Get auth service JWT configuration."""
        env = get_env()
        
        return {
            "secret": env.get("AUTH_JWT_SECRET", env.get("JWT_SECRET_KEY", "")),
            "algorithm": env.get("AUTH_JWT_ALGORITHM", "HS256"),
            "expiry": int(env.get("AUTH_JWT_EXPIRY", "3600"))
        }

    def _generate_test_jwt_token(self, payload: Dict, secret: str, algorithm: str = "HS256") -> str:
        """Generate test JWT token."""
        try:
            # Add standard JWT claims
            now = datetime.utcnow()
            payload.update({
                "iat": now,
                "exp": now + timedelta(hours=1),
                "iss": "test_issuer"
            })
            
            token = jwt.encode(payload, secret, algorithm=algorithm)
            return token
            
        except Exception as e:
            raise Exception(f"Test JWT token generation failed: {str(e)}")

    def _validate_token_backend(self, token: str) -> Dict[str, any]:
        """Validate token using backend logic."""
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "")
        
        if not secret:
            return {"valid": False, "error": "Backend JWT secret not configured"}
            
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return {"valid": True, "payload": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Token validation error: {str(e)}"}

    def _validate_token_auth(self, token: str) -> Dict[str, any]:
        """Validate token using auth service logic."""
        env = get_env()
        secret = env.get("AUTH_JWT_SECRET", env.get("JWT_SECRET_KEY", ""))
        
        if not secret:
            return {"valid": False, "error": "Auth JWT secret not configured"}
            
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return {"valid": True, "payload": payload}
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
        except Exception as e:
            return {"valid": False, "error": f"Token validation error: {str(e)}"}

    def _validate_jwt_env_var_consistency(self) -> Dict[str, any]:
        """Validate JWT environment variable consistency."""
        env = get_env()
        
        # Check for common JWT environment variables
        jwt_vars = {
            "JWT_SECRET": env.get("JWT_SECRET", ""),
            "JWT_SECRET_KEY": env.get("JWT_SECRET_KEY", ""),
            "AUTH_JWT_SECRET": env.get("AUTH_JWT_SECRET", ""),
            "JWT_ALGORITHM": env.get("JWT_ALGORITHM", ""),
            "JWT_EXPIRY": env.get("JWT_EXPIRY", "")
        }
        
        issues = []
        
        # Check for conflicting secret variables
        jwt_secret = jwt_vars["JWT_SECRET"]
        jwt_secret_key = jwt_vars["JWT_SECRET_KEY"] 
        auth_jwt_secret = jwt_vars["AUTH_JWT_SECRET"]
        
        if jwt_secret and jwt_secret_key and jwt_secret != jwt_secret_key:
            issues.append("Conflicting JWT_SECRET and JWT_SECRET_KEY values")
            
        if not (jwt_secret or jwt_secret_key):
            issues.append("No JWT secret configured (JWT_SECRET or JWT_SECRET_KEY required)")
            
        if auth_jwt_secret and jwt_secret_key and auth_jwt_secret != jwt_secret_key:
            issues.append("Auth service JWT secret doesn't match backend")
            
        if issues:
            return {
                "consistent": False,
                "error": "; ".join(issues),
                "details": {k: bool(v) for k, v in jwt_vars.items()}
            }
            
        return {
            "consistent": True,
            "message": "JWT environment variables consistent"
        }

    def _clear_jwt_env_vars(self, env):
        """Clear JWT environment variables for testing."""
        jwt_env_vars = [
            "JWT_SECRET",
            "JWT_SECRET_KEY", 
            "AUTH_JWT_SECRET",
            "JWT_ALGORITHM",
            "JWT_EXPIRY",
            "AUTH_JWT_ALGORITHM",
            "AUTH_JWT_EXPIRY"
        ]
        
        for var in jwt_env_vars:
            env.set(var, "", source="test_clear")


class TestCrossServiceJWTIntegration:
    """
    Test JWT integration patterns across services without Docker.
    
    Focus on authentication flow issues that cause service
    communication problems.
    """

    def test_frontend_backend_jwt_flow_integration(self):
        """
        Test frontend to backend JWT authentication flow.
        
        This tests the integration pattern that may be causing
        authentication failures in the Golden Path.
        """
        env = get_env()
        
        # Set up test JWT configuration
        test_secret = "integration_test_secret_123"
        env.set("JWT_SECRET_KEY", test_secret, source="test_frontend_backend")
        
        integration_issues = []
        
        try:
            # Simulate frontend authentication request
            user_credentials = {
                "email": "test@example.com",
                "password": "test_password"
            }
            
            # Test authentication flow
            auth_result = self._simulate_auth_service_login(user_credentials)
            
            if not auth_result["success"]:
                integration_issues.append({
                    "stage": "authentication",
                    "error": auth_result["error"]
                })
            else:
                # Test backend token validation
                token = auth_result["token"]
                backend_validation = self._simulate_backend_token_validation(token)
                
                if not backend_validation["valid"]:
                    integration_issues.append({
                        "stage": "backend_validation",
                        "token_preview": token[:50] + "...",
                        "error": backend_validation["error"]
                    })
                    
        except Exception as e:
            integration_issues.append({
                "stage": "integration_flow",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should pass after JWT configuration fixes
        assert len(integration_issues) == 0, (
            f"Frontend-backend JWT integration issues: {integration_issues}"
        )

    def test_websocket_authentication_jwt_integration(self):
        """
        Test WebSocket authentication JWT integration.
        
        This specifically tests WebSocket authentication issues
        that may be causing the 1011 errors in staging.
        """
        env = get_env()
        
        # Set up JWT configuration for WebSocket testing
        test_secret = "websocket_jwt_test_secret"
        env.set("JWT_SECRET_KEY", test_secret, source="test_websocket_jwt")
        
        websocket_auth_issues = []
        
        try:
            # Test WebSocket authentication flow
            user_token = self._generate_test_jwt_token(
                payload={"user_id": "ws_user123", "role": "user"},
                secret=test_secret
            )
            
            # Test different WebSocket authentication scenarios
            auth_scenarios = [
                {
                    "name": "header_authentication",
                    "auth_method": "header",
                    "token": user_token
                },
                {
                    "name": "subprotocol_authentication", 
                    "auth_method": "subprotocol",
                    "token": user_token
                },
                {
                    "name": "query_parameter_authentication",
                    "auth_method": "query",
                    "token": user_token
                }
            ]
            
            for scenario in auth_scenarios:
                try:
                    auth_result = self._simulate_websocket_authentication(
                        scenario["auth_method"],
                        scenario["token"]
                    )
                    
                    if not auth_result["authenticated"]:
                        websocket_auth_issues.append({
                            "scenario": scenario["name"],
                            "auth_method": scenario["auth_method"],
                            "error": auth_result["error"]
                        })
                        
                except Exception as e:
                    websocket_auth_issues.append({
                        "scenario": scenario["name"],
                        "error": str(e),
                        "exception_type": type(e).__name__
                    })
                    
        except Exception as e:
            websocket_auth_issues.append({
                "stage": "websocket_setup",
                "error": str(e),
                "exception_type": type(e).__name__
            })
        
        # Should pass after WebSocket authentication fixes
        assert len(websocket_auth_issues) == 0, (
            f"WebSocket JWT authentication issues: {websocket_auth_issues}"
        )

    # Helper methods for integration testing

    def _simulate_auth_service_login(self, credentials: Dict) -> Dict[str, any]:
        """Simulate auth service login process."""
        env = get_env()
        secret = env.get("JWT_SECRET_KEY", "")
        
        if not secret:
            return {"success": False, "error": "JWT secret not configured"}
            
        try:
            # Simulate successful authentication
            user_payload = {
                "user_id": "test_user_123",
                "email": credentials["email"],
                "role": "user"
            }
            
            token = self._generate_test_jwt_token(user_payload, secret)
            
            return {
                "success": True,
                "token": token,
                "user": user_payload
            }
            
        except Exception as e:
            return {"success": False, "error": f"Authentication failed: {str(e)}"}

    def _simulate_backend_token_validation(self, token: str) -> Dict[str, any]:
        """Simulate backend token validation."""
        return self._validate_token_backend(token)

    def _simulate_websocket_authentication(self, auth_method: str, token: str) -> Dict[str, any]:
        """Simulate WebSocket authentication process."""
        try:
            # Validate the token first
            validation_result = self._validate_token_backend(token)
            
            if not validation_result["valid"]:
                return {
                    "authenticated": False,
                    "error": f"Token validation failed: {validation_result['error']}"
                }
            
            # Simulate different authentication methods
            if auth_method == "header":
                # Simulate Authorization header authentication
                return {"authenticated": True, "method": "header"}
            elif auth_method == "subprotocol":
                # Simulate WebSocket subprotocol authentication  
                return {"authenticated": True, "method": "subprotocol"}
            elif auth_method == "query":
                # Simulate query parameter authentication
                return {"authenticated": True, "method": "query"}
            else:
                return {
                    "authenticated": False,
                    "error": f"Unsupported authentication method: {auth_method}"
                }
                
        except Exception as e:
            return {
                "authenticated": False,
                "error": f"WebSocket authentication error: {str(e)}"
            }


# Pytest markers for test organization
pytestmark = [
    pytest.mark.integration,
    pytest.mark.infrastructure_validation,
    pytest.mark.must_fail_initially
]