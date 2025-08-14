"""
Enhanced system health monitor with agent metrics integration.
Extends the base system health monitor with comprehensive agent monitoring.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.logging_config import central_logger
from .system_health_monitor import SystemHealthMonitor, HealthStatus, ComponentHealth, SystemAlert

logger = central_logger.get_logger(__name__)


def get_agent_metrics_collector():
    """Get agent metrics collector instance."""
    from app.services.metrics.agent_metrics import agent_metrics_collector
    return agent_metrics_collector


def get_alert_manager():
    """Get alert manager instance."""
    from app.monitoring.alert_manager import alert_manager
    return alert_manager


class EnhancedSystemHealthMonitor(SystemHealthMonitor):
    """Enhanced system health monitor with agent metrics integration."""
    
    def __init__(self, check_interval: int = 30):
        super().__init__(check_interval)
        self._register_enhanced_checkers()
        self._setup_alert_manager_integration()
    
    def _register_enhanced_checkers(self):
        """Register enhanced health checkers including agent metrics."""
        # Register agent metrics health checker
        self.register_component_checker("agent_metrics", self._check_agent_health)
        self.register_component_checker("agent_performance", self._check_agent_performance)
        self.register_component_checker("agent_errors", self._check_agent_errors)
        logger.debug("Registered enhanced health checkers with agent metrics")
    
    def _setup_alert_manager_integration(self):
        """Setup integration with alert manager."""
        try:
            alert_manager = get_alert_manager()
            
            # Register health monitor as alert callback
            alert_manager.register_notification_handler(
                alert_manager.NotificationChannel.DATABASE,
                self._handle_alert_notification
            )
            
            logger.debug("Setup alert manager integration")
        except Exception as e:
            logger.error(f"Failed to setup alert manager integration: {e}")
    
    async def _handle_alert_notification(self, alert, config):
        """Handle alert notifications from alert manager."""
        try:
            # Convert alert manager alert to system alert
            system_alert = SystemAlert(
                alert_id=alert.alert_id,
                component=alert.agent_name or "unknown",
                severity=alert.level.value,
                message=alert.message,
                timestamp=alert.timestamp,
                metadata={
                    "source": "alert_manager",
                    "rule_id": alert.rule_id,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value
                }
            )
            
            # Add to system alerts
            self.alerts.append(system_alert)
            
            # Trim history if needed
            if len(self.alerts) > self.max_alert_history:
                self.alerts = self.alerts[-self.max_alert_history:]
                
            logger.debug(f"Processed alert notification: {alert.title}")
            
        except Exception as e:
            logger.error(f"Error handling alert notification: {e}")
    
    async def _check_agent_health(self) -> Dict[str, Any]:
        """Check overall agent system health."""
        try:
            metrics_collector = get_agent_metrics_collector()
            system_overview = await metrics_collector.get_system_overview()
            
            # Calculate overall health score based on system metrics
            error_rate = system_overview.get("system_error_rate", 0.0)
            active_agents = system_overview.get("active_agents", 0)
            unhealthy_agents = system_overview.get("unhealthy_agents", 0)
            
            # Health score calculation (8 lines max)
            if active_agents == 0:
                health_score = 1.0  # No agents running, assume healthy
            else:
                error_penalty = min(0.5, error_rate * 2)  # Cap at 50% penalty
                unhealthy_penalty = min(0.3, (unhealthy_agents / active_agents) * 0.5)
                health_score = max(0.0, 1.0 - error_penalty - unhealthy_penalty)
            
            return {
                "health_score": health_score,
                "error_count": system_overview.get("total_failures", 0),
                "metadata": {
                    "total_operations": system_overview.get("total_operations", 0),
                    "system_error_rate": error_rate,
                    "active_agents": active_agents,
                    "unhealthy_agents": unhealthy_agents,
                    "active_operations": system_overview.get("active_operations", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error checking agent health: {e}")
            return {"health_score": 0.0, "error_count": 1, "metadata": {"error": str(e)}}
    
    async def _check_agent_performance(self) -> Dict[str, Any]:
        """Check agent performance metrics."""
        try:
            metrics_collector = get_agent_metrics_collector()
            all_metrics = metrics_collector.get_all_agent_metrics()
            
            if not all_metrics:
                return {"health_score": 1.0, "error_count": 0, "metadata": {"no_agents": True}}
            
            # Calculate performance score
            total_avg_time = sum(m.avg_execution_time_ms for m in all_metrics.values())
            avg_execution_time = total_avg_time / len(all_metrics)
            
            # Performance scoring (under 8 lines)
            if avg_execution_time < 5000:  # Under 5 seconds
                perf_score = 1.0
            elif avg_execution_time < 15000:  # Under 15 seconds
                perf_score = 0.8
            elif avg_execution_time < 30000:  # Under 30 seconds
                perf_score = 0.6
            else:
                perf_score = 0.3
            
            return {
                "health_score": perf_score,
                "error_count": 0,
                "metadata": {
                    "avg_execution_time_ms": avg_execution_time,
                    "agent_count": len(all_metrics),
                    "performance_category": self._get_performance_category(perf_score)
                }
            }
        except Exception as e:
            logger.error(f"Error checking agent performance: {e}")
            return {"health_score": 0.0, "error_count": 1, "metadata": {"error": str(e)}}
    
    async def _check_agent_errors(self) -> Dict[str, Any]:
        """Check agent error patterns and rates."""
        try:
            metrics_collector = get_agent_metrics_collector()
            all_metrics = metrics_collector.get_all_agent_metrics()
            
            if not all_metrics:
                return {"health_score": 1.0, "error_count": 0, "metadata": {"no_agents": True}}
            
            # Calculate error statistics (8 lines max)
            total_ops = sum(m.total_operations for m in all_metrics.values())
            total_failures = sum(m.failed_operations for m in all_metrics.values())
            total_timeouts = sum(m.timeout_count for m in all_metrics.values())
            total_validation_errors = sum(m.validation_error_count for m in all_metrics.values())
            
            overall_error_rate = total_failures / total_ops if total_ops > 0 else 0
            error_health_score = max(0.0, 1.0 - (overall_error_rate * 2))
            
            return {
                "health_score": error_health_score,
                "error_count": total_failures,
                "metadata": {
                    "total_operations": total_ops,
                    "total_failures": total_failures,
                    "overall_error_rate": overall_error_rate,
                    "timeout_count": total_timeouts,
                    "validation_error_count": total_validation_errors,
                    "agents_with_errors": len([m for m in all_metrics.values() if m.failed_operations > 0])
                }
            }
        except Exception as e:
            logger.error(f"Error checking agent errors: {e}")
            return {"health_score": 0.0, "error_count": 1, "metadata": {"error": str(e)}}
    
    def _get_performance_category(self, score: float) -> str:
        """Get performance category from score."""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    async def get_agent_health_details(self) -> Dict[str, Any]:
        """Get detailed agent health information."""
        try:
            metrics_collector = get_agent_metrics_collector()
            all_metrics = metrics_collector.get_all_agent_metrics()
            
            agent_health_data = []
            health_summary = {"healthy": 0, "degraded": 0, "unhealthy": 0}
            
            for agent_name, metrics in all_metrics.items():
                health_score = metrics_collector.get_health_score(agent_name)
                
                # Categorize health (8 lines max)
                if health_score >= 0.7:
                    health_summary["healthy"] += 1
                    status = "healthy"
                elif health_score >= 0.5:
                    health_summary["degraded"] += 1
                    status = "degraded"
                else:
                    health_summary["unhealthy"] += 1
                    status = "unhealthy"
                
                agent_health_data.append({
                    "name": agent_name,
                    "health_score": health_score,
                    "status": status,
                    "error_rate": metrics.error_rate,
                    "total_operations": metrics.total_operations,
                    "avg_execution_time_ms": metrics.avg_execution_time_ms,
                    "timeout_count": metrics.timeout_count,
                    "validation_error_count": metrics.validation_error_count
                })
            
            return {
                "agent_count": len(all_metrics),
                "health_summary": health_summary,
                "agent_details": agent_health_data
            }
        except Exception as e:
            logger.error(f"Error getting agent health details: {e}")
            return {"error": str(e)}

    async def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """Get comprehensive system health report including agent metrics."""
        try:
            # Get basic system health
            basic_health = {
                "components": len(self.component_health),
                "healthy_components": len([h for h in self.component_health.values() 
                                         if h.status == HealthStatus.HEALTHY]),
                "unhealthy_components": len([h for h in self.component_health.values() 
                                           if h.status != HealthStatus.HEALTHY]),
                "active_alerts": len(self.active_alerts),
                "uptime_seconds": time.time() - self.start_time
            }
            
            # Get agent health details
            agent_health = await self.get_agent_health_details()
            
            # Get system overview from metrics
            metrics_collector = get_agent_metrics_collector()
            system_overview = await metrics_collector.get_system_overview()
            
            return {
                "timestamp": datetime.utcnow(),
                "system_health": basic_health,
                "agent_health": agent_health,
                "metrics_overview": system_overview,
                "component_details": {name: {
                    "status": health.status.value,
                    "health_score": health.health_score,
                    "error_count": health.error_count,
                    "last_check": health.last_check,
                    "uptime": health.uptime
                } for name, health in self.component_health.items()}
            }
        except Exception as e:
            logger.error(f"Error generating comprehensive health report: {e}")
            return {"error": str(e), "timestamp": datetime.utcnow()}

    async def start_monitoring(self):
        """Start enhanced monitoring including alert manager."""
        await super().start_monitoring()
        
        try:
            # Start alert manager monitoring
            alert_manager = get_alert_manager()
            await alert_manager.start_monitoring()
            logger.info("Started enhanced monitoring with alert manager")
        except Exception as e:
            logger.error(f"Failed to start alert manager: {e}")

    async def stop_monitoring(self):
        """Stop enhanced monitoring including alert manager."""
        try:
            # Stop alert manager monitoring
            alert_manager = get_alert_manager()
            await alert_manager.stop_monitoring()
        except Exception as e:
            logger.error(f"Failed to stop alert manager: {e}")
        
        await super().stop_monitoring()
        logger.info("Stopped enhanced monitoring")


# Enhanced system health monitor instance
enhanced_system_health_monitor = EnhancedSystemHealthMonitor()