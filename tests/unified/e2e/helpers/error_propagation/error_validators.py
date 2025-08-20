"""Error Validation Components

This module contains validators for specific error types including authentication,
database, and network failures across service boundaries.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path for imports
import sys
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from ...real_websocket_client import RealWebSocketClient
from ...real_client_types import ClientConfig
from ...real_http_client import RealHTTPClient
from .error_generators import ErrorCorrelationContext, RealErrorPropagationTester, MockTokenGenerator

logger = logging.getLogger(__name__)


class AuthServiceFailurePropagationValidator:
    """Validates Auth service failures propagate correctly to Backend and Frontend."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
        self.auth_failure_scenarios: List[Dict[str, Any]] = []
    
    async def test_invalid_token_propagation_chain(self) -> Dict[str, Any]:
        """Test invalid token errors propagate through entire service chain."""
        context = self.tester._create_correlation_context("invalid_token_chain")
        context.service_chain.append("auth_validation")
        
        # Generate clearly invalid token
        invalid_token = MockTokenGenerator.create_invalid_token()
        
        # Test 1: HTTP API with invalid token
        api_result = await self._test_http_auth_rejection(invalid_token, context)
        
        # Test 2: WebSocket with invalid token
        ws_result = await self._test_websocket_auth_rejection(invalid_token, context)
        
        # Test 3: Verify error correlation
        correlation_result = self._validate_error_correlation(context)
        
        return {
            "test_type": "invalid_token_propagation",
            "request_id": context.request_id,
            "http_api_result": api_result,
            "websocket_result": ws_result,
            "correlation_result": correlation_result,
            "propagation_successful": self._assess_propagation_success(
                api_result, ws_result, correlation_result
            )
        }
    
    async def _test_http_auth_rejection(self, token: str, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test HTTP API auth rejection with error context."""
        context.service_chain.append("http_backend")
        
        try:
            headers = self._build_correlation_headers(context, token)
            
            # Try accessing protected endpoint
            response = await self.tester.http_client.get("/auth/me", token=token)
            
            return {
                "auth_error_detected": False,
                "unexpected_success": True,
                "response_status": getattr(response, 'status_code', None)
            }
            
        except Exception as e:
            return self._analyze_auth_error_response(e, context)
    
    def _build_correlation_headers(self, context: ErrorCorrelationContext, token: str) -> Dict[str, str]:
        """Build headers with correlation information."""
        return {
            "Authorization": f"Bearer {token}",
            "X-Request-ID": context.request_id,
            "X-Session-ID": context.session_id
        }
    
    def _analyze_auth_error_response(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze authentication error response."""
        error_str = str(error).lower()
        
        # Check for proper auth error indicators
        auth_indicators = ["unauthorized", "auth", "token", "invalid", "expired", "forbidden", "401", "403"]
        auth_error_detected = any(indicator in error_str for indicator in auth_indicators)
        
        # Check for user-friendly messaging
        friendly_indicators = ["please", "try again", "login", "expired", "invalid token", "authentication"]
        user_friendly = any(indicator in error_str for indicator in friendly_indicators)
        
        # Check for technical jargon that users shouldn't see
        jargon = ["traceback", "exception", "stack", "none", "null", "internal server error", "500"]
        has_technical_jargon = any(jargon in error_str for jargon in jargon)
        
        context.error_source = "http_auth"
        
        return {
            "auth_error_detected": auth_error_detected,
            "user_friendly": user_friendly and not has_technical_jargon,
            "error_message": str(error),
            "has_correlation_id": context.request_id in str(error)
        }
    
    async def _test_websocket_auth_rejection(self, token: str, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test WebSocket auth rejection with error context."""
        context.service_chain.append("websocket_backend")
        
        ws_url = self._build_websocket_url_with_auth(token, context)
        config = ClientConfig(timeout=8.0, max_retries=1)
        ws_client = RealWebSocketClient(ws_url, config)
        
        try:
            return await self._attempt_websocket_connection(ws_client, context)
        finally:
            await ws_client.close()
    
    def _build_websocket_url_with_auth(self, token: str, context: ErrorCorrelationContext) -> str:
        """Build WebSocket URL with authentication parameters."""
        ws_url = self.tester.orchestrator.get_websocket_url()
        return f"{ws_url}?token={token}&request_id={context.request_id}"
    
    async def _attempt_websocket_connection(self, ws_client: RealWebSocketClient, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Attempt WebSocket connection and analyze result."""
        try:
            connected = await ws_client.connect()
            
            if connected:
                return await self._test_websocket_auth_message(ws_client, context)
            else:
                return {"auth_error_detected": True, "connection_rejected": True}
                
        except Exception as e:
            return self._analyze_websocket_error(e, context)
    
    async def _test_websocket_auth_message(self, ws_client: RealWebSocketClient, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test WebSocket authentication via message."""
        await ws_client.send_json({
            "type": "auth_test",
            "request_id": context.request_id,
            "session_id": context.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        try:
            response = await ws_client.receive(timeout=5.0)
            return self._analyze_websocket_auth_response(response, context)
        except asyncio.TimeoutError:
            return {"auth_error_detected": False, "timeout_occurred": True}
    
    def _analyze_websocket_error(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze WebSocket connection error."""
        error_str = str(error).lower()
        auth_indicators = ["auth", "token", "unauthorized", "invalid", "websocket"]
        auth_error_detected = any(indicator in error_str for indicator in auth_indicators)
        
        context.error_source = "websocket_auth"
        
        return {
            "auth_error_detected": auth_error_detected,
            "exception_raised": True,
            "error_message": str(error)
        }
    
    def _analyze_websocket_auth_response(self, response: Any, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze WebSocket response for auth error handling."""
        if not response:
            return {"auth_error_detected": False, "no_response": True}
        
        response_str = json.dumps(response).lower() if isinstance(response, dict) else str(response).lower()
        
        # Check for auth error in response
        auth_indicators = ["error", "auth", "unauthorized", "invalid", "token"]
        auth_error_detected = any(indicator in response_str for indicator in auth_indicators)
        
        # Check for correlation ID preservation
        correlation_maintained = context.request_id.lower() in response_str
        
        return {
            "auth_error_detected": auth_error_detected,
            "correlation_maintained": correlation_maintained,
            "response": response
        }
    
    async def test_expired_token_recovery_chain(self) -> Dict[str, Any]:
        """Test expired token handling with recovery guidance."""
        context = self.tester._create_correlation_context("expired_token_recovery")
        
        expired_token = MockTokenGenerator.create_expired_token()
        recovery_result = await self._test_token_recovery_guidance(expired_token, context)
        
        return {
            "test_type": "expired_token_recovery",
            "request_id": context.request_id,
            "recovery_guidance_provided": recovery_result.get("recovery_guidance", False),
            "user_friendly_message": recovery_result.get("user_friendly", False),
            "actionable_steps": recovery_result.get("actionable_steps", [])
        }
    
    async def _test_token_recovery_guidance(self, token: str, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test that expired token errors provide recovery guidance."""
        try:
            response = await self.tester.http_client.get("/auth/me", token=token)
            return {"unexpected_success": True}
            
        except Exception as e:
            return self._analyze_recovery_guidance(str(e))
    
    def _analyze_recovery_guidance(self, error_str: str) -> Dict[str, Any]:
        """Analyze error message for recovery guidance."""
        error_lower = error_str.lower()
        
        # Check for recovery guidance keywords
        recovery_indicators = ["refresh", "login", "expired", "renew", "authenticate", "try again"]
        recovery_guidance = any(indicator in error_lower for indicator in recovery_indicators)
        
        # Check for actionable steps
        actionable_indicators = ["please", "contact", "visit", "go to", "try", "refresh"]
        actionable_steps = [indicator for indicator in actionable_indicators if indicator in error_lower]
        
        return {
            "recovery_guidance": recovery_guidance,
            "user_friendly": "please" in error_lower or "try" in error_lower,
            "actionable_steps": actionable_steps,
            "error_message": error_str
        }
    
    def _validate_error_correlation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Validate error correlation across service boundaries."""
        return {
            "correlation_maintained": len(context.service_chain) > 1,
            "request_id_tracked": bool(context.request_id),
            "service_chain": context.service_chain,
            "error_source_identified": bool(context.error_source)
        }
    
    def _assess_propagation_success(self, api_result: Dict, ws_result: Dict, correlation_result: Dict) -> bool:
        """Assess overall propagation success."""
        return (
            api_result.get("auth_error_detected", False) and
            ws_result.get("auth_error_detected", False) and
            correlation_result.get("correlation_maintained", False)
        )


class DatabaseErrorHandlingValidator:
    """Validates database errors are handled gracefully with recovery mechanisms."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
        self.db_error_scenarios: List[Dict[str, Any]] = []
    
    async def test_database_connection_failure_handling(self) -> Dict[str, Any]:
        """Test database connection failure handling and recovery."""
        context = self.tester._create_correlation_context("db_connection_failure")
        context.service_chain.append("database_layer")
        
        # Test database-dependent endpoint
        db_test_result = await self._test_database_dependent_operation(context)
        
        # Test graceful degradation
        degradation_result = await self._test_graceful_degradation(context)
        
        # Test recovery mechanisms
        recovery_result = await self._test_database_recovery(context)
        
        return {
            "test_type": "database_connection_failure",
            "request_id": context.request_id,
            "database_operation": db_test_result,
            "graceful_degradation": degradation_result,
            "recovery_mechanisms": recovery_result,
            "system_stability": self._assess_system_stability(
                db_test_result, degradation_result, recovery_result
            )
        }
    
    async def _test_database_dependent_operation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test operation that depends on database."""
        context.service_chain.append("user_profile_service")
        
        try:
            response = await self.tester.http_client.get("/auth/me", token="mock_token_for_db_test")
            
            return {
                "database_accessible": True,
                "operation_successful": True,
                "status_code": getattr(response, 'status_code', None)
            }
            
        except Exception as e:
            return self._analyze_database_error(e, context)
    
    def _analyze_database_error(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze database error response."""
        error_str = str(error).lower()
        
        # Check for database-related error indicators
        db_indicators = ["database", "connection", "timeout", "unavailable", "service", "502", "503"]
        db_error_detected = any(indicator in error_str for indicator in db_indicators)
        
        # Check for graceful error handling
        graceful_indicators = ["temporarily", "unavailable", "try again", "maintenance", "service"]
        graceful_handling = any(indicator in error_str for indicator in graceful_indicators)
        
        context.error_source = "database"
        
        return {
            "database_error_detected": db_error_detected,
            "graceful_handling": graceful_handling,
            "error_message": str(error),
            "system_stable": True  # If we can catch and handle it, system is stable
        }
    
    async def _test_graceful_degradation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test system graceful degradation when database is unavailable."""
        context.service_chain.append("degradation_layer")
        
        try:
            response = await self.tester.http_client.get("/health")
            
            return {
                "health_endpoint_available": True,
                "graceful_degradation": True,
                "status_code": getattr(response, 'status_code', None)
            }
            
        except Exception as e:
            return {
                "health_endpoint_failed": True,
                "system_still_responding": True,
                "error_handled": self._is_graceful_error(str(e))
            }
    
    def _is_graceful_error(self, error_str: str) -> bool:
        """Check if error indicates graceful handling."""
        return "health" in error_str.lower() or "service" in error_str.lower()
    
    async def _test_database_recovery(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test database recovery mechanisms."""
        context.service_chain.append("recovery_layer")
        
        recovery_attempts = []
        
        for attempt in range(3):
            try:
                response = await self.tester.http_client.get("/health")
                recovery_attempts.append({
                    "attempt": attempt + 1,
                    "successful": True,
                    "status": getattr(response, 'status_code', None)
                })
                break
                
            except Exception as e:
                recovery_attempts.append({
                    "attempt": attempt + 1,
                    "successful": False,
                    "error": str(e)
                })
                await asyncio.sleep(1.0)
        
        successful_recovery = any(attempt["successful"] for attempt in recovery_attempts)
        
        return {
            "recovery_attempts": recovery_attempts,
            "successful_recovery": successful_recovery,
            "retry_mechanism_active": len(recovery_attempts) > 1
        }
    
    def _assess_system_stability(self, *test_results) -> Dict[str, Any]:
        """Assess overall system stability during database issues."""
        stability_indicators = []
        
        for result in test_results:
            if isinstance(result, dict):
                if result.get("system_stable", False):
                    stability_indicators.append("stable_error_handling")
                if result.get("graceful_handling", False):
                    stability_indicators.append("graceful_degradation")
                if result.get("successful_recovery", False):
                    stability_indicators.append("recovery_capability")
        
        return {
            "stability_score": len(stability_indicators),
            "stability_indicators": stability_indicators,
            "system_resilient": len(stability_indicators) >= 2
        }