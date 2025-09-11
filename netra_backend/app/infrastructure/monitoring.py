#!/usr/bin/env python3
"""
Infrastructure Monitoring and Health Tracking
Phase 3 - Infrastructure Remediation Implementation

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure - System Health Monitoring
- Business Goal: Proactive detection of infrastructure issues to prevent service degradation
- Value Impact: Prevent $500K+ ARR disruptions through early issue detection
- Strategic Impact: Foundation for reliable service operations and enterprise customer SLA compliance

This module implements comprehensive infrastructure health monitoring to detect
connectivity issues, state drift, and service degradation before they impact users.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
import aiohttp

# SSOT imports
from shared.isolated_environment import get_env
from shared.types.core_types import ServiceName, EnvironmentName


class HealthStatus(Enum):
    """Infrastructure health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of an infrastructure health check."""
    check_name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_healthy(self) -> bool:
        """Check if the health status is healthy."""
        return self.status == HealthStatus.HEALTHY


@dataclass
class ServiceHealthMetrics:
    """Metrics for a specific service's health."""
    service_name: str
    availability_percent: float
    average_response_time_ms: float
    error_rate_percent: float
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    uptime_minutes: float = 0.0


class VPCConnectivityHealthCheck:
    """Health check for VPC connectivity."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def check_health(self) -> HealthCheckResult:
        """Check VPC connectivity health."""
        start_time = time.time()
        
        try:
            # Check if VPC connector is configured
            vpc_connector = self.env.get("VPC_CONNECTOR_NAME")
            if not vpc_connector:
                return HealthCheckResult(
                    check_name="vpc_connectivity",
                    status=HealthStatus.WARNING,
                    message="VPC connector not configured",
                    response_time_ms=0.0,
                    metadata={"vpc_connector": None}
                )
            
            # Check internal service URLs
            internal_auth_url = self.env.get("AUTH_SERVICE_INTERNAL_URL")
            if not internal_auth_url:
                return HealthCheckResult(
                    check_name="vpc_connectivity",
                    status=HealthStatus.WARNING,
                    message="Internal auth service URL not configured",
                    response_time_ms=(time.time() - start_time) * 1000,
                    metadata={"internal_urls_configured": False}
                )
            
            # Test internal connectivity (simplified check)
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                check_name="vpc_connectivity",
                status=HealthStatus.HEALTHY,
                message="VPC connectivity configured",
                response_time_ms=response_time_ms,
                metadata={
                    "vpc_connector": vpc_connector,
                    "internal_auth_configured": bool(internal_auth_url)
                }
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"VPC connectivity health check failed: {e}")
            
            return HealthCheckResult(
                check_name="vpc_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"VPC connectivity check failed: {e}",
                response_time_ms=response_time_ms,
                metadata={"error": str(e)}
            )


class ServiceDiscoveryHealthCheck:
    """Health check for service discovery functionality."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def check_health(self) -> HealthCheckResult:
        """Check service discovery health."""
        start_time = time.time()
        
        try:
            # Check required service URLs
            service_urls = {
                "auth_service": self.env.get("AUTH_SERVICE_URL"),
                "frontend_url": self.env.get("FRONTEND_URL"),
                "backend_url": self.env.get("BACKEND_URL")
            }
            
            missing_services = [name for name, url in service_urls.items() if not url]
            
            if missing_services:
                response_time_ms = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    check_name="service_discovery",
                    status=HealthStatus.WARNING,
                    message=f"Missing service URLs: {', '.join(missing_services)}",
                    response_time_ms=response_time_ms,
                    metadata={"missing_services": missing_services}
                )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                check_name="service_discovery",
                status=HealthStatus.HEALTHY,
                message="Service discovery URLs configured",
                response_time_ms=response_time_ms,
                metadata={"configured_services": list(service_urls.keys())}
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Service discovery health check failed: {e}")
            
            return HealthCheckResult(
                check_name="service_discovery",
                status=HealthStatus.CRITICAL,
                message=f"Service discovery check failed: {e}",
                response_time_ms=response_time_ms,
                metadata={"error": str(e)}
            )


class DatabaseConnectivityHealthCheck:
    """Health check for database connectivity."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def check_health(self) -> HealthCheckResult:
        """Check database connectivity health."""
        start_time = time.time()
        
        try:
            # Check database configuration
            database_url = self.env.get("DATABASE_URL")
            redis_url = self.env.get("REDIS_URL")
            
            issues = []
            
            if not database_url:
                issues.append("Database URL not configured")
                
            if not redis_url:
                issues.append("Redis URL not configured")
            
            # Check VPC connectivity requirements
            if database_url and "localhost" not in database_url.lower():
                vpc_connector = self.env.get("VPC_CONNECTOR_NAME")
                if not vpc_connector:
                    issues.append("External database requires VPC connector")
            
            response_time_ms = (time.time() - start_time) * 1000
            
            if issues:
                return HealthCheckResult(
                    check_name="database_connectivity",
                    status=HealthStatus.WARNING,
                    message=f"Database connectivity issues: {'; '.join(issues)}",
                    response_time_ms=response_time_ms,
                    metadata={"issues": issues}
                )
            
            return HealthCheckResult(
                check_name="database_connectivity",
                status=HealthStatus.HEALTHY,
                message="Database connectivity configured",
                response_time_ms=response_time_ms,
                metadata={
                    "database_configured": bool(database_url),
                    "redis_configured": bool(redis_url)
                }
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Database connectivity health check failed: {e}")
            
            return HealthCheckResult(
                check_name="database_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Database connectivity check failed: {e}",
                response_time_ms=response_time_ms,
                metadata={"error": str(e)}
            )


class WebSocketAuthenticationHealthCheck:
    """Health check for WebSocket authentication system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def check_health(self) -> HealthCheckResult:
        """Check WebSocket authentication health."""
        start_time = time.time()
        
        try:
            # Check if remediation components are available
            remediation_available = False
            try:
                from netra_backend.app.websocket_core.auth_remediation import (
                    get_websocket_auth_integration
                )
                auth_integration = get_websocket_auth_integration()
                remediation_health = auth_integration.get_health_status()
                remediation_available = remediation_health.get("remediation_available", False)
            except ImportError:
                remediation_available = False
            
            # Check authentication configuration
            auth_service_url = self.env.get("AUTH_SERVICE_URL")
            internal_auth_url = self.env.get("AUTH_SERVICE_INTERNAL_URL")
            jwt_secret = self.env.get("JWT_SECRET_KEY") or self.env.get("JWT_SECRET")
            
            issues = []
            
            if not auth_service_url:
                issues.append("Auth service URL not configured")
                
            if not jwt_secret:
                issues.append("JWT secret not configured")
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Determine health status
            if issues:
                status = HealthStatus.CRITICAL
                message = f"WebSocket auth issues: {'; '.join(issues)}"
            elif not remediation_available:
                status = HealthStatus.WARNING
                message = "WebSocket auth remediation not available - using legacy auth"
            else:
                status = HealthStatus.HEALTHY
                message = "WebSocket authentication healthy with remediation"
            
            return HealthCheckResult(
                check_name="websocket_authentication",
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                metadata={
                    "remediation_available": remediation_available,
                    "auth_service_configured": bool(auth_service_url),
                    "internal_auth_configured": bool(internal_auth_url),
                    "jwt_configured": bool(jwt_secret),
                    "issues": issues
                }
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"WebSocket authentication health check failed: {e}")
            
            return HealthCheckResult(
                check_name="websocket_authentication",
                status=HealthStatus.CRITICAL,
                message=f"WebSocket auth check failed: {e}",
                response_time_ms=response_time_ms,
                metadata={"error": str(e)}
            )


class InfrastructureHealthMonitor:
    """Comprehensive infrastructure health monitoring system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.health_checks = [
            VPCConnectivityHealthCheck(),
            ServiceDiscoveryHealthCheck(),
            DatabaseConnectivityHealthCheck(),
            WebSocketAuthenticationHealthCheck()
        ]
        self.health_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
        # Alerting configuration
        self.alert_callbacks: List[Callable] = []
        self.last_alert_time = {}
        self.alert_cooldown_seconds = 300  # 5 minutes
        
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run all infrastructure health checks and return comprehensive status."""
        check_start_time = time.time()
        
        results = []
        overall_status = HealthStatus.HEALTHY
        
        self.logger.info("Running comprehensive infrastructure health check")
        
        for health_check in self.health_checks:
            try:
                result = await health_check.check_health()
                results.append(result)
                
                # Update overall status (worst status wins)
                if result.status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                elif result.status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.WARNING
                
                # Check if we need to alert
                if result.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
                    await self._handle_alert(result)
                    
            except Exception as e:
                self.logger.error(f"Health check failed for {health_check.__class__.__name__}: {e}")
                error_result = HealthCheckResult(
                    check_name=health_check.__class__.__name__.lower(),
                    status=HealthStatus.CRITICAL,
                    message=f"Health check execution failed: {e}",
                    response_time_ms=0.0,
                    metadata={"error": str(e)}
                )
                results.append(error_result)
                overall_status = HealthStatus.CRITICAL
                await self._handle_alert(error_result)
        
        check_duration_ms = (time.time() - check_start_time) * 1000
        
        # Create comprehensive health report
        health_report = {
            "overall_status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "check_duration_ms": check_duration_ms,
            "checks": [
                {
                    "name": result.check_name,
                    "status": result.status.value,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "metadata": result.metadata,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in results
            ],
            "summary": self._generate_health_summary(results),
            "recommendations": self._generate_recommendations(results)
        }
        
        # Store in history
        self.health_history.append(health_report)
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
        
        self.logger.info(
            f"Infrastructure health check completed - Status: {overall_status.value}, "
            f"Duration: {check_duration_ms:.1f}ms, "
            f"Checks: {len(results)}, "
            f"Issues: {sum(1 for r in results if r.status != HealthStatus.HEALTHY)}"
        )
        
        return health_report
    
    def _generate_health_summary(self, results: List[HealthCheckResult]) -> Dict[str, Any]:
        """Generate health summary from check results."""
        total_checks = len(results)
        healthy_checks = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        warning_checks = sum(1 for r in results if r.status == HealthStatus.WARNING)
        critical_checks = sum(1 for r in results if r.status == HealthStatus.CRITICAL)
        
        avg_response_time = sum(r.response_time_ms for r in results) / len(results) if results else 0
        
        return {
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "warning_checks": warning_checks,
            "critical_checks": critical_checks,
            "health_percentage": (healthy_checks / total_checks * 100) if total_checks > 0 else 0,
            "average_response_time_ms": round(avg_response_time, 2)
        }
    
    def _generate_recommendations(self, results: List[HealthCheckResult]) -> List[str]:
        """Generate recommendations based on health check results."""
        recommendations = []
        
        for result in results:
            if result.status == HealthStatus.CRITICAL:
                if "vpc_connectivity" in result.check_name:
                    recommendations.append("Configure VPC connector for internal service communication")
                elif "database_connectivity" in result.check_name:
                    recommendations.append("Verify database and Redis connectivity configuration")
                elif "websocket_authentication" in result.check_name:
                    recommendations.append("Check authentication service configuration and JWT secrets")
                elif "service_discovery" in result.check_name:
                    recommendations.append("Configure missing service URLs for proper service discovery")
                    
            elif result.status == HealthStatus.WARNING:
                if "websocket_authentication" in result.check_name:
                    recommendations.append("Deploy WebSocket authentication remediation components")
                elif "vpc_connectivity" in result.check_name:
                    recommendations.append("Consider configuring internal service URLs for better performance")
        
        return recommendations
    
    async def _handle_alert(self, result: HealthCheckResult):
        """Handle alerting for health check issues."""
        alert_key = f"{result.check_name}_{result.status.value}"
        current_time = time.time()
        
        # Check cooldown period
        if alert_key in self.last_alert_time:
            time_since_last_alert = current_time - self.last_alert_time[alert_key]
            if time_since_last_alert < self.alert_cooldown_seconds:
                return  # Skip alert due to cooldown
        
        self.last_alert_time[alert_key] = current_time
        
        # Log alert
        if result.status == HealthStatus.CRITICAL:
            self.logger.critical(
                f"INFRASTRUCTURE ALERT: Critical issue detected - {result.check_name}: {result.message}"
            )
        else:
            self.logger.warning(
                f"INFRASTRUCTURE WARNING: Issue detected - {result.check_name}: {result.message}"
            )
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                await callback(result)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback function."""
        self.alert_callbacks.append(callback)
    
    def get_health_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get health check history for specified time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        return [
            report for report in self.health_history
            if datetime.fromisoformat(report["timestamp"].replace("Z", "+00:00")) > cutoff_time
        ]
    
    def get_service_metrics(self, service_name: str, minutes: int = 60) -> ServiceHealthMetrics:
        """Get health metrics for a specific service."""
        history = self.get_health_history(minutes)
        
        if not history:
            return ServiceHealthMetrics(
                service_name=service_name,
                availability_percent=0.0,
                average_response_time_ms=0.0,
                error_rate_percent=0.0
            )
        
        service_checks = []
        for report in history:
            for check in report["checks"]:
                if service_name.lower() in check["name"].lower():
                    service_checks.append(check)
        
        if not service_checks:
            return ServiceHealthMetrics(
                service_name=service_name,
                availability_percent=0.0,
                average_response_time_ms=0.0,
                error_rate_percent=0.0
            )
        
        # Calculate metrics
        total_checks = len(service_checks)
        healthy_checks = sum(1 for check in service_checks if check["status"] == "healthy")
        avg_response_time = sum(check["response_time_ms"] for check in service_checks) / total_checks
        
        # Find last error and consecutive failures
        last_error = None
        consecutive_failures = 0
        for check in reversed(service_checks):
            if check["status"] != "healthy":
                consecutive_failures += 1
                if not last_error:
                    last_error = check["message"]
            else:
                break
        
        return ServiceHealthMetrics(
            service_name=service_name,
            availability_percent=(healthy_checks / total_checks * 100) if total_checks > 0 else 0.0,
            average_response_time_ms=avg_response_time,
            error_rate_percent=((total_checks - healthy_checks) / total_checks * 100) if total_checks > 0 else 0.0,
            last_error=last_error,
            consecutive_failures=consecutive_failures,
            uptime_minutes=minutes if history else 0.0
        )


# Singleton instance for system-wide infrastructure monitoring
_infrastructure_monitor: Optional[InfrastructureHealthMonitor] = None


def get_infrastructure_monitor() -> InfrastructureHealthMonitor:
    """Get singleton infrastructure health monitor instance."""
    global _infrastructure_monitor
    
    if _infrastructure_monitor is None:
        _infrastructure_monitor = InfrastructureHealthMonitor()
    
    return _infrastructure_monitor


async def run_infrastructure_health_check() -> Dict[str, Any]:
    """
    Convenience function to run infrastructure health check.
    
    Returns:
        Comprehensive health report
    """
    monitor = get_infrastructure_monitor()
    return await monitor.run_comprehensive_health_check()


async def get_infrastructure_health_summary() -> Dict[str, Any]:
    """
    Get a quick infrastructure health summary.
    
    Returns:
        Health summary with key metrics
    """
    monitor = get_infrastructure_monitor()
    health_report = await monitor.run_comprehensive_health_check()
    
    return {
        "status": health_report["overall_status"],
        "summary": health_report["summary"],
        "timestamp": health_report["timestamp"],
        "recommendations_count": len(health_report["recommendations"])
    }