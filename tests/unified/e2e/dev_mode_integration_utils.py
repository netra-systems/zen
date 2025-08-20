#!/usr/bin/env python3
"""
Supporting Utilities for DEV MODE Integration Tests

BVJ (Business Value Justification):
- Segment: Platform/Internal | Goal: Development Velocity | Impact: Test Infrastructure
- Value Impact: Accelerates test development and reduces test maintenance overhead
- Strategic Impact: Enables comprehensive testing with reusable components
- Risk Mitigation: Centralizes common test patterns to reduce bugs and inconsistencies

Utilities:
✅ CORS validation helpers
✅ User journey simulation utilities
✅ Performance metrics collection
✅ Service coordination monitors
✅ Resource usage tracking
✅ WebSocket connection testing
✅ Error scenario simulation
✅ Test data management
"""

import asyncio
import httpx
import websockets
import json
import time
import uuid
import os
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from enum import Enum
from abc import ABC, abstractmethod


class TestMode(Enum):
    """Test execution modes."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"


class ServiceState(Enum):
    """Service states for monitoring."""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class TestMetrics:
    """Test execution metrics."""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    requests_made: int = 0
    requests_successful: int = 0
    requests_failed: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float('inf')
    errors: List[str] = field(default_factory=list)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.requests_made == 0:
            return 0.0
        return self.requests_successful / self.requests_made
    
    def finalize(self):
        """Finalize metrics calculation."""
        if self.end_time == 0.0:
            self.end_time = time.time()
        self.duration = self.end_time - self.start_time


class PerformanceMonitor:
    """Monitors performance metrics during test execution."""
    
    def __init__(self):
        self.metrics = TestMetrics()
        self.response_times: List[float] = []
        self._start_time = time.time()
    
    def start_request(self) -> float:
        """Start timing a request."""
        return time.time()
    
    def end_request(self, start_time: float, success: bool = True):
        """End timing a request and update metrics."""
        response_time = time.time() - start_time
        self.response_times.append(response_time)
        
        self.metrics.requests_made += 1
        
        if success:
            self.metrics.requests_successful += 1
        else:
            self.metrics.requests_failed += 1
        
        # Update response time statistics
        if response_time > self.metrics.max_response_time:
            self.metrics.max_response_time = response_time
        
        if response_time < self.metrics.min_response_time:
            self.metrics.min_response_time = response_time
        
        # Calculate running average
        if self.response_times:
            self.metrics.avg_response_time = sum(self.response_times) / len(self.response_times)
    
    def add_error(self, error: str):
        """Add an error to the metrics."""
        self.metrics.errors.append(error)
    
    def get_metrics(self) -> TestMetrics:
        """Get current metrics."""
        self.metrics.finalize()
        return self.metrics


class CORSTestHelper:
    """Helper utilities for CORS testing."""
    
    @staticmethod
    def validate_cors_headers(headers: Dict[str, str], origin: str) -> Dict[str, bool]:
        """Validate CORS headers in a response."""
        return {
            "has_allow_origin": "access-control-allow-origin" in headers,
            "origin_matches": headers.get("access-control-allow-origin") in [origin, "*"],
            "allows_credentials": headers.get("access-control-allow-credentials") == "true",
            "has_allow_methods": "access-control-allow-methods" in headers,
            "has_allow_headers": "access-control-allow-headers" in headers,
            "has_expose_headers": "access-control-expose-headers" in headers,
            "has_max_age": "access-control-max-age" in headers
        }
    
    @staticmethod
    def create_cors_preflight_headers(origin: str, method: str = "POST", 
                                    headers: str = "Content-Type,Authorization") -> Dict[str, str]:
        """Create headers for CORS preflight request."""
        return {
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers
        }
    
    @staticmethod
    async def test_cors_endpoint(client: httpx.AsyncClient, url: str, origin: str,
                               timeout: float = 10.0) -> Dict[str, Any]:
        """Test CORS for a specific endpoint."""
        result = {
            "url": url,
            "origin": origin,
            "preflight_success": False,
            "request_success": False,
            "cors_valid": False,
            "response_time": 0.0,
            "errors": []
        }
        
        try:
            start_time = time.time()
            
            # Test preflight request
            preflight_headers = CORSTestHelper.create_cors_preflight_headers(origin)
            preflight_response = await client.options(url, headers=preflight_headers, timeout=timeout)
            
            result["preflight_success"] = preflight_response.status_code == 200
            
            # Test actual request
            request_headers = {"Origin": origin}
            response = await client.get(url, headers=request_headers, timeout=timeout)
            
            result["request_success"] = response.status_code in [200, 404]
            result["response_time"] = time.time() - start_time
            
            # Validate CORS headers
            cors_validation = CORSTestHelper.validate_cors_headers(
                dict(response.headers), origin
            )
            result["cors_valid"] = cors_validation["origin_matches"] and cors_validation["allows_credentials"]
            result["cors_details"] = cors_validation
            
        except Exception as e:
            result["errors"].append(str(e))
        
        return result


class WebSocketTestHelper:
    """Helper utilities for WebSocket testing."""
    
    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout
        self.connection: Optional[websockets.WebSocketServerProtocol] = None
        self.messages_received: List[Dict[str, Any]] = []
        self.connection_time: float = 0.0
    
    async def connect(self, auth_token: Optional[str] = None) -> bool:
        """Connect to WebSocket with optional authentication."""
        try:
            start_time = time.time()
            
            # Add auth token to URL if provided
            connect_url = self.url
            if auth_token:
                separator = "&" if "?" in connect_url else "?"
                connect_url = f"{connect_url}{separator}token={auth_token}"
            
            self.connection = await websockets.connect(
                connect_url,
                timeout=self.timeout
            )
            
            self.connection_time = time.time() - start_time
            return True
            
        except Exception as e:
            return False
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send a JSON message through WebSocket."""
        if not self.connection:
            return False
        
        try:
            await self.connection.send(json.dumps(message))
            return True
        except Exception:
            return False
    
    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive a JSON message from WebSocket."""
        if not self.connection:
            return None
        
        try:
            message = await asyncio.wait_for(
                self.connection.recv(),
                timeout=timeout
            )
            
            parsed_message = json.loads(message)
            self.messages_received.append(parsed_message)
            return parsed_message
            
        except Exception:
            return None
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.connection:
            await self.connection.close()
            self.connection = None
    
    async def test_echo_flow(self, test_message: Dict[str, Any]) -> Dict[str, Any]:
        """Test WebSocket echo flow."""
        result = {
            "connected": False,
            "message_sent": False,
            "response_received": False,
            "connection_time": 0.0,
            "response_time": 0.0,
            "messages": []
        }
        
        if await self.connect():
            result["connected"] = True
            result["connection_time"] = self.connection_time
            
            send_time = time.time()
            if await self.send_message(test_message):
                result["message_sent"] = True
                
                response = await self.receive_message()
                if response:
                    result["response_received"] = True
                    result["response_time"] = time.time() - send_time
                    result["messages"] = self.messages_received
            
            await self.disconnect()
        
        return result


class UserSimulator:
    """Simulates user interactions for testing."""
    
    def __init__(self, base_url: str, auth_url: str):
        self.base_url = base_url
        self.auth_url = auth_url
        self.user_id = str(uuid.uuid4())
        self.email = f"test_user_{self.user_id[:8]}@example.com"
        self.access_token: Optional[str] = None
        self.session_data: Dict[str, Any] = {}
        self.performance_monitor = PerformanceMonitor()
    
    @asynccontextmanager
    async def http_session(self):
        """Managed HTTP client session."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client
    
    async def simulate_login(self) -> Dict[str, Any]:
        """Simulate user login process."""
        login_result = {
            "success": False,
            "user_id": self.user_id,
            "email": self.email,
            "access_token": None,
            "duration": 0.0,
            "errors": []
        }
        
        start_time = self.performance_monitor.start_request()
        
        try:
            async with self.http_session() as client:
                # Step 1: Get auth configuration
                auth_config_response = await client.get(f"{self.auth_url}/auth/config")
                
                if auth_config_response.status_code == 200:
                    # Step 2: Simulate successful authentication
                    self.access_token = f"mock_token_{self.user_id}"
                    login_result["access_token"] = self.access_token
                    login_result["success"] = True
                    
                    self.performance_monitor.end_request(start_time, True)
                else:
                    self.performance_monitor.end_request(start_time, False)
                    login_result["errors"].append(f"Auth config failed: {auth_config_response.status_code}")
                    
        except Exception as e:
            self.performance_monitor.end_request(start_time, False)
            login_result["errors"].append(str(e))
        
        login_result["duration"] = time.time() - start_time
        return login_result
    
    async def simulate_api_request(self, endpoint: str, method: str = "GET", 
                                 data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Simulate API request with authentication."""
        request_result = {
            "success": False,
            "status_code": 0,
            "response_time": 0.0,
            "endpoint": endpoint,
            "method": method,
            "errors": []
        }
        
        if not self.access_token:
            request_result["errors"].append("No access token available")
            return request_result
        
        start_time = self.performance_monitor.start_request()
        
        try:
            async with self.http_session() as client:
                headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
                
                url = f"{self.base_url}{endpoint}"
                
                if method.upper() == "POST":
                    response = await client.post(url, headers=headers, json=data or {})
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, json=data or {})
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    response = await client.get(url, headers=headers)
                
                request_result["status_code"] = response.status_code
                request_result["success"] = 200 <= response.status_code < 400
                
                self.performance_monitor.end_request(start_time, request_result["success"])
                
        except Exception as e:
            self.performance_monitor.end_request(start_time, False)
            request_result["errors"].append(str(e))
        
        request_result["response_time"] = time.time() - start_time
        return request_result
    
    async def simulate_user_journey(self, journey_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Simulate a complete user journey."""
        journey_result = {
            "user_id": self.user_id,
            "steps_completed": 0,
            "total_steps": len(journey_steps),
            "success": False,
            "total_duration": 0.0,
            "step_results": [],
            "performance_metrics": None
        }
        
        journey_start = time.time()
        
        try:
            # First, login the user
            login_result = await self.simulate_login()
            journey_result["step_results"].append({"type": "login", "result": login_result})
            
            if not login_result["success"]:
                return journey_result
            
            # Execute journey steps
            for i, step in enumerate(journey_steps):
                step_type = step.get("type", "unknown")
                
                if step_type == "api_request":
                    step_result = await self.simulate_api_request(
                        step["endpoint"],
                        step.get("method", "GET"),
                        step.get("data")
                    )
                elif step_type == "websocket":
                    # WebSocket step would be implemented here
                    step_result = {"success": True, "simulated": True}
                else:
                    step_result = {"success": False, "error": f"Unknown step type: {step_type}"}
                
                journey_result["step_results"].append({
                    "type": step_type,
                    "step_index": i,
                    "result": step_result
                })
                
                if step_result.get("success", False):
                    journey_result["steps_completed"] += 1
                else:
                    break  # Stop on first failure
        
        except Exception as e:
            journey_result["error"] = str(e)
        
        journey_result["total_duration"] = time.time() - journey_start
        journey_result["success"] = journey_result["steps_completed"] == journey_result["total_steps"]
        journey_result["performance_metrics"] = self.performance_monitor.get_metrics()
        
        return journey_result


class ServiceHealthChecker:
    """Monitors service health and readiness."""
    
    def __init__(self, services: Dict[str, str]):
        """Initialize with service name -> URL mapping."""
        self.services = services
        self.health_history: Dict[str, List[Dict[str, Any]]] = {}
        
        for service_name in services:
            self.health_history[service_name] = []
    
    async def check_service_health(self, service_name: str, 
                                 health_endpoint: str = "/health") -> Dict[str, Any]:
        """Check health of a specific service."""
        if service_name not in self.services:
            return {"error": f"Unknown service: {service_name}"}
        
        service_url = self.services[service_name]
        health_result = {
            "service_name": service_name,
            "url": service_url,
            "healthy": False,
            "response_time": 0.0,
            "status_code": 0,
            "timestamp": time.time(),
            "error": None
        }
        
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{service_url}{health_endpoint}")
                
                health_result["response_time"] = time.time() - start_time
                health_result["status_code"] = response.status_code
                health_result["healthy"] = response.status_code == 200
                
        except Exception as e:
            health_result["error"] = str(e)
            health_result["response_time"] = time.time() - start_time
        
        # Store in history
        self.health_history[service_name].append(health_result)
        
        # Keep only last 100 checks
        if len(self.health_history[service_name]) > 100:
            self.health_history[service_name] = self.health_history[service_name][-100:]
        
        return health_result
    
    async def check_all_services(self) -> Dict[str, Any]:
        """Check health of all services concurrently."""
        health_tasks = [
            self.check_service_health(service_name)
            for service_name in self.services
        ]
        
        health_results = await asyncio.gather(*health_tasks)
        
        summary = {
            "timestamp": time.time(),
            "total_services": len(self.services),
            "healthy_services": 0,
            "unhealthy_services": 0,
            "avg_response_time": 0.0,
            "service_results": {}
        }
        
        total_response_time = 0.0
        
        for result in health_results:
            service_name = result["service_name"]
            summary["service_results"][service_name] = result
            
            if result["healthy"]:
                summary["healthy_services"] += 1
            else:
                summary["unhealthy_services"] += 1
            
            total_response_time += result["response_time"]
        
        if health_results:
            summary["avg_response_time"] = total_response_time / len(health_results)
        
        return summary
    
    def get_service_availability(self, service_name: str, 
                               time_window_minutes: int = 60) -> float:
        """Calculate service availability over time window."""
        if service_name not in self.health_history:
            return 0.0
        
        history = self.health_history[service_name]
        if not history:
            return 0.0
        
        # Filter to time window
        cutoff_time = time.time() - (time_window_minutes * 60)
        recent_checks = [check for check in history if check["timestamp"] >= cutoff_time]
        
        if not recent_checks:
            return 0.0
        
        healthy_checks = sum(1 for check in recent_checks if check["healthy"])
        return healthy_checks / len(recent_checks)


class ErrorScenarioSimulator:
    """Simulates various error scenarios for testing."""
    
    @staticmethod
    async def simulate_network_delay(delay_seconds: float):
        """Simulate network delay."""
        await asyncio.sleep(delay_seconds)
    
    @staticmethod
    async def simulate_timeout_request(client: httpx.AsyncClient, url: str, 
                                     timeout: float = 1.0) -> Dict[str, Any]:
        """Simulate a request that should timeout."""
        result = {"timed_out": False, "error": None}
        
        try:
            response = await client.get(url, timeout=timeout)
            result["status_code"] = response.status_code
        except httpx.TimeoutException:
            result["timed_out"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    @staticmethod
    async def simulate_high_load(client: httpx.AsyncClient, url: str, 
                               concurrent_requests: int = 10, 
                               duration_seconds: float = 10.0) -> Dict[str, Any]:
        """Simulate high load on a service."""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "response_times": []
        }
        
        async def make_request():
            request_start = time.time()
            try:
                response = await client.get(url, timeout=5.0)
                response_time = time.time() - request_start
                
                results["response_times"].append(response_time)
                results["total_requests"] += 1
                
                if response.status_code == 200:
                    results["successful_requests"] += 1
                else:
                    results["failed_requests"] += 1
                    
            except Exception:
                results["total_requests"] += 1
                results["failed_requests"] += 1
                results["response_times"].append(5.0)  # Timeout time
        
        # Create concurrent tasks
        while time.time() < end_time:
            tasks = [make_request() for _ in range(concurrent_requests)]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.1)  # Small delay between batches
        
        # Calculate averages
        if results["response_times"]:
            results["avg_response_time"] = sum(results["response_times"]) / len(results["response_times"])
        
        return results


def create_test_data_factory() -> Dict[str, Callable]:
    """Create factory functions for generating test data."""
    
    def create_test_user():
        """Create test user data."""
        user_id = str(uuid.uuid4())
        return {
            "id": user_id,
            "email": f"test_user_{user_id[:8]}@example.com",
            "name": f"Test User {user_id[:8]}",
            "created_at": time.time()
        }
    
    def create_test_message():
        """Create test message data."""
        return {
            "id": str(uuid.uuid4()),
            "content": "Hello, can you help me optimize my AI workload?",
            "type": "user_message",
            "timestamp": time.time()
        }
    
    def create_test_thread():
        """Create test thread data."""
        return {
            "id": str(uuid.uuid4()),
            "title": "AI Optimization Discussion",
            "created_at": time.time(),
            "message_count": 0
        }
    
    return {
        "user": create_test_user,
        "message": create_test_message,
        "thread": create_test_thread
    }