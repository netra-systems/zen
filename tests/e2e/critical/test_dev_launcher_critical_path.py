#!/usr/bin/env python3
"""
Comprehensive test suite for dev launcher critical path.

Tests are designed to FAIL initially to expose real issues.
These tests use REAL services with MINIMAL mocking.

Critical Path Coverage:
1. Startups clear without errors (real errors fixed, not silenced)
2. Inter-service connections work
3. Database connections stable
4. Frontend/backend communication works
5. OAuth flow functional
6. WebSocket connections stable

Business Value Justification (BVJ):
- Segment: All tiers (foundation for platform access)
- Business Goal: Eliminate onboarding friction and development velocity blockers
- Value Impact: First impression, developer experience, time-to-productivity
- Revenue Impact: Reduce trial-to-paid conversion friction by ensuring smooth first experience

Architecture: Focused on REAL system integration
"""

import asyncio
import json
import os
import time
import psutil
import requests
from typing import Dict, Any, List, Optional
import subprocess
import pytest

# Shared components
from tests.e2e.config import TEST_CONFIG, TEST_ENDPOINTS
from tests.e2e.real_services_manager import RealServicesManager
from tests.e2e.enforce_real_services import E2EServiceValidator


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestDevLauncherCriticalPath:
    """Critical path tests for dev launcher - focused on REAL issues"""
    
    def setup_method(self):
        """Setup for each test - REAL services only"""
        self.services_manager = RealServicesManager()
        self.startup_timeout = 30  # Generous but not infinite
        self.health_check_timeout = 10
        
    def teardown_method(self):
        """Cleanup after each test"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical  
    def test_dev_launcher_startup_sequence(self):
        """Test the critical startup sequence works end-to-end"""
        
        # Step 1: Launch dev environment
        startup_result = self.services_manager.launch_dev_environment()
        assert startup_result['success'], f"Dev launcher failed: {startup_result.get('error')}"
        
        # Step 2: Wait for services to be ready (real timeout, not mocked)
        time.sleep(5)  # Give services time to initialize
        
        # Step 3: Verify all critical services are healthy
        health_results = self.services_manager.check_all_service_health()
        assert health_results['all_healthy'], f"Service health check failed: {health_results}"
        
        # Step 4: Test inter-service communication
        communication_test = self._test_inter_service_communication()
        assert communication_test['success'], f"Inter-service communication failed: {communication_test}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_database_connectivity_critical(self):
        """Test database connections are stable and functional"""
        
        # Test primary database connection
        db_result = self.services_manager.test_database_connectivity()
        assert db_result['connected'], f"Primary database connection failed: {db_result.get('error')}"
        
        # Test basic CRUD operations
        crud_result = self.services_manager.test_basic_crud()
        assert crud_result['success'], f"Basic CRUD operations failed: {crud_result.get('error')}"

    @pytest.mark.e2e  
    @pytest.mark.critical
    def test_frontend_backend_communication(self):
        """Test frontend can communicate with backend APIs"""
        
        # Test API endpoint accessibility
        api_health = self.services_manager.test_api_endpoints()
        assert api_health['accessible'], f"API endpoints not accessible: {api_health.get('error')}"
        
        # Test authentication flow
        auth_test = self.services_manager.test_auth_flow()
        assert auth_test['success'], f"Authentication flow failed: {auth_test.get('error')}"

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_websocket_connection_stability(self):
        """Test WebSocket connections work and are stable"""
        
        ws_result = self.services_manager.test_websocket_connection()
        assert ws_result['connected'], f"WebSocket connection failed: {ws_result.get('error')}"
        
        # Test message flow
        message_test = self.services_manager.test_websocket_messaging()
        assert message_test['success'], f"WebSocket messaging failed: {message_test.get('error')}"

    def _test_inter_service_communication(self) -> Dict[str, Any]:
        """Test that services can communicate with each other"""
        
        try:
            # Test backend can reach auth service
            backend_to_auth = self.services_manager.test_backend_auth_communication()
            if not backend_to_auth['success']:
                return {'success': False, 'error': f"Backend->Auth failed: {backend_to_auth.get('error')}"}
            
            # Test frontend can reach backend
            frontend_to_backend = self.services_manager.test_frontend_backend_communication() 
            if not frontend_to_backend['success']:
                return {'success': False, 'error': f"Frontend->Backend failed: {frontend_to_backend.get('error')}"}
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Initialize real services
E2EServiceValidator.enforce_real_services()
class TestDevLauncherRealSystemIntegration:
    """Integration tests using real system components"""
    
    def setup_method(self):
        """Setup with real services"""
        self.services_manager = RealServicesManager()
        
    def teardown_method(self):
        """Cleanup"""
        if hasattr(self, 'services_manager'):
            self.services_manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.critical
    def test_first_time_user_experience(self):
        """Test the complete first-time user experience"""
        
        # Step 1: System startup
        startup_result = self.services_manager.launch_dev_environment()
        assert startup_result['success'], "System startup failed"
        
        # Step 2: User can access landing page  
        landing_page_test = self.services_manager.test_landing_page_access()
        assert landing_page_test['accessible'], "Landing page not accessible"
        
        # Step 3: OAuth flow works
        oauth_test = self.services_manager.test_oauth_flow()
        assert oauth_test['success'], "OAuth flow failed"
        
        # Step 4: User can create first thread
        thread_test = self.services_manager.test_thread_creation()
        assert thread_test['success'], "Thread creation failed"

    @pytest.mark.e2e
    @pytest.mark.critical  
    def test_staging_deployment_readiness(self):
        """Test that the system is ready for staging deployment"""
        
        # Test all critical services are running
        health_check = self.services_manager.comprehensive_health_check()
        assert health_check['all_systems_ready'], f"System not ready for staging: {health_check}"
        
        # Test configuration is valid for deployment
        config_test = self.services_manager.test_deployment_config()
        assert config_test['valid'], f"Deployment config invalid: {config_test.get('error')}"