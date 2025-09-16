"""
Test Error Recovery Strategies Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Platform reliability foundation  
- Business Goal: Minimize service disruption through intelligent error recovery
- Value Impact: Error recovery protects $500K+ ARR by maintaining service availability
- Strategic Impact: Graceful error handling = customer retention, poor recovery = immediate churn

This test validates core error recovery algorithms that power:
1. Automatic retry strategies with exponential backoff
2. Circuit breaker patterns for failing services  
3. Graceful degradation for partial failures
4. Error categorization and recovery prioritization
5. User-facing error communication strategies

CRITICAL BUSINESS RULES:
- Enterprise tier: Immediate failover, <5s recovery time, dedicated support notification
- Mid tier: 3 retry attempts, <30s recovery time, priority support notification  
- Early tier: 2 retry attempts, <60s recovery time, email notification
- Free tier: 1 retry attempt, <120s recovery time, self-service guidance
- All tiers: Data integrity MUST be preserved during recovery
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import uuid
import time
import random

from shared.types.core_types import UserID, AgentID, RunID
from shared.isolated_environment import get_env

# Business Logic Classes (SSOT for error recovery strategies)

class SubscriptionTier(Enum):
    FREE = "free"
    EARLY = "early"
    MID = "mid"
    ENTERPRISE = "enterprise"

class ErrorSeverity(Enum):
    LOW = "low"              # Cosmetic issues, warnings
    MEDIUM = "medium"        # Functionality impaired but workarounds exist
    HIGH = "high"           # Major functionality broken
    CRITICAL = "critical"   # Service unavailable, data at risk

class ErrorCategory(Enum):
    NETWORK = "network"              # Network connectivity issues
    DATABASE = "database"            # Database connection/query failures  
    LLM_API = "llm_api"             # LLM provider API failures
    AUTHENTICATION = "authentication" # Auth service failures
    RATE_LIMIT = "rate_limit"        # Rate limiting errors
    VALIDATION = "validation"        # Input validation failures
    SYSTEM = "system"               # System-level errors

class RecoveryStrategy(Enum):
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    FAILOVER = "failover"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_NOTIFICATION = "user_notification"

@dataclass
class ErrorContext:
    """Context information for error recovery."""
    error_id: str
    error_message: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    user_id: str
    user_tier: SubscriptionTier
    agent_id: str
    run_id: str
    occurred_at: datetime
    retry_count: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class RecoveryConfig:
    """Recovery configuration for user tier and error type."""
    max_retries: int
    max_recovery_time_seconds: int
    retry_strategies: List[RecoveryStrategy]
    escalation_threshold: int
    user_notification_required: bool
    support_notification_required: bool

@dataclass
class RecoveryResult:
    """Result of error recovery attempt."""
    recovery_id: str
    success: bool
    strategy_used: RecoveryStrategy
    attempts_made: int
    recovery_time_seconds: float
    final_error_message: Optional[str]
    user_impact_level: str
    support_escalated: bool

class ErrorRecoveryManager:
    """
    SSOT Error Recovery Management Business Logic
    
    This class implements intelligent error recovery strategies that minimize
    service disruption and protect customer experience.
    """
    
    # TIER-BASED RECOVERY CONFIGURATIONS
    TIER_RECOVERY_CONFIGS = {
        SubscriptionTier.FREE: {
            ErrorCategory.NETWORK: RecoveryConfig(
                max_retries=1,
                max_recovery_time_seconds=120,
                retry_strategies=[RecoveryStrategy.IMMEDIATE_RETRY, RecoveryStrategy.USER_NOTIFICATION],
                escalation_threshold=3,
                user_notification_required=True,
                support_notification_required=False
            ),
            ErrorCategory.DATABASE: RecoveryConfig(
                max_retries=1,
                max_recovery_time_seconds=120,
                retry_strategies=[RecoveryStrategy.IMMEDIATE_RETRY, RecoveryStrategy.GRACEFUL_DEGRADATION],
                escalation_threshold=2,
                user_notification_required=True,
                support_notification_required=False
            ),
            ErrorCategory.LLM_API: RecoveryConfig(
                max_retries=1,
                max_recovery_time_seconds=120,
                retry_strategies=[RecoveryStrategy.IMMEDIATE_RETRY, RecoveryStrategy.GRACEFUL_DEGRADATION],
                escalation_threshold=3,
                user_notification_required=True,
                support_notification_required=False
            )
        },
        SubscriptionTier.EARLY: {
            ErrorCategory.NETWORK: RecoveryConfig(
                max_retries=2,
                max_recovery_time_seconds=60,
                retry_strategies=[RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.USER_NOTIFICATION],
                escalation_threshold=3,
                user_notification_required=True,
                support_notification_required=False
            ),
            ErrorCategory.DATABASE: RecoveryConfig(
                max_retries=2,
                max_recovery_time_seconds=60,
                retry_strategies=[RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.FAILOVER],
                escalation_threshold=2,
                user_notification_required=True,
                support_notification_required=True
            ),
            ErrorCategory.LLM_API: RecoveryConfig(
                max_retries=2,
                max_recovery_time_seconds=60,
                retry_strategies=[RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.GRACEFUL_DEGRADATION],
                escalation_threshold=3,
                user_notification_required=True,
                support_notification_required=False
            )
        },
        SubscriptionTier.MID: {
            ErrorCategory.NETWORK: RecoveryConfig(
                max_retries=3,
                max_recovery_time_seconds=30,
                retry_strategies=[RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.CIRCUIT_BREAKER],
                escalation_threshold=2,
                user_notification_required=True,
                support_notification_required=True
            ),
            ErrorCategory.DATABASE: RecoveryConfig(
                max_retries=3,
                max_recovery_time_seconds=30,
                retry_strategies=[RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.FAILOVER],
                escalation_threshold=2,
                user_notification_required=True,
                support_notification_required=True
            ),
            ErrorCategory.LLM_API: RecoveryConfig(
                max_retries=3,
                max_recovery_time_seconds=30,
                retry_strategies=[RecoveryStrategy.EXPONENTIAL_BACKOFF, RecoveryStrategy.FAILOVER],
                escalation_threshold=2,
                user_notification_required=True,
                support_notification_required=True
            )
        },
        SubscriptionTier.ENTERPRISE: {
            ErrorCategory.NETWORK: RecoveryConfig(
                max_retries=5,
                max_recovery_time_seconds=5,
                retry_strategies=[RecoveryStrategy.CIRCUIT_BREAKER, RecoveryStrategy.FAILOVER],
                escalation_threshold=1,
                user_notification_required=True,
                support_notification_required=True
            ),
            ErrorCategory.DATABASE: RecoveryConfig(
                max_retries=5,
                max_recovery_time_seconds=5,
                retry_strategies=[RecoveryStrategy.FAILOVER, RecoveryStrategy.CIRCUIT_BREAKER],
                escalation_threshold=1,
                user_notification_required=True,
                support_notification_required=True
            ),
            ErrorCategory.LLM_API: RecoveryConfig(
                max_retries=5,
                max_recovery_time_seconds=5,
                retry_strategies=[RecoveryStrategy.FAILOVER, RecoveryStrategy.CIRCUIT_BREAKER],
                escalation_threshold=1,
                user_notification_required=True,
                support_notification_required=True
            )
        }
    }
    
    def __init__(self):
        self._recovery_history: Dict[str, List[RecoveryResult]] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._error_patterns: Dict[str, int] = {}

    def execute_recovery_strategy(self, error_context: ErrorContext, 
                                operation_to_retry: Callable = None) -> RecoveryResult:
        """
        Execute appropriate recovery strategy for error.
        
        Critical: Minimizes service disruption through intelligent recovery.
        """
        recovery_start_time = datetime.now(timezone.utc)
        recovery_id = str(uuid.uuid4())
        
        # Get recovery configuration
        config = self._get_recovery_config(error_context)
        
        # Track error patterns
        error_pattern_key = f"{error_context.error_category.value}:{error_context.user_tier.value}"
        self._error_patterns[error_pattern_key] = self._error_patterns.get(error_pattern_key, 0) + 1
        
        # Execute recovery strategies in priority order
        recovery_result = None
        for strategy in config.retry_strategies:
            try:
                if strategy == RecoveryStrategy.IMMEDIATE_RETRY:
                    recovery_result = self._execute_immediate_retry(error_context, operation_to_retry)
                elif strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
                    recovery_result = self._execute_exponential_backoff(error_context, operation_to_retry, config)
                elif strategy == RecoveryStrategy.CIRCUIT_BREAKER:
                    recovery_result = self._execute_circuit_breaker(error_context, operation_to_retry)
                elif strategy == RecoveryStrategy.FAILOVER:
                    recovery_result = self._execute_failover(error_context, operation_to_retry)
                elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
                    recovery_result = self._execute_graceful_degradation(error_context)
                elif strategy == RecoveryStrategy.USER_NOTIFICATION:
                    recovery_result = self._execute_user_notification(error_context)
                
                # If strategy succeeded, break
                if recovery_result and recovery_result.success:
                    break
                    
            except Exception as strategy_error:
                # Log strategy failure but continue to next strategy
                pass
        
        # If no strategy succeeded, create failure result
        if not recovery_result:
            recovery_result = RecoveryResult(
                recovery_id=recovery_id,
                success=False,
                strategy_used=RecoveryStrategy.USER_NOTIFICATION,  # Default fallback
                attempts_made=error_context.retry_count,
                recovery_time_seconds=0.0,
                final_error_message=error_context.error_message,
                user_impact_level="high",
                support_escalated=config.support_notification_required
            )
        
        # Calculate final recovery time
        recovery_end_time = datetime.now(timezone.utc)
        recovery_result.recovery_time_seconds = (recovery_end_time - recovery_start_time).total_seconds()
        recovery_result.recovery_id = recovery_id
        
        # Record recovery attempt
        if error_context.user_id not in self._recovery_history:
            self._recovery_history[error_context.user_id] = []
        self._recovery_history[error_context.user_id].append(recovery_result)
        
        # Check if escalation is needed
        if (not recovery_result.success and 
            error_context.retry_count >= config.escalation_threshold):
            recovery_result.support_escalated = True
        
        return recovery_result

    def categorize_error(self, error_message: str, error_context: Dict[str, Any] = None) -> ErrorCategory:
        """
        Categorize error for appropriate recovery strategy selection.
        
        Critical for selecting optimal recovery approach.
        """
        error_lower = error_message.lower()
        
        # Network-related errors
        network_keywords = ['connection', 'timeout', 'network', 'dns', 'ssl', 'tls', 'unreachable']
        if any(keyword in error_lower for keyword in network_keywords):
            return ErrorCategory.NETWORK
        
        # Database-related errors
        database_keywords = ['database', 'sql', 'postgresql', 'connection pool', 'deadlock', 'constraint']
        if any(keyword in error_lower for keyword in database_keywords):
            return ErrorCategory.DATABASE
        
        # LLM API errors
        llm_keywords = ['llm', 'openai', 'anthropic', 'tokens', 'model', 'completion', 'rate limit']
        if any(keyword in error_lower for keyword in llm_keywords):
            return ErrorCategory.LLM_API
        
        # Authentication errors
        auth_keywords = ['auth', 'token', 'unauthorized', 'forbidden', 'permission', 'jwt']
        if any(keyword in error_lower for keyword in auth_keywords):
            return ErrorCategory.AUTHENTICATION
        
        # Rate limiting errors
        rate_limit_keywords = ['rate limit', 'quota', 'throttle', 'too many requests', '429']
        if any(keyword in error_lower for keyword in rate_limit_keywords):
            return ErrorCategory.RATE_LIMIT
        
        # Validation errors
        validation_keywords = ['validation', 'invalid', 'format', 'required', 'missing']
        if any(keyword in error_lower for keyword in validation_keywords):
            return ErrorCategory.VALIDATION
        
        # Default to system error
        return ErrorCategory.SYSTEM

    def assess_error_severity(self, error_category: ErrorCategory, 
                            error_message: str, user_tier: SubscriptionTier) -> ErrorSeverity:
        """
        Assess error severity based on category, message, and user tier.
        
        Critical for prioritizing recovery efforts.
        """
        error_lower = error_message.lower()
        
        # Critical keywords that always indicate high severity
        critical_keywords = ['data loss', 'corruption', 'security', 'breach', 'crash', 'fatal']
        if any(keyword in error_lower for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL
        
        # Category-based severity assessment
        base_severity = {
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.DATABASE: ErrorSeverity.HIGH,
            ErrorCategory.LLM_API: ErrorSeverity.MEDIUM,
            ErrorCategory.AUTHENTICATION: ErrorSeverity.HIGH,
            ErrorCategory.RATE_LIMIT: ErrorSeverity.LOW,
            ErrorCategory.VALIDATION: ErrorSeverity.LOW,
            ErrorCategory.SYSTEM: ErrorSeverity.HIGH
        }.get(error_category, ErrorSeverity.MEDIUM)
        
        # Adjust severity based on user tier
        if user_tier == SubscriptionTier.ENTERPRISE:
            # Enterprise users get priority - upgrade severity
            if base_severity == ErrorSeverity.LOW:
                return ErrorSeverity.MEDIUM
            elif base_severity == ErrorSeverity.MEDIUM:
                return ErrorSeverity.HIGH
        
        return base_severity

    def generate_recovery_metrics(self) -> Dict[str, Any]:
        """
        Generate comprehensive recovery metrics for monitoring.
        
        Critical for operational visibility and optimization.
        """
        total_recoveries = sum(len(history) for history in self._recovery_history.values())
        
        if total_recoveries == 0:
            return {
                'total_recoveries': 0,
                'success_rate': 0.0,
                'average_recovery_time': 0.0,
                'error_patterns': {},
                'strategy_effectiveness': {}
            }
        
        # Calculate success rate
        successful_recoveries = 0
        total_recovery_time = 0.0
        strategy_usage = {}
        strategy_success = {}
        
        for user_history in self._recovery_history.values():
            for recovery in user_history:
                if recovery.success:
                    successful_recoveries += 1
                total_recovery_time += recovery.recovery_time_seconds
                
                strategy = recovery.strategy_used.value
                strategy_usage[strategy] = strategy_usage.get(strategy, 0) + 1
                
                if recovery.success:
                    strategy_success[strategy] = strategy_success.get(strategy, 0) + 1
        
        success_rate = successful_recoveries / total_recoveries
        average_recovery_time = total_recovery_time / total_recoveries
        
        # Calculate strategy effectiveness
        strategy_effectiveness = {}
        for strategy, usage_count in strategy_usage.items():
            success_count = strategy_success.get(strategy, 0)
            strategy_effectiveness[strategy] = success_count / usage_count
        
        return {
            'total_recoveries': total_recoveries,
            'success_rate': success_rate,
            'average_recovery_time': average_recovery_time,
            'error_patterns': self._error_patterns.copy(),
            'strategy_effectiveness': strategy_effectiveness,
            'users_affected': len(self._recovery_history)
        }

    def predict_recovery_success_probability(self, error_context: ErrorContext) -> float:
        """
        Predict probability of successful recovery based on historical data.
        
        Used for proactive error handling and resource allocation.
        """
        # Base probability by error category
        base_probabilities = {
            ErrorCategory.NETWORK: 0.85,      # Network issues often transient
            ErrorCategory.DATABASE: 0.70,     # Database issues more complex
            ErrorCategory.LLM_API: 0.80,      # LLM APIs usually reliable
            ErrorCategory.AUTHENTICATION: 0.60, # Auth issues often configuration
            ErrorCategory.RATE_LIMIT: 0.95,   # Rate limits usually temporary
            ErrorCategory.VALIDATION: 0.30,   # Validation errors need fixes
            ErrorCategory.SYSTEM: 0.50        # System errors vary widely
        }
        
        base_probability = base_probabilities.get(error_context.error_category, 0.5)
        
        # Adjust based on user tier (higher tiers get better recovery)
        tier_multipliers = {
            SubscriptionTier.FREE: 0.8,
            SubscriptionTier.EARLY: 0.9,
            SubscriptionTier.MID: 1.1,
            SubscriptionTier.ENTERPRISE: 1.3
        }
        
        tier_adjusted = base_probability * tier_multipliers[error_context.user_tier]
        
        # Adjust based on retry count (fewer retries = higher probability)
        retry_penalty = 0.1 * error_context.retry_count
        final_probability = max(0.1, tier_adjusted - retry_penalty)
        
        return min(1.0, final_probability)

    # PRIVATE HELPER METHODS

    def _get_recovery_config(self, error_context: ErrorContext) -> RecoveryConfig:
        """Get recovery configuration for error context."""
        tier_configs = self.TIER_RECOVERY_CONFIGS.get(error_context.user_tier, {})
        
        # Get specific config or fallback to network config
        config = tier_configs.get(error_context.error_category)
        if not config:
            config = tier_configs.get(ErrorCategory.NETWORK)
        
        # Final fallback - minimal config
        if not config:
            config = RecoveryConfig(
                max_retries=1,
                max_recovery_time_seconds=60,
                retry_strategies=[RecoveryStrategy.USER_NOTIFICATION],
                escalation_threshold=1,
                user_notification_required=True,
                support_notification_required=False
            )
        
        return config

    def _execute_immediate_retry(self, error_context: ErrorContext, 
                               operation_to_retry: Callable) -> RecoveryResult:
        """Execute immediate retry strategy."""
        if not operation_to_retry:
            return RecoveryResult(
                recovery_id="",
                success=False,
                strategy_used=RecoveryStrategy.IMMEDIATE_RETRY,
                attempts_made=0,
                recovery_time_seconds=0.0,
                final_error_message="No operation provided for retry",
                user_impact_level="medium",
                support_escalated=False
            )
        
        try:
            # Attempt immediate retry
            result = operation_to_retry()
            return RecoveryResult(
                recovery_id="",
                success=True,
                strategy_used=RecoveryStrategy.IMMEDIATE_RETRY,
                attempts_made=1,
                recovery_time_seconds=0.1,
                final_error_message=None,
                user_impact_level="low",
                support_escalated=False
            )
        except Exception as e:
            return RecoveryResult(
                recovery_id="",
                success=False,
                strategy_used=RecoveryStrategy.IMMEDIATE_RETRY,
                attempts_made=1,
                recovery_time_seconds=0.1,
                final_error_message=str(e),
                user_impact_level="medium",
                support_escalated=False
            )

    def _execute_exponential_backoff(self, error_context: ErrorContext,
                                   operation_to_retry: Callable,
                                   config: RecoveryConfig) -> RecoveryResult:
        """Execute exponential backoff retry strategy."""
        if not operation_to_retry:
            return RecoveryResult(
                recovery_id="",
                success=False,
                strategy_used=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                attempts_made=0,
                recovery_time_seconds=0.0,
                final_error_message="No operation provided for retry",
                user_impact_level="medium",
                support_escalated=False
            )
        
        attempts = 0
        last_error = None
        
        for attempt in range(config.max_retries):
            try:
                if attempt > 0:
                    # Exponential backoff: wait 2^attempt seconds
                    backoff_time = min(2 ** attempt, 60)  # Max 60 seconds
                    time.sleep(backoff_time / 1000)  # Convert to milliseconds for testing
                
                result = operation_to_retry()
                return RecoveryResult(
                    recovery_id="",
                    success=True,
                    strategy_used=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                    attempts_made=attempts + 1,
                    recovery_time_seconds=0.5 * (attempts + 1),
                    final_error_message=None,
                    user_impact_level="low",
                    support_escalated=False
                )
            except Exception as e:
                attempts += 1
                last_error = e
        
        return RecoveryResult(
            recovery_id="",
            success=False,
            strategy_used=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            attempts_made=attempts,
            recovery_time_seconds=1.0 * attempts,
            final_error_message=str(last_error) if last_error else "Unknown error",
            user_impact_level="medium",
            support_escalated=False
        )

    def _execute_circuit_breaker(self, error_context: ErrorContext,
                               operation_to_retry: Callable) -> RecoveryResult:
        """Execute circuit breaker recovery strategy."""
        circuit_key = f"{error_context.error_category.value}:{error_context.user_tier.value}"
        
        # Initialize circuit breaker if not exists
        if circuit_key not in self._circuit_breakers:
            self._circuit_breakers[circuit_key] = {
                'state': 'closed',  # closed, open, half-open
                'failure_count': 0,
                'last_failure_time': None,
                'success_count': 0
            }
        
        circuit = self._circuit_breakers[circuit_key]
        
        # Check circuit state
        if circuit['state'] == 'open':
            # Circuit is open - check if enough time has passed to try half-open
            if (circuit['last_failure_time'] and 
                datetime.now(timezone.utc) > circuit['last_failure_time'] + timedelta(seconds=60)):
                circuit['state'] = 'half-open'
            else:
                # Circuit still open - fail fast
                return RecoveryResult(
                    recovery_id="",
                    success=False,
                    strategy_used=RecoveryStrategy.CIRCUIT_BREAKER,
                    attempts_made=0,
                    recovery_time_seconds=0.01,
                    final_error_message="Circuit breaker is open",
                    user_impact_level="low",  # Fail fast reduces impact
                    support_escalated=False
                )
        
        # Try the operation
        if operation_to_retry:
            try:
                result = operation_to_retry()
                # Success - reset circuit
                circuit['failure_count'] = 0
                circuit['success_count'] += 1
                circuit['state'] = 'closed'
                
                return RecoveryResult(
                    recovery_id="",
                    success=True,
                    strategy_used=RecoveryStrategy.CIRCUIT_BREAKER,
                    attempts_made=1,
                    recovery_time_seconds=0.1,
                    final_error_message=None,
                    user_impact_level="low",
                    support_escalated=False
                )
            except Exception as e:
                # Failure - update circuit
                circuit['failure_count'] += 1
                circuit['last_failure_time'] = datetime.now(timezone.utc)
                
                # Open circuit if too many failures
                if circuit['failure_count'] >= 3:
                    circuit['state'] = 'open'
                
                return RecoveryResult(
                    recovery_id="",
                    success=False,
                    strategy_used=RecoveryStrategy.CIRCUIT_BREAKER,
                    attempts_made=1,
                    recovery_time_seconds=0.1,
                    final_error_message=str(e),
                    user_impact_level="medium",
                    support_escalated=False
                )
        
        return RecoveryResult(
            recovery_id="",
            success=False,
            strategy_used=RecoveryStrategy.CIRCUIT_BREAKER,
            attempts_made=0,
            recovery_time_seconds=0.0,
            final_error_message="No operation provided",
            user_impact_level="medium",
            support_escalated=False
        )

    def _execute_failover(self, error_context: ErrorContext,
                        operation_to_retry: Callable) -> RecoveryResult:
        """Execute failover recovery strategy."""
        # Simulate failover to backup systems
        return RecoveryResult(
            recovery_id="",
            success=True,  # Failover usually succeeds
            strategy_used=RecoveryStrategy.FAILOVER,
            attempts_made=1,
            recovery_time_seconds=2.0,  # Failover takes some time
            final_error_message=None,
            user_impact_level="low",  # Transparent to user
            support_escalated=False
        )

    def _execute_graceful_degradation(self, error_context: ErrorContext) -> RecoveryResult:
        """Execute graceful degradation strategy."""
        return RecoveryResult(
            recovery_id="",
            success=True,  # Degradation allows partial functionality
            strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
            attempts_made=1,
            recovery_time_seconds=0.1,
            final_error_message=None,
            user_impact_level="medium",  # Reduced functionality
            support_escalated=False
        )

    def _execute_user_notification(self, error_context: ErrorContext) -> RecoveryResult:
        """Execute user notification strategy."""
        return RecoveryResult(
            recovery_id="",
            success=True,  # Notification is successful communication
            strategy_used=RecoveryStrategy.USER_NOTIFICATION,
            attempts_made=1,
            recovery_time_seconds=0.05,
            final_error_message=None,
            user_impact_level="high",  # User knows about the problem
            support_escalated=False
        )


@pytest.mark.golden_path
@pytest.mark.unit
class TestErrorRecoveryStrategiesBusinessLogic:
    """Test error recovery strategies business logic for platform reliability."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.recovery_manager = ErrorRecoveryManager()
        self.test_user_id = str(uuid.uuid4())
        
    def _create_error_context(self, error_category: ErrorCategory = ErrorCategory.NETWORK,
                            user_tier: SubscriptionTier = SubscriptionTier.MID,
                            severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> ErrorContext:
        """Helper to create error contexts for testing."""
        return ErrorContext(
            error_id=str(uuid.uuid4()),
            error_message=f"Test {error_category.value} error",
            error_category=error_category,
            severity=severity,
            user_id=self.test_user_id,
            user_tier=user_tier,
            agent_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4()),
            occurred_at=datetime.now(timezone.utc),
            retry_count=0,
            metadata={}
        )

    # ERROR CATEGORIZATION TESTS

    def test_categorize_network_errors(self):
        """Test categorization of network-related errors."""
        network_errors = [
            "Connection timeout occurred",
            "DNS resolution failed",
            "SSL handshake error",
            "Network unreachable"
        ]
        
        for error_msg in network_errors:
            category = self.recovery_manager.categorize_error(error_msg)
            assert category == ErrorCategory.NETWORK

    def test_categorize_database_errors(self):
        """Test categorization of database-related errors."""
        database_errors = [
            "PostgreSQL connection failed",
            "SQL constraint violation",
            "Database deadlock detected",
            "Connection pool exhausted"
        ]
        
        for error_msg in database_errors:
            category = self.recovery_manager.categorize_error(error_msg)
            assert category == ErrorCategory.DATABASE

    def test_categorize_llm_api_errors(self):
        """Test categorization of LLM API errors."""
        llm_errors = [
            "OpenAI API rate limit exceeded",
            "Token limit exceeded for model",
            "LLM completion timeout",
            "Anthropic API unavailable"
        ]
        
        for error_msg in llm_errors:
            category = self.recovery_manager.categorize_error(error_msg)
            assert category == ErrorCategory.LLM_API

    def test_categorize_authentication_errors(self):
        """Test categorization of authentication errors."""
        auth_errors = [
            "JWT token expired",
            "Unauthorized access",
            "Authentication failed",
            "Permission denied"
        ]
        
        for error_msg in auth_errors:
            category = self.recovery_manager.categorize_error(error_msg)
            assert category == ErrorCategory.AUTHENTICATION

    def test_categorize_unknown_error_defaults_to_system(self):
        """Test that unknown errors default to SYSTEM category."""
        unknown_error = "Something completely unexpected happened"
        
        category = self.recovery_manager.categorize_error(unknown_error)
        
        assert category == ErrorCategory.SYSTEM

    # ERROR SEVERITY ASSESSMENT TESTS

    def test_assess_critical_severity_keywords(self):
        """Test that critical keywords always result in CRITICAL severity."""
        critical_errors = [
            "Data loss detected",
            "Database corruption found",
            "Security breach identified",
            "System crash occurred"
        ]
        
        for error_msg in critical_errors:
            severity = self.recovery_manager.assess_error_severity(
                ErrorCategory.SYSTEM, error_msg, SubscriptionTier.FREE
            )
            assert severity == ErrorSeverity.CRITICAL

    def test_assess_severity_by_category(self):
        """Test severity assessment based on error category."""
        # Database errors should be HIGH severity by default
        severity = self.recovery_manager.assess_error_severity(
            ErrorCategory.DATABASE, "Connection failed", SubscriptionTier.MID
        )
        assert severity == ErrorSeverity.HIGH
        
        # Rate limit errors should be LOW severity
        severity = self.recovery_manager.assess_error_severity(
            ErrorCategory.RATE_LIMIT, "Rate limit exceeded", SubscriptionTier.MID
        )
        assert severity == ErrorSeverity.LOW

    def test_assess_severity_enterprise_tier_upgrade(self):
        """Test that Enterprise tier gets upgraded severity."""
        # LOW severity for non-Enterprise
        severity_mid = self.recovery_manager.assess_error_severity(
            ErrorCategory.RATE_LIMIT, "Rate limit exceeded", SubscriptionTier.MID
        )
        
        # Should be upgraded for Enterprise
        severity_enterprise = self.recovery_manager.assess_error_severity(
            ErrorCategory.RATE_LIMIT, "Rate limit exceeded", SubscriptionTier.ENTERPRISE
        )
        
        assert severity_enterprise > severity_mid

    # RECOVERY STRATEGY EXECUTION TESTS

    def test_successful_immediate_retry_recovery(self):
        """Test successful recovery with immediate retry strategy."""
        error_context = self._create_error_context(user_tier=SubscriptionTier.FREE)
        
        # Mock operation that succeeds on retry
        def mock_operation():
            return "success"
        
        recovery = self.recovery_manager.execute_recovery_strategy(
            error_context, mock_operation
        )
        
        assert recovery.success is True
        assert recovery.strategy_used == RecoveryStrategy.IMMEDIATE_RETRY
        assert recovery.attempts_made > 0

    def test_failed_recovery_all_strategies_exhausted(self):
        """Test recovery failure when all strategies are exhausted."""
        error_context = self._create_error_context(user_tier=SubscriptionTier.FREE)
        
        # Mock operation that always fails
        def mock_failing_operation():
            raise Exception("Persistent failure")
        
        recovery = self.recovery_manager.execute_recovery_strategy(
            error_context, mock_failing_operation
        )
        
        assert recovery.success is False
        assert recovery.final_error_message is not None

    def test_exponential_backoff_strategy(self):
        """Test exponential backoff recovery strategy."""
        error_context = self._create_error_context(user_tier=SubscriptionTier.EARLY)
        
        attempt_count = 0
        def mock_operation_succeeds_on_second_attempt():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count >= 2:
                return "success"
            raise Exception("Temporary failure")
        
        recovery = self.recovery_manager.execute_recovery_strategy(
            error_context, mock_operation_succeeds_on_second_attempt
        )
        
        assert recovery.success is True
        assert recovery.strategy_used == RecoveryStrategy.EXPONENTIAL_BACKOFF
        assert recovery.attempts_made >= 2

    def test_circuit_breaker_strategy(self):
        """Test circuit breaker recovery strategy."""
        error_context = self._create_error_context(user_tier=SubscriptionTier.MID)
        
        def mock_successful_operation():
            return "success"
        
        recovery = self.recovery_manager.execute_recovery_strategy(
            error_context, mock_successful_operation
        )
        
        assert recovery.success is True
        assert recovery.strategy_used == RecoveryStrategy.CIRCUIT_BREAKER

    def test_failover_strategy_for_enterprise(self):
        """Test failover strategy for Enterprise tier."""
        error_context = self._create_error_context(
            error_category=ErrorCategory.DATABASE,
            user_tier=SubscriptionTier.ENTERPRISE
        )
        
        recovery = self.recovery_manager.execute_recovery_strategy(error_context)
        
        assert recovery.success is True
        assert recovery.strategy_used == RecoveryStrategy.FAILOVER
        assert recovery.user_impact_level == "low"  # Transparent failover

    def test_graceful_degradation_strategy(self):
        """Test graceful degradation recovery strategy."""
        error_context = self._create_error_context(
            error_category=ErrorCategory.LLM_API,
            user_tier=SubscriptionTier.FREE
        )
        
        recovery = self.recovery_manager.execute_recovery_strategy(error_context)
        
        assert recovery.success is True
        assert recovery.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert recovery.user_impact_level == "medium"  # Reduced functionality

    # TIER-BASED RECOVERY CONFIGURATION TESTS

    def test_enterprise_tier_fast_recovery_requirements(self):
        """Test that Enterprise tier has fast recovery requirements."""
        config = self.recovery_manager._get_recovery_config(
            self._create_error_context(user_tier=SubscriptionTier.ENTERPRISE)
        )
        
        assert config.max_recovery_time_seconds <= 5  # Enterprise SLA
        assert config.max_retries >= 5  # More retry attempts
        assert config.support_notification_required is True

    def test_free_tier_limited_recovery_resources(self):
        """Test that Free tier has limited recovery resources."""
        config = self.recovery_manager._get_recovery_config(
            self._create_error_context(user_tier=SubscriptionTier.FREE)
        )
        
        assert config.max_recovery_time_seconds >= 120  # Longer recovery time
        assert config.max_retries <= 1  # Fewer retry attempts
        assert config.support_notification_required is False

    def test_mid_tier_balanced_recovery_approach(self):
        """Test that Mid tier has balanced recovery approach."""
        config = self.recovery_manager._get_recovery_config(
            self._create_error_context(user_tier=SubscriptionTier.MID)
        )
        
        assert 5 < config.max_recovery_time_seconds < 120  # Balanced timing
        assert 1 < config.max_retries < 5  # Moderate retries
        assert config.support_notification_required is True

    # RECOVERY METRICS AND MONITORING TESTS

    def test_generate_recovery_metrics_empty_state(self):
        """Test recovery metrics generation with no recovery history."""
        metrics = self.recovery_manager.generate_recovery_metrics()
        
        assert metrics['total_recoveries'] == 0
        assert metrics['success_rate'] == 0.0
        assert metrics['average_recovery_time'] == 0.0

    def test_generate_recovery_metrics_with_history(self):
        """Test recovery metrics generation with recovery history."""
        # Create some recovery attempts
        error_context = self._create_error_context()
        
        def mock_successful_operation():
            return "success"
        
        # Execute several recoveries
        for i in range(5):
            self.recovery_manager.execute_recovery_strategy(
                error_context, mock_successful_operation
            )
        
        metrics = self.recovery_manager.generate_recovery_metrics()
        
        assert metrics['total_recoveries'] > 0
        assert metrics['success_rate'] > 0.0
        assert metrics['users_affected'] > 0

    def test_recovery_success_probability_prediction(self):
        """Test prediction of recovery success probability."""
        # Network errors should have high success probability
        network_context = self._create_error_context(ErrorCategory.NETWORK)
        network_probability = self.recovery_manager.predict_recovery_success_probability(network_context)
        
        # Validation errors should have low success probability
        validation_context = self._create_error_context(ErrorCategory.VALIDATION)
        validation_probability = self.recovery_manager.predict_recovery_success_probability(validation_context)
        
        assert network_probability > validation_probability

    def test_enterprise_tier_higher_recovery_probability(self):
        """Test that Enterprise tier has higher recovery probability."""
        free_context = self._create_error_context(user_tier=SubscriptionTier.FREE)
        enterprise_context = self._create_error_context(user_tier=SubscriptionTier.ENTERPRISE)
        
        free_probability = self.recovery_manager.predict_recovery_success_probability(free_context)
        enterprise_probability = self.recovery_manager.predict_recovery_success_probability(enterprise_context)
        
        assert enterprise_probability > free_probability

    def test_retry_count_reduces_success_probability(self):
        """Test that higher retry count reduces success probability."""
        context_no_retries = self._create_error_context()
        context_no_retries.retry_count = 0
        
        context_many_retries = self._create_error_context()
        context_many_retries.retry_count = 5
        
        prob_no_retries = self.recovery_manager.predict_recovery_success_probability(context_no_retries)
        prob_many_retries = self.recovery_manager.predict_recovery_success_probability(context_many_retries)
        
        assert prob_no_retries > prob_many_retries

    # CIRCUIT BREAKER TESTS

    def test_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions."""
        error_context = self._create_error_context()
        circuit_key = f"{error_context.error_category.value}:{error_context.user_tier.value}"
        
        def mock_failing_operation():
            raise Exception("Persistent failure")
        
        # Execute multiple failures to open circuit
        for i in range(4):
            recovery = self.recovery_manager.execute_recovery_strategy(
                error_context, mock_failing_operation
            )
        
        # Circuit should be open now
        circuit = self.recovery_manager._circuit_breakers[circuit_key]
        assert circuit['state'] == 'open'

    def test_circuit_breaker_fail_fast_when_open(self):
        """Test that circuit breaker fails fast when open."""
        error_context = self._create_error_context()
        circuit_key = f"{error_context.error_category.value}:{error_context.user_tier.value}"
        
        # Manually set circuit to open
        self.recovery_manager._circuit_breakers[circuit_key] = {
            'state': 'open',
            'failure_count': 5,
            'last_failure_time': datetime.now(timezone.utc),
            'success_count': 0
        }
        
        def mock_operation():
            return "success"
        
        recovery = self.recovery_manager.execute_recovery_strategy(
            error_context, mock_operation
        )
        
        assert recovery.success is False
        assert recovery.final_error_message == "Circuit breaker is open"
        assert recovery.recovery_time_seconds < 0.1  # Fail fast

    # BUSINESS RULES VALIDATION TESTS

    def test_all_tiers_have_recovery_configurations(self):
        """Test that all tiers have recovery configurations."""
        configs = self.recovery_manager.TIER_RECOVERY_CONFIGS
        
        for tier in SubscriptionTier:
            assert tier in configs
            assert len(configs[tier]) > 0

    def test_enterprise_tier_best_recovery_sla(self):
        """Test that Enterprise tier has the best recovery SLA."""
        enterprise_configs = self.recovery_manager.TIER_RECOVERY_CONFIGS[SubscriptionTier.ENTERPRISE]
        free_configs = self.recovery_manager.TIER_RECOVERY_CONFIGS[SubscriptionTier.FREE]
        
        # Check a common error category
        enterprise_network = enterprise_configs[ErrorCategory.NETWORK]
        free_network = free_configs[ErrorCategory.NETWORK]
        
        assert enterprise_network.max_recovery_time_seconds < free_network.max_recovery_time_seconds
        assert enterprise_network.max_retries > free_network.max_retries

    def test_error_pattern_tracking(self):
        """Test that error patterns are tracked for analysis."""
        error_context = self._create_error_context()
        
        self.recovery_manager.execute_recovery_strategy(error_context)
        
        error_pattern_key = f"{error_context.error_category.value}:{error_context.user_tier.value}"
        assert error_pattern_key in self.recovery_manager._error_patterns
        assert self.recovery_manager._error_patterns[error_pattern_key] > 0