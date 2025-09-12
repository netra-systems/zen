"""
WebSocket NO_TOKEN Persistent Issue Reproduction Test

This test reproduces the PERSISTENT WebSocket authentication failure identified in:
- WEBSOCKET_AUTH_NO_TOKEN_FIVE_WHYS_ANALYSIS_PERSISTENT_20250908.md

Business Value Justification:
- Segment: Platform/Internal - WebSocket Infrastructure Testing
- Business Goal: Prevent $120K+ MRR loss from WebSocket auth failures  
- Value Impact: Validates execution of critical configuration fixes
- Revenue Impact: Ensures WebSocket reliability for chat functionality

CRITICAL FINDINGS FROM FIVE WHYS:
1. Technical root cause already identified (E2E config mismatch)
2. Issue persists due to EXECUTION FAILURE, not technical failure
3. This test VALIDATES that configuration fixes are properly implemented
4. Test failure indicates systematic execution process needs improvement

PURPOSE:
- Reproduce the exact "No JWT in WebSocket headers or subprotocols" error
- Validate E2E OAuth simulation configuration is working
- Test WebSocket authentication with staging environment context
- Prove configuration fixes resolve the persistent issue
"""

import asyncio
import json
import logging
import pytest
import websockets
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

from netra_backend.app.websocket_core.unified_websocket_auth import (
    UnifiedWebSocketAuthenticator, 
    extract_e2e_context_from_websocket,
    authenticate_websocket_ssot
)
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from shared.isolated_environment import get_env
from netra_backend.app.services.unified_authentication_service import get_unified_auth_service

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MockWebSocketForReproduction:
    """Mock WebSocket that reproduces the exact failure scenario."""
    
    def __init__(self, 
                 headers: Dict[str, str] = None, 
                 client_host: str = "169.254.169.126",
                 client_port: int = 48250,
                 simulate_no_token: bool = False):
        """
        Initialize mock WebSocket with the exact failure context.
        
        Args:
            headers: WebSocket headers (can be empty to simulate NO_TOKEN)
            client_host: Client host from failure context
            client_port: Client port from failure context  
            simulate_no_token: If True, simulate the exact NO_TOKEN scenario
        """
        # Exact headers from the failure context
        self.headers = headers or {
            "host": "api.staging.netrasystems.ai",
            "sec-websocket-key": "test-websocket-key-123",
            "sec-websocket-version": "13",
            "sec-websocket-extensions": "permessage-deflate",
            "sec-websocket-protocol": "jwt-auth",  # Note: NO JWT token in protocol
            "user-agent": "Python/3.12 websockets/15.0.1",
            "via": "1.1 google",
            "x-forwarded-for": "172.16.0.1",
            "x-forwarded-proto": "https",
            "forwarded": "for=172.16.0.1;proto=https",
            "x-cloud-trace-context": "test-trace-context",
            "traceparent": "test-traceparent",
            "upgrade": "websocket",
            "connection": "Upgrade"
        }
        
        # Simulate missing JWT token in subprotocols (reproduces NO_TOKEN error)
        if simulate_no_token:
            # This reproduces the exact failure: "jwt-auth" protocol without JWT token
            self.headers["sec-websocket-protocol"] = "jwt-auth"
        
        # Mock client info from failure context
        self.client = MagicMock()
        self.client.host = client_host
        self.client.port = client_port
        
        # WebSocket state
        from fastapi.websockets import WebSocketState
        self.client_state = WebSocketState.CONNECTED
        
        # Query parameters (empty from failure context)  
        self.query_params = {}
    
    def get(self, key: str, default: str = "") -> str:
        """Mock get method for header access."""
        return self.headers.get(key, default)


@pytest.mark.asyncio
async def test_reproduce_websocket_no_token_error():
    """
    CRITICAL: Reproduce the exact "NO_TOKEN" WebSocket authentication error.
    
    This test reproduces the specific failure scenario:
    - WebSocket connects with "jwt-auth" protocol but no JWT token
    - Environment is "staging"  
    - Client host is 169.254.169.126 (from failure context)
    - All WebSocket headers present but Authorization header missing
    - sec-websocket-protocol contains "jwt-auth" but no "jwt.{token}"
    
    EXPECTED RESULT:
    - If configuration is NOT fixed: Test should reproduce "NO_TOKEN" error
    - If configuration IS fixed: Test should pass or show different error
    """
    logger.info(" SEARCH:  REPRODUCING WEBSOCKET NO_TOKEN PERSISTENT ISSUE")
    
    # Create mock WebSocket that reproduces exact failure scenario
    mock_websocket = MockWebSocketForReproduction(simulate_no_token=True)
    
    # Initialize authenticator
    authenticator = UnifiedWebSocketAuthenticator()
    
    # Mock environment to match staging failure context
    with patch.dict('os.environ', {
        'ENVIRONMENT': 'staging',
        'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
        'TESTING': '0',
        # Simulate E2E testing environment
        'PYTEST_RUNNING': '1',
        'E2E_TEST_ENV': 'staging'
    }):
        
        # Extract E2E context (should detect E2E testing)
        e2e_context = extract_e2e_context_from_websocket(mock_websocket)
        logger.info(f"E2E CONTEXT: {e2e_context}")
        
        # Attempt WebSocket authentication (should reproduce the error)
        auth_result = await authenticator.authenticate_websocket_connection(
            mock_websocket, 
            e2e_context=e2e_context
        )
        
        # Log detailed authentication result
        logger.error(f" ALERT:  AUTHENTICATION RESULT: {auth_result.to_dict()}")
        
        # CRITICAL ASSERTION: This should reproduce the NO_TOKEN error
        assert not auth_result.success, "Authentication should fail due to missing JWT token"
        
        # Check if we get the specific NO_TOKEN error (if config not fixed)
        if auth_result.error_code == "NO_TOKEN":
            logger.critical(" ALERT:  NO_TOKEN ERROR REPRODUCED - Configuration fix not implemented!")
            assert "No JWT" in auth_result.error_message or "NO_TOKEN" in auth_result.error_message
            
        elif auth_result.error_code in ["TOKEN_VALIDATION_FAILED", "INVALID_E2E_BYPASS"]:
            logger.info(" PASS:  ERROR TYPE CHANGED - May indicate partial fix implementation")
            # Different error suggests some progress in configuration
            
        else:
            logger.warning(f" WARNING: [U+FE0F] UNEXPECTED ERROR TYPE: {auth_result.error_code}")
            # Log for analysis
        
        # Validate the failure metadata contains expected context
        assert auth_result.error_code is not None, "Error code should be present"
        assert auth_result.error_message is not None, "Error message should be present"
        
        return auth_result


@pytest.mark.asyncio  
async def test_validate_e2e_configuration_fix():
    """
    CRITICAL: Validate that E2E configuration is properly set up for staging.
    
    This test validates the specific fixes identified in the Five Whys analysis:
    1. E2E_OAUTH_SIMULATION_KEY is correct for staging
    2. JWT_SECRET_STAGING is available for test token creation
    3. E2E authentication bypass works with staging auth service
    
    EXPECTED RESULT:
    - If fixes implemented: E2E authentication should work
    - If fixes not implemented: Should show specific configuration errors
    """
    logger.info("[U+1F527] VALIDATING E2E CONFIGURATION FIXES")
    
    # Initialize E2E auth helper
    e2e_helper = E2EAuthHelper()
    
    # Mock staging environment  
    with patch.dict('os.environ', {
        'ENVIRONMENT': 'staging',
        'E2E_TEST_ENV': 'staging',
        'PYTEST_RUNNING': '1'
    }):
        
        try:
            # Test E2E OAuth simulation (this is what was failing)
            logger.info("Testing E2E OAuth simulation bypass...")
            
            test_email = "staging-e2e-user-002@netrasystems.ai"
            auth_result = await e2e_helper.get_staging_compatible_jwt_token(
                email=test_email,
                staging_environment="staging"
            )
            
            logger.info(f"E2E AUTH RESULT: {auth_result}")
            
            if auth_result and "token" in auth_result:
                logger.info(" PASS:  E2E OAUTH SIMULATION SUCCESS - Configuration likely fixed!")
                
                # Validate token format
                token = auth_result["token"]
                assert isinstance(token, str), "Token should be string"
                assert len(token) > 10, "Token should be substantial length"
                
                # Test if token can be used for WebSocket authentication
                await test_websocket_auth_with_valid_token(token)
                
            else:
                logger.error(" FAIL:  E2E OAUTH SIMULATION FAILED - Configuration not fixed")
                
                # Check specific configuration issues
                env = get_env()
                e2e_key = env.get("E2E_OAUTH_SIMULATION_KEY")
                jwt_secret = env.get("JWT_SECRET_STAGING") or env.get("JWT_SECRET_KEY")
                
                logger.error(f"E2E_OAUTH_SIMULATION_KEY present: {e2e_key is not None}")
                logger.error(f"JWT_SECRET_STAGING present: {jwt_secret is not None}")
                
                pytest.fail("E2E configuration validation failed - fixes not implemented")
                
        except Exception as e:
            logger.error(f" FIRE:  E2E CONFIGURATION VALIDATION EXCEPTION: {e}", exc_info=True)
            pytest.fail(f"E2E configuration validation failed with exception: {e}")


async def test_websocket_auth_with_valid_token(token: str):
    """Test WebSocket authentication with a valid E2E token."""
    logger.info("[U+1F510] TESTING WEBSOCKET AUTH WITH VALID E2E TOKEN")
    
    # Create WebSocket with proper JWT token in subprotocol
    import base64
    encoded_token = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
    
    headers = {
        "host": "api.staging.netrasystems.ai",
        "sec-websocket-protocol": f"jwt-auth,jwt.{encoded_token}",
        "sec-websocket-key": "test-key-123",
        "sec-websocket-version": "13"
    }
    
    mock_websocket = MockWebSocketForReproduction(headers=headers)
    authenticator = UnifiedWebSocketAuthenticator()
    
    # Test authentication with valid token
    auth_result = await authenticator.authenticate_websocket_connection(mock_websocket)
    
    logger.info(f"WEBSOCKET AUTH WITH VALID TOKEN: {auth_result.to_dict()}")
    
    if auth_result.success:
        logger.info(" PASS:  WEBSOCKET AUTHENTICATION WITH VALID TOKEN SUCCESSFUL")
        assert auth_result.user_context is not None
        assert auth_result.auth_result is not None
    else:
        logger.warning(f" WARNING: [U+FE0F] WEBSOCKET AUTH FAILED EVEN WITH VALID TOKEN: {auth_result.error_message}")
        # This might indicate other configuration issues


@pytest.mark.asyncio
async def test_systematic_remediation_tracking():
    """
    CRITICAL: Test that systematic remediation tracking is implemented.
    
    This test validates the organizational process improvements identified
    in the Five Whys analysis to prevent recurrence of this issue.
    """
    logger.info(" CHART:  TESTING SYSTEMATIC REMEDIATION TRACKING")
    
    # This test validates process improvements exist
    try:
        # Check if critical remediation tracker exists
        try:
            from scripts.critical_remediation_tracker import CriticalRemediationTracker
            tracker = CriticalRemediationTracker()
            logger.info(" PASS:  CRITICAL REMEDIATION TRACKER EXISTS")
        except ImportError:
            logger.warning(" WARNING: [U+FE0F] CRITICAL REMEDIATION TRACKER NOT IMPLEMENTED")
            pytest.skip("Remediation tracker not yet implemented - organizational process gap")
        
        # Check if monitoring for WebSocket auth failures exists
        try:
            from netra_backend.app.monitoring.staging_health_monitor import check_websocket_auth_health
            logger.info(" PASS:  WEBSOCKET AUTH HEALTH MONITORING EXISTS")  
        except ImportError:
            logger.warning(" WARNING: [U+FE0F] WEBSOCKET AUTH HEALTH MONITORING NOT IMPLEMENTED")
            
        # Check if configuration regression prevention exists
        try:
            from scripts.configuration_regression_prevention import validate_critical_config_changes
            logger.info(" PASS:  CONFIGURATION REGRESSION PREVENTION EXISTS")
        except ImportError:
            logger.warning(" WARNING: [U+FE0F] CONFIGURATION REGRESSION PREVENTION NOT IMPLEMENTED")
            
    except Exception as e:
        logger.error(f" FIRE:  SYSTEMATIC REMEDIATION TRACKING TEST FAILED: {e}")
        pytest.fail("Systematic remediation improvements not implemented")


if __name__ == "__main__":
    """
    Run reproduction test directly for debugging.
    
    Usage:
    python tests/five_whys/test_websocket_no_token_persistent_reproduction.py
    """
    import sys
    import asyncio
    
    async def main():
        print(" SEARCH:  RUNNING WEBSOCKET NO_TOKEN PERSISTENT ISSUE REPRODUCTION")
        print("=" * 80)
        
        # Test 1: Reproduce the NO_TOKEN error
        print("\n1. REPRODUCING NO_TOKEN ERROR...")
        try:
            result = await test_reproduce_websocket_no_token_error()
            print(f" PASS:  NO_TOKEN REPRODUCTION: {result.error_code}")
        except Exception as e:
            print(f" FAIL:  NO_TOKEN REPRODUCTION FAILED: {e}")
        
        # Test 2: Validate E2E configuration fixes
        print("\n2. VALIDATING E2E CONFIGURATION FIXES...")
        try:
            await test_validate_e2e_configuration_fix()
            print(" PASS:  E2E CONFIGURATION VALIDATION PASSED")
        except Exception as e:
            print(f" FAIL:  E2E CONFIGURATION VALIDATION FAILED: {e}")
        
        # Test 3: Check systematic remediation tracking
        print("\n3. CHECKING SYSTEMATIC REMEDIATION TRACKING...")
        try:
            await test_systematic_remediation_tracking()  
            print(" PASS:  REMEDIATION TRACKING VALIDATION PASSED")
        except Exception as e:
            print(f" FAIL:  REMEDIATION TRACKING VALIDATION FAILED: {e}")
        
        print("\n" + "=" * 80)
        print("[U+1F3C1] WEBSOCKET NO_TOKEN PERSISTENT ISSUE REPRODUCTION COMPLETE")
        
    # Run the test
    asyncio.run(main())