#!/usr/bin/env python3
"""
Configuration Drift Detection System
Phase 3 - Infrastructure Remediation Implementation

Business Value Justification (BVJ):
- Segment: Platform/Infrastructure - Configuration Management
- Business Goal: Prevent configuration drift from causing service degradation
- Value Impact: Maintain $500K+ ARR system reliability through consistent configuration
- Strategic Impact: Foundation for enterprise-grade operational excellence

This module implements configuration drift detection to identify when deployed
services diverge from their expected configuration, causing runtime failures.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from enum import Enum
import hashlib

# SSOT imports
from shared.isolated_environment import get_env
from netra_backend.app.infrastructure.monitoring import HealthStatus, HealthCheckResult


class DriftSeverity(Enum):
    """Configuration drift severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ConfigurationItem:
    """Represents a single configuration item."""
    key: str
    expected_value: Any
    actual_value: Optional[Any]
    source: str  # "environment", "secret", "database", etc.
    required: bool = True
    description: str = ""


@dataclass
class DriftDetectionResult:
    """Result of configuration drift detection."""
    item_key: str
    expected_value: Any
    actual_value: Optional[Any]
    severity: DriftSeverity
    message: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def has_drift(self) -> bool:
        """Check if there is configuration drift."""
        return self.expected_value != self.actual_value


class EnvironmentConfigurationValidator:
    """Validates environment configuration against expected values."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def validate_configuration(self) -> List[DriftDetectionResult]:
        """Validate environment configuration for drift."""
        results = []
        
        # Define expected configuration based on environment
        expected_config = self._get_expected_configuration()
        
        for config_item in expected_config:
            result = self._validate_config_item(config_item)
            results.append(result)
        
        return results
    
    def _get_expected_configuration(self) -> List[ConfigurationItem]:
        """Get expected configuration based on current environment."""
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Base configuration for all environments
        base_config = [
            ConfigurationItem(
                key="ENVIRONMENT",
                expected_value=environment,
                actual_value=None,
                source="environment",
                required=True,
                description="Current deployment environment"
            ),
            ConfigurationItem(
                key="AUTH_SERVICE_URL",
                expected_value=f"https://auth.{environment}.netrasystems.ai" if environment != "development" else None,
                actual_value=None,
                source="environment",
                required=environment != "development",
                description="Auth service external URL"
            ),
            ConfigurationItem(
                key="FRONTEND_URL",
                expected_value=f"https://app.{environment}.netrasystems.ai" if environment != "development" else None,
                actual_value=None,
                source="environment",
                required=environment != "development",
                description="Frontend application URL"
            )
        ]
        
        # Environment-specific configuration
        if environment in ["staging", "production"]:
            base_config.extend([
                ConfigurationItem(
                    key="AUTH_SERVICE_INTERNAL_URL",
                    expected_value=f"https://netra-auth-service-uc.a.run.app",
                    actual_value=None,
                    source="environment",
                    required=False,
                    description="Auth service internal VPC URL"
                ),
                ConfigurationItem(
                    key="VPC_CONNECTOR_NAME",
                    expected_value="staging-connector",
                    actual_value=None,
                    source="environment", 
                    required=True,
                    description="VPC connector for internal communication"
                ),
                ConfigurationItem(
                    key="DATABASE_URL",
                    expected_value="<configured>",  # We check presence, not exact value
                    actual_value=None,
                    source="environment",
                    required=True,
                    description="Database connection URL"
                ),
                ConfigurationItem(
                    key="REDIS_URL",
                    expected_value="<configured>",  # We check presence, not exact value
                    actual_value=None,
                    source="environment",
                    required=True,
                    description="Redis connection URL"
                )
            ])
        
        return base_config
    
    def _validate_config_item(self, config_item: ConfigurationItem) -> DriftDetectionResult:
        """Validate a single configuration item."""
        actual_value = self.env.get(config_item.key)
        config_item.actual_value = actual_value
        
        # Special handling for presence checks
        if config_item.expected_value == "<configured>":
            if actual_value is None or actual_value == "":
                return DriftDetectionResult(
                    item_key=config_item.key,
                    expected_value="configured value",
                    actual_value="not configured" if actual_value is None else "empty",
                    severity=DriftSeverity.CRITICAL if config_item.required else DriftSeverity.WARNING,
                    message=f"Required configuration '{config_item.key}' is not configured",
                    source=config_item.source
                )
            else:
                return DriftDetectionResult(
                    item_key=config_item.key,
                    expected_value="configured value",
                    actual_value="configured",
                    severity=DriftSeverity.INFO,
                    message=f"Configuration '{config_item.key}' is properly configured",
                    source=config_item.source
                )
        
        # Standard value comparison
        if config_item.expected_value != actual_value:
            if config_item.required:
                severity = DriftSeverity.CRITICAL
                message = f"Critical configuration drift: '{config_item.key}' expected '{config_item.expected_value}', got '{actual_value}'"
            else:
                severity = DriftSeverity.WARNING
                message = f"Configuration drift: '{config_item.key}' expected '{config_item.expected_value}', got '{actual_value}'"
            
            return DriftDetectionResult(
                item_key=config_item.key,
                expected_value=config_item.expected_value,
                actual_value=actual_value,
                severity=severity,
                message=message,
                source=config_item.source
            )
        else:
            return DriftDetectionResult(
                item_key=config_item.key,
                expected_value=config_item.expected_value,
                actual_value=actual_value,
                severity=DriftSeverity.INFO,
                message=f"Configuration '{config_item.key}' matches expected value",
                source=config_item.source
            )


class ServiceConfigurationValidator:
    """Validates service-specific configuration consistency."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.env = get_env()
        
    async def validate_service_configuration(self) -> List[DriftDetectionResult]:
        """Validate service configuration for consistency."""
        results = []
        
        # Validate WebSocket configuration consistency
        results.extend(await self._validate_websocket_configuration())
        
        # Validate authentication configuration consistency
        results.extend(await self._validate_authentication_configuration())
        
        # Validate database configuration consistency
        results.extend(await self._validate_database_configuration())
        
        return results
    
    async def _validate_websocket_configuration(self) -> List[DriftDetectionResult]:
        """Validate WebSocket configuration consistency."""
        results = []
        
        # Check WebSocket timeout configuration consistency
        connection_timeout = self.env.get("WEBSOCKET_CONNECTION_TIMEOUT", "300")
        heartbeat_interval = self.env.get("WEBSOCKET_HEARTBEAT_INTERVAL", "30")
        
        try:
            connection_timeout_val = int(connection_timeout)
            heartbeat_interval_val = int(heartbeat_interval)
            
            # Validate that heartbeat interval is reasonable compared to connection timeout
            if heartbeat_interval_val >= connection_timeout_val:
                results.append(DriftDetectionResult(
                    item_key="websocket_timeout_consistency",
                    expected_value=f"heartbeat_interval < connection_timeout",
                    actual_value=f"heartbeat: {heartbeat_interval_val}, timeout: {connection_timeout_val}",
                    severity=DriftSeverity.WARNING,
                    message=f"WebSocket heartbeat interval ({heartbeat_interval_val}s) should be less than connection timeout ({connection_timeout_val}s)",
                    source="environment"
                ))
            else:
                results.append(DriftDetectionResult(
                    item_key="websocket_timeout_consistency", 
                    expected_value="heartbeat_interval < connection_timeout",
                    actual_value=f"heartbeat: {heartbeat_interval_val}, timeout: {connection_timeout_val}",
                    severity=DriftSeverity.INFO,
                    message="WebSocket timeout configuration is consistent",
                    source="environment"
                ))
        except ValueError as e:
            results.append(DriftDetectionResult(
                item_key="websocket_timeout_consistency",
                expected_value="numeric timeout values",
                actual_value=f"connection_timeout: {connection_timeout}, heartbeat_interval: {heartbeat_interval}",
                severity=DriftSeverity.CRITICAL,
                message=f"WebSocket timeout configuration contains non-numeric values: {e}",
                source="environment"
            ))
        
        return results
    
    async def _validate_authentication_configuration(self) -> List[DriftDetectionResult]:
        """Validate authentication configuration consistency."""
        results = []
        
        # Check JWT secret configuration
        jwt_secret = self.env.get("JWT_SECRET_KEY") or self.env.get("JWT_SECRET")
        auth_service_url = self.env.get("AUTH_SERVICE_URL")
        
        if auth_service_url and not jwt_secret:
            results.append(DriftDetectionResult(
                item_key="auth_jwt_consistency",
                expected_value="JWT secret when auth service configured",
                actual_value="auth_service configured, jwt_secret missing",
                severity=DriftSeverity.CRITICAL,
                message="Auth service is configured but JWT secret is missing",
                source="environment"
            ))
        elif jwt_secret and auth_service_url:
            results.append(DriftDetectionResult(
                item_key="auth_jwt_consistency",
                expected_value="JWT secret and auth service both configured",
                actual_value="both configured",
                severity=DriftSeverity.INFO,
                message="Authentication configuration is consistent",
                source="environment"
            ))
        
        return results
    
    async def _validate_database_configuration(self) -> List[DriftDetectionResult]:
        """Validate database configuration consistency."""
        results = []
        
        database_url = self.env.get("DATABASE_URL")
        redis_url = self.env.get("REDIS_URL")
        vpc_connector = self.env.get("VPC_CONNECTOR_NAME")
        environment = self.env.get("ENVIRONMENT", "development").lower()
        
        # Check if external databases require VPC connector
        if environment in ["staging", "production"]:
            external_db_issues = []
            
            if database_url and "localhost" not in database_url.lower() and not vpc_connector:
                external_db_issues.append("DATABASE_URL requires VPC connector for external access")
                
            if redis_url and "localhost" not in redis_url.lower() and not vpc_connector:
                external_db_issues.append("REDIS_URL requires VPC connector for external access")
            
            if external_db_issues:
                results.append(DriftDetectionResult(
                    item_key="database_vpc_consistency",
                    expected_value="VPC connector for external database access",
                    actual_value="external databases configured without VPC connector",
                    severity=DriftSeverity.CRITICAL,
                    message=f"Database VPC inconsistency: {'; '.join(external_db_issues)}",
                    source="environment"
                ))
            else:
                results.append(DriftDetectionResult(
                    item_key="database_vpc_consistency",
                    expected_value="proper VPC configuration for databases",
                    actual_value="databases properly configured",
                    severity=DriftSeverity.INFO,
                    message="Database VPC configuration is consistent",
                    source="environment"
                ))
        
        return results


class ConfigurationDriftDetector:
    """Main configuration drift detection system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validators = [
            EnvironmentConfigurationValidator(),
            ServiceConfigurationValidator()
        ]
        self.drift_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        
    async def detect_configuration_drift(self) -> Dict[str, Any]:
        """Detect configuration drift across all validators."""
        detection_start_time = time.time()
        
        all_results = []
        validation_summary = {
            "total_items": 0,
            "info_count": 0,
            "warning_count": 0,
            "critical_count": 0,
            "drift_items": 0
        }
        
        self.logger.info("Starting comprehensive configuration drift detection")
        
        for validator in self.validators:
            try:
                results = await validator.validate_configuration()
                all_results.extend(results)
                
                # Update summary
                validation_summary["total_items"] += len(results)
                for result in results:
                    if result.severity == DriftSeverity.INFO:
                        validation_summary["info_count"] += 1
                    elif result.severity == DriftSeverity.WARNING:
                        validation_summary["warning_count"] += 1
                    elif result.severity == DriftSeverity.CRITICAL:
                        validation_summary["critical_count"] += 1
                    
                    if result.has_drift:
                        validation_summary["drift_items"] += 1
                        
            except Exception as e:
                self.logger.error(f"Configuration validation failed for {validator.__class__.__name__}: {e}")
                # Add error result
                all_results.append(DriftDetectionResult(
                    item_key=f"{validator.__class__.__name__.lower()}_validation_error",
                    expected_value="successful validation",
                    actual_value=f"validation failed: {e}",
                    severity=DriftSeverity.CRITICAL,
                    message=f"Configuration validation failed: {e}",
                    source="validator"
                ))
                validation_summary["critical_count"] += 1
                validation_summary["drift_items"] += 1
        
        detection_duration_ms = (time.time() - detection_start_time) * 1000
        
        # Determine overall drift status
        overall_status = self._determine_overall_drift_status(all_results)
        
        # Create drift report
        drift_report = {
            "overall_status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detection_duration_ms": detection_duration_ms,
            "summary": validation_summary,
            "drift_items": [
                {
                    "key": result.item_key,
                    "expected": str(result.expected_value),
                    "actual": str(result.actual_value),
                    "severity": result.severity.value,
                    "message": result.message,
                    "source": result.source,
                    "has_drift": result.has_drift,
                    "timestamp": result.timestamp.isoformat()
                }
                for result in all_results
            ],
            "critical_drift": [
                {
                    "key": result.item_key,
                    "message": result.message,
                    "expected": str(result.expected_value),
                    "actual": str(result.actual_value)
                }
                for result in all_results
                if result.severity == DriftSeverity.CRITICAL and result.has_drift
            ],
            "recommendations": self._generate_drift_recommendations(all_results)
        }
        
        # Store in history
        self.drift_history.append(drift_report)
        if len(self.drift_history) > self.max_history:
            self.drift_history = self.drift_history[-self.max_history:]
        
        self.logger.info(
            f"Configuration drift detection completed - Status: {overall_status}, "
            f"Duration: {detection_duration_ms:.1f}ms, "
            f"Total items: {validation_summary['total_items']}, "
            f"Drift items: {validation_summary['drift_items']}, "
            f"Critical: {validation_summary['critical_count']}"
        )
        
        return drift_report
    
    def _determine_overall_drift_status(self, results: List[DriftDetectionResult]) -> str:
        """Determine overall drift status from results."""
        if any(r.severity == DriftSeverity.CRITICAL and r.has_drift for r in results):
            return "critical_drift"
        elif any(r.severity == DriftSeverity.WARNING and r.has_drift for r in results):
            return "warning_drift"
        elif any(r.has_drift for r in results):
            return "minor_drift"
        else:
            return "no_drift"
    
    def _generate_drift_recommendations(self, results: List[DriftDetectionResult]) -> List[str]:
        """Generate recommendations based on drift detection results."""
        recommendations = []
        
        critical_items = [r for r in results if r.severity == DriftSeverity.CRITICAL and r.has_drift]
        
        for item in critical_items:
            if "vpc" in item.item_key.lower():
                recommendations.append("Configure VPC connector for proper internal service communication")
            elif "auth" in item.item_key.lower():
                recommendations.append("Verify authentication service configuration and JWT secrets")
            elif "database" in item.item_key.lower():
                recommendations.append("Check database connection configuration and network accessibility")
            elif "websocket" in item.item_key.lower():
                recommendations.append("Review WebSocket timeout and heartbeat configuration")
            elif "environment" in item.source.lower():
                recommendations.append(f"Set environment variable '{item.item_key}' to expected value")
        
        # Add general recommendations
        if critical_items:
            recommendations.append("Critical configuration drift detected - immediate attention required")
            recommendations.append("Verify deployment pipeline consistency and configuration management")
        
        return list(set(recommendations))  # Remove duplicates
    
    def get_drift_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get configuration drift history for specified time window."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        return [
            report for report in self.drift_history
            if datetime.fromisoformat(report["timestamp"].replace("Z", "+00:00")) > cutoff_time
        ]
    
    def get_drift_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get configuration drift trends over time."""
        history = self.get_drift_history(hours * 60)
        
        if not history:
            return {
                "trend": "no_data",
                "drift_frequency": 0.0,
                "critical_incidents": 0,
                "most_common_issues": []
            }
        
        # Calculate trend metrics
        drift_reports = [r for r in history if r["overall_status"] != "no_drift"]
        critical_reports = [r for r in history if "critical" in r["overall_status"]]
        
        # Find most common drift issues
        issue_counts = {}
        for report in drift_reports:
            for item in report["drift_items"]:
                if item["has_drift"]:
                    key = item["key"]
                    issue_counts[key] = issue_counts.get(key, 0) + 1
        
        most_common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "trend": "improving" if len(drift_reports) < len(history) / 2 else "stable",
            "drift_frequency": len(drift_reports) / len(history) * 100 if history else 0,
            "critical_incidents": len(critical_reports),
            "most_common_issues": [{"issue": k, "count": v} for k, v in most_common_issues],
            "total_reports": len(history),
            "time_window_hours": hours
        }


# Singleton instance for system-wide drift detection
_drift_detector: Optional[ConfigurationDriftDetector] = None


def get_drift_detector() -> ConfigurationDriftDetector:
    """Get singleton configuration drift detector instance."""
    global _drift_detector
    
    if _drift_detector is None:
        _drift_detector = ConfigurationDriftDetector()
    
    return _drift_detector


async def detect_infrastructure_drift() -> Dict[str, Any]:
    """
    Convenience function to detect configuration drift.
    
    Returns:
        Configuration drift report
    """
    detector = get_drift_detector()
    return await detector.detect_configuration_drift()


async def get_drift_summary() -> Dict[str, Any]:
    """
    Get a quick configuration drift summary.
    
    Returns:
        Drift summary with key metrics
    """
    detector = get_drift_detector()
    drift_report = await detector.detect_configuration_drift()
    
    return {
        "status": drift_report["overall_status"],
        "summary": drift_report["summary"],
        "critical_count": len(drift_report["critical_drift"]),
        "recommendations_count": len(drift_report["recommendations"]),
        "timestamp": drift_report["timestamp"]
    }