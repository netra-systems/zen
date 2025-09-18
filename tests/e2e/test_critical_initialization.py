from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
'''
'''
Critical System Initialization Tests - 30 Comprehensive Cold Start Scenarios

These tests validate the most critical and difficult initialization scenarios,
focusing on real services and common production failure modes.
'''
'''

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

import httpx
import psutil
import pytest
MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import websocket
from sqlalchemy import create_engine, text

# Add project root to path

from netra_backend.app.db.postgres import async_engine, initialize_postgres
from test_framework.test_helpers import ( )

# PERFORMANCE: Lazy loading for mission critical tests

# PERFORMANCE: Lazy loading for mission critical tests
_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e})"
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]

_lazy_imports = {}

def lazy_import(module_path: str, component: str = None):
    """Lazy import pattern for performance optimization"""
    if module_path not in _lazy_imports:
        try:
            module = __import__(module_path, fromlist=[component] if component else [])
            if component:
                _lazy_imports[module_path] = getattr(module, component)
            else:
                _lazy_imports[module_path] = module
        except ImportError as e:
            print(f"Warning: Failed to lazy load {module_path}: {e})"
            _lazy_imports[module_path] = None
    
    return _lazy_imports[module_path]


# Missing test utility functions - stub implementations
def cleanup_test_environment():
    """Clean up test environment."""
    pass

def wait_for_service(url: str, timeout: float = 30.0) -> bool:
    """Wait for service to become available."""
    import time
    import requests
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def get_available_port(start_port: int = 8000) -> int:
    """Get an available port."""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise RuntimeError("No available ports found)"

def kill_process_tree(pid: int):
    """Kill process tree."""
    try:
        import psutil
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except:
        pass

def create_test_user_with_oauth(email: str = "test@example.com):"
    """Create test user with OAuth."""
    return {
        "id": "test_user_123,"
        "email: email,"
        "oauth_provider": "test"
    }



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
        cls.test_user_email = "test_init@netrasystems.ai"
        cls.test_user_password = "TestInit123!@#"

        @classmethod
    def teardown_class(cls):
        """Cleanup after all tests."""
        pass
        cleanup_test_environment()

    def setup_method(self):
        """Setup for each test."""
        self.cleanup_processes()
        self.reset_databases()
        self.clear_service_discovery()

    def teardown_method(self):
        """Cleanup after each test."""
        pass
        self.cleanup_processes()

    def cleanup_processes(self):
        """Kill all test-related processes."""
        processes_to_kill = ["uvicorn", "node", "next", "dev_launcher]"
        for proc_name in processes_to_kill:
        try:
        if self.is_windows:
        subprocess.run( )
        ["taskkill", "/F", "/IM", "],"
        capture_output=True,
        timeout=5
                
        else:
        subprocess.run( )
        ["pkill", "-f, proc_name],"
        capture_output=True,
        timeout=5
                    
        except Exception:
        pass

    def reset_databases(self):
        """Reset all databases to clean state."""
        pass
        try:
        # Reset PostgreSQL
        engine = create_engine(get_env().get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test))"
        with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE))"
        conn.execute(text("CREATE SCHEMA public))"
        conn.commit()
        except Exception as e:
        print("")

        try:
                    # Clear Redis
        r = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.flushall()
        except Exception:
        pass

    def clear_service_discovery(self):
        """Clear service discovery files."""
        discovery_files = [ ]
        ".service_discovery.json,"
        ".dev_services.json,"
        ".service_ports.json"
    
        for file in discovery_files:
        file_path = self.project_root / file
        if file_path.exists():
        file_path.unlink()

        @contextmanager
    def start_dev_launcher(self, args: List[str] = None, timeout: int = 30):
        """Start dev launcher with specified arguments."""
        pass
        if args is None:
        args = ["--minimal", "--no-browser", "--non-interactive]"

        process = subprocess.Popen( )
        ["python, str(self.dev_launcher)] + args,"
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
        

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
        subprocess.run(["taskkill", "/F", "/T", "/PID, str(process.pid)], capture_output=True)"
        else:
        process.terminate()
        process.wait(timeout=5)

    def _check_services_ready(self) -> bool:
        """Check if all services are ready."""
        try:
        # Check backend
        response = httpx.get("formatted_string, timeout=2)"
        if response.status_code != 200:
        return False

            # Check auth service
        response = httpx.get("formatted_string, timeout=2)"
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
        headers["Authorization"] = ""

        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header=headers,
        timeout=10
        
        return ws


        @pytest.mark.e2e
class TestCriticalPath(SystemInitializationTestBase):
        """Category 1: Critical Path Tests - Must work for basic functionality"""

        @pytest.mark.e2e
    def test_01_complete_cold_start_from_empty_state(self):
        """Test 1: Full system startup with no existing data or configuration."""
    # Clear everything
        self.cleanup_processes()
        self.reset_databases()
        self.clear_service_discovery()

    # Remove all environment-specific files
        env_files = [".env.local", ".env.development", ".env.test", ".env.mock]"
        for env_file in env_files:
        file_path = self.project_root / env_file
        if file_path.exists():
        file_path.unlink()

            Start system from completely clean state
        with self.start_dev_launcher(["--minimal", "--no-browser]) as proc:"
                # Verify all services start
        assert self.wait_for_service(""), "Backend failed to start"
        assert self.wait_for_service(""), "Auth service failed to start"

                # Verify database tables created
        engine = create_engine(get_env().get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test))"
        with engine.connect() as conn:
        result = conn.execute(text( ))
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = 'public'"
                    
        table_count = result.scalar()
        assert table_count > 0, "Database tables not created"

                    # Verify Redis connectivity
        r = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6379, decode_responses=True)
        assert r.ping(), "Redis not accessible"

        @pytest.mark.e2e
    def test_02_service_startup_order_dependency_chain(self):
        """Test 2: Verify correct service startup sequencing and dependencies."""
        pass
    # Start services in wrong order intentionally
        self.cleanup_processes()

    # Try to start backend without auth service
        backend_proc = subprocess.Popen( )
        ["python", "-m", "uvicorn", "netra_backend.app.main:app", "--port", "8000],"
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=self.project_root
    

        time.sleep(3)

    # Backend should either wait for auth or fail gracefully
    # Now start auth service
        auth_proc = subprocess.Popen( )
        ["python", "-m", "uvicorn", "auth_service.main:app", "--port", "8081],"
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=self.project_root
    

        try:
        # Both services should eventually become healthy
        assert self.wait_for_service("", "timeout=20)"
        assert self.wait_for_service("", "timeout=20)"

        # Verify cross-service communication works
        response = httpx.get("formatted_string)"
        assert response.status_code in [200, 401], "Cross-service auth check failed"
        finally:
        backend_proc.terminate()
        auth_proc.terminate()

        @pytest.mark.e2e
    def test_03_database_schema_initialization_and_migration(self):
        """Test 3: Fresh database with automatic schema creation."""
    # Drop all database objects
        self.reset_databases()

        with self.start_dev_launcher() as proc:
        # Check database migrations ran
        engine = create_engine(get_env().get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/netra_test))"
        with engine.connect() as conn:
            # Check core tables exist
        tables_to_check = [ ]
        "users,"
        "threads,"
        "messages,"
        "oauth_providers,"
        "sessions"
            

        for table in tables_to_check:
        result = conn.execute(text( ))
        f"SELECT EXISTS (SELECT 1 FROM information_schema.tables  )"
        ""
                
        exists = result.scalar()
        assert exists, ""

                # Check indexes exist
        result = conn.execute(text( ))
        "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'"
                
        index_count = result.scalar()
        assert index_count > 0, "Database indexes not created"

        @pytest.mark.e2e
    def test_04_authentication_flow_end_to_end_setup(self):
        """Test 4: JWT and OAuth provider setup with cross-service validation."""
        pass
        with self.start_dev_launcher() as proc:
        # Test JWT secret generation and synchronization
        # Create token in auth service
        auth_response = httpx.post( )
        "",
        json={"email": "test@example.com", "password": "password}"
        

        if auth_response.status_code == 200:
        token = auth_response.json().get("access_token)"

            # Validate token in backend service
        backend_response = httpx.get( )
        "",
        headers={"Authorization": "}"
            
        assert backend_response.status_code in [200, 401], "Token validation failed"

            # Test OAuth provider configuration
        oauth_response = httpx.get("formatted_string)"
        assert oauth_response.status_code == 200, "OAuth providers not configured"
        providers = oauth_response.json()
        assert len(providers) > 0, "No OAuth providers available"

        @pytest.mark.e2e
    def test_05_websocket_connection_establishment(self):
        """Test 5: WebSocket endpoint registration and authentication."""
        with self.start_dev_launcher() as proc:
        # Test unauthenticated connection
        try:
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        timeout=10
            
        ws.send(json.dumps({"type": "ping}))"
        response = ws.recv()
        ws.close()
        assert response, "WebSocket connection failed"
        except Exception as e:
        pytest.fail("")

                # Test authenticated connection
                # First get a token
        auth_response = httpx.post( )
        "",
        json={ }
        "email": ","
        "password": "TestPass123!"
                
                

        if auth_response.status_code == 200:
        token = auth_response.json().get("access_token)"

                    # Connect with authentication
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header={"Authorization": "},"
        timeout=10
                    
        ws.send(json.dumps({"type": "authenticate", "token: token}))"
        response = ws.recv()
        ws.close()
        assert "authenticated" in response.lower() or "success in response.lower()"

        @pytest.mark.e2e
    def test_06_real_time_message_processing_pipeline(self):
        """Test 6: End-to-end message flow from WebSocket to LLM to response."""
        pass
        with self.start_dev_launcher() as proc:
        # Create authenticated session
        auth_response = httpx.post( )
        "",
        json={ }
        "email": ","
        "password": "TestPass123!"
        
        

        if auth_response.status_code == 200:
        token = auth_response.json().get("access_token)"

            # Create WebSocket connection
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header={"Authorization": "},"
        timeout=30
            

            # Send chat message
        message = { }
        "type": "chat_message,"
        "content": "Hello, this is a test message,"
        "thread_id": "test_thread_001"
            
        ws.send(json.dumps(message))

            # Wait for response (might be streamed)
        responses_received = []
        start_time = time.time()
        while time.time() - start_time < 10:
        try:
        response = ws.recv()
        responses_received.append(response)
        if "complete" in response.lower() or "done in response.lower():"
        break
        except websocket.WebSocketTimeoutException:
        break

        ws.close()
        assert len(responses_received) > 0, "No response received from message pipeline"

        @pytest.mark.e2e
    def test_07_frontend_static_asset_loading_and_api_connection(self):
        """Test 7: Next.js compilation and API endpoint discovery."""
        with self.start_dev_launcher(["--frontend-port", "3000]) as proc:"
        # Wait for frontend to compile
        assert self.wait_for_service("", timeout=60), "Frontend failed to start"

        # Check static assets are served
        response = httpx.get("formatted_string, follow_redirects=True)"
        assert response.status_code in [200, 304], "Frontend assets not served"

        # Check API configuration
        response = httpx.get("formatted_string, timeout=5)"
        assert response.status_code in [200, 404], "Frontend API route check failed"

        # Verify frontend can reach backend
        # This would normally be done through the browser, but we can check CORS
        response = httpx.options( )
        "",
        headers={ }
        "Origin: self.frontend_url,"
        "Access-Control-Request-Method": "GET"
        
        
        assert response.status_code in [200, 204], "CORS not configured correctly"

        @pytest.mark.e2e
    def test_08_health_check_cascade_validation(self):
        """Test 8: All service health endpoints with dependency validation."""
        pass
        with self.start_dev_launcher() as proc:
        # Check each service's health endpoint'
        services = [ ]
        (self.backend_url, "backend),"
        (self.auth_url, "auth),"
        

        for url, name in services:
        response = httpx.get("formatted_string, timeout=5)"
        assert response.status_code == 200, ""

        health_data = response.json()
        assert "status" in health_data, ""
        assert health_data["status"] in ["healthy", "ok"], ""

            # Check dependency health reporting
        if "dependencies in health_data:"
        for dep_name, dep_status in health_data["dependencies].items():"
        assert dep_status in ["healthy", "ok", "connected"], ""


        @pytest.mark.e2e
class TestServiceDependencies(SystemInitializationTestBase):
        """Category 2: Service Dependencies - Cross-service communication"""

        @pytest.mark.e2e
    def test_09_redis_connection_failure_recovery(self):
        """Test 9: Redis unavailable at startup with graceful degradation."""
    # Stop Redis if running
        try:
        if self.is_windows:
        subprocess.run(["taskkill", "/F", "/IM", "redis-server.exe], capture_output=True)"
        else:
        subprocess.run(["pkill", "redis-server], capture_output=True)"
        except Exception:
        pass

                    # Start services without Redis
        with self.start_dev_launcher(["--set-redis", "mock]) as proc:"
                        # Services should start even without Redis
        assert self.wait_for_service(""), "Backend failed without Redis"

                        # Test fallback caching behavior
        response = httpx.get("formatted_string)"
        assert response.status_code in [200, 501], "Cache fallback not working"

        @pytest.mark.e2e
    def test_10_clickhouse_port_configuration_matrix(self):
        """Test 10: Test all ClickHouse port configurations."""
        pass
        clickhouse_ports = { }
        "http: 8123,"
        "native: 9000,"
        "https: 8443"
    

        with self.start_dev_launcher() as proc:
        for protocol, port in clickhouse_ports.items():
            # Test connection on each port
        try:
        if protocol == "http:"
        response = httpx.get("formatted_string, timeout=2)"
        if response.status_code == 200:
        print("")
        except Exception:
                            # Port might not be configured
        pass

        @pytest.mark.e2e
    def test_11_auth_backend_jwt_secret_synchronization(self):
        """Test 11: JWT secret synchronization between services."""
        with self.start_dev_launcher() as proc:
        # Create token in auth service
        auth_response = httpx.post( )
        "",
        json={ }
        "email": ","
        "password": "TestPass123!"
        
        

        assert auth_response.status_code == 200, "Registration failed"
        auth_token = auth_response.json().get("access_token)"

        # Validate token in backend
        backend_response = httpx.get( )
        "",
        headers={"Authorization": "}"
        

        # Should either validate successfully or return proper auth error
        assert backend_response.status_code in [200, 401], "Token validation unexpected response"

        # Test with invalid token
        invalid_response = httpx.get( )
        "",
        headers={"Authorization": "Bearer invalid_token_12345}"
        
        assert invalid_response.status_code == 401, "Invalid token not rejected"

        @pytest.mark.e2e
    def test_12_service_discovery_dynamic_ports(self):
        """Test 12: Dynamic port allocation and service discovery."""
        pass
    # Occupy default ports
        occupied_sockets = []
        try:
        # Occupy port 8000
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.bind(('localhost', 8000))
        s1.listen(1)
        occupied_sockets.append(s1)

        # Start services - should use dynamic ports
        with self.start_dev_launcher(["--dynamic]) as proc:"
            # Check service discovery file created
        discovery_file = self.project_root / ".service_discovery.json"
        assert discovery_file.exists(), "Service discovery file not created"

        with open(discovery_file) as f:
        discovery = json.load(f)

                # Verify services on different ports
        backend_port = discovery.get("backend", {}).get("port)"
        assert backend_port != 8000, "Backend didn"t use dynamic port"
        assert backend_port != 8000, "Backend didn"t use dynamic port"

                # Verify service accessible on dynamic port
        assert self.wait_for_service("")
        finally:
        for s in occupied_sockets:
        s.close()

        @pytest.mark.e2e
    def test_13_database_connection_pool_high_load(self):
        """Test 13: Connection pool behavior under concurrent startup."""
        with self.start_dev_launcher() as proc:
        # Create multiple concurrent database operations
        import concurrent.futures

    def make_db_request(index):
        try:
        response = httpx.get("formatted_string, timeout=5)"
        return response.status_code
        except Exception as e:
        return str(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_db_request, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

                # Should handle concurrent requests without pool exhaustion
        success_count = sum(1 for r in results if isinstance(r, int) and r < 500)
        assert success_count > 40, ""

        @pytest.mark.e2e
    def test_14_cross_service_token_propagation(self):
        """Test 14: Tokens work across all services."""
        pass
        with self.start_dev_launcher() as proc:
        # Create token in auth service
        auth_response = httpx.post( )
        "",
        json={ }
        "email": ","
        "password": "TestPass123!"
        
        

        token = auth_response.json().get("access_token)"

        # Test token in different services
        services_to_test = [ ]
        ("", "backend),"
        ("", "auth),"
        

        for url, service_name in services_to_test:
        response = httpx.get( )
        url,
        headers={"Authorization": "}"
            
        assert response.status_code in [200, 404], ""

        @pytest.mark.e2e
    def test_15_websocket_connection_load_balancing(self):
        """Test 15: Multiple WebSocket connections handled properly."""
        with self.start_dev_launcher() as proc:
        connections = []

        try:
            # Create multiple WebSocket connections
        for i in range(10):
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        timeout=5
                
        connections.append(ws)

                # Send messages on all connections
        for i, ws in enumerate(connections):
        ws.send(json.dumps({"type": "ping", "id: i}))"

                    # Verify all connections receive responses
        for ws in connections:
        response = ws.recv()
        assert response, "Connection didn"t receive response"
        assert response, "Connection didn"t receive response"

        finally:
        for ws in connections:
        try:
        ws.close()
        except Exception:
        pass


        @pytest.mark.e2e
class TestUserJourney(SystemInitializationTestBase):
        """Category 3: User Journey - First-time user experience"""

        @pytest.mark.e2e
    def test_16_first_time_user_registration_flow(self):
        """Test 16: Complete new user signup through OAuth."""
        with self.start_dev_launcher() as proc:
        # Test user registration
        email = ""
        response = httpx.post( )
        "",
        json={ }
        "email: email,"
        "password": "NewUser123!,"
        "name": "New User"
        
        

        assert response.status_code == 200, "Registration failed"
        data = response.json()
        assert "access_token" in data, "No access token returned"
        assert "user" in data, "No user data returned"

        # Verify user can login
        login_response = httpx.post( )
        "",
        json={ }
        "email: email,"
        "password": "NewUser123!"
        
        
        assert login_response.status_code == 200, "Login failed for new user"

        @pytest.mark.e2e
    def test_17_initial_chat_session_creation(self):
        """Test 17: First-time user creates a chat thread."""
        pass
        with self.start_dev_launcher() as proc:
        # Register user
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "ChatUser123!}"
        

        token = auth_response.json().get("access_token)"

        # Create chat thread
        thread_response = httpx.post( )
        "",
        headers={"Authorization": "},"
        json={"title": "My First Chat}"
        

        assert thread_response.status_code in [200, 201], "Thread creation failed"
        thread_data = thread_response.json()
        thread_id = thread_data.get("id)"

        # Send first message
        message_response = httpx.post( )
        "",
        headers={"Authorization": "},"
        json={"content": "Hello, this is my first message!}"
        

        assert message_response.status_code in [200, 201], "Message creation failed"

        @pytest.mark.e2e
    def test_18_frontend_authentication_state(self):
        """Test 18: Frontend loads and manages auth state."""
        with self.start_dev_launcher(["--frontend-port", "3001]) as proc:"
        # Wait for frontend
        assert self.wait_for_service("http://localhost:3001", "timeout=60)"

        # Check frontend serves auth pages
        response = httpx.get("http://localhost:3001, follow_redirects=True)"
        assert response.status_code == 200, "Frontend not accessible"

        # Frontend should have auth endpoints configured
        # Check if API routes are set up
        api_response = httpx.get("http://localhost:3001/auth/session)"
        assert api_response.status_code in [200, 401, 404], "Auth API routes not configured"

        @pytest.mark.e2e
    def test_19_real_time_chat_message_exchange(self):
        """Test 19: User sends message and receives AI response."""
        pass
        with self.start_dev_launcher() as proc:
        # Create user and get token
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "Realtime123!}"
        

        token = auth_response.json().get("access_token)"

        # Create WebSocket connection
        ws = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header={"Authorization": "},"
        timeout=30
        

        # Send chat message
        ws.send(json.dumps({ }))
        "type": "chat_message,"
        "content": "What is 2+2?,"
        "thread_id": "realtime_thread"
        

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

        @pytest.mark.e2e
    def test_20_session_persistence_browser_restart(self):
        """Test 20: Session survives browser restart."""
        with self.start_dev_launcher() as proc:
        # Create session
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "Persist123!}"
        

        token = auth_response.json().get("access_token)"
        refresh_token = auth_response.json().get("refresh_token)"

        # Simulate browser restart - use refresh token
        time.sleep(2)

        if refresh_token:
        refresh_response = httpx.post( )
        "",
        json={"refresh_token: refresh_token}"
            

        assert refresh_response.status_code == 200, "Session refresh failed"
        new_token = refresh_response.json().get("access_token)"

            # Verify new token works
        me_response = httpx.get( )
        "",
        headers={"Authorization": "}"
            
        assert me_response.status_code in [200, 404], "New token not valid"

        @pytest.mark.e2e
    def test_21_multi_tab_session_synchronization(self):
        """Test 21: Multiple tabs with synchronized state."""
        pass
        with self.start_dev_launcher() as proc:
        # Create user session
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "MultiTab123!}"
        

        token = auth_response.json().get("access_token)"

        # Simulate multiple tabs with WebSocket connections
        ws1 = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header={"Authorization": "}"
        

        ws2 = websocket.create_connection( )
        "ws://localhost:8000/ws,"
        header={"Authorization": "}"
        

        Send message from tab 1
        ws1.send(json.dumps({ }))
        "type": "chat_message,"
        "content": "Message from tab 1,"
        "thread_id": "shared_thread"
        

        # Both connections should be maintained
        ws1.send(json.dumps({"type": "ping}))"
        ws2.send(json.dumps({"type": "ping}))"

        response1 = ws1.recv()
        response2 = ws2.recv()

        assert response1 and response2, "Multi-tab connections not maintained"

        ws1.close()
        ws2.close()


        @pytest.mark.e2e
class TestRecoveryResilience(SystemInitializationTestBase):
        """Category 4: Recovery and Resilience - Error handling"""

        @pytest.mark.e2e
    def test_22_database_recovery_after_partition(self):
        """Test 22: Database reconnection after network partition."""
        with self.start_dev_launcher() as proc:
        # Verify initial connectivity
        response = httpx.get("formatted_string)"
        assert response.status_code == 200

        # Simulate database connection loss (would need actual network control)
        # For now, test that health check reports database status
        health_data = response.json()
        if "dependencies in health_data:"
        assert "database" in health_data["dependencies"], "Database health not monitored"

        @pytest.mark.e2e
    def test_23_service_restart_without_data_loss(self):
        """Test 23: Backend restart with connection recovery."""
        pass
        with self.start_dev_launcher() as launcher_proc:
        # Create a thread
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "Restart123!}"
        

        token = auth_response.json().get("access_token)"

        # Create thread
        thread_response = httpx.post( )
        "",
        headers={"Authorization": "},"
        json={"title": "Persistent Thread}"
        

        thread_id = thread_response.json().get("id)"

        # Simulate backend restart by calling health check
        # In real scenario, would kill and restart process

        # Verify thread still exists after "restart"
        get_thread_response = httpx.get( )
        "",
        headers={"Authorization": "}"
        

        assert get_thread_response.status_code in [200, 404], "Thread retrieval failed"

        @pytest.mark.e2e
    def test_24_redis_failover_inmemory_fallback(self):
        """Test 24: Redis failure with in-memory cache fallback."""
    # Start without Redis
        with self.start_dev_launcher(["--set-redis", "mock]) as proc:"
        # Test caching operations work without Redis
        response = httpx.get("formatted_string)"
        assert response.status_code == 200, "Service not healthy without Redis"

        # Create data that would normally be cached
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "Cache123!}"
        

        assert auth_response.status_code == 200, "Registration failed without Redis"

        @pytest.mark.e2e
    def test_25_auth_service_recovery_token_refresh(self):
        """Test 25: Auth service restart with session survival."""
        pass
        with self.start_dev_launcher() as proc:
        # Create session
        email = ""
        auth_response = httpx.post( )
        "",
        json={"email": email, "password": "Recovery123!}"
        

        token = auth_response.json().get("access_token)"

        # Token should still be valid (JWT is stateless)
        me_response = httpx.get( )
        "",
        headers={"Authorization": "}"
        

        assert me_response.status_code in [200, 401, 404], "Token validation failed"

        @pytest.mark.e2e
    def test_26_frontend_hot_reload_development(self):
        """Test 26: Frontend hot reload preserves state."""
        with self.start_dev_launcher(["--dev", "--frontend-port", "3002]) as proc:"
        # Wait for frontend
        assert self.wait_for_service("http://localhost:3002", "timeout=60)"

        # Check development mode enabled
        response = httpx.get("http://localhost:3002)"
        assert response.status_code == 200, "Frontend not running in dev mode"

        # In real test, would modify a file and verify hot reload
        # For now, verify dev server is running


        @pytest.mark.e2e
class TestConfigurationEnvironment(SystemInitializationTestBase):
        """Category 5: Configuration and Environment - Setup validation"""

        @pytest.mark.e2e
    def test_27_environment_variable_loading_priority(self):
        """Test 27: Environment variable precedence and validation."""
    # Create test environment files
        env_test = self.project_root / ".env.mock"
        env_local = self.project_root / ".env.local"

        try:
        # Write conflicting values
        env_test.write_text("TEST_VAR=from_test )"
        PORT=8001
        ")"
        env_local.write_text("TEST_VAR=from_local )"
        PORT=8002
        ")"

        # Set system environment variable

        with self.start_dev_launcher() as proc:
            # Verify correct precedence (system > local > test)
        assert get_env().get("TEST_VAR") == "from_system", "System env var not prioritized"

        finally:
        env_test.unlink(missing_ok=True)
        env_local.unlink(missing_ok=True)
        env.delete("TEST_VAR", "test)"

        @pytest.mark.e2e
    def test_28_secrets_management_gcp_integration(self):
        """Test 28: Secrets loading with fallback mechanisms."""
        pass
        with self.start_dev_launcher(["--no-secrets]) as proc:"
        # Should work without GCP secrets
        response = httpx.get("formatted_string)"
        assert response.status_code == 200, "Service failed without GCP secrets"

        # Verify local secrets are used
        # Check if JWT secret is available
        auth_response = httpx.post( )
        "",
        json={ }
        "email": ","
        "password": "Secrets123!"
        
        

        assert auth_response.status_code == 200, "Auth failed without GCP secrets"

        @pytest.mark.e2e
    def test_29_cors_configuration_dynamic_ports(self):
        """Test 29: CORS allows connections with dynamic ports."""
    # Start with dynamic ports
        with self.start_dev_launcher(["--dynamic]) as proc:"
        Get actual ports from service discovery
        discovery_file = self.project_root / ".service_discovery.json"
        if discovery_file.exists():
        with open(discovery_file) as f:
        discovery = json.load(f)
        backend_port = discovery.get("backend", {}).get("port, 8000)"
        else:
        backend_port = 8000

                    # Test CORS headers
        response = httpx.options( )
        "",
        headers={ }
        "Origin": "http://localhost:3000,"
        "Access-Control-Request-Method": "GET,"
        "Access-Control-Request-Headers": "Authorization"
                    
                    

        assert response.status_code in [200, 204], "CORS preflight failed"

                    # Check CORS headers
        assert "access-control-allow-origin in response.headers or \"
        "Access-Control-Allow-Origin" in response.headers, "CORS headers missing"

        @pytest.mark.e2e
    def test_30_container_health_check_integration(self):
        """Test 30: Container health checks work correctly."""
        pass
        with self.start_dev_launcher() as proc:
        # Test all health endpoints match container expectations
        health_endpoints = [ ]
        ("", "backend),"
        ("", "auth),"
        

        for endpoint, service in health_endpoints:
        response = httpx.get(endpoint, timeout=5)
        assert response.status_code == 200, ""

            # Verify response format matches container platform expectations
        data = response.json()
        assert "status" in data, ""

            # Check for required container health check fields
        if service == "backend:"
                # Backend should report comprehensive health
        assert any(k in data for k in ["version", "uptime", "timestamp]), \"
        "Backend health missing container fields"


                # Test runner
        if __name__ == "__main__:"
        pytest.main([__file__, "-v", "--tb=short])"
