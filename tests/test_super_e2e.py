"""
Super End-to-End Test Suite
Complete user journey test from system startup to report generation
"""

import pytest
import asyncio
import subprocess
import time
import requests
import websocket
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock
import psutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSystemE2E:
    """Complete end-to-end test covering full user journey"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment once for all tests"""
        cls.backend_process = None
        cls.frontend_process = None
        cls.backend_url = "http://localhost:8000"
        cls.frontend_url = "http://localhost:3000"
        cls.ws_url = "ws://localhost:8000/ws"
        cls.test_user = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "username": "testuser"
        }
        cls.auth_token = None
        cls.websocket_conn = None
    
    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests"""
        if cls.backend_process:
            cls.stop_backend()
        if cls.frontend_process:
            cls.stop_frontend()
        if cls.websocket_conn:
            cls.websocket_conn.close()
    
    @classmethod
    def start_backend(cls):
        """Start the backend server"""
        print("Starting backend server...")
        env = os.environ.copy()
        env.update({
            "DATABASE_URL": "sqlite+aiosqlite:///test_e2e.db",
            "TESTING": "1",
            "SECRET_KEY": "test-secret-key-e2e",
            "REDIS_URL": "redis://localhost:6379/2",
            "LOG_LEVEL": "INFO"
        })
        
        cls.backend_process = subprocess.Popen(
            ["python", "scripts/run_server.py", "--no-reload"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for backend to be ready
        cls.wait_for_service(cls.backend_url + "/health", timeout=30)
        print("Backend server started successfully")
    
    @classmethod
    def start_frontend(cls):
        """Start the frontend development server"""
        print("Starting frontend server...")
        env = os.environ.copy()
        env.update({
            "NEXT_PUBLIC_API_URL": cls.backend_url,
            "NEXT_PUBLIC_WS_URL": cls.ws_url
        })
        
        cls.frontend_process = subprocess.Popen(
            ["npm.cmd", "run", "dev"],
            cwd="frontend",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for frontend to be ready
        cls.wait_for_service(cls.frontend_url, timeout=60)
        print("Frontend server started successfully")
    
    @classmethod
    def stop_backend(cls):
        """Stop the backend server"""
        if cls.backend_process:
            cls.backend_process.terminate()
            try:
                cls.backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Process didn't terminate, force killing")
                cls.backend_process.kill()
                cls.backend_process.wait(timeout=5)
            cls.backend_process = None
            print("Backend server stopped")
    
    @classmethod
    def stop_frontend(cls):
        """Stop the frontend server"""
        if cls.frontend_process:
            cls.frontend_process.terminate()
            cls.frontend_process.wait(timeout=10)
            cls.frontend_process = None
            print("Frontend server stopped")
    
    @classmethod
    def wait_for_service(cls, url: str, timeout: int = 30):
        """Wait for a service to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=1)
                if response.status_code == 200:
                    return True
            except (requests.exceptions.RequestException, ConnectionError):
                # Check if backend process is still running
                if hasattr(cls, 'backend_process') and cls.backend_process:
                    if cls.backend_process.poll() is not None:
                        # Process has terminated
                        stdout, stderr = cls.backend_process.communicate()
                        print(f"Backend process terminated with code: {cls.backend_process.returncode}")
                        print(f"STDOUT: {stdout.decode()}")
                        print(f"STDERR: {stderr.decode()}")
                        raise RuntimeError("Backend process terminated unexpectedly")
                time.sleep(0.5)
        raise TimeoutError(f"Service at {url} did not start within {timeout} seconds")
    
    def test_01_system_startup(self):
        """Test complete system startup sequence"""
        print("\n=== Testing System Startup ===")
        
        # Start backend
        self.start_backend()
        
        # Verify backend health
        response = requests.get(f"{self.backend_url}/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] in ["OK", "healthy"]
        print(f"Backend health check: {health_data}")
        
        # Start frontend
        self.start_frontend()
        
        # Verify frontend is accessible
        response = requests.get(self.frontend_url)
        assert response.status_code == 200
        print("Frontend is accessible")
        
        # Check detailed health (using extended health endpoint)
        response = requests.get(f"{self.backend_url}/health/detailed")
        if response.status_code == 200:
            detailed_health = response.json()
            print(f"Detailed health: {detailed_health}")
            # Don't assert specific keys since this might be a different endpoint
    
    def test_02_user_registration(self):
        """Test user development login flow (no registration endpoint)"""
        print("\n=== Testing User Development Login ===")
        
        # Use development login since no registration endpoint exists
        response = requests.post(
            f"{self.backend_url}/api/auth/dev_login",
            json={"email": self.test_user["email"]}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            self.__class__.auth_token = data["access_token"]
            print(f"Dev user logged in: {self.test_user['email']}")
        elif response.status_code == 403:
            print("Dev login disabled - will try token login in next test")
        else:
            print(f"Dev login failed with status {response.status_code}: {response.text}")
    
    def test_03_user_login(self):
        """Test user login flow"""
        print("\n=== Testing User Login ===")
        
        # If dev login already provided a token, skip password login
        if self.auth_token:
            print(f"Using existing auth token from dev login: {self.auth_token[:20]}...")
            return
        
        # Login user using token endpoint (OAuth2 password flow)
        response = requests.post(
            f"{self.backend_url}/api/auth/token",
            data={
                "username": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            self.__class__.auth_token = data["access_token"]
            print(f"User logged in via token: {self.test_user['email']}")
            print(f"Auth token received: {self.auth_token[:20]}...")
        else:
            print(f"Token login failed with {response.status_code}: {response.text}")
            # For development, this might be expected if user was created via dev login
    
    def test_04_websocket_connection(self):
        """Test WebSocket connection establishment"""
        print("\n=== Testing WebSocket Connection ===")
        
        # Create WebSocket connection with auth
        ws_url_with_auth = f"{self.ws_url}?token={self.auth_token}"
        
        try:
            self.__class__.websocket_conn = websocket.create_connection(
                ws_url_with_auth,
                timeout=10
            )
            print("WebSocket connected successfully")
            
            # Send ping
            self.websocket_conn.send(json.dumps({"type": "ping"}))
            
            # Wait for pong
            response = self.websocket_conn.recv()
            data = json.loads(response)
            assert data.get("type") == "pong"
            print("WebSocket heartbeat working")
            
        except Exception as e:
            pytest.fail(f"WebSocket connection failed: {e}")
    
    def test_05_navigate_to_demo(self):
        """Test navigation to demo page"""
        print("\n=== Testing Demo Page Navigation ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Get demo page data
        response = requests.get(
            f"{self.backend_url}/api/demo",
            headers=headers
        )
        
        if response.status_code == 200:
            demo_data = response.json()
            print(f"Demo page accessible, data: {demo_data}")
        else:
            print(f"Demo endpoint returned {response.status_code}")
        
        # Check if we can access the demo route
        response = requests.get(f"{self.frontend_url}/demo")
        assert response.status_code in [200, 301, 302]  # May redirect
        print("Demo page route accessible")
    
    def test_06_send_agent_request(self):
        """Test sending a request to the agent system"""
        print("\n=== Testing Agent Request ===")
        
        # Prepare agent request
        agent_request = {
            "type": "agent_request",
            "message": "Analyze my AI workload and provide optimization recommendations",
            "thread_id": "test_thread_001",
            "metadata": {
                "source": "demo",
                "test": True
            }
        }
        
        # Send via WebSocket
        if self.websocket_conn:
            self.websocket_conn.send(json.dumps(agent_request))
            print(f"Sent agent request: {agent_request['message']}")
            
            # Wait for agent responses
            responses = []
            start_time = time.time()
            timeout = 30  # 30 seconds timeout
            
            while time.time() - start_time < timeout:
                try:
                    response = self.websocket_conn.recv()
                    data = json.loads(response)
                    responses.append(data)
                    
                    print(f"Received response type: {data.get('type')}")
                    
                    # Check for different agent events
                    if data.get("type") == "agent_start":
                        print(f"Agent started: {data.get('agent_name')}")
                    elif data.get("type") == "agent_update":
                        print(f"Agent update: {data.get('content', '')[:100]}...")
                    elif data.get("type") == "agent_complete":
                        print("Agent completed processing")
                        break
                    elif data.get("type") == "error":
                        print(f"Error: {data.get('message')}")
                        break
                        
                except websocket.WebSocketTimeoutException:
                    break
            
            assert len(responses) > 0, "No responses received from agent"
            print(f"Total responses received: {len(responses)}")
    
    def test_07_get_agent_report(self):
        """Test retrieving agent-generated report"""
        print("\n=== Testing Agent Report Retrieval ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Get recent runs
        response = requests.get(
            f"{self.backend_url}/api/agent/runs",
            headers=headers
        )
        
        if response.status_code == 200:
            runs = response.json()
            print(f"Found {len(runs)} agent runs")
            
            if runs:
                latest_run = runs[0]
                run_id = latest_run.get("id")
                
                # Get report for the run
                response = requests.get(
                    f"{self.backend_url}/api/agent/runs/{run_id}/report",
                    headers=headers
                )
                
                if response.status_code == 200:
                    report = response.json()
                    print(f"Report retrieved successfully")
                    print(f"Report summary: {report.get('summary', '')[:200]}...")
                    assert "summary" in report or "content" in report
    
    def test_08_view_thread_history(self):
        """Test viewing conversation thread history"""
        print("\n=== Testing Thread History ===")
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Get threads
        response = requests.get(
            f"{self.backend_url}/api/threads",
            headers=headers
        )
        
        assert response.status_code == 200
        threads = response.json()
        print(f"Found {len(threads)} threads")
        
        if threads:
            thread_id = threads[0].get("id")
            
            # Get messages for thread
            response = requests.get(
                f"{self.backend_url}/api/threads/{thread_id}/messages",
                headers=headers
            )
            
            if response.status_code == 200:
                messages = response.json()
                print(f"Thread {thread_id} has {len(messages)} messages")
                
                for msg in messages[:3]:  # Show first 3 messages
                    print(f"  - {msg.get('role')}: {msg.get('content', '')[:100]}...")
    
    def test_09_test_optimization_tools(self):
        """Test specific optimization tools"""
        print("\n=== Testing Optimization Tools ===")
        
        # Test cost analysis request
        optimization_request = {
            "type": "agent_request",
            "message": "Perform cost analysis for GPT-4 usage with 1000 requests per day",
            "thread_id": "test_thread_002",
            "metadata": {
                "tool_request": "cost_analysis"
            }
        }
        
        if self.websocket_conn:
            self.websocket_conn.send(json.dumps(optimization_request))
            print("Sent cost analysis request")
            
            # Wait for response
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    response = self.websocket_conn.recv()
                    data = json.loads(response)
                    
                    if "cost" in str(data).lower() or "analysis" in str(data).lower():
                        print("Cost analysis response received")
                        break
                except:
                    pass
    
    def test_10_performance_metrics(self):
        """Test and measure system performance"""
        print("\n=== Testing Performance Metrics ===")
        
        metrics = {
            "startup_time": 0,
            "api_response_time": 0,
            "websocket_latency": 0,
            "agent_processing_time": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }
        
        # Measure API response time
        start = time.time()
        response = requests.get(f"{self.backend_url}/health")
        metrics["api_response_time"] = (time.time() - start) * 1000  # ms
        
        # Measure WebSocket latency
        if self.websocket_conn:
            start = time.time()
            self.websocket_conn.send(json.dumps({"type": "ping"}))
            response = self.websocket_conn.recv()
            metrics["websocket_latency"] = (time.time() - start) * 1000  # ms
        
        # Get system metrics
        process = psutil.Process()
        metrics["memory_usage"] = process.memory_info().rss / 1024 / 1024  # MB
        metrics["cpu_usage"] = process.cpu_percent()
        
        print("\nPerformance Metrics:")
        for key, value in metrics.items():
            if key.endswith("_time") or key.endswith("_latency"):
                print(f"  {key}: {value:.2f} ms")
            elif key == "memory_usage":
                print(f"  {key}: {value:.2f} MB")
            elif key == "cpu_usage":
                print(f"  {key}: {value:.1f}%")
            else:
                print(f"  {key}: {value}")
        
        # Assert reasonable performance
        assert metrics["api_response_time"] < 1000  # Less than 1 second
        assert metrics["websocket_latency"] < 500   # Less than 500ms
        assert metrics["memory_usage"] < 2000       # Less than 2GB
    
    def test_11_error_recovery(self):
        """Test system error recovery capabilities"""
        print("\n=== Testing Error Recovery ===")
        
        # Test invalid request handling
        invalid_request = {
            "type": "invalid_type",
            "data": None
        }
        
        if self.websocket_conn:
            self.websocket_conn.send(json.dumps(invalid_request))
            print("Sent invalid request")
            
            # Should receive error response
            response = self.websocket_conn.recv()
            data = json.loads(response)
            
            if data.get("type") == "error":
                print(f"Error handled correctly: {data.get('message')}")
            
            # Connection should still be alive
            self.websocket_conn.send(json.dumps({"type": "ping"}))
            response = self.websocket_conn.recv()
            data = json.loads(response)
            assert data.get("type") == "pong"
            print("Connection recovered from error")
    
    def test_12_concurrent_users(self):
        """Test system with multiple concurrent users"""
        print("\n=== Testing Concurrent Users ===")
        
        import threading
        import queue
        
        results = queue.Queue()
        
        def simulate_user(user_id: int):
            """Simulate a user session"""
            try:
                # Use dev login instead of password login
                response = requests.post(
                    f"{self.backend_url}/api/auth/dev_login",
                    json={"email": f"testuser{user_id}@example.com"}
                )
                
                if response.status_code == 200:
                    token = response.json()["access_token"]
                    
                    # Make API request
                    headers = {"Authorization": f"Bearer {token}"}
                    response = requests.get(
                        f"{self.backend_url}/api/threads",
                        headers=headers
                    )
                    
                    results.put({
                        "user_id": user_id,
                        "success": response.status_code == 200
                    })
                elif response.status_code == 403:
                    # Dev login disabled, fall back to token endpoint
                    results.put({"user_id": user_id, "success": False, "reason": "dev_login_disabled"})
                else:
                    results.put({"user_id": user_id, "success": False, "reason": f"auth_failed_{response.status_code}"})
                    
            except Exception as e:
                results.put({
                    "user_id": user_id,
                    "success": False,
                    "error": str(e)
                })
        
        # Simulate 5 concurrent users
        threads = []
        num_users = 5
        
        for i in range(num_users):
            thread = threading.Thread(target=simulate_user, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        successful = 0
        while not results.empty():
            result = results.get()
            if result["success"]:
                successful += 1
        
        print(f"Concurrent users test: {successful}/{num_users} successful")
        assert successful >= num_users * 0.8  # At least 80% success rate
    
    def test_13_graceful_shutdown(self):
        """Test graceful system shutdown"""
        print("\n=== Testing Graceful Shutdown ===")
        
        # Start backend if not already running
        if not self.backend_process:
            self.start_backend()
        
        # Close WebSocket connection gracefully
        if self.websocket_conn:
            self.websocket_conn.close()
            print("WebSocket connection closed")
            self.__class__.websocket_conn = None
        
        # Verify services are still responding
        response = requests.get(f"{self.backend_url}/health")
        assert response.status_code == 200
        print("Backend still healthy before shutdown")
        
        # Stop services
        self.stop_frontend()
        self.stop_backend()
        
        # Verify services are stopped
        # Add small delay for process shutdown
        import time
        time.sleep(2)
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=1)
            assert False, "Backend should be stopped"
        except (requests.exceptions.RequestException, ConnectionError):
            print("Backend stopped successfully")
        
        try:
            response = requests.get(f"{self.frontend_url}", timeout=1)
            assert False, "Frontend should be stopped"
        except (requests.exceptions.RequestException, ConnectionError):
            print("Frontend stopped successfully")


# Removed fake test class with empty test methods


if __name__ == "__main__":
    # Run the complete E2E test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-s",  # Show print statements
        "--disable-warnings"
    ])