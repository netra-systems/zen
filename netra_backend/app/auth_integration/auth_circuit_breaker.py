"""
Authentication Circuit Breaker - Graceful Failure Handling

Business Value Justification:
- Segment: Platform/Infrastructure - Authentication Reliability  
- Business Goal: Prevent cascade auth failures and maintain WebSocket connectivity
- Value Impact: Protects $500K+ ARR by providing graceful degradation during auth issues
- Revenue Impact: Maintains chat functionality even when auth services experience problems

CRITICAL MISSION:
Implement circuit breaker pattern for authentication to prevent WebSocket 1011 errors
from cascading across multiple connections when auth services are experiencing issues.

ARCHITECTURE:
- CircuitBreakerAuth: Main circuit breaker with state management
- AuthFailureDetector: Detects patterns indicating auth service issues
- GracefulDegradationManager: Manages fallback auth strategies
- RecoveryMonitor: Monitors auth service recovery and resets breaker

CIRCUIT BREAKER STATES:
1. CLOSED - Normal operation, all auth requests processed
2. OPEN - Auth service failing, activate fallback strategies  
3. HALF_OPEN - Testing recovery, limited auth requests allowed

REMEDIATION STRATEGY:
1. Monitor auth failure rates and patterns
2. Detect service degradation before complete failure
3. Activate appropriate fallback auth methods
4. Prevent auth storms that worsen service issues
5. Monitor recovery and gradually restore full auth
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

from fastapi import WebSocket

from netra_backend.app.logging_config import central_logger
from netra_backend.app.auth_integration.auth_permissiveness import (
    AuthPermissivenessResult,
    AuthPermissivenessLevel,
    authenticate_with_permissiveness
)

logger = central_logger.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states for auth service protection."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Service failing, use fallbacks
    HALF_OPEN = "half_open" # Testing recovery


@dataclass
class AuthFailurePattern:
    """Pattern of authentication failures for analysis."""
    failure_count: int = 0
    consecutive_failures: int = 0
    failure_rate: float = 0.0
    last_failure_time: Optional[float] = None
    error_patterns: Dict[str, int] = field(default_factory=dict)
    recovery_attempts: int = 0


@dataclass 
class CircuitBreakerConfig:
    """Configuration for auth circuit breaker."""
    
    # Failure thresholds
    failure_threshold: int = 5          # Consecutive failures to trip breaker
    failure_rate_threshold: float = 0.5 # 50% failure rate to trip breaker
    
    # Time windows
    failure_window_seconds: int = 60    # Window for calculating failure rate
    open_timeout_seconds: int = 30      # How long to stay open before testing
    half_open_max_requests: int = 3     # Max requests in half-open state
    
    # Recovery settings
    success_threshold: int = 3          # Consecutive successes to close breaker
    degradation_timeout: int = 300      # Max time in degraded mode (5 min)
    
    # Fallback settings
    enable_relaxed_fallback: bool = True
    enable_demo_fallback: bool = True
    enable_emergency_fallback: bool = True


class AuthFailureDetector:
    """Detects authentication failure patterns and service degradation."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.failure_history = deque(maxlen=100)  # Keep last 100 failures
        self.success_history = deque(maxlen=100)  # Keep last 100 successes
        self.pattern = AuthFailurePattern()
    
    def record_auth_failure(self, error_code: str, error_message: str):
        """Record an authentication failure for pattern analysis."""
        current_time = time.time()
        
        # Update failure pattern
        self.pattern.failure_count += 1
        self.pattern.consecutive_failures += 1
        self.pattern.last_failure_time = current_time
        
        # Track error patterns
        if error_code not in self.pattern.error_patterns:
            self.pattern.error_patterns[error_code] = 0
        self.pattern.error_patterns[error_code] += 1
        
        # Add to failure history
        self.failure_history.append({
            "timestamp": current_time,
            "error_code": error_code,
            "error_message": error_message[:100]  # Truncate long messages
        })
        
        # Calculate current failure rate
        self._update_failure_rate()
        
        logger.warning(f"AUTH CIRCUIT: Failure recorded - {error_code}: {error_message[:50]}...")
        
    def record_auth_success(self):
        """Record an authentication success."""
        current_time = time.time()
        
        # Reset consecutive failures on success
        self.pattern.consecutive_failures = 0
        
        # Add to success history
        self.success_history.append({
            "timestamp": current_time
        })
        
        # Update failure rate
        self._update_failure_rate()
        
    def should_trip_breaker(self) -> bool:
        """Determine if circuit breaker should trip based on failure patterns."""
        
        # Check consecutive failure threshold
        if self.pattern.consecutive_failures >= self.config.failure_threshold:
            logger.warning(f"AUTH CIRCUIT: Consecutive failure threshold reached: "
                          f"{self.pattern.consecutive_failures}/{self.config.failure_threshold}")
            return True
        
        # Check failure rate threshold
        if self.pattern.failure_rate >= self.config.failure_rate_threshold:
            logger.warning(f"AUTH CIRCUIT: Failure rate threshold reached: "
                          f"{self.pattern.failure_rate:.2%}/{self.config.failure_rate_threshold:.2%}")
            return True
        
        return False
    
    def _update_failure_rate(self):
        """Update the current failure rate based on recent history."""
        current_time = time.time()
        window_start = current_time - self.config.failure_window_seconds
        
        # Count recent failures and successes
        recent_failures = sum(1 for f in self.failure_history 
                             if f["timestamp"] >= window_start)
        recent_successes = sum(1 for s in self.success_history 
                              if s["timestamp"] >= window_start)
        
        # Calculate failure rate
        total_attempts = recent_failures + recent_successes
        if total_attempts > 0:
            self.pattern.failure_rate = recent_failures / total_attempts
        else:
            self.pattern.failure_rate = 0.0
    
    def get_failure_analysis(self) -> Dict[str, Any]:
        """Get detailed failure analysis for monitoring."""
        return {
            "pattern": {
                "failure_count": self.pattern.failure_count,
                "consecutive_failures": self.pattern.consecutive_failures, 
                "failure_rate": round(self.pattern.failure_rate, 3),
                "last_failure": self.pattern.last_failure_time,
                "error_patterns": self.pattern.error_patterns,
                "recovery_attempts": self.pattern.recovery_attempts
            },
            "thresholds": {
                "failure_threshold": self.config.failure_threshold,
                "failure_rate_threshold": self.config.failure_rate_threshold,
                "window_seconds": self.config.failure_window_seconds
            },
            "should_trip": self.should_trip_breaker(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class GracefulDegradationManager:
    """Manages fallback authentication strategies when circuit breaker is open."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.degradation_stats = {
            "relaxed_attempts": 0,
            "relaxed_successes": 0,
            "demo_attempts": 0,
            "demo_successes": 0,
            "emergency_attempts": 0,
            "emergency_successes": 0
        }
    
    async def authenticate_with_fallback(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Authenticate using fallback strategies when circuit breaker is open."""
        
        logger.info("AUTH CIRCUIT: Using fallback authentication strategies")
        
        # Try fallback strategies in order of preference
        fallback_strategies = []
        
        if self.config.enable_relaxed_fallback:
            fallback_strategies.append(("relaxed", AuthPermissivenessLevel.RELAXED))
        
        if self.config.enable_demo_fallback:
            fallback_strategies.append(("demo", AuthPermissivenessLevel.DEMO))
        
        if self.config.enable_emergency_fallback:
            fallback_strategies.append(("emergency", AuthPermissivenessLevel.EMERGENCY))
        
        # Try each fallback strategy
        for strategy_name, auth_level in fallback_strategies:
            try:
                logger.info(f"AUTH CIRCUIT: Trying {strategy_name} fallback")
                
                # Update attempt counter
                self.degradation_stats[f"{strategy_name}_attempts"] += 1
                
                # Try the fallback strategy
                result = await authenticate_with_permissiveness(websocket)
                
                if result.success:
                    # Update success counter
                    self.degradation_stats[f"{strategy_name}_successes"] += 1
                    
                    # Add fallback info to result
                    result.audit_info.update({
                        "fallback_strategy": strategy_name,
                        "circuit_breaker_active": True,
                        "degraded_authentication": True
                    })
                    
                    logger.info(f"AUTH CIRCUIT: {strategy_name} fallback succeeded")
                    return result
                else:
                    logger.warning(f"AUTH CIRCUIT: {strategy_name} fallback failed: {result.security_warnings}")
                    
            except Exception as e:
                logger.error(f"AUTH CIRCUIT: {strategy_name} fallback exception: {e}")
                continue
        
        # All fallback strategies failed
        logger.error("AUTH CIRCUIT: All fallback strategies failed")
        return AuthPermissivenessResult(
            success=False,
            level=AuthPermissivenessLevel.EMERGENCY,
            auth_method="all_fallbacks_failed",
            security_warnings=["Circuit breaker open and all fallback strategies failed"],
            audit_info={
                "circuit_breaker_active": True,
                "all_fallbacks_failed": True,
                "degradation_stats": self.degradation_stats
            }
        )
    
    def get_degradation_stats(self) -> Dict[str, Any]:
        """Get degradation statistics for monitoring."""
        stats = {}
        
        for strategy in ["relaxed", "demo", "emergency"]:
            attempts = self.degradation_stats[f"{strategy}_attempts"]
            successes = self.degradation_stats[f"{strategy}_successes"]
            success_rate = (successes / max(1, attempts)) * 100
            
            stats[f"{strategy}_fallback"] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate_percent": round(success_rate, 2)
            }
        
        return {
            "degradation_stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class RecoveryMonitor:
    """Monitors auth service recovery and manages circuit breaker state transitions."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.recovery_attempts = 0
        self.recovery_successes = 0
        self.half_open_requests = 0
        self.last_recovery_test = None
    
    def can_attempt_recovery(self, current_time: float, breaker_opened_time: float) -> bool:
        """Check if recovery can be attempted (transition to half-open)."""
        time_since_open = current_time - breaker_opened_time
        return time_since_open >= self.config.open_timeout_seconds
    
    def can_test_recovery(self) -> bool:
        """Check if a recovery test request can be made in half-open state."""
        return self.half_open_requests < self.config.half_open_max_requests
    
    def record_recovery_test(self):
        """Record that a recovery test is being attempted."""
        self.half_open_requests += 1
        self.recovery_attempts += 1
        self.last_recovery_test = time.time()
        
        logger.info(f"AUTH CIRCUIT: Recovery test {self.half_open_requests}/{self.config.half_open_max_requests}")
    
    def record_recovery_success(self):
        """Record a successful recovery test."""
        self.recovery_successes += 1
        
        logger.info(f"AUTH CIRCUIT: Recovery success {self.recovery_successes}/{self.config.success_threshold}")
    
    def should_close_breaker(self) -> bool:
        """Check if circuit breaker should close (recovery successful)."""
        return self.recovery_successes >= self.config.success_threshold
    
    def should_reopen_breaker(self) -> bool:
        """Check if circuit breaker should reopen (recovery tests failed)."""
        return self.half_open_requests >= self.config.half_open_max_requests and self.recovery_successes == 0
    
    def reset_recovery_state(self):
        """Reset recovery state when breaker closes or reopens."""
        self.half_open_requests = 0
        self.recovery_successes = 0
        self.last_recovery_test = None
        
        logger.info("AUTH CIRCUIT: Recovery state reset")
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """Get recovery monitoring status."""
        return {
            "recovery_attempts": self.recovery_attempts,
            "recovery_successes": self.recovery_successes,
            "half_open_requests": self.half_open_requests,
            "max_half_open_requests": self.config.half_open_max_requests,
            "success_threshold": self.config.success_threshold,
            "last_recovery_test": self.last_recovery_test,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class CircuitBreakerAuth:
    """Main circuit breaker for authentication with graceful degradation."""
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.state_changed_time = time.time()
        
        # Components
        self.failure_detector = AuthFailureDetector(self.config)
        self.degradation_manager = GracefulDegradationManager(self.config)
        self.recovery_monitor = RecoveryMonitor(self.config)
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.state_transitions = []
        
        logger.info("AUTH CIRCUIT: Circuit breaker initialized")
    
    async def authenticate(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """
        Authenticate with circuit breaker protection.
        
        Args:
            websocket: WebSocket connection object
            
        Returns:
            AuthPermissivenessResult: Authentication result
        """
        self.total_requests += 1
        current_time = time.time()
        
        # Log circuit breaker state
        logger.debug(f"AUTH CIRCUIT: Processing request - state: {self.state.value}, "
                    f"total: {self.total_requests}")
        
        try:
            # Handle based on circuit breaker state
            if self.state == CircuitBreakerState.CLOSED:
                # Normal operation - try full authentication
                result = await self._authenticate_closed(websocket)
                
            elif self.state == CircuitBreakerState.OPEN:
                # Service failing - check if we can transition to half-open
                if self.recovery_monitor.can_attempt_recovery(current_time, self.state_changed_time):
                    logger.info("AUTH CIRCUIT: Transitioning from OPEN to HALF_OPEN")
                    self._transition_to_state(CircuitBreakerState.HALF_OPEN)
                    result = await self._authenticate_half_open(websocket)
                else:
                    # Use fallback strategies
                    result = await self.degradation_manager.authenticate_with_fallback(websocket)
                
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # Testing recovery - limited requests allowed
                result = await self._authenticate_half_open(websocket)
                
            else:
                raise ValueError(f"Unknown circuit breaker state: {self.state}")
            
            # Process result and update state
            await self._process_authentication_result(result, websocket)
            
            return result
            
        except Exception as e:
            logger.error(f"AUTH CIRCUIT: Exception during authentication: {e}")
            
            # Record failure and check if breaker should trip
            self.failure_detector.record_auth_failure("CIRCUIT_EXCEPTION", str(e))
            self.failed_requests += 1
            
            if self.state == CircuitBreakerState.CLOSED and self.failure_detector.should_trip_breaker():
                self._trip_breaker()
            
            # Return failure result
            return AuthPermissivenessResult(
                success=False,
                level=AuthPermissivenessLevel.EMERGENCY,
                auth_method="circuit_breaker_exception",
                security_warnings=[f"Circuit breaker exception: {str(e)}"],
                audit_info={
                    "circuit_breaker_state": self.state.value,
                    "exception": str(e),
                    "exception_type": type(e).__name__
                }
            )
    
    async def _authenticate_closed(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Authenticate in CLOSED state (normal operation)."""
        try:
            # Try normal authentication
            result = await authenticate_with_permissiveness(websocket)
            
            # Add circuit breaker info
            result.audit_info.update({
                "circuit_breaker_state": "closed",
                "normal_authentication": True
            })
            
            return result
            
        except Exception as e:
            logger.error(f"AUTH CIRCUIT: Closed state authentication failed: {e}")
            raise
    
    async def _authenticate_half_open(self, websocket: WebSocket) -> AuthPermissivenessResult:
        """Authenticate in HALF_OPEN state (testing recovery)."""
        
        # Check if we can make a recovery test
        if not self.recovery_monitor.can_test_recovery():
            logger.info("AUTH CIRCUIT: Half-open request limit reached, using fallback")
            return await self.degradation_manager.authenticate_with_fallback(websocket)
        
        # Record recovery test attempt
        self.recovery_monitor.record_recovery_test()
        
        try:
            # Try normal authentication as recovery test
            result = await authenticate_with_permissiveness(websocket)
            
            # Add circuit breaker info
            result.audit_info.update({
                "circuit_breaker_state": "half_open",
                "recovery_test": True,
                "test_number": self.recovery_monitor.half_open_requests
            })
            
            return result
            
        except Exception as e:
            logger.error(f"AUTH CIRCUIT: Half-open state authentication failed: {e}")
            raise
    
    async def _process_authentication_result(self, result: AuthPermissivenessResult, websocket: WebSocket):
        """Process authentication result and update circuit breaker state."""
        
        if result.success:
            # Record success
            self.successful_requests += 1
            self.failure_detector.record_auth_success()
            
            # Handle state transitions on success
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.recovery_monitor.record_recovery_success()
                
                if self.recovery_monitor.should_close_breaker():
                    logger.info("AUTH CIRCUIT: Recovery successful - closing breaker")
                    self._close_breaker()
                    
        else:
            # Record failure
            self.failed_requests += 1
            error_code = result.audit_info.get("error_code", "UNKNOWN_ERROR")
            error_message = "; ".join(result.security_warnings) if result.security_warnings else "Unknown error"
            
            self.failure_detector.record_auth_failure(error_code, error_message)
            
            # Handle state transitions on failure
            if self.state == CircuitBreakerState.CLOSED:
                if self.failure_detector.should_trip_breaker():
                    self._trip_breaker()
                    
            elif self.state == CircuitBreakerState.HALF_OPEN:
                if self.recovery_monitor.should_reopen_breaker():
                    logger.warning("AUTH CIRCUIT: Recovery failed - reopening breaker")
                    self._reopen_breaker()
    
    def _trip_breaker(self):
        """Trip the circuit breaker to OPEN state."""
        logger.warning("AUTH CIRCUIT: Tripping breaker - too many failures detected")
        self._transition_to_state(CircuitBreakerState.OPEN)
    
    def _close_breaker(self):
        """Close the circuit breaker to normal operation."""
        logger.info("AUTH CIRCUIT: Closing breaker - service recovered")
        self._transition_to_state(CircuitBreakerState.CLOSED)
        self.recovery_monitor.reset_recovery_state()
    
    def _reopen_breaker(self):
        """Reopen the circuit breaker after failed recovery."""
        logger.warning("AUTH CIRCUIT: Reopening breaker - recovery tests failed")
        self._transition_to_state(CircuitBreakerState.OPEN)
        self.recovery_monitor.reset_recovery_state()
    
    def _transition_to_state(self, new_state: CircuitBreakerState):
        """Transition to a new circuit breaker state."""
        old_state = self.state
        self.state = new_state
        self.state_changed_time = time.time()
        
        # Record transition
        transition = {
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": self.state_changed_time,
            "iso_timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.state_transitions.append(transition)
        
        # Keep only recent transitions
        if len(self.state_transitions) > 100:
            self.state_transitions = self.state_transitions[-100:]
        
        logger.info(f"AUTH CIRCUIT: State transition {old_state.value} -> {new_state.value}")
    
    def get_circuit_status(self) -> Dict[str, Any]:
        """Get comprehensive circuit breaker status."""
        current_time = time.time()
        time_in_state = current_time - self.state_changed_time
        success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
        
        return {
            "circuit_breaker": {
                "state": self.state.value,
                "time_in_state_seconds": round(time_in_state, 2),
                "state_changed_time": self.state_changed_time
            },
            "statistics": {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate_percent": round(success_rate, 2)
            },
            "failure_analysis": self.failure_detector.get_failure_analysis(),
            "degradation_stats": self.degradation_manager.get_degradation_stats(),
            "recovery_status": self.recovery_monitor.get_recovery_status(),
            "recent_transitions": self.state_transitions[-10:] if self.state_transitions else [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def force_state(self, state: CircuitBreakerState, reason: str = "manual_override"):
        """Force circuit breaker to specific state (for testing/emergency)."""
        logger.warning(f"AUTH CIRCUIT: Forcing state to {state.value} - reason: {reason}")
        self._transition_to_state(state)
        
        # Add manual transition record
        self.state_transitions[-1]["manual_override"] = True
        self.state_transitions[-1]["reason"] = reason


# Global circuit breaker instance
_circuit_breaker_auth: Optional[CircuitBreakerAuth] = None


def get_circuit_breaker_auth(config: Optional[CircuitBreakerConfig] = None) -> CircuitBreakerAuth:
    """Get the global circuit breaker auth instance."""
    global _circuit_breaker_auth
    if _circuit_breaker_auth is None:
        _circuit_breaker_auth = CircuitBreakerAuth(config)
        logger.info("AUTH CIRCUIT: Global circuit breaker instance created")
    return _circuit_breaker_auth


# Convenience functions
async def authenticate_with_circuit_breaker(websocket: WebSocket) -> AuthPermissivenessResult:
    """
    Authenticate WebSocket connection with circuit breaker protection.
    
    This is the main entry point for circuit breaker protected authentication.
    
    Args:
        websocket: WebSocket connection object
        
    Returns:
        AuthPermissivenessResult: Authentication result with circuit breaker info
    """
    circuit_breaker = get_circuit_breaker_auth()
    return await circuit_breaker.authenticate(websocket)


def get_auth_circuit_status() -> Dict[str, Any]:
    """Get current authentication circuit breaker status."""
    circuit_breaker = get_circuit_breaker_auth()
    return circuit_breaker.get_circuit_status()


def configure_auth_circuit_breaker(config: CircuitBreakerConfig):
    """Configure the global auth circuit breaker."""
    global _circuit_breaker_auth
    _circuit_breaker_auth = CircuitBreakerAuth(config)
    logger.info("AUTH CIRCUIT: Global circuit breaker reconfigured")


# Export public interface
__all__ = [
    "CircuitBreakerState",
    "CircuitBreakerConfig", 
    "AuthFailurePattern",
    "CircuitBreakerAuth",
    "get_circuit_breaker_auth",
    "authenticate_with_circuit_breaker",
    "get_auth_circuit_status",
    "configure_auth_circuit_breaker"
]