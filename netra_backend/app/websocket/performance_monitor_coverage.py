"""WebSocket Performance Monitor Coverage Tracking.

Handles monitoring coverage metrics and failure tracking.
"""

from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class MonitoringCoverageTracker:
    """Tracks monitoring coverage and check failures."""
    
    def __init__(self):
        self.coverage = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "check_results": deque(maxlen=100)
        }
    
    def update_coverage_metrics(self, total_checks: int) -> None:
        """Update monitoring coverage metrics."""
        self.coverage["total_checks"] += total_checks
    
    async def handle_check_results(self, check_names: List[str], results: List[Any]) -> None:
        """Handle individual check results and log failures."""
        for check_name, result in zip(check_names, results):
            if isinstance(result, Exception):
                await self._handle_check_failure(check_name, result)
            else:
                self._record_check_success(check_name)
    
    async def _handle_check_failure(self, check_name: str, error: Exception) -> None:
        """Handle individual monitoring check failure."""
        self.coverage["failed_checks"] += 1
        self._record_check_result(check_name, False, str(error))
        logger.warning(f"Monitoring check '{check_name}' failed: {error}")
    
    def _record_check_success(self, check_name: str) -> None:
        """Record successful monitoring check."""
        self.coverage["successful_checks"] += 1
        self._record_check_result(check_name, True, None)
    
    def _record_check_result(self, check_name: str, success: bool, error: Optional[str]) -> None:
        """Record monitoring check result for coverage tracking."""
        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_name": check_name,
            "success": success,
            "error": error
        }
        self.coverage["check_results"].append(result)
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get monitoring coverage summary."""
        total = self.coverage["total_checks"]
        if total == 0:
            return {"coverage_percentage": 100.0, "recent_failures": 0}
        success_rate = (self.coverage["successful_checks"] / total) * 100
        recent_failures = self._count_recent_failures()
        return {"coverage_percentage": success_rate, "recent_failures": recent_failures}
    
    def _count_recent_failures(self) -> int:
        """Count recent monitoring check failures."""
        recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        return sum(1 for result in self.coverage["check_results"] 
                  if not result["success"] and 
                  datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00')) > recent_cutoff)
    
    def reset_coverage(self) -> None:
        """Reset coverage tracking."""
        self.coverage = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "check_results": deque(maxlen=100)
        }