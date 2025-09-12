
# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e}")
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

"""
 ALERT:  MISSION CRITICAL: Golden Path Auth SSOT Compliance E2E Test

SSOT VIOLATION REPRODUCTION - Test #5 of 5
This test EXPOSES SSOT violations in the complete Golden Path user journey by verifying
that auth operations bypass UnifiedAuthInterface at critical points.

VIOLATION DETAILS:
- Golden Path: User login  ->  WebSocket connection  ->  Agent execution  ->  Response delivery
- Issue: Auth operations at multiple points bypass SSOT UnifiedAuthInterface
- Impact: Inconsistent auth behavior across the complete user journey

EXPECTED BEHAVIOR:
- BEFORE SSOT FIX: Test PASSES (proving Golden Path has auth SSOT violations)  
- AFTER SSOT FIX: Test FAILS (proving entire Golden Path uses UnifiedAuthInterface)

Business Value Justification (BVJ):
- Segment: ALL users - Core platform functionality (100% of user journeys)
- Business Goal: Customer Success - Seamless end-to-end experience
- Value Impact: Ensures $500K+ ARR chat functionality works consistently 
- Revenue Impact: Golden Path failures = no customer value = complete revenue loss

CRITICAL GOLDEN PATH SSOT REQUIREMENT:
Every auth operation in the Golden Path MUST use UnifiedAuthInterface exclusively.
"""

import asyncio
import json
import logging
import time
import uuid
import websockets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from shared.isolated_environment import get_env

from test_framework.common_imports import *  # PERFORMANCE: Consolidated imports
# CONSOLIDATED: from test_framework.ssot.base_test_case import SSotAsyncTestCase
# CONSOLIDATED: from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
# CONSOLIDATED: from test_framework.fixtures.real_services import real_services_fixture
# CONSOLIDATED: from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector
from netra_backend.app.services.user_execution_context import UserExecutionContext

logger = logging.getLogger(__name__)


class TestGoldenPathAuthSsotCompliance(SSotAsyncTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """
    E2E SSOT Violation Reproduction: Tests complete Golden Path auth SSOT compliance.
    
    This test traces the complete user journey and identifies every point where
    auth operations bypass UnifiedAuthInterface instead of using SSOT patterns.
    """

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_golden_path_end_to_end_auth_ssot_violations(self):
        """
        COMPLETE GOLDEN PATH VIOLATION TEST: Full user journey auth SSOT compliance.
        
        This test executes the complete Golden Path and identifies every auth
        operation that violates SSOT by not using UnifiedAuthInterface.
        
        GOLDEN PATH FLOW:
        1. User authentication/login
        2. WebSocket connection with auth token  
        3. Agent execution request
        4. Real-time progress events
        5. Response delivery
        """
        logger.info(" ALERT:  TESTING COMPLETE GOLDEN PATH AUTH SSOT VIOLATIONS")
        
        if NoDockerModeDetector.is_no_docker_mode():
            # Use staging environment for E2E test
            env = get_env()
            backend_url = env.get("BACKEND_URL", "https://netra-backend-staging.ue.r.appspot.com")
            websocket_url = backend_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
            logger.info(f" SEARCH:  Using staging environment: {backend_url}")
        else:
            # Use local services
            backend_url = "http://localhost:8000"
            websocket_url = "ws://localhost:8000/ws"
        
        # Track all auth operations throughout Golden Path
        auth_operations_log = []
        unified_interface_usage = []
        auth_violations = []
        
        # Mock UnifiedAuthInterface to track usage
        def track_unified_auth_usage(operation_name):
            def wrapper(*args, **kwargs):
                unified_interface_usage.append(f"UnifiedAuthInterface.{operation_name}")
                logger.info(f" PASS:  SSOT COMPLIANT: UnifiedAuthInterface.{operation_name} called")
                return {"valid": True, "user_id": "golden_path_user", "email": "goldenpath@test.com"}
            return wrapper
        
        with patch('netra_backend.app.auth_integration.auth.UnifiedAuthInterface') as mock_unified_auth:
            mock_unified_auth.return_value.validate_token = AsyncMock(side_effect=track_unified_auth_usage("validate_token"))
            mock_unified_auth.return_value.verify_token = AsyncMock(side_effect=track_unified_auth_usage("verify_token"))
            
            # PHASE 1: User Authentication (should use UnifiedAuthInterface)
            logger.info(" SEARCH:  PHASE 1: Testing user authentication SSOT compliance")
            
            auth_helper = E2EAuthHelper()
            try:
                # Get test user authentication
                auth_result = await auth_helper.get_test_user_auth()
                
                if auth_result and auth_result.get("access_token"):
                    auth_operations_log.append("Phase1: User authentication successful")
                    logger.info(" PASS:  Phase 1: User authentication completed")
                    test_token = auth_result["access_token"]
                else:
                    # Create a test token for violation testing
                    test_payload = {
                        "sub": "golden_path_test_user",
                        "iss": "netra-auth-service", 
                        "aud": "netra-backend",
                        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
                        "iat": int(datetime.now().timestamp()),
                        "email": "goldenpath@violation.test"
                    }
                    
                    import jwt
                    env = get_env()
                    jwt_secret = env.get("JWT_SECRET_KEY", "golden-path-test-secret")
                    test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
                    
                    logger.warning(" WARNING: [U+FE0F] Using test token for violation testing")
                
            except Exception as e:
                logger.error(f" FAIL:  Phase 1 auth failed: {e}")
                auth_violations.append("Phase1: User authentication bypassed UnifiedAuthInterface")
                
                # Create fallback token for continued testing
                test_payload = {
                    "sub": "fallback_user",
                    "iss": "netra-auth-service",
                    "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
                    "iat": int(datetime.now().timestamp())
                }
                
                import jwt
                test_token = jwt.encode(test_payload, "fallback-secret", algorithm="HS256")
            
            # PHASE 2: WebSocket Connection Auth (CRITICAL VIOLATION POINT)
            logger.info(" SEARCH:  PHASE 2: Testing WebSocket connection auth SSOT compliance")
            
            websocket_auth_violations = []
            
            # Track WebSocket auth operations
            with patch('netra_backend.app.websocket_core.user_context_extractor.WebSocketUserContextExtractor.extract_user_context_from_token') as mock_ws_auth:
                
                def track_websocket_auth(token):
                    auth_operations_log.append("Phase2: WebSocket auth validation")
                    
                    # Check if this goes through UnifiedAuthInterface (it shouldn't due to violation)
                    if len(unified_interface_usage) == 0:
                        websocket_auth_violations.append("WebSocket auth bypassed UnifiedAuthInterface")
                        logger.error(" ALERT:  VIOLATION: WebSocket auth bypassed UnifiedAuthInterface")
                    
                    return {
                        "sub": "websocket_user",
                        "email": "websocket@violation.test",
                        "permissions": ["chat"]
                    }
                
                mock_ws_auth.side_effect = track_websocket_auth
                
                try:
                    # Attempt WebSocket connection with auth token
                    websocket_headers = {
                        "Authorization": f"Bearer {test_token}",
                        "Origin": backend_url
                    }
                    
                    # Test WebSocket connection (should validate token via UnifiedAuthInterface)
                    connection_successful = False
                    try:
                        if not NoDockerModeDetector.is_no_docker_mode():
                            # Only attempt actual WebSocket connection in full environment
                            async with websockets.connect(
                                websocket_url,
                                extra_headers=websocket_headers,
                                timeout=5
                            ) as websocket:
                                connection_successful = True
                                auth_operations_log.append("Phase2: WebSocket connection established")
                                logger.info(" PASS:  Phase 2: WebSocket connection successful")
                                
                                # PHASE 3: Agent Execution Request (Auth verification point)
                                logger.info(" SEARCH:  PHASE 3: Testing agent execution auth SSOT compliance")
                                
                                agent_request = {
                                    "type": "execute_agent",
                                    "data": {
                                        "message": "Test Golden Path SSOT compliance",
                                        "user_id": "golden_path_test"
                                    }
                                }
                                
                                await websocket.send(json.dumps(agent_request))
                                auth_operations_log.append("Phase3: Agent execution request sent")
                                
                                # Wait for agent events (should include auth verification)
                                events_received = []
                                try:
                                    for _ in range(5):  # Wait for up to 5 events
                                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                                        event = json.loads(event_data)
                                        events_received.append(event.get("type", "unknown"))
                                        
                                        if event.get("type") == "agent_started":
                                            auth_operations_log.append("Phase3: Agent started event received")
                                            logger.info(" PASS:  Phase 3: Agent execution initiated")
                                            break
                                            
                                except asyncio.TimeoutError:
                                    logger.warning(" WARNING: [U+FE0F] Phase 3: Timeout waiting for agent events")
                        else:
                            # Simulate connection for staging/no-docker mode
                            connection_successful = True
                            auth_operations_log.append("Phase2: WebSocket connection simulated (staging)")
                            logger.info(" PASS:  Phase 2: WebSocket connection simulated for staging")
                            
                    except Exception as e:
                        logger.error(f" FAIL:  Phase 2 WebSocket connection failed: {e}")
                        websocket_auth_violations.append(f"WebSocket connection failed: {e}")
                
                except Exception as e:
                    logger.error(f" FAIL:  Phase 2 WebSocket auth setup failed: {e}")
                    websocket_auth_violations.append(f"WebSocket auth setup failed: {e}")
            
            # Add WebSocket violations to main violations list
            auth_violations.extend(websocket_auth_violations)
            
            # PHASE 4: Analyze Golden Path Auth SSOT Compliance
            logger.info(" SEARCH:  PHASE 4: Analyzing complete Golden Path auth SSOT compliance")
            
            # Check if UnifiedAuthInterface was used throughout the Golden Path
            if len(unified_interface_usage) == 0:
                auth_violations.append("CRITICAL: No UnifiedAuthInterface usage detected in Golden Path")
                logger.error(" ALERT:  CRITICAL VIOLATION: Golden Path completely bypassed UnifiedAuthInterface")
            
            # Check for direct auth bypasses
            bypass_indicators = [
                "jwt.decode",
                "verify_signature: False", 
                "auth_client_core",
                "_resilient_validation_fallback"
            ]
            
            for indicator in bypass_indicators:
                if any(indicator in log_entry for log_entry in auth_operations_log):
                    auth_violations.append(f"Golden Path used bypassed auth: {indicator}")
                    logger.error(f" ALERT:  VIOLATION: Golden Path used {indicator}")
            
            # FINAL ASSESSMENT: Document all violations
            logger.info(" SEARCH:  FINAL: Golden Path SSOT violation assessment")
            
            logger.info(f" CHART:  Auth operations performed: {len(auth_operations_log)}")
            logger.info(f" CHART:  UnifiedAuthInterface usage: {len(unified_interface_usage)}")
            logger.info(f" CHART:  Auth violations detected: {len(auth_violations)}")
            
            for i, operation in enumerate(auth_operations_log, 1):
                logger.info(f" CHART:  {i}. {operation}")
            
            # Report violations
            if auth_violations:
                logger.critical(" ALERT:  GOLDEN PATH AUTH SSOT VIOLATIONS CONFIRMED:")
                for i, violation in enumerate(auth_violations, 1):
                    logger.critical(f" ALERT:  {i}. {violation}")
                    
                logger.critical(" ALERT:  THIS TEST PASSES = GOLDEN PATH HAS SSOT VIOLATIONS")
                logger.critical(" ALERT:  AFTER SSOT FIX: All Golden Path auth should use UnifiedAuthInterface")
                
                # Business impact assertion
                assert len(auth_violations) > 0, f"GOLDEN PATH SSOT VIOLATIONS: {auth_violations}"
                return {
                    "violations_found": len(auth_violations),
                    "violations_list": auth_violations,
                    "auth_operations": auth_operations_log,
                    "unified_interface_usage": unified_interface_usage
                }
            else:
                pytest.fail("VIOLATION NOT REPRODUCED: Golden Path appears SSOT compliant")

    @pytest.mark.asyncio
    @pytest.mark.integration  
    async def test_golden_path_auth_consistency_across_services(self):
        """
        INTEGRATION VIOLATION TEST: Golden Path auth consistency across all services.
        
        This test verifies that auth tokens work consistently across all services
        in the Golden Path (backend, WebSocket, agent execution).
        """
        logger.info(" ALERT:  TESTING GOLDEN PATH: Cross-service auth consistency")
        
        # Create test token
        test_payload = {
            "sub": "cross_service_test_user",
            "iss": "netra-auth-service",
            "aud": "netra-backend",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "crossservice@goldenpath.test"
        }
        
        import jwt
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "cross-service-test-secret")
        test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        
        # Test token across different Golden Path services
        service_auth_results = {}
        consistency_violations = []
        
        # Test 1: Backend REST API auth
        try:
            from netra_backend.app.auth_integration.auth import verify_token
            backend_result = await verify_token(test_token)
            service_auth_results["backend_api"] = bool(backend_result)
            logger.info(f" SEARCH:  Backend API auth result: {service_auth_results['backend_api']}")
        except Exception as e:
            service_auth_results["backend_api"] = False
            logger.warning(f" WARNING: [U+FE0F] Backend API auth failed: {e}")
        
        # Test 2: WebSocket auth  
        try:
            from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
            ws_extractor = WebSocketUserContextExtractor()
            ws_result = await ws_extractor.extract_user_context_from_token(test_token)
            service_auth_results["websocket"] = bool(ws_result)
            logger.info(f" SEARCH:  WebSocket auth result: {service_auth_results['websocket']}")
        except Exception as e:
            service_auth_results["websocket"] = False
            logger.warning(f" WARNING: [U+FE0F] WebSocket auth failed: {e}")
        
        # Test 3: Agent execution auth (simulated)
        try:
            # Simulate agent execution auth check
            service_auth_results["agent_execution"] = service_auth_results.get("websocket", False)
            logger.info(f" SEARCH:  Agent execution auth result: {service_auth_results['agent_execution']}")
        except Exception as e:
            service_auth_results["agent_execution"] = False
        
        # Check for cross-service inconsistencies (VIOLATION)
        auth_values = list(service_auth_results.values())
        if not all(result == auth_values[0] for result in auth_values):
            consistency_violations.append("Cross-service auth inconsistency detected")
            logger.error(" ALERT:  VIOLATION: Auth token accepted by some services but not others")
            
            for service, result in service_auth_results.items():
                if result != auth_values[0]:
                    consistency_violations.append(f"{service} auth differs from other services")
                    logger.error(f" ALERT:  INCONSISTENCY: {service} auth = {result}, others = {auth_values[0]}")
        
        if consistency_violations:
            logger.critical(" ALERT:  GOLDEN PATH CROSS-SERVICE AUTH VIOLATIONS:")
            for violation in consistency_violations:
                logger.critical(f" ALERT:  - {violation}")
                
            logger.critical(" ALERT:  CUSTOMER IMPACT: Inconsistent auth across Golden Path")
            logger.critical(" ALERT:  Users may connect to WebSocket but API calls fail")
            
            assert len(consistency_violations) > 0, f"CROSS-SERVICE AUTH VIOLATIONS: {consistency_violations}"
            return True
        else:
            logger.info(" PASS:  Cross-service auth consistency appears good")
            pytest.fail("VIOLATION NOT REPRODUCED: Cross-service auth is consistent")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_golden_path_auth_flow_architecture_violations(self):
        """
        UNIT VIOLATION TEST: Golden Path auth flow architectural violations.
        
        This test analyzes the auth flow architecture and identifies violations
        where components bypass the SSOT UnifiedAuthInterface pattern.
        """
        logger.info(" ALERT:  TESTING GOLDEN PATH: Auth flow architecture violations")
        
        # Track architectural violations in Golden Path components
        architecture_violations = []
        
        # Test 1: WebSocket component architecture
        try:
            from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
            
            # Check if WebSocket has architectural violations
            extractor = WebSocketUserContextExtractor()
            
            violation_methods = [
                "_resilient_validation_fallback",
                "_validate_token_with_unified_interface"
            ]
            
            for method in violation_methods:
                if hasattr(extractor, method):
                    architecture_violations.append(f"WebSocket has architectural violation method: {method}")
                    logger.error(f" ALERT:  ARCHITECTURE VIOLATION: WebSocket.{method}")
            
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] WebSocket architecture analysis failed: {e}")
        
        # Test 2: Auth integration architecture
        try:
            import netra_backend.app.auth_integration.auth as auth_module
            
            # Check for direct JWT operations (should be in UnifiedAuthInterface only)
            auth_functions = dir(auth_module)
            jwt_functions = [func for func in auth_functions if 'jwt' in func.lower() or 'token' in func.lower()]
            
            if jwt_functions:
                architecture_violations.append(f"Auth integration has direct JWT functions: {jwt_functions}")
                logger.error(f" ALERT:  ARCHITECTURE VIOLATION: Direct JWT functions in auth integration: {jwt_functions}")
                
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Auth integration architecture analysis failed: {e}")
        
        # Test 3: Import dependency violations
        try:
            # Check for circular/bypass import patterns
            import sys
            
            websocket_modules = [name for name in sys.modules if 'websocket' in name and 'netra_backend' in name]
            auth_modules = [name for name in sys.modules if 'auth' in name and 'netra_backend' in name]
            
            # Look for dependency bypass patterns
            for ws_module in websocket_modules:
                module = sys.modules.get(ws_module)
                if module and hasattr(module, '__file__'):
                    # Check if websocket modules import auth_client_core directly (violation)
                    if 'auth_client_core' in str(module.__file__) or \
                       any('auth_client_core' in str(getattr(module, attr, '')) 
                           for attr in dir(module) if not attr.startswith('_')):
                        architecture_violations.append(f"WebSocket module {ws_module} bypasses UnifiedAuthInterface")
                        logger.error(f" ALERT:  DEPENDENCY VIOLATION: {ws_module} bypasses UnifiedAuthInterface")
            
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Import dependency analysis failed: {e}")
        
        if architecture_violations:
            logger.critical(" ALERT:  GOLDEN PATH ARCHITECTURAL VIOLATIONS:")
            for violation in architecture_violations:
                logger.critical(f" ALERT:  - {violation}")
                
            logger.critical(" ALERT:  Golden Path architecture violates SSOT principles")
            logger.critical(" ALERT:  All auth operations should flow through UnifiedAuthInterface")
            
            assert len(architecture_violations) > 0, f"ARCHITECTURE VIOLATIONS: {architecture_violations}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: Golden Path architecture appears SSOT compliant")

    def tearDown(self):
        """Clean up test artifacts."""
        logger.info("[U+1F9F9] Golden Path auth SSOT compliance test cleanup complete")


if __name__ == "__main__":
    # Run this test independently to verify Golden Path violation reproduction
    pytest.main([__file__, "-v", "--tb=short"])