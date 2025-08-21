"""Error reporting and monitoring for Triage Sub Agent operations."""

import asyncio
from typing import Any, Dict, List

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TriageErrorReporter:
    """Handles error reporting and monitoring for triage operations."""
    
    def __init__(self):
        self.error_metrics = {
            'intent_detection_failures': 0,
            'entity_extraction_failures': 0,
            'tool_recommendation_failures': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
    
    def log_intent_recovery(self, run_id: str, fallback_result: Dict[str, Any]) -> None:
        """Log successful intent detection recovery."""
        logger.info(
            f"Intent detection recovered with keyword fallback",
            run_id=run_id,
            detected_intent=fallback_result.get('intent'),
            confidence=fallback_result.get('confidence'),
            method=fallback_result.get('method')
        )
        self._increment_metric('successful_recoveries')
    
    def log_entity_recovery(self, run_id: str, fallback_result: Dict[str, Any]) -> None:
        """Log successful entity extraction recovery."""
        logger.info(
            f"Entity extraction recovered with partial results",
            run_id=run_id,
            extracted_entities=fallback_result.get('entities', [])
        )
        self._increment_metric('successful_recoveries')
    
    def log_tool_recovery(self, run_id: str, intent: str, fallback_result: Dict[str, Any]) -> None:
        """Log successful tool recommendation recovery."""
        logger.info(
            f"Tool recommendation recovered with default tools",
            run_id=run_id,
            intent=intent,
            recommended_tools=fallback_result.get('tools', [])
        )
        self._increment_metric('successful_recoveries')
    
    async def log_retry_warning(
        self,
        operation_name: str,
        attempt: int,
        max_retries: int,
        delay: float,
        error: Exception
    ) -> None:
        """Log retry attempt warning."""
        logger.warning(
            f"Triage operation '{operation_name}' failed on attempt {attempt + 1}/{max_retries + 1}. "
            f"Retrying in {delay}s. Error: {error}"
        )
        self._increment_metric('recovery_attempts')
    
    def log_operation_failure(self, operation_name: str, run_id: str, error: Exception) -> None:
        """Log operation failure."""
        logger.error(
            f"Triage operation '{operation_name}' failed completely",
            run_id=run_id,
            error=str(error),
            operation=operation_name
        )
        self._increment_failure_metric(operation_name)
    
    def _increment_failure_metric(self, operation_name: str) -> None:
        """Increment failure metric for specific operation."""
        metric_key = f"{operation_name}_failures"
        if metric_key in self.error_metrics:
            self.error_metrics[metric_key] += 1
    
    def _increment_metric(self, metric_name: str) -> None:
        """Increment a specific metric."""
        if metric_name in self.error_metrics:
            self.error_metrics[metric_name] += 1
    
    def get_error_metrics(self) -> Dict[str, int]:
        """Get current error metrics."""
        return self.error_metrics.copy()
    
    def reset_error_metrics(self) -> None:
        """Reset error metrics to zero."""
        for key in self.error_metrics:
            self.error_metrics[key] = 0
    
    def calculate_success_rate(self) -> Dict[str, float]:
        """Calculate success rates for different operations."""
        success_rates = {}
        
        operations = ['intent_detection', 'entity_extraction', 'tool_recommendation']
        for operation in operations:
            failures = self.error_metrics.get(f"{operation}_failures", 0)
            recoveries = self.error_metrics.get('successful_recoveries', 0)
            total_attempts = failures + recoveries
            
            if total_attempts > 0:
                success_rates[operation] = (recoveries / total_attempts) * 100
            else:
                success_rates[operation] = 100.0
        
        return success_rates
    
    def should_alert(self, operation_name: str, threshold: int = 5) -> bool:
        """Check if error count exceeds alerting threshold."""
        metric_key = f"{operation_name}_failures"
        return self.error_metrics.get(metric_key, 0) >= threshold
    
    def generate_error_report(self) -> Dict[str, Any]:
        """Generate comprehensive error report."""
        return {
            'metrics': self.get_error_metrics(),
            'success_rates': self.calculate_success_rate(),
            'alerts': self._get_active_alerts(),
            'timestamp': self._get_current_timestamp()
        }
    
    def _get_active_alerts(self) -> List[str]:
        """Get list of active alerts based on thresholds."""
        alerts = []
        operations = ['intent_detection', 'entity_extraction', 'tool_recommendation']
        
        for operation in operations:
            if self.should_alert(operation):
                alerts.append(f"High failure rate detected for {operation}")
        
        return alerts
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp for reporting."""
        from datetime import datetime, UTC
        return datetime.now(UTC).isoformat()
    
    def log_recovery_attempt(self, operation_name: str, run_id: str, strategy: str) -> None:
        """Log recovery attempt."""
        logger.info(
            f"Attempting recovery for {operation_name}",
            run_id=run_id,
            strategy=strategy,
            operation=operation_name
        )
    
    def log_recovery_success(self, operation_name: str, run_id: str, strategy: str) -> None:
        """Log successful recovery."""
        logger.info(
            f"Recovery successful for {operation_name}",
            run_id=run_id,
            strategy=strategy,
            operation=operation_name
        )
        self._increment_metric('successful_recoveries')
    
    def log_recovery_failure(self, operation_name: str, run_id: str, strategy: str, error: Exception) -> None:
        """Log failed recovery attempt."""
        logger.error(
            f"Recovery failed for {operation_name}",
            run_id=run_id,
            strategy=strategy,
            operation=operation_name,
            error=str(error)
        )
    
    def calculate_retry_delay(self, attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
        """Calculate exponential backoff delay for retries."""
        delay = base_delay * (2 ** attempt)
        return min(delay, max_delay)
    
    def should_retry(self, attempt: int, max_retries: int) -> bool:
        """Determine if operation should be retried."""
        return attempt < max_retries