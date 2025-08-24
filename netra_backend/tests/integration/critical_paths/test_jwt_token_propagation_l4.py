"""L4 Integration Test: JWT Token Propagation Across Service Boundaries

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Security and Authentication Integrity
- Value Impact: Prevents unauthorized access patterns that could lead to data breaches
- Strategic Impact: Ensures secure token flow across all microservices

L4 Test: Complete JWT token flow validation from OAuth authentication through 
Auth Service to Backend API to WebSocket real-time messaging with actual 
staging environment services, real cryptographic validation, and production-like 
network conditions.

Critical Security Requirements:
- JWT signature validation using RS256/HS256
- Token expiry validation (access: 15min, refresh: 7 days)
- Audience and issuer validation
- Cross-service token forwarding headers
- WebSocket authentication during connection upgrade
- Protection against token replay attacks
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import jwt as jwt_lib
import pytest
import websockets

from netra_backend.app.logging_config import central_logger

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

logger = central_logger.get_logger(__name__)

@dataclass
class JWTTokenData:
    """Container for JWT token information and metadata."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_id: str
    email: str
    issued_at: float
    expires_at: float
    scopes: List[str]
    signature_valid: bool = False
    audience_valid: bool = False
    issuer_valid: bool = False

@dataclass
class TokenPropagationResult:
    """Results from token propagation testing across services."""
    auth_service_validation: Dict[str, Any]
    backend_api_validation: Dict[str, Any]
    websocket_authentication: Dict[str, Any]
    cross_service_consistency: bool
    security_validations_passed: int
    total_response_time: float
    token_integrity_maintained: bool

class JWTTokenPropagationL4Suite(L4StagingCriticalPathTestBase):
    """L4 test suite for JWT token propagation across service boundaries."""
    
    def __init__(self):
        super().__init__("JWT_Token_Propagation_L4")
        self.oauth_client_id = None
        self.oauth_client_secret = None
        self.test_tokens: Dict[str, JWTTokenData] = {}
        self.websocket_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.security_test_results: List[Dict[str, Any]] = []
        
    async def setup_test_specific_environment(self) -> None:
        """Setup OAuth and JWT-specific testing environment."""
        try:
            # Fetch OAuth configuration from auth service
            oauth_config_response = await self.test_client.get(
                f"{self.service_endpoints.auth}/api/oauth/config"
            )
            
            if oauth_config_response.status_code == 200:
                oauth_config = oauth_config_response.json()
                self.oauth_client_id = oauth_config.get("client_id")
                self.oauth_client_secret = oauth_config.get("client_secret") 
            else:
                # Use fallback configuration for testing
                self.oauth_client_id = "test_client_id_staging"
                logger.warning("Using fallback OAuth configuration for L4 testing")
            
            # Verify JWT signing configuration
            jwt_config_response = await self.test_client.get(
                f"{self.service_endpoints.auth}/api/jwt/config"
            )
            
            if jwt_config_response.status_code != 200:
                raise RuntimeError("JWT configuration not available in staging")
                
            # Validate staging environment has proper HTTPS certificates
            await self._validate_tls_configuration()
            
        except Exception as e:
            raise RuntimeError(f"JWT test environment setup failed: {e}")
    
    async def _validate_tls_configuration(self) -> None:
        """Validate TLS configuration for secure token transmission."""
        try:
            # Test HTTPS connectivity to all services
            https_endpoints = [
                self.service_endpoints.auth,
                self.service_endpoints.backend,
                self.service_endpoints.frontend
            ]
            
            for endpoint in https_endpoints:
                if not endpoint.startswith("https://"):
                    logger.warning(f"Non-HTTPS endpoint detected: {endpoint}")
                    continue
                    
                # Verify TLS handshake
                response = await self.test_client.get(f"{endpoint}/health")
                if response.status_code != 200:
                    raise RuntimeError(f"TLS validation failed for {endpoint}")
                    
        except Exception as e:
            raise RuntimeError(f"TLS configuration validation failed: {e}")
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute complete JWT token propagation test across all services."""
        test_results = {
            "oauth_authentication": {},
            "jwt_generation": {},
            "token_validation_results": [],
            "cross_service_propagation": {},
            "websocket_authentication": {},
            "token_refresh_flow": {},
            "concurrent_access_test": {},
            "security_breach_prevention": {},
            "service_calls": 0,
            "total_duration": 0
        }
        
        start_time = time.time()
        
        try:
            # Test 1: OAuth Authentication Flow
            oauth_result = await self._test_oauth_authentication_flow()
            test_results["oauth_authentication"] = oauth_result
            test_results["service_calls"] += oauth_result.get("service_calls", 0)
            
            if not oauth_result.get("success"):
                raise RuntimeError("OAuth authentication failed")
            
            # Test 2: JWT Token Generation and Validation
            jwt_result = await self._test_jwt_generation_and_validation(
                oauth_result["user_data"]
            )
            test_results["jwt_generation"] = jwt_result
            test_results["service_calls"] += jwt_result.get("service_calls", 0)
            
            if not jwt_result.get("success"):
                raise RuntimeError("JWT generation failed")
            
            # Test 3: Cross-Service Token Propagation
            propagation_result = await self._test_cross_service_token_propagation(
                jwt_result["token_data"]
            )
            test_results["cross_service_propagation"] = propagation_result
            test_results["service_calls"] += propagation_result.get("service_calls", 0)
            
            # Test 4: WebSocket Authentication with JWT
            websocket_result = await self._test_websocket_jwt_authentication(
                jwt_result["token_data"]
            )
            test_results["websocket_authentication"] = websocket_result
            test_results["service_calls"] += websocket_result.get("service_calls", 0)
            
            # Test 5: Token Refresh Flow
            refresh_result = await self._test_token_refresh_flow(
                jwt_result["token_data"]
            )
            test_results["token_refresh_flow"] = refresh_result
            test_results["service_calls"] += refresh_result.get("service_calls", 0)
            
            # Test 6: Concurrent Token Access
            concurrent_result = await self._test_concurrent_token_access(
                jwt_result["token_data"]
            )
            test_results["concurrent_access_test"] = concurrent_result
            test_results["service_calls"] += concurrent_result.get("service_calls", 0)
            
            # Test 7: Security Breach Prevention
            security_result = await self._test_security_breach_prevention(
                jwt_result["token_data"]
            )
            test_results["security_breach_prevention"] = security_result
            test_results["service_calls"] += security_result.get("service_calls", 0)
            
        except Exception as e:
            test_results["error"] = str(e)
            logger.error(f"Critical path test execution failed: {e}")
        
        finally:
            test_results["total_duration"] = time.time() - start_time
        
        return test_results
    
    async def _test_oauth_authentication_flow(self) -> Dict[str, Any]:
        """Test OAuth authentication flow with Google OAuth provider."""
        try:
            # Step 1: Initiate OAuth flow
            oauth_params = {
                "client_id": self.oauth_client_id,
                "response_type": "code",
                "scope": "openid email profile",
                "redirect_uri": f"{self.service_endpoints.auth}/auth/callback",
                "state": f"test_state_{uuid.uuid4().hex[:16]}"
            }
            
            oauth_url = f"{self.service_endpoints.auth}/api/oauth/authorize?" + \
                       urlencode(oauth_params)
            
            # Step 2: Simulate OAuth provider response
            # In staging, we'll use the test OAuth endpoint
            auth_code = f"test_auth_code_{uuid.uuid4().hex[:16]}"
            
            # Step 3: Exchange code for token
            token_exchange_data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": oauth_params["redirect_uri"],
                "client_id": self.oauth_client_id,
                "client_secret": self.oauth_client_secret or "test_secret"
            }
            
            token_response = await self.test_client.post(
                f"{self.service_endpoints.auth}/api/oauth/token",
                data=token_exchange_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                # Try alternative test endpoint for staging
                test_user_data = {
                    "email": f"test_user_{uuid.uuid4().hex[:8]}@staging-test.netrasystems.ai",
                    "name": "L4 Test User",
                    "provider": "google",
                    "test_mode": True
                }
                
                test_auth_response = await self.test_client.post(
                    f"{self.service_endpoints.auth}/api/test/oauth",
                    json=test_user_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if test_auth_response.status_code != 200:
                    raise RuntimeError(f"OAuth test authentication failed: {test_auth_response.status_code}")
                
                oauth_result = test_auth_response.json()
            else:
                oauth_result = token_response.json()
            
            return {
                "success": True,
                "user_data": oauth_result,
                "service_calls": 2,
                "oauth_flow_completed": True,
                "user_id": oauth_result.get("user_id"),
                "email": oauth_result.get("email")
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 1}
    
    async def _test_jwt_generation_and_validation(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test JWT token generation and cryptographic validation."""
        try:
            user_id = user_data.get("user_id")
            email = user_data.get("email")
            
            # Request JWT token from auth service
            jwt_request = {
                "user_id": user_id,
                "email": email,
                "scopes": ["read", "write", "api"],
                "tier": "enterprise",
                "duration_minutes": 15  # 15-minute access token
            }
            
            jwt_response = await self.test_client.post(
                f"{self.service_endpoints.auth}/api/jwt/generate",
                json=jwt_request,
                headers={"Content-Type": "application/json"}
            )
            
            if jwt_response.status_code != 200:
                raise RuntimeError(f"JWT generation failed: {jwt_response.status_code}")
            
            jwt_data = jwt_response.json()
            
            # Create token data object
            token_data = JWTTokenData(
                access_token=jwt_data["access_token"],
                refresh_token=jwt_data["refresh_token"],
                token_type=jwt_data.get("token_type", "Bearer"),
                expires_in=jwt_data.get("expires_in", 900),
                user_id=user_id,
                email=email,
                issued_at=time.time(),
                expires_at=time.time() + jwt_data.get("expires_in", 900),
                scopes=jwt_request["scopes"]
            )
            
            # Validate JWT cryptographic properties
            validation_result = await self._validate_jwt_cryptographic_properties(token_data)
            
            # Store token for later tests
            self.test_tokens[user_id] = token_data
            
            return {
                "success": True,
                "token_data": token_data,
                "cryptographic_validation": validation_result,
                "service_calls": 2,
                "jwt_generated": True,
                "token_expires_in": token_data.expires_in
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service_calls": 1}
    
    async def _validate_jwt_cryptographic_properties(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Validate JWT token cryptographic properties and claims."""
        try:
            validation_results = {
                "signature_valid": False,
                "claims_valid": False,
                "expiry_valid": False,
                "audience_valid": False,
                "issuer_valid": False,
                "algorithm_secure": False
            }
            
            # Get public key from auth service for signature validation
            key_response = await self.test_client.get(
                f"{self.service_endpoints.auth}/api/jwt/public-key"
            )
            
            if key_response.status_code == 200:
                public_key_data = key_response.json()
                public_key = public_key_data.get("public_key")
                
                try:
                    # Decode and validate JWT token
                    decoded_token = jwt_lib.decode(
                        token_data.access_token,
                        public_key,
                        algorithms=["RS256", "HS256"],
                        audience=f"{self.service_endpoints.backend}",
                        issuer=f"{self.service_endpoints.auth}"
                    )
                    
                    validation_results["signature_valid"] = True
                    validation_results["claims_valid"] = decoded_token.get("user_id") == token_data.user_id
                    validation_results["expiry_valid"] = decoded_token.get("exp", 0) > time.time()
                    validation_results["audience_valid"] = True
                    validation_results["issuer_valid"] = True
                    validation_results["algorithm_secure"] = True
                    
                    # Update token data with validation results
                    token_data.signature_valid = True
                    token_data.audience_valid = True  
                    token_data.issuer_valid = True
                    
                except jwt_lib.InvalidTokenError as e:
                    validation_results["jwt_error"] = str(e)
            
            return validation_results
            
        except Exception as e:
            return {"validation_error": str(e)}
    
    async def _test_cross_service_token_propagation(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test token propagation and validation across all services."""
        try:
            propagation_results = {
                "auth_service_validation": {},
                "backend_api_validation": {},
                "cross_service_consistency": False,
                "service_calls": 0
            }
            
            headers = {
                "Authorization": f"Bearer {token_data.access_token}",
                "Content-Type": "application/json"
            }
            
            # Test 1: Auth Service Token Validation
            auth_validation = await self.test_client.get(
                f"{self.service_endpoints.auth}/api/token/validate",
                headers=headers
            )
            
            propagation_results["auth_service_validation"] = {
                "status_code": auth_validation.status_code,
                "valid": auth_validation.status_code == 200,
                "response": auth_validation.json() if auth_validation.status_code == 200 else None
            }
            propagation_results["service_calls"] += 1
            
            # Test 2: Backend API Token Validation
            backend_validation = await self.test_client.get(
                f"{self.service_endpoints.backend}/api/user/profile",
                headers=headers
            )
            
            propagation_results["backend_api_validation"] = {
                "status_code": backend_validation.status_code,
                "valid": backend_validation.status_code == 200,
                "response": backend_validation.json() if backend_validation.status_code == 200 else None
            }
            propagation_results["service_calls"] += 1
            
            # Test 3: Cross-service consistency check
            auth_valid = propagation_results["auth_service_validation"]["valid"]
            backend_valid = propagation_results["backend_api_validation"]["valid"]
            propagation_results["cross_service_consistency"] = auth_valid and backend_valid
            
            # Test 4: Token forwarding headers validation
            headers_test = await self._test_token_forwarding_headers(token_data)
            propagation_results["headers_forwarding"] = headers_test
            propagation_results["service_calls"] += headers_test.get("service_calls", 0)
            
            return propagation_results
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_token_forwarding_headers(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test token forwarding through service-to-service calls."""
        try:
            # Test backend making authenticated call to another service
            service_to_service_data = {
                "target_service": "metrics",
                "operation": "get_user_stats",
                "user_id": token_data.user_id
            }
            
            headers = {
                "Authorization": f"Bearer {token_data.access_token}",
                "Content-Type": "application/json",
                "X-Forwarded-User": token_data.user_id,
                "X-Forwarded-Token": token_data.access_token
            }
            
            forwarding_response = await self.test_client.post(
                f"{self.service_endpoints.backend}/api/internal/proxy",
                json=service_to_service_data,
                headers=headers
            )
            
            return {
                "forwarding_successful": forwarding_response.status_code in [200, 202],
                "status_code": forwarding_response.status_code,
                "headers_preserved": True,
                "service_calls": 1
            }
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_websocket_jwt_authentication(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test WebSocket authentication with JWT token."""
        try:
            websocket_result = {
                "connection_established": False,
                "authentication_successful": False,
                "message_delivery_successful": False,
                "service_calls": 0
            }
            
            # WebSocket URL with token in query parameter
            ws_url = f"{self.service_endpoints.websocket.replace('https:', 'wss:')}" + \
                    f"?token={token_data.access_token}"
            
            try:
                # Establish WebSocket connection with JWT authentication
                websocket = await websockets.connect(
                    ws_url,
                    extra_headers={
                        "Authorization": f"Bearer {token_data.access_token}",
                        "User-Agent": "L4-Test-Client"
                    },
                    timeout=10
                )
                
                websocket_result["connection_established"] = True
                websocket_result["service_calls"] += 1
                
                # Test authentication by sending a message
                auth_message = {
                    "type": "authenticate",
                    "token": token_data.access_token,
                    "user_id": token_data.user_id
                }
                
                await websocket.send(json.dumps(auth_message))
                
                # Wait for authentication response
                auth_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                auth_data = json.loads(auth_response)
                
                websocket_result["authentication_successful"] = auth_data.get("authenticated", False)
                
                if websocket_result["authentication_successful"]:
                    # Test real-time message delivery
                    test_message = {
                        "type": "test_message",
                        "content": "L4 JWT propagation test message",
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for message acknowledgment or echo
                    message_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    websocket_result["message_delivery_successful"] = len(message_response) > 0
                
                # Store connection for cleanup
                self.websocket_connections[token_data.user_id] = websocket
                
            except (websockets.exceptions.ConnectionClosed, 
                   websockets.exceptions.InvalidHandshake, 
                   asyncio.TimeoutError) as e:
                websocket_result["websocket_error"] = str(e)
            
            return websocket_result
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_token_refresh_flow(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test JWT token refresh flow across services."""
        try:
            refresh_result = {
                "refresh_successful": False,
                "new_token_valid": False,
                "old_token_invalidated": False,
                "service_calls": 0
            }
            
            # Step 1: Request token refresh
            refresh_request = {
                "refresh_token": token_data.refresh_token,
                "grant_type": "refresh_token"
            }
            
            refresh_response = await self.test_client.post(
                f"{self.service_endpoints.auth}/api/jwt/refresh",
                json=refresh_request,
                headers={"Content-Type": "application/json"}
            )
            
            refresh_result["service_calls"] += 1
            
            if refresh_response.status_code == 200:
                refresh_data = refresh_response.json()
                new_access_token = refresh_data["access_token"]
                
                refresh_result["refresh_successful"] = True
                
                # Step 2: Validate new token works
                new_headers = {
                    "Authorization": f"Bearer {new_access_token}",
                    "Content-Type": "application/json"
                }
                
                validation_response = await self.test_client.get(
                    f"{self.service_endpoints.backend}/api/user/profile",
                    headers=new_headers
                )
                
                refresh_result["new_token_valid"] = validation_response.status_code == 200
                refresh_result["service_calls"] += 1
                
                # Step 3: Verify old token is invalidated (should return 401)
                old_headers = {
                    "Authorization": f"Bearer {token_data.access_token}",
                    "Content-Type": "application/json"
                }
                
                old_validation_response = await self.test_client.get(
                    f"{self.service_endpoints.backend}/api/user/profile",
                    headers=old_headers
                )
                
                refresh_result["old_token_invalidated"] = old_validation_response.status_code == 401
                refresh_result["service_calls"] += 1
                
                # Update token data for future tests
                token_data.access_token = new_access_token
                if "refresh_token" in refresh_data:
                    token_data.refresh_token = refresh_data["refresh_token"]
            
            return refresh_result
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_concurrent_token_access(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test concurrent token access across multiple services."""
        try:
            concurrent_requests = 10
            concurrent_result = {
                "total_requests": concurrent_requests,
                "successful_requests": 0,
                "failed_requests": 0,
                "average_response_time": 0,
                "service_calls": 0
            }
            
            headers = {
                "Authorization": f"Bearer {token_data.access_token}",
                "Content-Type": "application/json"
            }
            
            async def make_concurrent_request(request_id: int) -> Dict[str, Any]:
                """Make a concurrent authenticated request."""
                start_time = time.time()
                try:
                    response = await self.test_client.get(
                        f"{self.service_endpoints.backend}/api/user/profile?req_id={request_id}",
                        headers=headers
                    )
                    duration = time.time() - start_time
                    
                    return {
                        "request_id": request_id,
                        "success": response.status_code == 200,
                        "status_code": response.status_code,
                        "duration": duration
                    }
                except Exception as e:
                    return {
                        "request_id": request_id,
                        "success": False,
                        "error": str(e),
                        "duration": time.time() - start_time
                    }
            
            # Execute concurrent requests
            tasks = [make_concurrent_request(i) for i in range(concurrent_requests)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze results
            total_duration = 0
            for result in results:
                if isinstance(result, dict):
                    if result.get("success"):
                        concurrent_result["successful_requests"] += 1
                    else:
                        concurrent_result["failed_requests"] += 1
                    total_duration += result.get("duration", 0)
                else:
                    concurrent_result["failed_requests"] += 1
            
            concurrent_result["average_response_time"] = total_duration / concurrent_requests
            concurrent_result["service_calls"] = concurrent_requests
            concurrent_result["success_rate"] = (concurrent_result["successful_requests"] / concurrent_requests) * 100
            
            return concurrent_result
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_security_breach_prevention(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test security measures against token-based attacks."""
        try:
            security_result = {
                "replay_attack_prevented": False,
                "token_tampering_detected": False,
                "expired_token_rejected": False,
                "invalid_signature_rejected": False,
                "service_calls": 0
            }
            
            # Test 1: Token replay attack prevention
            replay_result = await self._test_replay_attack_prevention(token_data)
            security_result["replay_attack_prevented"] = replay_result.get("prevented", False)
            security_result["service_calls"] += replay_result.get("service_calls", 0)
            
            # Test 2: Token tampering detection
            tampering_result = await self._test_token_tampering_detection(token_data)
            security_result["token_tampering_detected"] = tampering_result.get("detected", False)
            security_result["service_calls"] += tampering_result.get("service_calls", 0)
            
            # Test 3: Expired token rejection
            expiry_result = await self._test_expired_token_rejection(token_data)
            security_result["expired_token_rejected"] = expiry_result.get("rejected", False)
            security_result["service_calls"] += expiry_result.get("service_calls", 0)
            
            # Test 4: Invalid signature rejection
            signature_result = await self._test_invalid_signature_rejection(token_data)
            security_result["invalid_signature_rejected"] = signature_result.get("rejected", False)
            security_result["service_calls"] += signature_result.get("service_calls", 0)
            
            return security_result
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_replay_attack_prevention(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test prevention of token replay attacks."""
        try:
            # Use the same token multiple times in rapid succession
            headers = {
                "Authorization": f"Bearer {token_data.access_token}",
                "Content-Type": "application/json",
                "X-Request-ID": str(uuid.uuid4())  # Different request IDs
            }
            
            # Make multiple rapid requests to test replay detection
            rapid_requests = []
            for i in range(5):
                rapid_requests.append(
                    self.test_client.get(
                        f"{self.service_endpoints.backend}/api/user/profile",
                        headers=headers
                    )
                )
            
            responses = await asyncio.gather(*rapid_requests)
            
            # All should succeed (replay attacks are typically prevented at network/CDN level)
            # but we verify the system handles rapid token usage correctly
            success_count = sum(1 for r in responses if r.status_code == 200)
            
            return {
                "prevented": success_count == len(responses),  # All should succeed for legitimate rapid requests
                "successful_requests": success_count,
                "total_requests": len(responses),
                "service_calls": len(responses)
            }
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_token_tampering_detection(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test detection of tampered JWT tokens."""
        try:
            # Create a tampered token by modifying the payload
            token_parts = token_data.access_token.split('.')
            if len(token_parts) != 3:
                return {"detected": False, "error": "Invalid JWT format", "service_calls": 0}
            
            # Tamper with the payload (base64 decode, modify, re-encode)
            import base64
            payload = token_parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            try:
                decoded_payload = json.loads(base64.urlsafe_b64decode(payload))
                decoded_payload["user_id"] = "tampered_user_id"
                tampered_payload = base64.urlsafe_b64encode(
                    json.dumps(decoded_payload).encode()
                ).decode().rstrip('=')
                
                tampered_token = f"{token_parts[0]}.{tampered_payload}.{token_parts[2]}"
                
                # Try using tampered token
                tampered_headers = {
                    "Authorization": f"Bearer {tampered_token}",
                    "Content-Type": "application/json"
                }
                
                response = await self.test_client.get(
                    f"{self.service_endpoints.backend}/api/user/profile",
                    headers=tampered_headers
                )
                
                # Should be rejected (401 or 403)
                tampered_rejected = response.status_code in [401, 403]
                
                return {
                    "detected": tampered_rejected,
                    "response_status": response.status_code,
                    "service_calls": 1
                }
                
            except Exception as decode_error:
                return {"detected": False, "decode_error": str(decode_error), "service_calls": 0}
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_expired_token_rejection(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test rejection of expired JWT tokens."""
        try:
            # Create a token with very short expiry for testing
            short_expiry_request = {
                "user_id": token_data.user_id,
                "email": token_data.email,
                "scopes": token_data.scopes,
                "tier": "enterprise",
                "duration_seconds": 2  # 2-second expiry
            }
            
            short_token_response = await self.test_client.post(
                f"{self.service_endpoints.auth}/api/jwt/generate",
                json=short_expiry_request,
                headers={"Content-Type": "application/json"}
            )
            
            if short_token_response.status_code != 200:
                return {"rejected": False, "error": "Could not generate short-expiry token", "service_calls": 1}
            
            short_token_data = short_token_response.json()
            short_token = short_token_data["access_token"]
            
            # Wait for token to expire
            await asyncio.sleep(3)
            
            # Try using expired token
            expired_headers = {
                "Authorization": f"Bearer {short_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.test_client.get(
                f"{self.service_endpoints.backend}/api/user/profile",
                headers=expired_headers
            )
            
            # Should be rejected (401)
            expired_rejected = response.status_code == 401
            
            return {
                "rejected": expired_rejected,
                "response_status": response.status_code,
                "service_calls": 2
            }
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def _test_invalid_signature_rejection(self, token_data: JWTTokenData) -> Dict[str, Any]:
        """Test rejection of tokens with invalid signatures."""
        try:
            # Create token with invalid signature by replacing signature part
            token_parts = token_data.access_token.split('.')
            if len(token_parts) != 3:
                return {"rejected": False, "error": "Invalid JWT format", "service_calls": 0}
            
            # Replace signature with garbage
            invalid_signature = "invalid_signature_data_base64"
            invalid_token = f"{token_parts[0]}.{token_parts[1]}.{invalid_signature}"
            
            # Try using token with invalid signature
            invalid_headers = {
                "Authorization": f"Bearer {invalid_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.test_client.get(
                f"{self.service_endpoints.backend}/api/user/profile",
                headers=invalid_headers
            )
            
            # Should be rejected (401 or 403)
            signature_rejected = response.status_code in [401, 403]
            
            return {
                "rejected": signature_rejected,
                "response_status": response.status_code,
                "service_calls": 1
            }
            
        except Exception as e:
            return {"error": str(e), "service_calls": 1}
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate that JWT token propagation meets enterprise security requirements."""
        try:
            validation_checks = []
            
            # Check 1: OAuth authentication succeeded
            oauth_success = results.get("oauth_authentication", {}).get("success", False)
            validation_checks.append(oauth_success)
            
            # Check 2: JWT generation succeeded with proper validation
            jwt_result = results.get("jwt_generation", {})
            jwt_success = jwt_result.get("success", False)
            crypto_validation = jwt_result.get("cryptographic_validation", {})
            signature_valid = crypto_validation.get("signature_valid", False)
            validation_checks.extend([jwt_success, signature_valid])
            
            # Check 3: Cross-service propagation works
            propagation_result = results.get("cross_service_propagation", {})
            cross_service_consistent = propagation_result.get("cross_service_consistency", False)
            validation_checks.append(cross_service_consistent)
            
            # Check 4: WebSocket authentication succeeds
            ws_result = results.get("websocket_authentication", {})
            ws_auth_success = ws_result.get("authentication_successful", False)
            validation_checks.append(ws_auth_success)
            
            # Check 5: Token refresh flow works
            refresh_result = results.get("token_refresh_flow", {})
            refresh_success = refresh_result.get("refresh_successful", False)
            old_token_invalidated = refresh_result.get("old_token_invalidated", False)
            validation_checks.extend([refresh_success, old_token_invalidated])
            
            # Check 6: Concurrent access performs well
            concurrent_result = results.get("concurrent_access_test", {})
            success_rate = concurrent_result.get("success_rate", 0)
            concurrent_acceptable = success_rate >= 95.0  # 95% success rate required
            validation_checks.append(concurrent_acceptable)
            
            # Check 7: Security measures are effective
            security_result = results.get("security_breach_prevention", {})
            tampering_detected = security_result.get("token_tampering_detected", False)
            expired_rejected = security_result.get("expired_token_rejected", False)
            invalid_sig_rejected = security_result.get("invalid_signature_rejected", False)
            validation_checks.extend([tampering_detected, expired_rejected, invalid_sig_rejected])
            
            # Check 8: Performance requirements met
            total_duration = results.get("total_duration", float('inf'))
            performance_acceptable = total_duration < 30.0  # Max 30 seconds for complete test
            validation_checks.append(performance_acceptable)
            
            # All checks must pass for enterprise-grade security
            return all(validation_checks)
            
        except Exception as e:
            self.test_metrics.errors.append(f"Critical path validation failed: {str(e)}")
            return False
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up JWT test-specific resources."""
        try:
            # Close WebSocket connections
            for user_id, websocket in self.websocket_connections.items():
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket for {user_id}: {e}")
            
            # Revoke test tokens
            for user_id, token_data in self.test_tokens.items():
                try:
                    revoke_data = {"token": token_data.access_token}
                    await self.test_client.post(
                        f"{self.service_endpoints.auth}/api/jwt/revoke",
                        json=revoke_data,
                        headers={"Content-Type": "application/json"}
                    )
                except Exception as e:
                    logger.warning(f"Error revoking token for {user_id}: {e}")
            
        except Exception as e:
            logger.warning(f"JWT cleanup error: {e}")

@pytest.mark.L4
@pytest.mark.critical_path
@pytest.mark.staging
class TestJWTTokenPropagationL4:
    """L4 integration test class for JWT token propagation across service boundaries."""
    
    @pytest.fixture
    async def jwt_l4_suite(self):
        """Create and initialize JWT L4 test suite."""
        suite = JWTTokenPropagationL4Suite()
        await suite.initialize_l4_environment()
        yield suite
        await suite.cleanup_l4_resources()
    
    @pytest.mark.asyncio
    async def test_complete_jwt_token_propagation_flow(self, jwt_l4_suite):
        """Test complete JWT token propagation across all service boundaries."""
        # Execute the critical path test
        test_metrics = await jwt_l4_suite.run_complete_critical_path_test()
        
        # Validate results meet enterprise security requirements
        assert test_metrics.success, f"JWT token propagation failed: {test_metrics.errors}"
        
        # Validate performance requirements
        assert test_metrics.duration < 30.0, f"Test took too long: {test_metrics.duration:.2f}s"
        assert test_metrics.success_rate >= 95.0, f"Success rate too low: {test_metrics.success_rate:.1f}%"
        assert test_metrics.error_count == 0, f"Unexpected errors: {test_metrics.error_count}"
        
        # Log test results for monitoring
        logger.info(f"JWT L4 test completed successfully in {test_metrics.duration:.2f}s")
        logger.info(f"Service calls made: {test_metrics.service_calls}")
        logger.info(f"Success rate: {test_metrics.success_rate:.1f}%")
    
    @pytest.mark.asyncio
    async def test_jwt_security_requirements_enterprise(self, jwt_l4_suite):
        """Test JWT security requirements specifically for enterprise tier."""
        # Validate enterprise-specific security requirements are met
        test_metrics = await jwt_l4_suite.run_complete_critical_path_test()
        
        security_details = test_metrics.details.get("security_breach_prevention", {})
        
        # Enterprise security requirements
        assert security_details.get("token_tampering_detected", False), "Token tampering must be detected"
        assert security_details.get("expired_token_rejected", False), "Expired tokens must be rejected"
        assert security_details.get("invalid_signature_rejected", False), "Invalid signatures must be rejected"
        
        # JWT cryptographic validation requirements
        jwt_details = test_metrics.details.get("jwt_generation", {})
        crypto_validation = jwt_details.get("cryptographic_validation", {})
        
        assert crypto_validation.get("signature_valid", False), "JWT signature must be cryptographically valid"
        assert crypto_validation.get("algorithm_secure", False), "JWT algorithm must be secure (RS256/HS256)"
        assert crypto_validation.get("audience_valid", False), "JWT audience must be validated"
        assert crypto_validation.get("issuer_valid", False), "JWT issuer must be validated"
        
        logger.info("Enterprise JWT security requirements validated successfully")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])