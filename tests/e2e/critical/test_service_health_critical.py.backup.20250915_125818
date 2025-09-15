"""
Critical Service Health Tests - Core system availability

Tests that all critical services are healthy and can communicate.
Essential for system stability and uptime monitoring.

Business Value Justification (BVJ):
- Segment: All tiers (system availability is universal)
- Business Goal: Maintain 99.9% uptime and prevent service outages
- Value Impact: Ensures customers can access the platform at all times
- Revenue Impact: Downtime directly impacts revenue and customer satisfaction

Test Coverage:
- All services are running and healthy
- Inter-service communication works
- Database connectivity is stable
- Basic API endpoints respond correctly
"""

import pytest
import requests
import time
from typing import Dict, Any, List
from shared.isolated_environment import IsolatedEnvironment

from tests.e2e.config import TEST_CONFIG, TEST_ENDPOINTS  
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.enforce_real_services import E2EServiceValidator
from shared.isolated_environment import get_env


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestCriticalServiceHealth:
    """Critical service health checks using real services"""
    
    def setup_method(self):
        """Setup with real service manager"""
        self.services_manager = RealServicesManager()
        # Start services for health testing
        startup_result = self.services_manager.launch_dev_environment()
        if not startup_result.get("success", False):
            pytest.skip(f"Could not start services: {startup_result.get('error', 'Unknown error')}")
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_all_services_healthy(self):
        """Test all critical services are running and healthy"""
        
        health_check = self.services_manager.check_all_service_health()
        assert health_check['all_healthy'], f"Service health failures: {health_check.get('failures')}"
        
        # Verify specific critical services (frontend not critical for backend health)
        critical_services = ['backend', 'auth_service', 'database']
        for service in critical_services:
            service_health = health_check['services'].get(service, {})
            assert service_health.get('healthy', False), f"{service} is not healthy: {service_health.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical  
    def test_database_connectivity(self):
        """Test database connections are stable"""
        
        db_health = self.services_manager.check_database_health()
        assert db_health['connected'], f"Database connection failed: {db_health.get('error')}"
        
        # Test basic query works
        query_test = self.services_manager.test_database_query()
        assert query_test['success'], f"Database query failed: {query_test.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_api_endpoints_responding(self):
        """Test critical API endpoints are responding"""
        
        # Test health endpoint
        health_response = self.services_manager.test_health_endpoint()
        assert health_response['responding'], f"Health endpoint failed: {health_response.get('error')}"
        
        # Test auth endpoints
        auth_response = self.services_manager.test_auth_endpoints()
        assert auth_response['responding'], f"Auth endpoints failed: {auth_response.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_inter_service_communication(self):
        """Test services can communicate with each other"""
        
        communication_test = self.services_manager.test_service_communication()
        assert communication_test['all_connected'], f"Service communication failed: {communication_test.get('failures')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_websocket_service_health(self):
        """Test WebSocket service is healthy and accepting connections"""
        
        ws_health = self.services_manager.test_websocket_health()
        assert ws_health['healthy'], f"WebSocket service unhealthy: {ws_health.get('error')}"
        
        # Test connection establishment
        connection_test = self.services_manager.test_websocket_connection_basic()
        assert connection_test['connected'], f"WebSocket connection failed: {connection_test.get('error')}"


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestCriticalSystemStability:
    """System stability and resilience tests"""
    
    def setup_method(self):
        """Setup"""
        self.services_manager = RealServicesManager()
        # Start services for stability testing
        startup_result = self.services_manager.launch_dev_environment()
        if not startup_result.get("success", False):
            pytest.skip(f"Could not start services: {startup_result.get('error', 'Unknown error')}")
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_system_startup_stability(self):
        """Test system can start up consistently"""
        
        # Test startup process
        startup_result = self.services_manager.test_system_startup()
        assert startup_result['success'], f"System startup failed: {startup_result.get('error')}"
        
        # Wait for stabilization
        time.sleep(5)
        
        # Verify all services are stable after startup
        stability_check = self.services_manager.check_post_startup_stability()
        assert stability_check['stable'], f"System unstable after startup: {stability_check.get('issues')}"

    @pytest.mark.e2e
    @pytest.mark.critical  
    def test_basic_load_handling(self):
        """Test system can handle basic concurrent requests"""
        
        load_test = self.services_manager.test_basic_concurrent_load()
        assert load_test['handled'], f"Basic load test failed: {load_test.get('error')}"
        
        # Verify system remained stable under load
        post_load_health = self.services_manager.check_all_service_health()
        assert post_load_health['all_healthy'], f"System unstable after load: {post_load_health.get('failures')}"
