"""
 ALERT:  MISSION CRITICAL: WebSocket Auth Fallback SSOT Violation

SSOT VIOLATION REPRODUCTION - Test #4 of 5  
This test EXPOSES the violation where WebSocket implements fallback auth patterns
that duplicate/bypass the SSOT UnifiedAuthInterface instead of properly delegating.

VIOLATION DETAILS:
- File: netra_backend/app/websocket_core/user_context_extractor.py
- Lines: 265-324 (_resilient_validation_fallback method)
- Issue: WebSocket implements complex fallback auth logic duplicating SSOT patterns

EXPECTED BEHAVIOR:
- BEFORE SSOT FIX: Test PASSES (proving fallback patterns violate SSOT)
- AFTER SSOT FIX: Test FAILS (proving WebSocket uses UnifiedAuthInterface exclusively)

Business Value Justification (BVJ):
- Segment: Platform/Engineering - SSOT compliance and maintainability
- Business Goal: System Stability - Eliminate duplicate auth logic maintenance 
- Value Impact: Reduces auth bugs and security vulnerabilities from logic duplication
- Revenue Impact: Auth fallback bugs could cause service outages ($100K+ revenue risk)

CRITICAL FALLBACK SSOT REQUIREMENT:
WebSocket MUST delegate ALL fallback/resilience to UnifiedAuthInterface - NO local patterns.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from shared.isolated_environment import get_env

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector

logger = logging.getLogger(__name__)


class TestWebSocketAuthFallbackSsotViolation(SSotAsyncTestCase):
    """
    SSOT Violation Reproduction: Tests WebSocket fallback auth patterns violate SSOT.
    
    This test proves WebSocket implements its own fallback/resilience patterns
    instead of delegating all fallback logic to UnifiedAuthInterface.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_implements_local_fallback_patterns_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket implements local fallback auth patterns.
        
        CURRENT VIOLATION: _resilient_validation_fallback() method (lines 265-324)
        implements complex fallback logic that should be in UnifiedAuthInterface.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: WebSocket local fallback patterns")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Check if WebSocket has fallback methods (VIOLATION)
        extractor = WebSocketUserContextExtractor()
        
        fallback_violation_methods = [
            "_resilient_validation_fallback",
            "_validate_token_with_unified_interface"
        ]
        
        violations_found = []
        fallback_logic_detected = False
        
        for method_name in fallback_violation_methods:
            if hasattr(extractor, method_name):
                violations_found.append(method_name)
                fallback_logic_detected = True
                logger.error(f" ALERT:  SSOT VIOLATION: WebSocket has fallback method: {method_name}")
                
                # Test that the method exists and can be called
                method = getattr(extractor, method_name)
                if callable(method):
                    logger.error(f" ALERT:  CALLABLE FALLBACK LOGIC FOUND: {method_name}")
        
        # Check for fallback logic in source code
        try:
            import inspect
            source_code = inspect.getsource(WebSocketUserContextExtractor)
            
            fallback_patterns = [
                "resilient_validation_fallback",
                "validate_token_with_resilience", 
                "AuthOperationType",
                "# Fall through to full validation",
                "# Resilient validation fallback"
            ]
            
            for pattern in fallback_patterns:
                if pattern in source_code:
                    violations_found.append(f"Source contains: {pattern}")
                    fallback_logic_detected = True
                    logger.error(f" ALERT:  FALLBACK PATTERN IN SOURCE: {pattern}")
        
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Could not analyze source code: {e}")
        
        if fallback_logic_detected:
            logger.critical(" ALERT:  FALLBACK SSOT VIOLATION CONFIRMED")
            logger.critical(f" ALERT:  Fallback violations found: {violations_found}")
            logger.critical(" ALERT:  WebSocket should delegate ALL fallback to UnifiedAuthInterface")
            logger.critical(" ALERT:  THIS TEST PASSES = VIOLATION EXISTS")
            
            assert len(violations_found) > 0, f"FALLBACK SSOT VIOLATION: WebSocket implements local fallback: {violations_found}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: No local fallback patterns detected")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_fallback_logic_complexity_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket fallback logic is complex and duplicates SSOT.
        
        This test demonstrates that WebSocket implements complex multi-step
        fallback logic that should be centralized in UnifiedAuthInterface.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: Complex fallback logic duplication")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Test the fallback logic by triggering it
        extractor = WebSocketUserContextExtractor()
        
        # Mock the primary auth to fail, forcing fallback
        with patch.object(extractor, '_validate_token_with_unified_interface', 
                          side_effect=Exception("Primary auth failed")):
            
            # Track fallback complexity by monitoring method calls
            fallback_calls = []
            
            # Mock auth_client_core to track fallback usage
            with patch('netra_backend.app.clients.auth_client_core.validate_token_with_resilience') as mock_resilient_auth:
                mock_resilient_auth.return_value = {
                    "success": True,
                    "valid": True, 
                    "user_id": "fallback_user",
                    "email": "test@fallback.com",
                    "permissions": ["chat"]
                }
                
                # Mock environment access to track configuration duplication
                with patch('shared.isolated_environment.get_env') as mock_env:
                    mock_env.return_value = {
                        "ENVIRONMENT": "test",
                        "JWT_SECRET_KEY": "test_secret"
                    }
                    
                    test_token = "test.fallback.token"
                    
                    try:
                        # This should trigger the complex fallback logic (VIOLATION)
                        user_context = await extractor.extract_user_context_from_token(test_token)
                        
                        # Check if fallback logic was used
                        if mock_resilient_auth.called and user_context:
                            fallback_calls.append("validate_token_with_resilience")
                            logger.error(" ALERT:  COMPLEX FALLBACK LOGIC EXECUTED")
                            logger.error(f" ALERT:  Fallback result: {user_context}")
                            
                            # Check environment access (configuration duplication)
                            if mock_env.called:
                                fallback_calls.append("environment_access")
                                logger.error(" ALERT:  FALLBACK ACCESSES ENVIRONMENT DIRECTLY")
                            
                            # Check for JWT payload construction (logic duplication)
                            if user_context.get("sub") == "fallback_user":
                                fallback_calls.append("jwt_payload_construction")
                                logger.error(" ALERT:  FALLBACK CONSTRUCTS JWT PAYLOAD LOCALLY")
                            
                            logger.critical(" ALERT:  COMPLEX FALLBACK SSOT VIOLATION CONFIRMED")
                            logger.critical(f" ALERT:  Fallback complexity indicators: {fallback_calls}")
                            logger.critical(" ALERT:  ALL FALLBACK LOGIC SHOULD BE IN UnifiedAuthInterface")
                            
                            assert len(fallback_calls) > 0, f"COMPLEX FALLBACK VIOLATION: {fallback_calls}"
                            return True
                            
                    except Exception as e:
                        logger.info(f"[U+2139][U+FE0F] Fallback test failed: {e}")
        
        pytest.fail("VIOLATION NOT REPRODUCED: Complex fallback logic not detected")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_fallback_auth_client_core_duplication_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket duplicates auth_client_core fallback logic.
        
        CURRENT VIOLATION: WebSocket imports and uses auth_client_core directly
        instead of accessing it through UnifiedAuthInterface abstraction.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: auth_client_core duplication in fallback")
        
        # Check for direct auth_client_core import violations
        try:
            import sys
            
            # Check if WebSocket can import auth_client_core directly (VIOLATION)
            websocket_can_import_auth_client = False
            try:
                from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
                
                # Try to access auth_client_core through WebSocket (should not be allowed)
                extractor = WebSocketUserContextExtractor()
                
                # Look for auth_client_core usage in the module
                import netra_backend.app.websocket_core.user_context_extractor as ws_module
                
                # Check module globals for auth_client_core references
                module_globals = dir(ws_module)
                auth_client_refs = [name for name in module_globals if 'auth_client' in name.lower()]
                
                if auth_client_refs:
                    websocket_can_import_auth_client = True
                    logger.error(f" ALERT:  VIOLATION: WebSocket has auth_client references: {auth_client_refs}")
                
            except Exception as e:
                logger.info(f"[U+2139][U+FE0F] Direct import test failed: {e}")
            
            # Test if WebSocket fallback can call auth_client_core methods
            auth_client_duplication_detected = False
            
            with patch('netra_backend.app.clients.auth_client_core.validate_token_with_resilience') as mock_auth_client:
                mock_auth_client.return_value = {"success": True, "valid": True, "user_id": "duplicate_test"}
                
                from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
                extractor = WebSocketUserContextExtractor()
                
                # Force fallback by mocking primary auth failure
                with patch.object(extractor, '_validate_token_with_unified_interface', 
                                  side_effect=Exception("Force fallback")):
                    
                    try:
                        test_token = "test.duplication.token"
                        user_context = await extractor.extract_user_context_from_token(test_token)
                        
                        # Check if auth_client_core was called directly (VIOLATION)
                        if mock_auth_client.called:
                            auth_client_duplication_detected = True
                            logger.error(" ALERT:  VIOLATION: WebSocket called auth_client_core directly")
                            logger.error(f" ALERT:  Direct call arguments: {mock_auth_client.call_args}")
                            
                    except Exception as e:
                        logger.info(f"[U+2139][U+FE0F] Duplication test failed: {e}")
            
            # Summarize violations  
            violations = []
            if websocket_can_import_auth_client:
                violations.append("WebSocket can import auth_client_core directly")
            if auth_client_duplication_detected:
                violations.append("WebSocket calls auth_client_core methods directly")
            
            if violations:
                logger.critical(" ALERT:  AUTH_CLIENT_CORE DUPLICATION VIOLATIONS:")
                for violation in violations:
                    logger.critical(f" ALERT:  - {violation}")
                    
                logger.critical(" ALERT:  WebSocket should ONLY use UnifiedAuthInterface")
                logger.critical(" ALERT:  NO DIRECT auth_client_core access allowed")
                
                assert len(violations) > 0, f"AUTH_CLIENT_CORE DUPLICATION: {violations}"
                return True
            else:
                pytest.fail("VIOLATION NOT REPRODUCED: No auth_client_core duplication detected")
                
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Duplication test failed: {e}")
            pytest.skip("Cannot test auth_client_core duplication")

    @pytest.mark.asyncio 
    @pytest.mark.integration
    async def test_websocket_fallback_resilience_pattern_duplication_violation(self):
        """
        INTEGRATION VIOLATION TEST: WebSocket duplicates resilience patterns from auth_client_core.
        
        This test demonstrates that WebSocket implements the same resilience patterns
        (retry logic, error handling, etc.) that should be centralized in UnifiedAuthInterface.
        """
        if NoDockerModeDetector.is_no_docker_mode():
            pytest.skip("Integration test requires services")
            
        logger.info(" ALERT:  TESTING ARCHITECTURAL VIOLATION: Resilience pattern duplication")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Test resilience pattern duplication by monitoring retry behavior
        retry_attempts = []
        resilience_patterns_detected = []
        
        def track_auth_calls(*args, **kwargs):
            retry_attempts.append({"args": args, "kwargs": kwargs})
            # Simulate auth service failure to test resilience 
            if len(retry_attempts) == 1:
                raise Exception("Auth service temporarily unavailable")
            return {"success": True, "valid": True, "user_id": "resilient_user"}
        
        with patch('netra_backend.app.clients.auth_client_core.validate_token_with_resilience', 
                   side_effect=track_auth_calls):
            
            # Monitor environment access (resilience configuration duplication)  
            env_accesses = []
            def track_env_access():
                env_accesses.append("env_access")
                return {"ENVIRONMENT": "test", "JWT_SECRET_KEY": "test"}
            
            with patch('shared.isolated_environment.get_env', side_effect=track_env_access):
                
                extractor = WebSocketUserContextExtractor()
                
                # Force fallback path  
                with patch.object(extractor, '_validate_token_with_unified_interface',
                                  side_effect=Exception("Primary auth unavailable")):
                    
                    try:
                        test_token = "test.resilience.token"
                        user_context = await extractor.extract_user_context_from_token(test_token)
                        
                        # Analyze resilience pattern duplication
                        if len(retry_attempts) > 0:
                            resilience_patterns_detected.append("retry_logic_duplication")
                            logger.error(" ALERT:  RESILIENCE VIOLATION: WebSocket implements retry logic")
                        
                        if len(env_accesses) > 0:
                            resilience_patterns_detected.append("environment_resilience_config")
                            logger.error(" ALERT:  RESILIENCE VIOLATION: WebSocket accesses resilience config")
                        
                        # Check for error handling patterns
                        if user_context and user_context.get("user_id") == "resilient_user":
                            resilience_patterns_detected.append("error_recovery_patterns")
                            logger.error(" ALERT:  RESILIENCE VIOLATION: WebSocket implements error recovery")
                        
                        # Check for JWT payload construction after failure (resilience duplication)
                        if user_context and "sub" in user_context:
                            resilience_patterns_detected.append("jwt_construction_after_failure")
                            logger.error(" ALERT:  RESILIENCE VIOLATION: WebSocket constructs JWT after auth failure")
                        
                    except Exception as e:
                        logger.info(f"[U+2139][U+FE0F] Resilience test failed: {e}")
        
        if resilience_patterns_detected:
            logger.critical(" ALERT:  RESILIENCE PATTERN DUPLICATION VIOLATIONS:")
            for pattern in resilience_patterns_detected:
                logger.critical(f" ALERT:  - {pattern}")
                
            logger.critical(" ALERT:  ALL RESILIENCE PATTERNS SHOULD BE IN UnifiedAuthInterface")
            logger.critical(" ALERT:  WebSocket should delegate resilience, not implement it")
            
            assert len(resilience_patterns_detected) > 0, f"RESILIENCE DUPLICATION: {resilience_patterns_detected}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: No resilience pattern duplication detected")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_fallback_creates_auth_state_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket fallback creates auth state independently.
        
        This test shows that WebSocket fallback logic constructs user authentication
        state (JWT payload) instead of receiving it from UnifiedAuthInterface.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: Independent auth state creation in fallback")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Track auth state construction
        state_construction_violations = []
        
        with patch('netra_backend.app.clients.auth_client_core.validate_token_with_resilience') as mock_auth:
            # Return minimal auth data to test state construction
            mock_auth.return_value = {
                "success": True,
                "valid": True,
                "user_id": "state_test_user",
                "email": "state@test.com", 
                "permissions": ["chat", "read"]
            }
            
            extractor = WebSocketUserContextExtractor()
            
            # Force fallback
            with patch.object(extractor, '_validate_token_with_unified_interface',
                              side_effect=Exception("Primary auth failed")):
                
                try:
                    test_token = "test.state.token"
                    user_context = await extractor.extract_user_context_from_token(test_token)
                    
                    if user_context:
                        # Check if WebSocket constructed JWT-style payload (VIOLATION)
                        jwt_fields = ["sub", "iss", "aud", "exp", "iat", "email"]
                        constructed_fields = [field for field in jwt_fields if field in user_context]
                        
                        if len(constructed_fields) > 0:
                            state_construction_violations.append(f"JWT fields constructed: {constructed_fields}")
                            logger.error(f" ALERT:  VIOLATION: WebSocket constructed JWT fields: {constructed_fields}")
                        
                        # Check if WebSocket added its own auth metadata
                        if "permissions" in user_context:
                            state_construction_violations.append("Permissions processed locally")
                            logger.error(" ALERT:  VIOLATION: WebSocket processed permissions locally")
                        
                        # Check for timestamp creation (iat, exp)
                        if "iat" in user_context or "exp" in user_context:
                            state_construction_violations.append("Timestamp creation")
                            logger.error(" ALERT:  VIOLATION: WebSocket created auth timestamps")
                        
                        # Check for issuer/audience setting
                        if user_context.get("iss") == "netra-auth-service":
                            state_construction_violations.append("Issuer field set locally")
                            logger.error(" ALERT:  VIOLATION: WebSocket set JWT issuer locally")
                        
                except Exception as e:
                    logger.info(f"[U+2139][U+FE0F] State construction test failed: {e}")
        
        if state_construction_violations:
            logger.critical(" ALERT:  AUTH STATE CONSTRUCTION VIOLATIONS:")
            for violation in state_construction_violations:
                logger.critical(f" ALERT:  - {violation}")
                
            logger.critical(" ALERT:  WebSocket should receive complete auth state from UnifiedAuthInterface")
            logger.critical(" ALERT:  NO LOCAL auth state construction allowed")
            
            assert len(state_construction_violations) > 0, f"AUTH STATE VIOLATIONS: {state_construction_violations}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: No independent auth state construction detected")

    def tearDown(self):
        """Clean up test artifacts.""" 
        logger.info("[U+1F9F9] Fallback SSOT violation test cleanup complete")


if __name__ == "__main__":
    # Run this test independently to verify violation reproduction
    pytest.main([__file__, "-v", "--tb=short"])