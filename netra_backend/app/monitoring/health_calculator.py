"""
Health score calculator for factory status monitoring.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: System health monitoring and alerting
- Value Impact: Provides composite health scores for system components
- Revenue Impact: Critical for Enterprise SLA monitoring
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthScoreCalculator:
    """Calculates composite health scores from various metrics."""
    
    def __init__(self):
        """Initialize health calculator with thresholds."""
        self.thresholds = {
            "cpu": {"warning": 70, "critical": 90},
            "memory": {"warning": 75, "critical": 90},
            "disk": {"warning": 80, "critical": 95},
            "response_time": {"warning": 500, "critical": 1000},  # ms
            "error_rate": {"warning": 0.01, "critical": 0.05},  # percentage
        }
    
    def calculate_overall_health(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall system health score."""
        try:
            scores = {}
            
            # Calculate individual component scores
            if "system" in metrics:
                scores["system"] = self._calculate_system_health(metrics["system"])
            
            if "performance" in metrics:
                scores["performance"] = self._calculate_performance_health(metrics["performance"])
            
            if "code_quality" in metrics:
                scores["code_quality"] = self._calculate_code_quality_health(metrics["code_quality"])
            
            # Calculate composite score
            if scores:
                avg_score = sum(s["score"] for s in scores.values()) / len(scores)
                overall_status = self._score_to_status(avg_score)
            else:
                avg_score = 0
                overall_status = HealthStatus.UNKNOWN
            
            return {
                "overall_score": avg_score,
                "overall_status": overall_status.value,
                "component_scores": scores,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            return {
                "overall_score": 0,
                "overall_status": HealthStatus.UNKNOWN.value,
                "component_scores": {},
                "error": str(e)
            }
    
    def _calculate_system_health(self, system_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate system health score."""
        score = 100
        issues = []
        
        # Check CPU
        if "cpu" in system_metrics:
            cpu_usage = system_metrics["cpu"].get("usage_percent", 0)
            if cpu_usage > self.thresholds["cpu"]["critical"]:
                score -= 30
                issues.append(f"Critical CPU usage: {cpu_usage}%")
            elif cpu_usage > self.thresholds["cpu"]["warning"]:
                score -= 15
                issues.append(f"High CPU usage: {cpu_usage}%")
        
        # Check Memory
        if "memory" in system_metrics:
            mem_usage = system_metrics["memory"].get("usage_percent", 0)
            if mem_usage > self.thresholds["memory"]["critical"]:
                score -= 30
                issues.append(f"Critical memory usage: {mem_usage}%")
            elif mem_usage > self.thresholds["memory"]["warning"]:
                score -= 15
                issues.append(f"High memory usage: {mem_usage}%")
        
        # Check Disk
        if "disk" in system_metrics:
            disk_usage = system_metrics["disk"].get("usage_percent", 0)
            if disk_usage > self.thresholds["disk"]["critical"]:
                score -= 30
                issues.append(f"Critical disk usage: {disk_usage}%")
            elif disk_usage > self.thresholds["disk"]["warning"]:
                score -= 15
                issues.append(f"High disk usage: {disk_usage}%")
        
        return {
            "score": max(0, score),
            "status": self._score_to_status(score).value,
            "issues": issues
        }
    
    def _calculate_performance_health(self, perf_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance health score."""
        score = 100
        issues = []
        
        # Check response times
        if "response_times" in perf_metrics:
            p95_time = perf_metrics["response_times"].get("p95_ms", 0)
            if p95_time > self.thresholds["response_time"]["critical"]:
                score -= 40
                issues.append(f"Critical response time: {p95_time}ms")
            elif p95_time > self.thresholds["response_time"]["warning"]:
                score -= 20
                issues.append(f"Slow response time: {p95_time}ms")
        
        # Check error rate
        if "throughput" in perf_metrics:
            requests_per_sec = perf_metrics["throughput"].get("requests_per_second", 1)
            errors_per_sec = perf_metrics["throughput"].get("errors_per_second", 0)
            
            if requests_per_sec > 0:
                error_rate = errors_per_sec / requests_per_sec
                if error_rate > self.thresholds["error_rate"]["critical"]:
                    score -= 40
                    issues.append(f"Critical error rate: {error_rate*100:.2f}%")
                elif error_rate > self.thresholds["error_rate"]["warning"]:
                    score -= 20
                    issues.append(f"High error rate: {error_rate*100:.2f}%")
        
        return {
            "score": max(0, score),
            "status": self._score_to_status(score).value,
            "issues": issues
        }
    
    def _calculate_code_quality_health(self, quality_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate code quality health score."""
        score = 100
        issues = []
        
        # Check test coverage
        if "coverage" in quality_metrics:
            coverage = quality_metrics["coverage"].get("line_percent", 0)
            if coverage < 50:
                score -= 20
                issues.append(f"Low test coverage: {coverage}%")
            elif coverage < 70:
                score -= 10
                issues.append(f"Test coverage below target: {coverage}%")
        
        # Check critical issues
        if "issues" in quality_metrics:
            critical_issues = quality_metrics["issues"].get("critical", 0)
            if critical_issues > 0:
                score -= min(30, critical_issues * 10)
                issues.append(f"Critical issues found: {critical_issues}")
        
        # Check test failures
        if "tests" in quality_metrics:
            total_tests = quality_metrics["tests"].get("total", 0)
            failed_tests = quality_metrics["tests"].get("failed", 0)
            
            if total_tests > 0 and failed_tests > 0:
                failure_rate = failed_tests / total_tests
                if failure_rate > 0.1:
                    score -= 30
                    issues.append(f"High test failure rate: {failure_rate*100:.1f}%")
                elif failure_rate > 0.05:
                    score -= 15
                    issues.append(f"Test failures: {failed_tests}/{total_tests}")
        
        return {
            "score": max(0, score),
            "status": self._score_to_status(score).value,
            "issues": issues
        }
    
    def _score_to_status(self, score: float) -> HealthStatus:
        """Convert numeric score to health status."""
        if score >= 80:
            return HealthStatus.HEALTHY
        elif score >= 60:
            return HealthStatus.WARNING
        elif score > 0:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.UNKNOWN


__all__ = ['HealthScoreCalculator', 'HealthStatus']