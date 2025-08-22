"""Error Correlation Testing

This module contains utilities for testing cross-service error correlation
with tracking IDs and correlation context validation.
"""

import asyncio
import json
import logging

# Add project root to path for imports
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.helpers.error_propagation.error_generators import (
    ErrorCorrelationContext,
    RealErrorPropagationTester,
)
from tests.e2e.real_client_types import ClientConfig
from tests.e2e.real_websocket_client import RealWebSocketClient

logger = logging.getLogger(__name__)


class ErrorCorrelationValidator:
    """Validates error correlation works across all services with tracking IDs."""
    
    def __init__(self, tester: RealErrorPropagationTester):
        self.tester = tester
        self.correlation_tests: List[Dict[str, Any]] = []
    
    async def test_cross_service_error_correlation(self) -> Dict[str, Any]:
        """Test error correlation across multiple service boundaries."""
        context = self.tester._create_correlation_context("cross_service_correlation", "test_user_correlation")
        
        # Test correlation through HTTP -> Auth -> Database chain
        correlation_chain_result = await self._test_correlation_chain(context)
        
        # Test WebSocket correlation
        websocket_correlation_result = await self._test_websocket_correlation(context)
        
        # Validate correlation ID persistence
        persistence_result = self._validate_correlation_persistence(context)
        
        return {
            "test_type": "cross_service_error_correlation",
            "request_id": context.request_id,
            "correlation_chain": correlation_chain_result,
            "websocket_correlation": websocket_correlation_result,
            "correlation_persistence": persistence_result,
            "overall_correlation_success": self._assess_correlation_success(
                correlation_chain_result, websocket_correlation_result, persistence_result
            )
        }
    
    async def _test_correlation_chain(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test correlation through HTTP -> Auth -> Database chain."""
        context.service_chain.extend(["http_gateway", "auth_service", "database_layer"])
        
        try:
            headers = self._build_correlation_headers(context)
            
            # This should fail and propagate correlation IDs through the chain
            response = await self.tester.http_client.get("/auth/me", token="invalid_correlation_test_token")
            
            return {"unexpected_success": True, "response": response}
            
        except Exception as e:
            return self._analyze_correlation_in_error(e, context)
    
    def _build_correlation_headers(self, context: ErrorCorrelationContext) -> Dict[str, str]:
        """Build headers with correlation information."""
        return {
            "X-Request-ID": context.request_id,
            "X-Session-ID": context.session_id,
            "X-User-ID": context.user_id or "anonymous"
        }
    
    def _analyze_correlation_in_error(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze error for correlation information."""
        error_str = str(error)
        
        # Check if correlation IDs are preserved in error
        correlation_preserved = (
            context.request_id in error_str or
            context.session_id in error_str
        )
        
        # Check for structured error format
        structured_error = self._check_structured_error_format(error_str)
        
        return {
            "error_raised": True,
            "correlation_preserved": correlation_preserved,
            "structured_error": structured_error,
            "error_message": str(error)
        }
    
    async def _test_websocket_correlation(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test error correlation through WebSocket connections."""
        context.service_chain.append("websocket_gateway")
        
        ws_url = self._build_websocket_correlation_url(context)
        config = ClientConfig(timeout=8.0, max_retries=1)
        ws_client = RealWebSocketClient(ws_url, config)
        
        try:
            return await self._test_websocket_correlation_flow(ws_client, context)
        finally:
            await ws_client.close()
    
    def _build_websocket_correlation_url(self, context: ErrorCorrelationContext) -> str:
        """Build WebSocket URL with correlation parameters."""
        ws_url = self.tester.orchestrator.get_websocket_url()
        return (
            f"{ws_url}?token=invalid_ws_correlation_test&"
            f"request_id={context.request_id}&"
            f"session_id={context.session_id}"
        )
    
    async def _test_websocket_correlation_flow(self, ws_client: RealWebSocketClient, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Test WebSocket correlation flow."""
        try:
            connected = await ws_client.connect()
            
            if connected:
                return await self._send_correlation_test_message(ws_client, context)
            else:
                return {
                    "connection_failed": True,
                    "correlation_in_connection_error": True
                }
                
        except Exception as e:
            return self._analyze_websocket_correlation_error(e, context)
    
    async def _send_correlation_test_message(self, ws_client: RealWebSocketClient, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Send test message with correlation data."""
        test_message = {
            "type": "correlation_test",
            "request_id": context.request_id,
            "session_id": context.session_id,
            "user_id": context.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await ws_client.send_json(test_message)
        
        try:
            response = await ws_client.receive(timeout=5.0)
            return self._analyze_websocket_correlation_response(response, context)
        except asyncio.TimeoutError:
            return {"websocket_timeout": True, "correlation_unknown": True}
    
    def _analyze_websocket_correlation_error(self, error: Exception, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze WebSocket correlation error."""
        error_str = str(error)
        correlation_in_error = (
            context.request_id in error_str or
            context.session_id in error_str
        )
        
        return {
            "websocket_exception": True,
            "correlation_in_exception": correlation_in_error,
            "error_message": str(error)
        }
    
    def _analyze_websocket_correlation_response(self, response: Any, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Analyze WebSocket response for correlation information."""
        if not response:
            return {"no_response": True}
        
        response_str = json.dumps(response) if isinstance(response, dict) else str(response)
        
        correlation_indicators = [
            context.request_id in response_str,
            context.session_id in response_str,
            "request_id" in response_str.lower(),
            "session_id" in response_str.lower()
        ]
        
        return {
            "correlation_preserved": any(correlation_indicators),
            "correlation_indicators_count": sum(correlation_indicators),
            "response": response
        }
    
    def _check_structured_error_format(self, error_str: str) -> Dict[str, Any]:
        """Check if error follows structured format with correlation data."""
        structured_indicators = [
            "request_id" in error_str.lower(),
            "session_id" in error_str.lower(),
            "timestamp" in error_str.lower(),
            "error_code" in error_str.lower()
        ]
        
        return {
            "has_structured_format": sum(structured_indicators) >= 2,
            "structured_indicators": structured_indicators,
            "indicator_count": sum(structured_indicators)
        }
    
    def _validate_correlation_persistence(self, context: ErrorCorrelationContext) -> Dict[str, Any]:
        """Validate that correlation context is properly maintained."""
        return {
            "context_created": bool(context.request_id),
            "service_chain_tracked": len(context.service_chain) > 0,
            "error_source_identified": bool(context.error_source),
            "correlation_complete": (
                bool(context.request_id) and
                len(context.service_chain) > 0 and
                bool(context.error_source)
            )
        }
    
    def _assess_correlation_success(self, *test_results) -> Dict[str, Any]:
        """Assess overall success of error correlation."""
        success_indicators = []
        
        for result in test_results:
            if isinstance(result, dict):
                if result.get("correlation_preserved", False):
                    success_indicators.append("correlation_preserved")
                if result.get("structured_error", {}).get("has_structured_format", False):
                    success_indicators.append("structured_format")
                if result.get("correlation_complete", False):
                    success_indicators.append("context_complete")
        
        return {
            "success_indicators": success_indicators,
            "correlation_score": len(success_indicators),
            "correlation_effective": len(success_indicators) >= 2
        }


class CorrelationTestHelper:
    """Helper utilities for correlation testing."""
    
    @staticmethod
    def validate_correlation_headers(headers: Dict[str, str]) -> Dict[str, bool]:
        """Validate that correlation headers are properly formatted."""
        required_headers = ["X-Request-ID", "X-Session-ID"]
        optional_headers = ["X-User-ID", "X-Correlation-ID"]
        
        validation_result = {}
        
        for header in required_headers:
            validation_result[f"{header}_present"] = header in headers
            if header in headers:
                validation_result[f"{header}_valid"] = bool(headers[header])
        
        for header in optional_headers:
            if header in headers:
                validation_result[f"{header}_present"] = True
                validation_result[f"{header}_valid"] = bool(headers[header])
        
        return validation_result
    
    @staticmethod
    def extract_correlation_info(error_message: str) -> Dict[str, Any]:
        """Extract correlation information from error message."""
        correlation_info = {
            "request_id_found": False,
            "session_id_found": False,
            "timestamp_found": False,
            "correlation_data": {}
        }
        
        # Simple extraction patterns
        import re
        
        request_id_match = re.search(r'request[_-]?id[:\s]*([a-zA-Z0-9\-_]+)', error_message, re.IGNORECASE)
        if request_id_match:
            correlation_info["request_id_found"] = True
            correlation_info["correlation_data"]["request_id"] = request_id_match.group(1)
        
        session_id_match = re.search(r'session[_-]?id[:\s]*([a-zA-Z0-9\-_]+)', error_message, re.IGNORECASE)
        if session_id_match:
            correlation_info["session_id_found"] = True
            correlation_info["correlation_data"]["session_id"] = session_id_match.group(1)
        
        # Look for timestamp patterns
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'timestamp[:\s]*(\d+)'
        ]
        
        for pattern in timestamp_patterns:
            timestamp_match = re.search(pattern, error_message, re.IGNORECASE)
            if timestamp_match:
                correlation_info["timestamp_found"] = True
                correlation_info["correlation_data"]["timestamp"] = timestamp_match.group(0)
                break
        
        return correlation_info
