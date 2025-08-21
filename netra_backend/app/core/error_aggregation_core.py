"""Core error aggregation system - main orchestration and pattern management.

Provides the main ErrorAggregationSystem and ErrorAggregator classes
with modular error processing pipeline.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from netra_backend.app.core.error_codes import ErrorSeverity
from netra_backend.app.logging_config import central_logger
from netra_backend.app.core.error_aggregation_utils import ErrorPattern, ErrorSignatureExtractor
from netra_backend.app.core.error_aggregation_trend import ErrorTrendAnalyzer
from netra_backend.app.core.error_aggregation_alerts import AlertEngine

logger = central_logger.get_logger(__name__)


class ErrorAggregator:
    """Aggregates errors into patterns with time-based cleanup."""
    
    def __init__(self, window_size_minutes: int = 60, max_samples_per_pattern: int = 10):
        """Initialize error aggregator with configurable parameters."""
        self.window_size = timedelta(minutes=window_size_minutes)
        self.max_samples = max_samples_per_pattern
        self.signature_extractor = ErrorSignatureExtractor()
        self.patterns: Dict[str, ErrorPattern] = {}
        self.error_history: List[tuple[datetime, Dict[str, Any]]] = []
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(hours=1)
    
    def add_error(self, error_data: Dict[str, Any]) -> ErrorPattern:
        """Add error to aggregation pipeline."""
        timestamp = self._extract_timestamp(error_data)
        signature = self.signature_extractor.extract_signature(error_data)
        pattern = self._get_or_create_pattern(signature)
        self._complete_error_processing(pattern, error_data, timestamp)
        return pattern
    
    def _complete_error_processing(self, pattern: ErrorPattern, error_data: Dict[str, Any], timestamp: datetime) -> None:
        """Complete error processing pipeline."""
        self._process_error_data(pattern, error_data, timestamp)
        self._add_to_history(timestamp, error_data)
        self._cleanup_if_needed()
    
    def get_patterns_in_window(self, window_minutes: int = 60) -> List[ErrorPattern]:
        """Get error patterns within specified time window."""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        return [
            pattern for pattern in self.patterns.values()
            if pattern.last_occurrence >= cutoff_time
        ]
    
    def get_top_patterns(self, limit: int = 10, window_minutes: int = 60) -> List[ErrorPattern]:
        """Get top error patterns by count within window."""
        patterns = self.get_patterns_in_window(window_minutes)
        return sorted(patterns, key=lambda p: p.count, reverse=True)[:limit]
    
    def _extract_timestamp(self, error_data: Dict[str, Any]) -> datetime:
        """Extract and validate timestamp from error data."""
        timestamp = error_data.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return timestamp
    
    def _process_error_data(self, pattern: ErrorPattern, error_data: Dict[str, Any], timestamp: datetime) -> None:
        """Process error data for pattern update."""
        self._update_pattern(pattern, error_data, timestamp)
        self._store_sample_error(pattern, error_data, timestamp)
    
    def _get_or_create_pattern(self, signature) -> ErrorPattern:
        """Get existing pattern or create new one."""
        pattern = self.patterns.get(signature.pattern_hash)
        if not pattern:
            pattern = ErrorPattern(signature=signature)
            self.patterns[signature.pattern_hash] = pattern
        return pattern
    
    def _update_pattern(self, pattern: ErrorPattern, error_data: Dict[str, Any], timestamp: datetime) -> None:
        """Update pattern with new error occurrence."""
        pattern.count += 1
        pattern.last_occurrence = timestamp
        self._update_severity_distribution(pattern, error_data)
        self._track_affected_entities(pattern, error_data)
    
    def _update_severity_distribution(self, pattern: ErrorPattern, error_data: Dict[str, Any]) -> None:
        """Update pattern severity distribution."""
        severity = error_data.get('severity', ErrorSeverity.MEDIUM)
        if isinstance(severity, str):
            severity = ErrorSeverity(severity)
        pattern.severity_distribution[severity] += 1
    
    def _track_affected_entities(self, pattern: ErrorPattern, error_data: Dict[str, Any]) -> None:
        """Track affected users and operations."""
        if 'user_id' in error_data:
            pattern.affected_users.add(error_data['user_id'])
        if 'operation_id' in error_data:
            pattern.affected_operations.add(error_data['operation_id'])
    
    def _store_sample_error(self, pattern: ErrorPattern, error_data: Dict[str, Any], timestamp: datetime) -> None:
        """Store sample error if under limit."""
        if len(pattern.sample_errors) < self.max_samples:
            sample = self._create_sample_entry(error_data, timestamp)
            pattern.sample_errors.append(sample)
    
    def _create_sample_entry(self, error_data: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
        """Create sample error entry."""
        return {
            'timestamp': timestamp.isoformat(),
            'message': error_data.get('message', ''),
            'context': error_data.get('context', {})
        }
    
    def _add_to_history(self, timestamp: datetime, error_data: Dict[str, Any]) -> None:
        """Add error to historical tracking."""
        self.error_history.append((timestamp, error_data))
    
    def _cleanup_if_needed(self) -> None:
        """Trigger cleanup if interval elapsed."""
        if datetime.now() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_data()
    
    def _cleanup_old_data(self) -> None:
        """Clean up old error data beyond retention period."""
        cutoff_time = datetime.now() - timedelta(days=7)
        self._cleanup_history(cutoff_time)
        removed_count = self._cleanup_patterns(cutoff_time)
        self.last_cleanup = datetime.now()
        self._log_cleanup_results(removed_count)
    
    def _cleanup_history(self, cutoff_time: datetime) -> None:
        """Remove old entries from error history."""
        self.error_history = [
            (timestamp, data) for timestamp, data in self.error_history
            if timestamp >= cutoff_time
        ]
    
    def _cleanup_patterns(self, cutoff_time: datetime) -> int:
        """Remove old patterns and return count."""
        patterns_to_remove = self._identify_old_patterns(cutoff_time)
        self._remove_old_patterns(patterns_to_remove)
        return len(patterns_to_remove)
    
    def _identify_old_patterns(self, cutoff_time: datetime) -> List[str]:
        """Identify patterns older than cutoff time."""
        return [
            pattern_hash for pattern_hash, pattern in self.patterns.items()
            if pattern.last_occurrence < cutoff_time
        ]
    
    def _remove_old_patterns(self, patterns_to_remove: List[str]) -> None:
        """Remove old patterns from storage."""
        for pattern_hash in patterns_to_remove:
            del self.patterns[pattern_hash]
    
    def _log_cleanup_results(self, removed_count: int) -> None:
        """Log cleanup operation results."""
        logger.info(
            f"Cleaned up {removed_count} old patterns, "
            f"{len(self.error_history)} history entries remain"
        )


class ErrorAggregationSystem:
    """Main error aggregation and alerting system orchestrator."""
    
    def __init__(self):
        """Initialize aggregation system components."""
        self.aggregator = ErrorAggregator()
        self.trend_analyzer = ErrorTrendAnalyzer()
        self.alert_engine = AlertEngine()
        self.processing_active = False
        self.process_task: Optional[asyncio.Task] = None
        self.process_interval = 30  # seconds
    
    async def process_error(self, error_data: Dict[str, Any]) -> None:
        """Process single error through complete pipeline."""
        pattern = self.aggregator.add_error(error_data)
        trend = self._analyze_pattern_trend(pattern)
        alerts = self.alert_engine.evaluate_pattern(pattern, trend)
        self._log_generated_alerts(alerts)
    
    async def start_processing(self) -> None:
        """Start background processing if not active."""
        if self.processing_active:
            return
        self.processing_active = True
        self.process_task = asyncio.create_task(self._processing_loop())
        logger.info("Error aggregation processing started")
    
    async def stop_processing(self) -> None:
        """Stop background processing gracefully."""
        self.processing_active = False
        if self.process_task:
            await self._cancel_process_task()
        logger.info("Error aggregation processing stopped")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status and metrics."""
        basic_status = self._get_basic_status()
        extended_status = self._get_extended_status()
        return {**basic_status, **extended_status}
    
    def _get_basic_status(self) -> Dict[str, Any]:
        """Get basic system status metrics."""
        return {
            'total_patterns': len(self.aggregator.patterns),
            'active_patterns': len(self.aggregator.get_patterns_in_window(60)),
            'total_alerts': len(self.alert_engine.alerts),
            'processing_active': self.processing_active
        }
    
    def _get_extended_status(self) -> Dict[str, Any]:
        """Get extended system status metrics."""
        return {
            'unresolved_alerts': self._count_unresolved_alerts(),
            'top_patterns': self._get_top_patterns_summary()
        }
    
    def _analyze_pattern_trend(self, pattern: ErrorPattern):
        """Analyze trend for given pattern."""
        return self.trend_analyzer.analyze_pattern_trend(
            pattern, self.aggregator.error_history
        )
    
    def _log_generated_alerts(self, alerts: List) -> None:
        """Log newly generated alerts."""
        for alert in alerts:
            logger.warning(f"Error alert generated: {alert.message}")
    
    async def _cancel_process_task(self) -> None:
        """Cancel processing task with proper exception handling."""
        self.process_task.cancel()
        try:
            await self.process_task
        except asyncio.CancelledError:
            pass
    
    async def _processing_loop(self) -> None:
        """Background processing loop for periodic analysis."""
        while self.processing_active:
            if not await self._try_process_patterns():
                break
    
    async def _try_process_patterns(self) -> bool:
        """Try to process patterns with error handling."""
        try:
            await self._process_all_patterns()
            await asyncio.sleep(self.process_interval)
            return True
        except asyncio.CancelledError:
            return False
        except Exception as e:
            await self._handle_processing_error(e)
            return True
    
    async def _handle_processing_error(self, error: Exception) -> None:
        """Handle processing loop errors."""
        logger.error(f"Error aggregation processing error: {error}")
        await asyncio.sleep(self.process_interval)
    
    async def _process_all_patterns(self) -> None:
        """Process all patterns for trend analysis and alerting."""
        patterns = self.aggregator.get_patterns_in_window(60)
        for pattern in patterns:
            trend = self._analyze_pattern_trend(pattern)
            self.alert_engine.evaluate_pattern(pattern, trend)
    
    def _count_unresolved_alerts(self) -> int:
        """Count unresolved alerts."""
        return len([
            a for a in self.alert_engine.alerts
            if not a.resolved
        ])
    
    def _get_top_patterns_summary(self) -> List[Dict[str, Any]]:
        """Get summary of top error patterns."""
        top_patterns = self.aggregator.get_top_patterns(5)
        return [self._create_pattern_summary(p) for p in top_patterns]
    
    def _create_pattern_summary(self, pattern: ErrorPattern) -> Dict[str, Any]:
        """Create summary for single pattern."""
        return {
            'signature': pattern.signature.pattern_hash,
            'count': pattern.count,
            'error_type': pattern.signature.error_type,
            'module': pattern.signature.module
        }


# Global error aggregation system instance
error_aggregation_system = ErrorAggregationSystem()