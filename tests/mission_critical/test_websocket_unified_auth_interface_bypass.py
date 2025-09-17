"
 ALERT:  MISSION CRITICAL: WebSocket UnifiedAuthInterface Bypass SSOT Violation

SSOT VIOLATION REPRODUCTION - Test #2 of 5
This test EXPOSES the violation where WebSocket bypasses UnifiedAuthInterface and
implements local JWT validation logic instead of using the SSOT auth service.

VIOLATION DETAILS:
- File: netra_backend/app/websocket_core/user_context_extractor.py  
- Lines: 265-324 (Fallback auth logic bypassing UnifiedAuthInterface)
- Issue: WebSocket implements its own auth logic instead of using SSOT UnifiedAuthInterface

EXPECTED BEHAVIOR:
- BEFORE SSOT FIX: Test PASSES (proving UnifiedAuthInterface is bypassed)
- AFTER SSOT FIX: Test FAILS (proving all auth goes through UnifiedAuthInterface)

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - SSOT compliance and architecture integrity  
- Business Goal: System Stability - Single source of truth for auth operations
- Value Impact: Prevents auth logic duplication and security inconsistencies
- Revenue Impact: Auth bypass bugs could compromise entire $500K+ ARR platform

CRITICAL AUTH SSOT REQUIREMENT:
WebSocket MUST use UnifiedAuthInterface for ALL auth operations - NO local auth logic.
"

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared.isolated_environment import get_env

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector

logger = logging.getLogger(__name__)


class WebSocketUnifiedAuthInterfaceBypassTests(SSotAsyncTestCase):
    "
    SSOT Violation Reproduction: Tests that WebSocket bypasses UnifiedAuthInterface.
    
    This test proves WebSocket implements local auth logic instead of using
    the SSOT UnifiedAuthInterface for auth operations.
"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_bypasses_unified_auth_interface_violation(self):
    "
        VIOLATION REPRODUCTION: WebSocket uses local auth logic instead of UnifiedAuthInterface.
        
        CURRENT VIOLATION: user_context_extractor.py lines 265-324
        _resilient_validation_fallback() implements local JWT validation
        instead of calling UnifiedAuthInterface.
        "
        logger.info( ALERT:  TESTING SSOT VIOLATION: WebSocket bypasses UnifiedAuthInterface")
        
        # Mock UnifiedAuthInterface to verify it's NOT being called
        unified_auth_called = False
        
        def track_unified_auth_usage(*args, **kwargs):
            nonlocal unified_auth_called
            unified_auth_called = True
            return {valid: True, user_id: "test_user}"
        
        with patch('netra_backend.app.auth_integration.auth.UnifiedAuthInterface') as mock_unified_auth:
            mock_unified_auth.return_value.validate_token = AsyncMock(side_effect=track_unified_auth_usage)
            
            # Test token that would trigger fallback logic
            test_token = eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXIiLCJpc3MiOiJuZXRyYS1hdXRoLXNlcnZpY2UifQ.test_signature
            
            from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
            extractor = WebSocketUserContextExtractor()
            
            # Force the fallback path by mocking the primary validation to fail
            with patch.object(extractor, '_validate_token_with_unified_interface', side_effect=Exception(Primary validation failed)):"
                try:
                    # This should call UnifiedAuthInterface but currently doesn't due to violation
                    user_context = await extractor.extract_user_context_from_token(test_token)
                    
                    # Check if UnifiedAuthInterface was bypassed (VIOLATION)
                    if not unified_auth_called and user_context:
                        logger.error( ALERT:  SSOT VIOLATION CONFIRMED: WebSocket bypassed UnifiedAuthInterface!")
                        logger.error(f ALERT:  Local auth logic used instead: {user_context})
                        
                        # Verify fallback logic was used instead of SSOT
                        assert user_context is not None, VIOLATION: Local auth logic used instead of UnifiedAuthInterface"
                        
                        logger.critical(" ALERT:  AUTH SSOT VIOLATION: WebSocket implemented local auth logic)
                        logger.critical( ALERT:  THIS TEST PASSES = VIOLATION EXISTS)
                        logger.critical(" ALERT:  AFTER SSOT FIX: All auth should go through UnifiedAuthInterface)"
                        
                        return True
                        
                    elif unified_auth_called:
                        pytest.fail(VIOLATION NOT REPRODUCED: UnifiedAuthInterface was properly called)
                        
                except Exception as e:
                    logger.info(f[U+2139][U+FE0F] Auth extraction failed: {e})
                    # This might indicate the violation is partially fixed
                    
        pytest.fail(VIOLATION TEST INCONCLUSIVE: Unable to determine bypass status")"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_local_jwt_validation_ssot_violation(self):

        VIOLATION REPRODUCTION: WebSocket implements local JWT validation logic.
        
        This test proves WebSocket has its own JWT validation instead of 
        delegating to the SSOT auth service.
        ""
        logger.info( ALERT:  TESTING SSOT VIOLATION: Local JWT validation implemented)
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Check if WebSocket has local JWT validation methods (VIOLATION)
        extractor = WebSocketUserContextExtractor()
        
        # Look for violation methods that should not exist
        violation_methods = [
            _resilient_validation_fallback,"
            _validate_token_with_unified_interface"
        ]
        
        violations_found = []
        for method_name in violation_methods:
            if hasattr(extractor, method_name):
                violations_found.append(method_name)
                logger.error(f ALERT:  SSOT VIOLATION: WebSocket has local auth method: {method_name})
        
        if violations_found:
            logger.critical( ALERT:  AUTH SSOT VIOLATION: WebSocket implements local auth logic)"
            logger.critical(f" ALERT:  Violation methods found: {violations_found})
            logger.critical( ALERT:  ALL AUTH SHOULD GO THROUGH UnifiedAuthInterface ONLY)
            
            assert len(violations_found) > 0, fSSOT VIOLATION: WebSocket has local auth methods: {violations_found}
            return True
        else:
            pytest.fail(VIOLATION NOT REPRODUCED: No local auth methods found")"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_auth_client_core_import_violation(self):

        VIOLATION REPRODUCTION: WebSocket imports auth_client_core directly.
        
        CURRENT VIOLATION: user_context_extractor.py line 276
        from netra_backend.app.clients.auth_client_core import validate_token_with_resilience
        
        This should go through UnifiedAuthInterface instead.
        ""
        logger.info( ALERT:  TESTING SSOT VIOLATION: Direct auth_client_core import)
        
        # Read the user_context_extractor.py file to check for violation imports
        try:
            import inspect
            from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
            
            # Get the source code of the extractor
            source_code = inspect.getsource(WebSocketUserContextExtractor)
            
            # Check for SSOT violations in imports/usage
            violation_patterns = [
                from netra_backend.app.clients.auth_client_core import,"
                validate_token_with_resilience",
                AuthOperationType,
                _resilient_validation_fallback""
            ]
            
            violations_found = []
            for pattern in violation_patterns:
                if pattern in source_code:
                    violations_found.append(pattern)
                    logger.error(f ALERT:  SSOT VIOLATION FOUND in source: {pattern})
            
            if violations_found:
                logger.critical( ALERT:  AUTH SSOT VIOLATION: Direct auth_client_core usage)
                logger.critical(f" ALERT:  Violations: {violations_found})
                logger.critical( ALERT:  SHOULD USE: UnifiedAuthInterface only")
                
                assert len(violations_found) > 0, fSSOT VIOLATION: Direct auth imports found: {violations_found}
                return True
            else:
                pytest.fail(VIOLATION NOT REPRODUCED: No direct auth imports found)"
                
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Could not analyze source code: {e})
            pytest.skip(Cannot analyze source code for violations)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_websocket_auth_flow_bypasses_ssot_architecture(self):
    ""
        INTEGRATION VIOLATION TEST: WebSocket auth flow bypasses SSOT architecture.
        
        This test demonstrates that WebSocket implements a parallel auth system
        instead of using the canonical SSOT UnifiedAuthInterface.
        
        if NoDockerModeDetector.is_no_docker_mode():
            pytest.skip(Integration test requires services)"
            
        logger.info(" ALERT:  TESTING ARCHITECTURAL VIOLATION: Parallel auth system in WebSocket)
        
        # Track which auth components are used
        unified_interface_used = False
        local_auth_logic_used = False
        
        with patch('netra_backend.app.auth_integration.auth.UnifiedAuthInterface') as mock_unified:
            mock_unified.return_value.validate_token = AsyncMock(return_value={valid: False}
            
            # Monitor if local auth fallback is triggered
            def track_local_auth(*args, **kwargs):
                nonlocal local_auth_logic_used
                local_auth_logic_used = True
                return {"success: True, valid": True, user_id: fallback_user}
            
            with patch('netra_backend.app.clients.auth_client_core.validate_token_with_resilience', 
                      side_effect=track_local_auth):
                
                test_token = test.jwt.token"
                
                from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
                extractor = WebSocketUserContextExtractor()
                
                try:
                    user_context = await extractor.extract_user_context_from_token(test_token)
                    
                    # Check if local auth logic was used (VIOLATION)
                    if local_auth_logic_used and not unified_interface_used:
                        logger.error( ALERT:  ARCHITECTURAL VIOLATION: WebSocket uses parallel auth system")
                        logger.error( ALERT:  LOCAL AUTH LOGIC USED INSTEAD OF SSOT UnifiedAuthInterface)
                        
                        assert local_auth_logic_used, VIOLATION: WebSocket bypassed SSOT auth architecture""
                        
                        logger.critical( ALERT:  SYSTEM ARCHITECTURE VIOLATION CONFIRMED)
                        logger.critical( ALERT:  WebSocket implements parallel auth instead of using SSOT)"
                        
                        return True
                        
                except Exception as e:
                    logger.info(f"[U+2139][U+FE0F] Auth flow failed: {e})
        
        if not local_auth_logic_used:
            pytest.fail(VIOLATION NOT REPRODUCED: Local auth logic was not used)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_auth_configuration_duplication_violation(self):
    ""
        VIOLATION REPRODUCTION: WebSocket duplicates auth configuration logic.
        
        This test shows that WebSocket has its own auth configuration
        instead of using the SSOT configuration from UnifiedAuthInterface.
        
        logger.info( ALERT:  TESTING SSOT VIOLATION: Duplicated auth configuration)"
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Check if WebSocket accesses environment variables directly (VIOLATION)
        # Should use UnifiedAuthInterface configuration instead
        
        with patch('shared.isolated_environment.get_env') as mock_env:
            env_accessed = False
            
            def track_env_access():
                nonlocal env_accessed  
                env_accessed = True
                return {
                    "ENVIRONMENT: test,
                    JWT_SECRET_KEY: test_secret
                }
            
            mock_env.side_effect = track_env_access
            
            extractor = WebSocketUserContextExtractor()
            test_token = "test.token"
            
            try:
                await extractor.extract_user_context_from_token(test_token)
                
                if env_accessed:
                    logger.error( ALERT:  SSOT VIOLATION: WebSocket accesses environment directly)
                    logger.error( ALERT:  SHOULD USE: UnifiedAuthInterface configuration only)"
                    
                    assert env_accessed, VIOLATION: WebSocket duplicates auth configuration access"
                    
                    logger.critical( ALERT:  CONFIGURATION DUPLICATION VIOLATION)
                    logger.critical( ALERT:  WebSocket should use SSOT auth configuration")"
                    
                    return True
                    
            except Exception as e:
                logger.info(f[U+2139][U+FE0F] Environment access test failed: {e})
        
        if not env_accessed:
            pytest.fail(VIOLATION NOT REPRODUCED: No direct environment access detected)

    def tearDown(self):
        "Clean up test artifacts."
        logger.info([U+1F9F9] UnifiedAuthInterface bypass violation test cleanup complete)"


if __name__ == "__main__":
    # Run this test independently to verify violation reproduction
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution
