#!/usr/bin/env python3
"""
Automated Staging Health Checks

Provides pre-deployment validation, continuous monitoring during operation,
post-deployment verification, and rollback triggers on critical failures.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import httpx
import yaml

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from shared.isolated_environment import get_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthCheckMode(Enum):
    """Health check execution modes."""
    PRE_DEPLOYMENT = "pre_deployment"
    CONTINUOUS = "continuous"
    POST_DEPLOYMENT = "post_deployment"
    ROLLBACK_CHECK = "rollback_check"
    VALIDATION = "validation"

class CheckResult(Enum):
    """Health check results."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    CRITICAL = "critical"

class AutomatedHealthChecker:
    """Automated health checks with deployment integration."""
    
    def __init__(self, backend_url: str = "http://localhost:8000", config_path: Optional[str] = None):
        self.backend_url = backend_url
        self.config = self._load_configuration(config_path)
        self.client = None
        
        # Check results storage
        self.check_results: List[Dict[str, Any]] = []
        self.critical_failures: List[Dict[str, Any]] = []
        self.rollback_triggered = False
        
        # Monitoring state
        self.monitoring_active = False
        self.continuous_check_interval = 60  # seconds
        
    def _load_configuration(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load health check configuration."""
        default_config = {
            "thresholds": {
                "overall_health_threshold": 0.8,
                "component_failure_threshold": 2,
                "response_time_threshold_ms": 1000,
                "resource_usage_threshold_percent": 80,
                "consecutive_failure_threshold": 3,
                "rollback_threshold": 0.5
            },
            "deployment_checks": {
                "pre_deployment": [
                    "websocket_health",
                    "database_health",
                    "service_health",
                    "configuration_health",
                    "resource_availability"
                ],
                "post_deployment": [
                    "websocket_health",
                    "database_health",
                    "service_health",
                    "configuration_health",
                    "performance_metrics",
                    "business_impact"
                ]
            },
            "continuous_monitoring": {
                "enabled": True,
                "interval_seconds": 60,
                "checks": [
                    "critical_components",
                    "performance_degradation",
                    "resource_exhaustion",
                    "alert_conditions"
                ]
            },
            "rollback_triggers": {
                "critical_component_failures": 3,
                "overall_health_below": 0.5,
                "business_impact_critical": True,
                "consecutive_failures": 5
            },
            "notifications": {
                "webhook_urls": [],
                "email_recipients": [],
                "slack_channels": []
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                        user_config = yaml.safe_load(f)
                    else:
                        user_config = json.load(f)
                
                # Merge configurations
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    async def run_pre_deployment_checks(self) -> Tuple[CheckResult, Dict[str, Any]]:
        """Run pre-deployment validation checks."""
        logger.info("[U+1F680] Starting pre-deployment health checks")
        
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            checks_to_run = self.config["deployment_checks"]["pre_deployment"]
            results = {}
            overall_result = CheckResult.PASS
            
            for check_name in checks_to_run:
                logger.info(f"Running pre-deployment check: {check_name}")
                result = await self._run_specific_check(check_name, HealthCheckMode.PRE_DEPLOYMENT)
                results[check_name] = result
                
                # Update overall result
                if result["result"] == CheckResult.CRITICAL or result["result"] == CheckResult.FAIL:
                    overall_result = CheckResult.FAIL
                elif result["result"] == CheckResult.WARN and overall_result == CheckResult.PASS:
                    overall_result = CheckResult.WARN
            
            # Generate pre-deployment summary
            summary = self._generate_deployment_summary(results, "pre_deployment")
            
            # Check if deployment should proceed
            deployment_approved = self._evaluate_deployment_approval(results)
            summary["deployment_approved"] = deployment_approved
            
            logger.info(f"Pre-deployment checks completed: {overall_result.value}")
            if not deployment_approved:
                logger.error(" FAIL:  Deployment NOT APPROVED - critical issues found")
            else:
                logger.info(" PASS:  Deployment APPROVED - all checks passed")
            
            return overall_result, summary
            
        except Exception as e:
            logger.error(f"Pre-deployment checks failed: {e}")
            return CheckResult.CRITICAL, {"error": str(e), "deployment_approved": False}
        
        finally:
            if self.client:
                await self.client.aclose()
    
    async def run_post_deployment_verification(self, deployment_id: str) -> Tuple[CheckResult, Dict[str, Any]]:
        """Run post-deployment verification checks."""
        logger.info(f" SEARCH:  Starting post-deployment verification for deployment {deployment_id}")
        
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            # Wait for deployment to stabilize
            logger.info("Waiting for deployment to stabilize...")
            await asyncio.sleep(30)
            
            checks_to_run = self.config["deployment_checks"]["post_deployment"]
            results = {}
            overall_result = CheckResult.PASS
            
            for check_name in checks_to_run:
                logger.info(f"Running post-deployment check: {check_name}")
                result = await self._run_specific_check(check_name, HealthCheckMode.POST_DEPLOYMENT)
                results[check_name] = result
                
                # Update overall result
                if result["result"] == CheckResult.CRITICAL or result["result"] == CheckResult.FAIL:
                    overall_result = CheckResult.FAIL
                elif result["result"] == CheckResult.WARN and overall_result == CheckResult.PASS:
                    overall_result = CheckResult.WARN
            
            # Generate post-deployment summary
            summary = self._generate_deployment_summary(results, "post_deployment")
            summary["deployment_id"] = deployment_id
            
            # Check if rollback is needed
            rollback_needed = self._evaluate_rollback_necessity(results)
            summary["rollback_needed"] = rollback_needed
            
            if rollback_needed:
                logger.error(" ALERT:  ROLLBACK TRIGGERED - critical post-deployment failures detected")
                await self._trigger_rollback(deployment_id, results)
            
            logger.info(f"Post-deployment verification completed: {overall_result.value}")
            
            return overall_result, summary
            
        except Exception as e:
            logger.error(f"Post-deployment verification failed: {e}")
            return CheckResult.CRITICAL, {"error": str(e), "rollback_needed": True}
        
        finally:
            if self.client:
                await self.client.aclose()
    
    async def start_continuous_monitoring(self) -> None:
        """Start continuous health monitoring."""
        logger.info(" CHART:  Starting continuous health monitoring")
        
        if not self.config["continuous_monitoring"]["enabled"]:
            logger.info("Continuous monitoring is disabled in configuration")
            return
        
        self.monitoring_active = True
        self.continuous_check_interval = self.config["continuous_monitoring"]["interval_seconds"]
        
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            while self.monitoring_active:
                try:
                    logger.debug("Running continuous health checks")
                    await self._run_continuous_checks()
                    await asyncio.sleep(self.continuous_check_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Continuous monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Continuous monitoring error: {e}")
                    await asyncio.sleep(10)  # Brief pause before retry
                    
        finally:
            self.monitoring_active = False
            if self.client:
                await self.client.aclose()
    
    def stop_continuous_monitoring(self) -> None:
        """Stop continuous health monitoring."""
        logger.info("Stopping continuous health monitoring")
        self.monitoring_active = False
    
    async def validate_environment(self) -> Tuple[CheckResult, Dict[str, Any]]:
        """Validate staging environment configuration and readiness."""
        logger.info("[U+1F527] Validating staging environment")
        
        try:
            self.client = httpx.AsyncClient(timeout=30.0)
            
            validation_results = {}
            overall_result = CheckResult.PASS
            
            # Check environment configuration
            config_result = await self._validate_environment_configuration()
            validation_results["environment_configuration"] = config_result
            
            # Check service availability
            services_result = await self._validate_service_availability()
            validation_results["service_availability"] = services_result
            
            # Check resource requirements
            resources_result = await self._validate_resource_requirements()
            validation_results["resource_requirements"] = resources_result
            
            # Check network connectivity
            network_result = await self._validate_network_connectivity()
            validation_results["network_connectivity"] = network_result
            
            # Check database readiness
            database_result = await self._validate_database_readiness()
            validation_results["database_readiness"] = database_result
            
            # Determine overall result
            for result in validation_results.values():
                if result["result"] == CheckResult.CRITICAL or result["result"] == CheckResult.FAIL:
                    overall_result = CheckResult.FAIL
                elif result["result"] == CheckResult.WARN and overall_result == CheckResult.PASS:
                    overall_result = CheckResult.WARN
            
            summary = {
                "validation_results": validation_results,
                "overall_result": overall_result.value,
                "environment_ready": overall_result in [CheckResult.PASS, CheckResult.WARN],
                "timestamp": time.time()
            }
            
            logger.info(f"Environment validation completed: {overall_result.value}")
            
            return overall_result, summary
            
        except Exception as e:
            logger.error(f"Environment validation failed: {e}")
            return CheckResult.CRITICAL, {"error": str(e), "environment_ready": False}
        
        finally:
            if self.client:
                await self.client.aclose()
    
    async def _run_specific_check(self, check_name: str, mode: HealthCheckMode) -> Dict[str, Any]:
        """Run a specific health check."""
        start_time = time.time()
        
        try:
            if check_name == "websocket_health":
                return await self._check_websocket_health(mode)
            elif check_name == "database_health":
                return await self._check_database_health(mode)
            elif check_name == "service_health":
                return await self._check_service_health(mode)
            elif check_name == "configuration_health":
                return await self._check_configuration_health(mode)
            elif check_name == "resource_availability":
                return await self._check_resource_availability(mode)
            elif check_name == "performance_metrics":
                return await self._check_performance_metrics(mode)
            elif check_name == "business_impact":
                return await self._check_business_impact(mode)
            elif check_name == "critical_components":
                return await self._check_critical_components(mode)
            elif check_name == "performance_degradation":
                return await self._check_performance_degradation(mode)
            elif check_name == "resource_exhaustion":
                return await self._check_resource_exhaustion(mode)
            elif check_name == "alert_conditions":
                return await self._check_alert_conditions(mode)
            else:
                return {
                    "result": CheckResult.FAIL,
                    "message": f"Unknown check: {check_name}",
                    "duration_seconds": time.time() - start_time
                }
                
        except Exception as e:
            logger.error(f"Check {check_name} failed: {e}")
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Check failed with exception: {str(e)}",
                "duration_seconds": time.time() - start_time,
                "error": str(e)
            }
    
    async def _check_websocket_health(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check WebSocket health."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/websocket")
            response.raise_for_status()
            data = response.json()
            
            health_percentage = data.get("health_percentage", 0)
            components_healthy = data.get("components_healthy", 0)
            components_total = data.get("components_total", 1)
            
            if health_percentage >= 90:
                result = CheckResult.PASS
                message = f"WebSocket health excellent: {health_percentage:.1f}%"
            elif health_percentage >= 70:
                result = CheckResult.WARN
                message = f"WebSocket health degraded: {health_percentage:.1f}%"
            else:
                result = CheckResult.FAIL
                message = f"WebSocket health poor: {health_percentage:.1f}%"
            
            return {
                "result": result,
                "message": message,
                "health_percentage": health_percentage,
                "components_healthy": components_healthy,
                "components_total": components_total,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"WebSocket health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_database_health(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check database health."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/database")
            response.raise_for_status()
            data = response.json()
            
            databases_healthy = data.get("databases_healthy", 0)
            databases_total = data.get("databases_total", 1)
            health_percentage = (databases_healthy / databases_total) * 100 if databases_total > 0 else 0
            
            if databases_healthy == databases_total:
                result = CheckResult.PASS
                message = f"All {databases_total} databases healthy"
            elif databases_healthy >= databases_total * 0.7:
                result = CheckResult.WARN
                message = f"{databases_healthy}/{databases_total} databases healthy"
            else:
                result = CheckResult.FAIL
                message = f"Only {databases_healthy}/{databases_total} databases healthy"
            
            return {
                "result": result,
                "message": message,
                "databases_healthy": databases_healthy,
                "databases_total": databases_total,
                "health_percentage": health_percentage,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Database health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_service_health(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check service dependencies health."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/services")
            response.raise_for_status()
            data = response.json()
            
            services_healthy = data.get("services_healthy", 0)
            services_total = data.get("services_total", 1)
            health_percentage = (services_healthy / services_total) * 100 if services_total > 0 else 0
            
            if services_healthy == services_total:
                result = CheckResult.PASS
                message = f"All {services_total} services healthy"
            elif services_healthy >= services_total * 0.8:
                result = CheckResult.WARN
                message = f"{services_healthy}/{services_total} services healthy"
            else:
                result = CheckResult.FAIL
                message = f"Only {services_healthy}/{services_total} services healthy"
            
            return {
                "result": result,
                "message": message,
                "services_healthy": services_healthy,
                "services_total": services_total,
                "health_percentage": health_percentage,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Service health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_configuration_health(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check configuration health."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/metrics?metric_type=configuration")
            response.raise_for_status()
            data = response.json()
            
            config_status = data.get("configuration", {})
            
            if config_status.get("status") == "metrics_not_available":
                result = CheckResult.WARN
                message = "Configuration metrics not available"
            else:
                # Analyze configuration status
                valid_configs = sum(1 for v in config_status.values() if v is True)
                total_configs = len(config_status)
                
                if valid_configs == total_configs:
                    result = CheckResult.PASS
                    message = "All configurations valid"
                elif valid_configs >= total_configs * 0.8:
                    result = CheckResult.WARN
                    message = f"{valid_configs}/{total_configs} configurations valid"
                else:
                    result = CheckResult.FAIL
                    message = f"Only {valid_configs}/{total_configs} configurations valid"
            
            return {
                "result": result,
                "message": message,
                "configuration_status": config_status,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Configuration health check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_resource_availability(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check resource availability."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/metrics?metric_type=resources")
            response.raise_for_status()
            data = response.json()
            
            resources = data.get("resources", {})
            
            if resources.get("status") == "metrics_not_available":
                result = CheckResult.WARN
                message = "Resource metrics not available"
            else:
                cpu_usage = resources.get("cpu_usage_percent", 0)
                memory_usage = resources.get("memory_usage_percent", 0)
                disk_usage = resources.get("disk_usage_percent", 0)
                
                # Check against thresholds
                threshold = self.config["thresholds"]["resource_usage_threshold_percent"]
                
                high_usage_resources = []
                if cpu_usage > threshold:
                    high_usage_resources.append(f"CPU {cpu_usage:.1f}%")
                if memory_usage > threshold:
                    high_usage_resources.append(f"Memory {memory_usage:.1f}%")
                if disk_usage > threshold:
                    high_usage_resources.append(f"Disk {disk_usage:.1f}%")
                
                if not high_usage_resources:
                    result = CheckResult.PASS
                    message = f"Resource usage normal (CPU: {cpu_usage:.1f}%, Mem: {memory_usage:.1f}%, Disk: {disk_usage:.1f}%)"
                elif len(high_usage_resources) == 1:
                    result = CheckResult.WARN
                    message = f"High resource usage: {high_usage_resources[0]}"
                else:
                    result = CheckResult.FAIL
                    message = f"Multiple resources high: {', '.join(high_usage_resources)}"
            
            return {
                "result": result,
                "message": message,
                "resource_metrics": resources,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Resource availability check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_performance_metrics(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check performance metrics."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/metrics?metric_type=performance")
            response.raise_for_status()
            data = response.json()
            
            performance = data.get("performance", {})
            
            if performance.get("status") == "metrics_not_available":
                result = CheckResult.WARN
                message = "Performance metrics not available"
            else:
                api_time = performance.get("api_response_time_ms", 0)
                ws_latency = performance.get("websocket_latency_ms", 0)
                db_time = performance.get("database_query_time_ms", 0)
                
                # Check against thresholds
                slow_components = []
                if api_time > 500:
                    slow_components.append(f"API {api_time:.1f}ms")
                if ws_latency > 100:
                    slow_components.append(f"WebSocket {ws_latency:.1f}ms")
                if db_time > 50:
                    slow_components.append(f"Database {db_time:.1f}ms")
                
                if not slow_components:
                    result = CheckResult.PASS
                    message = f"Performance good (API: {api_time:.1f}ms, WS: {ws_latency:.1f}ms, DB: {db_time:.1f}ms)"
                elif len(slow_components) == 1:
                    result = CheckResult.WARN
                    message = f"Slow performance: {slow_components[0]}"
                else:
                    result = CheckResult.FAIL
                    message = f"Multiple slow components: {', '.join(slow_components)}"
            
            return {
                "result": result,
                "message": message,
                "performance_metrics": performance,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Performance metrics check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_business_impact(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check business impact level."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/critical")
            response.raise_for_status()
            data = response.json()
            
            critical_analysis = data.get("critical_analysis", {})
            business_impact_level = critical_analysis.get("business_impact_level", "unknown")
            
            if business_impact_level == "none":
                result = CheckResult.PASS
                message = "No business impact detected"
            elif business_impact_level == "moderate":
                result = CheckResult.WARN
                message = "Moderate business impact detected"
            elif business_impact_level == "critical":
                result = CheckResult.CRITICAL
                message = "CRITICAL business impact detected"
            else:
                result = CheckResult.WARN
                message = f"Unknown business impact level: {business_impact_level}"
            
            return {
                "result": result,
                "message": message,
                "business_impact_level": business_impact_level,
                "critical_analysis": critical_analysis,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Business impact check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_critical_components(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check critical components status."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/critical")
            response.raise_for_status()
            data = response.json()
            
            critical_analysis = data.get("critical_analysis", {})
            components_below_threshold = critical_analysis.get("components_below_threshold", 0)
            
            if components_below_threshold == 0:
                result = CheckResult.PASS
                message = "All critical components healthy"
            elif components_below_threshold <= 1:
                result = CheckResult.WARN
                message = f"{components_below_threshold} critical component below threshold"
            else:
                result = CheckResult.FAIL
                message = f"{components_below_threshold} critical components below threshold"
            
            return {
                "result": result,
                "message": message,
                "components_below_threshold": components_below_threshold,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Critical components check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _check_performance_degradation(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check for performance degradation."""
        # This would implement trend analysis for performance degradation
        # For now, we'll use the performance metrics check
        return await self._check_performance_metrics(mode)
    
    async def _check_resource_exhaustion(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check for resource exhaustion."""
        # This would implement more sophisticated resource exhaustion detection
        # For now, we'll use the resource availability check
        return await self._check_resource_availability(mode)
    
    async def _check_alert_conditions(self, mode: HealthCheckMode) -> Dict[str, Any]:
        """Check for active alert conditions."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health")
            response.raise_for_status()
            data = response.json()
            
            alert_status = data.get("alert_status", {})
            alerts_active = alert_status.get("alerts_active", False)
            alert_count = alert_status.get("alert_count", 0)
            alert_severity = alert_status.get("alert_severity", "none")
            
            if not alerts_active:
                result = CheckResult.PASS
                message = "No active alerts"
            elif alert_severity == "critical":
                result = CheckResult.CRITICAL
                message = f"{alert_count} critical alerts active"
            elif alert_severity == "warning":
                result = CheckResult.WARN
                message = f"{alert_count} warning alerts active"
            else:
                result = CheckResult.PASS
                message = f"{alert_count} info alerts active"
            
            return {
                "result": result,
                "message": message,
                "alerts_active": alerts_active,
                "alert_count": alert_count,
                "alert_severity": alert_severity,
                "details": data
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Alert conditions check failed: {str(e)}",
                "error": str(e)
            }
    
    async def _run_continuous_checks(self) -> None:
        """Run continuous monitoring checks."""
        checks_to_run = self.config["continuous_monitoring"]["checks"]
        
        for check_name in checks_to_run:
            try:
                result = await self._run_specific_check(check_name, HealthCheckMode.CONTINUOUS)
                self.check_results.append({
                    "check_name": check_name,
                    "timestamp": time.time(),
                    "mode": HealthCheckMode.CONTINUOUS.value,
                    **result
                })
                
                # Check for critical failures
                if result["result"] == CheckResult.CRITICAL:
                    self.critical_failures.append({
                        "check_name": check_name,
                        "timestamp": time.time(),
                        **result
                    })
                    
                    # Send alert notification
                    await self._send_alert_notification(check_name, result)
                    
                    # Check rollback conditions
                    if self._should_trigger_rollback():
                        logger.error(" ALERT:  ROLLBACK CONDITIONS MET - triggering rollback")
                        await self._trigger_emergency_rollback()
                        break
                
            except Exception as e:
                logger.error(f"Continuous check {check_name} failed: {e}")
        
        # Clean old results (keep last 100)
        if len(self.check_results) > 100:
            self.check_results = self.check_results[-100:]
    
    async def _validate_environment_configuration(self) -> Dict[str, Any]:
        """Validate environment configuration."""
        try:
            env = get_env()
            
            required_vars = [
                "DATABASE_URL",
                "JWT_SECRET_KEY",
                "ENVIRONMENT"
            ]
            
            missing_vars = []
            invalid_vars = []
            
            for var in required_vars:
                value = env.get(var)
                if not value:
                    missing_vars.append(var)
                elif var == "DATABASE_URL" and not value.startswith(("postgresql://", "postgres://")):
                    invalid_vars.append(f"{var}: invalid format")
                elif var == "JWT_SECRET_KEY" and len(value) < 32:
                    invalid_vars.append(f"{var}: too short")
            
            if missing_vars or invalid_vars:
                result = CheckResult.FAIL
                issues = missing_vars + invalid_vars
                message = f"Configuration issues: {', '.join(issues)}"
            else:
                result = CheckResult.PASS
                message = "Environment configuration valid"
            
            return {
                "result": result,
                "message": message,
                "missing_variables": missing_vars,
                "invalid_variables": invalid_vars
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Environment validation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _validate_service_availability(self) -> Dict[str, Any]:
        """Validate service availability."""
        try:
            services_to_check = [
                ("backend", f"{self.backend_url}/health"),
                ("auth_service", "http://localhost:8081/health")
            ]
            
            available_services = []
            unavailable_services = []
            
            for service_name, url in services_to_check:
                try:
                    response = await self.client.get(url, timeout=5.0)
                    if response.status_code == 200:
                        available_services.append(service_name)
                    else:
                        unavailable_services.append(f"{service_name} (status: {response.status_code})")
                except Exception:
                    unavailable_services.append(f"{service_name} (unreachable)")
            
            if not unavailable_services:
                result = CheckResult.PASS
                message = f"All {len(available_services)} services available"
            elif len(unavailable_services) == 1:
                result = CheckResult.WARN
                message = f"1 service unavailable: {unavailable_services[0]}"
            else:
                result = CheckResult.FAIL
                message = f"{len(unavailable_services)} services unavailable"
            
            return {
                "result": result,
                "message": message,
                "available_services": available_services,
                "unavailable_services": unavailable_services
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Service availability validation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _validate_resource_requirements(self) -> Dict[str, Any]:
        """Validate resource requirements."""
        try:
            # Get current resource usage
            response = await self.client.get(f"{self.backend_url}/staging/health/metrics?metric_type=resources")
            response.raise_for_status()
            data = response.json()
            
            resources = data.get("resources", {})
            
            if resources.get("status") == "metrics_not_available":
                result = CheckResult.WARN
                message = "Resource metrics not available for validation"
            else:
                cpu_usage = resources.get("cpu_usage_percent", 0)
                memory_usage = resources.get("memory_usage_percent", 0)
                
                # Check if resources are sufficient for deployment
                if cpu_usage > 80 or memory_usage > 85:
                    result = CheckResult.FAIL
                    message = f"Insufficient resources for deployment (CPU: {cpu_usage:.1f}%, Mem: {memory_usage:.1f}%)"
                elif cpu_usage > 60 or memory_usage > 70:
                    result = CheckResult.WARN
                    message = f"Limited resources available (CPU: {cpu_usage:.1f}%, Mem: {memory_usage:.1f}%)"
                else:
                    result = CheckResult.PASS
                    message = f"Sufficient resources available (CPU: {cpu_usage:.1f}%, Mem: {memory_usage:.1f}%)"
            
            return {
                "result": result,
                "message": message,
                "resource_metrics": resources
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Resource requirements validation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _validate_network_connectivity(self) -> Dict[str, Any]:
        """Validate network connectivity."""
        try:
            # Test connectivity to backend
            start_time = time.time()
            response = await self.client.get(f"{self.backend_url}/health")
            response.raise_for_status()
            backend_latency = (time.time() - start_time) * 1000
            
            if backend_latency < 100:
                result = CheckResult.PASS
                message = f"Network connectivity excellent ({backend_latency:.1f}ms)"
            elif backend_latency < 500:
                result = CheckResult.WARN
                message = f"Network connectivity acceptable ({backend_latency:.1f}ms)"
            else:
                result = CheckResult.FAIL
                message = f"Network connectivity poor ({backend_latency:.1f}ms)"
            
            return {
                "result": result,
                "message": message,
                "backend_latency_ms": backend_latency
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Network connectivity validation failed: {str(e)}",
                "error": str(e)
            }
    
    async def _validate_database_readiness(self) -> Dict[str, Any]:
        """Validate database readiness."""
        try:
            response = await self.client.get(f"{self.backend_url}/staging/health/database")
            response.raise_for_status()
            data = response.json()
            
            databases_healthy = data.get("databases_healthy", 0)
            databases_total = data.get("databases_total", 1)
            
            if databases_healthy == databases_total:
                result = CheckResult.PASS
                message = f"All {databases_total} databases ready"
            elif databases_healthy >= databases_total * 0.7:
                result = CheckResult.WARN
                message = f"{databases_healthy}/{databases_total} databases ready"
            else:
                result = CheckResult.FAIL
                message = f"Only {databases_healthy}/{databases_total} databases ready"
            
            return {
                "result": result,
                "message": message,
                "databases_healthy": databases_healthy,
                "databases_total": databases_total
            }
            
        except Exception as e:
            return {
                "result": CheckResult.CRITICAL,
                "message": f"Database readiness validation failed: {str(e)}",
                "error": str(e)
            }
    
    def _generate_deployment_summary(self, results: Dict[str, Dict[str, Any]], deployment_phase: str) -> Dict[str, Any]:
        """Generate deployment summary from check results."""
        total_checks = len(results)
        passed_checks = sum(1 for r in results.values() if r["result"] == CheckResult.PASS)
        warned_checks = sum(1 for r in results.values() if r["result"] == CheckResult.WARN)
        failed_checks = sum(1 for r in results.values() if r["result"] in [CheckResult.FAIL, CheckResult.CRITICAL])
        
        summary = {
            "deployment_phase": deployment_phase,
            "timestamp": time.time(),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "warned_checks": warned_checks,
            "failed_checks": failed_checks,
            "success_rate": (passed_checks / total_checks) * 100 if total_checks > 0 else 0,
            "detailed_results": results
        }
        
        return summary
    
    def _evaluate_deployment_approval(self, results: Dict[str, Dict[str, Any]]) -> bool:
        """Evaluate whether deployment should be approved."""
        critical_failures = sum(1 for r in results.values() if r["result"] == CheckResult.CRITICAL)
        failures = sum(1 for r in results.values() if r["result"] == CheckResult.FAIL)
        
        # Deployment not approved if any critical failures or too many failures
        if critical_failures > 0:
            return False
        
        if failures > self.config["thresholds"]["component_failure_threshold"]:
            return False
        
        return True
    
    def _evaluate_rollback_necessity(self, results: Dict[str, Dict[str, Any]]) -> bool:
        """Evaluate whether rollback is necessary."""
        critical_failures = sum(1 for r in results.values() if r["result"] == CheckResult.CRITICAL)
        failures = sum(1 for r in results.values() if r["result"] == CheckResult.FAIL)
        
        rollback_triggers = self.config["rollback_triggers"]
        
        if critical_failures >= rollback_triggers["critical_component_failures"]:
            return True
        
        # Check for business impact
        for result in results.values():
            if (result.get("business_impact_level") == "critical" and 
                rollback_triggers["business_impact_critical"]):
                return True
        
        return False
    
    def _should_trigger_rollback(self) -> bool:
        """Check if rollback should be triggered based on continuous monitoring."""
        if len(self.critical_failures) >= self.config["rollback_triggers"]["consecutive_failures"]:
            return True
        
        # Check recent critical failures (last 5 minutes)
        recent_time = time.time() - 300
        recent_critical_failures = [
            f for f in self.critical_failures 
            if f["timestamp"] > recent_time
        ]
        
        return len(recent_critical_failures) >= 3
    
    async def _trigger_rollback(self, deployment_id: str, results: Dict[str, Dict[str, Any]]) -> None:
        """Trigger deployment rollback."""
        logger.error(f" ALERT:  TRIGGERING ROLLBACK for deployment {deployment_id}")
        
        rollback_info = {
            "deployment_id": deployment_id,
            "rollback_triggered_at": time.time(),
            "trigger_reason": "post_deployment_health_check_failures",
            "failed_checks": [
                name for name, result in results.items() 
                if result["result"] in [CheckResult.FAIL, CheckResult.CRITICAL]
            ]
        }
        
        # Send rollback notifications
        await self._send_rollback_notification(rollback_info)
        
        # In a real implementation, this would trigger the actual rollback process
        # For now, we'll just log the rollback action
        logger.info(f"Rollback notification sent for deployment {deployment_id}")
        
        self.rollback_triggered = True
    
    async def _trigger_emergency_rollback(self) -> None:
        """Trigger emergency rollback due to continuous monitoring failures."""
        logger.error(" ALERT:  TRIGGERING EMERGENCY ROLLBACK due to continuous monitoring failures")
        
        rollback_info = {
            "emergency_rollback_triggered_at": time.time(),
            "trigger_reason": "continuous_monitoring_critical_failures",
            "critical_failures_count": len(self.critical_failures),
            "recent_failures": self.critical_failures[-5:] if len(self.critical_failures) >= 5 else self.critical_failures
        }
        
        # Send emergency rollback notifications
        await self._send_rollback_notification(rollback_info)
        
        # Stop continuous monitoring
        self.stop_continuous_monitoring()
        
        self.rollback_triggered = True
    
    async def _send_alert_notification(self, check_name: str, result: Dict[str, Any]) -> None:
        """Send alert notification for critical failures."""
        alert_payload = {
            "alert_type": "health_check_failure",
            "check_name": check_name,
            "severity": result["result"].value,
            "message": result["message"],
            "timestamp": time.time()
        }
        
        # Send to configured webhook URLs
        webhook_urls = self.config["notifications"]["webhook_urls"]
        for webhook_url in webhook_urls:
            try:
                await self.client.post(webhook_url, json=alert_payload)
                logger.info(f"Alert notification sent to {webhook_url}")
            except Exception as e:
                logger.error(f"Failed to send alert to {webhook_url}: {e}")
    
    async def _send_rollback_notification(self, rollback_info: Dict[str, Any]) -> None:
        """Send rollback notification."""
        rollback_payload = {
            "notification_type": "deployment_rollback",
            **rollback_info
        }
        
        # Send to configured webhook URLs
        webhook_urls = self.config["notifications"]["webhook_urls"]
        for webhook_url in webhook_urls:
            try:
                await self.client.post(webhook_url, json=rollback_payload)
                logger.info(f"Rollback notification sent to {webhook_url}")
            except Exception as e:
                logger.error(f"Failed to send rollback notification to {webhook_url}: {e}")


async def main():
    """Main function for automated health checks."""
    parser = argparse.ArgumentParser(description="Automated Staging Health Checks")
    parser.add_argument("mode", choices=[
        "pre-deployment", "post-deployment", "continuous", "validate", "rollback-check"
    ], help="Health check mode")
    parser.add_argument("--deployment-id", help="Deployment ID for post-deployment checks")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output file for results")
    
    args = parser.parse_args()
    
    # Create health checker
    checker = AutomatedHealthChecker(
        backend_url=args.backend_url,
        config_path=args.config
    )
    
    try:
        if args.mode == "pre-deployment":
            result, summary = await checker.run_pre_deployment_checks()
            print(f"Pre-deployment checks: {result.value}")
            print(f"Deployment approved: {summary.get('deployment_approved', False)}")
            
        elif args.mode == "post-deployment":
            if not args.deployment_id:
                print("ERROR: --deployment-id required for post-deployment checks")
                sys.exit(1)
            
            result, summary = await checker.run_post_deployment_verification(args.deployment_id)
            print(f"Post-deployment verification: {result.value}")
            print(f"Rollback needed: {summary.get('rollback_needed', False)}")
            
        elif args.mode == "continuous":
            print("Starting continuous monitoring (Ctrl+C to stop)")
            await checker.start_continuous_monitoring()
            
        elif args.mode == "validate":
            result, summary = await checker.validate_environment()
            print(f"Environment validation: {result.value}")
            print(f"Environment ready: {summary.get('environment_ready', False)}")
            
        elif args.mode == "rollback-check":
            result, summary = await checker.run_post_deployment_verification("rollback-check")
            print(f"Rollback check: {result.value}")
        
        # Save results to file if requested
        if args.output:
            output_data = {
                "mode": args.mode,
                "result": result.value if 'result' in locals() else "unknown",
                "summary": summary if 'summary' in locals() else {},
                "timestamp": time.time()
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"Results saved to {args.output}")
    
    except KeyboardInterrupt:
        print("\\nHealth checks stopped by user")
    except Exception as e:
        print(f"\\nHealth checks failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())