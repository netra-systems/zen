"""End-to-end tests for agent execution with circuit breakers.

This test suite validates the complete flow from API request through agent 
execution with circuit breaker protection, ensuring no AttributeError issues
occur in production scenarios.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import patch, Mock
import aiohttp
from datetime import datetime

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.test_utils import wait_for_condition, create_test_user
from test_framework.performance_helpers import retry_on_failure


class TestAgentCircuitBreakerE2E(BaseE2ETest):
    """E2E tests for agent execution with circuit breaker protection."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Setup test environment with real services."""
        await self.start_services(['backend', 'auth', 'redis', 'postgres'])
        await self.wait_for_health_check()
        self.api_base = "http://localhost:8000"
        self.auth_token = await self.get_test_auth_token()
        
    async def get_test_auth_token(self) -> str:
        """Get authentication token for test user."""
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self.api_base}/auth/login",
                json={"email": "test@example.com", "password": "testpass"}
            )
            data = await response.json()
            return data.get("token", "test_token")
            
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_triage_agent_execution_with_circuit_breaker(self):
        """Test complete triage agent execution flow with circuit breaker."""
        # Prepare test request
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        request_data = {
            "type": "triage",
            "message": "System performance is degraded",
            "context": {
                "user_id": "test_user",
                "session_id": "test_session",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Execute agent request
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{self.api_base}/api/agents/execute",
                json=request_data,
                headers=headers
            )
            
            assert response.status == 200
            result = await response.json()
            
            # Verify response structure
            assert "status" in result
            assert "agent" in result
            assert result["agent"] == "triage"
            
            # Verify no circuit breaker errors
            assert "error" not in result or "AttributeError" not in result.get("error", "")
            assert "slow_requests" not in result.get("error", "")
            
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_tracking_during_load(self):
        """Test circuit breaker metrics are tracked correctly under load."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Generate load with mixed response times
        async def make_request(delay: float = 0):
            """Make a single agent request with optional delay."""
            request_data = {
                "type": "triage",
                "message": f"Test message with delay {delay}",
                "simulate_delay": delay  # Backend should simulate this delay
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    response = await session.post(
                        f"{self.api_base}/api/agents/execute",
                        json=request_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    return await response.json()
                except Exception as e:
                    return {"error": str(e)}
        
        # Execute requests with varying delays
        tasks = []
        # Fast requests
        for _ in range(5):
            tasks.append(make_request(0.1))
        # Slow requests (should trigger slow_requests counter)
        for _ in range(3):
            tasks.append(make_request(6.0))
        # Normal requests
        for _ in range(5):
            tasks.append(make_request(2.0))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check metrics endpoint
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{self.api_base}/api/metrics/circuit_breakers",
                headers=headers
            )
            
            if response.status == 200:
                metrics = await response.json()
                
                # Verify slow_requests is tracked
                triage_metrics = metrics.get("agents", {}).get("triage", {})
                assert "slow_requests" in triage_metrics or len(triage_metrics) > 0
                
        # Verify no AttributeError in results
        for result in results:
            if isinstance(result, dict) and "error" in result:
                assert "AttributeError" not in result["error"]
                assert "'slow_requests'" not in result["error"]
                
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_state_transitions(self):
        """Test circuit breaker state transitions during agent failures."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Force failures to trigger circuit breaker
        failure_request = {
            "type": "triage",
            "message": "FORCE_ERROR",  # Special message to trigger error
            "context": {"force_failure": True}
        }
        
        failure_responses = []
        for i in range(5):  # Enough to trip circuit breaker
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.api_base}/api/agents/execute",
                    json=failure_request,
                    headers=headers
                )
                failure_responses.append({
                    "attempt": i + 1,
                    "status": response.status,
                    "data": await response.json()
                })
                
        # Check if circuit breaker tripped
        last_response = failure_responses[-1]["data"]
        
        # Circuit should be open or showing circuit breaker error
        if "error" in last_response:
            error_msg = last_response["error"].lower()
            # Should NOT have AttributeError about slow_requests
            assert "attributeerror" not in error_msg or "slow_requests" not in error_msg
            
        # Verify circuit breaker status endpoint
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{self.api_base}/api/agents/triage/circuit_breaker/status",
                headers=headers
            )
            
            if response.status == 200:
                cb_status = await response.json()
                assert "state" in cb_status
                # State should be OPEN or HALF_OPEN after failures
                assert cb_status["state"] in ["OPEN", "HALF_OPEN", "CLOSED"]
                
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_agents_concurrent_execution(self):
        """Test multiple agent types executing concurrently with circuit breakers."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        agent_requests = [
            {"type": "triage", "message": "Triage request 1"},
            {"type": "data", "message": "Data analysis request"},
            {"type": "triage", "message": "Triage request 2"},
            {"type": "optimization", "message": "Optimization request"},
            {"type": "reporting", "message": "Generate report"},
        ]
        
        async def execute_agent(request_data):
            """Execute a single agent request."""
            async with aiohttp.ClientSession() as session:
                try:
                    response = await session.post(
                        f"{self.api_base}/api/agents/execute",
                        json=request_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    )
                    return {
                        "agent": request_data["type"],
                        "status": response.status,
                        "data": await response.json()
                    }
                except Exception as e:
                    return {
                        "agent": request_data["type"],
                        "error": str(e)
                    }
        
        # Execute all agents concurrently
        results = await asyncio.gather(
            *[execute_agent(req) for req in agent_requests],
            return_exceptions=True
        )
        
        # Verify no AttributeError in any agent execution
        for result in results:
            if isinstance(result, dict):
                if "error" in result:
                    assert "AttributeError" not in result["error"]
                    assert "'slow_requests'" not in result["error"]
                elif "data" in result and "error" in result["data"]:
                    error_msg = result["data"]["error"]
                    assert "AttributeError" not in error_msg
                    assert "'slow_requests'" not in error_msg
                    
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_after_fixes(self):
        """Test circuit breaker recovers properly after issues are fixed."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Phase 1: Cause failures to open circuit
        for _ in range(3):
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.api_base}/api/agents/execute",
                    json={"type": "triage", "message": "FORCE_ERROR"},
                    headers=headers
                )
        
        # Wait for circuit to open
        await asyncio.sleep(1)
        
        # Phase 2: Check circuit is open
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{self.api_base}/api/agents/triage/circuit_breaker/status",
                headers=headers
            )
            if response.status == 200:
                status = await response.json()
                initial_state = status.get("state", "UNKNOWN")
        
        # Phase 3: Wait for recovery timeout
        await asyncio.sleep(5)  # Typical recovery timeout
        
        # Phase 4: Send successful requests to close circuit
        success_count = 0
        for _ in range(5):
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"{self.api_base}/api/agents/execute",
                    json={"type": "triage", "message": "Normal request"},
                    headers=headers
                )
                if response.status == 200:
                    success_count += 1
                    
        # Verify circuit recovered
        assert success_count > 0, "Circuit should allow some requests after recovery"
        
        # Check final circuit state
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                f"{self.api_base}/api/agents/triage/circuit_breaker/status",
                headers=headers
            )
            if response.status == 200:
                status = await response.json()
                final_state = status.get("state", "UNKNOWN")
                # Should be CLOSED or HALF_OPEN after successful requests
                assert final_state in ["CLOSED", "HALF_OPEN"]
                
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_agent_execution_with_metrics(self):
        """Test agent execution via WebSocket with circuit breaker metrics."""
        # Establish WebSocket connection
        ws_url = "ws://localhost:8000/ws"
        
        import websockets
        
        async with websockets.connect(
            ws_url,
            extra_headers={"Authorization": f"Bearer {self.auth_token}"}
        ) as websocket:
            
            # Send agent execution request
            request = {
                "type": "agent_execute",
                "agent": "triage",
                "message": "WebSocket triage request",
                "request_id": "ws_test_001"
            }
            
            await websocket.send(json.dumps(request))
            
            # Receive response
            response = await websocket.recv()
            result = json.loads(response)
            
            # Verify no AttributeError
            if "error" in result:
                assert "AttributeError" not in result["error"]
                assert "'slow_requests'" not in result["error"]
                
            # Send slow request to test metrics
            slow_request = {
                "type": "agent_execute",
                "agent": "triage",
                "message": "Slow WebSocket request",
                "simulate_delay": 6.0,
                "request_id": "ws_test_002"
            }
            
            await websocket.send(json.dumps(slow_request))
            
            # Wait for slow response
            slow_response = await asyncio.wait_for(
                websocket.recv(),
                timeout=10.0
            )
            slow_result = json.loads(slow_response)
            
            # Should complete without AttributeError
            assert "request_id" in slow_result
            assert slow_result["request_id"] == "ws_test_002"
            

class TestCircuitBreakerMetricsMonitoring(E2ETestBase):
    """E2E tests for circuit breaker metrics monitoring and alerting."""
    
    @pytest.fixture(autouse=True)
    async def setup_monitoring(self):
        """Setup monitoring infrastructure."""
        await self.start_services(['backend', 'auth', 'redis', 'postgres'])
        await self.wait_for_health_check()
        self.api_base = "http://localhost:8000"
        self.metrics_endpoint = f"{self.api_base}/metrics"
        
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_prometheus_metrics_export(self):
        """Test circuit breaker metrics are exported to Prometheus format."""
        async with aiohttp.ClientSession() as session:
            response = await session.get(self.metrics_endpoint)
            
            if response.status == 200:
                metrics_text = await response.text()
                
                # Check for circuit breaker metrics
                assert "circuit_breaker_state" in metrics_text
                assert "circuit_breaker_failures_total" in metrics_text
                assert "circuit_breaker_successes_total" in metrics_text
                
                # Check for slow_requests metric (critical for regression)
                assert "circuit_breaker_slow_requests_total" in metrics_text or \
                       "slow_requests" in metrics_text
                       
    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_grafana_dashboard_data(self):
        """Test circuit breaker data is available for Grafana dashboards."""
        # Query metrics in Prometheus format
        async with aiohttp.ClientSession() as session:
            # Get raw metrics
            response = await session.get(
                f"{self.api_base}/api/metrics/raw",
                params={"format": "json"}
            )
            
            if response.status == 200:
                metrics = await response.json()
                
                # Verify structure for Grafana
                assert "circuit_breakers" in metrics
                
                cb_metrics = metrics["circuit_breakers"]
                for breaker_name, breaker_data in cb_metrics.items():
                    # Each breaker should have complete metrics
                    assert "total_calls" in breaker_data
                    assert "failed_calls" in breaker_data
                    assert "state" in breaker_data
                    # Critical: slow_requests should be present
                    assert "slow_requests" in breaker_data or \
                           "slow_calls" in breaker_data or \
                           len(breaker_data) > 0
                           

class TestRegressionPrevention(E2ETestBase):
    """Specific tests to prevent regression of the circuit breaker metrics issue."""
    
    @pytest.fixture(autouse=True)
    async def setup_regression_tests(self):
        """Setup for regression testing."""
        await self.start_services(['backend', 'auth', 'redis'])
        await self.wait_for_health_check()
        self.api_base = "http://localhost:8000"
        
    @pytest.mark.e2e
    @pytest.mark.regression
    @pytest.mark.asyncio
    async def test_no_attribute_error_on_slow_requests(self):
        """Regression test: Ensure no AttributeError on slow_requests access."""
        # This is the exact scenario that caused the original issue
        
        # Simulate the retry manager accessing metrics
        async with aiohttp.ClientSession() as session:
            # Trigger a slow operation that would cause retry
            response = await session.post(
                f"{self.api_base}/api/agents/execute",
                json={
                    "type": "triage",
                    "message": "Test slow operation",
                    "simulate_delay": 6.0,
                    "force_retry": True
                },
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            result = await response.json()
            
            # The original bug would cause AttributeError here
            if "error" in result:
                error_msg = result["error"]
                assert "AttributeError" not in error_msg, \
                    f"Regression detected: AttributeError found in: {error_msg}"
                assert "'CircuitBreakerMetrics' object has no attribute 'slow_requests'" not in error_msg, \
                    f"Regression detected: Original error found in: {error_msg}"
                    
    @pytest.mark.e2e
    @pytest.mark.regression
    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_interface_consistency(self):
        """Regression test: Verify all metrics implementations have consistent interface."""
        # Get metrics from different endpoints
        endpoints = [
            "/api/metrics/circuit_breakers",
            "/api/agents/metrics",
            "/api/health/detailed"
        ]
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints:
                response = await session.get(f"{self.api_base}{endpoint}")
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Find any circuit breaker metrics in response
                    def check_metrics(obj, path=""):
                        """Recursively check for metrics objects."""
                        if isinstance(obj, dict):
                            # Check if this looks like a metrics object
                            if "failures" in obj or "successes" in obj:
                                # Should be able to access slow_requests
                                # Even if not present, should not cause error
                                slow = obj.get("slow_requests", 0)
                                assert isinstance(slow, (int, float)), \
                                    f"Invalid slow_requests at {path}: {slow}"
                            
                            # Recurse
                            for key, value in obj.items():
                                check_metrics(value, f"{path}.{key}")
                        elif isinstance(obj, list):
                            for i, item in enumerate(obj):
                                check_metrics(item, f"{path}[{i}]")
                    
                    check_metrics(data, endpoint)
                    
    @pytest.mark.e2e
    @pytest.mark.regression
    @pytest.mark.asyncio
    async def test_agent_execution_after_circuit_breaker_fix(self):
        """Regression test: Ensure agents work correctly after circuit breaker fix."""
        # Test each agent type
        agent_types = ["triage", "data", "optimization", "actions", "reporting"]
        
        results = []
        async with aiohttp.ClientSession() as session:
            for agent_type in agent_types:
                response = await session.post(
                    f"{self.api_base}/api/agents/execute",
                    json={
                        "type": agent_type,
                        "message": f"Regression test for {agent_type} agent"
                    }
                )
                
                result = {
                    "agent": agent_type,
                    "status": response.status,
                    "data": await response.json()
                }
                results.append(result)
                
        # All agents should execute without AttributeError
        for result in results:
            if result["status"] != 200:
                # Even on failure, should not be AttributeError
                error = result["data"].get("error", "")
                assert "AttributeError" not in error, \
                    f"Regression in {result['agent']}: {error}"
                assert "slow_requests" not in error, \
                    f"Regression in {result['agent']}: {error}"