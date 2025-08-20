"""Triage Processing Monitoring Helpers

Helper functions for processing monitoring to maintain 450-line module limit.
Contains metrics tracking, performance monitoring, and WebSocket enhancements.
"""

import time
from typing import Dict, Any
from app.logging_config import central_logger
from app.agents.base.monitoring import ExecutionMonitor, ExecutionMetrics

logger = central_logger.get_logger(__name__)


class TriageProcessingMonitor:
    """Monitoring helper for triage processing operations."""
    
    def __init__(self, monitor: ExecutionMonitor = None):
        self.monitor = monitor or ExecutionMonitor()
        self.metrics = ExecutionMetrics()
    
    def build_enhanced_metadata_updates(self, start_time: float, retry_count: int, 
                                      max_retries: int = 3) -> Dict[str, Any]:
        """Build enhanced metadata updates with monitoring data."""
        duration_ms = int((time.time() - start_time) * 1000)
        self.metrics.execution_time_ms = duration_ms
        base_metadata = self._build_base_metadata(duration_ms, retry_count, max_retries)
        base_metadata.update(self._build_extended_metadata(duration_ms))
        return base_metadata
    
    def _build_base_metadata(self, duration_ms: int, retry_count: int, max_retries: int) -> Dict[str, Any]:
        """Build base metadata structure."""
        return {
            "triage_duration_ms": duration_ms,
            "cache_hit": False,
            "retry_count": retry_count,
            "fallback_used": retry_count >= max_retries
        }
    
    def _build_extended_metadata(self, duration_ms: int) -> Dict[str, Any]:
        """Build extended metadata structure."""
        return {
            "llm_tokens_used": self.metrics.llm_tokens_used,
            "processing_time_ms": duration_ms
        }
    
    def extract_enhanced_performance_metrics(self, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract enhanced performance metrics from triage result."""
        base_metrics = self._extract_base_performance_metrics(triage_result)
        metadata = triage_result.get('metadata', {})
        base_metrics.update({
            'tokens_used': metadata.get('llm_tokens_used', 0),
            'retry_count': metadata.get('retry_count', 0),
            'fallback_used': metadata.get('fallback_used', False)
        })
        return base_metrics
    
    def _extract_base_performance_metrics(self, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract base performance metrics from triage result."""
        metadata = triage_result.get('metadata', {})
        return {
            'category': triage_result.get('category'),
            'confidence': triage_result.get('confidence_score', 0),
            'duration_ms': metadata.get('triage_duration_ms'),
            'cache_hit': metadata.get('cache_hit')
        }
    
    def format_enhanced_performance_log_message(self, run_id: str, 
                                              metrics: Dict[str, Any]) -> str:
        """Format enhanced performance log message."""
        return (
            f"Triage completed for run_id {run_id}: "
            f"category={metrics['category']}, confidence={metrics['confidence']}, "
            f"duration={metrics['duration_ms']}ms, cache_hit={metrics['cache_hit']}, "
            f"tokens_used={metrics.get('tokens_used', 0)}, "
            f"retry_count={metrics.get('retry_count', 0)}"
        )
    
    def record_fallback_metrics(self) -> None:
        """Record fallback usage metrics."""
        self.metrics.retry_count += 1
    
    def record_success_metrics(self, triage_result: Dict[str, Any]) -> None:
        """Record success metrics from triage result."""
        metadata = triage_result.get('metadata', {})
        if 'llm_tokens_used' in metadata:
            self.metrics.llm_tokens_used += metadata['llm_tokens_used']
    
    def record_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Record performance metrics for analysis."""
        # Performance metrics are logged and can be used for optimization
        pass
    
    def get_current_metrics(self) -> ExecutionMetrics:
        """Get current execution metrics."""
        return self.metrics
    
    def reset_metrics(self) -> None:
        """Reset metrics for new processing cycle."""
        self.metrics = ExecutionMetrics()


class TriageWebSocketMonitor:
    """WebSocket monitoring helper for triage operations."""
    
    def __init__(self):
        self.metrics = ExecutionMetrics()
        self.logger = logger
    
    def build_final_update_message(self, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Build final update message with enhanced information."""
        return {
            "status": "processed",
            "message": self._create_status_message(triage_result),
            "result": triage_result,
            "metrics": self._extract_message_metrics(triage_result)
        }
    
    def _create_status_message(self, triage_result: Dict[str, Any]) -> str:
        """Create status message with category and confidence."""
        category = triage_result.get('category', 'Unknown')
        confidence = triage_result.get('confidence_score', 0)
        return f"Request categorized as: {category} with confidence {confidence:.2f}"
    
    def _extract_message_metrics(self, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metrics for WebSocket message."""
        metadata = triage_result.get('metadata', {})
        return {
            "duration_ms": metadata.get('triage_duration_ms', 0),
            "fallback_used": metadata.get('fallback_used', False),
            "tokens_used": metadata.get('llm_tokens_used', 0),
            "retry_count": metadata.get('retry_count', 0)
        }
    
    def record_websocket_metrics(self) -> None:
        """Record WebSocket message metrics."""
        self.metrics.websocket_messages_sent += 1
    
    def get_websocket_metrics(self) -> Dict[str, int]:
        """Get WebSocket-specific metrics."""
        return {
            "messages_sent": self.metrics.websocket_messages_sent,
            "total_tokens": self.metrics.llm_tokens_used
        }


class TriageProcessingErrorHelper:
    """Error handling helper for triage processing."""
    
    def __init__(self):
        self.logger = logger
        self.metrics = ExecutionMetrics()
    
    def create_error_fallback_result(self, state, start_time: float = None) -> Dict[str, Any]:
        """Create error fallback result with monitoring metadata."""
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
        base_result = self._create_error_result_structure()
        base_result["metadata"] = self._create_error_metadata(duration_ms)
        return base_result
    
    def _create_error_result_structure(self) -> Dict[str, Any]:
        """Create error result structure."""
        return {
            "category": "Error",
            "confidence_score": 0.0,
            "user_intent": {"intent": "unknown", "confidence": 0.0},
            "extracted_entities": {},
            "tool_recommendations": []
        }
    
    def _create_error_metadata(self, duration_ms: int) -> Dict[str, Any]:
        """Create error metadata."""
        return {
            "triage_duration_ms": duration_ms,
            "error_details": "Processing error occurred",
            "fallback_used": True,
            "retry_count": 0
        }
    
    def log_processing_error(self, error: Exception, run_id: str) -> None:
        """Log processing error with context."""
        self.logger.error(f"Triage processing error for run_id {run_id}: {error}")
        self.metrics.circuit_breaker_trips += 1
    
    def create_fallback_result_with_monitoring(self, state, run_id: str, 
                                             start_time: float = None) -> Dict[str, Any]:
        """Create fallback result with comprehensive monitoring data."""
        duration_ms = int((time.time() - start_time) * 1000) if start_time else 0
        base_result = self._create_fallback_result_structure()
        base_result["metadata"] = self._create_fallback_monitoring_metadata(duration_ms, run_id)
        return base_result
    
    def _create_fallback_result_structure(self) -> Dict[str, Any]:
        """Create fallback result structure."""
        return {
            "category": "General Inquiry",
            "confidence_score": 0.3,
            "user_intent": {"intent": "general", "confidence": 0.3},
            "extracted_entities": {},
            "tool_recommendations": []
        }
    
    def _create_fallback_monitoring_metadata(self, duration_ms: int, run_id: str) -> Dict[str, Any]:
        """Create fallback monitoring metadata."""
        return {
            "triage_duration_ms": duration_ms,
            "fallback_used": True,
            "error_details": f"Fallback activated for {run_id}",
            "retry_count": 0
        }