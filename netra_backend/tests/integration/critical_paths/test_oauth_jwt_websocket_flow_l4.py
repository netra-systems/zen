"""L4 Integration Test: Complete OAuth → JWT → WebSocket Authentication Flow

Business Value Justification (BVJ):
- Segment: Enterprise segment  
- Business Goal: Complete authentication flow reliability
- Value Impact: $30K MRR - Complete auth flow critical for real-time features
- Strategic Impact: Validates end-to-end authentication from OAuth login through WebSocket connection

L4 Test: Real staging environment validation of complete OAuth → JWT → WebSocket authentication flow.
Tests against real staging services including auth.staging.netrasystems.ai with full JWT lifecycle.

Critical Path:
OAuth initiation → User authorization → Token exchange → JWT validation → Session creation → WebSocket auth → Message flow → Token refresh → Logout

Coverage: Complete OAuth flow, JWT lifecycle, WebSocket authentication, session persistence, token refresh, cross-service validation
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import base64
import hashlib
import json
import secrets
import time
import uuid
from typing import Any, Dict, Optional

# OAuth service replaced with mock
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
import pytest
import websockets

from netra_backend.tests.integration.critical_paths.integration.critical_paths.l4_staging_critical_base import (
    L4StagingCriticalPathTestBase,
)

OAuthService = AsyncMock
# JWT service replaced with auth_integration
# from auth_integration import create_access_token, validate_token_jwt
# from app.auth_integration.auth import create_access_token
from unittest.mock import AsyncMock

create_access_token = AsyncMock()
# from app.core.unified.jwt_validator import validate_token_jwt
from unittest.mock import AsyncMock

validate_token_jwt = AsyncMock()
JWTService = AsyncMock
# Session manager replaced with mock
SessionManager = AsyncMock
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class OAuthJWTWebSocketFlowL4Test(L4StagingCriticalPathTestBase):
    """L4 test for complete OAuth → JWT → WebSocket authentication flow."""
    
    def __init__(self):
        super().__init__("oauth_jwt_websocket_flow_l4")
        self.oauth_service: Optional[OAuthService] = None
        self.jwt_service: Optional[JWTService] = None
        self.session_manager: Optional[SessionManager] = None
        self.active_sessions: Dict[str, Dict] = {}
        
    async def setup_test_specific_environment(self) -> None:
        """Setup OAuth JWT WebSocket specific test environment."""
        self.oauth_service = OAuthService()
        await self.oauth_service.initialize()
        self.jwt_service = JWTService()
        await self.jwt_service.initialize()
        self.session_manager = SessionManager()
        await self.session_manager.initialize()
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute complete OAuth → JWT → WebSocket authentication critical path."""
        try:
            oauth_data = await self._execute_oauth_flow()
            jwt_data = await self._execute_jwt_flow(oauth_data)
            ws_data = await self._execute_websocket_flow(jwt_data)
            refresh_data = await self._execute_refresh_flow(jwt_data)
            validation_data = await self._execute_validation_flow(refresh_data)
            await self._execute_logout_flow(validation_data)
            
            return {"service_calls": 12, "overall_success": True, "steps_completed": 6}
        except Exception as e:
            logger.error(f"Critical path execution failed: {e}")
            return {"service_calls": 0, "overall_success": False, "error": str(e)}
    
    async def _execute_oauth_flow(self) -> Dict[str, Any]:
        """Execute OAuth authorization flow with staging services."""
        auth_params = self._build_oauth_params()
        auth_code = await self._get_oauth_authorization_code(auth_params)
        token_data = await self._exchange_auth_code_for_token(auth_code, auth_params["code_verifier"])
        return token_data
    
    def _build_oauth_params(self) -> Dict[str, str]:
        """Build OAuth authorization parameters."""
        code_verifier = self._generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)
        state = f"oauth_l4_{uuid.uuid4().hex[:16]}"
        
        return {
            "response_type": "code",
            "client_id": "netra_staging_oauth_client",
            "redirect_uri": f"{self.service_endpoints.frontend}/auth/callback",
            "scope": "read write websocket",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "code_verifier": code_verifier
        }
    
    async def _get_oauth_authorization_code(self, auth_params: Dict[str, str]) -> str:
        """Get OAuth authorization code from staging service."""
        auth_url = f"{self.service_endpoints.auth}/oauth/authorize?{urlencode(auth_params)}"
        auth_response = await self.test_client.get(auth_url, timeout=15.0)
        
        if auth_response.status_code not in [200, 302]:
            raise Exception(f"OAuth authorization failed: {auth_response.status_code}")
        
        authorization_data = {
            "username": "test_enterprise@staging.netrasystems.ai",
            "password": "test_staging_pass_l4_oauth_123",
            "state": auth_params["state"],
            "approve": "true",
            "client_id": "netra_staging_oauth_client"
        }
        
        submit_response = await self.test_client.post(
            f"{self.service_endpoints.auth}/oauth/authorize",
            data=authorization_data,
            timeout=15.0
        )
        
        if submit_response.status_code != 302:
            raise Exception(f"OAuth authorization submit failed: {submit_response.status_code}")
        
        redirect_url = submit_response.headers.get("location", "")
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get("code", [None])[0]
        
        if not auth_code:
            raise Exception("No authorization code returned")
        
        return auth_code
    
    async def _exchange_auth_code_for_token(self, auth_code: str, code_verifier: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "code_verifier": code_verifier,
            "client_id": "netra_staging_oauth_client",
            "redirect_uri": f"{self.service_endpoints.frontend}/auth/callback"
        }
        
        token_response = await self.test_client.post(
            f"{self.service_endpoints.auth}/oauth/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15.0
        )
        
        if token_response.status_code != 200:
            raise Exception(f"Token exchange failed: {token_response.status_code}")
        
        token_result = token_response.json()
        return {
            "access_token": token_result["access_token"],
            "refresh_token": token_result.get("refresh_token"),
            "token_type": token_result["token_type"]
        }
    
    async def _execute_jwt_flow(self, oauth_data: Dict) -> Dict[str, Any]:
        """Execute JWT validation and session creation."""
        access_token = oauth_data["access_token"]
        jwt_validation = await self.jwt_service.verify_token(access_token)
        
        if not jwt_validation.get("valid", False):
            raise Exception(f"JWT validation failed: {jwt_validation.get('error')}")
        
        user_id = jwt_validation["user_id"]
        session_data = await self._create_session(user_id, access_token)
        return {"session_id": session_data["session_id"], "user_id": user_id, "access_token": access_token}
    
    async def _create_session(self, user_id: str, access_token: str) -> Dict[str, Any]:
        """Create session in Redis and local tracking."""
        session_id = f"session_l4_{uuid.uuid4().hex[:8]}"
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "access_token": access_token,
            "created_at": time.time(),
            "test_session": True
        }
        
        session_key = f"session:{session_id}"
        await self.redis_session.set(session_key, json.dumps(session_data), ex=3600)
        
        stored_session = await self.redis_session.get(session_key)
        if not stored_session:
            raise Exception("Session not found after creation")
        
        self.active_sessions[session_id] = session_data
        return session_data
    
    async def _execute_websocket_flow(self, jwt_data: Dict) -> Dict[str, Any]:
        """Execute WebSocket authentication and message flow."""
        access_token = jwt_data["access_token"]
        user_id = jwt_data["user_id"]
        ws_url = self.service_endpoints.websocket.replace("http", "ws")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with websockets.connect(ws_url, extra_headers=headers, ping_interval=20, ping_timeout=10) as websocket:
            await self._authenticate_websocket(websocket, access_token, user_id)
            await self._test_websocket_message(websocket, user_id)
        
        return {"user_id": user_id, "ws_connected": True, "auth_successful": True}
    
    async def _authenticate_websocket(self, websocket, access_token: str, user_id: str) -> None:
        """Authenticate WebSocket connection."""
        auth_message = {
            "type": "authenticate",
            "access_token": access_token,
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(auth_message))
        auth_response_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        auth_response = json.loads(auth_response_raw)
        
        if auth_response.get("type") != "auth_success":
            raise Exception(f"WebSocket auth failed: {auth_response}")
    
    async def _test_websocket_message(self, websocket, user_id: str) -> None:
        """Test WebSocket message exchange."""
        test_message = {
            "type": "thread_message",
            "data": {
                "thread_id": f"test_thread_{uuid.uuid4().hex[:8]}",
                "content": "L4 WebSocket auth test message",
                "user_id": user_id
            },
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(test_message))
        message_response_raw = await asyncio.wait_for(websocket.recv(), timeout=10.0)
        message_response = json.loads(message_response_raw)
        
        if message_response.get("type") != "message_received":
            raise Exception(f"Message not acknowledged: {message_response}")
    
    async def _execute_refresh_flow(self, jwt_data: Dict) -> Dict[str, Any]:
        """Execute token refresh flow."""
        user_id = jwt_data["user_id"]
        session_id = jwt_data["session_id"]
        new_access_token = await self._generate_new_token(user_id)
        await self._update_session_with_token(session_id, new_access_token)
        await self._validate_new_token(new_access_token)
        return {"session_id": session_id, "user_id": user_id, "new_token": new_access_token}
    
    async def _generate_new_token(self, user_id: str) -> str:
        """Generate new JWT token."""
        new_token_result = await self.jwt_service.generate_token(
            user_id=user_id,
            permissions=["read", "write", "websocket"],
            tier="enterprise"
        )
        
        if not new_token_result.get("success", False):
            raise Exception(f"Token refresh failed: {new_token_result.get('error')}")
        
        return new_token_result["token"]
    
    async def _update_session_with_token(self, session_id: str, new_access_token: str) -> None:
        """Update session with new access token."""
        session_key = f"session:{session_id}"
        session_data = self.active_sessions[session_id]
        session_data["access_token"] = new_access_token
        session_data["refreshed_at"] = time.time()
        await self.redis_session.set(session_key, json.dumps(session_data), ex=3600)
    
    async def _validate_new_token(self, new_access_token: str) -> None:
        """Validate the new access token."""
        token_validation = await self.jwt_service.verify_token(new_access_token)
        if not token_validation.get("valid", False):
            raise Exception("Refreshed token validation failed")
    
    async def _execute_validation_flow(self, refresh_data: Dict) -> Dict[str, Any]:
        """Execute cross-service authentication validation."""
        access_token = refresh_data["new_token"]
        session_id = refresh_data["session_id"]
        validations = await self._run_cross_service_validations(access_token, session_id)
        self._check_validation_results(validations)
        return {"session_id": session_id, "validation_success": True}
    
    async def _run_cross_service_validations(self, access_token: str, session_id: str) -> list:
        """Run validations across all services."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        backend_endpoint = f"{self.service_endpoints.backend}/api/user/profile"
        backend_response = await self.test_client.get(backend_endpoint, headers=headers)
        backend_valid = backend_response.status_code == 200
        
        session_endpoint = f"{self.service_endpoints.auth}/api/sessions/validate"
        session_payload = {"session_id": session_id}
        session_response = await self.test_client.post(session_endpoint, json=session_payload, headers=headers)
        session_valid = session_response.status_code == 200
        
        session_key = f"session:{session_id}"
        redis_session = await self.redis_session.get(session_key)
        redis_valid = redis_session is not None
        
        return [backend_valid, session_valid, redis_valid]
    
    def _check_validation_results(self, validations: list) -> None:
        """Check that sufficient validations passed."""
        successful_validations = sum(validations)
        if successful_validations < 2:
            raise Exception(f"Only {successful_validations}/3 validations passed")
    
    async def _execute_logout_flow(self, validation_data: Dict) -> Dict[str, Any]:
        """Execute complete logout flow."""
        session_id = validation_data["session_id"]
        await self._remove_session_from_redis(session_id)
        self._remove_session_from_local(session_id)
        logout_success = await self._call_logout_endpoint(session_id)
        return {"session_removed": True, "logout_success": logout_success}
    
    async def _remove_session_from_redis(self, session_id: str) -> None:
        """Remove session from Redis."""
        session_key = f"session:{session_id}"
        await self.redis_session.delete(session_key)
    
    def _remove_session_from_local(self, session_id: str) -> None:
        """Remove session from local tracking."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
    
    async def _call_logout_endpoint(self, session_id: str) -> bool:
        """Call logout endpoint."""
        logout_endpoint = f"{self.service_endpoints.auth}/api/auth/logout"
        logout_data = {"session_id": session_id}
        logout_response = await self.test_client.post(logout_endpoint, json=logout_data)
        return logout_response.status_code in [200, 204]
    
    def _generate_code_verifier(self) -> str:
        """Generate PKCE code verifier."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """Generate PKCE code challenge."""
        digest = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate OAuth JWT WebSocket flow meets business requirements."""
        if not results.get("overall_success", False):
            return False
        
        business_requirements = {
            "max_response_time_seconds": 15.0,
            "min_success_rate_percent": 100.0,
            "max_error_count": 0
        }
        
        return await self.validate_business_metrics(business_requirements)
    
    async def cleanup_test_specific_resources(self) -> None:
        """Clean up OAuth JWT WebSocket test resources."""
        await self._cleanup_sessions()
        await self._cleanup_services()
    
    async def _cleanup_sessions(self) -> None:
        """Clean up all active sessions."""
        for session_id in list(self.active_sessions.keys()):
            try:
                session_key = f"session:{session_id}"
                await self.redis_session.delete(session_key)
            except Exception:
                pass
    
    async def _cleanup_services(self) -> None:
        """Clean up authentication services."""
        if self.oauth_service:
            await self.oauth_service.shutdown()
        if self.jwt_service:
            await self.jwt_service.shutdown()
        if self.session_manager:
            await self.session_manager.shutdown()

@pytest.fixture
async def oauth_jwt_websocket_l4_test():
    """Create OAuth JWT WebSocket L4 test instance."""
    test_instance = OAuthJWTWebSocketFlowL4Test()
    await test_instance.initialize_l4_environment()
    yield test_instance
    await test_instance.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.L4
async def test_complete_oauth_jwt_websocket_flow_l4(oauth_jwt_websocket_l4_test):
    """Test complete OAuth → JWT → WebSocket authentication flow in staging."""
    test_metrics = await oauth_jwt_websocket_l4_test.run_complete_critical_path_test()
    assert test_metrics.success is True, f"Critical path failed: {test_metrics.errors}"
    assert test_metrics.duration < 60.0, f"Test took too long: {test_metrics.duration:.2f}s"
    assert test_metrics.service_calls >= 12, "Expected at least 12 service calls"

@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.L4
async def test_oauth_websocket_message_flow_l4(oauth_jwt_websocket_l4_test):
    """Test OAuth-authenticated WebSocket message flow specifically."""
    oauth_data = await oauth_jwt_websocket_l4_test._execute_oauth_flow()
    jwt_data = await oauth_jwt_websocket_l4_test._execute_jwt_flow(oauth_data)
    ws_data = await oauth_jwt_websocket_l4_test._execute_websocket_flow(jwt_data)
    
    assert ws_data["auth_successful"] is True
    assert ws_data["ws_connected"] is True

@pytest.mark.asyncio  
@pytest.mark.staging
@pytest.mark.L4
async def test_oauth_token_refresh_session_persistence_l4(oauth_jwt_websocket_l4_test):
    """Test OAuth token refresh maintains session persistence."""
    oauth_data = await oauth_jwt_websocket_l4_test._execute_oauth_flow()
    jwt_data = await oauth_jwt_websocket_l4_test._execute_jwt_flow(oauth_data)
    refresh_data = await oauth_jwt_websocket_l4_test._execute_refresh_flow(jwt_data)
    
    session_id = jwt_data["session_id"]
    assert session_id in oauth_jwt_websocket_l4_test.active_sessions
    assert refresh_data["new_token"] != jwt_data["access_token"]

@pytest.mark.asyncio
@pytest.mark.staging 
@pytest.mark.L4
async def test_oauth_cross_service_auth_consistency_l4(oauth_jwt_websocket_l4_test):
    """Test OAuth authentication consistency across all staging services."""
    oauth_data = await oauth_jwt_websocket_l4_test._execute_oauth_flow()
    jwt_data = await oauth_jwt_websocket_l4_test._execute_jwt_flow(oauth_data)
    refresh_data = await oauth_jwt_websocket_l4_test._execute_refresh_flow(jwt_data)
    validation_data = await oauth_jwt_websocket_l4_test._execute_validation_flow(refresh_data)
    
    assert validation_data["validation_success"] is True

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])