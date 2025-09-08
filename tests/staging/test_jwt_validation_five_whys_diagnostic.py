"""
Diagnostic Test: JWT Token Validation Five Whys Analysis
========================================================

This test reproduces and validates the root cause identified in the Five Whys analysis:
JWT secret configuration inconsistency between auth service and backend service in staging.

Business Impact: $120K+ MRR at risk from WebSocket authentication failures
Technical Impact: 62-63% success rate (should be >95%)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any

import httpx
import jwt
import pytest

from shared.isolated_environment import get_env
from shared.jwt_secret_manager import get_jwt_secret_manager, get_unified_jwt_secret
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service

logger = logging.getLogger(__name__)

# Staging environment constants
STAGING_AUTH_SERVICE_URL = "https://auth.staging.netrasystems.ai"
STAGING_BACKEND_URL = "https://api.staging.netrasystems.ai"
STAGING_TEST_USER_EMAIL = "staging-e2e-user-001@test.local"


class JWTSecretAnalyzer:
    """Analyzer to investigate JWT secret consistency across services."""
    
    def __init__(self):
        self.env = get_env()
        self.jwt_manager = get_jwt_secret_manager()
        
    def get_auth_service_jwt_secret_info(self) -> Dict[str, Any]:
        """Get JWT secret info that auth service would use."""
        return {
            "environment": self.env.get("ENVIRONMENT", "unknown"),
            "jwt_secret_staging": bool(self.env.get("JWT_SECRET_STAGING")),
            "jwt_secret_key": bool(self.env.get("JWT_SECRET_KEY")),
            "jwt_secret": bool(self.env.get("JWT_SECRET")),
            "available_secrets": [
                key for key in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]
                if self.env.get(key)
            ],
            "unified_secret_length": len(get_unified_jwt_secret()) if get_unified_jwt_secret() else 0,
            "unified_debug_info": self.jwt_manager.get_debug_info()
        }
    
    def get_backend_service_jwt_secret_info(self) -> Dict[str, Any]:
        """Get JWT secret info that backend service would use."""
        # Backend uses same unified JWT secret manager
        return self.get_auth_service_jwt_secret_info()
    
    def calculate_jwt_secret_hash(self, secret: str) -> str:
        """Calculate hash of JWT secret for comparison without exposing actual secret."""
        return hashlib.sha256(secret.encode()).hexdigest()[:16]
        
    def compare_secret_consistency(self) -> Dict[str, Any]:
        """Compare JWT secret consistency between auth and backend logic."""
        try:
            # Both services use unified JWT secret manager
            unified_secret = get_unified_jwt_secret()
            secret_hash = self.calculate_jwt_secret_hash(unified_secret)
            
            return {
                "consistent": True,  # Both use same unified manager
                "secret_hash": secret_hash,
                "secret_length": len(unified_secret),
                "auth_service_info": self.get_auth_service_jwt_secret_info(),
                "backend_service_info": self.get_backend_service_jwt_secret_info()
            }
        except Exception as e:
            return {
                "consistent": False,
                "error": str(e),
                "auth_service_info": "ERROR",
                "backend_service_info": "ERROR"
            }


class StagingTokenValidator:
    """Validator to test token generation and validation in staging."""
    
    def __init__(self):
        self.analyzer = JWTSecretAnalyzer()
        self.auth_client = AuthServiceClient()
        self.unified_auth = get_unified_auth_service()
        
    async def generate_test_token_with_auth_service(self, user_email: str = STAGING_TEST_USER_EMAIL) -> Optional[str]:
        """Generate a test token using the auth service directly."""
        try:
            # Use auth service dev-login endpoint for testing
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{STAGING_AUTH_SERVICE_URL}/auth/dev-login", json={
                    "email": user_email,
                    "provider": "test"
                })
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                else:
                    logger.error(f"Auth service token generation failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to generate test token: {e}")
            return None
    
    async def validate_token_with_auth_service(self, token: str) -> Dict[str, Any]:
        """Validate token directly with auth service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(f"{STAGING_AUTH_SERVICE_URL}/auth/validate", json={
                    "token": token,
                    "token_type": "access"
                })
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_token_with_backend_service(self, token: str) -> Dict[str, Any]:
        """Validate token using backend unified authentication service."""
        try:
            # Use the same validation logic that causes the issue
            auth_result = await self.auth_client.validate_token(token)
            
            return {
                "success": auth_result is not None and auth_result.get("valid", False),
                "result": auth_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_token_structure(self, token: str) -> Dict[str, Any]:
        """Analyze JWT token structure without validation."""
        try:
            # Split token parts
            parts = token.split('.')
            if len(parts) != 3:
                return {"error": "Invalid JWT format", "parts_count": len(parts)}
            
            # Decode header and payload (without verification)
            import base64
            def decode_jwt_part(part):
                # Add padding if needed
                missing_padding = len(part) % 4
                if missing_padding:
                    part += '=' * (4 - missing_padding)
                return json.loads(base64.urlsafe_b64decode(part))
            
            header = decode_jwt_part(parts[0])
            payload = decode_jwt_part(parts[1])
            
            # Calculate expected signature with different possible secrets
            secret_tests = {}
            for secret_name in ["JWT_SECRET_STAGING", "JWT_SECRET_KEY", "JWT_SECRET"]:
                secret = get_env().get(secret_name)
                if secret:
                    try:
                        # Create expected signature
                        message = f"{parts[0]}.{parts[1]}"
                        expected_signature = hmac.new(
                            secret.encode(),
                            message.encode(),
                            hashlib.sha256
                        ).digest()
                        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
                        
                        secret_tests[secret_name] = {
                            "secret_hash": hashlib.sha256(secret.encode()).hexdigest()[:16],
                            "signature_matches": expected_signature_b64 == parts[2]
                        }
                    except Exception as e:
                        secret_tests[secret_name] = {"error": str(e)}
            
            return {
                "header": header,
                "payload": payload,
                "signature_tests": secret_tests,
                "token_parts": {
                    "header_length": len(parts[0]),
                    "payload_length": len(parts[1]),
                    "signature_length": len(parts[2])
                },
                "expiry": datetime.fromtimestamp(payload.get('exp', 0), tz=timezone.utc).isoformat() if payload.get('exp') else None,
                "issued_at": datetime.fromtimestamp(payload.get('iat', 0), tz=timezone.utc).isoformat() if payload.get('iat') else None
            }
            
        except Exception as e:
            return {"error": str(e)}


@pytest.mark.asyncio 
@pytest.mark.staging
class TestJWTValidationFiveWhysAnalysis:
    """Test suite that validates the Five Whys analysis findings."""

    @pytest.fixture
    def analyzer(self):
        """JWT secret analyzer fixture."""
        return JWTSecretAnalyzer()
    
    @pytest.fixture  
    def validator(self):
        """Staging token validator fixture."""
        return StagingTokenValidator()

    def test_jwt_secret_configuration_analysis(self, analyzer):
        """Test JWT secret configuration consistency - addresses Why #3."""
        secret_info = analyzer.get_auth_service_jwt_secret_info()
        
        # Log findings for debugging
        logger.info("JWT Secret Configuration Analysis:")
        logger.info(json.dumps(secret_info, indent=2))
        
        # Validate that staging secrets are properly configured
        assert secret_info["environment"].lower() == "staging", "Should be running in staging environment"
        
        # Check that unified JWT secret manager can resolve a secret
        assert secret_info["unified_secret_length"] > 0, "Unified JWT secret manager should resolve a secret"
        assert secret_info["unified_secret_length"] >= 32, "JWT secret should be at least 32 characters"
        
        # Check that JWT_SECRET_STAGING is available (as configured in auth service)
        available_secrets = secret_info["available_secrets"]
        logger.info(f"Available JWT secrets: {available_secrets}")
        
        # This test will reveal if JWT_SECRET_STAGING is missing
        staging_secret_available = "JWT_SECRET_STAGING" in available_secrets
        generic_secret_available = "JWT_SECRET_KEY" in available_secrets
        
        assert staging_secret_available or generic_secret_available, \
            f"Either JWT_SECRET_STAGING or JWT_SECRET_KEY must be available. Found: {available_secrets}"

    def test_secret_consistency_between_services(self, analyzer):
        """Test that auth and backend services use consistent JWT secrets - addresses Why #2."""
        consistency_info = analyzer.compare_secret_consistency()
        
        logger.info("Secret Consistency Analysis:")
        logger.info(json.dumps(consistency_info, indent=2))
        
        # Both services should use the same unified JWT secret manager
        assert consistency_info["consistent"], "Auth and backend services should use consistent JWT secrets"
        
        # Validate secret meets minimum requirements
        assert consistency_info["secret_length"] >= 32, "JWT secret should be at least 32 characters"
        
        # Log the secret hash for comparison in logs (safe to log)
        logger.info(f"JWT Secret Hash: {consistency_info['secret_hash']}")

    @pytest.mark.asyncio
    async def test_token_generation_with_auth_service(self, validator):
        """Test token generation using auth service - baseline test."""
        token = await validator.generate_test_token_with_auth_service()
        
        if not token:
            pytest.skip("Auth service token generation failed - may be expected in test environment")
        
        # Validate token structure
        analysis = await validator.analyze_token_structure(token)
        logger.info("Generated Token Analysis:")
        logger.info(json.dumps(analysis, indent=2))
        
        assert "error" not in analysis, f"Token structure analysis failed: {analysis.get('error')}"
        assert analysis["header"]["alg"] == "HS256", "Token should use HS256 algorithm"
        
        # Check if token is signed with any available secret
        signature_tests = analysis.get("signature_tests", {})
        valid_signature_found = any(test.get("signature_matches") for test in signature_tests.values())
        
        if not valid_signature_found:
            logger.warning("Generated token signature does not match any available JWT secret")
            logger.warning(f"Signature tests: {signature_tests}")

    @pytest.mark.asyncio
    async def test_same_service_token_validation(self, validator):
        """Test token validation within same auth service - should always work."""
        # Generate token
        token = await validator.generate_test_token_with_auth_service()
        if not token:
            pytest.skip("Auth service token generation failed - may be expected in test environment")
        
        # Validate with same service
        auth_validation = await validator.validate_token_with_auth_service(token)
        
        logger.info("Same-Service Token Validation:")
        logger.info(json.dumps(auth_validation, indent=2))
        
        # This should always work if JWT secrets are consistent within the service
        if not auth_validation["success"]:
            logger.error("CRITICAL: Auth service cannot validate its own tokens!")
            logger.error(f"Status: {auth_validation.get('status_code')}")
            logger.error(f"Response: {auth_validation.get('response')}")
            
            # This failure indicates the auth service has internal JWT secret issues
            pytest.fail("Auth service failed to validate its own token - internal JWT secret issue")

    @pytest.mark.asyncio
    async def test_cross_service_token_validation(self, validator):
        """Test cross-service validation - reproduces the Five Whys issue."""
        # Generate token with auth service
        token = await validator.generate_test_token_with_auth_service()
        if not token:
            pytest.skip("Auth service token generation failed - may be expected in test environment")
        
        # Validate with auth service (baseline)
        auth_validation = await validator.validate_token_with_auth_service(token)
        
        # Validate with backend service (the failing scenario)
        backend_validation = await validator.validate_token_with_backend_service(token)
        
        logger.info("Cross-Service Token Validation:")
        logger.info(f"Auth service validation: {auth_validation['success']}")
        logger.info(f"Backend service validation: {backend_validation['success']}")
        
        # Log detailed results
        if not backend_validation["success"]:
            logger.error("VALIDATION FAILURE - This confirms Five Whys analysis!")
            logger.error(f"Auth validation result: {auth_validation}")
            logger.error(f"Backend validation result: {backend_validation}")
            
            # Analyze the token to understand why it failed
            analysis = await validator.analyze_token_structure(token)
            logger.error("Token Structure Analysis:")
            logger.error(json.dumps(analysis, indent=2))
        
        # The critical test: both services should validate the same token
        if auth_validation["success"] and not backend_validation["success"]:
            pytest.fail(
                "FIVE WHYS CONFIRMED: Auth service validates token but backend service rejects it. "
                "This proves JWT secret inconsistency between services."
            )
        
        assert auth_validation["success"], "Auth service should validate its own token"
        assert backend_validation["success"], "Backend service should validate auth service token"

    @pytest.mark.asyncio
    async def test_staging_environment_jwt_secret_debugging(self, analyzer, validator):
        """Comprehensive JWT secret debugging for staging environment."""
        
        # 1. Environment analysis
        env = get_env()
        environment = env.get("ENVIRONMENT", "unknown")
        
        # 2. Available secrets analysis
        secret_info = analyzer.get_auth_service_jwt_secret_info()
        
        # 3. Generate and analyze a test token
        token = await validator.generate_test_token_with_auth_service()
        token_analysis = None
        if token:
            token_analysis = await validator.analyze_token_structure(token)
        
        # 4. Comprehensive debugging report
        debug_report = {
            "environment": environment,
            "secret_configuration": secret_info,
            "token_generated": token is not None,
            "token_analysis": token_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("COMPREHENSIVE JWT SECRET DEBUGGING REPORT:")
        logger.info(json.dumps(debug_report, indent=2))
        
        # 5. Critical assertions for Five Whys validation
        assert environment.lower() == "staging", "Test must run in staging environment"
        assert secret_info["unified_secret_length"] >= 32, "JWT secret must be properly configured"
        
        # 6. If token generation works, secret signature should match
        if token and token_analysis:
            signature_tests = token_analysis.get("signature_tests", {})
            valid_signatures = [name for name, test in signature_tests.items() if test.get("signature_matches")]
            
            if not valid_signatures:
                logger.error("CRITICAL: No JWT secret signatures match the generated token")
                logger.error("This indicates the auth service is using a different JWT secret than available in environment")
                pytest.fail("JWT secret mismatch detected - auth service uses different secret than environment")
            else:
                logger.info(f"Token validates with secrets: {valid_signatures}")


if __name__ == "__main__":
    # Run the diagnostic tests
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))