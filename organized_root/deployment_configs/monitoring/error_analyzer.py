"""
Error analysis and pattern detection for deployment logs.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ErrorCategory(Enum):
    """Error categorization for automated recovery."""
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    DATABASE = "database"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    QUOTA = "quota"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # Service completely down
    HIGH = "high"         # Major functionality impaired
    MEDIUM = "medium"     # Degraded performance
    LOW = "low"          # Minor issues

class RetryStrategy(Enum):
    """Retry strategies for error recovery."""
    IMMEDIATE = "immediate"           # Retry immediately
    EXPONENTIAL_BACKOFF = "exponential"  # Exponential backoff
    LINEAR_BACKOFF = "linear"        # Linear backoff
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker pattern
    NO_RETRY = "no_retry"            # Do not retry

@dataclass
class ErrorPattern:
    """Error pattern definition."""
    category: ErrorCategory
    severity: ErrorSeverity
    pattern: str  # Regex pattern
    description: str
    retry_strategy: RetryStrategy
    auto_recovery: bool = False
    recovery_action: Optional[str] = None
    
    def __post_init__(self):
        """Compile regex pattern."""
        self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE)

@dataclass
class AnalyzedError:
    """Analyzed error with categorization and recovery strategy."""
    original_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    service: str
    timestamp: datetime
    pattern_matched: Optional[str] = None
    retry_strategy: RetryStrategy = RetryStrategy.NO_RETRY
    auto_recovery: bool = False
    recovery_action: Optional[str] = None
    occurrence_count: int = 1

@dataclass
class ErrorAnalysis:
    """Complete error analysis result."""
    total_errors: int
    errors_by_category: Dict[ErrorCategory, int] = field(default_factory=dict)
    errors_by_severity: Dict[ErrorSeverity, int] = field(default_factory=dict)
    errors_by_service: Dict[str, int] = field(default_factory=dict)
    critical_errors: List[AnalyzedError] = field(default_factory=list)
    recovery_recommendations: List[str] = field(default_factory=list)
    error_rate: float = 0.0
    time_window_seconds: int = 300

class ErrorAnalyzer:
    """Analyzes deployment errors and recommends recovery actions."""
    
    def __init__(self):
        self.error_patterns = self._initialize_error_patterns()
        self.error_history: List[AnalyzedError] = []
        
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize common error patterns."""
        return [
            # Authentication errors
            ErrorPattern(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(401|403|unauthorized|forbidden|authentication failed|invalid credentials)",
                description="Authentication or authorization failure",
                retry_strategy=RetryStrategy.NO_RETRY,
                auto_recovery=True,
                recovery_action="regenerate_service_account_key"
            ),
            
            # Service account errors
            ErrorPattern(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(service account.*not found|invalid service account|key.*expired)",
                description="Service account issue",
                retry_strategy=RetryStrategy.NO_RETRY,
                auto_recovery=True,
                recovery_action="rotate_service_account"
            ),
            
            # Network errors
            ErrorPattern(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                pattern=r"(connection refused|connection reset|ECONNREFUSED|ETIMEDOUT|network unreachable)",
                description="Network connectivity issue",
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                auto_recovery=False
            ),
            
            # DNS errors
            ErrorPattern(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                pattern=r"(NXDOMAIN|DNS.*failed|name resolution failed|getaddrinfo ENOTFOUND)",
                description="DNS resolution failure",
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                auto_recovery=False
            ),
            
            # Database connection errors
            ErrorPattern(
                category=ErrorCategory.DATABASE,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(database.*connection.*failed|connection pool exhausted|too many connections)",
                description="Database connection issue",
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                auto_recovery=True,
                recovery_action="reset_connection_pool"
            ),
            
            # Resource exhaustion
            ErrorPattern(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(out of memory|OOM|memory limit exceeded|CPU limit|disk full)",
                description="Resource exhaustion",
                retry_strategy=RetryStrategy.NO_RETRY,
                auto_recovery=True,
                recovery_action="scale_up_resources"
            ),
            
            # Timeout errors
            ErrorPattern(
                category=ErrorCategory.TIMEOUT,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"(timeout|timed out|deadline exceeded|request timeout)",
                description="Operation timeout",
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                auto_recovery=False
            ),
            
            # Permission errors
            ErrorPattern(
                category=ErrorCategory.PERMISSION,
                severity=ErrorSeverity.HIGH,
                pattern=r"(permission denied|access denied|insufficient permissions|IAM.*denied)",
                description="Permission issue",
                retry_strategy=RetryStrategy.NO_RETRY,
                auto_recovery=True,
                recovery_action="update_iam_permissions"
            ),
            
            # Quota errors
            ErrorPattern(
                category=ErrorCategory.QUOTA,
                severity=ErrorSeverity.HIGH,
                pattern=r"(quota exceeded|rate limit|too many requests|429)",
                description="Quota or rate limit exceeded",
                retry_strategy=RetryStrategy.CIRCUIT_BREAKER,
                auto_recovery=False
            ),
            
            # Configuration errors
            ErrorPattern(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                pattern=r"(configuration error|invalid configuration|missing.*environment|undefined variable)",
                description="Configuration issue",
                retry_strategy=RetryStrategy.NO_RETRY,
                auto_recovery=False
            ),
            
            # Container/Docker errors
            ErrorPattern(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(container.*failed|docker.*error|image.*not found|pull.*failed)",
                description="Container/Docker issue",
                retry_strategy=RetryStrategy.LINEAR_BACKOFF,
                auto_recovery=True,
                recovery_action="rebuild_container"
            ),
            
            # Health check failures
            ErrorPattern(
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                pattern=r"(health check failed|readiness probe failed|liveness probe failed)",
                description="Health check failure",
                retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                auto_recovery=False
            )
        ]
    
    def analyze_error(self, 
                     error_message: str, 
                     service: str,
                     timestamp: Optional[datetime] = None) -> AnalyzedError:
        """
        Analyze a single error message.
        
        Args:
            error_message: The error message to analyze
            service: Service that generated the error
            timestamp: Error timestamp
            
        Returns:
            AnalyzedError with categorization and recovery strategy
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Check against known patterns
        for pattern in self.error_patterns:
            if pattern.compiled_pattern.search(error_message):
                return AnalyzedError(
                    original_message=error_message,
                    category=pattern.category,
                    severity=pattern.severity,
                    service=service,
                    timestamp=timestamp,
                    pattern_matched=pattern.description,
                    retry_strategy=pattern.retry_strategy,
                    auto_recovery=pattern.auto_recovery,
                    recovery_action=pattern.recovery_action
                )
        
        # Unknown error
        return AnalyzedError(
            original_message=error_message,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            service=service,
            timestamp=timestamp,
            retry_strategy=RetryStrategy.NO_RETRY
        )
    
    def analyze_error_batch(self, 
                           errors: List[Dict[str, Any]]) -> ErrorAnalysis:
        """
        Analyze a batch of errors.
        
        Args:
            errors: List of error dictionaries with 'message', 'service', 'timestamp' keys
            
        Returns:
            ErrorAnalysis with aggregated results
        """
        analysis = ErrorAnalysis(total_errors=len(errors))
        
        # Group errors for deduplication
        error_groups = defaultdict(list)
        
        for error_data in errors:
            analyzed = self.analyze_error(
                error_data.get("message", ""),
                error_data.get("service", "unknown"),
                error_data.get("timestamp")
            )
            
            # Group by message pattern for deduplication
            key = (analyzed.category, analyzed.severity, analyzed.pattern_matched)
            error_groups[key].append(analyzed)
            
            # Update counters
            analysis.errors_by_category[analyzed.category] = \
                analysis.errors_by_category.get(analyzed.category, 0) + 1
            analysis.errors_by_severity[analyzed.severity] = \
                analysis.errors_by_severity.get(analyzed.severity, 0) + 1
            analysis.errors_by_service[analyzed.service] = \
                analysis.errors_by_service.get(analyzed.service, 0) + 1
            
            # Track critical errors
            if analyzed.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
                analysis.critical_errors.append(analyzed)
        
        # Generate recovery recommendations
        analysis.recovery_recommendations = self._generate_recovery_recommendations(error_groups)
        
        # Calculate error rate (errors per minute)
        if analysis.time_window_seconds > 0:
            analysis.error_rate = (analysis.total_errors / analysis.time_window_seconds) * 60
        
        # Store in history
        for errors_list in error_groups.values():
            if errors_list:
                consolidated = errors_list[0]
                consolidated.occurrence_count = len(errors_list)
                self.error_history.append(consolidated)
        
        return analysis
    
    def _generate_recovery_recommendations(self, 
                                          error_groups: Dict[Tuple, List[AnalyzedError]]) -> List[str]:
        """Generate recovery recommendations based on error patterns."""
        recommendations = []
        
        for (category, severity, pattern), errors in error_groups.items():
            if not errors:
                continue
                
            error = errors[0]
            count = len(errors)
            
            # High frequency errors
            if count > 5:
                recommendations.append(
                    f"High frequency {category.value} errors ({count} occurrences): {pattern}"
                )
            
            # Auto-recovery available
            if error.auto_recovery and error.recovery_action:
                recommendations.append(
                    f"Auto-recovery available for {pattern}: Execute '{error.recovery_action}'"
                )
            
            # Retry strategy recommendations
            if error.retry_strategy != RetryStrategy.NO_RETRY:
                recommendations.append(
                    f"Retry with {error.retry_strategy.value} strategy for {pattern}"
                )
        
        # Category-specific recommendations
        if ErrorCategory.AUTHENTICATION in [cat for (cat, _, _) in error_groups.keys()]:
            recommendations.append("Review service account permissions and key rotation")
        
        if ErrorCategory.RESOURCE in [cat for (cat, _, _) in error_groups.keys()]:
            recommendations.append("Consider scaling up resources or optimizing resource usage")
        
        if ErrorCategory.NETWORK in [cat for (cat, _, _) in error_groups.keys()]:
            recommendations.append("Check network connectivity and firewall rules")
        
        return recommendations
    
    def detect_error_patterns(self, 
                             time_window_minutes: int = 5) -> List[str]:
        """
        Detect patterns in recent error history.
        
        Args:
            time_window_minutes: Time window to analyze
            
        Returns:
            List of detected patterns
        """
        patterns = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]
        
        if not recent_errors:
            return patterns
        
        # Check for error storms (>10 errors in window)
        if len(recent_errors) > 10:
            patterns.append(f"Error storm detected: {len(recent_errors)} errors in {time_window_minutes} minutes")
        
        # Check for cascading failures (multiple services)
        services_affected = set(e.service for e in recent_errors)
        if len(services_affected) > 3:
            patterns.append(f"Cascading failure: {len(services_affected)} services affected")
        
        # Check for repeated errors
        error_counts = defaultdict(int)
        for error in recent_errors:
            key = (error.category, error.pattern_matched)
            error_counts[key] += 1
        
        for (category, pattern), count in error_counts.items():
            if count > 3:
                patterns.append(f"Repeated {category.value} error: {pattern} ({count} times)")
        
        return patterns
    
    def get_error_summary(self) -> str:
        """Get a formatted error summary."""
        if not self.error_history:
            return "No errors recorded"
        
        lines = ["ERROR ANALYSIS SUMMARY", "=" * 40]
        
        # Count by category
        category_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for error in self.error_history:
            category_counts[error.category] += error.occurrence_count
            severity_counts[error.severity] += error.occurrence_count
        
        lines.append("\nErrors by Category:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {category.value}: {count}")
        
        lines.append("\nErrors by Severity:")
        for severity, count in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {severity.value}: {count}")
        
        # Recent patterns
        patterns = self.detect_error_patterns()
        if patterns:
            lines.append("\nDetected Patterns:")
            for pattern in patterns:
                lines.append(f"  - {pattern}")
        
        return "\n".join(lines)