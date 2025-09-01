"""
CRITICAL MISSION TEST SUITE: Cross-Service JWT Token Validation Failure
========================================================================

This test suite is designed to FAIL and expose the exact root cause of the 
CRITICAL staging authentication issue where tokens issued by auth service
are being rejected by backend service.

ISSUE DESCRIPTION:
- Auth service issues tokens successfully (200 OK)
- Auth service can verify its own tokens (200 OK) 
- Backend service rejects tokens from auth service (401 Unauthorized)

EXPECTED BEHAVIOR: ALL THESE TESTS SHOULD FAIL INITIALLY
This proves the issue exists and provides comprehensive diagnostics.

Tests are designed to be EXTREMELY DIFFICULT and catch edge cases that
might be causing the cross-service validation failures.

Author: Claude Code - Mission Critical Test Suite
Date: 2025-09-01
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from unittest.mock import patch

import httpx
import jwt
import pytest
import requests

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.isolated_environment import IsolatedEnvironment
    from shared.jwt_secret_manager import SharedJWTSecretManager
    from auth_service.auth_core.config import AuthConfig
    from auth_service.auth_core.core.jwt_handler import JWTHandler
    from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Project root: {project_root}")
    print(f"Python path: {sys.path[:3]}")
    raise

# Configure detailed logging for diagnostics
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class StagingAuthCrossServiceValidator:
    """
    Comprehensive cross-service validation tester.
    Designed to catch ALL potential JWT validation discrepancies.
    """
    
    def __init__(self):
        self.env = IsolatedEnvironment.get_instance()
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.staging_backend_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
        
        # Force staging environment for all tests
        self.env.set("ENVIRONMENT", "staging")
        
        # Clear any cached secrets to force fresh loading
        SharedJWTSecretManager.clear_cache()
        
        # Initialize components
        self.auth_config = AuthConfig()
        self.jwt_handler = JWTHandler()
        self.backend_validator = UnifiedJWTValidator()
        
    async def setup_detailed_diagnostics(self) -> Dict[str, Any]:
        """Setup comprehensive diagnostics about the system state."""
        diagnostics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "test_suite": "staging_auth_cross_service_validation",
            "environment_details": {},
            "jwt_secret_analysis": {},
            "service_configurations": {},
            "network_connectivity": {},
            "system_state": {}
        }
        
        # Environment analysis
        diagnostics["environment_details"] = {
            "ENVIRONMENT": self.env.get("ENVIRONMENT"),
            "JWT_SECRET_STAGING": "***" if self.env.get("JWT_SECRET_STAGING") else None,
            "JWT_SECRET_KEY": "***" if self.env.get("JWT_SECRET_KEY") else None,
            "JWT_SECRET": "***" if self.env.get("JWT_SECRET") else None,
            "GCP_PROJECT_ID": self.env.get("GCP_PROJECT_ID"),
            "SERVICE_SECRET": "***" if self.env.get("SERVICE_SECRET") else None,
            "SERVICE_ID": self.env.get("SERVICE_ID"),
        }
        
        # JWT Secret Analysis
        try:
            auth_secret = self.auth_config.get_jwt_secret()
            shared_secret = SharedJWTSecretManager.get_jwt_secret()
            
            diagnostics["jwt_secret_analysis"] = {
                "auth_config_secret_length": len(auth_secret) if auth_secret else 0,
                "shared_manager_secret_length": len(shared_secret) if shared_secret else 0,
                "secrets_match": auth_secret == shared_secret,
                "auth_secret_hash": hashlib.sha256(auth_secret.encode()).hexdigest()[:16] if auth_secret else None,
                "shared_secret_hash": hashlib.sha256(shared_secret.encode()).hexdigest()[:16] if shared_secret else None,
                "secret_validation_passed": False
            }
            
            # Validate secret synchronization
            try:
                SharedJWTSecretManager.validate_synchronization()
                diagnostics["jwt_secret_analysis"]["secret_validation_passed"] = True
            except Exception as e:
                diagnostics["jwt_secret_analysis"]["secret_validation_error"] = str(e)
                
        except Exception as e:
            diagnostics["jwt_secret_analysis"]["error"] = str(e)
        
        # Service Configuration Analysis
        try:
            diagnostics["service_configurations"] = {
                "auth_service": {
                    "environment": self.auth_config.get_environment(),
                    "jwt_algorithm": self.auth_config.get_jwt_algorithm(),
                    "access_expiry_minutes": self.auth_config.get_jwt_access_expiry_minutes(),
                    "refresh_expiry_days": self.auth_config.get_jwt_refresh_expiry_days(),
                    "service_expiry_minutes": self.auth_config.get_jwt_service_expiry_minutes(),
                    "service_id": self.auth_config.get_service_id(),
                    "frontend_url": self.auth_config.get_frontend_url(),
                    "auth_service_url": self.auth_config.get_auth_service_url(),
                },
                "backend_service": {
                    "algorithm": self.backend_validator.algorithm,
                    "issuer": self.backend_validator.issuer,
                    "access_token_expire_minutes": self.backend_validator.access_token_expire_minutes,
                    "refresh_token_expire_days": self.backend_validator.refresh_token_expire_days,
                }
            }
        except Exception as e:
            diagnostics["service_configurations"]["error"] = str(e)
        
        # Network connectivity tests
        try:
            # Test auth service connectivity
            auth_health_response = await self._test_service_connectivity(
                f"{self.staging_auth_url}/health"
            )
            diagnostics["network_connectivity"]["auth_service"] = auth_health_response
            
            # Test backend service connectivity
            backend_health_response = await self._test_service_connectivity(
                f"{self.staging_backend_url}/health"
            )
            diagnostics["network_connectivity"]["backend_service"] = backend_health_response
            
        except Exception as e:
            diagnostics["network_connectivity"]["error"] = str(e)
        
        return diagnostics
    
    async def _test_service_connectivity(self, url: str) -> Dict[str, Any]:
        """Test connectivity to a service endpoint."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                return {
                    "url": url,
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if response.elapsed else 0,
                    "headers": dict(response.headers),
                    "accessible": response.status_code < 500
                }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "accessible": False
            }
    
    def generate_test_token(self, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Generate a test token with specific claims for validation testing."""
        # Use auth service's JWT handler to create token
        user_id = kwargs.get("user_id", f"test_user_{uuid.uuid4().hex[:8]}")
        email = kwargs.get("email", f"{user_id}@test.netra.ai")
        permissions = kwargs.get("permissions", ["read", "write"])
        
        token = self.jwt_handler.create_access_token(user_id, email, permissions)
        
        # Decode token to analyze claims (without verification for analysis)
        claims = jwt.decode(token, options={"verify_signature": False})
        
        return token, claims
    
    def generate_malformed_token_variations(self, base_token: str) -> List[Tuple[str, str, str]]:
        """Generate various malformed token variations to test edge cases."""
        variations = []
        
        # Parse base token
        header, payload, signature = base_token.split('.')
        
        # 1. Modified signature
        variations.append((
            f"{header}.{payload}.{'x' * len(signature)}",
            "modified_signature",
            "Token with completely modified signature"
        ))
        
        # 2. Modified header algorithm
        try:
            header_data = json.loads(base64.urlsafe_b64decode(header + '==').decode())
            header_data['alg'] = 'none'
            modified_header = base64.urlsafe_b64encode(
                json.dumps(header_data).encode()
            ).decode().rstrip('=')
            variations.append((
                f"{modified_header}.{payload}.{signature}",
                "none_algorithm",
                "Token with 'none' algorithm"
            ))
        except:
            pass
        
        # 3. Modified issuer in payload
        try:
            payload_data = json.loads(base64.urlsafe_b64decode(payload + '==').decode())
            payload_data['iss'] = 'malicious-issuer'
            modified_payload = base64.urlsafe_b64encode(
                json.dumps(payload_data).encode()
            ).decode().rstrip('=')
            variations.append((
                f"{header}.{modified_payload}.{signature}",
                "wrong_issuer",
                "Token with wrong issuer"
            ))
        except:
            pass
        
        # 4. Modified audience
        try:
            payload_data = json.loads(base64.urlsafe_b64decode(payload + '==').decode())
            payload_data['aud'] = 'wrong-audience'
            modified_payload = base64.urlsafe_b64encode(
                json.dumps(payload_data).encode()
            ).decode().rstrip('=')
            variations.append((
                f"{header}.{modified_payload}.{signature}",
                "wrong_audience", 
                "Token with wrong audience"
            ))
        except:
            pass
        
        # 5. Expired token
        try:
            payload_data = json.loads(base64.urlsafe_b64decode(payload + '==').decode())
            payload_data['exp'] = int(time.time()) - 3600  # 1 hour ago
            modified_payload = base64.urlsafe_b64encode(
                json.dumps(payload_data).encode()
            ).decode().rstrip('=')
            variations.append((
                f"{header}.{modified_payload}.{signature}",
                "expired_token",
                "Expired token"
            ))
        except:
            pass
        
        # 6. Future token (issued in future)
        try:
            payload_data = json.loads(base64.urlsafe_b64decode(payload + '==').decode())
            payload_data['iat'] = int(time.time()) + 3600  # 1 hour in future
            modified_payload = base64.urlsafe_b64encode(
                json.dumps(payload_data).encode()
            ).decode().rstrip('=')
            variations.append((
                f"{header}.{modified_payload}.{signature}",
                "future_token",
                "Token issued in future"
            ))
        except:
            pass
        
        # 7. Malformed structure
        variations.extend([
            ("not.a.jwt", "malformed_structure", "Not a JWT structure"),
            ("", "empty_token", "Empty token"),
            ("bearer " + base_token, "bearer_prefix", "Token with Bearer prefix"),
            (base_token + "extra", "extra_data", "Token with extra data"),
        ])
        
        return variations


@pytest.mark.asyncio
@pytest.mark.mission_critical
class TestStagingCrossServiceJWTValidation:
    """
    CRITICAL MISSION TEST: Cross-Service JWT Validation Failures
    
    These tests are DESIGNED TO FAIL and expose the root cause of
    staging authentication issues between auth service and backend.
    """
    
    async def test_00_setup_comprehensive_diagnostics(self):
        """
        DIAGNOSTIC TEST: Comprehensive system state analysis.
        This test captures the complete system state for debugging.
        """
        validator = StagingAuthCrossServiceValidator()
        diagnostics = await validator.setup_detailed_diagnostics()
        
        # Log full diagnostics
        logger.critical("=== COMPREHENSIVE SYSTEM DIAGNOSTICS ===")
        logger.critical(json.dumps(diagnostics, indent=2))
        
        # Assertions that SHOULD pass for a working system
        assert diagnostics["environment_details"]["ENVIRONMENT"] == "staging"
        assert diagnostics["jwt_secret_analysis"]["secrets_match"], \
            f"JWT secrets don't match between auth config and shared manager! " \
            f"Auth hash: {diagnostics['jwt_secret_analysis']['auth_secret_hash']}, " \
            f"Shared hash: {diagnostics['jwt_secret_analysis']['shared_secret_hash']}"
        
        assert diagnostics["jwt_secret_analysis"]["secret_validation_passed"], \
            f"JWT secret validation failed: {diagnostics['jwt_secret_analysis'].get('secret_validation_error', 'Unknown error')}"
        
        assert diagnostics["network_connectivity"]["auth_service"]["accessible"], \
            "Auth service is not accessible"
        
        assert diagnostics["network_connectivity"]["backend_service"]["accessible"], \
            "Backend service is not accessible"
    
    async def test_01_jwt_secret_synchronization_deep_analysis(self):
        """
        CRITICAL TEST: Deep analysis of JWT secret synchronization.
        This test SHOULD FAIL if secrets are not properly synchronized.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Test 1: Direct secret comparison
        auth_secret = validator.auth_config.get_jwt_secret()
        shared_secret = SharedJWTSecretManager.get_jwt_secret()
        
        logger.critical(f"Auth Service Secret Length: {len(auth_secret)}")
        logger.critical(f"Shared Manager Secret Length: {len(shared_secret)}")
        logger.critical(f"Auth Secret Hash: {hashlib.sha256(auth_secret.encode()).hexdigest()[:16]}")
        logger.critical(f"Shared Secret Hash: {hashlib.sha256(shared_secret.encode()).hexdigest()[:16]}")
        
        assert auth_secret == shared_secret, \
            "AUTH SERVICE AND SHARED MANAGER HAVE DIFFERENT JWT SECRETS!"
        
        # Test 2: Secret source analysis
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=False):
            # Clear cache to force re-loading
            SharedJWTSecretManager.clear_cache()
            
            # Test different loading paths
            secret_staging = validator.env.get("JWT_SECRET_STAGING")
            secret_key = validator.env.get("JWT_SECRET_KEY") 
            secret_legacy = validator.env.get("JWT_SECRET")
            
            logger.critical(f"JWT_SECRET_STAGING available: {secret_staging is not None}")
            logger.critical(f"JWT_SECRET_KEY available: {secret_key is not None}")
            logger.critical(f"JWT_SECRET (legacy) available: {secret_legacy is not None}")
            
            # Re-load secrets
            fresh_secret = SharedJWTSecretManager.get_jwt_secret()
            
            assert fresh_secret == auth_secret, \
                "JWT secret changed after cache clear - inconsistent loading!"
        
        # Test 3: Secret strength validation
        assert len(auth_secret) >= 32, \
            f"JWT secret is too short for staging: {len(auth_secret)} characters"
        
        assert auth_secret != "development-jwt-secret-minimum-32-characters-long", \
            "Using development JWT secret in staging environment!"
        
        # Test 4: Environment binding validation
        SharedJWTSecretManager.validate_synchronization()
    
    async def test_02_token_generation_consistency(self):
        """
        CRITICAL TEST: Token generation consistency between services.
        This test SHOULD FAIL if token generation parameters differ.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Generate test tokens with identical parameters
        test_user_id = "test_user_consistency"
        test_email = "consistency@test.netra.ai"
        test_permissions = ["read", "write", "admin"]
        
        # Generate multiple tokens to test consistency
        tokens = []
        claims_list = []
        
        for i in range(5):
            token, claims = validator.generate_test_token(
                user_id=f"{test_user_id}_{i}",
                email=test_email,
                permissions=test_permissions
            )
            tokens.append(token)
            claims_list.append(claims)
        
        # Validate all tokens have consistent structure
        base_claims = claims_list[0]
        
        for i, claims in enumerate(claims_list[1:], 1):
            # Check consistent issuer
            assert claims.get("iss") == base_claims.get("iss"), \
                f"Token {i} has different issuer: {claims.get('iss')} vs {base_claims.get('iss')}"
            
            # Check consistent audience
            assert claims.get("aud") == base_claims.get("aud"), \
                f"Token {i} has different audience: {claims.get('aud')} vs {base_claims.get('aud')}"
            
            # Check consistent algorithm in header
            header_1 = jwt.get_unverified_header(tokens[0])
            header_i = jwt.get_unverified_header(tokens[i])
            assert header_1.get("alg") == header_i.get("alg"), \
                f"Token {i} has different algorithm: {header_i.get('alg')} vs {header_1.get('alg')}"
            
            # Check token type consistency
            assert claims.get("token_type") == base_claims.get("token_type"), \
                f"Token {i} has different token_type: {claims.get('token_type')} vs {base_claims.get('token_type')}"
            
            # Check environment consistency
            assert claims.get("env") == base_claims.get("env"), \
                f"Token {i} has different environment: {claims.get('env')} vs {base_claims.get('env')}"
        
        # Validate all tokens can be verified by auth service JWT handler
        for i, token in enumerate(tokens):
            validation_result = validator.jwt_handler.validate_token(token, "access")
            assert validation_result is not None, \
                f"Token {i} failed validation by auth service JWT handler"
            
            assert validation_result.get("sub") == f"{test_user_id}_{i}", \
                f"Token {i} validation returned wrong subject"
    
    async def test_03_cross_service_validation_core_issue(self):
        """
        CRITICAL TEST: The core cross-service validation issue.
        This test WILL FAIL and expose the exact problem.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Generate a token using auth service
        token, original_claims = validator.generate_test_token()
        
        logger.critical("=== CROSS-SERVICE VALIDATION CORE TEST ===")
        logger.critical(f"Generated token: {token[:50]}...")
        logger.critical(f"Original claims: {json.dumps(original_claims, indent=2)}")
        
        # Test 1: Auth service self-validation (should work)
        auth_validation = validator.jwt_handler.validate_token(token, "access")
        logger.critical(f"Auth service validation result: {auth_validation is not None}")
        
        if auth_validation:
            logger.critical(f"Auth validation claims: {json.dumps(auth_validation, indent=2, default=str)}")
        
        assert auth_validation is not None, \
            "Auth service cannot validate its own token!"
        
        # Test 2: Backend service validation (EXPECTED TO FAIL)
        try:
            backend_validation = await validator.backend_validator.validate_token_jwt(token)
            logger.critical(f"Backend service validation result: {backend_validation}")
            
            # This assertion SHOULD FAIL in the broken system
            assert backend_validation.valid, \
                f"CRITICAL: Backend service rejected token that auth service accepted! " \
                f"Error: {backend_validation.error}"
            
        except Exception as e:
            logger.critical(f"Backend validation threw exception: {e}")
            pytest.fail(f"Backend validation failed with exception: {e}")
        
        # Test 3: Direct staging service validation
        await self._test_staging_service_endpoints_directly(token)
    
    async def _test_staging_service_endpoints_directly(self, token: str):
        """Test actual staging service endpoints directly."""
        # Test auth service validation endpoint
        auth_validation_url = f"{self.staging_auth_url}/auth/validate-token"
        backend_api_url = f"{self.staging_backend_url}/api/v1/health"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test auth service validation
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                auth_response = await client.post(
                    auth_validation_url,
                    json={"token": token}
                )
                logger.critical(f"Auth service validation response: {auth_response.status_code}")
                logger.critical(f"Auth service validation body: {auth_response.text}")
                
                # Auth service should accept its own token
                assert auth_response.status_code == 200, \
                    f"Auth service rejected its own token: {auth_response.status_code} - {auth_response.text}"
        
        except Exception as e:
            logger.critical(f"Auth service validation request failed: {e}")
        
        # Test backend service with token
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_response = await client.get(
                    backend_api_url,
                    headers=headers
                )
                logger.critical(f"Backend service response: {backend_response.status_code}")
                logger.critical(f"Backend service body: {backend_response.text}")
                
                # Backend service should accept token from auth service
                # THIS ASSERTION SHOULD FAIL and expose the issue
                assert backend_response.status_code != 401, \
                    f"CRITICAL BUG: Backend service returned 401 for valid auth service token! " \
                    f"Response: {backend_response.text}"
        
        except Exception as e:
            logger.critical(f"Backend service validation request failed: {e}")
    
    async def test_04_token_claims_validation_comprehensive(self):
        """
        CRITICAL TEST: Comprehensive token claims validation.
        Tests ALL aspects of JWT claims that could cause validation failures.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Test different claim combinations
        test_cases = [
            {
                "name": "standard_claims",
                "user_id": "standard_user",
                "email": "standard@test.netra.ai",
                "permissions": ["read", "write"]
            },
            {
                "name": "admin_claims", 
                "user_id": "admin_user",
                "email": "admin@test.netra.ai",
                "permissions": ["read", "write", "admin", "super_admin"]
            },
            {
                "name": "minimal_claims",
                "user_id": "minimal_user",
                "email": "minimal@test.netra.ai",
                "permissions": []
            },
            {
                "name": "service_claims",
                "user_id": "service_netra_backend",
                "email": "service@netra.ai",
                "permissions": ["service", "api_access"]
            }
        ]
        
        for test_case in test_cases:
            logger.critical(f"Testing claims case: {test_case['name']}")
            
            token, claims = validator.generate_test_token(**test_case)
            
            # Analyze claims in detail
            logger.critical(f"Generated claims for {test_case['name']}: {json.dumps(claims, indent=2, default=str)}")
            
            # Critical claims validation
            required_claims = ["sub", "iat", "exp", "iss", "aud", "jti"]
            for claim in required_claims:
                assert claim in claims, \
                    f"Missing required claim '{claim}' in {test_case['name']} token"
            
            # Issuer validation
            assert claims.get("iss") == "netra-auth-service", \
                f"Wrong issuer in {test_case['name']}: {claims.get('iss')}"
            
            # Audience validation
            valid_audiences = ["netra-platform", "netra-backend", "netra-services", "netra-admin"]
            assert claims.get("aud") in valid_audiences, \
                f"Invalid audience in {test_case['name']}: {claims.get('aud')}"
            
            # Environment validation
            assert claims.get("env") == "staging", \
                f"Wrong environment in {test_case['name']}: {claims.get('env')}"
            
            # Time validation
            now = time.time()
            iat = claims.get("iat", 0)
            exp = claims.get("exp", 0)
            
            assert iat <= now + 60, \
                f"Token issued too far in future for {test_case['name']}: iat={iat}, now={now}"
            
            assert exp > now, \
                f"Token already expired for {test_case['name']}: exp={exp}, now={now}"
            
            assert exp - iat <= 24 * 60 * 60, \
                f"Token validity period too long for {test_case['name']}: {exp - iat} seconds"
            
            # Validate token with auth service
            auth_result = validator.jwt_handler.validate_token(token, "access")
            assert auth_result is not None, \
                f"Auth service rejected {test_case['name']} token"
            
            # Critical test: Validate with backend service
            backend_result = await validator.backend_validator.validate_token_jwt(token)
            assert backend_result.valid, \
                f"CRITICAL: Backend rejected {test_case['name']} token that auth accepted! " \
                f"Error: {backend_result.error}"
    
    async def test_05_clock_synchronization_and_timing_issues(self):
        """
        CRITICAL TEST: Clock synchronization and timing-related validation issues.
        Tests for time skew problems between services.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Test tokens with various timing edge cases
        base_time = int(time.time())
        
        timing_test_cases = [
            {
                "name": "current_time",
                "iat_offset": 0,
                "exp_offset": 900,  # 15 minutes
                "should_validate": True
            },
            {
                "name": "slight_future_iat", 
                "iat_offset": 30,  # 30 seconds in future
                "exp_offset": 930,
                "should_validate": True  # Should be within clock skew tolerance
            },
            {
                "name": "past_iat",
                "iat_offset": -300,  # 5 minutes ago
                "exp_offset": 600,   # 10 minutes from now
                "should_validate": True
            },
            {
                "name": "far_future_iat",
                "iat_offset": 300,   # 5 minutes in future  
                "exp_offset": 1200,
                "should_validate": False  # Should exceed clock skew tolerance
            },
            {
                "name": "nearly_expired",
                "iat_offset": -895,  # Almost 15 minutes ago
                "exp_offset": 5,     # Expires in 5 seconds
                "should_validate": True
            },
            {
                "name": "just_expired",
                "iat_offset": -905,
                "exp_offset": -5,    # Expired 5 seconds ago
                "should_validate": False
            }
        ]
        
        for test_case in timing_test_cases:
            logger.critical(f"Testing timing case: {test_case['name']}")
            
            # Create custom token with specific timing
            iat = base_time + test_case["iat_offset"]
            exp = base_time + test_case["exp_offset"]
            
            # Build custom payload
            payload = {
                "sub": f"timing_test_{test_case['name']}",
                "iat": iat,
                "exp": exp,
                "token_type": "access",
                "type": "access",
                "iss": "netra-auth-service",
                "aud": "netra-platform",
                "jti": str(uuid.uuid4()),
                "env": "staging",
                "svc_id": validator.auth_config.get_service_id(),
                "email": f"timing@{test_case['name']}.test",
                "permissions": ["read"]
            }
            
            # Encode token with auth service secret
            secret = validator.auth_config.get_jwt_secret()
            token = jwt.encode(payload, secret, algorithm="HS256")
            
            logger.critical(f"Created {test_case['name']} token with iat={iat}, exp={exp} (now={base_time})")
            
            # Test validation
            auth_result = validator.jwt_handler.validate_token(token, "access")
            backend_result = await validator.backend_validator.validate_token_jwt(token)
            
            logger.critical(f"Auth validation: {auth_result is not None}")
            logger.critical(f"Backend validation: {backend_result.valid if backend_result else False}")
            
            if test_case["should_validate"]:
                assert auth_result is not None, \
                    f"Auth service rejected valid {test_case['name']} token"
                
                # Critical assertion - backend should match auth service
                assert backend_result.valid, \
                    f"CRITICAL: Backend rejected {test_case['name']} token that auth accepted! " \
                    f"Backend error: {backend_result.error if backend_result else 'No result'}"
            else:
                # Both services should reject invalid timing
                if auth_result is not None:
                    logger.warning(f"Auth service unexpectedly accepted {test_case['name']} token")
                
                if backend_result and backend_result.valid:
                    logger.warning(f"Backend service unexpectedly accepted {test_case['name']} token")
    
    async def test_06_malformed_token_edge_cases(self):
        """
        CRITICAL TEST: Malformed token handling consistency.
        Tests that both services handle malformed tokens the same way.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Generate a valid base token
        base_token, _ = validator.generate_test_token()
        
        # Generate malformed variations
        malformed_tokens = validator.generate_malformed_token_variations(base_token)
        
        for token, variation_type, description in malformed_tokens:
            logger.critical(f"Testing malformed token: {variation_type} - {description}")
            
            # Test auth service handling
            auth_result = None
            auth_exception = None
            try:
                auth_result = validator.jwt_handler.validate_token(token, "access")
            except Exception as e:
                auth_exception = e
            
            # Test backend service handling
            backend_result = None
            backend_exception = None
            try:
                backend_result = await validator.backend_validator.validate_token_jwt(token)
            except Exception as e:
                backend_exception = e
            
            logger.critical(f"Auth result: {auth_result is not None}, exception: {auth_exception}")
            logger.critical(f"Backend result: {backend_result.valid if backend_result else False}, exception: {backend_exception}")
            
            # Critical consistency check
            auth_accepted = auth_result is not None and auth_exception is None
            backend_accepted = backend_result and backend_result.valid and backend_exception is None
            
            # Both services should handle malformed tokens consistently
            if auth_accepted != backend_accepted:
                logger.critical(f"INCONSISTENT HANDLING: {variation_type}")
                logger.critical(f"Auth accepted: {auth_accepted}, Backend accepted: {backend_accepted}")
                
                # This is a critical issue if one accepts what the other rejects
                if variation_type not in ["bearer_prefix", "extra_data"]:  # These might have different handling
                    pytest.fail(
                        f"CRITICAL INCONSISTENCY: Auth and Backend handle {variation_type} differently! "
                        f"Auth: {auth_accepted}, Backend: {backend_accepted}"
                    )
    
    async def test_07_service_signature_and_enhanced_security(self):
        """
        CRITICAL TEST: Service signature and enhanced security features.
        Tests advanced JWT security features that might cause validation issues.
        """
        validator = StagingAuthCrossServiceValidator()
        
        # Generate token and examine service signature
        token, claims = validator.generate_test_token()
        
        # Validate token first to get service signature
        auth_validation = validator.jwt_handler.validate_token(token, "access")
        assert auth_validation is not None, "Auth service validation failed"
        
        logger.critical("=== SERVICE SIGNATURE ANALYSIS ===")
        logger.critical(f"Service signature present: {'service_signature' in auth_validation}")
        
        if 'service_signature' in auth_validation:
            service_sig = auth_validation['service_signature']
            logger.critical(f"Service signature: {service_sig[:16]}...")
            
            # Validate signature generation
            service_secret = validator.auth_config.get_service_secret()
            service_id = validator.auth_config.get_service_id()
            
            logger.critical(f"Service secret available: {service_secret is not None}")
            logger.critical(f"Service ID: {service_id}")
            
            # Test signature verification
            service_claims = {
                "sub": auth_validation.get("sub"),
                "iss": auth_validation.get("iss"), 
                "aud": auth_validation.get("aud"),
                "svc_id": auth_validation.get("svc_id"),
                "exp": auth_validation.get("exp")
            }
            
            domain_prefix = "NETRA_SERVICE_AUTH_V1"
            signature_data = f"{domain_prefix}:{service_claims}"
            
            expected_signature = hmac.new(
                service_secret.encode('utf-8'),
                signature_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            logger.critical(f"Expected signature: {expected_signature[:16]}...")
            logger.critical(f"Actual signature:   {service_sig[:16]}...")
            
            assert service_sig == expected_signature, \
                "Service signature mismatch - enhanced security validation failing!"
        
        # Test backend validation with service signature
        backend_result = await validator.backend_validator.validate_token_jwt(token)
        assert backend_result.valid, \
            f"Backend rejected token with service signature! Error: {backend_result.error}"
    
    async def test_08_comprehensive_failure_analysis(self):
        """
        CRITICAL TEST: Comprehensive failure analysis.
        This test performs end-to-end analysis of the entire validation pipeline.
        """
        validator = StagingAuthCrossServiceValidator()
        
        logger.critical("=== COMPREHENSIVE FAILURE ANALYSIS ===")
        
        # Generate multiple tokens with different characteristics
        test_scenarios = [
            {"name": "basic_user", "user_id": "basic_user", "permissions": ["read"]},
            {"name": "admin_user", "user_id": "admin_user", "permissions": ["admin"]}, 
            {"name": "service_user", "user_id": "service_backend", "permissions": ["service"]},
            {"name": "complex_user", "user_id": "complex_user", "permissions": ["read", "write", "admin", "api"]},
        ]
        
        failure_summary = {
            "total_tests": len(test_scenarios),
            "auth_service_passed": 0,
            "backend_service_passed": 0,
            "both_passed": 0,
            "failures": []
        }
        
        for scenario in test_scenarios:
            logger.critical(f"Testing scenario: {scenario['name']}")
            
            token, claims = validator.generate_test_token(**scenario)
            
            # Test auth service
            auth_result = validator.jwt_handler.validate_token(token, "access")
            auth_passed = auth_result is not None
            
            if auth_passed:
                failure_summary["auth_service_passed"] += 1
                logger.critical(f"✓ Auth service validated {scenario['name']}")
            else:
                logger.critical(f"✗ Auth service rejected {scenario['name']}")
                failure_summary["failures"].append({
                    "scenario": scenario['name'],
                    "service": "auth",
                    "token": token[:50],
                    "claims": claims
                })
            
            # Test backend service
            backend_result = await validator.backend_validator.validate_token_jwt(token)
            backend_passed = backend_result and backend_result.valid
            
            if backend_passed:
                failure_summary["backend_service_passed"] += 1
                logger.critical(f"✓ Backend service validated {scenario['name']}")
            else:
                logger.critical(f"✗ Backend service rejected {scenario['name']}")
                logger.critical(f"Backend error: {backend_result.error if backend_result else 'No result'}")
                failure_summary["failures"].append({
                    "scenario": scenario['name'],
                    "service": "backend",
                    "token": token[:50],
                    "claims": claims,
                    "error": backend_result.error if backend_result else "No result"
                })
            
            # Check consistency
            if auth_passed and backend_passed:
                failure_summary["both_passed"] += 1
                logger.critical(f"✓ Both services validated {scenario['name']}")
            elif auth_passed != backend_passed:
                logger.critical(f"✗ CRITICAL INCONSISTENCY in {scenario['name']}")
                logger.critical(f"  Auth: {'PASS' if auth_passed else 'FAIL'}")
                logger.critical(f"  Backend: {'PASS' if backend_passed else 'FAIL'}")
        
        # Final analysis
        logger.critical("=== FINAL FAILURE ANALYSIS ===")
        logger.critical(f"Total scenarios tested: {failure_summary['total_tests']}")
        logger.critical(f"Auth service passed: {failure_summary['auth_service_passed']}")
        logger.critical(f"Backend service passed: {failure_summary['backend_service_passed']}")
        logger.critical(f"Both services passed: {failure_summary['both_passed']}")
        logger.critical(f"Total failures: {len(failure_summary['failures'])}")
        
        # Log all failures
        for failure in failure_summary["failures"]:
            logger.critical(f"FAILURE: {failure}")
        
        # Critical assertions
        assert failure_summary["auth_service_passed"] == failure_summary["total_tests"], \
            f"Auth service failed {failure_summary['total_tests'] - failure_summary['auth_service_passed']} scenarios"
        
        assert failure_summary["backend_service_passed"] == failure_summary["total_tests"], \
            f"Backend service failed {failure_summary['total_tests'] - failure_summary['backend_service_passed']} scenarios"
        
        assert failure_summary["both_passed"] == failure_summary["total_tests"], \
            f"CRITICAL: Cross-service validation inconsistency detected! " \
            f"Only {failure_summary['both_passed']}/{failure_summary['total_tests']} scenarios passed both services"


# Helper functions for running individual tests
async def run_single_test(test_name: str):
    """Run a single test for debugging purposes."""
    test_instance = TestStagingCrossServiceJWTValidation()
    test_method = getattr(test_instance, test_name)
    await test_method()


if __name__ == "__main__":
    """
    Run the test suite directly for debugging.
    This will execute all tests and provide detailed output.
    """
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    async def main():
        test_instance = TestStagingCrossServiceJWTValidation()
        
        try:
            logger.critical("Starting comprehensive cross-service JWT validation test suite...")
            
            await test_instance.test_00_setup_comprehensive_diagnostics()
            await test_instance.test_01_jwt_secret_synchronization_deep_analysis()
            await test_instance.test_02_token_generation_consistency()
            await test_instance.test_03_cross_service_validation_core_issue()
            await test_instance.test_04_token_claims_validation_comprehensive()
            await test_instance.test_05_clock_synchronization_and_timing_issues()
            await test_instance.test_06_malformed_token_edge_cases()
            await test_instance.test_07_service_signature_and_enhanced_security()
            await test_instance.test_08_comprehensive_failure_analysis()
            
            logger.critical("All tests completed successfully!")
            
        except Exception as e:
            logger.critical(f"TEST FAILED: {e}")
            logger.critical("This failure exposes the root cause of the cross-service validation issue!")
            raise
    
    # Run the tests
    asyncio.run(main())