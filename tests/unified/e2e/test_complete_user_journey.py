#!/usr/bin/env python3
"""
Complete User Journey Integration Tests for DEV MODE

BVJ (Business Value Justification):
- Segment: ALL (Free, Early, Mid, Enterprise) | Goal: User Acquisition | Impact: $150K MRR
- Value Impact: Complete user journey validation prevents integration failures causing 100% user loss
- Strategic Impact: Each working user journey = $99-999/month recurring revenue
- Risk Mitigation: Catches cross-service integration failures before production

Test Coverage:
✅ Login → Message → Response complete flow
✅ WebSocket connection and communication
✅ Service coordination and state management  
✅ Error recovery across services
✅ Performance and resource monitoring
✅ Multi-user session isolation
✅ Authentication flow validation
✅ Real service interaction testing
"""

import pytest
import asyncio
import time
import os
from typing import Dict, Any, List

# Test environment setup
os.environ["TESTING"] = "1"
os.environ["CORS_ORIGINS"] = "*"
os.environ["ENVIRONMENT"] = "development"

from helpers.user_journey_helpers import (
    UserJourneyConfig,
    TestUser,
    UserCreationHelper,
    LoginFlowHelper,
    WebSocketSimulationHelper,
    MessageFlowHelper,
    ServiceCoordinationHelper,
    ErrorRecoveryHelper,
    PerformanceMonitoringHelper,
    ServiceHealthHelper
)






class TestCompleteUserJourney:
    """Complete user journey integration tests."""
    
    @pytest.fixture
    def journey_config(self):
        """User journey test configuration."""
        return UserJourneyConfig()
    
    @pytest.mark.asyncio
    async def test_single_user_complete_journey(self, journey_config):
        """Test complete user journey from login to chat response."""
        # Create test user
        user = UserCreationHelper.create_test_user()
        journey_start = time.time()
        
        # Step 1: Login flow
        login_result = await LoginFlowHelper.simulate_login_flow(journey_config, user)
        assert login_result["success"], f"Login failed: {login_result}"
        assert login_result["duration"] < journey_config.performance_thresholds["login_time"], \
            f"Login too slow: {login_result['duration']:.2f}s"
        
        # Step 2: WebSocket connection
        websocket_result = await WebSocketSimulationHelper.establish_websocket_connection(journey_config, user)
        assert websocket_result["success"], f"WebSocket connection failed: {websocket_result}"
        assert websocket_result["connection_time"] < journey_config.performance_thresholds["websocket_connect"], \
            f"WebSocket connection too slow: {websocket_result['connection_time']:.2f}s"
        
        # Step 3: Message flow
        message_result = await MessageFlowHelper.simulate_message_flow(journey_config, user)
        assert message_result["success"], f"Message flow failed: {message_result}"
        assert message_result["response_time"] < journey_config.performance_thresholds["message_response"], \
            f"Message response too slow: {message_result['response_time']:.2f}s"
        
        # Step 4: Service coordination validation
        coordination_result = await ServiceCoordinationHelper.validate_service_coordination(journey_config, user)
        assert coordination_result["session_consistency"], \
            f"Service coordination failed: {coordination_result}"
        
        # Overall journey performance
        total_duration = time.time() - journey_start
        assert total_duration < journey_config.performance_thresholds["total_journey"], \
            f"Total journey too slow: {total_duration:.2f}s"
        
        user.journey_metrics["total_duration"] = total_duration
    
    @pytest.mark.asyncio
    async def test_multi_user_session_isolation(self, journey_config):
        """Test multiple users with session isolation."""
        users = []
        
        # Create multiple test users
        for i in range(3):
            user = UserCreationHelper.create_test_user()
            users.append(user)
        
        # Perform login for all users concurrently
        login_tasks = [
            LoginFlowHelper.simulate_login_flow(journey_config, user) 
            for user in users
        ]
        login_results = await asyncio.gather(*login_tasks)
        
        # Verify all logins succeeded
        for i, result in enumerate(login_results):
            assert result["success"], f"User {i} login failed: {result}"
        
        # Verify each user has unique session data
        user_ids = [user.user_id for user in users]
        assert len(set(user_ids)) == len(user_ids), "User IDs not unique"
        
        tokens = [user.access_token for user in users]
        assert len(set(tokens)) == len(tokens), "Access tokens not unique"
        
        # Test concurrent message flows
        message_tasks = [
            MessageFlowHelper.simulate_message_flow(journey_config, user)
            for user in users
        ]
        message_results = await asyncio.gather(*message_tasks)
        
        # Verify all message flows succeeded
        for i, result in enumerate(message_results):
            assert result["success"], f"User {i} message flow failed: {result}"
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, journey_config):
        """Test error recovery across services."""
        user = UserCreationHelper.create_test_user()
        
        # Test error recovery
        recovery_result = await ErrorRecoveryHelper.test_error_recovery_scenarios(journey_config, user)
        assert recovery_result["invalid_auth_handled"], "Invalid auth not handled properly"
        assert recovery_result["recovery_successful"], "Recovery login failed"
        assert recovery_result["coordination_restored"], "Service coordination failed after recovery"
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, journey_config):
        """Test performance monitoring and resource usage."""
        # Collect performance data
        performance_data = await PerformanceMonitoringHelper.collect_performance_metrics(journey_config, iterations=5)
        
        # Analyze performance metrics
        for metric_name, times in performance_data.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                # Performance assertions based on metric type
                if metric_name == "login_times":
                    assert avg_time < 3.0, f"Average login time too slow: {avg_time:.2f}s"
                elif metric_name == "websocket_times":
                    assert avg_time < 2.0, f"Average WebSocket connection too slow: {avg_time:.2f}s"
                elif metric_name == "message_times":
                    assert avg_time < 8.0, f"Average message response too slow: {avg_time:.2f}s"
                elif metric_name == "total_times":
                    assert avg_time < 20.0, f"Average total journey too slow: {avg_time:.2f}s"
                    assert max_time < 40.0, f"Max total journey too slow: {max_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_service_startup_coordination(self, journey_config):
        """Test service startup and initialization coordination."""
        startup_metrics = await ServiceHealthHelper.test_service_startup_coordination(journey_config)
        
        # Assert service health and readiness
        for service_name, health_data in startup_metrics["service_health_checks"].items():
            assert health_data.get("healthy", False), \
                f"Service {service_name} not healthy: {health_data}"
        
        # At least one service should be ready for meaningful testing
        ready_services = sum(1 for data in startup_metrics["service_readiness"].values() 
                           if data.get("ready", False))
        assert ready_services >= 1, \
            f"No services ready for testing: {startup_metrics['service_readiness']}"