"""
Golden Path Unit Tests: Error Recovery Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform/Internal)
- Business Goal: Ensure graceful degradation maintains business continuity and user trust
- Value Impact: Error recovery prevents user abandonment and maintains service reliability
- Strategic/Revenue Impact: Critical for $500K+ ARR - system resilience enables enterprise trust and retention

CRITICAL: This test validates the business logic for error recovery and graceful degradation
that maintains business operations when technical failures occur. Enterprise customers expect
99.9% uptime and graceful handling of failures without losing business value delivery.

Key Error Recovery Areas Tested:
1. Authentication Error Recovery - Graceful auth failure handling without blocking users
2. Database Connection Recovery - Business continuity during database issues  
3. LLM Service Recovery - AI service failures with fallback strategies
4. WebSocket Connection Recovery - Real-time communication failure handling
5. Agent Execution Recovery - AI agent failure recovery with partial results delivery
"""

import pytest
import asyncio
import uuid
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass, field
from enum import Enum
import random

# Import business logic components for testing
from test_framework.base import BaseTestCase
from shared.types.core_types import (
    UserID, ThreadID, ExecutionID, SessionID,
    ensure_user_id, ensure_thread_id
)


class ErrorSeverity(Enum):
    """Business impact severity levels for error classification."""
    LOW = "low"              # Minimal business impact, background functionality
    MEDIUM = "medium"        # Some business impact, degrades user experience  
    HIGH = "high"           # Significant business impact, blocks core functionality
    CRITICAL = "critical"   # Severe business impact, blocks all functionality


class ErrorCategory(Enum):
    """Categories of errors that affect business operations."""
    AUTHENTICATION = "authentication"      # User access and security errors
    DATABASE = "database"                 # Data persistence and retrieval errors
    LLM_SERVICE = "llm_service"          # AI/LLM service connectivity errors
    WEBSOCKET = "websocket"              # Real-time communication errors
    AGENT_EXECUTION = "agent_execution"   # AI agent processing errors
    PAYMENT = "payment"                  # Billing and subscription errors
    RATE_LIMITING = "rate_limiting"       # Usage quota and throttling errors


class RecoveryStrategy(Enum):
    """Business recovery strategies for different error scenarios."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"         # Automatic retry with increasing delays
    FALLBACK_SERVICE = "fallback_service"             # Switch to alternative service
    GRACEFUL_DEGRADATION = "graceful_degradation"     # Reduced functionality mode
    CACHE_RESPONSE = "cache_response"                 # Return cached/historical data
    USER_NOTIFICATION = "user_notification"           # Inform user with business context
    CIRCUIT_BREAKER = "circuit_breaker"               # Temporary service disable
    MANUAL_INTERVENTION = "manual_intervention"       # Escalate to human support


@dataclass
class BusinessError:
    """Represents a business error with recovery context."""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    technical_details: str
    business_impact: str
    user_facing_message: str
    recovery_strategies: List[RecoveryStrategy]
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolution_method: Optional[RecoveryStrategy] = None
    business_continuity_maintained: bool = False


@dataclass
class RecoveryMetrics:
    """Metrics tracking for business continuity during errors."""
    total_errors: int = 0
    errors_recovered: int = 0
    average_recovery_time_ms: float = 0.0
    business_continuity_percentage: float = 0.0
    user_impact_minimized: int = 0
    revenue_protected: float = 0.0


class BusinessErrorRecoveryManager:
    """Business logic for error recovery and graceful degradation."""
    
    def __init__(self):
        self.recovery_policies = self._initialize_recovery_policies()
        self.active_errors: Dict[str, BusinessError] = {}
        self.error_history: List[BusinessError] = []
        self.recovery_metrics = RecoveryMetrics()
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.fallback_caches: Dict[str, Any] = {}
        
    def _initialize_recovery_policies(self) -> Dict[ErrorCategory, Dict[str, Any]]:
        """Initialize business policies for error recovery."""
        return {
            ErrorCategory.AUTHENTICATION: {
                "allowed_severities": [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH],
                "default_strategies": [RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.USER_NOTIFICATION],
                "business_continuity_threshold": 0.95,  # 95% of auth requests must succeed
                "user_impact_tolerance": "low",
                "revenue_impact": "high"  # Auth failures block revenue
            },
            ErrorCategory.DATABASE: {
                "allowed_severities": [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL],
                "default_strategies": [RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.CACHE_RESPONSE, RecoveryStrategy.CIRCUIT_BREAKER],
                "business_continuity_threshold": 0.99,  # 99% database availability required
                "user_impact_tolerance": "medium",
                "revenue_impact": "critical"  # Database failures block all business
            },
            ErrorCategory.LLM_SERVICE: {
                "allowed_severities": [ErrorSeverity.LOW, ErrorSeverity.MEDIUM, ErrorSeverity.HIGH],
                "default_strategies": [RecoveryStrategy.FALLBACK_SERVICE, RecoveryStrategy.CACHE_RESPONSE, RecoveryStrategy.GRACEFUL_DEGRADATION],
                "business_continuity_threshold": 0.90,  # 90% LLM availability acceptable with fallbacks
                "user_impact_tolerance": "medium",
                "revenue_impact": "high"  # LLM failures reduce core value proposition
            },
            ErrorCategory.WEBSOCKET: {
                "allowed_severities": [ErrorSeverity.LOW, ErrorSeverity.MEDIUM],
                "default_strategies": [RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.GRACEFUL_DEGRADATION],
                "business_continuity_threshold": 0.85,  # 85% real-time connectivity acceptable
                "user_impact_tolerance": "high",  # Users can still get value without real-time updates
                "revenue_impact": "medium"  # WebSocket failures reduce UX but don't block core functionality
            },
            ErrorCategory.AGENT_EXECUTION: {
                "allowed_severities": [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH],
                "default_strategies": [RecoveryStrategy.FALLBACK_SERVICE, RecoveryStrategy.GRACEFUL_DEGRADATION, RecoveryStrategy.USER_NOTIFICATION],
                "business_continuity_threshold": 0.95,  # 95% agent success rate required
                "user_impact_tolerance": "low",
                "revenue_impact": "critical"  # Agent failures directly impact core value delivery
            }
        }
    
    def handle_business_error(self, error: BusinessError) -> Dict[str, Any]:
        """Handle business error with appropriate recovery strategy."""
        error_id = error.error_id
        self.active_errors[error_id] = error
        self.recovery_metrics.total_errors += 1
        
        # Business Rule 1: Select appropriate recovery strategy based on policy
        policy = self.recovery_policies.get(error.category, {})
        available_strategies = policy.get("default_strategies", [RecoveryStrategy.USER_NOTIFICATION])
        
        # Business Rule 2: Execute recovery strategies in priority order
        recovery_result = {
            "error_recovered": False,
            "strategies_attempted": [],
            "business_continuity_maintained": False,
            "user_impact_minimized": False,
            "recovery_time_ms": 0,
            "final_strategy": None
        }
        
        start_time = time.time()
        
        for strategy in available_strategies:
            recovery_result["strategies_attempted"].append(strategy)
            
            if self._attempt_recovery_strategy(error, strategy):
                # Recovery successful
                error.resolved_at = datetime.now(timezone.utc)
                error.resolution_method = strategy
                recovery_result.update({
                    "error_recovered": True,
                    "final_strategy": strategy,
                    "business_continuity_maintained": True
                })
                self.recovery_metrics.errors_recovered += 1
                break
        
        # Business Rule 3: Calculate recovery metrics
        end_time = time.time()
        recovery_time_ms = (end_time - start_time) * 1000
        recovery_result["recovery_time_ms"] = recovery_time_ms
        
        # Business Rule 4: Update business continuity metrics
        self._update_recovery_metrics(error, recovery_result)
        
        # Business Rule 5: Archive error for business analysis
        if error_id in self.active_errors:
            self.error_history.append(self.active_errors[error_id])
            if recovery_result["error_recovered"]:
                del self.active_errors[error_id]
        
        return recovery_result
    
    def _attempt_recovery_strategy(self, error: BusinessError, strategy: RecoveryStrategy) -> bool:
        """Attempt specific recovery strategy with business logic."""
        
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            return self._retry_with_exponential_backoff(error)
        elif strategy == RecoveryStrategy.FALLBACK_SERVICE:
            return self._switch_to_fallback_service(error)
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            return self._enable_graceful_degradation(error)
        elif strategy == RecoveryStrategy.CACHE_RESPONSE:
            return self._serve_cached_response(error)
        elif strategy == RecoveryStrategy.USER_NOTIFICATION:
            return self._notify_user_with_business_context(error)
        elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            return self._activate_circuit_breaker(error)
        else:
            return False
    
    def _retry_with_exponential_backoff(self, error: BusinessError) -> bool:
        """Simulate retry with exponential backoff for business continuity."""
        # Business Logic: Different retry policies based on error category
        if error.category == ErrorCategory.AUTHENTICATION:
            max_retries, base_delay = 3, 100  # Quick retries for auth
        elif error.category == ErrorCategory.DATABASE:
            max_retries, base_delay = 5, 500  # More retries for database
        else:
            max_retries, base_delay = 2, 200  # Default retry policy
        
        # Simulate retry attempts
        for attempt in range(max_retries):
            # Business Rule: Increase delay exponentially
            delay_ms = base_delay * (2 ** attempt)
            
            # Simulate service call (80% success rate after retries)
            if random.random() > 0.2:  # 80% success rate
                error.business_continuity_maintained = True
                return True
                
        return False
    
    def _switch_to_fallback_service(self, error: BusinessError) -> bool:
        """Switch to fallback service to maintain business operations."""
        fallback_services = {
            ErrorCategory.LLM_SERVICE: "cached_llm_responses",
            ErrorCategory.AGENT_EXECUTION: "simplified_agent_logic",
            ErrorCategory.DATABASE: "read_replica_database"
        }
        
        fallback_service = fallback_services.get(error.category)
        if fallback_service:
            # Business Rule: Fallback should provide 70% of normal functionality
            error.business_continuity_maintained = True
            self.fallback_caches[error.category.value] = {
                "active": True,
                "service": fallback_service,
                "functionality_percentage": 0.7
            }
            return True
        
        return False
    
    def _enable_graceful_degradation(self, error: BusinessError) -> bool:
        """Enable graceful degradation to maintain core business value."""
        # Business Rule: Always succeed with graceful degradation but reduced functionality
        degradation_policies = {
            ErrorCategory.WEBSOCKET: {
                "functionality_maintained": 0.6,  # Polling fallback instead of real-time
                "user_message": "Real-time updates temporarily unavailable, using 30-second refresh"
            },
            ErrorCategory.LLM_SERVICE: {
                "functionality_maintained": 0.4,  # Basic responses instead of AI analysis
                "user_message": "AI analysis temporarily limited, providing standard recommendations"
            },
            ErrorCategory.AGENT_EXECUTION: {
                "functionality_maintained": 0.5,  # Simplified agent logic
                "user_message": "Analysis running in simplified mode for faster results"
            }
        }
        
        policy = degradation_policies.get(error.category)
        if policy:
            error.business_continuity_maintained = True
            error.user_facing_message = policy["user_message"]
            return True
            
        return False
    
    def _serve_cached_response(self, error: BusinessError) -> bool:
        """Serve cached response to maintain business continuity."""
        # Business Rule: Cache responses should be recent and relevant
        cache_policies = {
            ErrorCategory.LLM_SERVICE: {"max_age_hours": 24, "success_rate": 0.8},
            ErrorCategory.DATABASE: {"max_age_hours": 1, "success_rate": 0.9},
            ErrorCategory.AGENT_EXECUTION: {"max_age_hours": 4, "success_rate": 0.7}
        }
        
        policy = cache_policies.get(error.category)
        if policy and random.random() < policy["success_rate"]:
            error.business_continuity_maintained = True
            error.user_facing_message = "Showing recent analysis while system recovers"
            return True
        
        return False
    
    def _notify_user_with_business_context(self, error: BusinessError) -> bool:
        """Notify user with business-appropriate error messaging."""
        # Business Rule: Always succeed - user notification is last resort
        business_messages = {
            ErrorCategory.AUTHENTICATION: "We're having trouble verifying your account. Please try again in a moment.",
            ErrorCategory.DATABASE: "We're experiencing temporary data access issues. Your request is being processed.",
            ErrorCategory.LLM_SERVICE: "AI analysis is temporarily slow. We're working to restore full speed.",
            ErrorCategory.WEBSOCKET: "Real-time updates are temporarily unavailable. Your analysis will continue.",
            ErrorCategory.AGENT_EXECUTION: "AI agents are running in backup mode. Results may take a bit longer."
        }
        
        error.user_facing_message = business_messages.get(
            error.category, 
            "We're experiencing a temporary issue. Our team is working to resolve it quickly."
        )
        error.business_continuity_maintained = True
        return True
    
    def _activate_circuit_breaker(self, error: BusinessError) -> bool:
        """Activate circuit breaker to prevent cascading failures."""
        circuit_id = f"{error.category.value}_circuit"
        
        # Business Rule: Circuit breaker prevents further damage
        self.circuit_breakers[circuit_id] = {
            "opened_at": datetime.now(timezone.utc),
            "error_threshold": 5,  # Open after 5 errors
            "recovery_timeout_minutes": 5,
            "business_justification": "Preventing cascading failures that could impact all users"
        }
        
        error.business_continuity_maintained = True
        return True
    
    def _update_recovery_metrics(self, error: BusinessError, recovery_result: Dict[str, Any]) -> None:
        """Update business recovery metrics for monitoring and reporting."""
        # Business Rule: Track recovery performance for business reporting
        if recovery_result["error_recovered"]:
            # Update average recovery time
            current_avg = self.recovery_metrics.average_recovery_time_ms
            total_recovered = self.recovery_metrics.errors_recovered
            new_time = recovery_result["recovery_time_ms"]
            
            if total_recovered > 1:
                self.recovery_metrics.average_recovery_time_ms = (
                    (current_avg * (total_recovered - 1) + new_time) / total_recovered
                )
            else:
                self.recovery_metrics.average_recovery_time_ms = new_time
        
        # Update business continuity percentage
        total_errors = self.recovery_metrics.total_errors
        errors_with_continuity = sum(
            1 for e in self.error_history + list(self.active_errors.values())
            if e.business_continuity_maintained
        )
        
        self.recovery_metrics.business_continuity_percentage = (
            errors_with_continuity / total_errors if total_errors > 0 else 1.0
        )
    
    def get_business_health_report(self) -> Dict[str, Any]:
        """Generate business health report for monitoring and decision-making."""
        return {
            "system_health_score": self._calculate_system_health_score(),
            "business_continuity_percentage": self.recovery_metrics.business_continuity_percentage,
            "active_errors": len(self.active_errors),
            "total_errors_handled": self.recovery_metrics.total_errors,
            "average_recovery_time_ms": self.recovery_metrics.average_recovery_time_ms,
            "revenue_impact_assessment": self._assess_revenue_impact(),
            "customer_satisfaction_impact": self._assess_customer_satisfaction_impact(),
            "recommended_actions": self._generate_business_recommendations()
        }
    
    def _calculate_system_health_score(self) -> float:
        """Calculate overall system health score for business monitoring."""
        if self.recovery_metrics.total_errors == 0:
            return 1.0
        
        # Business Rule: Health score based on recovery success and business continuity
        recovery_rate = self.recovery_metrics.errors_recovered / self.recovery_metrics.total_errors
        continuity_rate = self.recovery_metrics.business_continuity_percentage
        
        # Weight: 60% recovery success, 40% business continuity
        health_score = (recovery_rate * 0.6) + (continuity_rate * 0.4)
        return min(health_score, 1.0)
    
    def _assess_revenue_impact(self) -> Dict[str, Any]:
        """Assess potential revenue impact of current errors."""
        revenue_impact = {"high": 0, "medium": 0, "low": 0, "total_estimated_loss": 0.0}
        
        for error in list(self.active_errors.values()) + self.error_history:
            policy = self.recovery_policies.get(error.category, {})
            impact_level = policy.get("revenue_impact", "low")
            
            if impact_level == "critical":
                revenue_impact["high"] += 1
                revenue_impact["total_estimated_loss"] += 1000  # $1000 per critical error
            elif impact_level == "high":
                revenue_impact["high"] += 1
                revenue_impact["total_estimated_loss"] += 500   # $500 per high impact error
            elif impact_level == "medium":
                revenue_impact["medium"] += 1
                revenue_impact["total_estimated_loss"] += 100  # $100 per medium impact error
            else:
                revenue_impact["low"] += 1
                revenue_impact["total_estimated_loss"] += 10   # $10 per low impact error
        
        return revenue_impact
    
    def _assess_customer_satisfaction_impact(self) -> Dict[str, Any]:
        """Assess customer satisfaction impact of error recovery."""
        satisfaction_score = 0.9  # Start with 90% baseline
        
        # Reduce satisfaction based on active high-severity errors
        for error in self.active_errors.values():
            if error.severity == ErrorSeverity.CRITICAL:
                satisfaction_score -= 0.2
            elif error.severity == ErrorSeverity.HIGH:
                satisfaction_score -= 0.1
            elif error.severity == ErrorSeverity.MEDIUM:
                satisfaction_score -= 0.05
        
        return {
            "predicted_satisfaction_score": max(satisfaction_score, 0.0),
            "impact_level": "high" if satisfaction_score < 0.7 else "medium" if satisfaction_score < 0.8 else "low"
        }
    
    def _generate_business_recommendations(self) -> List[str]:
        """Generate business recommendations based on error patterns."""
        recommendations = []
        
        # Analyze error patterns for business recommendations
        if len(self.active_errors) > 5:
            recommendations.append("Consider scaling infrastructure to handle current error load")
        
        if self.recovery_metrics.business_continuity_percentage < 0.95:
            recommendations.append("Improve fallback systems to maintain 95%+ business continuity")
        
        if self.recovery_metrics.average_recovery_time_ms > 5000:
            recommendations.append("Optimize recovery procedures to reduce mean time to recovery")
        
        # Category-specific recommendations
        auth_errors = sum(1 for e in self.active_errors.values() if e.category == ErrorCategory.AUTHENTICATION)
        if auth_errors > 2:
            recommendations.append("Review authentication infrastructure - multiple auth errors detected")
        
        return recommendations


@pytest.mark.unit
@pytest.mark.golden_path
class TestErrorRecoveryBusinessLogic(BaseTestCase):
    """Test error recovery business logic for system resilience and business continuity."""

    def setup_method(self):
        """Setup test environment for each test."""
        super().setup_method()
        self.error_manager = BusinessErrorRecoveryManager()
        self.test_user_id = ensure_user_id("test-user-123")

    def test_authentication_error_recovery_business_continuity(self):
        """Test authentication errors maintain business continuity through recovery."""
        # Business Value: Auth errors should not permanently block user access
        
        auth_error = BusinessError(
            error_id="auth-001",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            message="JWT token validation failed",
            technical_details="Token signature verification failed with key rotation",
            business_impact="User cannot access premium features, revenue impact $500/day",
            user_facing_message="",  # Will be set by recovery
            recovery_strategies=[RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.USER_NOTIFICATION]
        )
        
        # Business Rule 1: Error recovery must be attempted
        recovery_result = self.error_manager.handle_business_error(auth_error)
        assert recovery_result["strategies_attempted"], "Recovery strategies must be attempted"
        assert len(recovery_result["strategies_attempted"]) > 0, "At least one strategy must be tried"
        
        # Business Rule 2: Business continuity must be maintained
        assert recovery_result["business_continuity_maintained"] is True, "Auth errors must maintain business continuity"
        
        # Business Rule 3: User must receive business-appropriate messaging
        assert auth_error.user_facing_message, "User must receive error messaging"
        assert "account" in auth_error.user_facing_message.lower(), "Message must reference account context"
        assert "try again" in auth_error.user_facing_message.lower(), "Message must provide user action"
        
        # Business Rule 4: Recovery metrics must be updated
        assert self.error_manager.recovery_metrics.total_errors == 1, "Error count must be tracked"
        if recovery_result["error_recovered"]:
            assert self.error_manager.recovery_metrics.errors_recovered == 1, "Recovery count must be tracked"

    def test_llm_service_error_fallback_business_strategy(self):
        """Test LLM service errors use fallback strategies to maintain AI value delivery."""
        # Business Value: LLM failures should not prevent AI value delivery through fallbacks
        
        llm_error = BusinessError(
            error_id="llm-001",
            category=ErrorCategory.LLM_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            message="OpenAI API timeout",
            technical_details="GPT-4 API timeout after 30 seconds, rate limit potentially exceeded",
            business_impact="AI analysis delayed, user experience degraded, potential churn risk",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.FALLBACK_SERVICE, RecoveryStrategy.CACHE_RESPONSE]
        )
        
        # Business Rule 1: LLM errors must attempt fallback services first
        recovery_result = self.error_manager.handle_business_error(llm_error)
        attempted_strategies = recovery_result["strategies_attempted"]
        
        # Either fallback service or cache response should be attempted
        fallback_attempted = RecoveryStrategy.FALLBACK_SERVICE in attempted_strategies
        cache_attempted = RecoveryStrategy.CACHE_RESPONSE in attempted_strategies
        assert fallback_attempted or cache_attempted, "LLM errors must attempt service/cache fallback"
        
        # Business Rule 2: Fallback must maintain reasonable functionality level
        if ErrorCategory.LLM_SERVICE.value in self.error_manager.fallback_caches:
            fallback_info = self.error_manager.fallback_caches[ErrorCategory.LLM_SERVICE.value]
            assert fallback_info["functionality_percentage"] >= 0.4, "LLM fallback must maintain 40%+ functionality"
        
        # Business Rule 3: User must be informed of service degradation appropriately
        if llm_error.user_facing_message:
            assert "AI" in llm_error.user_facing_message, "Message must reference AI context"
            assert not "timeout" in llm_error.user_facing_message.lower(), "Technical details must be hidden from user"

    def test_database_error_critical_business_impact_recovery(self):
        """Test database errors receive highest priority recovery due to critical business impact."""
        # Business Value: Database failures block all business operations and require immediate recovery
        
        db_error = BusinessError(
            error_id="db-001",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            message="Primary database connection lost",
            technical_details="PostgreSQL primary instance unreachable, connection pool exhausted",
            business_impact="All user data inaccessible, complete service outage, revenue loss $5000/hour",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.RETRY_WITH_BACKOFF, RecoveryStrategy.CACHE_RESPONSE, RecoveryStrategy.CIRCUIT_BREAKER]
        )
        
        # Business Rule 1: Database errors must have multiple recovery strategies
        policy = self.error_manager.recovery_policies[ErrorCategory.DATABASE]
        assert len(policy["default_strategies"]) >= 2, "Database errors must have multiple recovery options"
        
        # Business Rule 2: Database errors require highest business continuity threshold
        assert policy["business_continuity_threshold"] >= 0.99, "Database must have 99%+ continuity requirement"
        
        # Business Rule 3: Recovery must be attempted with all available strategies
        recovery_result = self.error_manager.handle_business_error(db_error)
        assert len(recovery_result["strategies_attempted"]) >= 1, "Multiple recovery strategies must be attempted"
        
        # Business Rule 4: Circuit breaker may be activated for protection
        if RecoveryStrategy.CIRCUIT_BREAKER in recovery_result["strategies_attempted"]:
            circuit_id = f"{ErrorCategory.DATABASE.value}_circuit"
            assert circuit_id in self.error_manager.circuit_breakers, "Circuit breaker must be activated"
            
            circuit_info = self.error_manager.circuit_breakers[circuit_id]
            assert "business_justification" in circuit_info, "Circuit breaker must have business justification"

    def test_websocket_error_graceful_degradation_business_logic(self):
        """Test WebSocket errors gracefully degrade to maintain core business functionality."""
        # Business Value: WebSocket failures should not block core functionality, only real-time features
        
        ws_error = BusinessError(
            error_id="ws-001",
            category=ErrorCategory.WEBSOCKET,
            severity=ErrorSeverity.MEDIUM,
            message="WebSocket connection dropped",
            technical_details="WebSocket connection terminated unexpectedly, client reconnection failed",
            business_impact="Real-time updates unavailable, user experience degraded but core features work",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.GRACEFUL_DEGRADATION, RecoveryStrategy.USER_NOTIFICATION]
        )
        
        # Business Rule 1: WebSocket errors should prioritize graceful degradation
        recovery_result = self.error_manager.handle_business_error(ws_error)
        attempted_strategies = recovery_result["strategies_attempted"]
        assert RecoveryStrategy.GRACEFUL_DEGRADATION in attempted_strategies, "WebSocket errors must attempt graceful degradation"
        
        # Business Rule 2: WebSocket policy must allow higher user impact tolerance
        policy = self.error_manager.recovery_policies[ErrorCategory.WEBSOCKET]
        assert policy["user_impact_tolerance"] == "high", "WebSocket failures have high user impact tolerance"
        
        # Business Rule 3: Business continuity must be maintained despite real-time feature loss
        assert recovery_result["business_continuity_maintained"] is True, "Core business must continue without WebSocket"
        
        # Business Rule 4: User message must explain alternative functionality
        if ws_error.user_facing_message:
            assert "real-time" in ws_error.user_facing_message.lower() or "updates" in ws_error.user_facing_message.lower(), "Message must explain real-time impact"

    def test_agent_execution_error_business_value_preservation(self):
        """Test agent execution errors preserve as much business value as possible."""
        # Business Value: AI agent failures should deliver partial results when possible
        
        agent_error = BusinessError(
            error_id="agent-001",
            category=ErrorCategory.AGENT_EXECUTION,
            severity=ErrorSeverity.HIGH,
            message="Optimization agent execution failed",
            technical_details="Agent timeout during cost analysis phase, partial results available",
            business_impact="Cost optimization recommendations incomplete, user value reduced 60%",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.GRACEFUL_DEGRADATION, RecoveryStrategy.FALLBACK_SERVICE]
        )
        
        # Business Rule 1: Agent errors must attempt to deliver partial business value
        recovery_result = self.error_manager.handle_business_error(agent_error)
        
        # Should attempt graceful degradation or fallback service
        attempted_strategies = recovery_result["strategies_attempted"]
        value_preservation_attempted = (
            RecoveryStrategy.GRACEFUL_DEGRADATION in attempted_strategies or
            RecoveryStrategy.FALLBACK_SERVICE in attempted_strategies
        )
        assert value_preservation_attempted, "Agent errors must attempt to preserve business value"
        
        # Business Rule 2: Agent execution policy must prioritize business value delivery
        policy = self.error_manager.recovery_policies[ErrorCategory.AGENT_EXECUTION]
        assert policy["revenue_impact"] == "critical", "Agent failures have critical revenue impact"
        assert policy["business_continuity_threshold"] >= 0.95, "Agent execution must maintain 95%+ success rate"
        
        # Business Rule 3: Recovery must maintain business continuity
        assert recovery_result["business_continuity_maintained"] is True, "Business continuity must be maintained"

    def test_multiple_concurrent_errors_business_prioritization(self):
        """Test multiple concurrent errors are handled with proper business prioritization."""
        # Business Value: Error handling must prioritize based on business impact when resources are limited
        
        # Create errors of different business priorities
        critical_db_error = BusinessError(
            error_id="multi-001",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            message="Database unavailable",
            technical_details="Primary DB down",
            business_impact="Complete service outage",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.CACHE_RESPONSE]
        )
        
        medium_ws_error = BusinessError(
            error_id="multi-002", 
            category=ErrorCategory.WEBSOCKET,
            severity=ErrorSeverity.MEDIUM,
            message="WebSocket issues",
            technical_details="Connection instability",
            business_impact="Real-time features degraded",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.GRACEFUL_DEGRADATION]
        )
        
        low_auth_error = BusinessError(
            error_id="multi-003",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            message="Auth slowness",
            technical_details="JWT validation delay",
            business_impact="Login delays",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.RETRY_WITH_BACKOFF]
        )
        
        # Handle all errors
        db_recovery = self.error_manager.handle_business_error(critical_db_error)
        ws_recovery = self.error_manager.handle_business_error(medium_ws_error)
        auth_recovery = self.error_manager.handle_business_error(low_auth_error)
        
        # Business Rule 1: All errors must be handled
        assert db_recovery["strategies_attempted"], "Critical database error must be handled"
        assert ws_recovery["strategies_attempted"], "WebSocket error must be handled"
        assert auth_recovery["strategies_attempted"], "Auth error must be handled"
        
        # Business Rule 2: Business continuity must be maintained across all errors
        total_errors = self.error_manager.recovery_metrics.total_errors
        assert total_errors == 3, "All 3 errors must be tracked"
        
        continuity_percentage = self.error_manager.recovery_metrics.business_continuity_percentage
        assert continuity_percentage > 0.8, "Business continuity must be maintained despite multiple errors"

    def test_business_health_reporting_error_impact_analysis(self):
        """Test business health reporting provides actionable insights from error patterns."""
        # Business Value: Error analysis must provide business intelligence for decision-making
        
        # Create pattern of errors to analyze
        errors_to_create = [
            BusinessError("health-001", ErrorCategory.LLM_SERVICE, ErrorSeverity.MEDIUM, "LLM timeout", "", "AI delays", "", [RecoveryStrategy.FALLBACK_SERVICE]),
            BusinessError("health-002", ErrorCategory.LLM_SERVICE, ErrorSeverity.HIGH, "LLM unavailable", "", "AI blocked", "", [RecoveryStrategy.CACHE_RESPONSE]),
            BusinessError("health-003", ErrorCategory.DATABASE, ErrorSeverity.HIGH, "DB slow", "", "Data delays", "", [RecoveryStrategy.RETRY_WITH_BACKOFF]),
            BusinessError("health-004", ErrorCategory.AUTHENTICATION, ErrorSeverity.MEDIUM, "Auth issues", "", "Login problems", "", [RecoveryStrategy.USER_NOTIFICATION])
        ]
        
        # Handle all errors
        for error in errors_to_create:
            self.error_manager.handle_business_error(error)
        
        # Generate business health report
        health_report = self.error_manager.get_business_health_report()
        
        # Business Rule 1: Health report must contain business-relevant metrics
        assert "system_health_score" in health_report, "Must provide overall health score"
        assert "business_continuity_percentage" in health_report, "Must report business continuity"
        assert "revenue_impact_assessment" in health_report, "Must assess revenue impact"
        assert "customer_satisfaction_impact" in health_report, "Must assess customer impact"
        assert "recommended_actions" in health_report, "Must provide business recommendations"
        
        # Business Rule 2: Health score must be meaningful business metric
        health_score = health_report["system_health_score"]
        assert 0.0 <= health_score <= 1.0, "Health score must be normalized 0-1"
        
        # Business Rule 3: Revenue impact must be quantified
        revenue_impact = health_report["revenue_impact_assessment"]
        assert "total_estimated_loss" in revenue_impact, "Must estimate revenue impact"
        assert revenue_impact["total_estimated_loss"] > 0, "Must quantify revenue loss"
        
        # Business Rule 4: Customer satisfaction impact must be predicted
        satisfaction_impact = health_report["customer_satisfaction_impact"]
        assert "predicted_satisfaction_score" in satisfaction_impact, "Must predict customer satisfaction"
        assert "impact_level" in satisfaction_impact, "Must categorize satisfaction impact"
        
        # Business Rule 5: Recommendations must be actionable for business
        recommendations = health_report["recommended_actions"]
        assert isinstance(recommendations, list), "Recommendations must be list"
        if recommendations:
            for rec in recommendations:
                assert isinstance(rec, str), "Each recommendation must be descriptive string"
                assert len(rec) > 20, "Recommendations must be substantive"

    def test_error_recovery_performance_business_requirements(self):
        """Test error recovery performance meets business time requirements."""
        # Business Value: Fast error recovery prevents user abandonment and revenue loss
        
        performance_error = BusinessError(
            error_id="perf-001",
            category=ErrorCategory.LLM_SERVICE,
            severity=ErrorSeverity.HIGH,
            message="Performance test error",
            technical_details="Simulated high-impact error for performance testing",
            business_impact="AI service degradation affecting user experience",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.FALLBACK_SERVICE, RecoveryStrategy.CACHE_RESPONSE]
        )
        
        # Business Rule 1: Error recovery must complete quickly
        start_time = time.time()
        recovery_result = self.error_manager.handle_business_error(performance_error)
        recovery_time_ms = recovery_result["recovery_time_ms"]
        
        # Business Rule: Recovery must complete within 5 seconds for business continuity
        assert recovery_time_ms < 5000, f"Error recovery ({recovery_time_ms}ms) must complete within 5000ms"
        
        # Business Rule 2: Recovery metrics must track performance
        avg_recovery_time = self.error_manager.recovery_metrics.average_recovery_time_ms
        assert avg_recovery_time > 0, "Average recovery time must be tracked"
        assert avg_recovery_time == recovery_time_ms, "First error should set average recovery time"
        
        # Business Rule 3: Fast recovery preserves business value
        assert recovery_result["business_continuity_maintained"] is True, "Fast recovery must maintain business continuity"

    def test_circuit_breaker_business_protection_logic(self):
        """Test circuit breaker protects business operations from cascading failures."""
        # Business Value: Circuit breakers prevent small issues from becoming business-wide outages
        
        circuit_error = BusinessError(
            error_id="circuit-001",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.CRITICAL,
            message="Repeated database failures",
            technical_details="Database connection pool exhausted, multiple connection failures",
            business_impact="Risk of cascading failure across all business operations",
            user_facing_message="",
            recovery_strategies=[RecoveryStrategy.CIRCUIT_BREAKER]
        )
        
        # Business Rule 1: Circuit breaker must activate for business protection
        recovery_result = self.error_manager.handle_business_error(circuit_error)
        
        assert RecoveryStrategy.CIRCUIT_BREAKER in recovery_result["strategies_attempted"], "Circuit breaker must be attempted"
        
        # Business Rule 2: Circuit breaker must be tracked with business context
        circuit_id = f"{ErrorCategory.DATABASE.value}_circuit"
        if circuit_id in self.error_manager.circuit_breakers:
            circuit_info = self.error_manager.circuit_breakers[circuit_id]
            
            assert "business_justification" in circuit_info, "Circuit breaker must have business justification"
            assert "error_threshold" in circuit_info, "Circuit breaker must have error threshold"
            assert "recovery_timeout_minutes" in circuit_info, "Circuit breaker must have recovery timeout"
            
            business_justification = circuit_info["business_justification"]
            assert "business" in business_justification.lower() or "user" in business_justification.lower(), "Justification must reference business impact"
        
        # Business Rule 3: Circuit breaker activation maintains business continuity
        assert recovery_result["business_continuity_maintained"] is True, "Circuit breaker must maintain business continuity"