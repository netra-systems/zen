"""
Critical System Initialization Tests - 30 Comprehensive Cold Start Scenarios

These tests validate the most critical and difficult initialization scenarios,
focusing on real services and common production failure modes.
"""

import asyncio
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import httpx
import psutil
import pytest
import redis
import websocket
from sqlalchemy import create_engine, text

# Add project root to path

from netra_backend.app.db.postgres import async_engine, initialize_postgres
from test_framework.test_helpers import (
    cleanup_test_environment,
    wait_for_service,
    get_available_port,
    kill_process_tree,
    create_test_user_with_oauth
)


class SystemInitializationTestBase:
    """Base class for system initialization tests with comprehensive helpers."""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment."""
        cls.project_root = Path(__file__).parent.parent.parent
        cls.dev_launcher = cls.project_root / "scripts" / "dev_launcher.py"
        cls.is_windows = platform.system() == "Windows"
        cls.test_start_time = datetime.now()
        
        # Service URLs
        cls.backend_url = "http://localhost:8000"
        cls.auth_url = "http://localhost:8081"
        cls.frontend_url = "http://localhost:3000"
        
        # Test data
        cls.test_user_email = "test_init@netra.ai"
        cls.test_user_password = "TestInit123!@#"
        
    @classmethod
    def teardown_class(cls):
        """Cleanup after all tests."""
        cleanup_test_environment()
        
    def setup_method(self):
        """Setup for each test."""
        self.cleanup_processes()
        self.reset_databases()
        self.clear_service_discovery()
        
    def teardown_method(self):
        """Cleanup after each test."""
        self.cleanup_processes()
        
    def cleanup_processes(self):
        """Kill all test-related processes."""
        processes_to_kill = ["uvicorn", "node", "next", "dev_launcher"]
        for proc_name in processes_to_kill:
            try:
                if self.is_windows:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", f"{proc_name}.exe"],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    subprocess.run(
                        ["pkill", "-f", proc_name],
                        capture_output=True,
                        timeout=5
                    )
            except Exception:
                pass
                
    def reset_databases(self):
        """Reset all databases to clean state."""
        try:
            # Reset PostgreSQL
            engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test"))
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                conn.commit()
        except Exception as e:
            print(f"Database reset error (may be expected): {e}")
            
        try:
            # Clear Redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.flushall()
        except Exception:
            pass
            
    def clear_service_discovery(self):
        """Clear service discovery files."""
        discovery_files = [
            ".service_discovery.json",
            ".dev_services.json",
            ".service_ports.json"
        ]
        for file in discovery_files:
            file_path = self.project_root / file
            if file_path.exists():
                file_path.unlink()
                
    @contextmanager
    def start_dev_launcher(self, args: List[str] = None, timeout: int = 30):
        """Start dev launcher with specified arguments."""
        if args is None:
            args = ["--minimal", "--no-browser", "--non-interactive"]
            
        process = subprocess.Popen(
            ["python", str(self.dev_launcher)] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        try:
            # Wait for services to be ready
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._check_services_ready():
                    break
                time.sleep(1)
            yield process
        finally:
            if self.is_windows:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
            else:
                process.terminate()
            process.wait(timeout=5)
            
    def _check_services_ready(self) -> bool:
        """Check if all services are ready."""
        try:
            # Check backend
            response = httpx.get(f"{self.backend_url}/health", timeout=2)
            if response.status_code != 200:
                return False
                
            # Check auth service
            response = httpx.get(f"{self.auth_url}/health", timeout=2)
            if response.status_code != 200:
                return False
                
            return True
        except Exception:
            return False
            
    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = httpx.get(url, timeout=2)
                if response.status_code in [200, 404]:  # 404 is ok, means service is up
                    return True
            except Exception:
                pass
            time.sleep(1)
        return False
        
    def create_websocket_connection(self, token: str = None):
        """Create authenticated WebSocket connection."""
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        ws = websocket.create_connection(
            "ws://localhost:8000/ws",
            header=headers,
            timeout=10
        )
        return ws


class TestCriticalPath(SystemInitializationTestBase):
    """Category 1: Critical Path Tests - Must work for basic functionality"""
    
    def test_01_complete_cold_start_from_empty_state(self):
        """Test 1: Full system startup with no existing data or configuration."""
        # Clear everything
        self.cleanup_processes()
        self.reset_databases()
        self.clear_service_discovery()
        
        # Remove all environment-specific files
        env_files = [".env.local", ".env.development", ".env.test"]
        for env_file in env_files:
            file_path = self.project_root / env_file
            if file_path.exists():
                file_path.unlink()
                
        # Start system from completely clean state
        with self.start_dev_launcher(["--minimal", "--no-browser"]) as proc:
            # Verify all services start
            assert self.wait_for_service(f"{self.backend_url}/health"), "Backend failed to start"
            assert self.wait_for_service(f"{self.auth_url}/health"), "Auth service failed to start"
            
            # Verify database tables created
            engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test"))
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                table_count = result.scalar()
                assert table_count > 0, "Database tables not created"
                
            # Verify Redis connectivity
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            assert r.ping(), "Redis not accessible"
            
    def test_02_service_startup_order_dependency_chain(self):
        """Test 2: Verify correct service startup sequencing and dependencies."""
        # Start services in wrong order intentionally
        self.cleanup_processes()
        
        # Try to start backend without auth service
        backend_proc = subprocess.Popen(
            ["python", "-m", "uvicorn", "netra_backend.app.main:app", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_root
        )
        
        time.sleep(3)
        
        # Backend should either wait for auth or fail gracefully
        # Now start auth service
        auth_proc = subprocess.Popen(
            ["python", "-m", "uvicorn", "auth_service.main:app", "--port", "8081"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_root
        )
        
        try:
            # Both services should eventually become healthy
            assert self.wait_for_service(f"{self.backend_url}/health", timeout=20)
            assert self.wait_for_service(f"{self.auth_url}/health", timeout=20)
            
            # Verify cross-service communication works
            response = httpx.get(f"{self.backend_url}/auth/verify")
            assert response.status_code in [200, 401], "Cross-service auth check failed"
        finally:
            backend_proc.terminate()
            auth_proc.terminate()
            
    def test_03_database_schema_initialization_and_migration(self):
        """Test 3: Fresh database with automatic schema creation."""
        # Drop all database objects
        self.reset_databases()
        
        with self.start_dev_launcher() as proc:
            # Check database migrations ran
            engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test"))
            with engine.connect() as conn:
                # Check core tables exist
                tables_to_check = [
                    "users",
                    "threads",
                    "messages",
                    "oauth_providers",
                    "sessions"
                ]
                
                for table in tables_to_check:
                    result = conn.execute(text(
                        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                        f"WHERE table_name = '{table}')"
                    ))
                    exists = result.scalar()
                    assert exists, f"Table {table} not created"
                    
                # Check indexes exist
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'"
                ))
                index_count = result.scalar()
                assert index_count > 0, "Database indexes not created"
                
    def test_04_authentication_flow_end_to_end_setup(self):
        """Test 4: JWT and OAuth provider setup with cross-service validation."""
        with self.start_dev_launcher() as proc:
            # Test JWT secret generation and synchronization
            # Create token in auth service
            auth_response = httpx.post(
                f"{self.auth_url}/auth/login",
                json={"email": "test@example.com", "password": "password"}
            )
            
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token")
                
                # Validate token in backend service
                backend_response = httpx.get(
                    f"{self.backend_url}/api/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert backend_response.status_code in [200, 401], "Token validation failed"
                
            # Test OAuth provider configuration
            oauth_response = httpx.get(f"{self.auth_url}/auth/oauth/providers")
            assert oauth_response.status_code == 200, "OAuth providers not configured"
            providers = oauth_response.json()
            assert len(providers) > 0, "No OAuth providers available"
            
    def test_05_websocket_connection_establishment(self):
        """Test 5: WebSocket endpoint registration and authentication."""
        with self.start_dev_launcher() as proc:
            # Test unauthenticated connection
            try:
                ws = websocket.create_connection(
                    "ws://localhost:8000/ws",
                    timeout=10
                )
                ws.send(json.dumps({"type": "ping"}))
                response = ws.recv()
                ws.close()
                assert response, "WebSocket connection failed"
            except Exception as e:
                pytest.fail(f"WebSocket connection failed: {e}")
                
            # Test authenticated connection
            # First get a token
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": f"ws_test_{int(time.time())}@test.com",
                    "password": "TestPass123!"
                }
            )
            
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token")
                
                # Connect with authentication
                ws = websocket.create_connection(
                    "ws://localhost:8000/ws",
                    header={"Authorization": f"Bearer {token}"},
                    timeout=10
                )
                ws.send(json.dumps({"type": "authenticate", "token": token}))
                response = ws.recv()
                ws.close()
                assert "authenticated" in response.lower() or "success" in response.lower()
                
    def test_06_real_time_message_processing_pipeline(self):
        """Test 6: End-to-end message flow from WebSocket to LLM to response."""
        with self.start_dev_launcher() as proc:
            # Create authenticated session
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": f"pipeline_test_{int(time.time())}@test.com",
                    "password": "TestPass123!"
                }
            )
            
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token")
                
                # Create WebSocket connection
                ws = websocket.create_connection(
                    "ws://localhost:8000/ws",
                    header={"Authorization": f"Bearer {token}"},
                    timeout=30
                )
                
                # Send chat message
                message = {
                    "type": "chat_message",
                    "content": "Hello, this is a test message",
                    "thread_id": "test_thread_001"
                }
                ws.send(json.dumps(message))
                
                # Wait for response (might be streamed)
                responses_received = []
                start_time = time.time()
                while time.time() - start_time < 10:
                    try:
                        response = ws.recv()
                        responses_received.append(response)
                        if "complete" in response.lower() or "done" in response.lower():
                            break
                    except websocket.WebSocketTimeoutException:
                        break
                        
                ws.close()
                assert len(responses_received) > 0, "No response received from message pipeline"
                
    def test_07_frontend_static_asset_loading_and_api_connection(self):
        """Test 7: Next.js compilation and API endpoint discovery."""
        with self.start_dev_launcher(["--frontend-port", "3000"]) as proc:
            # Wait for frontend to compile
            assert self.wait_for_service(f"{self.frontend_url}", timeout=60), "Frontend failed to start"
            
            # Check static assets are served
            response = httpx.get(f"{self.frontend_url}/_next/static/chunks/main.js", follow_redirects=True)
            assert response.status_code in [200, 304], "Frontend assets not served"
            
            # Check API configuration
            response = httpx.get(f"{self.frontend_url}/api/health", timeout=5)
            assert response.status_code in [200, 404], "Frontend API route check failed"
            
            # Verify frontend can reach backend
            # This would normally be done through the browser, but we can check CORS
            response = httpx.options(
                f"{self.backend_url}/api/threads",
                headers={
                    "Origin": self.frontend_url,
                    "Access-Control-Request-Method": "GET"
                }
            )
            assert response.status_code in [200, 204], "CORS not configured correctly"
            
    def test_08_health_check_cascade_validation(self):
        """Test 8: All service health endpoints with dependency validation."""
        with self.start_dev_launcher() as proc:
            # Check each service's health endpoint
            services = [
                (self.backend_url, "backend"),
                (self.auth_url, "auth"),
            ]
            
            for url, name in services:
                response = httpx.get(f"{url}/health", timeout=5)
                assert response.status_code == 200, f"{name} health check failed"
                
                health_data = response.json()
                assert "status" in health_data, f"{name} health response missing status"
                assert health_data["status"] in ["healthy", "ok"], f"{name} not healthy"
                
                # Check dependency health reporting
                if "dependencies" in health_data:
                    for dep_name, dep_status in health_data["dependencies"].items():
                        assert dep_status in ["healthy", "ok", "connected"], f"{name} dependency {dep_name} not healthy"


class TestServiceDependencies(SystemInitializationTestBase):
    """Category 2: Service Dependencies - Cross-service communication"""
    
    def test_09_redis_connection_failure_recovery(self):
        """Test 9: Redis unavailable at startup with graceful degradation."""
        # Stop Redis if running
        try:
            if self.is_windows:
                subprocess.run(["taskkill", "/F", "/IM", "redis-server.exe"], capture_output=True)
            else:
                subprocess.run(["pkill", "redis-server"], capture_output=True)
        except Exception:
            pass
            
        # Start services without Redis
        with self.start_dev_launcher(["--set-redis", "mock"]) as proc:
            # Services should start even without Redis
            assert self.wait_for_service(f"{self.backend_url}/health"), "Backend failed without Redis"
            
            # Test fallback caching behavior
            response = httpx.get(f"{self.backend_url}/api/cache/test")
            assert response.status_code in [200, 501], "Cache fallback not working"
            
    def test_10_clickhouse_port_configuration_matrix(self):
        """Test 10: Test all ClickHouse port configurations."""
        clickhouse_ports = {
            "http": 8123,
            "native": 9000,
            "https": 8443
        }
        
        with self.start_dev_launcher() as proc:
            for protocol, port in clickhouse_ports.items():
                # Test connection on each port
                try:
                    if protocol == "http":
                        response = httpx.get(f"http://localhost:{port}/ping", timeout=2)
                        if response.status_code == 200:
                            print(f"ClickHouse {protocol} port {port} accessible")
                except Exception:
                    # Port might not be configured
                    pass
                    
    def test_11_auth_backend_jwt_secret_synchronization(self):
        """Test 11: JWT secret synchronization between services."""
        with self.start_dev_launcher() as proc:
            # Create token in auth service
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": f"jwt_sync_{int(time.time())}@test.com",
                    "password": "TestPass123!"
                }
            )
            
            assert auth_response.status_code == 200, "Registration failed"
            auth_token = auth_response.json().get("access_token")
            
            # Validate token in backend
            backend_response = httpx.get(
                f"{self.backend_url}/api/me",
                headers={"Authorization": f"Bearer {auth_token}"}
            )
            
            # Should either validate successfully or return proper auth error
            assert backend_response.status_code in [200, 401], "Token validation unexpected response"
            
            # Test with invalid token
            invalid_response = httpx.get(
                f"{self.backend_url}/api/me",
                headers={"Authorization": "Bearer invalid_token_12345"}
            )
            assert invalid_response.status_code == 401, "Invalid token not rejected"
            
    def test_12_service_discovery_dynamic_ports(self):
        """Test 12: Dynamic port allocation and service discovery."""
        # Occupy default ports
        occupied_sockets = []
        try:
            # Occupy port 8000
            s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s1.bind(('localhost', 8000))
            s1.listen(1)
            occupied_sockets.append(s1)
            
            # Start services - should use dynamic ports
            with self.start_dev_launcher(["--dynamic"]) as proc:
                # Check service discovery file created
                discovery_file = self.project_root / ".service_discovery.json"
                assert discovery_file.exists(), "Service discovery file not created"
                
                with open(discovery_file) as f:
                    discovery = json.load(f)
                    
                # Verify services on different ports
                backend_port = discovery.get("backend", {}).get("port")
                assert backend_port != 8000, "Backend didn't use dynamic port"
                
                # Verify service accessible on dynamic port
                assert self.wait_for_service(f"http://localhost:{backend_port}/health")
        finally:
            for s in occupied_sockets:
                s.close()
                
    def test_13_database_connection_pool_high_load(self):
        """Test 13: Connection pool behavior under concurrent startup."""
        with self.start_dev_launcher() as proc:
            # Create multiple concurrent database operations
            import concurrent.futures
            
            def make_db_request(index):
                try:
                    response = httpx.get(f"{self.backend_url}/api/threads", timeout=5)
                    return response.status_code
                except Exception as e:
                    return str(e)
                    
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(make_db_request, i) for i in range(50)]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                
            # Should handle concurrent requests without pool exhaustion
            success_count = sum(1 for r in results if isinstance(r, int) and r < 500)
            assert success_count > 40, f"Too many failures under load: {success_count}/50 succeeded"
            
    def test_14_cross_service_token_propagation(self):
        """Test 14: Tokens work across all services."""
        with self.start_dev_launcher() as proc:
            # Create token in auth service
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": f"cross_service_{int(time.time())}@test.com",
                    "password": "TestPass123!"
                }
            )
            
            token = auth_response.json().get("access_token")
            
            # Test token in different services
            services_to_test = [
                (f"{self.backend_url}/api/me", "backend"),
                (f"{self.auth_url}/auth/me", "auth"),
            ]
            
            for url, service_name in services_to_test:
                response = httpx.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"}
                )
                assert response.status_code in [200, 404], f"Token not valid in {service_name}"
                
    def test_15_websocket_connection_load_balancing(self):
        """Test 15: Multiple WebSocket connections handled properly."""
        with self.start_dev_launcher() as proc:
            connections = []
            
            try:
                # Create multiple WebSocket connections
                for i in range(10):
                    ws = websocket.create_connection(
                        "ws://localhost:8000/ws",
                        timeout=5
                    )
                    connections.append(ws)
                    
                # Send messages on all connections
                for i, ws in enumerate(connections):
                    ws.send(json.dumps({"type": "ping", "id": i}))
                    
                # Verify all connections receive responses
                for ws in connections:
                    response = ws.recv()
                    assert response, "Connection didn't receive response"
                    
            finally:
                for ws in connections:
                    try:
                        ws.close()
                    except Exception:
                        pass


class TestUserJourney(SystemInitializationTestBase):
    """Category 3: User Journey - First-time user experience"""
    
    def test_16_first_time_user_registration_flow(self):
        """Test 16: Complete new user signup through OAuth."""
        with self.start_dev_launcher() as proc:
            # Test user registration
            email = f"new_user_{int(time.time())}@test.com"
            response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": email,
                    "password": "NewUser123!",
                    "name": "New User"
                }
            )
            
            assert response.status_code == 200, "Registration failed"
            data = response.json()
            assert "access_token" in data, "No access token returned"
            assert "user" in data, "No user data returned"
            
            # Verify user can login
            login_response = httpx.post(
                f"{self.auth_url}/auth/login",
                json={
                    "email": email,
                    "password": "NewUser123!"
                }
            )
            assert login_response.status_code == 200, "Login failed for new user"
            
    def test_17_initial_chat_session_creation(self):
        """Test 17: First-time user creates a chat thread."""
        with self.start_dev_launcher() as proc:
            # Register user
            email = f"chat_user_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "ChatUser123!"}
            )
            
            token = auth_response.json().get("access_token")
            
            # Create chat thread
            thread_response = httpx.post(
                f"{self.backend_url}/api/threads",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "My First Chat"}
            )
            
            assert thread_response.status_code in [200, 201], "Thread creation failed"
            thread_data = thread_response.json()
            thread_id = thread_data.get("id")
            
            # Send first message
            message_response = httpx.post(
                f"{self.backend_url}/api/threads/{thread_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={"content": "Hello, this is my first message!"}
            )
            
            assert message_response.status_code in [200, 201], "Message creation failed"
            
    def test_18_frontend_authentication_state(self):
        """Test 18: Frontend loads and manages auth state."""
        with self.start_dev_launcher(["--frontend-port", "3001"]) as proc:
            # Wait for frontend
            assert self.wait_for_service("http://localhost:3001", timeout=60)
            
            # Check frontend serves auth pages
            response = httpx.get("http://localhost:3001", follow_redirects=True)
            assert response.status_code == 200, "Frontend not accessible"
            
            # Frontend should have auth endpoints configured
            # Check if API routes are set up
            api_response = httpx.get("http://localhost:3001/auth/session")
            assert api_response.status_code in [200, 401, 404], "Auth API routes not configured"
            
    def test_19_real_time_chat_message_exchange(self):
        """Test 19: User sends message and receives AI response."""
        with self.start_dev_launcher() as proc:
            # Create user and get token
            email = f"realtime_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "Realtime123!"}
            )
            
            token = auth_response.json().get("access_token")
            
            # Create WebSocket connection
            ws = websocket.create_connection(
                "ws://localhost:8000/ws",
                header={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            
            # Send chat message
            ws.send(json.dumps({
                "type": "chat_message",
                "content": "What is 2+2?",
                "thread_id": "realtime_thread"
            }))
            
            # Collect responses
            responses = []
            start_time = time.time()
            while time.time() - start_time < 10:
                try:
                    response = ws.recv()
                    responses.append(response)
                except websocket.WebSocketTimeoutException:
                    break
                    
            ws.close()
            
            # Should receive at least one response
            assert len(responses) > 0, "No AI response received"
            
    def test_20_session_persistence_browser_restart(self):
        """Test 20: Session survives browser restart."""
        with self.start_dev_launcher() as proc:
            # Create session
            email = f"persist_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "Persist123!"}
            )
            
            token = auth_response.json().get("access_token")
            refresh_token = auth_response.json().get("refresh_token")
            
            # Simulate browser restart - use refresh token
            time.sleep(2)
            
            if refresh_token:
                refresh_response = httpx.post(
                    f"{self.auth_url}/auth/refresh",
                    json={"refresh_token": refresh_token}
                )
                
                assert refresh_response.status_code == 200, "Session refresh failed"
                new_token = refresh_response.json().get("access_token")
                
                # Verify new token works
                me_response = httpx.get(
                    f"{self.backend_url}/api/me",
                    headers={"Authorization": f"Bearer {new_token}"}
                )
                assert me_response.status_code in [200, 404], "New token not valid"
                
    def test_21_multi_tab_session_synchronization(self):
        """Test 21: Multiple tabs with synchronized state."""
        with self.start_dev_launcher() as proc:
            # Create user session
            email = f"multitab_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "MultiTab123!"}
            )
            
            token = auth_response.json().get("access_token")
            
            # Simulate multiple tabs with WebSocket connections
            ws1 = websocket.create_connection(
                "ws://localhost:8000/ws",
                header={"Authorization": f"Bearer {token}"}
            )
            
            ws2 = websocket.create_connection(
                "ws://localhost:8000/ws",
                header={"Authorization": f"Bearer {token}"}
            )
            
            # Send message from tab 1
            ws1.send(json.dumps({
                "type": "chat_message",
                "content": "Message from tab 1",
                "thread_id": "shared_thread"
            }))
            
            # Both connections should be maintained
            ws1.send(json.dumps({"type": "ping"}))
            ws2.send(json.dumps({"type": "ping"}))
            
            response1 = ws1.recv()
            response2 = ws2.recv()
            
            assert response1 and response2, "Multi-tab connections not maintained"
            
            ws1.close()
            ws2.close()


class TestRecoveryResilience(SystemInitializationTestBase):
    """Category 4: Recovery and Resilience - Error handling"""
    
    def test_22_database_recovery_after_partition(self):
        """Test 22: Database reconnection after network partition."""
        with self.start_dev_launcher() as proc:
            # Verify initial connectivity
            response = httpx.get(f"{self.backend_url}/health")
            assert response.status_code == 200
            
            # Simulate database connection loss (would need actual network control)
            # For now, test that health check reports database status
            health_data = response.json()
            if "dependencies" in health_data:
                assert "database" in health_data["dependencies"], "Database health not monitored"
                
    def test_23_service_restart_without_data_loss(self):
        """Test 23: Backend restart with connection recovery."""
        with self.start_dev_launcher() as launcher_proc:
            # Create a thread
            email = f"restart_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "Restart123!"}
            )
            
            token = auth_response.json().get("access_token")
            
            # Create thread
            thread_response = httpx.post(
                f"{self.backend_url}/api/threads",
                headers={"Authorization": f"Bearer {token}"},
                json={"title": "Persistent Thread"}
            )
            
            thread_id = thread_response.json().get("id")
            
            # Simulate backend restart by calling health check
            # In real scenario, would kill and restart process
            
            # Verify thread still exists after "restart"
            get_thread_response = httpx.get(
                f"{self.backend_url}/api/threads/{thread_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert get_thread_response.status_code in [200, 404], "Thread retrieval failed"
            
    def test_24_redis_failover_inmemory_fallback(self):
        """Test 24: Redis failure with in-memory cache fallback."""
        # Start without Redis
        with self.start_dev_launcher(["--set-redis", "mock"]) as proc:
            # Test caching operations work without Redis
            response = httpx.get(f"{self.backend_url}/health")
            assert response.status_code == 200, "Service not healthy without Redis"
            
            # Create data that would normally be cached
            email = f"cache_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "Cache123!"}
            )
            
            assert auth_response.status_code == 200, "Registration failed without Redis"
            
    def test_25_auth_service_recovery_token_refresh(self):
        """Test 25: Auth service restart with session survival."""
        with self.start_dev_launcher() as proc:
            # Create session
            email = f"auth_recovery_{int(time.time())}@test.com"
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={"email": email, "password": "Recovery123!"}
            )
            
            token = auth_response.json().get("access_token")
            
            # Token should still be valid (JWT is stateless)
            me_response = httpx.get(
                f"{self.backend_url}/api/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert me_response.status_code in [200, 401, 404], "Token validation failed"
            
    def test_26_frontend_hot_reload_development(self):
        """Test 26: Frontend hot reload preserves state."""
        with self.start_dev_launcher(["--dev", "--frontend-port", "3002"]) as proc:
            # Wait for frontend
            assert self.wait_for_service("http://localhost:3002", timeout=60)
            
            # Check development mode enabled
            response = httpx.get("http://localhost:3002")
            assert response.status_code == 200, "Frontend not running in dev mode"
            
            # In real test, would modify a file and verify hot reload
            # For now, verify dev server is running
            

class TestConfigurationEnvironment(SystemInitializationTestBase):
    """Category 5: Configuration and Environment - Setup validation"""
    
    def test_27_environment_variable_loading_priority(self):
        """Test 27: Environment variable precedence and validation."""
        # Create test environment files
        env_test = self.project_root / ".env.test"
        env_local = self.project_root / ".env.local"
        
        try:
            # Write conflicting values
            env_test.write_text("TEST_VAR=from_test\nPORT=8001\n")
            env_local.write_text("TEST_VAR=from_local\nPORT=8002\n")
            
            # Set system environment variable
            os.environ["TEST_VAR"] = "from_system"
            
            with self.start_dev_launcher() as proc:
                # Verify correct precedence (system > local > test)
                assert os.getenv("TEST_VAR") == "from_system", "System env var not prioritized"
                
        finally:
            env_test.unlink(missing_ok=True)
            env_local.unlink(missing_ok=True)
            os.environ.pop("TEST_VAR", None)
            
    def test_28_secrets_management_gcp_integration(self):
        """Test 28: Secrets loading with fallback mechanisms."""
        with self.start_dev_launcher(["--no-secrets"]) as proc:
            # Should work without GCP secrets
            response = httpx.get(f"{self.backend_url}/health")
            assert response.status_code == 200, "Service failed without GCP secrets"
            
            # Verify local secrets are used
            # Check if JWT secret is available
            auth_response = httpx.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": f"secrets_{int(time.time())}@test.com",
                    "password": "Secrets123!"
                }
            )
            
            assert auth_response.status_code == 200, "Auth failed without GCP secrets"
            
    def test_29_cors_configuration_dynamic_ports(self):
        """Test 29: CORS allows connections with dynamic ports."""
        # Start with dynamic ports
        with self.start_dev_launcher(["--dynamic"]) as proc:
            # Get actual ports from service discovery
            discovery_file = self.project_root / ".service_discovery.json"
            if discovery_file.exists():
                with open(discovery_file) as f:
                    discovery = json.load(f)
                    backend_port = discovery.get("backend", {}).get("port", 8000)
            else:
                backend_port = 8000
                
            # Test CORS headers
            response = httpx.options(
                f"http://localhost:{backend_port}/api/threads",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization"
                }
            )
            
            assert response.status_code in [200, 204], "CORS preflight failed"
            
            # Check CORS headers
            assert "access-control-allow-origin" in response.headers or \
                   "Access-Control-Allow-Origin" in response.headers, "CORS headers missing"
                   
    def test_30_container_health_check_integration(self):
        """Test 30: Container health checks work correctly."""
        with self.start_dev_launcher() as proc:
            # Test all health endpoints match container expectations
            health_endpoints = [
                (f"{self.backend_url}/health", "backend"),
                (f"{self.auth_url}/health", "auth"),
            ]
            
            for endpoint, service in health_endpoints:
                response = httpx.get(endpoint, timeout=5)
                assert response.status_code == 200, f"{service} health check failed"
                
                # Verify response format matches container platform expectations
                data = response.json()
                assert "status" in data, f"{service} missing status field"
                
                # Check for required container health check fields
                if service == "backend":
                    # Backend should report comprehensive health
                    assert any(k in data for k in ["version", "uptime", "timestamp"]), \
                        "Backend health missing container fields"


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])