"""Services Tests - Split from test_multi_service_health.py

Business Value Justification (BVJ):
- Segment: Enterprise  
- Business Goal: Operational visibility and SLA compliance
- Value Impact: Prevents $20K MRR revenue loss from service outages
- Revenue Impact: Zero downtime monitoring for Enterprise tier

This test validates unified health monitoring across all microservices:
1. Unified health endpoint aggregation 
2. Individual service health validation
3. Dependency health check propagation
4. Alert threshold validation and triggering
5. Multi-service communication health

CRITICAL: NO MOCKS - Uses real health endpoints and monitoring systems
"""

import asyncio
import pytest
import httpx
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
from app.logging_config import central_logger
from app.core.health import HealthInterface, HealthLevel, DatabaseHealthChecker, DependencyHealthChecker
from app.core.system_health_monitor import SystemHealthMonitor
from app.core.alert_manager import HealthAlertManager
from app.core.health_types import HealthCheckResult
from app.routes.health import health_interface
from app.config import settings
import os

    def __init__(self):
        self.health_results: Dict[str, Any] = {}
        self.alert_manager = HealthAlertManager()
        self.system_monitor = SystemHealthMonitor()
        # Create a new health interface to avoid conflicts with the existing one
        self.unified_interface = HealthInterface("test-multi-service", "1.0.0")
        self._setup_test_health_checkers()

    def _setup_test_health_checkers(self) -> None:
        """Setup health checkers for testing."""
        # Register basic database and dependency checkers
        self.unified_interface.register_checker(DatabaseHealthChecker("postgres"))
        self.unified_interface.register_checker(DatabaseHealthChecker("redis"))
        self.unified_interface.register_checker(DependencyHealthChecker("websocket"))

    def _validate_service_identity(self, response_data: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Validate service identity matches expected configuration."""
        expected_service = config.get("expected_service")
        if not expected_service:
            return True  # No validation required
        actual_service = response_data.get("service")
        return actual_service == expected_service

    def _format_dependency_result(self, result: HealthCheckResult) -> Dict[str, Any]:
        """Format dependency health check result."""
        # The HealthCheckResult uses details.success, not a top-level success attribute
        success = result.details.get("success", result.status == "healthy")
        return {
            "healthy": success and result.status == "healthy",
            "status": result.status,
            "response_time_ms": result.response_time * 1000,
            "health_score": result.details.get("health_score", 1.0 if success else 0.0),
            "component_name": result.details.get("component_name", "unknown"),
            "error": result.details.get("error_message") if result.status != "healthy" else None
        }

    def _is_clickhouse_disabled(self) -> bool:
        """Check if ClickHouse is disabled in environment."""
        import os
        return os.getenv("SKIP_CLICKHOUSE_INIT", "false").lower() == "true"
