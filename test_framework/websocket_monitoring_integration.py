#!/usr/bin/env python
"""WEBSOCKET MONITORING AND ALERTING INTEGRATION

Provides monitoring and alerting integration for WebSocket deployment validation.
Integrates with deployment pipeline for continuous WebSocket health monitoring.

Business Value: Prevents WebSocket regression failures that impact $180K+ MRR chat functionality
Monitoring: Real-time WebSocket health metrics and alerting thresholds
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

from shared.isolated_environment import get_env
from loguru import logger


@dataclass
class WebSocketHealthMetric:
    """Individual WebSocket health metric."""
    
    name: str
    value: float
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    timestamp: datetime = None
    status: str = "ok"  # ok, warning, critical
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}
            
        # Determine status based on thresholds
        if self.threshold_critical and self.value <= self.threshold_critical:
            self.status = "critical"
        elif self.threshold_warning and self.value <= self.threshold_warning:
            self.status = "warning"
        else:
            self.status = "ok"


@dataclass
class WebSocketAlert:
    """WebSocket monitoring alert."""
    
    alert_id: str
    severity: str  # info, warning, critical
    title: str
    description: str
    timestamp: datetime
    environment: str
    metrics: Dict[str, Any]
    resolution_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.resolution_suggestions is None:
            self.resolution_suggestions = []


class WebSocketHealthMonitor:
    """Monitors WebSocket health metrics and generates alerts."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.env = get_env()
        self.alerts: List[WebSocketAlert] = []
        
        # Define monitoring thresholds based on environment
        self.thresholds = self._get_environment_thresholds()
        
    def _get_environment_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get monitoring thresholds based on environment."""
        if self.environment == "production":
            return {
                "handshake_success_rate": {"warning": 95.0, "critical": 90.0},
                "connection_success_rate": {"warning": 98.0, "critical": 95.0},
                "avg_connection_duration": {"warning": 300.0, "critical": 60.0},  # seconds
                "message_throughput": {"warning": 100.0, "critical": 50.0},  # msg/min
                "error_rate": {"warning": 5.0, "critical": 10.0},  # %
                "auth_failure_rate": {"warning": 2.0, "critical": 5.0}  # %
            }
        elif self.environment == "staging":
            return {
                "handshake_success_rate": {"warning": 90.0, "critical": 80.0},
                "connection_success_rate": {"warning": 95.0, "critical": 85.0}, 
                "avg_connection_duration": {"warning": 180.0, "critical": 30.0},
                "message_throughput": {"warning": 50.0, "critical": 20.0},
                "error_rate": {"warning": 10.0, "critical": 20.0},
                "auth_failure_rate": {"warning": 5.0, "critical": 15.0}
            }
        else:  # development
            return {
                "handshake_success_rate": {"warning": 80.0, "critical": 60.0},
                "connection_success_rate": {"warning": 90.0, "critical": 75.0},
                "avg_connection_duration": {"warning": 120.0, "critical": 15.0},
                "message_throughput": {"warning": 25.0, "critical": 10.0},
                "error_rate": {"warning": 15.0, "critical": 30.0},
                "auth_failure_rate": {"warning": 10.0, "critical": 25.0}
            }
            
    async def collect_websocket_metrics(self) -> List[WebSocketHealthMetric]:
        """Collect current WebSocket health metrics."""
        metrics = []
        
        try:
            # Get WebSocket health data
            health_data = await self._get_websocket_health_data()
            
            # Create metrics from health data
            metrics.extend(self._create_metrics_from_health_data(health_data))
            
            # Get WebSocket connection statistics
            connection_stats = await self._get_connection_statistics()
            metrics.extend(self._create_metrics_from_connection_stats(connection_stats))
            
            # Get WebSocket authentication metrics
            auth_stats = await self._get_auth_statistics()
            metrics.extend(self._create_metrics_from_auth_stats(auth_stats))
            
        except Exception as e:
            logger.error(f"Failed to collect WebSocket metrics: {e}")
            # Create error metric
            metrics.append(WebSocketHealthMetric(
                name="metric_collection_success",
                value=0.0,
                threshold_critical=0.5,
                details={"error": str(e)}
            ))
            
        return metrics
        
    async def _get_websocket_health_data(self) -> Dict[str, Any]:
        """Get WebSocket health data from health endpoint."""
        try:
            import aiohttp
            
            base_url = self._get_base_url()
            health_url = f"{base_url}/api/websocket/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Health endpoint returned {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}
            
    async def _get_connection_statistics(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        try:
            import aiohttp
            
            base_url = self._get_base_url()
            stats_url = f"{base_url}/api/websocket/stats"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(stats_url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"Stats endpoint returned {response.status}"}
                        
        except Exception as e:
            return {"error": str(e)}
            
    async def _get_auth_statistics(self) -> Dict[str, Any]:
        """Get WebSocket authentication statistics.""" 
        # This would typically come from auth service or WebSocket auth metrics
        # For now, simulate based on connection success
        return {
            "auth_attempts": 100,
            "auth_successes": 95,
            "auth_failures": 5,
            "avg_auth_time_ms": 150
        }
        
    def _create_metrics_from_health_data(self, health_data: Dict[str, Any]) -> List[WebSocketHealthMetric]:
        """Create metrics from WebSocket health data."""
        metrics = []
        
        if "error" in health_data:
            metrics.append(WebSocketHealthMetric(
                name="websocket_health_check_success",
                value=0.0,
                threshold_critical=0.5,
                details={"error": health_data["error"]}
            ))
            return metrics
            
        # Health check success
        metrics.append(WebSocketHealthMetric(
            name="websocket_health_check_success",
            value=1.0,
            threshold_critical=0.5
        ))
        
        # Service status
        status = health_data.get("status", "unknown")
        status_value = 1.0 if status == "healthy" else 0.0
        
        metrics.append(WebSocketHealthMetric(
            name="websocket_service_healthy",
            value=status_value,
            threshold_critical=0.5,
            details={"status": status}
        ))
        
        # Active connections
        ws_metrics = health_data.get("metrics", {}).get("websocket", {})
        active_connections = ws_metrics.get("active_connections", 0)
        
        metrics.append(WebSocketHealthMetric(
            name="active_connections_count",
            value=float(active_connections),
            threshold_warning=50.0,  # Warning if too many connections
            details={"connections": active_connections}
        ))
        
        return metrics
        
    def _create_metrics_from_connection_stats(self, stats: Dict[str, Any]) -> List[WebSocketHealthMetric]:
        """Create metrics from connection statistics."""
        metrics = []
        
        if "error" in stats:
            return metrics
            
        # Connection success rate
        ws_stats = stats.get("websocket_manager", {})
        total_connections = ws_stats.get("total_connections", 0)
        active_connections = ws_stats.get("active_connections", 0)
        
        if total_connections > 0:
            # Calculate success rate (simplified - active/total)
            success_rate = (active_connections / total_connections) * 100
            thresholds = self.thresholds.get("connection_success_rate", {})
            
            metrics.append(WebSocketHealthMetric(
                name="connection_success_rate",
                value=success_rate,
                threshold_warning=thresholds.get("warning"),
                threshold_critical=thresholds.get("critical"),
                details={"total": total_connections, "active": active_connections}
            ))
            
        # Message throughput
        messages_sent = ws_stats.get("messages_sent", 0)
        messages_received = ws_stats.get("messages_received", 0)
        uptime = ws_stats.get("uptime_seconds", 1)
        
        if uptime > 0:
            throughput = ((messages_sent + messages_received) / uptime) * 60  # per minute
            thresholds = self.thresholds.get("message_throughput", {})
            
            metrics.append(WebSocketHealthMetric(
                name="message_throughput_per_minute",
                value=throughput,
                threshold_warning=thresholds.get("warning"),
                threshold_critical=thresholds.get("critical"),
                details={"sent": messages_sent, "received": messages_received, "uptime": uptime}
            ))
            
        # Error rate
        errors_handled = ws_stats.get("errors_handled", 0)
        if total_connections > 0:
            error_rate = (errors_handled / total_connections) * 100
            thresholds = self.thresholds.get("error_rate", {})
            
            metrics.append(WebSocketHealthMetric(
                name="websocket_error_rate",
                value=error_rate,
                threshold_warning=thresholds.get("warning"),
                threshold_critical=thresholds.get("critical"),
                details={"errors": errors_handled, "total": total_connections}
            ))
            
        return metrics
        
    def _create_metrics_from_auth_stats(self, auth_stats: Dict[str, Any]) -> List[WebSocketHealthMetric]:
        """Create metrics from authentication statistics."""
        metrics = []
        
        auth_attempts = auth_stats.get("auth_attempts", 0)
        auth_failures = auth_stats.get("auth_failures", 0)
        
        if auth_attempts > 0:
            # Authentication failure rate
            failure_rate = (auth_failures / auth_attempts) * 100
            thresholds = self.thresholds.get("auth_failure_rate", {})
            
            metrics.append(WebSocketHealthMetric(
                name="auth_failure_rate",
                value=failure_rate,
                threshold_warning=thresholds.get("warning"),
                threshold_critical=thresholds.get("critical"),
                details={"attempts": auth_attempts, "failures": auth_failures}
            ))
            
            # Authentication success rate
            success_rate = ((auth_attempts - auth_failures) / auth_attempts) * 100
            thresholds = self.thresholds.get("handshake_success_rate", {})
            
            metrics.append(WebSocketHealthMetric(
                name="handshake_success_rate",
                value=success_rate,
                threshold_warning=thresholds.get("warning"),
                threshold_critical=thresholds.get("critical"),
                details={"attempts": auth_attempts, "successes": auth_attempts - auth_failures}
            ))
            
        return metrics
        
    def analyze_metrics(self, metrics: List[WebSocketHealthMetric]) -> List[WebSocketAlert]:
        """Analyze metrics and generate alerts."""
        alerts = []
        
        critical_metrics = [m for m in metrics if m.status == "critical"]
        warning_metrics = [m for m in metrics if m.status == "warning"]
        
        # Critical alert
        if critical_metrics:
            alert = WebSocketAlert(
                alert_id=f"websocket_critical_{int(time.time())}",
                severity="critical",
                title="Critical WebSocket Health Issues Detected",
                description=f"WebSocket service has {len(critical_metrics)} critical health issues",
                timestamp=datetime.utcnow(),
                environment=self.environment,
                metrics={m.name: {"value": m.value, "details": m.details} for m in critical_metrics},
                resolution_suggestions=[
                    "Check WebSocket service health endpoint",
                    "Review WebSocket authentication configuration", 
                    "Validate JWT secret synchronization",
                    "Check load balancer timeout settings",
                    "Consider rolling back recent deployment"
                ]
            )
            alerts.append(alert)
            
        # Warning alert
        elif warning_metrics:
            alert = WebSocketAlert(
                alert_id=f"websocket_warning_{int(time.time())}",
                severity="warning",
                title="WebSocket Performance Degradation",
                description=f"WebSocket service has {len(warning_metrics)} performance warnings",
                timestamp=datetime.utcnow(),
                environment=self.environment,
                metrics={m.name: {"value": m.value, "details": m.details} for m in warning_metrics},
                resolution_suggestions=[
                    "Monitor WebSocket connection patterns",
                    "Check for increased error rates",
                    "Validate authentication performance",
                    "Review connection timeout settings"
                ]
            )
            alerts.append(alert)
            
        # Business impact assessment
        handshake_success = next((m for m in metrics if m.name == "handshake_success_rate"), None)
        if handshake_success and handshake_success.value < 85:
            # High business impact alert
            business_alert = WebSocketAlert(
                alert_id=f"websocket_business_impact_{int(time.time())}",
                severity="critical",
                title="High Business Impact - WebSocket Chat Functionality at Risk",
                description=f"WebSocket handshake success rate at {handshake_success.value:.1f}% - Chat functionality severely impacted",
                timestamp=datetime.utcnow(),
                environment=self.environment,
                metrics={"handshake_success_rate": {"value": handshake_success.value, "details": handshake_success.details}},
                resolution_suggestions=[
                    "URGENT: Review JWT secret configuration",
                    "Check WebSocket authentication pipeline",
                    "Validate staging deployment configuration",
                    "Consider emergency rollback if in production",
                    "Estimate MRR impact and notify business stakeholders"
                ]
            )
            alerts.append(business_alert)
            
        return alerts
        
    def _get_base_url(self) -> str:
        """Get base URL for API calls."""
        if self.environment == "staging":
            return "https://staging.netrasystems.ai"
        elif self.environment == "production":
            return "https://app.netrasystems.ai"
        else:
            return "http://localhost:8000"
            
    async def run_monitoring_cycle(self, duration_minutes: int = 30) -> Dict[str, Any]:
        """Run continuous monitoring for specified duration."""
        logger.info(f"Starting WebSocket monitoring cycle for {duration_minutes} minutes...")
        
        monitoring_results = {
            "start_time": datetime.utcnow().isoformat(),
            "environment": self.environment,
            "duration_minutes": duration_minutes,
            "cycles": [],
            "alerts_generated": [],
            "summary": {}
        }
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        cycle_count = 0
        
        try:
            while time.time() < end_time:
                cycle_count += 1
                cycle_start = time.time()
                
                logger.info(f"Monitoring cycle #{cycle_count} starting...")
                
                # Collect metrics
                metrics = await self.collect_websocket_metrics()
                
                # Analyze metrics and generate alerts
                alerts = self.analyze_metrics(metrics)
                
                cycle_result = {
                    "cycle_number": cycle_count,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metrics": [
                        {
                            "name": m.name,
                            "value": m.value,
                            "status": m.status,
                            "details": m.details
                        }
                        for m in metrics
                    ],
                    "alerts": [
                        {
                            "alert_id": a.alert_id,
                            "severity": a.severity,
                            "title": a.title,
                            "description": a.description
                        }
                        for a in alerts
                    ]
                }
                
                monitoring_results["cycles"].append(cycle_result)
                monitoring_results["alerts_generated"].extend([
                    {
                        "alert_id": a.alert_id,
                        "severity": a.severity,
                        "title": a.title,
                        "description": a.description,
                        "timestamp": a.timestamp.isoformat(),
                        "resolution_suggestions": a.resolution_suggestions
                    }
                    for a in alerts
                ])
                
                # Log alerts
                for alert in alerts:
                    if alert.severity == "critical":
                        logger.error(f" ALERT:  CRITICAL ALERT: {alert.title}")
                        logger.error(f"   Description: {alert.description}")
                    elif alert.severity == "warning":
                        logger.warning(f" WARNING: [U+FE0F] WARNING ALERT: {alert.title}")
                        logger.warning(f"   Description: {alert.description}")
                        
                # Log healthy metrics
                healthy_metrics = [m for m in metrics if m.status == "ok"]
                logger.info(f" PASS:  Cycle #{cycle_count}: {len(healthy_metrics)}/{len(metrics)} metrics healthy")
                
                # Wait before next cycle (2 minute intervals)
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, 120 - cycle_duration)  # 2 minutes between cycles
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            
        # Generate summary
        total_alerts = len(monitoring_results["alerts_generated"])
        critical_alerts = len([a for a in monitoring_results["alerts_generated"] if a["severity"] == "critical"])
        warning_alerts = len([a for a in monitoring_results["alerts_generated"] if a["severity"] == "warning"])
        
        monitoring_results["end_time"] = datetime.utcnow().isoformat()
        monitoring_results["summary"] = {
            "total_cycles": cycle_count,
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "warning_alerts": warning_alerts,
            "monitoring_healthy": critical_alerts == 0,
            "business_impact": "high" if critical_alerts > 0 else ("medium" if warning_alerts > 3 else "low")
        }
        
        logger.info(f"Monitoring completed: {cycle_count} cycles, {total_alerts} alerts ({critical_alerts} critical)")
        
        return monitoring_results


class WebSocketAlertManager:
    """Manages WebSocket alerts and notifications."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.alert_history: List[WebSocketAlert] = []
        
    def process_alert(self, alert: WebSocketAlert) -> None:
        """Process and handle an alert."""
        self.alert_history.append(alert)
        
        # Log alert
        if alert.severity == "critical":
            logger.error(f" ALERT:  CRITICAL: {alert.title}")
        elif alert.severity == "warning":
            logger.warning(f" WARNING: [U+FE0F] WARNING: {alert.title}")
        else:
            logger.info(f"[U+2139][U+FE0F] INFO: {alert.title}")
            
        logger.info(f"   Environment: {alert.environment}")
        logger.info(f"   Description: {alert.description}")
        
        if alert.resolution_suggestions:
            logger.info(f"   Suggested actions:")
            for suggestion in alert.resolution_suggestions:
                logger.info(f"     [U+2022] {suggestion}")
                
    def should_trigger_rollback(self, alerts: List[WebSocketAlert]) -> Tuple[bool, str]:
        """Determine if alerts should trigger deployment rollback."""
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        
        if not critical_alerts:
            return False, "No critical alerts"
            
        # Check for specific rollback triggers
        for alert in critical_alerts:
            if "business_impact" in alert.alert_id:
                return True, f"High business impact detected: {alert.title}"
            if "websocket_critical" in alert.alert_id:
                return True, f"Critical WebSocket issues: {alert.title}"
                
        # Check for multiple critical alerts
        if len(critical_alerts) >= 2:
            return True, f"Multiple critical alerts detected ({len(critical_alerts)})"
            
        return False, "Critical alerts present but below rollback threshold"
        
    def estimate_mrr_impact(self, alerts: List[WebSocketAlert]) -> int:
        """Estimate MRR impact based on alerts."""
        base_websocket_mrr = 180_000  # $180K monthly WebSocket/chat functionality
        
        # Find the worst metric
        worst_impact = 0.0
        
        for alert in alerts:
            if alert.severity == "critical":
                if "handshake_success_rate" in alert.metrics:
                    success_rate = alert.metrics["handshake_success_rate"]["value"]
                    if success_rate < 50:
                        worst_impact = max(worst_impact, 0.6)  # 60% impact
                    elif success_rate < 70:
                        worst_impact = max(worst_impact, 0.35)  # 35% impact
                    elif success_rate < 85:
                        worst_impact = max(worst_impact, 0.15)  # 15% impact
                        
                if "connection_success_rate" in alert.metrics:
                    success_rate = alert.metrics["connection_success_rate"]["value"]
                    if success_rate < 70:
                        worst_impact = max(worst_impact, 0.5)  # 50% impact
                    elif success_rate < 85:
                        worst_impact = max(worst_impact, 0.25)  # 25% impact
                        
            elif alert.severity == "warning":
                worst_impact = max(worst_impact, 0.05)  # 5% impact for warnings
                
        return int(base_websocket_mrr * worst_impact)


# ============================================================================
# CLI INTEGRATION
# ============================================================================

async def main():
    """Main CLI for WebSocket monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Monitoring and Alerting")
    parser.add_argument("--environment", default="staging", choices=["staging", "production", "development"])
    parser.add_argument("--duration", type=int, default=30, help="Monitoring duration in minutes")
    parser.add_argument("--output-file", help="Save monitoring results to file")
    parser.add_argument("--alert-threshold", choices=["low", "medium", "high"], default="medium", 
                       help="Alert sensitivity threshold")
    
    args = parser.parse_args()
    
    # Initialize monitoring
    monitor = WebSocketHealthMonitor(args.environment)
    alert_manager = WebSocketAlertManager(args.environment)
    
    # Run monitoring
    try:
        logger.info(f" SEARCH:  Starting WebSocket monitoring for {args.environment} environment...")
        results = await monitor.run_monitoring_cycle(args.duration)
        
        # Process alerts
        all_alerts = []
        for alert_data in results["alerts_generated"]:
            alert = WebSocketAlert(
                alert_id=alert_data["alert_id"],
                severity=alert_data["severity"],
                title=alert_data["title"],
                description=alert_data["description"],
                timestamp=datetime.fromisoformat(alert_data["timestamp"]),
                environment=args.environment,
                metrics=alert_data.get("metrics", {}),
                resolution_suggestions=alert_data.get("resolution_suggestions", [])
            )
            all_alerts.append(alert)
            alert_manager.process_alert(alert)
            
        # Check rollback recommendation
        should_rollback, rollback_reason = alert_manager.should_trigger_rollback(all_alerts)
        
        # Estimate business impact
        mrr_impact = alert_manager.estimate_mrr_impact(all_alerts)
        
        # Add summary information
        results["rollback_recommendation"] = {
            "should_rollback": should_rollback,
            "reason": rollback_reason,
            "estimated_mrr_impact": mrr_impact
        }
        
        # Save results if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output_file}")
            
        # Print summary
        print("\n" + "="*80)
        print("WEBSOCKET MONITORING SUMMARY")
        print("="*80)
        print(f"Environment: {args.environment}")
        print(f"Duration: {args.duration} minutes")
        print(f"Cycles: {results['summary']['total_cycles']}")
        print(f"Total Alerts: {results['summary']['total_alerts']}")
        print(f"  - Critical: {results['summary']['critical_alerts']}")
        print(f"  - Warning: {results['summary']['warning_alerts']}")
        print(f"Business Impact: {results['summary']['business_impact'].upper()}")
        print(f"Estimated MRR Impact: ${mrr_impact:,}")
        
        if should_rollback:
            print(f"\n ALERT:  ROLLBACK RECOMMENDED: {rollback_reason}")
        else:
            print(f"\n PASS:  DEPLOYMENT STABLE: {rollback_reason}")
        print("="*80)
        
        # Exit with appropriate code
        if results["summary"]["critical_alerts"] > 0:
            sys.exit(1)  # Critical alerts
        elif results["summary"]["warning_alerts"] > 5:
            sys.exit(2)  # Too many warnings
        else:
            sys.exit(0)  # All good
            
    except KeyboardInterrupt:
        logger.info("WebSocket monitoring interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"WebSocket monitoring error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())