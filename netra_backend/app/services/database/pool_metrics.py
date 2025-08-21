"""Database Connection Pool Metrics Module

Tracks and analyzes connection pool performance metrics.
"""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.pool import Pool

from netra_backend.app.db.postgres import Database, async_engine
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class ConnectionPoolMetrics:
    """Collect and track connection pool metrics"""
    
    def __init__(self) -> None:
        self._metrics_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        self._last_alert_time = 0
        self._alert_cooldown = 300  # 5 minutes
        
    def get_pool_status(self, pool: Optional[Pool] = None) -> Dict[str, Any]:
        """Get current pool status"""
        status = self._init_status()
        self._collect_sync_pool_status(status)
        self._collect_async_pool_status(status)
        status["health"] = self._assess_pool_health(status)
        self._store_metrics(status)
        return status
    
    def _init_status(self) -> Dict[str, Any]:
        """Initialize status dictionary"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sync_pool": None,
            "async_pool": None,
            "health": "unknown"
        }
    
    def _collect_sync_pool_status(self, status: Dict[str, Any]) -> None:
        """Collect sync pool metrics"""
        # Currently we only use async engine, no sync instance
        status["sync_pool"] = None
    
    def _collect_async_pool_status(self, status: Dict[str, Any]) -> None:
        """Collect async pool metrics"""
        try:
            if async_engine:
                async_pool = async_engine.pool
                status["async_pool"] = self._extract_pool_metrics(async_pool, "async")
        except Exception as e:
            logger.error(f"Error getting async pool status: {e}")
            status["async_pool"] = {"error": str(e)}
    
    def _extract_pool_metrics(self, pool: Pool, pool_type: str) -> Dict[str, Any]:
        """Extract metrics from a SQLAlchemy pool"""
        metrics = self._init_pool_metrics(pool_type)
        self._extract_basic_metrics(pool, metrics)
        self._calculate_derived_metrics(metrics)
        self._calculate_utilization(pool, metrics)
        return metrics
    
    def _init_pool_metrics(self, pool_type: str) -> Dict[str, Any]:
        """Initialize metrics dictionary"""
        return {
            "type": pool_type,
            "pool_class": None,
            "size": None,
            "checked_in": None,
            "checked_out": None,
            "overflow": None,
            "total_connections": None,
            "utilization_percent": None,
            "overflow_percent": None
        }
    
    def _extract_basic_metrics(self, pool: Pool, metrics: Dict[str, Any]) -> None:
        """Extract basic pool metrics"""
        try:
            metrics["pool_class"] = pool.__class__.__name__
            if hasattr(pool, 'size'):
                metrics["size"] = pool.size()
            if hasattr(pool, 'checkedin'):
                metrics["checked_in"] = pool.checkedin()
            if hasattr(pool, 'overflow'):
                metrics["overflow"] = pool.overflow()
        except Exception as e:
            logger.error(f"Error extracting pool metrics: {e}")
            metrics["error"] = str(e)
    
    def _calculate_derived_metrics(self, metrics: Dict[str, Any]) -> None:
        """Calculate derived metrics"""
        if metrics["size"] is not None and metrics["checked_in"] is not None:
            metrics["checked_out"] = metrics["size"] - metrics["checked_in"]
        if metrics["checked_out"] is not None and metrics["overflow"] is not None:
            metrics["total_connections"] = metrics["checked_out"] + metrics["overflow"]
    
    def _calculate_utilization(self, pool: Pool, metrics: Dict[str, Any]) -> None:
        """Calculate utilization percentages"""
        self._calculate_pool_utilization(metrics)
        self._calculate_overflow_utilization(pool, metrics)
    
    def _calculate_pool_utilization(self, metrics: Dict[str, Any]) -> None:
        """Calculate pool utilization percentage"""
        size = metrics.get("size")
        total = metrics.get("total_connections")
        if size and total and size > 0:
            metrics["utilization_percent"] = (total / size) * 100
    
    def _calculate_overflow_utilization(self, pool: Pool, metrics: Dict[str, Any]) -> None:
        """Calculate overflow utilization percentage"""
        max_overflow = getattr(pool, '_max_overflow', 0)
        overflow = metrics.get("overflow")
        if max_overflow > 0 and overflow is not None:
            metrics["overflow_percent"] = (overflow / max_overflow) * 100
    
    def _assess_pool_health(self, status: Dict[str, Any]) -> str:
        """Assess overall pool health based on metrics"""
        warnings, critical_issues = self._collect_health_issues(status)
        return self._determine_health_level(warnings, critical_issues)
    
    def _collect_health_issues(self, status: Dict[str, Any]) -> tuple:
        """Collect health warnings and critical issues"""
        warnings = []
        critical_issues = []
        for pool_type in ["sync_pool", "async_pool"]:
            self._check_pool_health(status, pool_type, warnings, critical_issues)
        return warnings, critical_issues
    
    def _check_pool_health(self, status: Dict[str, Any], pool_type: str, 
                          warnings: List[str], critical_issues: List[str]) -> None:
        """Check health of a specific pool"""
        pool_status = status.get(pool_type)
        if pool_status is None:
            # Pool not configured (e.g., sync pool when only async is used)
            return
        if "error" in pool_status:
            critical_issues.append(f"{pool_type} error")
            return
        self._check_utilization(pool_status, pool_type, warnings, critical_issues)
        self._check_overflow(pool_status, pool_type, warnings, critical_issues)
    
    def _check_utilization(self, pool_status: Dict[str, Any], pool_type: str,
                          warnings: List[str], critical_issues: List[str]) -> None:
        """Check pool utilization levels"""
        utilization = pool_status.get("utilization_percent")
        if utilization is None:
            return
        if utilization > 90:
            critical_issues.append(f"{pool_type} utilization critical ({utilization:.1f}%)")
        elif utilization > 75:
            warnings.append(f"{pool_type} utilization high ({utilization:.1f}%)")
    
    def _check_overflow(self, pool_status: Dict[str, Any], pool_type: str,
                       warnings: List[str], critical_issues: List[str]) -> None:
        """Check overflow usage levels"""
        overflow_percent = pool_status.get("overflow_percent")
        if overflow_percent is None:
            return
        if overflow_percent > 80:
            critical_issues.append(f"{pool_type} overflow critical ({overflow_percent:.1f}%)")
        elif overflow_percent > 50:
            warnings.append(f"{pool_type} overflow high ({overflow_percent:.1f}%)")
    
    def _determine_health_level(self, warnings: List[str], critical_issues: List[str]) -> str:
        """Determine overall health level"""
        if critical_issues:
            self._send_alert("critical", critical_issues)
            return "critical"
        elif warnings:
            self._send_alert("warning", warnings)
            return "warning"
        return "healthy"
    
    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in history"""
        self._metrics_history.append(metrics)
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _send_alert(self, level: str, issues: List[str]) -> None:
        """Send alert notification with cooldown"""
        if not self._should_send_alert():
            return
        self._last_alert_time = time.time()
        self._log_alert(level, issues)
    
    def _should_send_alert(self) -> bool:
        """Check if alert should be sent based on cooldown"""
        current_time = time.time()
        return current_time - self._last_alert_time >= self._alert_cooldown
    
    def _log_alert(self, level: str, issues: List[str]) -> None:
        """Log alert message"""
        alert_message = f"Database pool {level}: {', '.join(issues)}"
        if level == "critical":
            logger.critical(alert_message)
        else:
            logger.warning(alert_message)
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics history"""
        return self._metrics_history[-limit:] if self._metrics_history else []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from recent metrics"""
        if not self._metrics_history:
            return {"error": "No metrics history available"}
        return self._calculate_summary_stats()
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        recent_metrics = self._metrics_history[-10:]
        summary = self._init_summary_stats(recent_metrics)
        self._analyze_health_distribution(recent_metrics, summary)
        self._analyze_utilization_stats(recent_metrics, summary)
        return summary
    
    def _init_summary_stats(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Initialize summary statistics"""
        return {
            "total_readings": len(self._metrics_history),
            "recent_readings": len(recent_metrics),
            "health_distribution": {},
            "avg_utilization": {},
            "max_utilization": {},
            "alerts_in_period": 0
        }
    
    def _analyze_health_distribution(self, metrics: List[Dict[str, Any]], 
                                    summary: Dict[str, Any]) -> None:
        """Analyze health distribution"""
        health_counts = {}
        for metric in metrics:
            health = metric.get("health", "unknown")
            health_counts[health] = health_counts.get(health, 0) + 1
        summary["health_distribution"] = health_counts
    
    def _analyze_utilization_stats(self, metrics: List[Dict[str, Any]], 
                                  summary: Dict[str, Any]) -> None:
        """Analyze utilization statistics"""
        for pool_type in ["sync_pool", "async_pool"]:
            self._calculate_pool_utilization_stats(metrics, pool_type, summary)
    
    def _calculate_pool_utilization_stats(self, metrics: List[Dict[str, Any]], 
                                         pool_type: str, summary: Dict[str, Any]) -> None:
        """Calculate utilization stats for a specific pool"""
        utilizations = self._extract_utilizations(metrics, pool_type)
        if utilizations:
            summary["avg_utilization"][pool_type] = sum(utilizations) / len(utilizations)
            summary["max_utilization"][pool_type] = max(utilizations)
    
    def _extract_utilizations(self, metrics: List[Dict[str, Any]], 
                            pool_type: str) -> List[float]:
        """Extract utilization values for a pool type"""
        utilizations = []
        for metric in metrics:
            pool_data = metric.get(pool_type)
            if pool_data and "utilization_percent" in pool_data:
                utilizations.append(pool_data["utilization_percent"])
        return utilizations