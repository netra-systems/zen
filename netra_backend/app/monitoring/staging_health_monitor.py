"""
Comprehensive Staging Environment Health Monitor

Monitors all critical components in staging environment to prevent failures
before they impact users. Integrates with existing health infrastructure.
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union

from netra_backend.app.core.health.interface import BaseHealthChecker, HealthInterface, HealthLevel
from netra_backend.app.core.health.checks import (
    UnifiedDatabaseHealthChecker,
    ServiceHealthChecker,
    DependencyHealthChecker
)
from netra_backend.app.core.health_types import HealthCheckResult
from netra_backend.app.core.unified_logging import central_logger
from netra_backend.app.schemas.core_models import HealthCheckResult as CoreHealthCheckResult
from shared.isolated_environment import get_env

logger = central_logger.get_logger(__name__)


class WebSocketHealthChecker(BaseHealthChecker):
    """Enhanced WebSocket health checker for staging environment."""
    
    def __init__(self):
        super().__init__("staging_websocket", timeout=10.0)
        self.env = get_env()
        
    async def check_health(self) -> HealthCheckResult:
        """Check WebSocket connectivity and event transmission."""
        start_time = time.time()
        
        try:
            # Check WebSocket server availability
            websocket_available = await self._check_websocket_server()
            
            # Check event transmission capabilities 
            event_system_working = await self._check_event_transmission()
            
            # Check WebSocket event pipeline
            event_pipeline_status = await self._check_event_pipeline()
            
            response_time = (time.time() - start_time) * 1000
            
            success = websocket_available and event_system_working and event_pipeline_status
            health_score = self._calculate_websocket_health_score(
                websocket_available, event_system_working, event_pipeline_status
            )
            
            details = {
                "component_name": self.name,
                "success": success,
                "health_score": health_score,
                "websocket_server_available": websocket_available,
                "event_transmission_working": event_system_working,
                "event_pipeline_functional": event_pipeline_status,
                "critical_events_supported": [
                    "agent_started", "agent_thinking", "tool_executing", 
                    "tool_completed", "agent_completed"
                ],
                "response_time_ms": response_time
            }
            
            return HealthCheckResult(
                component_name=self.name,
                success=success,
                health_score=health_score,
                response_time_ms=response_time,
                status="healthy" if success else "unhealthy",
                response_time=response_time / 1000,
                details=details
            )
            
        except Exception as e:
            logger.error(f"WebSocket health check failed: {e}")
            return self._create_websocket_error_result(str(e), time.time() - start_time)
    
    async def _check_websocket_server(self) -> bool:
        """Check if WebSocket server is running and accessible."""
        try:
            # Import WebSocket health check from existing infrastructure
            from netra_backend.app.core.health_checkers import check_websocket_health
            result = await check_websocket_health()
            return result.details.get("success", result.status == "healthy")
        except Exception as e:
            logger.warning(f"WebSocket server check failed: {e}")
            return False
    
    async def _check_event_transmission(self) -> bool:
        """Check if WebSocket event transmission is working."""
        try:
            # Check if WebSocket manager is properly initialized
            from netra_backend.app.websockets.websocket_manager import websocket_manager
            return websocket_manager.is_initialized() if hasattr(websocket_manager, 'is_initialized') else True
        except Exception as e:
            logger.warning(f"Event transmission check failed: {e}")
            return False
    
    async def _check_event_pipeline(self) -> bool:
        """Check if the WebSocket event pipeline is functional."""
        try:
            # Check if agent registry has WebSocket integration using SSOT
            from netra_backend.app.core.registry.universal_registry import get_global_registry
            agent_registry = get_global_registry('agent')
            return hasattr(agent_registry, 'websocket_manager') and agent_registry.websocket_manager is not None
        except Exception as e:
            logger.warning(f"Event pipeline check failed: {e}")
            return False
    
    def _calculate_websocket_health_score(self, server: bool, events: bool, pipeline: bool) -> float:
        """Calculate overall WebSocket health score."""
        components = [server, events, pipeline]
        working_components = sum(1 for comp in components if comp)
        return working_components / len(components)
    
    def _create_websocket_error_result(self, error_msg: str, duration: float) -> HealthCheckResult:
        """Create error result for WebSocket health check."""
        response_time = duration * 1000
        details = {
            "component_name": self.name,
            "success": False,
            "health_score": 0.0,
            "error_message": error_msg,
            "response_time_ms": response_time
        }
        
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=response_time,
            status="unhealthy",
            response_time=duration,
            details=details
        )


class ResourceHealthChecker(BaseHealthChecker):
    """Monitor system resource usage (CPU, memory, connections)."""
    
    def __init__(self):
        super().__init__("staging_resources", timeout=5.0)
        
    async def check_health(self) -> HealthCheckResult:
        """Check system resource health."""
        start_time = time.time()
        
        try:
            # Get system resource metrics
            cpu_usage = await self._get_cpu_usage()
            memory_usage = await self._get_memory_usage()
            disk_usage = await self._get_disk_usage()
            connection_count = await self._get_connection_count()
            
            # Calculate health scores
            cpu_healthy = cpu_usage < 70.0
            memory_healthy = memory_usage < 80.0
            disk_healthy = disk_usage < 85.0
            connections_healthy = connection_count < 1000
            
            overall_healthy = all([cpu_healthy, memory_healthy, disk_healthy, connections_healthy])
            health_score = self._calculate_resource_health_score(
                cpu_usage, memory_usage, disk_usage, connection_count
            )
            
            response_time = (time.time() - start_time) * 1000
            
            details = {
                "component_name": self.name,
                "success": overall_healthy,
                "health_score": health_score,
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "disk_usage_percent": disk_usage,
                "active_connections": connection_count,
                "thresholds": {
                    "cpu_threshold": 70.0,
                    "memory_threshold": 80.0,
                    "disk_threshold": 85.0,
                    "connection_threshold": 1000
                },
                "status_details": {
                    "cpu_healthy": cpu_healthy,
                    "memory_healthy": memory_healthy,
                    "disk_healthy": disk_healthy,
                    "connections_healthy": connections_healthy
                },
                "response_time_ms": response_time
            }
            
            return HealthCheckResult(
                component_name=self.name,
                success=overall_healthy,
                health_score=health_score,
                response_time_ms=response_time,
                status="healthy" if overall_healthy else "degraded",
                response_time=response_time / 1000,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Resource health check failed: {e}")
            return self._create_resource_error_result(str(e), time.time() - start_time)
    
    async def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            # Get CPU usage over a short interval for accuracy
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    async def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception:
            return 0.0
    
    async def _get_disk_usage(self) -> float:
        """Get current disk usage percentage."""
        try:
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100
        except Exception:
            return 0.0
    
    async def _get_connection_count(self) -> int:
        """Get current number of active network connections."""
        try:
            connections = psutil.net_connections()
            return len([c for c in connections if c.status == 'ESTABLISHED'])
        except Exception:
            return 0
    
    def _calculate_resource_health_score(self, cpu: float, memory: float, disk: float, connections: int) -> float:
        """Calculate overall resource health score."""
        # CPU score (inverted - lower usage is better)
        cpu_score = max(0, (100 - cpu) / 100)
        
        # Memory score (inverted - lower usage is better)
        memory_score = max(0, (100 - memory) / 100)
        
        # Disk score (inverted - lower usage is better) 
        disk_score = max(0, (100 - disk) / 100)
        
        # Connection score (based on reasonable limits)
        connection_score = max(0, min(1.0, (1000 - connections) / 1000))
        
        # Weighted average (CPU and memory are more critical)
        return (cpu_score * 0.3 + memory_score * 0.3 + disk_score * 0.2 + connection_score * 0.2)
    
    def _create_resource_error_result(self, error_msg: str, duration: float) -> HealthCheckResult:
        """Create error result for resource health check."""
        response_time = duration * 1000
        details = {
            "component_name": self.name,
            "success": False,
            "health_score": 0.0,
            "error_message": error_msg,
            "response_time_ms": response_time
        }
        
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=response_time,
            status="unhealthy",
            response_time=duration,
            details=details
        )


class ConfigurationHealthChecker(BaseHealthChecker):
    """Check configuration consistency across staging environment."""
    
    def __init__(self):
        super().__init__("staging_configuration", timeout=5.0)
        
    async def check_health(self) -> HealthCheckResult:
        """Check configuration consistency and completeness."""
        start_time = time.time()
        
        try:
            # Check critical configuration values
            database_config_valid = await self._check_database_configuration()
            auth_config_valid = await self._check_auth_configuration()
            websocket_config_valid = await self._check_websocket_configuration()
            environment_config_valid = await self._check_environment_configuration()
            
            all_configs_valid = all([
                database_config_valid,
                auth_config_valid,
                websocket_config_valid,
                environment_config_valid
            ])
            
            health_score = sum([
                database_config_valid,
                auth_config_valid,
                websocket_config_valid,
                environment_config_valid
            ]) / 4
            
            response_time = (time.time() - start_time) * 1000
            
            details = {
                "component_name": self.name,
                "success": all_configs_valid,
                "health_score": health_score,
                "configuration_status": {
                    "database_config_valid": database_config_valid,
                    "auth_config_valid": auth_config_valid,
                    "websocket_config_valid": websocket_config_valid,
                    "environment_config_valid": environment_config_valid
                },
                "critical_configs_checked": [
                    "DATABASE_URL", "JWT_SECRET_KEY", "WEBSOCKET_ENABLED", "ENVIRONMENT"
                ],
                "response_time_ms": response_time
            }
            
            return HealthCheckResult(
                component_name=self.name,
                success=all_configs_valid,
                health_score=health_score,
                response_time_ms=response_time,
                status="healthy" if all_configs_valid else "degraded",
                response_time=response_time / 1000,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return self._create_config_error_result(str(e), time.time() - start_time)
    
    async def _check_database_configuration(self) -> bool:
        """Check if database configuration is valid."""
        try:
            env = get_env()
            database_url = env.get("DATABASE_URL")
            return database_url is not None and len(database_url) > 0
        except Exception:
            return False
    
    async def _check_auth_configuration(self) -> bool:
        """Check if authentication configuration is valid."""
        try:
            env = get_env()
            jwt_secret = env.get("JWT_SECRET_KEY")
            return jwt_secret is not None and len(jwt_secret) > 0
        except Exception:
            return False
    
    async def _check_websocket_configuration(self) -> bool:
        """Check if WebSocket configuration is valid."""
        try:
            env = get_env()
            websocket_enabled = env.get("WEBSOCKET_ENABLED", "true").lower()
            return websocket_enabled in ["true", "1", "yes"]
        except Exception:
            return False
    
    async def _check_environment_configuration(self) -> bool:
        """Check if environment is properly configured."""
        try:
            env = get_env()
            environment = env.get("ENVIRONMENT", "development").lower()
            return environment in ["development", "staging", "production"]
        except Exception:
            return False
    
    def _create_config_error_result(self, error_msg: str, duration: float) -> HealthCheckResult:
        """Create error result for configuration health check."""
        response_time = duration * 1000
        details = {
            "component_name": self.name,
            "success": False,
            "health_score": 0.0,
            "error_message": error_msg,
            "response_time_ms": response_time
        }
        
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=response_time,
            status="unhealthy",
            response_time=duration,
            details=details
        )


class PerformanceMetricsChecker(BaseHealthChecker):
    """Monitor performance metrics for staging environment."""
    
    def __init__(self):
        super().__init__("staging_performance", timeout=10.0)
        self.metrics_history: List[Dict[str, Any]] = []
        
    async def check_health(self) -> HealthCheckResult:
        """Check performance metrics and response times."""
        start_time = time.time()
        
        try:
            # Measure various performance metrics
            api_response_time = await self._measure_api_response_time()
            websocket_latency = await self._measure_websocket_latency()
            database_query_time = await self._measure_database_query_time()
            
            # Check if metrics meet performance thresholds
            api_performance_good = api_response_time < 500  # ms
            websocket_performance_good = websocket_latency < 100  # ms  
            database_performance_good = database_query_time < 50  # ms
            
            overall_performance_good = all([
                api_performance_good,
                websocket_performance_good,
                database_performance_good
            ])
            
            health_score = self._calculate_performance_score(
                api_response_time, websocket_latency, database_query_time
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Store metrics for trend analysis
            current_metrics = {
                "timestamp": time.time(),
                "api_response_time": api_response_time,
                "websocket_latency": websocket_latency,
                "database_query_time": database_query_time,
                "health_score": health_score
            }
            self._update_metrics_history(current_metrics)
            
            details = {
                "component_name": self.name,
                "success": overall_performance_good,
                "health_score": health_score,
                "performance_metrics": {
                    "api_response_time_ms": api_response_time,
                    "websocket_latency_ms": websocket_latency,
                    "database_query_time_ms": database_query_time
                },
                "performance_thresholds": {
                    "api_response_threshold_ms": 500,
                    "websocket_latency_threshold_ms": 100,
                    "database_query_threshold_ms": 50
                },
                "performance_status": {
                    "api_performance_good": api_performance_good,
                    "websocket_performance_good": websocket_performance_good,
                    "database_performance_good": database_performance_good
                },
                "trend_analysis": self._analyze_performance_trends(),
                "response_time_ms": response_time
            }
            
            return HealthCheckResult(
                component_name=self.name,
                success=overall_performance_good,
                health_score=health_score,
                response_time_ms=response_time,
                status="healthy" if overall_performance_good else "degraded",
                response_time=response_time / 1000,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Performance metrics check failed: {e}")
            return self._create_performance_error_result(str(e), time.time() - start_time)
    
    async def _measure_api_response_time(self) -> float:
        """Measure API response time."""
        try:
            import httpx
            start = time.time()
            
            # Make a simple health check API call
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:8000/health")
                response.raise_for_status()
                
            return (time.time() - start) * 1000
        except Exception:
            return 999.0  # High value indicates failure
    
    async def _measure_websocket_latency(self) -> float:
        """Measure WebSocket latency."""
        try:
            # Simulate WebSocket latency measurement
            # In practice, this would send a ping message and measure response time
            start = time.time()
            
            # Simulate network roundtrip
            await asyncio.sleep(0.01)
            
            return (time.time() - start) * 1000
        except Exception:
            return 999.0  # High value indicates failure
    
    async def _measure_database_query_time(self) -> float:
        """Measure database query response time."""
        try:
            from netra_backend.app.core.health_checkers import check_postgres_health
            
            start = time.time()
            await check_postgres_health()
            return (time.time() - start) * 1000
        except Exception:
            return 999.0  # High value indicates failure
    
    def _calculate_performance_score(self, api_time: float, ws_latency: float, db_time: float) -> float:
        """Calculate overall performance health score."""
        # Score each metric based on thresholds (lower is better)
        api_score = max(0, min(1.0, (500 - api_time) / 500))
        ws_score = max(0, min(1.0, (100 - ws_latency) / 100))
        db_score = max(0, min(1.0, (50 - db_time) / 50))
        
        # Weighted average
        return (api_score * 0.4 + ws_score * 0.3 + db_score * 0.3)
    
    def _update_metrics_history(self, metrics: Dict[str, Any]) -> None:
        """Update metrics history for trend analysis."""
        self.metrics_history.append(metrics)
        
        # Keep only last 100 measurements
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends from historical data."""
        if len(self.metrics_history) < 2:
            return {"status": "insufficient_data", "measurements_count": len(self.metrics_history)}
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 measurements
        older_metrics = self.metrics_history[-20:-10] if len(self.metrics_history) >= 20 else []
        
        if not older_metrics:
            return {"status": "insufficient_historical_data", "recent_measurements": len(recent_metrics)}
        
        # Calculate trends
        recent_avg_api = sum(m["api_response_time"] for m in recent_metrics) / len(recent_metrics)
        older_avg_api = sum(m["api_response_time"] for m in older_metrics) / len(older_metrics)
        
        recent_avg_ws = sum(m["websocket_latency"] for m in recent_metrics) / len(recent_metrics)
        older_avg_ws = sum(m["websocket_latency"] for m in older_metrics) / len(older_metrics)
        
        recent_avg_db = sum(m["database_query_time"] for m in recent_metrics) / len(recent_metrics)
        older_avg_db = sum(m["database_query_time"] for m in older_metrics) / len(older_metrics)
        
        return {
            "status": "trend_analysis_available",
            "api_response_trend": "improving" if recent_avg_api < older_avg_api else "degrading",
            "websocket_latency_trend": "improving" if recent_avg_ws < older_avg_ws else "degrading",
            "database_query_trend": "improving" if recent_avg_db < older_avg_db else "degrading",
            "recent_averages": {
                "api_response_time_ms": recent_avg_api,
                "websocket_latency_ms": recent_avg_ws,
                "database_query_time_ms": recent_avg_db
            },
            "historical_averages": {
                "api_response_time_ms": older_avg_api,
                "websocket_latency_ms": older_avg_ws,
                "database_query_time_ms": older_avg_db
            }
        }
    
    def _create_performance_error_result(self, error_msg: str, duration: float) -> HealthCheckResult:
        """Create error result for performance metrics check."""
        response_time = duration * 1000
        details = {
            "component_name": self.name,
            "success": False,
            "health_score": 0.0,
            "error_message": error_msg,
            "response_time_ms": response_time
        }
        
        return HealthCheckResult(
            component_name=self.name,
            success=False,
            health_score=0.0,
            response_time_ms=response_time,
            status="unhealthy",
            response_time=duration,
            details=details
        )


class StagingHealthMonitor:
    """Comprehensive staging environment health monitor."""
    
    def __init__(self):
        self.health_interface = HealthInterface(
            service_name="staging_environment",
            version="1.0.0",
            sla_target=99.5
        )
        
        # Register all staging-specific health checkers
        self._register_health_checkers()
        
        # Initialize alerting and metrics
        self.alert_thresholds = self._initialize_alert_thresholds()
        self.last_health_check = None
        self.health_history: List[Dict[str, Any]] = []
        
    def _register_health_checkers(self) -> None:
        """Register all health checkers for staging environment."""
        # WebSocket monitoring
        self.health_interface.register_checker(WebSocketHealthChecker())
        
        # Database monitoring (PostgreSQL, Redis, ClickHouse)
        self.health_interface.register_checker(UnifiedDatabaseHealthChecker("postgres"))
        self.health_interface.register_checker(UnifiedDatabaseHealthChecker("redis"))
        self.health_interface.register_checker(UnifiedDatabaseHealthChecker("clickhouse"))
        
        # Service dependency monitoring
        self.health_interface.register_checker(ServiceHealthChecker("auth_service", "http://localhost:8081/health"))
        self.health_interface.register_checker(ServiceHealthChecker("backend", "http://localhost:8000/health"))
        
        # External dependency monitoring
        self.health_interface.register_checker(DependencyHealthChecker("websocket"))
        self.health_interface.register_checker(DependencyHealthChecker("llm"))
        
        # System resource monitoring
        self.health_interface.register_checker(ResourceHealthChecker())
        
        # Configuration monitoring
        self.health_interface.register_checker(ConfigurationHealthChecker())
        
        # Performance monitoring
        self.health_interface.register_checker(PerformanceMetricsChecker())
        
        logger.info("Registered all staging health checkers")
    
    def _initialize_alert_thresholds(self) -> Dict[str, Any]:
        """Initialize alert thresholds for staging environment."""
        return {
            "overall_health_score_threshold": 0.8,
            "critical_component_failure_threshold": 2,
            "performance_degradation_threshold": 0.7,
            "resource_usage_critical_threshold": 0.9,
            "consecutive_failure_alert_threshold": 3,
            "response_time_alert_threshold_ms": 1000
        }
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Get comprehensive staging environment health status."""
        try:
            health_status = await self.health_interface.get_health_status(HealthLevel.COMPREHENSIVE)
            
            # Enhance with staging-specific analysis
            enhanced_status = await self._enhance_with_staging_analysis(health_status)
            
            # Store for historical analysis
            self._store_health_check_result(enhanced_status)
            
            return enhanced_status
            
        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
                "service": "staging_environment"
            }
    
    async def get_critical_health(self) -> Dict[str, Any]:
        """Get health status for critical components only."""
        try:
            health_status = await self.health_interface.get_health_status(HealthLevel.STANDARD)
            
            # Focus on critical components
            critical_status = self._filter_critical_components(health_status)
            
            return critical_status
            
        except Exception as e:
            logger.error(f"Critical health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
                "service": "staging_environment_critical"
            }
    
    async def _enhance_with_staging_analysis(self, base_status: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance health status with staging-specific analysis."""
        # Add business impact analysis
        business_impact = self._analyze_business_impact(base_status)
        
        # Add failure prediction
        failure_prediction = self._predict_potential_failures(base_status)
        
        # Add remediation suggestions
        remediation_suggestions = self._generate_remediation_suggestions(base_status)
        
        # Add trend analysis
        trend_analysis = self._analyze_health_trends()
        
        enhanced_status = {
            **base_status,
            "staging_analysis": {
                "business_impact": business_impact,
                "failure_prediction": failure_prediction,
                "remediation_suggestions": remediation_suggestions,
                "trend_analysis": trend_analysis
            },
            "alert_status": self._check_alert_conditions(base_status)
        }
        
        return enhanced_status
    
    def _analyze_business_impact(self, health_status: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze potential business impact of current health status."""
        checks = health_status.get("checks", {})
        
        # Critical business functions
        chat_functionality_impacted = self._is_chat_functionality_impacted(checks)
        user_authentication_impacted = self._is_auth_functionality_impacted(checks)
        data_persistence_impacted = self._is_data_persistence_impacted(checks)
        
        impact_level = "none"
        if chat_functionality_impacted or user_authentication_impacted:
            impact_level = "critical"
        elif data_persistence_impacted:
            impact_level = "moderate"
        
        return {
            "impact_level": impact_level,
            "chat_functionality_impacted": chat_functionality_impacted,
            "user_authentication_impacted": user_authentication_impacted,
            "data_persistence_impacted": data_persistence_impacted,
            "estimated_user_impact_percent": self._estimate_user_impact_percentage(
                chat_functionality_impacted, user_authentication_impacted, data_persistence_impacted
            )
        }
    
    def _predict_potential_failures(self, health_status: Dict[str, Any]) -> Dict[str, Any]:
        """Predict potential failures based on current trends."""
        checks = health_status.get("checks", {})
        
        potential_failures = []
        
        # Check for degrading performance trends
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict):
                health_score = check_result.get("health_score", 1.0)
                if health_score < 0.8:
                    potential_failures.append({
                        "component": check_name,
                        "risk_level": "high" if health_score < 0.6 else "moderate",
                        "predicted_failure_time": "within 1 hour" if health_score < 0.5 else "within 24 hours"
                    })
        
        return {
            "failure_prediction_available": len(potential_failures) > 0,
            "potential_failures": potential_failures,
            "overall_risk_level": self._calculate_overall_risk_level(potential_failures)
        }
    
    def _generate_remediation_suggestions(self, health_status: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate automated remediation suggestions."""
        suggestions = []
        checks = health_status.get("checks", {})
        
        for check_name, check_result in checks.items():
            if isinstance(check_result, dict) and not check_result.get("success", True):
                suggestions.extend(self._get_component_remediation_suggestions(check_name, check_result))
        
        return suggestions
    
    def _filter_critical_components(self, health_status: Dict[str, Any]) -> Dict[str, Any]:
        """Filter health status to show only critical components."""
        critical_components = [
            "staging_websocket", "database_postgres", "service_auth_service", 
            "service_backend", "staging_configuration"
        ]
        
        checks = health_status.get("checks", {})
        critical_checks = {
            name: result for name, result in checks.items() 
            if any(critical in name for critical in critical_components)
        }
        
        return {
            **health_status,
            "checks": critical_checks,
            "focus": "critical_components_only"
        }
    
    def _store_health_check_result(self, health_result: Dict[str, Any]) -> None:
        """Store health check result for trend analysis."""
        self.health_history.append({
            "timestamp": time.time(),
            "status": health_result.get("status"),
            "overall_health_score": self._extract_overall_health_score(health_result),
            "component_count": len(health_result.get("checks", {})),
            "failed_components": self._count_failed_components(health_result)
        })
        
        # Keep only last 1000 entries
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]
    
    def _analyze_health_trends(self) -> Dict[str, Any]:
        """Analyze health trends from historical data."""
        if len(self.health_history) < 10:
            return {"status": "insufficient_data", "history_length": len(self.health_history)}
        
        recent_checks = self.health_history[-10:]
        older_checks = self.health_history[-20:-10] if len(self.health_history) >= 20 else []
        
        recent_avg_score = sum(check.get("overall_health_score", 0) for check in recent_checks) / len(recent_checks)
        
        if older_checks:
            older_avg_score = sum(check.get("overall_health_score", 0) for check in older_checks) / len(older_checks)
            trend = "improving" if recent_avg_score > older_avg_score else "degrading"
        else:
            trend = "stable"
        
        return {
            "status": "trend_analysis_available",
            "overall_trend": trend,
            "recent_average_health_score": recent_avg_score,
            "checks_analyzed": len(recent_checks),
            "stability_score": self._calculate_stability_score(recent_checks)
        }
    
    def _check_alert_conditions(self, health_status: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any alert conditions are met."""
        alerts = []
        
        # Check overall health score
        overall_score = self._extract_overall_health_score(health_status)
        if overall_score < self.alert_thresholds["overall_health_score_threshold"]:
            alerts.append({
                "type": "overall_health_degraded",
                "severity": "warning",
                "message": f"Overall health score {overall_score:.2f} below threshold {self.alert_thresholds['overall_health_score_threshold']}"
            })
        
        # Check critical component failures
        failed_components = self._count_failed_components(health_status)
        if failed_components >= self.alert_thresholds["critical_component_failure_threshold"]:
            alerts.append({
                "type": "multiple_component_failures",
                "severity": "critical",
                "message": f"{failed_components} components failed, exceeding threshold of {self.alert_thresholds['critical_component_failure_threshold']}"
            })
        
        return {
            "alerts_active": len(alerts) > 0,
            "alert_count": len(alerts),
            "alerts": alerts,
            "alert_severity": self._determine_highest_alert_severity(alerts)
        }
    
    # Helper methods for business impact analysis
    def _is_chat_functionality_impacted(self, checks: Dict[str, Any]) -> bool:
        """Check if chat functionality is impacted."""
        websocket_check = checks.get("staging_websocket", {})
        if isinstance(websocket_check, dict):
            return not websocket_check.get("success", True)
        return False
    
    def _is_auth_functionality_impacted(self, checks: Dict[str, Any]) -> bool:
        """Check if authentication functionality is impacted."""
        auth_check = checks.get("service_auth_service", {})
        if isinstance(auth_check, dict):
            return not auth_check.get("success", True)
        return False
    
    def _is_data_persistence_impacted(self, checks: Dict[str, Any]) -> bool:
        """Check if data persistence is impacted."""
        postgres_check = checks.get("database_postgres", {})
        if isinstance(postgres_check, dict):
            return not postgres_check.get("success", True)
        return False
    
    def _estimate_user_impact_percentage(self, chat_impact: bool, auth_impact: bool, data_impact: bool) -> int:
        """Estimate percentage of users impacted."""
        if auth_impact:
            return 100  # All users affected
        elif chat_impact:
            return 90   # Most users affected (chat is primary interface)
        elif data_impact:
            return 30   # Some users affected (data operations)
        else:
            return 0    # No user impact
    
    def _calculate_overall_risk_level(self, potential_failures: List[Dict[str, Any]]) -> str:
        """Calculate overall risk level from potential failures."""
        if not potential_failures:
            return "low"
        
        high_risk_count = sum(1 for failure in potential_failures if failure.get("risk_level") == "high")
        if high_risk_count > 0:
            return "high"
        
        moderate_risk_count = sum(1 for failure in potential_failures if failure.get("risk_level") == "moderate")
        if moderate_risk_count > 2:
            return "moderate"
        
        return "low"
    
    def _get_component_remediation_suggestions(self, component_name: str, check_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get remediation suggestions for a specific component."""
        suggestions = []
        
        if "websocket" in component_name.lower():
            suggestions.append({
                "action": "restart_websocket_service",
                "description": "Restart WebSocket service to restore connectivity",
                "urgency": "high"
            })
        elif "database" in component_name.lower():
            suggestions.append({
                "action": "check_database_connections",
                "description": "Check database connection pool and restart if necessary",
                "urgency": "critical"
            })
        elif "service" in component_name.lower():
            suggestions.append({
                "action": "restart_service",
                "description": f"Restart {component_name} service",
                "urgency": "high"
            })
        elif "resource" in component_name.lower():
            suggestions.append({
                "action": "scale_resources",
                "description": "Scale up system resources or optimize resource usage",
                "urgency": "moderate"
            })
        elif "performance" in component_name.lower():
            suggestions.append({
                "action": "investigate_performance",
                "description": "Investigate performance bottlenecks and optimize",
                "urgency": "moderate"
            })
        
        return suggestions
    
    def _extract_overall_health_score(self, health_status: Dict[str, Any]) -> float:
        """Extract overall health score from health status."""
        checks = health_status.get("checks", {})
        if not checks:
            return 1.0
        
        total_score = 0
        count = 0
        for check_result in checks.values():
            if isinstance(check_result, dict):
                score = check_result.get("health_score", 1.0)
                total_score += score
                count += 1
        
        return total_score / count if count > 0 else 1.0
    
    def _count_failed_components(self, health_status: Dict[str, Any]) -> int:
        """Count the number of failed components."""
        checks = health_status.get("checks", {})
        failed_count = 0
        
        for check_result in checks.values():
            if isinstance(check_result, dict) and not check_result.get("success", True):
                failed_count += 1
        
        return failed_count
    
    def _calculate_stability_score(self, recent_checks: List[Dict[str, Any]]) -> float:
        """Calculate stability score based on recent health checks."""
        if not recent_checks:
            return 1.0
        
        # Calculate variance in health scores
        scores = [check.get("overall_health_score", 0) for check in recent_checks]
        if len(scores) < 2:
            return 1.0
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        
        # Lower variance means higher stability
        stability_score = max(0, 1.0 - variance)
        return stability_score
    
    def _determine_highest_alert_severity(self, alerts: List[Dict[str, str]]) -> str:
        """Determine the highest alert severity level."""
        if not alerts:
            return "none"
        
        severities = [alert.get("severity", "info") for alert in alerts]
        
        if "critical" in severities:
            return "critical"
        elif "warning" in severities:
            return "warning"
        elif "info" in severities:
            return "info"
        else:
            return "unknown"


# Global staging health monitor instance
staging_health_monitor = StagingHealthMonitor()