"""Database Connection Pool Monitoring Service

Provides comprehensive monitoring of database connection pools including:
- Pool status metrics
- Health checks
- Alert notifications
- Performance tracking
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.pool import Pool
from sqlalchemy import text
from app.db.postgres import async_engine, Database
from app.logging_config import central_logger
from app.core.exceptions import DatabaseError, NetraException
import asyncio
import time

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
        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sync_pool": None,
            "async_pool": None,
            "health": "unknown"
        }
        
        # Sync pool status
        try:
            if hasattr(Database, 'engine') and Database.engine:
                sync_pool = Database.engine.pool
                status["sync_pool"] = self._extract_pool_metrics(sync_pool, "sync")
        except Exception as e:
            logger.error(f"Error getting sync pool status: {e}")
            status["sync_pool"] = {"error": str(e)}
        
        # Async pool status
        try:
            if async_engine:
                async_pool = async_engine.pool
                status["async_pool"] = self._extract_pool_metrics(async_pool, "async")
        except Exception as e:
            logger.error(f"Error getting async pool status: {e}")
            status["async_pool"] = {"error": str(e)}
        
        # Overall health assessment
        status["health"] = self._assess_pool_health(status)
        
        # Store metrics history
        self._store_metrics(status)
        
        return status
    
    def _extract_pool_metrics(self, pool: Pool, pool_type: str) -> Dict[str, Any]:
        """Extract metrics from a SQLAlchemy pool"""
        metrics = {
            "type": pool_type,
            "pool_class": pool.__class__.__name__,
            "size": None,
            "checked_in": None,
            "checked_out": None,
            "overflow": None,
            "total_connections": None,
            "utilization_percent": None,
            "overflow_percent": None
        }
        
        try:
            if hasattr(pool, 'size'):
                metrics["size"] = pool.size()
            if hasattr(pool, 'checkedin'):
                metrics["checked_in"] = pool.checkedin()
            if hasattr(pool, 'overflow'):
                metrics["overflow"] = pool.overflow()
            
            # Calculate derived metrics
            if metrics["size"] is not None and metrics["checked_in"] is not None:
                metrics["checked_out"] = metrics["size"] - metrics["checked_in"]
                
            if metrics["checked_out"] is not None and metrics["overflow"] is not None:
                metrics["total_connections"] = metrics["checked_out"] + metrics["overflow"]
                
            # Calculate utilization percentages
            if metrics["size"] is not None and metrics["total_connections"] is not None:
                if metrics["size"] > 0:
                    metrics["utilization_percent"] = (metrics["total_connections"] / metrics["size"]) * 100
                    
            # Get max overflow from pool configuration
            max_overflow = getattr(pool, '_max_overflow', 0)
            if max_overflow > 0 and metrics["overflow"] is not None:
                metrics["overflow_percent"] = (metrics["overflow"] / max_overflow) * 100
                
        except Exception as e:
            logger.error(f"Error extracting {pool_type} pool metrics: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _assess_pool_health(self, status: Dict[str, Any]) -> str:
        """Assess overall pool health based on metrics"""
        warnings = []
        critical_issues = []
        
        for pool_type in ["sync_pool", "async_pool"]:
            pool_status = status.get(pool_type)
            if not pool_status or "error" in pool_status:
                critical_issues.append(f"{pool_type} error")
                continue
                
            # Check utilization
            utilization = pool_status.get("utilization_percent")
            if utilization is not None:
                if utilization > 90:
                    critical_issues.append(f"{pool_type} utilization critical ({utilization:.1f}%)")
                elif utilization > 75:
                    warnings.append(f"{pool_type} utilization high ({utilization:.1f}%)")
            
            # Check overflow usage
            overflow_percent = pool_status.get("overflow_percent")
            if overflow_percent is not None:
                if overflow_percent > 80:
                    critical_issues.append(f"{pool_type} overflow critical ({overflow_percent:.1f}%)")
                elif overflow_percent > 50:
                    warnings.append(f"{pool_type} overflow high ({overflow_percent:.1f}%)")
        
        if critical_issues:
            self._send_alert("critical", critical_issues)
            return "critical"
        elif warnings:
            self._send_alert("warning", warnings)
            return "warning"
        else:
            return "healthy"
    
    def _store_metrics(self, metrics: Dict[str, Any]) -> None:
        """Store metrics in history"""
        self._metrics_history.append(metrics)
        
        # Trim history if it gets too large
        if len(self._metrics_history) > self._max_history_size:
            self._metrics_history = self._metrics_history[-self._max_history_size:]
    
    def _send_alert(self, level: str, issues: List[str]) -> None:
        """Send alert notification with cooldown"""
        current_time = time.time()
        if current_time - self._last_alert_time < self._alert_cooldown:
            return  # Skip alert due to cooldown
        
        self._last_alert_time = current_time
        
        alert_message = f"Database pool {level}: {', '.join(issues)}"
        
        if level == "critical":
            logger.critical(alert_message)
        else:
            logger.warning(alert_message)
        
        # Here you could integrate with external alerting systems
        # like PagerDuty, Slack, email, etc.
    
    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent metrics history"""
        return self._metrics_history[-limit:] if self._metrics_history else []
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from recent metrics"""
        if not self._metrics_history:
            return {"error": "No metrics history available"}
        
        recent_metrics = self._metrics_history[-10:]  # Last 10 readings
        
        summary = {
            "total_readings": len(self._metrics_history),
            "recent_readings": len(recent_metrics),
            "health_distribution": {},
            "avg_utilization": {},
            "max_utilization": {},
            "alerts_in_period": 0
        }
        
        # Analyze health distribution
        health_counts = {}
        for metric in recent_metrics:
            health = metric.get("health", "unknown")
            health_counts[health] = health_counts.get(health, 0) + 1
        
        summary["health_distribution"] = health_counts
        
        # Analyze utilization for each pool type
        for pool_type in ["sync_pool", "async_pool"]:
            utilizations = []
            for metric in recent_metrics:
                pool_data = metric.get(pool_type)
                if pool_data and "utilization_percent" in pool_data:
                    utilizations.append(pool_data["utilization_percent"])
            
            if utilizations:
                summary["avg_utilization"][pool_type] = sum(utilizations) / len(utilizations)
                summary["max_utilization"][pool_type] = max(utilizations)
        
        return summary

class ConnectionHealthChecker:
    """Perform periodic health checks on database connections"""
    
    def __init__(self, metrics: ConnectionPoolMetrics) -> None:
        self.metrics = metrics
        self._running = False
        self._check_interval = 60  # 1 minute
        
    async def start_monitoring(self) -> None:
        """Start periodic monitoring"""
        self._running = True
        logger.info("Starting database connection monitoring")
        
        while self._running:
            try:
                await self.perform_health_check()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Error in health check monitoring: {e}")
                await asyncio.sleep(self._check_interval)
    
    def stop_monitoring(self) -> None:
        """Stop periodic monitoring"""
        self._running = False
        logger.info("Stopping database connection monitoring")
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check"""
        health_check = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pool_status": None,
            "connectivity_test": None,
            "performance_test": None,
            "overall_health": "unknown"
        }
        
        try:
            # Get pool status
            health_check["pool_status"] = self.metrics.get_pool_status()
            
            # Test connectivity
            health_check["connectivity_test"] = await self._test_connectivity()
            
            # Test performance
            health_check["performance_test"] = await self._test_performance()
            
            # Assess overall health
            health_check["overall_health"] = self._assess_overall_health(health_check)
            
        except Exception as e:
            logger.error(f"Error performing health check: {e}")
            health_check["error"] = str(e)
            health_check["overall_health"] = "error"
        
        return health_check
    
    async def _test_connectivity(self) -> Dict[str, Any]:
        """Test basic database connectivity"""
        test_result = {
            "status": "unknown",
            "response_time_ms": None,
            "error": None
        }
        
        try:
            start_time = time.time()
            
            # Test async engine connectivity
            if async_engine:
                async with async_engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    result.fetchone()
            
            end_time = time.time()
            test_result["response_time_ms"] = round((end_time - start_time) * 1000, 2)
            test_result["status"] = "healthy"
            
        except Exception as e:
            test_result["status"] = "failed"
            test_result["error"] = str(e)
            logger.error(f"Connectivity test failed: {e}")
        
        return test_result
    
    async def _test_performance(self) -> Dict[str, Any]:
        """Test database performance"""
        test_result = {
            "status": "unknown",
            "avg_response_time_ms": None,
            "max_response_time_ms": None,
            "error": None
        }
        
        try:
            response_times = []
            test_queries = [
                text("SELECT 1"),
                text("SELECT NOW()"),
                text("SELECT COUNT(*) FROM information_schema.tables")
            ]
            
            if async_engine:
                for query in test_queries:
                    start_time = time.time()
                    async with async_engine.connect() as conn:
                        result = await conn.execute(query)
                        result.fetchall()
                    end_time = time.time()
                    response_times.append((end_time - start_time) * 1000)
            
            if response_times:
                test_result["avg_response_time_ms"] = round(sum(response_times) / len(response_times), 2)
                test_result["max_response_time_ms"] = round(max(response_times), 2)
                
                # Assess performance
                if test_result["max_response_time_ms"] > 5000:  # 5 seconds
                    test_result["status"] = "slow"
                elif test_result["avg_response_time_ms"] > 1000:  # 1 second
                    test_result["status"] = "degraded"
                else:
                    test_result["status"] = "healthy"
            
        except Exception as e:
            test_result["status"] = "failed"
            test_result["error"] = str(e)
            logger.error(f"Performance test failed: {e}")
        
        return test_result
    
    def _assess_overall_health(self, health_check: Dict[str, Any]) -> str:
        """Assess overall system health"""
        pool_health = health_check.get("pool_status", {}).get("health", "unknown")
        connectivity_status = health_check.get("connectivity_test", {}).get("status", "unknown")
        performance_status = health_check.get("performance_test", {}).get("status", "unknown")
        
        # If any critical component is failed, overall health is critical
        if "failed" in [connectivity_status, performance_status] or pool_health == "critical":
            return "critical"
        
        # If any component has issues, overall health is degraded
        if "slow" in [performance_status] or "degraded" in [performance_status] or pool_health == "warning":
            return "warning"
        
        # If all components are healthy
        if all(status == "healthy" for status in [pool_health, connectivity_status, performance_status]):
            return "healthy"
        
        return "unknown"

# Global instances
connection_metrics = ConnectionPoolMetrics()
health_checker = ConnectionHealthChecker(connection_metrics)

async def get_connection_status() -> Dict[str, Any]:
    """Get comprehensive connection status"""
    try:
        return {
            "pool_metrics": connection_metrics.get_pool_status(),
            "summary_stats": connection_metrics.get_summary_stats(),
            "health_check": await health_checker.perform_health_check()
        }
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        raise DatabaseError(
            message="Failed to get connection status",
            context={"error": str(e)}
        )

async def start_connection_monitoring() -> None:
    """Start the connection monitoring service"""
    try:
        await health_checker.start_monitoring()
    except Exception as e:
        logger.error(f"Error starting connection monitoring: {e}")
        raise

def stop_connection_monitoring() -> None:
    """Stop the connection monitoring service"""
    health_checker.stop_monitoring()