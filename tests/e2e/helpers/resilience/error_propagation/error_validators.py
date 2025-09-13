"""Authentication Error Validation Components



This module contains validators for authentication error types across service boundaries.

"""



import asyncio

import json

import logging



# Add project root to path for imports

import sys

import time

from datetime import datetime, timezone

from pathlib import Path

from typing import Any, Dict, List





from tests.e2e.helpers.resilience.error_propagation.error_generators import (

    ErrorCorrelationContext,

    MockTokenGenerator,

    RealErrorPropagationTester,

)

from test_framework.http_client import ClientConfig

from test_framework.http_client import UnifiedHTTPClient as RealHTTPClient

from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient



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





# Validation functions for export

def validate_error_propagation(error_context: Dict[str, Any]) -> bool:

    """Validate that errors propagate correctly across service boundaries."""

    required_fields = ["error_type", "source_service", "target_services"]

    return all(field in error_context for field in required_fields)





def validate_error_isolation(error_context: Dict[str, Any]) -> bool:

    """Validate that errors are properly isolated to prevent cascading failures."""

    return error_context.get("isolated", False) and error_context.get("contained", False)





def validate_recovery_behavior(recovery_context: Dict[str, Any]) -> bool:

    """Validate that service recovery behavior is appropriate."""

    return recovery_context.get("recovered", False) and recovery_context.get("recovery_time", 0) < 30

    

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





class AuthTokenValidator:

    """Utility for validating authentication tokens and scenarios."""

    

    @staticmethod

    def validate_token_format(token: str) -> Dict[str, bool]:

        """Validate token format and structure."""

        if not token:

            return {"valid_format": False, "reason": "empty_token"}

        

        # Basic JWT format check (header.payload.signature)

        parts = token.split('.')

        

        validation_result = {

            "valid_format": len(parts) == 3,

            "has_header": len(parts) > 0 and bool(parts[0]),

            "has_payload": len(parts) > 1 and bool(parts[1]),

            "has_signature": len(parts) > 2 and bool(parts[2]),

            "part_count": len(parts)

        }

        

        if not validation_result["valid_format"]:

            validation_result["reason"] = f"invalid_part_count_{len(parts)}"

        

        return validation_result

    

    @staticmethod

    def extract_token_info(token: str) -> Dict[str, Any]:

        """Extract information from token (for testing purposes only)."""

        if not token:

            return {"error": "empty_token"}

        

        parts = token.split('.')

        if len(parts) != 3:

            return {"error": "invalid_format", "part_count": len(parts)}

        

        try:

            import base64

            

            # Decode header

            header_data = base64.b64decode(parts[0] + '==').decode('utf-8')

            header = json.loads(header_data)

            

            # Decode payload

            payload_data = base64.b64decode(parts[1] + '==').decode('utf-8')

            payload = json.loads(payload_data)

            

            return {

                "header": header,

                "payload": payload,

                "algorithm": header.get("alg"),

                "token_type": header.get("typ"),

                "expiry": payload.get("exp"),

                "subject": payload.get("sub"),

                "issued_at": payload.get("iat")

            }

            

        except Exception as e:

            return {"error": "decode_failed", "message": str(e)}

    

    @staticmethod

    def is_token_expired(token: str) -> Dict[str, Any]:

        """Check if token is expired."""

        token_info = AuthTokenValidator.extract_token_info(token)

        

        if "error" in token_info:

            return {"error": token_info["error"], "expired": None}

        

        expiry = token_info.get("expiry")

        if not expiry:

            return {"expired": None, "reason": "no_expiry_claim"}

        

        current_time = int(time.time())

        

        return {

            "expired": current_time > expiry,

            "expiry_timestamp": expiry,

            "current_timestamp": current_time,

            "time_remaining": expiry - current_time if current_time <= expiry else 0

        }

