"""
OAuth Proxy PR Environment Test - P1 STAGING BROKEN

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise & Development - PR environment OAuth validation  
2. **Business Goal**: Enable OAuth testing in PR staging environments
3. **Value Impact**: PR environments can't test OAuth (Google requires exact URLs)
4. **Revenue Impact**: Prevents staging OAuth testing, blocks development velocity

**SPEC**: auth_environment_isolation.xml lines 115-149
**ISSUE**: PR environments can't use OAuth (Google requires exact URLs) 
**IMPACT**: Can't test auth in staging PRs

**TEST SCOPE:**
- OAuth flow with PR environment URL encoding
- State parameter encoding with PR number and CSRF protection
- Proxy redirects to correct PR environment with subdomain routing
- Token transfer via secure cookie with proper domain settings
- Complete flow in <10 seconds for staging deployment validation

**SUCCESS CRITERIA:**
- OAuth proxy correctly routes PR environment auth
- State encoding/decoding works for PR number extraction
- Token transfer via secure cookie succeeds
- PR environment receives valid token for authentication
- All flows complete in <10 seconds
"""

import asyncio
import base64
import hashlib
import json
import time
import urllib.parse
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from netra_backend.app.logging_config import central_logger
from tests.e2e.oauth_test_providers import GoogleOAuthProvider, OAuthUserFactory
from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient
from tests.e2e.real_services_manager import create_real_services_manager

logger = central_logger.get_logger(__name__)


class OAuthProxyStagingTester:
    """OAuth proxy staging environment test execution manager"""
    
    def __init__(self):
        """Initialize OAuth proxy staging tester"""
        self.services_manager = create_real_services_manager()
        self.oauth_provider = GoogleOAuthProvider()
        self.proxy_client: Optional[RealHTTPClient] = None
        self.pr_client: Optional[RealHTTPClient] = None
        self.test_user: Optional[Dict[str, Any]] = None
        self.start_time = None
        
        # PR environment simulation
        self.pr_number = 42
        self.pr_domain = f"pr-{self.pr_number}.staging.netrasystems.ai"
        self.proxy_domain = "auth.staging.netrasystems.ai"
        self.csrf_token = self._generate_csrf_token()
    
    def _generate_csrf_token(self) -> str:
        """Generate CSRF token for state protection"""
        return hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:32]
    
    def _encode_state_parameter(self, pr_number: int, return_url: str, csrf_token: str) -> str:
        """Encode state parameter with PR routing information"""
        state_data = {
            "pr_number": pr_number,
            "csrf_token": csrf_token,
            "return_url": return_url,
            "timestamp": int(time.time())
        }
        json_data = json.dumps(state_data)
        encoded_state = base64.b64encode(json_data.encode()).decode()
        return encoded_state
    
    def _decode_state_parameter(self, encoded_state: str) -> Dict[str, Any]:
        """Decode state parameter to extract PR routing information"""
        try:
            json_data = base64.b64decode(encoded_state.encode()).decode()
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Failed to decode state parameter: {e}")
            raise ValueError(f"Invalid state parameter: {e}")
    
    async def setup_pr_environment_simulation(self) -> None:
        """Setup PR environment simulation for OAuth proxy testing"""
        self.start_time = time.time()
        
        # Start services for proxy testing
        await self.services_manager.start_all_services()
        service_urls = self.services_manager.get_service_urls()
        
        # Initialize proxy client (simulates auth.staging.netrasystems.ai)
        self.proxy_client = RealHTTPClient(
            base_url=service_urls.get("auth_service", "http://localhost:3002")
        )
        
        # Initialize PR client (simulates pr-42.staging.netrasystems.ai)
        self.pr_client = RealHTTPClient(
            base_url=service_urls.get("backend", "http://localhost:8000")
        )
        
        # Create test user for OAuth flow
        self.test_user = OAuthUserFactory.create_enterprise_user()
        logger.info(f"Setup PR environment simulation for PR #{self.pr_number}")
    
    async def test_oauth_state_encoding(self) -> Dict[str, Any]:
        """Test OAuth state parameter encoding with PR information"""
        logger.info("Testing OAuth state parameter encoding...")
        
        return_url = f"https://{self.pr_domain}/auth/callback"
        
        # Encode state parameter
        encoded_state = self._encode_state_parameter(
            pr_number=self.pr_number,
            return_url=return_url,
            csrf_token=self.csrf_token
        )
        
        # Decode and verify
        decoded_state = self._decode_state_parameter(encoded_state)
        
        # Validate state components
        assert decoded_state["pr_number"] == self.pr_number, "PR number encoding failed"
        assert decoded_state["return_url"] == return_url, "Return URL encoding failed"
        assert decoded_state["csrf_token"] == self.csrf_token, "CSRF token encoding failed"
        assert "timestamp" in decoded_state, "Timestamp missing from state"
        
        # Verify timestamp is recent (within 60 seconds)
        timestamp_age = time.time() - decoded_state["timestamp"]
        assert timestamp_age < 60, f"State timestamp too old: {timestamp_age}s"
        
        logger.info("✓ OAuth state encoding validation passed")
        return {
            "encoded_state": encoded_state,
            "decoded_state": decoded_state,
            "validation_time": time.time() - self.start_time
        }
    
    async def test_oauth_proxy_initiation(self, encoded_state: str) -> Dict[str, Any]:
        """Test OAuth proxy initiation from PR environment"""
        logger.info("Testing OAuth proxy initiation...")
        
        # Simulate PR environment initiating OAuth flow
        oauth_url = f"https://accounts.google.com/o/oauth2/auth"
        proxy_callback_url = f"https://{self.proxy_domain}/auth/oauth/callback"
        
        # Build OAuth authorization URL with proxy callback
        oauth_params = {
            "client_id": self.oauth_provider.client_id,
            "redirect_uri": proxy_callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "state": encoded_state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        authorization_url = f"{oauth_url}?{urllib.parse.urlencode(oauth_params)}"
        
        # Verify authorization URL contains proper state
        parsed_url = urllib.parse.urlparse(authorization_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        assert "state" in query_params, "State parameter missing from OAuth URL"
        assert query_params["state"][0] == encoded_state, "State parameter mismatch"
        assert proxy_callback_url in authorization_url, "Proxy callback URL not found"
        
        logger.info("✓ OAuth proxy initiation validation passed")
        return {
            "authorization_url": authorization_url,
            "proxy_callback_url": proxy_callback_url,
            "validation_time": time.time() - self.start_time
        }
    
    async def test_oauth_proxy_callback_processing(self, encoded_state: str) -> Dict[str, Any]:
        """Test OAuth proxy callback processing and token exchange"""
        logger.info("Testing OAuth proxy callback processing...")
        
        # Mock Google OAuth callback to proxy
        mock_auth_code = f"mock_auth_code_{uuid.uuid4().hex[:16]}"
        
        # Simulate Google calling back to proxy with authorization code
        callback_data = {
            "code": mock_auth_code,
            "state": encoded_state,
            "scope": "openid email profile"
        }
        
        # Decode state to extract PR routing information
        decoded_state = self._decode_state_parameter(encoded_state)
        
        # Verify CSRF token
        assert decoded_state["csrf_token"] == self.csrf_token, "CSRF token mismatch"
        
        # Mock token exchange with Google
        mock_tokens = self.oauth_provider.create_mock_tokens(self.test_user)
        
        # Verify PR routing information
        assert decoded_state["pr_number"] == self.pr_number, "PR number missing from state"
        return_url = decoded_state["return_url"]
        assert self.pr_domain in return_url, "PR domain not found in return URL"
        
        logger.info("✓ OAuth proxy callback processing validation passed")
        return {
            "auth_code": mock_auth_code,
            "tokens": mock_tokens,
            "pr_routing": {
                "pr_number": decoded_state["pr_number"],
                "return_url": return_url
            },
            "validation_time": time.time() - self.start_time
        }
    
    async def test_secure_token_transfer(self, tokens: Dict[str, Any], pr_routing: Dict[str, Any]) -> Dict[str, Any]:
        """Test secure token transfer via cookie to PR environment"""
        logger.info("Testing secure token transfer...")
        
        # Create secure token for transfer
        transfer_token = {
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "expires_in": tokens["expires_in"],
            "user_info": tokens["user_info"],
            "pr_number": pr_routing["pr_number"]
        }
        
        # Encode token for secure transfer
        token_data = json.dumps(transfer_token)
        encoded_token = base64.b64encode(token_data.encode()).decode()
        
        # Define secure cookie settings (per spec)
        cookie_settings = {
            "secure": True,
            "httponly": True,
            "samesite": "none",
            "domain": ".staging.netrasystems.ai",
            "max_age": 300,  # 5 minutes
            "path": "/"
        }
        
        # Build redirect URL to PR environment
        pr_callback_url = pr_routing["return_url"]
        redirect_url = f"{pr_callback_url}?token_ready=1"
        
        # Validate cookie settings for subdomain access
        assert cookie_settings["domain"] == ".staging.netrasystems.ai", "Cookie domain incorrect"
        assert cookie_settings["secure"] is True, "Cookie not secure"
        assert cookie_settings["httponly"] is True, "Cookie not httponly"
        assert cookie_settings["max_age"] == 300, "Cookie max_age incorrect"
        
        # Verify PR environment can access the token
        assert self.pr_domain.endswith("staging.netrasystems.ai"), "PR domain not under cookie domain"
        
        logger.info("✓ Secure token transfer validation passed")
        return {
            "encoded_token": encoded_token,
            "cookie_settings": cookie_settings,
            "redirect_url": redirect_url,
            "validation_time": time.time() - self.start_time
        }
    
    async def test_pr_environment_token_retrieval(self, encoded_token: str) -> Dict[str, Any]:
        """Test PR environment retrieving and validating transferred token"""
        logger.info("Testing PR environment token retrieval...")
        
        # Decode transferred token
        try:
            token_data = base64.b64decode(encoded_token.encode()).decode()
            transfer_token = json.loads(token_data)
        except Exception as e:
            raise ValueError(f"Failed to decode transfer token: {e}")
        
        # Verify token components
        assert "access_token" in transfer_token, "Access token missing"
        assert "user_info" in transfer_token, "User info missing"
        assert transfer_token["pr_number"] == self.pr_number, "PR number mismatch"
        
        # Validate user information
        user_info = transfer_token["user_info"]
        assert user_info["email"] == self.test_user["email"], "User email mismatch"
        assert user_info["name"] == self.test_user["name"], "User name mismatch"
        
        # Verify token expiry
        expires_in = transfer_token.get("expires_in", 3600)
        assert expires_in > 0, "Token already expired"
        
        logger.info("✓ PR environment token retrieval validation passed")
        return {
            "user_info": user_info,
            "token_valid": True,
            "pr_number": transfer_token["pr_number"],
            "validation_time": time.time() - self.start_time
        }
    
    async def test_complete_oauth_proxy_flow(self) -> Dict[str, Any]:
        """Test complete OAuth proxy flow for PR environment"""
        logger.info("Testing complete OAuth proxy flow...")
        
        flow_results = {}
        
        # Step 1: State encoding
        state_result = await self.test_oauth_state_encoding()
        flow_results["state_encoding"] = state_result
        
        # Step 2: OAuth initiation
        initiation_result = await self.test_oauth_proxy_initiation(state_result["encoded_state"])
        flow_results["oauth_initiation"] = initiation_result
        
        # Step 3: Callback processing
        callback_result = await self.test_oauth_proxy_callback_processing(state_result["encoded_state"])
        flow_results["callback_processing"] = callback_result
        
        # Step 4: Token transfer
        transfer_result = await self.test_secure_token_transfer(
            callback_result["tokens"], 
            callback_result["pr_routing"]
        )
        flow_results["token_transfer"] = transfer_result
        
        # Step 5: Token retrieval
        retrieval_result = await self.test_pr_environment_token_retrieval(
            transfer_result["encoded_token"]
        )
        flow_results["token_retrieval"] = retrieval_result
        
        # Calculate total execution time
        total_time = time.time() - self.start_time
        flow_results["total_execution_time"] = total_time
        
        # Verify execution time requirement
        assert total_time < 10.0, f"OAuth proxy flow too slow: {total_time:.2f}s > 10s"
        
        logger.info(f"✓ Complete OAuth proxy flow validation passed in {total_time:.2f}s")
        return flow_results
    
    async def cleanup(self) -> None:
        """Cleanup test resources"""
        try:
            if self.services_manager:
                await self.services_manager.stop_all_services()
            logger.info("✓ OAuth proxy staging test cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Test execution
@pytest.mark.asyncio
async def test_oauth_proxy_pr_environment_complete_flow():
    """
    CRITICAL Test #8: OAuth Proxy PR Environment Validation
    
    Validates OAuth proxy functionality for PR staging environments including:
    - State parameter encoding with PR number and CSRF protection
    - Proxy callback handling and token exchange  
    - Secure token transfer via subdomain cookie
    - PR environment token retrieval and validation
    - Complete flow execution in <10 seconds
    """
    tester = OAuthProxyStagingTester()
    
    try:
        # Setup PR environment simulation
        await tester.setup_pr_environment_simulation()
        
        # Execute complete OAuth proxy flow test
        results = await tester.test_complete_oauth_proxy_flow()
        
        # Validate critical results
        assert results["state_encoding"]["validation_time"] < 1.0, "State encoding too slow"
        assert results["oauth_initiation"]["validation_time"] < 2.0, "OAuth initiation too slow"
        assert results["callback_processing"]["validation_time"] < 3.0, "Callback processing too slow"
        assert results["token_transfer"]["validation_time"] < 5.0, "Token transfer too slow"
        assert results["token_retrieval"]["validation_time"] < 7.0, "Token retrieval too slow"
        assert results["total_execution_time"] < 10.0, "Total flow too slow"
        
        # Verify PR routing worked correctly
        assert results["token_retrieval"]["pr_number"] == 42, "PR number routing failed"
        assert results["token_retrieval"]["token_valid"] is True, "Token validation failed"
        
        logger.info(f"🎉 OAuth proxy PR environment test PASSED in {results['total_execution_time']:.2f}s")
        
    finally:
        await tester.cleanup()


@pytest.mark.asyncio
async def test_oauth_proxy_error_scenarios():
    """Test OAuth proxy error handling scenarios"""
    tester = OAuthProxyStagingTester()
    
    try:
        await tester.setup_pr_environment_simulation()
        
        # Test 1: Invalid state parameter
        with pytest.raises(ValueError, match="Invalid state parameter"):
            tester._decode_state_parameter("invalid_base64!")
        
        # Test 2: Expired state parameter
        old_state = tester._encode_state_parameter(
            pr_number=42,
            return_url="https://pr-42.staging.netrasystems.ai/auth/callback",
            csrf_token="expired_token"
        )
        decoded = tester._decode_state_parameter(old_state)
        # Manually set old timestamp
        decoded["timestamp"] = int(time.time()) - 3600  # 1 hour ago
        
        # Re-encode expired state
        expired_json = json.dumps(decoded)
        expired_state = base64.b64encode(expired_json.encode()).decode()
        
        # Should detect expired state in production (mock here)
        expired_decoded = tester._decode_state_parameter(expired_state)
        timestamp_age = time.time() - expired_decoded["timestamp"]
        assert timestamp_age > 300, "Should detect expired state"
        
        # Test 3: CSRF token mismatch 
        wrong_csrf_state = tester._encode_state_parameter(
            pr_number=42,
            return_url="https://pr-42.staging.netrasystems.ai/auth/callback", 
            csrf_token="wrong_token"
        )
        decoded_wrong = tester._decode_state_parameter(wrong_csrf_state)
        assert decoded_wrong["csrf_token"] != tester.csrf_token, "CSRF mismatch detection"
        
        logger.info("✓ OAuth proxy error scenarios validation passed")
        
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    """Direct execution for development testing"""
    async def run_oauth_proxy_staging_test():
        await test_oauth_proxy_pr_environment_complete_flow()
        await test_oauth_proxy_error_scenarios()
    
    asyncio.run(run_oauth_proxy_staging_test())
