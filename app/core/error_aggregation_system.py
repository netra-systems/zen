"""Error pattern aggregation and intelligent reporting system.

Provides sophisticated error pattern recognition, trend analysis, and 
intelligent alerting to proactively identify system issues.
"""

import asyncio
import hashlib
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.error_codes import ErrorSeverity
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AggregationLevel(Enum):
    """Levels of error aggregation."""
    IMMEDIATE = "immediate"      # Real-time individual errors
    WINDOWED = "windowed"        # Time-windowed aggregation
    PATTERN = "pattern"          # Pattern-based grouping
    TREND = "trend"             # Trend analysis
    PREDICTIVE = "predictive"   # Predictive analysis


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorSignature:
    """Unique signature for error patterns."""
    error_type: str
    module: str
    function: str
    pattern_hash: str
    key_terms: List[str] = field(default_factory=list)


@dataclass
class ErrorPattern:
    """Aggregated error pattern."""
    signature: ErrorSignature
    count: int = 0
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)
    severity_distribution: Dict[ErrorSeverity, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    affected_users: Set[str] = field(default_factory=set)
    affected_operations: Set[str] = field(default_factory=set)
    sample_errors: List[Dict[str, Any]] = field(default_factory=list)
    trend_score: float = 0.0


@dataclass
class ErrorTrend:
    """Error trend analysis data."""
    pattern: ErrorPattern
    time_windows: List[Tuple[datetime, int]] = field(default_factory=list)
    growth_rate: float = 0.0
    acceleration: float = 0.0
    projection: Optional[int] = None
    is_spike: bool = False
    is_sustained: bool = False


@dataclass
class AlertRule:
    """Rule for generating alerts."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression
    severity: AlertSeverity
    threshold_count: int = 0
    threshold_rate: float = 0.0
    time_window_minutes: int = 60
    cooldown_minutes: int = 30
    active: bool = True


@dataclass
class ErrorAlert:
    """Generated error alert."""
    alert_id: str
    rule: AlertRule
    pattern: ErrorPattern
    trend: Optional[ErrorTrend]
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    message: str = ""


class ErrorSignatureExtractor:
    """Extracts unique signatures from errors."""
    
    def __init__(self):
        """Initialize signature extractor."""
        self.key_terms = {
            'connection', 'timeout', 'permission', 'not found',
            'memory', 'disk', 'network', 'authentication',
            'validation', 'constraint', 'deadlock', 'overflow'
        }
    
    def extract_signature(self, error_data: Dict[str, Any]) -> ErrorSignature:
        """Extract error signature from error data."""
        error_type = error_data.get('error_type', 'Unknown')
        module = error_data.get('module', 'unknown')
        function = error_data.get('function', 'unknown')
        message = str(error_data.get('message', '')).lower()
        
        # Extract key terms from error message
        key_terms = [
            term for term in self.key_terms
            if term in message
        ]
        
        # Create pattern hash
        pattern_components = [
            error_type,
            module,
            function,
            ' '.join(sorted(key_terms))
        ]
        
        pattern_string = '|'.join(pattern_components)
        pattern_hash = hashlib.md5(pattern_string.encode()).hexdigest()[:16]
        
        return ErrorSignature(
            error_type=error_type,
            module=module,
            function=function,
            pattern_hash=pattern_hash,
            key_terms=key_terms
        )


class ErrorAggregator:
    """Aggregates errors into patterns."""
    
    def __init__(
        self,
        window_size_minutes: int = 60,
        max_samples_per_pattern: int = 10
    ):
        """Initialize error aggregator."""
        self.window_size = timedelta(minutes=window_size_minutes)
        self.max_samples = max_samples_per_pattern
        
        self.signature_extractor = ErrorSignatureExtractor()
        self.patterns: Dict[str, ErrorPattern] = {}
        self.error_history: List[Tuple[datetime, Dict[str, Any]]] = []
        
        # Cleanup tracking
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(hours=1)
    
    def add_error(self, error_data: Dict[str, Any]) -> ErrorPattern:
        """Add error to aggregation."""
        timestamp = error_data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        # Extract signature
        signature = self.signature_extractor.extract_signature(error_data)
        
        # Get or create pattern
        pattern = self.patterns.get(signature.pattern_hash)
        if not pattern:
            pattern = ErrorPattern(signature=signature)
            self.patterns[signature.pattern_hash] = pattern
        
        # Update pattern
        pattern.count += 1
        pattern.last_occurrence = timestamp
        
        # Update severity distribution
        severity = error_data.get('severity', ErrorSeverity.MEDIUM)
        if isinstance(severity, str):
            severity = ErrorSeverity(severity)
        pattern.severity_distribution[severity] += 1
        
        # Track affected entities
        if 'user_id' in error_data:
            pattern.affected_users.add(error_data['user_id'])
        if 'operation_id' in error_data:
            pattern.affected_operations.add(error_data['operation_id'])
        
        # Store sample error
        if len(pattern.sample_errors) < self.max_samples:
            pattern.sample_errors.append({
                'timestamp': timestamp.isoformat(),
                'message': error_data.get('message', ''),
                'context': error_data.get('context', {})
            })
        
        # Add to history
        self.error_history.append((timestamp, error_data))
        
        # Periodic cleanup
        if datetime.now() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data()
        
        return pattern
    
    def get_patterns_in_window(
        self,
        window_minutes: int = 60
    ) -> List[ErrorPattern]:
        """Get error patterns within time window."""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        return [
            pattern for pattern in self.patterns.values()
            if pattern.last_occurrence >= cutoff_time
        ]
    
    def get_top_patterns(
        self,
        limit: int = 10,
        window_minutes: int = 60
    ) -> List[ErrorPattern]:
        """Get top error patterns by count."""
        patterns = self.get_patterns_in_window(window_minutes)
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:limit]
    
    def _cleanup_old_data(self) -> None:
        """Clean up old error data."""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        # Clean history
        self.error_history = [
            (timestamp, data) for timestamp, data in self.error_history
            if timestamp >= cutoff_time
        ]
        
        # Clean old patterns
        patterns_to_remove = [
            pattern_hash for pattern_hash, pattern in self.patterns.items()
            if pattern.last_occurrence < cutoff_time
        ]
        
        for pattern_hash in patterns_to_remove:
            del self.patterns[pattern_hash]
        
        self.last_cleanup = datetime.now()
        
        logger.info(
            f"Cleaned up {len(patterns_to_remove)} old patterns, "
            f"{len(self.error_history)} history entries remain"
        )


class ErrorTrendAnalyzer:
    """Analyzes error trends and patterns."""
    
    def __init__(self, analysis_window_hours: int = 24):
        """Initialize trend analyzer."""
        self.analysis_window = timedelta(hours=analysis_window_hours)
        self.spike_threshold = 5.0  # 5x normal rate
        self.sustained_threshold_minutes = 30
    
    def analyze_pattern_trend(
        self,
        pattern: ErrorPattern,
        error_history: List[Tuple[datetime, Dict[str, Any]]]
    ) -> ErrorTrend:
        """Analyze trend for specific error pattern."""
        # Filter history for this pattern
        pattern_history = [
            (timestamp, data) for timestamp, data in error_history
            if self._matches_pattern(data, pattern.signature)
        ]
        
        # Create time windows
        time_windows = self._create_time_windows(pattern_history)
        
        # Calculate trend metrics
        growth_rate = self._calculate_growth_rate(time_windows)
        acceleration = self._calculate_acceleration(time_windows)
        
        # Detect patterns
        is_spike = self._detect_spike(time_windows)
        is_sustained = self._detect_sustained_error(time_windows)
        
        # Project future occurrences
        projection = self._project_future_occurrences(time_windows, growth_rate)
        
        return ErrorTrend(
            pattern=pattern,
            time_windows=time_windows,
            growth_rate=growth_rate,
            acceleration=acceleration,
            projection=projection,
            is_spike=is_spike,
            is_sustained=is_sustained
        )
    
    def _matches_pattern(
        self,
        error_data: Dict[str, Any],
        signature: ErrorSignature
    ) -> bool:
        """Check if error matches pattern signature."""
        return (
            error_data.get('error_type') == signature.error_type and
            error_data.get('module') == signature.module and
            error_data.get('function') == signature.function
        )
    
    def _create_time_windows(
        self,
        pattern_history: List[Tuple[datetime, Dict[str, Any]]],
        window_minutes: int = 10
    ) -> List[Tuple[datetime, int]]:
        """Create time windows with error counts."""
        if not pattern_history:
            return []
        
        window_size = timedelta(minutes=window_minutes)
        start_time = pattern_history[0][0]
        end_time = datetime.now()
        
        windows = []
        current_time = start_time
        
        while current_time < end_time:
            window_end = current_time + window_size
            
            # Count errors in this window
            count = sum(
                1 for timestamp, _ in pattern_history
                if current_time <= timestamp < window_end
            )
            
            windows.append((current_time, count))
            current_time = window_end
        
        return windows
    
    def _calculate_growth_rate(
        self,
        time_windows: List[Tuple[datetime, int]]
    ) -> float:
        """Calculate error growth rate."""
        if len(time_windows) < 2:
            return 0.0
        
        # Use linear regression on recent windows
        recent_windows = time_windows[-10:]  # Last 10 windows
        
        if len(recent_windows) < 2:
            return 0.0
        
        # Simple slope calculation
        x_values = list(range(len(recent_windows)))
        y_values = [count for _, count in recent_windows]
        
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        
        if n * sum_x2 - sum_x * sum_x == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope
    
    def _calculate_acceleration(
        self,
        time_windows: List[Tuple[datetime, int]]
    ) -> float:
        """Calculate acceleration in error rate."""
        if len(time_windows) < 3:
            return 0.0
        
        # Calculate acceleration as second derivative
        recent_counts = [count for _, count in time_windows[-5:]]
        
        if len(recent_counts) < 3:
            return 0.0
        
        # Simple second difference
        first_diffs = [
            recent_counts[i + 1] - recent_counts[i]
            for i in range(len(recent_counts) - 1)
        ]
        
        second_diffs = [
            first_diffs[i + 1] - first_diffs[i]
            for i in range(len(first_diffs) - 1)
        ]
        
        return sum(second_diffs) / len(second_diffs) if second_diffs else 0.0
    
    def _detect_spike(self, time_windows: List[Tuple[datetime, int]]) -> bool:
        """Detect error spikes."""
        if len(time_windows) < 5:
            return False
        
        recent_counts = [count for _, count in time_windows[-5:]]
        baseline = sum(recent_counts[:-1]) / len(recent_counts[:-1])
        
        if baseline == 0:
            return recent_counts[-1] > 10  # Arbitrary spike threshold
        
        return recent_counts[-1] / baseline >= self.spike_threshold
    
    def _detect_sustained_error(
        self,
        time_windows: List[Tuple[datetime, int]]
    ) -> bool:
        """Detect sustained error patterns."""
        if not time_windows:
            return False
        
        # Check if errors have been occurring consistently
        sustained_windows = sum(
            1 for _, count in time_windows[-6:]  # Last hour (6 * 10min windows)
            if count > 0
        )
        
        return sustained_windows >= 4  # At least 4 out of 6 windows have errors
    
    def _project_future_occurrences(
        self,
        time_windows: List[Tuple[datetime, int]],
        growth_rate: float
    ) -> Optional[int]:
        """Project future error occurrences."""
        if not time_windows or growth_rate <= 0:
            return None
        
        # Project for next window based on trend
        recent_average = sum(count for _, count in time_windows[-3:]) / 3
        projection = int(recent_average + growth_rate * 3)
        
        return max(0, projection)


class AlertEngine:
    """Generates alerts based on error patterns and trends."""
    
    def __init__(self):
        """Initialize alert engine."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[ErrorAlert] = []
        self.alert_history: Dict[str, datetime] = {}  # Rule cooldowns
        
        # Setup default alert rules
        self._setup_default_rules()
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules."""
        self.rules = {
            'high_error_rate': AlertRule(
                rule_id='high_error_rate',
                name='High Error Rate',
                description='Error rate exceeds threshold',
                condition='pattern.count > 50 and window_minutes <= 60',
                severity=AlertSeverity.HIGH,
                threshold_count=50,
                time_window_minutes=60
            ),
            'critical_error_spike': AlertRule(
                rule_id='critical_error_spike',
                name='Critical Error Spike',
                description='Sudden spike in critical errors',
                condition='trend.is_spike and pattern.severity_distribution.get("critical", 0) > 0',
                severity=AlertSeverity.CRITICAL,
                time_window_minutes=30
            ),
            'sustained_errors': AlertRule(
                rule_id='sustained_errors',
                name='Sustained Error Pattern',
                description='Errors occurring consistently over time',
                condition='trend.is_sustained and pattern.count > 20',
                severity=AlertSeverity.MEDIUM,
                time_window_minutes=120
            ),
            'new_error_pattern': AlertRule(
                rule_id='new_error_pattern',
                name='New Error Pattern',
                description='Previously unseen error pattern',
                condition='pattern.count >= 5 and pattern_age_minutes < 30',
                severity=AlertSeverity.MEDIUM,
                threshold_count=5,
                time_window_minutes=30
            )
        }
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add custom alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name}")
    
    def evaluate_pattern(
        self,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend] = None
    ) -> List[ErrorAlert]:
        """Evaluate pattern against alert rules."""
        alerts = []
        
        for rule in self.rules.values():
            if not rule.active:
                continue
            
            # Check cooldown
            if self._is_in_cooldown(rule.rule_id):
                continue
            
            # Evaluate rule condition
            if self._evaluate_rule_condition(rule, pattern, trend):
                alert = self._create_alert(rule, pattern, trend)
                alerts.append(alert)
                
                # Set cooldown
                self.alert_history[rule.rule_id] = datetime.now()
        
        self.alerts.extend(alerts)
        return alerts
    
    def _is_in_cooldown(self, rule_id: str) -> bool:
        """Check if rule is in cooldown period."""
        if rule_id not in self.alert_history:
            return False
        
        rule = self.rules[rule_id]
        last_alert = self.alert_history[rule_id]
        cooldown_period = timedelta(minutes=rule.cooldown_minutes)
        
        return datetime.now() - last_alert < cooldown_period
    
    def _evaluate_rule_condition(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> bool:
        """Evaluate rule condition."""
        try:
            # Prepare evaluation context
            context = {
                'pattern': pattern,
                'trend': trend,
                'window_minutes': rule.time_window_minutes,
                'pattern_age_minutes': (
                    datetime.now() - pattern.first_occurrence
                ).total_seconds() / 60
            }
            
            # Evaluate condition
            return eval(rule.condition, {'__builtins__': {}}, context)
            
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return False
    
    def _create_alert(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> ErrorAlert:
        """Create alert from rule and pattern."""
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        # Generate alert message
        message = self._generate_alert_message(rule, pattern, trend)
        
        return ErrorAlert(
            alert_id=alert_id,
            rule=rule,
            pattern=pattern,
            trend=trend,
            message=message
        )
    
    def _generate_alert_message(
        self,
        rule: AlertRule,
        pattern: ErrorPattern,
        trend: Optional[ErrorTrend]
    ) -> str:
        """Generate alert message."""
        message_parts = [
            f"Alert: {rule.name}",
            f"Error Pattern: {pattern.signature.error_type} in {pattern.signature.module}",
            f"Count: {pattern.count}",
            f"Affected Users: {len(pattern.affected_users)}",
        ]
        
        if trend:
            if trend.is_spike:
                message_parts.append("⚠️ Error spike detected")
            if trend.is_sustained:
                message_parts.append("📈 Sustained error pattern")
            if trend.projection:
                message_parts.append(f"Projected: {trend.projection} errors next window")
        
        return " | ".join(message_parts)


class ErrorAggregationSystem:
    """Main error aggregation and alerting system."""
    
    def __init__(self):
        """Initialize aggregation system."""
        self.aggregator = ErrorAggregator()
        self.trend_analyzer = ErrorTrendAnalyzer()
        self.alert_engine = AlertEngine()
        
        # Processing control
        self.processing_active = False
        self.process_task: Optional[asyncio.Task] = None
        self.process_interval = 30  # seconds
    
    async def process_error(self, error_data: Dict[str, Any]) -> None:
        """Process single error through aggregation pipeline."""
        # Add to aggregator
        pattern = self.aggregator.add_error(error_data)
        
        # Analyze trends for this pattern
        trend = self.trend_analyzer.analyze_pattern_trend(
            pattern, self.aggregator.error_history
        )
        
        # Check for alerts
        alerts = self.alert_engine.evaluate_pattern(pattern, trend)
        
        # Log any new alerts
        for alert in alerts:
            logger.warning(f"Error alert generated: {alert.message}")
    
    async def start_processing(self) -> None:
        """Start background processing."""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.process_task = asyncio.create_task(self._processing_loop())
        logger.info("Error aggregation processing started")
    
    async def stop_processing(self) -> None:
        """Stop background processing."""
        self.processing_active = False
        if self.process_task:
            self.process_task.cancel()
            try:
                await self.process_task
            except asyncio.CancelledError:
                pass
        logger.info("Error aggregation processing stopped")
    
    async def _processing_loop(self) -> None:
        """Background processing loop."""
        while self.processing_active:
            try:
                # Periodic trend analysis for all patterns
                patterns = self.aggregator.get_patterns_in_window(60)
                
                for pattern in patterns:
                    trend = self.trend_analyzer.analyze_pattern_trend(
                        pattern, self.aggregator.error_history
                    )
                    
                    # Check for alerts
                    self.alert_engine.evaluate_pattern(pattern, trend)
                
                await asyncio.sleep(self.process_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error aggregation processing error: {e}")
                await asyncio.sleep(self.process_interval)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status and metrics."""
        return {
            'total_patterns': len(self.aggregator.patterns),
            'active_patterns': len(self.aggregator.get_patterns_in_window(60)),
            'total_alerts': len(self.alert_engine.alerts),
            'unresolved_alerts': len([
                a for a in self.alert_engine.alerts
                if not a.resolved
            ]),
            'processing_active': self.processing_active,
            'top_patterns': [
                {
                    'signature': p.signature.pattern_hash,
                    'count': p.count,
                    'error_type': p.signature.error_type,
                    'module': p.signature.module
                }
                for p in self.aggregator.get_top_patterns(5)
            ]
        }


# Global error aggregation system
error_aggregation_system = ErrorAggregationSystem()