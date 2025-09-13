"""
uvicorn Protocol Enhancement Module for Issue #449 Remediation

PURPOSE: Enhanced uvicorn protocol layer handling to prevent WebSocket middleware 
         stack failures in GCP Cloud Run environments.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality protection through enhanced
                uvicorn ASGI protocol transition handling.

ISSUE #449 REMEDIATION - PHASE 1: uvicorn Protocol Layer Enhancement
- Enhanced WebSocket exclusion middleware with uvicorn-specific handling
- ASGI scope validation and protocol transition protection  
- uvicorn protocol negotiation failure prevention
- Enhanced error recovery for middleware stack conflicts

CRITICAL FIXES:
- uvicorn WebSocket protocol transition failure prevention
- ASGI scope corruption detection and recovery
- Middleware stack ordering protection for uvicorn
- Protocol negotiation enhancement for Cloud Run
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, Tuple, List
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.responses import JSONResponse
from fastapi import Request, Response
import time

logger = logging.getLogger(__name__)


class UvicornProtocolValidator:
    """
    Enhanced uvicorn protocol validation for Issue #449 remediation.
    
    CRITICAL: This class prevents uvicorn middleware stack failures by validating
    and protecting ASGI scopes during protocol transitions.
    """
    
    def __init__(self):
        self.protocol_transitions = []
        self.validation_failures = []
        self.scope_corruptions = []
        
    def validate_websocket_scope(self, scope: Scope) -> Tuple[bool, Optional[str]]:
        """
        Enhanced WebSocket scope validation for uvicorn compatibility.
        
        CRITICAL FIX: Prevents uvicorn from rejecting valid WebSocket scopes
        due to middleware stack conflicts.
        
        Args:
            scope: ASGI scope to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Phase 1: Basic WebSocket scope structure validation
            if not isinstance(scope, dict):
                error = f"Invalid scope type: {type(scope)} - uvicorn expects dict"
                self.validation_failures.append({
                    "error": "scope_type_invalid",
                    "details": error,
                    "scope_type": type(scope).__name__
                })
                return False, error
            
            # Phase 2: WebSocket-specific scope validation
            scope_type = scope.get("type")
            if scope_type != "websocket":
                return True, None  # Not a WebSocket, let other validators handle
            
            # Phase 3: Required WebSocket fields validation
            required_ws_fields = ["path", "query_string", "headers"]
            missing_fields = []
            
            for field in required_ws_fields:
                if field not in scope:
                    missing_fields.append(field)
            
            if missing_fields:
                error = f"WebSocket scope missing required fields for uvicorn: {missing_fields}"
                self.validation_failures.append({
                    "error": "missing_websocket_fields",
                    "details": error,
                    "missing_fields": missing_fields,
                    "scope": scope
                })
                return False, error
            
            # Phase 4: uvicorn-specific WebSocket validation
            # Check for corrupted HTTP fields in WebSocket scope
            invalid_http_fields = ["method", "query_params"]
            found_invalid_fields = []
            
            for field in invalid_http_fields:
                if field in scope:
                    found_invalid_fields.append(field)
            
            if found_invalid_fields:
                error = f"WebSocket scope contains invalid HTTP fields: {found_invalid_fields}"
                self.scope_corruptions.append({
                    "error": "websocket_scope_corruption",
                    "details": error,
                    "invalid_fields": found_invalid_fields,
                    "scope": scope
                })
                return False, error
            
            # Phase 5: ASGI version compatibility check
            asgi_info = scope.get("asgi", {})
            asgi_version = asgi_info.get("version", "unknown")
            
            if asgi_version not in ["2.0", "2.1", "3.0", "3.1"]:
                logger.warning(f"Unusual ASGI version for uvicorn: {asgi_version}")
            
            # Phase 6: Headers validation (bytes format required)
            headers = scope.get("headers", [])
            if not isinstance(headers, list):
                error = f"WebSocket headers must be list for uvicorn, got {type(headers)}"
                return False, error
            
            for header_pair in headers:
                if not isinstance(header_pair, (list, tuple)) or len(header_pair) != 2:
                    error = f"Invalid header format for uvicorn: {header_pair}"
                    return False, error
                
                header_name, header_value = header_pair
                if not isinstance(header_name, bytes) or not isinstance(header_value, bytes):
                    error = f"Headers must be bytes for uvicorn: {header_name}={header_value}"
                    return False, error
            
            return True, None
            
        except Exception as e:
            error = f"WebSocket scope validation exception: {e}"
            logger.error(error, exc_info=True)
            self.validation_failures.append({
                "error": "validation_exception",
                "details": error,
                "exception": str(e)
            })
            return False, error
    
    def detect_protocol_transition_corruption(self, scope: Scope) -> Optional[Dict[str, Any]]:
        """
        Detect uvicorn protocol transition corruption.
        
        CRITICAL FIX: Identifies when uvicorn has corrupted the ASGI scope
        during HTTP to WebSocket protocol transitions.
        
        Args:
            scope: ASGI scope to analyze
            
        Returns:
            Corruption details if detected, None if clean
        """
        try:
            scope_type = scope.get("type", "unknown")
            
            # Detection Pattern 1: WebSocket scope with HTTP method
            if scope_type == "websocket" and "method" in scope:
                corruption = {
                    "pattern": "websocket_with_http_method",
                    "details": f"WebSocket scope contains HTTP method: {scope.get('method')}",
                    "scope_type": scope_type,
                    "corrupted_fields": ["method"],
                    "uvicorn_failure": "protocol_transition_incomplete"
                }
                self.scope_corruptions.append(corruption)
                return corruption
            
            # Detection Pattern 2: HTTP scope with WebSocket fields
            if scope_type == "http":
                websocket_fields = ["websocket"]
                found_ws_fields = [field for field in websocket_fields if field in scope]
                
                if found_ws_fields:
                    corruption = {
                        "pattern": "http_with_websocket_fields",
                        "details": f"HTTP scope contains WebSocket fields: {found_ws_fields}",
                        "scope_type": scope_type,
                        "corrupted_fields": found_ws_fields,
                        "uvicorn_failure": "protocol_transition_incomplete"
                    }
                    self.scope_corruptions.append(corruption)
                    return corruption
            
            # Detection Pattern 3: Invalid scope type
            valid_types = ["http", "websocket", "lifespan"]
            if scope_type not in valid_types:
                corruption = {
                    "pattern": "invalid_scope_type",
                    "details": f"Invalid ASGI scope type: {scope_type}",
                    "scope_type": scope_type,
                    "corrupted_fields": ["type"],
                    "uvicorn_failure": "scope_type_corruption"
                }
                self.scope_corruptions.append(corruption)
                return corruption
            
            return None
            
        except Exception as e:
            logger.error(f"Protocol transition corruption detection error: {e}", exc_info=True)
            return {
                "pattern": "detection_error",
                "details": f"Cannot detect corruption: {e}",
                "exception": str(e)
            }
    
    def repair_corrupted_scope(self, scope: Scope) -> Tuple[Scope, List[str]]:
        """
        Attempt to repair corrupted ASGI scope for uvicorn compatibility.
        
        CRITICAL FIX: Repairs scope corruption caused by uvicorn middleware
        stack conflicts to prevent connection failures.
        
        Args:
            scope: Corrupted ASGI scope
            
        Returns:
            Tuple of (repaired_scope, repair_actions)
        """
        repaired_scope = scope.copy()
        repair_actions = []
        
        try:
            scope_type = scope.get("type", "unknown")
            
            # Repair Pattern 1: Remove HTTP method from WebSocket scope
            if scope_type == "websocket" and "method" in repaired_scope:
                del repaired_scope["method"]
                repair_actions.append("removed_http_method_from_websocket")
                logger.warning("Repaired WebSocket scope by removing HTTP method")
            
            # Repair Pattern 2: Remove query_params from WebSocket scope
            if scope_type == "websocket" and "query_params" in repaired_scope:
                del repaired_scope["query_params"]
                repair_actions.append("removed_query_params_from_websocket")
                logger.warning("Repaired WebSocket scope by removing query_params")
            
            # Repair Pattern 3: Ensure required fields exist
            if scope_type == "websocket":
                # Ensure query_string exists (required for WebSocket)
                if "query_string" not in repaired_scope:
                    repaired_scope["query_string"] = b""
                    repair_actions.append("added_missing_query_string")
                
                # Ensure headers exist
                if "headers" not in repaired_scope:
                    repaired_scope["headers"] = []
                    repair_actions.append("added_missing_headers")
                
                # Ensure path exists
                if "path" not in repaired_scope:
                    repaired_scope["path"] = "/ws"
                    repair_actions.append("added_default_path")
            
            # Repair Pattern 4: Fix ASGI version info
            if "asgi" not in repaired_scope:
                repaired_scope["asgi"] = {"version": "3.0"}
                repair_actions.append("added_asgi_version_info")
            
            return repaired_scope, repair_actions
            
        except Exception as e:
            logger.error(f"Scope repair error: {e}", exc_info=True)
            repair_actions.append(f"repair_failed: {e}")
            return scope, repair_actions


class UvicornWebSocketExclusionMiddleware(BaseHTTPMiddleware):
    """
    Enhanced WebSocket exclusion middleware for uvicorn protocol handling.
    
    CRITICAL FIX for Issue #449: This middleware prevents uvicorn middleware stack
    failures by providing enhanced WebSocket exclusion with protocol validation.
    
    KEY IMPROVEMENTS:
    - uvicorn-specific protocol transition protection
    - Enhanced ASGI scope validation and repair
    - Protocol negotiation failure prevention
    - Comprehensive error recovery for middleware conflicts
    """
    
    def __init__(self, app: ASGIApp, **kwargs):
        super().__init__(app, **kwargs)
        self.protocol_validator = UvicornProtocolValidator()
        self.middleware_conflicts = []
        self.protocol_recoveries = []
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Enhanced HTTP request dispatch with uvicorn protocol protection.
        
        CRITICAL FIX: Provides comprehensive protection against uvicorn
        middleware stack failures during WebSocket protocol transitions.
        """
        try:
            # Phase 1: Enhanced request validation for uvicorn compatibility
            validation_result = self._validate_request_for_uvicorn(request)
            if not validation_result["valid"]:
                return await self._create_uvicorn_safe_error_response(
                    validation_result["error"], 400
                )
            
            # Phase 2: WebSocket upgrade detection and protection
            if self._is_websocket_upgrade_request(request):
                logger.debug("WebSocket upgrade detected - applying uvicorn protection")
                return await self._handle_websocket_upgrade_protection(request, call_next)
            
            # Phase 3: Normal HTTP processing with enhanced error handling
            return await self._handle_http_request_with_protection(request, call_next)
            
        except Exception as e:
            logger.error(f"uvicorn WebSocket exclusion middleware error: {e}", exc_info=True)
            return await self._create_uvicorn_safe_error_response(
                f"Middleware protection error: {e}", 500
            )
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Enhanced ASGI middleware call with uvicorn protocol handling.
        
        CRITICAL FIX: Provides comprehensive ASGI scope protection and validation
        to prevent uvicorn middleware stack failures.
        """
        try:
            # Phase 1: Enhanced scope type detection and validation
            scope_type = scope.get("type", "unknown")
            
            if scope_type == "websocket":
                await self._handle_websocket_scope_protection(scope, receive, send)
                return
            elif scope_type == "http":
                await self._handle_http_scope_protection(scope, receive, send)
                return
            else:
                # Phase 2: Unknown scope type protection
                logger.debug(f"Non-standard ASGI scope type: {scope_type} - applying safe passthrough")
                await self._handle_unknown_scope_protection(scope, receive, send)
                return
                
        except Exception as e:
            logger.error(f"CRITICAL: uvicorn ASGI scope handling error: {e}", exc_info=True)
            await self._send_uvicorn_safe_error(send, scope, str(e))
    
    async def _handle_websocket_scope_protection(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Enhanced WebSocket scope protection for uvicorn compatibility.
        
        CRITICAL FIX: Prevents uvicorn WebSocket scope corruption and validation failures.
        """
        try:
            # Phase 1: uvicorn WebSocket scope validation
            is_valid, error_message = self.protocol_validator.validate_websocket_scope(scope)
            
            if not is_valid:
                logger.error(f"uvicorn WebSocket scope validation failed: {error_message}")
                await self._send_websocket_error(send, 1011, "uvicorn scope validation failed")
                return
            
            # Phase 2: Protocol transition corruption detection
            corruption = self.protocol_validator.detect_protocol_transition_corruption(scope)
            
            if corruption:
                logger.warning(f"uvicorn protocol corruption detected: {corruption['pattern']}")
                
                # Attempt scope repair
                repaired_scope, repair_actions = self.protocol_validator.repair_corrupted_scope(scope)
                
                if repair_actions:
                    logger.info(f"uvicorn scope repaired: {repair_actions}")
                    self.protocol_recoveries.append({
                        "corruption": corruption,
                        "repair_actions": repair_actions,
                        "timestamp": time.time()
                    })
                    scope = repaired_scope
            
            # Phase 3: Safe WebSocket passthrough with monitoring
            logger.debug("WebSocket scope validated - bypassing HTTP middleware stack")
            await self.app(scope, receive, send)
            
        except Exception as e:
            logger.error(f"WebSocket scope protection error: {e}", exc_info=True)
            await self._send_websocket_error(send, 1011, f"Protocol protection error: {e}")
    
    async def _handle_http_scope_protection(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Enhanced HTTP scope protection with WebSocket upgrade detection.
        
        CRITICAL FIX: Detects WebSocket upgrade attempts in HTTP scopes and applies
        appropriate uvicorn protocol handling.
        """
        try:
            # Phase 1: Check for WebSocket upgrade in HTTP scope
            headers = dict(scope.get("headers", []))
            upgrade_header = headers.get(b"upgrade", b"").decode().lower()
            connection_header = headers.get(b"connection", b"").decode().lower()
            
            if upgrade_header == "websocket" and "upgrade" in connection_header:
                logger.warning("WebSocket upgrade detected in HTTP scope - potential uvicorn protocol confusion")
                
                # This indicates uvicorn protocol transition issue
                self.middleware_conflicts.append({
                    "type": "websocket_in_http_scope",
                    "path": scope.get("path", "/"),
                    "headers": headers,
                    "timestamp": time.time()
                })
                
                # Apply enhanced handling for WebSocket upgrade
                await self._handle_websocket_upgrade_in_http_scope(scope, receive, send)
                return
            
            # Phase 2: Normal HTTP processing with enhanced monitoring
            await super().__call__(scope, receive, send)
            
        except Exception as e:
            logger.error(f"HTTP scope protection error: {e}", exc_info=True)
            await self._send_uvicorn_safe_error(send, scope, str(e))
    
    async def _handle_websocket_upgrade_in_http_scope(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle WebSocket upgrade detected in HTTP scope.
        
        CRITICAL FIX: Provides recovery for uvicorn protocol confusion where
        WebSocket upgrades are processed as HTTP requests.
        """
        try:
            logger.info("Applying WebSocket upgrade recovery for uvicorn protocol confusion")
            
            # Attempt to convert HTTP scope to WebSocket scope
            websocket_scope = scope.copy()
            websocket_scope["type"] = "websocket"
            
            # Remove HTTP-specific fields
            http_fields_to_remove = ["method", "query_params"]
            for field in http_fields_to_remove:
                if field in websocket_scope:
                    del websocket_scope[field]
            
            # Ensure WebSocket-required fields
            if "query_string" not in websocket_scope:
                websocket_scope["query_string"] = scope.get("query_string", b"")
            
            # Validate converted scope
            is_valid, error_message = self.protocol_validator.validate_websocket_scope(websocket_scope)
            
            if is_valid:
                logger.info("Successfully converted HTTP scope to WebSocket scope")
                await self.app(websocket_scope, receive, send)
            else:
                logger.error(f"WebSocket scope conversion failed: {error_message}")
                await self._send_uvicorn_safe_error(send, scope, "WebSocket upgrade conversion failed")
            
        except Exception as e:
            logger.error(f"WebSocket upgrade recovery error: {e}", exc_info=True)
            await self._send_uvicorn_safe_error(send, scope, f"Upgrade recovery failed: {e}")
    
    async def _handle_unknown_scope_protection(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handle unknown ASGI scope types safely.
        
        CRITICAL FIX: Provides safe handling for unexpected scope types that
        might cause uvicorn middleware stack failures.
        """
        try:
            scope_type = scope.get("type", "unknown")
            logger.debug(f"Unknown ASGI scope type: {scope_type} - applying safe passthrough")
            
            # Pass through unknown scopes safely
            await self.app(scope, receive, send)
            
        except Exception as e:
            logger.error(f"Unknown scope protection error: {e}", exc_info=True)
            # For unknown scopes, we cannot send standardized errors
            # Just log and let it fail gracefully
            pass
    
    def _validate_request_for_uvicorn(self, request: Request) -> Dict[str, Any]:
        """
        Enhanced request validation for uvicorn compatibility.
        
        CRITICAL FIX: Validates request objects to prevent uvicorn middleware
        stack failures due to malformed request attributes.
        """
        try:
            # Phase 1: Basic request object validation
            if not hasattr(request, 'url') or not hasattr(request.url, 'path'):
                return {
                    "valid": False,
                    "error": "Invalid request object - missing URL attributes"
                }
            
            # Phase 2: Request scope validation
            if hasattr(request, 'scope') and request.scope:
                scope_type = request.scope.get('type', 'unknown')
                if scope_type not in ['http', 'websocket']:
                    return {
                        "valid": False,
                        "error": f"Invalid request scope type: {scope_type}"
                    }
            
            # Phase 3: HTTP method validation for HTTP requests
            if hasattr(request, 'method'):
                method = request.method
                if not isinstance(method, str) or not method:
                    return {
                        "valid": False,
                        "error": f"Invalid HTTP method: {method}"
                    }
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Request validation exception: {e}"
            }
    
    def _is_websocket_upgrade_request(self, request: Request) -> bool:
        """
        Enhanced WebSocket upgrade detection for uvicorn compatibility.
        
        CRITICAL FIX: Improved detection prevents uvicorn from mishandling
        WebSocket upgrade requests in the middleware stack.
        """
        try:
            # Check standard WebSocket upgrade headers
            upgrade_header = request.headers.get("upgrade", "").lower()
            connection_header = request.headers.get("connection", "").lower()
            
            is_upgrade = (
                upgrade_header == "websocket" and
                "upgrade" in connection_header
            )
            
            if is_upgrade:
                # Additional validation for uvicorn compatibility
                ws_version = request.headers.get("sec-websocket-version")
                ws_key = request.headers.get("sec-websocket-key")
                
                if not ws_version or not ws_key:
                    logger.warning("WebSocket upgrade missing required headers")
                    return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"WebSocket upgrade detection error: {e}", exc_info=True)
            return False
    
    async def _handle_websocket_upgrade_protection(self, request: Request, call_next: Callable) -> Response:
        """
        Handle WebSocket upgrade with enhanced uvicorn protection.
        
        CRITICAL FIX: Provides comprehensive protection during WebSocket upgrade
        to prevent uvicorn middleware stack conflicts.
        """
        try:
            logger.debug("Applying WebSocket upgrade protection for uvicorn")
            
            # WebSocket upgrades should not be processed by HTTP middleware
            # Return appropriate response to indicate upgrade handling
            return JSONResponse(
                status_code=426,  # Upgrade Required
                content={
                    "error": "websocket_upgrade_required",
                    "message": "WebSocket upgrade detected - use WebSocket protocol",
                    "path": request.url.path,
                    "middleware": "uvicorn_websocket_exclusion"
                },
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade"
                }
            )
            
        except Exception as e:
            logger.error(f"WebSocket upgrade protection error: {e}", exc_info=True)
            return await self._create_uvicorn_safe_error_response(
                f"WebSocket upgrade protection failed: {e}", 500
            )
    
    async def _handle_http_request_with_protection(self, request: Request, call_next: Callable) -> Response:
        """
        Handle HTTP request with enhanced uvicorn protection.
        
        CRITICAL FIX: Provides protection for normal HTTP requests to prevent
        them from interfering with WebSocket protocol handling.
        """
        try:
            # Enhanced HTTP request processing with monitoring
            start_time = time.time()
            response = await call_next(request)
            processing_time = time.time() - start_time
            
            # Monitor for potential uvicorn issues
            if processing_time > 10.0:  # Slow processing might indicate issues
                logger.warning(f"Slow HTTP processing: {processing_time:.2f}s for {request.url.path}")
            
            return response
            
        except Exception as e:
            logger.error(f"HTTP request protection error: {e}", exc_info=True)
            return await self._create_uvicorn_safe_error_response(
                f"HTTP request protection failed: {e}", 500
            )
    
    async def _create_uvicorn_safe_error_response(self, error_message: str, status_code: int) -> Response:
        """
        Create error response safe for uvicorn handling.
        
        CRITICAL FIX: Ensures error responses don't cause additional uvicorn
        middleware stack issues.
        """
        try:
            return JSONResponse(
                status_code=status_code,
                content={
                    "error": "uvicorn_middleware_protection",
                    "message": error_message,
                    "issue_reference": "#449",
                    "middleware": "uvicorn_websocket_exclusion",
                    "timestamp": time.time()
                },
                headers={
                    "X-Middleware-Protection": "uvicorn-websocket-exclusion",
                    "X-Issue-Reference": "449"
                }
            )
        except Exception as e:
            logger.critical(f"Cannot create safe error response: {e}")
            # Return minimal response as last resort
            return Response(
                content="Internal middleware error",
                status_code=500,
                media_type="text/plain"
            )
    
    async def _send_websocket_error(self, send: Send, code: int, reason: str) -> None:
        """
        Send WebSocket error response safely for uvicorn.
        
        CRITICAL FIX: Ensures WebSocket error responses are compatible with
        uvicorn protocol handling.
        """
        try:
            await send({
                "type": "websocket.close",
                "code": code,
                "reason": reason
            })
        except Exception as e:
            logger.error(f"Failed to send WebSocket error: {e}")
    
    async def _send_uvicorn_safe_error(self, send: Send, scope: Scope, error_message: str) -> None:
        """
        Send HTTP error response safe for uvicorn handling.
        
        CRITICAL FIX: Provides error responses that don't cause additional
        uvicorn middleware stack issues.
        """
        try:
            scope_type = scope.get("type", "unknown")
            
            if scope_type == "http":
                response_data = {
                    "error": "uvicorn_middleware_error",
                    "message": error_message,
                    "scope_type": scope_type,
                    "issue_reference": "#449"
                }
                response_body = json.dumps(response_data)
                content_length = str(len(response_body.encode("utf-8")))
                
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", content_length.encode()),
                        (b"x-middleware-error", b"uvicorn-protection"),
                    ],
                })
                
                await send({
                    "type": "http.response.body",
                    "body": response_body.encode("utf-8"),
                })
            else:
                # For non-HTTP scopes, just log the error
                logger.error(f"Cannot send error response for scope type: {scope_type}")
                
        except Exception as e:
            logger.critical(f"Failed to send uvicorn safe error: {e}")
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """
        Get diagnostic information for Issue #449 troubleshooting.
        
        Returns comprehensive diagnostic data for uvicorn middleware issues.
        """
        return {
            "middleware": "uvicorn_websocket_exclusion",
            "issue_reference": "#449",
            "validation_failures": len(self.protocol_validator.validation_failures),
            "scope_corruptions": len(self.protocol_validator.scope_corruptions),
            "middleware_conflicts": len(self.middleware_conflicts),
            "protocol_recoveries": len(self.protocol_recoveries),
            "recent_failures": self.protocol_validator.validation_failures[-5:],
            "recent_corruptions": self.protocol_validator.scope_corruptions[-5:],
            "recent_conflicts": self.middleware_conflicts[-5:],
            "recent_recoveries": self.protocol_recoveries[-5:]
        }


def create_uvicorn_websocket_exclusion_middleware() -> UvicornWebSocketExclusionMiddleware:
    """
    Factory function to create enhanced uvicorn WebSocket exclusion middleware.
    
    CRITICAL FIX for Issue #449: Creates the enhanced middleware with uvicorn
    protocol protection for WebSocket connections.
    
    Returns:
        Configured UvicornWebSocketExclusionMiddleware instance
    """
    logger.info("Creating enhanced uvicorn WebSocket exclusion middleware for Issue #449")
    return UvicornWebSocketExclusionMiddleware


# Export the enhanced middleware for use in middleware setup
__all__ = [
    "UvicornWebSocketExclusionMiddleware",
    "UvicornProtocolValidator", 
    "create_uvicorn_websocket_exclusion_middleware"
]