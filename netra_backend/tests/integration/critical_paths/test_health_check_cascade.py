"""Health Check Cascade with Dependencies Critical Path Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all tiers)
- Business Goal: Proactive monitoring and issue detection
- Value Impact: Protects $7K MRR via proactive monitoring and faster incident response
- Strategic Impact: Enables SLA compliance and customer trust through reliability

Critical Path: Service health check -> Dependency validation -> Health propagation -> Alert generation
Coverage: Health check orchestration, dependency mapping, cascading health status, alerting
"""

import pytest
import asyncio
import time
import logging
import json
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock

from netra_backend.app.services.health_check_service import HealthCheckService
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.services.monitoring.alerting_service import AlertingService

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = logging.getLogger(__name__)


class HealthCheckCascadeManager:
    """Manages health check cascade testing with dependencies."""
    
    def __init__(self):
        self.health_service = None
        self.db_manager = None
        self.redis_service = None
        self.alerting_service = None
        self.health_checks = []
        self.dependency_map = {}
        self.alert_events = []
        
    async def initialize_services(self):
        """Initialize health check cascade services."""
        self.health_service = HealthCheckService()
        await self.health_service.start()
        
        self.db_manager = DatabaseConnectionManager()
        await self.db_manager.initialize()
        
        self.redis_service = RedisService()
        await self.redis_service.connect()
        
        self.alerting_service = AlertingService()
        await self.alerting_service.initialize()
        
        # Configure dependency map
        self.dependency_map = {
            "api_service": ["database", "redis"],
            "websocket_service": ["redis", "auth_service"],
            "auth_service": ["database"],
            "agent_service": ["database", "redis", "llm_service"]
        }
    
    async def register_service_health_check(self, service_name: str, 
                                          check_function: callable) -> Dict[str, Any]:
        """Register health check for a service."""
        registration_start = time.time()
        
        try:
            # Register health check
            registration_result = await self.health_service.register_health_check(
                service_name, check_function, {
                    "timeout": 5.0,
                    "interval": 10.0,
                    "dependencies": self.dependency_map.get(service_name, [])
                }
            )
            
            health_check_info = {
                "service_name": service_name,
                "registration_success": registration_result.get("success", False),
                "dependencies": self.dependency_map.get(service_name, []),
                "registration_time": time.time() - registration_start
            }
            
            self.health_checks.append(health_check_info)
            return health_check_info
            
        except Exception as e:
            return {
                "service_name": service_name,
                "registration_success": False,
                "error": str(e),
                "registration_time": time.time() - registration_start
            }
    
    async def simulate_service_failure(self, service_name: str) -> Dict[str, Any]:
        """Simulate service failure and observe cascade."""
        failure_start = time.time()
        
        # Simulate failure
        failure_result = await self.health_service.simulate_failure(service_name)
        
        # Wait for cascade to propagate
        await asyncio.sleep(0.5)
        
        # Check health of all services
        cascade_health = {}
        for health_check in self.health_checks:
            health_status = await self.health_service.get_health_status(
                health_check["service_name"]
            )
            cascade_health[health_check["service_name"]] = health_status
        
        return {
            "failed_service": service_name,
            "failure_simulated": failure_result.get("success", False),
            "cascade_health": cascade_health,
            "cascade_time": time.time() - failure_start
        }
    
    async def test_dependency_health_propagation(self, services: List[str]) -> Dict[str, Any]:
        """Test health status propagation through dependencies."""
        propagation_start = time.time()
        
        # Check initial health status
        initial_health = {}
        for service in services:
            health = await self.health_service.get_health_status(service)
            initial_health[service] = health
        
        # Simulate failure in a core dependency (database)
        db_failure = await self.simulate_service_failure("database")
        
        # Check health propagation
        propagated_health = {}
        for service in services:
            health = await self.health_service.get_health_status(service)
            propagated_health[service] = health
        
        # Analyze impact
        affected_services = []
        for service in services:
            if service != "database":
                if "database" in self.dependency_map.get(service, []):
                    if (initial_health[service].get("status") == "healthy" and 
                        propagated_health[service].get("status") != "healthy"):
                        affected_services.append(service)
        
        return {
            "initial_health": initial_health,
            "propagated_health": propagated_health,
            "affected_services": affected_services,
            "propagation_time": time.time() - propagation_start,
            "cascade_detected": len(affected_services) > 0
        }
    
    async def test_health_check_alerting(self, critical_services: List[str]) -> Dict[str, Any]:
        """Test alerting integration with health checks."""
        alerting_start = time.time()
        
        # Configure alerts for critical services
        alert_configs = []
        for service in critical_services:
            alert_config = await self.alerting_service.configure_health_alert(
                service, {
                    "severity": "critical",
                    "notify_channels": ["email", "slack"],
                    "escalation_timeout": 300
                }
            )
            alert_configs.append(alert_config)
        
        # Simulate failure and check alerting
        failed_service = critical_services[0]
        await self.simulate_service_failure(failed_service)
        
        # Wait for alerts to trigger
        await asyncio.sleep(1.0)
        
        # Check generated alerts
        generated_alerts = await self.alerting_service.get_recent_alerts(
            service_filter=failed_service
        )
        
        return {
            "critical_services": critical_services,
            "alert_configs": alert_configs,
            "failed_service": failed_service,
            "generated_alerts": generated_alerts,
            "alerting_time": time.time() - alerting_start,
            "alerts_triggered": len(generated_alerts) > 0
        }
    
    async def cleanup(self):
        """Clean up health check cascade resources."""
        # Clear health check registrations
        for health_check in self.health_checks:
            await self.health_service.unregister_health_check(
                health_check["service_name"]
            )
        
        # Clear alert configurations
        for alert in self.alert_events:
            await self.alerting_service.clear_alert_config(alert["service"])
        
        if self.health_service:
            await self.health_service.stop()
        if self.db_manager:
            await self.db_manager.shutdown()
        if self.redis_service:
            await self.redis_service.disconnect()
        if self.alerting_service:
            await self.alerting_service.shutdown()


@pytest.fixture
async def health_cascade_manager():
    """Create health check cascade manager for testing."""
    manager = HealthCheckCascadeManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_service_health_check_registration(health_cascade_manager):
    """Test service health check registration and basic functionality."""
    manager = health_cascade_manager
    
    # Mock health check function
    async def mock_api_health():
        return {"status": "healthy", "response_time": 0.1}
    
    # Register health check
    registration_result = await manager.register_service_health_check(
        "api_service", mock_api_health
    )
    
    assert registration_result["registration_success"] is True
    assert registration_result["registration_time"] < 0.5
    assert "database" in registration_result["dependencies"]
    assert "redis" in registration_result["dependencies"]


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_dependency_cascade_failure_detection(health_cascade_manager):
    """Test cascade failure detection through dependencies."""
    manager = health_cascade_manager
    
    # Register multiple services with dependencies
    services = ["api_service", "websocket_service", "auth_service", "agent_service"]
    
    for service in services:
        async def mock_health():
            return {"status": "healthy"}
        
        await manager.register_service_health_check(service, mock_health)
    
    # Test dependency propagation
    propagation_result = await manager.test_dependency_health_propagation(services)
    
    assert propagation_result["cascade_detected"] is True
    assert propagation_result["propagation_time"] < 2.0
    assert len(propagation_result["affected_services"]) >= 1
    
    # Verify services dependent on database are affected
    dependent_services = [s for s in services if "database" in manager.dependency_map.get(s, [])]
    affected_services = propagation_result["affected_services"]
    
    # At least some dependent services should be affected
    assert any(service in affected_services for service in dependent_services)


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_health_check_alerting_integration(health_cascade_manager):
    """Test integration between health checks and alerting system."""
    manager = health_cascade_manager
    
    # Test with critical services
    critical_services = ["api_service", "auth_service"]
    
    # Register services first
    for service in critical_services:
        async def mock_health():
            return {"status": "healthy"}
        
        await manager.register_service_health_check(service, mock_health)
    
    # Test alerting integration
    alerting_result = await manager.test_health_check_alerting(critical_services)
    
    assert alerting_result["alerts_triggered"] is True
    assert alerting_result["alerting_time"] < 3.0
    assert len(alerting_result["generated_alerts"]) > 0
    
    # Verify alert contains relevant information
    first_alert = alerting_result["generated_alerts"][0]
    assert first_alert.get("service") == alerting_result["failed_service"]
    assert first_alert.get("severity") in ["critical", "warning"]


@pytest.mark.asyncio
@pytest.mark.l3_realism
async def test_health_check_recovery_detection(health_cascade_manager):
    """Test health check recovery detection and cascade restoration."""
    manager = health_cascade_manager
    
    # Register service
    async def mock_health():
        return {"status": "healthy"}
    
    await manager.register_service_health_check("api_service", mock_health)
    
    # Simulate failure
    failure_result = await manager.simulate_service_failure("api_service")
    assert failure_result["failure_simulated"] is True
    
    # Wait for failure to be detected
    await asyncio.sleep(0.5)
    
    # Check failed status
    failed_status = await manager.health_service.get_health_status("api_service")
    assert failed_status.get("status") != "healthy"
    
    # Simulate recovery
    recovery_result = await manager.health_service.simulate_recovery("api_service")
    
    # Wait for recovery to be detected
    await asyncio.sleep(0.5)
    
    # Verify recovery
    recovered_status = await manager.health_service.get_health_status("api_service")
    assert recovered_status.get("status") == "healthy"