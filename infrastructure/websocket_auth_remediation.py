#!/usr/bin/env python3
"""
WebSocket Authentication Remediation Implementation
Infrastructure Remediation Plan - Phase 2

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure - WebSocket Reliability
- Business Goal: Restore WebSocket handshake reliability for chat functionality
- Value Impact: Enable $500K+ ARR chat workflow completion
- Strategic Impact: Foundation for real-time user experience

This module implements fixes for WebSocket authentication race conditions
and handshake timing issues that prevent reliable chat functionality.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
import aiohttp

# SSOT imports
from shared.isolated_environment import get_env
from shared.types.core_types import UserID, ConnectionID, SessionID
from netra_backend.app.services.user_execution_context import UserExecutionContext


@dataclass
class WebSocketAuthResult:
    """Result of WebSocket authentication attempt."""
    success: bool
    user_context: Optional[UserExecutionContext] = None
    connection_id: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None
    retry_count: int = 0


@dataclass
class AuthServiceHealthStatus:
    """Health status of auth service connectivity."""
    service_available: bool
    average_response_time_ms: float
    success_rate_percent: float
    last_error: Optional[str] = None
    consecutive_failures: int = 0


class WebSocketAuthenticationError(Exception):
    """Raised when WebSocket authentication fails."""
    pass


class WebSocketAuthenticationTimeout(WebSocketAuthenticationError):
    """Raised when WebSocket authentication times out.""" 
    pass


class WebSocketAuthHelpers:
    """Enhanced authentication helpers for WebSocket handshakes."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        env = get_env()
        self.auth_timeout = float(env.get("WEBSOCKET_AUTH_TIMEOUT", "15.0"))
        self.retry_attempts = int(env.get("WEBSOCKET_AUTH_RETRIES", "3"))
        self.backoff_multiplier = float(env.get("WEBSOCKET_AUTH_BACKOFF", "1.5"))
        
    async def validate_websocket_token(
        self, 
        token: str, 
        connection_id: str,
        use_internal_service: bool = True
    ) -> WebSocketAuthResult:
        """
        Validate JWT token for WebSocket connections with enhanced error handling.
        
        Args:
            token: JWT token to validate
            connection_id: WebSocket connection identifier
            use_internal_service: Whether to use internal auth service URL
            
        Returns:
            WebSocketAuthResult with validation outcome
        """
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(
                    f"WebSocket auth attempt {attempt + 1}/{self.retry_attempts} "
                    f"for connection {connection_id}"
                )
                
                # Get auth service URL (internal or external)
                auth_service_url = self._get_auth_service_url(use_internal_service)
                
                # Perform token validation with timeout
                validation_result = await self._call_auth_service_with_timeout(
                    auth_service_url, token, connection_id
                )
                
                if validation_result["valid"]:
                    # Create user execution context from valid token
                    user_context = UserExecutionContext.create_from_token_data(
                        validation_result["user_data"]
                    )
                    
                    response_time = (time.time() - start_time) * 1000
                    
                    self.logger.info(
                        f"WebSocket auth successful for connection {connection_id} "
                        f"(attempt {attempt + 1}, {response_time:.1f}ms)"
                    )
                    
                    return WebSocketAuthResult(
                        success=True,
                        user_context=user_context,
                        connection_id=connection_id,
                        response_time_ms=response_time,
                        retry_count=attempt
                    )
                else:
                    # Invalid token - don't retry
                    response_time = (time.time() - start_time) * 1000
                    error_msg = f"Invalid token for connection {connection_id}"
                    
                    self.logger.warning(error_msg)
                    
                    return WebSocketAuthResult(
                        success=False,
                        connection_id=connection_id,
                        error_message=error_msg,
                        response_time_ms=response_time,
                        retry_count=attempt
                    )
                    
            except asyncio.TimeoutError as e:
                last_error = f"Auth service timeout: {e}"
                self.logger.warning(
                    f"WebSocket auth timeout for connection {connection_id} "
                    f"(attempt {attempt + 1}/{self.retry_attempts})"
                )
                
            except aiohttp.ClientError as e:
                last_error = f"Auth service connection error: {e}"
                self.logger.warning(
                    f"WebSocket auth connection error for connection {connection_id} "
                    f"(attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                
            except Exception as e:
                last_error = f"Auth service error: {e}"
                self.logger.error(
                    f"WebSocket auth unexpected error for connection {connection_id} "
                    f"(attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
            
            # Wait before retry (except on last attempt)
            if attempt < self.retry_attempts - 1:
                backoff_delay = self.backoff_multiplier ** attempt
                await asyncio.sleep(backoff_delay)
        
        # All attempts failed
        response_time = (time.time() - start_time) * 1000
        error_msg = f"Auth failed after {self.retry_attempts} attempts: {last_error}"
        
        self.logger.error(
            f"WebSocket auth failed for connection {connection_id} after "
            f"{self.retry_attempts} attempts ({response_time:.1f}ms total)"
        )
        
        return WebSocketAuthResult(
            success=False,
            connection_id=connection_id,
            error_message=error_msg,
            response_time_ms=response_time,
            retry_count=self.retry_attempts - 1
        )
    
    async def _call_auth_service_with_timeout(
        self,
        auth_service_url: str,
        token: str,
        connection_id: str
    ) -> Dict[str, Any]:
        """Call auth service with proper timeout handling."""
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Connection-ID": connection_id  # For auth service logging
        }
        
        timeout = aiohttp.ClientTimeout(total=self.auth_timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{auth_service_url}/auth/validate-websocket",
                headers=headers,
                json={"connection_id": connection_id}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "valid": True,
                        "user_data": result.get("user_data", {})
                    }
                elif response.status == 401:
                    # Invalid/expired token
                    return {
                        "valid": False,
                        "error": "Invalid or expired token"
                    }
                else:
                    # Auth service error
                    error_text = await response.text()
                    raise aiohttp.ClientError(
                        f"Auth service returned {response.status}: {error_text}"
                    )
    
    def _get_auth_service_url(self, use_internal: bool) -> str:
        """Get auth service URL for validation calls."""
        env = get_env()
        if use_internal:
            # Use internal VPC URL for better performance and reliability
            internal_url = env.get("AUTH_SERVICE_INTERNAL_URL")
            if internal_url:
                return internal_url
        
        # Fallback to external URL
        external_url = env.get("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
        return external_url


class WebSocketAuthCircuitBreaker:
    """Circuit breaker pattern for auth service calls."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        env = get_env()
        self.failure_threshold = int(env.get("AUTH_CIRCUIT_BREAKER_THRESHOLD", "5"))
        self.recovery_timeout = int(env.get("AUTH_CIRCUIT_BREAKER_TIMEOUT", "60"))
        self.half_open_max_calls = int(env.get("AUTH_CIRCUIT_BREAKER_HALF_OPEN", "3"))
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.half_open_calls = 0
        
    async def call_with_circuit_breaker(self, auth_helpers: WebSocketAuthHelpers, *args, **kwargs) -> WebSocketAuthResult:
        """Execute auth call with circuit breaker protection."""
        
        # Check circuit breaker state
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.half_open_calls = 0
                self.logger.info("Auth circuit breaker: Attempting reset to HALF_OPEN")
            else:
                # Circuit is still open - fail fast
                return WebSocketAuthResult(
                    success=False,
                    error_message="Auth service circuit breaker is OPEN - failing fast",
                    connection_id=kwargs.get("connection_id", "unknown")
                )
        
        try:
            # Make the actual auth call
            result = await auth_helpers.validate_websocket_token(*args, **kwargs)
            
            if result.success:
                self._on_success()
            else:
                self._on_failure()
            
            return result
            
        except Exception as e:
            self._on_failure()
            return WebSocketAuthResult(
                success=False,
                error_message=f"Auth service call failed: {e}",
                connection_id=kwargs.get("connection_id", "unknown")
            )
    
    def _on_success(self):
        """Handle successful auth call."""
        if self.state == "HALF_OPEN":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = "CLOSED"
                self.failure_count = 0
                self.logger.info("Auth circuit breaker: Reset to CLOSED state")
        elif self.state == "CLOSED":
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed auth call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "CLOSED" and self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(
                f"Auth circuit breaker: OPENED due to {self.failure_count} failures"
            )
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.logger.warning("Auth circuit breaker: Back to OPEN from HALF_OPEN")
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker."""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.recovery_timeout


class WebSocketAuthMonitor:
    """Monitor for WebSocket authentication health and performance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.auth_attempts = []
        env = get_env()
        self.max_history = int(env.get("AUTH_MONITOR_HISTORY", "1000"))
        
    def record_auth_attempt(self, result: WebSocketAuthResult):
        """Record an authentication attempt for monitoring."""
        record = {
            "timestamp": datetime.now(timezone.utc),
            "success": result.success,
            "response_time_ms": result.response_time_ms,
            "retry_count": result.retry_count,
            "connection_id": result.connection_id,
            "error_message": result.error_message
        }
        
        self.auth_attempts.append(record)
        
        # Maintain history limit
        if len(self.auth_attempts) > self.max_history:
            self.auth_attempts = self.auth_attempts[-self.max_history:]
        
        # Log significant events
        if not result.success:
            self.logger.warning(
                f"WebSocket auth failed for {result.connection_id}: {result.error_message}"
            )
        elif result.retry_count > 0:
            self.logger.info(
                f"WebSocket auth succeeded with {result.retry_count} retries for {result.connection_id}"
            )
    
    def get_auth_service_health(self, window_minutes: int = 15) -> AuthServiceHealthStatus:
        """Get auth service health status for a time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        recent_attempts = [
            attempt for attempt in self.auth_attempts
            if attempt["timestamp"] > cutoff_time
        ]
        
        if not recent_attempts:
            return AuthServiceHealthStatus(
                service_available=True,  # Assume healthy if no recent attempts
                average_response_time_ms=0.0,
                success_rate_percent=100.0
            )
        
        # Calculate metrics
        successful_attempts = [a for a in recent_attempts if a["success"]]
        success_rate = (len(successful_attempts) / len(recent_attempts)) * 100
        
        response_times = [
            a["response_time_ms"] for a in recent_attempts
            if a["response_time_ms"] is not None
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        # Check for consecutive failures
        consecutive_failures = 0
        for attempt in reversed(recent_attempts):
            if not attempt["success"]:
                consecutive_failures += 1
            else:
                break
        
        last_error = None
        failed_attempts = [a for a in recent_attempts if not a["success"]]
        if failed_attempts:
            last_error = failed_attempts[-1]["error_message"]
        
        return AuthServiceHealthStatus(
            service_available=success_rate > 50.0,  # Consider available if >50% success
            average_response_time_ms=avg_response_time,
            success_rate_percent=success_rate,
            last_error=last_error,
            consecutive_failures=consecutive_failures
        )


class WebSocketAuthManager:
    """Comprehensive WebSocket authentication manager with remediation features."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.auth_helpers = WebSocketAuthHelpers()
        self.circuit_breaker = WebSocketAuthCircuitBreaker()
        self.monitor = WebSocketAuthMonitor()
        
        # Demo mode configuration
        env = get_env()
        self.demo_mode = env.get("DEMO_MODE", "0") == "1"
        if self.demo_mode:
            self.logger.info("WebSocket auth manager running in DEMO_MODE - auth bypass enabled")
    
    async def authenticate_websocket_connection(
        self,
        token: Optional[str],
        connection_id: str
    ) -> WebSocketAuthResult:
        """
        Authenticate WebSocket connection with comprehensive error handling.
        
        This is the main entry point for WebSocket authentication that includes
        all remediation features: retry logic, circuit breaker, monitoring, and demo mode.
        """
        
        # Demo mode bypass
        if self.demo_mode:
            self.logger.info(f"DEMO_MODE: Bypassing auth for connection {connection_id}")
            return self._create_demo_auth_result(connection_id)
        
        # Validate token presence
        if not token:
            result = WebSocketAuthResult(
                success=False,
                connection_id=connection_id,
                error_message="No authentication token provided",
                response_time_ms=0.0
            )
            self.monitor.record_auth_attempt(result)
            return result
        
        # Authenticate with circuit breaker protection
        result = await self.circuit_breaker.call_with_circuit_breaker(
            self.auth_helpers,
            token,
            connection_id,
            use_internal_service=True  # Prefer internal service for better performance
        )
        
        # Record attempt for monitoring
        self.monitor.record_auth_attempt(result)
        
        return result
    
    def _create_demo_auth_result(self, connection_id: str) -> WebSocketAuthResult:
        """Create authentication result for demo mode."""
        # Create demo user context
        demo_user_context = UserExecutionContext(
            user_id=UserID("demo-user"),
            session_id=SessionID("demo-session"),
            organization_id=None,
            permissions=set(),
            metadata={"demo_mode": True}
        )
        
        return WebSocketAuthResult(
            success=True,
            user_context=demo_user_context,
            connection_id=connection_id,
            response_time_ms=1.0,  # Instant demo auth
            retry_count=0
        )
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of WebSocket authentication system."""
        auth_health = self.monitor.get_auth_service_health()
        
        return {
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "auth_service_available": auth_health.service_available,
            "auth_success_rate_percent": auth_health.success_rate_percent,
            "average_response_time_ms": auth_health.average_response_time_ms,
            "consecutive_failures": auth_health.consecutive_failures,
            "last_error": auth_health.last_error,
            "demo_mode_enabled": self.demo_mode
        }


async def main():
    """Main function to test WebSocket authentication remediation."""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize auth manager
    auth_manager = WebSocketAuthManager()
    
    # Test authentication scenarios
    test_scenarios = [
        {"name": "Valid Token", "token": "valid-jwt-token", "connection_id": "test-conn-1"},
        {"name": "Invalid Token", "token": "invalid-token", "connection_id": "test-conn-2"},
        {"name": "No Token", "token": None, "connection_id": "test-conn-3"},
    ]
    
    print("=== WebSocket Authentication Remediation Test ===\n")
    
    for scenario in test_scenarios:
        print(f"Testing: {scenario['name']}")
        
        result = await auth_manager.authenticate_websocket_connection(
            scenario["token"],
            scenario["connection_id"]
        )
        
        print(f"  Result: {' PASS:  Success' if result.success else ' FAIL:  Failed'}")
        if result.error_message:
            print(f"  Error: {result.error_message}")
        print(f"  Response time: {result.response_time_ms:.1f}ms")
        print(f"  Retries: {result.retry_count}")
        print()
    
    # Show health status
    health = auth_manager.get_health_status()
    print("=== Authentication System Health ===")
    for key, value in health.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())