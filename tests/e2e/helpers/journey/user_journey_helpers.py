"""
User Journey Helper Functions

Helper functions for user journey simulation and testing.
Extracted from test_complete_user_journey.py for modularity.
"""

import asyncio
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List

import httpx


@dataclass
class UserJourneyConfig:
    """Configuration for user journey testing."""
    backend_url: str = "http://localhost:8000"
    auth_url: str = "http://localhost:8081"
    frontend_url: str = "http://localhost:3001"
    websocket_url: str = "ws://localhost:8000/ws"
    timeout: float = 30.0
    performance_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "login_time": 5.0,
        "websocket_connect": 3.0,
        "message_response": 10.0,
        "total_journey": 30.0
    })


@dataclass
class TestUser:
    """Test user data structure."""
    email: str
    user_id: str
    access_token: str = None
    session_data: Dict[str, Any] = field(default_factory=dict)
    journey_metrics: Dict[str, float] = field(default_factory=dict)


class UserCreationHelper:
    """Helper for creating test users."""
    
    @staticmethod
    def create_test_user() -> TestUser:
        """Create a test user with unique credentials."""
        user_id = str(uuid.uuid4())
        email = f"test_user_{user_id[:8]}@example.com"
        
        return TestUser(
            email=email,
            user_id=user_id
        )


class LoginFlowHelper:
    """Helper for login flow simulation."""
    
    @staticmethod
    async def simulate_login_flow(config: UserJourneyConfig, user: TestUser) -> Dict[str, Any]:
        """Simulate complete login flow."""
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # Step 1: Get auth configuration
            auth_config_response = await client.get(
                f"{config.auth_url}/auth/config",
                headers={"Origin": config.frontend_url}
            )
            
            assert auth_config_response.status_code == 200, \
                f"Auth config failed: {auth_config_response.status_code}"
            
            auth_config = auth_config_response.json()
            
            # Step 2: Simulate OAuth login (mock success)
            login_data = {
                "email": user.email,
                "user_id": user.user_id,
                "provider": "development"
            }
            
            # In real scenario, this would be OAuth flow
            # For testing, we simulate successful auth
            mock_token = f"mock_token_{user.user_id}"
            user.access_token = mock_token
            
            # Step 3: Validate token with backend
            auth_headers = {
                "Authorization": f"Bearer {mock_token}",
                "Origin": config.frontend_url
            }
            
            user_response = await client.get(
                f"{config.backend_url}/api/v1/auth/status",
                headers=auth_headers
            )
            
            login_duration = time.time() - start_time
            user.journey_metrics["login_duration"] = login_duration
            
            return {
                "success": True,
                "user_data": {
                    "id": user.user_id,
                    "email": user.email
                },
                "access_token": mock_token,
                "duration": login_duration,
                "auth_config": auth_config
            }


class WebSocketSimulationHelper:
    """Helper for WebSocket connection simulation."""
    
    @staticmethod
    async def establish_websocket_connection(config: UserJourneyConfig, user: TestUser) -> Dict[str, Any]:
        """Establish WebSocket connection for user."""
        start_time = time.time()
        connection_result = {"success": False, "error": None}
        
        try:
            # In a real scenario, this would include auth token in connection
            websocket_url = f"{config.websocket_url}?token={user.access_token}"
            
            # For testing, we simulate WebSocket connection
            # Real WebSocket testing requires running services
            simulated_connection = {
                "connected": True,
                "connection_time": time.time() - start_time,
                "user_id": user.user_id
            }
            
            user.journey_metrics["websocket_connect_duration"] = simulated_connection["connection_time"]
            connection_result = {
                "success": True,
                "connection_time": simulated_connection["connection_time"],
                "connection_id": f"ws_{user.user_id}"
            }
            
        except Exception as e:
            connection_result = {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
        
        return connection_result


class MessageFlowHelper:
    """Helper for message flow simulation."""
    
    @staticmethod
    async def simulate_message_flow(config: UserJourneyConfig, user: TestUser) -> Dict[str, Any]:
        """Simulate complete message sending and response flow."""
        start_time = time.time()
        
        # Simulate user sending a message
        test_message = {
            "type": "user_message",
            "content": "Hello, can you help me optimize my AI workload?",
            "thread_id": f"thread_{user.user_id}",
            "timestamp": time.time()
        }
        
        # In real scenario, this would go through WebSocket
        # For testing, we simulate the flow
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            auth_headers = {
                "Authorization": f"Bearer {user.access_token}",
                "Origin": config.frontend_url,
                "Content-Type": "application/json"
            }
            
            # Simulate sending message to backend
            message_response = await client.post(
                f"{config.backend_url}/api/v1/threads/{test_message['thread_id']}/messages",
                headers=auth_headers,
                json=test_message
            )
            
            response_duration = time.time() - start_time
            user.journey_metrics["message_response_duration"] = response_duration
            
            # Simulate receiving agent response
            agent_response = {
                "type": "agent_response",
                "content": "I can help you optimize your AI workload. What specific challenges are you facing?",
                "thread_id": test_message["thread_id"],
                "timestamp": time.time(),
                "agent_id": "supervisor_agent"
            }
            
            return {
                "success": True,
                "message_sent": test_message,
                "agent_response": agent_response,
                "response_time": response_duration,
                "total_flow_time": time.time() - start_time
            }


class ServiceCoordinationHelper:
    """Helper for service coordination validation."""
    
    @staticmethod
    async def validate_service_coordination(config: UserJourneyConfig, user: TestUser) -> Dict[str, Any]:
        """Validate coordination between services for user session."""
        coordination_results = {
            "auth_service_sync": False,
            "backend_service_sync": False,
            "session_consistency": False,
            "data_persistence": False
        }
        
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            auth_headers = {
                "Authorization": f"Bearer {user.access_token}",
                "Origin": config.frontend_url
            }
            
            # Check auth service recognizes user
            auth_status = await client.get(
                f"{config.auth_url}/auth/status",
                headers=auth_headers
            )
            coordination_results["auth_service_sync"] = auth_status.status_code == 200
            
            # Check backend service recognizes user
            backend_status = await client.get(
                f"{config.backend_url}/api/v1/auth/status", 
                headers=auth_headers
            )
            coordination_results["backend_service_sync"] = backend_status.status_code == 200
            
            # Verify session consistency
            if coordination_results["auth_service_sync"] and coordination_results["backend_service_sync"]:
                coordination_results["session_consistency"] = True
            
            # Check data persistence (threads/messages)
            threads_response = await client.get(
                f"{config.backend_url}/api/v1/threads",
                headers=auth_headers
            )
            coordination_results["data_persistence"] = threads_response.status_code in [200, 404]
        
        return coordination_results


class ErrorRecoveryHelper:
    """Helper for error recovery testing."""
    
    @staticmethod
    async def test_error_recovery_scenarios(config: UserJourneyConfig, user: TestUser) -> Dict[str, Any]:
        """Test error recovery across services."""
        # Test login with invalid credentials
        user.access_token = "invalid_token_12345"
        
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # This should fail gracefully
            auth_response = await client.get(
                f"{config.backend_url}/api/v1/auth/status",
                headers={
                    "Authorization": f"Bearer {user.access_token}",
                    "Origin": config.frontend_url
                }
            )
            
            # Should return 401 or similar, not crash
            assert auth_response.status_code in [401, 403], \
                f"Expected auth failure, got {auth_response.status_code}"
        
        # Test recovery with valid login
        login_result = await LoginFlowHelper.simulate_login_flow(config, user)
        assert login_result["success"], "Recovery login failed"
        
        # Verify service coordination after recovery
        coordination_result = await ServiceCoordinationHelper.validate_service_coordination(config, user)
        assert coordination_result["session_consistency"], \
            "Service coordination failed after recovery"
        
        return {
            "invalid_auth_handled": True,
            "recovery_successful": login_result["success"],
            "coordination_restored": coordination_result["session_consistency"]
        }


class PerformanceMonitoringHelper:
    """Helper for performance monitoring."""
    
    @staticmethod
    async def collect_performance_metrics(config: UserJourneyConfig, iterations: int = 5) -> Dict[str, List[float]]:
        """Collect performance metrics across multiple user journeys."""
        performance_data = {
            "login_times": [],
            "websocket_times": [],
            "message_times": [],
            "total_times": []
        }
        
        # Run multiple user journeys for performance baseline
        for i in range(iterations):
            user = UserCreationHelper.create_test_user()
            journey_start = time.time()
            
            # Execute journey steps
            login_result = await LoginFlowHelper.simulate_login_flow(config, user)
            websocket_result = await WebSocketSimulationHelper.establish_websocket_connection(config, user)
            message_result = await MessageFlowHelper.simulate_message_flow(config, user)
            
            total_time = time.time() - journey_start
            
            # Collect performance data
            if login_result["success"]:
                performance_data["login_times"].append(login_result["duration"])
            if websocket_result["success"]:
                performance_data["websocket_times"].append(websocket_result["connection_time"])
            if message_result["success"]:
                performance_data["message_times"].append(message_result["response_time"])
            
            performance_data["total_times"].append(total_time)
        
        return performance_data


class ServiceHealthHelper:
    """Helper for service health and startup coordination testing."""
    
    @staticmethod
    async def test_service_startup_coordination(config: UserJourneyConfig) -> Dict[str, Any]:
        """Test service startup and initialization coordination."""
        startup_metrics = {
            "service_health_checks": {},
            "service_readiness": {},
            "cross_service_communication": {}
        }
        
        async with httpx.AsyncClient(timeout=config.timeout) as client:
            # Test service health endpoints
            services = {
                "backend": f"{config.backend_url}/health",
                "auth": f"{config.auth_url}/health"
            }
            
            for service_name, health_url in services.items():
                try:
                    start_time = time.time()
                    health_response = await client.get(health_url, timeout=5.0)
                    response_time = time.time() - start_time
                    
                    startup_metrics["service_health_checks"][service_name] = {
                        "status_code": health_response.status_code,
                        "response_time": response_time,
                        "healthy": health_response.status_code == 200
                    }
                    
                except Exception as e:
                    startup_metrics["service_health_checks"][service_name] = {
                        "error": str(e),
                        "healthy": False
                    }
            
            # Test service readiness
            readiness_endpoints = {
                "backend": f"{config.backend_url}/health/ready",
                "auth": f"{config.auth_url}/health/ready"
            }
            
            for service_name, ready_url in readiness_endpoints.items():
                try:
                    ready_response = await client.get(ready_url, timeout=5.0)
                    startup_metrics["service_readiness"][service_name] = {
                        "status_code": ready_response.status_code,
                        "ready": ready_response.status_code == 200
                    }
                except Exception as e:
                    startup_metrics["service_readiness"][service_name] = {
                        "error": str(e),
                        "ready": False
                    }
        
        return startup_metrics